from __future__ import annotations

import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    POOL_ID,
    payload_sha256 as limiter_payload_sha256,
)
from scripts import activate_v24264_targeted_capacity as activation_target  # noqa: E402
from scripts import audit_v24264_targeted_capacity as audit_target  # noqa: E402
from scripts import run_v24264_targeted_capacity as runner  # noqa: E402
from scripts import watch_v24264_targeted_capacity as watcher_target  # noqa: E402
from scripts.preregister_v24264_targeted_capacity import (  # noqa: E402
    LEVELS,
    MODEL_SLOT_CAP,
    OUTPUT,
    TASK_COUNT,
    WAVES_PER_LEVEL,
    _validate_schedule,
    build_protocol,
    targeted_schedule,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    _selected_tasks,
    payload_sha256,
    read_object,
)


def result(position: int) -> dict:
    return read_object(
        ROOT
        / (
            "outputs/v24261_direct_executor_smoke16_v1_20260802/tasks/"
            f"task_{position:04d}/result.json"
        )
    )


def receipt(acquisitions: int, *, wait: float = 0.0) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24263_global_model_slot_receipt",
        "pool_id": POOL_ID,
        "slot_cap": MODEL_SLOT_CAP,
        "acquisitions": acquisitions,
        "total_wait_seconds": wait,
        "max_wait_seconds": wait,
        "slot_acquisition_counts": [acquisitions, 0],
        "label_blind": True,
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["receipt_payload_sha256"] = limiter_payload_sha256(value)
    return value


def outcome(position: int) -> runner.limited.TaskOutcome:
    value = result(position)
    return runner.limited.TaskOutcome(
        value, receipt(int(value["cost"]["model"]["requests"]))
    )


def passing_waves(protocol: dict, concurrency: int) -> list[dict]:
    baseline = {
        int(row["task_position"]): row
        for row in protocol["baseline_contract"]["rows"]
    }
    schedule = next(
        row
        for row in protocol["capacity_contract"]["schedule"]
        if int(row["concurrency"]) == concurrency
    )
    waves = []
    for wave in schedule["waves"]:
        rows = [
            {
                "slot": slot,
                **runner.safe_task_row(int(position), outcome(int(position))),
            }
            for slot, position in enumerate(wave["task_positions"], start=1)
        ]
        waves.append(
            {
                "wave": int(wave["wave"]),
                "request_count": concurrency,
                "elapsed_seconds": max(
                    float(baseline[int(position)]["elapsed_seconds"])
                    for position in wave["task_positions"]
                ),
                "tasks": rows,
            }
        )
    return waves


