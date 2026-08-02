#!/usr/bin/env python3
"""Neutral 1->2->4 concurrency staircase for the V2.42.73 full task chain."""

from __future__ import annotations

import argparse
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
from deepwide_agent.native_search import AzureNativeSearchClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import object_sha256  # noqa: E402
from deepwide_agent.v24273_two_wave_task_runtime import (  # noqa: E402
    run_v24273_task,
    validate_v24273_result,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24257_score_first_smoke import sha256  # noqa: E402


OUTPUT = Path("results/v24273_neutral_capacity_staircase_v1_20260802.json")
LEVELS = (1, 2, 4)
LEVEL_BATCH_WALL_CEILINGS = {1: 35.0, 2: 45.0, 4: 70.0}
MAXIMUM_TASK_WALL_SECONDS = 35.0
MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)
NEUTRAL_QUESTIONS = (
    (
        "Using official public Python documentation, return exactly one Markdown "
        "table with columns Feature, Python Version, and Status for three Python "
        "3.13 language or runtime features. Return only the Markdown table."
    ),
    (
        "Using official public PostgreSQL documentation, return exactly one Markdown "
        "table with columns Feature, PostgreSQL Version, and Status for three "
        "PostgreSQL 17 features. Return only the Markdown table."
    ),
    (
        "Using official public Rust documentation, return exactly one Markdown table "
        "with columns Feature, Rust Version, and Status for three Rust 1.80 language "
        "or toolchain features. Return only the Markdown table."
    ),
    (
        "Using official public Node.js documentation, return exactly one Markdown "
        "table with columns Feature, Node.js Version, and Status for three Node.js 22 "
        "runtime features. Return only the Markdown table."
    ),
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
        "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
)
LEVEL_KEYS = frozenset(
    {
        "level",
        "selected",
        "batch_wall_seconds",
        "batch_wall_ceiling_seconds",
        "maximum_task_wall_seconds",
        "tasks",
        "terminal",
        "model_generated",
        "fallback",
        "failure_count",
        "model_requests",
        "model_attempts",
        "model_retry_count",
        "search_calls",
        "raw_recovered_or_unrecovered_search_failures",
        "fetch_calls",
        "fetch_failures",
        "system_tokens",
        "task_wall_sum_seconds",
        "task_wall_mean_seconds",
        "task_wall_max_seconds",
        "stage_seconds_sum",
        "controller_decisions",
        "controller_reasons",
        "checks",
        "passed",
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
        "levels_requested",
        "level_batch_wall_ceilings_seconds",
        "maximum_task_wall_seconds",
        "stop_on_first_failed_level",
        "levels",
        "highest_passing_concurrency",
        "all_requested_levels_passed",
        "source_policy",
        "authorization",
        "result_payload_sha256",
    }
)


def _counter_snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    return {name: max(0, int(getattr(client, name, 0) or 0)) for name in names}


