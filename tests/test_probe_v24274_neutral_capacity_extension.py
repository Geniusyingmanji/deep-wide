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
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

from deepwide_agent.v24272_two_wave_entropy_voc import object_sha256  # noqa: E402
from scripts import probe_v24274_neutral_capacity_extension as target  # noqa: E402
from test_probe_v24273_neutral_capacity_staircase import task  # noqa: E402


def result(levels):
    passing = [value["level"] for value in levels if value["passed"]]
    value = {
        "artifact_version": 1,
        "role": "v24274_neutral_capacity_extension",
        "created_at_unix": 1,
        "probe_scope": "neutral_public_documentation_full_task_concurrency_8_then_16_only",
        "provider": "azure-native-keyless-two-wave-cached",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "levels_requested": list(target.LEVELS),
        "batch_wall_ceilings_seconds": {str(level): target.BATCH_WALL_CEILINGS[level] for level in target.LEVELS},
        "maximum_task_wall_seconds": target.MAXIMUM_TASK_WALL_SECONDS,
        "stop_on_first_failed_level": True,
        "levels": levels,
        "highest_passing_concurrency": max(passing) if passing else 4,
        "all_requested_levels_passed": len(levels) == len(target.LEVELS) and all(value["passed"] for value in levels),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired_once_for_extension": True,
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


class ProbeV24274NeutralCapacityExtensionTests(unittest.TestCase):
    def test_synthetic_8_and_16_pass(self):
        levels = [
            target.summarize_level(level=level, tasks=[task(index + 1) for index in range(level)], batch_wall_seconds=20.0)
            for level in target.LEVELS
        ]
        value = result(levels)
        target.validate_result(value)
        self.assertEqual(value["highest_passing_concurrency"], 16)

    def test_failed_8_stops_extension_and_retains_prior_safe_four(self):
        failed = target.summarize_level(
            level=8,
            tasks=[task(index + 1, fallback=index == 7) for index in range(8)],
            batch_wall_seconds=20.0,
        )
        value = result([failed])
        target.validate_result(value)
        self.assertEqual(value["highest_passing_concurrency"], 4)
        self.assertFalse(value["all_requested_levels_passed"])

    def test_resealed_authority_and_continuation_after_failure_rejected(self):
        failed = target.summarize_level(
            level=8,
            tasks=[task(index + 1, fallback=index == 7) for index in range(8)],
            batch_wall_seconds=20.0,
        )
        passed16 = target.summarize_level(
            level=16,
            tasks=[task(index + 1) for index in range(16)],
            batch_wall_seconds=20.0,
        )
        with self.assertRaisesRegex(RuntimeError, "continued"):
            target.validate_result(result([failed, passed16]))
        value = result([failed])
        altered = copy.deepcopy(value)
        altered["authorization"]["dev_benchmark_launch"] = True
        unsigned = dict(altered)
        unsigned.pop("result_payload_sha256")
        altered["result_payload_sha256"] = object_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "identity"):
            target.validate_result(altered)

    def test_neutral_questions_cover_sixteen_without_urls_or_benchmark_ids(self):
        self.assertEqual(len(target.NEUTRAL_QUESTIONS), 16)
        encoded = "\n".join(target.NEUTRAL_QUESTIONS)
        self.assertNotIn("task_", encoded)
        self.assertNotIn("DeepWide", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
