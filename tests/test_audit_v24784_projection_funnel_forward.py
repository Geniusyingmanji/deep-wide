from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24784_projection_funnel_forward as audit  # noqa: E402


def observation(*, joint: bool = False) -> dict:
    value = {
        "status": "validated",
        "base_result_valid": True,
        "funnel_receipt_valid": True,
        "prediction_changed": joint,
        "changed_cell_count": int(joint),
        "founded_changed_cell_count": int(joint),
        "country_changed_cell_count": 0,
        "nonunknown_changed_cell_count": 0,
        "projection_backed_support_set_count": int(joint),
        "initial_fetch_request_count": 8,
        "reserve_fetch_request_count": 2,
        "actual_fetch_request_count": 10,
        "initial_usable_page_count": 6,
        "reserve_usable_page_count": 2,
        "actual_usable_page_count": 8,
        "final_entity_slots_with_two_usable_identity_sources": 2,
        "entity_slots_brought_to_two_sources_by_reserve": 1,
        "reserve_target_entity_count": 2,
        "failed_url_retry_count": 0,
        "scheduler_contract": True,
        "candidate_changes_only_unknown": True,
        "semantic_safety_contract": True,
        "funnel_counts": {name: 0 for name in audit.contract.FUNNEL_SUM_FIELDS},
        "task_local_joint_projection_backed_safe_change": joint,
    }
    counts = value["funnel_counts"]
    counts.update(
        target_count=8,
        baseline_unknown_target_count=8,
        core_page_count=6,
        reserve_page_count=2,
        input_page_count=8,
        intact_page_count=8,
        page_target_pair_count=64,
        supported_column_pair_count=64,
        exact_entity_anchor_pair_count=1,
        target_segment_pair_count=1,
        explicit_relation_token_pair_count=1,
        parsable_relation_pair_count=1,
        bound_relation_pair_count=1,
        projection_emitted_pair_count=1,
        semantic_projection_count=1,
        distinct_target_value_projection_count=int(joint),
        projection_target_binding_count=int(joint),
        projection_unknown_target_value_group_count=int(joint),
        projection_two_or_more_source_group_count=int(joint),
        catalog_candidate_target_value_group_count=int(joint),
        catalog_eligible_support_set_count=int(joint),
        projection_backed_eligible_support_set_count=int(joint),
        unconflicted_projection_backed_unknown_proposal_count=int(joint),
    )
    return value


def receipt(ordinal: int, *, joint: bool = False) -> dict:
    obs = observation(joint=joint)
    reasons = {name: 0 for name in audit.contract.funnel.REASONS}
    reasons["explicit_relation_absent"] = 63
    reasons["projection_emitted"] = 1
    return {
        "ordinal": ordinal,
        "parent_receipt_sha256": f"{ordinal:064x}",
        "parent_receipt_valid": True,
        "failure_taxonomy": "success",
        "model_receipt_sha256": f"{ordinal + 8:064x}",
        "model_receipt_present": True,
        "model_receipt_valid": True,
        "model_acquisitions": 2,
        "model_slot_timeouts": 0,
        "transport_receipt_sha256": f"{ordinal + 16:064x}",
        "transport_receipt_present": True,
        "transport_receipt_valid": True,
        "hosted_search_attempts": 1,
        "hard_fetch_helper_calls": 10,
        "fetch_deadline_rejections": 0,
        "parent_effect_receipt_flags_match": True,
        "result_projection_sha256": f"{ordinal + 24:064x}",
        "result_projection_valid": True,
        "observation": obs,
        "funnel_reason_counts": reasons,
        "strict_task_local_joint": audit._strict_joint(obs),
    }


def protocol() -> dict:
    return {
        "forward_health_gate": {"protected_watchers": []},
        "mechanism_gate_before_private_truth": {
            "validated_funnel_receipt_count_required": 8,
            "private_catalog_absent_count_required": 0,
            "base_runtime_failure_count_required": 0,
            "funnel_validation_failure_count_required": 0,
            "minimum_projection_emitted_task_count": 1,
            "minimum_projection_backed_support_task_count": 1,
            "minimum_unconflicted_projection_backed_unknown_proposal_task_count": 1,
            "minimum_changed_task_count": 1,
            "minimum_changed_cell_count": 1,
            "nonunknown_changed_cell_count_required": 0,
            "minimum_task_local_joint_projection_backed_safe_change_task_count": 1,
            "cross_task_aggregate_cooccurrence_may_substitute_for_task_local_joint": False,
        },
    }


def parents(rows: list[dict]):
    replayed, reasons, _effects = audit._replay_summary(rows)
    summary = {
        **replayed,
        "funnel_reason_counts": reasons,
        "parent_failure_taxonomy_counts": {"success": 8},
        "all_task_ordinals_submitted_once": True,
        "within_experiment_wall_ceiling": True,
        "resume_retry_skip_or_selective_rerun": False,
        "actual_fetch_request_count": replayed["actual_fetch_request_count"],
    }
    freeze = {
        "predictions_sha256": "a" * 64,
        "run_summary_sha256": "a" * 64,
        "all_predictions_terminal_before_private_truth_or_quality_open": True,
        "private_truth_or_quality_path_opened_or_hashed": False,
    }
    forward = {
        "prediction_freeze_sha256": "a" * 64,
        "run_summary_sha256": "a" * 64,
        "execution_start_sha256": "a" * 64,
        "resume_retry_skip_or_selective_rerun": False,
    }
    return summary, freeze, forward


