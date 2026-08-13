#!/usr/bin/env python3
"""Run the single authorized fresh20 paired-checkpoint reliability forward."""

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

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25280_paired_checkpoint_reliability_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import HardTotalWallResponsesClient  # noqa: E402
from deepwide_agent.v24985_robust_late_page_fetch import validate_search_class  # noqa: E402
from scripts import run_v25248_header_totality_shadow_external as transport  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


runtime = contract.runtime
TASK_ROLE = "v25280_paired_checkpoint_reliability_task_result"
FORWARD_ROLE = "v25280_paired_checkpoint_reliability_forward_result"
FREEZE_ROLE = "v25280_paired_checkpoint_reliability_prediction_freeze"
CLAIM_ROLE = "v25280_paired_checkpoint_reliability_attempt_claim"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.80 expected JSON object")
    return value


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    transport._publish_json(path, value)


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    transport._publish_jsonl(path, rows)


def _atomic_progress(completed: int) -> None:
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25280_paired_checkpoint_reliability_safe_progress",
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "completed": int(completed),
            "unfinished": contract.TASK_COUNT - int(completed),
            "contains_question_package_query_url_page_prediction_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "progress_payload_sha256",
    )
    path = ROOT / contract.SAFE_PROGRESS
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _clean_pushed() -> None:
    if (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.52.80 forward requires clean pushed HEAD")


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
    markers = (str(contract.RUNNER), "scripts/run_official_eval_local.py")
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


def execution_start_commit_boundary(
    start: Mapping[str, Any], *, current_head: str, current_target: str
) -> bool:
    try:
        parent_row = contract.git(
            ROOT, "rev-list", "--parents", "-n", "1", current_head
        ).split()
        changed = sorted(
            line.strip()
            for line in contract.git(
                ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", current_head
            ).splitlines()
            if line.strip()
        )
    except BaseException:
        return False
    return bool(
        current_head == current_target
        and len(parent_row) == 2
        and parent_row[0] == current_head
        and parent_row[1] == start.get("git_head")
        and changed == [str(contract.EXECUTION_START)]
    )


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    current_head = contract.git(ROOT, "rev-parse", "HEAD")
    current_target = contract.git(ROOT, "rev-parse", "target/main")
    if (
        set(start)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "status",
            "created_at_unix",
            "git_head",
            "protocol_sha256",
            "preactivation_audit_sha256",
            "source_manifest",
            "task_vector_sha256",
            "selected",
            "executor_concurrency",
            "model_slot_cap",
            "runtime_input_contract",
            "truthful_physical_caps",
            "paired_estimand",
            "protected_watchers",
            "findings",
            "authorization",
            "execution_start_payload_sha256",
        }
        or start.get("artifact_version") != 1
        or start.get("role")
        != "v25282_paired_checkpoint_reliability_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or isinstance(start.get("created_at_unix"), bool)
        or not isinstance(start.get("created_at_unix"), int)
        or re.fullmatch(r"[0-9a-f]{40}", str(start.get("git_head"))) is None
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("source_manifest") != protocol["source_manifest"]
        or {
            path: contract.sha256(contract.ordinary(ROOT, Path(path), tracked=True))
            for path in protocol["source_manifest"]
        }
        != dict(protocol["source_manifest"])
        or start.get("task_vector_sha256") != contract.TASK_VECTOR_SHA256
        or start.get("selected") != contract.TASK_COUNT
        or start.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("truthful_physical_caps") != contract.PHYSICAL_CAPS
        or start.get("paired_estimand")
        != {
            "one_real_forward_per_task": True,
            "candidate_local_same_checkpoint_projection": True,
            "fixed_injected_stage": runtime.INJECTED_STAGE,
            "fixed_injected_failure_type": runtime.INJECTED_FAILURE_TYPE,
        }
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("findings") != []
        or start.get("authorization")
        != {
            "single_fresh20_paired_checkpoint_reliability_forward": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "candidate_quality_or_prediction_change_claim": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not execution_start_commit_boundary(
            start, current_head=current_head, current_target=current_target
        )
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.52.80 execution start drifted")
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
                "role": "v25280_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def build_attempt_claim(
    protocol: Mapping[str, Any], start: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    checked = contract.validate_protocol(ROOT, protocol)
    if (
        start.get("role") != "v25282_paired_checkpoint_reliability_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise ValueError("V2.52.80 attempt claim start drifted")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": CLAIM_ROLE,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "protocol_id": contract.PROTOCOL_ID,
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start[
                "execution_start_payload_sha256"
            ],
            "source_manifest": copy.deepcopy(checked["source_manifest"]),
            "task_vector_sha256": contract.TASK_VECTOR_SHA256,
            "selected": contract.TASK_COUNT,
            "attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect": True,
            "retry_resume_skip_replacement_selective_rerun_or_second_attempt": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "candidate_quality_or_prediction_change_claim": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
        "claim_payload_sha256",
    )


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "protocol_id",
            "protocol_sha256",
            "execution_start_sha256",
            "execution_start_payload_sha256",
            "source_manifest",
            "task_vector_sha256",
            "selected",
            "attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect",
            "retry_resume_skip_replacement_selective_rerun_or_second_attempt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "candidate_quality_or_prediction_change_claim",
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota",
            "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CLAIM_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name))) is None
            for name in (
                "protocol_sha256",
                "execution_start_sha256",
                "execution_start_payload_sha256",
                "task_vector_sha256",
            )
        )
        or copied.get("task_vector_sha256") != contract.TASK_VECTOR_SHA256
        or copied.get("selected") != contract.TASK_COUNT
        or not isinstance(copied.get("source_manifest"), Mapping)
        or copied.get(
            "attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect"
        )
        is not True
        or any(
            copied.get(name) is not False
            for name in (
                "retry_resume_skip_replacement_selective_rerun_or_second_attempt",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "candidate_quality_or_prediction_change_claim",
                "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota",
            )
        )
        or not contract.sealed(copied, "claim_payload_sha256")
    ):
        raise ValueError("V2.52.80 attempt claim drifted")
    return copied


