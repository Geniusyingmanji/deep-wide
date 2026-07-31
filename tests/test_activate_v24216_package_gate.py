from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.activate_v24216_package_gate import build_activation


ROOT = Path(__file__).resolve().parents[1]


class ActivateV24216PackageGateTests(unittest.TestCase):
    def test_activation_binds_unique_isolated_watcher_without_full220(self) -> None:
        verified = {"sha256": "p" * 64, "value": {}}
        rows = [{"pid": 7, "argv": ["python", "-I", "-B", "scripts/watch_v24216_package_gate.py"]}]
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "scripts.activate_v24216_package_gate.validate_protocol",
            return_value=verified,
        ), mock.patch(
            "scripts.activate_v24216_package_gate.process_snapshot",
            return_value=rows,
        ), mock.patch(
            "scripts.activate_v24216_package_gate.actual_python_script",
            return_value="scripts/watch_v24216_package_gate.py",
        ), mock.patch(
            "scripts.activate_v24216_package_gate._start_ticks", return_value=9
        ):
            value = build_activation(
                ROOT, proc_root=Path(directory), created_at_unix=1
            )
        self.assertEqual(value["watcher"]["pid"], 7)
        self.assertEqual(value["watcher"]["start_ticks"], 9)
        self.assertTrue(value["mapping_and_evaluator_only_after_both_forward_arms_terminal"])
        self.assertFalse(value["historical_baseline_result_reuse_allowed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
