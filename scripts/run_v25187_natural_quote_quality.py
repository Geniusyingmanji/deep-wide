#!/usr/bin/env python3
"""Run the single authorized V2.51.87 same-response external forward."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25186_same_response_quote_quality_runtime as runtime  # noqa: E402
from deepwide_agent import v25187_natural_quote_quality_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import HardTotalWallResponsesClient  # noqa: E402
from deepwide_agent.v24985_robust_late_page_fetch import validate_search_class  # noqa: E402
from scripts import run_v25183_quote_aware_external as accounting  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25187_natural_quote_quality_task_result"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.87 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.51.87 expected JSONL objects")
    return rows


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(ROOT, "rev-parse", "HEAD") != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.51.87 requires clean pushed HEAD")


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    markers = (str(contract.RUNNER), str(contract.EVALUATOR), "scripts/run_" + "official_eval_local.py")
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and int(parts[0]) != os.getpid() and "python" in parts[1].casefold() and any(marker in parts[2] for marker in markers):
            output.append(int(parts[0]))
    return sorted(output)


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        start.get("role") != "v25187_natural_quote_quality_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256") != protocol["population"]["task_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization") != {
            "one_external_forward": True,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.51.87 execution start drifted")
    return protocol, start


def _prepare_output() -> None:
    root = ROOT / contract.OUTPUT_ROOT
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    slots = ROOT / contract.MODEL_SLOT_DIRECTORY
    slots.mkdir(mode=0o700)
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        _publish_json(slots / f"slot_{index:02d}.lock", {
            "artifact_version": 1,
            "role": "v25187_model_slot",
            "slot": index,
            "slot_cap": contract.MODEL_SLOT_CAP,
            "contains_credential_or_benchmark_content": False,
        })


def _search(question: str, deadline: float) -> Any:
    if contract.SEARCH != accounting.contract.SEARCH or contract.LIMITS != accounting.contract.LIMITS:
        raise RuntimeError("V2.51.87 accounting search configuration drifted")
    return accounting._search(question, deadline)


def _fallback_table() -> str:
    return (
        "```markdown\n| " + " | ".join(contract.COLUMNS) + " |\n|"
        + "|".join("---" for _ in contract.COLUMNS) + "|\n| "
        + " | ".join("Unknown" for _ in contract.COLUMNS) + " |\n```"
    )


def _terminal_outer_failure(
    task: Mapping[str, str], exc: BaseException, elapsed: float,
    health: Mapping[str, int] | None = None,
    actual_effect_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    fallback = _fallback_table()
    row = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": str(task["opaque_id"]),
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": False,
        "failure_as_zero": True,
        "outer_failure_type": (type(exc).__name__ or "Exception")[:128],
        "predictions": {arm: fallback for arm in contract.ARMS},
        "prediction_sha256": {arm: hashlib.sha256(fallback.encode()).hexdigest() for arm in contract.ARMS},
        "prediction_kind": "fallback",
        "failure_types": None,
        "parent_result": None,
        "parent_result_payload_sha256": None,
        "cost": None,
        "content_free_receipt": None,
        "runtime_result_payload_sha256": None,
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "effect_health": accounting._health(health),
        "actual_effect_snapshot": accounting._validate_actual_effect_snapshot(
            actual_effect_snapshot or accounting._actual_effect_snapshot(None, {})
        ),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
    }
    return contract.seal(row, "result_payload_sha256")


def _from_runtime(
    task: Mapping[str, str], value: Mapping[str, Any], elapsed: float,
    health: Mapping[str, int] | None = None,
    actual_effect_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = runtime.validate_result(value)
    if checked["opaque_id"] != task["opaque_id"]:
        raise RuntimeError("V2.51.87 task identity drifted")
    sparse = checked["parent_result"]["parent_result"]["parent_result"]["parent_result"]
    row = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": checked["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "predictions": copy.deepcopy(checked["predictions"]),
        "prediction_sha256": copy.deepcopy(checked["prediction_sha256"]),
        "prediction_kind": checked["prediction_kind"],
        "failure_types": copy.deepcopy(sparse["failure_types"]),
        "parent_result": copy.deepcopy(checked["parent_result"]),
        "parent_result_payload_sha256": checked["parent_result_payload_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "content_free_receipt": copy.deepcopy(checked["content_free_receipt"]),
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "effect_health": accounting._health(health),
        "actual_effect_snapshot": accounting._validate_actual_effect_snapshot(
            actual_effect_snapshot or accounting._actual_effect_snapshot(None, {})
        ),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
    }
    return contract.seal(row, "result_payload_sha256")


def _reconstruct_runtime(copied: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_version": 1, "role": runtime.ROLE, "policy_id": runtime.POLICY_ID,
        "opaque_id": copied["opaque_id"], "status": "terminal",
        "predictions": copy.deepcopy(copied["predictions"]),
        "prediction_sha256": copy.deepcopy(copied["prediction_sha256"]),
        "prediction_kind": copied["prediction_kind"], "cost": copy.deepcopy(copied["cost"]),
        "parent_result": copy.deepcopy(copied["parent_result"]),
        "parent_result_payload_sha256": copied["parent_result_payload_sha256"],
        "content_free_receipt": copy.deepcopy(copied["content_free_receipt"]),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "result_payload_sha256": copied["runtime_result_payload_sha256"],
    }


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version", "role", "protocol_id", "opaque_id", "runtime_input_keys",
        "terminal", "runtime_completed", "failure_as_zero", "outer_failure_type",
        "predictions", "prediction_sha256", "prediction_kind", "failure_types",
        "parent_result", "parent_result_payload_sha256", "cost", "content_free_receipt",
        "runtime_result_payload_sha256", "elapsed_seconds", "effect_health",
        "actual_effect_snapshot",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "retry_resume_skip_population_replacement_or_selective_rerun",
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
        "result_payload_sha256",
    }
    predictions = copied.get("predictions") or {}
    hashes = copied.get("prediction_sha256") or {}
    completed = copied.get("runtime_completed") is True
    if (
        set(copied) != expected or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("runtime_input_keys") != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("runtime_completed"), bool)
        or not isinstance(copied.get("failure_as_zero"), bool)
        or copied.get("failure_as_zero") is completed
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id") or "")) is None
        or set(predictions) != set(contract.ARMS) or set(hashes) != set(contract.ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] or hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in contract.ARMS)
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float)) or copied["elapsed_seconds"] < 0
        or accounting._health(copied.get("effect_health")) != copied.get("effect_health")
        or accounting._validate_actual_effect_snapshot(copied.get("actual_effect_snapshot") or {}) != copied.get("actual_effect_snapshot")
        or any(copied.get(name) is not False for name in (
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "retry_resume_skip_population_replacement_or_selective_rerun",
            "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
        ))
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.87 task row drifted")
    if completed:
        runtime_value = runtime.validate_result(_reconstruct_runtime(copied))
        sparse = runtime_value["parent_result"]["parent_result"]["parent_result"]["parent_result"]
        sparse_receipt = sparse["content_free_receipt"]
        if (
            copied.get("outer_failure_type") is not None
            or copied.get("failure_types") != sparse.get("failure_types")
            or copied["actual_effect_snapshot"]["model_logical_requests"] != sparse_receipt["provider_forward_count"]
            or copied["actual_effect_snapshot"]["model_provider_attempts"] != sparse_receipt["model_provider_attempt_count"]
            or copied["actual_effect_snapshot"]["model_provider_requests"] != sparse_receipt["model_provider_request_count"]
            or copied["actual_effect_snapshot"]["logical_queries"] != sparse_receipt["physical_query_count"]
            or copied["actual_effect_snapshot"]["fetch_requests"] != sparse_receipt["physical_fetch_count"]
            or copied["actual_effect_snapshot"]["fetch_calls"] != sparse_receipt["physical_fetch_count"]
        ):
            raise RuntimeError("V2.51.87 bound runtime row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str) or not copied["outer_failure_type"]
        or any(copied.get(name) is not None for name in (
            "failure_types", "parent_result", "parent_result_payload_sha256", "cost",
            "content_free_receipt", "runtime_result_payload_sha256",
        ))
        or predictions[contract.CONTROL_ARM] != predictions[contract.CANDIDATE_ARM]
    ):
        raise RuntimeError("V2.51.87 outer failure row drifted")
    return copied


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.51.87 runtime input must be opaque_id and question")
    started = time.monotonic()
    model: Any = None
    searches: dict[str, Any] = {}
    try:
        deadline = started + float(contract.LIMITS["wall_seconds"])
        inner = HardTotalWallResponsesClient(
            contract.MODEL["proxy_url"], contract.MODEL["name"],
            reasoning_effort=contract.MODEL["reasoning_effort"],
            service_tier=contract.MODEL["service_tier"], timeout=contract.MODEL["timeout_seconds"],
            max_retries=contract.MODEL["max_retries"], absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
            stage_callback=lambda _event: None,
        )
        model = accounting._EffectAccountingModelSlotLimiter(
            inner, slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
            output_root=ROOT / contract.OUTPUT_ROOT, slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID, absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        searches = {phase: _search(str(task["question"]), deadline) for phase in runtime.PHASES}
        result = runtime.run_task(
            task, model=model, searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS), monotonic=time.monotonic,
        )
        row = _from_runtime(
            task, result, time.monotonic() - started,
            accounting._health_snapshot(model, searches),
            accounting._actual_effect_snapshot(model, searches),
        )
    except BaseException as exc:
        row = _terminal_outer_failure(
            task, exc, time.monotonic() - started,
            accounting._health_snapshot(model, searches),
            accounting._actual_effect_snapshot(model, searches),
        )
    return validate_task_row(row)


_INTEGER_NAMES = {
    "task_count", "terminal_tasks", "completed_runtime_tasks", "failure_as_zero_tasks",
    "model_generated_tasks", "fallback_tasks", "same_raw_counterfactual_active_tasks",
    "prediction_changed_tasks", "parent_public_export_failure_tasks",
    "additional_effect_tasks", "physical_queries", "physical_fetches",
    "physical_model_forwards", "model_provider_requests", "model_provider_attempts",
    "model_provider_successes", "system_total_tokens", "content_free_receipt_valid_tasks",
    "outer_or_accounting_failure_tasks", "terminal_effect_hard_failures",
    "positive_signed_credit_count",
}


def aggregate_rows(rows: Sequence[Mapping[str, Any]], *, wall_seconds: float) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if len(checked) != contract.TASK_COUNT or [row["opaque_id"] for row in checked] != [task["opaque_id"] for task in contract.task_vector()]:
        raise RuntimeError("V2.51.87 fixed task vector drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    effects = [row["actual_effect_snapshot"] for row in checked]
    value = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "model_generated_tasks": sum(row["prediction_kind"] == "model_generated" for row in completed),
        "fallback_tasks": sum(row["prediction_kind"] == "fallback" for row in completed),
        "same_raw_counterfactual_active_tasks": sum(r["same_raw_counterfactual_active"] for r in receipts),
        "prediction_changed_tasks": sum(r["prediction_changed"] for r in receipts),
        "parent_public_export_failure_tasks": sum(r["parent_public_export_failure_present"] for r in receipts),
        "additional_effect_tasks": sum(not r["additional_model_search_fetch_or_network_effect"] is False for r in receipts),
        "physical_queries": sum(e["logical_queries"] for e in effects),
        "physical_fetches": sum(e["fetch_requests"] for e in effects),
        "physical_model_forwards": sum(e["model_logical_requests"] for e in effects),
        "model_provider_requests": sum(e["model_provider_requests"] for e in effects),
        "model_provider_attempts": sum(e["model_provider_attempts"] for e in effects),
        "model_provider_successes": sum(e["model_provider_successes"] for e in effects),
        "system_total_tokens": sum(int(row["cost"]["system_total_tokens"]) for row in completed),
        "content_free_receipt_valid_tasks": len(receipts),
        "outer_or_accounting_failure_tasks": sum(not row["runtime_completed"] for row in checked),
        "terminal_effect_hard_failures": sum(sum(row["effect_health"].values()) for row in checked),
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    false_names = {
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
    }
    wall = copied.get("batch_wall_seconds")
    if (
        set(copied) != {*_INTEGER_NAMES, "batch_wall_seconds", *false_names}
        or any(isinstance(copied.get(name), bool) or not isinstance(copied.get(name), int) or copied[name] < 0 for name in _INTEGER_NAMES)
        or isinstance(wall, bool) or not isinstance(wall, (int, float)) or not math.isfinite(float(wall)) or wall < 0
        or any(copied.get(name) is not False for name in false_names)
        or copied["task_count"] != contract.TASK_COUNT
        or copied["terminal_tasks"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"] + copied["failure_as_zero_tasks"] != copied["terminal_tasks"]
        or copied["model_generated_tasks"] + copied["fallback_tasks"] != copied["completed_runtime_tasks"]
        or copied["prediction_changed_tasks"] > copied["same_raw_counterfactual_active_tasks"]
        or copied["content_free_receipt_valid_tasks"] != copied["completed_runtime_tasks"]
        or copied["outer_or_accounting_failure_tasks"] != copied["failure_as_zero_tasks"]
        or copied["model_provider_successes"] > copied["model_provider_requests"]
        or copied["model_provider_requests"] > copied["model_provider_attempts"]
        or copied["positive_signed_credit_count"] != 0
    ):
        raise RuntimeError("V2.51.87 aggregate drifted")
    return copied


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    aggregate = validate_aggregate(aggregate)
    gate = contract.mechanism_gate()
    completed = aggregate["completed_runtime_tasks"]
    checks = {
        "fixed_terminal_denominator": aggregate["task_count"] == aggregate["terminal_tasks"] == gate["fixed_task_denominator"],
        "all_runtime_tasks_completed": completed == gate["completed_runtime_tasks"] and aggregate["failure_as_zero_tasks"] <= gate["maximum_failure_as_zero_tasks"],
        "production_reliability": aggregate["model_generated_tasks"] >= gate["minimum_model_generated_tasks"] and aggregate["fallback_tasks"] <= gate["maximum_fallback_tasks"],
        "same_raw_activation_minimum": aggregate["same_raw_counterfactual_active_tasks"] >= gate["minimum_same_raw_counterfactual_active_tasks"],
        "prediction_change_minimum_and_exact_activation": aggregate["prediction_changed_tasks"] >= gate["minimum_prediction_changed_tasks"] and aggregate["prediction_changed_tasks"] == aggregate["same_raw_counterfactual_active_tasks"],
        "zero_export_failure": aggregate["parent_public_export_failure_tasks"] <= gate["maximum_public_export_failure_tasks"],
        "zero_additional_effect": aggregate["additional_effect_tasks"] == 0,
        "zero_outer_or_accounting_failure": aggregate["outer_or_accounting_failure_tasks"] <= gate["maximum_outer_or_accounting_failure_tasks"],
        "zero_terminal_effect_hard_failure": aggregate["terminal_effect_hard_failures"] <= gate["maximum_terminal_effect_hard_failures"],
        "exact_query_budget": aggregate["physical_queries"] == gate["exact_physical_queries_per_completed_task"] * completed,
        "fetch_cap_preserved": aggregate["physical_fetches"] <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "model_forward_cap_preserved": aggregate["physical_model_forwards"] <= gate["maximum_model_forwards_total"],
        "content_free_receipts_complete": aggregate["content_free_receipt_valid_tasks"] == completed,
        "positive_signed_credit_zero": aggregate["positive_signed_credit_count"] == gate["positive_signed_credit_count"],
    }
    failed = sorted(name for name, ok in checks.items() if not ok)
    return {
        "checks": checks,
        "failed_checks": failed,
        "same_response_mechanism_gate_passed": not failed,
        "postfreeze_external_evaluator_design": not failed,
        "external_evaluator_now": False,
        "deepwidebench_dev64_exact220_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        set(copied) != {"artifact_version", "role", "protocol_id", "created_at_unix", "execution_start_sha256", "execution_start_payload_sha256", "task_rows_sha256", "prediction_freeze_sha256", "aggregate", "mechanism_decision", "authorization", "result_payload_sha256"}
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25187_natural_quote_quality_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(aggregate, Mapping) or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("mechanism_decision") != mechanism_decision(aggregate)
        or copied.get("authorization") != {
            "forward_audit": True,
            "postfreeze_evaluator_implementation_only_after_pushed_forward_audit_go": True,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.87 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.51.87 shared runtime is not ready")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    future = (contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.EVALUATOR,
              contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL, contract.RESULT,
              contract.POSTAUDIT, contract.OUTPUT_ROOT)
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.51.87 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.51.87 watcher identity drifted")
    validate_search_class()
    tasks = contract.task_vector()
    _prepare_output()
    started = time.monotonic()
    values: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(ROOT, owner=contract.LEASE_OWNER, purpose=contract.LEASE_PURPOSE, path=ROOT / contract.LEASE_PATH):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {pool.submit(run_one_task, task): index for index, task in enumerate(tasks)}
            for future in as_completed(futures):
                values[futures[future]] = future.result()
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.51.87 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal({
        "artifact_version": 1,
        "role": "v25187_natural_quote_quality_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "task_count": contract.TASK_COUNT,
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "control_prediction_hash_vector_sha256": contract.payload_sha256([row["prediction_sha256"][contract.CONTROL_ARM] for row in rows]),
        "candidate_prediction_hash_vector_sha256": contract.payload_sha256([row["prediction_sha256"][contract.CANDIDATE_ARM] for row in rows]),
        "all_predictions_terminal_before_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }, "freeze_payload_sha256")
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    aggregate = aggregate_rows(rows, wall_seconds=time.monotonic() - started)
    decision = mechanism_decision(aggregate)
    forward = contract.seal({
        "artifact_version": 1,
        "role": "v25187_natural_quote_quality_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "execution_start_payload_sha256": start["execution_start_payload_sha256"],
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "aggregate": aggregate,
        "mechanism_decision": decision,
        "authorization": {
            "forward_audit": True,
            "postfreeze_evaluator_implementation_only_after_pushed_forward_audit_go": True,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        },
    }, "result_payload_sha256")
    _publish_json(ROOT / contract.FORWARD_RESULT, forward)
    return validate_forward_result(forward)


def main() -> None:
    value = run_forward()
    print(json.dumps({"path": str(contract.FORWARD_RESULT), "aggregate": value["aggregate"], "mechanism_decision": value["mechanism_decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()
