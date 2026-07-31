from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.activate_v24200_successor import build_activation


def proc(root: Path, pid: int, ticks: int) -> None:
    path = root / str(pid)
    path.mkdir(parents=True)
    fields = ["S"] + ["0"] * 18 + [str(ticks)] + ["0"] * 8
    (path / "stat").write_text(f"{pid} (python) " + " ".join(fields))


class ActivateV24200SuccessorTests(unittest.TestCase):
    def test_activation_only_grants_status_envelope_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            proc(proc_root, 101, 500)
            rows = [
                {
                    "pid": 101,
                    "argv": ["python", "-I", "-B", "scripts/watch_v24200_successor.py"],
                }
            ]
            with mock.patch(
                "scripts.activate_v24200_successor.validate_protocol",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.activate_v24200_successor.process_snapshot", return_value=rows
            ):
                value = build_activation(root, proc_root=proc_root, created_at_unix=1)
        self.assertTrue(value["status_envelope_read_allowed"])
        self.assertFalse(value["package_gate_evaluation_or_launch_allowed"])
        self.assertFalse(value["shared_api_lease_acquire_allowed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
