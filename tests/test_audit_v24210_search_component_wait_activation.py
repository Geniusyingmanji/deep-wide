from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.audit_v24210_search_component_wait_activation import build_audit


class AuditV24210SearchComponentWaitActivationTests(unittest.TestCase):
    def test_wait_audit_opens_no_selected_parent_or_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "outputs/v24210_selected_search_component_watcher_state_v1_20260731.json"
            state_path.parent.mkdir()
            state = {
                "role": "v24210_selected_search_component_watcher_state",
                "protocol": {"sha256": "p" * 64},
                "execution_activation": {"sha256": "a" * 64},
                "status": "waiting_for_scope_and_search_quality_terminal",
                "reason": "scope_parent_and_search_quality_preterminal",
                "scope_parent_safe_state_envelope_opened": True,
                "search_quality_safe_state_envelope_opened": True,
                "selected_work_order_opened": False,
                "markdown_publication_opened": False,
                "scope_publication_opened": False,
                "search_gate_opened": False,
                "numeric_metrics_reports_predictions_or_aggregates_read": False,
                "component_publication_created": False,
                "search_component_published": False,
                "search_component_retired": False,
                "search_component_absent_noop": False,
                "candidate_materialized": False,
                "p12_scope_schema70_parent_preserved": False,
                "mainline_scope_zero_byte_alias_preserved": False,
                "threshold_query_policy_or_gate_changed": False,
                "entropy_controller_published_or_implemented": False,
                "joint_package_built_or_materialized": False,
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
            state_path.write_text(json.dumps(state))
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
                "scripts.audit_v24210_search_component_wait_activation.ROOT", root
            ), mock.patch(
                "scripts.audit_v24210_search_component_wait_activation.validate_protocol",
                return_value=protocol,
            ), mock.patch(
                "scripts.audit_v24210_search_component_wait_activation.validate_activation",
                return_value=activation,
            ), mock.patch(
                "scripts.audit_v24210_search_component_wait_activation.protected_processes",
                return_value={},
            ):
                value = build_audit(root, created_at_unix=1)
        boundary = value["boundary"]
        self.assertTrue(boundary["selected_parent_content_and_quality_gate_unopened"])
        self.assertTrue(boundary["component_publication_absent"])
        self.assertTrue(boundary["candidate_root_absent"])
        self.assertFalse(boundary["shared_api_lease_acquired"])
        self.assertFalse(boundary["benchmark_forward_or_full220_launch_allowed"])
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))


if __name__ == "__main__":
    unittest.main()
