from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24374_batch_stratified_external_gate as target  # noqa: E402


def task_projection(
    ordinal: int,
    *,
    parent_before: int = 0,
    legacy_after: int = 0,
    target_after: int = 0,
    recovered: int = 0,
    reverted_legacy: int = 0,
    status: str | None = None,
    union_hosts: int = 10,
    hidden_pages: int = 2,
    recursive: int = 0,
    provider_calls: int = 2,
) -> dict:
    selected = min(union_hosts, 10)
    verifier = min(2, max(0, selected - 2))
    proposal = selected - verifier
    eligible = 1 if parent_before else 0
    model_requests = 3 if eligible else 2
    selected_bound = 1 if parent_before and status is not None else 0
    verification_counts = {name: 0 for name in target.VERIFICATION_STATUSES}
    selected_counts = {name: 0 for name in target.VERIFICATION_STATUSES}
    if eligible:
        verification_counts[status or "no_independent_candidate_support"] = 1
    if selected_bound:
        selected_counts[str(status)] = 1
    proposal_entropy = 0.25 if eligible else 0.0
    selected_entropy = 0.25 if selected_bound else 0.0
    utility_entropy = 0.25 if target_after else 0.0
    value: dict = {
        "ordinal": ordinal,
        "wall_seconds": 30.0,
        "parent_taxonomy": "success",
        "completion_kind": "paired" if parent_before else "identity_no_reserve",
        "batch_logical_query_counts": [2, 2],
        "slot_acquisition_counts": [2, 1] if model_requests == 3 else [1, 1],
        "proposal_support_entropy_total_nats": proposal_entropy,
        "selected_proposal_entropy_nats": selected_entropy,
        "utility_aligned_entropy_credit_nats": utility_entropy,
        "slot_total_wait_seconds": 5.0,
        "slot_max_wait_seconds": 2.0,
        "all_parent_artifacts_valid": True,
        "effect_accounting_complete": True,
        "structural_shared_normalization": True,
        "host_union_precedes_partition_fetch_candidate": True,
        "source_partition_disjoint": True,
        "hidden_verifier_prompt_excluded": True,
        "hidden_verifier_no_new_candidate": True,
        "parent_support_ids_reused": True,
        "target_segment_entity_boundary_enforced": True,
        "legacy_character_window_projector_used_for_final_decision": False,
        "observed_pages_respect_frozen_partition": True,
        "parent_semantic_catalog_present": True,
        "deadline_exhausted": False,
        "private_replay_valid": True,
        "logical_query_count": 4,
        "discovery_batch_count": 2,
        "provider_search_call_count": provider_calls,
        "single_shot_multi_query_chunks": 2,
        "recursive_split_requests": recursive,
        "pre_host_dedup_url_lead_count": union_hosts + 2,
        "registrable_host_union_count": union_hosts,
        "registrable_host_duplicate_url_count": 2,
        "selected_batch_host_counts": [5, 5] if selected == 10 else [selected, 0],
        "proposal_batch_host_counts": [4, 4] if selected == 10 else [proposal, 0],
        "verifier_batch_host_counts": [1, 1] if selected == 10 else [verifier, 0],
        "full_capacity_batch_stratification_satisfied": selected == 10,
        "selected_source_count": selected,
        "proposal_source_count": proposal,
        "verifier_source_count": verifier,
        "verifier_source_cap": 2,
        "parent_proposal_page_count": proposal,
        "hidden_verifier_page_count": min(hidden_pages, verifier),
        "parent_fetch_calls": proposal,
        "hidden_verifier_fetch_calls": verifier,
        "total_fetch_calls": selected,
        "parent_eligible_support_set_count": eligible,
        "parent_candidate_changed_cells": parent_before,
        "legacy_candidate_changed_cells": legacy_after,
        "target_segment_candidate_changed_cells": target_after,
        "target_segment_recovered_cells": recovered,
        "target_segment_reverted_legacy_cells": reverted_legacy,
        "hidden_verifier_admitted_cells": target_after,
        "hidden_verifier_reverted_cells": parent_before - target_after,
        "selection_resolution_count": parent_before,
        "candidate_changes_without_declaration": 0,
        "selected_exactly_bound_candidate_changes": selected_bound,
        "verification_record_count": eligible,
        "verified_candidate_records": verification_counts["verified_candidate"],
        "no_independent_candidate_support_records": verification_counts[
            "no_independent_candidate_support"
        ],
        "verifier_supports_baseline_records": verification_counts[
            "verifier_supports_baseline"
        ],
        "independent_conflict_records": verification_counts[
            "independent_conflict"
        ],
        "nonpositive_proposal_entropy_records": verification_counts[
            "nonpositive_proposal_entropy"
        ],
        "selected_verified_candidate_changes": selected_counts[
            "verified_candidate"
        ],
        "selected_no_independent_candidate_support_changes": selected_counts[
            "no_independent_candidate_support"
        ],
        "selected_verifier_supports_baseline_changes": selected_counts[
            "verifier_supports_baseline"
        ],
        "selected_independent_conflict_changes": selected_counts[
            "independent_conflict"
        ],
        "selected_nonpositive_proposal_entropy_changes": selected_counts[
            "nonpositive_proposal_entropy"
        ],
        "verifier_semantic_projection_count": 1 if hidden_pages and eligible else 0,
        "model_requests": model_requests,
        "model_attempts": model_requests,
        "model_total_tokens": 100,
        "slot_acquisitions": model_requests,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "search_calls": provider_calls,
        "fetch_failures": verifier - min(hidden_pages, verifier),
        "search_total_tokens": 200,
        "hosted_search_attempts": provider_calls,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": selected,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": verifier - min(hidden_pages, verifier),
    }
    value["checks"] = target._task_checks(value)
    value["passed"] = all(value["checks"].values())
    target.validate_task_projection(value)
    return value


