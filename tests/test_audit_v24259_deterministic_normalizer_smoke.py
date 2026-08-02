from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts import audit_v24259_deterministic_normalizer_smoke as audit  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


def _stat(proc_root: Path, pid: int, ticks: int) -> None:
    directory = proc_root / str(pid)
    directory.mkdir(parents=True)
    fields = ["S"] + ["0"] * 18 + [str(ticks)] + ["0"] * 8
    (directory / "stat").write_text(
        f"{pid} (python) " + " ".join(fields), encoding="utf-8"
    )


def _start(root: Path, pid: int, ticks: int) -> None:
    value = {
        "artifact_version": 1,
        "role": "v24259_deterministic_normalizer_smoke_execution_start",
        "created_at_unix": 1,
        "protocol_sha256": "p" * 64,
        "activation_sha256": "a" * 64,
        "selected_opaque_ids_sha256": "s" * 64,
        "runner": {"pid": pid, "start_ticks": ticks, "marker": audit.RUNNER_MARKER},
        "label_blind": True,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    path = root / audit.EXECUTION_START
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class AuditV24259Tests(unittest.TestCase):
    def test_overlay_binds_owner_pid_lock_and_start_ticks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / audit.OUTPUT
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text("protocol", encoding="utf-8")
            _start(root, 101, 500)
            # Test fixture uses a synthetic protocol digest.
            value = json.loads((root / audit.EXECUTION_START).read_text())
            value["protocol_sha256"] = audit.sha256(protocol_path)
            value["execution_start_payload_sha256"] = payload_sha256(
                {k: v for k, v in value.items() if k != "execution_start_payload_sha256"}
            )
            (root / audit.EXECUTION_START).write_text(json.dumps(value), encoding="utf-8")
            proc_root = root / "proc"
            proc_root.mkdir()
            _stat(proc_root, 101, 500)
            rows = [{"pid": 101, "argv": ["python", "-I", "-B", audit.RUNNER_MARKER]}]
            lease = {
                "active": True,
                "owner": audit.LEASE_OWNER,
                "purpose": audit.LEASE_PURPOSE,
                "ordinary": True,
                "record_valid": True,
                "pid": 101,
                "lock_holder_pids": [101],
            }
            result = audit.lease_overlay(
                root, {}, proc_root=proc_root, processes=rows, observed_lease=lease
            )
        self.assertTrue(result["identity_valid"])
        self.assertEqual(result["findings"], [])

    def test_start_tick_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / audit.OUTPUT
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text("protocol", encoding="utf-8")
            _start(root, 101, 500)
            value = json.loads((root / audit.EXECUTION_START).read_text())
            value["protocol_sha256"] = audit.sha256(protocol_path)
            value["execution_start_payload_sha256"] = payload_sha256(
                {k: v for k, v in value.items() if k != "execution_start_payload_sha256"}
            )
            (root / audit.EXECUTION_START).write_text(json.dumps(value), encoding="utf-8")
            proc_root = root / "proc"
            proc_root.mkdir()
            _stat(proc_root, 101, 999)
            rows = [{"pid": 101, "argv": ["python", "-I", "-B", audit.RUNNER_MARKER]}]
            lease = {
                "active": True,
                "owner": audit.LEASE_OWNER,
                "purpose": audit.LEASE_PURPOSE,
                "ordinary": True,
                "record_valid": True,
                "pid": 101,
                "lock_holder_pids": [101],
            }
            result = audit.lease_overlay(
                root, {}, proc_root=proc_root, processes=rows, observed_lease=lease
            )
        self.assertFalse(result["identity_valid"])
        self.assertIn("runner_start_ticks", result["findings"])


if __name__ == "__main__":
    unittest.main()
