#!/usr/bin/env python3
"""Run the single authorized V2.52.44 fresh64 shadow forward."""

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

from deepwide_agent import v25244_header_totality_shadow_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import HardTotalWallResponsesClient  # noqa: E402
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
    validate_search_class,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


runtime = contract.runtime
TASK_ROLE = "v25244_header_totality_shadow_external_task_result"
EFFECT_ROLE = "v25244_header_totality_shadow_external_effect_snapshot"
FORWARD_ROLE = "v25244_header_totality_shadow_external_forward_result"
FREEZE_ROLE = "v25244_header_totality_shadow_external_prediction_freeze"
CLAIM_ROLE = "v25244_header_totality_shadow_external_attempt_claim"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.44 expected JSON object")
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
            "role": "v25244_header_totality_shadow_external_safe_progress",
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
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(ROOT, "rev-parse", "HEAD") != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.52.44 forward requires clean pushed HEAD")


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


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        set(start) != {
            "artifact_version", "role", "protocol_id", "status", "created_at_unix",
            "protocol_sha256", "preactivation_audit_sha256", "source_manifest",
            "task_vector_sha256", "selected", "executor_concurrency", "model_slot_cap",
            "runtime_input_contract", "protected_watchers", "findings", "authorization",
            "execution_start_payload_sha256",
        }
        or start.get("artifact_version") != 1
        or start.get("role") != "v25244_header_totality_shadow_external_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("source_manifest") != protocol["source_manifest"]
        or {
            path: contract.sha256(
                contract.ordinary(ROOT, Path(path), tracked=True)
            )
            for path in protocol["source_manifest"]
        }
        != dict(protocol["source_manifest"])
        or start.get("task_vector_sha256") != contract.TASK_VECTOR_SHA256
        or start.get("selected") != contract.TASK_COUNT
        or start.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("findings") != []
        or start.get("authorization") != {
            "single_fresh64_shadow_forward": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.52.44 execution start drifted")
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
                "role": "v25244_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def build_attempt_claim(
    protocol: Mapping[str, Any], start: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    checked_protocol = contract.validate_protocol(ROOT, protocol)
    if (
        start.get("role") != "v25244_header_totality_shadow_external_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise ValueError("V2.52.44 attempt claim start drifted")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": CLAIM_ROLE,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "protocol_id": contract.PROTOCOL_ID,
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start["execution_start_payload_sha256"],
            "source_manifest": copy.deepcopy(checked_protocol["source_manifest"]),
            "task_vector_sha256": contract.TASK_VECTOR_SHA256,
            "selected": contract.TASK_COUNT,
            "attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect": True,
            "retry_resume_skip_replacement_selective_rerun_or_second_attempt": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
        "claim_payload_sha256",
    )


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied) != {
            "artifact_version", "role", "created_at_unix", "protocol_id",
            "protocol_sha256", "execution_start_sha256",
            "execution_start_payload_sha256", "source_manifest",
            "task_vector_sha256", "selected",
            "attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect",
            "retry_resume_skip_replacement_selective_rerun_or_second_attempt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "candidate_activation_or_prediction_change",
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota",
            "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CLAIM_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name) or "")) is None
            for name in (
                "protocol_sha256", "execution_start_sha256",
                "execution_start_payload_sha256", "task_vector_sha256",
            )
        )
        or copied.get("task_vector_sha256") != contract.TASK_VECTOR_SHA256
        or copied.get("selected") != contract.TASK_COUNT
        or not isinstance(copied.get("source_manifest"), Mapping)
        or copied.get("attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "retry_resume_skip_replacement_selective_rerun_or_second_attempt",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "candidate_activation_or_prediction_change",
                "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota",
            )
        )
        or not contract.sealed(copied, "claim_payload_sha256")
    ):
        raise ValueError("V2.52.44 attempt claim drifted")
    return copied