def passing_tasks() -> list[dict]:
    values = [task_projection(index) for index in range(1, target.SELECTED + 1)]
    values[0] = task_projection(
        1,
        parent_before=1,
        legacy_after=0,
        target_after=1,
        recovered=1,
        status="verified_candidate",
    )
    return values


def public_result(aggregate: dict) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24374_target_segment_external_result",
        "protocol_id": target.PROTOCOL_ID,
        "created_at_unix": 0,
        "selected": target.SELECTED,
        "executor_count": target.EXECUTOR_COUNT,
        "model_slot_cap": target.MODEL_SLOT_CAP,
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


def write_json(root: Path, relative: Path, value: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


class V24374BatchStratifiedExternalGateTests(unittest.TestCase):
    def test_protocol_freezes_fourth_disjoint_128_entity_vector(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        target.validate_protocol(ROOT, value=protocol)
        encoded = json.dumps(protocol, ensure_ascii=False)
        current = {
            entity
            for question in target.QUESTIONS
            for entity in target._question_entity_vector(question)
        }
        prior = {
            entity
            for question in (
                *target.prior_gate.prior_gate.control.task_source.QUESTIONS,
                *target.prior_gate.prior_gate.QUESTIONS,
                *target.prior_gate.QUESTIONS,
            )
            for entity in target._question_entity_vector(question)
        }
        self.assertEqual(len(current), 128)
        self.assertEqual(len(prior), 352)
        self.assertTrue(current.isdisjoint(prior))
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(protocol["discovery_partition"]["proposal_source_cap"], 8)
        self.assertEqual(protocol["discovery_partition"]["verifier_source_cap"], 2)
        self.assertEqual(
            protocol["mechanism"]["target_segment_projection_policy"],
            target.TARGET_SEGMENT_PROJECTION_POLICY_ID,
        )
        self.assertEqual(
            protocol["mechanism"]["batch_stratified_runner_policy"],
            target.BATCH_STRATIFIED_RUNNER_POLICY_ID,
        )
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)

        tampered = copy.deepcopy(protocol)
        tampered["authorization"]["hidden_launch"] = True
        tampered.pop("protocol_payload_sha256")
        tampered["protocol_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(ROOT, value=tampered)

        extra_top = copy.deepcopy(protocol)
        extra_top["hidden_surface"] = False
        extra_top.pop("protocol_payload_sha256")
        extra_top["protocol_payload_sha256"] = payload_sha256(extra_top)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(ROOT, value=extra_top)

    def test_one_net_recovered_verified_cell_is_mechanism_go(self) -> None:
        aggregate = target.aggregate_tasks(passing_tasks(), 120.0)
        self.assertTrue(aggregate["passed"])
        self.assertEqual(aggregate["target_segment_recovered_cells"], 1)
        self.assertEqual(aggregate["target_segment_net_cell_gain"], 1)
        self.assertEqual(aggregate["legacy_candidate_changed_cells"], 0)
        self.assertEqual(aggregate["target_segment_candidate_changed_cells"], 1)
        self.assertEqual(aggregate["selected_verified_candidate_changes"], 1)
        self.assertGreater(aggregate["utility_aligned_entropy_credit_nats"], 0)

    def test_negative_net_gain_is_valid_diagnostic_but_no_go(self) -> None:
        values = [task_projection(index) for index in range(1, 17)]
        values[0] = task_projection(
            1,
            parent_before=1,
            legacy_after=1,
            target_after=0,
            recovered=0,
            reverted_legacy=1,
            status="independent_conflict",
        )
        aggregate = target.aggregate_tasks(values, 120.0)
        self.assertEqual(aggregate["target_segment_net_cell_gain"], -1)
        self.assertFalse(aggregate["passed"])
        self.assertFalse(aggregate["checks"]["target_segment_net_cell_gain"])

    def test_status_and_entropy_conservation_fail_closed(self) -> None:
        task = passing_tasks()[0]
        altered = copy.deepcopy(task)
        altered["selected_independent_conflict_changes"] = 1
        altered["checks"] = target._task_checks(altered)
        altered["passed"] = all(altered["checks"].values())
        with self.assertRaises(RuntimeError):
            target.validate_task_projection(altered)

        aggregate = target.aggregate_tasks(passing_tasks(), 120.0)
        altered_aggregate = copy.deepcopy(aggregate)
        altered_aggregate["selected_proposal_entropy_nats"] = 0.0
        altered_aggregate["checks"] = target._aggregate_checks(altered_aggregate)
        altered_aggregate["passed"] = all(altered_aggregate["checks"].values())
        with self.assertRaises(RuntimeError):
            target.validate_aggregate(altered_aggregate)

    def test_public_result_rejects_content_and_resealed_count_tamper(self) -> None:
        result = public_result(target.aggregate_tasks(passing_tasks(), 120.0))
        target.validate_public_result(result)
        leaked = copy.deepcopy(result)
        leaked["private_text"] = "non-url private content"
        leaked.pop("result_payload_sha256")
        leaked["result_payload_sha256"] = payload_sha256(leaked)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(leaked)

        tampered = copy.deepcopy(result)
        tampered["aggregate"]["target_segment_recovered_cells"] = 2
        tampered["aggregate"]["checks"] = target._aggregate_checks(
            tampered["aggregate"]
        )
        tampered["aggregate"]["passed"] = all(
            tampered["aggregate"]["checks"].values()
        )
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            target.validate_public_result(tampered)

    def test_decision_and_postaudit_recompute_from_frozen_result(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary)
            for relative in (
                target.PROTOCOL,
                target.PREAUDIT,
                target.ACTIVATION,
                target.EXECUTION_START,
            ):
                write_json(root, relative, {})
            write_json(
                root,
                target.EXECUTION_START,
                {"protected_watchers": [{"pid": 1, "start_ticks": 2}]},
            )
            write_json(
                root,
                target.RESULT,
                public_result(target.aggregate_tasks(passing_tasks(), 120.0)),
            )
            decision = target.build_decision(root, now=0)
            write_json(root, target.DECISION, decision)
            target.validate_decision(root)
            self.assertEqual(decision["status"], "fresh_target_segment_external_go")

            changed = copy.deepcopy(decision)
            changed["observed"]["target_segment_net_cell_gain"] = 0
            changed.pop("decision_payload_sha256")
            changed["decision_payload_sha256"] = payload_sha256(changed)
            with self.assertRaises(RuntimeError):
                target.validate_decision(root, value=changed)

            watchers = [{"pid": 1, "start_ticks": 2}]
            with patch.object(
                target, "lease_observation", return_value={"active": False}
            ), patch.object(target, "protected_watcher_snapshot", return_value=watchers):
                audit = target.build_postaudit(root, now=0)
                write_json(root, target.POSTAUDIT, audit)
                target.validate_postaudit(root)
            self.assertTrue(audit["audit_valid"])

    def test_git_ready_requires_clean_pushed_tracked_start(self) -> None:
        def clean_git(root: Path, *args: str) -> str:
            del root
            if args in (("rev-parse", "HEAD"), ("rev-parse", "target/main")):
                return "abc"
            if args == ("status", "--porcelain"):
                return ""
            if args[:2] == ("ls-files", "--error-unmatch"):
                return str(target.EXECUTION_START)
            raise AssertionError(args)

        with patch.object(target, "_git", side_effect=clean_git):
            self.assertTrue(target._git_ready(ROOT))
        with patch.object(
            target,
            "_git",
            side_effect=subprocess.CalledProcessError(1, ["git"]),
        ):
            self.assertFalse(target._git_ready(ROOT))

    def test_preaudit_rejects_unavailable_proxy(self) -> None:
        protocol = target.build_protocol(ROOT, now=0, require_pristine=False)
        with patch.object(
            target, "validate_protocol", return_value=protocol
        ), patch.object(
            target,
            "_run_tests",
            return_value={name: True for name in target.TEST_FILES},
        ), patch.object(target, "_future", return_value=True), patch.object(
            target, "_port_listening", return_value=False
        ), patch.object(
            target, "lease_observation", return_value={"active": False}
        ), patch.object(
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
