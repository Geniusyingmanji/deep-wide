#!/usr/bin/env python3
"""Run one neutral public-documentation probe of V2.42.90 rescue.

The probe publishes count/timing/table-shape receipts only.  It does not open
the benchmark manifest, mapping, predictions, gold data, or evaluator.  The
synthetic visible question, generated queries, URLs, pages, and answer are not
persisted or hashed in the result.
"""

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
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.native_search import AzureNativeSearchClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import object_sha256  # noqa: E402
from deepwide_agent.v24289_low_coverage_rescue import validate_receipt as validate_rescue_receipt  # noqa: E402
from deepwide_agent.v24290_low_coverage_task_runtime import (  # noqa: E402
    run_v24290_task,
    validate_v24290_result,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


OUTPUT = Path("results/v24290_neutral_low_coverage_probe_v1_20260803.json")
NEUTRAL_TASK = {
    "opaque_id": "task_" + "0" * 24,
    "question": (
        "Using only official public Python documentation, return exactly one "
        "Markdown table of six Python 3.13 language or runtime changes. The "
        "column names are: Feature, Python Version, Status, Official Module, "
        "and Documentation Section. Return only the table."
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


class FirstWaveSourceMissInjection:
    """Execute the real first search but expose no first-wave source leads."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.search_invocations = 0
        self.first_wave_real_provider_call_executed = False
        self.first_wave_source_batches_masked = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def search_many(self, queries: Any, **kwargs: Any) -> Any:
        value = self.inner.search_many(queries, **kwargs)
        self.search_invocations += 1
        if self.search_invocations == 1:
            self.first_wave_real_provider_call_executed = True
            self.first_wave_source_batches_masked = len(value) if isinstance(value, list) else 0
            return []
        return value

    def fetch_urls(self, requests_: Any) -> Any:
        return self.inner.fetch_urls(requests_)


def _counters(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    return {name: max(0, int(getattr(client, name, 0) or 0)) for name in names}


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.90 neutral {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.90 neutral {label} is invalid")
    return number


def project(
    result: Mapping[str, Any],
    *,
    model_counters: Mapping[str, int],
    search_counters: Mapping[str, int],
    wall_seconds: float,
    now: int | None = None,
) -> dict[str, Any]:
    validate_v24290_result(result)
    runtime_retrieval = result["two_wave_retrieval"]
    receipt = runtime_retrieval["receipt"]
    validate_rescue_receipt(receipt)
    rescue = receipt["rescue"]
    before = receipt["total_before_rescue"]
    total = receipt["total"]
    value = {
        "artifact_version": 1,
        "role": "v24290_neutral_low_coverage_probe",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "probe_scope": "neutral_public_documentation_low_coverage_rescue_only",
        "provider": "azure-native-keyless-same-response-tail-rescue",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "completion_kind": result["completion_kind"],
        "model_counters": dict(model_counters),
        "search_counters": dict(search_counters),
        "fault_injection": {
            "kind": "first_wave_visible_source_miss_after_real_provider_call",
            "first_wave_real_provider_call_executed": True,
            "first_wave_source_batches_masked_in_memory": True,
            "second_wave_and_tail_source_urls_unmodified": True,
            "question_query_url_host_page_or_provider_payload_persisted": False,
            "claim_scope": "mechanism_robustness_not_natural_frequency_or_benchmark_quality",
        },
        "controller": {
            "decision": receipt["controller"]["decision"],
            "reason": receipt["controller"]["reason"],
            "search_invocations_before_rescue": receipt["controller_search_invocations_before_rescue"],
            "search_invocations_after_rescue": receipt["controller_search_invocations_after_rescue"],
            "provider_search_calls_before_rescue": receipt["provider_search_calls_before_rescue"],
            "provider_search_calls_after_rescue": receipt["provider_search_calls_after_rescue"],
            "hosted_search_requests_added_by_rescue": receipt["hosted_search_requests_added_by_rescue"],
        },
        "coverage": {
            "queries_executed": total["queries_executed"],
            "fetches_before_rescue": before["fetches_attempted"],
            "usable_pages_before_rescue": before["usable_pages"],
            "unique_hosts_before_rescue": before["unique_hosts"],
            "content_chars_before_rescue": before["content_chars"],
            "rescue_triggered": rescue["triggered"],
            "rescue_reason": rescue["reason"],
            "rescue_tail_candidates": rescue["tail_candidates"],
            "rescue_fetches": rescue["fetches_attempted"],
            "rescue_usable_pages": rescue["usable_pages"],
            "fetches_after_rescue": total["fetches_attempted"],
            "usable_pages_after_rescue": total["usable_pages"],
            "unique_hosts_after_rescue": total["unique_hosts"],
            "content_chars_after_rescue": total["content_chars"],
        },
        "runtime_health": {
            "cache_miss_count": runtime_retrieval["cache_miss_count"],
            "network_fetches_during_cache_serve": runtime_retrieval["network_fetches_during_cache_serve"],
            "provider_fetch_calls_match_receipt": search_counters["fetch_calls"] == total["fetches_attempted"],
        },
        "table_shape": dict(result["telemetry"]["table"]),
        "attributed_timing": dict(result["attributed_timing"]),
        "budget": {
            "admitted_model_calls": result["budget"]["admitted_model_calls"],
            "admitted_search_queries": result["budget"]["admitted_search_queries"],
            "admitted_fetch_targets": result["budget"]["admitted_fetch_targets"],
            "elapsed_seconds": result["budget"]["elapsed_seconds"],
            "deadline_exceeded_at_return": result["budget"]["deadline_exceeded_at_return"],
        },
        "source_policy": {
            "synthetic_opaque_id_used_but_not_persisted": True,
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_field_query_url_host_page_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired": True,
        },
        "authorization": {
            "dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
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
    injection = value.get("fault_injection")
    controller = value.get("controller")
    coverage = value.get("coverage")
    health = value.get("runtime_health")
    table = value.get("table_shape")
    budget = value.get("budget")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24290_neutral_low_coverage_probe"
        or value.get("probe_scope") != "neutral_public_documentation_low_coverage_rescue_only"
        or value.get("provider") != "azure-native-keyless-same-response-tail-rescue"
        or value.get("model") != "gpt-5.6-sol"
        or value.get("reasoning_effort") != "low"
        or value.get("completion_kind") not in {"primary", "normalized_primary", "repaired", "normalized_repaired", "best_effort_fallback"}
        or not isinstance(model, Mapping)
        or set(model) != set(MODEL_COUNTERS)
        or not isinstance(search, Mapping)
        or set(search) != set(SEARCH_COUNTERS)
        or any(isinstance(number, bool) or not isinstance(number, int) or number < 0 for number in [*model.values(), *search.values()])
        or not isinstance(injection, Mapping)
        or injection
        != {
            "kind": "first_wave_visible_source_miss_after_real_provider_call",
            "first_wave_real_provider_call_executed": True,
            "first_wave_source_batches_masked_in_memory": True,
            "second_wave_and_tail_source_urls_unmodified": True,
            "question_query_url_host_page_or_provider_payload_persisted": False,
            "claim_scope": "mechanism_robustness_not_natural_frequency_or_benchmark_quality",
        }
        or not isinstance(controller, Mapping)
        or set(controller) != {
            "decision", "reason", "search_invocations_before_rescue", "search_invocations_after_rescue",
            "provider_search_calls_before_rescue", "provider_search_calls_after_rescue", "hosted_search_requests_added_by_rescue",
        }
        or not isinstance(coverage, Mapping)
        or not isinstance(health, Mapping)
        or not isinstance(table, Mapping)
        or not isinstance(budget, Mapping)
        or not isinstance(source, Mapping)
        or source.get("synthetic_opaque_id_used_but_not_persisted") is not True
        or source.get("shared_api_lease_acquired") is not True
        or any(value_ for key, value_ in source.items() if key not in {"synthetic_opaque_id_used_but_not_persisted", "shared_api_lease_acquired"})
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != object_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.90 neutral projection drifted")
    _finite(value.get("wall_seconds"), label="wall seconds")
    _finite(budget.get("elapsed_seconds"), label="task wall seconds")
    if (
        controller["search_invocations_before_rescue"] != controller["search_invocations_after_rescue"]
        or controller["provider_search_calls_before_rescue"] != controller["provider_search_calls_after_rescue"]
        or controller["hosted_search_requests_added_by_rescue"] != 0
        or coverage["fetches_after_rescue"] > 10
        or coverage["usable_pages_after_rescue"] < coverage["usable_pages_before_rescue"]
        or coverage["content_chars_after_rescue"] < coverage["content_chars_before_rescue"]
        or health.get("cache_miss_count") != 0
        or health.get("network_fetches_during_cache_serve") != 0
        or health.get("provider_fetch_calls_match_receipt") is not True
        or budget["admitted_fetch_targets"] != coverage["usable_pages_after_rescue"]
        or search["fetch_calls"] != coverage["fetches_after_rescue"]
    ):
        raise RuntimeError("V2.42.90 neutral effect accounting drifted")


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def run_probe(
    root: Path = ROOT,
    *,
    output: Path = OUTPUT,
    proxy_url: str = "http://127.0.0.1:9878/responses",
) -> dict[str, Any]:
    root = root.resolve()
    if output.is_absolute() or ".." in output.parts:
        raise ValueError("V2.42.90 probe output must be repository-relative")
    model = ResponsesClient(
        proxy_url,
        "gpt-5.6-sol",
        reasoning_effort="low",
        service_tier="priority",
        timeout=180,
        max_retries=2,
    )
    raw_search = AzureNativeSearchClient(
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
    search = FirstWaveSourceMissInjection(raw_search)
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
        owner="v24290_neutral_low_coverage_probe_v1",
        purpose="neutral_public_documentation_low_coverage_tail_rescue",
    ):
        result = run_v24290_task(
            NEUTRAL_TASK,
            model=model,
            search=search,
            limits=limits,
        )
    if (
        search.first_wave_real_provider_call_executed is not True
        or search.first_wave_source_batches_masked < 0
    ):
        raise RuntimeError("V2.42.90 neutral fault injection did not execute")
    projection = project(
        result,
        model_counters=_counters(model, MODEL_COUNTERS),
        search_counters=_counters(search, SEARCH_COUNTERS),
        wall_seconds=max(0.0, time.monotonic() - started),
    )
    _publish_new(root / output, projection)
    return projection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--proxy-url", default="http://127.0.0.1:9878/responses")
    args = parser.parse_args()
    value = run_probe(Path(args.root), output=Path(args.output), proxy_url=args.proxy_url)
    print(json.dumps({"path": args.output, "wall_seconds": value["wall_seconds"], "rescue_triggered": value["coverage"]["rescue_triggered"]}, sort_keys=True))


if __name__ == "__main__":
    main()
