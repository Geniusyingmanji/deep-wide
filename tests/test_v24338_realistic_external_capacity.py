from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24338_realistic_external_capacity as target  # noqa: E402


def task_projection(ordinal: int, *, passed: bool = True) -> dict:
    value = {
        "ordinal": ordinal, "wall_seconds": 30.0, "parent_taxonomy": "success", "all_parent_artifacts_valid": True, "result_status": "completed", "completion_kind": "identity_no_reserve", "effect_accounting_complete": True, "prefix_status": "frozen", "prefix_producer_execution_count": 1, "logical_model_admissions": 2, "provider_model_requests": 2, "provider_model_attempts": 2, "pre_provider_model_rejections": 0, "slot_acquisitions": 2, "slot_timeouts": 0, "provider_deadline_failures": 0, "slot_total_wait_seconds": 5.0, "slot_max_wait_seconds": 2.0, "slot_acquisition_counts": [1, 1], "core_logical_queries": 4, "search_provider_effects": 1, "core_fetch_targets": 7, "reserve_fetch_targets": 3, "core_usable_pages": 6, "reserve_usable_pages": 3, "repeated_upstream_effects": 0, "catalog_status": "built_empty", "catalog_target_count": 3, "catalog_page_count": 3, "catalog_independent_source_count": 3, "catalog_candidate_groups_considered": 0, "catalog_eligible_support_set_count": 0, "catalog_quarantined_candidate_groups": {}, "catalog_built_before_revision": True, "revision_model_admitted": False, "third_model_call_skipped_no_eligible_support": True, "candidate_identity_handoff": True, "admitted_cell_changes": 0, "credited_entropy_positive": False, "private_replay_valid": True, "model_requests": 2, "model_attempts": 2, "model_total_tokens": 100, "search_calls": 1, "fetch_calls": 10, "fetch_failures": 0, "search_total_tokens": 200, "hosted_search_deadline_failures": 0, "hard_fetch_helper_calls": 10, "hard_fetch_deadline_failures": 0, "fetch_deadline_rejections": 0, "fetch_helper_failures": 0, "deadline_exhausted": False, "task_text_identifier_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False, "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["checks"] = target._task_checks(value)
    if not passed: value["checks"]["deadline_not_exhausted"] = False
    value["passed"] = all(value["checks"].values()); return value


class V24338RealisticExternalCapacityTests(unittest.TestCase):
    def test_task_vectors_are_disjoint_and_content_free_protocol(self) -> None:
        self.assertTrue(set(target.level_ordinals(4)).isdisjoint(target.level_ordinals(8)))
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=protocol)
        encoded = json.dumps(protocol, ensure_ascii=False)
        self.assertNotIn("task_vector_sha256", protocol["task_contract"])
        for index in range(1, 13):
            self.assertNotIn(target.neutral_task(index)["question"], encoded)
            self.assertNotIn(target.neutral_task(index)["opaque_id"], encoded)

    def test_level_summary_computes_throughput_and_conservation(self) -> None:
        values = [task_projection(index) for index in target.level_ordinals(4)]
        level = target.summarize_level(4, values, 60.0)
        self.assertTrue(level["passed"])
        self.assertEqual(level["throughput_tasks_per_minute"], 4.0)
        self.assertEqual(level["model_requests"], 8)
        self.assertEqual(level["slot_acquisitions"], 8)
        self.assertEqual(level["third_model_call_skipped_tasks"], 4)

    def test_failed_task_makes_level_no_go(self) -> None:
        values = [task_projection(index) for index in target.level_ordinals(4)]
        values[-1] = task_projection(values[-1]["ordinal"], passed=False)
        level = target.summarize_level(4, values, 60.0)
        self.assertFalse(level["passed"])
        self.assertFalse(level["checks"]["all_tasks_passed"])

    def test_preaudit_fails_on_port_or_lease(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        with (patch.object(target, "validate_protocol", return_value=protocol), patch.object(target, "_run_test", return_value=True), patch.object(target, "sha256", return_value="a" * 64), patch.object(target, "_port_listening", return_value=False), patch.object(target, "lease_observation", return_value={"active": False})):
            with self.assertRaises(RuntimeError): target.build_preaudit(ROOT, now=0)
        with (patch.object(target, "validate_protocol", return_value=protocol), patch.object(target, "_run_test", return_value=True), patch.object(target, "sha256", return_value="a" * 64), patch.object(target, "_port_listening", return_value=True), patch.object(target, "lease_observation", return_value={"active": True})):
            with self.assertRaises(RuntimeError): target.build_preaudit(ROOT, now=0)


if __name__ == "__main__": unittest.main()
