from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24357_explicit_partition_external_gate as target  # noqa: E402


def task_projection(
    ordinal: int,
    *,
    before: int = 0,
    after: int = 0,
    catalog: bool = True,
    observed: bool = True,
    hidden_page: bool = True,
    passed: bool = True,
) -> dict:
    value = {
        "ordinal": ordinal,
        "wall_seconds": 30.0,
        "parent_taxonomy": "success",
        "all_parent_artifacts_valid": True,
        "completion_kind": "paired" if before else "identity_no_reserve",
        "effect_accounting_complete": True,
        "structural_shared_normalization": True,
        "partition_precedes_fetch_candidate": True,
        "source_partition_disjoint": True,
        "hidden_verifier_prompt_excluded": True,
        "hidden_verifier_no_new_candidate": True,
        "parent_support_ids_reused": True,
        "observed_pages_respect_frozen_partition": observed,
        "parent_semantic_catalog_present": catalog,
        "selected_source_count": 10,
        "proposal_source_count": 9,
        "verifier_source_count": 1,
        "verifier_source_cap": 1,
        "parent_proposal_page_count": 9,
        "hidden_verifier_page_count": 1 if hidden_page else 0,
        "parent_fetch_calls": 9,
        "hidden_verifier_fetch_calls": 1,
        "total_fetch_calls": 10,
        "parent_eligible_support_set_count": 1 if before else 0,
        "candidate_changed_cells_before_hidden_verifier": before,
        "candidate_changed_cells_after_hidden_verifier": after,
        "hidden_verifier_admitted_cells": after,
        "hidden_verifier_reverted_cells": before - after,
        "proposal_conditional_entropy_reduction_nats": 0.25 if before else 0.0,
        "utility_aligned_entropy_credit_nats": 0.25 if after else 0.0,
        "utility_set_count": after,
        "final_candidate_nonidentity": after > 0,
        "model_requests": 3 if before else 2,
        "model_attempts": 3 if before else 2,
        "model_total_tokens": 100,
        "slot_acquisitions": 3 if before else 2,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "slot_total_wait_seconds": 5.0,
        "slot_max_wait_seconds": 2.0,
        "slot_acquisition_counts": [2, 1] if before else [1, 1],
        "search_calls": 1,
        "fetch_failures": 0 if hidden_page else 1,
        "search_total_tokens": 200,
        "hosted_search_attempts": 1,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": 10,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": 0,
        "deadline_exhausted": False,
        "private_replay_valid": True,
    }
    if not observed:
        value["candidate_changed_cells_after_hidden_verifier"] = 0
        value["hidden_verifier_admitted_cells"] = 0
        value["hidden_verifier_reverted_cells"] = before
        value["utility_aligned_entropy_credit_nats"] = 0.0
        value["utility_set_count"] = 0
        value["final_candidate_nonidentity"] = False
    value["checks"] = target._task_checks(value)
    if not passed:
        value["deadline_exhausted"] = True
        value["checks"] = target._task_checks(value)
    value["passed"] = all(value["checks"].values())
    target.validate_task_projection(value)
    return value


class V24357ExplicitPartitionExternalGateTests(unittest.TestCase):
    def test_protocol_is_content_free_and_freezes_nine_plus_one(self) -> None:
        tasks = [target.neutral_task(index) for index in range(1, 13)]
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=protocol)
        encoded = json.dumps(protocol, ensure_ascii=False)
        self.assertEqual(protocol["partition"]["proposal_source_cap"], 9)
        self.assertEqual(protocol["partition"]["verifier_source_cap"], 1)
        self.assertEqual(len(set(protocol["partition"]["seed_sha256_vector"])), 12)
        for task in tasks:
            self.assertNotIn(task["question"], encoded)
            self.assertNotIn(task["opaque_id"], encoded)

    def test_one_independent_retention_satisfies_mechanism_gate(self) -> None:
        values = [task_projection(index) for index in range(1, 13)]
        values[0] = task_projection(1, before=1, after=1)
        aggregate = target.aggregate_tasks(values, 60.0)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["parent_candidate_tasks"], 1)
        self.assertEqual(aggregate["utility_aligned_tasks"], 1)
        self.assertEqual(aggregate["final_nonidentity_tasks"], 1)

    def test_parent_candidate_without_independent_retention_is_no_go(self) -> None:
        values = [task_projection(index) for index in range(1, 13)]
        values[0] = task_projection(1, before=1, after=0)
        aggregate = target.aggregate_tasks(values, 60.0)
        self.assertFalse(aggregate["passed"])
        self.assertTrue(aggregate["checks"]["parent_candidate_tasks"])
        self.assertFalse(aggregate["checks"]["utility_aligned_tasks"])
        self.assertFalse(aggregate["checks"]["final_nonidentity_tasks"])

    def test_missing_hidden_page_is_valid_fail_closed_task(self) -> None:
        value = task_projection(1, hidden_page=False)
        self.assertTrue(value["passed"])
        self.assertEqual(value["hidden_verifier_page_count"], 0)
        values = [value, *(task_projection(index) for index in range(2, 13))]
        self.assertTrue(target.aggregate_tasks(values, 60.0)["checks"]["hidden_page_tasks"])

    def test_transport_partition_and_credit_tamper_are_rejected(self) -> None:
        cases = (
            lambda value: value.__setitem__("hard_fetch_helper_calls", 11),
            lambda value: value.__setitem__("verifier_source_cap", 2),
            lambda value: value.__setitem__("utility_aligned_entropy_credit_nats", 1.0),
        )
        for mutate in cases:
            value = task_projection(1, before=1, after=1)
            mutate(value)
            with self.assertRaises(RuntimeError):
                target.validate_task_projection(value)

    def test_public_result_rejects_task_content_when_resealed(self) -> None:
        values = [task_projection(index) for index in range(1, 13)]
        values[0] = task_projection(1, before=1, after=1)
        aggregate = target.aggregate_tasks(values, 60.0)
        result = {
            "artifact_version": 1,
            "role": "v24357_explicit_partition_external_result",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 0,
            "selected": 12,
            "executor_count": 8,
            "model_slot_cap": 2,
            "aggregate": aggregate,
            "passed": True,
            "temporary_execution_directory_remaining": False,
            "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "provenance": {},
        }
        result["result_payload_sha256"] = payload_sha256(result)
        target.validate_public_result(result)
        altered = copy.deepcopy(result)
        altered["aggregate"]["leaked"] = "https://example.invalid/private"
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(altered)

    def test_preaudit_rejects_unavailable_proxy(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        with patch.object(target, "validate_protocol", return_value=protocol), patch.object(
            target, "_run_tests", return_value={name: True for name in target.TEST_FILES}
        ), patch.object(target, "_future", return_value=True), patch.object(
            target, "_port_listening", return_value=False
        ), patch.object(target, "lease_observation", return_value={"active": False}), patch.object(
            target, "protected_watcher_snapshot", return_value=[]
        ), patch.object(
            target, "_parent", return_value={"closure": {"protected_watchers": []}}
        ), patch.object(target, "sha256", return_value="a" * 64), patch.object(
            target, "_git", side_effect=lambda root, *args: ""
        ):
            with self.assertRaises(RuntimeError):
                target.build_preaudit(ROOT, now=0)


if __name__ == "__main__":
    unittest.main()
