from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24216_package_gate import _lease_compatibility, run_cycle


ROOT = Path(__file__).resolve().parents[1]
VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}
ACTIVATION = {
    "path": "results/activation.json",
    "sha256": "a" * 64,
    "watcher_pid": 1,
    "watcher_start_ticks": 2,
}


class WatchV24216PackageGateTests(unittest.TestCase):
    def test_lease_compatibility_suppresses_only_registered_findings(self) -> None:
        activation = {"watcher_pid": 7}
        lease = {"owner": "v24216_joint_package_same_dev64_gate_v1", "purpose": "paired_cold_dev64_joint_package_vs_selected_baseline", "pid": 7}
        observed = {
            "active": True,
            "ordinary": True,
            "record_valid": True,
            "owner": lease["owner"],
            "purpose": lease["purpose"],
            "pid": 7,
            "lock_holder_pids": [7],
        }
        parent = {
            "critical_findings": ["shared_api_lease_identity"],
            "audit_payload_sha256": "p" * 64,
        }
        compatibility = {
            "critical_findings": [
                "shared_api_lease_identity",
                "v24195:unknown_lease_owner",
            ],
            "compatibility": {
                "mode": "unknown_lease_owner_active",
                "unrelated_parent_critical_findings_preserved": True,
            },
            "audit_payload_sha256": "c" * 64,
        }
        with mock.patch(
            "scripts.watch_v24216_package_gate.process_snapshot", return_value=[]
        ), mock.patch(
            "scripts.watch_v24216_package_gate.lease_observation",
            return_value=observed,
        ), mock.patch(
            "scripts.watch_v24216_package_gate.build_v24187_report",
            return_value=parent,
        ), mock.patch(
            "scripts.watch_v24216_package_gate.build_v24195_report",
            return_value=compatibility,
        ):
            value = _lease_compatibility(
                ROOT,
                activation=activation,
                lease=lease,
                proc_root=Path("/proc"),
            )
        self.assertEqual(value["unrelated_findings"], [])
        self.assertTrue(value["lease_owner_purpose_pid_and_kernel_holder_exact"])

    def test_lease_compatibility_rejects_unrelated_parent_finding(self) -> None:
        activation = {"watcher_pid": 7}
        lease = {"owner": "v24216_joint_package_same_dev64_gate_v1", "purpose": "paired_cold_dev64_joint_package_vs_selected_baseline", "pid": 7}
        observed = {
            "active": True,
            "ordinary": True,
            "record_valid": True,
            "owner": lease["owner"],
            "purpose": lease["purpose"],
            "pid": 7,
            "lock_holder_pids": [7],
        }
        parent = {
            "critical_findings": ["shared_api_lease_identity", "unrelated"],
            "audit_payload_sha256": "p" * 64,
        }
        compatibility = {
            "critical_findings": [
                "shared_api_lease_identity",
                "unrelated",
                "v24195:unknown_lease_owner",
            ],
            "compatibility": {
                "mode": "unknown_lease_owner_active",
                "unrelated_parent_critical_findings_preserved": True,
            },
            "audit_payload_sha256": "c" * 64,
        }
        with mock.patch(
            "scripts.watch_v24216_package_gate.process_snapshot", return_value=[]
        ), mock.patch(
            "scripts.watch_v24216_package_gate.lease_observation",
            return_value=observed,
        ), mock.patch(
            "scripts.watch_v24216_package_gate.build_v24187_report",
            return_value=parent,
        ), mock.patch(
            "scripts.watch_v24216_package_gate.build_v24195_report",
            return_value=compatibility,
        ):
            with self.assertRaises(RuntimeError):
                _lease_compatibility(
                    ROOT,
                    activation=activation,
                    lease=lease,
                    proc_root=Path("/proc"),
                )

    def test_before_activation_parent_is_not_opened(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch(
                "scripts.watch_v24216_package_gate.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24216_package_gate._activation", return_value=None
            ), mock.patch(
                "scripts.watch_v24216_package_gate._execution_outputs_absent",
                return_value=True,
            ), mock.patch(
                "scripts.watch_v24216_package_gate._parent_state"
            ) as parent:
                value = run_cycle(ROOT, state_path=state, now=1)
        parent.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["parent_safe_state_envelope_opened"])
        self.assertFalse(value["shared_api_lease_acquired"])

    def test_preterminal_never_opens_publication_or_runner(self) -> None:
        parent = {
            "status": "waiting_for_v24213_entropy_recovery_terminal",
            "terminal": False,
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch(
                "scripts.watch_v24216_package_gate.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24216_package_gate._activation",
                return_value=ACTIVATION,
            ), mock.patch(
                "scripts.watch_v24216_package_gate._parent_state",
                return_value=(parent, False),
            ), mock.patch(
                "scripts.watch_v24216_package_gate._execution_outputs_absent",
                return_value=True,
            ), mock.patch(
                "scripts.watch_v24216_package_gate.validate_parent_publication"
            ) as publication, mock.patch(
                "scripts.watch_v24216_package_gate.prepare_pair"
            ) as prepare, mock.patch(
                "scripts.watch_v24216_package_gate.acquire_deepwide_api_lease"
            ) as lease:
                value = run_cycle(ROOT, state_path=state, now=1)
        publication.assert_not_called()
        prepare.assert_not_called()
        lease.assert_not_called()
        self.assertEqual(
            value["status"], "waiting_for_v24215_joint_package_terminal"
        )
        self.assertTrue(value["parent_safe_state_envelope_opened"])
        self.assertFalse(value["parent_publication_opened"])
        self.assertFalse(value["mapping_or_evaluator_opened"])
        self.assertFalse(value["package_gate_evaluated"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
