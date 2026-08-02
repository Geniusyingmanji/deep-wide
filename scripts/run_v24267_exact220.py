#!/usr/bin/env python3
"""Run the single cold V2.42.67 exact-220 label-blind forward."""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    NORMALIZED_KINDS,
    validate_v24259_result,
)
from deepwide_agent.v24267_total_fallback import (  # noqa: E402
    build_total_fallback_result,
)
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    POOL_ID,
    validate_receipt,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24267_exact220 import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_RESULT,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT,
    OUTPUT_ROOT,
    PREDICTION_FREEZE,
    RUNNER_MARKER,
    RUN_SUMMARY,
    RUNTIME_PREDICTIONS,
    SAFE_PROGRESS,
    SELECTED_COUNT,
    TASK_ROOT,
    selected_tasks,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    _child_env,
    _new_json,
    _safe_progress,
    _start_ticks,
    _terminate_group,
    payload_sha256,
    read_object,
    sha256,
)
from scripts.run_v24261_score_first_smoke import task_command as base_task_command  # noqa: E402
from scripts.run_v24262_score_first_capacity import _atomic_json  # noqa: E402


ROLE = "v24267_exact220_forward_result"
CHILD = "scripts/run_v24267_score_first_task.py"
RECEIPT_NAME = "model_slot_receipt.json"
MODEL_GENERATED = frozenset({"primary", "repaired", *NORMALIZED_KINDS})
RUNTIME_ROW_KEYS = frozenset(
    {
        "opaque_id",
        "status",
        "prediction",
        "prediction_sha256",
        "completion_kind",
        "elapsed_seconds",
        "cost",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
)
SUMMARY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "selected",
        "completed",
        "failed",
        "model_generated_tables",
        "fallback_tables",
        "completion_kinds",
        "system_total_tokens",
        "wall_seconds_sum",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "official_evaluator_called",
    }
)
FREEZE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "selected",
        "terminal",
        "selected_opaque_ids_sha256",
        "runtime_predictions_sha256",
        "run_summary_sha256",
        "prediction_hashes_sha256",
        "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open",
        "mapping_query_answer_gold_or_evaluator_opened_or_hashed",
        "label_blind",
        "freeze_payload_sha256",
    }
)
PROGRESS_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "selected",
        "completed_predictions",
        "unfinished_predictions",
        "executor_concurrency",
        "global_model_slot_cap",
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "progress_payload_sha256",
    }
)
EXECUTION_START_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "protocol_sha256",
        "activation_sha256",
        "selected_opaque_ids_sha256",
        "runner",
        "selected",
        "executor_concurrency",
        "global_model_slot_cap",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "api_called_before_execution_start",
        "execution_start_payload_sha256",
    }
)
ACTIVATION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "status",
        "protocol_sha256",
        "preactivation_audit_sha256",
        "decision_contract_sha256",
        "control_manifest_sha256",
        "forward_manifest_sha256",
        "selected_count",
        "executor_concurrency",
        "global_model_slot_cap",
        "shared_api_lease_active_before_activation",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "additional_rollout_avg4_leaderboard_or_sota_authorized",
        "activation_payload_sha256",
    }
)
FORWARD_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "selected",
        "terminal_predictions",
        "model_generated_tables",
        "fallback_tables",
        "system_total_tokens",
        "prediction_freeze_sha256",
        "shared_model_receipts",
        "exact220_terminal_before_evaluator_open",
        "mapping_query_answer_gold_or_evaluator_opened_or_hashed",
        "label_blind",
        "official_evaluator_called",
        "additional_rollout_avg4_leaderboard_or_sota_launched",
        "execution_start_sha256",
        "activation_payload_sha256",
        "result_payload_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "children",
        "present",
        "valid",
        "invalid",
        "actual_model_requests",
        "slot_acquisitions",
        "all_acquisitions_match_actual_requests",
    }
)


@dataclasses.dataclass(frozen=True)
class TaskOutcome:
    result: dict[str, Any]
    receipt_present: bool
    receipt_valid: bool
    receipt_acquisitions: int


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _nonnegative(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"V2.42.67 {label} is not nonnegative")
    return value


