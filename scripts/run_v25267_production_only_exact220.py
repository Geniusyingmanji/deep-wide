#!/usr/bin/env python3
"""Run one atomic label-blind V2.52.67 production-only exact-220 forward."""

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

from deepwide_agent import v25110_exact_visible_schema as visible_schema  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25265_production_only_totality_runtime as runtime  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import HardTotalWallResponsesClient  # noqa: E402
from deepwide_agent.v24985_robust_late_page_fetch import validate_search_class  # noqa: E402
from scripts import run_v25260_observed_reliability_external as accounting  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25267_production_only_exact220_task_result"
ATTEMPT_ROLE = "v25267_production_only_exact220_attempt_claim"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    value = json.loads(contract.ordinary(ROOT, relative, tracked=tracked).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.67 expected JSON object")
    return value


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


def _atomic_progress(completed: int) -> None:
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25267_production_only_exact220_safe_progress",
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "completed": int(completed),
            "unfinished": contract.TASK_COUNT - int(completed),
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "progress_payload_sha256",
    )
    path = ROOT / contract.SAFE_PROGRESS
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.52.67 forward requires clean pushed HEAD")


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
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (contract.RUNNER_MARKER, "scripts/run_official_eval_local.py")
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        start.get("role") != "v25268_production_only_exact220_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or re.fullmatch(r"[0-9a-f]{40}", str(start.get("git_head") or "")) is None
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("selected") != contract.TASK_COUNT
        or start.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("truthful_physical_caps") != contract.PHYSICAL_CAPS
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("findings") != []
        or start.get("authorization")
        != {
            "single_exact220_forward": True,
            "postfreeze_official_evaluator": False,
            "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.52.67 execution start drifted")
    current = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    parents = contract.git(ROOT, "rev-list", "--parents", "-n", "1", current).split()
    changed = sorted(
        line.strip()
        for line in contract.git(
            ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", current
        ).splitlines()
        if line.strip()
    )
    if (
        current != target
        or len(parents) != 2
        or parents[1] != start["git_head"]
        or changed != [str(contract.EXECUTION_START)]
    ):
        raise RuntimeError("V2.52.67 execution-start commit boundary drifted")
    return protocol, start


def _prepare_output() -> None:
    root = ROOT / contract.OUTPUT_ROOT
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    slots = ROOT / contract.MODEL_SLOT_DIRECTORY
    slots.mkdir(mode=0o700)
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        _publish_json(
            slots / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v25267_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _search(question: str, deadline: float):
    return accounting.transport._EffectAccountingSearchClient(
        contract.SEARCH["proxy_url"],
        contract.SEARCH["model"],
        visible_question=question,
        reasoning_effort=contract.MODEL["reasoning_effort"],
        service_tier=contract.MODEL["service_tier"],
        timeout=contract.SEARCH["timeout_seconds"],
        max_retries=contract.SEARCH["max_retries"],
        absolute_deadline=deadline,
        cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        max_workers=contract.SEARCH["workers"],
        batch_size=contract.SEARCH["batch_size"],
        search_context_size=contract.SEARCH["context_size"],
        max_output_tokens=contract.SEARCH["max_output_tokens"],
        fetch_pages=False,
        fetch_workers=contract.SEARCH["fetch_workers"],
        fetch_timeout=contract.SEARCH["fetch_timeout_seconds"],
        max_page_chars=contract.LIMITS["page_chars"],
        hard_fetch_deadline_seconds=contract.SEARCH["hard_fetch_deadline_seconds"],
        stage_callback=lambda _event: None,
    )


def _visible_fallback(question: str) -> str:
    columns = visible_schema.extract_exact_visible_columns(question) or ["Unknown"]
    return (
        "```markdown\n| " + " | ".join(columns) + " |\n| "
        + " | ".join("---" for _ in columns) + " |\n| "
        + " | ".join("Unknown" for _ in columns) + " |\n```"
    )


def _terminal_outer_failure(
    task: Mapping[str, str], exc: BaseException, elapsed: float,
    budget: cap.PhysicalEffectBudget, model: Any, searches: Mapping[str, Any],
) -> dict[str, Any]:
    prediction = _visible_fallback(str(task["question"]))
    stage = copy.deepcopy(exc.stage_receipt) if isinstance(exc, runtime.ProductionOnlyStageError) else None
    budget_receipt = cap.validate_budget_receipt(budget.receipt())
    value = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": str(task["opaque_id"]),
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": False,
        "failure_as_zero": True,
        "outer_failure_type": (type(exc).__name__ or "Exception")[:128],
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "prediction_kind": "fallback",
        "runtime_result": None,
        "runtime_result_payload_sha256": None,
        "content_free_stage_receipt": stage,
        "content_free_budget_receipt": budget_receipt,
        "cost": None,
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "effect_health": accounting.transport._health_snapshot(model, searches),
        "actual_effect_snapshot": accounting.transport._actual_effect_snapshot(model, searches),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
        "contains_question_query_url_page_answer_or_credential_outside_prediction": False,
    }
    return contract.seal(value, "result_payload_sha256")


