from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelRequestError  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24318_deadline_conservation_runtime import (  # noqa: E402
    CACHE_FIELD,
    MODEL_FIELD,
    run_v24318_task,
    validate_v24318_result,
)
from test_v24272_two_wave_retrieval import FakeSearch  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402
from test_v24290_low_coverage_task_runtime import TABLE, plan, task  # noqa: E402


class PreProviderRejection(ModelRequestError):
    pass


class Model:
    def __init__(self, values):
        self.values = list(values)
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, *_args, **_kwargs):
        value = self.values.pop(0)
        if isinstance(value, PreProviderRejection):
            raise value
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


class ManualClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class ExpiringSearch(TailSearch):
    def __init__(self, clock, *, staged):
        super().__init__(sparse=staged)
        self.clock = clock

    def fetch_urls(self, requests_):
        value = super().fetch_urls(requests_)
        self.clock.value = 121.0
        return value


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


def call(arm: str, values, *, search=None, clock=None):
    return run_v24318_task(
        task(),
        arm=arm,
        model=Model(values),
        search=search or TailSearch(sparse=True, failed_fetches=8),
        limits=limits(),
        two_wave_policy=TwoWavePolicy(),
        reserve_policy=StagedReservePolicy() if arm == "candidate" else None,
        monotonic=clock or ManualClock(),
    )


class V24318DeadlineConservationRuntimeTests(unittest.TestCase):
    def test_normal_success_keeps_exact_provider_equality(self) -> None:
        for arm in ("baseline", "candidate"):
            value = call(arm, [plan(), TABLE])
            self.assertEqual(validate_v24318_result(value, arm), "candidate")
            receipt = value[MODEL_FIELD]
            self.assertEqual(receipt["logical_admissions_total"], 2)
            self.assertEqual(receipt["provider_requests_total"], 2)
            self.assertEqual(receipt["pre_provider_rejections_total"], 0)

    def test_initial_synthesis_pre_provider_rejection_is_not_retried(self) -> None:
        value = call(
            "candidate",
            [plan(), PreProviderRejection("content-free synthetic")],
        )
        self.assertEqual(validate_v24318_result(value, "candidate"), "candidate")
        receipt = value[MODEL_FIELD]
        self.assertEqual(receipt["logical_admissions_total"], 2)
        self.assertEqual(receipt["provider_requests_total"], 1)
        self.assertEqual(receipt["pre_provider_rejections_total"], 1)
        self.assertFalse(receipt["synthesis_recovery_attempted"])

    def test_recovery_pre_provider_rejection_is_conserved(self) -> None:
        value = call(
            "candidate",
            [
                plan(),
                ModelRequestError("content-free provider failure"),
                PreProviderRejection("content-free deadline rejection"),
            ],
        )
        self.assertEqual(validate_v24318_result(value, "candidate"), "candidate")
        receipt = value[MODEL_FIELD]
        self.assertEqual(receipt["logical_admissions_total"], 3)
        self.assertEqual(receipt["provider_requests_total"], 2)
        self.assertEqual(receipt["pre_provider_rejections_total"], 1)
        self.assertTrue(receipt["synthesis_recovery_attempted"])

    def test_repair_pre_provider_rejection_is_conserved(self) -> None:
        value = call(
            "baseline",
            [plan(), "not a table", PreProviderRejection("content-free")],
        )
        self.assertEqual(validate_v24318_result(value, "baseline"), "candidate")
        receipt = value[MODEL_FIELD]
        self.assertEqual(receipt["logical_admissions_by_stage"]["repair"], 1)
        self.assertEqual(receipt["pre_provider_rejections_by_stage"]["repair"], 1)

    def test_candidate_cached_pages_can_be_deadline_deferred(self) -> None:
        clock = ManualClock()
        value = call(
            "candidate",
            [plan()],
            search=ExpiringSearch(clock, staged=True),
            clock=clock,
        )
        self.assertEqual(validate_v24318_result(value, "candidate"), "candidate")
        cache = value[CACHE_FIELD]
        self.assertGreater(cache["cached_usable_pages"], 0)
        self.assertEqual(cache["cache_returned_pages"], 0)
        self.assertEqual(
            cache["cached_usable_pages"], cache["deadline_deferred_pages"]
        )

    def test_baseline_cached_pages_can_be_deadline_deferred(self) -> None:
        clock = ManualClock()
        search = ExpiringSearch(clock, staged=False)
        value = call("baseline", [plan()], search=search, clock=clock)
        self.assertEqual(validate_v24318_result(value, "baseline"), "candidate")
        self.assertGreater(value[CACHE_FIELD]["deadline_deferred_pages"], 0)

    def test_conservation_tamper_fails_closed(self) -> None:
        value = call("candidate", [plan(), TABLE])
        for field in (MODEL_FIELD, CACHE_FIELD):
            altered = copy.deepcopy(value)
            if field == MODEL_FIELD:
                altered[field]["pre_provider_rejections_total"] += 1
            else:
                altered[field]["deadline_deferred_pages"] += 1
            with self.assertRaises(ValueError):
                validate_v24318_result(altered, "candidate")

    def test_receipts_are_content_free_and_privileged_input_fails_before_effect(self) -> None:
        value = call("candidate", [plan(), TABLE])
        encoded = json.dumps(
            {MODEL_FIELD: value[MODEL_FIELD], CACHE_FIELD: value[CACHE_FIELD]}
        ).casefold()
        self.assertNotIn(task()["opaque_id"].casefold(), encoded)
        model = Model([plan(), TABLE])
        search = FakeSearch()
        with self.assertRaises(ValueError):
            run_v24318_task(
                {**task(), "question_type": "forbidden"},
                arm="baseline",
                model=model,
                search=search,
                limits=limits(),
                two_wave_policy=TwoWavePolicy(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
