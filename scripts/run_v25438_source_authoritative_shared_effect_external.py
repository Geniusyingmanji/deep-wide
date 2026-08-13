#!/usr/bin/env python3
"""Run the single authorized V2.54.38 shared-effect external gate."""

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

from deepwide_agent import v24982_paired_production_runtime as counters  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25370_shared_synthesis_changed_safe_runtime as base_runtime  # noqa: E402
from deepwide_agent import v25389_hybrid_record_fallback_runtime as hybrid_runtime  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership_runtime  # noqa: E402
from deepwide_agent import v25401_grounded_record_membership_runtime as grounded_runtime  # noqa: E402
from deepwide_agent import v25434_source_authoritative_shared_runtime as runtime  # noqa: E402
from deepwide_agent import v25438_source_authoritative_shared_effect_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import HardTotalWallResponsesClient  # noqa: E402
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
    validate_search_class,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25438_source_authoritative_shared_effect_frozen_task_result"
FORWARD_ROLE = "v25438_source_authoritative_shared_effect_external_forward_result"
FREEZE_ROLE = "v25438_source_authoritative_shared_effect_prediction_freeze"
ARMS = runtime.ARMS


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.38 expected JSON object")
    return value


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
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


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.54.38 requires clean pushed HEAD")


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
            len(parts) == 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    expected = {
        "one_external_forward": True,
        "postfreeze_quality": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
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
        start.get("role") != "v25438_source_authoritative_shared_effect_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("group_vector_sha256")
        != protocol["population"]["group_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization") != expected
        or not contract.sealed(start, "execution_start_payload_sha256")
        or current != target
        or len(parents) != 2
        or parents[1] != start.get("git_head")
        or changed != [str(contract.EXECUTION_START)]
    ):
        raise RuntimeError("V2.54.38 execution start drifted")
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
                "role": "v25438_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _search(question: str, deadline: float) -> RobustLatePageBoundSearchClient:
    return RobustLatePageBoundSearchClient(
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


def _fallback_prediction(question: str) -> str:
    identities: list[str] = []
    allowed = set(contract.population.identity_vector())
    for value in re.findall(r"\bRFC 9[0-9]{3}\b", str(question)):
        if value not in allowed:
            continue
        if value not in identities:
            identities.append(value)
    if len(identities) != contract.population.ROWS_PER_TASK:
        identities = ["Unknown"]
    body = "\n".join(
        "| "
        + " | ".join([identity, *("Unknown" for _ in contract.COLUMNS[1:])])
        + " |"
        for identity in identities
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


def _empty_effect_snapshot() -> dict[str, int]:
    return {
        "query_admitted_count": 0,
        "fetch_admitted_count": 0,
        "model_admitted_count": 0,
        "query_rejected_count": 0,
        "fetch_rejected_count": 0,
        "model_rejected_count": 0,
    }


def _effect_snapshot(budget: cap.PhysicalEffectBudget | None) -> dict[str, int]:
    if budget is None:
        return _empty_effect_snapshot()
    receipt = cap.validate_budget_receipt(budget.receipt())
    return {name: int(receipt[name]) for name in _empty_effect_snapshot()}


def _health(value: Mapping[str, int] | None = None) -> dict[str, int]:
    names = (
        "model_request_failures",
        "model_hard_total_wall_timeouts",
        "search_request_failures",
        "search_transport_failures",
        "search_hard_total_wall_timeouts",
        "fetch_helper_failures",
        "fetch_hard_deadline_failures",
        "fetch_deadline_rejections",
    )
    source = dict(value or {})
    output = {name: int(source.get(name, 0)) for name in names}
    if any(amount < 0 for amount in output.values()):
        raise ValueError("V2.54.38 health snapshot drifted")
    return output


def _health_snapshot(model: Any, searches: Mapping[str, Any]) -> dict[str, int]:
    def count(value: Any, name: str) -> int:
        observed = getattr(value, name, 0) if value is not None else 0
        return (
            int(observed)
            if isinstance(observed, int) and not isinstance(observed, bool)
            else 0
        )

    clients = list(searches.values())
    return _health(
        {
            "model_request_failures": count(model, "failures"),
            "model_hard_total_wall_timeouts": count(model, "hard_total_wall_timeouts"),
            "search_request_failures": sum(count(client, "failures") for client in clients),
            "search_transport_failures": sum(
                count(client, "transport_failures") for client in clients
            ),
            "search_hard_total_wall_timeouts": sum(
                count(client, "hard_total_wall_timeouts") for client in clients
            ),
            "fetch_helper_failures": sum(
                count(client, "fetch_helper_failures") for client in clients
            ),
            "fetch_hard_deadline_failures": sum(
                count(client, "hard_fetch_deadline_failures") for client in clients
            ),
            "fetch_deadline_rejections": sum(
                count(client, "fetch_deadline_rejections") for client in clients
            ),
        }
    )


def _task_metadata() -> dict[str, int]:
    output = {
        group["task"]["opaque_id"]: int(group["task_index"])
        for group in contract.population.group_vector()
    }
    if len(output) != contract.TASK_COUNT:
        raise RuntimeError("V2.54.38 task metadata drifted")
    return output


def _metadata(task: Mapping[str, str]) -> int:
    value = _task_metadata().get(str(task.get("opaque_id")))
    if value is None or dict(task) != contract.task_vector()[value]:
        raise ValueError("V2.54.38 task is outside frozen population")
    return value


def _validate_cost(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.54.38 cost is absent")
    copied = copy.deepcopy(dict(value))
    if (
        set(copied) != {"model", "search", "system_total_tokens"}
        or set(copied.get("model") or {}) != set(counters._MODEL_COUNTERS)
        or set(copied.get("search") or {}) != set(contract.PHASES)
        or any(
            set(copied["search"][phase]) != set(counters._SEARCH_COUNTERS)
            for phase in contract.PHASES
        )
        or any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for amount in copied["model"].values()
        )
        or any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for phase in contract.PHASES
            for amount in copied["search"][phase].values()
        )
        or isinstance(copied.get("system_total_tokens"), bool)
        or not isinstance(copied.get("system_total_tokens"), int)
        or copied["system_total_tokens"] < 0
        or copied["system_total_tokens"]
        != copied["model"]["total_tokens"]
        + sum(copied["search"][phase]["total_tokens"] for phase in contract.PHASES)
    ):
        raise ValueError("V2.54.38 cost drifted")
    return copied


def _decode_completed(
    result: Mapping[str, Any], stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = runtime.validate_result(result)
    checked_stage = runtime.validate_stage_receipt(stage)
    grounded_result = grounded_runtime.validate_result(
        checked["private_parent_result"]
    )
    membership_result = membership_runtime.validate_result(
        grounded_result["private_parent_result"]
    )
    hybrid_result = hybrid_runtime.validate_result(
        membership_result["private_parent_result"]
    )
    shared_result = base_runtime.validate_result(
        hybrid_result["private_parent_result"]
    )
    grounded_stage = grounded_runtime.validate_stage_receipt(
        checked_stage["parent_stage_receipt"]
    )
    membership_stage = membership_runtime.validate_stage_receipt(
        grounded_stage["parent_stage_receipt"]
    )
    hybrid_stage = hybrid_runtime.validate_stage_receipt(
        membership_stage["parent_stage_receipt"]
    )
    parent_receipt = base_runtime.validate_receipt(
        hybrid_stage["parent_content_free_receipt"]
    )
    membership_receipt = membership_runtime.validate_receipt(
        membership_stage["visible_membership_synthesis_receipt"]
    )
    hybrid_receipt = hybrid_runtime.validate_receipt(
        hybrid_stage["hybrid_record_fallback_receipt"]
    )
    grounded_receipt = grounded_runtime.validate_receipt(
        grounded_stage["grounded_record_membership_receipt"]
    )
    source_receipt = runtime.validate_receipt(
        checked["source_authoritative_receipt"]
    )
    budget = cap.validate_budget_receipt(
        checked_stage["outer_physical_budget_receipt"]
    )
    predictions = copy.deepcopy(checked["predictions"])
    if (
        grounded_result["result_payload_sha256"]
        != checked["private_parent_result_payload_sha256"]
        or membership_result["result_payload_sha256"]
        != grounded_result["private_parent_result_payload_sha256"]
        or hybrid_result["result_payload_sha256"]
        != membership_result["private_parent_result_payload_sha256"]
        or shared_result["result_payload_sha256"]
        != hybrid_result["private_parent_result_payload_sha256"]
        or predictions[runtime.BASE_ARM]
        != shared_result["predictions"][base_runtime.CONTROL_ARM]
        or predictions[runtime.CANDIDATE_ARM] != checked["prediction"]
        or checked["prediction_changed"]
        is not (predictions[runtime.BASE_ARM] != predictions[runtime.CANDIDATE_ARM])
        or source_receipt["candidate_prediction_changed"]
        is not checked["prediction_changed"]
    ):
        raise ValueError("V2.54.38 shared parent chain drifted")
    return {
        "result": checked,
        "stage": checked_stage,
        "grounded_result": grounded_result,
        "membership_result": membership_result,
        "hybrid_result": hybrid_result,
        "shared_result": shared_result,
        "parent_receipt": parent_receipt,
        "membership_receipt": membership_receipt,
        "hybrid_receipt": hybrid_receipt,
        "grounded_receipt": grounded_receipt,
        "source_receipt": source_receipt,
        "budget": budget,
        "predictions": predictions,
    }


def _terminal_outer_failure(
    task: Mapping[str, str],
    exc: BaseException,
    elapsed: float,
    *,
    budget: cap.PhysicalEffectBudget | None,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    task_index = _metadata(task)
    prediction = _fallback_prediction(str(task["question"]))
    predictions = {arm: prediction for arm in ARMS}
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": str(task["opaque_id"]),
        "task_index": task_index,
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": False,
        "failure_as_zero": True,
        "outer_failure_type": (type(exc).__name__ or "Exception")[:128],
        "runtime_result": None,
        "runtime_result_payload_sha256": None,
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(prediction.encode()).hexdigest() for arm in ARMS
        },
        "prediction_kind": "fallback",
        "candidate_prediction_changed": False,
        "accepted_authority_page_count": 0,
        "available_candidate_count": 0,
        "selected_candidate_count": 0,
        "applied_coordinate_count": 0,
        "synthesis_capture_valid": False,
        "source_authoritative_application_valid": False,
        "content_free_stage_receipt": None,
        "actual_effect_snapshot": _effect_snapshot(budget),
        "cost": None,
        "hard_failure_health": _health(health),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        "query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions": False,
    }
    return validate_task_row(contract.seal(row, "result_payload_sha256"))


def _from_runtime(
    task: Mapping[str, str],
    value: Mapping[str, Any],
    stage: Mapping[str, Any],
    *,
    elapsed: float,
    budget: cap.PhysicalEffectBudget,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    task_index = _metadata(task)
    decoded = _decode_completed(value, stage)
    checked = decoded["result"]
    source = decoded["source_receipt"]
    observed_budget = cap.validate_budget_receipt(budget.receipt())
    if (
        checked["opaque_id"] != task["opaque_id"]
        or decoded["budget"] != observed_budget
        or decoded["parent_receipt"]["physical_query_count"]
        != observed_budget["query_admitted_count"]
        or decoded["parent_receipt"]["physical_fetch_count"]
        != observed_budget["fetch_admitted_count"]
        or decoded["parent_receipt"]["physical_model_forward_count"]
        != observed_budget["model_admitted_count"]
    ):
        raise RuntimeError("V2.54.38 runtime task binding drifted")
    predictions = copy.deepcopy(decoded["predictions"])
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": checked["opaque_id"],
        "task_index": task_index,
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "runtime_result": copy.deepcopy(checked),
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in ARMS
        },
        "prediction_kind": checked["prediction_kind"],
        "candidate_prediction_changed": bool(checked["prediction_changed"]),
        "accepted_authority_page_count": int(
            source["accepted_authority_page_count"]
        ),
        "available_candidate_count": int(source["available_candidate_count"]),
        "selected_candidate_count": int(source["selected_candidate_count"]),
        "applied_coordinate_count": int(source["applied_coordinate_count"]),
        "synthesis_capture_valid": bool(source["synthesis_capture_valid"]),
        "source_authoritative_application_valid": bool(
            source["source_authoritative_application_valid"]
        ),
        "content_free_stage_receipt": copy.deepcopy(decoded["stage"]),
        "actual_effect_snapshot": _effect_snapshot(budget),
        "cost": copy.deepcopy(checked["cost"]),
        "hard_failure_health": _health(health),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        "query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions": False,
    }
    return validate_task_row(contract.seal(row, "result_payload_sha256"))


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "opaque_id",
        "task_index",
        "runtime_input_keys",
        "terminal",
        "runtime_completed",
        "failure_as_zero",
        "outer_failure_type",
        "runtime_result",
        "runtime_result_payload_sha256",
        "predictions",
        "prediction_sha256",
        "prediction_kind",
        "candidate_prediction_changed",
        "accepted_authority_page_count",
        "available_candidate_count",
        "selected_candidate_count",
        "applied_coordinate_count",
        "synthesis_capture_valid",
        "source_authoritative_application_valid",
        "content_free_stage_receipt",
        "actual_effect_snapshot",
        "cost",
        "hard_failure_health",
        "elapsed_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "positive_signed_credit_count",
        "retry_resume_replay_backfill_replacement_or_selective_rerun",
        "query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions",
        "result_payload_sha256",
    }
    metadata = _task_metadata().get(str(copied.get("opaque_id")))
    effects = copied.get("actual_effect_snapshot") or {}
    health = copied.get("hard_failure_health") or {}
    predictions = copied.get("predictions") or {}
    hashes = copied.get("prediction_sha256") or {}
    completed = copied.get("runtime_completed") is True
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or metadata is None
        or copied.get("task_index") != metadata
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("runtime_completed"), bool)
        or copied.get("failure_as_zero") is completed
        or set(predictions) != set(ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in ARMS)
        or set(hashes) != set(ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or copied.get("candidate_prediction_changed")
        is not (predictions[runtime.BASE_ARM] != predictions[runtime.CANDIDATE_ARM])
        or not isinstance(copied.get("synthesis_capture_valid"), bool)
        or not isinstance(
            copied.get("source_authoritative_application_valid"), bool
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in (
                "accepted_authority_page_count",
                "available_candidate_count",
                "selected_candidate_count",
                "applied_coordinate_count",
            )
        )
        or copied["selected_candidate_count"] > copied["available_candidate_count"]
        or copied["applied_coordinate_count"] != copied["selected_candidate_count"]
        or copied["candidate_prediction_changed"]
        is not (copied["applied_coordinate_count"] > 0)
        or set(effects) != set(_empty_effect_snapshot())
        or any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for amount in effects.values()
        )
        or set(health) != set(_health())
        or any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for amount in health.values()
        )
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or copied["elapsed_seconds"] < 0
        or copied.get("positive_signed_credit_count") != 0
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_replay_backfill_replacement_or_selective_rerun",
                "query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.54.38 task row drifted")
    if completed:
        runtime_result = copied.get("runtime_result")
        stage = copied.get("content_free_stage_receipt")
        if not isinstance(runtime_result, Mapping) or not isinstance(stage, Mapping):
            raise ValueError("V2.54.38 completed runtime surface is absent")
        decoded = _decode_completed(runtime_result, stage)
        checked = decoded["result"]
        source = decoded["source_receipt"]
        budget = decoded["budget"]
        cost = _validate_cost(copied.get("cost"))
        if (
            copied.get("runtime_result_payload_sha256") != checked["result_payload_sha256"]
            or copied["predictions"] != decoded["predictions"]
            or copied["prediction_kind"] != checked["prediction_kind"]
            or copied["candidate_prediction_changed"]
            != checked["prediction_changed"]
            or copied["accepted_authority_page_count"]
            != source["accepted_authority_page_count"]
            or copied["available_candidate_count"]
            != source["available_candidate_count"]
            or copied["selected_candidate_count"]
            != source["selected_candidate_count"]
            or copied["applied_coordinate_count"]
            != source["applied_coordinate_count"]
            or copied["synthesis_capture_valid"]
            is not source["synthesis_capture_valid"]
            or copied["source_authoritative_application_valid"]
            is not source["source_authoritative_application_valid"]
            or copied["cost"] != checked["cost"]
            or checked["opaque_id"] != copied["opaque_id"]
            or copied.get("outer_failure_type") is not None
            or any(
                effects[f"{kind}_{suffix}_count"] != budget[f"{kind}_{suffix}_count"]
                for kind in ("query", "fetch", "model")
                for suffix in ("admitted", "rejected")
            )
            or decoded["parent_receipt"]["physical_query_count"]
            != effects["query_admitted_count"]
            or decoded["parent_receipt"]["physical_fetch_count"]
            != effects["fetch_admitted_count"]
            or decoded["parent_receipt"]["physical_model_forward_count"]
            != effects["model_admitted_count"]
            or cost["system_total_tokens"] != decoded["parent_receipt"]["system_total_tokens"]
        ):
            raise ValueError("V2.54.38 completed task row drifted")
    else:
        if (
            not isinstance(copied.get("outer_failure_type"), str)
            or not copied["outer_failure_type"]
            or copied.get("runtime_result") is not None
            or copied.get("runtime_result_payload_sha256") is not None
            or copied.get("content_free_stage_receipt") is not None
            or copied.get("cost") is not None
            or copied.get("prediction_kind") != "fallback"
            or len(set(predictions.values())) != 1
            or any(
                copied[name] != 0
                for name in (
                    "accepted_authority_page_count",
                    "available_candidate_count",
                    "selected_candidate_count",
                    "applied_coordinate_count",
                )
            )
            or copied["synthesis_capture_valid"] is not False
            or copied["source_authoritative_application_valid"] is not False
        ):
            raise ValueError("V2.54.38 failure task row drifted")
    return copied


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.54.38 runtime input must be opaque_id and question")
    _metadata(task)
    started = time.monotonic()
    outer_model: Any = None
    searches: dict[str, Any] = {}
    budget: cap.PhysicalEffectBudget | None = None
    try:
        limits = ScoreFirstLimits(**contract.LIMITS)
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
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
            output_root=ROOT / contract.OUTPUT_ROOT,
            slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        budget = cap.PhysicalEffectBudget()
        searches = {
            phase: cap.HardCappedSearchClient(
                _search(str(task["question"]), deadline), budget, phase=phase
            )
            for phase in runtime.PHASES
        }
        outer_model = cap.HardCappedModelLimiter(bounded, budget)
        result, stage = runtime.run_task(
            task,
            model=outer_model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=time.monotonic,
        )
        row = _from_runtime(
            task,
            result,
            stage,
            elapsed=time.monotonic() - started,
            budget=budget,
            health=_health_snapshot(outer_model, searches),
        )
    except BaseException as exc:
        row = _terminal_outer_failure(
            task,
            exc,
            time.monotonic() - started,
            budget=budget,
            health=_health_snapshot(outer_model, searches),
        )
    return validate_task_row(row)


