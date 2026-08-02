#!/usr/bin/env python3
"""Neutral eight-way capacity gate for the V2.42.75 hard-fetch transport."""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import (  # noqa: E402
    TwoWavePolicy,
    object_sha256,
)
from deepwide_agent.v24273_two_wave_task_runtime import (  # noqa: E402
    run_v24273_task,
    validate_v24273_result,
)
from deepwide_agent.v24275_forward_contract import (  # noqa: E402
    LIMITS,
    MODEL,
    SEARCH,
    TWO_WAVE_POLICY,
    sha256,
)
from deepwide_agent.v24275_hard_deadline_fetch import (  # noqa: E402
    HardDeadlineNativeSearchClient,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


OUTPUT = Path("results/v24276_hard_deadline_capacity_v1_20260802.json")
CONCURRENCY = 8
BATCH_WALL_CEILING_SECONDS = 180.0
MAXIMUM_TASK_WALL_SECONDS = 120.0
NEUTRAL_QUESTIONS = (
    "Using official Python documentation, return one Markdown table with columns Feature, Version, and Status for three Python 3.13 features. Return only the table.",
    "Using official PostgreSQL documentation, return one Markdown table with columns Feature, Version, and Status for three PostgreSQL 17 features. Return only the table.",
    "Using official Rust documentation, return one Markdown table with columns Feature, Version, and Status for three Rust 1.80 features. Return only the table.",
    "Using official Node.js documentation, return one Markdown table with columns Feature, Version, and Status for three Node.js 22 features. Return only the table.",
    "Using official Go documentation, return one Markdown table with columns Feature, Version, and Status for three Go 1.23 features. Return only the table.",
    "Using official Java documentation, return one Markdown table with columns Feature, Version, and Status for three Java 21 features. Return only the table.",
    "Using official Kubernetes documentation, return one Markdown table with columns Feature, Version, and Status for three Kubernetes 1.31 features. Return only the table.",
    "Using official SQLite documentation, return one Markdown table with columns Feature, Version, and Status for three SQLite 3.46 features. Return only the table.",
)
SOURCE_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24267_total_fallback.py",
    "src/deepwide_agent/v24268_keyless_batched_runtime.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24270_budget_equivalent_union.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24272_two_wave_retrieval.py",
    "src/deepwide_agent/v24273_two_wave_task_runtime.py",
    "src/deepwide_agent/v24275_forward_contract.py",
    "src/deepwide_agent/v24275_hard_deadline_fetch.py",
    "scripts/run_v24275_fetch_helper.py",
    "scripts/probe_v24276_hard_deadline_capacity.py",
)
MODEL_COUNTERS = ("requests", "attempts", "input_tokens", "output_tokens", "total_tokens")
SEARCH_COUNTERS = (
    "calls",
    "failures",
    "tool_calls",
    "fetch_calls",
    "fetch_failures",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)
TASK_KEYS = frozenset(
    {
        "ordinal",
        "terminal",
        "failure_type",
        "completion_kind",
        "wall_seconds",
        "model_counters",
        "search_counters",
        "stage_seconds",
        "failure_types",
        "retrieval_status",
        "controller_decision",
        "controller_reason",
        "queries_executed",
        "fetches_attempted",
        "usable_pages",
        "unrecoverable_search_failures",
        "cache_miss_count",
        "cache_serve_network_fetches",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_helper_failures",
        "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "probe_scope",
        "provider",
        "model",
        "reasoning_effort",
        "concurrency",
        "batch_wall_ceiling_seconds",
        "maximum_task_wall_seconds",
        "limits",
        "two_wave_policy",
        "hard_fetch_contract",
        "tasks",
        "summary",
        "source_manifest",
        "source_manifest_sha256",
        "source_policy",
        "authorization",
        "passed",
        "result_payload_sha256",
    }
)


def _counter_snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    return {name: max(0, int(getattr(client, name, 0) or 0)) for name in names}


def _finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.76 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.76 {label} is invalid")
    return number


