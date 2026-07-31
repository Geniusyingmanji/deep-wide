from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.audit_v24214_joint_package_wait import build_audit


ROOT = Path(__file__).resolve().parents[1]


def wait_state() -> dict:
    value = {
        "role": "v24214_selected_joint_package_watcher_state",
        "protocol": {"sha256": "p" * 64},
        "execution_activation": {"sha256": "a" * 64},
        "status": "waiting_for_v24213_entropy_recovery_terminal",
        "reason": "parent_preterminal",
        "parent_safe_state_envelope_opened": True,
        "parent_state": {"terminal": False},
    }
    false_fields = (
        "selected_work_order_opened",
        "markdown_publication_opened",
        "scope_publication_opened",
        "search_publication_opened",
        "entropy_publication_opened",
        "joint_package_publication_created",
        "identity_handoff_only",
        "joint_package_materialized",
        "single_deepest_cumulative_graph_used",
        "component_directory_overlay_used",
        "complete_parent_and_component_regression_rerun",
        "strict_component_activation_validated",
        "silent_component_drop_or_baseline_fallback_used",
        "package_gate_evaluated_or_launched",
        "dev64_launch_allowed",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    value.update({field: False for field in false_fields})
    value["state_payload_sha256"] = payload_sha256(value)
    return value


class AuditV24214JointPackageWaitTests(unittest.TestCase):
    def test_wait_audit_preserves_processes_and_all_false_authorities(self) -> None:
        protocol = {
            "sha256": "p" * 64,
            "value": {
                "decision_contract_sha256": "d" * 64,
                "control_surface": {"manifest_sha256": "m" * 64},
                "safe_wait_boundary": {"protected_processes": {"r1": {"pid": 1}}},
            },
        }
        activation = {
            "sha256": "a" * 64,
            "value": {"watcher": {"pid": 2, "start_ticks": 3}},
        }
        with mock.patch(
            "scripts.audit_v24214_joint_package_wait.validate_protocol",
            return_value=protocol,
        ), mock.patch(
            "scripts.audit_v24214_joint_package_wait.validate_activation",
            return_value=activation,
        ), mock.patch(
            "scripts.audit_v24214_joint_package_wait.read_object",
            return_value=wait_state(),
        ), mock.patch(
            "scripts.audit_v24214_joint_package_wait.protected_processes",
            return_value={"r1": {"pid": 1}},
        ), mock.patch(
            "scripts.audit_v24214_joint_package_wait.sha256", return_value="s" * 64
        ):
            value = build_audit(ROOT, created_at_unix=1)
        boundary = value["boundary"]
        self.assertTrue(boundary["selected_work_order_and_component_publications_unopened"])
        self.assertTrue(boundary["all_protocol_protected_process_identities_preserved"])
        self.assertFalse(boundary["component_directory_overlay_used"])
        self.assertFalse(boundary["package_gate_evaluated_or_launched"])
        self.assertFalse(boundary["dev64_launch_allowed"])
        self.assertFalse(boundary["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
