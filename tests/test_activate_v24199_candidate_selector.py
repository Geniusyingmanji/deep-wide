from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.activate_v24199_candidate_selector import (
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


class ActivateV24199CandidateSelectorTests(unittest.TestCase):
    def test_activation_binds_unique_pid_and_grants_no_build_or_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            proc(proc_root, 101, 500)
            rows = [
                {
                    "pid": 101,
                    "argv": [
                        "python",
                        "-I",
                        "-B",
                        "scripts/watch_v24199_candidate_selector.py",
                    ],
                }
            ]
            verified = {
                "sha256": "a" * 64,
                "value": {"selector_protocol": {"sha256": "s" * 64}},
            }
            with mock.patch(
                "scripts.activate_v24199_candidate_selector.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.activate_v24199_candidate_selector.process_snapshot",
                return_value=rows,
            ):
                value = build_activation(root, proc_root=proc_root, created_at_unix=1)
                path = root / "results/v24199_candidate_selector_activation_v1_20260731.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(value), encoding="utf-8")
                checked = validate_activation(root, path, proc_root=proc_root)
        self.assertEqual(checked["value"]["selector"]["start_ticks"], 500)
        self.assertFalse(
            value["candidate_code_build_merge_or_freeze_generation_allowed"]
        )
        self.assertFalse(value["shared_api_lease_acquire_allowed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_duplicate_or_nonisolated_selector_is_rejected(self) -> None:
        verified = {
            "sha256": "a" * 64,
            "value": {"selector_protocol": {"sha256": "s" * 64}},
        }
        for rows in (
            [{"pid": 1, "argv": ["python", "scripts/watch_v24199_candidate_selector.py"]}],
            [
                {"pid": 1, "argv": ["python", "-I", "-B", "scripts/watch_v24199_candidate_selector.py"]},
                {"pid": 2, "argv": ["python", "-I", "-B", "scripts/watch_v24199_candidate_selector.py"]},
            ],
        ):
            with mock.patch(
                "scripts.activate_v24199_candidate_selector.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.activate_v24199_candidate_selector.process_snapshot",
                return_value=rows,
            ), self.assertRaisesRegex(RuntimeError, "identity"):
                build_activation(Path("/tmp"), created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