def _search(question: str, deadline: float) -> transport.RobustLatePageBoundSearchClient:
    return transport._EffectAccountingSearchClient(
        contract.SEARCH["proxy_url"],
        contract.SEARCH["model"],
        visible_question=question,
        reasoning_effort=contract.SEARCH["reasoning_effort"],
        service_tier=contract.SEARCH["service_tier"],
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


def _fallback_table(task: Mapping[str, str]) -> str:
    rows = contract.packages_from_question(task["question"])
    body = "\n".join(
        f"| {package} | Unknown | Unknown | Unknown |" for package in rows
    )
    return (
        "```markdown\n| "
        + " | ".join(contract.COLUMNS)
        + " |\n| "
        + " | ".join("---" for _ in contract.COLUMNS)
        + " |\n"
        + body
        + "\n```"
    )


def _terminal_outer_failure(
    task: Mapping[str, str],
    exc: BaseException,
    elapsed: float,
    budget: cap.PhysicalEffectBudget,
    model: Any,
    searches: Mapping[str, Any],
) -> dict[str, Any]:
    prediction = _fallback_table(task)
    control_stage = (
        copy.deepcopy(exc.stage_receipt)
        if isinstance(exc, runtime.parent.ProductionCheckpointStageError)
        else None
    )
    budget_receipt = cap.validate_budget_receipt(budget.receipt())
    return contract.seal(
        {
            "artifact_version": 1,
            "role": TASK_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "opaque_id": str(task["opaque_id"]),
            "runtime_input_keys": [
                "opaque_id",
                "question",
                "same_forward_public_pages",
            ],
            "terminal": True,
            "runtime_completed": False,
            "failure_as_zero": True,
            "outer_failure_type": (type(exc).__name__ or "Exception")[:128],
            "prediction": prediction,
            "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
            "prediction_kind": "fallback",
            "paired_runtime_result": None,
            "paired_runtime_result_payload_sha256": None,
            "control_stage_receipt": control_stage,
            "candidate_stage_receipt": None,
            "content_free_paired_receipt": None,
            "content_free_budget_receipt": budget_receipt,
            "cost": None,
            "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
            "effect_health": transport._health_snapshot(model, searches),
            "actual_effect_snapshot": transport._actual_effect_snapshot(
                model, searches
            ),
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
            "contains_question_package_query_url_page_answer_or_credential_outside_prediction": False,
        },
        "result_payload_sha256",
    )


def _from_runtime(
    task: Mapping[str, str],
    value: Mapping[str, Any],
    elapsed: float,
    budget: cap.PhysicalEffectBudget,
    model: Any,
    searches: Mapping[str, Any],
    *,
    health: Mapping[str, int] | None = None,
    effect: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = runtime.validate_result(value)
    if checked["opaque_id"] != task["opaque_id"]:
        raise RuntimeError("V2.52.80 completed identity drifted")
    control = checked["control_result"]
    control_stage = checked["control_stage_receipt"]
    candidate_stage = checked["candidate_stage_receipt"]
    paired = checked["content_free_paired_receipt"]
    prediction = control["prediction"]
    budget_receipt = cap.validate_budget_receipt(budget.receipt())
    if (
        control_stage["outer_physical_budget_receipt"] != budget_receipt
        or candidate_stage is not None
        and candidate_stage["outer_physical_budget_receipt"] != budget_receipt
    ):
        raise RuntimeError("V2.52.80 budget receipt drifted")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": TASK_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "opaque_id": checked["opaque_id"],
            "runtime_input_keys": [
                "opaque_id",
                "question",
                "same_forward_public_pages",
            ],
            "terminal": True,
            "runtime_completed": True,
            "failure_as_zero": False,
            "outer_failure_type": None,
            "prediction": prediction,
            "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
            "prediction_kind": control["prediction_kind"],
            "paired_runtime_result": copy.deepcopy(checked),
            "paired_runtime_result_payload_sha256": checked["result_payload_sha256"],
            "control_stage_receipt": copy.deepcopy(control_stage),
            "candidate_stage_receipt": copy.deepcopy(candidate_stage),
            "content_free_paired_receipt": copy.deepcopy(paired),
            "content_free_budget_receipt": budget_receipt,
            "cost": copy.deepcopy(control["cost"]),
            "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
            "effect_health": (
                transport._health(health)
                if health is not None
                else transport._health_snapshot(model, searches)
            ),
            "actual_effect_snapshot": (
                transport._validate_actual_effect_snapshot(effect)
                if effect is not None
                else transport._actual_effect_snapshot(model, searches)
            ),
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
            "contains_question_package_query_url_page_answer_or_credential_outside_prediction": False,
        },
        "result_payload_sha256",
    )


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    completed = copied.get("runtime_completed") is True
    control_stage = copied.get("control_stage_receipt")
    candidate_stage = copied.get("candidate_stage_receipt")
    paired = copied.get("content_free_paired_receipt")
    budget = copied.get("content_free_budget_receipt")
    effect = copied.get("actual_effect_snapshot")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "opaque_id",
            "runtime_input_keys",
            "terminal",
            "runtime_completed",
            "failure_as_zero",
            "outer_failure_type",
            "prediction",
            "prediction_sha256",
            "prediction_kind",
            "paired_runtime_result",
            "paired_runtime_result_payload_sha256",
            "control_stage_receipt",
            "candidate_stage_receipt",
            "content_free_paired_receipt",
            "content_free_budget_receipt",
            "cost",
            "elapsed_seconds",
            "effect_health",
            "actual_effect_snapshot",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "retry_resume_skip_population_replacement_or_selective_rerun",
            "contains_question_package_query_url_page_answer_or_credential_outside_prediction",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id")))
        is None
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("runtime_completed"), bool)
        or not isinstance(copied.get("failure_as_zero"), bool)
        or copied.get("failure_as_zero") is completed
        or not isinstance(copied.get("prediction"), str)
        or not copied["prediction"]
        or copied.get("prediction_sha256")
        != hashlib.sha256(copied["prediction"].encode()).hexdigest()
        or copied.get("prediction_kind")
        not in {"model_generated", "fallback", "visible_fallback"}
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or copied["elapsed_seconds"] < 0
        or transport._health(copied.get("effect_health"))
        != copied.get("effect_health")
        or transport._validate_actual_effect_snapshot(effect or {}) != effect
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
                "retry_resume_skip_population_replacement_or_selective_rerun",
                "contains_question_package_query_url_page_answer_or_credential_outside_prediction",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.52.80 task row drifted")
    if control_stage is not None and (
        not isinstance(control_stage, Mapping)
        or runtime.parent.validate_stage_receipt(control_stage) != dict(control_stage)
        or control_stage["outer_physical_budget_receipt"] != budget
    ):
        raise ValueError("V2.52.80 control stage receipt drifted")
    if candidate_stage is not None and (
        not isinstance(candidate_stage, Mapping)
        or runtime.parent.validate_stage_receipt(candidate_stage) != dict(candidate_stage)
        or candidate_stage["outer_physical_budget_receipt"] != budget
    ):
        raise ValueError("V2.52.80 candidate stage receipt drifted")
    if completed:
        result = copied.get("paired_runtime_result")
        if (
            copied.get("outer_failure_type") is not None
            or not isinstance(result, Mapping)
            or runtime.validate_result(result) != dict(result)
            or copied.get("paired_runtime_result_payload_sha256")
            != result["result_payload_sha256"]
            or copied.get("cost") != result["control_result"]["cost"]
            or copied["opaque_id"] != result["opaque_id"]
            or control_stage != result["control_stage_receipt"]
            or candidate_stage != result["candidate_stage_receipt"]
            or not isinstance(paired, Mapping)
            or runtime.validate_receipt(paired) != dict(paired)
            or paired != result["content_free_paired_receipt"]
            or copied["prediction"] != result["control_result"]["prediction"]
            or copied["prediction_kind"]
            != result["control_result"]["prediction_kind"]
        ):
            raise ValueError("V2.52.80 completed task row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or len(copied["outer_failure_type"]) > 128
        or any(
            copied.get(name) is not None
            for name in (
                "paired_runtime_result",
                "paired_runtime_result_payload_sha256",
                "candidate_stage_receipt",
                "content_free_paired_receipt",
                "cost",
            )
        )
    ):
        raise ValueError("V2.52.80 outer failure task row drifted")
    return copied


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.52.80 runtime input must be opaque_id and question")
    started = time.monotonic()
    budget = cap.PhysicalEffectBudget()
    model: Any = None
    searches: dict[str, Any] = {}
    try:
        deadline = started + float(contract.LIMITS["wall_seconds"])
        inner = HardTotalWallResponsesClient(
            contract.MODEL["proxy_url"],
            contract.MODEL["name"],
            reasoning_effort=contract.MODEL["reasoning_effort"],
            service_tier=contract.MODEL["service_tier"],
            timeout=contract.MODEL["timeout_seconds"],
            max_retries=contract.MODEL["max_retries"],
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
            stage_callback=lambda _event: None,
        )
        accounted = transport._EffectAccountingModelSlotLimiter(
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
            phase: cap.HardCappedSearchClient(
                _search(str(task["question"]), deadline), budget, phase=phase
            )
            for phase in runtime.parent.PHASES
        }
        result = runtime.run_paired_task(
            task,
            model=model,
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            budget=budget,
            monotonic=time.monotonic,
        )
        row = _from_runtime(
            task, result, time.monotonic() - started, budget, model, searches
        )
    except BaseException as exc:
        row = _terminal_outer_failure(
            task, exc, time.monotonic() - started, budget, model, searches
        )
    return validate_task_row(row)


