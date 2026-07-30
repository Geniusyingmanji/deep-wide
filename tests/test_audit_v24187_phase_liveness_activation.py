from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audit_v24187_phase_liveness_activation import (
    build_activation,
    validate_activation,
)
from scripts.preregister_v24187_phase_liveness import publish_new
from scripts.preregister_v24187_phase_liveness import DEFAULT_STATE


class AuditV24187PhaseLivenessActivationTests(unittest.TestCase):
    def test_valid_state_and_unique_isolated_watcher_activate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = root / "results/protocol.json"
            state = root / DEFAULT_STATE
            protocol.parent.mkdir(parents=True)
            state.parent.mkdir(parents=True)
            protocol.write_text("{}", encoding="utf-8")
            state.write_text("{}", encoding="utf-8")
            frozen = {
                "path": protocol,
                "sha256": "a" * 64,
                "value": {
                    "decision_contract_sha256": "b" * 64,
                    "control_surface": {"manifest_sha256": "c" * 64},
                },
            }
            value = {
                "role": "v24187_phase_liveness_audit",
                "protocol": {"sha256": "a" * 64},
                "overall_status": "degraded_forward_healthy_manual_review_only",
                "current_phase": {"phase": "r1_full220"},
                "critical_findings": [],
                "degraded_findings": ["taxonomy:manual"],
                "source_policy": {
                    "runtime_task_state_question_answer_evidence_or_prediction_rows_opened": False,
                    "mapping_gold_category_question_type_evaluator_or_score_read": False,
                    "credential_value_or_keyring_read": False,
                    "network_or_api_called": False,
                },
                "claims": {
                    "benchmark_score_available": False,
                    "avg_at_4_available": False,
                },
            }
            with patch(
                "scripts.audit_v24187_phase_liveness_activation.validate_protocol",
                return_value=frozen,
            ), patch(
                "scripts.audit_v24187_phase_liveness_activation._read",
                return_value=value,
            ), patch(
                "scripts.audit_v24187_phase_liveness_activation._process",
                return_value={
                    "present": True,
                    "match_count": 1,
                    "pids": [1],
                    "isolated_no_bytecode_count": 1,
                    "command_lines_emitted": False,
                },
            ):
                activation = build_activation(
                    root,
                    protocol_path=protocol,
                    state_path=state,
                    created_at_unix=1,
                )
        self.assertTrue(activation["activation_valid"])
        self.assertFalse(
            activation["boundary"][
                "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read"
            ]
        )

    def test_create_exclusive_and_payload_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "activation.json"
            value = {
                "role": "v24187_phase_liveness_activation_audit",
                "activation_valid": True,
            }
            from scripts.audit_v24187_phase_liveness import payload_sha

            value["audit_payload_sha256"] = payload_sha(value)
            publish_new(path, value)
            with self.assertRaises(FileExistsError):
                publish_new(path, value)
            with patch(
                "scripts.audit_v24187_phase_liveness_activation.DEFAULT_ACTIVATION",
                Path("activation.json"),
            ):
                self.assertTrue(validate_activation(root, path)["activation_valid"])


if __name__ == "__main__":
    unittest.main()
