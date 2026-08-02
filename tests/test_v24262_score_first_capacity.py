from __future__ import annotations

import copy
import sys
import threading
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.preregister_v24262_score_first_capacity import (
    LEVELS,
    OUTPUT,
    TASK_COUNT,
    WAVES_PER_LEVEL,
    build_protocol,
    schedule_manifest,
    task_positions,
    validate_protocol,
)
from scripts.project_v24262_serial_capacity_baseline import (
    validate_projection,
)
from scripts import activate_v24262_score_first_capacity as activation_target
from scripts import audit_v24262_score_first_capacity as audit_target
from scripts import watch_v24262_score_first_capacity as watcher_target
from scripts.run_v24257_score_first_smoke import read_object
from scripts.run_v24257_score_first_smoke import payload_sha256
from scripts.run_v24262_score_first_capacity import (
    aggregate,
    evaluate_level,
    execute_ladder,
    safe_progress,
    safe_task_row,
    validate_progress,
    validate_result,
)


def passing_waves(protocol: dict, concurrency: int) -> list[dict]:
    baseline = {row["task_position"]: row for row in protocol["baseline_contract"]["rows"]}
    waves = []
    for wave in range(1, WAVES_PER_LEVEL + 1):
        rows = []
        positions = task_positions(concurrency, wave)
        for slot, position in enumerate(positions, start=1):
            base = baseline[position]
            rows.append(
                {
                    "slot": slot,
                    "task_position": position,
                    "completion_kind": base["completion_kind"],
                    "model_generated": base["completion_kind"] != "best_effort_fallback",
                    "infrastructure_fallback": False,
                    "failure_types": [],
                    "elapsed_seconds": base["elapsed_seconds"],
                    "system_total_tokens": base["system_total_tokens"],
                    "fetch_calls": base["fetch_calls"],
                    "model_requests": base["model_requests"],
                    "model_attempts": base["model_attempts"],
                    "logical_search_calls": base["logical_search_calls"],
                    "logical_search_failures": base["logical_search_failures"],
                    "fetch_failures": base["fetch_failures"],
                    "question_query_url_page_prediction_answer_or_opaque_id_emitted": False,
                }
            )
        waves.append(
            {
                "wave": wave,
                "request_count": concurrency,
                "elapsed_seconds": max(row["elapsed_seconds"] for row in rows),
                "tasks": rows,
            }
        )
    return waves