_AGGREGATE_INTS = (
    "task_count",
    "terminal_tasks",
    "completed_runtime_tasks",
    "failure_as_zero_tasks",
    "model_generated_tasks",
    "fallback_tasks",
    "clean_trusted_checkpoint_tasks",
    "ineligible_no_checkpoint_tasks",
    "ineligible_natural_recovery_tasks",
    "candidate_recovery_tasks",
    "prediction_equal_tasks",
    "checkpoint_equal_tasks",
    "cost_equal_tasks",
    "budget_receipt_equal_tasks",
    "fixed_fault_identity_tasks",
    "budget_receipt_tasks",
    "budget_rejection_tasks",
    "physical_queries",
    "physical_fetches",
    "physical_model_forwards",
    "maximum_queries_on_one_task",
    "maximum_fetches_on_one_task",
    "maximum_model_forwards_on_one_task",
    "candidate_additional_queries",
    "candidate_additional_fetches",
    "candidate_additional_model_forwards",
    "candidate_additional_system_total_tokens",
    "system_total_tokens",
    "terminal_effect_health_failures",
    "positive_signed_credit_count",
)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    false_names = {
        "contains_question_package_query_url_page_answer_prediction_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "evaluator_or_quality_metric_called",
    }
    if (
        set(copied) != {*_AGGREGATE_INTS, "batch_wall_seconds", *false_names}
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _AGGREGATE_INTS
        )
        or isinstance(copied.get("batch_wall_seconds"), bool)
        or not isinstance(copied.get("batch_wall_seconds"), (int, float))
        or not math.isfinite(float(copied["batch_wall_seconds"]))
        or copied["batch_wall_seconds"] < 0
        or any(copied.get(name) is not False for name in false_names)
        or copied["task_count"] != contract.TASK_COUNT
        or copied["terminal_tasks"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"] + copied["failure_as_zero_tasks"]
        != copied["terminal_tasks"]
        or copied["model_generated_tasks"] + copied["fallback_tasks"]
        != copied["terminal_tasks"]
        or copied["clean_trusted_checkpoint_tasks"]
        + copied["ineligible_no_checkpoint_tasks"]
        + copied["ineligible_natural_recovery_tasks"]
        > copied["completed_runtime_tasks"]
        or copied["candidate_recovery_tasks"]
        > copied["clean_trusted_checkpoint_tasks"]
        or any(
            copied[name] > copied["candidate_recovery_tasks"]
            for name in (
                "prediction_equal_tasks",
                "checkpoint_equal_tasks",
                "cost_equal_tasks",
                "budget_receipt_equal_tasks",
                "fixed_fault_identity_tasks",
            )
        )
        or copied["budget_receipt_tasks"] != copied["terminal_tasks"]
        or copied["maximum_queries_on_one_task"] > cap.QUERY_CAP
        or copied["maximum_fetches_on_one_task"] > cap.FETCH_CAP
        or copied["maximum_model_forwards_on_one_task"] > cap.MODEL_CAP
        or copied["positive_signed_credit_count"] != 0
    ):
        raise ValueError("V2.52.80 aggregate drifted")
    return copied


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    tasks = contract.task_vector(ROOT)
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in tasks]
    ):
        raise RuntimeError("V2.52.80 fixed task vector drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    paired = [
        row["content_free_paired_receipt"]
        for row in completed
        if row["content_free_paired_receipt"] is not None
    ]
    budgets = [row["content_free_budget_receipt"] for row in checked]
    effects = [row["actual_effect_snapshot"] for row in checked]
    value = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "model_generated_tasks": sum(
            row["runtime_completed"]
            and row["prediction_kind"] == "model_generated"
            for row in checked
        ),
        "fallback_tasks": sum(
            not row["runtime_completed"]
            or row["prediction_kind"] != "model_generated"
            for row in checked
        ),
        "clean_trusted_checkpoint_tasks": sum(
            receipt["paired_projection_eligible"] for receipt in paired
        ),
        "ineligible_no_checkpoint_tasks": sum(
            receipt["eligibility_reason"] == "control_has_no_trusted_checkpoint"
            for receipt in paired
        ),
        "ineligible_natural_recovery_tasks": sum(
            receipt["eligibility_reason"]
            == "control_not_clean_checkpoint_result"
            for receipt in paired
        ),
        "candidate_recovery_tasks": sum(
            receipt["candidate_recovery_created"] for receipt in paired
        ),
        "prediction_equal_tasks": sum(
            receipt["control_and_candidate_prediction_equal"] for receipt in paired
        ),
        "checkpoint_equal_tasks": sum(
            receipt["control_and_candidate_checkpoint_equal"] for receipt in paired
        ),
        "cost_equal_tasks": sum(
            receipt["control_and_candidate_cost_equal"] for receipt in paired
        ),
        "budget_receipt_equal_tasks": sum(
            receipt["control_and_candidate_physical_budget_receipt_equal"]
            for receipt in paired
        ),
        "fixed_fault_identity_tasks": sum(
            receipt["candidate_injected_failure_stage"] == runtime.INJECTED_STAGE
            and receipt["candidate_injected_failure_type"]
            == runtime.INJECTED_FAILURE_TYPE
            for receipt in paired
        ),
        "budget_receipt_tasks": len(budgets),
        "budget_rejection_tasks": sum(
            any(
                budget[name] > 0
                for name in (
                    "query_rejected_count",
                    "fetch_rejected_count",
                    "model_rejected_count",
                )
            )
            for budget in budgets
        ),
        "physical_queries": sum(effect["logical_queries"] for effect in effects),
        "physical_fetches": sum(effect["fetch_requests"] for effect in effects),
        "physical_model_forwards": sum(
            effect["model_logical_requests"] for effect in effects
        ),
        "maximum_queries_on_one_task": max(
            (effect["logical_queries"] for effect in effects), default=0
        ),
        "maximum_fetches_on_one_task": max(
            (effect["fetch_requests"] for effect in effects), default=0
        ),
        "maximum_model_forwards_on_one_task": max(
            (effect["model_logical_requests"] for effect in effects), default=0
        ),
        "candidate_additional_queries": sum(
            receipt["candidate_additional_query_count"] for receipt in paired
        ),
        "candidate_additional_fetches": sum(
            receipt["candidate_additional_fetch_count"] for receipt in paired
        ),
        "candidate_additional_model_forwards": sum(
            receipt["candidate_additional_model_forward_count"] for receipt in paired
        ),
        "candidate_additional_system_total_tokens": sum(
            receipt["candidate_additional_system_total_tokens"] for receipt in paired
        ),
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"]) for row in completed
        ),
        "terminal_effect_health_failures": sum(
            sum(row["effect_health"].values()) for row in checked
        ),
        "positive_signed_credit_count": 0,
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_question_package_query_url_page_answer_prediction_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "evaluator_or_quality_metric_called": False,
    }
    return validate_aggregate(value)


