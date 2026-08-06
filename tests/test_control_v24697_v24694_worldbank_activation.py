from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import control_v24697_v24694_worldbank_activation as control  # noqa: E402


class V24697WorldBankActivationTests(unittest.TestCase):
    def protocol(self):
        return {"execution": {"protected_watchers": []}}

    def test_preaudit_authorizes_activation_only(self) -> None:
        with patch.object(control, "_validate_protocol", side_effect=lambda: self.protocol()), patch.object(
            control, "_validate_package"
        ), patch.object(control, "_validate_control_build"), patch.object(
            control, "_forward_findings", return_value=([], [], [], [])
        ), patch.object(control, "_run_tests", return_value=(control.EXPECTED_TESTS, True)), patch.object(
            control, "protected_watcher_snapshot", return_value=[]
        ), patch.object(control, "_active_runners", return_value=[]), patch.object(
            control, "_endpoint", return_value=True
        ), patch.object(control, "_lease_inactive", return_value=True), patch.object(
            control, "_pristine", return_value=True
        ), patch.object(control, "sha256", return_value="a" * 64):
            value = control._preaudit_value(now=0)
        self.assertTrue(value["authorization"]["activation_generation"])
        self.assertFalse(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["one_external_forward_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_preaudit_fails_closed_on_privileged_field(self) -> None:
        with patch.object(control, "_validate_protocol", side_effect=lambda: self.protocol()), patch.object(
            control, "_validate_package"
        ), patch.object(control, "_validate_control_build"), patch.object(
            control, "_forward_findings", return_value=(["x:gold"], [], [], [])
        ), patch.object(control, "_run_tests", return_value=(control.EXPECTED_TESTS, True)), patch.object(
            control, "protected_watcher_snapshot", return_value=[]
        ), patch.object(control, "_active_runners", return_value=[]), patch.object(
            control, "_endpoint", return_value=True
        ), patch.object(control, "_lease_inactive", return_value=True), patch.object(
            control, "_pristine", return_value=True
        ), patch.object(control, "sha256", return_value="a" * 64):
            value = control._preaudit_value(now=0)
        self.assertIn("privileged_forward_field_access", value["findings"])
        self.assertFalse(value["launch_authorized"])

    def test_preaudit_fails_closed_on_lease_runner_or_endpoint(self) -> None:
        with patch.object(control, "_validate_protocol", side_effect=lambda: self.protocol()), patch.object(
            control, "_validate_package"
        ), patch.object(control, "_validate_control_build"), patch.object(
            control, "_forward_findings", return_value=([], [], [], [])
        ), patch.object(control, "_run_tests", return_value=(control.EXPECTED_TESTS, True)), patch.object(
            control, "protected_watcher_snapshot", return_value=[]
        ), patch.object(control, "_active_runners", return_value=[{"pid": 1}]), patch.object(
            control, "_endpoint", return_value=False
        ), patch.object(control, "_lease_inactive", return_value=False), patch.object(
            control, "_pristine", return_value=True
        ), patch.object(control, "sha256", return_value="a" * 64):
            value = control._preaudit_value(now=0)
        self.assertIn("gpt56_endpoint_unreachable", value["findings"])
        self.assertIn("shared_api_lease_active", value["findings"])
        self.assertIn("v24694_runner_already_active", value["findings"])

    def test_activation_cannot_authorize_forward(self) -> None:
        preaudit = {
            "role": "v24697_v24694_worldbank_preactivation_audit",
            "audit_valid": True,
            "authorization": {"activation_generation": True},
            "protocol_file_sha256": "a" * 64,
        }
        preaudit["audit_sha256"] = control.payload_sha256(preaudit)
        with patch.object(control, "_validate_protocol", side_effect=lambda: self.protocol()), patch.object(
            control, "_validate_control_build"
        ), patch.object(control, "_read", return_value=preaudit), patch.object(
            control, "protected_watcher_snapshot", return_value=[]
        ), patch.object(control, "_active_runners", return_value=[]), patch.object(
            control, "_lease_inactive", return_value=True
        ), patch.object(control, "_pristine", return_value=True), patch.object(
            control, "sha256", return_value="a" * 64
        ):
            value = control._activation_value(now=0)
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["one_external_forward_launch"])

    def test_start_is_only_forward_authority(self) -> None:
        audit = {"launch_authorized": True}
        audit["audit_sha256"] = control.payload_sha256(audit)
        activation = {
            "launch_authorized": True,
            "authorization": {"execution_start_generation": True},
            "protocol_sha256": "a" * 64,
            "preaudit_sha256": "a" * 64,
        }
        activation["activation_sha256"] = control.payload_sha256(activation)
        values = iter((audit, activation))
        with patch.object(control, "_validate_protocol", side_effect=lambda: self.protocol()), patch.object(
            control, "_validate_control_build"
        ), patch.object(control, "_read", side_effect=lambda _path: next(values)), patch.object(
            control, "protected_watcher_snapshot", return_value=[]
        ), patch.object(control, "_active_runners", return_value=[]), patch.object(
            control, "_lease_inactive", return_value=True
        ), patch.object(control, "_endpoint", return_value=True), patch.object(
            control, "_pristine", return_value=True
        ), patch.object(control, "sha256", return_value="a" * 64):
            value = control._start_value(now=0)
        self.assertTrue(value["authorization"]["one_external_forward_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_resealed_activation_cannot_skip_chain(self) -> None:
        value = {
            "role": "wrong",
            "audit_valid": True,
            "authorization": {"activation_generation": True},
            "protocol_file_sha256": "a" * 64,
        }
        value["audit_sha256"] = control.payload_sha256(value)
        with patch.object(control, "_validate_protocol", side_effect=lambda: self.protocol()), patch.object(
            control, "_validate_control_build"
        ), patch.object(control, "_read", return_value=value), patch.object(
            control, "protected_watcher_snapshot", return_value=[]
        ), patch.object(control, "_active_runners", return_value=[]), patch.object(
            control, "_lease_inactive", return_value=True
        ), patch.object(control, "_pristine", return_value=True), patch.object(
            control, "sha256", return_value="a" * 64
        ):
            activation = control._activation_value(now=0)
        self.assertIn("preactivation_chain_invalid", activation["findings"])

    def test_control_has_no_run_or_evaluate_command(self) -> None:
        tree = ast.parse((ROOT / "scripts/control_v24697_v24694_worldbank_activation.py").read_text())
        choices = [
            node.value.elts
            for node in ast.walk(tree)
            if isinstance(node, ast.keyword)
            and node.arg == "choices"
            and isinstance(node.value, ast.Tuple)
        ]
        serialized = ast.dump(tree)
        self.assertTrue(choices)
        self.assertNotIn("run_forward", serialized)
        self.assertNotIn("evaluate_predictions", serialized)

    def test_forward_scan_is_clean(self) -> None:
        self.assertEqual(control._forward_findings(), ([], [], [], []))


if __name__ == "__main__":
    unittest.main()