class V24264TargetedCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = build_protocol(ROOT, now=1, require_pristine=False)

    def test_schedule_is_exact_four_eight_twelve_and_balanced(self) -> None:
        schedule = targeted_schedule()
        self.assertEqual([row["concurrency"] for row in schedule], [4, 8, 12])
        for level in schedule:
            concurrency = int(level["concurrency"])
            positions = [
                int(position)
                for wave in level["waves"]
                for position in wave["task_positions"]
            ]
            self.assertEqual(len(level["waves"]), WAVES_PER_LEVEL)
            self.assertEqual(len(positions), concurrency * WAVES_PER_LEVEL)
            expected = concurrency * WAVES_PER_LEVEL // TASK_COUNT
            self.assertEqual(
                {position: positions.count(position) for position in range(1, 13)},
                {position: expected for position in range(1, 13)},
            )
        drifted = copy.deepcopy(schedule)
        drifted[0]["waves"][0]["task_positions"][0] = 2
        with self.assertRaisesRegex(RuntimeError, "exposure"):
            _validate_schedule(drifted)

    def test_protocol_retains_limiter_and_label_blind_boundary(self) -> None:
        protocol = self.protocol
        self.assertEqual(protocol["capacity_contract"]["levels"], [4, 8, 12])
        self.assertEqual(protocol["model_slot_contract"]["slot_cap"], 2)
        self.assertEqual(protocol["model_slot_contract"]["pool_id"], POOL_ID)
        self.assertEqual(
            protocol["source_policy"]["runtime_boundary"],
            ["opaque_id", "question"],
        )
        self.assertTrue(
            protocol["capacity_contract"]["gates"][
                "matched_task_wall_ratios_are_diagnostic_only"
            ]
        )
        self.assertFalse(protocol["authorization"]["official_evaluator_call"])
        self.assertFalse(protocol["authorization"]["paired_dev64_launch"])
        self.assertFalse(protocol["authorization"]["full220_launch"])

    def test_task_command_uses_same_child_and_exact_two_slot_pool(self) -> None:
        command = runner.task_command(
            ROOT,
            self.protocol,
            Path("task"),
            Path("result"),
            Path("progress"),
            Path("receipt"),
        )
        self.assertEqual(command[3], str(ROOT / runner.CHILD))
        self.assertEqual(command[command.index("--model-slot-cap") + 1], "2")
        self.assertEqual(
            command[command.index("--model-slot-pool-id") + 1], POOL_ID
        )
        self.assertNotIn("category", command)
        self.assertNotIn("question_type", command)

    def test_four_level_passes_and_executes_each_task_exactly_once(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["capacity_contract"]["schedule"] = protocol[
            "capacity_contract"
        ]["schedule"][:1]
        tasks = _selected_tasks(ROOT, protocol)
        identity = {id(task): index for index, task in enumerate(tasks, start=1)}
        observed: list[int] = []
        lock = threading.Lock()

        def fake_task(_root, _protocol, task, _task_root):
            position = identity[id(task)]
            with lock:
                observed.append(position)
            return outcome(position)

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            task_parent = Path(directory) / "tasks"
            task_parent.mkdir()
            levels = runner.execute_ladder(
                ROOT,
                protocol,
                tasks,
                task_parent,
                task_runner=fake_task,
            )
        self.assertEqual(sorted(observed), list(range(1, 13)))
        self.assertEqual(len(observed), 12)
        self.assertTrue(levels[0]["passed"])

    def test_high_matched_wall_ratio_is_diagnostic_when_absolute_health_passes(self) -> None:
        waves = passing_waves(self.protocol, 4)
        row = next(
            row
            for wave in waves
            for row in wave["tasks"]
            if row["task_position"] == 4
        )
        row["elapsed_seconds"] = 220.0
        waves[0]["elapsed_seconds"] = 220.0
        level = runner.evaluate_level(self.protocol, 4, waves)
        self.assertGreater(level["p95_matched_wall_ratio"], 3.5)
        self.assertLessEqual(level["p95_wall_seconds"], 600)
        self.assertGreaterEqual(level["effective_speedup"], 1.5)
        self.assertTrue(level["matched_task_wall_ratios_diagnostic_only"])
        self.assertTrue(level["passed"], level["findings"])

    def test_model_request_error_and_any_stage_failure_fail_level(self) -> None:
        waves = passing_waves(self.protocol, 4)
        row = waves[0]["tasks"][0]
        row["failure_types"] = ["ModelRequestError"]
        row["model_generated"] = False
        level = runner.evaluate_level(self.protocol, 4, waves)
        self.assertFalse(level["passed"])
        self.assertEqual(level["model_request_error_count"], 1)
        self.assertIn("model_request_errors_above_gate", level["findings"])
        self.assertIn("stage_failures_above_gate", level["findings"])

    def test_invalid_receipt_fails_level(self) -> None:
        waves = passing_waves(self.protocol, 4)
        waves[0]["tasks"][0]["model_slot_receipt_valid"] = False
        level = runner.evaluate_level(self.protocol, 4, waves)
        self.assertFalse(level["passed"])
        self.assertIn("model_slot_receipt_invalid", level["findings"])
        self.assertIn(
            "model_slot_receipt_invalid_above_gate", level["findings"]
        )

    def test_low_effective_speedup_fails_even_with_valid_tasks(self) -> None:
        waves = passing_waves(self.protocol, 4)
        for wave in waves:
            wave["elapsed_seconds"] = 300.0
        level = runner.evaluate_level(self.protocol, 4, waves)
        self.assertLess(level["effective_speedup"], 1.5)
        self.assertFalse(level["passed"])
        self.assertIn("effective_speedup_below_gate", level["findings"])

    def test_absolute_task_tail_above_six_hundred_fails(self) -> None:
        waves = passing_waves(self.protocol, 4)
        waves[0]["tasks"][0]["elapsed_seconds"] = 601.0
        waves[0]["elapsed_seconds"] = 601.0
        level = runner.evaluate_level(self.protocol, 4, waves)
        self.assertFalse(level["passed"])
        self.assertIn("absolute_p95_wall_seconds_above_gate", level["findings"])

    def test_result_rejects_resealed_content_and_schedule_injection(self) -> None:
        level = runner.evaluate_level(
            self.protocol, 4, passing_waves(self.protocol, 4)
        )
        value = runner.aggregate(self.protocol, [copy.deepcopy(level)])
        runner.validate_result(self.protocol, value)
        value["levels"][0]["waves"][0]["tasks"][0]["prediction"] = "forbidden"
        unsigned = dict(value)
        unsigned.pop("result_payload_sha256")
        value["result_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "wave schema"):
            runner.validate_result(self.protocol, value)
        value = runner.aggregate(self.protocol, [copy.deepcopy(level)])
        value["levels"][0]["waves"][0]["tasks"].reverse()
        unsigned = dict(value)
        unsigned.pop("result_payload_sha256")
        value["result_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "schedule"):
            runner.validate_result(self.protocol, value)

    def test_progress_rejects_resealed_content_injection(self) -> None:
        level = runner.evaluate_level(
            self.protocol, 4, passing_waves(self.protocol, 4)
        )
        value = runner.safe_progress(
            [level], active_level=None, active_wave=None, status="level_terminal"
        )
        runner.validate_progress(value)
        value["question"] = "forbidden"
        unsigned = dict(value)
        unsigned.pop("progress_payload_sha256")
        value["progress_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "progress schema"):
            runner.validate_progress(value)

    def test_preactivation_audit_blocks_active_lease_without_network(self) -> None:
        with mock.patch.object(
            audit_target, "validate_protocol", return_value=self.protocol
        ), mock.patch.object(
            audit_target, "process_snapshot", return_value=[]
        ), mock.patch.object(
            audit_target, "lease_observation", return_value={"active": True}
        ), mock.patch.object(audit_target, "sha256", return_value="p" * 64):
            value = audit_target.build_preactivation_report(ROOT, now=1)
        self.assertFalse(value["launch_authorized"])
        self.assertIn("shared_api_lease_active", value["findings"])
        self.assertFalse(
            value["network_model_search_fetch_or_evaluator_api_called_by_audit"]
        )

    def test_activation_requires_valid_audit_and_clean_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / activation_target.OUTPUT
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text("{}\n", encoding="utf-8")
            preaudit = {
                "role": "v24264_targeted_capacity_preactivation_audit",
                "audit_valid": True,
                "launch_authorized": True,
                "protocol_sha256": __import__("hashlib").sha256(b"{}\n").hexdigest(),
                "target_levels": list(LEVELS),
                "global_model_slot_cap": MODEL_SLOT_CAP,
            }
            preaudit["audit_payload_sha256"] = payload_sha256(preaudit)
            path = root / activation_target.PREAUDIT
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(preaudit), encoding="utf-8")
            with mock.patch.object(
                activation_target, "validate_protocol", return_value=self.protocol
            ), mock.patch.object(
                activation_target, "process_snapshot", return_value=[]
            ), mock.patch.object(
                activation_target,
                "lease_observation",
                return_value={"active": False},
            ):
                value = activation_target.build_activation(root, now=2)
            self.assertEqual(value["target_levels"], [4, 8, 12])
            self.assertEqual(value["global_model_slot_cap"], 2)
            with mock.patch.object(
                activation_target, "validate_protocol", return_value=self.protocol
            ), mock.patch.object(
                activation_target, "process_snapshot", return_value=[]
            ), mock.patch.object(
                activation_target,
                "lease_observation",
                return_value={"active": True},
            ), self.assertRaisesRegex(RuntimeError, "activation boundary"):
                activation_target.build_activation(root, now=3)

    def test_watcher_reads_only_content_free_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activation = {
                "role": "v24264_targeted_capacity_activation",
                "status": "active",
            }
            activation["activation_payload_sha256"] = payload_sha256(activation)
            path = root / watcher_target.ACTIVATION
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(activation), encoding="utf-8")
            progress = runner.safe_progress(
                [], active_level=4, active_wave=1, status="running"
            )
            progress_path = root / watcher_target.PROGRESS
            progress_path.parent.mkdir(parents=True, exist_ok=True)
            progress_path.write_text(json.dumps(progress), encoding="utf-8")
            with mock.patch.object(
                watcher_target, "validate_protocol", return_value=self.protocol
            ), mock.patch.object(
                watcher_target,
                "lease_observation",
                return_value={
                    "active": True,
                    "owner": watcher_target.LEASE_OWNER,
                },
            ):
                value = watcher_target.build_state(root)
        self.assertEqual(value["status"], "running_capacity_under_registered_lease")
        rendered = json.dumps(value)
        for forbidden in ("opaque_id", "prediction", "question", "query", "url", "page"):
            self.assertNotIn(f'"{forbidden}"', rendered)
        self.assertFalse(
            value["network_model_search_fetch_evaluator_or_api_called_by_watcher"]
        )

    def test_postresult_audit_requires_runner_child_watcher_and_lease_closure(self) -> None:
        level = runner.evaluate_level(
            self.protocol, 4, passing_waves(self.protocol, 4)
        )
        result_value = runner.aggregate(self.protocol, [level])
        sealed = [
            {"launch_authorized": True},
            {"status": "active"},
            {"api_called_before_execution_start": False},
        ]
        common = (
            mock.patch.object(
                audit_target, "validate_protocol", return_value=self.protocol
            ),
            mock.patch.object(audit_target, "_sealed_file", side_effect=sealed),
            mock.patch.object(audit_target, "read_object", return_value=result_value),
            mock.patch.object(audit_target, "validate_result"),
            mock.patch.object(audit_target, "process_snapshot", return_value=[]),
            mock.patch.object(
                audit_target, "lease_observation", return_value={"active": False}
            ),
            mock.patch.object(audit_target, "sha256", return_value="a" * 64),
        )
        with common[0], common[1], common[2], common[3], common[4], common[5], common[6], mock.patch.object(
            audit_target,
            "_matching",
            side_effect=lambda _rows, marker: (
                [123] if marker == audit_target.WATCHER_MARKER else []
            ),
        ):
            blocked = audit_target.build_postresult_report(ROOT, now=1)
        self.assertFalse(blocked["audit_valid"])
        self.assertTrue(
            blocked["execution_closure"]["watcher_process_present_after_result"]
        )
        sealed = [
            {"launch_authorized": True},
            {"status": "active"},
            {"api_called_before_execution_start": False},
        ]
        common = (
            mock.patch.object(
                audit_target, "validate_protocol", return_value=self.protocol
            ),
            mock.patch.object(audit_target, "_sealed_file", side_effect=sealed),
            mock.patch.object(audit_target, "read_object", return_value=result_value),
            mock.patch.object(audit_target, "validate_result"),
            mock.patch.object(audit_target, "process_snapshot", return_value=[]),
            mock.patch.object(
                audit_target, "lease_observation", return_value={"active": False}
            ),
            mock.patch.object(audit_target, "sha256", return_value="a" * 64),
        )
        with common[0], common[1], common[2], common[3], common[4], common[5], common[6], mock.patch.object(
            audit_target, "_matching", return_value=[]
        ):
            closed = audit_target.build_postresult_report(ROOT, now=1)
        self.assertTrue(closed["audit_valid"])
        self.assertTrue(
            closed["authorization"]["paired_dev64_successor_design"]
        )
        self.assertFalse(closed["authorization"]["paired_dev64_launch"])


if __name__ == "__main__":
    unittest.main()