def reliability_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_aggregate(aggregate)
    gate = contract.reliability_gate()
    checks = {
        "fixed_terminal_denominator": checked["task_count"]
        == checked["terminal_tasks"]
        == gate["fixed_task_denominator"],
        "all_runtime_tasks_completed": checked["completed_runtime_tasks"]
        == gate["required_completed_runtime_tasks"],
        "outer_failure_zero": checked["failure_as_zero_tasks"]
        <= gate["maximum_outer_failure_tasks"],
        "all_clean_trusted_checkpoints": checked["clean_trusted_checkpoint_tasks"]
        == gate["required_clean_trusted_checkpoint_tasks"],
        "all_candidate_recoveries_created": checked["candidate_recovery_tasks"]
        == gate["required_candidate_recovery_tasks"],
        "all_predictions_equal": checked["prediction_equal_tasks"]
        == gate["required_prediction_equal_tasks"],
        "all_checkpoints_equal": checked["checkpoint_equal_tasks"]
        == gate["required_checkpoint_equal_tasks"],
        "all_costs_equal": checked["cost_equal_tasks"]
        == gate["required_cost_equal_tasks"],
        "all_budget_receipts_equal": checked["budget_receipt_equal_tasks"]
        == gate["required_budget_receipt_equal_tasks"],
        "all_fixed_fault_identities": checked["fixed_fault_identity_tasks"]
        == gate["required_fixed_fault_identity_tasks"],
        "budget_rejection_zero": checked["budget_rejection_tasks"]
        <= gate["maximum_budget_rejection_tasks"],
        "candidate_additional_effect_zero": (
            checked["candidate_additional_queries"]
            <= gate["maximum_candidate_additional_queries_total"]
            and checked["candidate_additional_fetches"]
            <= gate["maximum_candidate_additional_fetches_total"]
            and checked["candidate_additional_model_forwards"]
            <= gate["maximum_candidate_additional_model_forwards_total"]
            and checked["candidate_additional_system_total_tokens"]
            <= gate["maximum_candidate_additional_system_total_tokens"]
        ),
        "query_cap_preserved": checked["physical_queries"]
        <= gate["maximum_physical_queries_total"],
        "fetch_cap_preserved": checked["physical_fetches"]
        <= gate["maximum_physical_fetches_total"],
        "model_cap_preserved": checked["physical_model_forwards"]
        <= gate["maximum_model_forwards_total"],
        "all_budget_receipts_valid": checked["budget_receipt_tasks"]
        == checked["terminal_tasks"],
        "positive_signed_credit_zero": checked["positive_signed_credit_count"]
        == gate["positive_signed_credit_count"],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "reliability_gate_passed": not failed,
        "postforward_reliability_audit_and_diagnosis": True,
        "candidate_quality_or_prediction_change_claim": False,
        "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "execution_start_sha256",
            "attempt_claim_sha256",
            "task_rows_sha256",
            "prediction_freeze_sha256",
            "aggregate",
            "reliability_decision",
            "authorization",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != FORWARD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name))) is None
            for name in (
                "execution_start_sha256",
                "attempt_claim_sha256",
                "task_rows_sha256",
                "prediction_freeze_sha256",
            )
        )
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("reliability_decision") != reliability_decision(aggregate)
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "postforward_reliability_diagnosis": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "candidate_quality_or_prediction_change_claim": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.52.80 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.52.80 shared runtime is not ready")
    future = (
        contract.ATTEMPT_CLAIM,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.52.80 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.52.80 protected watcher identity drifted")
    validate_search_class()
    tasks = contract.task_vector(ROOT)
    claim = build_attempt_claim(protocol, start)
    _publish_json(ROOT / contract.ATTEMPT_CLAIM, claim)
    validate_attempt_claim(_read(contract.ATTEMPT_CLAIM, tracked=False))
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    _prepare_output()
    started = time.monotonic()
    values: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {
                pool.submit(run_one_task, task): index
                for index, task in enumerate(tasks)
            }
            completed = 0
            for future in as_completed(futures):
                index = futures[future]
                values[index] = validate_task_row(future.result())
                completed += 1
                _atomic_progress(completed)
    rows = [validate_task_row(row) for row in values if row is not None]
    if (
        len(rows) != contract.TASK_COUNT
        or [row["opaque_id"] for row in rows]
        != [task["opaque_id"] for task in tasks]
    ):
        raise RuntimeError("V2.52.80 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    aggregate = aggregate_rows(rows, wall_seconds=time.monotonic() - started)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": FREEZE_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "terminal": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "control_prediction_hash_vector_sha256": contract.payload_sha256(
                [row["prediction_sha256"] for row in rows]
            ),
            "paired_runtime_result_hash_vector_sha256": contract.payload_sha256(
                [row["paired_runtime_result_payload_sha256"] for row in rows]
            ),
            "all_control_predictions_and_paired_results_terminal_before_diagnosis": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "candidate_quality_or_prediction_change_claim": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": FORWARD_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "attempt_claim_sha256": contract.sha256(ROOT / contract.ATTEMPT_CLAIM),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "aggregate": aggregate,
            "reliability_decision": reliability_decision(aggregate),
            "authorization": {
                "forward_audit": True,
                "postforward_reliability_diagnosis": True,
                "retry_resume_skip_replacement_or_selective_rerun": False,
                "candidate_quality_or_prediction_change_claim": False,
                "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            },
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, forward)
    return validate_forward_result(forward)


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_RESULT),
                "aggregate": value["aggregate"],
                "reliability_decision": value["reliability_decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
