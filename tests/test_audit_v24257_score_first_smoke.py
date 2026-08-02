from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts import audit_v24257_score_first_smoke as target
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256


def _write_start(root: Path, pid: int, ticks: int) -> None:
    protocol_path = root / target.OUTPUT
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    protocol_path.write_text("{}\n", encoding="utf-8")
    value = {
        "artifact_version": 1,
        "role": "v24257_score_first_smoke_execution_start",
        "created_at_unix": 1,
        "protocol_sha256": sha256(protocol_path),
        "activation_sha256": "a" * 64,
        "selected_opaque_ids_sha256": "s" * 64,
        "runner": {
            "pid": pid,
            "start_ticks": ticks,
            "marker": target.RUNNER_MARKER,
        },
        "label_blind": True,
        "mapping_gold_evaluator_or_score_read": False,
        "api_called_before_execution_start": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    path = root / target.EXECUTION_START
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_proc_stat(proc_root: Path, pid: int, ticks: int) -> None:
    directory = proc_root / str(pid)
    directory.mkdir(parents=True)
    fields = ["S"] + ["0"] * 18 + [str(ticks)] + ["0"] * 8
    (directory / "stat").write_text(
        f"{pid} (python) " + " ".join(fields), encoding="utf-8"
    )


class AuditV24257ScoreFirstSmokeTests(unittest.TestCase):
    def test_registered_owner_overlay_requires_exact_live_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            _write_start(root, 101, 500)
            _write_proc_stat(proc_root, 101, 500)
            rows = [
                {
                    "pid": 101,
                    "argv": ["python", "-I", "-B", target.RUNNER_MARKER],
                }
            ]
            lease = {
                "active": True,
                "ordinary": True,
                "record_valid": True,
                "owner": target.LEASE_OWNER,
                "purpose": target.LEASE_PURPOSE,
                "pid": 101,
                "lock_holder_pids": [101],
            }
            value = target.lease_overlay(
                root,
                {},
                proc_root=proc_root,
                processes=rows,
                observed_lease=lease,
            )

        self.assertTrue(value["identity_valid"])
        self.assertTrue(value["legacy_finding_suppression_allowed"])
        self.assertEqual(value["findings"], [])

    def test_unrelated_owner_cannot_suppress_legacy_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            value = target.lease_overlay(
                root,
                {},
                proc_root=proc_root,
                processes=[],
                observed_lease={
                    "active": True,
                    "owner": "unrelated",
                    "purpose": "unrelated",
                },
            )
        self.assertFalse(value["identity_valid"])
        self.assertFalse(value["legacy_finding_suppression_allowed"])
        self.assertIn("unrelated_active_lease_owner", value["findings"])

    def test_static_runtime_audit_rejects_privileged_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/runtime.py"
            source.parent.mkdir(parents=True)
            source.write_text(
                "def safe(payload):\n    return payload.get('question')\n",
                encoding="utf-8",
            )
            protocol = {"control_surface": {"manifest": {"src/runtime.py": "x"}}}
            safe = target._static_source_audit(root, protocol)
            self.assertEqual(safe["privileged_runtime_field_accesses"], [])
            source.write_text(
                "def leaked(payload):\n    return payload.get('category')\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "capability audit failed"):
                target._static_source_audit(root, protocol)

    def test_preactivation_report_authorizes_no_forward(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / target.OUTPUT
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text("{}\n", encoding="utf-8")
            source = root / "src/runtime.py"
            source.parent.mkdir(parents=True)
            source.write_text("VALUE = 1\n", encoding="utf-8")
            protocol = {
                "protocol_id": "v24257_score_first_smoke16_v1",
                "decision_contract_sha256": "d" * 64,
                "control_surface": {
                    "manifest": {"src/runtime.py": "x"},
                    "manifest_sha256": "m" * 64,
                },
            }
            inactive = {"active": False, "ordinary": True}
            with mock.patch.object(
                target, "validate_protocol", return_value=protocol
            ):
                report = target.build_report(
                    root,
                    now=1,
                    proc_root=root / "proc",
                    processes=[],
                    observed_lease=inactive,
                )
        self.assertTrue(report["audit_valid"])
        self.assertTrue(report["authorization"]["activation_publish"])
        self.assertFalse(
            report["authorization"][
                "single_smoke16_launch_after_activation_and_lease_overlay_validation"
            ]
        )
        self.assertFalse(report["authorization"]["official_evaluator_call"])
        self.assertFalse(report["authorization"]["paired_dev64_or_full220_launch"])


if __name__ == "__main__":
    unittest.main()
