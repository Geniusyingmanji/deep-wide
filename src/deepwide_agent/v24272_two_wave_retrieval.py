"""Bounded two-wave retrieval adapter for the V2.42.72 build-only kernel.

The adapter is label-blind and receives planned query text produced from the
visible question in the same forward pass.  It executes a small first wave,
derives content-free evidence-yield observations, invokes the pure entropy/VOC
kernel, and conditionally executes one delta-only second wave.  Search
narratives and snippets are never active evidence; only deterministically
fetched public-page text is returned to the caller.

This module does not synthesize a benchmark answer, read evaluator resources,
or authorize a benchmark launch.  Its persisted receipt contains counts,
timings, hashes of other content-free receipts, and the controller decision --
never query strings, URLs, hosts, page text, task IDs, predictions, or scores.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url
from .v24257_score_first_runtime import _lead_requests, _normalize_text
from .v24269_task_union_discovery import validate_receipt as validate_discovery_receipt
from .v24270_budget_equivalent_union import (
    BudgetEquivalentTaskUnionSearchClient,
    payload_sha256,
    validate_receipt as validate_budget_receipt,
)
from .v24272_two_wave_entropy_voc import (
    FirstWaveObservation,
    POLICY_ID as CONTROLLER_POLICY_ID,
    TwoWavePolicy,
    decide_two_wave,
    object_sha256,
    validate_receipt as validate_controller_receipt,
)


POLICY_ID = "v24272_label_blind_two_wave_retrieval_build_only_v1"
RECEIPT_ROLE = "v24272_two_wave_retrieval_receipt"
WAVE_KEYS = frozenset(
    {
        "executed",
        "queries_executed",
        "sources_discovered",
        "fetches_attempted",
        "usable_pages",
        "novel_pages",
        "new_unique_hosts",
        "content_chars",
        "search_seconds",
        "fetch_seconds",
        "unrecoverable_search_failures",
    }
)
TOTAL_KEYS = frozenset(
    {
        "queries_executed",
        "sources_discovered",
        "fetches_attempted",
        "usable_pages",
        "novel_pages",
        "unique_hosts",
        "content_chars",
        "search_seconds",
        "fetch_seconds",
        "unrecoverable_search_failures",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "controller_policy_id",
        "label_blind",
        "planned_query_count",
        "required_column_count",
        "explicit_row_target",
        "search_results_per_query",
        "wave1",
        "controller",
        "wave2",
        "total",
        "budget_equivalence",
        "discovery_union",
        "delta_only_second_wave",
        "provider_narrative_or_snippet_forwarded",
        "fetched_page_text_is_only_active_evidence",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _nonnegative_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.72 retrieval {label} is not a nonnegative integer")
    return value


def _nonnegative_number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.72 retrieval {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"V2.42.72 retrieval {label} is invalid")
    return number


def _elapsed(started: float, monotonic: Callable[[], float]) -> float:
    return round(max(0.0, float(monotonic()) - float(started)), 6)


def _queries(values: Sequence[str]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, str):
            raise ValueError("V2.42.72 planned query is not text")
        query = _normalize_text(raw)
        folded = query.casefold()
        if query and folded not in seen:
            queries.append(query)
            seen.add(folded)
    if not queries:
        raise ValueError("V2.42.72 requires at least one visible-plan query")
    return queries


def _results(batches: object) -> list[Mapping[str, Any]]:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return []
    values: list[Mapping[str, Any]] = []
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        values.extend(
            result
            for result in (batch.get("results") or [])
            if isinstance(result, Mapping)
        )
    return values


def _page_text(value: Mapping[str, Any]) -> str:
    return str(value.get("raw_content") or value.get("content") or "").replace(
        "\x00", ""
    ).strip()


def _content_fingerprint(text: str) -> str:
    normalized = re.sub(r"\s+", " ", str(text)).strip().casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _wave_stats(
    *,
    executed: bool,
    query_count: int,
    leads: Sequence[Mapping[str, Any]],
    pages: object,
    search_seconds: float,
    fetch_seconds: float,
    failure_count: int,
    prior_fingerprints: set[str],
    prior_hosts: set[str],
) -> tuple[dict[str, Any], set[str], set[str]]:
    page_values = _results(pages)
    usable = [value for value in page_values if _page_text(value)]
    fingerprints = set(prior_fingerprints)
    hosts = set(prior_hosts)
    novel = 0
    new_hosts = 0
    characters = 0
    for value in usable:
        text = _page_text(value)
        characters += len(text)
        fingerprint = _content_fingerprint(text)
        if fingerprint not in fingerprints:
            fingerprints.add(fingerprint)
            novel += 1
        url = canonicalize_url(str(value.get("url", "")))
        host = (urlsplit(url).hostname or "").casefold() if url else ""
        if host and host not in hosts:
            hosts.add(host)
            new_hosts += 1
    value = {
        "executed": bool(executed),
        "queries_executed": int(query_count),
        "sources_discovered": len(leads),
        "fetches_attempted": len(leads),
        "usable_pages": len(usable),
        "novel_pages": novel,
        "new_unique_hosts": new_hosts,
        "content_chars": characters,
        "search_seconds": round(max(0.0, float(search_seconds)), 6),
        "fetch_seconds": round(max(0.0, float(fetch_seconds)), 6),
        "unrecoverable_search_failures": max(0, int(failure_count)),
    }
    _validate_wave(value)
    return value, fingerprints, hosts


def _validate_wave(value: Mapping[str, Any]) -> None:
    if set(value) != WAVE_KEYS or not isinstance(value.get("executed"), bool):
        raise ValueError("V2.42.72 retrieval wave schema drifted")
    for name in WAVE_KEYS - {"executed", "search_seconds", "fetch_seconds"}:
        _nonnegative_integer(value.get(name), label=f"wave {name}")
    for name in ("search_seconds", "fetch_seconds"):
        _nonnegative_number(value.get(name), label=f"wave {name}")
    if (
        value["usable_pages"] > value["fetches_attempted"]
        or value["novel_pages"] > value["usable_pages"]
        or value["new_unique_hosts"] > value["usable_pages"]
        or value["unrecoverable_search_failures"] > value["queries_executed"]
    ):
        raise ValueError("V2.42.72 retrieval wave accounting drifted")
    if not value["executed"] and any(
        value[name]
        for name in WAVE_KEYS - {"executed", "search_seconds", "fetch_seconds"}
    ):
        raise ValueError("V2.42.72 nonexecuted wave has effects")
    if not value["executed"] and (
        value["search_seconds"] or value["fetch_seconds"]
    ):
        raise ValueError("V2.42.72 nonexecuted wave has latency")


def _effective_policy(
    policy: TwoWavePolicy,
    *,
    first_queries: int,
    second_queries: int,
    max_results: int,
) -> TwoWavePolicy:
    wave1_fetches = min(policy.wave1_fetches, first_queries * max_results)
    wave2_fetches = min(policy.wave2_fetches, second_queries * max_results)
    if wave1_fetches <= 0:
        raise ValueError("V2.42.72 first wave has no fetch capacity")
    return dataclasses.replace(
        policy,
        wave1_queries=first_queries,
        wave1_fetches=wave1_fetches,
        wave2_queries=second_queries,
        wave2_fetches=wave2_fetches,
        minimum_usable_pages=min(policy.minimum_usable_pages, wave1_fetches),
        minimum_novel_pages=min(
            policy.minimum_novel_pages,
            policy.minimum_usable_pages,
            wave1_fetches,
        ),
        minimum_unique_hosts=min(policy.minimum_unique_hosts, wave1_fetches),
    )


def run_two_wave_retrieval(
    queries: Sequence[str],
    *,
    search: Any,
    required_column_count: int,
    explicit_row_target: int = 0,
    search_results_per_query: int = 3,
    policy: TwoWavePolicy | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Execute at most two retrieval waves and return raw pages plus a receipt."""

    planned = _queries(queries)
    columns = _nonnegative_integer(required_column_count, label="column count")
    if columns <= 0:
        raise ValueError("V2.42.72 required column count must be positive")
    row_target = _nonnegative_integer(explicit_row_target, label="row target")
    top_k = _nonnegative_integer(
        search_results_per_query, label="results per query"
    )
    if not 1 <= top_k <= 6:
        raise ValueError("V2.42.72 results per query is outside [1,6]")
    requested = policy or TwoWavePolicy()
    requested.validate()
    wave1_queries = planned[: requested.wave1_queries]
    remaining = planned[len(wave1_queries) :]
    wave2_queries = remaining[: requested.wave2_queries]
    effective = _effective_policy(
        requested,
        first_queries=len(wave1_queries),
        second_queries=len(wave2_queries),
        max_results=top_k,
    )
    effective.validate()
    capped = BudgetEquivalentTaskUnionSearchClient(
        search,
        search_results_per_query=top_k,
        global_fetch_cap=effective.wave1_fetches + effective.wave2_fetches,
    )

    first_search_start = float(monotonic())
    first_batches = capped.search_many(
        wave1_queries,
        max_results=top_k,
        search_depth="advanced",
        include_raw_content=False,
    )
    first_search_seconds = _elapsed(first_search_start, monotonic)
    first_leads = _lead_requests(first_batches, effective.wave1_fetches)
    first_fetch_start = float(monotonic())
    first_pages = capped.fetch_urls(first_leads) if first_leads else []
    first_fetch_seconds = _elapsed(first_fetch_start, monotonic)
    first_discovery = capped.parent.receipt()
    first_stats, fingerprints, hosts = _wave_stats(
        executed=True,
        query_count=len(wave1_queries),
        leads=first_leads,
        pages=first_pages,
        search_seconds=first_search_seconds,
        fetch_seconds=first_fetch_seconds,
        failure_count=int(first_discovery["raw_unrecoverable_failure_count"]),
        prior_fingerprints=set(),
        prior_hosts=set(),
    )
    observation = FirstWaveObservation(
        queries_executed=first_stats["queries_executed"],
        sources_discovered=first_stats["sources_discovered"],
        fetches_attempted=first_stats["fetches_attempted"],
        usable_pages=first_stats["usable_pages"],
        novel_pages=first_stats["novel_pages"],
        unique_hosts=first_stats["new_unique_hosts"],
        content_chars=first_stats["content_chars"],
        required_column_count=columns,
        explicit_row_target=row_target,
        search_seconds=first_stats["search_seconds"],
        fetch_seconds=first_stats["fetch_seconds"],
        unrecoverable_search_failures=first_stats[
            "unrecoverable_search_failures"
        ],
    )
    controller = decide_two_wave(observation, policy=effective)

    second_batches: list[dict[str, Any]] = []
    second_pages: Any = []
    second_leads: list[dict[str, str]] = []
    if controller["decision"] == "expand":
        second_search_start = float(monotonic())
        second_batches = capped.search_many(
            wave2_queries,
            max_results=top_k,
            search_depth="advanced",
            include_raw_content=False,
        )
        second_search_seconds = _elapsed(second_search_start, monotonic)
        first_urls = {
            canonicalize_url(str(value.get("url", "")))
            for value in first_leads
            if canonicalize_url(str(value.get("url", "")))
        }
        second_leads = [
            value
            for value in _lead_requests(second_batches, effective.wave2_fetches)
            if canonicalize_url(str(value.get("url", ""))) not in first_urls
        ][: effective.wave2_fetches]
        second_fetch_start = float(monotonic())
        second_pages = capped.fetch_urls(second_leads) if second_leads else []
        second_fetch_seconds = _elapsed(second_fetch_start, monotonic)
        live_discovery = capped.parent.receipt()
        second_failures = int(live_discovery["raw_unrecoverable_failure_count"]) - int(
            first_discovery["raw_unrecoverable_failure_count"]
        )
        second_stats, fingerprints, hosts = _wave_stats(
            executed=True,
            query_count=len(wave2_queries),
            leads=second_leads,
            pages=second_pages,
            search_seconds=second_search_seconds,
            fetch_seconds=second_fetch_seconds,
            failure_count=max(0, second_failures),
            prior_fingerprints=fingerprints,
            prior_hosts=hosts,
        )
    else:
        second_stats = {
            "executed": False,
            "queries_executed": 0,
            "sources_discovered": 0,
            "fetches_attempted": 0,
            "usable_pages": 0,
            "novel_pages": 0,
            "new_unique_hosts": 0,
            "content_chars": 0,
            "search_seconds": 0.0,
            "fetch_seconds": 0.0,
            "unrecoverable_search_failures": 0,
        }
        _validate_wave(second_stats)

    discovery = capped.parent.receipt()
    budget = capped.receipt()
    total = {
        "queries_executed": first_stats["queries_executed"]
        + second_stats["queries_executed"],
        "sources_discovered": first_stats["sources_discovered"]
        + second_stats["sources_discovered"],
        "fetches_attempted": first_stats["fetches_attempted"]
        + second_stats["fetches_attempted"],
        "usable_pages": first_stats["usable_pages"] + second_stats["usable_pages"],
        "novel_pages": first_stats["novel_pages"] + second_stats["novel_pages"],
        "unique_hosts": len(hosts),
        "content_chars": first_stats["content_chars"] + second_stats["content_chars"],
        "search_seconds": round(
            first_stats["search_seconds"] + second_stats["search_seconds"], 6
        ),
        "fetch_seconds": round(
            first_stats["fetch_seconds"] + second_stats["fetch_seconds"], 6
        ),
        "unrecoverable_search_failures": first_stats[
            "unrecoverable_search_failures"
        ]
        + second_stats["unrecoverable_search_failures"],
    }
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "controller_policy_id": CONTROLLER_POLICY_ID,
        "label_blind": True,
        "planned_query_count": len(planned),
        "required_column_count": columns,
        "explicit_row_target": row_target,
        "search_results_per_query": top_k,
        "wave1": first_stats,
        "controller": controller,
        "wave2": second_stats,
        "total": total,
        "budget_equivalence": budget,
        "discovery_union": discovery,
        "delta_only_second_wave": True,
        "provider_narrative_or_snippet_forwarded": False,
        "fetched_page_text_is_only_active_evidence": True,
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = object_sha256(receipt)
    validate_retrieval_receipt(receipt)
    return {
        "search_batches": [*first_batches, *second_batches],
        "page_batches": [*first_pages, *second_pages],
        "receipt": receipt,
    }


