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
from scripts import v24361_two_batch_partition_external_gate as target  # noqa: E402


def task_projection(
    ordinal: int,
    *,
    before: int = 0,
    after: int = 0,
    union_hosts: int = 10,
    selected_hosts: int | None = None,
    recursive: int = 0,
    provider_calls: int = 2,
    hidden_page: bool = True,
) -> dict:
    selected = min(union_hosts, 10) if selected_hosts is None else selected_hosts
    verifier = 1 if selected >= 3 else 0
    proposal = selected - verifier
    hidden_fetch = verifier
    total_fetch = selected
    value = {
        "ordinal": ordinal,
        "wall_seconds": 30.0,
        "parent_taxonomy": "success",
        "all_parent_artifacts_valid": True,
        "completion_kind": "paired" if before else "identity_no_reserve",
        "effect_accounting_complete": True,
        "structural_shared_normalization": True,
        "logical_query_count": 4,
        "discovery_batch_count": 2,
        "batch_logical_query_counts": [2, 2],
        "provider_search_call_count": provider_calls,
        "single_shot_multi_query_chunks": 2,
        "recursive_split_requests": recursive,
        "pre_host_dedup_url_lead_count": union_hosts + 2,
        "registrable_host_union_count": union_hosts,
        "registrable_host_duplicate_url_count": 2,
        "selected_source_count": selected,
        "proposal_source_count": proposal,
        "verifier_source_count": verifier,
        "verifier_source_cap": 1,
        "host_union_precedes_partition_fetch_candidate": True,
        "source_partition_disjoint": True,
        "hidden_verifier_prompt_excluded": True,
        "hidden_verifier_no_new_candidate": True,
        "parent_support_ids_reused": True,
        "observed_pages_respect_frozen_partition": True,
        "parent_semantic_catalog_present": True,
        "parent_proposal_page_count": proposal,
        "hidden_verifier_page_count": hidden_fetch if hidden_page else 0,
        "parent_fetch_calls": proposal,
        "hidden_verifier_fetch_calls": hidden_fetch,
        "total_fetch_calls": total_fetch,
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
        "search_calls": provider_calls,
        "fetch_failures": 0 if hidden_page else 1,
        "search_total_tokens": 200,
        "hosted_search_attempts": provider_calls,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": total_fetch,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": 0,
        "deadline_exhausted": False,
        "private_replay_valid": True,
    }
    value["checks"] = target._task_checks(value)
    value["passed"] = all(value["checks"].values())
    target.validate_task_projection(value)
    return value


def public_result(aggregate: dict) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24361_two_batch_partition_external_result",
        "protocol_id": target.PROTOCOL_ID,
        "created_at_unix": 0,
        "selected": 12,
        "executor_count": 8,
        "model_slot_cap": 2,
        "aggregate": aggregate,
        "passed": aggregate["passed"],
        "temporary_execution_directory_remaining": False,
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_revaluation": False,
        "provenance": {
            "protocol_sha256": "a" * 64,
            "preactivation_audit_sha256": "b" * 64,
            "activation_sha256": "c" * 64,
            "execution_start_sha256": "d" * 64,
            "surface_manifest_sha256": "e" * 64,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


class V24361TwoBatchPartitionExternalGateTests(unittest.TestCase):
    def test_protocol_is_content_free_and_freezes_two_batch_ten_fetch(self) -> None:
        tasks = [target.neutral_task(index) for index in range(1, 13)]
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=protocol)
        encoded = json.dumps(protocol, ensure_ascii=False)
        discovery = protocol["discovery_partition"]
        self.assertEqual(discovery["deterministic_batch_query_counts"], [2, 2])
        self.assertFalse(discovery["recursive_query_local_split_allowed"])
        self.assertEqual(discovery["selected_fetch_source_cap"], 10)
        for task in tasks:
            self.assertNotIn(task["question"], encoded)
            self.assertNotIn(task["opaque_id"], encoded)

    def test_one_independent_retention_with_host_coverage_is_mechanism_go(self) -> None:
        values = [task_projection(index) for index in range(1, 13)]
        values[0] = task_projection(1, before=1, after=1)
        aggregate = target.aggregate_tasks(values, 60.0)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["exact_two_batch_tasks"], 12)
        self.assertEqual(aggregate["zero_recursive_split_tasks"], 12)
        self.assertEqual(aggregate["union_ge_ten_host_tasks"], 12)
        self.assertEqual(aggregate["selected_source_count"], 120)
        self.assertEqual(aggregate["utility_aligned_tasks"], 1)

    def test_transport_retry_does_not_invent_a_third_logical_batch(self) -> None:
        values = [task_projection(index) for index in range(1, 13)]
        values[0] = task_projection(
            1, before=1, after=1, provider_calls=3
        )
        aggregate = target.aggregate_tasks(values, 60.0)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["exact_two_batch_tasks"], 12)
        self.assertEqual(aggregate["search_calls"], 25)
        self.assertEqual(aggregate["hosted_search_attempts"], 25)

        over_budget = task_projection(1, provider_calls=5)
        self.assertFalse(over_budget["checks"]["transport_retry_within_frozen_budget"])

    def test_coverage_candidate_and_recursive_failures_are_independent_no_go(self) -> None:
        cases = []
        low_coverage = [
            task_projection(index, union_hosts=6) for index in range(1, 13)
        ]
        cases.append((low_coverage, "union_ge_ten_host_tasks"))
        no_candidate = [task_projection(index) for index in range(1, 13)]
        cases.append((no_candidate, "parent_candidate_tasks"))
        recursive = [task_projection(index) for index in range(1, 13)]
        recursive[0] = task_projection(1, recursive=1)
        cases.append((recursive, "all_tasks_structurally_passed"))
        for values, failed in cases:
            with self.subTest(failed=failed):
                aggregate = target.aggregate_tasks(values, 60.0)
                self.assertFalse(aggregate["passed"])
                self.assertFalse(aggregate["checks"][failed])

    def test_task_and_aggregate_extra_field_tamper_fail_closed(self) -> None:
        task = task_projection(1)
        task["private_text"] = "secret"
        with self.assertRaises(RuntimeError):
            target.validate_task_projection(task)
        values = [task_projection(index) for index in range(1, 13)]
        aggregate = target.aggregate_tasks(values, 60.0)
        aggregate["private_text"] = "secret"
        with self.assertRaises(RuntimeError):
            target.validate_aggregate(aggregate)

    def test_public_result_rejects_resealed_content_and_recomputed_gate_tamper(self) -> None:
        values = [task_projection(index) for index in range(1, 13)]
        values[0] = task_projection(1, before=1, after=1)
        result = public_result(target.aggregate_tasks(values, 60.0))
        target.validate_public_result(result)

        leaked = copy.deepcopy(result)
        leaked["private_text"] = "non-url private content"
        leaked.pop("result_payload_sha256")
        leaked["result_payload_sha256"] = payload_sha256(leaked)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(leaked)

        tampered = copy.deepcopy(result)
        tampered["aggregate"]["selected_source_count"] = 1
        tampered["aggregate"]["checks"]["selected_host_count_total"] = True
        tampered["aggregate"]["passed"] = True
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(tampered)

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
