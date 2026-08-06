from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from scripts import control_v24666_v24664_activation as control  # noqa: E402


class V24666ControlTests(unittest.TestCase):
    def test_frozen_protocol_and_package_validate(self):
        protocol = control._validate_protocol(); package = control._validate_package()
        self.assertEqual(protocol["task_contract"]["runtime_input_keys"], ["opaque_id", "question"])
        self.assertTrue(package["label_blind_audit"]["passed"])
        self.assertEqual(control._forward_findings(), ([], [], []))

    def test_control_tests_exclude_evaluator_surfaces(self):
        paths = {str(path) for path, _count, _timeout in control.CONTROL_TESTS}
        self.assertNotIn("tests/test_build_v24664_ror_surfaces.py", paths)
        self.assertEqual(sum(count for _path, count, _timeout in control.CONTROL_TESTS), 31)

    def test_preaudit_synthetic_go_authorizes_activation_only(self):
        protocol = control._validate_protocol()
        with patch.object(control, "_validate_protocol", return_value=protocol), patch.object(
            control, "_validate_package", return_value={}
        ), patch.object(control, "_validate_control_build", return_value={}), patch.object(
            control, "_forward_findings", return_value=([], [], [])
        ), patch.object(control, "_run_tests", return_value=(31, True)), patch.object(
            control, "_endpoint", return_value=True
        ), patch.object(control, "_lease_inactive", return_value=True), patch.object(
            control, "_active_runners", return_value=[]
        ), patch.object(control, "_pristine", return_value=True), patch.object(
            control, "protected_watcher_snapshot", return_value=protocol["execution"]["protected_watchers"]
        ), patch.object(control, "sha256", return_value="a" * 64):
            value = control._preaudit_value(now=0)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["activation_generation"])
        self.assertFalse(value["authorization"]["one_external_forward_launch"])

    def test_preaudit_runner_or_endpoint_fails_closed(self):
        protocol = control._validate_protocol()
        with patch.object(control, "_validate_protocol", return_value=protocol), patch.object(
            control, "_validate_package", return_value={}
        ), patch.object(control, "_validate_control_build", return_value={}), patch.object(
            control, "_forward_findings", return_value=([], [], [])
        ), patch.object(control, "_run_tests", return_value=(31, True)), patch.object(
            control, "_endpoint", return_value=False
        ), patch.object(control, "_lease_inactive", return_value=True), patch.object(
            control, "_active_runners", return_value=[{"pid": 1, "marker": "x"}]
        ), patch.object(control, "_pristine", return_value=True), patch.object(
            control, "protected_watcher_snapshot", return_value=protocol["execution"]["protected_watchers"]
        ), patch.object(control, "sha256", return_value="a" * 64):
            value = control._preaudit_value(now=0)
        self.assertIn("gpt56_endpoint_unreachable", value["findings"])
        self.assertIn("v24664_runner_already_active", value["findings"])

    def test_activation_authorizes_only_start(self):
        protocol = control._validate_protocol()
        audit = {"role": "v24666_v24664_strict_closure_preactivation_audit",
                 "audit_valid": True, "launch_authorized": True,
                 "protocol_file_sha256": "a" * 64,
                 "authorization": {"activation_generation": True}}
        audit["audit_sha256"] = control.payload_sha256(audit)
        with patch.object(control, "_validate_protocol", return_value=protocol), patch.object(
            control, "_validate_control_build", return_value={}
        ), patch.object(control, "_read", return_value=audit), patch.object(
            control, "sha256", return_value="a" * 64
        ), patch.object(control, "protected_watcher_snapshot", return_value=protocol["execution"]["protected_watchers"]), patch.object(
            control, "_lease_inactive", return_value=True
        ), patch.object(control, "_active_runners", return_value=[]), patch.object(control, "_pristine", return_value=True):
            value = control._activation_value(now=0)
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["one_external_forward_launch"])

    def test_only_start_can_authorize_forward(self):
        source = (ROOT / "scripts/control_v24666_v24664_activation.py").read_text()
        self.assertIn('choices=("audit", "activate", "start")', source)
        self.assertNotIn('"run":', source); self.assertNotIn('"evaluate":', source)

    def test_start_authorizes_one_forward_not_evaluator(self):
        protocol = control._validate_protocol()
        audit = {"launch_authorized": True}; audit["audit_sha256"] = control.payload_sha256(audit)
        activation = {"launch_authorized": True, "protocol_sha256": "a" * 64,
                      "preaudit_sha256": "a" * 64,
                      "authorization": {"execution_start_generation": True}}
        activation["activation_sha256"] = control.payload_sha256(activation)
        with patch.object(control, "_validate_protocol", return_value=protocol), patch.object(
            control, "_validate_control_build", return_value={}
        ), patch.object(control, "_read", side_effect=[audit, activation]), patch.object(
            control, "sha256", return_value="a" * 64
        ), patch.object(control, "protected_watcher_snapshot", return_value=protocol["execution"]["protected_watchers"]), patch.object(
            control, "_lease_inactive", return_value=True
        ), patch.object(control, "_endpoint", return_value=True), patch.object(
            control, "_active_runners", return_value=[]
        ), patch.object(control, "_pristine", return_value=True):
            value = control._start_value(now=0)
        self.assertTrue(value["authorization"]["one_external_forward_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_runner_markers_are_exact(self):
        self.assertEqual(control.RUNNER_MARKERS, (
            "scripts/run_v24664_strict_support_closure.py",
            "scripts/run_v24664_ror_task.py",
        ))


if __name__ == "__main__": unittest.main()
