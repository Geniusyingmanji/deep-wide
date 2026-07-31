from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24215_joint_package_recovery import run_cycle


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


class WatchV24215JointPackageRecoveryTests(unittest.TestCase):
    def test_before_activation_parent_is_not_opened(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch(
                "scripts.watch_v24215_joint_package_recovery._assert_failed_namespace_preserved"
            ), mock.patch(
                "scripts.watch_v24215_joint_package_recovery.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24215_joint_package_recovery._activation",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24215_joint_package_recovery._parent_state"
            ) as parent:
                value = run_cycle(ROOT, state_path=state, now=1)
        parent.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["parent_safe_state_envelope_opened"])
        self.assertFalse(value["selected_work_order_opened"])

    def test_preterminal_cycle_never_loads_selected_inputs(self) -> None:
        parent = {"status": "waiting_for_gate2a_terminal", "terminal": False}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch(
                "scripts.watch_v24215_joint_package_recovery._assert_failed_namespace_preserved"
            ), mock.patch(
                "scripts.watch_v24215_joint_package_recovery.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24215_joint_package_recovery._activation",
                return_value=ACTIVATION,
            ), mock.patch(
                "scripts.watch_v24215_joint_package_recovery._parent_state",
                return_value=(parent, False),
            ), mock.patch(
                "scripts.watch_v24215_joint_package_recovery.load_recovery_inputs"
            ) as selected:
                value = run_cycle(ROOT, state_path=state, now=1)
        selected.assert_not_called()
        self.assertEqual(
            value["status"], "waiting_for_v24213_entropy_recovery_terminal"
        )
        self.assertTrue(value["parent_safe_state_envelope_opened"])
        self.assertFalse(value["selected_work_order_opened"])
        self.assertFalse(
            value[
                "v24214_protocol_activation_state_candidate_or_publication_reused_overwritten_or_resumed"
            ]
        )
        self.assertFalse(value["package_gate_evaluated_or_launched"])
        self.assertFalse(value["dev64_launch_allowed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