class _EffectAccountingSearchClient(RobustLatePageBoundSearchClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actual_search_invocations = 0
        self.actual_logical_query_count = 0
        self.actual_fetch_invocations = 0
        self.actual_fetch_request_count = 0

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> Any:
        values = list(queries)
        self.actual_search_invocations += 1
        self.actual_logical_query_count += len(values)
        return super().search_many(values, **kwargs)

    def fetch_urls(self, requests: Sequence[Mapping[str, str]]) -> Any:
        values = list(requests)
        self.actual_fetch_invocations += 1
        self.actual_fetch_request_count += len(values)
        return super().fetch_urls(values)


class _EffectAccountingModelSlotLimiter(DeadlineAwareGlobalModelSlotLimiter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actual_logical_invocations = 0

    def complete(self, system: str, user: str, *, max_output_tokens: int, json_mode: bool = False) -> Any:
        self.actual_logical_invocations += 1
        return super().complete(system, user, max_output_tokens=max_output_tokens, json_mode=json_mode)


def _search(question: str, deadline: float) -> RobustLatePageBoundSearchClient:
    return _EffectAccountingSearchClient(
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


_HEALTH_NAMES = (
    "model_request_failures", "model_hard_total_wall_timeouts",
    "search_transport_failures", "search_hard_total_wall_timeouts",
    "fetch_helper_failures", "fetch_hard_deadline_failures", "fetch_deadline_rejections",
)


def _count(value: Any, name: str) -> int:
    observed = getattr(value, name, 0) if value is not None else 0
    return int(observed) if isinstance(observed, int) and not isinstance(observed, bool) and observed >= 0 else 0


def _health(value: Mapping[str, int] | None = None) -> dict[str, int]:
    source = dict(value or {})
    if set(source).difference(_HEALTH_NAMES) or any(
        isinstance(source.get(name, 0), bool)
        or not isinstance(source.get(name, 0), int)
        or source.get(name, 0) < 0
        for name in _HEALTH_NAMES
    ):
        raise ValueError("V2.52.44 health drifted")
    return {name: int(source.get(name, 0)) for name in _HEALTH_NAMES}


def _health_snapshot(model: Any, searches: Mapping[str, Any]) -> dict[str, int]:
    clients = list(searches.values())
    return _health({
        "model_request_failures": _count(model, "failures"),
        "model_hard_total_wall_timeouts": _count(model, "hard_total_wall_timeouts"),
        "search_transport_failures": sum(_count(client, "transport_failures") for client in clients),
        "search_hard_total_wall_timeouts": sum(_count(client, "hard_total_wall_timeouts") for client in clients),
        "fetch_helper_failures": sum(_count(client, "fetch_helper_failures") for client in clients),
        "fetch_hard_deadline_failures": sum(_count(client, "hard_fetch_deadline_failures") for client in clients),
        "fetch_deadline_rejections": sum(_count(client, "fetch_deadline_rejections") for client in clients),
    })


_EFFECT_COUNT_NAMES = (
    "model_logical_requests", "model_provider_requests", "model_provider_attempts",
    "model_provider_successes", "model_slot_acquisitions", "search_invocations",
    "logical_queries", "fetch_invocations", "fetch_requests", "fetch_calls",
    "fetch_helper_calls",
)


def _actual_effect_snapshot(model: Any, searches: Mapping[str, Any]) -> dict[str, Any]:
    clients = list(searches.values())
    return contract.seal(
        {
            "artifact_version": 1,
            "role": EFFECT_ROLE,
            "model_logical_requests": _count(model, "actual_logical_invocations"),
            "model_provider_requests": _count(model, "requests"),
            "model_provider_attempts": _count(model, "attempts"),
            "model_provider_successes": _count(model, "calls"),
            "model_slot_acquisitions": _count(model, "acquisitions"),
            "search_invocations": sum(_count(client, "actual_search_invocations") for client in clients),
            "logical_queries": sum(_count(client, "actual_logical_query_count") for client in clients),
            "fetch_invocations": sum(_count(client, "actual_fetch_invocations") for client in clients),
            "fetch_requests": sum(_count(client, "actual_fetch_request_count") for client in clients),
            "fetch_calls": sum(_count(client, "fetch_calls") for client in clients),
            "fetch_helper_calls": sum(_count(client, "hard_fetch_helper_calls") for client in clients),
            "effect_count_complete_even_on_outer_failure": True,
            "contains_question_package_query_url_page_prediction_answer_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        },
        "snapshot_payload_sha256",
    )


def _validate_actual_effect_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied) != {
            "artifact_version", "role", *_EFFECT_COUNT_NAMES,
            "effect_count_complete_even_on_outer_failure",
            "contains_question_package_query_url_page_prediction_answer_or_credential",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "snapshot_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != EFFECT_ROLE
        or any(isinstance(copied.get(name), bool) or not isinstance(copied.get(name), int) or copied[name] < 0 for name in _EFFECT_COUNT_NAMES)
        or copied["model_provider_successes"] > copied["model_provider_attempts"]
        or copied.get("effect_count_complete_even_on_outer_failure") is not True
        or copied.get("contains_question_package_query_url_page_prediction_answer_or_credential") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or not contract.sealed(copied, "snapshot_payload_sha256")
    ):
        raise ValueError("V2.52.44 effect snapshot drifted")
    return copied


def _fallback_table() -> str:
    return (
        "```markdown\n| " + " | ".join(contract.COLUMNS) + " |\n| "
        + " | ".join("---" for _ in contract.COLUMNS) + " |\n| "
        + " | ".join("Unknown" for _ in contract.COLUMNS) + " |\n```"
    )


def _terminal_outer_failure(
    task: Mapping[str, str], exc: BaseException, elapsed: float,
    health: Mapping[str, int] | None = None,
    effect: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    fallback = _fallback_table()
    return contract.seal(
        {
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
            "runtime_result": None,
            "runtime_result_payload_sha256": None,
            "content_free_shadow_receipt": None,
            "cost": None,
            "parent_behavior_drift": False,
            "shadow_prediction_changed": False,
            "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
            "effect_health": _health(health),
            "actual_effect_snapshot": _validate_actual_effect_snapshot(effect or _actual_effect_snapshot(None, {})),
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
            "contains_question_package_query_url_page_answer_or_credential_outside_predictions": False,
        },
        "result_payload_sha256",
    )


def _from_runtime(
    task: Mapping[str, str], value: Mapping[str, Any], elapsed: float,
    health: Mapping[str, int] | None = None,
    effect: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = runtime.validate_result(value)
    if checked["opaque_id"] != task["opaque_id"]:
        raise RuntimeError("V2.52.44 task identity drifted")
    parent = checked["parent_result"]
    predictions = copy.deepcopy(checked["predictions"])
    hashes = copy.deepcopy(checked["prediction_sha256"])
    if predictions != parent["predictions"] or hashes != parent["prediction_sha256"]:
        raise RuntimeError("V2.52.44 shadow changed parent prediction")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": TASK_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "opaque_id": checked["opaque_id"],
            "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
            "terminal": True,
            "runtime_completed": True,
            "failure_as_zero": False,
            "outer_failure_type": None,
            "predictions": predictions,
            "prediction_sha256": hashes,
            "prediction_kind": checked["prediction_kind"],
            "runtime_result": copy.deepcopy(checked),
            "runtime_result_payload_sha256": checked["result_payload_sha256"],
            "content_free_shadow_receipt": copy.deepcopy(checked["content_free_receipt"]),
            "cost": copy.deepcopy(checked["cost"]),
            "parent_behavior_drift": False,
            "shadow_prediction_changed": False,
            "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
            "effect_health": _health(health),
            "actual_effect_snapshot": _validate_actual_effect_snapshot(effect or _actual_effect_snapshot(None, {})),
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
            "contains_question_package_query_url_page_answer_or_credential_outside_predictions": False,
        },
        "result_payload_sha256",
    )


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    predictions = copied.get("predictions") or {}
    hashes = copied.get("prediction_sha256") or {}
    completed = copied.get("runtime_completed") is True
    expected = {
        "artifact_version", "role", "protocol_id", "opaque_id", "runtime_input_keys",
        "terminal", "runtime_completed", "failure_as_zero", "outer_failure_type",
        "predictions", "prediction_sha256", "prediction_kind", "runtime_result",
        "runtime_result_payload_sha256", "content_free_shadow_receipt", "cost",
        "parent_behavior_drift", "shadow_prediction_changed", "elapsed_seconds",
        "effect_health", "actual_effect_snapshot",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "retry_resume_skip_population_replacement_or_selective_rerun",
        "contains_question_package_query_url_page_answer_or_credential_outside_predictions",
        "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id") or "")) is None
        or copied.get("runtime_input_keys") != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("runtime_completed"), bool)
        or not isinstance(copied.get("failure_as_zero"), bool)
        or copied.get("failure_as_zero") is completed
        or set(predictions) != set(contract.ARMS)
        or set(hashes) != set(contract.ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] or hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in contract.ARMS)
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or copied.get("parent_behavior_drift") is not False
        or copied.get("shadow_prediction_changed") is not False
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or copied["elapsed_seconds"] < 0
        or _health(copied.get("effect_health")) != copied.get("effect_health")
        or _validate_actual_effect_snapshot(copied.get("actual_effect_snapshot") or {}) != copied.get("actual_effect_snapshot")
        or any(copied.get(name) is not False for name in (
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "retry_resume_skip_population_replacement_or_selective_rerun",
            "contains_question_package_query_url_page_answer_or_credential_outside_predictions",
        ))
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.52.44 task row drifted")
    if completed:
        runtime_result = copied.get("runtime_result")
        sparse_parent: Any = runtime_result
        if isinstance(sparse_parent, Mapping):
            for _ in range(5):
                sparse_parent = sparse_parent.get("parent_result")
                if not isinstance(sparse_parent, Mapping):
                    break
        sparse_receipt = (
            sparse_parent.get("content_free_receipt")
            if isinstance(sparse_parent, Mapping)
            else None
        )
        if (
            copied.get("outer_failure_type") is not None
            or not isinstance(runtime_result, Mapping)
            or runtime.validate_result(runtime_result) != dict(runtime_result)
            or copied.get("runtime_result_payload_sha256") != runtime_result["result_payload_sha256"]
            or copied.get("content_free_shadow_receipt") != runtime_result["content_free_receipt"]
            or copied.get("cost") != runtime_result["cost"]
            or copied["opaque_id"] != runtime_result["opaque_id"]
            or dict(predictions) != runtime_result["predictions"]
            or dict(hashes) != runtime_result["prediction_sha256"]
            or dict(predictions) != runtime_result["parent_result"]["predictions"]
            or dict(hashes) != runtime_result["parent_result"]["prediction_sha256"]
            or not isinstance(sparse_receipt, Mapping)
            or copied["actual_effect_snapshot"]["model_logical_requests"]
            != sparse_receipt.get("provider_forward_count")
            or copied["actual_effect_snapshot"]["model_provider_attempts"]
            != sparse_receipt.get("model_provider_attempt_count")
            or copied["actual_effect_snapshot"]["model_provider_requests"]
            != sparse_receipt.get("model_provider_request_count")
            or copied["actual_effect_snapshot"]["logical_queries"]
            != sparse_receipt.get("physical_query_count")
            or copied["actual_effect_snapshot"]["fetch_requests"]
            != sparse_receipt.get("physical_fetch_count")
            or copied["actual_effect_snapshot"]["fetch_calls"]
            != sparse_receipt.get("physical_fetch_count")
        ):
            raise ValueError("V2.52.44 completed runtime row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or len(copied["outer_failure_type"]) > 128
        or any(copied.get(name) is not None for name in (
            "runtime_result", "runtime_result_payload_sha256", "content_free_shadow_receipt", "cost",
        ))
        or predictions[contract.CONTROL_ARM] != predictions[contract.CANDIDATE_ARM]
    ):
        raise ValueError("V2.52.44 outer failure row drifted")
    return copied


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.52.44 runtime input must be opaque_id and question")
    started = time.monotonic()
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
        model = _EffectAccountingModelSlotLimiter(
            inner,
            slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
            output_root=ROOT / contract.OUTPUT_ROOT,
            slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        searches = {phase: _search(str(task["question"]), deadline) for phase in runtime.PHASES}
        result = runtime.run_task(
            task,
            model=model,
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            monotonic=time.monotonic,
        )
        row = _from_runtime(
            task, result, time.monotonic() - started,
            _health_snapshot(model, searches), _actual_effect_snapshot(model, searches),
        )
    except BaseException as exc:
        row = _terminal_outer_failure(
            task, exc, time.monotonic() - started,
            _health_snapshot(model, searches), _actual_effect_snapshot(model, searches),
        )
    return validate_task_row(row)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    integer_names = {
        "task_count", "terminal_tasks", "completed_runtime_tasks", "failure_as_zero_tasks",
        "model_generated_tasks", "fallback_tasks", "shadow_eligibility_tasks",
        "shadow_entry_tasks", "shadow_completed_tasks", "shadow_observer_failure_tasks",
        "safe_shadow_candidate_tasks", "parent_behavior_drift_tasks",
        "shadow_prediction_change_tasks", "content_free_shadow_receipt_valid_tasks",
        "physical_queries", "physical_fetches", "physical_model_forwards",
        "system_total_tokens", "terminal_effect_health_failures", "positive_signed_credit_count",
    }
    false_names = {
        "contains_question_package_query_url_page_answer_prediction_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "evaluator_or_quality_metric_called",
    }
    expected = {*integer_names, "batch_wall_seconds", *false_names}
    wall = copied.get("batch_wall_seconds")
    if (
        set(copied) != expected
        or any(isinstance(copied.get(name), bool) or not isinstance(copied.get(name), int) or copied[name] < 0 for name in integer_names)
        or isinstance(wall, bool) or not isinstance(wall, (int, float)) or not math.isfinite(float(wall)) or wall < 0
        or any(copied.get(name) is not False for name in false_names)
        or copied["task_count"] != contract.TASK_COUNT
        or copied["terminal_tasks"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"] + copied["failure_as_zero_tasks"] != copied["terminal_tasks"]
        or copied["model_generated_tasks"] + copied["fallback_tasks"] != copied["terminal_tasks"]
        or copied["shadow_entry_tasks"] != copied["shadow_eligibility_tasks"]
        or copied["shadow_completed_tasks"] + copied["shadow_observer_failure_tasks"] != copied["shadow_entry_tasks"]
        or copied["safe_shadow_candidate_tasks"] > copied["shadow_completed_tasks"]
        or copied["content_free_shadow_receipt_valid_tasks"] != copied["completed_runtime_tasks"]
        or copied["parent_behavior_drift_tasks"] != 0
        or copied["shadow_prediction_change_tasks"] != 0
        or copied["positive_signed_credit_count"] != 0
    ):
        raise ValueError("V2.52.44 aggregate drifted")
    return copied


def aggregate_rows(rows: Sequence[Mapping[str, Any]], *, wall_seconds: float) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    tasks = contract.task_vector(ROOT)
    if len(checked) != contract.TASK_COUNT or [row["opaque_id"] for row in checked] != [task["opaque_id"] for task in tasks]:
        raise RuntimeError("V2.52.44 fixed task vector drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    receipts = [row["content_free_shadow_receipt"] for row in completed]
    effects = [row["actual_effect_snapshot"] for row in checked]
    value = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "model_generated_tasks": sum(row["runtime_completed"] and row["prediction_kind"] == "model_generated" for row in checked),
        "fallback_tasks": sum(not row["runtime_completed"] or row["prediction_kind"] == "fallback" for row in checked),
        "shadow_eligibility_tasks": sum(receipt["shadow_eligibility_count"] for receipt in receipts),
        "shadow_entry_tasks": sum(receipt["shadow_entry_count"] for receipt in receipts),
        "shadow_completed_tasks": sum(receipt["shadow_completed_count"] for receipt in receipts),
        "shadow_observer_failure_tasks": sum(receipt["shadow_failure_present"] for receipt in receipts),
        "safe_shadow_candidate_tasks": sum(receipt["shadow_candidate_available_count"] for receipt in receipts),
        "parent_behavior_drift_tasks": sum(row["parent_behavior_drift"] for row in checked),
        "shadow_prediction_change_tasks": sum(row["shadow_prediction_changed"] for row in checked),
        "content_free_shadow_receipt_valid_tasks": len(receipts),
        "physical_queries": sum(effect["logical_queries"] for effect in effects),
        "physical_fetches": sum(effect["fetch_requests"] for effect in effects),
        "physical_model_forwards": sum(effect["model_logical_requests"] for effect in effects),
        "system_total_tokens": sum(int(row["cost"]["system_total_tokens"]) for row in completed),
        "terminal_effect_health_failures": sum(sum(row["effect_health"].values()) for row in checked),
        "positive_signed_credit_count": 0,
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_question_package_query_url_page_answer_prediction_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "evaluator_or_quality_metric_called": False,
    }
    return validate_aggregate(value)


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_aggregate(aggregate)
    gate = contract.mechanism_gate()
    checks = {
        "fixed_terminal_denominator": checked["task_count"] == checked["terminal_tasks"] == gate["fixed_task_denominator"],
        "all_runtime_tasks_completed": checked["completed_runtime_tasks"] == gate["required_completed_runtime_tasks"],
        "natural_shadow_entry_nonzero": checked["shadow_entry_tasks"] >= gate["minimum_natural_shadow_entry_tasks"],
        "safe_shadow_candidate_nonzero": checked["safe_shadow_candidate_tasks"] >= gate["minimum_safe_shadow_candidate_tasks"],
        "shadow_observer_failure_zero": checked["shadow_observer_failure_tasks"] <= gate["maximum_shadow_observer_failure_tasks"],
        "parent_behavior_drift_zero": checked["parent_behavior_drift_tasks"] <= gate["maximum_parent_behavior_drift_tasks"],
        "shadow_prediction_change_zero": checked["shadow_prediction_change_tasks"] <= gate["maximum_shadow_prediction_change_tasks"],
        "query_budget_preserved": checked["physical_queries"] <= gate["maximum_physical_queries_total"],
        "fetch_budget_preserved": checked["physical_fetches"] <= gate["maximum_physical_fetches_total"],
        "model_budget_preserved": checked["physical_model_forwards"] <= gate["maximum_model_forwards_total"],
        "all_completed_receipts_valid": checked["content_free_shadow_receipt_valid_tasks"] == checked["completed_runtime_tasks"],
        "positive_signed_credit_zero": checked["positive_signed_credit_count"] == gate["positive_signed_credit_count"],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    passed = not failed
    return {
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": passed,
        "independent_activation_and_quality_design": passed,
        "candidate_activation_or_prediction_change": False,
        "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        set(copied) != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "execution_start_sha256", "attempt_claim_sha256", "task_rows_sha256",
            "prediction_freeze_sha256",
            "aggregate", "mechanism_decision", "authorization", "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != FORWARD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or any(re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name) or "")) is None for name in (
            "execution_start_sha256", "attempt_claim_sha256", "task_rows_sha256",
            "prediction_freeze_sha256",
        ))
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("mechanism_decision") != mechanism_decision(aggregate)
        or copied.get("authorization") != {
            "forward_audit": True,
            "independent_activation_and_quality_design_only_after_pushed_forward_audit_go": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.52.44 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.52.44 shared runtime is not ready")
    future = (
        contract.ATTEMPT_CLAIM, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.52.44 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.52.44 protected watcher identity drifted")
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
        ROOT, owner=contract.LEASE_OWNER, purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {pool.submit(run_one_task, task): index for index, task in enumerate(tasks)}
            completed = 0
            for future in as_completed(futures):
                index = futures[future]
                values[index] = validate_task_row(future.result())
                completed += 1
                _atomic_progress(completed)
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT or [row["opaque_id"] for row in rows] != [task["opaque_id"] for task in tasks]:
        raise RuntimeError("V2.52.44 terminal denominator drifted")
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
            "prediction_hash_vector_sha256": contract.payload_sha256([row["prediction_sha256"] for row in rows]),
            "all_parent_predictions_terminal_before_any_activation_quality_or_evaluator_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "candidate_activation_or_prediction_change": False,
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
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "aggregate": aggregate,
            "mechanism_decision": mechanism_decision(aggregate),
            "authorization": {
                "forward_audit": True,
                "independent_activation_and_quality_design_only_after_pushed_forward_audit_go": True,
                "retry_resume_skip_replacement_or_selective_rerun": False,
                "candidate_activation_or_prediction_change": False,
                "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
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
        "aggregate": value["aggregate"],
        "mechanism_decision": value["mechanism_decision"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
