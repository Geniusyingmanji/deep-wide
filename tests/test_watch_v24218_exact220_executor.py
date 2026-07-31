from __future__ import annotations

import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import watch_v24218_exact220_executor as watch


ROOT = Path(__file__).resolve().parents[1]
VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
        "execution": {"quiet_observations_before_lease": 2},
    },
}
ACTIVATION = {
    "path": str(watch.ACTIVATION),
    "sha256": "a" * 64,
    "watcher_pid": 7,
    "watcher_start_ticks": 9,
}


def parent_state(role: str, status: str, terminal: bool) -> dict:
    value = {
        "role": role,
        "status": status,
        "terminal": terminal,
        "benchmark_forward_or_full220_launch_allowed": False,
    }
    if role == "v24216_package_gate_watcher_state":
        value.update(
            capacity_measurement_allowed=(terminal and status.endswith("go")),
            mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing=False,
        )
    else:
        value.update(
            benchmark_question_prediction_mapping_gold_category_evaluator_score_read=False,
            capacity_report_created=(terminal and status.startswith("complete")),
            capacity_freeze_created=(terminal and status.startswith("complete")),
        )
    value["state_payload_sha256"] = watch.payload_sha256(value)
    return value


class WatchV24218Exact220ExecutorTests(unittest.TestCase):
    def test_repeated_phase_updates_replace_not_nest_state_seal(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "state.json"
            value = {"role": "test"}
            watch._phase(path, value, status="one", reason="first")
            first = value["state_payload_sha256"]
            watch._phase(path, value, status="two", reason="second")
            self.assertNotEqual(value["state_payload_sha256"], first)
            unsigned = dict(value)
            seal = unsigned.pop("state_payload_sha256")
            self.assertEqual(seal, watch.payload_sha256(unsigned))

    def test_package_preterminal_does_not_open_capacity_or_api(self) -> None:
        package = parent_state(
            "v24216_package_gate_watcher_state",
            "waiting_for_v24215_joint_package_terminal",
            False,
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(watch, "_package_parent", return_value=(package, "waiting")), mock.patch.object(
                watch, "_capacity_parent"
            ) as capacity, mock.patch.object(watch, "_active_api_workers") as workers:
                value = watch.run_cycle(ROOT, state_path=state, now=1)
        capacity.assert_not_called()
        workers.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_v24216_package_gate_terminal")
        self.assertFalse(value["capacity_parent_safe_envelope_opened"])
        self.assertFalse(value["benchmark_forward_called"])

    def test_capacity_preterminal_does_not_open_package_bytes_or_api(self) -> None:
        package = parent_state(
            "v24216_package_gate_watcher_state", "complete_package_gate_go", True
        )
        capacity = parent_state(
            "v24217_capacity_successor_watcher_state",
            "waiting_for_second_quiet_observation",
            False,
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(watch, "_package_parent", return_value=(package, "go")), mock.patch.object(
                watch, "_capacity_parent", return_value=(capacity, "waiting")
            ), mock.patch.object(watch, "validate_package_authority") as open_package, mock.patch.object(
                watch, "_active_api_workers"
            ) as workers:
                value = watch.run_cycle(ROOT, state_path=state, now=1)
        open_package.assert_not_called()
        workers.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_v24217_capacity_freeze")
        self.assertFalse(value["candidate_package_opened"])

    def test_execution_start_without_result_is_terminal_no_retry(self) -> None:
        package_state_value = parent_state(
            "v24216_package_gate_watcher_state", "complete_package_gate_go", True
        )
        capacity_state_value = parent_state(
            "v24217_capacity_successor_watcher_state",
            "complete_capacity_recommendation_available",
            True,
        )
        package = {"mode": "selected_joint_candidate"}
        capacity = {"schedule": {"executor_concurrency": 4}}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            start = Path(directory) / "start.json"
            start.write_text("{}", encoding="utf-8")
            with mock.patch.object(watch, "EXECUTION_START", start), mock.patch.object(
                watch, "RESULT", Path(directory) / "result.json"
            ), mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(
                watch, "_package_parent", return_value=(package_state_value, "go")
            ), mock.patch.object(
                watch, "_capacity_parent", return_value=(capacity_state_value, "go")
            ), mock.patch.object(
                watch, "validate_package_authority", return_value=package
            ), mock.patch.object(
                watch, "validate_capacity_authority", return_value=capacity
            ), mock.patch.object(
                watch, "_validate_execution_start", return_value={}
            ), mock.patch.object(watch, "_future_run_absent", return_value=True):
                value = watch.run_cycle(ROOT, state_path=state, now=1)
        self.assertEqual(value["status"], "terminal_incomplete_exact220_attempt_no_retry")
        self.assertTrue(value["terminal"])
        self.assertTrue(value["execution_start_published"])

    def test_start_precedes_executor_and_one_lease_wraps_execution(self) -> None:
        package_state_value = parent_state(
            "v24216_package_gate_watcher_state", "complete_package_gate_go", True
        )
        capacity_state_value = parent_state(
            "v24217_capacity_successor_watcher_state",
            "complete_capacity_recommendation_available",
            True,
        )
        package = {
            "mode": "selected_joint_candidate",
            "package_state": {"path": "package", "sha256": "1" * 64},
            "publication": {"path": "publication", "sha256": "2" * 64},
            "gate_decision": {"path": "gate", "sha256": "3" * 64},
            "source_manifest_sha256": "4" * 64,
        }
        capacity = {
            "state": {"path": "capacity-state", "sha256": "5" * 64},
            "report": {"path": "capacity-report", "sha256": "6" * 64},
            "freeze": {"path": "capacity-freeze", "sha256": "7" * 64},
            "schedule": {"executor_concurrency": 4, "agent_width": 1},
        }
        compatibility = {
            "owner": watch.LEASE_OWNER,
            "purpose": watch.LEASE_PURPOSE,
            "watcher_pid": 7,
            "watcher_start_ticks": 9,
            "owner_purpose_pid_and_lock_holder_exact": True,
            "contents_emitted": False,
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            base = Path(directory)
            state = base / "state.json"
            start = base / "start.json"
            result = base / "result.json"

            @contextlib.contextmanager
            def lease_factory(*_args, **_kwargs):
                yield {"owner": watch.LEASE_OWNER, "purpose": watch.LEASE_PURPOSE, "pid": 7}

            def executor(*_args, **_kwargs):
                self.assertTrue(start.is_file())
                result.write_text("{}", encoding="utf-8")
                return {"selected": 220, "runtime_completed": 200, "runtime_failed": 20}

            with mock.patch.object(watch, "EXECUTION_START", start), mock.patch.object(
                watch, "RESULT", result
            ), mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(
                watch, "_package_parent", return_value=(package_state_value, "go")
            ), mock.patch.object(
                watch, "_capacity_parent", return_value=(capacity_state_value, "go")
            ), mock.patch.object(
                watch, "validate_package_authority", return_value=package
            ), mock.patch.object(
                watch, "validate_capacity_authority", return_value=capacity
            ), mock.patch.object(
                watch,
                "_active_api_workers",
                return_value={
                    "present": False,
                    "match_count": 0,
                    "pids": [],
                    "matched_markers": [],
                    "command_lines_emitted": False,
                },
            ), mock.patch.object(
                watch, "_previous_quiet_streak", return_value=1
            ), mock.patch.object(
                watch, "_future_run_absent", return_value=True
            ), mock.patch.object(
                watch, "_lease_compatibility", return_value=compatibility
            ), mock.patch.object(watch, "file_sha256", return_value="8" * 64):
                value = watch.run_cycle(
                    ROOT,
                    state_path=state,
                    now=1,
                    lease_factory=lease_factory,
                    executor=executor,
                )
        self.assertEqual(value["status"], "complete_exact220_local_result_released_not_sota")
        self.assertTrue(value["execution_start_published"])
        self.assertTrue(value["all_four_shards_exact_terminal"])
        self.assertFalse(value["leaderboard_submission_or_sota_claim"])


if __name__ == "__main__":
    unittest.main()
