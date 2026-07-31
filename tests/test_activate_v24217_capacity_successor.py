from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.activate_v24217_capacity_successor import build_activation


ROOT = Path(__file__).resolve().parents[1]


class ActivateV24217CapacitySuccessorTests(unittest.TestCase):
    def test_activation_binds_unique_watcher_without_full220(self) -> None:
        rows = [
            {
                "pid": 7,
                "argv": [
                    "python",
                    "-I",
                    "-B",
                    "scripts/watch_v24217_capacity_successor.py",
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "scripts.activate_v24217_capacity_successor.validate_protocol",
            return_value={"sha256": "p" * 64, "value": {}},
        ), mock.patch(
            "scripts.activate_v24217_capacity_successor.process_snapshot",
            return_value=rows,
        ), mock.patch(
            "scripts.activate_v24217_capacity_successor.actual_python_script",
            return_value="scripts/watch_v24217_capacity_successor.py",
        ), mock.patch(
            "scripts.activate_v24217_capacity_successor._start_ticks",
            return_value=9,
        ):
            value = build_activation(
                ROOT, proc_root=Path(directory), created_at_unix=1
            )
        self.assertEqual(value["watcher"]["pid"], 7)
        self.assertTrue(value["execution_start_required_before_client_or_api"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])
        self.assertFalse(value["retry_resume_or_selective_rerun_allowed"])


if __name__ == "__main__":
    unittest.main()
