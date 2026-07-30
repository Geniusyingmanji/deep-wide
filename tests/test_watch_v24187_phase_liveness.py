from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.watch_v24187_phase_liveness import _target, run_once


class WatchV24187PhaseLivenessTests(unittest.TestCase):
    def test_run_once_binds_thresholds_and_writes_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = root / "results/protocol.json"
            state = root / "outputs/state.json"
            protocol.parent.mkdir(parents=True)
            protocol.write_text("{}", encoding="utf-8")
            frozen = {
                "path": protocol,
                "sha256": "a" * 64,
                "value": {
                    "decision_contract_sha256": "b" * 64,
                    "control_surface": {"manifest_sha256": "c" * 64},
                    "execution": {
                        "state_path": "outputs/state.json",
                        "state_freshness_seconds": 180,
                        "transition_grace_seconds": 180,
                    },
                },
            }
            report = {
                "artifact_version": 1,
                "role": "v24187_phase_liveness_audit",
                "overall_status": "healthy",
                "current_phase": {"phase": "r1_full220"},
                "critical_findings": [],
                "degraded_findings": [],
            }
            with patch(
                "scripts.watch_v24187_phase_liveness.validate_protocol",
                return_value=frozen,
            ), patch(
                "scripts.watch_v24187_phase_liveness.build_report",
                return_value=dict(report),
            ) as builder:
                value = run_once(
                    root,
                    protocol=protocol,
                    state=state,
                    proc_root=Path("/proc"),
                    now=100,
                )
            builder.assert_called_once_with(
                root,
                now=100,
                freshness_seconds=180,
                transition_grace_seconds=180,
                proc_root=Path("/proc"),
                protocol_record={
                    "path": "results/protocol.json",
                    "sha256": "a" * 64,
                    "decision_contract_sha256": "b" * 64,
                    "control_manifest_sha256": "c" * 64,
                },
            )
            self.assertEqual(json.loads(state.read_text()), value)

    def test_state_escape_and_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outputs").mkdir()
            with self.assertRaises(RuntimeError):
                _target(root, Path("../outside.json"), "outputs/state.json")
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            target = root / "outputs/state.json"
            target.symlink_to(outside)
            with self.assertRaises(RuntimeError):
                _target(root, target, "outputs/state.json")

    def test_watcher_has_no_mutating_or_network_surface(self) -> None:
        source = (
            Path(__file__).parents[1] / "scripts/watch_v24187_phase_liveness.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "ANTHROPIC_API_KEY",
            "TAVILY_API_KEY",
            "subprocess",
            "os.kill",
            "requests.",
            "urllib",
            "socket.",
            "runtime_predictions.jsonl",
            "evaluator_mapping.jsonl",
            "--resume",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
