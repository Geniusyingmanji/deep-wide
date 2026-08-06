#!/usr/bin/env python3
"""Run one fresh, fixed-policy, label-blind V2.46.35 exact-220 forward."""

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
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24280_task_union_single_shot import validate_receipt as validate_single  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import coarse_exception_type, validate_parent_receipt  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import run_observed_subprocess  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import validate_receipt as validate_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24318_deadline_conservation_runtime import MODEL_FIELD, validate_v24318_result  # noqa: E402
from deepwide_agent.v24319_runner_integration import (  # noqa: E402
    PARENT_BOUNDS_FIELD,
    project_parent_failure,
    validate_projected_parent_result,
)
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    COUNT_FIELDS as BACKFILL_COUNT_FIELDS,
    validate_receipt as validate_backfill,
)
from deepwide_agent.v24630_exact220_task_integration import (  # noqa: E402
    validate_cross_artifacts,
    validate_envelope,
)
from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
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
    OUTPUT_ROOT,
    PARENT_DEADLINE_GRACE_SECONDS,
    PARENT_EXIT_NAME,
    PREAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RECEIPT_NAME,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SELECTED_COUNT,
    TASK_ROOT,
    TRANSPORT_NAME,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    selected_tasks,
    sha256,
    validate_forward_contract,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


SINGLE_NAME = "search_single_shot_receipt.json"
BACKFILL_NAME = "citation_title_backfill_receipt.json"
MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)


@dataclass(frozen=True)
class TaskOutcome:
    position: int
    result: dict[str, Any]
    parent_exit: dict[str, Any] | None
    accepted_parent_success: bool
    model_receipt_present: bool
    model_receipt_valid: bool
    model_acquisitions: int
    model_slot_timeouts: int
    transport_receipt_valid: bool
    transport: dict[str, Any]
    single_receipt_valid: bool
    single: dict[str, Any] | None
    backfill_receipt_valid: bool
    backfill: dict[str, Any] | None


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


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


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


