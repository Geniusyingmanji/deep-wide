from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.activate_v24197_parallel_all220 import (
    build_activation,
    validate_activation,
)


def proc(proc_root: Path, pid: int, ticks: int) -> None:
    directory = proc_root / str(pid)
    directory.mkdir(parents=True)
    fields = ["S"] + ["0"] * 18 + [str(ticks)] + ["0"] * 8
    (directory / "stat").write_text(
        f"{pid} (python) " + " ".join(fields), encoding="utf-8"
    )


class ActivateV24197ParallelAll220Tests(unittest.TestCase):
    def test_activation_binds_unique_pid_and_never_authorizes_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            proc(proc_root, 101, 500)
            rows = [{"pid": 101, "argv": ["python", "-I", "-B", "scripts/watch_v24197_parallel_all220.py"]}]
            verified = {"sha256": "a" * 64, "value": {}}
            with mock.patch(
                "scripts.activate_v24197_parallel_all220.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.activate_v24197_parallel_all220.process_snapshot",
                return_value=rows,
            ):
                value = build_activation(root, proc_root=proc_root, created_at_unix=1)
                path = root / "results/v24197_parallel_all220_activation_v1_20260731.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(value), encoding="utf-8")
                checked = validate_activation(root, path, proc_root=proc_root)
        self.assertEqual(checked["value"]["executor"]["start_ticks"], 500)
        self.assertFalse(value["shared_api_lease_acquire_allowed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_duplicate_nonisolated_or_pid_reuse_is_rejected(self) -> None:
        verified = {"sha256": "a" * 64, "value": {}}
        for rows in (
            [{"pid": 1, "argv": ["python", "scripts/watch_v24197_parallel_all220.py"]}],
            [
                {"pid": 1, "argv": ["python", "-I", "-B", "scripts/watch_v24197_parallel_all220.py"]},
                {"pid": 2, "argv": ["python", "-I", "-B", "scripts/watch_v24197_parallel_all220.py"]},
            ],
        ):
            with mock.patch(
                "scripts.activate_v24197_parallel_all220.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.activate_v24197_parallel_all220.process_snapshot",
                return_value=rows,
            ), self.assertRaisesRegex(RuntimeError, "identity"):
                build_activation(Path("/tmp"), created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
