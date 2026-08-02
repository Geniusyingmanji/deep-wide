#!/usr/bin/env python3
"""Run one exact, label-blind V2.42.75 consumed-dev64 candidate rollout."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    validate_receipt,
)
from deepwide_agent.v24267_total_fallback import (  # noqa: E402
    build_total_fallback_result,
)
from deepwide_agent.v24273_two_wave_task_runtime import (  # noqa: E402
    validate_v24273_result,
)
from deepwide_agent.v24275_forward_contract import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_PROTOCOL,
    FORWARD_RESULT,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    OUTPUT_ROOT,
    PREAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUNNER_MARKER,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SEARCH,
    SELECTED_COUNT,
    TASK_ROOT,
    TWO_WAVE_POLICY,
    payload_sha256,
    read_object,
    selected_tasks,
    sha256,
    validate_protocol,
)
from deepwide_agent.v24275_hard_deadline_fetch import (  # noqa: E402
    validate_transport_health,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)
RECEIPT_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
RUNTIME_ROW_KEYS = frozenset(
    {
        "opaque_id",
        "status",
        "prediction",
        "prediction_sha256",
        "completion_kind",
        "elapsed_seconds",
        "cost",
        "telemetry",
        "label_blind",
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read",
    }
)
COST_KEYS = frozenset(
    {
        "model_requests",
        "model_attempts",
        "model_input_tokens",
        "model_output_tokens",
        "model_total_tokens",
        "search_calls",
        "search_failures",
        "search_tool_calls",
        "search_fetch_calls",
        "search_fetch_failures",
        "search_input_tokens",
        "search_output_tokens",
        "search_total_tokens",
        "system_total_tokens",
    }
)
TELEMETRY_KEYS = frozenset(
    {
        "stage_seconds",
        "logical_query_count",
        "fetch_requested_source_count",
        "fetch_usable_page_count",
        "raw_unrecoverable_failure_count",
        "retrieval_completed",
        "retrieval_failed",
        "controller_stop",
        "controller_expand",
        "controller_absent",
        "cache_miss_count",
        "cache_serve_network_fetches",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_helper_failures",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
    }
)
SUMMARY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "selected",
        "completed",
        "failed",
        "model_generated_tables",
        "fallback_tables",
        "completion_kinds",
        "cost_totals",
        "telemetry_totals",
        "stage_seconds_sum",
        "wall_seconds_sum",
        "label_blind",
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read",
        "official_evaluator_called",
    }
)
FREEZE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "selected",
        "terminal",
        "selected_opaque_ids_sha256",
        "runtime_predictions_sha256",
        "run_summary_sha256",
        "prediction_hashes_sha256",
        "exact_terminal_before_control_prediction_mapping_gold_or_evaluator_open",
        "control_prediction_mapping_gold_or_evaluator_opened_or_hashed",
        "label_blind",
        "freeze_payload_sha256",
    }
)
PROGRESS_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "selected",
        "completed_predictions",
        "unfinished_predictions",
        "executor_concurrency",
        "global_model_slot_cap",
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read",
        "progress_payload_sha256",
    }
)
ACTIVATION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "status",
        "forward_contract_sha256",
        "forward_contract_payload_sha256",
        "preactivation_audit_sha256",
        "forward_manifest_sha256",
        "selected_count",
        "executor_concurrency",
        "global_model_slot_cap",
        "shared_api_lease_active_before_activation",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read",
        "new_exact220_or_sota_authorized",
        "activation_payload_sha256",
    }
)
EXECUTION_START_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "protocol_sha256",
        "activation_sha256",
        "selected_opaque_ids_sha256",
        "runner",
        "selected",
        "executor_concurrency",
        "global_model_slot_cap",
        "label_blind",
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read",
        "api_called_before_execution_start",
        "execution_start_payload_sha256",
    }
)
FORWARD_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "selected",
        "terminal_predictions",
        "model_generated_tables",
        "fallback_tables",
        "cost_totals",
        "telemetry_totals",
        "stage_seconds_sum",
        "wall_seconds_sum",
        "prediction_freeze_sha256",
        "shared_model_receipts",
        "candidate_exact64_before_control_or_evaluator_open",
        "control_prediction_mapping_gold_or_evaluator_opened_or_hashed",
        "label_blind",
        "official_evaluator_called",
        "new_exact220_or_sota_launched",
        "execution_start_sha256",
        "activation_payload_sha256",
        "result_payload_sha256",
    }
)
RECEIPT_SUMMARY_KEYS = frozenset(
    {
        "children",
        "present",
        "valid",
        "invalid",
        "actual_model_requests",
        "slot_acquisitions",
        "all_acquisitions_match_actual_requests",
    }
)


@dataclass(frozen=True)
class TaskOutcome:
    row: dict[str, Any]
    receipt_present: bool
    receipt_valid: bool
    receipt_acquisitions: int


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.75 {label} is not a nonnegative integer")
    return value


def _nonnegative_number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.42.75 {label} is not a nonnegative number")
    return float(value)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


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


def _start_ticks(pid: int, proc_root: Path = Path("/proc")) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.42.75 process stat is truncated")
    return int(suffix[19])


def validate_activation(
    root: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
    value = read_object(root / ACTIVATION)
    preaudit = read_object(root / PREAUDIT)
    if (
        preaudit.get("role") != "v24275_two_wave_dev64_preactivation_audit"
        or preaudit.get("audit_valid") is not True
        or preaudit.get("launch_authorized") is not True
        or preaudit.get("forward_contract_sha256")
        != sha256(root / FORWARD_PROTOCOL)
        or preaudit.get("forward_contract_payload_sha256")
        != protocol["forward_contract_payload_sha256"]
        or not _sealed(preaudit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.75 preactivation audit drifted")
    if (
        set(value) != ACTIVATION_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24275_two_wave_dev64_activation"
        or value.get("status") != "active"
        or value.get("forward_contract_sha256")
        != sha256(root / FORWARD_PROTOCOL)
        or value.get("forward_contract_payload_sha256")
        != protocol["forward_contract_payload_sha256"]
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("forward_manifest_sha256")
        != protocol["forward_surface"]["dependency_manifest_sha256"]
        or value.get("selected_count") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("shared_api_lease_active_before_activation") is not False
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get(
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("new_exact220_or_sota_authorized") is not False
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.75 activation drifted")
    return value


def validate_execution_start(
    root: Path, protocol: dict[str, Any], activation: dict[str, Any]
) -> dict[str, Any]:
    value = read_object(root / EXECUTION_START)
    runner = value.get("runner")
    if (
        set(value) != EXECUTION_START_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24275_two_wave_dev64_execution_start"
        or value.get("protocol_sha256") != sha256(root / FORWARD_PROTOCOL)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("selected_opaque_ids_sha256")
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or not isinstance(runner, dict)
        or set(runner) != {"pid", "start_ticks", "marker"}
        or _nonnegative_int(runner.get("pid"), "runner pid") <= 0
        or _nonnegative_int(runner.get("start_ticks"), "runner ticks") < 0
        or runner.get("marker") != RUNNER_MARKER
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("label_blind") is not True
        or value.get(
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("api_called_before_execution_start") is not False
        or not _sealed(value, "execution_start_payload_sha256")
        or activation.get("activation_payload_sha256")
        != read_object(root / ACTIVATION).get("activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.75 execution start drifted")
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


def task_command(
    root: Path,
    task_path: Path,
    result_path: Path,
    progress_path: Path,
    receipt_path: Path,
    transport_path: Path,
) -> list[str]:
    return [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / CHILD_MARKER),
        "--task",
        str(task_path),
        "--result",
        str(result_path),
        "--progress",
        str(progress_path),
        "--model-slot-directory",
        str(root / MODEL_SLOT_DIRECTORY),
        "--model-slot-receipt",
        str(receipt_path),
        "--transport-health",
        str(transport_path),
        "--model-slot-cap",
        str(MODEL_SLOT_CAP),
        "--model-slot-pool-id",
        MODEL_SLOT_POOL_ID,
        "--proxy-url",
        MODEL["proxy_url"],
        "--model",
        MODEL["name"],
        "--reasoning-effort",
        MODEL["reasoning_effort"],
        "--service-tier",
        MODEL["service_tier"],
        "--model-timeout",
        str(MODEL["timeout_seconds"]),
        "--model-max-retries",
        str(MODEL["max_retries"]),
        "--search-batch-size",
        str(SEARCH["batch_size"]),
        "--search-workers",
        str(SEARCH["workers"]),
        "--search-context-size",
        SEARCH["context_size"],
        "--search-output-tokens",
        str(SEARCH["max_output_tokens"]),
        "--search-timeout",
        str(SEARCH["timeout_seconds"]),
        "--search-max-retries",
        str(SEARCH["max_retries"]),
        "--fetch-workers",
        str(SEARCH["fetch_workers"]),
        "--fetch-timeout",
        str(SEARCH["fetch_timeout_seconds"]),
        "--wall-seconds",
        str(LIMITS["wall_seconds"]),
        "--model-calls",
        str(LIMITS["model_calls"]),
        "--search-queries",
        str(LIMITS["search_queries"]),
        "--fetch-targets",
        str(LIMITS["fetch_targets"]),
        "--search-results-per-query",
        str(LIMITS["search_results_per_query"]),
        "--evidence-chars",
        str(LIMITS["evidence_chars"]),
        "--page-chars",
        str(LIMITS["page_chars"]),
        "--plan-output-tokens",
        str(LIMITS["plan_output_tokens"]),
        "--synthesis-output-tokens",
        str(LIMITS["synthesis_output_tokens"]),
        "--repair-output-tokens",
        str(LIMITS["repair_output_tokens"]),
        "--wave1-queries",
        str(TWO_WAVE_POLICY["wave1_queries"]),
        "--wave1-fetches",
        str(TWO_WAVE_POLICY["wave1_fetches"]),
        "--wave2-queries",
        str(TWO_WAVE_POLICY["wave2_queries"]),
        "--wave2-fetches",
        str(TWO_WAVE_POLICY["wave2_fetches"]),
        "--minimum-usable-pages",
        str(TWO_WAVE_POLICY["minimum_usable_pages"]),
        "--minimum-novel-pages",
        str(TWO_WAVE_POLICY["minimum_novel_pages"]),
        "--minimum-unique-hosts",
        str(TWO_WAVE_POLICY["minimum_unique_hosts"]),
        "--content-chars-per-column",
        str(TWO_WAVE_POLICY["content_chars_per_column"]),
        "--maximum-wave1-seconds",
        str(TWO_WAVE_POLICY["maximum_wave1_seconds"]),
        "--latency-loss-per-second",
        str(TWO_WAVE_POLICY["latency_loss_per_second"]),
        "--information-gain-weight",
        str(TWO_WAVE_POLICY["information_gain_weight"]),
        "--minimum-net-value",
        str(TWO_WAVE_POLICY["minimum_net_value"]),
        "--beta-prior-alpha",
        str(TWO_WAVE_POLICY["beta_prior_alpha"]),
        "--beta-prior-beta",
        str(TWO_WAVE_POLICY["beta_prior_beta"]),
    ]


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait(timeout=5)


def _safe_progress(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        return {}
    try:
        value = read_object(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RuntimeError):
        return {}
    if (
        value.get("role") != "v24257_score_first_safe_progress"
        or value.get("contains_question_query_url_page_prediction_or_answer")
        is not False
        or value.get("mapping_gold_evaluator_or_score_read") is not False
    ):
        return {}
    return value


def _cost(result: Mapping[str, Any]) -> dict[str, int]:
    model = result["cost"]["model"]
    search = result["cost"]["search"]
    return {
        "model_requests": int(model["requests"]),
        "model_attempts": int(model["attempts"]),
        "model_input_tokens": int(model["input_tokens"]),
        "model_output_tokens": int(model["output_tokens"]),
        "model_total_tokens": int(model["total_tokens"]),
        "search_calls": int(search["calls"]),
        "search_failures": int(search["failures"]),
        "search_tool_calls": int(search["tool_calls"]),
        "search_fetch_calls": int(search["fetch_calls"]),
        "search_fetch_failures": int(search["fetch_failures"]),
        "search_input_tokens": int(search["input_tokens"]),
        "search_output_tokens": int(search["output_tokens"]),
        "search_total_tokens": int(search["total_tokens"]),
        "system_total_tokens": int(result["cost"]["system_total_tokens"]),
    }


def _stages(result: Mapping[str, Any]) -> dict[str, float]:
    stages: dict[str, float] = {}
    telemetry = result.get("telemetry")
    if isinstance(telemetry, Mapping):
        for event in [
            *(telemetry.get("model_events") or []),
            *(telemetry.get("search_events") or []),
        ]:
            if isinstance(event, Mapping):
                stage = str(event.get("stage", ""))
                if stage in {"plan", "search", "fetch", "synthesis", "repair"}:
                    stages[stage] = round(
                        stages.get(stage, 0.0)
                        + max(0.0, float(event.get("elapsed_seconds", 0.0))),
                        6,
                    )
    return stages


def runtime_row(
    result: Mapping[str, Any],
    *,
    v24273: bool,
    transport_health: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if v24273:
        validate_v24273_result(result)
    retrieval = result.get("two_wave_retrieval") if v24273 else None
    completed = isinstance(retrieval, Mapping) and retrieval.get("status") == "completed"
    nested = retrieval.get("receipt") if completed else None
    total = nested.get("total") if isinstance(nested, Mapping) else {}
    controller = nested.get("controller") if isinstance(nested, Mapping) else {}
    decision = controller.get("decision") if isinstance(controller, Mapping) else None
    health = dict(transport_health or {})
    expected_health = {
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_helper_failures",
    }
    if (v24273 and set(health) != expected_health) or (
        not v24273 and set(health) - expected_health
    ):
        raise ValueError("V2.42.75 transport health schema drifted")
    if any(
        isinstance(health.get(name), bool)
        or not isinstance(health.get(name), int)
        or health[name] < 0
        for name in health
    ):
        raise ValueError("V2.42.75 transport health counter drifted")
    telemetry = {
        "stage_seconds": _stages(result),
        "logical_query_count": int(total.get("queries_executed", 0)),
        "fetch_requested_source_count": int(total.get("fetches_attempted", 0)),
        "fetch_usable_page_count": int(total.get("usable_pages", 0)),
        "raw_unrecoverable_failure_count": int(
            total.get("unrecoverable_search_failures", 0)
        ),
        "retrieval_completed": int(completed),
        "retrieval_failed": int(not completed),
        "controller_stop": int(decision == "stop"),
        "controller_expand": int(decision == "expand"),
        "controller_absent": int(decision not in {"stop", "expand"}),
        "cache_miss_count": int(
            retrieval.get("cache_miss_count", 0)
            if isinstance(retrieval, Mapping)
            else 0
        ),
        "cache_serve_network_fetches": int(
            retrieval.get("network_fetches_during_cache_serve", 0)
            if isinstance(retrieval, Mapping)
            else 0
        ),
        "hard_fetch_helper_calls": int(health.get("hard_fetch_helper_calls", 0)),
        "hard_fetch_deadline_failures": int(
            health.get("hard_fetch_deadline_failures", 0)
        ),
        "fetch_helper_failures": int(health.get("fetch_helper_failures", 0)),
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential": False,
    }
    value = {
        "opaque_id": result["opaque_id"],
        "status": "completed",
        "prediction": result["prediction"],
        "prediction_sha256": result["prediction_sha256"],
        "completion_kind": result["completion_kind"],
        "elapsed_seconds": result["budget"]["elapsed_seconds"],
        "cost": _cost(result),
        "telemetry": telemetry,
        "label_blind": True,
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read": False,
    }
    validate_runtime_row(value)
    return value


def validate_runtime_row(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RUNTIME_ROW_KEYS
        or value.get("status") != "completed"
        or not isinstance(value.get("opaque_id"), str)
        or not isinstance(value.get("prediction"), str)
        or not value["prediction"]
        or hashlib.sha256(value["prediction"].encode()).hexdigest()
        != value.get("prediction_sha256")
        or not isinstance(value.get("completion_kind"), str)
        or value.get("label_blind") is not True
        or value.get(
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise ValueError("V2.42.75 runtime row drifted")
    _nonnegative_number(value.get("elapsed_seconds"), "elapsed seconds")
    cost = value.get("cost")
    telemetry = value.get("telemetry")
    if not isinstance(cost, Mapping) or set(cost) != COST_KEYS:
        raise ValueError("V2.42.75 runtime cost drifted")
    for key in COST_KEYS:
        _nonnegative_int(cost.get(key), f"cost.{key}")
    if cost["system_total_tokens"] != cost["model_total_tokens"] + cost[
        "search_total_tokens"
    ]:
        raise ValueError("V2.42.75 token accounting drifted")
    if not isinstance(telemetry, Mapping) or set(telemetry) != TELEMETRY_KEYS:
        raise ValueError("V2.42.75 runtime telemetry drifted")
    if telemetry.get(
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential"
    ) is not False:
        raise ValueError("V2.42.75 runtime telemetry contains content")
    for key in TELEMETRY_KEYS - {
        "stage_seconds",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
    }:
        _nonnegative_int(telemetry.get(key), f"telemetry.{key}")
    if telemetry["retrieval_completed"] + telemetry["retrieval_failed"] != 1:
        raise ValueError("V2.42.75 retrieval terminal accounting drifted")
    if (
        telemetry["hard_fetch_deadline_failures"]
        + telemetry["fetch_helper_failures"]
        > telemetry["hard_fetch_helper_calls"]
        or (
            telemetry["retrieval_completed"] == 1
            and (
                telemetry["hard_fetch_helper_calls"]
                != cost["search_fetch_calls"]
                or telemetry["hard_fetch_deadline_failures"]
                + telemetry["fetch_helper_failures"]
                > cost["search_fetch_failures"]
            )
        )
    ):
        raise ValueError("V2.42.75 hard-fetch accounting drifted")
    if (
        telemetry["controller_stop"]
        + telemetry["controller_expand"]
        + telemetry["controller_absent"]
        != 1
    ):
        raise ValueError("V2.42.75 controller accounting drifted")
    stages = telemetry.get("stage_seconds")
    if not isinstance(stages, Mapping) or any(
        key not in {"plan", "search", "fetch", "synthesis", "repair"}
        or _nonnegative_number(number, f"stage.{key}") < 0
        for key, number in stages.items()
    ):
        raise ValueError("V2.42.75 stage timing drifted")


def _fallback_row(
    task: Mapping[str, Any],
    *,
    kind: str,
    stage: str,
    failure_type: str,
    elapsed: float,
    progress: Mapping[str, Any],
) -> dict[str, Any]:
    result = build_total_fallback_result(
        task,
        limits=ScoreFirstLimits(**dict(LIMITS)),
        completion_kind=kind,
        failure_stage=stage,
        failure_type=failure_type,
        elapsed_seconds=elapsed,
        last_progress=progress,
    )
    return runtime_row(result, v24273=False)


def run_one_task(
    root: Path,
    protocol: dict[str, Any],
    task: dict[str, str],
    task_root: Path,
    *,
    popen: Any = subprocess.Popen,
) -> TaskOutcome:
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    task_path = task_root / "visible_task.json"
    result_path = task_root / "result.json"
    progress_path = task_root / "safe_progress.json"
    receipt_path = task_root / RECEIPT_NAME
    transport_path = task_root / TRANSPORT_NAME
    _new_json(task_path, task)
    process = popen(
        task_command(
            root,
            task_path,
            result_path,
            progress_path,
            receipt_path,
            transport_path,
        ),
        cwd=root,
        env=_child_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    started = time.monotonic()
    timed_out = False
    try:
        return_code = process.wait(
            timeout=float(LIMITS["wall_seconds"])
            + float(protocol["execution"]["parent_deadline_grace_seconds"])
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_group(process)
        return_code = process.returncode
    elapsed = time.monotonic() - started
    receipt: dict[str, Any] | None = None
    if receipt_path.is_file() and not receipt_path.is_symlink():
        try:
            receipt = validate_receipt(
                read_object(receipt_path), expected_cap=MODEL_SLOT_CAP
            )
        except (OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError):
            receipt = None
    health: dict[str, int] = {
        "hard_fetch_helper_calls": 0,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
    }
    if transport_path.is_file() and not transport_path.is_symlink():
        try:
            health = validate_transport_health(read_object(transport_path))
        except (OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError):
            health = {
                "hard_fetch_helper_calls": 1,
                "hard_fetch_deadline_failures": 0,
                "fetch_helper_failures": 1,
            }
    row: dict[str, Any]
    if not timed_out and return_code == 0 and result_path.is_file():
        try:
            envelope = read_object(result_path)
            unsigned = dict(envelope)
            seal = unsigned.pop("envelope_payload_sha256", None)
            if (
                set(envelope)
                != {
                    "artifact_version",
                    "role",
                    "result",
                    "transport_health",
                    "envelope_payload_sha256",
                }
                or envelope.get("artifact_version") != 1
                or envelope.get("role") != "v24275_two_wave_task_envelope"
                or seal != payload_sha256(unsigned)
                or validate_transport_health(envelope.get("transport_health"))
                != health
            ):
                raise ValueError("V2.42.75 child envelope drifted")
            result = envelope["result"]
            validate_v24273_result(result)
            row = runtime_row(
                result,
                v24273=True,
                transport_health=health,
            )
        except (
            KeyError,
            OSError,
            TypeError,
            UnicodeError,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
        ):
            row = runtime_row(
                build_total_fallback_result(
                    task,
                    limits=ScoreFirstLimits(**dict(LIMITS)),
                    completion_kind="worker_failure_fallback",
                    failure_stage="result_validation",
                    failure_type="ChildResultInvalid",
                    elapsed_seconds=elapsed,
                    last_progress=_safe_progress(progress_path),
                ),
                v24273=False,
                transport_health=health,
            )
    else:
        row = runtime_row(
            build_total_fallback_result(
                task,
                limits=ScoreFirstLimits(**dict(LIMITS)),
                completion_kind=(
                    "hard_deadline_fallback"
                    if timed_out
                    else "worker_failure_fallback"
                ),
                failure_stage="parent_executor",
                failure_type=(
                    "HardDeadlineExceeded" if timed_out else "WorkerNonzeroExit"
                ),
                elapsed_seconds=elapsed,
                last_progress=_safe_progress(progress_path),
            ),
            v24273=False,
            transport_health=health,
        )
    acquisitions = int(receipt.get("acquisitions", 0)) if receipt else 0
    valid = False
    if receipt is not None:
        try:
            validate_receipt(
                receipt,
                expected_cap=MODEL_SLOT_CAP,
                expected_acquisitions=int(row["cost"]["model_requests"]),
            )
            valid = True
        except (KeyError, TypeError, ValueError):
            valid = False
    return TaskOutcome(row, receipt is not None, valid, acquisitions)


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != SELECTED_COUNT:
        raise ValueError("V2.42.75 summary row count drifted")
    kinds: dict[str, int] = {}
    costs = {key: 0 for key in COST_KEYS}
    telemetry_totals = {
        key: 0
        for key in TELEMETRY_KEYS
        if key
        not in {
            "stage_seconds",
            "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
        }
    }
    stages: dict[str, float] = {}
    for row in rows:
        validate_runtime_row(row)
        kind = str(row["completion_kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
        for key in COST_KEYS:
            costs[key] += int(row["cost"][key])
        for key in telemetry_totals:
            telemetry_totals[key] += int(row["telemetry"][key])
        for key, seconds in row["telemetry"]["stage_seconds"].items():
            stages[key] = round(stages.get(key, 0.0) + float(seconds), 6)
    value = {
        "artifact_version": 1,
        "role": "v24275_candidate_run_summary",
        "selected": SELECTED_COUNT,
        "completed": SELECTED_COUNT,
        "failed": 0,
        "model_generated_tables": sum(
            row["completion_kind"] in MODEL_GENERATED for row in rows
        ),
        "fallback_tables": sum(
            row["completion_kind"] not in MODEL_GENERATED for row in rows
        ),
        "completion_kinds": kinds,
        "cost_totals": costs,
        "telemetry_totals": telemetry_totals,
        "stage_seconds_sum": stages,
        "wall_seconds_sum": round(
            sum(float(row["elapsed_seconds"]) for row in rows), 6
        ),
        "label_blind": True,
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
    }
    validate_summary(value)
    return value


def validate_summary(value: Mapping[str, Any]) -> None:
    if (
        set(value) != SUMMARY_KEYS
        or value.get("role") != "v24275_candidate_run_summary"
        or value.get("selected") != SELECTED_COUNT
        or value.get("completed") != SELECTED_COUNT
        or value.get("failed") != 0
        or value.get("model_generated_tables", -1)
        + value.get("fallback_tables", -1)
        != SELECTED_COUNT
        or sum((value.get("completion_kinds") or {}).values()) != SELECTED_COUNT
        or value.get("label_blind") is not True
        or value.get(
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("official_evaluator_called") is not False
    ):
        raise ValueError("V2.42.75 summary drifted")
    costs = value.get("cost_totals")
    telemetry = value.get("telemetry_totals")
    stages = value.get("stage_seconds_sum")
    if not isinstance(costs, Mapping) or set(costs) != COST_KEYS:
        raise ValueError("V2.42.75 summary cost schema drifted")
    for key in COST_KEYS:
        _nonnegative_int(costs.get(key), f"summary.cost.{key}")
    if costs["system_total_tokens"] != costs["model_total_tokens"] + costs[
        "search_total_tokens"
    ]:
        raise ValueError("V2.42.75 summary token accounting drifted")
    expected_telemetry = TELEMETRY_KEYS - {
        "stage_seconds",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
    }
    if not isinstance(telemetry, Mapping) or set(telemetry) != expected_telemetry:
        raise ValueError("V2.42.75 summary telemetry schema drifted")
    for key in expected_telemetry:
        _nonnegative_int(telemetry.get(key), f"summary.telemetry.{key}")
    if telemetry["retrieval_completed"] + telemetry["retrieval_failed"] != SELECTED_COUNT:
        raise ValueError("V2.42.75 summary retrieval accounting drifted")
    if (
        telemetry["controller_stop"]
        + telemetry["controller_expand"]
        + telemetry["controller_absent"]
        != SELECTED_COUNT
    ):
        raise ValueError("V2.42.75 summary controller accounting drifted")
    if not isinstance(stages, Mapping) or any(
        key not in {"plan", "search", "fetch", "synthesis", "repair"}
        or _nonnegative_number(number, f"summary.stage.{key}") < 0
        for key, number in stages.items()
    ):
        raise ValueError("V2.42.75 summary stage schema drifted")
    _nonnegative_number(value.get("wall_seconds_sum"), "summary wall")


def progress(completed: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_safe_progress",
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "completed_predictions": completed,
        "unfinished_predictions": SELECTED_COUNT - completed,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["progress_payload_sha256"] = payload_sha256(value)
    if (
        set(value) != PROGRESS_KEYS
        or not 0 <= completed <= SELECTED_COUNT
        or not _sealed(value, "progress_payload_sha256")
    ):
        raise ValueError("V2.42.75 progress drifted")
    return value


def execute_forward(
    root: Path,
    protocol: dict[str, Any],
    tasks: list[dict[str, str]],
    *,
    runner: Callable[[Path, dict[str, Any], dict[str, str], Path], TaskOutcome] = run_one_task,
    progress_writer: Callable[[dict[str, Any]], None] | None = None,
) -> list[TaskOutcome]:
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.42.75 scheduler task count drifted")
    outcomes: dict[int, TaskOutcome] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=EXECUTOR_CONCURRENCY, thread_name_prefix="v24275-dev64"
    ) as executor:
        futures = {
            executor.submit(
                runner,
                root,
                protocol,
                task,
                root / TASK_ROOT / f"task_{position:04d}",
            ): position
            for position, task in enumerate(tasks, start=1)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            try:
                outcome = future.result()
                validate_runtime_row(outcome.row)
            except BaseException as exc:
                row = _fallback_row(
                    tasks[position - 1],
                    kind="worker_failure_fallback",
                    stage="parent_future",
                    failure_type=type(exc).__name__,
                    elapsed=0.0,
                    progress={},
                )
                outcome = TaskOutcome(row, False, False, 0)
            outcomes[position] = outcome
            if progress_writer:
                progress_writer(progress(len(outcomes)))
    ordered = [outcomes[position] for position in range(1, SELECTED_COUNT + 1)]
    if [outcome.row["opaque_id"] for outcome in ordered] != [
        task["opaque_id"] for task in tasks
    ]:
        raise RuntimeError("V2.42.75 scheduler order drifted")
    return ordered


def validate_prediction_freeze(
    root: Path, protocol: dict[str, Any], value: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if (
        set(value) != FREEZE_KEYS
        or value.get("role") != "v24275_candidate_prediction_freeze"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal") != SELECTED_COUNT
        or value.get("selected_opaque_ids_sha256")
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or value.get("runtime_predictions_sha256")
        != sha256(root / RUNTIME_PREDICTIONS)
        or value.get("run_summary_sha256") != sha256(root / RUN_SUMMARY)
        or value.get(
            "exact_terminal_before_control_prediction_mapping_gold_or_evaluator_open"
        )
        is not True
        or value.get("control_prediction_mapping_gold_or_evaluator_opened_or_hashed")
        is not False
        or value.get("label_blind") is not True
        or not _sealed(value, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.42.75 prediction freeze drifted")
    rows = [
        json.loads(line)
        for line in (root / RUNTIME_PREDICTIONS)
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    if len(rows) != SELECTED_COUNT:
        raise RuntimeError("V2.42.75 prediction freeze row count drifted")
    for row in rows:
        validate_runtime_row(row)
    if (
        payload_sha256([row["opaque_id"] for row in rows])
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or payload_sha256([row["prediction_sha256"] for row in rows])
        != value.get("prediction_hashes_sha256")
    ):
        raise RuntimeError("V2.42.75 prediction vector drifted")
    validate_summary(read_object(root / RUN_SUMMARY))
    return rows


def validate_forward_result(
    root: Path, protocol: dict[str, Any], value: Mapping[str, Any]
) -> None:
    activation = validate_activation(root, protocol)
    validate_execution_start(root, protocol, activation)
    freeze = read_object(root / PREDICTION_FREEZE)
    validate_prediction_freeze(root, protocol, freeze)
    if (
        set(value) != FORWARD_KEYS
        or value.get("role") != "v24275_two_wave_dev64_forward_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal_predictions") != SELECTED_COUNT
        or value.get("model_generated_tables", -1)
        + value.get("fallback_tables", -1)
        != SELECTED_COUNT
        or value.get("prediction_freeze_sha256")
        != sha256(root / PREDICTION_FREEZE)
        or value.get("candidate_exact64_before_control_or_evaluator_open") is not True
        or value.get("control_prediction_mapping_gold_or_evaluator_opened_or_hashed")
        is not False
        or value.get("label_blind") is not True
        or value.get("official_evaluator_called") is not False
        or value.get("new_exact220_or_sota_launched") is not False
        or value.get("execution_start_sha256") != sha256(root / EXECUTION_START)
        or value.get("activation_payload_sha256")
        != activation["activation_payload_sha256"]
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.42.75 forward result drifted")
    run_summary = read_object(root / RUN_SUMMARY)
    validate_summary(run_summary)
    for name in (
        "model_generated_tables",
        "fallback_tables",
        "cost_totals",
        "telemetry_totals",
        "stage_seconds_sum",
        "wall_seconds_sum",
    ):
        if value.get(name) != run_summary.get(name):
            raise RuntimeError(f"V2.42.75 forward {name} binding drifted")
    receipts = value.get("shared_model_receipts")
    if not isinstance(receipts, Mapping) or set(receipts) != RECEIPT_SUMMARY_KEYS:
        raise RuntimeError("V2.42.75 model receipt summary drifted")
    for key in RECEIPT_SUMMARY_KEYS - {"all_acquisitions_match_actual_requests"}:
        _nonnegative_int(receipts.get(key), f"receipt.{key}")
    healthy = (
        receipts["children"] == SELECTED_COUNT
        and receipts["present"] == SELECTED_COUNT
        and receipts["valid"] == SELECTED_COUNT
        and receipts["invalid"] == 0
        and receipts["slot_acquisitions"] == receipts["actual_model_requests"]
    )
    if receipts.get("all_acquisitions_match_actual_requests") is not healthy:
        raise RuntimeError("V2.42.75 model receipt accounting drifted")


def _prepare_slots(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v24275_model_slot",
                "pool_id": MODEL_SLOT_POOL_ID,
                "slot": index,
                "slot_cap": MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def main() -> None:
    root = ROOT
    protocol = validate_protocol(root, FORWARD_PROTOCOL)
    activation = validate_activation(root, protocol)
    tasks = selected_tasks(root, protocol)
    for path in (root / EXECUTION_START, root / FORWARD_RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.42.75 forward surface is not pristine")
    start = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_execution_start",
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(root / FORWARD_PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected_opaque_ids_sha256": protocol["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "runner": {
            "pid": os.getpid(),
            "start_ticks": _start_ticks(os.getpid()),
            "marker": RUNNER_MARKER,
        },
        "selected": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "label_blind": True,
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = payload_sha256(start)
    _new_json(root / EXECUTION_START, start)
    (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    _prepare_slots(root)
    (root / TASK_ROOT).mkdir(mode=0o700)
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["forward_owner"],
        purpose=lease["forward_purpose"],
        path=root / lease["path"],
    ):
        outcomes = execute_forward(
            root,
            protocol,
            tasks,
            progress_writer=lambda value: _atomic_json(root / SAFE_PROGRESS, value),
        )
    rows = [outcome.row for outcome in outcomes]
    _write_jsonl_new(root / RUNTIME_PREDICTIONS, rows)
    run_summary = summary(rows)
    _new_json(root / RUN_SUMMARY, run_summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24275_candidate_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "selected": SELECTED_COUNT,
        "terminal": SELECTED_COUNT,
        "selected_opaque_ids_sha256": protocol["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "run_summary_sha256": sha256(root / RUN_SUMMARY),
        "prediction_hashes_sha256": payload_sha256(
            [row["prediction_sha256"] for row in rows]
        ),
        "exact_terminal_before_control_prediction_mapping_gold_or_evaluator_open": True,
        "control_prediction_mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = payload_sha256(freeze)
    _new_json(root / PREDICTION_FREEZE, freeze)
    validate_prediction_freeze(root, protocol, freeze)
    requests = sum(row["cost"]["model_requests"] for row in rows)
    acquisitions = sum(outcome.receipt_acquisitions for outcome in outcomes)
    valid = sum(outcome.receipt_valid for outcome in outcomes)
    forward = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_forward_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "terminal_predictions": SELECTED_COUNT,
        "model_generated_tables": run_summary["model_generated_tables"],
        "fallback_tables": run_summary["fallback_tables"],
        "cost_totals": run_summary["cost_totals"],
        "telemetry_totals": run_summary["telemetry_totals"],
        "stage_seconds_sum": run_summary["stage_seconds_sum"],
        "wall_seconds_sum": run_summary["wall_seconds_sum"],
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "shared_model_receipts": {
            "children": SELECTED_COUNT,
            "present": sum(outcome.receipt_present for outcome in outcomes),
            "valid": valid,
            "invalid": SELECTED_COUNT - valid,
            "actual_model_requests": requests,
            "slot_acquisitions": acquisitions,
            "all_acquisitions_match_actual_requests": valid == SELECTED_COUNT
            and acquisitions == requests,
        },
        "candidate_exact64_before_control_or_evaluator_open": True,
        "control_prediction_mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
        "official_evaluator_called": False,
        "new_exact220_or_sota_launched": False,
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "activation_payload_sha256": activation["activation_payload_sha256"],
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    _new_json(root / FORWARD_RESULT, forward)
    validate_forward_result(root, protocol, forward)
    _atomic_json(root / SAFE_PROGRESS, progress(SELECTED_COUNT))
    print(
        json.dumps(
            {"forward_result": str(FORWARD_RESULT), "terminal_predictions": 64},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
