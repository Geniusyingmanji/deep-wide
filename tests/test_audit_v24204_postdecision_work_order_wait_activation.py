from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.audit_v24204_postdecision_work_order_wait_activation import build_audit


class AuditV24204PostdecisionWorkOrderWaitActivationTests(unittest.TestCase):
    def test_wait_audit_preserves_processes_and_grants_no_build_or_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "outputs/v24204_postdecision_work_order_watcher_state_v1_20260731.json"
            state_path.parent.mkdir()
            state = {
                "role": "v24204_postdecision_work_order_watcher_state",
                "protocol": {"sha256": "p" * 64},
                "execution_activation": {"sha256": "a" * 64},
                "status": "waiting_for_v24200_terminal_decision",
                "reason": "parent_quality_chain_preterminal",
                "parent_safe_state_envelope_opened": True,
                "parent_content_free_decision_receipt_opened": False,
                "parent_numeric_metrics_reports_predictions_or_aggregates_read": False,
                "selected_work_order_published": False,
                "identity_handoff_selected": False,
                "nonempty_blocked_work_order_selected": False,
                "candidate_code_built_merged_or_materialized": False,
                "component_implementation_publisher_invoked": False,
                "package_gate_evaluated_or_launched": False,
                "shared_api_lease_acquired": False,
                "network_model_search_fetch_evaluator_or_api_called": False,
                "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
                "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
                "credential_value_read_persisted_hashed_or_emitted": False,
                "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
                "benchmark_forward_or_full220_launch_allowed": False,
                "leaderboard_submission_or_sota_claim": False,
                "terminal": False,
            }
            state["state_payload_sha256"] = payload_sha256(state)
            state_path.write_text(__import__("json").dumps(state))
            protocol = {
                "sha256": "p" * 64,
                "value": {
                    "decision_contract_sha256": "d" * 64,
                    "control_surface": {"manifest_sha256": "m" * 64},
                    "safe_wait_boundary": {"protected_processes": {}},
                },
            }
            activation = {
                "sha256": "a" * 64,
                "value": {"watcher": {"pid": 101, "start_ticks": 500}},
            }
            with mock.patch(
                "scripts.audit_v24204_postdecision_work_order_wait_activation.ROOT",
                root,
            ), mock.patch(
                "scripts.audit_v24204_postdecision_work_order_wait_activation.validate_protocol",
                return_value=protocol,
            ), mock.patch(
                "scripts.audit_v24204_postdecision_work_order_wait_activation.validate_activation",
                return_value=activation,
            ), mock.patch(
                "scripts.audit_v24204_postdecision_work_order_wait_activation.protected_processes",
                return_value={},
            ):
                value = build_audit(root, created_at_unix=1)
        self.assertTrue(value["boundary"]["parent_safe_state_envelope_opened"])
        self.assertTrue(
            value["boundary"][
                "parent_content_free_decision_receipt_absent_and_unopened"
            ]
        )
        self.assertFalse(value["boundary"]["candidate_code_built_merged_or_materialized"])
        self.assertFalse(value["boundary"]["package_gate_evaluated_or_launched"])
        self.assertFalse(value["boundary"]["benchmark_forward_or_full220_launch_allowed"])
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))


if __name__ == "__main__":
    unittest.main()