def validate_preaudit(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / PREAUDIT)
    if (
        value.get("role") != "v24635_exact220_preactivation_audit"
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not False
        or value.get("findings") != []
        or value.get("authorization")
        != {
            "activation_design": True,
            "exact220_launch": False,
            "evaluator_call": False,
        }
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("dependency_manifest_sha256") != contract["dependency_manifest_sha256"]
        or value.get("protected_watchers") != contract["execution"]["protected_watchers"]
        or value.get("git", {}).get("head_equals_target_main") is not True
        or value.get("git", {}).get(
            "forward_contract_and_dependencies_tracked"
        )
        is not True
        or value.get("unexpected_privileged_runtime_field_accesses") != []
        or value.get("credential_literal_hits") != []
        or value.get("evaluator_modules_in_forward_dependency_manifest") != []
        or value.get("evaluator_capabilities_in_forward_surface") != []
        or value.get("evaluator_capability_detection")
        != {
            "method": "python_ast_import_dynamic_import_process_launch_call_and_resource_access_v1",
            "inert_conflict_process_marker_literals_allowed": True,
            "literal_substring_scan_used_as_capability_test": False,
        }
        or not isinstance(value.get("focused_tests"), list)
        or not value["focused_tests"]
        or not all(item.get("passed") is True for item in value["focused_tests"])
        or value.get("shared_api_lease_active") is not False
        or value.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.35 preactivation audit drifted")
    return value


def validate_activation(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / ACTIVATION)
    if (
        value.get("role") != "v24635_exact220_activation"
        or value.get("status") != "active"
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers") != contract["execution"]["protected_watchers"]
        or value.get("shared_api_lease_active_before_activation") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("authorization")
        != {
            "execution_start_design": True,
            "exact220_launch": False,
            "evaluator_call": False,
        }
        or value.get("model_endpoint_reachable_without_provider_request") is not True
        or value.get("git", {}).get("head_equals_target_main") is not True
        or value.get("git", {}).get("worktree_clean") is not True
        or value.get("git", {}).get(
            "forward_contract_and_preaudit_tracked"
        )
        is not True
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.46.35 activation drifted")
    return value


def validate_execution_start(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / EXECUTION_START)
    if (
        value.get("role") != "v24635_exact220_execution_start_authorization"
        or value.get("status") != "authorized_not_started"
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("runtime_input_contract") != ["opaque_id", "question"]
        or value.get("api_called_before_execution_start") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("protected_watchers")
        != contract["execution"]["protected_watchers"]
        or value.get("api_called_before_execution_start") is not False
        or value.get("evaluator_imported_or_called") is not False
        or value.get("resume_retry_skip_or_rerun") is not False
        or value.get("git", {}).get("head_equals_target_main") is not True
        or value.get("git", {}).get("worktree_clean") is not True
        or value.get("git", {}).get(
            "contract_preaudit_and_activation_tracked"
        )
        is not True
        or value.get("authorization")
        != {
            "single_fresh_exact220_forward": True,
            "evaluator_call": False,
            "resume_retry_skip_or_rerun": False,
        }
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.46.35 execution-start authorization drifted")
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


def task_command(root: Path, directory: Path) -> list[str]:
    return [
        str(root / ".venv-eval/bin/python"), "-I", "-B", str(root / CHILD_MARKER),
        "--task", str(directory / "visible_task.json"),
        "--result", str(directory / "result.json"),
        "--progress", str(directory / "safe_progress.json"),
        "--model-slot-directory", str(root / MODEL_SLOT_DIRECTORY),
        "--model-slot-receipt", str(directory / RECEIPT_NAME),
        "--transport-health", str(directory / TRANSPORT_NAME),
        "--search-single-shot-receipt", str(directory / SINGLE_NAME),
        "--citation-title-backfill-receipt", str(directory / BACKFILL_NAME),
        "--child-terminal-receipt", str(directory / CHILD_TERMINAL_NAME),
    ]


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
    task: dict[str, str], *, failure: str, elapsed: float,
    progress: dict[str, Any], model_receipt: dict[str, Any] | None,
    timed_out: bool,
) -> dict[str, Any]:
    value = project_parent_failure(
        task,
        limits=ScoreFirstLimits(**LIMITS),
        completion_kind="hard_deadline_fallback" if timed_out else "worker_failure_fallback",
        failure_type=failure,
        elapsed_seconds=elapsed,
        progress=progress,
        model_slot_receipt=model_receipt,
        expected_cap=MODEL_SLOT_CAP,
    )
    validate_projected_parent_result(value)
    return value


def _validate_bundle(value: dict[str, Any], directory: Path) -> None:
    envelope = validate_envelope(value)
    model = validate_model(read_object(directory / RECEIPT_NAME), expected_cap=MODEL_SLOT_CAP)
    transport = validate_transport_health(read_object(directory / TRANSPORT_NAME))
    single = read_object(directory / SINGLE_NAME)
    backfill = read_object(directory / BACKFILL_NAME)
    validate_single(single)
    validate_backfill(backfill)
    validate_cross_artifacts(
        envelope["result"],
        arm=ARM,
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
        raise ValueError("V2.46.35 independent task artifacts drifted")


def run_one_task(
    root: Path, contract: dict[str, Any], position: int, task: dict[str, str],
    directory: Path, *, popen: Any = subprocess.Popen,
) -> TaskOutcome:
    del contract
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    _new_json(directory / "visible_task.json", task)
    observed = run_observed_subprocess(
        cwd=root,
        output_root=root / OUTPUT_ROOT,
        directory=directory,
        command=task_command(root, directory),
        environment=_child_env(),
        timeout_seconds=float(LIMITS["wall_seconds"]) + PARENT_DEADLINE_GRACE_SECONDS,
        result_validator=lambda value: _validate_bundle(dict(value), directory),
        model_receipt_validator=lambda value: validate_model(dict(value), expected_cap=MODEL_SLOT_CAP),
        transport_receipt_validator=lambda value: validate_transport_health(dict(value)),
        result_name="result.json",
        model_receipt_name=RECEIPT_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name=CHILD_TERMINAL_NAME,
        parent_name=PARENT_EXIT_NAME,
        popen=popen,
    )
    parent = observed.receipt
    validate_parent_receipt(parent)
    model_path = directory / RECEIPT_NAME
    model_value: dict[str, Any] | None = None
    model_present = model_path.is_file() and not model_path.is_symlink()
    try:
        if model_present:
            model_value = validate_model(read_object(model_path), expected_cap=MODEL_SLOT_CAP)
    except (OSError, RuntimeError, TypeError, ValueError):
        model_value = None
    transport = _empty_transport()
    transport_valid = False
    try:
        transport = validate_transport_health(read_object(directory / TRANSPORT_NAME))
        transport_valid = True
    except (OSError, RuntimeError, TypeError, ValueError):
        pass
    single: dict[str, Any] | None = None
    backfill: dict[str, Any] | None = None
    try:
        single = read_object(directory / SINGLE_NAME)
        validate_single(single)
    except (OSError, RuntimeError, TypeError, ValueError):
        single = None
    try:
        backfill = validate_backfill(read_object(directory / BACKFILL_NAME))
    except (OSError, RuntimeError, TypeError, ValueError):
        backfill = None
    accepted = (
        parent["failure_taxonomy"] == "success"
        and observed.return_code == 0
        and observed.timed_out is False
        and observed.subprocess_exception is False
        and model_value is not None
        and transport_valid
        and single is not None
        and backfill is not None
    )
    if accepted:
        try:
            envelope = read_object(directory / "result.json")
            _validate_bundle(envelope, directory)
            result = envelope["result"]
            validate_v24318_result(result, ARM)
            return TaskOutcome(
                position, result, parent, True, model_present, True,
                int(model_value["acquisitions"]), int(model_value["slot_timeouts"]),
                True, transport, True, single, True, backfill,
            )
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            accepted = False
    progress = _safe_progress(directory / "safe_progress.json")
    timed_out = parent["failure_taxonomy"] == "hard_deadline_timeout"
    result = _fallback(
        task,
        failure=str(parent["failure_taxonomy"]),
        elapsed=float(parent["elapsed_seconds"]),
        progress=progress,
        model_receipt=model_value,
        timed_out=timed_out,
    )
    return TaskOutcome(
        position, result, parent, False, model_present, model_value is not None,
        int(model_value.get("acquisitions", 0)) if model_value else 0,
        int(model_value.get("slot_timeouts", 0)) if model_value else 0,
        transport_valid, transport, single is not None, single,
        backfill is not None, backfill,
    )


def _progress(completed: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24635_exact220_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "completed": completed,
        "unfinished": SELECTED_COUNT - completed,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["progress_payload_sha256"] = payload_sha256(value)
    return value


def execute_forward(
    root: Path, contract: dict[str, Any], tasks: list[dict[str, str]], *,
    task_runner: Callable[..., TaskOutcome] = run_one_task,
    progress_writer: Callable[[dict[str, Any]], None] | None = None,
) -> list[TaskOutcome]:
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.46.35 scheduler requires exact-220 tasks")
    outcomes: dict[int, TaskOutcome] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=EXECUTOR_CONCURRENCY, thread_name_prefix="v24635-full220"
    ) as executor:
        futures = {
            executor.submit(
                task_runner, root, contract, position, task,
                root / TASK_ROOT / f"task_{position:04d}",
            ): (position, task)
            for position, task in enumerate(tasks, start=1)
        }
        for future in concurrent.futures.as_completed(futures):
            position, task = futures[future]
            try:
                outcome = future.result()
                if not isinstance(outcome, TaskOutcome) or outcome.position != position:
                    raise TypeError("V2.46.35 task outcome drifted")
                if PARENT_BOUNDS_FIELD in outcome.result:
                    validate_projected_parent_result(outcome.result)
                else:
                    validate_v24318_result(outcome.result, ARM)
            except BaseException as error:
                outcome = TaskOutcome(
                    position,
                    _fallback(
                        task, failure=coarse_exception_type(error), elapsed=0,
                        progress={}, model_receipt=None, timed_out=False,
                    ),
                    None, False, False, False, 0, 0, False,
                    _empty_transport(), False, None, False, None,
                )
            outcomes[position] = outcome
            if progress_writer is not None:
                progress_writer(_progress(len(outcomes)))
    ordered = [outcomes[position] for position in range(1, SELECTED_COUNT + 1)]
    if [item.result["opaque_id"] for item in ordered] != [task["opaque_id"] for task in tasks]:
        raise RuntimeError("V2.46.35 scheduler order drifted")
    return ordered


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
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    prediction = value["prediction"]
    elapsed = value["elapsed_seconds"]
    if (
        not isinstance(prediction, str) or not prediction
        or hashlib.sha256(prediction.encode()).hexdigest() != value["prediction_sha256"]
        or isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed)) or float(elapsed) < 0
    ):
        raise ValueError("V2.46.35 runtime row drifted")
    return value


def _summary(outcomes: list[TaskOutcome], wall: float) -> dict[str, Any]:
    results = [item.result for item in outcomes]
    completion = Counter(str(result["completion_kind"]) for result in results)
    parent = Counter(
        str(item.parent_exit["failure_taxonomy"]) if item.parent_exit else "parent_unobserved"
        for item in outcomes
    )
    backfill = {
        name: sum(int((item.backfill or {}).get(name, 0)) for item in outcomes)
        for name in BACKFILL_COUNT_FIELDS
    }
    transport_fields = (
        "hosted_search_attempts", "hosted_search_deadline_failures",
        "hard_fetch_helper_calls", "hard_fetch_deadline_failures",
        "fetch_deadline_rejections", "fetch_helper_failures",
    )
    transport = {
        name: sum(int(item.transport.get(name, 0)) for item in outcomes)
        for name in transport_fields
    }
    value = {
        "artifact_version": 1,
        "role": "v24635_exact220_run_summary",
        "protocol_id": PROTOCOL_ID,
        "selected": SELECTED_COUNT,
        "completed": SELECTED_COUNT,
        "failed": 0,
        "model_generated_tables": sum(result["completion_kind"] in MODEL_GENERATED for result in results),
        "fallback_tables": sum(result["completion_kind"] not in MODEL_GENERATED for result in results),
        "completion_kinds": dict(sorted(completion.items())),
        "system_total_tokens": sum(int(result["cost"]["system_total_tokens"]) for result in results),
        "model_requests": sum(int(result["cost"]["model"]["requests"]) for result in results),
        "model_attempts": sum(int(result["cost"]["model"]["attempts"]) for result in results),
        "search_calls": sum(int(result["cost"]["search"]["calls"]) for result in results),
        "search_fetch_calls": sum(int(result["cost"]["search"]["fetch_calls"]) for result in results),
        "task_wall_sum_seconds": round(sum(float(result["budget"]["elapsed_seconds"]) for result in results), 6),
        "forward_wall_seconds": round(max(0.0, wall), 6),
        "parent_exit_taxonomy": dict(sorted(parent.items())),
        "accepted_parent_successes": sum(item.accepted_parent_success for item in outcomes),
        "model_receipts_present": sum(item.model_receipt_present for item in outcomes),
        "valid_model_receipts": sum(item.model_receipt_valid for item in outcomes),
        "valid_transport_receipts": sum(item.transport_receipt_valid for item in outcomes),
        "valid_single_shot_receipts": sum(item.single_receipt_valid for item in outcomes),
        "valid_backfill_receipts": sum(item.backfill_receipt_valid for item in outcomes),
        "model_slot_acquisitions": sum(item.model_acquisitions for item in outcomes),
        "model_slot_timeouts": sum(item.model_slot_timeouts for item in outcomes),
        "backfill_totals": backfill,
        "transport_totals": transport,
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
    }
    value["summary_payload_sha256"] = payload_sha256(value)
    return value


def _prepare_slots(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {"artifact_version": 1, "role": "v24635_model_slot", "slot": index,
             "slot_cap": MODEL_SLOT_CAP, "contains_credential_or_benchmark_content": False},
        )


def main() -> None:
    root = ROOT
    contract = validate_forward_contract(root)
    validate_preaudit(root, contract)
    activation = validate_activation(root, contract)
    start = validate_execution_start(root, contract)
    tasks = selected_tasks(root, contract)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "target/main"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()
    if head != remote or subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip():
        raise RuntimeError("V2.46.35 launch requires clean HEAD == target/main")
    required_tracked = (
        FORWARD_CONTRACT,
        PREAUDIT,
        ACTIVATION,
        EXECUTION_START,
        *tuple(Path(relative) for relative in contract["dependency_manifest"]),
    )
    if any(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)], cwd=root,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        ).returncode != 0
        for path in required_tracked
    ):
        raise RuntimeError("V2.46.35 launch dependency is not tracked")
    for marker in (
        "scripts/run_v24630_exact220.py",
        "scripts/finalize_v24630_exact220.py",
        "scripts/run_official_eval_local.py",
    ):
        rows = subprocess.run(
            ["ps", "-eo", "cmd="], text=True, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, check=False,
        ).stdout.splitlines()
        if any(marker in row for row in rows if "ps -eo" not in row):
            raise RuntimeError("V2.46.35 conflicting benchmark or evaluator is active")
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            pass
    except OSError as exc:
        raise RuntimeError("V2.46.35 GPT-5.6 endpoint is unreachable") from exc
    for path in (root / FORWARD_RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.46.35 forward surface is not pristine")
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        if protected_watcher_snapshot() != contract["execution"]["protected_watchers"]:
            raise RuntimeError("V2.46.35 protected watcher drifted before effect")
        (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        _prepare_slots(root)
        (root / TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = execute_forward(
            root, contract, tasks,
            progress_writer=lambda value: _atomic_json(root / SAFE_PROGRESS, value),
        )
        wall = max(0.0, time.monotonic() - started)
    rows = [_runtime_row(item.result) for item in outcomes]
    _write_jsonl_new(root / RUNTIME_PREDICTIONS, rows)
    summary = _summary(outcomes, wall)
    _new_json(root / RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24635_exact220_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "selected": SELECTED_COUNT,
        "terminal": SELECTED_COUNT,
        "selected_opaque_ids_sha256": contract["task_contract"]["selected_opaque_ids_sha256"],
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "run_summary_sha256": sha256(root / RUN_SUMMARY),
        "prediction_hashes_sha256": payload_sha256([row["prediction_sha256"] for row in rows]),
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = payload_sha256(freeze)
    _new_json(root / PREDICTION_FREEZE, freeze)
    forward = {
        "artifact_version": 1,
        "role": "v24635_exact220_forward_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "terminal_predictions": SELECTED_COUNT,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "system_total_tokens": summary["system_total_tokens"],
        "forward_wall_seconds": summary["forward_wall_seconds"],
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "run_summary_sha256": sha256(root / RUN_SUMMARY),
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "activation_payload_sha256": activation["activation_payload_sha256"],
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_rerun_launched": False,
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    _new_json(root / FORWARD_RESULT, forward)
    _atomic_json(root / SAFE_PROGRESS, _progress(SELECTED_COUNT))
    print(json.dumps({"terminal": SELECTED_COUNT, "wall_seconds": wall, "forward_result": str(FORWARD_RESULT)}, sort_keys=True))


if __name__ == "__main__":
    main()