AGGREGATE_INTEGER_FIELDS = (
    "task_count",
    "terminal_tasks",
    "completed_runtime_tasks",
    "failure_as_zero_tasks",
    "outer_failure_tasks",
    "naked_outer_failure_tasks",
    "parent_role_tasks",
    "first_wave_completed_tasks",
    "second_wave_completed_tasks",
    "grounded_plan_provider_success_tasks",
    "base_synthesis_success_tasks",
    "exact_canonical_base_table_tasks",
    "synthesis_capture_valid_tasks",
    "accepted_authority_page_tasks",
    "accepted_authority_page_count_total",
    "available_candidate_tasks",
    "available_candidate_count_total",
    "selected_candidate_tasks",
    "selected_candidate_count_total",
    "applied_candidate_tasks",
    "applied_coordinate_count_total",
    "prediction_changed_tasks",
    "application_failure_tasks",
    "budget_rejection_tasks",
    "all_physical_queries",
    "all_physical_fetches",
    "all_physical_model_forwards",
    "completed_physical_queries",
    "completed_physical_fetches",
    "completed_physical_model_forwards",
    "per_task_hard_cap_preserved_tasks",
    "fallback_tasks",
    "positive_signed_credit_count",
    "system_total_tokens",
)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        *AGGREGATE_INTEGER_FIELDS,
        "batch_wall_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate",
    }
    if (
        set(copied) != expected
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in AGGREGATE_INTEGER_FIELDS
        )
        or copied["task_count"] != contract.TASK_COUNT
        or copied["terminal_tasks"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"] + copied["failure_as_zero_tasks"]
        != contract.TASK_COUNT
        or copied["outer_failure_tasks"] != copied["failure_as_zero_tasks"]
        or copied["selected_candidate_count_total"]
        > copied["available_candidate_count_total"]
        or copied["applied_coordinate_count_total"]
        != copied["selected_candidate_count_total"]
        or copied["prediction_changed_tasks"] != copied["applied_candidate_tasks"]
        or copied["positive_signed_credit_count"] != 0
        or isinstance(copied.get("batch_wall_seconds"), bool)
        or not isinstance(copied.get("batch_wall_seconds"), (int, float))
        or not math.isfinite(float(copied["batch_wall_seconds"]))
        or copied["batch_wall_seconds"] < 0
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate",
            )
        )
    ):
        raise ValueError("V2.54.38 aggregate drifted")
    return copied


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in contract.task_vector()]
    ):
        raise RuntimeError("V2.54.38 fixed population order drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    decoded = [
        _decode_completed(row["runtime_result"], row["content_free_stage_receipt"])
        for row in completed
    ]
    parents = [item["parent_receipt"] for item in decoded]
    sources = [item["source_receipt"] for item in decoded]
    value: dict[str, Any] = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "outer_failure_tasks": sum(not row["runtime_completed"] for row in checked),
        "naked_outer_failure_tasks": sum(
            not row["runtime_completed"]
            and row["content_free_stage_receipt"] is None
            for row in checked
        ),
        "parent_role_tasks": sum(
            item["result"]["role"] == runtime.ROLE for item in decoded
        ),
        "first_wave_completed_tasks": sum(
            parent["first_wave_completed"] for parent in parents
        ),
        "second_wave_completed_tasks": sum(
            parent["second_wave_completed"] for parent in parents
        ),
        "grounded_plan_provider_success_tasks": sum(
            parent["grounded_plan_model_call_success"] for parent in parents
        ),
        "base_synthesis_success_tasks": sum(
            parent["base_synthesis_model_success"] for parent in parents
        ),
        "exact_canonical_base_table_tasks": sum(
            parent["base_table_exact_canonical"] for parent in parents
        ),
        "synthesis_capture_valid_tasks": sum(
            receipt["synthesis_capture_valid"] for receipt in sources
        ),
        "accepted_authority_page_tasks": sum(
            receipt["accepted_authority_page_count"] > 0 for receipt in sources
        ),
        "accepted_authority_page_count_total": sum(
            receipt["accepted_authority_page_count"] for receipt in sources
        ),
        "available_candidate_tasks": sum(
            receipt["available_candidate_count"] > 0 for receipt in sources
        ),
        "available_candidate_count_total": sum(
            receipt["available_candidate_count"] for receipt in sources
        ),
        "selected_candidate_tasks": sum(
            receipt["selected_candidate_count"] > 0 for receipt in sources
        ),
        "selected_candidate_count_total": sum(
            receipt["selected_candidate_count"] for receipt in sources
        ),
        "applied_candidate_tasks": sum(
            receipt["applied_coordinate_count"] > 0 for receipt in sources
        ),
        "applied_coordinate_count_total": sum(
            receipt["applied_coordinate_count"] for receipt in sources
        ),
        "prediction_changed_tasks": sum(
            receipt["candidate_prediction_changed"] for receipt in sources
        ),
        "application_failure_tasks": sum(
            not receipt["source_authoritative_application_valid"]
            and receipt["application_failure_type"] is not None
            for receipt in sources
        ),
        "budget_rejection_tasks": sum(
            any(
                row["actual_effect_snapshot"][f"{kind}_rejected_count"] > 0
                for kind in ("query", "fetch", "model")
            )
            for row in checked
        ),
        "all_physical_queries": sum(
            row["actual_effect_snapshot"]["query_admitted_count"] for row in checked
        ),
        "all_physical_fetches": sum(
            row["actual_effect_snapshot"]["fetch_admitted_count"] for row in checked
        ),
        "all_physical_model_forwards": sum(
            row["actual_effect_snapshot"]["model_admitted_count"] for row in checked
        ),
        "completed_physical_queries": sum(
            row["actual_effect_snapshot"]["query_admitted_count"] for row in completed
        ),
        "completed_physical_fetches": sum(
            row["actual_effect_snapshot"]["fetch_admitted_count"] for row in completed
        ),
        "completed_physical_model_forwards": sum(
            row["actual_effect_snapshot"]["model_admitted_count"] for row in completed
        ),
        "per_task_hard_cap_preserved_tasks": sum(
            row["actual_effect_snapshot"]["query_admitted_count"] <= 4
            and row["actual_effect_snapshot"]["fetch_admitted_count"] <= 14
            and row["actual_effect_snapshot"]["model_admitted_count"] <= 3
            for row in checked
        ),
        "fallback_tasks": sum(row["prediction_kind"] == "fallback" for row in checked),
        "positive_signed_credit_count": 0,
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"])
            for row in completed
            if row["cost"] is not None
        ),
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate": False,
    }
    return validate_aggregate(value)


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_aggregate(aggregate)
    gate = contract.mechanism_gate()
    completed = value["completed_runtime_tasks"]
    checks = {
        "fixed_task_denominator": value["task_count"] == gate["fixed_task_denominator"],
        "all_tasks_terminal": value["terminal_tasks"] == gate["required_terminal_tasks"],
        "all_runtime_tasks_completed": completed == gate["required_completed_runtime_tasks"],
        "zero_outer_failure": value["outer_failure_tasks"] <= gate["maximum_outer_failure_tasks"],
        "zero_naked_outer_failure": value["naked_outer_failure_tasks"]
        <= gate["maximum_naked_outer_failure_tasks"],
        "parent_role_exact": value["parent_role_tasks"] == contract.TASK_COUNT,
        "all_synthesis_captures_valid": value["synthesis_capture_valid_tasks"]
        == gate["required_synthesis_capture_valid_tasks"],
        "minimum_accepted_authority_page_tasks": value[
            "accepted_authority_page_tasks"
        ]
        >= gate["minimum_accepted_authority_page_tasks"],
        "minimum_available_candidate_tasks": value["available_candidate_tasks"]
        >= gate["minimum_available_candidate_tasks"],
        "minimum_applied_candidate_tasks": value["applied_candidate_tasks"]
        >= gate["minimum_applied_candidate_tasks"],
        "minimum_prediction_changed_tasks": value["prediction_changed_tasks"]
        >= gate["minimum_prediction_changed_tasks"],
        "zero_application_failure": value["application_failure_tasks"]
        <= gate["maximum_application_failure_tasks"],
        "zero_budget_rejection": value["budget_rejection_tasks"]
        <= gate["maximum_budget_rejection_tasks"],
        "exact_completed_query_budget": value["completed_physical_queries"]
        == gate["exact_physical_queries_per_completed_task"] * completed,
        "completed_fetch_cap_preserved": value["completed_physical_fetches"]
        <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "exact_completed_model_budget": value["completed_physical_model_forwards"]
        == gate["exact_normal_path_model_forwards_per_completed_task"] * completed,
        "all_rows_per_task_hard_caps": value["per_task_hard_cap_preserved_tasks"]
        == contract.TASK_COUNT,
        "candidate_coordinate_accounting_exact": value[
            "selected_candidate_count_total"
        ]
        == value["applied_coordinate_count_total"],
        "positive_signed_credit_zero": value["positive_signed_credit_count"]
        == gate["positive_signed_credit_count"],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": not failed,
        "postfreeze_quality_protocol_authorized": not failed,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        copied.get("role") != FORWARD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("mechanism_decision") != mechanism_decision(aggregate)
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "postfreeze_quality_protocol": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.54.38 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.54.38 shared runtime is not ready")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    future = (
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.POSTFREEZE_QUALITY_PROTOCOL,
        contract.QUALITY_RESULT,
        contract.QUALITY_AUDIT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.54.38 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.54.38 protected watcher identity drifted")
    validate_search_class()
    tasks = contract.task_vector()
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
            for future in as_completed(futures):
                values[futures[future]] = future.result()
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.54.38 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": FREEZE_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_vector_sha256": {
                arm: contract.payload_sha256([row["predictions"][arm] for row in rows])
                for arm in ARMS
            },
            "prediction_hash_vector_sha256": {
                arm: contract.payload_sha256(
                    [row["prediction_sha256"][arm] for row in rows]
                )
                for arm in ARMS
            },
            "both_prediction_texts_persisted": True,
            "all_predictions_terminal_before_truth_evaluator_or_quality_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    aggregate = aggregate_rows(rows, wall_seconds=time.monotonic() - started)
    decision = mechanism_decision(aggregate)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": FORWARD_ROLE,
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
                "postfreeze_quality_protocol": False,
                "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
                "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
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
                "mechanism_decision": value["mechanism_decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
