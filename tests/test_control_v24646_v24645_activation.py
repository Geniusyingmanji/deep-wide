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

from scripts import control_v24646_v24645_activation as control


class ActivationControlTests(unittest.TestCase):
    def test_frozen_protocol_and_package_validate(self) -> None:
        protocol = control._validate_protocol()
        package = control._validate_package_build()
        self.assertEqual(protocol["task_contract"]["runtime_input_keys"], ["opaque_id", "question"])
        self.assertTrue(package["label_blind_audit"]["passed"])

    def test_preaudit_excludes_evaluator_test_suite(self) -> None:
        paths = {str(path) for path, _count, _timeout in control.CONTROL_TESTS}
        self.assertNotIn("tests/test_v24645_external_package.py", paths)
        self.assertEqual(sum(count for _path, count, _timeout in control.CONTROL_TESTS), 27)
        self.assertEqual(control.EXPECTED_FOCUSED_TESTS, 27)

    def test_preaudit_synthetic_go_only_authorizes_activation(self) -> None:
        protocol = control._validate_protocol()
        with (
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_validate_package_build", return_value={}),
            patch.object(control, "_validate_control_build", return_value={"audit_valid": True}),
            patch.object(control, "_forward_findings", return_value=([], [], [])),
            patch.object(control, "_run_focused_tests", return_value=(27, True)),
            patch.object(control, "_endpoint_reachable", return_value=True),
            patch.object(control, "protected_watcher_snapshot", return_value=protocol["execution"]["protected_watchers"]),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_active_runners", return_value=[]),
            patch.object(control, "_future_pristine", return_value=True),
            patch.object(control, "sha256", return_value="a" * 64),
        ):
            value = control._preaudit_value(now=0)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["launch_authorized"])
        self.assertTrue(value["authorization"]["activation_generation"])
        self.assertFalse(value["authorization"]["one_external_forward_launch"])
        self.assertFalse(value["checks"]["private_population_gold_provenance_or_evaluator_opened_or_hashed"])

    def test_preaudit_endpoint_or_runner_fails_closed(self) -> None:
        protocol = control._validate_protocol()
        with (
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_validate_package_build", return_value={}),
            patch.object(control, "_validate_control_build", return_value={"audit_valid": True}),
            patch.object(control, "_forward_findings", return_value=([], [], [])),
            patch.object(control, "_run_focused_tests", return_value=(27, True)),
            patch.object(control, "_endpoint_reachable", return_value=False),
            patch.object(control, "protected_watcher_snapshot", return_value=protocol["execution"]["protected_watchers"]),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_active_runners", return_value=[{"pid": 1, "marker": "runner"}]),
            patch.object(control, "_future_pristine", return_value=True),
            patch.object(control, "sha256", return_value="a" * 64),
        ):
            value = control._preaudit_value(now=0)
        self.assertFalse(value["audit_valid"])
        self.assertIn("gpt56_endpoint_unreachable", value["findings"])
        self.assertIn("v24645_runner_already_active", value["findings"])

    def test_activation_only_authorizes_execution_start(self) -> None:
        protocol = control._validate_protocol()
        audit = {
            "role": "v24646_v24645_primary_identity_preactivation_audit",
            "audit_valid": True,
            "launch_authorized": True,
            "protocol_file_sha256": "a" * 64,
            "authorization": {"activation_generation": True},
        }
        audit["audit_sha256"] = control.payload_sha256(audit)
        with (
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_validate_control_build", return_value={}),
            patch.object(control, "_read", return_value=audit),
            patch.object(control, "sha256", return_value="a" * 64),
            patch.object(control, "protected_watcher_snapshot", return_value=protocol["execution"]["protected_watchers"]),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_active_runners", return_value=[]),
            patch.object(control, "_future_pristine", return_value=True),
        ):
            value = control._activation_value(now=0)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["one_external_forward_launch"])

    def test_execution_start_is_only_stage_with_launch_authority(self) -> None:
        source = (ROOT / "scripts/control_v24646_v24645_activation.py").read_text(encoding="utf-8")
        self.assertIn('choices=("audit", "activate", "start")', source)
        self.assertNotIn('"protocol":', source)
        self.assertNotIn('"run":', source)
        self.assertNotIn('"evaluate":', source)

    def test_execution_start_sealed_chain_authorizes_one_forward_only(self) -> None:
        protocol = control._validate_protocol()
        audit = {
            "role": "v24646_v24645_primary_identity_preactivation_audit",
            "audit_valid": True,
            "launch_authorized": True,
            "protocol_file_sha256": "a" * 64,
            "authorization": {"activation_generation": True},
        }
        audit["audit_sha256"] = control.payload_sha256(audit)
        activation = {
            "role": "v24646_v24645_primary_identity_activation",
            "launch_authorized": True,
            "protocol_sha256": "a" * 64,
            "preaudit_sha256": "a" * 64,
            "authorization": {"execution_start_generation": True},
        }
        activation["activation_sha256"] = control.payload_sha256(activation)
        with (
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_validate_control_build", return_value={}),
            patch.object(control, "_read", side_effect=[audit, activation]),
            patch.object(control, "sha256", return_value="a" * 64),
            patch.object(
                control,
                "protected_watcher_snapshot",
                return_value=protocol["execution"]["protected_watchers"],
            ),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_endpoint_reachable", return_value=True),
            patch.object(control, "_active_runners", return_value=[]),
            patch.object(control, "_future_pristine", return_value=True),
        ):
            value = control._start_value(now=0)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["launch_authorized"])
        self.assertEqual(
            value["authorization"],
            {
                "one_external_forward_launch": True,
                "evaluator": False,
                "dev64": False,
                "exact220": False,
            },
        )
        self.assertFalse(value["first_network_model_search_or_fetch_effect_started"])
        self.assertFalse(
            value[
                "private_population_gold_provenance_or_evaluator_opened_or_hashed"
            ]
        )

    def test_active_runner_scan_matches_only_frozen_markers(self) -> None:
        with unittest.mock.patch.object(Path, "iterdir", return_value=[]):
            self.assertEqual(control._active_runners(Path("/proc")), [])
        self.assertEqual(
            control.RUNNER_MARKERS,
            (
                "scripts/run_v24645_primary_identity_pair.py",
                "scripts/run_v24645_ror_task.py",
            ),
        )


if __name__ == "__main__":
    unittest.main()
