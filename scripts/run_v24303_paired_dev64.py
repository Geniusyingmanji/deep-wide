#!/usr/bin/env python3
"""Execute one fresh interleaved, label-blind V2.43.03 paired-dev64."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    POOL_ID,
    validate_receipt,
)
from deepwide_agent.v24267_total_fallback import (  # noqa: E402
    build_total_fallback_result,
)
from deepwide_agent.v24287_hard_deadline_fetch import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24303_forward_contract import (  # noqa: E402
    ACTIVATION,
    ARMS,
    CHILD_MARKER,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY_PER_ARM,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT_ROOT,
    PREDICTION_FREEZE,
    PREAUDIT,
    PROTOCOL_ID,
    protected_watcher_snapshot,
    RUNNER_MARKER,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SELECTED_COUNT,
    TASK_ROOT,
    TOTAL_EXECUTOR_CONCURRENCY,
    TOTAL_TASK_COUNT,
    payload_sha256,
    read_object,
    selected_tasks,
    sha256,
    validate_forward_contract,
)
from deepwide_agent.v24303_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD,
    validate_v24303_result,
    zero_effect_receipt,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


RECEIPT_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)


@dataclass(frozen=True)
class WorkItem:
    arm: str
    position: int
    task: dict[str, str]


@dataclass(frozen=True)
class TaskOutcome:
    arm: str
    position: int
    result: dict[str, Any]
    receipt_present: bool
    receipt_valid: bool
    receipt_acquisitions: int
    transport: dict[str, int]


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _start_ticks(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    return int(raw[raw.rfind(")") + 2 :].split()[19])


def validate_preaudit(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / PREAUDIT)
    if (
        value.get("role") != "v24303_paired_dev64_preactivation_audit"
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("dependency_manifest_sha256")
        != contract["dependency_manifest_sha256"]
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.03 preactivation audit drifted")
    return value


def validate_activation(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / ACTIVATION)
    if (
        value.get("role") != "v24303_paired_dev64_activation"
        or value.get("status") != "active"
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("dependency_manifest_sha256")
        != contract["dependency_manifest_sha256"]
        or value.get("selected_per_arm") != SELECTED_COUNT
        or value.get("executor_concurrency_per_arm")
        != EXECUTOR_CONCURRENCY_PER_ARM
        or value.get("total_executor_concurrency") != TOTAL_EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("shared_api_lease_active_before_activation") is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("exact220_leaderboard_or_sota_authorized") is not False
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.03 activation drifted")
    return value


def validate_execution_start(
    root: Path,
    contract: dict[str, Any],
    activation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = read_object(root / EXECUTION_START)
    active = activation or validate_activation(root, contract)
    unsigned = dict(value)
    seal = unsigned.pop("execution_start_payload_sha256", None)
    runner = value.get("runner")
    if (
        value.get("role") != "v24303_paired_dev64_execution_start"
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or not isinstance(runner, dict)
        or runner.get("marker") != RUNNER_MARKER
        or value.get("selected_per_arm") != SELECTED_COUNT
        or value.get("total_tasks") != TOTAL_TASK_COUNT
        or value.get("executor_concurrency_per_arm")
        != EXECUTOR_CONCURRENCY_PER_ARM
        or value.get("total_executor_concurrency") != TOTAL_EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("selected_opaque_ids_sha256")
        != contract["task_contract"]["selected_opaque_ids_sha256"]
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("api_called_before_execution_start") is not False
        or active.get("created_at_unix", 0) > value.get("created_at_unix", -1)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.03 execution start drifted")
    return value


def _child_env() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "TERM": "xterm-256color",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def task_command(root: Path, item: WorkItem, directory: Path) -> list[str]:
    return [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / CHILD_MARKER),
        "--arm",
        item.arm,
        "--task",
        str(directory / "visible_task.json"),
        "--result",
        str(directory / "result.json"),
        "--progress",
        str(directory / "safe_progress.json"),
        "--model-slot-directory",
        str(root / MODEL_SLOT_DIRECTORY),
        "--model-slot-receipt",
        str(directory / RECEIPT_NAME),
        "--transport-health",
        str(directory / TRANSPORT_NAME),
    ]


def _terminate_group(process: Any) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait(timeout=2)


def _safe_progress(path: Path) -> dict[str, Any]:
    try:
        value = read_object(path)
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError):
        return {}
    if (
        value.get("role") != "v24257_score_first_safe_progress"
        or value.get("contains_question_query_url_page_prediction_or_answer") is not False
        or value.get("mapping_gold_evaluator_or_score_read") is not False
    ):
        return {}
    return value


def _fallback(
    item: WorkItem,
    *,
    kind: str,
    failure: str,
    elapsed: float,
    progress: dict[str, Any],
) -> dict[str, Any]:
    value = build_total_fallback_result(
        item.task,
        limits=ScoreFirstLimits(**LIMITS),
        completion_kind=kind,
        failure_stage=f"v24303_{item.arm}_parent_executor",
        failure_type=failure,
        elapsed_seconds=elapsed,
        last_progress=progress,
    )
    value[RECEIPT_FIELD] = zero_effect_receipt(item.arm)
    validate_v24303_result(value, item.arm)
    return value


def run_one_task(
    root: Path,
    contract: dict[str, Any],
    item: WorkItem,
    directory: Path,
    *,
    popen: Any = subprocess.Popen,
) -> TaskOutcome:
    del contract
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    _new_json(directory / "visible_task.json", item.task)
    process = popen(
        task_command(root, item, directory),
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
        return_code = process.wait(timeout=float(LIMITS["wall_seconds"]) + 15.0)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_group(process)
        return_code = process.returncode
    elapsed = max(0.0, time.monotonic() - started)
    receipt_path = directory / RECEIPT_NAME
    transport_path = directory / TRANSPORT_NAME
    receipt: dict[str, Any] | None = None
    health = {
        "hard_fetch_helper_calls": 0,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
    }
    try:
        if receipt_path.is_file() and not receipt_path.is_symlink():
            receipt = validate_receipt(
                read_object(receipt_path), expected_cap=MODEL_SLOT_CAP
            )
    except (KeyError, OSError, TypeError, ValueError, RuntimeError):
        receipt = None
    try:
        if transport_path.is_file() and not transport_path.is_symlink():
            health = validate_transport_health(read_object(transport_path))
    except (OSError, ValueError, RuntimeError):
        health = {
            "hard_fetch_helper_calls": 0,
            "hard_fetch_deadline_failures": 0,
            "fetch_helper_failures": 1,
        }
    if not timed_out and return_code == 0 and (directory / "result.json").is_file():
        try:
            envelope = read_object(directory / "result.json")
            unsigned = dict(envelope)
            seal = unsigned.pop("envelope_payload_sha256", None)
            if (
                envelope.get("role") != "v24303_paired_dev64_task_envelope"
                or envelope.get("arm") != item.arm
                or envelope.get(
                    "mapping_gold_category_question_type_split_evaluator_score_read"
                )
                is not False
                or envelope.get("transport_health") != health
                or seal != payload_sha256(unsigned)
            ):
                raise ValueError("V2.43.03 task envelope drifted")
            result = envelope["result"]
            validate_v24303_result(result, item.arm)
            requests = int(result["cost"]["model"]["requests"])
            if receipt is None:
                raise ValueError("V2.43.03 model-slot receipt absent")
            validate_receipt(
                receipt,
                expected_cap=MODEL_SLOT_CAP,
                expected_acquisitions=requests,
            )
            return TaskOutcome(
                item.arm, item.position, result, True, True, requests, health
            )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            pass
    kind = "hard_deadline_fallback" if timed_out else "worker_failure_fallback"
    failure = "HardDeadlineExceeded" if timed_out else "WorkerOrEnvelopeFailure"
    result = _fallback(
        item,
        kind=kind,
        failure=failure,
        elapsed=elapsed,
        progress=_safe_progress(directory / "safe_progress.json"),
    )
    requests = int(result["cost"]["model"]["requests"])
    valid = False
    acquisitions = 0
    if receipt is not None:
        acquisitions = int(receipt.get("acquisitions", 0))
        try:
            validate_receipt(
                receipt,
                expected_cap=MODEL_SLOT_CAP,
                expected_acquisitions=requests,
            )
            valid = True
        except (KeyError, TypeError, ValueError):
            pass
    return TaskOutcome(
        item.arm,
        item.position,
        result,
        receipt is not None,
        valid,
        acquisitions,
        health,
    )


def interleaved_work_items(tasks: list[dict[str, str]]) -> list[WorkItem]:
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.43.03 scheduler requires exactly 64 visible tasks")
    return [
        WorkItem(arm=arm, position=position, task=tasks[position - 1])
        for position in range(1, SELECTED_COUNT + 1)
        for arm in ARMS
    ]


def _progress(completed: dict[str, int]) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24303_paired_dev64_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected_per_arm": SELECTED_COUNT,
        "completed_by_arm": {arm: int(completed.get(arm, 0)) for arm in ARMS},
        "unfinished_by_arm": {
            arm: SELECTED_COUNT - int(completed.get(arm, 0)) for arm in ARMS
        },
        "total_completed": sum(int(completed.get(arm, 0)) for arm in ARMS),
        "total_unfinished": TOTAL_TASK_COUNT
        - sum(int(completed.get(arm, 0)) for arm in ARMS),
        "executor_concurrency_per_arm": EXECUTOR_CONCURRENCY_PER_ARM,
        "total_executor_concurrency": TOTAL_EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["progress_payload_sha256"] = payload_sha256(value)
    validate_progress(value)
    return value


def validate_progress(value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("progress_payload_sha256", None)
    completed = value.get("completed_by_arm")
    unfinished = value.get("unfinished_by_arm")
    if (
        value.get("role") != "v24303_paired_dev64_safe_forward_progress"
        or value.get("selected_per_arm") != SELECTED_COUNT
        or not isinstance(completed, dict)
        or not isinstance(unfinished, dict)
        or set(completed) != set(ARMS)
        or set(unfinished) != set(ARMS)
        or any(
            isinstance(completed[arm], bool)
            or not isinstance(completed[arm], int)
            or not 0 <= completed[arm] <= SELECTED_COUNT
            or unfinished[arm] != SELECTED_COUNT - completed[arm]
            for arm in ARMS
        )
        or value.get("total_completed") != sum(completed.values())
        or value.get("total_unfinished") != sum(unfinished.values())
        or value.get("executor_concurrency_per_arm")
        != EXECUTOR_CONCURRENCY_PER_ARM
        or value.get("total_executor_concurrency") != TOTAL_EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get(
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.03 safe progress drifted")


def execute_forward(
    root: Path,
    contract: dict[str, Any],
    tasks: list[dict[str, str]],
    *,
    task_runner: Callable[
        [Path, dict[str, Any], WorkItem, Path], TaskOutcome
    ] = run_one_task,
    progress_writer: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, list[TaskOutcome]]:
    items = interleaved_work_items(tasks)
    outcomes: dict[tuple[str, int], TaskOutcome] = {}
    active = {arm: 0 for arm in ARMS}
    completed = {arm: 0 for arm in ARMS}
    next_index = 0
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=TOTAL_EXECUTOR_CONCURRENCY,
        thread_name_prefix="v24303-paired",
    ) as executor:
        futures: dict[concurrent.futures.Future[TaskOutcome], WorkItem] = {}
        while len(outcomes) < TOTAL_TASK_COUNT:
            admitted = True
            while admitted and len(futures) < TOTAL_EXECUTOR_CONCURRENCY:
                admitted = False
                for offset in range(len(items)):
                    index = (next_index + offset) % len(items)
                    item = items[index]
                    key = (item.arm, item.position)
                    if key in outcomes or any(
                        pending.arm == item.arm and pending.position == item.position
                        for pending in futures.values()
                    ):
                        continue
                    if active[item.arm] >= EXECUTOR_CONCURRENCY_PER_ARM:
                        continue
                    directory = (
                        root
                        / TASK_ROOT
                        / item.arm
                        / f"task_{item.position:04d}"
                    )
                    future = executor.submit(
                        task_runner, root, contract, item, directory
                    )
                    futures[future] = item
                    active[item.arm] += 1
                    next_index = (index + 1) % len(items)
                    admitted = True
                    break
            if not futures:
                raise RuntimeError("V2.43.03 paired scheduler deadlocked")
            done, _ = concurrent.futures.wait(
                futures,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                item = futures.pop(future)
                active[item.arm] -= 1
                try:
                    outcome = future.result()
                    if (
                        not isinstance(outcome, TaskOutcome)
                        or outcome.arm != item.arm
                        or outcome.position != item.position
                    ):
                        raise TypeError("V2.43.03 task outcome drifted")
                    validate_v24303_result(outcome.result, item.arm)
                except BaseException as exc:
                    outcome = TaskOutcome(
                        item.arm,
                        item.position,
                        _fallback(
                            item,
                            kind="worker_failure_fallback",
                            failure=type(exc).__name__,
                            elapsed=0.0,
                            progress={},
                        ),
                        False,
                        False,
                        0,
                        {
                            "hard_fetch_helper_calls": 0,
                            "hard_fetch_deadline_failures": 0,
                            "fetch_helper_failures": 0,
                        },
                    )
                outcomes[(item.arm, item.position)] = outcome
                completed[item.arm] += 1
                if progress_writer is not None:
                    progress_writer(_progress(completed))
    ordered = {
        arm: [outcomes[(arm, position)] for position in range(1, SELECTED_COUNT + 1)]
        for arm in ARMS
    }
    for arm in ARMS:
        if [item.result["opaque_id"] for item in ordered[arm]] != [
            task["opaque_id"] for task in tasks
        ]:
            raise RuntimeError(f"V2.43.03 {arm} scheduler result order drifted")
    return ordered


def _mechanism_telemetry(result: dict[str, Any], arm: str) -> dict[str, Any]:
    retrieval = result.get("staged_reserve_retrieval") or {}
    receipt = retrieval.get("receipt") if retrieval.get("status") == "completed" else None
    controller = (receipt or {}).get("controller") or {}
    stage = (receipt or {}).get("reserved_stage") or {}
    recovery = result.get(RECEIPT_FIELD) or {}
    return {
        "retrieval_completed": receipt is not None,
        "controller_stop": bool(receipt and controller.get("decision") == "stop"),
        "controller_expand": bool(
            receipt and controller.get("decision") == "expand"
        ),
        "reserved_stage_executed": bool(stage.get("executed")),
        "low_coverage_diversity_tail": bool(
            stage.get("reason") == "low_coverage_diversity_tail"
        ),
        "selected_tail_count": int(stage.get("selected_tail_count", 0) or 0),
        "reserved_fetches": int(stage.get("fetches_attempted", 0) or 0),
        "reserved_usable_pages": int(stage.get("usable_pages", 0) or 0),
        "hosted_search_requests_added_by_reserved": int(
            (receipt or {}).get("hosted_search_requests_added_by_reserved", 0) or 0
        ),
        "cache_miss_count": int(retrieval.get("cache_miss_count", 0) or 0),
        "cache_serve_network_fetches": int(
            retrieval.get("network_fetches_during_cache_serve", 0) or 0
        ),
        "recovery_enabled": bool(recovery.get("recovery_enabled")),
        "synthesis_initial_model_request_error": bool(
            recovery.get("synthesis_initial_model_request_error")
        ),
        "synthesis_recovery_attempted": bool(
            recovery.get("synthesis_recovery_attempted")
        ),
        "synthesis_recovery_succeeded": bool(
            recovery.get("synthesis_recovery_succeeded")
        ),
        "synthesis_recovery_model_request_error": bool(
            recovery.get("synthesis_recovery_model_request_error")
        ),
        "repair_blocked_after_recovery": bool(
            recovery.get("repair_blocked_after_recovery")
        ),
        "fourth_model_effect": bool(recovery.get("fourth_model_effect")),
        "total_model_effects": int(recovery.get("total_effects_admitted", 0) or 0),
    }


def _runtime_row(result: dict[str, Any], arm: str) -> dict[str, Any]:
    model = result["cost"]["model"]
    search = result["cost"]["search"]
    value = {
        "opaque_id": result["opaque_id"],
        "status": "completed",
        "prediction": result["prediction"],
        "prediction_sha256": result["prediction_sha256"],
        "completion_kind": result["completion_kind"],
        "elapsed_seconds": result["budget"]["elapsed_seconds"],
        "cost": {
            "model_calls": model["requests"],
            "model_successful_calls": model["requests"],
            "model_failed_calls": 0,
            "model_attempts": model["attempts"],
            "input_tokens": model["input_tokens"],
            "output_tokens": model["output_tokens"],
            "total_tokens": model["total_tokens"],
            "search_calls": search["calls"],
            "search_failures": search["failures"],
            "search_tool_calls": search["tool_calls"],
            "search_fetch_calls": search["fetch_calls"],
            "search_fetch_failures": search["fetch_failures"],
            "search_input_tokens": search["input_tokens"],
            "search_output_tokens": search["output_tokens"],
            "search_total_tokens": search["total_tokens"],
            "system_total_tokens": result["cost"]["system_total_tokens"],
        },
        "mechanism_telemetry": _mechanism_telemetry(result, arm),
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    validate_runtime_row(value, arm)
    return value


def validate_runtime_row(value: dict[str, Any], arm: str) -> None:
    if arm not in ARMS:
        raise RuntimeError("V2.43.03 runtime row arm drifted")
    prediction = value.get("prediction")
    elapsed = value.get("elapsed_seconds")
    cost = value.get("cost")
    telemetry = value.get("mechanism_telemetry")
    bool_fields = {
        "retrieval_completed",
        "controller_stop",
        "controller_expand",
        "reserved_stage_executed",
        "low_coverage_diversity_tail",
        "recovery_enabled",
        "synthesis_initial_model_request_error",
        "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded",
        "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery",
        "fourth_model_effect",
    }
    count_fields = {
        "selected_tail_count",
        "reserved_fetches",
        "reserved_usable_pages",
        "hosted_search_requests_added_by_reserved",
        "cache_miss_count",
        "cache_serve_network_fetches",
        "total_model_effects",
    }
    if (
        value.get("status") != "completed"
        or not isinstance(value.get("opaque_id"), str)
        or not isinstance(prediction, str)
        or not prediction
        or hashlib.sha256(prediction.encode()).hexdigest()
        != value.get("prediction_sha256")
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or not isinstance(cost, dict)
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for number in cost.values()
        )
        or not isinstance(telemetry, dict)
        or set(telemetry) != bool_fields | count_fields
        or any(not isinstance(telemetry[name], bool) for name in bool_fields)
        or any(
            isinstance(telemetry[name], bool)
            or not isinstance(telemetry[name], int)
            or telemetry[name] < 0
            for name in count_fields
        )
        or telemetry["controller_stop"] + telemetry["controller_expand"]
        != int(telemetry["retrieval_completed"])
        or telemetry["low_coverage_diversity_tail"]
        and not telemetry["reserved_stage_executed"]
        or telemetry["hosted_search_requests_added_by_reserved"] != 0
        or telemetry["recovery_enabled"] is not (arm == "candidate")
        or telemetry["fourth_model_effect"]
        or telemetry["total_model_effects"] > 3
        or telemetry["synthesis_recovery_succeeded"]
        and not telemetry["synthesis_recovery_attempted"]
        or telemetry["synthesis_recovery_model_request_error"]
        and not telemetry["synthesis_recovery_attempted"]
        or arm == "baseline"
        and any(
            telemetry[name]
            for name in (
                "synthesis_recovery_attempted",
                "synthesis_recovery_succeeded",
                "synthesis_recovery_model_request_error",
                "repair_blocked_after_recovery",
            )
        )
        or value.get("label_blind") is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise RuntimeError("V2.43.03 runtime row drifted")


def _summary(
    arm: str,
    results: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    outcomes: list[TaskOutcome],
    wall: float,
) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    for result in results:
        kinds[result["completion_kind"]] = kinds.get(result["completion_kind"], 0) + 1
    fields = tuple(rows[0]["mechanism_telemetry"]) if rows else ()
    value = {
        "artifact_version": 1,
        "role": "v24303_paired_dev64_run_summary",
        "arm": arm,
        "selected": SELECTED_COUNT,
        "completed": SELECTED_COUNT,
        "failed": 0,
        "model_generated_tables": sum(
            result["completion_kind"] in MODEL_GENERATED for result in results
        ),
        "fallback_tables": sum(
            result["completion_kind"] not in MODEL_GENERATED for result in results
        ),
        "completion_kinds": kinds,
        "system_total_tokens": sum(
            int(result["cost"]["system_total_tokens"]) for result in results
        ),
        "task_wall_seconds_sum": round(
            sum(float(result["budget"]["elapsed_seconds"]) for result in results), 6
        ),
        "shared_forward_wall_seconds": round(max(0.0, wall), 6),
        "hard_fetch_helper_calls": sum(
            item.transport["hard_fetch_helper_calls"] for item in outcomes
        ),
        "hard_fetch_deadline_failures": sum(
            item.transport["hard_fetch_deadline_failures"] for item in outcomes
        ),
        "fetch_helper_failures": sum(
            item.transport["fetch_helper_failures"] for item in outcomes
        ),
        "mechanism_totals": {
            name: sum(int(row["mechanism_telemetry"][name]) for row in rows)
            for name in fields
        },
        "label_blind": True,
        "official_evaluator_called": False,
    }
    validate_summary(value, arm)
    return value


def validate_summary(value: dict[str, Any], arm: str) -> None:
    mechanism = value.get("mechanism_totals")
    if (
        value.get("role") != "v24303_paired_dev64_run_summary"
        or value.get("arm") != arm
        or value.get("selected") != SELECTED_COUNT
        or value.get("completed") != SELECTED_COUNT
        or value.get("failed") != 0
        or value.get("model_generated_tables", -1)
        + value.get("fallback_tables", -1)
        != SELECTED_COUNT
        or not isinstance(mechanism, dict)
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for number in mechanism.values()
        )
        or mechanism.get("controller_stop", 0)
        + mechanism.get("controller_expand", 0)
        != mechanism.get("retrieval_completed", 0)
        or mechanism.get("hosted_search_requests_added_by_reserved", 0) != 0
        or value.get("hard_fetch_deadline_failures", 0)
        + value.get("fetch_helper_failures", 0)
        > value.get("hard_fetch_helper_calls", 0)
        or value.get("label_blind") is not True
        or value.get("official_evaluator_called") is not False
    ):
        raise RuntimeError("V2.43.03 run summary drifted")


def validate_prediction_freeze(
    root: Path, contract: dict[str, Any], arm: str, value: dict[str, Any]
) -> list[dict[str, Any]]:
    unsigned = dict(value)
    seal = unsigned.pop("freeze_payload_sha256", None)
    if (
        value.get("role") != "v24303_paired_dev64_prediction_freeze"
        or value.get("arm") != arm
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal") != SELECTED_COUNT
        or value.get("selected_opaque_ids_sha256")
        != contract["task_contract"]["selected_opaque_ids_sha256"]
        or value.get("runtime_predictions_sha256")
        != sha256(root / RUNTIME_PREDICTIONS[arm])
        or value.get("run_summary_sha256") != sha256(root / RUN_SUMMARY[arm])
        or value.get("arm_terminal_before_mapping_gold_or_evaluator_open") is not True
        or value.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or value.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError(f"V2.43.03 {arm} prediction freeze drifted")
    rows = [
        json.loads(line)
        for line in (root / RUNTIME_PREDICTIONS[arm]).read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(rows) != SELECTED_COUNT:
        raise RuntimeError(f"V2.43.03 {arm} prediction row count drifted")
    for row in rows:
        validate_runtime_row(row, arm)
    if (
        payload_sha256([row["opaque_id"] for row in rows])
        != contract["task_contract"]["selected_opaque_ids_sha256"]
        or payload_sha256([row["prediction_sha256"] for row in rows])
        != value.get("prediction_hashes_sha256")
    ):
        raise RuntimeError(f"V2.43.03 {arm} prediction vector drifted")
    validate_summary(read_object(root / RUN_SUMMARY[arm]), arm)
    return rows


def validate_forward_result(
    root: Path, contract: dict[str, Any], value: dict[str, Any]
) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    activation = validate_activation(root, contract)
    validate_execution_start(root, contract, activation)
    summaries = {arm: read_object(root / RUN_SUMMARY[arm]) for arm in ARMS}
    for arm in ARMS:
        validate_prediction_freeze(
            root, contract, arm, read_object(root / PREDICTION_FREEZE[arm])
        )
    if (
        value.get("role") != "v24303_paired_dev64_forward_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected_per_arm") != SELECTED_COUNT
        or value.get("terminal_predictions_per_arm")
        != {arm: SELECTED_COUNT for arm in ARMS}
        or value.get("arm_summaries")
        != {
            arm: {
                "model_generated_tables": summaries[arm]["model_generated_tables"],
                "fallback_tables": summaries[arm]["fallback_tables"],
                "system_total_tokens": summaries[arm]["system_total_tokens"],
                "task_wall_seconds_sum": summaries[arm]["task_wall_seconds_sum"],
                "mechanism_totals": summaries[arm]["mechanism_totals"],
            }
            for arm in ARMS
        }
        or value.get("prediction_freeze_sha256")
        != {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}
        or value.get("both_arms_exact64_before_mapping_gold_or_evaluator_open")
        is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("official_evaluator_called") is not False
        or value.get("additional_rollout_resume_skip_or_rerun_launched") is not False
        or value.get("execution_start_sha256") != sha256(root / EXECUTION_START)
        or value.get("activation_payload_sha256")
        != activation["activation_payload_sha256"]
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.03 forward result drifted")


def _prepare_slots(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v24303_model_slot",
                "pool_id": POOL_ID,
                "slot": index,
                "slot_cap": MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def main() -> None:
    root = ROOT
    contract = validate_forward_contract(root)
    validate_preaudit(root, contract)
    activation = validate_activation(root, contract)
    tasks = selected_tasks(root, contract)
    for path in (root / EXECUTION_START, root / FORWARD_RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.43.03 forward surface is not pristine")
    with acquire_deepwide_api_lease(
        root,
        owner=LEASE_OWNER,
        purpose=LEASE_PURPOSE,
        path=root / LEASE_PATH,
    ):
        start = {
            "artifact_version": 1,
            "role": "v24303_paired_dev64_execution_start",
            "created_at_unix": int(time.time()),
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "activation_sha256": sha256(root / ACTIVATION),
            "runner": {
                "pid": os.getpid(),
                "start_ticks": _start_ticks(os.getpid()),
                "marker": RUNNER_MARKER,
            },
            "selected_per_arm": SELECTED_COUNT,
            "total_tasks": TOTAL_TASK_COUNT,
            "executor_concurrency_per_arm": EXECUTOR_CONCURRENCY_PER_ARM,
            "total_executor_concurrency": TOTAL_EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "protected_watchers": protected_watcher_snapshot(),
            "selected_opaque_ids_sha256": contract["task_contract"][
                "selected_opaque_ids_sha256"
            ],
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "api_called_before_execution_start": False,
        }
        start["execution_start_payload_sha256"] = payload_sha256(start)
        _new_json(root / EXECUTION_START, start)
        (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        _prepare_slots(root)
        (root / TASK_ROOT).mkdir(mode=0o700)
        for arm in ARMS:
            (root / TASK_ROOT / arm).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = execute_forward(
            root,
            contract,
            tasks,
            progress_writer=lambda value: _atomic_json(root / SAFE_PROGRESS, value),
        )
        wall = max(0.0, time.monotonic() - started)
    summaries: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        results = [outcome.result for outcome in outcomes[arm]]
        rows = [_runtime_row(result, arm) for result in results]
        _write_jsonl_new(root / RUNTIME_PREDICTIONS[arm], rows)
        summary = _summary(arm, results, rows, outcomes[arm], wall)
        summaries[arm] = summary
        _new_json(root / RUN_SUMMARY[arm], summary)
        freeze = {
            "artifact_version": 1,
            "role": "v24303_paired_dev64_prediction_freeze",
            "arm": arm,
            "protocol_id": PROTOCOL_ID,
            "selected": SELECTED_COUNT,
            "terminal": SELECTED_COUNT,
            "selected_opaque_ids_sha256": contract["task_contract"][
                "selected_opaque_ids_sha256"
            ],
            "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS[arm]),
            "run_summary_sha256": sha256(root / RUN_SUMMARY[arm]),
            "prediction_hashes_sha256": payload_sha256(
                [row["prediction_sha256"] for row in rows]
            ),
            "arm_terminal_before_mapping_gold_or_evaluator_open": True,
            "mapping_gold_or_evaluator_opened_or_hashed": False,
            "label_blind": True,
        }
        freeze["freeze_payload_sha256"] = payload_sha256(freeze)
        _new_json(root / PREDICTION_FREEZE[arm], freeze)
        validate_prediction_freeze(root, contract, arm, freeze)
    receipts: dict[str, dict[str, int | bool]] = {}
    for arm in ARMS:
        requests = sum(
            int(outcome.result["cost"]["model"]["requests"])
            for outcome in outcomes[arm]
        )
        acquisitions = sum(outcome.receipt_acquisitions for outcome in outcomes[arm])
        valid = sum(outcome.receipt_valid for outcome in outcomes[arm])
        receipts[arm] = {
            "children": SELECTED_COUNT,
            "present": sum(outcome.receipt_present for outcome in outcomes[arm]),
            "valid": valid,
            "invalid": SELECTED_COUNT - valid,
            "actual_model_requests": requests,
            "slot_acquisitions": acquisitions,
            "all_acquisitions_match_actual_requests": valid == SELECTED_COUNT
            and acquisitions == requests,
        }
    forward = {
        "artifact_version": 1,
        "role": "v24303_paired_dev64_forward_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected_per_arm": SELECTED_COUNT,
        "terminal_predictions_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "shared_forward_wall_seconds": round(wall, 6),
        "arm_summaries": {
            arm: {
                "model_generated_tables": summaries[arm]["model_generated_tables"],
                "fallback_tables": summaries[arm]["fallback_tables"],
                "system_total_tokens": summaries[arm]["system_total_tokens"],
                "task_wall_seconds_sum": summaries[arm]["task_wall_seconds_sum"],
                "mechanism_totals": summaries[arm]["mechanism_totals"],
            }
            for arm in ARMS
        },
        "prediction_freeze_sha256": {
            arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
        },
        "shared_model_receipts": receipts,
        "both_arms_exact64_before_mapping_gold_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
        "additional_rollout_resume_skip_or_rerun_launched": False,
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "activation_payload_sha256": activation["activation_payload_sha256"],
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    validate_forward_result(root, contract, forward)
    _new_json(root / FORWARD_RESULT, forward)
    _atomic_json(
        root / SAFE_PROGRESS,
        _progress({arm: SELECTED_COUNT for arm in ARMS}),
    )
    print(
        json.dumps(
            {
                "forward_result": str(FORWARD_RESULT),
                "terminal_per_arm": SELECTED_COUNT,
                "wall_seconds": wall,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
