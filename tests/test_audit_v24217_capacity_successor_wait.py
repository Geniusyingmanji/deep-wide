from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24217_capacity_successor import payload_sha256
from scripts import audit_v24217_capacity_successor_wait as audit


ROOT = Path(__file__).resolve().parents[1]


class AuditV24217CapacitySuccessorWaitTests(unittest.TestCase):
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
            "role": "v24217_capacity_successor_watcher_state",
            "protocol": {"sha256": "p" * 64},
            "execution_activation": {"sha256": "a" * 64},
            "status": "waiting_for_v24216_package_gate_terminal",
            "reason": "parent_preterminal",
            "parent_safe_state_envelope_opened": True,
            "parent_state": {"terminal": False},
        }
        false_fields = (
            "parent_terminal_go_validated",
            "legacy_capacity_boundary_validated",
            "shared_api_lease_acquired",
            "lease_compatibility_valid",
            "execution_start_published",
            "neutral_capacity_model_api_called",
            "capacity_report_created",
            "capacity_freeze_created",
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read",
            "search_fetch_or_evaluator_api_called",
            "credential_value_read_persisted_hashed_or_emitted",
            "response_text_or_response_id_persisted",
            "legacy_watcher_signaled_restarted_modified_or_terminated",
            "process_signal_restart_resume_rerun_skip_or_selective_retry",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
            "terminal",
        )
        state.update({field: False for field in false_fields})
        state["state_payload_sha256"] = payload_sha256(state)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps(state), encoding="utf-8")
            with mock.patch.object(audit, "validate_protocol", return_value=protocol), mock.patch.object(
                audit, "validate_activation", return_value=activation
            ), mock.patch.object(audit, "STATE", path), mock.patch.object(
                audit, "_present", return_value=False
            ):
                value = audit.build_audit(ROOT, created_at_unix=1)
        self.assertFalse(value["boundary"]["shared_api_lease_acquired"])
        self.assertFalse(value["boundary"]["neutral_capacity_model_api_called"])
        self.assertFalse(value["boundary"]["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
