from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.audit_v24216_package_gate_wait import build_audit


ROOT = Path(__file__).resolve().parents[1]


class AuditV24216PackageGateWaitTests(unittest.TestCase):
    def test_wait_audit_reports_zero_execution_side_effects(self) -> None:
        protocol = {
            "sha256": "p" * 64,
            "value": {
                "decision_contract_sha256": "d" * 64,
                "control_surface": {"manifest_sha256": "m" * 64},
            },
        }
        activation = {
            "sha256": "a" * 64,
            "value": {"watcher": {"pid": 1, "start_ticks": 2}},
        }
        state = {
            "role": "v24216_package_gate_watcher_state",
            "protocol": {"sha256": "p" * 64},
            "execution_activation": {"sha256": "a" * 64},
            "status": "waiting_for_v24215_joint_package_terminal",
            "reason": "parent_preterminal",
            "parent_safe_state_envelope_opened": True,
            "parent_state": {
                "path": "outputs/v24215_selected_joint_package_recovery_state_v1_20260731.json",
                "terminal": False,
            },
            "runtime_forward_inputs_exactly_opaque_id_and_question": True,
        }
        false_fields = (
            "parent_publication_opened",
            "r1_release_envelope_opened",
            "capacity_priority_rechecked",
            "paired_roots_materialized",
            "historical_baseline_result_reused",
            "baseline_forward_called",
            "candidate_forward_called",
            "both_forward_arms_exact_terminal_before_mapping",
            "mapping_or_evaluator_opened",
            "baseline_evaluator_called",
            "candidate_evaluator_called",
            "package_gate_evaluated",
            "package_gate_passed",
            "capacity_measurement_allowed",
            "all220_freeze_design_allowed",
            "shared_api_lease_acquired",
            "lease_compatibility_valid",
            "network_model_search_fetch_evaluator_or_api_called",
            "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing",
            "credential_value_read_persisted_hashed_or_emitted",
            "process_signal_restart_resume_rerun_skip_or_selective_retry",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
            "terminal",
        )
        state.update({field: False for field in false_fields})
        from deepwide_agent.v24216_package_gate import payload_sha256

        state["state_payload_sha256"] = payload_sha256(state)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "state.json"
            path.write_text(__import__("json").dumps(state), encoding="utf-8")
            with mock.patch(
                "scripts.audit_v24216_package_gate_wait.validate_protocol",
                return_value=protocol,
            ), mock.patch(
                "scripts.audit_v24216_package_gate_wait.validate_activation",
                return_value=activation,
            ), mock.patch(
                "scripts.audit_v24216_package_gate_wait.STATE", path
            ), mock.patch(
                "scripts.audit_v24216_package_gate_wait._present", return_value=False
            ):
                value = build_audit(ROOT, created_at_unix=1)
        self.assertFalse(value["boundary"]["shared_api_lease_acquired"])
        self.assertFalse(value["boundary"]["network_model_search_fetch_evaluator_or_api_called"])
        self.assertFalse(value["boundary"]["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