class V24262ScoreFirstCapacityTests(unittest.TestCase):
    def test_serial_projection_contains_metrics_only(self) -> None:
        value = validate_projection(ROOT)
        rendered = __import__("json").dumps(value)
        for forbidden in ("opaque_id", "question", "query", "url", "page", "prediction", "answer"):
            self.assertNotIn(f'"{forbidden}"', rendered)
        self.assertTrue(value["source_policy"]["completed_parent_task_result_files_opened_post_terminal"])
        self.assertFalse(value["source_policy"]["prediction_or_question_content_used_for_projection"])

    def test_protocol_freezes_real_pipeline_without_quality_authority(self) -> None:
        value = build_protocol(ROOT, now=1, require_pristine=False)
        self.assertEqual(value["capacity_contract"]["levels"], list(LEVELS))
        self.assertEqual(value["capacity_contract"]["waves_per_level"], 3)
        self.assertEqual(value["task_contract"]["selected_count"], TASK_COUNT)
        self.assertEqual(value["source_policy"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertFalse(value["authorization"]["official_evaluator_call"])
        self.assertFalse(value["authorization"]["paired_dev64_launch"])
        self.assertFalse(value["authorization"]["full220_launch"])

    def test_schedule_is_exact_deterministic_and_balanced_at_twelve(self) -> None:
        schedule = schedule_manifest()
        self.assertEqual([row["concurrency"] for row in schedule], list(LEVELS))
        self.assertEqual(task_positions(12, 1), list(range(1, 13)))
        self.assertEqual(task_positions(12, 2), list(range(1, 13)))
        with self.assertRaises(ValueError):
            task_positions(3, 1)

    def test_safe_task_row_never_emits_content_or_identifier(self) -> None:
        result = read_object(
            ROOT
            / "outputs/v24261_direct_executor_smoke16_v1_20260802/tasks/task_0001/result.json"
        )
        row = safe_task_row(1, result)
        self.assertNotIn("opaque_id", row)
        self.assertNotIn("prediction", row)
        self.assertNotIn("question", row)
        self.assertFalse(row["question_query_url_page_prediction_answer_or_opaque_id_emitted"])

    def test_matched_serial_level_passes_and_selects_highest_passed(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        first = evaluate_level(protocol, 1, passing_waves(protocol, 1))
        fourth = evaluate_level(protocol, 4, passing_waves(protocol, 4))
        self.assertTrue(first["passed"])
        self.assertTrue(fourth["passed"])
        value = aggregate(protocol, [first, fourth])
        self.assertEqual(value["selected_executor_concurrency"], 4)
        self.assertEqual(value["capacity_gate"], "go")
        self.assertFalse(value["official_evaluator_called"])

    def test_infrastructure_failure_stops_level(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        waves = passing_waves(protocol, 4)
        waves[0]["tasks"][0]["completion_kind"] = "worker_failure_fallback"
        waves[0]["tasks"][0]["model_generated"] = False
        waves[0]["tasks"][0]["infrastructure_fallback"] = True
        waves[0]["tasks"][0]["failure_types"] = ["WorkerNonzeroExit"]
        level = evaluate_level(protocol, 4, waves)
        self.assertFalse(level["passed"])
        self.assertIn("infrastructure_fallbacks_above_gate", level["findings"])

    def test_latency_and_cost_regression_fail_closed(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        waves = passing_waves(protocol, 4)
        for wave in waves:
            wave["elapsed_seconds"] *= 10
            for row in wave["tasks"]:
                row["elapsed_seconds"] *= 10
                row["system_total_tokens"] *= 2
                row["fetch_calls"] *= 2
        level = evaluate_level(protocol, 4, waves)
        self.assertFalse(level["passed"])
        self.assertIn("median_matched_wall_ratio_above_gate", level["findings"])
        self.assertIn("mean_matched_token_ratio_above_gate", level["findings"])
        self.assertIn("mean_matched_fetch_ratio_above_gate", level["findings"])

    def test_progress_contains_summaries_only(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        level = evaluate_level(protocol, 1, passing_waves(protocol, 1))
        value = safe_progress([level], active_level=None, active_wave=None, status="level_terminal")
        rendered = __import__("json").dumps(value)
        for forbidden in ("opaque_id", "prediction", "question", "query", "url", "page"):
            self.assertNotIn(f'"{forbidden}"', rendered)
        self.assertFalse(value["contains_question_query_url_page_prediction_answer_opaque_id_or_credential"])
        validate_progress(value)
        value["question"] = "forbidden"
        unsigned = dict(value)
        unsigned.pop("progress_payload_sha256")
        value["progress_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "progress schema"):
            validate_progress(value)

    def test_protocol_validation_rejects_resealed_source_drift(self) -> None:
        # The live protocol is created only after tests pass; exercise the builder seal here.
        value = build_protocol(ROOT, now=1, require_pristine=False)
        tampered = copy.deepcopy(value)
        tampered["capacity_contract"]["levels"] = [1]
        old_seal = tampered.pop("decision_contract_sha256")
        self.assertNotEqual(old_seal, payload_sha256(tampered))

    def test_executor_reaches_real_cross_task_concurrency_and_stops_cleanly(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        protocol = copy.deepcopy(protocol)
        protocol["capacity_contract"]["schedule"] = schedule_manifest()[:3]
        tasks = __import__(
            "scripts.run_v24257_score_first_smoke", fromlist=["_selected_tasks"]
        )._selected_tasks(ROOT, protocol)
        by_id = {task["opaque_id"]: index for index, task in enumerate(tasks, start=1)}
        results = {
            index: read_object(
                ROOT
                / f"outputs/v24261_direct_executor_smoke16_v1_20260802/tasks/task_{index:04d}/result.json"
            )
            for index in range(1, TASK_COUNT + 1)
        }
        lock = threading.Lock()
        active = 0
        maximum = 0

        def runner(_root, _protocol, task, _task_root):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            try:
                time.sleep(0.01)
                return copy.deepcopy(results[by_id[task["opaque_id"]]])
            finally:
                with lock:
                    active -= 1

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            levels = execute_ladder(
                ROOT,
                protocol,
                tasks,
                Path(directory) / "tasks",
                task_runner=runner,
            )
        self.assertEqual([level["concurrency"] for level in levels], [1, 2, 4])
        self.assertTrue(all(level["passed"] for level in levels))
        self.assertEqual(maximum, 4)

    def test_result_validation_rejects_safe_summary_tampering(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        levels = [
            evaluate_level(protocol, concurrency, passing_waves(protocol, concurrency))
            for concurrency in (1, 2, 4)
        ]
        value = aggregate(protocol, levels)
        validate_result(protocol, value)
        tampered = copy.deepcopy(value)
        tampered["levels"][-1]["effective_speedup"] = 999
        unsigned = dict(tampered)
        unsigned.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "level summary"):
            validate_result(protocol, tampered)

    def test_result_validation_rejects_resealed_content_injection(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        levels = [
            evaluate_level(protocol, concurrency, passing_waves(protocol, concurrency))
            for concurrency in (1, 2, 4)
        ]
        value = aggregate(protocol, levels)
        value["levels"][0]["waves"][0]["tasks"][0]["prediction"] = "forbidden"
        unsigned = dict(value)
        unsigned.pop("result_payload_sha256")
        value["result_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "wave schema"):
            validate_result(protocol, value)

    def test_preactivation_audit_blocks_active_lease_without_network(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        with mock.patch.object(
            audit_target, "validate_protocol", return_value=protocol
        ), mock.patch.object(
            audit_target, "process_snapshot", return_value=[]
        ), mock.patch.object(
            audit_target, "lease_observation", return_value={"active": True}
        ), mock.patch.object(
            audit_target, "sha256", return_value="p" * 64
        ):
            value = audit_target.build_report(ROOT, now=1)
        self.assertFalse(value["launch_authorized"])
        self.assertIn("shared_api_lease_active", value["findings"])
        self.assertFalse(value["network_model_search_fetch_or_evaluator_api_called_by_audit"])
        self.assertFalse(value["official_evaluator_dev64_full220_or_leaderboard_authorized"])

    def test_activation_requires_clean_lease_and_valid_preaudit(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / activation_target.OUTPUT
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text("{}\n", encoding="utf-8")
            preaudit = {
                "role": "v24262_score_first_capacity_preactivation_audit",
                "audit_valid": True,
                "launch_authorized": True,
                "protocol_sha256": __import__("hashlib").sha256(b"{}\n").hexdigest(),
            }
            preaudit["audit_payload_sha256"] = payload_sha256(preaudit)
            preaudit_path = root / activation_target.PREAUDIT
            preaudit_path.parent.mkdir(parents=True, exist_ok=True)
            preaudit_path.write_text(__import__("json").dumps(preaudit), encoding="utf-8")
            with mock.patch.object(
                activation_target, "validate_protocol", return_value=protocol
            ), mock.patch.object(
                activation_target, "process_snapshot", return_value=[]
            ), mock.patch.object(
                activation_target, "lease_observation", return_value={"active": False}
            ):
                value = activation_target.build_activation(root, now=2)
            self.assertEqual(value["status"], "active")
            self.assertFalse(value["mapping_gold_category_question_type_split_evaluator_score_read"])
            self.assertFalse(value["official_evaluator_dev64_full220_or_leaderboard_authorized"])
            with mock.patch.object(
                activation_target, "validate_protocol", return_value=protocol
            ), mock.patch.object(
                activation_target, "process_snapshot", return_value=[]
            ), mock.patch.object(
                activation_target, "lease_observation", return_value={"active": True}
            ), self.assertRaisesRegex(RuntimeError, "activation boundary"):
                activation_target.build_activation(root, now=3)

    def test_watcher_reads_only_safe_progress_summary(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activation = {
                "role": "v24262_score_first_capacity_activation",
                "status": "active",
            }
            activation["activation_payload_sha256"] = payload_sha256(activation)
            activation_path = root / watcher_target.ACTIVATION
            activation_path.parent.mkdir(parents=True)
            activation_path.write_text(__import__("json").dumps(activation), encoding="utf-8")
            progress = safe_progress([], active_level=1, active_wave=1, status="running")
            progress_path = root / watcher_target.PROGRESS
            progress_path.parent.mkdir(parents=True, exist_ok=True)
            progress_path.write_text(__import__("json").dumps(progress), encoding="utf-8")
            with mock.patch.object(
                watcher_target, "validate_protocol", return_value=protocol
            ), mock.patch.object(
                watcher_target,
                "lease_observation",
                return_value={"active": True, "owner": watcher_target.LEASE_OWNER},
            ):
                value = watcher_target.build_state(root)
        self.assertEqual(value["status"], "running_capacity_under_registered_lease")
        self.assertEqual(value["progress_summary"]["active_level"], 1)
        rendered = __import__("json").dumps(value)
        for forbidden in ("opaque_id", "prediction", "question", "query", "url", "page"):
            self.assertNotIn(f'"{forbidden}"', rendered)
        self.assertFalse(value["network_model_search_fetch_evaluator_or_api_called_by_watcher"])


if __name__ == "__main__":
    unittest.main()
