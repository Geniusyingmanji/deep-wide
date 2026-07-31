from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.activate_v24213_entropy_recovery import build_activation  # noqa: E402


def proc(root: Path, pid: int, ticks: int) -> None:
    path = root / str(pid)
    path.mkdir(parents=True)
    fields = ["S"] + ["0"] * 18 + [str(ticks)] + ["0"] * 8
    (path / "stat").write_text(f"{pid} (python) " + " ".join(fields))


class ActivateV24213EntropyRecoveryTests(unittest.TestCase):
    def test_activation_grants_recovery_publication_only(self) -> None:
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
                        "scripts/watch_v24213_entropy_recovery.py",
                    ],
                }
            ]
            with mock.patch(
                "scripts.activate_v24213_entropy_recovery.validate_protocol",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.activate_v24213_entropy_recovery.process_snapshot",
                return_value=rows,
            ):
                value = build_activation(
                    root, proc_root=proc_root, created_at_unix=1
                )
        self.assertTrue(value["selected_entropy_component_recovery_publication_allowed"])
        self.assertFalse(
            value[
                "failed_v24212_activation_state_candidate_or_publication_reuse_allowed"
            ]
        )
        self.assertFalse(value["shared_api_lease_acquire_allowed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