class V24784ProjectionFunnelForwardAuditTests(unittest.TestCase):
    def test_same_task_joint_go_and_cross_task_aggregate_cannot_substitute(self) -> None:
        rows = [receipt(index, joint=index == 1) for index in range(1, 9)]
        summary, freeze, forward = parents(rows)
        with (
            patch.object(audit.contract, "sha256", return_value="a" * 64),
            patch.object(audit.contract, "protected_watcher_snapshot", return_value=[]),
        ):
            checks, _replayed, _reasons, effects = audit._gate_checks(
                rows, summary, freeze, forward, protocol()
            )
        self.assertTrue(checks["minimum_strict_task_local_joint_projection_backed_safe_change"])
        self.assertEqual(effects["strict_task_local_joint_count"], 1)
        split = copy.deepcopy(rows)
        split[0]["observation"]["changed_cell_count"] = 0
        split[0]["observation"]["founded_changed_cell_count"] = 0
        split[0]["observation"]["prediction_changed"] = False
        split[0]["observation"]["task_local_joint_projection_backed_safe_change"] = False
        split[0]["strict_task_local_joint"] = False
        split[1]["observation"]["funnel_counts"]["projection_backed_eligible_support_set_count"] = 0
        split[1]["observation"]["funnel_counts"]["unconflicted_projection_backed_unknown_proposal_count"] = 0
        split[1]["strict_task_local_joint"] = False
        self.assertEqual(audit._replay_summary(split)[2]["strict_task_local_joint_count"], 0)

    def test_projection_emission_is_an_independent_joint_requirement(self) -> None:
        value = observation(joint=True)
        value["funnel_counts"]["projection_emitted_pair_count"] = 0
        self.assertFalse(audit._strict_joint(value))

    def test_nonunknown_change_or_safety_failure_rejects_joint(self) -> None:
        for field, replacement in (
            ("nonunknown_changed_cell_count", 1),
            ("candidate_changes_only_unknown", False),
            ("semantic_safety_contract", False),
        ):
            value = observation(joint=True)
            value[field] = replacement
            self.assertFalse(audit._strict_joint(value))

    def test_replay_preserves_fixed_status_and_funnel_denominators(self) -> None:
        rows = [receipt(index, joint=index == 1) for index in range(1, 9)]
        replayed, reasons, effects = audit._replay_summary(rows)
        self.assertEqual(replayed["selected_tasks"], 8)
        self.assertEqual(replayed["status_validated_count"], 8)
        self.assertEqual(replayed["page_target_pair_count"], 512)
        self.assertEqual(sum(reasons.values()), 512)
        self.assertEqual(effects["all_task_fetch_request_count"], 80)

    def test_effect_overcaps_fail_health_checks(self) -> None:
        rows = [receipt(index, joint=index == 1) for index in range(1, 9)]
        rows[0]["hard_fetch_helper_calls"] = 11
        summary, freeze, forward = parents(rows)
        with (
            patch.object(audit.contract, "sha256", return_value="a" * 64),
            patch.object(audit.contract, "protected_watcher_snapshot", return_value=[]),
        ):
            checks, *_ = audit._gate_checks(rows, summary, freeze, forward, protocol())
        self.assertFalse(checks["physical_fetch_helpers_within_frozen_caps"])
        self.assertFalse(checks["all_task_fetch_requests_within_frozen_caps"])

    def test_synthetic_audit_roundtrip_and_resealed_task_tamper_rejected(self) -> None:
        rows = [receipt(index, joint=index == 1) for index in range(1, 9)]
        replayed, reasons, effects = audit._replay_summary(rows)
        checks = {name: True for name in audit.GATE_CHECK_NAMES}
        value = {
            "artifact_version": 1,
            "role": "v24784_projection_funnel_forward_audit",
            "protocol_id": audit.contract.PROTOCOL_ID,
            "created_at_unix": 0,
            "protocol_sha256": "a" * 64,
            "forward_result_sha256": "a" * 64,
            "prediction_freeze_sha256": "a" * 64,
            "run_summary_sha256": "a" * 64,
            "execution_start_sha256": "a" * 64,
            "task_receipts": rows,
            "replayed_summary_counts": replayed,
            "replayed_funnel_reason_counts": reasons,
            "content_free_effect_metrics": effects,
            "gate_checks": checks,
            "forward_health_go": True,
            "mechanism_go": True,
            "findings": [],
            "protected_watchers": [],
            "source_policy": dict(audit.SOURCE_POLICY),
            "authorization": {
                "task_cluster_disjoint_paired_dev64_design": True,
                "private_truth_or_quality_surface_open": False,
                "additional_forward_retry_resume_or_rerun": False,
                "paired_dev64_execution": False,
                "exact220": False,
                "entropy_or_credit_experiment": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = audit.contract.payload_sha256(value)
        with patch.object(audit, "_bound_state_matches", return_value=True):
            self.assertEqual(audit.validate_audit(value), value)
            altered = copy.deepcopy(value)
            altered["task_receipts"][0]["strict_task_local_joint"] = False
            altered.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = audit.contract.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                audit.validate_audit(altered)

    def test_source_policy_never_opens_prediction_rows_or_private_surfaces(self) -> None:
        source = Path(audit.__file__).read_text(encoding="utf-8")
        self.assertNotIn("PREDICTIONS.read_text", source)
        self.assertFalse(audit.SOURCE_POLICY["prediction_jsonl_opened_or_parsed"])
        self.assertFalse(
            audit.SOURCE_POLICY[
                "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read"
            ]
        )

    def test_create_only_publish_rejects_overwrite(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            audit.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                audit.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
