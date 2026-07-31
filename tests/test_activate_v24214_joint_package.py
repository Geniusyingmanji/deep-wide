from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.activate_v24214_joint_package import build_activation


ROOT = Path(__file__).resolve().parents[1]


class ActivateV24214JointPackageTests(unittest.TestCase):
    def test_activation_binds_one_isolated_watcher_without_gate_authority(self) -> None:
        rows = [
            {
                "pid": 7,
                "argv": [
                    "python",
                    "-I",
                    "-B",
                    "scripts/watch_v24214_joint_package.py",
                ],
            }
        ]
        with mock.patch(
            "scripts.activate_v24214_joint_package.validate_protocol",
            return_value={"sha256": "p" * 64},
        ), mock.patch(
            "scripts.activate_v24214_joint_package.process_snapshot",
            return_value=rows,
        ), mock.patch(
            "scripts.activate_v24214_joint_package._start_ticks", return_value=9
        ):
            value = build_activation(ROOT, created_at_unix=1)
        self.assertEqual(value["watcher"]["pid"], 7)
        self.assertTrue(value["watcher"]["python_isolated_no_bytecode"])
        self.assertFalse(value["component_directory_overlay_allowed"])
        self.assertFalse(value["package_gate_evaluation_or_launch_allowed"])
        self.assertFalse(value["dev64_launch_allowed"])
        self.assertFalse(value["shared_api_lease_acquire_allowed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])
        unsigned = dict(value)
        seal = unsigned.pop("activation_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))


if __name__ == "__main__":
    unittest.main()