def _finite_nonnegative(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.73 capacity {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.73 capacity {label} is invalid")
    return number


def _new_client_pair(proxy_url: str) -> tuple[ResponsesClient, AzureNativeSearchClient]:
    model = ResponsesClient(
        proxy_url,
        "gpt-5.6-sol",
        reasoning_effort="low",
        service_tier="priority",
        timeout=180,
        max_retries=2,
    )
    search = AzureNativeSearchClient(
        proxy_url,
        "gpt-5.6-sol",
        reasoning_effort="low",
        service_tier="priority",
        timeout=180,
        max_retries=2,
        max_workers=1,
        batch_size=8,
        search_context_size="medium",
        max_output_tokens=7_000,
        fetch_pages=False,
        fetch_workers=8,
        fetch_timeout=20,
        max_page_chars=5_000,
    )
    return model, search


def _limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=2_000,
        synthesis_output_tokens=6_000,
        repair_output_tokens=4_000,
    )


def _stage_seconds(result: Mapping[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    telemetry = result["telemetry"]
    for event in [*telemetry["model_events"], *telemetry["search_events"]]:
        stage = str(event["stage"])
        values[stage] = round(
            values.get(stage, 0.0) + float(event["elapsed_seconds"]), 6
        )
    return values


def _run_case(
    *, level: int, ordinal: int, proxy_url: str
) -> dict[str, Any]:
    model, search = _new_client_pair(proxy_url)
    started = time.monotonic()
    try:
        synthetic = f"{level:02x}{ordinal:02x}".ljust(24, "0")
        result = run_v24273_task(
            {
                "opaque_id": "task_" + synthetic,
                "question": NEUTRAL_QUESTIONS[ordinal],
            },
            model=model,
            search=search,
            limits=_limits(),
        )
        wall = round(max(0.0, time.monotonic() - started), 6)
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
            "wall_seconds": wall,
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
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        }
    except Exception as exc:  # noqa: BLE001 - content-free terminal capacity outcome
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
        or not isinstance(value.get("ordinal"), int)
        or isinstance(value.get("ordinal"), bool)
        or value["ordinal"] <= 0
        or value.get("terminal") is not True
        or not isinstance(value.get("failure_types"), list)
        or any(not isinstance(item, str) or len(item) > 128 for item in value["failure_types"])
        or not isinstance(model, Mapping)
        or set(model) != set(MODEL_COUNTERS)
        or not isinstance(search, Mapping)
        or set(search) != set(SEARCH_COUNTERS)
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for number in [*model.values(), *search.values()]
        )
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
        raise RuntimeError("V2.42.73 capacity task outcome drifted")
    _finite_nonnegative(value.get("wall_seconds"), label="task wall")
    for name, amount in stages.items():
        _finite_nonnegative(amount, label=f"stage {name}")
    for name in (
        "queries_executed",
        "fetches_attempted",
        "usable_pages",
        "unrecoverable_search_failures",
        "cache_miss_count",
        "cache_serve_network_fetches",
    ):
        amount = value.get(name)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise RuntimeError("V2.42.73 capacity task counter drifted")
    failure_type = value.get("failure_type")
    if failure_type is not None and (
        not isinstance(failure_type, str) or not failure_type or len(failure_type) > 128
    ):
        raise RuntimeError("V2.42.73 capacity failure type drifted")


def summarize_level(
    *, level: int, tasks: Sequence[Mapping[str, Any]], batch_wall_seconds: float
) -> dict[str, Any]:
    if level not in LEVEL_BATCH_WALL_CEILINGS or len(tasks) != level:
        raise RuntimeError("V2.42.73 capacity level shape drifted")
    values = [dict(task) for task in tasks]
    for task in values:
        validate_task(task)
    terminal = sum(task["terminal"] is True for task in values)
    model_generated = sum(task["completion_kind"] in MODEL_GENERATED for task in values)
    fallback = level - model_generated
    failure_count = sum(
        bool(task["failure_type"])
        or bool(task["failure_types"])
        or task["retrieval_status"] != "completed"
        for task in values
    )
    model_requests = sum(task["model_counters"]["requests"] for task in values)
    model_attempts = sum(task["model_counters"]["attempts"] for task in values)
    search_calls = sum(task["search_counters"]["calls"] for task in values)
    raw_search_failures = sum(task["search_counters"]["failures"] for task in values)
    fetch_calls = sum(task["search_counters"]["fetch_calls"] for task in values)
    fetch_failures = sum(task["search_counters"]["fetch_failures"] for task in values)
    system_tokens = sum(
        task["model_counters"]["total_tokens"]
        + task["search_counters"]["total_tokens"]
        for task in values
    )
    task_walls = [float(task["wall_seconds"]) for task in values]
    stage_sum: dict[str, float] = {}
    decisions = {"stop": 0, "expand": 0, "absent": 0}
    reasons: dict[str, int] = {}
    for task in values:
        for stage, seconds in task["stage_seconds"].items():
            stage_sum[stage] = round(stage_sum.get(stage, 0.0) + float(seconds), 6)
        decision = task["controller_decision"]
        decisions[decision if decision in {"stop", "expand"} else "absent"] += 1
        reason = str(task["controller_reason"] or "absent")
        reasons[reason] = reasons.get(reason, 0) + 1
    checks = {
        "exact_terminal": terminal == level,
        "all_model_generated": model_generated == level,
        "no_forward_or_retrieval_failures": failure_count == 0,
        "no_model_retries": model_attempts == model_requests,
        "no_fetch_failures": fetch_failures == 0,
        "no_unrecoverable_search_failures": sum(
            task["unrecoverable_search_failures"] for task in values
        )
        == 0,
        "no_cache_misses": sum(task["cache_miss_count"] for task in values) == 0,
        "cache_serve_has_no_network_fetch": sum(
            task["cache_serve_network_fetches"] for task in values
        )
        == 0,
        "maximum_task_wall": max(task_walls) <= MAXIMUM_TASK_WALL_SECONDS,
        "batch_wall": float(batch_wall_seconds) <= LEVEL_BATCH_WALL_CEILINGS[level],
    }
    value = {
        "level": level,
        "selected": level,
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "batch_wall_ceiling_seconds": LEVEL_BATCH_WALL_CEILINGS[level],
        "maximum_task_wall_seconds": MAXIMUM_TASK_WALL_SECONDS,
        "tasks": values,
        "terminal": terminal,
        "model_generated": model_generated,
        "fallback": fallback,
        "failure_count": failure_count,
        "model_requests": model_requests,
        "model_attempts": model_attempts,
        "model_retry_count": max(0, model_attempts - model_requests),
        "search_calls": search_calls,
        "raw_recovered_or_unrecovered_search_failures": raw_search_failures,
        "fetch_calls": fetch_calls,
        "fetch_failures": fetch_failures,
        "system_tokens": system_tokens,
        "task_wall_sum_seconds": round(sum(task_walls), 6),
        "task_wall_mean_seconds": round(sum(task_walls) / level, 6),
        "task_wall_max_seconds": round(max(task_walls), 6),
        "stage_seconds_sum": stage_sum,
        "controller_decisions": decisions,
        "controller_reasons": reasons,
        "checks": checks,
        "passed": all(checks.values()),
    }
    validate_level(value)
    return value


def validate_level(value: Mapping[str, Any]) -> None:
    tasks = value.get("tasks")
    checks = value.get("checks")
    if (
        set(value) != LEVEL_KEYS
        or value.get("level") not in LEVELS
        or value.get("selected") != value.get("level")
        or not isinstance(tasks, list)
        or len(tasks) != value.get("level")
        or not isinstance(checks, Mapping)
        or set(checks)
        != {
            "exact_terminal",
            "all_model_generated",
            "no_forward_or_retrieval_failures",
            "no_model_retries",
            "no_fetch_failures",
            "no_unrecoverable_search_failures",
            "no_cache_misses",
            "cache_serve_has_no_network_fetch",
            "maximum_task_wall",
            "batch_wall",
        }
        or any(not isinstance(flag, bool) for flag in checks.values())
        or value.get("passed") is not all(checks.values())
    ):
        raise RuntimeError("V2.42.73 capacity level receipt drifted")
    for task in tasks:
        validate_task(task)
    for name in (
        "batch_wall_seconds",
        "batch_wall_ceiling_seconds",
        "maximum_task_wall_seconds",
        "task_wall_sum_seconds",
        "task_wall_mean_seconds",
        "task_wall_max_seconds",
    ):
        _finite_nonnegative(value.get(name), label=f"level {name}")


def validate_result(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    levels = value.get("levels")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24273_neutral_capacity_staircase"
        or value.get("probe_scope")
        != "neutral_public_documentation_full_task_concurrency_capacity_only"
        or value.get("provider") != "azure-native-keyless-two-wave-cached"
        or value.get("model") != "gpt-5.6-sol"
        or value.get("reasoning_effort") != "low"
        or value.get("levels_requested") != list(LEVELS)
        or value.get("level_batch_wall_ceilings_seconds")
        != {str(level): LEVEL_BATCH_WALL_CEILINGS[level] for level in LEVELS}
        or value.get("maximum_task_wall_seconds") != MAXIMUM_TASK_WALL_SECONDS
        or value.get("stop_on_first_failed_level") is not True
        or not isinstance(levels, list)
        or not 1 <= len(levels) <= len(LEVELS)
        or [level.get("level") for level in levels] != list(LEVELS[: len(levels)])
        or not isinstance(source, Mapping)
        or source.get("benchmark_manifest_mapping_gold_prediction_or_evaluator_read")
        is not False
        or source.get(
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted"
        )
        is not False
        or source.get("credential_value_read_persisted_hashed_or_emitted") is not False
        or source.get("official_evaluator_called") is not False
        or source.get("shared_api_lease_acquired_once_for_staircase") is not True
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != object_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.73 capacity staircase identity drifted")
    for level in levels:
        validate_level(level)
    first_failure = next((index for index, level in enumerate(levels) if not level["passed"]), None)
    if first_failure is not None and first_failure != len(levels) - 1:
        raise RuntimeError("V2.42.73 capacity staircase continued after failure")
    passing = [level["level"] for level in levels if level["passed"]]
    highest = max(passing) if passing else 0
    if (
        value.get("highest_passing_concurrency") != highest
        or value.get("all_requested_levels_passed")
        is not (len(levels) == len(LEVELS) and all(level["passed"] for level in levels))
    ):
        raise RuntimeError("V2.42.73 capacity staircase aggregate drifted")


def _publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def run_staircase(
    root: Path = ROOT,
    *,
    output: Path = OUTPUT,
    proxy_url: str = "http://127.0.0.1:9878/responses",
) -> dict[str, Any]:
    root = root.resolve()
    if output.is_absolute() or ".." in output.parts:
        raise ValueError("V2.42.73 capacity output must be repository-relative")
    summaries: list[dict[str, Any]] = []
    with acquire_deepwide_api_lease(
        root,
        owner="v24273_neutral_capacity_staircase_v1",
        purpose="neutral_nonbenchmark_full_task_concurrency_staircase",
    ):
        for level in LEVELS:
            started = time.monotonic()
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=level, thread_name_prefix=f"v24273-neutral-c{level}"
            ) as pool:
                futures = [
                    pool.submit(
                        _run_case, level=level, ordinal=ordinal, proxy_url=proxy_url
                    )
                    for ordinal in range(level)
                ]
                tasks = [future.result() for future in futures]
            summary = summarize_level(
                level=level,
                tasks=tasks,
                batch_wall_seconds=max(0.0, time.monotonic() - started),
            )
            summaries.append(summary)
            if not summary["passed"]:
                break
    passing = [level["level"] for level in summaries if level["passed"]]
    value = {
        "artifact_version": 1,
        "role": "v24273_neutral_capacity_staircase",
        "created_at_unix": int(time.time()),
        "probe_scope": "neutral_public_documentation_full_task_concurrency_capacity_only",
        "provider": "azure-native-keyless-two-wave-cached",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "levels_requested": list(LEVELS),
        "level_batch_wall_ceilings_seconds": {
            str(level): LEVEL_BATCH_WALL_CEILINGS[level] for level in LEVELS
        },
        "maximum_task_wall_seconds": MAXIMUM_TASK_WALL_SECONDS,
        "stop_on_first_failed_level": True,
        "levels": summaries,
        "highest_passing_concurrency": max(passing) if passing else 0,
        "all_requested_levels_passed": len(summaries) == len(LEVELS)
        and all(level["passed"] for level in summaries),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired_once_for_staircase": True,
        },
        "authorization": {
            "dev_benchmark_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission": False,
            "sota_claim": False,
            "training_credit_assignment": False,
        },
    }
    value["result_payload_sha256"] = object_sha256(value)
    validate_result(value)
    _publish_new(root / output, value)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--proxy-url", default="http://127.0.0.1:9878/responses")
    args = parser.parse_args()
    result = run_staircase(
        Path(args.root), output=Path(args.output), proxy_url=args.proxy_url
    )
    print(
        json.dumps(
            {
                "path": str(args.output),
                "sha256": sha256(Path(args.root).resolve() / args.output),
                "highest_passing_concurrency": result[
                    "highest_passing_concurrency"
                ],
                "all_requested_levels_passed": result[
                    "all_requested_levels_passed"
                ],
            },
            sort_keys=True,
        )
    )
