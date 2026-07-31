from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from deepwide_agent.v24194_capacity_ladder import (
    PROBE_EXPECTED_OUTPUT,
    PROBE_INPUT_UTF8_BYTES,
    ProbeSettings,
    payload_sha256,
    run_capacity_ladder,
)
from scripts.preregister_v24194_capacity_ladder import ROOT
from scripts.preregister_v24194_capacity_ladder import build_protocol
from scripts.watch_v24194_capacity_ladder import _validate_freeze, run_cycle
from deepwide_agent.v24194_capacity_ladder import build_capacity_freeze


class WatchV24194CapacityLadderTests(unittest.TestCase):
    @staticmethod
    def _valid_report() -> dict:
        class Client:
            def __init__(self) -> None:
                self.lock = threading.Lock()

            def complete(self, system, user, *, max_output_tokens):
                return SimpleNamespace(
                    text=PROBE_EXPECTED_OUTPUT,
                    attempts=1,
                    output_truncated=False,
                    input_utf8_bytes=len((system + user).encode("utf-8")),
                    request_body_bytes=PROBE_INPUT_UTF8_BYTES + 1024,
                    max_output_tokens=max_output_tokens,
                )

        return run_capacity_ladder(Client(), settings=ProbeSettings())

    def _run(self, state: Path, **kwargs):
        protocol = build_protocol(ROOT, created_at_unix=1, require_pristine=False)

        def target(_root, _raw, expected, _parent):
            if expected.endswith("watcher_state_v1_20260731.json"):
                return state
            return state.parent / Path(expected).name

        verified = {"path": ROOT / "results/synthetic_v24194.json", "sha256": "a" * 64, "value": protocol}
        with mock.patch(
            "scripts.watch_v24194_capacity_ladder.validate_protocol",
            return_value=verified,
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._target",
            side_effect=target,
        ):
            return run_cycle(ROOT, state_path=state, **kwargs)

    def test_live_r1_wait_never_constructs_client_or_takes_lease(self) -> None:
        def forbidden(*_args, **_kwargs):
            raise AssertionError("pre-release wait touched an execution surface")

        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            value = self._run(
                state,
                now=1,
                lease_factory=forbidden,
                client_factory=forbidden,
                ladder_runner=forbidden,
            )
        self.assertEqual(value["status"], "waiting_for_r1_release")
        self.assertFalse(value["shared_api_lease_acquired"])
        self.assertFalse(value["neutral_capacity_model_api_called"])
        self.assertFalse(value["full220_launch_allowed"])

    def test_campaign_not_terminal_blocks_execution(self) -> None:
        def forbidden(*_args, **_kwargs):
            raise AssertionError("campaign wait touched an execution surface")

        release = {"result_sha256": "a" * 64}
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "scripts.watch_v24194_capacity_ladder._release_pair",
            return_value=release,
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._campaign_terminal",
            return_value=None,
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._active_api_workers",
            return_value={"present": False, "match_count": 0, "pids": [], "matched_markers": [], "command_lines_emitted": False},
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._execution_activation",
            return_value=None,
        ):
            value = self._run(
                Path(directory) / "state.json",
                now=2,
                lease_factory=forbidden,
                client_factory=forbidden,
                ladder_runner=forbidden,
            )
        self.assertEqual(value["status"], "waiting_for_quality_campaign_terminal")

    def test_missing_execution_activation_blocks_after_campaign_terminal(self) -> None:
        def forbidden(*_args, **_kwargs):
            raise AssertionError("activation wait touched an execution surface")

        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "scripts.watch_v24194_capacity_ladder._release_pair",
            return_value={"result_sha256": "a" * 64},
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._campaign_terminal",
            return_value={"phase": "post_gate1_and_leaderboard_handoff", "terminal": True},
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._active_api_workers",
            return_value={"present": False, "match_count": 0, "pids": [], "matched_markers": [], "command_lines_emitted": False},
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._execution_activation",
            return_value=None,
        ):
            value = self._run(
                Path(directory) / "state.json",
                now=3,
                lease_factory=forbidden,
                client_factory=forbidden,
                ladder_runner=forbidden,
            )
        self.assertEqual(value["status"], "waiting_for_execution_activation")

    def test_api_worker_resets_quiet_streak(self) -> None:
        def forbidden(*_args, **_kwargs):
            raise AssertionError("worker wait touched an execution surface")

        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "scripts.watch_v24194_capacity_ladder._release_pair",
            return_value={"result_sha256": "a" * 64},
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._campaign_terminal",
            return_value={"phase": "post_gate1_and_leaderboard_handoff", "terminal": True},
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._active_api_workers",
            return_value={"present": True, "match_count": 1, "pids": [9], "matched_markers": ["scripts/run_deepwide_agent.py"], "command_lines_emitted": False},
        ), mock.patch(
            "scripts.watch_v24194_capacity_ladder._execution_activation",
            return_value={"sha256": "b" * 64},
        ):
            value = self._run(
                Path(directory) / "state.json",
                now=4,
                lease_factory=forbidden,
                client_factory=forbidden,
                ladder_runner=forbidden,
            )
        self.assertEqual(value["status"], "waiting_for_api_workers_to_exit")
        self.assertEqual(value["consecutive_quiet_observations"], 0)

    def test_sealed_report_without_freeze_recovers_without_reprobe(self) -> None:
        release = {"result_sha256": "a" * 64}
        campaign = {"phase": "post_gate1_and_leaderboard_handoff", "terminal": True}
        activation = {"sha256": "b" * 64}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state.json"
            report_path = root / "v24194_capacity_ladder_report_v1_20260731.json"
            freeze_path = root / "v24194_next_fresh_all220_capacity_freeze_v1_20260731.json"
            report = self._valid_report()
            report.update(
                protocol={"path": "results/v24194_capacity_ladder_preregistration_v1_20260731.json", "sha256": "a" * 64},
                r1_release=release,
                quality_campaign_terminal=campaign,
                execution_activation=activation,
                shared_api_lease_owner="v24194_neutral_gpt56_capacity_ladder_v1",
                shared_api_lease_acquired=True,
                created_at_unix=5,
            )
            report["report_payload_sha256"] = payload_sha256(report)
            report_path.write_text(__import__("json").dumps(report))

            def target(_root, _raw, expected, _parent):
                if expected.endswith("watcher_state_v1_20260731.json"):
                    return state
                if expected.endswith("capacity_ladder_report_v1_20260731.json"):
                    return report_path
                return freeze_path

            protocol = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
            verified = {"path": ROOT / "results/synthetic_v24194.json", "sha256": "a" * 64, "value": protocol}
            forbidden = mock.Mock(side_effect=AssertionError("reprobe"))
            with mock.patch(
                "scripts.watch_v24194_capacity_ladder.validate_protocol",
                return_value=verified,
            ), mock.patch(
                "scripts.watch_v24194_capacity_ladder._target",
                side_effect=target,
            ), mock.patch(
                "scripts.watch_v24194_capacity_ladder._release_pair",
                return_value=release,
            ), mock.patch(
                "scripts.watch_v24194_capacity_ladder._campaign_terminal",
                return_value=campaign,
            ), mock.patch(
                "scripts.watch_v24194_capacity_ladder._active_api_workers",
                return_value={"present": False, "match_count": 0, "pids": [], "matched_markers": [], "command_lines_emitted": False},
            ), mock.patch(
                "scripts.watch_v24194_capacity_ladder._execution_activation",
                return_value=activation,
            ):
                value = run_cycle(
                    ROOT,
                    state_path=state,
                    now=5,
                    lease_factory=forbidden,
                    client_factory=forbidden,
                    ladder_runner=forbidden,
                )
            self.assertEqual(value["status"], "complete_capacity_recommendation_available")
            self.assertIn("recovered_freeze", value["reason"])
            self.assertTrue(freeze_path.is_file())
            forbidden.assert_not_called()

    def test_freeze_reseal_cannot_override_recomputed_capacity(self) -> None:
        report = self._valid_report()
        freeze = build_capacity_freeze(
            report,
            report_path="results/v24194_capacity_ladder_report_v1_20260731.json",
            report_sha256="c" * 64,
            protocol_path="results/v24194_capacity_ladder_preregistration_v1_20260731.json",
            protocol_sha256="a" * 64,
        )
        freeze["parallel_shard_cap"] = 99
        freeze["freeze_payload_sha256"] = payload_sha256(freeze)
        with self.assertRaisesRegex(RuntimeError, "freeze is invalid"):
            _validate_freeze(
                freeze,
                report=report,
                report_sha="c" * 64,
                protocol_sha="a" * 64,
            )


if __name__ == "__main__":
    unittest.main()
