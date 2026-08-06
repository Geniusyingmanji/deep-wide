#!/usr/bin/env python3
"""Run one fresh label-blind shared-forward V2.46.57 paired dev64."""

from __future__ import annotations

import concurrent.futures
import dataclasses
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import build_best_effort_prediction  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24286_visible_schema_runtime import extract_robust_visible_columns  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    parent_receipt,
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import run_observed_subprocess  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import validate_receipt as validate_model_receipt  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24655_unknown_cell_targeted_runtime import validate_result as validate_pair_result  # noqa: E402
from deepwide_agent.v24657_runner_integration import (  # noqa: E402
    validate_envelope,
    validate_observed_bundle,
)
from deepwide_agent.v24657_forward_contract import (  # noqa: E402
    ACTIVATION,
    ARMS,
    CHILD_MARKER,
    CHILD_TERMINAL_NAME,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT_ROOT,
    PAIR_SUMMARY,
    PARENT_EXIT_NAME,
    PARENT_TIMEOUT_SECONDS,
    PREDICTION_FREEZE,
    PREAUDIT,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
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
PAIR_RESULT_NAME = "result.json"
COST_FIELDS = frozenset(
    {
        "model_calls", "model_successful_calls", "model_failed_calls",
        "model_attempts", "input_tokens", "output_tokens", "total_tokens",
        "search_calls", "search_failures", "search_tool_calls",
        "search_fetch_calls", "search_fetch_failures", "search_input_tokens",
        "search_output_tokens", "search_total_tokens", "system_total_tokens",
    }
)
CONTENT_FREE_FAILURES = frozenset(
    {
        "success",
        "hard_deadline_timeout",
        "child_nonzero_with_terminal_receipt",
        "child_nonzero_without_terminal_receipt",
        "zero_exit_missing_result_envelope",
        "result_envelope_invalid",
        "model_receipt_missing_or_invalid",
        "transport_receipt_missing_or_invalid",
        "parent_subprocess_exception",
        "local_orchestration_failure",
    }
)


@dataclasses.dataclass(frozen=True)
class PairOutcome:
    position: int
    task: dict[str, str]
    rows: dict[str, dict[str, Any]]
    parent_exit: dict[str, Any]
    result: dict[str, Any] | None
    model_receipt: dict[str, Any] | None
    transport_health: dict[str, Any] | None


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
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _write_jsonl_new(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _child_environment() -> dict[str, str]:
    return {
        "HOME": str(Path.home()),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "TERM": "xterm-256color",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def _local_parent_receipt() -> dict[str, Any]:
    return parent_receipt(
        return_code=None,
        timed_out=False,
        elapsed_seconds=0.0,
        subprocess_exception=True,
        child_terminal_receipt_present=False,
        child_terminal_receipt_valid=False,
        result_envelope_present=False,
        result_envelope_valid=False,
        model_receipt_present=False,
        model_receipt_valid=False,
        transport_receipt_present=False,
        transport_receipt_valid=False,
    )


def _cost_projection(core: Mapping[str, Any]) -> dict[str, int]:
    cost = core.get("cost")
    model = cost.get("model") if isinstance(cost, Mapping) else {}
    search = cost.get("search") if isinstance(cost, Mapping) else {}
    model = model if isinstance(model, Mapping) else {}
    search = search if isinstance(search, Mapping) else {}

    def integer(source: Mapping[str, Any], name: str) -> int:
        value = source.get(name)
        return int(value) if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    return {
        "model_calls": integer(model, "requests"),
        "model_successful_calls": integer(model, "requests"),
        "model_failed_calls": 0,
        "model_attempts": integer(model, "attempts"),
        "input_tokens": integer(model, "input_tokens"),
        "output_tokens": integer(model, "output_tokens"),
        "total_tokens": integer(model, "total_tokens"),
        "search_calls": integer(search, "calls"),
        "search_failures": integer(search, "failures"),
        "search_tool_calls": integer(search, "tool_calls"),
        "search_fetch_calls": integer(search, "fetch_calls"),
        "search_fetch_failures": integer(search, "fetch_failures"),
        "search_input_tokens": integer(search, "input_tokens"),
        "search_output_tokens": integer(search, "output_tokens"),
        "search_total_tokens": integer(search, "total_tokens"),
        "system_total_tokens": integer(model, "total_tokens") + integer(search, "total_tokens"),
    }


def _runtime_row(
    task: Mapping[str, str],
    *,
    arm: str,
    result: Mapping[str, Any] | None,
    parent_taxonomy: str,
    failure_elapsed_seconds: float = 0.0,
) -> dict[str, Any]:
    if arm not in ARMS or parent_taxonomy not in CONTENT_FREE_FAILURES:
        raise ValueError("V2.46.57 runtime row input drifted")
    success = result is not None and parent_taxonomy == "success"
    if success:
        validate_pair_result(result)
        receipt = result["receipt"]
        runtime_arm = "baseline" if arm == "baseline" else "unknown_cell_targeted"
        prediction = str(result["predictions"][runtime_arm])
        prediction_hash = str(result["prediction_sha256"][runtime_arm])
        cost = _cost_projection({
            "cost": {
                "model": receipt["model_cost"],
                "search": receipt["search_cost"],
            }
        })
        completion = "v24655_unknown_cell_targeted"
        elapsed = float(result["elapsed_seconds"])
        evidence_count = int(receipt["generic_usable_page_count"]) + int(
            receipt["targeted_usable_page_count"]
        )
        process_trace_complete = (
            receipt["logical_model_admission_count"]
            == receipt["model_cost"]["requests"]
            + receipt["pre_provider_model_rejection_count"]
        )
        prediction_identity = (
            result["prediction_sha256"]["baseline"]
            == result["prediction_sha256"]["unknown_cell_targeted"]
        )
        proposed = int(receipt["proposed_cell_change_count"])
        admitted = int(receipt["admitted_cell_change_count"])
        entropy_task_credit_nats = 0.0
        selected_unknown_target_count = int(receipt["selected_unknown_target_count"])
        deterministic_support_pass_count = sum(
            item["support_receipt"]["deterministic_support_gate_passed"] is True
            for item in receipt["cell_admissions"]
        )
    else:
        columns = extract_robust_visible_columns(task["question"]) or ["Result"]
        prediction = build_best_effort_prediction(task["question"], columns)
        prediction_hash = hashlib.sha256(prediction.encode("utf-8")).hexdigest()
        cost = {name: 0 for name in COST_FIELDS}
        completion = "paired_forward_failure"
        elapsed = float(failure_elapsed_seconds)
        evidence_count = 0
        process_trace_complete = False
        prediction_identity = True
        proposed = admitted = selected_unknown_target_count = 0
        deterministic_support_pass_count = 0
        entropy_task_credit_nats = 0.0
    value = {
        "opaque_id": task["opaque_id"],
        "arm": arm,
        "status": "completed" if success else "failed",
        "prediction": prediction,
        "prediction_sha256": prediction_hash,
        "completion_kind": completion,
        "error": None if success else parent_taxonomy,
        "evidence_count": evidence_count,
        "cost": cost,
        "elapsed_seconds": round(max(0.0, elapsed), 6),
        "process_model_cost": {"trace_complete": process_trace_complete},
        "shared_pair_cost_attributed_in_full_to_both_arms": True,
        "candidate_prediction_identity": prediction_identity,
        "selected_unknown_target_count": selected_unknown_target_count,
        "deterministic_support_pass_count": deterministic_support_pass_count,
        "proposed_cell_changes": proposed,
        "admitted_cell_changes": admitted,
        "entropy_task_credit_nats": entropy_task_credit_nats,
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    validate_runtime_row(value, arm)
    return value


def validate_runtime_row(value: Mapping[str, Any], arm: str) -> dict[str, Any]:
    expected = {
        "opaque_id", "arm", "status", "prediction", "prediction_sha256",
        "completion_kind", "error", "evidence_count", "cost", "elapsed_seconds",
        "process_model_cost", "shared_pair_cost_attributed_in_full_to_both_arms",
        "candidate_prediction_identity", "selected_unknown_target_count",
        "deterministic_support_pass_count", "proposed_cell_changes",
        "admitted_cell_changes", "entropy_task_credit_nats",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
    cost = value.get("cost")
    integer_fields = (
        "evidence_count", "selected_unknown_target_count",
        "deterministic_support_pass_count",
        "proposed_cell_changes", "admitted_cell_changes",
    )
    if (
        set(value) != expected
        or arm not in ARMS
        or value.get("arm") != arm
        or not isinstance(value.get("opaque_id"), str)
        or not isinstance(value.get("prediction"), str)
        or hashlib.sha256(str(value["prediction"]).encode("utf-8")).hexdigest()
        != value.get("prediction_sha256")
        or value.get("status") not in {"completed", "failed"}
        or (value.get("status") == "completed") != (value.get("error") is None)
        or (value.get("error") is not None and value.get("error") not in CONTENT_FREE_FAILURES)
        or not isinstance(cost, Mapping)
        or set(cost) != COST_FIELDS
        or any(
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
            or float(number) < 0
            for number in cost.values()
        )
        or value.get("shared_pair_cost_attributed_in_full_to_both_arms") is not True
        or value.get("process_model_cost") not in ({"trace_complete": True}, {"trace_complete": False})
        or not isinstance(value.get("candidate_prediction_identity"), bool)
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in integer_fields
        )
        or value.get("proposed_cell_changes", 0)
        > value.get("selected_unknown_target_count", -1)
        or value.get("admitted_cell_changes", 0) > value.get("proposed_cell_changes", -1)
        or value.get("deterministic_support_pass_count")
        != value.get("admitted_cell_changes")
        or value.get("entropy_task_credit_nats") != 0.0
        or value.get("candidate_prediction_identity")
        is not (value.get("admitted_cell_changes") == 0)
        or value.get("label_blind") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
    ):
        raise RuntimeError("V2.46.57 runtime row drifted")
    return dict(value)


def _failure_outcome(
    position: int,
    task: Mapping[str, str],
    *,
    taxonomy: str = "local_orchestration_failure",
    parent: Mapping[str, Any] | None = None,
    model: Mapping[str, Any] | None = None,
    transport: Mapping[str, Any] | None = None,
) -> PairOutcome:
    receipt = dict(parent) if parent is not None else _local_parent_receipt()
    validate_parent_receipt(receipt)
    if taxonomy not in CONTENT_FREE_FAILURES:
        taxonomy = "local_orchestration_failure"
    rows = {
        arm: _runtime_row(
            task,
            arm=arm,
            result=None,
            parent_taxonomy=taxonomy,
            failure_elapsed_seconds=float(receipt["elapsed_seconds"]),
        )
        for arm in ARMS
    }
    return PairOutcome(
        position=position,
        task=dict(task),
        rows=rows,
        parent_exit=receipt,
        result=None,
        model_receipt=dict(model) if model is not None else None,
        transport_health=dict(transport) if transport is not None else None,
    )


def run_one_task(
    root: Path,
    position: int,
    task: Mapping[str, str],
    directory: Path,
) -> PairOutcome:
    result_path = directory / PAIR_RESULT_NAME
    model_path = directory / RECEIPT_NAME
    transport_path = directory / TRANSPORT_NAME
    parent_path = directory / PARENT_EXIT_NAME
    try:
        _new_json(directory / "visible_task.json", task)

        def result_validator(value: Mapping[str, Any]) -> object:
            envelope = validate_envelope(value)
            if model_path.is_file() and transport_path.is_file():
                validate_observed_bundle(
                    envelope,
                    model_slot_receipt=read_object(model_path),
                    transport_health=read_object(transport_path),
                    expected_cap=MODEL_SLOT_CAP,
                )
            return envelope

        observed = run_observed_subprocess(
            cwd=root,
            output_root=root / OUTPUT_ROOT,
            directory=directory,
            command=[
                str(root / ".venv-eval/bin/python"),
                "-I",
                "-B",
                str(root / CHILD_MARKER),
                "--task",
                str(directory / "visible_task.json"),
                "--result",
                str(result_path),
                "--model-slot-directory",
                str(root / MODEL_SLOT_DIRECTORY),
                "--model-slot-receipt",
                str(model_path),
                "--transport-health",
                str(transport_path),
                "--child-terminal-receipt",
                str(directory / CHILD_TERMINAL_NAME),
            ],
            environment=_child_environment(),
            timeout_seconds=PARENT_TIMEOUT_SECONDS,
            result_validator=result_validator,
            model_receipt_validator=lambda value: validate_model_receipt(
                value, expected_cap=MODEL_SLOT_CAP
            ),
            transport_receipt_validator=validate_transport_health,
            result_name=result_path.name,
            model_receipt_name=model_path.name,
            transport_receipt_name=transport_path.name,
            terminal_name=CHILD_TERMINAL_NAME,
            parent_name=PARENT_EXIT_NAME,
        )
        parent_value = validate_parent_receipt(observed.receipt)
        taxonomy = str(parent_value["failure_taxonomy"])
        if taxonomy != "success":
            model_value = (
                validate_model_receipt(read_object(model_path), expected_cap=MODEL_SLOT_CAP)
                if parent_value["model_receipt_valid"] is True
                else None
            )
            transport_value = (
                validate_transport_health(read_object(transport_path))
                if parent_value["transport_receipt_valid"] is True
                else None
            )
            return _failure_outcome(
                position,
                task,
                taxonomy=taxonomy,
                parent=parent_value,
                model=model_value,
                transport=transport_value,
            )
        envelope = read_object(result_path)
        model = read_object(model_path)
        transport = read_object(transport_path)
        validate_observed_bundle(
            envelope,
            model_slot_receipt=model,
            transport_health=transport,
            expected_cap=MODEL_SLOT_CAP,
        )
        result = dict(envelope["result"])
        validate_pair_result(result)
        rows = {
            arm: _runtime_row(task, arm=arm, result=result, parent_taxonomy="success")
            for arm in ARMS
        }
        return PairOutcome(
            position=position,
            task=dict(task),
            rows=rows,
            parent_exit=parent_value,
            result=result,
            model_receipt=model,
            transport_health=transport,
        )
    except Exception:
        if parent_path.is_file() and not parent_path.is_symlink():
            try:
                parent_value = validate_parent_receipt(read_object(parent_path))
                return _failure_outcome(
                    position,
                    task,
                    taxonomy=str(parent_value["failure_taxonomy"]),
                    parent=parent_value,
                    model=(
                        validate_model_receipt(
                            read_object(model_path), expected_cap=MODEL_SLOT_CAP
                        )
                        if parent_value["model_receipt_valid"] is True
                        else None
                    ),
                    transport=(
                        validate_transport_health(read_object(transport_path))
                        if parent_value["transport_receipt_valid"] is True
                        else None
                    ),
                )
            except Exception:
                pass
        synthetic = _local_parent_receipt()
        if not parent_path.exists() and not parent_path.is_symlink():
            try:
                _new_json(parent_path, synthetic)
            except Exception:
                pass
        return _failure_outcome(position, task, parent=synthetic)


def execute_forward(
    root: Path,
    tasks: Sequence[Mapping[str, str]],
) -> list[PairOutcome]:
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.46.57 task count drifted")
    directories: list[Path] = []
    for position in range(1, SELECTED_COUNT + 1):
        directory = root / TASK_ROOT / f"task_{position:04d}"
        directory.mkdir(mode=0o700)
        directories.append(directory)
    outcomes: dict[int, PairOutcome] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=EXECUTOR_CONCURRENCY,
        thread_name_prefix="v24657-forward",
    ) as executor:
        futures = {
            executor.submit(
                run_one_task,
                root,
                position,
                tasks[position - 1],
                directories[position - 1],
            ): position
            for position in range(1, SELECTED_COUNT + 1)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            try:
                outcome = future.result()
            except Exception:
                outcome = _failure_outcome(position, tasks[position - 1])
            outcomes[position] = outcome
            _atomic_json(root / SAFE_PROGRESS, _progress(len(outcomes)))
    if set(outcomes) != set(range(1, SELECTED_COUNT + 1)):
        raise RuntimeError("V2.46.57 terminal pair coverage drifted")
    return [outcomes[position] for position in range(1, SELECTED_COUNT + 1)]


def _arm_summary(
    arm: str,
    rows: Sequence[Mapping[str, Any]],
    wall_seconds: float,
) -> dict[str, Any]:
    if arm not in ARMS or len(rows) != SELECTED_COUNT:
        raise RuntimeError("V2.46.57 arm summary input drifted")
    completed = sum(row["status"] == "completed" for row in rows)
    value = {
        "artifact_version": 1,
        "role": "v24657_unknown_cell_targeted_paired_dev64_arm_summary",
        "arm": arm,
        "selected": SELECTED_COUNT,
        "completed": completed,
        "failed": SELECTED_COUNT - completed,
        "completion_kinds": dict(sorted(Counter(str(row["completion_kind"]) for row in rows).items())),
        "observable_system_total_tokens_lower_bound": sum(int(row["cost"]["system_total_tokens"]) for row in rows),
        "observable_task_wall_seconds_lower_bound": round(sum(float(row["elapsed_seconds"]) for row in rows), 6),
        "cost_trace_complete_tasks": sum(row["process_model_cost"]["trace_complete"] is True for row in rows),
        "cost_is_shared_pair_total_duplicated_across_arms": True,
        "forward_wall_seconds": round(max(0.0, wall_seconds), 6),
        "changed_candidate_tasks": sum(row["candidate_prediction_identity"] is False for row in rows),
        "selected_unknown_target_count": sum(int(row["selected_unknown_target_count"]) for row in rows),
        "deterministic_support_pass_count": sum(int(row["deterministic_support_pass_count"]) for row in rows),
        "proposed_cell_changes": sum(int(row["proposed_cell_changes"]) for row in rows),
        "admitted_cell_changes": sum(int(row["admitted_cell_changes"]) for row in rows),
        "entropy_task_credit_nats": 0.0,
        "label_blind": True,
        "official_evaluator_called": False,
    }
    validate_arm_summary(value, arm)
    return value


def validate_arm_summary(value: Mapping[str, Any], arm: str) -> dict[str, Any]:
    if (
        value.get("role") != "v24657_unknown_cell_targeted_paired_dev64_arm_summary"
        or value.get("arm") != arm
        or value.get("selected") != SELECTED_COUNT
        or value.get("completed", -1) + value.get("failed", -1) != SELECTED_COUNT
        or sum((value.get("completion_kinds") or {}).values()) != SELECTED_COUNT
        or value.get("admitted_cell_changes", 0) > value.get("proposed_cell_changes", -1)
        or value.get("deterministic_support_pass_count")
        != value.get("admitted_cell_changes")
        or value.get("entropy_task_credit_nats") != 0.0
        or value.get("cost_trace_complete_tasks", -1) > SELECTED_COUNT
        or value.get("cost_is_shared_pair_total_duplicated_across_arms") is not True
        or value.get("label_blind") is not True
        or value.get("official_evaluator_called") is not False
    ):
        raise RuntimeError("V2.46.57 arm summary drifted")
    return dict(value)


def _pair_summary(outcomes: Sequence[PairOutcome], wall_seconds: float) -> dict[str, Any]:
    if len(outcomes) != SELECTED_COUNT:
        raise RuntimeError("V2.46.57 pair outcome count drifted")
    successes = [item for item in outcomes if item.result is not None]
    complete_successes = [
        item
        for item in successes
        if item.result["receipt"]["logical_model_admission_count"]
        == item.result["receipt"]["model_cost"]["requests"]
        + item.result["receipt"]["pre_provider_model_rejection_count"]
    ]
    model_receipts = [item.model_receipt for item in outcomes if item.model_receipt is not None]
    transports = [item.transport_health for item in outcomes if item.transport_health is not None]
    core_receipts = [item.result["receipt"] for item in successes]
    complete_core_receipts = [
        item.result["receipt"]
        for item in complete_successes
    ]
    complete_model_receipts = [
        item.model_receipt
        for item in complete_successes
        if item.model_receipt is not None
    ]
    mechanism = [item.result["receipt"] for item in successes]
    parent_taxonomy = Counter(str(item.parent_exit["failure_taxonomy"]) for item in outcomes)
    value = {
        "artifact_version": 1,
        "role": "v24657_unknown_cell_targeted_paired_dev64_pair_summary",
        "selected_pair_tasks": SELECTED_COUNT,
        "terminal_pair_tasks": SELECTED_COUNT,
        "successful_pair_tasks": len(successes),
        "failed_pair_tasks": SELECTED_COUNT - len(successes),
        "prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "forward_wall_seconds": round(max(0.0, wall_seconds), 6),
        "parent_exit_receipts_present_and_valid": SELECTED_COUNT,
        "parent_exit_taxonomy": dict(sorted(parent_taxonomy.items())),
        "valid_child_terminal_receipts": sum(item.parent_exit["child_terminal_receipt_valid"] is True for item in outcomes),
        "valid_result_envelopes": sum(item.parent_exit["result_envelope_valid"] is True for item in outcomes),
        "valid_model_receipts": len(model_receipts),
        "valid_transport_receipts": len(transports),
        "effect_accounting_complete_tasks": len(complete_core_receipts),
        "logical_model_admissions": sum(int(receipt["logical_model_admission_count"]) for receipt in core_receipts),
        "provider_model_requests": sum(int(receipt["model_cost"]["requests"]) for receipt in core_receipts),
        "provider_model_attempts": sum(int(receipt["model_cost"]["attempts"]) for receipt in core_receipts),
        "pre_provider_model_rejections": sum(int(receipt["pre_provider_model_rejection_count"]) for receipt in core_receipts),
        "slot_acquisitions": sum(int(receipt["acquisitions"]) for receipt in model_receipts),
        "slot_timeouts": sum(int(receipt["slot_timeouts"]) for receipt in model_receipts),
        "provider_deadline_failures": sum(int(receipt["provider_deadline_failures"]) for receipt in model_receipts),
        "hard_fetch_deadline_failures": sum(int(receipt["hard_fetch_deadline_failures"]) for receipt in transports),
        "fetch_helper_failures": sum(int(receipt["fetch_helper_failures"]) for receipt in transports),
        "hosted_search_deadline_failures": sum(int(receipt["hosted_search_deadline_failures"]) for receipt in transports),
        "fetch_deadline_rejections": sum(int(receipt["fetch_deadline_rejections"]) for receipt in transports),
        "deadline_exhausted_tasks": sum(receipt["deadline_exhausted"] is True for receipt in transports),
        "repeated_upstream_effects": sum(
            0 for _receipt in core_receipts
        ),
        "shared_generic_prefix_tasks": sum(
            item["shared_plan_generic_search_fetch_baseline_prefix"] is True
            for item in mechanism
        ),
        "baseline_precedes_targeted_search_tasks": sum(
            item["baseline_precedes_unknown_target_queries"] is True
            for item in mechanism
        ),
        "selected_unknown_target_tasks": sum(int(item["selected_unknown_target_count"]) > 0 for item in mechanism),
        "selected_unknown_target_count": sum(int(item["selected_unknown_target_count"]) for item in mechanism),
        "deterministic_support_tasks": sum(int(item["admitted_cell_change_count"]) > 0 for item in mechanism),
        "deterministic_support_pass_count": sum(int(item["admitted_cell_change_count"]) for item in mechanism),
        "revision_model_admitted_tasks": sum(item["candidate_additional_provider_model_effect"] is True for item in mechanism),
        "revision_gate_tasks": sum(int(item["proposed_cell_change_count"]) > 0 for item in mechanism),
        "changed_candidate_tasks": sum(int(item["admitted_cell_change_count"]) > 0 for item in mechanism),
        "proposed_cell_changes": sum(int(item["proposed_cell_change_count"]) for item in mechanism),
        "admitted_cell_changes": sum(int(item["admitted_cell_change_count"]) for item in mechanism),
        "entropy_task_credit_nats": 0.0,
        "model_conservation_on_complete_tasks": (
            len(complete_core_receipts) == len(complete_model_receipts)
            and sum(int(receipt["logical_model_admission_count"]) for receipt in complete_core_receipts)
            == sum(int(receipt["acquisitions"]) + int(receipt["slot_timeouts"]) for receipt in complete_model_receipts)
            and sum(int(receipt["model_cost"]["requests"]) for receipt in complete_core_receipts)
            == sum(int(receipt["acquisitions"]) for receipt in complete_model_receipts)
        ),
        "label_blind": True,
        "official_evaluator_called": False,
    }
    value["summary_payload_sha256"] = payload_sha256(value)
    validate_pair_summary(value)
    return value


def validate_pair_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("summary_payload_sha256", None)
    if (
        value.get("role") != "v24657_unknown_cell_targeted_paired_dev64_pair_summary"
        or value.get("selected_pair_tasks") != SELECTED_COUNT
        or value.get("terminal_pair_tasks") != SELECTED_COUNT
        or value.get("successful_pair_tasks", -1) + value.get("failed_pair_tasks", -1) != SELECTED_COUNT
        or value.get("prediction_rows_per_arm") != {arm: SELECTED_COUNT for arm in ARMS}
        or value.get("parent_exit_receipts_present_and_valid") != SELECTED_COUNT
        or sum((value.get("parent_exit_taxonomy") or {}).values()) != SELECTED_COUNT
        or value.get("valid_result_envelopes") != value.get("successful_pair_tasks")
        or not 0 <= value.get("effect_accounting_complete_tasks", -1) <= value.get("successful_pair_tasks", -1)
        or not 0 <= value.get("shared_generic_prefix_tasks", -1) <= value.get("successful_pair_tasks", -1)
        or not 0 <= value.get("baseline_precedes_targeted_search_tasks", -1) <= value.get("successful_pair_tasks", -1)
        or value.get("repeated_upstream_effects") != 0
        or not 0 <= value.get("selected_unknown_target_tasks", -1) <= value.get("successful_pair_tasks", -1)
        or not 0 <= value.get("deterministic_support_tasks", -1) <= value.get("selected_unknown_target_tasks", -1)
        or not 0 <= value.get("changed_candidate_tasks", -1) <= value.get("deterministic_support_tasks", -1)
        or value.get("selected_unknown_target_count", -1)
        > 2 * value.get("successful_pair_tasks", -1)
        or value.get("proposed_cell_changes", -1)
        > value.get("selected_unknown_target_count", -1)
        or value.get("admitted_cell_changes", 0) > value.get("proposed_cell_changes", -1)
        or value.get("deterministic_support_pass_count")
        != value.get("admitted_cell_changes")
        or value.get("entropy_task_credit_nats") != 0.0
        or value.get("model_conservation_on_complete_tasks") is not True
        or value.get("label_blind") is not True
        or value.get("official_evaluator_called") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.46.57 pair summary drifted")
    return dict(value)


def _read_runtime_rows(path: Path, arm: str) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != SELECTED_COUNT:
        raise RuntimeError("V2.46.57 runtime row count drifted")
    for row in rows:
        validate_runtime_row(row, arm)
    return rows


def validate_prediction_freeze(
    root: Path,
    contract: Mapping[str, Any],
    arm: str,
    value: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    freeze = dict(value) if value is not None else read_object(root / PREDICTION_FREEZE[arm])
    unsigned = dict(freeze)
    seal = unsigned.pop("freeze_payload_sha256", None)
    rows = _read_runtime_rows(root / RUNTIME_PREDICTIONS[arm], arm)
    if (
        freeze.get("role") != "v24657_unknown_cell_targeted_paired_dev64_prediction_freeze"
        or freeze.get("protocol_id") != PROTOCOL_ID
        or freeze.get("arm") != arm
        or freeze.get("selected") != SELECTED_COUNT
        or freeze.get("terminal") != SELECTED_COUNT
        or freeze.get("selected_opaque_ids_sha256") != contract["task_contract"]["selected_opaque_ids_sha256"]
        or freeze.get("runtime_predictions_sha256") != sha256(root / RUNTIME_PREDICTIONS[arm])
        or freeze.get("run_summary_sha256") != sha256(root / RUN_SUMMARY[arm])
        or freeze.get("prediction_hashes_sha256") != payload_sha256([row["prediction_sha256"] for row in rows])
        or freeze.get("both_arms_terminal_before_mapping_gold_or_evaluator_open") is not True
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or freeze.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.46.57 prediction freeze drifted")
    if [row["opaque_id"] for row in rows] != contract["task_contract"]["selected_opaque_ids"]:
        raise RuntimeError("V2.46.57 frozen runtime order drifted")
    validate_arm_summary(read_object(root / RUN_SUMMARY[arm]), arm)
    return rows


def validate_forward_result(
    root: Path, contract: Mapping[str, Any], value: Mapping[str, Any]
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    pair = validate_pair_summary(read_object(root / PAIR_SUMMARY))
    rows = {arm: validate_prediction_freeze(root, contract, arm) for arm in ARMS}
    if (
        value.get("role") != "v24657_unknown_cell_targeted_paired_dev64_forward_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected_pair_tasks") != SELECTED_COUNT
        or value.get("terminal_pair_tasks") != SELECTED_COUNT
        or value.get("terminal_prediction_rows_per_arm") != {arm: SELECTED_COUNT for arm in ARMS}
        or value.get("pair_summary_sha256") != sha256(root / PAIR_SUMMARY)
        or value.get("prediction_freeze_sha256") != {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}
        or value.get("changed_candidate_tasks") != pair["changed_candidate_tasks"]
        or value.get("admitted_cell_changes") != pair["admitted_cell_changes"]
        or value.get("repeated_upstream_effects") != 0
        or value.get("both_arms_exact64_before_mapping_gold_or_evaluator_open") is not True
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("additional_rollout_resume_skip_or_rerun_launched") is not False
        or value.get("execution_start_sha256") != sha256(root / EXECUTION_START)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.46.57 forward result drifted")
    changed = 0
    for baseline, candidate in zip(rows["baseline"], rows["candidate"], strict=True):
        identity = baseline["prediction_sha256"] == candidate["prediction_sha256"]
        if (
            baseline["opaque_id"] != candidate["opaque_id"]
            or baseline["status"] != candidate["status"]
            or baseline["error"] != candidate["error"]
            or baseline["cost"] != candidate["cost"]
            or baseline["candidate_prediction_identity"] is not identity
            or candidate["candidate_prediction_identity"] is not identity
        ):
            raise RuntimeError("V2.46.57 paired row alignment drifted")
        changed += int(not identity)
    if changed != pair["changed_candidate_tasks"]:
        raise RuntimeError("V2.46.57 changed-task aggregate drifted")
    return dict(value)


def _progress(completed: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24657_unknown_cell_targeted_paired_dev64_safe_progress",
        "selected": SELECTED_COUNT,
        "terminal_pair_tasks": completed,
        "remaining_pair_tasks": SELECTED_COUNT - completed,
        "prediction_rows_per_arm": {arm: completed for arm in ARMS},
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_task_id_or_hash": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["progress_payload_sha256"] = payload_sha256(value)
    return value


def _validate_control(root: Path, contract: Mapping[str, Any]) -> None:
    preaudit = read_object(root / PREAUDIT)
    activation = read_object(root / ACTIVATION)
    start = read_object(root / EXECUTION_START)
    preaudit_unsigned = dict(preaudit)
    preaudit_seal = preaudit_unsigned.pop("audit_payload_sha256", None)
    activation_unsigned = dict(activation)
    activation_seal = activation_unsigned.pop("activation_payload_sha256", None)
    start_unsigned = dict(start)
    start_seal = start_unsigned.pop("execution_start_payload_sha256", None)
    if (
        preaudit.get("role")
        != "v24657_unknown_cell_targeted_paired_dev64_preactivation_audit"
        or preaudit.get("protocol_id") != PROTOCOL_ID
        or preaudit.get("audit_valid") is not True
        or preaudit.get("launch_authorized") is not True
        or preaudit.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or preaudit_seal != payload_sha256(preaudit_unsigned)
        or activation.get("role")
        != "v24657_unknown_cell_targeted_paired_dev64_activation"
        or activation.get("protocol_id") != PROTOCOL_ID
        or activation.get("status") != "active"
        or activation.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or activation.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or activation_seal != payload_sha256(activation_unsigned)
        or start.get("role")
        != "v24657_unknown_cell_targeted_paired_dev64_execution_start"
        or start.get("protocol_id") != PROTOCOL_ID
        or start.get("status") != "ready"
        or start.get("execution_authorized") is not True
        or start.get("activation_base_commit") != start.get("target_main_at_start")
        or start.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or start.get("activation_sha256") != sha256(root / ACTIVATION)
        or start.get("selected_pair_tasks") != SELECTED_COUNT
        or start.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != MODEL_SLOT_CAP
        or any(item.get("protected_watchers") != contract["execution"]["protected_watchers"] for item in (preaudit, activation, start))
        or start.get("api_called_before_execution_start") is not False
        or start.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or start.get("evaluator_authorized") is not False
        or start_seal != payload_sha256(start_unsigned)
    ):
        raise RuntimeError("V2.46.57 control artifact drifted")


def _prepare_slots(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
            "role": "v24657_unknown_cell_targeted_model_slot",
                "pool_id": POOL_ID,
                "slot": index,
                "slot_cap": MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _git_ready(root: Path) -> bool:
    def output(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=root, check=True, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, timeout=20,
        ).stdout.strip()
    if output("rev-parse", "HEAD") != output("rev-parse", "target/main") or output("status", "--porcelain"):
        return False
    try:
        output("ls-files", "--error-unmatch", str(EXECUTION_START))
    except subprocess.CalledProcessError:
        return False
    return True


def main() -> None:
    root = ROOT.resolve()
    contract = validate_forward_contract(root)
    _validate_control(root, contract)
    tasks = selected_tasks(root, contract)
    for path in (root / FORWARD_RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.46.57 forward surface is not pristine")
    if not _git_ready(root):
        raise RuntimeError("V2.46.57 execution-start is not committed and pushed")
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        _prepare_slots(root)
        (root / TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = execute_forward(root, tasks)
        wall = max(0.0, time.monotonic() - started)
    rows = {arm: [outcome.rows[arm] for outcome in outcomes] for arm in ARMS}
    for arm in ARMS:
        _write_jsonl_new(root / RUNTIME_PREDICTIONS[arm], rows[arm])
        _new_json(root / RUN_SUMMARY[arm], _arm_summary(arm, rows[arm], wall))
    pair = _pair_summary(outcomes, wall)
    _new_json(root / PAIR_SUMMARY, pair)
    for arm in ARMS:
        freeze = {
            "artifact_version": 1,
            "role": "v24657_unknown_cell_targeted_paired_dev64_prediction_freeze",
            "protocol_id": PROTOCOL_ID,
            "arm": arm,
            "selected": SELECTED_COUNT,
            "terminal": SELECTED_COUNT,
            "selected_opaque_ids_sha256": contract["task_contract"]["selected_opaque_ids_sha256"],
            "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS[arm]),
            "run_summary_sha256": sha256(root / RUN_SUMMARY[arm]),
            "prediction_hashes_sha256": payload_sha256([row["prediction_sha256"] for row in rows[arm]]),
            "both_arms_terminal_before_mapping_gold_or_evaluator_open": True,
            "mapping_gold_or_evaluator_opened_or_hashed": False,
            "label_blind": True,
        }
        freeze["freeze_payload_sha256"] = payload_sha256(freeze)
        _new_json(root / PREDICTION_FREEZE[arm], freeze)
        validate_prediction_freeze(root, contract, arm, freeze)
    forward = {
        "artifact_version": 1,
        "role": "v24657_unknown_cell_targeted_paired_dev64_forward_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected_pair_tasks": SELECTED_COUNT,
        "terminal_pair_tasks": SELECTED_COUNT,
        "terminal_prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "successful_pair_tasks": pair["successful_pair_tasks"],
        "failed_pair_tasks": pair["failed_pair_tasks"],
        "changed_candidate_tasks": pair["changed_candidate_tasks"],
        "admitted_cell_changes": pair["admitted_cell_changes"],
        "repeated_upstream_effects": pair["repeated_upstream_effects"],
        "forward_wall_seconds": pair["forward_wall_seconds"],
        "pair_summary_sha256": sha256(root / PAIR_SUMMARY),
        "prediction_freeze_sha256": {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS},
        "both_arms_exact64_before_mapping_gold_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
        "additional_rollout_resume_skip_or_rerun_launched": False,
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "activation_sha256": sha256(root / ACTIVATION),
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    validate_forward_result(root, contract, forward)
    _new_json(root / FORWARD_RESULT, forward)
    _atomic_json(root / SAFE_PROGRESS, _progress(SELECTED_COUNT))
    if protected_watcher_snapshot() != contract["execution"]["protected_watchers"]:
        raise RuntimeError("V2.46.57 protected watcher identity drifted")
    print(json.dumps({
        "forward_result": str(FORWARD_RESULT),
        "terminal_pairs": SELECTED_COUNT,
        "successful_pairs": pair["successful_pair_tasks"],
        "changed_candidate_tasks": pair["changed_candidate_tasks"],
        "wall_seconds": wall,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
