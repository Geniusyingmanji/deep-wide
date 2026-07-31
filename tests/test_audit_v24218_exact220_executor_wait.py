from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24218_exact220_executor import payload_sha256
from scripts import audit_v24218_exact220_executor_wait as audit


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}
ACTIVATION = {
    "sha256": "a" * 64,
    "value": {"watcher": {"pid": 7, "start_ticks": 9}},
}


def wait_state() -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24218_exact220_executor_watcher_state",
        "created_at_unix": 1,
        "protocol": {"sha256": "p" * 64},
        "execution_activation": {"sha256": "a" * 64},
        "package_parent_safe_envelope_opened": True,
        "package_parent_go_validated": False,
        "capacity_parent_safe_envelope_opened": False,
        "capacity_parent_go_validated": False,
        "active_api_workers": None,
        "consecutive_quiet_observations": 0,
        "shared_api_lease_acquired": False,
        "lease_compatibility_valid": False,
        "execution_start_published": False,
        "candidate_package_opened": False,
        "capacity_report_or_freeze_opened": False,
        "materialization_created": False,
        "fresh_candidate_roots_created": False,
        "preflight_model_search_api_called": False,
        "benchmark_forward_called": False,
        "all_four_shards_exact_terminal": False,
        "mapping_or_evaluator_opened": False,
        "official_evaluator_called": False,
        "result_created": False,
        "runtime_forward_inputs_exactly_opaque_id_and_question": True,
        "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_used_for_forward_routing": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "existing_benchmark_or_watcher_signaled_restarted_modified_or_terminated": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
        "package_parent": {"terminal": False},
        "status": "waiting_for_v24216_package_gate_terminal",
        "reason": "package_parent_preterminal",
    }
    value["state_payload_sha256"] = payload_sha256(value)
    return value


class AuditV24218Exact220ExecutorWaitTests(unittest.TestCase):
    def test_wait_audit_proves_zero_side_effects(self) -> None:
        state = wait_state()
        with mock.patch.object(audit, "validate_protocol", return_value=VERIFIED), mock.patch.object(
            audit, "validate_activation", return_value=ACTIVATION
        ), mock.patch.object(audit, "read_object", return_value=state), mock.patch.object(
            audit, "_present", return_value=False
        ), mock.patch.object(audit, "sha256", return_value="s" * 64):
            with mock.patch.object(audit, "protected_processes", return_value={}):
                VERIFIED["value"]["safe_wait_boundary"] = {"protected_processes": {}}
                value = audit.build_audit(created_at_unix=2)
        self.assertFalse(value["boundary"]["benchmark_forward_called"])
        self.assertFalse(value["boundary"]["mapping_or_evaluator_opened"])
        self.assertTrue(value["authorization"]["future_incomplete_attempt_is_terminal_no_retry"])

    def test_wait_audit_rejects_early_forward(self) -> None:
        state = wait_state()
        state["benchmark_forward_called"] = True
        unsigned = dict(state)
        unsigned.pop("state_payload_sha256")
        state["state_payload_sha256"] = payload_sha256(unsigned)
        with mock.patch.object(audit, "validate_protocol", return_value=VERIFIED), mock.patch.object(
            audit, "validate_activation", return_value=ACTIVATION
        ), mock.patch.object(audit, "read_object", return_value=state), mock.patch.object(
            audit, "_present", return_value=False
        ):
            with mock.patch.object(audit, "protected_processes", return_value={}):
                VERIFIED["value"]["safe_wait_boundary"] = {"protected_processes": {}}
                with self.assertRaisesRegex(RuntimeError, "wait boundary"):
                    audit.build_audit(created_at_unix=2)


if __name__ == "__main__":
    unittest.main()
