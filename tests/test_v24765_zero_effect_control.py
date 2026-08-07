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

from scripts import control_v24765_zero_effect_external as control  # noqa: E402


def _package() -> dict:
    value = {
        "role": "v24766_zero_effect_package_build_audit",
        "protocol_id": control.PROTOCOL_ID,
        "audit_valid": True,
        "findings": [],
        "label_blind_audit": {"passed": True},
        "source_manifest": {},
        "authorization": {
            "preactivation_audit_generation": True,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = control.payload_sha256(value)
    return value


class V24765ZeroEffectControlTests(unittest.TestCase):
    def test_protocol_and_forward_ast_are_label_blind(self) -> None:
        value = control._validate_protocol()
        self.assertEqual(
            value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"]
        )
        self.assertEqual(control._forward_findings(), ([], [], []))

    def test_commands_are_staged_and_never_include_run_or_evaluate(self) -> None:
        source = Path(control.__file__).read_text(encoding="utf-8")
        self.assertIn('choices=("audit", "activate", "start")', source)
        self.assertNotIn('"run": (', source)
        self.assertNotIn('"evaluate": (', source)
        self.assertEqual(sum(count for _path, count, _timeout in control.CONTROL_TESTS), 24)

    def test_all_commands_reject_before_effect_when_package_artifact_absent(self) -> None:
        for function in (control.preaudit, control.activate, control.start):
            with (
                patch.object(control, "_clean_remote"),
                patch.object(control, "_validate_package", side_effect=RuntimeError("missing")),
                patch.object(control, "_endpoint") as endpoint,
                patch.object(control, "_lease_inactive") as lease,
                patch.object(control, "_active_runners") as runners,
            ):
                with self.assertRaisesRegex(RuntimeError, "missing"):
                    function()
                endpoint.assert_not_called()
                lease.assert_not_called()
                runners.assert_not_called()

    def test_preaudit_go_authorizes_only_activation_generation(self) -> None:
        protocol = control._validate_protocol()
        package = _package()
        watchers = protocol["forward_health_gate"]["protected_watchers"]
        with (
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_validate_package", return_value=package),
            patch.object(control, "_forward_findings", return_value=([], [], [])),
            patch.object(control, "_run_tests", return_value=(24, True)),
            patch.object(control, "_endpoint", return_value=True),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_active_runners", return_value=[]),
            patch.object(control, "_pristine", return_value=True),
            patch.object(control, "protected_watcher_snapshot", return_value=watchers),
            patch.object(control, "sha256", return_value="a" * 64),
            patch.object(control, "_git", side_effect=["", "c" * 40, "c" * 40]),
        ):
            value = control._preaudit_value(now=0)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["activation_generation"])
        self.assertFalse(value["authorization"]["one_external_forward_launch"])
        self.assertFalse(value["authorization"]["private_truth_or_quality_surface_open"])

    def test_preaudit_fails_closed_on_endpoint_runner_or_label_finding(self) -> None:
        protocol = control._validate_protocol()
        with (
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_validate_package", return_value=_package()),
            patch.object(control, "_forward_findings", return_value=(["field"], [], [])),
            patch.object(control, "_run_tests", return_value=(24, True)),
            patch.object(control, "_endpoint", return_value=False),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_active_runners", return_value=[{"pid": 1, "marker": "x"}]),
            patch.object(control, "_pristine", return_value=True),
            patch.object(
                control,
                "protected_watcher_snapshot",
                return_value=protocol["forward_health_gate"]["protected_watchers"],
            ),
            patch.object(control, "sha256", return_value="a" * 64),
            patch.object(control, "_git", side_effect=["", "c" * 40, "c" * 40]),
        ):
            value = control._preaudit_value(now=0)
        self.assertIn("privileged_forward_field_access", value["findings"])
        self.assertIn("gpt56_endpoint_unreachable", value["findings"])
        self.assertIn("v24765_runner_already_active", value["findings"])
        self.assertFalse(value["launch_authorized"])

    def test_activation_authorizes_only_execution_start_generation(self) -> None:
        protocol = control._validate_protocol()
        audit = {
            "role": "v24765_zero_effect_preactivation_audit",
            "protocol_id": control.PROTOCOL_ID,
            "audit_valid": True,
            "launch_authorized": True,
            "protocol_sha256": "a" * 64,
            "package_build_sha256": "a" * 64,
            "authorization": {"activation_generation": True},
        }
        audit["audit_payload_sha256"] = control.payload_sha256(audit)
        with (
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_validate_package", return_value=_package()),
            patch.object(control, "_read", return_value=audit),
            patch.object(control, "sha256", return_value="a" * 64),
            patch.object(
                control,
                "protected_watcher_snapshot",
                return_value=protocol["forward_health_gate"]["protected_watchers"],
            ),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_active_runners", return_value=[]),
            patch.object(control, "_pristine", return_value=True),
            patch.object(control, "_git", side_effect=["", "c" * 40, "c" * 40]),
        ):
            value = control._activation_value(now=0)
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["one_external_forward_launch"])

    def test_start_authorizes_one_forward_but_never_quality_or_evaluator(self) -> None:
        protocol = control._validate_protocol()
        audit = {"launch_authorized": True}
        audit["audit_payload_sha256"] = control.payload_sha256(audit)
        activation = {
            "launch_authorized": True,
            "protocol_sha256": "a" * 64,
            "package_build_sha256": "a" * 64,
            "preaudit_sha256": "a" * 64,
            "authorization": {"execution_start_generation": True},
        }
        activation["activation_payload_sha256"] = control.payload_sha256(activation)
        with (
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_validate_package", return_value=_package()),
            patch.object(control, "_read", side_effect=[audit, activation]),
            patch.object(control, "sha256", return_value="a" * 64),
            patch.object(
                control,
                "protected_watcher_snapshot",
                return_value=protocol["forward_health_gate"]["protected_watchers"],
            ),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_endpoint", return_value=True),
            patch.object(control, "_active_runners", return_value=[]),
            patch.object(control, "_pristine", return_value=True),
            patch.object(control, "_git", side_effect=["", "c" * 40, "c" * 40]),
        ):
            value = control._start_value(now=0)
        self.assertEqual(
            value["authorization"],
            {
                "one_external_forward_launch": True,
                "private_truth_or_quality_surface_open": False,
                "evaluator": False,
                "paired_dev64": False,
                "exact220": False,
            },
        )

    def test_resealed_package_launch_authority_tamper_is_rejected(self) -> None:
        package = _package()
        altered = copy.deepcopy(package)
        altered["authorization"]["external_launch"] = True
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = control.payload_sha256(altered)
        with patch.object(control, "_read", return_value=altered):
            with self.assertRaises(RuntimeError):
                control._validate_package()


if __name__ == "__main__":
    unittest.main()
