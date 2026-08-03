from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelRequestError  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD,
    parent_exit_receipt,
    run_v24310_task,
    validate_v24310_result,
)
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402
from test_v24290_low_coverage_task_runtime import FakeModel, TABLE, plan, task  # noqa: E402


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


def call(arm: str, values: list[object]):
    return run_v24310_task(
        task(),
        arm=arm,
        model=FakeModel(values),
        search=TailSearch(sparse=True, failed_fetches=8),
        limits=limits(),
        two_wave_policy=TwoWavePolicy(),
        reserve_policy=StagedReservePolicy() if arm == "candidate" else None,
        monotonic=Clock(),
    )


class V24310PairedDevRuntimeTests(unittest.TestCase):
    def test_both_arms_share_exact_bounded_recovery(self) -> None:
        projected = []
        for arm in ("baseline", "candidate"):
            value = call(arm, [plan(), ModelRequestError("synthetic"), TABLE])
            validate_v24310_result(value, arm)
            receipt = value[RECEIPT_FIELD]
            self.assertTrue(receipt["recovery_enabled"])
            self.assertTrue(receipt["synthesis_recovery_attempted"])
            self.assertTrue(receipt["synthesis_recovery_succeeded"])
            self.assertEqual(receipt["total_effects_admitted"], 3)
            self.assertFalse(receipt["fourth_model_effect"])
            projected.append(
                {key: receipt[key] for key in receipt if key != "arm"}
            )
        self.assertEqual(projected[0], projected[1])

    def test_only_candidate_has_staged_reserve_retrieval(self) -> None:
        baseline = call("baseline", [plan(), TABLE])
        candidate = call("candidate", [plan(), TABLE])
        self.assertIn("two_wave_retrieval", baseline)
        self.assertNotIn("staged_reserve_retrieval", baseline)
        baseline_retrieval = baseline["two_wave_retrieval"]["receipt"]
        self.assertEqual(baseline_retrieval["wave1"]["fetches_attempted"], 6)
        self.assertEqual(baseline_retrieval["wave2"]["fetches_attempted"], 4)
        self.assertIn("staged_reserve_retrieval", candidate)
        self.assertNotIn("two_wave_retrieval", candidate)
        candidate_retrieval = candidate["staged_reserve_retrieval"]["receipt"]
        self.assertEqual(
            candidate_retrieval["first_wave"]["fetches_attempted"], 6
        )
        self.assertEqual(
            candidate_retrieval["second_wave_observation"]["fetches_attempted"],
            2,
        )
        self.assertEqual(
            candidate_retrieval["reserved_stage"]["fetches_attempted"], 2
        )
        self.assertEqual(
            candidate_retrieval["hosted_search_requests_added_by_reserved"], 0
        )

    def test_success_and_repair_do_not_engage_recovery(self) -> None:
        for arm in ("baseline", "candidate"):
            primary = call(arm, [plan(), TABLE])
            self.assertFalse(
                primary[RECEIPT_FIELD]["synthesis_recovery_attempted"]
            )
            repaired = call(arm, [plan(), "not a table", TABLE])
            self.assertEqual(
                repaired[RECEIPT_FIELD]["effects_by_stage"]["repair"], 1
            )
            self.assertFalse(
                repaired[RECEIPT_FIELD]["synthesis_recovery_attempted"]
            )

    def test_privileged_input_rejected_before_effect(self) -> None:
        model = FakeModel([plan(), TABLE])
        search = TailSearch(sparse=False)
        with self.assertRaises(ValueError):
            run_v24310_task(
                {**task(), "question_type": "forbidden"},
                arm="baseline",
                model=model,
                search=search,
                limits=limits(),
                two_wave_policy=TwoWavePolicy(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.search_invocations, 0)

    def test_recovery_receipt_tamper_fails_closed(self) -> None:
        value = call("candidate", [plan(), ModelRequestError("x"), TABLE])
        altered = copy.deepcopy(value)
        altered[RECEIPT_FIELD]["provider_requests_delta"] += 1
        with self.assertRaises(ValueError):
            validate_v24310_result(altered, "candidate")

    def test_second_provider_failure_preserves_three_effects(self) -> None:
        for arm in ("baseline", "candidate"):
            value = call(
                arm,
                [
                    plan(),
                    ModelRequestError("first"),
                    ModelRequestError("second"),
                ],
            )
            self.assertEqual(validate_v24310_result(value, arm), "candidate")
            self.assertEqual(value["completion_kind"], "best_effort_fallback")
            receipt = value[RECEIPT_FIELD]
            self.assertEqual(receipt["total_effects_admitted"], 3)
            self.assertEqual(receipt["provider_requests_delta"], 3)
            self.assertTrue(receipt["synthesis_recovery_attempted"])
            self.assertTrue(receipt["synthesis_recovery_model_request_error"])
            self.assertFalse(receipt["fourth_model_effect"])

    def test_experiment_receipt_is_content_free(self) -> None:
        value = call(
            "candidate",
            [plan(), ModelRequestError("task_0123456789abcdef01234567"), TABLE],
        )
        encoded = json.dumps(value[RECEIPT_FIELD]).casefold()
        for forbidden in (
            task()["opaque_id"],
            task()["question"],
            "task_0123456789abcdef01234567",
            "| a |",
        ):
            self.assertNotIn(forbidden.casefold(), encoded)

    def test_parent_exit_preserves_effect_count_without_guessing_stage(self) -> None:
        value = parent_exit_receipt(
            "baseline",
            provider_requests_lower_bound=2,
            provider_attempts_lower_bound=5,
            admitted_model_effects_upper_bound=3,
            effect_count_complete=False,
        )
        self.assertFalse(value["effect_attribution_complete"])
        self.assertFalse(value["effect_count_complete"])
        self.assertFalse(value["provider_attempt_count_complete"])
        self.assertEqual(value["unattributed_model_effects"], 2)
        self.assertEqual(value["total_effects_admitted"], 2)
        self.assertEqual(value["admitted_model_effects_upper_bound"], 3)
        self.assertFalse(any(value["effects_by_stage"].values()))
        self.assertEqual(value["provider_attempts_delta"], 5)


if __name__ == "__main__":
    unittest.main()