def validate_retrieval_receipt(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("controller_policy_id") != CONTROLLER_POLICY_ID
        or value.get("label_blind") is not True
        or value.get("delta_only_second_wave") is not True
        or value.get("provider_narrative_or_snippet_forwarded") is not False
        or value.get("fetched_page_text_is_only_active_evidence") is not True
        or value.get(
            "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.42.72 retrieval receipt identity drifted")
    planned = _nonnegative_integer(value.get("planned_query_count"), label="planned queries")
    columns = _nonnegative_integer(value.get("required_column_count"), label="columns")
    row_target = _nonnegative_integer(value.get("explicit_row_target"), label="row target")
    top_k = _nonnegative_integer(value.get("search_results_per_query"), label="top k")
    if planned <= 0 or columns <= 0 or not 1 <= top_k <= 6:
        raise ValueError("V2.42.72 retrieval contract dimensions drifted")
    first = value.get("wave1")
    second = value.get("wave2")
    total = value.get("total")
    controller = value.get("controller")
    budget = value.get("budget_equivalence")
    discovery = value.get("discovery_union")
    if not isinstance(first, Mapping) or not isinstance(second, Mapping):
        raise ValueError("V2.42.72 retrieval wave receipt is absent")
    _validate_wave(first)
    _validate_wave(second)
    if not isinstance(total, Mapping) or set(total) != TOTAL_KEYS:
        raise ValueError("V2.42.72 retrieval total schema drifted")
    for name in TOTAL_KEYS - {"search_seconds", "fetch_seconds"}:
        _nonnegative_integer(total.get(name), label=f"total {name}")
    for name in ("search_seconds", "fetch_seconds"):
        _nonnegative_number(total.get(name), label=f"total {name}")
    expected_sum = {
        "queries_executed": first["queries_executed"] + second["queries_executed"],
        "sources_discovered": first["sources_discovered"] + second["sources_discovered"],
        "fetches_attempted": first["fetches_attempted"] + second["fetches_attempted"],
        "usable_pages": first["usable_pages"] + second["usable_pages"],
        "novel_pages": first["novel_pages"] + second["novel_pages"],
        "content_chars": first["content_chars"] + second["content_chars"],
        "unrecoverable_search_failures": first["unrecoverable_search_failures"]
        + second["unrecoverable_search_failures"],
    }
    if any(total[name] != amount for name, amount in expected_sum.items()):
        raise ValueError("V2.42.72 retrieval total accounting drifted")
    if total["unique_hosts"] != first["new_unique_hosts"] + second["new_unique_hosts"]:
        raise ValueError("V2.42.72 retrieval host accounting drifted")
    if not math.isclose(
        float(total["search_seconds"]),
        float(first["search_seconds"]) + float(second["search_seconds"]),
        abs_tol=2e-6,
    ) or not math.isclose(
        float(total["fetch_seconds"]),
        float(first["fetch_seconds"]) + float(second["fetch_seconds"]),
        abs_tol=2e-6,
    ):
        raise ValueError("V2.42.72 retrieval latency accounting drifted")
    if not isinstance(controller, Mapping):
        raise ValueError("V2.42.72 controller receipt is absent")
    validate_controller_receipt(controller)
    observation = controller["first_wave"]
    expected_observation = {
        "queries_executed": first["queries_executed"],
        "sources_discovered": first["sources_discovered"],
        "fetches_attempted": first["fetches_attempted"],
        "usable_pages": first["usable_pages"],
        "novel_pages": first["novel_pages"],
        "unique_hosts": first["new_unique_hosts"],
        "content_chars": first["content_chars"],
        "required_column_count": columns,
        "explicit_row_target": row_target,
        "search_seconds": first["search_seconds"],
        "fetch_seconds": first["fetch_seconds"],
        "unrecoverable_search_failures": first["unrecoverable_search_failures"],
    }
    if observation != expected_observation:
        raise ValueError("V2.42.72 controller observation binding drifted")
    expanded = controller["decision"] == "expand"
    if second["executed"] is not expanded:
        raise ValueError("V2.42.72 second-wave execution disagrees with controller")
    if not isinstance(budget, Mapping) or not isinstance(discovery, Mapping):
        raise ValueError("V2.42.72 nested retrieval receipts are absent")
    validate_budget_receipt(budget)
    validate_discovery_receipt(discovery)
    if budget["parent_discovery_receipt_sha256"] != payload_sha256(discovery):
        raise ValueError("V2.42.72 nested discovery receipt binding drifted")
    if (
        budget["logical_query_count"] != total["queries_executed"]
        or discovery["logical_query_count"] != total["queries_executed"]
        or discovery["fetch_requested_source_count"] != total["fetches_attempted"]
        or discovery["fetch_usable_page_count"] != total["usable_pages"]
        or discovery["raw_unrecoverable_failure_count"]
        != total["unrecoverable_search_failures"]
        or total["fetches_attempted"] > budget["global_fetch_cap"]
    ):
        raise ValueError("V2.42.72 nested effect accounting drifted")
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    if not isinstance(seal, str) or seal != object_sha256(unsigned):
        raise ValueError("V2.42.72 retrieval receipt seal drifted")


__all__ = [
    "POLICY_ID",
    "run_two_wave_retrieval",
    "validate_retrieval_receipt",
]
