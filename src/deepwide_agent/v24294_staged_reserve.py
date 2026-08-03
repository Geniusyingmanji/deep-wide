"""Label-blind 6+2+2 staged reserve inside the existing ten-fetch cap.

This build-only kernel fixes the V2.42.93 budget deadlock: the old 6+4
schedule exhausted all fetch capacity before it could observe post-expand
coverage.  The new schedule fetches two second-wave ranked pages, then spends
the final two slots on the original ranked continuation when coverage is
sufficient or on deterministic host-diverse same-response tail candidates
when coverage remains low.  It never adds a hosted-search request.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url
from .v24257_score_first_runtime import _lead_requests
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24272_two_wave_entropy_voc import (
    FirstWaveObservation,
    TwoWavePolicy,
    decide_two_wave,
    validate_receipt as validate_controller_receipt,
)
from .v24272_two_wave_retrieval import _effective_policy
from .v24289_low_coverage_rescue import RescuePolicy, _low_coverage, _page_stats, _queries, _raw_candidates


POLICY_ID = "v24294_label_blind_staged_reserve_6_2_2_build_only_v1"
RECEIPT_ROLE = "v24294_staged_reserve_receipt"
STAGE3_REASONS = frozenset(
    {
        "controller_stop",
        "coverage_sufficient_ranked_continuation",
        "low_coverage_diversity_tail",
        "low_coverage_ranked_fallback",
        "latency_ceiling_ranked_continuation",
        "no_reserved_candidates",
    }
)
WAVE_KEYS = frozenset(
    {
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
TOTAL_KEYS = frozenset((WAVE_KEYS - {"new_unique_hosts"}) | {"unique_hosts"})
STAGE3_KEYS = frozenset(
    {
        "executed",
        "reason",
        "low_coverage_before",
        "ranked_candidate_count",
        "tail_candidate_count",
        "selected_ranked_count",
        "selected_tail_count",
        "fetches_attempted",
        "usable_pages",
        "novel_pages",
        "new_unique_hosts",
        "content_chars",
        "fetch_seconds",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind",
        "planned_query_count",
        "required_column_count",
        "explicit_row_target",
        "search_results_per_query",
        "two_wave_policy",
        "reserve_policy",
        "first_wave",
        "controller",
        "second_wave_observation",
        "total_before_reserved",
        "reserved_stage",
        "total",
        "controller_search_invocations_before_reserved",
        "controller_search_invocations_after_reserved",
        "provider_search_calls_before_reserved",
        "provider_search_calls_after_reserved",
        "hosted_search_requests_added_by_reserved",
        "same_response_deterministic_candidates_only",
        "provider_narrative_or_snippet_forwarded",
        "fetched_page_text_is_only_active_evidence",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclasses.dataclass(frozen=True)
class StagedReservePolicy:
    second_wave_observation_fetches: int = 2
    reserved_fetches: int = 2
    minimum_total_usable_pages: int = 4
    minimum_total_unique_hosts: int = 2
    content_chars_per_column: int = 1_200
    maximum_pre_reserved_retrieval_seconds: float = 60.0

    def validate(self) -> None:
        for name in (
            "second_wave_observation_fetches",
            "reserved_fetches",
            "minimum_total_usable_pages",
            "minimum_total_unique_hosts",
            "content_chars_per_column",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"V2.42.94 {name} is invalid")
        seconds = self.maximum_pre_reserved_retrieval_seconds
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or not math.isfinite(float(seconds))
            or seconds <= 0
        ):
            raise ValueError("V2.42.94 reserved latency ceiling is invalid")


def _elapsed(started: float, monotonic: Callable[[], float]) -> float:
    return round(max(0.0, float(monotonic()) - float(started)), 6)


def _nonnegative_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.94 {label} is not a nonnegative integer")
    return value


def _nonnegative_number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.94 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"V2.42.94 {label} is invalid")
    return number


def _validate_wave(value: Mapping[str, Any], *, label: str) -> None:
    if set(value) != WAVE_KEYS:
        raise ValueError(f"V2.42.94 {label} wave schema drifted")
    for name in WAVE_KEYS - {"search_seconds", "fetch_seconds"}:
        _nonnegative_integer(value.get(name), label=f"{label} {name}")
    for name in ("search_seconds", "fetch_seconds"):
        _nonnegative_number(value.get(name), label=f"{label} {name}")
    if (
        value["sources_discovered"] != value["fetches_attempted"]
        or value["usable_pages"] > value["fetches_attempted"]
        or value["novel_pages"] > value["usable_pages"]
        or value["new_unique_hosts"] > value["usable_pages"]
        or value["unrecoverable_search_failures"] > value["queries_executed"]
    ):
        raise ValueError(f"V2.42.94 {label} wave accounting drifted")


def _validate_total(value: Mapping[str, Any], *, label: str) -> None:
    if set(value) != TOTAL_KEYS:
        raise ValueError(f"V2.42.94 {label} total schema drifted")
    for name in TOTAL_KEYS - {"search_seconds", "fetch_seconds"}:
        _nonnegative_integer(value.get(name), label=f"{label} {name}")
    for name in ("search_seconds", "fetch_seconds"):
        _nonnegative_number(value.get(name), label=f"{label} {name}")
    if (
        value["sources_discovered"] != value["fetches_attempted"]
        or value["usable_pages"] > value["fetches_attempted"]
        or value["novel_pages"] > value["usable_pages"]
        or value["unique_hosts"] > value["usable_pages"]
        or value["unrecoverable_search_failures"] > value["queries_executed"]
    ):
        raise ValueError(f"V2.42.94 {label} total accounting drifted")


def _dedupe(values: Sequence[Mapping[str, Any]], selected_urls: set[str]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in values:
        url = canonicalize_url(str(raw.get("url", "")))
        if not url or url in selected_urls or url in seen:
            continue
        seen.add(url)
        output.append(dict(raw))
    return output


def _diversity_order(values: Sequence[Mapping[str, Any]], prior_hosts: set[str]) -> list[dict[str, Any]]:
    """Stable rank with unseen-host candidates first; no content or label scoring."""

    indexed = []
    for index, raw in enumerate(values):
        url = canonicalize_url(str(raw.get("url", "")))
        host = (urlsplit(url).hostname or "").casefold() if url else ""
        indexed.append((host in prior_hosts or not host, index, dict(raw)))
    indexed.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in indexed]


def _wave(
    *,
    queries: int,
    leads: list[dict[str, Any]],
    pages: object,
    search_seconds: float,
    fetch_seconds: float,
    failures: int,
    fingerprints: set[str],
    hosts: set[str],
) -> tuple[dict[str, Any], set[str], set[str]]:
    stats, fingerprints, hosts = _page_stats(
        pages, prior_fingerprints=fingerprints, prior_hosts=hosts
    )
    value = {
        "queries_executed": queries,
        "sources_discovered": len(leads),
        "fetches_attempted": len(leads),
        **stats,
        "search_seconds": search_seconds,
        "fetch_seconds": fetch_seconds,
        "unrecoverable_search_failures": failures,
    }
    _validate_wave(value, label="runtime")
    return value, fingerprints, hosts


def run_staged_reserve(
    queries: Sequence[str],
    *,
    search: Any,
    required_column_count: int,
    explicit_row_target: int = 0,
    search_results_per_query: int = 3,
    two_wave_policy: TwoWavePolicy | None = None,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    planned = _queries(queries)
    if isinstance(required_column_count, bool) or not isinstance(required_column_count, int) or required_column_count <= 0:
        raise ValueError("V2.42.94 column count is invalid")
    if isinstance(explicit_row_target, bool) or not isinstance(explicit_row_target, int) or explicit_row_target < 0:
        raise ValueError("V2.42.94 row target is invalid")
    if isinstance(search_results_per_query, bool) or not isinstance(search_results_per_query, int) or not 1 <= search_results_per_query <= 6:
        raise ValueError("V2.42.94 top-k is invalid")
    requested = two_wave_policy or TwoWavePolicy()
    requested.validate()
    reserve = reserve_policy or StagedReservePolicy()
    reserve.validate()
    first_queries = planned[: requested.wave1_queries]
    second_queries = planned[len(first_queries) : len(first_queries) + requested.wave2_queries]
    effective = _effective_policy(
        requested,
        first_queries=len(first_queries),
        second_queries=len(second_queries),
        max_results=search_results_per_query,
    )
    if effective.wave2_fetches < reserve.second_wave_observation_fetches + reserve.reserved_fetches:
        raise ValueError("V2.42.94 second-wave budget cannot fund observation plus reserve")
    global_cap = effective.wave1_fetches + effective.wave2_fetches
    if global_cap > 10:
        raise ValueError("V2.42.94 global fetch cap exceeds ten")

    union = TaskUnionDiscoverySearchClient(search)
    selected_urls: set[str] = set()
    fingerprints: set[str] = set()
    hosts: set[str] = set()
    first_tail: list[dict[str, Any]] = []

    started = float(monotonic())
    first_raw = union.search_many(
        first_queries, max_results=search_results_per_query, search_depth="advanced", include_raw_content=False
    )
    first_search_seconds = _elapsed(started, monotonic)
    first_candidates = _raw_candidates(first_raw)
    first_leads = _lead_requests(first_raw, effective.wave1_fetches)
    selected_urls.update(canonicalize_url(str(value.get("url", ""))) for value in first_leads)
    first_tail.extend(_dedupe(first_candidates, selected_urls))
    started = float(monotonic())
    first_pages = union.fetch_urls(first_leads) if first_leads else []
    first_fetch_seconds = _elapsed(started, monotonic)
    first_receipt = union.receipt()
    first, fingerprints, hosts = _wave(
        queries=len(first_queries), leads=first_leads, pages=first_pages,
        search_seconds=first_search_seconds, fetch_seconds=first_fetch_seconds,
        failures=int(first_receipt["raw_unrecoverable_failure_count"]),
        fingerprints=fingerprints, hosts=hosts,
    )
    observation = FirstWaveObservation(
        queries_executed=first["queries_executed"],
        sources_discovered=first["sources_discovered"],
        fetches_attempted=first["fetches_attempted"],
        usable_pages=first["usable_pages"],
        novel_pages=first["novel_pages"],
        unique_hosts=first["new_unique_hosts"],
        content_chars=first["content_chars"],
        required_column_count=required_column_count,
        explicit_row_target=explicit_row_target,
        search_seconds=first["search_seconds"],
        fetch_seconds=first["fetch_seconds"],
        unrecoverable_search_failures=first["unrecoverable_search_failures"],
    )
    controller = decide_two_wave(observation, policy=effective)

    second_raw: list[dict[str, Any]] = []
    second_ranked: list[dict[str, Any]] = []
    second_pages: object = []
    second = {
        "queries_executed": 0, "sources_discovered": 0, "fetches_attempted": 0,
        "usable_pages": 0, "novel_pages": 0, "new_unique_hosts": 0,
        "content_chars": 0, "search_seconds": 0.0, "fetch_seconds": 0.0,
        "unrecoverable_search_failures": 0,
    }
    ranked_reserved: list[dict[str, Any]] = []
    if controller["decision"] == "expand":
        started = float(monotonic())
        second_raw = union.search_many(
            second_queries, max_results=search_results_per_query, search_depth="advanced", include_raw_content=False
        )
        second_search_seconds = _elapsed(started, monotonic)
        second_ranked = _dedupe(_raw_candidates(second_raw), selected_urls)
        observe_count = min(reserve.second_wave_observation_fetches, len(second_ranked))
        second_leads = second_ranked[:observe_count]
        ranked_reserved = second_ranked[observe_count : observe_count + reserve.reserved_fetches]
        selected_urls.update(canonicalize_url(str(value.get("url", ""))) for value in second_leads)
        started = float(monotonic())
        second_pages = union.fetch_urls(second_leads) if second_leads else []
        second_fetch_seconds = _elapsed(started, monotonic)
        live = union.receipt()
        second, fingerprints, hosts = _wave(
            queries=len(second_queries), leads=second_leads, pages=second_pages,
            search_seconds=second_search_seconds, fetch_seconds=second_fetch_seconds,
            failures=max(0, int(live["raw_unrecoverable_failure_count"]) - int(first_receipt["raw_unrecoverable_failure_count"])),
            fingerprints=fingerprints, hosts=hosts,
        )

    total_before = {
        "queries_executed": first["queries_executed"] + second["queries_executed"],
        "sources_discovered": first["sources_discovered"] + second["sources_discovered"],
        "fetches_attempted": first["fetches_attempted"] + second["fetches_attempted"],
        "usable_pages": first["usable_pages"] + second["usable_pages"],
        "novel_pages": first["novel_pages"] + second["novel_pages"],
        "unique_hosts": len(hosts),
        "content_chars": first["content_chars"] + second["content_chars"],
        "search_seconds": round(first["search_seconds"] + second["search_seconds"], 6),
        "fetch_seconds": round(first["fetch_seconds"] + second["fetch_seconds"], 6),
        "unrecoverable_search_failures": first["unrecoverable_search_failures"] + second["unrecoverable_search_failures"],
    }
    low_policy = RescuePolicy(
        maximum_rescue_fetches=reserve.reserved_fetches,
        minimum_total_usable_pages=reserve.minimum_total_usable_pages,
        minimum_total_unique_hosts=reserve.minimum_total_unique_hosts,
        content_chars_per_column=reserve.content_chars_per_column,
        maximum_pre_rescue_retrieval_seconds=reserve.maximum_pre_reserved_retrieval_seconds,
    )
    low = _low_coverage(total_before, columns=required_column_count, policy=low_policy)
    latency_ok = total_before["search_seconds"] + total_before["fetch_seconds"] <= reserve.maximum_pre_reserved_retrieval_seconds
    ranked_candidates = _dedupe(ranked_reserved, selected_urls)
    ranked_urls = {
        canonicalize_url(str(value.get("url", ""))) for value in ranked_candidates
    }
    tail_candidates = _dedupe(
        [*first_tail, *second_ranked], selected_urls | ranked_urls
    )
    remaining = max(0, global_cap - int(total_before["fetches_attempted"]))
    capacity = min(reserve.reserved_fetches, remaining)
    reserved_leads: list[dict[str, Any]] = []
    selected_tail_count = 0
    selected_ranked_count = 0
    reason = "controller_stop"
    if controller["decision"] == "expand":
        if low and latency_ok:
            tail_selected = _diversity_order(tail_candidates, hosts)[:capacity]
            remaining_capacity = capacity - len(tail_selected)
            ranked_selected = ranked_candidates[:remaining_capacity]
            reserved_leads = [*tail_selected, *ranked_selected]
            selected_tail_count = len(tail_selected)
            selected_ranked_count = len(ranked_selected)
            reason = (
                "low_coverage_diversity_tail" if tail_selected else
                "low_coverage_ranked_fallback" if ranked_selected else
                "no_reserved_candidates"
            )
        else:
            reserved_leads = ranked_candidates[:capacity]
            selected_ranked_count = len(reserved_leads)
            reason = (
                "coverage_sufficient_ranked_continuation" if not low
                else "latency_ceiling_ranked_continuation"
            ) if reserved_leads else "no_reserved_candidates"
    search_before = int(union.search_invocations)
    provider_before = max(0, int(getattr(search, "calls", 0) or 0))
    started = float(monotonic())
    reserved_pages = union.fetch_urls(reserved_leads) if reserved_leads else []
    reserved_fetch_seconds = _elapsed(started, monotonic) if reserved_leads else 0.0
    reserved_stats, fingerprints, hosts = _page_stats(
        reserved_pages, prior_fingerprints=fingerprints, prior_hosts=hosts
    )
    search_after = int(union.search_invocations)
    provider_after = max(0, int(getattr(search, "calls", 0) or 0))
    stage = {
        "executed": bool(reserved_leads),
        "reason": reason,
        "low_coverage_before": low,
        "ranked_candidate_count": len(ranked_candidates),
        "tail_candidate_count": len(tail_candidates),
        "selected_ranked_count": selected_ranked_count,
        "selected_tail_count": selected_tail_count,
        "fetches_attempted": len(reserved_leads),
        **reserved_stats,
        "fetch_seconds": reserved_fetch_seconds,
    }
    total = {
        **total_before,
        "sources_discovered": total_before["sources_discovered"] + len(reserved_leads),
        "fetches_attempted": total_before["fetches_attempted"] + len(reserved_leads),
        "usable_pages": total_before["usable_pages"] + stage["usable_pages"],
        "novel_pages": total_before["novel_pages"] + stage["novel_pages"],
        "unique_hosts": len(hosts),
        "content_chars": total_before["content_chars"] + stage["content_chars"],
        "fetch_seconds": round(total_before["fetch_seconds"] + stage["fetch_seconds"], 6),
    }
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "label_blind": True,
        "planned_query_count": len(planned),
        "required_column_count": required_column_count,
        "explicit_row_target": explicit_row_target,
        "search_results_per_query": search_results_per_query,
        "two_wave_policy": dataclasses.asdict(effective),
        "reserve_policy": dataclasses.asdict(reserve),
        "first_wave": first,
        "controller": controller,
        "second_wave_observation": second,
        "total_before_reserved": total_before,
        "reserved_stage": stage,
        "total": total,
        "controller_search_invocations_before_reserved": search_before,
        "controller_search_invocations_after_reserved": search_after,
        "provider_search_calls_before_reserved": provider_before,
        "provider_search_calls_after_reserved": provider_after,
        "hosted_search_requests_added_by_reserved": max(0, provider_after - provider_before),
        "same_response_deterministic_candidates_only": True,
        "provider_narrative_or_snippet_forwarded": False,
        "fetched_page_text_is_only_active_evidence": True,
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    validate_receipt(receipt)
    return {"page_batches": [*first_pages, *second_pages, *reserved_pages], "receipt": receipt}


def validate_receipt(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
        or value.get("hosted_search_requests_added_by_reserved") != 0
        or value.get("controller_search_invocations_before_reserved") != value.get("controller_search_invocations_after_reserved")
        or value.get("provider_search_calls_before_reserved") != value.get("provider_search_calls_after_reserved")
        or value.get("same_response_deterministic_candidates_only") is not True
        or value.get("provider_narrative_or_snippet_forwarded") is not False
        or value.get("fetched_page_text_is_only_active_evidence") is not True
        or value.get("contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.42.94 receipt identity drifted")
    policy = value.get("two_wave_policy")
    reserve_raw = value.get("reserve_policy")
    first = value.get("first_wave")
    second = value.get("second_wave_observation")
    before = value.get("total_before_reserved")
    stage = value.get("reserved_stage")
    total = value.get("total")
    controller = value.get("controller")
    if not all(isinstance(item, Mapping) for item in (policy, reserve_raw, first, second, before, stage, total, controller)):
        raise ValueError("V2.42.94 nested receipt field is absent")
    frozen = TwoWavePolicy(**dict(policy)); frozen.validate()
    reserve = StagedReservePolicy(**dict(reserve_raw)); reserve.validate()
    _validate_wave(first, label="first")
    _validate_wave(second, label="second observation")
    _validate_total(before, label="pre-reserved")
    _validate_total(total, label="final")
    validate_controller_receipt(controller)
    if dict(controller.get("policy") or {}) != dict(policy):
        raise ValueError("V2.42.94 controller policy drifted")
    if set(stage) != STAGE3_KEYS or not isinstance(stage.get("executed"), bool) or not isinstance(stage.get("low_coverage_before"), bool) or stage.get("reason") not in STAGE3_REASONS:
        raise ValueError("V2.42.94 reserved stage schema drifted")
    for name in STAGE3_KEYS - {"executed", "low_coverage_before", "reason", "fetch_seconds"}:
        _nonnegative_integer(stage.get(name), label=f"reserved {name}")
    _nonnegative_number(stage.get("fetch_seconds"), label="reserved fetch seconds")
    if (
        stage["fetches_attempted"] > reserve.reserved_fetches
        or stage["executed"] != bool(stage["fetches_attempted"])
        or stage["selected_ranked_count"] + stage["selected_tail_count"] != stage["fetches_attempted"]
        or stage["usable_pages"] > stage["fetches_attempted"]
        or total["fetches_attempted"] > frozen.wave1_fetches + frozen.wave2_fetches
        or total["fetches_attempted"] > 10
        or total["queries_executed"] > frozen.wave1_queries + frozen.wave2_queries
        or total["sources_discovered"] != before["sources_discovered"] + stage["fetches_attempted"]
        or total["fetches_attempted"] != before["fetches_attempted"] + stage["fetches_attempted"]
        or total["usable_pages"] != before["usable_pages"] + stage["usable_pages"]
        or total["novel_pages"] != before["novel_pages"] + stage["novel_pages"]
        or total["content_chars"] != before["content_chars"] + stage["content_chars"]
    ):
        raise ValueError("V2.42.94 reserved or total accounting drifted")
    expected_before = {
        "queries_executed": first["queries_executed"] + second["queries_executed"],
        "sources_discovered": first["sources_discovered"] + second["sources_discovered"],
        "fetches_attempted": first["fetches_attempted"] + second["fetches_attempted"],
        "usable_pages": first["usable_pages"] + second["usable_pages"],
        "novel_pages": first["novel_pages"] + second["novel_pages"],
        "content_chars": first["content_chars"] + second["content_chars"],
        "search_seconds": round(float(first["search_seconds"]) + float(second["search_seconds"]), 6),
        "fetch_seconds": round(float(first["fetch_seconds"]) + float(second["fetch_seconds"]), 6),
        "unrecoverable_search_failures": first["unrecoverable_search_failures"] + second["unrecoverable_search_failures"],
    }
    if any(before[name] != expected for name, expected in expected_before.items()):
        raise ValueError("V2.42.94 pre-reserved aggregation drifted")
    low_policy = RescuePolicy(
        maximum_rescue_fetches=reserve.reserved_fetches,
        minimum_total_usable_pages=reserve.minimum_total_usable_pages,
        minimum_total_unique_hosts=reserve.minimum_total_unique_hosts,
        content_chars_per_column=reserve.content_chars_per_column,
        maximum_pre_rescue_retrieval_seconds=reserve.maximum_pre_reserved_retrieval_seconds,
    )
    expected_low = _low_coverage(before, columns=int(value.get("required_column_count", 0)), policy=low_policy)
    if stage["low_coverage_before"] != expected_low:
        raise ValueError("V2.42.94 low-coverage decision drifted")
    decision = controller.get("decision")
    if decision == "stop":
        if stage["executed"] or stage["reason"] != "controller_stop" or stage["fetches_attempted"]:
            raise ValueError("V2.42.94 stop path has reserved effects")
    elif decision == "expand":
        if second["fetches_attempted"] > reserve.second_wave_observation_fetches:
            raise ValueError("V2.42.94 observation stage consumed reserved capacity")
        if stage["reason"] == "low_coverage_diversity_tail" and (not expected_low or stage["selected_tail_count"] <= 0):
            raise ValueError("V2.42.94 diversity tail reason drifted")
        if stage["reason"] == "low_coverage_ranked_fallback" and (
            not expected_low
            or stage["tail_candidate_count"] != 0
            or stage["selected_tail_count"] != 0
            or stage["selected_ranked_count"] <= 0
        ):
            raise ValueError("V2.42.94 ranked fallback reason drifted")
        if stage["reason"] == "coverage_sufficient_ranked_continuation" and (expected_low or stage["selected_ranked_count"] <= 0):
            raise ValueError("V2.42.94 ranked continuation reason drifted")
        latency_ok = (
            float(before["search_seconds"]) + float(before["fetch_seconds"])
            <= reserve.maximum_pre_reserved_retrieval_seconds
        )
        if stage["reason"] == "latency_ceiling_ranked_continuation" and (
            not expected_low or latency_ok or stage["selected_ranked_count"] <= 0
        ):
            raise ValueError("V2.42.94 latency continuation reason drifted")
        if stage["reason"] == "no_reserved_candidates" and stage["executed"]:
            raise ValueError("V2.42.94 empty reserved reason has effects")
        if stage["reason"] == "low_coverage_diversity_tail" and not latency_ok:
            raise ValueError("V2.42.94 diversity tail exceeded latency ceiling")
    else:
        raise ValueError("V2.42.94 controller decision drifted")


__all__ = [
    "POLICY_ID",
    "StagedReservePolicy",
    "payload_sha256",
    "run_staged_reserve",
    "validate_receipt",
]
