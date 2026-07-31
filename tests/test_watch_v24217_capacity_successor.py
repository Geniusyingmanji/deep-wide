from __future__ import annotations

import contextlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from deepwide_agent.v24194_capacity_ladder import (
    PROBE_EXPECTED_OUTPUT,
    PROBE_INPUT_UTF8_BYTES,
    ProbeSettings,
)
from scripts import watch_v24217_capacity_successor as watch


ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ProbeSettings(
    levels=(1,),
    waves_per_level=2,
    absolute_latency_ceiling_seconds=999,
    baseline_p95_multiplier=999,
    baseline_median_multiplier=999,
)
VERIFIED = {
    "sha256": "e" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
        "execution": {"quiet_observations_before_lease": 1},
        "neutral_capacity_contract": {
            "capacity_contract": {
                "settings": SETTINGS.as_dict(),
                "endpoint": "http://127.0.0.1:9878/responses",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "service_tier": "priority",
                "request_timeout_seconds": 180,
                "client_max_retries": 1,
            }
        },
        "safe_wait_boundary": {
            "legacy_capacity": {
                "v24194": {"pid": 1, "start_ticks": 2},
                "v24196": {"pid": 3, "start_ticks": 4},
            }
        },
    },
}
ACTIVATION = {
    "path": str(watch.ACTIVATION),
    "sha256": "a" * 64,
    "watcher_pid": 7,
    "watcher_start_ticks": 9,
}
LEGACY = {
    "v24194_pid_start_ticks_exact": True,
    "v24196_pid_start_ticks_exact": True,
    "both_legacy_watchers_terminal_false": True,
    "both_legacy_watchers_shared_lease_and_api_false": True,
    "legacy_execution_activation_reports_and_freezes_absent": True,
    "contents_emitted": False,
}


def parent(status: str, terminal: bool, allowed: bool) -> dict:
    return {
        "status": status,
        "terminal": terminal,
        "capacity_measurement_allowed": allowed,
        "all220_freeze_design_allowed": allowed,
    }


class FakeClient:
    def complete(self, system, user, *, max_output_tokens):
        return SimpleNamespace(
            text=PROBE_EXPECTED_OUTPUT,
            attempts=1,
            output_truncated=False,
            input_utf8_bytes=len((system + user).encode("utf-8")),
            request_body_bytes=PROBE_INPUT_UTF8_BYTES + 100,
            max_output_tokens=max_output_tokens,
        )


