from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24328_shared_prefix_capacity_staircase as target  # noqa: E402


def task(ordinal: int, *, passed: bool = True, wall: float = 20.0) -> dict:
    value = {
        "ordinal": ordinal,
        "wall_seconds": wall,
        "parent_taxonomy": "success",
        "all_parent_artifacts_valid": True,
        "result_status": "completed",
        "completion_kind": "identity_no_reserve",
        "effect_accounting_complete": True,
        "prefix_status": "frozen",
        "prefix_producer_execution_count": 1,
        "candidate_identity_handoff": True,
        "proposed_cell_changes": 0,
        "admitted_cell_changes": 0,
        "credited_entropy_positive": False,
        "logical_model_admissions": 3,
        "provider_model_requests": 3,
        "provider_model_attempts": 3,
        "pre_provider_model_rejections": 0,
        "slot_acquisitions": 3,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "slot_total_wait_seconds": 1.5,
        "slot_max_wait_seconds": 1.0,
        "slot_acquisition_counts": [2, 1],
        "core_logical_queries": 4,
        "search_provider_effects": 1,
        "core_fetch_targets": 7,
        "reserve_fetch_targets": 3,
        "core_network_fetch_effects": 7,
        "reserve_network_fetch_effects": 3,
        "core_usable_pages": 6,
        "reserve_usable_pages": 3,
        "repeated_upstream_effects": 0,
        "model_requests": 3,
        "model_attempts": 3,
        "model_total_tokens": 1000,
        "search_calls": 1,
        "fetch_calls": 10,
        "fetch_failures": 0,
        "search_total_tokens": 2000,
        "hosted_search_attempts": 1,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": 10,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": 0,
        "deadline_exhausted": False,
        "model_slot_cap": 2,
        "task_text_identifier_query_url_page_prediction_response_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["checks"] = target._task_checks(value)
    if not passed:
        value["slot_timeouts"] = 1
        value["pre_provider_model_rejections"] = 1
        value["slot_acquisitions"] = 2
        value["slot_acquisition_counts"] = [1, 1]
        value["provider_model_requests"] = 2
        value["provider_model_attempts"] = 2
        value["checks"] = target._task_checks(value)
    value["passed"] = all(value["checks"].values())
    target.validate_task_projection(value)
    return value


class V24328SharedPrefixCapacityTests(unittest.TestCase):
    def test_neutral_tasks_are_visible_only_distinct_and_not_benchmark_selected(self) -> None:
        values = [target.neutral_task(index) for index in range(1, 9)]
        self.assertEqual(len({value["opaque_id"] for value in values}), 8)
        self.assertTrue(all(set(value) == {"opaque_id", "question"} for value in values))
        self.assertEqual(len({value["question"] for value in values}), 1)
        encoded = "\n".join(value["question"] for value in values)
        self.assertNotIn("DeepWide", encoded)
        self.assertNotIn("question_type", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)

    def test_task_projection_is_content_free_and_mechanically_gated(self) -> None:
        value = task(1)
        self.assertTrue(value["passed"])
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.URL.search(encoded))
        self.assertFalse(any(item in encoded for item in target.CONTENT_LITERALS))

    def test_slot_timeout_fails_task_and_level(self) -> None:
        failed = task(2, passed=False)
        self.assertFalse(failed["passed"])
        self.assertFalse(failed["checks"]["no_slot_or_provider_deadline_failure"])
        level = target.summarize_level(
            level=2,
            tasks=[task(1), failed],
            batch_wall_seconds=30.0,
        )
        self.assertFalse(level["passed"])

    def test_missing_child_artifacts_are_content_free_terminal_no_go(self) -> None:
        value = target._local_failure_projection(1)
        self.assertFalse(value["passed"])
        self.assertEqual(value["parent_taxonomy"], "parent_subprocess_exception")
        self.assertEqual(value["model_requests"], 0)
        self.assertEqual(value["fetch_calls"], 0)
        target.validate_task_projection(value)

    def test_level_summarizes_wait_throughput_and_exact_ordinals(self) -> None:
        level = target.summarize_level(
            level=4,
            tasks=[task(index, wall=10.0 + index) for index in range(1, 5)],
            batch_wall_seconds=30.0,
        )
        self.assertTrue(level["passed"])
        self.assertEqual(level["throughput_tasks_per_minute"], 8.0)
        self.assertEqual(level["slot_acquisitions"], 12)
        self.assertEqual(level["slot_acquisition_counts"], [8, 4])
        self.assertEqual(level["task_wall_p95_seconds"], 14.0)

    def test_result_requires_all_four_levels_for_authorization(self) -> None:
        activation = {"protected_watchers": target.protected_watcher_snapshot()}
        levels = [
            target.summarize_level(
                level=level,
                tasks=[task(index) for index in range(1, level + 1)],
                batch_wall_seconds=20.0 + level,
            )
            for level in target.LEVELS
        ]
        value = target.build_result(levels=levels, activation=activation, now=0)
        self.assertTrue(value["all_requested_levels_passed"])
        self.assertEqual(value["recommended_executor_count"], 8)
        self.assertTrue(
            value["authorization"]["fresh_shared_prefix_paired_benchmark_protocol_design"]
        )
        partial = target.build_result(levels=levels[:3], activation=activation, now=0)
        self.assertFalse(partial["all_requested_levels_passed"])
        self.assertFalse(
            partial["authorization"]["fresh_shared_prefix_paired_benchmark_protocol_design"]
        )

    def test_resealed_result_cannot_enable_benchmark_or_evaluator(self) -> None:
        activation = {"protected_watchers": target.protected_watcher_snapshot()}
        levels = [
            target.summarize_level(
                level=level,
                tasks=[task(index) for index in range(1, level + 1)],
                batch_wall_seconds=20.0 + level,
            )
            for level in target.LEVELS
        ]
        value = target.build_result(levels=levels, activation=activation, now=0)
        altered = copy.deepcopy(value)
        altered["authorization"]["exact220"] = True
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_result(altered)

    def test_protocol_is_sealed_and_launch_false(self) -> None:
        value = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=value)
        self.assertFalse(value["authorization"]["capacity_staircase_launch"])
        self.assertFalse(value["authorization"]["paired_benchmark_launch"])
        self.assertFalse(value["authorization"]["exact220"])


if __name__ == "__main__":
    unittest.main()