def _stage_seconds(result: Mapping[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    telemetry = result["telemetry"]
    for event in [*telemetry["model_events"], *telemetry["search_events"]]:
        stage = str(event["stage"])
        values[stage] = round(
            values.get(stage, 0.0) + float(event["elapsed_seconds"]), 6
        )
    return values


def _new_client_pair(proxy_url: str) -> tuple[ResponsesClient, HardDeadlineNativeSearchClient]:
    if proxy_url != MODEL["proxy_url"]:
        raise ValueError("V2.42.76 proxy identity drifted")
    model = ResponsesClient(
        proxy_url,
        MODEL["name"],
        reasoning_effort=MODEL["reasoning_effort"],
        service_tier=MODEL["service_tier"],
        timeout=MODEL["timeout_seconds"],
        max_retries=MODEL["max_retries"],
    )
    search = HardDeadlineNativeSearchClient(
        SEARCH["proxy_url"],
        SEARCH["model"],
        reasoning_effort=MODEL["reasoning_effort"],
        service_tier=MODEL["service_tier"],
        timeout=SEARCH["timeout_seconds"],
        max_retries=SEARCH["max_retries"],
        max_workers=SEARCH["workers"],
        batch_size=SEARCH["batch_size"],
        search_context_size=SEARCH["context_size"],
        max_output_tokens=SEARCH["max_output_tokens"],
        fetch_pages=False,
        fetch_workers=SEARCH["fetch_workers"],
        fetch_timeout=SEARCH["fetch_timeout_seconds"],
        max_page_chars=LIMITS["page_chars"],
        hard_fetch_deadline_seconds=SEARCH["hard_fetch_deadline_seconds"],
    )
    return model, search


def _run_case(ordinal: int, proxy_url: str) -> dict[str, Any]:
    model, search = _new_client_pair(proxy_url)
    started = time.monotonic()
    try:
        result = run_v24273_task(
            {
                "opaque_id": "task_" + f"76{ordinal:02x}".ljust(24, "0"),
                "question": NEUTRAL_QUESTIONS[ordinal],
            },
            model=model,
            search=search,
            limits=ScoreFirstLimits(**dict(LIMITS)),
            policy=TwoWavePolicy(**dict(TWO_WAVE_POLICY)),
        )
        validate_v24273_result(result)
        retrieval = result["two_wave_retrieval"]
        nested = retrieval.get("receipt") or {}
        total = nested.get("total") or {}
        controller = nested.get("controller") or {}
        value = {
            "ordinal": ordinal + 1,
            "terminal": True,
            "failure_type": None,
            "completion_kind": str(result["completion_kind"]),
            "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
            "model_counters": _counter_snapshot(model, MODEL_COUNTERS),
            "search_counters": _counter_snapshot(search, SEARCH_COUNTERS),
            "stage_seconds": _stage_seconds(result),
            "failure_types": [str(item["type"]) for item in result["failures"]],
            "retrieval_status": retrieval["status"],
            "controller_decision": controller.get("decision"),
            "controller_reason": controller.get("reason"),
            "queries_executed": int(total.get("queries_executed", 0)),
            "fetches_attempted": int(total.get("fetches_attempted", 0)),
            "usable_pages": int(total.get("usable_pages", 0)),
            "unrecoverable_search_failures": int(
                total.get("unrecoverable_search_failures", 0)
            ),
            "cache_miss_count": int(retrieval["cache_miss_count"]),
            "cache_serve_network_fetches": int(
                retrieval["network_fetches_during_cache_serve"]
            ),
            "hard_fetch_helper_calls": int(search.hard_fetch_helper_calls),
            "hard_fetch_deadline_failures": int(search.hard_fetch_deadline_failures),
            "fetch_helper_failures": int(search.fetch_helper_failures),
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        }
    except Exception as exc:  # noqa: BLE001 - content-free terminal probe row
        value = {
            "ordinal": ordinal + 1,
            "terminal": True,
            "failure_type": type(exc).__name__,
            "completion_kind": "capacity_probe_failure",
            "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
            "model_counters": _counter_snapshot(model, MODEL_COUNTERS),
            "search_counters": _counter_snapshot(search, SEARCH_COUNTERS),
            "stage_seconds": {},
            "failure_types": [type(exc).__name__],
            "retrieval_status": "failed",
            "controller_decision": None,
            "controller_reason": None,
            "queries_executed": 0,
            "fetches_attempted": 0,
            "usable_pages": 0,
            "unrecoverable_search_failures": 0,
            "cache_miss_count": 0,
            "cache_serve_network_fetches": 0,
            "hard_fetch_helper_calls": int(search.hard_fetch_helper_calls),
            "hard_fetch_deadline_failures": int(search.hard_fetch_deadline_failures),
            "fetch_helper_failures": int(search.fetch_helper_failures),
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        }
    validate_task(value)
    return value


def validate_task(value: Mapping[str, Any]) -> None:
    model = value.get("model_counters")
    search = value.get("search_counters")
    stages = value.get("stage_seconds")
    if (
        set(value) != TASK_KEYS
        or value.get("terminal") is not True
        or not isinstance(value.get("ordinal"), int)
        or isinstance(value.get("ordinal"), bool)
        or not 1 <= value["ordinal"] <= CONCURRENCY
        or not isinstance(value.get("completion_kind"), str)
        or not isinstance(value.get("failure_types"), list)
        or not isinstance(model, Mapping)
        or set(model) != set(MODEL_COUNTERS)
        or not isinstance(search, Mapping)
        or set(search) != set(SEARCH_COUNTERS)
        or not isinstance(stages, Mapping)
        or not set(stages).issubset({"plan", "search", "fetch", "synthesis", "repair"})
        or value.get(
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise RuntimeError("V2.42.76 task schema drifted")
    _finite_nonnegative(value.get("wall_seconds"), "task wall")
    for number in [*model.values(), *search.values()]:
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise RuntimeError("V2.42.76 counter drifted")
    for number in stages.values():
        _finite_nonnegative(number, "stage wall")
    for name in (
        "queries_executed",
        "fetches_attempted",
        "usable_pages",
        "unrecoverable_search_failures",
        "cache_miss_count",
        "cache_serve_network_fetches",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_helper_failures",
    ):
        number = value.get(name)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise RuntimeError("V2.42.76 task counter drifted")


def summarize(tasks: Sequence[Mapping[str, Any]], batch_wall: float) -> dict[str, Any]:
    if len(tasks) != CONCURRENCY:
        raise RuntimeError("V2.42.76 task count drifted")
    values = [dict(task) for task in tasks]
    for task in values:
        validate_task(task)
    walls = [float(task["wall_seconds"]) for task in values]
    terminal = sum(task["terminal"] is True for task in values)
    model_generated = sum(task["completion_kind"] in MODEL_GENERATED for task in values)
    forward_failures = sum(
        bool(task["failure_type"])
        or bool(task["failure_types"])
        or task["retrieval_status"] != "completed"
        for task in values
    )
    hard_deadlines = sum(task["hard_fetch_deadline_failures"] for task in values)
    helper_failures = sum(task["fetch_helper_failures"] for task in values)
    helper_calls = sum(task["hard_fetch_helper_calls"] for task in values)
    fetch_calls = sum(task["search_counters"]["fetch_calls"] for task in values)
    model_requests = sum(task["model_counters"]["requests"] for task in values)
    model_attempts = sum(task["model_counters"]["attempts"] for task in values)
    unrecoverable = sum(task["unrecoverable_search_failures"] for task in values)
    cache_misses = sum(task["cache_miss_count"] for task in values)
    cache_network = sum(task["cache_serve_network_fetches"] for task in values)
    checks = {
        "exact_terminal": terminal == CONCURRENCY,
        "all_model_generated": model_generated == CONCURRENCY,
        "no_forward_or_retrieval_failures": forward_failures == 0,
        "no_model_retries": model_attempts == model_requests,
        "no_unrecoverable_search_failures": unrecoverable == 0,
        "hard_fetch_helper_calls_match_fetch_calls": helper_calls == fetch_calls,
        "no_hard_fetch_deadlines": hard_deadlines == 0,
        "no_fetch_helper_failures": helper_failures == 0,
        "no_cache_misses": cache_misses == 0,
        "cache_serve_has_no_network_fetch": cache_network == 0,
        "maximum_task_wall": max(walls) <= MAXIMUM_TASK_WALL_SECONDS,
        "batch_wall": batch_wall <= BATCH_WALL_CEILING_SECONDS,
    }
    return {
        "selected": CONCURRENCY,
        "terminal": terminal,
        "model_generated": model_generated,
        "fallback": CONCURRENCY - model_generated,
        "forward_or_retrieval_failures": forward_failures,
        "model_requests": model_requests,
        "model_attempts": model_attempts,
        "search_calls": sum(task["search_counters"]["calls"] for task in values),
        "fetch_calls": fetch_calls,
        "fetch_failures": sum(task["search_counters"]["fetch_failures"] for task in values),
        "hard_fetch_helper_calls": helper_calls,
        "hard_fetch_deadline_failures": hard_deadlines,
        "fetch_helper_failures": helper_failures,
        "unrecoverable_search_failures": unrecoverable,
        "cache_misses": cache_misses,
        "cache_serve_network_fetches": cache_network,
        "task_wall_sum_seconds": round(sum(walls), 6),
        "task_wall_mean_seconds": round(sum(walls) / CONCURRENCY, 6),
        "task_wall_max_seconds": round(max(walls), 6),
        "batch_wall_seconds": round(batch_wall, 6),
        "checks": checks,
        "passed": all(checks.values()),
    }


def validate_result(value: Mapping[str, Any], root: Path = ROOT) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    tasks = value.get("tasks")
    summary = value.get("summary")
    manifest = value.get("source_manifest")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24276_hard_deadline_capacity"
        or value.get("probe_scope")
        != "neutral_public_documentation_full_task_concurrency_8_hard_fetch_deadline"
        or value.get("provider") != SEARCH["provider"]
        or value.get("model") != MODEL["name"]
        or value.get("reasoning_effort") != MODEL["reasoning_effort"]
        or value.get("concurrency") != CONCURRENCY
        or value.get("limits") != LIMITS
        or value.get("two_wave_policy") != TWO_WAVE_POLICY
        or value.get("hard_fetch_contract")
        != {
            "per_url_total_wall_deadline_seconds": SEARCH[
                "hard_fetch_deadline_seconds"
            ],
            "url_passed_over_stdin_not_argv": True,
            "helper_process_group_terminated_on_deadline": True,
        }
        or not isinstance(tasks, list)
        or len(tasks) != CONCURRENCY
        or not isinstance(summary, Mapping)
        or value.get("passed") is not summary.get("passed")
        or not isinstance(manifest, Mapping)
        or object_sha256(manifest) != value.get("source_manifest_sha256")
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != object_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.76 result identity drifted")
    for task in tasks:
        validate_task(task)
    expected = summarize(tasks, float(summary["batch_wall_seconds"]))
    if dict(summary) != expected:
        raise RuntimeError("V2.42.76 result summary drifted")
    if set(manifest) != set(SOURCE_FILES):
        raise RuntimeError("V2.42.76 source manifest membership drifted")
    for relative, digest in manifest.items():
        path = root / relative
        if path.is_symlink() or not path.is_file() or sha256(path) != digest:
            raise RuntimeError(f"V2.42.76 source drifted: {relative}")


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def run_probe(
    root: Path = ROOT,
    *,
    output: Path = OUTPUT,
    proxy_url: str = MODEL["proxy_url"],
) -> dict[str, Any]:
    root = root.resolve()
    if output.is_absolute() or ".." in output.parts:
        raise ValueError("V2.42.76 output must be repository-relative")
    with acquire_deepwide_api_lease(
        root,
        owner="v24276_hard_deadline_capacity_v1",
        purpose="neutral_nonbenchmark_hard_fetch_concurrency_8",
    ):
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=CONCURRENCY, thread_name_prefix="v24276-neutral-c8"
        ) as pool:
            tasks = list(
                pool.map(
                    lambda ordinal: _run_case(ordinal, proxy_url),
                    range(CONCURRENCY),
                )
            )
        batch_wall = max(0.0, time.monotonic() - started)
    summary = summarize(tasks, batch_wall)
    manifest = {relative: sha256(root / relative) for relative in SOURCE_FILES}
    value = {
        "artifact_version": 1,
        "role": "v24276_hard_deadline_capacity",
        "created_at_unix": int(time.time()),
        "probe_scope": "neutral_public_documentation_full_task_concurrency_8_hard_fetch_deadline",
        "provider": SEARCH["provider"],
        "model": MODEL["name"],
        "reasoning_effort": MODEL["reasoning_effort"],
        "concurrency": CONCURRENCY,
        "batch_wall_ceiling_seconds": BATCH_WALL_CEILING_SECONDS,
        "maximum_task_wall_seconds": MAXIMUM_TASK_WALL_SECONDS,
        "limits": dict(LIMITS),
        "two_wave_policy": dict(TWO_WAVE_POLICY),
        "hard_fetch_contract": {
            "per_url_total_wall_deadline_seconds": SEARCH[
                "hard_fetch_deadline_seconds"
            ],
            "url_passed_over_stdin_not_argv": True,
            "helper_process_group_terminated_on_deadline": True,
        },
        "tasks": tasks,
        "summary": summary,
        "source_manifest": manifest,
        "source_manifest_sha256": object_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "dev_benchmark_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "passed": summary["passed"],
    }
    value["result_payload_sha256"] = object_sha256(value)
    validate_result(value, root)
    _publish_new(root / output, value)
    return value


if __name__ == "__main__":
    result = run_probe()
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "sha256": sha256(ROOT / OUTPUT),
                "passed": result["passed"],
                "batch_wall_seconds": result["summary"]["batch_wall_seconds"],
                "task_wall_max_seconds": result["summary"]["task_wall_max_seconds"],
            },
            sort_keys=True,
        )
    )
