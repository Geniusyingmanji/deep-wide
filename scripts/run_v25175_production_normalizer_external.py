#!/usr/bin/env python3
"""Run the single authorized V2.51.75 normalizer-localization forward."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import math
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25171_observed_production_normalizer_runtime as runtime  # noqa: E402
from deepwide_agent import v25175_production_normalizer_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
    validate_search_class,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25175_production_normalizer_external_task_result"
EFFECT_SNAPSHOT_ROLE = "v25175_content_free_actual_effect_snapshot"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.75 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.51.75 expected JSONL objects")
    return rows


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
            handle.write(
                json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.51.75 requires clean pushed HEAD")


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
    markers = (
        str(contract.RUNNER),
        str(contract.EVALUATOR),
        "scripts/run_" + "official_eval_local.py",
    )
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
    if (
        start.get("role")
        != "v25175_production_normalizer_external_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256")
        != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization")
        != {
            "one_external_forward": True,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.51.75 execution start drifted")
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
                "role": "v25175_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


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

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        self.actual_logical_invocations += 1
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


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
        hard_fetch_deadline_seconds=contract.SEARCH[
            "hard_fetch_deadline_seconds"
        ],
        stage_callback=lambda _event: None,
    )


_HEALTH_NAMES = (
    "model_request_failures",
    "model_hard_total_wall_timeouts",
    "search_transport_failures",
    "search_hard_total_wall_timeouts",
    "fetch_helper_failures",
    "fetch_hard_deadline_failures",
    "fetch_deadline_rejections",
)


def _health(value: Mapping[str, int] | None = None) -> dict[str, int]:
    source = dict(value or {})
    if set(source).difference(_HEALTH_NAMES) or any(
        isinstance(source.get(name, 0), bool)
        or not isinstance(source.get(name, 0), int)
        or source.get(name, 0) < 0
        for name in _HEALTH_NAMES
    ):
        raise ValueError("V2.51.75 health drifted")
    return {name: int(source.get(name, 0)) for name in _HEALTH_NAMES}


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
            "model_hard_total_wall_timeouts": count(
                model, "hard_total_wall_timeouts"
            ),
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
                count(client, "hard_fetch_deadline_failures")
                for client in clients
            ),
            "fetch_deadline_rejections": sum(
                count(client, "fetch_deadline_rejections")
                for client in clients
            ),
        }
    )


_EFFECT_COUNT_NAMES = (
    "model_logical_requests",
    "model_provider_requests",
    "model_provider_attempts",
    "model_provider_successes",
    "model_slot_acquisitions",
    "search_invocations",
    "logical_queries",
    "search_provider_attempts",
    "search_provider_responses",
    "web_search_tool_calls",
    "fetch_invocations",
    "fetch_requests",
    "fetch_calls",
    "fetch_helper_calls",
)


def _actual_effect_snapshot(
    model: Any, searches: Mapping[str, Any]
) -> dict[str, Any]:
    def count(value: Any, name: str) -> int:
        observed = getattr(value, name, 0) if value is not None else 0
        return (
            int(observed)
            if isinstance(observed, int)
            and not isinstance(observed, bool)
            and observed >= 0
            else 0
        )

    clients = list(searches.values())
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": EFFECT_SNAPSHOT_ROLE,
        "model_logical_requests": count(model, "actual_logical_invocations"),
        "model_provider_requests": count(model, "requests"),
        "model_provider_attempts": count(model, "attempts"),
        "model_provider_successes": count(model, "calls"),
        "model_slot_acquisitions": count(model, "acquisitions"),
        "search_invocations": sum(
            count(client, "actual_search_invocations") for client in clients
        ),
        "logical_queries": sum(
            count(client, "actual_logical_query_count") for client in clients
        ),
        "search_provider_attempts": sum(
            count(client, "hosted_search_attempts") for client in clients
        ),
        "search_provider_responses": sum(
            count(client, "calls") for client in clients
        ),
        "web_search_tool_calls": sum(
            count(client, "tool_calls") for client in clients
        ),
        "fetch_invocations": sum(
            count(client, "actual_fetch_invocations") for client in clients
        ),
        "fetch_requests": sum(
            count(client, "actual_fetch_request_count") for client in clients
        ),
        "fetch_calls": sum(count(client, "fetch_calls") for client in clients),
        "fetch_helper_calls": sum(
            count(client, "hard_fetch_helper_calls") for client in clients
        ),
        "effect_count_complete_even_on_outer_failure": True,
        "contains_question_query_url_title_page_target_authority_column_prediction_answer_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
    }
    return contract.seal(value, "snapshot_payload_sha256")


def _validate_actual_effect_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            *_EFFECT_COUNT_NAMES,
            "effect_count_complete_even_on_outer_failure",
            "contains_question_query_url_title_page_target_authority_column_prediction_answer_or_credential",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "snapshot_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != EFFECT_SNAPSHOT_ROLE
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _EFFECT_COUNT_NAMES
        )
        or copied["model_provider_successes"] > copied["model_provider_attempts"]
        or copied["search_provider_attempts"] > 0
        and copied["search_provider_responses"]
        > copied["search_provider_attempts"]
        or copied.get("effect_count_complete_even_on_outer_failure") is not True
        or copied.get(
            "contains_question_query_url_title_page_target_authority_column_prediction_answer_or_credential"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or not contract.sealed(copied, "snapshot_payload_sha256")
    ):
        raise ValueError("V2.51.75 actual effect snapshot drifted")
    return copied


def _fallback_table() -> str:
    return (
        "```markdown\n| "
        + " | ".join(contract.COLUMNS)
        + " |\n|"
        + "|".join("---" for _ in contract.COLUMNS)
        + "|\n| "
        + " | ".join("Unknown" for _ in contract.COLUMNS)
        + " |\n```"
    )


def _terminal_outer_failure(
    task: Mapping[str, str],
    exc: BaseException,
    elapsed: float,
    health: Mapping[str, int] | None = None,
    actual_effect_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    fallback = _fallback_table()
    row: dict[str, Any] = {
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
        "prediction_sha256": {
            arm: hashlib.sha256(fallback.encode()).hexdigest()
            for arm in contract.ARMS
        },
        "prediction_kind": "fallback",
        "failure_types": None,
        "parent_result": None,
        "parent_result_payload_sha256": None,
        "cost": None,
        "content_free_receipt": None,
        "runtime_result_payload_sha256": None,
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "effect_health": _health(health),
        "actual_effect_snapshot": _validate_actual_effect_snapshot(
            actual_effect_snapshot or _actual_effect_snapshot(None, {})
        ),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
    }
    return contract.seal(row, "result_payload_sha256")


def _from_runtime(
    task: Mapping[str, str],
    value: Mapping[str, Any],
    elapsed: float,
    health: Mapping[str, int] | None = None,
    actual_effect_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = runtime.validate_result(value)
    if checked["opaque_id"] != task["opaque_id"]:
        raise RuntimeError("V2.51.75 task identity drifted")
    predictions = {
        contract.PRODUCTION_ARM: checked["production_prediction"],
        contract.DETERMINISTIC_FINAL_ARM: checked["prediction"],
    }
    row: dict[str, Any] = {
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
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in contract.ARMS
        },
        "prediction_kind": checked["prediction_kind"],
        "failure_types": copy.deepcopy(
            checked["parent_result"]["parent_result"]["parent_result"][
                "failure_types"
            ]
        ),
        "parent_result": copy.deepcopy(checked["parent_result"]),
        "parent_result_payload_sha256": checked["parent_result_payload_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "content_free_receipt": copy.deepcopy(checked["content_free_receipt"]),
        "runtime_result_payload_sha256": str(checked["result_payload_sha256"]),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "effect_health": _health(health),
        "actual_effect_snapshot": _validate_actual_effect_snapshot(
            actual_effect_snapshot or _actual_effect_snapshot(None, {})
        ),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
    }
    return contract.seal(row, "result_payload_sha256")


def _reconstruct_runtime(copied: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": runtime.ROLE,
        "policy_id": runtime.POLICY_ID,
        "opaque_id": copied["opaque_id"],
        "status": "terminal",
        "production_prediction": copied["predictions"][contract.PRODUCTION_ARM],
        "production_prediction_sha256": copied["prediction_sha256"][
            contract.PRODUCTION_ARM
        ],
        "prediction": copied["predictions"][contract.DETERMINISTIC_FINAL_ARM],
        "prediction_sha256": copied["prediction_sha256"][
            contract.DETERMINISTIC_FINAL_ARM
        ],
        "prediction_kind": copied["prediction_kind"],
        "parent_result": copy.deepcopy(copied["parent_result"]),
        "parent_result_payload_sha256": copied["parent_result_payload_sha256"],
        "cost": copy.deepcopy(copied["cost"]),
        "content_free_receipt": copy.deepcopy(copied["content_free_receipt"]),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "result_payload_sha256": copied["runtime_result_payload_sha256"],
    }


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "opaque_id",
        "runtime_input_keys",
        "terminal",
        "runtime_completed",
        "failure_as_zero",
        "outer_failure_type",
        "predictions",
        "prediction_sha256",
        "prediction_kind",
        "failure_types",
        "parent_result",
        "parent_result_payload_sha256",
        "cost",
        "content_free_receipt",
        "runtime_result_payload_sha256",
        "elapsed_seconds",
        "effect_health",
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
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("runtime_completed"), bool)
        or not isinstance(copied.get("failure_as_zero"), bool)
        or copied.get("failure_as_zero") is completed
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id") or ""))
        is None
        or set(predictions) != set(contract.ARMS)
        or set(hashes) != set(contract.ARMS)
        or any(
            not isinstance(predictions[arm], str)
            or not predictions[arm]
            or hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in contract.ARMS
        )
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or copied["elapsed_seconds"] < 0
        or _health(copied.get("effect_health")) != copied.get("effect_health")
        or _validate_actual_effect_snapshot(
            copied.get("actual_effect_snapshot") or {}
        )
        != copied.get("actual_effect_snapshot")
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_skip_population_replacement_or_selective_rerun",
                "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.75 task row drifted")
    if completed:
        parent_result = copied.get("parent_result") or {}
        vertical_parent = parent_result.get("parent_result") or {}
        sparse_parent = vertical_parent.get("parent_result") or {}
        sparse_receipt = sparse_parent.get("content_free_receipt") or {}
        if (
            copied.get("outer_failure_type") is not None
            or copied.get("failure_types") != sparse_parent.get("failure_types")
            or not isinstance(copied.get("runtime_result_payload_sha256"), str)
            or len(copied["runtime_result_payload_sha256"]) != 64
            or runtime.validate_result(_reconstruct_runtime(copied))["opaque_id"]
            != copied["opaque_id"]
            or copied["actual_effect_snapshot"]["model_logical_requests"]
            != sparse_receipt["provider_forward_count"]
            or copied["actual_effect_snapshot"]["model_provider_attempts"]
            != sparse_receipt["model_provider_attempt_count"]
            or copied["actual_effect_snapshot"]["model_provider_requests"]
            != sparse_receipt["model_provider_request_count"]
            or copied["actual_effect_snapshot"]["logical_queries"]
            != sparse_receipt["physical_query_count"]
            or copied["actual_effect_snapshot"]["fetch_requests"]
            != sparse_receipt["physical_fetch_count"]
            or copied["actual_effect_snapshot"]["fetch_calls"]
            != sparse_receipt["physical_fetch_count"]
        ):
            raise RuntimeError("V2.51.75 bound runtime row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or len(copied["outer_failure_type"]) > 128
        or any(
            copied.get(name) is not None
            for name in (
                "failure_types",
                "parent_result",
                "parent_result_payload_sha256",
                "cost",
                "content_free_receipt",
                "runtime_result_payload_sha256",
            )
        )
        or predictions[contract.PRODUCTION_ARM]
        != predictions[contract.DETERMINISTIC_FINAL_ARM]
    ):
        raise RuntimeError("V2.51.75 outer failure row drifted")
    return copied


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.51.75 runtime input must be opaque_id and question")
    started = time.monotonic()
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
        searches = {
            phase: _search(str(task["question"]), deadline)
            for phase in runtime.PHASES
        }
        result = runtime.run_task(
            task,
            model=model,
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            monotonic=time.monotonic,
        )
        row = _from_runtime(
            task,
            result,
            time.monotonic() - started,
            _health_snapshot(model, searches),
            _actual_effect_snapshot(model, searches),
        )
    except BaseException as exc:
        row = _terminal_outer_failure(
            task,
            exc,
            time.monotonic() - started,
            _health_snapshot(model, searches),
            _actual_effect_snapshot(model, searches),
        )
    return validate_task_row(row)


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in contract.task_vector()]
    ):
        raise RuntimeError("V2.51.75 fixed task vector drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    observations = [
        receipt["production_normalizer_observation"]
        for receipt in receipts
        if receipt["production_normalizer_observation"] is not None
    ]
    dispositions = {
        name: sum(observation["disposition_counts"][name] for observation in observations)
        for name in runtime.observer.DISPOSITION_NAMES
    }
    effects = [row["actual_effect_snapshot"] for row in checked]
    hard_failures = sum(sum(row["effect_health"].values()) for row in checked)
    parser_count_totals = {
        name: sum(observation[name] for observation in observations)
        for name in runtime.observer.COUNT_NAMES
    }
    value = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "production_model_generated_tasks": sum(
            row["prediction_kind"] == "model_generated" for row in completed
        ),
        "production_fallback_tasks": sum(
            row["prediction_kind"] == "fallback" for row in completed
        ),
        "observer_entry_tasks": sum(
            receipt["production_normalizer_observer_entry_count"]
            for receipt in receipts
        ),
        "observer_completed_tasks": sum(
            receipt["production_normalizer_observer_completed_count"]
            for receipt in receipts
        ),
        "observer_failure_tasks": sum(
            receipt["production_normalizer_observer_failure_present"]
            for receipt in receipts
        ),
        "disposition_counts": dispositions,
        "nonzero_disposition_buckets": sum(value > 0 for value in dispositions.values()),
        "accepted_observation_tasks": sum(
            observation["frozen_synthesis_contract_accepted"]
            for observation in observations
        ),
        "rejected_observation_tasks": sum(
            not observation["frozen_synthesis_contract_accepted"]
            for observation in observations
        ),
        "provider_output_truncated_tasks": sum(
            observation["provider_output_truncated"] for observation in observations
        ),
        "parser_count_totals": parser_count_totals,
        "disposition_accounting_error": sum(dispositions.values()) - len(observations),
        "parent_behavior_drift_tasks": 0,
        "physical_queries": sum(effect["logical_queries"] for effect in effects),
        "physical_fetches": sum(effect["fetch_requests"] for effect in effects),
        "physical_model_forwards": sum(
            effect["model_logical_requests"] for effect in effects
        ),
        "model_provider_requests": sum(
            effect["model_provider_requests"] for effect in effects
        ),
        "model_provider_attempts": sum(
            effect["model_provider_attempts"] for effect in effects
        ),
        "model_provider_successes": sum(
            effect["model_provider_successes"] for effect in effects
        ),
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"]) for row in completed
        ),
        "observed_all_task_model_logical_requests": sum(
            effect["model_logical_requests"] for effect in effects
        ),
        "observed_all_task_logical_queries": sum(
            effect["logical_queries"] for effect in effects
        ),
        "observed_all_task_fetch_requests": sum(
            effect["fetch_requests"] for effect in effects
        ),
        "content_free_receipt_valid_tasks": len(receipts),
        "outer_or_accounting_failure_tasks": sum(
            not row["runtime_completed"] for row in checked
        ),
        "terminal_transport_timeout_helper_or_model_hard_failures": hard_failures,
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the complete content-free aggregate before any gate decision."""

    copied = copy.deepcopy(dict(value))
    integer_names = {
        "task_count",
        "terminal_tasks",
        "completed_runtime_tasks",
        "failure_as_zero_tasks",
        "production_model_generated_tasks",
        "production_fallback_tasks",
        "observer_entry_tasks",
        "observer_completed_tasks",
        "observer_failure_tasks",
        "nonzero_disposition_buckets",
        "accepted_observation_tasks",
        "rejected_observation_tasks",
        "provider_output_truncated_tasks",
        "parent_behavior_drift_tasks",
        "physical_queries",
        "physical_fetches",
        "physical_model_forwards",
        "model_provider_requests",
        "model_provider_attempts",
        "model_provider_successes",
        "system_total_tokens",
        "observed_all_task_model_logical_requests",
        "observed_all_task_logical_queries",
        "observed_all_task_fetch_requests",
        "content_free_receipt_valid_tasks",
        "outer_or_accounting_failure_tasks",
        "terminal_transport_timeout_helper_or_model_hard_failures",
        "positive_signed_credit_count",
    }
    false_names = {
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
    }
    expected = {
        *integer_names,
        "disposition_counts",
        "parser_count_totals",
        "disposition_accounting_error",
        "batch_wall_seconds",
        *false_names,
    }
    dispositions = copied.get("disposition_counts")
    parser_counts = copied.get("parser_count_totals")
    wall = copied.get("batch_wall_seconds")
    if (
        set(copied) != expected
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_names
        )
        or isinstance(copied.get("disposition_accounting_error"), bool)
        or not isinstance(copied.get("disposition_accounting_error"), int)
        or not isinstance(dispositions, Mapping)
        or set(dispositions) != set(runtime.observer.DISPOSITION_NAMES)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in dispositions.values()
        )
        or not isinstance(parser_counts, Mapping)
        or set(parser_counts) != set(runtime.observer.COUNT_NAMES)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in parser_counts.values()
        )
        or isinstance(wall, bool)
        or not isinstance(wall, (int, float))
        or not math.isfinite(float(wall))
        or wall < 0
        or any(copied.get(name) is not False for name in false_names)
        or copied["task_count"] != contract.TASK_COUNT
        or copied["terminal_tasks"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"]
        + copied["failure_as_zero_tasks"]
        != copied["terminal_tasks"]
        or copied["production_model_generated_tasks"]
        + copied["production_fallback_tasks"]
        != copied["completed_runtime_tasks"]
        or copied["observer_completed_tasks"]
        + copied["observer_failure_tasks"]
        != copied["observer_entry_tasks"]
        or copied["accepted_observation_tasks"]
        + copied["rejected_observation_tasks"]
        != copied["observer_completed_tasks"]
        or sum(dispositions.values()) != copied["observer_completed_tasks"]
        or copied["disposition_accounting_error"]
        != sum(dispositions.values()) - copied["observer_completed_tasks"]
        or copied["nonzero_disposition_buckets"]
        != sum(count > 0 for count in dispositions.values())
        or copied["provider_output_truncated_tasks"]
        > copied["observer_completed_tasks"]
        or copied["content_free_receipt_valid_tasks"]
        != copied["completed_runtime_tasks"]
        or copied["outer_or_accounting_failure_tasks"]
        != copied["failure_as_zero_tasks"]
        or copied["observed_all_task_model_logical_requests"]
        != copied["physical_model_forwards"]
        or copied["observed_all_task_logical_queries"]
        != copied["physical_queries"]
        or copied["observed_all_task_fetch_requests"]
        != copied["physical_fetches"]
        or copied["model_provider_successes"]
        > copied["model_provider_requests"]
        or copied["model_provider_requests"]
        > copied["model_provider_attempts"]
        or copied["positive_signed_credit_count"] != 0
        or copied["parent_behavior_drift_tasks"] != 0
    ):
        raise RuntimeError("V2.51.75 aggregate drifted")
    return copied


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    aggregate = validate_aggregate(aggregate)
    gate = contract.mechanism_gate()
    completed = int(aggregate["completed_runtime_tasks"])
    disposition_total = sum(aggregate["disposition_counts"].values())
    localization_checks = {
        "fixed_terminal_denominator": aggregate["task_count"]
        == aggregate["terminal_tasks"]
        == gate["fixed_task_denominator"],
        "all_runtime_tasks_completed": completed == gate["completed_runtime_tasks"]
        and aggregate["failure_as_zero_tasks"] <= gate["maximum_failure_as_zero_tasks"],
        "observer_entry_completion_exact": aggregate["observer_entry_tasks"]
        == aggregate["observer_completed_tasks"]
        == gate["observer_entry_tasks"]
        == gate["observer_completed_tasks"]
        and aggregate["observer_failure_tasks"] <= gate["maximum_observer_failure_tasks"],
        "disposition_accounting_and_parent_acceptance_parity_exact": aggregate[
            "disposition_accounting_error"
        ]
        == gate["maximum_disposition_accounting_error"]
        and disposition_total == aggregate["observer_completed_tasks"]
        and aggregate["accepted_observation_tasks"]
        == aggregate["production_model_generated_tasks"]
        and aggregate["rejected_observation_tasks"]
        == aggregate["production_fallback_tasks"],
        "nonzero_disposition_localization": aggregate["nonzero_disposition_buckets"]
        >= gate["minimum_nonzero_disposition_buckets"],
        "zero_parent_behavior_drift": aggregate["parent_behavior_drift_tasks"]
        <= gate["maximum_parent_behavior_drift_tasks"],
        "zero_outer_or_accounting_failure": aggregate[
            "outer_or_accounting_failure_tasks"
        ]
        <= gate["maximum_outer_or_accounting_failure_tasks"],
        "zero_terminal_effect_hard_failure": aggregate[
            "terminal_transport_timeout_helper_or_model_hard_failures"
        ]
        <= gate["maximum_terminal_transport_timeout_helper_or_model_hard_failures"],
        "exact_physical_query_budget": aggregate["physical_queries"]
        == gate["exact_physical_queries_per_completed_task"] * completed,
        "physical_fetch_cap_preserved": aggregate["physical_fetches"]
        <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "sparse_provider_forward_cap": aggregate["physical_model_forwards"]
        <= gate["maximum_sparse_model_forwards_total"],
        "all_content_free_receipts_valid": aggregate[
            "content_free_receipt_valid_tasks"
        ]
        == completed,
        "positive_signed_credit_remains_zero": aggregate[
            "positive_signed_credit_count"
        ]
        == 0,
    }
    reliability_checks = {
        "minimum_model_generated_production": aggregate[
            "production_model_generated_tasks"
        ]
        >= gate["minimum_production_model_generated_tasks_for_reliability"],
        "maximum_production_fallback": aggregate["production_fallback_tasks"]
        <= gate["maximum_production_fallback_tasks_for_reliability"],
    }
    failed_localization = sorted(
        name for name, passed in localization_checks.items() if not passed
    )
    failed_reliability = sorted(
        name for name, passed in reliability_checks.items() if not passed
    )
    localized = not failed_localization
    repair_needed = aggregate["production_fallback_tasks"] > 0
    return {
        "localization_checks": localization_checks,
        "production_reliability_checks": reliability_checks,
        "failed_localization_checks": failed_localization,
        "failed_production_reliability_checks": failed_reliability,
        "normalizer_localization_gate_passed": localized,
        "production_reliability_gate_passed": not failed_reliability,
        "normalizer_repair_design": localized and repair_needed,
        "binding_successor_design": False,
        "vertical_binding_policy_change": False,
        "postfreeze_external_evaluator_implementation_and_protocol": False,
        "deepwidebench_dev64_exact220_or_sota": False,
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
            "execution_start_payload_sha256",
            "task_rows_sha256",
            "prediction_freeze_sha256",
            "aggregate",
            "mechanism_decision",
            "authorization",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25175_production_normalizer_external_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name) or "")) is None
            for name in (
                "execution_start_sha256",
                "execution_start_payload_sha256",
                "task_rows_sha256",
                "prediction_freeze_sha256",
            )
        )
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("mechanism_decision") != mechanism_decision(aggregate)
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "normalizer_repair_design_only_after_pushed_forward_audit_go": True,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "postfreeze_external_evaluator_implementation_and_protocol": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.75 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.51.75 shared runtime is not ready")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    future = (
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR,
        contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.51.75 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.51.75 protected watcher identity drifted")
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
        raise RuntimeError("V2.51.75 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25175_production_normalizer_external_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "production_prediction_hash_vector_sha256": contract.payload_sha256(
                [row["prediction_sha256"][contract.PRODUCTION_ARM] for row in rows]
            ),
            "normalizer_observed_final_prediction_hash_vector_sha256": contract.payload_sha256(
                [row["prediction_sha256"][contract.DETERMINISTIC_FINAL_ARM] for row in rows]
            ),
            "all_predictions_terminal_before_hidden_mapping_gold_evaluator_or_quality_decision": True,
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
            "role": "v25175_production_normalizer_external_forward_result",
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
                "normalizer_repair_design_only_after_pushed_forward_audit_go": True,
                "binding_successor_design": False,
                "vertical_binding_policy_change": False,
                "postfreeze_external_evaluator_implementation_and_protocol": False,
                "deepwidebench_dev64_exact220_or_sota": False,
                "retry_resume_skip_population_replacement_or_selective_rerun": False,
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
