from __future__ import annotations

import copy
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import control_v24784_projection_funnel_external as control  # noqa: E402


def package() -> dict:
    value = {
        "role": "v24784_projection_funnel_package_audit",
        "protocol_id": control.contract.PROTOCOL_ID,
        "audit_valid": True,
        "findings": [],
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
    value["audit_payload_sha256"] = control.contract.payload_sha256(value)
    return value


class V24784ProjectionFunnelControlTests(unittest.TestCase):
    def protocol(self) -> dict:
        return control._validate_protocol()

    @contextmanager
    def state(self, *, pristine: bool = True):
        protocol = self.protocol()
        with (
            patch.object(control, "_validate_package", return_value=package()),
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_clean_remote"),
            patch.object(
                control.contract,
                "protected_watcher_snapshot",
                return_value=protocol["forward_health_gate"]["protected_watchers"],
            ),
            patch.object(control, "_endpoint", return_value=True),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_active_runners", return_value=[]),
            patch.object(control, "_pristine", return_value=pristine),
            patch.object(control.contract, "sha256", return_value="a" * 64),
        ):
            yield

    def test_protocol_and_forward_ast_are_label_blind(self) -> None:
        value = self.protocol()
        self.assertEqual(
            value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"]
        )
        self.assertEqual(control._forward_findings(), ([], [], [], []))

    def test_commands_are_staged_and_never_include_run_or_evaluate(self) -> None:
        source = Path(control.__file__).read_text(encoding="utf-8")
        self.assertIn('choices=("audit", "activate", "start")', source)
        self.assertNotIn('"run": (', source)
        self.assertNotIn('"evaluate": (', source)
        self.assertEqual(
            sum(count for _path, count, _timeout in control.CONTROL_TESTS), 44
        )

    def test_all_commands_reject_package_before_state_probes(self) -> None:
        for function in (control.preaudit, control.activate, control.start):
            with (
                patch.object(control, "_clean_remote"),
                patch.object(
                    control, "_validate_package", side_effect=RuntimeError("missing")
                ),
                patch.object(control, "_endpoint") as endpoint,
                patch.object(control, "_lease_inactive") as lease,
                patch.object(control, "_active_runners") as runners,
            ):
                with self.assertRaisesRegex(RuntimeError, "missing"):
                    function()
                endpoint.assert_not_called()
                lease.assert_not_called()
                runners.assert_not_called()

    def test_preaudit_go_only_authorizes_activation_generation(self) -> None:
        with (
            self.state(),
            patch.object(control, "_forward_findings", return_value=([], [], [], [])),
            patch.object(control, "_run_tests", return_value=(44, True, [])),
        ):
            value = control._preaudit_value(now=0)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["authorization"], control.PREAUTH)
        self.assertFalse(value["authorization"]["one_external_forward_launch"])

    def test_preaudit_fails_closed_on_endpoint_runner_label_or_surface(self) -> None:
        protocol = self.protocol()
        with (
            patch.object(control, "_validate_package", return_value=package()),
            patch.object(control, "_validate_protocol", return_value=protocol),
            patch.object(control, "_clean_remote"),
            patch.object(control, "_forward_findings", return_value=(["field"], [], [], [])),
            patch.object(control, "_run_tests", return_value=(44, True, [])),
            patch.object(
                control.contract,
                "protected_watcher_snapshot",
                return_value=protocol["forward_health_gate"]["protected_watchers"],
            ),
            patch.object(control, "_endpoint", return_value=False),
            patch.object(control, "_lease_inactive", return_value=True),
            patch.object(control, "_active_runners", return_value=[123]),
            patch.object(control, "_pristine", return_value=False),
            patch.object(control.contract, "sha256", return_value="a" * 64),
        ):
            value = control._preaudit_value(now=0)
        for finding in (
            "privileged_forward_field_access",
            "gpt56_endpoint_unreachable",
            "v24784_runner_already_active",
            "future_surface_not_pristine",
        ):
            self.assertIn(finding, value["findings"])
        self.assertFalse(value["launch_authorized"])

    def test_activation_only_authorizes_execution_start_generation(self) -> None:
        audit = {
            "authorization": dict(control.PREAUTH),
            "launch_authorized": True,
        }
        with (
            self.state(),
            patch.object(control, "validate_preaudit", return_value=audit),
            patch.object(control, "_read", return_value=audit),
        ):
            value = control._activation_value(now=0)
        self.assertEqual(value["authorization"], control.ACTIVATION_AUTH)
        self.assertFalse(value["authorization"]["one_external_forward_launch"])

    def test_start_alone_authorizes_one_forward(self) -> None:
        audit = {"authorization": dict(control.PREAUTH), "launch_authorized": True}
        activation = {
            "authorization": dict(control.ACTIVATION_AUTH),
            "launch_authorized": True,
        }
        with (
            self.state(),
            patch.object(control, "validate_preaudit", return_value=audit),
            patch.object(control, "validate_activation", return_value=activation),
            patch.object(control, "_read", side_effect=[audit, activation]),
        ):
            value = control._start_value(now=0)
        self.assertEqual(value["authorization"], control.START_AUTH)
        self.assertFalse(value["first_network_model_search_or_fetch_effect_started"])
        self.assertFalse(value["authorization"]["private_truth_or_quality_surface_open"])

    def test_resealed_package_launch_authority_tamper_is_rejected(self) -> None:
        value = package()
        altered = copy.deepcopy(value)
        altered["authorization"]["external_launch"] = True
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = control.contract.payload_sha256(altered)
        with (
            patch.object(control, "_read", return_value=altered),
            patch.object(
                control.package_audit,
                "validate_audit",
                return_value=altered,
            ),
        ):
            with self.assertRaises(RuntimeError):
                control._validate_package()

    def test_create_only_publish_rejects_overwrite(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
