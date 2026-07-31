from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.preregister_v24196_capacity_executor import ROOT, build_protocol
from scripts.watch_v24196_capacity_executor import (
    _compatibility_valid,
    _wait_for_compatibility_watcher,
    run_cycle,
)


EMPTY_WORKERS = {
    "present": False,
    "match_count": 0,
    "pids": [],
    "matched_markers": [],
    "command_lines_emitted": False,
}


class WatchV24196CapacityExecutorTests(unittest.TestCase):
    def _run(self, state: Path, **kwargs):
        protocol = build_protocol(ROOT, created_at_unix=1, require_pristine=False)

        def target(_root, _raw, expected, _parent):
            if expected.endswith("watcher_state_v1_20260731.json"):
                return state
            return state.parent / Path(expected).name

        verified = {
            "path": ROOT / "results/synthetic_v24196.json",
            "sha256": "a" * 64,
            "value": protocol,
        }
        with mock.patch(
            "scripts.watch_v24196_capacity_executor.validate_protocol",
            return_value=verified,
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._target",
            side_effect=target,
        ):
            return run_cycle(ROOT, state_path=state, **kwargs)

    def test_pre_release_wait_never_takes_lease_or_constructs_client(self) -> None:
        forbidden = mock.Mock(side_effect=AssertionError("execution surface"))
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "scripts.watch_v24196_capacity_executor._release_pair",
            return_value=None,
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._campaign_terminal",
            return_value=None,
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._active_api_workers",
            return_value=EMPTY_WORKERS,
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._legacy_capacity_watcher",
            return_value={"present": True, "match_count": 1, "pids": [9], "command_lines_emitted": False},
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._activation_summary",
            return_value=None,
        ):
            value = self._run(
                Path(directory) / "state.json",
                now=1,
                lease_factory=forbidden,
                client_factory=forbidden,
                ladder_runner=forbidden,
            )
        self.assertEqual(value["status"], "waiting_for_r1_release")
        self.assertFalse(value["shared_api_lease_acquired"])
        self.assertFalse(value["neutral_capacity_model_api_called"])
        forbidden.assert_not_called()

    def test_healthy_legacy_watcher_blocks_lease_after_all_other_gates(self) -> None:
        forbidden = mock.Mock(side_effect=AssertionError("legacy watcher not preserved"))
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "scripts.watch_v24196_capacity_executor._release_pair",
            return_value={"result_sha256": "r" * 64},
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._campaign_terminal",
            return_value={"phase": "post_gate1_and_leaderboard_handoff", "terminal": True},
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._active_api_workers",
            return_value=EMPTY_WORKERS,
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._legacy_capacity_watcher",
            return_value={"present": True, "match_count": 1, "pids": [9], "command_lines_emitted": False},
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._activation_summary",
            return_value={"sha256": "x" * 64},
        ):
            value = self._run(
                Path(directory) / "state.json",
                now=2,
                lease_factory=forbidden,
                client_factory=forbidden,
                ladder_runner=forbidden,
            )
        self.assertEqual(
            value["status"], "waiting_for_legacy_v24194_watcher_safe_handoff"
        )
        forbidden.assert_not_called()

    def test_missing_activation_blocks_before_legacy_handoff_check(self) -> None:
        forbidden = mock.Mock(side_effect=AssertionError("activation missing"))
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "scripts.watch_v24196_capacity_executor._release_pair",
            return_value={"result_sha256": "r" * 64},
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._campaign_terminal",
            return_value={"terminal": True},
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._active_api_workers",
            return_value=EMPTY_WORKERS,
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._legacy_capacity_watcher",
            return_value={"present": True},
        ), mock.patch(
            "scripts.watch_v24196_capacity_executor._activation_summary",
            return_value=None,
        ):
            value = self._run(
                Path(directory) / "state.json",
                lease_factory=forbidden,
                client_factory=forbidden,
                ladder_runner=forbidden,
            )
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        forbidden.assert_not_called()

    @staticmethod
    def _compatibility(pid: int, created: int = 10) -> dict:
        value = {
            "role": "v24195_lease_owner_compatibility_audit",
            "created_at_unix": created,
            "overall_status": "degraded_forward_healthy_manual_review_only",
            "critical_findings": [],
            "compatibility": {
                "mode": "registered_successor_active",
                "successor_identity_valid": True,
                "successor_identity_findings": [],
                "successor_executor_pid": pid,
                "suppressed_expected_parent_findings": [
                    "shared_api_lease_identity"
                ],
                "unrelated_parent_critical_findings_preserved": True,
            },
            "parent_v24187": {
                "critical_findings": ["shared_api_lease_identity"]
            },
            "authorization": {
                "shared_api_lease_acquire": False,
                "benchmark_forward_or_full220_launch": False,
            },
        }
        from scripts.preregister_v24196_capacity_executor import payload_sha

        value["audit_payload_sha256"] = payload_sha(value)
        return value

    def test_compatibility_requires_only_expected_parent_finding(self) -> None:
        value = self._compatibility(101)
        self.assertTrue(_compatibility_valid(value, executor_pid=101))
        value["parent_v24187"]["critical_findings"].append("unrelated")
        self.assertFalse(_compatibility_valid(value, executor_pid=101))
        value = self._compatibility(101)
        value["compatibility"]["successor_executor_pid"] = 202
        self.assertFalse(_compatibility_valid(value, executor_pid=101))

    def test_watcher_observation_rejects_stale_or_resealed_forgery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "outputs/v24195_lease_owner_compatibility_watcher_state_v1_20260731.json"
            path.parent.mkdir(parents=True)
            value = self._compatibility(101, created=9)
            path.write_text(__import__("json").dumps(value), encoding="utf-8")
            clock = iter([0.0, 1.0])
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                _wait_for_compatibility_watcher(
                    root,
                    acquired_at_unix=10,
                    executor_pid=101,
                    timeout_seconds=1,
                    sleeper=lambda _seconds: None,
                    monotonic=lambda: next(clock),
                )
            forged = self._compatibility(101, created=10)
            forged["compatibility"]["suppressed_expected_parent_findings"] = []
            from scripts.preregister_v24196_capacity_executor import payload_sha

            forged["audit_payload_sha256"] = payload_sha(
                {
                    key: item
                    for key, item in forged.items()
                    if key != "audit_payload_sha256"
                }
            )
            path.write_text(__import__("json").dumps(forged), encoding="utf-8")
            clock = iter([0.0, 1.0])
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                _wait_for_compatibility_watcher(
                    root,
                    acquired_at_unix=10,
                    executor_pid=101,
                    timeout_seconds=1,
                    sleeper=lambda _seconds: None,
                    monotonic=lambda: next(clock),
                )


if __name__ == "__main__":
    unittest.main()
