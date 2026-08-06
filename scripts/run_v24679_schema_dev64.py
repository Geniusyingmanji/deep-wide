#!/usr/bin/env python3
"""Run one fresh label-blind V2.46.79 paired dev64 forward."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    validate_receipt as validate_single,
)
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    coarse_exception_type,
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_observed_subprocess,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model,
)
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24318_deadline_conservation_runtime import (  # noqa: E402
    validate_v24318_result,
)
from deepwide_agent.v24319_runner_integration import (  # noqa: E402
    project_parent_failure,
    validate_projected_parent_result,
)
from deepwide_agent.v24630_exact220_task_integration import (  # noqa: E402
    validate_cross_artifacts,
    validate_envelope as validate_baseline_envelope,
)
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    validate_receipt as validate_backfill,
)
from deepwide_agent.v24677_expanded_visible_schema_runtime import (  # noqa: E402
    validate_envelope as validate_candidate_envelope,
)
from deepwide_agent.v24679_schema_dev64_contract import (  # noqa: E402
    ACTIVATION,
    ARMS,
    CHILD_MARKER,
    CHILD_TERMINAL_NAME,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    EXPECTED_TREATED_COUNT,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT_ROOT,
    PAIR_SUMMARY,
    PARENT_EXIT_NAME,
    PARENT_TIMEOUT_SECONDS,
    PREAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SELECTED_COUNT,
    TASK_ROOT,
    TOTAL_CHILD_RUNS,
    is_treated_task,
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
SINGLE_NAME = "search_single_shot_receipt.json"
BACKFILL_NAME = "citation_title_backfill_receipt.json"
PROGRESS_NAME = "safe_progress.json"
MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)
COST_FIELDS = (
    "model_calls",
    "model_attempts",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "search_calls",
    "search_failures",
    "search_tool_calls",
    "search_fetch_calls",
    "search_fetch_failures",
    "search_input_tokens",
    "search_output_tokens",
    "search_total_tokens",
    "system_total_tokens",
)


@dataclass(frozen=True)
class TaskOutcome:
    arm: str
    position: int
    task: dict[str, str]
    result: dict[str, Any]
    parent_exit: dict[str, Any] | None
    accepted_parent_success: bool
    model_receipt_valid: bool
    model_acquisitions: int
    model_slot_timeouts: int
    transport_receipt_valid: bool
    transport: dict[str, Any]
    single_receipt_valid: bool
    backfill_receipt_valid: bool


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _empty_transport() -> dict[str, Any]:
    return validate_transport_health(
        {
            "hosted_search_attempts": 0,
            "hosted_search_deadline_failures": 0,
            "hard_fetch_helper_calls": 0,
            "hard_fetch_deadline_failures": 0,
            "fetch_deadline_rejections": 0,
            "fetch_helper_failures": 0,
            "deadline_exhausted": False,
        }
    )


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


def _safe_progress(path: Path) -> dict[str, Any]:
    try:
        value = read_object(path)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
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
    failure: str,
    elapsed: float,
    progress: dict[str, Any],
    model_receipt: dict[str, Any] | None,
    timed_out: bool,
) -> dict[str, Any]:
    value = project_parent_failure(
        task,
        limits=ScoreFirstLimits(**LIMITS),
        completion_kind=(
            "hard_deadline_fallback" if timed_out else "worker_failure_fallback"
        ),
        failure_type=failure,
        elapsed_seconds=elapsed,
        progress=progress,
        model_slot_receipt=model_receipt,
        expected_cap=MODEL_SLOT_CAP,
    )
    validate_projected_parent_result(value)
    return value


def task_command(root: Path, directory: Path, arm: str) -> list[str]:
    return [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / CHILD_MARKER),
        "--arm",
        arm,
        "--task",
        str(directory / "visible_task.json"),
        "--result",
        str(directory / "result.json"),
        "--progress",
        str(directory / PROGRESS_NAME),
        "--model-slot-directory",
        str(root / MODEL_SLOT_DIRECTORY),
        "--model-slot-receipt",
        str(directory / RECEIPT_NAME),
        "--transport-health",
        str(directory / TRANSPORT_NAME),
        "--search-single-shot-receipt",
        str(directory / SINGLE_NAME),
        "--citation-title-backfill-receipt",
        str(directory / BACKFILL_NAME),
        "--child-terminal-receipt",
        str(directory / CHILD_TERMINAL_NAME),
    ]


def _validate_bundle(value: Mapping[str, Any], directory: Path, arm: str) -> dict[str, Any]:
    envelope = (
        validate_baseline_envelope(value)
        if arm == "baseline"
        else validate_candidate_envelope(value)
    )
    model = validate_model(
        read_object(directory / RECEIPT_NAME), expected_cap=MODEL_SLOT_CAP
    )
    transport = validate_transport_health(read_object(directory / TRANSPORT_NAME))
    single = read_object(directory / SINGLE_NAME)
    backfill = read_object(directory / BACKFILL_NAME)
    validate_single(single)
    validate_backfill(backfill)
    validate_cross_artifacts(
        envelope["result"],
        arm="baseline",
        model_slot_receipt=model,
        transport_health=transport,
        search_single_shot_receipt=single,
        citation_title_backfill_receipt=backfill,
        expected_cap=MODEL_SLOT_CAP,
    )
    if (
        envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != single
        or envelope["citation_title_backfill_receipt"] != backfill
    ):
        raise ValueError("V2.46.79 independent child artifacts drifted")
    if arm == "candidate" and envelope["schema_transition_receipt"].get(
        "incremental_schema_applied"
    ) is not True:
        raise ValueError("V2.46.79 candidate treatment did not activate")
    return envelope


def run_one_task(
    root: Path,
    position: int,
    task: dict[str, str],
    arm: str,
    directory: Path,
    *,
    popen: Any = subprocess.Popen,
) -> TaskOutcome:
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    _new_json(directory / "visible_task.json", task)
    observed = run_observed_subprocess(
        cwd=root,
        output_root=root / OUTPUT_ROOT,
        directory=directory,
        command=task_command(root, directory, arm),
        environment=_child_env(),
        timeout_seconds=PARENT_TIMEOUT_SECONDS,
        result_validator=lambda value: _validate_bundle(dict(value), directory, arm),
        model_receipt_validator=lambda value: validate_model(
            dict(value), expected_cap=MODEL_SLOT_CAP
        ),
        transport_receipt_validator=lambda value: validate_transport_health(dict(value)),
        result_name="result.json",
        model_receipt_name=RECEIPT_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name=CHILD_TERMINAL_NAME,
        parent_name=PARENT_EXIT_NAME,
        popen=popen,
    )
    parent = validate_parent_receipt(observed.receipt)
    model_value: dict[str, Any] | None = None
    transport = _empty_transport()
    transport_valid = False
    single_valid = backfill_valid = False
    try:
        model_value = validate_model(
            read_object(directory / RECEIPT_NAME), expected_cap=MODEL_SLOT_CAP
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        pass
    try:
        transport = validate_transport_health(read_object(directory / TRANSPORT_NAME))
        transport_valid = True
    except (OSError, RuntimeError, TypeError, ValueError):
        pass
    try:
        validate_single(read_object(directory / SINGLE_NAME))
        single_valid = True
    except (OSError, RuntimeError, TypeError, ValueError):
        pass
    try:
        validate_backfill(read_object(directory / BACKFILL_NAME))
        backfill_valid = True
    except (OSError, RuntimeError, TypeError, ValueError):
        pass
    accepted = (
        parent["failure_taxonomy"] == "success"
        and observed.return_code == 0
        and observed.timed_out is False
        and observed.subprocess_exception is False
        and model_value is not None
        and transport_valid
        and single_valid
        and backfill_valid
    )
    if accepted:
        try:
            envelope = _validate_bundle(read_object(directory / "result.json"), directory, arm)
            result = dict(envelope["result"])
            validate_v24318_result(result, "baseline")
            if result.get("opaque_id") != task["opaque_id"]:
                raise ValueError("V2.46.79 child result identity drifted")
            return TaskOutcome(
                arm,
                position,
                dict(task),
                result,
                parent,
                True,
                True,
                int(model_value["acquisitions"]),
                int(model_value["slot_timeouts"]),
                True,
                transport,
                True,
                True,
            )
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            accepted = False
    progress = _safe_progress(directory / PROGRESS_NAME)
    result = _fallback(
        task,
        failure=str(parent["failure_taxonomy"]),
        elapsed=float(parent["elapsed_seconds"]),
        progress=progress,
        model_receipt=model_value,
        timed_out=parent["failure_taxonomy"] == "hard_deadline_timeout",
    )
    return TaskOutcome(
        arm,
        position,
        dict(task),
        result,
        parent,
        False,
        model_value is not None,
        int(model_value.get("acquisitions", 0)) if model_value else 0,
        int(model_value.get("slot_timeouts", 0)) if model_value else 0,
        transport_valid,
        transport,
        single_valid,
        backfill_valid,
    )


def _exception_outcome(
    position: int, task: dict[str, str], arm: str, error: BaseException
) -> TaskOutcome:
    result = _fallback(
        task,
        failure=coarse_exception_type(error),
        elapsed=0.0,
        progress={},
        model_receipt=None,
        timed_out=False,
    )
    return TaskOutcome(
        arm,
        position,
        dict(task),
        result,
        None,
        False,
        False,
        0,
        0,
        False,
        _empty_transport(),
        False,
        False,
    )


def execute_batch(
    root: Path,
    tasks: list[dict[str, str]],
    jobs: list[tuple[int, dict[str, str], str]],
    *,
    task_runner: Callable[..., TaskOutcome] = run_one_task,
    completed_offset: int = 0,
) -> dict[int, TaskOutcome]:
    output: dict[int, TaskOutcome] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=EXECUTOR_CONCURRENCY, thread_name_prefix="v24679-dev64"
    ) as executor:
        futures = {
            executor.submit(
                task_runner,
                root,
                position,
                task,
                arm,
                root / TASK_ROOT / arm / f"task_{position:04d}",
            ): (position, task, arm)
            for position, task, arm in jobs
        }
        for future in concurrent.futures.as_completed(futures):
            position, task, arm = futures[future]
            try:
                value = future.result()
                if (
                    not isinstance(value, TaskOutcome)
                    or value.position != position
                    or value.arm != arm
                    or value.task != task
                    or value.result.get("opaque_id") != task["opaque_id"]
                ):
                    raise TypeError("V2.46.79 outcome identity drifted")
            except BaseException as error:
                value = _exception_outcome(position, task, arm, error)
            output[position] = value
            _atomic_json(root / SAFE_PROGRESS, _progress(completed_offset + len(output)))
    return output


def execute_forward(
    root: Path,
    tasks: list[dict[str, str]],
    *,
    task_runner: Callable[..., TaskOutcome] = run_one_task,
) -> tuple[list[TaskOutcome], list[TaskOutcome]]:
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.46.79 requires exact dev64 tasks")
    baseline_jobs = [
        (position, task, "baseline")
        for position, task in enumerate(tasks, start=1)
    ]
    baseline = execute_batch(root, tasks, baseline_jobs, task_runner=task_runner)
    treated_jobs = [
        (position, task, "candidate")
        for position, task in enumerate(tasks, start=1)
        if is_treated_task(task)
    ]
    if len(treated_jobs) != EXPECTED_TREATED_COUNT:
        raise RuntimeError("V2.46.79 treated task count drifted")
    treated = execute_batch(
        root,
        tasks,
        treated_jobs,
        task_runner=task_runner,
        completed_offset=SELECTED_COUNT,
    )
    baseline_ordered = [baseline[position] for position in range(1, SELECTED_COUNT + 1)]
    candidate: list[TaskOutcome] = []
    for position, task in enumerate(tasks, start=1):
        if position in treated:
            candidate.append(treated[position])
        else:
            parent = baseline[position]
            candidate.append(
                TaskOutcome(
                    "candidate",
                    position,
                    dict(task),
                    parent.result,
                    parent.parent_exit,
                    parent.accepted_parent_success,
                    parent.model_receipt_valid,
                    parent.model_acquisitions,
                    parent.model_slot_timeouts,
                    parent.transport_receipt_valid,
                    parent.transport,
                    parent.single_receipt_valid,
                    parent.backfill_receipt_valid,
                )
            )
    return baseline_ordered, candidate


def _runtime_row(outcome: TaskOutcome, *, reused: bool) -> dict[str, Any]:
    result = outcome.result
    if outcome.accepted_parent_success:
        validate_v24318_result(result, "baseline")
    else:
        validate_projected_parent_result(result)
    if result.get("opaque_id") != outcome.task.get("opaque_id"):
        raise ValueError("V2.46.79 runtime result identity drifted")
    model = result["cost"]["model"]
    search = result["cost"]["search"]
    accepted = outcome.accepted_parent_success
    prediction = str(result["prediction"])
    failure = None
    if not accepted:
        parent_taxonomy = (
            str(outcome.parent_exit["failure_taxonomy"])
            if outcome.parent_exit
            else "local_orchestration_failure"
        )
        failure = (
            "invalid_or_incomplete_child_bundle"
            if parent_taxonomy == "success"
            else parent_taxonomy
        )
    value = {
        "opaque_id": result["opaque_id"],
        "arm": outcome.arm,
        "status": "completed",
        "prediction": prediction,
        "prediction_sha256": str(result["prediction_sha256"]),
        "completion_kind": result["completion_kind"],
        "forward_success": accepted,
        "error": failure,
        "elapsed_seconds": float(result["budget"]["elapsed_seconds"]),
        "cost": {
            "model_calls": int(model["requests"]),
            "model_attempts": int(model["attempts"]),
            "input_tokens": int(model["input_tokens"]),
            "output_tokens": int(model["output_tokens"]),
            "total_tokens": int(model["total_tokens"]),
            "search_calls": int(search["calls"]),
            "search_failures": int(search["failures"]),
            "search_tool_calls": int(search["tool_calls"]),
            "search_fetch_calls": int(search["fetch_calls"]),
            "search_fetch_failures": int(search["fetch_failures"]),
            "search_input_tokens": int(search["input_tokens"]),
            "search_output_tokens": int(search["output_tokens"]),
            "search_total_tokens": int(search["total_tokens"]),
            "system_total_tokens": int(result["cost"]["system_total_tokens"]),
        },
        "process_model_cost": {"trace_complete": accepted},
        "candidate_reused_same_run_baseline": reused,
        "incremental_schema_task": is_treated_task(outcome.task),
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    return validate_runtime_row(value, outcome.arm)


def validate_runtime_row(value: Mapping[str, Any], arm: str) -> dict[str, Any]:
    copied = dict(value)
    cost = copied.get("cost")
    expected = {
        "opaque_id",
        "arm",
        "status",
        "prediction",
        "prediction_sha256",
        "completion_kind",
        "forward_success",
        "error",
        "elapsed_seconds",
        "cost",
        "process_model_cost",
        "candidate_reused_same_run_baseline",
        "incremental_schema_task",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
    if (
        set(copied) != expected
        or arm not in ARMS
        or copied.get("arm") != arm
        or copied.get("status") != "completed"
        or not isinstance(copied.get("forward_success"), bool)
        or copied.get("forward_success") != (copied.get("error") is None)
        or not isinstance(copied.get("prediction"), str)
        or not copied["prediction"]
        or hashlib.sha256(copied["prediction"].encode()).hexdigest()
        != copied.get("prediction_sha256")
        or not isinstance(copied.get("completion_kind"), str)
        or not copied["completion_kind"]
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or float(copied["elapsed_seconds"]) < 0
        or not isinstance(cost, Mapping)
        or set(cost) != set(COST_FIELDS)
        or any(
            isinstance(cost.get(name), bool)
            or not isinstance(cost.get(name), int)
            or cost[name] < 0
            for name in COST_FIELDS
        )
        or not isinstance(copied.get("candidate_reused_same_run_baseline"), bool)
        or not isinstance(copied.get("incremental_schema_task"), bool)
        or not isinstance(copied.get("process_model_cost"), Mapping)
        or set(copied["process_model_cost"]) != {"trace_complete"}
        or copied["process_model_cost"].get("trace_complete")
        is not copied["forward_success"]
        or copied.get("candidate_reused_same_run_baseline")
        is not (arm == "candidate" and not copied["incremental_schema_task"])
        or copied.get("label_blind") is not True
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise ValueError("V2.46.79 runtime row drifted")
    return copied


def _summary(arm: str, rows: list[dict[str, Any]], wall: float) -> dict[str, Any]:
    if len(rows) != SELECTED_COUNT:
        raise ValueError("V2.46.79 summary requires the fixed 64 denominator")
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_run_summary",
        "protocol_id": PROTOCOL_ID,
        "arm": arm,
        "selected": SELECTED_COUNT,
        "completed": SELECTED_COUNT,
        "failed": 0,
        "runtime_failures": sum(not row["forward_success"] for row in rows),
        "model_generated_tables": sum(
            row["status"] == "completed" and row["completion_kind"] in MODEL_GENERATED
            for row in rows
        ),
        "fallback_tables": sum(
            row["completion_kind"] not in MODEL_GENERATED for row in rows
        ),
        "completion_kinds": dict(sorted(Counter(row["completion_kind"] for row in rows).items())),
        "system_total_tokens": sum(row["cost"]["system_total_tokens"] for row in rows),
        "model_requests": sum(row["cost"]["model_calls"] for row in rows),
        "model_attempts": sum(row["cost"]["model_attempts"] for row in rows),
        "search_calls": sum(row["cost"]["search_calls"] for row in rows),
        "search_fetch_calls": sum(row["cost"]["search_fetch_calls"] for row in rows),
        "task_wall_sum_seconds": round(sum(row["elapsed_seconds"] for row in rows), 6),
        "forward_wall_seconds": round(max(0.0, wall), 6),
        "incremental_schema_tasks": sum(row["incremental_schema_task"] for row in rows),
        "same_run_baseline_reused_tasks": sum(
            row["candidate_reused_same_run_baseline"] for row in rows
        ),
        "all_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
    }
    value["summary_payload_sha256"] = payload_sha256(value)
    return value


def _pair_summary(
    baseline: list[TaskOutcome],
    candidate: list[TaskOutcome],
    rows: dict[str, list[dict[str, Any]]],
    wall: float,
) -> dict[str, Any]:
    changed = sum(
        left["prediction_sha256"] != right["prediction_sha256"]
        for left, right in zip(rows["baseline"], rows["candidate"], strict=True)
    )
    real = baseline + [
        outcome for outcome in candidate if is_treated_task(outcome.task)
    ]
    transport_fields = (
        "hosted_search_attempts",
        "hosted_search_deadline_failures",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_deadline_rejections",
        "fetch_helper_failures",
    )
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_pair_summary",
        "protocol_id": PROTOCOL_ID,
        "selected_pair_tasks": SELECTED_COUNT,
        "terminal_prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "real_child_runs": len(real),
        "expected_real_child_runs": TOTAL_CHILD_RUNS,
        "incremental_schema_tasks": EXPECTED_TREATED_COUNT,
        "same_run_baseline_reused_candidate_tasks": SELECTED_COUNT
        - EXPECTED_TREATED_COUNT,
        "changed_candidate_tasks": changed,
        "baseline_runtime_failures": sum(
            not row["forward_success"] for row in rows["baseline"]
        ),
        "candidate_runtime_failures": sum(
            not row["forward_success"] for row in rows["candidate"]
        ),
        "accepted_real_child_successes": sum(item.accepted_parent_success for item in real),
        "valid_model_receipts": sum(item.model_receipt_valid for item in real),
        "valid_transport_receipts": sum(item.transport_receipt_valid for item in real),
        "valid_single_shot_receipts": sum(item.single_receipt_valid for item in real),
        "valid_backfill_receipts": sum(item.backfill_receipt_valid for item in real),
        "model_slot_acquisitions": sum(item.model_acquisitions for item in real),
        "model_slot_timeouts": sum(item.model_slot_timeouts for item in real),
        "transport_totals": {
            name: sum(int(item.transport.get(name, 0)) for item in real)
            for name in transport_fields
        },
        "forward_wall_seconds": round(max(0.0, wall), 6),
        "all_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_selective_rerun": False,
    }
    value["summary_payload_sha256"] = payload_sha256(value)
    return value


def _progress(completed: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected_real_child_runs": TOTAL_CHILD_RUNS,
        "completed_real_child_runs": completed,
        "unfinished_real_child_runs": TOTAL_CHILD_RUNS - completed,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["progress_payload_sha256"] = payload_sha256(value)
    return value


def _prepare_slots(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v24679_model_slot",
                "slot": index,
                "slot_cap": MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def validate_control(root: Path, contract: Mapping[str, Any]) -> None:
    preaudit = read_object(root / PREAUDIT)
    activation = read_object(root / ACTIVATION)
    start = read_object(root / EXECUTION_START)
    if (
        preaudit.get("role") != "v24679_schema_dev64_preactivation_audit"
        or preaudit.get("audit_valid") is not True
        or preaudit.get("findings") != []
        or preaudit.get("launch_authorized") is not True
        or preaudit.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or activation.get("role") != "v24679_schema_dev64_activation"
        or activation.get("status") != "active"
        or activation.get("preaudit_sha256") != sha256(root / PREAUDIT)
        or start.get("role") != "v24679_schema_dev64_execution_start"
        or start.get("status") != "authorized"
        or start.get("activation_sha256") != sha256(root / ACTIVATION)
        or start.get("authorization")
        != {
            "one_fresh_paired_dev64_forward": True,
            "evaluator": False,
            "exact220": False,
        }
        or any(not _sealed(value, field) for value, field in (
            (preaudit, "audit_payload_sha256"),
            (activation, "activation_payload_sha256"),
            (start, "execution_start_payload_sha256"),
        ))
        or protected_watcher_snapshot() != contract["execution"]["protected_watchers"]
    ):
        raise RuntimeError("V2.46.79 control chain drifted")


def main() -> None:
    root = ROOT.resolve()
    contract = validate_forward_contract(root)
    validate_control(root, contract)
    tasks = selected_tasks(root, contract)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "target/main"], cwd=root, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    ).stdout.strip()
    if head != remote or dirty:
        raise RuntimeError("V2.46.79 launch requires clean pushed HEAD")
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2):
            pass
    except OSError as error:
        raise RuntimeError("V2.46.79 GPT-5.6 endpoint unreachable") from error
    for path in (root / OUTPUT_ROOT, root / FORWARD_RESULT, root / FORWARD_AUDIT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.46.79 forward surface is not pristine")
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        if protected_watcher_snapshot() != contract["execution"]["protected_watchers"]:
            raise RuntimeError("V2.46.79 watcher drifted before effect")
        (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        _prepare_slots(root)
        (root / TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        baseline, candidate = execute_forward(root, tasks)
        wall = max(0.0, time.monotonic() - started)
    outcomes = {"baseline": baseline, "candidate": candidate}
    rows: dict[str, list[dict[str, Any]]] = {}
    for arm in ARMS:
        rows[arm] = [
            _runtime_row(
                outcome,
                reused=(arm == "candidate" and not is_treated_task(outcome.task)),
            )
            for outcome in outcomes[arm]
        ]
        _write_jsonl_new(root / RUNTIME_PREDICTIONS[arm], rows[arm])
        summary = _summary(arm, rows[arm], wall)
        _new_json(root / RUN_SUMMARY[arm], summary)
        freeze = {
            "artifact_version": 1,
            "role": "v24679_schema_dev64_prediction_freeze",
            "protocol_id": PROTOCOL_ID,
            "arm": arm,
            "selected": SELECTED_COUNT,
            "terminal": SELECTED_COUNT,
            "selected_opaque_ids_sha256": contract["task_contract"][
                "selected_opaque_ids_sha256"
            ],
            "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS[arm]),
            "run_summary_sha256": sha256(root / RUN_SUMMARY[arm]),
            "prediction_hashes_sha256": payload_sha256(
                [row["prediction_sha256"] for row in rows[arm]]
            ),
            "both_arms_terminal_before_mapping_gold_or_evaluator_open": True,
            "mapping_gold_or_evaluator_opened_or_hashed": False,
            "label_blind": True,
        }
        freeze["freeze_payload_sha256"] = payload_sha256(freeze)
        _new_json(root / PREDICTION_FREEZE[arm], freeze)
    pair = _pair_summary(baseline, candidate, rows, wall)
    _new_json(root / PAIR_SUMMARY, pair)
    forward = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_forward_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected_pair_tasks": SELECTED_COUNT,
        "terminal_prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "real_child_runs": TOTAL_CHILD_RUNS,
        "incremental_schema_tasks": EXPECTED_TREATED_COUNT,
        "same_run_baseline_reused_candidate_tasks": SELECTED_COUNT
        - EXPECTED_TREATED_COUNT,
        "changed_candidate_tasks": pair["changed_candidate_tasks"],
        "baseline_runtime_failures": pair["baseline_runtime_failures"],
        "candidate_runtime_failures": pair["candidate_runtime_failures"],
        "forward_wall_seconds": pair["forward_wall_seconds"],
        "pair_summary_sha256": sha256(root / PAIR_SUMMARY),
        "prediction_freeze_sha256": {
            arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
        },
        "both_arms_exact64_before_mapping_gold_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_selective_rerun": False,
        "execution_start_sha256": sha256(root / EXECUTION_START),
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    _new_json(root / FORWARD_RESULT, forward)
    _atomic_json(root / SAFE_PROGRESS, _progress(TOTAL_CHILD_RUNS))
    print(
        json.dumps(
            {
                "forward_result": str(FORWARD_RESULT),
                "terminal_per_arm": SELECTED_COUNT,
                "real_child_runs": TOTAL_CHILD_RUNS,
                "changed_candidate_tasks": pair["changed_candidate_tasks"],
                "wall_seconds": wall,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