def _from_runtime(
    task: Mapping[str, str], result: Mapping[str, Any], stage: Mapping[str, Any],
    elapsed: float, budget: cap.PhysicalEffectBudget, model: Any,
    searches: Mapping[str, Any],
) -> dict[str, Any]:
    checked = runtime.validate_result(result)
    stage_receipt = runtime.validate_stage_receipt(stage)
    budget_receipt = cap.validate_budget_receipt(budget.receipt())
    if (
        checked["opaque_id"] != task["opaque_id"]
        or stage_receipt["failure_present"] is not False
        or stage_receipt["outer_physical_budget_receipt"] != budget_receipt
    ):
        raise RuntimeError("V2.52.67 completed task binding drifted")
    value = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": checked["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "prediction": checked["prediction"],
        "prediction_sha256": checked["prediction_sha256"],
        "prediction_kind": checked["prediction_kind"],
        "runtime_result": copy.deepcopy(checked),
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "content_free_stage_receipt": stage_receipt,
        "content_free_budget_receipt": budget_receipt,
        "cost": copy.deepcopy(checked["cost"]),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "effect_health": accounting.transport._health_snapshot(model, searches),
        "actual_effect_snapshot": accounting.transport._actual_effect_snapshot(model, searches),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
        "contains_question_query_url_page_answer_or_credential_outside_prediction": False,
    }
    return contract.seal(value, "result_payload_sha256")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    completed = copied.get("runtime_completed") is True
    stage = copied.get("content_free_stage_receipt")
    budget = copied.get("content_free_budget_receipt")
    effect = copied.get("actual_effect_snapshot")
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "opaque_id", "runtime_input_keys",
            "terminal", "runtime_completed", "failure_as_zero", "outer_failure_type",
            "prediction", "prediction_sha256", "prediction_kind", "runtime_result",
            "runtime_result_payload_sha256", "content_free_stage_receipt",
            "content_free_budget_receipt", "cost", "elapsed_seconds", "effect_health",
            "actual_effect_snapshot",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "retry_resume_skip_backfill_replacement_or_selective_rerun",
            "contains_question_query_url_page_answer_or_credential_outside_prediction",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id") or "")) is None
        or copied.get("runtime_input_keys") != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("runtime_completed"), bool)
        or not isinstance(copied.get("failure_as_zero"), bool)
        or copied.get("failure_as_zero") is completed
        or not isinstance(copied.get("prediction"), str)
        or not copied["prediction"]
        or copied.get("prediction_sha256") != hashlib.sha256(copied["prediction"].encode()).hexdigest()
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or copied["elapsed_seconds"] < 0
        or accounting.transport._health(copied.get("effect_health")) != copied.get("effect_health")
        or accounting.transport._validate_actual_effect_snapshot(effect or {}) != effect
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or effect["logical_queries"] != budget["query_admitted_count"]
        or effect["fetch_requests"] != budget["fetch_admitted_count"]
        or effect["model_logical_requests"] != budget["model_admitted_count"]
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_skip_backfill_replacement_or_selective_rerun",
                "contains_question_query_url_page_answer_or_credential_outside_prediction",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.52.67 task row drifted")
    if stage is not None:
        if (
            not isinstance(stage, Mapping)
            or runtime.validate_stage_receipt(stage) != dict(stage)
            or stage["outer_physical_budget_receipt"] != budget
        ):
            raise ValueError("V2.52.67 stage receipt drifted")
    if completed:
        result = copied.get("runtime_result")
        if (
            copied.get("outer_failure_type") is not None
            or not isinstance(result, Mapping)
            or runtime.validate_result(result) != dict(result)
            or copied.get("runtime_result_payload_sha256") != result["result_payload_sha256"]
            or copied.get("cost") != result["cost"]
            or copied["opaque_id"] != result["opaque_id"]
            or copied["prediction"] != result["prediction"]
            or stage is None
            or stage["failure_present"] is not False
        ):
            raise ValueError("V2.52.67 completed task row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or any(copied.get(name) is not None for name in ("runtime_result", "runtime_result_payload_sha256", "cost"))
        or stage is not None and stage["failure_present"] is not True
    ):
        raise ValueError("V2.52.67 outer failure row drifted")
    return copied


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.52.67 runtime input must be opaque_id and question")
    started = time.monotonic()
    budget = cap.PhysicalEffectBudget()
    model: Any = None
    searches: dict[str, Any] = {}
    try:
        deadline = started + float(contract.LIMITS["wall_seconds"])
        inner = HardTotalWallResponsesClient(
            contract.MODEL["proxy_url"], contract.MODEL["name"],
            reasoning_effort=contract.MODEL["reasoning_effort"],
            service_tier=contract.MODEL["service_tier"],
            timeout=contract.MODEL["timeout_seconds"],
            max_retries=contract.MODEL["max_retries"],
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
            stage_callback=lambda _event: None,
        )
        accounted = accounting.transport._EffectAccountingModelSlotLimiter(
            inner,
            slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
            output_root=ROOT / contract.OUTPUT_ROOT,
            slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        model = cap.HardCappedModelLimiter(accounted, budget)
        searches = {
            phase: cap.HardCappedSearchClient(_search(str(task["question"]), deadline), budget, phase=phase)
            for phase in runtime.PHASES
        }
        result, stage = runtime.run_task(
            task,
            model=model,
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            budget=budget,
            monotonic=time.monotonic,
        )
        row = _from_runtime(task, result, stage, time.monotonic() - started, budget, model, searches)
    except BaseException as exc:
        row = _terminal_outer_failure(task, exc, time.monotonic() - started, budget, model, searches)
    return validate_task_row(row)


AGGREGATE_INTS = (
    "task_count", "terminal_tasks", "completed_runtime_tasks", "failure_as_zero_tasks",
    "model_generated_tasks", "fallback_tasks", "stage_receipt_tasks",
    "stage_failure_tasks", "budget_receipt_tasks", "budget_rejection_tasks",
    "physical_queries", "physical_fetches", "physical_model_forwards",
    "maximum_queries_on_one_task", "maximum_fetches_on_one_task",
    "maximum_model_forwards_on_one_task", "system_total_tokens",
    "terminal_effect_health_failures", "positive_signed_credit_count",
)


def aggregate_rows(rows: Sequence[Mapping[str, Any]], *, wall_seconds: float) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    tasks = contract.task_vector(ROOT)
    if len(checked) != contract.TASK_COUNT or [row["opaque_id"] for row in checked] != [task["opaque_id"] for task in tasks]:
        raise RuntimeError("V2.52.67 fixed task vector drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    stages = [row["content_free_stage_receipt"] for row in checked if row["content_free_stage_receipt"] is not None]
    budgets = [row["content_free_budget_receipt"] for row in checked]
    effects = [row["actual_effect_snapshot"] for row in checked]
    value = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "model_generated_tasks": sum(row["runtime_completed"] and row["prediction_kind"] == "model_generated" for row in checked),
        "fallback_tasks": sum(not row["runtime_completed"] or row["prediction_kind"] == "fallback" for row in checked),
        "stage_receipt_tasks": len(stages),
        "stage_failure_tasks": sum(stage["failure_present"] for stage in stages),
        "budget_receipt_tasks": len(budgets),
        "budget_rejection_tasks": sum(any(budget[name] > 0 for name in ("query_rejected_count", "fetch_rejected_count", "model_rejected_count")) for budget in budgets),
        "physical_queries": sum(effect["logical_queries"] for effect in effects),
        "physical_fetches": sum(effect["fetch_requests"] for effect in effects),
        "physical_model_forwards": sum(effect["model_logical_requests"] for effect in effects),
        "maximum_queries_on_one_task": max((effect["logical_queries"] for effect in effects), default=0),
        "maximum_fetches_on_one_task": max((effect["fetch_requests"] for effect in effects), default=0),
        "maximum_model_forwards_on_one_task": max((effect["model_logical_requests"] for effect in effects), default=0),
        "system_total_tokens": sum(int(row["cost"]["system_total_tokens"]) for row in completed),
        "terminal_effect_health_failures": sum(sum(row["effect_health"].values()) for row in checked),
        "positive_signed_credit_count": 0,
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_question_query_url_page_answer_prediction_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "evaluator_or_quality_metric_called": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    false_names = {
        "contains_question_query_url_page_answer_prediction_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "evaluator_or_quality_metric_called",
    }
    if (
        set(copied) != {*AGGREGATE_INTS, "batch_wall_seconds", *false_names}
        or any(isinstance(copied.get(name), bool) or not isinstance(copied.get(name), int) or copied[name] < 0 for name in AGGREGATE_INTS)
        or isinstance(copied.get("batch_wall_seconds"), bool)
        or not isinstance(copied.get("batch_wall_seconds"), (int, float))
        or not math.isfinite(float(copied["batch_wall_seconds"]))
        or any(copied.get(name) is not False for name in false_names)
        or copied["task_count"] != copied["terminal_tasks"] != 0
        or copied["task_count"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"] + copied["failure_as_zero_tasks"] != contract.TASK_COUNT
        or copied["model_generated_tasks"] + copied["fallback_tasks"] != contract.TASK_COUNT
        or copied["budget_receipt_tasks"] != contract.TASK_COUNT
        or copied["maximum_queries_on_one_task"] > cap.QUERY_CAP
        or copied["maximum_fetches_on_one_task"] > cap.FETCH_CAP
        or copied["maximum_model_forwards_on_one_task"] > cap.MODEL_CAP
        or copied["positive_signed_credit_count"] != 0
    ):
        raise ValueError("V2.52.67 aggregate drifted")
    return copied


def validate_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != contract.SUMMARY_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("selected") != contract.TASK_COUNT
        or copied.get("completed") != contract.TASK_COUNT
        or copied.get("failed") != 0
        or copied.get("model_generated_tables", -1) + copied.get("fallback_tables", -1) != contract.TASK_COUNT
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("official_evaluator_called") is not False
        or not contract.sealed(copied, "summary_payload_sha256")
    ):
        raise RuntimeError("V2.52.67 summary drifted")
    return copied


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        copied.get("role") != contract.FORWARD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("selected") != contract.TASK_COUNT
        or copied.get("terminal_predictions") != contract.TASK_COUNT
        or copied.get("model_generated_tables", -1) + copied.get("fallback_tables", -1) != contract.TASK_COUNT
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("official_evaluator_called") is not False
        or copied.get("positive_signed_credit_count") != 0
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.52.67 forward result drifted")
    return copied


def _attempt_claim(protocol: Mapping[str, Any], start: Mapping[str, Any]) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ATTEMPT_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "execution_start_payload_sha256": start["execution_start_payload_sha256"],
        "task_vector_sha256": contract.payload_sha256(contract.task_vector(ROOT, protocol)),
        "selected": contract.TASK_COUNT,
        "attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect": True,
        "retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "evaluator_deepwidebench_avg4_leaderboard_or_sota": False,
    }
    return validate_attempt_claim(contract.seal(value, "claim_payload_sha256"))


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "protocol_sha256", "execution_start_sha256",
            "execution_start_payload_sha256", "task_vector_sha256", "selected",
            "attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect",
            "retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "evaluator_deepwidebench_avg4_leaderboard_or_sota", "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ATTEMPT_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("selected") != contract.TASK_COUNT
        or copied.get("attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "evaluator_deepwidebench_avg4_leaderboard_or_sota",
            )
        )
        or not contract.sealed(copied, "claim_payload_sha256")
    ):
        raise ValueError("V2.52.67 attempt claim drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.52.67 shared runtime is not ready")
    future = (
        contract.ATTEMPT_CLAIM, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.52.67 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.52.67 protected watcher identity drifted")
    validate_search_class()
    claim = _attempt_claim(protocol, start)
    _publish_json(ROOT / contract.ATTEMPT_CLAIM, claim)
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    tasks = contract.task_vector(ROOT, protocol)
    _prepare_output()
    started = time.monotonic()
    values: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(ROOT, owner=contract.LEASE_OWNER, purpose=contract.LEASE_PURPOSE, path=ROOT / contract.LEASE_PATH):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {pool.submit(run_one_task, task): index for index, task in enumerate(tasks)}
            completed = 0
            for future in as_completed(futures):
                values[futures[future]] = validate_task_row(future.result())
                completed += 1
                _atomic_progress(completed)
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT or [row["opaque_id"] for row in rows] != [task["opaque_id"] for task in tasks]:
        raise RuntimeError("V2.52.67 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    aggregate = aggregate_rows(rows, wall_seconds=time.monotonic() - started)
    predictions = [
        {
            "opaque_id": row["opaque_id"],
            "status": "completed",
            "prediction": row["prediction"],
            "prediction_sha256": row["prediction_sha256"],
            "completion_kind": "model_generated" if row["runtime_completed"] and row["prediction_kind"] == "model_generated" else "best_effort_fallback",
            "elapsed_seconds": row["elapsed_seconds"],
            "cost": copy.deepcopy(row["cost"]),
            "label_blind": True,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        for row in rows
    ]
    _publish_jsonl(ROOT / contract.RUNTIME_PREDICTIONS, predictions)
    summary = contract.seal(
        {
            "artifact_version": 1,
            "role": contract.SUMMARY_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "selected": contract.TASK_COUNT,
            "completed": contract.TASK_COUNT,
            "failed": 0,
            "runtime_completed": aggregate["completed_runtime_tasks"],
            "failure_as_zero_tasks": aggregate["failure_as_zero_tasks"],
            "model_generated_tables": aggregate["model_generated_tasks"],
            "fallback_tables": aggregate["fallback_tasks"],
            "system_total_tokens": aggregate["system_total_tokens"],
            "forward_wall_seconds": aggregate["batch_wall_seconds"],
            "official_evaluator_called": False,
            "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
        },
        "summary_payload_sha256",
    )
    _publish_json(ROOT / contract.RUN_SUMMARY, summary)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": contract.FREEZE_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "terminal": contract.TASK_COUNT,
            "runtime_results_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "prediction_hashes_sha256": contract.payload_sha256([row["prediction_sha256"] for row in predictions]),
            "all_predictions_terminal_before_mapping_query_answer_or_official_evaluator_open": True,
            "mapping_gold_or_evaluator_opened_or_hashed": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": contract.FORWARD_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "terminal_predictions": contract.TASK_COUNT,
            "model_generated_tables": summary["model_generated_tables"],
            "fallback_tables": summary["fallback_tables"],
            "system_total_tokens": summary["system_total_tokens"],
            "forward_wall_seconds": summary["forward_wall_seconds"],
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "attempt_claim_sha256": contract.sha256(ROOT / contract.ATTEMPT_CLAIM),
            "runtime_results_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "aggregate": aggregate,
            "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
            "official_evaluator_called": False,
            "retry_resume_skip_backfill_replacement_or_selective_rerun_launched": False,
            "authorization": {
                "forward_audit": True,
                "postfreeze_exact220_evaluator_only_after_pushed_forward_audit": True,
                "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
                "leaderboard_or_sota": False,
            },
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, forward)
    return validate_forward_result(forward)


def main() -> None:
    value = run_forward()
    print(json.dumps({
        "path": str(contract.FORWARD_RESULT),
        "selected": value["selected"],
        "terminal_predictions": value["terminal_predictions"],
        "model_generated_tables": value["model_generated_tables"],
        "fallback_tables": value["fallback_tables"],
        "forward_wall_seconds": value["forward_wall_seconds"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
