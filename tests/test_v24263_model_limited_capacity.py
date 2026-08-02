from __future__ import annotations

import copy
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

from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    POOL_ID,
    payload_sha256 as limiter_payload_sha256,
)
from scripts.preregister_v24263_model_limited_capacity import (  # noqa: E402
    MODEL_SLOT_CAP,
    OUTPUT,
    ROOT,
    build_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    _selected_tasks,
    payload_sha256,
    read_object,
)
from scripts import run_v24263_model_limited_capacity as runner  # noqa: E402
from scripts import activate_v24263_model_limited_capacity as activation_target  # noqa: E402
from scripts import audit_v24263_model_limited_capacity as audit_target  # noqa: E402
from scripts import watch_v24263_model_limited_capacity as watcher_target  # noqa: E402


def result(position: int) -> dict:
    return read_object(
        ROOT
        / f"outputs/v24261_direct_executor_smoke16_v1_20260802/tasks/task_{position:04d}/result.json"
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


def outcome(position: int, *, wait: float = 0.0) -> runner.TaskOutcome:
    value = result(position)
    requests = int(value["cost"]["model"]["requests"])
    return runner.TaskOutcome(value, receipt(requests, wait=wait))


def passing_waves(protocol: dict, concurrency: int) -> list[dict]:
    waves = []
    schedule = next(
        level
        for level in protocol["capacity_contract"]["schedule"]
        if level["concurrency"] == concurrency
    )
    for wave in schedule["waves"]:
        rows = []
        for slot, position in enumerate(wave["task_positions"], start=1):
            rows.append({"slot": slot, **runner.safe_task_row(position, outcome(position))})
        baseline = {
            row["task_position"]: row
            for row in protocol["baseline_contract"]["rows"]
        }
        waves.append(
            {
                "wave": wave["wave"],
                "request_count": concurrency,
                "elapsed_seconds": max(
                    float(baseline[position]["elapsed_seconds"])
                    for position in wave["task_positions"]
                ),
                "tasks": rows,
            }
        )
    return waves


class V24263ModelLimitedCapacityTests(unittest.TestCase):
    def test_protocol_is_single_change_bound_to_parent_failure(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        self.assertEqual(protocol["single_change"]["global_model_request_concurrency_cap"], 2)
        self.assertTrue(protocol["single_change"]["search_and_fetch_outside_model_lock"])
        self.assertTrue(protocol["single_change"]["model_prompt_provider_retry_search_fetch_task_selection_and_limits_unchanged"])
        self.assertEqual(protocol["parents"]["concurrency_four_model_request_errors"], 6)
        self.assertEqual(protocol["parents"]["concurrency_four_search_failures"], 0)
        self.assertFalse(protocol["authorization"]["official_evaluator_call"])
        self.assertFalse(protocol["authorization"]["paired_dev64_launch"])
        self.assertFalse(protocol["authorization"]["full220_launch"])

    def test_task_command_changes_child_and_adds_exact_slot_contract(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        paths = [Path("task"), Path("result"), Path("progress")]
        command = runner.task_command(
            ROOT, protocol, *paths, Path("receipt")
        )
        self.assertEqual(command[3], str(ROOT / runner.CHILD))
        self.assertEqual(command.count("--model-slot-cap"), 1)
        self.assertEqual(command[command.index("--model-slot-cap") + 1], "2")
        self.assertEqual(
            command[command.index("--model-slot-pool-id") + 1], POOL_ID
        )
        self.assertNotIn("category", command)
        self.assertNotIn("question_type", command)

    def test_safe_row_accepts_matching_receipt_and_emits_no_content(self) -> None:
        row = runner.safe_task_row(1, outcome(1, wait=1.25))
        self.assertTrue(row["model_slot_receipt_valid"])
        self.assertEqual(row["model_slot_acquisitions"], row["model_requests"])
        self.assertEqual(row["model_slot_total_wait_seconds"], 1.25)
        self.assertNotIn("opaque_id", row)
        self.assertNotIn("prediction", row)
        self.assertNotIn("question", row)

    def test_missing_or_mismatched_receipt_is_infrastructure_failure(self) -> None:
        missing = runner.safe_task_row(1, runner.TaskOutcome(result(1), None))
        self.assertFalse(missing["model_slot_receipt_valid"])
        self.assertTrue(missing["infrastructure_fallback"])
        self.assertFalse(missing["model_generated"])
        self.assertIn("ModelSlotReceiptInvalid", missing["failure_types"])
        wrong = runner.TaskOutcome(result(1), receipt(1))
        row = runner.safe_task_row(1, wrong)
        self.assertFalse(row["model_slot_receipt_valid"])

    def test_level_aggregates_slot_wait_and_counts(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        waves = passing_waves(protocol, 2)
        level = runner.evaluate_level(protocol, 2, waves)
        expected = sum(row["model_requests"] for wave in waves for row in wave["tasks"])
        self.assertTrue(level["passed"])
        self.assertEqual(level["model_slot_acquisitions"], expected)
        self.assertEqual(sum(level["model_slot_acquisition_counts"]), expected)
        self.assertEqual(level["model_slot_receipt_invalid_count"], 0)

    def test_invalid_receipt_fails_level_even_if_prediction_is_model_generated(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        waves = passing_waves(protocol, 2)
        row = waves[0]["tasks"][0]
        row["model_slot_receipt_valid"] = False
        row["infrastructure_fallback"] = True
        row["model_generated"] = False
        row["failure_types"] = ["ModelSlotReceiptInvalid"]
        level = runner.evaluate_level(protocol, 2, waves)
        self.assertFalse(level["passed"])
        self.assertIn("model_slot_receipt_invalid", level["findings"])

    def test_result_validation_rejects_resealed_content_injection(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        levels = [
            runner.evaluate_level(protocol, concurrency, passing_waves(protocol, concurrency))
            for concurrency in (1, 2, 4)
        ]
        value = runner.aggregate(protocol, levels)
        runner.validate_result(protocol, value)
        value["levels"][0]["waves"][0]["tasks"][0]["prediction"] = "forbidden"
        unsigned = dict(value)
        unsigned.pop("result_payload_sha256")
        value["result_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "wave schema"):
            runner.validate_result(protocol, value)

    def test_progress_contains_limiter_summary_only(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        level = runner.evaluate_level(protocol, 1, passing_waves(protocol, 1))
        value = runner.safe_progress(
            [level], active_level=None, active_wave=None, status="level_terminal"
        )
        runner.validate_progress(value)
        rendered = __import__("json").dumps(value)
        for forbidden in ("opaque_id", "prediction", "question", "query", "url", "page"):
            self.assertNotIn(f'"{forbidden}"', rendered)
        self.assertEqual(value["level_summaries"][0]["model_slot_receipt_invalid_count"], 0)

    def test_fake_nonzero_child_returns_fail_closed_outcome(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        tasks = _selected_tasks(ROOT, protocol)

        class Process:
            returncode = 1
            pid = 123

            def wait(self, timeout=None):
                return 1

        with tempfile.TemporaryDirectory(dir=ROOT) as directory, mock.patch.object(
            runner.executor61.scientific.parent, "_child_env", return_value={}
        ):
            value = runner.run_one_task(
                ROOT,
                protocol,
                tasks[0],
                Path(directory) / "task",
                popen=lambda *_args, **_kwargs: Process(),
            )
        self.assertEqual(value.result["completion_kind"], "worker_failure_fallback")
        self.assertIsNone(value.receipt)

    def test_parent_accepts_exact_receipt_and_rejects_missing_receipt(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        tasks = _selected_tasks(ROOT, protocol)

        class Process:
            returncode = 0
            pid = 123

            def wait(self, timeout=None):
                return 0

        def popen_with_receipt(command, **_kwargs):
            result_path = Path(command[command.index("--result") + 1])
            receipt_path = Path(
                command[command.index("--model-slot-receipt") + 1]
            )
            result_path.write_text(
                __import__("json").dumps(result(1)), encoding="utf-8"
            )
            receipt_path.write_text(
                __import__("json").dumps(receipt(2)), encoding="utf-8"
            )
            return Process()

        def popen_without_receipt(command, **_kwargs):
            result_path = Path(command[command.index("--result") + 1])
            result_path.write_text(
                __import__("json").dumps(result(1)), encoding="utf-8"
            )
            return Process()

        with tempfile.TemporaryDirectory(dir=ROOT) as directory, mock.patch.object(
            runner.executor61.scientific.parent, "_child_env", return_value={}
        ):
            accepted = runner.run_one_task(
                ROOT,
                protocol,
                tasks[0],
                Path(directory) / "accepted",
                popen=popen_with_receipt,
            )
            rejected = runner.run_one_task(
                ROOT,
                protocol,
                tasks[0],
                Path(directory) / "rejected",
                popen=popen_without_receipt,
            )
        self.assertEqual(accepted.result["completion_kind"], "normalized_primary")
        self.assertIsNotNone(accepted.receipt)
        self.assertEqual(rejected.result["completion_kind"], "worker_failure_fallback")
        self.assertEqual(rejected.result["failures"][0]["type"], "ModelSlotReceiptInvalid")
        self.assertIsNone(rejected.receipt)

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
        self.assertEqual(value["global_model_slot_cap"], 2)
        self.assertFalse(
            value["network_model_search_fetch_or_evaluator_api_called_by_audit"]
        )
        self.assertFalse(
            value["official_evaluator_dev64_full220_or_leaderboard_authorized"]
        )

    def test_activation_requires_valid_preaudit_and_clean_lease(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / activation_target.OUTPUT
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text("{}\n", encoding="utf-8")
            preaudit = {
                "role": "v24263_model_limited_capacity_preactivation_audit",
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
            self.assertEqual(value["global_model_slot_cap"], 2)
            self.assertFalse(value["mapping_gold_category_question_type_split_evaluator_score_read"])
            with mock.patch.object(
                activation_target, "validate_protocol", return_value=protocol
            ), mock.patch.object(
                activation_target, "process_snapshot", return_value=[]
            ), mock.patch.object(
                activation_target, "lease_observation", return_value={"active": True}
            ), self.assertRaisesRegex(RuntimeError, "activation boundary"):
                activation_target.build_activation(root, now=3)

    def test_watcher_reads_only_limiter_progress_summary(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activation = {
                "role": "v24263_model_limited_capacity_activation",
                "status": "active",
            }
            activation["activation_payload_sha256"] = payload_sha256(activation)
            activation_path = root / watcher_target.ACTIVATION
            activation_path.parent.mkdir(parents=True)
            activation_path.write_text(__import__("json").dumps(activation), encoding="utf-8")
            progress = runner.safe_progress(
                [], active_level=4, active_wave=1, status="running"
            )
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
        rendered = __import__("json").dumps(value)
        for forbidden in ("opaque_id", "prediction", "question", "query", "url", "page"):
            self.assertNotIn(f'"{forbidden}"', rendered)
        self.assertFalse(
            value["network_model_search_fetch_evaluator_or_api_called_by_watcher"]
        )


if __name__ == "__main__":
    unittest.main()
