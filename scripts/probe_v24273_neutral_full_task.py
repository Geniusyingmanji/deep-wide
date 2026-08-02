#!/usr/bin/env python3
"""Run one neutral full V2.42.73 task and persist only content-free metrics."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections.abc import Mapping
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
    validate_runtime_retrieval,
    validate_v24273_result,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24257_score_first_smoke import sha256  # noqa: E402


OUTPUT = Path("results/v24273_neutral_full_task_probe_v1_20260802.json")
NEUTRAL_TASK = {
    "opaque_id": "task_" + "0" * 24,
    "question": (
        "Using official public Python documentation, return exactly one Markdown "
        "table with columns Feature, Python Version, and Status for three Python "
        "3.13 language or runtime features. Return only the Markdown table."
    ),
}
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
PROJECTION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "probe_scope",
        "provider",
        "model",
        "reasoning_effort",
        "wall_seconds",
        "completion_kind",
        "model_counters",
        "search_counters",
        "stage_seconds",
        "table_shape",
        "budget",
        "failure_types",
        "normalization",
        "two_wave_retrieval",
        "source_policy",
        "authorization",
        "result_payload_sha256",
    }
)


def _counter_snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    return {name: max(0, int(getattr(client, name, 0) or 0)) for name in names}


def _finite_nonnegative(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.73 neutral full probe {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.73 neutral full probe {label} is invalid")
    return number


def _content_free_projection(
    result: Mapping[str, Any],
    *,
    model_counters: Mapping[str, int],
    search_counters: Mapping[str, int],
    wall_seconds: float,
    now: int | None = None,
) -> dict[str, Any]:
    validate_v24273_result(result)
    telemetry = result["telemetry"]
    stages: dict[str, float] = {}
    for event in [*telemetry["model_events"], *telemetry["search_events"]]:
        stage = str(event["stage"])
        stages[stage] = round(
            stages.get(stage, 0.0) + float(event["elapsed_seconds"]), 6
        )
    failures = [str(item["type"]) for item in result["failures"]]
    normalization = result["normalization"]
    retrieval = result["two_wave_retrieval"]
    value = {
        "artifact_version": 1,
        "role": "v24273_neutral_full_task_probe",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "probe_scope": "neutral_public_documentation_full_task_latency_only",
        "provider": "azure-native-keyless-two-wave-cached",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "completion_kind": result["completion_kind"],
        "model_counters": dict(model_counters),
        "search_counters": dict(search_counters),
        "stage_seconds": stages,
        "table_shape": dict(telemetry["table"]),
        "budget": {
            "admitted_model_calls": result["budget"]["admitted_model_calls"],
            "admitted_search_queries": result["budget"]["admitted_search_queries"],
            "admitted_fetch_targets": result["budget"]["admitted_fetch_targets"],
            "elapsed_seconds": result["budget"]["elapsed_seconds"],
            "deadline_exceeded_at_return": result["budget"][
                "deadline_exceeded_at_return"
            ],
        },
        "failure_types": failures,
        "normalization": {
            "event_count": len(normalization["events"]),
            "statuses": [str(event["status"]) for event in normalization["events"]],
            "nonempty_factual_cell_rewritten": normalization[
                "nonempty_factual_cell_rewritten"
            ],
        },
        "two_wave_retrieval": retrieval,
        "source_policy": {
            "synthetic_opaque_id_used_but_not_persisted": True,
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_query_url_host_page_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired": True,
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
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    model = value.get("model_counters")
    search = value.get("search_counters")
    stages = value.get("stage_seconds")
    table = value.get("table_shape")
    budget = value.get("budget")
    normalization = value.get("normalization")
    retrieval = value.get("two_wave_retrieval")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    if (
        set(value) != PROJECTION_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24273_neutral_full_task_probe"
        or value.get("probe_scope")
        != "neutral_public_documentation_full_task_latency_only"
        or value.get("provider") != "azure-native-keyless-two-wave-cached"
        or value.get("model") != "gpt-5.6-sol"
        or value.get("reasoning_effort") != "low"
        or value.get("completion_kind")
        not in {
            "primary",
            "repaired",
            "normalized_primary",
            "normalized_repaired",
            "best_effort_fallback",
            "worker_failure_fallback",
            "hard_deadline_fallback",
        }
        or not isinstance(model, Mapping)
        or set(model) != set(MODEL_COUNTERS)
        or not isinstance(search, Mapping)
        or set(search) != set(SEARCH_COUNTERS)
        or any(
            isinstance(value_, bool) or not isinstance(value_, int) or value_ < 0
            for value_ in [*model.values(), *search.values()]
        )
        or not isinstance(stages, Mapping)
        or not set(stages).issubset({"plan", "search", "fetch", "synthesis", "repair"})
        or not isinstance(table, Mapping)
        or set(table)
        != {
            "row_count",
            "column_count",
            "cell_count",
            "unknown_cell_count",
            "unknown_cell_ratio",
        }
        or not isinstance(budget, Mapping)
        or set(budget)
        != {
            "admitted_model_calls",
            "admitted_search_queries",
            "admitted_fetch_targets",
            "elapsed_seconds",
            "deadline_exceeded_at_return",
        }
        or not isinstance(value.get("failure_types"), list)
        or any(not isinstance(item, str) or len(item) > 128 for item in value["failure_types"])
        or not isinstance(normalization, Mapping)
        or set(normalization)
        != {"event_count", "statuses", "nonempty_factual_cell_rewritten"}
        or normalization.get("nonempty_factual_cell_rewritten") is not False
        or not isinstance(retrieval, Mapping)
        or not isinstance(source, Mapping)
        or source.get("synthetic_opaque_id_used_but_not_persisted") is not True
        or source.get("benchmark_manifest_mapping_gold_prediction_or_evaluator_read")
        is not False
        or source.get("question_query_url_host_page_prediction_answer_or_hash_persisted")
        is not False
        or source.get("credential_value_read_persisted_hashed_or_emitted") is not False
        or source.get("official_evaluator_called") is not False
        or source.get("shared_api_lease_acquired") is not True
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != object_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.73 neutral full-task projection drifted")
    validate_runtime_retrieval(retrieval)
    _finite_nonnegative(value.get("wall_seconds"), label="wall seconds")
    for name, amount in stages.items():
        _finite_nonnegative(amount, label=f"stage {name}")
    _finite_nonnegative(budget["elapsed_seconds"], label="budget elapsed")
    if (
        budget["admitted_model_calls"] != model["requests"]
        or search["fetch_calls"] != retrieval["observed_inner_fetch_calls"]
        or budget["admitted_fetch_targets"]
        != retrieval.get("cache_requested_source_count", 0)
        or budget["admitted_search_queries"] > 4
        or search["fetch_calls"] > 10
    ):
        raise RuntimeError("V2.42.73 neutral full-task accounting drifted")


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


def run_probe(
    root: Path = ROOT,
    *,
    output: Path = OUTPUT,
    proxy_url: str = "http://127.0.0.1:9878/responses",
) -> dict[str, Any]:
    root = root.resolve()
    if output.is_absolute() or ".." in output.parts:
        raise ValueError("V2.42.73 probe output must be repository-relative")
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
    limits = ScoreFirstLimits(
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
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        root,
        owner="v24273_neutral_full_task_probe_v1",
        purpose="neutral_nonbenchmark_full_task_latency_probe",
    ):
        result = run_v24273_task(
            NEUTRAL_TASK,
            model=model,
            search=search,
            limits=limits,
        )
    projection = _content_free_projection(
        result,
        model_counters=_counter_snapshot(model, MODEL_COUNTERS),
        search_counters=_counter_snapshot(search, SEARCH_COUNTERS),
        wall_seconds=max(0.0, time.monotonic() - started),
    )
    _publish_new(root / output, projection)
    return projection


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--proxy-url", default="http://127.0.0.1:9878/responses")
    args = parser.parse_args()
    result = run_probe(Path(args.root), output=Path(args.output), proxy_url=args.proxy_url)
    print(
        json.dumps(
            {
                "path": str(args.output),
                "sha256": sha256(Path(args.root).resolve() / args.output),
                "wall_seconds": result["wall_seconds"],
                "completion_kind": result["completion_kind"],
                "decision": result["two_wave_retrieval"].get("receipt", {})
                .get("controller", {})
                .get("decision"),
            },
            sort_keys=True,
        )
    )
