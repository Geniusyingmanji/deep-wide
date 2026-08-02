from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24272_two_wave_entropy_voc import object_sha256  # noqa: E402
from scripts import probe_v24273_neutral_capacity_staircase as target  # noqa: E402


def task(ordinal: int, *, wall: float = 10.0, fallback: bool = False):
    return {
        "ordinal": ordinal,
        "terminal": True,
        "failure_type": None,
        "completion_kind": "best_effort_fallback" if fallback else "primary",
        "wall_seconds": wall,
        "model_counters": {
            "requests": 2,
            "attempts": 2,
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
        "search_counters": {
            "calls": 1,
            "failures": 2,
            "tool_calls": 1,
            "fetch_calls": 6,
            "fetch_failures": 0,
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
        "stage_seconds": {"plan": 2.0, "search": 5.0, "fetch": 1.0, "synthesis": 2.0},
        "failure_types": [],
        "retrieval_status": "completed",
        "controller_decision": "stop",
        "controller_reason": "first_wave_sufficient",
        "queries_executed": 2,
        "fetches_attempted": 6,
        "usable_pages": 6,
        "unrecoverable_search_failures": 0,
        "cache_miss_count": 0,
        "cache_serve_network_fetches": 0,
        "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


def result(levels):
    passing = [value["level"] for value in levels if value["passed"]]
    value = {
        "artifact_version": 1,
        "role": "v24273_neutral_capacity_staircase",
        "created_at_unix": 1,
        "probe_scope": "neutral_public_documentation_full_task_concurrency_capacity_only",
        "provider": "azure-native-keyless-two-wave-cached",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "levels_requested": list(target.LEVELS),
        "level_batch_wall_ceilings_seconds": {
            str(level): target.LEVEL_BATCH_WALL_CEILINGS[level]
            for level in target.LEVELS
        },
        "maximum_task_wall_seconds": target.MAXIMUM_TASK_WALL_SECONDS,
        "stop_on_first_failed_level": True,
        "levels": levels,
        "highest_passing_concurrency": max(passing) if passing else 0,
        "all_requested_levels_passed": len(levels) == len(target.LEVELS)
        and all(value["passed"] for value in levels),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired_once_for_staircase": True,
        },
        "authorization": {
            "dev_benchmark_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission": False,
            "sota_claim": False,
            "training_credit_assignment": False,
        },
    }
    value["result_payload_sha256"] = object_sha256(value)
    return value


class ProbeV24273NeutralCapacityStaircaseTests(unittest.TestCase):
    def test_all_three_synthetic_levels_pass_and_validate(self):
        levels = [
            target.summarize_level(
                level=level,
                tasks=[task(index + 1) for index in range(level)],
                batch_wall_seconds=12.0,
            )
            for level in target.LEVELS
        ]
        value = result(levels)
        target.validate_result(value)
        self.assertEqual(value["highest_passing_concurrency"], 4)
        self.assertTrue(value["all_requested_levels_passed"])

    def test_fallback_or_slow_task_fails_level(self):
        fallback = target.summarize_level(
            level=2,
            tasks=[task(1), task(2, fallback=True)],
            batch_wall_seconds=12.0,
        )
        self.assertFalse(fallback["passed"])
        self.assertFalse(fallback["checks"]["all_model_generated"])
        slow = target.summarize_level(
            level=1,
            tasks=[task(1, wall=36.0)],
            batch_wall_seconds=36.0,
        )
        self.assertFalse(slow["passed"])
        self.assertFalse(slow["checks"]["maximum_task_wall"])

    def test_continuation_after_failed_level_and_resealed_authority_are_rejected(self):
        first = target.summarize_level(
            level=1, tasks=[task(1)], batch_wall_seconds=12.0
        )
        failed = target.summarize_level(
            level=2,
            tasks=[task(1), task(2, fallback=True)],
            batch_wall_seconds=12.0,
        )
        continued = target.summarize_level(
            level=4,
            tasks=[task(index + 1) for index in range(4)],
            batch_wall_seconds=12.0,
        )
        with self.assertRaisesRegex(RuntimeError, "continued"):
            target.validate_result(result([first, failed, continued]))
        value = result([first])
        altered = copy.deepcopy(value)
        altered["authorization"]["dev_benchmark_launch"] = True
        unsigned = dict(altered)
        unsigned.pop("result_payload_sha256")
        altered["result_payload_sha256"] = object_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "identity"):
            target.validate_result(altered)

    def test_neutral_questions_have_no_benchmark_id_or_url(self):
        encoded = "\n".join(target.NEUTRAL_QUESTIONS)
        self.assertNotIn("task_", encoded)
        self.assertNotIn("DeepWide", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
