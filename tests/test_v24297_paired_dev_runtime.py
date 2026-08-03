from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24297_paired_dev_runtime import (  # noqa: E402
    run_v24297_task,
    validate_v24297_result,
)
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402


LIMITS = ScoreFirstLimits(
    wall_seconds=180,
    model_calls=3,
    search_queries=4,
    fetch_targets=10,
    search_results_per_query=3,
    evidence_chars=60_000,
    page_chars=5_000,
    plan_output_tokens=4_000,
    synthesis_output_tokens=30_000,
    repair_output_tokens=12_000,
)
TASK = {
    "opaque_id": "task_000000000000000000000001",
    "question": "Return one table. The column names are: Name, Version, and Date.",
}


class FakeModel:
    def __init__(self, values: list[object]) -> None:
        self.values = list(values)
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 8
        self.output_tokens += 4
        self.total_tokens += 12
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


def model() -> FakeModel:
    plan = json.dumps(
        {
            "columns": ["ignored"],
            "queries": ["one", "two", "three", "four"],
        }
    )
    table = "| Name | Version | Date |\n| --- | --- | --- |\n| A | 1 | 2026 |"
    return FakeModel([plan, table])


class V24297PairedDevRuntimeTests(unittest.TestCase):
    def test_baseline_is_frozen_six_plus_four(self) -> None:
        result = run_v24297_task(
            TASK,
            arm="baseline",
            model=model(),
            search=TailSearch(sparse=True, failed_fetches=8),
            limits=LIMITS,
            two_wave_policy=TwoWavePolicy(),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24297_result(result, "baseline"), "candidate")
        receipt = result["two_wave_retrieval"]["receipt"]
        self.assertEqual(receipt["wave1"]["fetches_attempted"], 6)
        self.assertEqual(receipt["wave2"]["fetches_attempted"], 4)

    def test_candidate_is_staged_six_plus_two_plus_two(self) -> None:
        result = run_v24297_task(
            TASK,
            arm="candidate",
            model=model(),
            search=TailSearch(sparse=True, failed_fetches=8),
            limits=LIMITS,
            two_wave_policy=TwoWavePolicy(),
            reserve_policy=StagedReservePolicy(),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24297_result(result, "candidate"), "candidate")
        receipt = result["staged_reserve_retrieval"]["receipt"]
        self.assertEqual(receipt["first_wave"]["fetches_attempted"], 6)
        self.assertEqual(receipt["second_wave_observation"]["fetches_attempted"], 2)
        self.assertEqual(receipt["reserved_stage"]["fetches_attempted"], 2)
        self.assertEqual(receipt["reserved_stage"]["reason"], "low_coverage_diversity_tail")
        self.assertEqual(receipt["hosted_search_requests_added_by_reserved"], 0)

    def test_each_arm_totalizes_failure(self) -> None:
        for arm in ("baseline", "candidate"):
            result = run_v24297_task(
                TASK,
                arm=arm,
                model=FakeModel([KeyboardInterrupt()]),
                search=TailSearch(sparse=False),
                limits=LIMITS,
                two_wave_policy=TwoWavePolicy(),
                reserve_policy=StagedReservePolicy() if arm == "candidate" else None,
                monotonic=Clock(),
            )
            self.assertEqual(validate_v24297_result(result, arm), "fallback")
            self.assertEqual(result["completion_kind"], "worker_failure_fallback")

    def test_privileged_input_and_unknown_arm_are_rejected_before_effects(self) -> None:
        search = TailSearch(sparse=False)
        with self.assertRaises(ValueError):
            run_v24297_task(
                {**TASK, "category": "forbidden"},
                arm="baseline",
                model=model(),
                search=search,
                limits=LIMITS,
                two_wave_policy=TwoWavePolicy(),
            )
        self.assertEqual(search.search_invocations, 0)
        with self.assertRaises(ValueError):
            validate_v24297_result({}, "other")


if __name__ == "__main__":
    unittest.main()
