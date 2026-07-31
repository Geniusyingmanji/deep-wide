from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.activate_v24196_capacity_executor import (
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


class ActivateV24196CapacityExecutorTests(unittest.TestCase):
    def test_activation_binds_unique_pid_start_ticks_and_seal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            proc(proc_root, 101, 500)
            rows = [{"pid": 101, "argv": ["python", "-I", "-B", "scripts/watch_v24196_capacity_executor.py"]}]
            verified = {"path": root / "p", "sha256": "a" * 64, "value": {}}
            with mock.patch(
                "scripts.activate_v24196_capacity_executor.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.activate_v24196_capacity_executor.process_snapshot",
                return_value=rows,
            ):
                value = build_activation(
                    root, proc_root=proc_root, created_at_unix=1
                )
                path = root / "results/v24196_capacity_executor_activation_v1_20260731.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(value), encoding="utf-8")
                checked = validate_activation(root, path, proc_root=proc_root)
            self.assertEqual(value["executor"]["pid"], 101)
            self.assertEqual(value["executor"]["start_ticks"], 500)
            self.assertEqual(checked["value"], value)

    def test_pid_reuse_or_resealed_field_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            proc(proc_root, 101, 500)
            rows = [{"pid": 101, "argv": ["python", "-I", "-B", "scripts/watch_v24196_capacity_executor.py"]}]
            verified = {"path": root / "p", "sha256": "a" * 64, "value": {}}
            with mock.patch(
                "scripts.activate_v24196_capacity_executor.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.activate_v24196_capacity_executor.process_snapshot",
                return_value=rows,
            ):
                value = build_activation(root, proc_root=proc_root, created_at_unix=1)
                path = root / "results/v24196_capacity_executor_activation_v1_20260731.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(value), encoding="utf-8")
                fields = ["S"] + ["0"] * 18 + ["999"] + ["0"] * 8
                (proc_root / "101/stat").write_text(
                    "101 (python) " + " ".join(fields), encoding="utf-8"
                )
                with self.assertRaisesRegex(RuntimeError, "contract"):
                    validate_activation(root, path, proc_root=proc_root)

    def test_nonisolated_or_duplicate_executor_is_rejected(self) -> None:
        verified = {"path": Path("p"), "sha256": "a" * 64, "value": {}}
        for rows in (
            [{"pid": 1, "argv": ["python", "scripts/watch_v24196_capacity_executor.py"]}],
            [
                {"pid": 1, "argv": ["python", "-I", "-B", "scripts/watch_v24196_capacity_executor.py"]},
                {"pid": 2, "argv": ["python", "-I", "-B", "scripts/watch_v24196_capacity_executor.py"]},
            ],
        ):
            with mock.patch(
                "scripts.activate_v24196_capacity_executor.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.activate_v24196_capacity_executor.process_snapshot",
                return_value=rows,
            ), self.assertRaisesRegex(RuntimeError, "identity"):
                build_activation(Path("/tmp"), created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