class WatchV24217CapacitySuccessorTests(unittest.TestCase):
    def test_preterminal_never_opens_legacy_or_client(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(
                watch,
                "_parent",
                return_value=(
                    parent("waiting_for_v24215_joint_package_terminal", False, False),
                    "waiting",
                ),
            ), mock.patch.object(watch, "_legacy_boundary") as legacy, mock.patch.object(
                watch, "ResponsesClient"
            ) as client:
                value = watch.run_cycle(ROOT, state_path=state, now=1)
        legacy.assert_not_called()
        client.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_v24216_package_gate_terminal")
        self.assertFalse(value["neutral_capacity_model_api_called"])

    def test_parent_no_go_is_terminal_without_api(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(
                watch,
                "_parent",
                return_value=(parent("complete_package_gate_no_go", True, False), "no_go"),
            ), mock.patch.object(watch, "_legacy_boundary") as legacy:
                value = watch.run_cycle(ROOT, state_path=state, now=1)
        legacy.assert_not_called()
        self.assertEqual(value["status"], "terminal_parent_package_gate_no_go")
        self.assertTrue(value["terminal"])
        self.assertFalse(value["neutral_capacity_model_api_called"])

    def test_execution_start_without_report_is_terminal_no_retry(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            start = Path(directory) / "start.json"
            start.write_text("{}", encoding="utf-8")
            with mock.patch.object(watch, "EXECUTION_START", start), mock.patch.object(
                watch, "REPORT", Path(directory) / "report.json"
            ), mock.patch.object(watch, "FREEZE", Path(directory) / "freeze.json"), mock.patch.object(
                watch, "validate_protocol", return_value=VERIFIED
            ), mock.patch.object(watch, "_activation", return_value=ACTIVATION), mock.patch.object(
                watch,
                "_parent",
                return_value=(parent("complete_package_gate_go", True, True), "go"),
            ), mock.patch.object(watch, "_legacy_boundary", return_value=LEGACY), mock.patch.object(
                watch,
                "_validate_execution_start",
                return_value={"parent_package_gate": {}, "shared_api_lease": {}},
            ), mock.patch.object(watch, "ResponsesClient") as client:
                value = watch.run_cycle(ROOT, state_path=state, now=1)
        client.assert_not_called()
        self.assertEqual(value["status"], "terminal_incomplete_capacity_attempt_no_retry")
        self.assertTrue(value["terminal"])

    def test_existing_report_must_match_live_execution_start(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            start = Path(directory) / "start.json"
            report = Path(directory) / "report.json"
            freeze = Path(directory) / "freeze.json"
            start.write_text("{}", encoding="utf-8")
            report.write_text("{}", encoding="utf-8")
            go = parent("complete_package_gate_go", True, True)
            sealed_report = {
                "parent_package_gate": {"sha256": "wrong"},
                "execution_activation": {
                    "path": str(watch.ACTIVATION),
                    "sha256": ACTIVATION["sha256"],
                },
                "shared_api_lease": {},
                "created_at_unix": 2,
            }
            sealed_start = {
                "parent_package_gate": {"sha256": "right"},
                "shared_api_lease": {},
                "created_at_unix": 1,
            }
            with mock.patch.object(watch, "EXECUTION_START", start), mock.patch.object(
                watch, "REPORT", report
            ), mock.patch.object(watch, "FREEZE", freeze), mock.patch.object(
                watch, "validate_protocol", return_value=VERIFIED
            ), mock.patch.object(watch, "_activation", return_value=ACTIVATION), mock.patch.object(
                watch, "_parent", return_value=(go, "go")
            ), mock.patch.object(
                watch, "_legacy_boundary", return_value=LEGACY
            ), mock.patch.object(
                watch, "read_object", side_effect=lambda path: sealed_report if path == report else {}
            ), mock.patch.object(
                watch, "validate_report", return_value={"selected": 1}
            ), mock.patch.object(
                watch, "_validate_execution_start", return_value=sealed_start
            ):
                with self.assertRaisesRegex(RuntimeError, "live binding"):
                    watch.run_cycle(ROOT, state_path=state, now=3)

    def test_start_receipt_precedes_client_construction(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            base = Path(directory)
            state = base / "state.json"
            start = base / "start.json"
            report = base / "report.json"
            freeze = base / "freeze.json"

            @contextlib.contextmanager
            def lease_factory(*_args, **_kwargs):
                yield {"owner": watch.LEASE_OWNER, "purpose": watch.LEASE_PURPOSE, "pid": 7}

            def client_factory(*_args, **_kwargs):
                self.assertTrue(start.is_file())
                return FakeClient()

            compatibility = {
                "owner": watch.LEASE_OWNER,
                "purpose": watch.LEASE_PURPOSE,
                "watcher_pid": 7,
                "watcher_start_ticks": 9,
                "owner_purpose_pid_and_lock_holder_exact": True,
                "parent_expected_findings": ["shared_api_lease_identity"],
                "compatibility_expected_findings": [
                    "shared_api_lease_identity",
                    "v24195:unknown_lease_owner",
                ],
                "unrelated_findings": [],
                "contents_emitted": False,
            }
            go = parent("complete_package_gate_go", True, True)
            with mock.patch.object(watch, "EXECUTION_START", start), mock.patch.object(
                watch, "REPORT", report
            ), mock.patch.object(watch, "FREEZE", freeze), mock.patch.object(
                watch, "validate_protocol", return_value=VERIFIED
            ), mock.patch.object(watch, "_activation", return_value=ACTIVATION), mock.patch.object(
                watch, "_parent", return_value=(go, "go")
            ), mock.patch.object(
                watch, "_legacy_boundary", return_value=LEGACY
            ), mock.patch.object(
                watch,
                "_active_api_workers",
                return_value={"present": False, "match_count": 0, "pids": [], "matched_markers": [], "command_lines_emitted": False},
            ), mock.patch.object(
                watch, "_lease_compatibility", return_value=compatibility
            ):
                value = watch.run_cycle(
                    ROOT,
                    state_path=state,
                    now=1,
                    lease_factory=lease_factory,
                    client_factory=client_factory,
                )
                self.assertEqual(
                    value["status"], "complete_capacity_recommendation_available"
                )
                self.assertTrue(start.is_file())
                self.assertTrue(report.is_file())
                self.assertTrue(freeze.is_file())
                self.assertLessEqual(start.stat().st_mtime_ns, report.stat().st_mtime_ns)
                self.assertLessEqual(report.stat().st_mtime_ns, freeze.stat().st_mtime_ns)
                self.assertFalse(
                    value["benchmark_forward_or_full220_launch_allowed"]
                )


if __name__ == "__main__":
    unittest.main()