def validate_activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / ACTIVATION)
    if (
        set(value) != ACTIVATION_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24267_exact220_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("decision_contract_sha256") != protocol["decision_contract_sha256"]
        or value.get("forward_manifest_sha256") != protocol["forward_surface"]["manifest_sha256"]
        or value.get("control_manifest_sha256") != protocol["control_surface"]["manifest_sha256"]
        or value.get("selected_count") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("shared_api_lease_active_before_activation") is not False
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("additional_rollout_avg4_leaderboard_or_sota_authorized") is not False
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.67 activation drifted")
    return value


def validate_execution_start(
    root: Path, protocol: dict[str, Any], activation: dict[str, Any]
) -> dict[str, Any]:
    value = read_object(root / EXECUTION_START)
    runner = value.get("runner")
    if (
        set(value) != EXECUTION_START_KEYS
        or value.get("role") != "v24267_exact220_execution_start"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("selected_opaque_ids_sha256")
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or not isinstance(runner, dict)
        or set(runner) != {"pid", "start_ticks", "marker"}
        or _nonnegative(runner.get("pid"), "runner pid") <= 0
        or _nonnegative(runner.get("start_ticks"), "runner start ticks") < 0
        or runner.get("marker") != RUNNER_MARKER
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("label_blind") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("api_called_before_execution_start") is not False
        or not _sealed(value, "execution_start_payload_sha256")
        or activation.get("activation_payload_sha256")
        != read_object(root / ACTIVATION).get("activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.67 execution start drifted")
    return value


def task_command(
    root: Path,
    protocol: dict[str, Any],
    task_path: Path,
    result_path: Path,
    progress_path: Path,
    receipt_path: Path,
) -> list[str]:
    command = base_task_command(root, protocol, task_path, result_path, progress_path)
    command[3] = str(root / CHILD)
    command.extend(
        [
            "--model-slot-directory",
            str(root / MODEL_SLOT_DIRECTORY),
            "--model-slot-receipt",
            str(receipt_path),
            "--model-slot-cap",
            str(MODEL_SLOT_CAP),
            "--model-slot-pool-id",
            POOL_ID,
        ]
    )
    return command


def run_one_task(
    root: Path,
    protocol: dict[str, Any],
    task: dict[str, str],
    task_root: Path,
    *,
    popen: Any = subprocess.Popen,
) -> TaskOutcome:
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    task_path = task_root / "visible_task.json"
    result_path = task_root / "result.json"
    progress_path = task_root / "safe_progress.json"
    receipt_path = task_root / RECEIPT_NAME
    _new_json(task_path, task)
    process = popen(
        task_command(root, protocol, task_path, result_path, progress_path, receipt_path),
        cwd=root,
        env=_child_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    started = time.monotonic()
    timed_out = False
    try:
        return_code = process.wait(
            timeout=float(protocol["limits"]["wall_seconds"])
            + float(protocol["execution"]["parent_deadline_grace_seconds"])
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_group(process)
        return_code = process.returncode
    elapsed = time.monotonic() - started
    receipt: dict[str, Any] | None = None
    if receipt_path.is_file() and not receipt_path.is_symlink():
        try:
            candidate = read_object(receipt_path)
            receipt = validate_receipt(candidate, expected_cap=MODEL_SLOT_CAP)
        except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError):
            receipt = None
    if not timed_out and return_code == 0 and result_path.is_file():
        try:
            result = read_object(result_path)
            validate_v24259_result(result)
            expected = int(result["cost"]["model"]["requests"])
            if receipt is None:
                raise ValueError("model slot receipt absent")
            validate_receipt(
                receipt,
                expected_cap=MODEL_SLOT_CAP,
                expected_acquisitions=expected,
            )
            return TaskOutcome(result, True, True, expected)
        except (KeyError, OSError, TypeError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError):
            fallback = build_total_fallback_result(
                task,
                limits=ScoreFirstLimits(**dict(protocol["limits"])),
                completion_kind="worker_failure_fallback",
                failure_stage="model_slot_receipt",
                failure_type="ModelSlotReceiptInvalid",
                elapsed_seconds=elapsed,
                last_progress=_safe_progress_or_empty(progress_path),
            )
            return TaskOutcome(
                fallback,
                receipt is not None,
                False,
                int(receipt.get("acquisitions", 0)) if receipt is not None else 0,
            )
    fallback = build_total_fallback_result(
        task,
        limits=ScoreFirstLimits(**dict(protocol["limits"])),
        completion_kind="hard_deadline_fallback" if timed_out else "worker_failure_fallback",
        failure_stage="parent_executor",
        failure_type="HardDeadlineExceeded" if timed_out else "WorkerNonzeroExit",
        elapsed_seconds=elapsed,
        last_progress=_safe_progress_or_empty(progress_path),
    )
    receipt_valid = False
    if receipt is not None:
        try:
            validate_receipt(
                receipt,
                expected_cap=MODEL_SLOT_CAP,
                expected_acquisitions=int(fallback["cost"]["model"]["requests"]),
            )
            receipt_valid = True
        except (KeyError, TypeError, ValueError):
            receipt_valid = False
    return TaskOutcome(
        fallback,
        receipt is not None,
        receipt_valid,
        int(receipt.get("acquisitions", 0)) if receipt is not None else 0,
    )


def _safe_progress_or_empty(path: Path) -> dict[str, Any]:
    try:
        return _safe_progress(path)
    except (KeyError, OSError, TypeError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError):
        return {}


def _executor_exception_outcome(
    task: dict[str, str], protocol: dict[str, Any], failure: BaseException
) -> TaskOutcome:
    result = build_total_fallback_result(
        task,
        limits=ScoreFirstLimits(**dict(protocol["limits"])),
        completion_kind="worker_failure_fallback",
        failure_stage="parent_future",
        failure_type=type(failure).__name__,
        elapsed_seconds=0.0,
    )
    return TaskOutcome(result, False, False, 0)


def _runtime_row(result: dict[str, Any]) -> dict[str, Any]:
    value = {
        "opaque_id": result["opaque_id"],
        "status": "completed",
        "prediction": result["prediction"],
        "prediction_sha256": result["prediction_sha256"],
        "completion_kind": result["completion_kind"],
        "elapsed_seconds": result["budget"]["elapsed_seconds"],
        "cost": {"system_total_tokens": result["cost"]["system_total_tokens"]},
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    validate_runtime_row(value)
    return value


def validate_runtime_row(value: dict[str, Any]) -> None:
    prediction = value.get("prediction")
    elapsed = value.get("elapsed_seconds")
    cost = value.get("cost")
    if (
        set(value) != RUNTIME_ROW_KEYS
        or value.get("status") != "completed"
        or not isinstance(value.get("opaque_id"), str)
        or not isinstance(prediction, str)
        or not prediction
        or hashlib.sha256(prediction.encode()).hexdigest() != value.get("prediction_sha256")
        or not isinstance(value.get("completion_kind"), str)
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or not isinstance(cost, dict)
        or set(cost) != {"system_total_tokens"}
        or isinstance(cost["system_total_tokens"], bool)
        or not isinstance(cost["system_total_tokens"], int)
        or cost["system_total_tokens"] < 0
        or value.get("label_blind") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
    ):
        raise RuntimeError("V2.42.67 runtime row drifted")


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    for result in results:
        kind = str(result["completion_kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
    value = {
        "artifact_version": 1,
        "role": "v24267_exact220_run_summary",
        "selected": SELECTED_COUNT,
        "completed": SELECTED_COUNT,
        "failed": 0,
        "model_generated_tables": sum(result["completion_kind"] in MODEL_GENERATED for result in results),
        "fallback_tables": sum(result["completion_kind"] not in MODEL_GENERATED for result in results),
        "completion_kinds": kinds,
        "system_total_tokens": sum(int(result["cost"]["system_total_tokens"]) for result in results),
        "wall_seconds_sum": round(sum(float(result["budget"]["elapsed_seconds"]) for result in results), 6),
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
    }
    validate_summary(value)
    return value


def validate_summary(value: dict[str, Any]) -> None:
    if (
        set(value) != SUMMARY_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24267_exact220_run_summary"
        or value.get("selected") != SELECTED_COUNT
        or value.get("completed") != SELECTED_COUNT
        or value.get("failed") != 0
        or value.get("model_generated_tables", -1) + value.get("fallback_tables", -1) != SELECTED_COUNT
        or sum((value.get("completion_kinds") or {}).values()) != SELECTED_COUNT
        or value.get("label_blind") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("official_evaluator_called") is not False
    ):
        raise RuntimeError("V2.42.67 run summary drifted")


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _safe_forward_progress(completed: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24267_exact220_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "completed_predictions": completed,
        "unfinished_predictions": SELECTED_COUNT - completed,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["progress_payload_sha256"] = payload_sha256(value)
    validate_progress(value)
    return value


def validate_progress(value: dict[str, Any]) -> None:
    if (
        set(value) != PROGRESS_KEYS
        or value.get("role") != "v24267_exact220_safe_forward_progress"
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("contains_question_query_url_page_prediction_answer_opaque_id_or_credential") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or not _sealed(value, "progress_payload_sha256")
    ):
        raise RuntimeError("V2.42.67 progress schema drifted")
    completed = _nonnegative(value.get("completed_predictions"), "completed predictions")
    unfinished = _nonnegative(value.get("unfinished_predictions"), "unfinished predictions")
    if completed + unfinished != SELECTED_COUNT:
        raise RuntimeError("V2.42.67 progress accounting drifted")


def validate_prediction_freeze(
    root: Path, protocol: dict[str, Any], value: dict[str, Any]
) -> list[dict[str, Any]]:
    if (
        set(value) != FREEZE_KEYS
        or value.get("role") != "v24267_exact220_prediction_freeze"
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal") != SELECTED_COUNT
        or value.get("selected_opaque_ids_sha256")
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or value.get("runtime_predictions_sha256") != sha256(root / RUNTIME_PREDICTIONS)
        or value.get("run_summary_sha256") != sha256(root / RUN_SUMMARY)
        or value.get("exact_terminal_before_mapping_query_answer_gold_or_evaluator_open") is not True
        or value.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed") is not False
        or value.get("label_blind") is not True
        or not _sealed(value, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.42.67 prediction freeze drifted")
    rows = [
        json.loads(line)
        for line in (root / RUNTIME_PREDICTIONS).read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(rows) != SELECTED_COUNT:
        raise RuntimeError("V2.42.67 prediction freeze row count drifted")
    for row in rows:
        validate_runtime_row(row)
    if (
        payload_sha256([row["opaque_id"] for row in rows])
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or payload_sha256([row["prediction_sha256"] for row in rows])
        != value.get("prediction_hashes_sha256")
    ):
        raise RuntimeError("V2.42.67 prediction freeze vector drifted")
    validate_summary(read_object(root / RUN_SUMMARY))
    return rows


def validate_forward_result(
    root: Path, protocol: dict[str, Any], value: dict[str, Any]
) -> None:
    activation = validate_activation(root, protocol)
    validate_execution_start(root, protocol, activation)
    freeze = read_object(root / PREDICTION_FREEZE)
    validate_prediction_freeze(root, protocol, freeze)
    if (
        set(value) != FORWARD_KEYS
        or value.get("role") != ROLE
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal_predictions") != SELECTED_COUNT
        or value.get("model_generated_tables", -1) + value.get("fallback_tables", -1)
        != SELECTED_COUNT
        or value.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or value.get("exact220_terminal_before_evaluator_open") is not True
        or value.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed") is not False
        or value.get("label_blind") is not True
        or value.get("official_evaluator_called") is not False
        or value.get("additional_rollout_avg4_leaderboard_or_sota_launched") is not False
        or value.get("execution_start_sha256") != sha256(root / EXECUTION_START)
        or value.get("activation_payload_sha256") != activation["activation_payload_sha256"]
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.42.67 forward result drifted")
    summary = read_object(root / RUN_SUMMARY)
    if (
        value["model_generated_tables"] != summary["model_generated_tables"]
        or value["fallback_tables"] != summary["fallback_tables"]
        or value["system_total_tokens"] != summary["system_total_tokens"]
    ):
        raise RuntimeError("V2.42.67 forward summary binding drifted")
    receipts = value.get("shared_model_receipts")
    if not isinstance(receipts, dict) or set(receipts) != RECEIPT_KEYS:
        raise RuntimeError("V2.42.67 receipt schema drifted")
    for key in RECEIPT_KEYS - {"all_acquisitions_match_actual_requests"}:
        _nonnegative(receipts.get(key), f"receipts.{key}")
    health = (
        receipts["children"] == SELECTED_COUNT
        and receipts["present"] == SELECTED_COUNT
        and receipts["valid"] == SELECTED_COUNT
        and receipts["invalid"] == 0
        and receipts["slot_acquisitions"] == receipts["actual_model_requests"]
    )
    if receipts.get("all_acquisitions_match_actual_requests") is not health:
        raise RuntimeError("V2.42.67 receipt accounting drifted")


def execute_forward(
    root: Path,
    protocol: dict[str, Any],
    tasks: list[dict[str, str]],
    *,
    task_runner: Callable[[Path, dict[str, Any], dict[str, str], Path], TaskOutcome] = run_one_task,
    progress_writer: Callable[[dict[str, Any]], None] | None = None,
) -> list[TaskOutcome]:
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.42.67 exact-220 task count drifted")
    outcomes: dict[int, TaskOutcome] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=EXECUTOR_CONCURRENCY, thread_name_prefix="v24267-exact220"
    ) as executor:
        futures = {
            executor.submit(task_runner, root, protocol, task, root / TASK_ROOT / f"task_{position:04d}"): position
            for position, task in enumerate(tasks, start=1)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            try:
                outcome = future.result()
                if not isinstance(outcome, TaskOutcome):
                    raise RuntimeError("V2.42.67 child outcome lacks receipt evidence")
                validate_v24259_result(outcome.result)
            except BaseException as exc:
                outcome = _executor_exception_outcome(tasks[position - 1], protocol, exc)
            validate_v24259_result(outcome.result)
            outcomes[position] = outcome
            if progress_writer:
                progress_writer(_safe_forward_progress(len(outcomes)))
    ordered = [outcomes[position] for position in range(1, SELECTED_COUNT + 1)]
    if [value.result["opaque_id"] for value in ordered] != [task["opaque_id"] for task in tasks]:
        raise RuntimeError("V2.42.67 exact-220 result order drifted")
    return ordered


def _prepare_slots(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {"artifact_version": 1, "role": "v24267_model_slot", "pool_id": POOL_ID, "slot": index, "slot_cap": MODEL_SLOT_CAP, "contains_credential_or_benchmark_content": False},
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if root != ROOT or protocol_path.resolve() != (root / OUTPUT).resolve():
        raise RuntimeError("V2.42.67 executor path drifted")
    protocol = validate_protocol(root, OUTPUT)
    activation = validate_activation(root, protocol)
    tasks = selected_tasks(root, protocol)
    for path in (root / EXECUTION_START, root / FORWARD_RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.42.67 forward surface is not pristine")
    start = {
        "artifact_version": 1,
        "role": "v24267_exact220_execution_start",
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(root / OUTPUT),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected_opaque_ids_sha256": protocol["task_contract"]["selected_opaque_ids_sha256"],
        "runner": {"pid": os.getpid(), "start_ticks": _start_ticks(os.getpid()), "marker": RUNNER_MARKER},
        "selected": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = payload_sha256(start)
    _new_json(root / EXECUTION_START, start)
    (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    _prepare_slots(root)
    (root / TASK_ROOT).mkdir(mode=0o700)
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(root, owner=lease["forward_owner"], purpose=lease["forward_purpose"], path=root / lease["path"]):
        outcomes = execute_forward(
            root,
            protocol,
            tasks,
            progress_writer=lambda value: _atomic_json(root / SAFE_PROGRESS, value),
        )
    results = [outcome.result for outcome in outcomes]
    rows = [_runtime_row(result) for result in results]
    _write_jsonl_new(root / RUNTIME_PREDICTIONS, rows)
    summary = _summary(results)
    _new_json(root / RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24267_exact220_prediction_freeze",
        "protocol_id": protocol["protocol_id"],
        "selected": SELECTED_COUNT,
        "terminal": SELECTED_COUNT,
        "selected_opaque_ids_sha256": protocol["task_contract"]["selected_opaque_ids_sha256"],
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "run_summary_sha256": sha256(root / RUN_SUMMARY),
        "prediction_hashes_sha256": payload_sha256([row["prediction_sha256"] for row in rows]),
        "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open": True,
        "mapping_query_answer_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = payload_sha256(freeze)
    validate_prediction_freeze(root, protocol, freeze)
    _new_json(root / PREDICTION_FREEZE, freeze)
    requests = sum(int(result["cost"]["model"]["requests"]) for result in results)
    acquisitions = sum(outcome.receipt_acquisitions for outcome in outcomes)
    valid = sum(outcome.receipt_valid for outcome in outcomes)
    forward = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "terminal_predictions": SELECTED_COUNT,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "system_total_tokens": summary["system_total_tokens"],
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "shared_model_receipts": {
            "children": SELECTED_COUNT,
            "present": sum(outcome.receipt_present for outcome in outcomes),
            "valid": valid,
            "invalid": SELECTED_COUNT - valid,
            "actual_model_requests": requests,
            "slot_acquisitions": acquisitions,
            "all_acquisitions_match_actual_requests": valid == SELECTED_COUNT and acquisitions == requests,
        },
        "exact220_terminal_before_evaluator_open": True,
        "mapping_query_answer_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
        "official_evaluator_called": False,
        "additional_rollout_avg4_leaderboard_or_sota_launched": False,
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "activation_payload_sha256": activation["activation_payload_sha256"],
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    validate_forward_result(root, protocol, forward)
    _new_json(root / FORWARD_RESULT, forward)
    _atomic_json(root / SAFE_PROGRESS, _safe_forward_progress(SELECTED_COUNT))
    print(json.dumps({"forward_result": str(FORWARD_RESULT), "terminal_predictions": SELECTED_COUNT}, sort_keys=True))


if __name__ == "__main__":
    main()
