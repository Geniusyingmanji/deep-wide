#!/usr/bin/env python3
"""Execute one cold, exact, label-blind V2.43.15 DeepWideBench rollout."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24267_total_fallback import build_total_fallback_result  # noqa: E402
from deepwide_agent.v24287_hard_deadline_fetch import validate_transport_health  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    TAXONOMY,
    coarse_exception_type,
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import run_observed_subprocess  # noqa: E402
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD as RECOVERY_RECEIPT_FIELD,
    parent_exit_receipt as recovery_parent_exit_receipt,
    validate_v24310_result,
    zero_effect_receipt,
)
from deepwide_agent.v24313_runner_integration import (  # noqa: E402
    validate_deadline_model_receipt as validate_receipt,
)
from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    ACTIVATION,
    ARM,
    CHILD_MARKER,
    CHILD_TERMINAL_NAME,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    OUTPUT_ROOT,
    PARENT_DEADLINE_GRACE_SECONDS,
    PARENT_EXIT_NAME,
    PREDICTION_FREEZE,
    PREAUDIT,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUNNER_MARKER,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    selected_tasks,
    sha256,
    validate_forward_contract,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


RECEIPT_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
MODEL_GENERATED = frozenset({"primary", "repaired", "normalized_primary", "normalized_repaired"})
PARENT_EXIT_TAXONOMY = frozenset(TAXONOMY)
MECHANISM_BOOL_FIELDS = frozenset(
    {
        "retrieval_completed",
        "controller_stop",
        "controller_expand",
        "reserved_stage_executed",
        "low_coverage_diversity_tail",
        "recovery_enabled",
        "effect_attribution_complete",
        "effect_count_complete",
        "provider_attempt_count_complete",
        "synthesis_initial_model_request_error",
        "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded",
        "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery",
        "fourth_model_effect",
    }
)
MECHANISM_COUNT_FIELDS = frozenset(
    {
        "selected_tail_count",
        "reserved_fetches",
        "reserved_usable_pages",
        "hosted_search_requests_added_by_reserved",
        "cache_miss_count",
        "cache_serve_network_fetches",
        "total_model_effects_lower_bound",
        "admitted_model_effects_upper_bound",
        "unattributed_model_effects",
    }
)


@dataclass(frozen=True)
class TaskOutcome:
    result: dict[str, Any]
    receipt_present: bool
    receipt_valid: bool
    receipt_acquisitions: int
    transport: dict[str, int]
    parent_exit: dict[str, Any] | None = None
    accepted_parent_success: bool = False


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _valid_parent_exit(value: dict[str, Any]) -> bool:
    try:
        validate_parent_receipt(value)
    except (KeyError, TypeError, ValueError):
        return False
    return True


def _new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _start_ticks(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    fields = raw[raw.rfind(")") + 2 :].split()
    return int(fields[19])


def validate_preaudit(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / PREAUDIT)
    if (
        value.get("role") != "v24315_exact220_preactivation_audit"
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("dependency_manifest_sha256") != contract["dependency_manifest_sha256"]
        or value.get("protected_watchers")
        != contract["execution"]["protected_watchers"]
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.15 preactivation audit drifted")
    return value


def validate_activation(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / ACTIVATION)
    preaudit = validate_preaudit(root, contract)
    if (
        value.get("role") != "v24315_exact220_activation"
        or value.get("status") != "active"
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("dependency_manifest_sha256") != contract["dependency_manifest_sha256"]
        or value.get("control_manifest_sha256") != preaudit["control_manifest_sha256"]
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers")
        != contract["execution"]["protected_watchers"]
        or value.get("shared_api_lease_active_before_activation") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("additional_rollout_avg4_leaderboard_or_sota_authorized") is not False
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.15 activation drifted")
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


def task_command(root: Path, task_root: Path) -> list[str]:
    return [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / CHILD_MARKER),
        "--task",
        str(task_root / "visible_task.json"),
        "--result",
        str(task_root / "result.json"),
        "--progress",
        str(task_root / "safe_progress.json"),
        "--model-slot-directory",
        str(root / MODEL_SLOT_DIRECTORY),
        "--model-slot-receipt",
        str(task_root / RECEIPT_NAME),
        "--transport-health",
        str(task_root / TRANSPORT_NAME),
        "--child-terminal-receipt",
        str(task_root / CHILD_TERMINAL_NAME),
    ]


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
    task: dict[str, str],
    *,
    kind: str,
    failure: str,
    elapsed: float,
    progress: dict[str, Any],
    recovery_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = build_total_fallback_result(
        task,
        limits=ScoreFirstLimits(**LIMITS),
        completion_kind=kind,
        failure_stage="v24315_parent_executor",
        failure_type=failure,
        elapsed_seconds=elapsed,
        last_progress=progress,
    )
    value[RECOVERY_RECEIPT_FIELD] = recovery_receipt or zero_effect_receipt(ARM)
    validate_v24310_result(value, ARM)
    return value


def _validate_task_envelope(
    value: dict[str, Any], directory: Path | None = None
) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("envelope_payload_sha256", None)
    health = value.get("transport_health")
    if (
        value.get("role") != "v24315_exact220_task_envelope"
        or value.get("arm") != ARM
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or not isinstance(health, dict)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.15 task envelope drifted")
    validate_transport_health(health)
    result = value["result"]
    validate_v24310_result(result, ARM)
    if directory is not None:
        receipt = validate_receipt(
            read_object(directory / RECEIPT_NAME),
            expected_cap=MODEL_SLOT_CAP,
            expected_acquisitions=int(result["cost"]["model"]["requests"]),
        )
        transport = validate_transport_health(read_object(directory / TRANSPORT_NAME))
        if value["transport_health"] != transport or not isinstance(receipt, dict):
            raise ValueError("V2.43.15 cross-artifact envelope drifted")


def run_one_task(
    root: Path,
    contract: dict[str, Any],
    task: dict[str, str],
    task_root: Path,
    *,
    popen: Any = subprocess.Popen,
) -> TaskOutcome:
    del contract
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    _new_json(task_root / "visible_task.json", task)
    observed = run_observed_subprocess(
        cwd=root,
        output_root=root / OUTPUT_ROOT,
        directory=task_root,
        command=task_command(root, task_root),
        environment=_child_env(),
        timeout_seconds=float(LIMITS["wall_seconds"])
        + PARENT_DEADLINE_GRACE_SECONDS,
        result_validator=lambda value: _validate_task_envelope(
            dict(value), task_root
        ),
        model_receipt_validator=lambda value: validate_receipt(
            dict(value), expected_cap=MODEL_SLOT_CAP
        ),
        transport_receipt_validator=lambda value: validate_transport_health(
            dict(value)
        ),
        result_name="result.json",
        model_receipt_name=RECEIPT_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name=CHILD_TERMINAL_NAME,
        parent_name=PARENT_EXIT_NAME,
        popen=popen,
    )
    parent_exit = observed.receipt
    elapsed = float(parent_exit["elapsed_seconds"])
    receipt_path = task_root / RECEIPT_NAME
    transport_path = task_root / TRANSPORT_NAME
    receipt: dict[str, Any] | None = None
    health = {"hard_fetch_helper_calls": 0, "hard_fetch_deadline_failures": 0, "fetch_helper_failures": 0}
    receipt_present = receipt_path.is_file() and not receipt_path.is_symlink()
    try:
        if receipt_present:
            receipt = validate_receipt(read_object(receipt_path), expected_cap=MODEL_SLOT_CAP)
    except (KeyError, OSError, TypeError, ValueError, RuntimeError):
        receipt = None
    try:
        if transport_path.is_file() and not transport_path.is_symlink():
            health = validate_transport_health(read_object(transport_path))
    except (OSError, ValueError, RuntimeError):
        health = {"hard_fetch_helper_calls": 0, "hard_fetch_deadline_failures": 0, "fetch_helper_failures": 0}
    accepted_parent_success = (
        parent_exit["failure_taxonomy"] == "success"
        and parent_exit["child_terminal_receipt_present"] is True
        and parent_exit["child_terminal_receipt_valid"] is True
        and observed.return_code == 0
        and observed.timed_out is False
        and observed.subprocess_exception is False
    )
    if accepted_parent_success and (task_root / "result.json").is_file():
        try:
            envelope = read_object(task_root / "result.json")
            _validate_task_envelope(envelope)
            if envelope.get("transport_health") != health:
                raise ValueError("V2.43.15 transport/envelope drifted")
            result = envelope["result"]
            validate_v24310_result(result, ARM)
            requests = int(result["cost"]["model"]["requests"])
            if receipt is None:
                raise ValueError("model-slot receipt absent")
            validate_receipt(receipt, expected_cap=MODEL_SLOT_CAP, expected_acquisitions=requests)
            return TaskOutcome(
                result,
                True,
                True,
                requests,
                health,
                parent_exit,
                True,
            )
        except (KeyError, OSError, TypeError, ValueError, RuntimeError):
            pass
    progress = _safe_progress(task_root / "safe_progress.json")
    progress_model = progress.get("model_cost")
    progress_model = progress_model if isinstance(progress_model, dict) else {}
    acquisitions = int(receipt.get("acquisitions", 0)) if receipt else 0
    request_lower = max(acquisitions, int(progress_model.get("requests", 0) or 0))
    attempt_lower = max(request_lower, int(progress_model.get("attempts", 0) or 0))
    admitted_upper = max(
        request_lower, int(progress.get("admitted_model_calls", 0) or 0)
    )
    admitted_upper = min(int(LIMITS["model_calls"]), admitted_upper)
    effect_complete = receipt is not None
    admitted_upper = request_lower if effect_complete else int(LIMITS["model_calls"])
    progress = dict(progress)
    progress["admitted_model_calls"] = request_lower
    progress["model_cost"] = {
        **{
            name: int(progress_model.get(name, 0) or 0)
            for name in (
                "requests",
                "attempts",
                "input_tokens",
                "output_tokens",
                "total_tokens",
            )
        },
        "requests": request_lower,
        "attempts": attempt_lower,
    }
    recovery_receipt = recovery_parent_exit_receipt(
        ARM,
        provider_requests_lower_bound=request_lower,
        provider_attempts_lower_bound=attempt_lower,
        admitted_model_effects_upper_bound=admitted_upper,
        effect_count_complete=effect_complete,
        provider_attempt_count_complete=False,
    )
    timed_out = parent_exit["failure_taxonomy"] == "hard_deadline_timeout"
    kind = "hard_deadline_fallback" if timed_out else "worker_failure_fallback"
    result = _fallback(
        task,
        kind=kind,
        failure=str(parent_exit["failure_taxonomy"]),
        elapsed=elapsed,
        progress=progress,
        recovery_receipt=recovery_receipt,
    )
    requests = int(result["cost"]["model"]["requests"])
    valid = False
    if receipt is not None:
        try:
            validate_receipt(receipt, expected_cap=MODEL_SLOT_CAP, expected_acquisitions=requests)
            valid = True
        except (KeyError, TypeError, ValueError):
            valid = False
    return TaskOutcome(
        result,
        receipt_present,
        valid,
        acquisitions,
        health,
        parent_exit,
    )


def _progress(completed: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24315_exact220_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "completed_predictions": completed,
        "unfinished_predictions": SELECTED_COUNT - completed,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
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
    completed = value.get("completed_predictions")
    unfinished = value.get("unfinished_predictions")
    if (
        value.get("role") != "v24315_exact220_safe_forward_progress"
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or not isinstance(completed, int)
        or not isinstance(unfinished, int)
        or min(completed, unfinished) < 0
        or completed + unfinished != SELECTED_COUNT
        or value.get("contains_question_query_url_page_prediction_answer_opaque_id_or_credential") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.15 safe progress drifted")


def execute_forward(
    root: Path,
    contract: dict[str, Any],
    tasks: list[dict[str, str]],
    *,
    task_runner: Callable[[Path, dict[str, Any], dict[str, str], Path], TaskOutcome] = run_one_task,
    progress_writer: Callable[[dict[str, Any]], None] | None = None,
) -> list[TaskOutcome]:
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.43.15 scheduler requires exactly 220 visible tasks")
    outcomes: dict[int, TaskOutcome] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=EXECUTOR_CONCURRENCY, thread_name_prefix="v24315-exact220"
    ) as executor:
        futures = {
            executor.submit(task_runner, root, contract, task, root / TASK_ROOT / f"task_{position:04d}"): position
            for position, task in enumerate(tasks, start=1)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            try:
                outcome = future.result()
                if not isinstance(outcome, TaskOutcome):
                    raise TypeError("task outcome drifted")
                validate_v24310_result(outcome.result, ARM)
            except BaseException as exc:
                task = tasks[position - 1]
                unknown_effects = recovery_parent_exit_receipt(
                    ARM,
                    provider_requests_lower_bound=0,
                    provider_attempts_lower_bound=0,
                    admitted_model_effects_upper_bound=int(LIMITS["model_calls"]),
                    effect_count_complete=False,
                    provider_attempt_count_complete=False,
                )
                outcome = TaskOutcome(
                    _fallback(
                        task,
                        kind="worker_failure_fallback",
                        failure=coarse_exception_type(exc),
                        elapsed=0.0,
                        progress={},
                        recovery_receipt=unknown_effects,
                    ),
                    False,
                    False,
                    0,
                    {"hard_fetch_helper_calls": 0, "hard_fetch_deadline_failures": 0, "fetch_helper_failures": 0},
                    None,
                )
            outcomes[position] = outcome
            if progress_writer is not None:
                progress_writer(_progress(len(outcomes)))
    ordered = [outcomes[position] for position in range(1, SELECTED_COUNT + 1)]
    if [item.result["opaque_id"] for item in ordered] != [task["opaque_id"] for task in tasks]:
        raise RuntimeError("V2.43.15 scheduler result order drifted")
    return ordered


def _mechanism_telemetry(result: dict[str, Any]) -> dict[str, Any]:
    retrieval = result.get("staged_reserve_retrieval") or {}
    receipt = retrieval.get("receipt") if retrieval.get("status") == "completed" else None
    controller = (receipt or {}).get("controller") or {}
    stage = (receipt or {}).get("reserved_stage") or {}
    recovery = result.get(RECOVERY_RECEIPT_FIELD) or {}
    return {
        "retrieval_completed": receipt is not None,
        "controller_stop": bool(receipt and controller.get("decision") == "stop"),
        "controller_expand": bool(receipt and controller.get("decision") == "expand"),
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
        "effect_attribution_complete": bool(
            recovery.get("effect_attribution_complete")
        ),
        "effect_count_complete": bool(recovery.get("effect_count_complete")),
        "provider_attempt_count_complete": bool(
            recovery.get("provider_attempt_count_complete")
        ),
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
        "total_model_effects_lower_bound": int(
            recovery.get("total_effects_admitted", 0) or 0
        ),
        "admitted_model_effects_upper_bound": int(
            recovery.get("admitted_model_effects_upper_bound", 0) or 0
        ),
        "unattributed_model_effects": int(
            recovery.get("unattributed_model_effects", 0) or 0
        ),
    }


def _runtime_row(result: dict[str, Any]) -> dict[str, Any]:
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
        "mechanism_telemetry": _mechanism_telemetry(result),
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    validate_runtime_row(value)
    return value


def validate_runtime_row(value: dict[str, Any]) -> None:
    prediction = value.get("prediction")
    elapsed = value.get("elapsed_seconds")
    cost = value.get("cost")
    telemetry = value.get("mechanism_telemetry")
    expected_cost = {
        "model_calls", "model_successful_calls", "model_failed_calls", "model_attempts",
        "input_tokens", "output_tokens", "total_tokens", "search_calls", "search_failures",
        "search_tool_calls", "search_fetch_calls", "search_fetch_failures", "search_input_tokens",
        "search_output_tokens", "search_total_tokens", "system_total_tokens",
    }
    if (
        set(value) != {"opaque_id", "status", "prediction", "prediction_sha256", "completion_kind", "elapsed_seconds", "cost", "mechanism_telemetry", "label_blind", "mapping_gold_category_question_type_split_evaluator_score_read"}
        or value.get("status") != "completed"
        or not isinstance(value.get("opaque_id"), str)
        or not isinstance(prediction, str)
        or not prediction
        or hashlib.sha256(prediction.encode()).hexdigest() != value.get("prediction_sha256")
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or not isinstance(cost, dict)
        or set(cost) != expected_cost
        or any(isinstance(number, bool) or not isinstance(number, int) or number < 0 for number in cost.values())
        or not isinstance(telemetry, dict)
        or set(telemetry) != MECHANISM_BOOL_FIELDS | MECHANISM_COUNT_FIELDS
        or any(not isinstance(telemetry[name], bool) for name in MECHANISM_BOOL_FIELDS)
        or any(
            isinstance(telemetry[name], bool)
            or not isinstance(telemetry[name], int)
            or telemetry[name] < 0
            for name in MECHANISM_COUNT_FIELDS
        )
        or telemetry["controller_stop"] + telemetry["controller_expand"]
        != int(telemetry["retrieval_completed"])
        or telemetry["low_coverage_diversity_tail"]
        and not telemetry["reserved_stage_executed"]
        or telemetry["hosted_search_requests_added_by_reserved"] != 0
        or telemetry["recovery_enabled"] is not True
        or telemetry["fourth_model_effect"]
        or telemetry["total_model_effects_lower_bound"] > 3
        or telemetry["admitted_model_effects_upper_bound"] > 3
        or telemetry["total_model_effects_lower_bound"]
        > telemetry["admitted_model_effects_upper_bound"]
        or telemetry["effect_count_complete"]
        and telemetry["total_model_effects_lower_bound"]
        != telemetry["admitted_model_effects_upper_bound"]
        or telemetry["effect_attribution_complete"]
        and not telemetry["effect_count_complete"]
        or telemetry["effect_attribution_complete"]
        and telemetry["unattributed_model_effects"] != 0
        or value.get("label_blind") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
    ):
        raise RuntimeError("V2.43.15 runtime row drifted")


def _summary(results: list[dict[str, Any]], outcomes: list[TaskOutcome], wall_seconds: float) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    for result in results:
        kinds[result["completion_kind"]] = kinds.get(result["completion_kind"], 0) + 1
    valid_parent_exits = [
        item.parent_exit
        for item in outcomes
        if isinstance(item.parent_exit, dict) and _valid_parent_exit(item.parent_exit)
    ]
    taxonomy = {
        name: sum(receipt.get("failure_taxonomy") == name for receipt in valid_parent_exits)
        for name in PARENT_EXIT_TAXONOMY
    }
    rows = [_runtime_row(result) for result in results]
    fields = MECHANISM_BOOL_FIELDS | MECHANISM_COUNT_FIELDS
    value = {
        "artifact_version": 1,
        "role": "v24315_exact220_run_summary",
        "selected": SELECTED_COUNT,
        "completed": SELECTED_COUNT,
        "failed": 0,
        "model_generated_tables": sum(result["completion_kind"] in MODEL_GENERATED for result in results),
        "fallback_tables": sum(result["completion_kind"] not in MODEL_GENERATED for result in results),
        "completion_kinds": kinds,
        "system_total_tokens": sum(int(result["cost"]["system_total_tokens"]) for result in results),
        "task_wall_seconds_sum": round(sum(float(result["budget"]["elapsed_seconds"]) for result in results), 6),
        "forward_wall_seconds": round(max(0.0, wall_seconds), 6),
        "hard_fetch_helper_calls": sum(item.transport["hard_fetch_helper_calls"] for item in outcomes),
        "hard_fetch_deadline_failures": sum(item.transport["hard_fetch_deadline_failures"] for item in outcomes),
        "fetch_helper_failures": sum(item.transport["fetch_helper_failures"] for item in outcomes),
        "parent_exit_observability": {
            "receipts_present": sum(isinstance(item.parent_exit, dict) for item in outcomes),
            "receipts_valid": len(valid_parent_exits),
            "valid_child_terminal_receipts": sum(
                receipt.get("child_terminal_receipt_present") is True
                and receipt.get("child_terminal_receipt_valid") is True
                for receipt in valid_parent_exits
            ),
            "model_slot_receipts_present": sum(item.receipt_present for item in outcomes),
            "valid_model_slot_receipts": sum(item.receipt_valid for item in outcomes),
            "valid_transport_receipts": sum(
                receipt.get("transport_receipt_present") is True
                and receipt.get("transport_receipt_valid") is True
                for receipt in valid_parent_exits
            ),
            "taxonomy": taxonomy,
            "accepted_parent_successes": sum(item.accepted_parent_success for item in outcomes),
            "non_success_parent_exits": SELECTED_COUNT
            - sum(item.accepted_parent_success for item in outcomes),
            "incomplete_effect_counts": sum(
                not bool(
                    item.result.get(RECOVERY_RECEIPT_FIELD, {}).get(
                        "effect_count_complete"
                    )
                )
                for item in outcomes
            ),
        },
        "mechanism_totals": {
            name: sum(int(row["mechanism_telemetry"][name]) for row in rows)
            for name in fields
        },
        "label_blind": True,
        "official_evaluator_called": False,
    }
    validate_summary(value)
    return value


def validate_summary(value: dict[str, Any]) -> None:
    mechanism = value.get("mechanism_totals")
    observability = value.get("parent_exit_observability")
    numeric = (
        "system_total_tokens",
        "task_wall_seconds_sum",
        "forward_wall_seconds",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_helper_failures",
    )
    if (
        value.get("role") != "v24315_exact220_run_summary"
        or value.get("selected") != SELECTED_COUNT
        or value.get("completed") != SELECTED_COUNT
        or value.get("failed") != 0
        or value.get("model_generated_tables", -1) + value.get("fallback_tables", -1) != SELECTED_COUNT
        or sum((value.get("completion_kinds") or {}).values()) != SELECTED_COUNT
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in numeric
        )
        or value["hard_fetch_deadline_failures"] + value["fetch_helper_failures"]
        > value["hard_fetch_helper_calls"]
        or not isinstance(mechanism, dict)
        or set(mechanism) != MECHANISM_BOOL_FIELDS | MECHANISM_COUNT_FIELDS
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for number in mechanism.values()
        )
        or mechanism.get("controller_stop", 0)
        + mechanism.get("controller_expand", 0)
        != mechanism.get("retrieval_completed", 0)
        or mechanism.get("hosted_search_requests_added_by_reserved", 0) != 0
        or mechanism.get("recovery_enabled") != SELECTED_COUNT
        or mechanism.get("effect_attribution_complete", 0)
        > mechanism.get("effect_count_complete", 0)
        or mechanism.get("provider_attempt_count_complete", 0)
        > mechanism.get("effect_count_complete", 0)
        or mechanism.get("total_model_effects_lower_bound", 0)
        > mechanism.get("admitted_model_effects_upper_bound", 0)
        or not isinstance(observability, dict)
        or not isinstance(observability.get("receipts_present"), int)
        or not 0 <= observability["receipts_present"] <= SELECTED_COUNT
        or not isinstance(observability.get("receipts_valid"), int)
        or not 0 <= observability["receipts_valid"] <= observability["receipts_present"]
        or not isinstance(observability.get("valid_child_terminal_receipts"), int)
        or not 0 <= observability["valid_child_terminal_receipts"] <= observability["receipts_valid"]
        or not isinstance(observability.get("model_slot_receipts_present"), int)
        or not isinstance(observability.get("valid_model_slot_receipts"), int)
        or not 0 <= observability["valid_model_slot_receipts"] <= observability["model_slot_receipts_present"] <= observability["receipts_present"]
        or not isinstance(observability.get("valid_transport_receipts"), int)
        or not 0 <= observability["valid_transport_receipts"] <= observability["receipts_valid"]
        or not isinstance(observability.get("incomplete_effect_counts"), int)
        or observability.get("incomplete_effect_counts")
        != SELECTED_COUNT - mechanism.get("effect_count_complete", -1)
        or not isinstance(observability.get("accepted_parent_successes"), int)
        or not isinstance(observability.get("non_success_parent_exits"), int)
        or observability.get("non_success_parent_exits")
        != SELECTED_COUNT - observability.get("accepted_parent_successes", -1)
        or not isinstance(observability.get("taxonomy"), dict)
        or set(observability["taxonomy"]) != PARENT_EXIT_TAXONOMY
        or sum(observability["taxonomy"].values()) != observability["receipts_valid"]
        or observability["accepted_parent_successes"]
        > observability["taxonomy"].get("success", 0)
        or value.get("label_blind") is not True
        or value.get("official_evaluator_called") is not False
    ):
        raise RuntimeError("V2.43.15 run summary drifted")


def validate_prediction_freeze(root: Path, contract: dict[str, Any], value: dict[str, Any]) -> list[dict[str, Any]]:
    unsigned = dict(value)
    seal = unsigned.pop("freeze_payload_sha256", None)
    expected_keys = {
        "artifact_version", "role", "protocol_id", "selected", "terminal",
        "selected_opaque_ids_sha256", "runtime_predictions_sha256", "run_summary_sha256",
        "prediction_hashes_sha256", "exact_terminal_before_mapping_gold_or_evaluator_open",
        "mapping_gold_or_evaluator_opened_or_hashed", "label_blind", "freeze_payload_sha256",
    }
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v24315_exact220_prediction_freeze"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal") != SELECTED_COUNT
        or value.get("selected_opaque_ids_sha256") != contract["task_contract"]["selected_opaque_ids_sha256"]
        or value.get("runtime_predictions_sha256") != sha256(root / RUNTIME_PREDICTIONS)
        or value.get("run_summary_sha256") != sha256(root / RUN_SUMMARY)
        or value.get("exact_terminal_before_mapping_gold_or_evaluator_open") is not True
        or value.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or value.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.15 prediction freeze drifted")
    rows = [json.loads(line) for line in (root / RUNTIME_PREDICTIONS).read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != SELECTED_COUNT:
        raise RuntimeError("V2.43.15 prediction freeze row count drifted")
    for row in rows:
        validate_runtime_row(row)
    if (
        payload_sha256([row["opaque_id"] for row in rows]) != contract["task_contract"]["selected_opaque_ids_sha256"]
        or payload_sha256([row["prediction_sha256"] for row in rows]) != value.get("prediction_hashes_sha256")
    ):
        raise RuntimeError("V2.43.15 prediction freeze vector drifted")
    validate_summary(read_object(root / RUN_SUMMARY))
    return rows


def validate_forward_result(root: Path, contract: dict[str, Any], value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    expected_keys = {
        "artifact_version", "role", "protocol_id", "created_at_unix", "selected",
        "terminal_predictions", "model_generated_tables", "fallback_tables",
        "system_total_tokens", "forward_wall_seconds", "prediction_freeze_sha256",
        "shared_model_receipts", "mechanism_totals", "parent_exit_observability",
        "exact220_terminal_before_evaluator_open",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "official_evaluator_called", "additional_rollout_or_rerun_launched",
        "execution_start_sha256", "activation_payload_sha256", "result_payload_sha256",
    }
    validate_activation(root, contract)
    execution = read_object(root / EXECUTION_START)
    execution_unsigned = dict(execution)
    execution_seal = execution_unsigned.pop("execution_start_payload_sha256", None)
    runner = execution.get("runner") or {}
    if (
        execution.get("role") != "v24315_exact220_execution_start"
        or execution.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or execution.get("activation_sha256") != sha256(root / ACTIVATION)
        or execution.get("selected") != SELECTED_COUNT
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("protected_watchers")
        != contract["execution"]["protected_watchers"]
        or execution.get("selected_opaque_ids_sha256")
        != contract["task_contract"]["selected_opaque_ids_sha256"]
        or runner.get("marker") != RUNNER_MARKER
        or not isinstance(runner.get("pid"), int)
        or runner.get("pid", 0) <= 0
        or not isinstance(runner.get("start_ticks"), int)
        or runner.get("start_ticks", -1) < 0
        or execution.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or execution.get("api_called_before_execution_start") is not False
        or execution_seal != payload_sha256(execution_unsigned)
    ):
        raise RuntimeError("V2.43.15 execution start drifted")
    freeze = read_object(root / PREDICTION_FREEZE)
    validate_prediction_freeze(root, contract, freeze)
    summary = read_object(root / RUN_SUMMARY)
    observability = summary["parent_exit_observability"]
    mechanism = summary["mechanism_totals"]
    receipts = value.get("shared_model_receipts") or {}
    receipt_numbers = [
        receipts.get(name)
        for name in ("children", "present", "valid", "invalid", "actual_model_requests", "slot_acquisitions")
    ]
    receipt_health = (
        receipts.get("children") == SELECTED_COUNT
        and isinstance(receipts.get("present"), int)
        and isinstance(receipts.get("valid"), int)
        and isinstance(receipts.get("invalid"), int)
        and 0 <= receipts["valid"] <= receipts["present"] <= SELECTED_COUNT
        and receipts["invalid"] == SELECTED_COUNT - receipts["valid"]
        and receipts["slot_acquisitions"] == receipts["actual_model_requests"]
        and receipts["valid"] == SELECTED_COUNT
        and receipts["actual_model_requests"]
        == mechanism["total_model_effects_lower_bound"]
    )
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v24315_exact220_forward_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal_predictions") != SELECTED_COUNT
        or value.get("model_generated_tables") != summary["model_generated_tables"]
        or value.get("fallback_tables") != summary["fallback_tables"]
        or value.get("system_total_tokens") != summary["system_total_tokens"]
        or value.get("forward_wall_seconds") != summary["forward_wall_seconds"]
        or value.get("parent_exit_observability") != observability
        or value.get("mechanism_totals") != mechanism
        or observability.get("receipts_present") != SELECTED_COUNT
        or observability.get("receipts_valid") != SELECTED_COUNT
        or observability.get("valid_child_terminal_receipts") != SELECTED_COUNT
        or observability.get("valid_model_slot_receipts") != SELECTED_COUNT
        or observability.get("valid_transport_receipts") != SELECTED_COUNT
        or observability.get("non_success_parent_exits") != 0
        or observability.get("incomplete_effect_counts") != 0
        or mechanism.get("effect_count_complete") != SELECTED_COUNT
        or mechanism.get("fourth_model_effect") != 0
        or value.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or value.get("exact220_terminal_before_evaluator_open") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("additional_rollout_or_rerun_launched") is not False
        or value.get("execution_start_sha256") != sha256(root / EXECUTION_START)
        or value.get("activation_payload_sha256")
        != read_object(root / ACTIVATION).get("activation_payload_sha256")
        or any(isinstance(number, bool) or not isinstance(number, int) or number < 0 for number in receipt_numbers)
        or receipts.get("children") != SELECTED_COUNT
        or receipts.get("present", SELECTED_COUNT + 1) > SELECTED_COUNT
        or receipts.get("valid", SELECTED_COUNT + 1) > receipts.get("present", -1)
        or receipts.get("invalid") != SELECTED_COUNT - receipts.get("valid", -1)
        or receipts.get("all_acquisitions_match_actual_requests") != receipt_health
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.15 forward result drifted")


def _prepare_slots(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {"artifact_version": 1, "role": "v24315_model_slot", "pool_id": POOL_ID, "slot": index, "slot_cap": MODEL_SLOT_CAP, "contains_credential_or_benchmark_content": False},
        )


def main() -> None:
    root = ROOT
    contract = validate_forward_contract(root)
    validate_preaudit(root, contract)
    activation = validate_activation(root, contract)
    tasks = selected_tasks(root, contract)
    for path in (root / EXECUTION_START, root / FORWARD_RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.43.15 forward surface is not pristine")
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        start = {
            "artifact_version": 1,
            "role": "v24315_exact220_execution_start",
            "created_at_unix": int(time.time()),
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "activation_sha256": sha256(root / ACTIVATION),
            "runner": {"pid": os.getpid(), "start_ticks": _start_ticks(os.getpid()), "marker": RUNNER_MARKER},
            "selected": SELECTED_COUNT,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "protected_watchers": protected_watcher_snapshot(),
            "selected_opaque_ids_sha256": contract["task_contract"]["selected_opaque_ids_sha256"],
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "api_called_before_execution_start": False,
        }
        start["execution_start_payload_sha256"] = payload_sha256(start)
        _new_json(root / EXECUTION_START, start)
        (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        _prepare_slots(root)
        (root / TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = execute_forward(
            root,
            contract,
            tasks,
            progress_writer=lambda value: _atomic_json(root / SAFE_PROGRESS, value),
        )
        wall = max(0.0, time.monotonic() - started)
    results = [outcome.result for outcome in outcomes]
    rows = [_runtime_row(result) for result in results]
    _write_jsonl_new(root / RUNTIME_PREDICTIONS, rows)
    summary = _summary(results, outcomes, wall)
    _new_json(root / RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24315_exact220_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "selected": SELECTED_COUNT,
        "terminal": SELECTED_COUNT,
        "selected_opaque_ids_sha256": contract["task_contract"]["selected_opaque_ids_sha256"],
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "run_summary_sha256": sha256(root / RUN_SUMMARY),
        "prediction_hashes_sha256": payload_sha256([row["prediction_sha256"] for row in rows]),
        "exact_terminal_before_mapping_gold_or_evaluator_open": True,
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = payload_sha256(freeze)
    _new_json(root / PREDICTION_FREEZE, freeze)
    validate_prediction_freeze(root, contract, freeze)
    requests = sum(int(result["cost"]["model"]["requests"]) for result in results)
    acquisitions = sum(item.receipt_acquisitions for item in outcomes)
    valid = sum(item.receipt_valid for item in outcomes)
    forward = {
        "artifact_version": 1,
        "role": "v24315_exact220_forward_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "terminal_predictions": SELECTED_COUNT,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "system_total_tokens": summary["system_total_tokens"],
        "forward_wall_seconds": summary["forward_wall_seconds"],
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "mechanism_totals": summary["mechanism_totals"],
        "parent_exit_observability": summary["parent_exit_observability"],
        "shared_model_receipts": {
            "children": SELECTED_COUNT,
            "present": sum(item.receipt_present for item in outcomes),
            "valid": valid,
            "invalid": SELECTED_COUNT - valid,
            "actual_model_requests": requests,
            "slot_acquisitions": acquisitions,
            "all_acquisitions_match_actual_requests": valid == SELECTED_COUNT and acquisitions == requests,
        },
        "exact220_terminal_before_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
        "additional_rollout_or_rerun_launched": False,
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "activation_payload_sha256": activation["activation_payload_sha256"],
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    validate_forward_result(root, contract, forward)
    _new_json(root / FORWARD_RESULT, forward)
    _atomic_json(root / SAFE_PROGRESS, _progress(SELECTED_COUNT))
    print(json.dumps({"forward_result": str(FORWARD_RESULT), "terminal": SELECTED_COUNT, "wall_seconds": wall}, sort_keys=True))


if __name__ == "__main__":
    main()
