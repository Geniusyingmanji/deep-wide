"""Build-only label-blind rescue for low-coverage two-wave retrieval.

The V2.42.87 post-terminal diagnosis found that the normal controller-stop
path was quality-neutral while tasks that expanded and still had little usable
evidence regressed.  This successor does not issue another hosted-search
request.  It retains the deterministic tail of URLs already returned by the
same two hosted-search effects and, only after an ``expand`` decision remains
low coverage, fetches at most four tail pages inside the existing global
10-page budget.

The trigger observes only same-pass counts (usable pages, hosts, characters,
columns, and elapsed retrieval wall).  It has no benchmark labels, evaluator,
score, answer, file, environment, process, or model capability.
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
from .v24257_score_first_runtime import _lead_requests, _normalize_text
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24272_two_wave_entropy_voc import (
    FirstWaveObservation,
    TwoWavePolicy,
    decide_two_wave,
    validate_receipt as validate_controller_receipt,
)
from .v24272_two_wave_retrieval import _content_fingerprint, _effective_policy, _results


POLICY_ID = "v24289_label_blind_low_coverage_tail_rescue_build_only_v1"
RECEIPT_ROLE = "v24289_low_coverage_tail_rescue_receipt"
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
TOTAL_KEYS = frozenset(
    (WAVE_KEYS - {"new_unique_hosts"}) | {"unique_hosts"}
)
RESCUE_KEYS = frozenset(
    {
        "triggered",
        "reason",
        "tail_candidates",
        "fetches_attempted",
        "usable_pages",
        "novel_pages",
        "new_unique_hosts",
        "content_chars",
        "fetch_seconds",
    }
)
RESCUE_REASONS = frozenset(
    {
        "low_coverage_tail_available",
        "controller_stop",
        "coverage_sufficient",
        "latency_ceiling",
        "no_tail_or_remaining_budget",
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
        "rescue_policy",
        "first_wave",
        "controller",
        "second_wave",
        "total_before_rescue",
        "rescue",
        "total",
        "controller_search_invocations_before_rescue",
        "controller_search_invocations_after_rescue",
        "provider_search_calls_before_rescue",
        "provider_search_calls_after_rescue",
        "hosted_search_requests_added_by_rescue",
        "same_response_deterministic_tail_only",
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
class RescuePolicy:
    maximum_rescue_fetches: int = 4
    minimum_total_usable_pages: int = 4
    minimum_total_unique_hosts: int = 2
    content_chars_per_column: int = 1_200
    maximum_pre_rescue_retrieval_seconds: float = 60.0

    def validate(self) -> None:
        for name in (
            "maximum_rescue_fetches",
            "minimum_total_usable_pages",
            "minimum_total_unique_hosts",
            "content_chars_per_column",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"V2.42.89 {name} is invalid")
        seconds = self.maximum_pre_rescue_retrieval_seconds
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(float(seconds)) or seconds <= 0:
            raise ValueError("V2.42.89 rescue latency ceiling is invalid")


def _queries(values: Sequence[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, str):
            raise ValueError("V2.42.89 planned query is not text")
        value = _normalize_text(raw)
        folded = value.casefold()
        if value and folded not in seen:
            output.append(value)
            seen.add(folded)
    if not output:
        raise ValueError("V2.42.89 requires a visible-plan query")
    return output


def _elapsed(started: float, monotonic: Callable[[], float]) -> float:
    return round(max(0.0, float(monotonic()) - float(started)), 6)


def _nonnegative_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.89 {label} is not a nonnegative integer")
    return value


def _nonnegative_number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.89 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"V2.42.89 {label} is invalid")
    return number


def _validate_wave(value: Mapping[str, Any], *, label: str) -> None:
    if set(value) != WAVE_KEYS:
        raise ValueError(f"V2.42.89 {label} wave schema drifted")
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
        raise ValueError(f"V2.42.89 {label} wave accounting drifted")


def _validate_total(value: Mapping[str, Any], *, label: str) -> None:
    if set(value) != TOTAL_KEYS:
        raise ValueError(f"V2.42.89 {label} total schema drifted")
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
        raise ValueError(f"V2.42.89 {label} total accounting drifted")


def _page_stats(
    pages: object,
    *,
    prior_fingerprints: set[str],
    prior_hosts: set[str],
) -> tuple[dict[str, int], set[str], set[str]]:
    fingerprints = set(prior_fingerprints)
    hosts = set(prior_hosts)
    usable = novel = new_hosts = characters = 0
    for value in _results(pages):
        text = str(value.get("raw_content") or value.get("content") or "").replace("\x00", "").strip()
        if not text:
            continue
        usable += 1
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
    return {
        "usable_pages": usable,
        "novel_pages": novel,
        "new_unique_hosts": new_hosts,
        "content_chars": characters,
    }, fingerprints, hosts


def _raw_candidates(batches: object) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for batch in batches if isinstance(batches, Sequence) and not isinstance(batches, (str, bytes)) else []:
        if not isinstance(batch, Mapping):
            continue
        query = _normalize_text(batch.get("query"))
        for result in batch.get("results") or []:
            if isinstance(result, Mapping):
                fetch_url = _normalize_text(result.get("fetch_url") or result.get("url"))
                if canonicalize_url(fetch_url):
                    candidates.append(
                        {
                            "url": fetch_url,
                            "query": query,
                            "title": _normalize_text(result.get("title"))[:500],
                            "member_label": "",
                        }
                    )
    return candidates


def _low_coverage(total: Mapping[str, Any], *, columns: int, policy: RescuePolicy) -> bool:
    return (
        int(total["usable_pages"]) < policy.minimum_total_usable_pages
        or int(total["unique_hosts"]) < policy.minimum_total_unique_hosts
        or int(total["content_chars"]) < columns * policy.content_chars_per_column
    )


def run_low_coverage_rescue(
    queries: Sequence[str],
    *,
    search: Any,
    required_column_count: int,
    explicit_row_target: int = 0,
    search_results_per_query: int = 3,
    two_wave_policy: TwoWavePolicy | None = None,
    rescue_policy: RescuePolicy | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    planned = _queries(queries)
    if isinstance(required_column_count, bool) or not isinstance(required_column_count, int) or required_column_count <= 0:
        raise ValueError("V2.42.89 column count is invalid")
    if isinstance(explicit_row_target, bool) or not isinstance(explicit_row_target, int) or explicit_row_target < 0:
        raise ValueError("V2.42.89 row target is invalid")
    if isinstance(search_results_per_query, bool) or not isinstance(search_results_per_query, int) or not 1 <= search_results_per_query <= 6:
        raise ValueError("V2.42.89 top-k is invalid")
    requested = two_wave_policy or TwoWavePolicy()
    requested.validate()
    rescue = rescue_policy or RescuePolicy()
    rescue.validate()
    first_queries = planned[: requested.wave1_queries]
    second_queries = planned[len(first_queries) : len(first_queries) + requested.wave2_queries]
    effective = _effective_policy(
        requested,
        first_queries=len(first_queries),
        second_queries=len(second_queries),
        max_results=search_results_per_query,
    )
    global_cap = effective.wave1_fetches + effective.wave2_fetches
    union = TaskUnionDiscoverySearchClient(search)
    selected_urls: set[str] = set()
    fingerprints: set[str] = set()
    hosts: set[str] = set()
    candidate_tail: list[dict[str, Any]] = []

    first_search_started = float(monotonic())
    first_raw = union.search_many(first_queries, max_results=search_results_per_query, search_depth="advanced", include_raw_content=False)
    first_search_seconds = _elapsed(first_search_started, monotonic)
    first_candidates = _raw_candidates(first_raw)
    first_leads = _lead_requests(first_raw, effective.wave1_fetches)
    selected_urls.update(canonicalize_url(str(value.get("url", ""))) for value in first_leads)
    candidate_tail.extend(value for value in first_candidates if canonicalize_url(str(value.get("url", ""))) not in selected_urls)
    first_fetch_started = float(monotonic())
    first_pages = union.fetch_urls(first_leads) if first_leads else []
    first_fetch_seconds = _elapsed(first_fetch_started, monotonic)
    first_page_stats, fingerprints, hosts = _page_stats(first_pages, prior_fingerprints=fingerprints, prior_hosts=hosts)
    first_receipt = union.receipt()
    first = {
        "queries_executed": len(first_queries),
        "sources_discovered": len(first_leads),
        "fetches_attempted": len(first_leads),
        **first_page_stats,
        "search_seconds": first_search_seconds,
        "fetch_seconds": first_fetch_seconds,
        "unrecoverable_search_failures": int(first_receipt["raw_unrecoverable_failure_count"]),
    }
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
    second_pages: Any = []
    second = {
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
    if controller["decision"] == "expand":
        second_search_started = float(monotonic())
        second_raw = union.search_many(second_queries, max_results=search_results_per_query, search_depth="advanced", include_raw_content=False)
        second_search_seconds = _elapsed(second_search_started, monotonic)
        second_candidates = _raw_candidates(second_raw)
        second_fresh = [
            value for value in second_candidates
            if canonicalize_url(str(value.get("url", ""))) not in selected_urls
        ]
        second_leads = second_fresh[: effective.wave2_fetches]
        selected_urls.update(canonicalize_url(str(value.get("url", ""))) for value in second_leads)
        candidate_tail.extend(
            value for value in second_fresh[effective.wave2_fetches :]
            if canonicalize_url(str(value.get("url", ""))) not in selected_urls
        )
        second_fetch_started = float(monotonic())
        second_pages = union.fetch_urls(second_leads) if second_leads else []
        second_fetch_seconds = _elapsed(second_fetch_started, monotonic)
        second_page_stats, fingerprints, hosts = _page_stats(second_pages, prior_fingerprints=fingerprints, prior_hosts=hosts)
        live = union.receipt()
        second = {
            "queries_executed": len(second_queries),
            "sources_discovered": len(second_leads),
            "fetches_attempted": len(second_leads),
            **second_page_stats,
            "search_seconds": second_search_seconds,
            "fetch_seconds": second_fetch_seconds,
            "unrecoverable_search_failures": max(0, int(live["raw_unrecoverable_failure_count"]) - int(first_receipt["raw_unrecoverable_failure_count"])),
        }

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
    tail_seen: set[str] = set()
    unique_tail: list[dict[str, Any]] = []
    for value in candidate_tail:
        url = canonicalize_url(str(value.get("url", "")))
        if url and url not in selected_urls and url not in tail_seen:
            tail_seen.add(url)
            unique_tail.append(value)
    remaining = max(0, global_cap - int(total_before["fetches_attempted"]))
    low = _low_coverage(total_before, columns=required_column_count, policy=rescue)
    latency_ok = total_before["search_seconds"] + total_before["fetch_seconds"] <= rescue.maximum_pre_rescue_retrieval_seconds
    controller_search_before_rescue = int(union.search_invocations)
    provider_search_before_rescue = max(0, int(getattr(search, "calls", 0) or 0))
    rescue_leads = unique_tail[: min(rescue.maximum_rescue_fetches, remaining)] if controller["decision"] == "expand" and low and latency_ok else []
    rescue_fetch_started = float(monotonic())
    rescue_pages = union.fetch_urls(rescue_leads) if rescue_leads else []
    rescue_fetch_seconds = _elapsed(rescue_fetch_started, monotonic) if rescue_leads else 0.0
    rescue_page_stats, fingerprints, hosts = _page_stats(rescue_pages, prior_fingerprints=fingerprints, prior_hosts=hosts)
    controller_search_after_rescue = int(union.search_invocations)
    provider_search_after_rescue = max(0, int(getattr(search, "calls", 0) or 0))
    rescue_stage = {
        "triggered": bool(rescue_leads),
        "reason": (
            "low_coverage_tail_available" if rescue_leads else
            "controller_stop" if controller["decision"] == "stop" else
            "coverage_sufficient" if not low else
            "latency_ceiling" if not latency_ok else
            "no_tail_or_remaining_budget"
        ),
        "tail_candidates": len(unique_tail),
        "fetches_attempted": len(rescue_leads),
        **rescue_page_stats,
        "fetch_seconds": rescue_fetch_seconds,
    }
    total = {
        **total_before,
        "sources_discovered": total_before["sources_discovered"] + len(rescue_leads),
        "fetches_attempted": total_before["fetches_attempted"] + len(rescue_leads),
        "usable_pages": total_before["usable_pages"] + rescue_stage["usable_pages"],
        "novel_pages": total_before["novel_pages"] + rescue_stage["novel_pages"],
        "unique_hosts": len(hosts),
        "content_chars": total_before["content_chars"] + rescue_stage["content_chars"],
        "fetch_seconds": round(total_before["fetch_seconds"] + rescue_stage["fetch_seconds"], 6),
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
        "rescue_policy": dataclasses.asdict(rescue),
        "first_wave": first,
        "controller": controller,
        "second_wave": second,
        "total_before_rescue": total_before,
        "rescue": rescue_stage,
        "total": total,
        "controller_search_invocations_before_rescue": controller_search_before_rescue,
        "controller_search_invocations_after_rescue": controller_search_after_rescue,
        "provider_search_calls_before_rescue": provider_search_before_rescue,
        "provider_search_calls_after_rescue": provider_search_after_rescue,
        "hosted_search_requests_added_by_rescue": max(
            0, provider_search_after_rescue - provider_search_before_rescue
        ),
        "same_response_deterministic_tail_only": True,
        "provider_narrative_or_snippet_forwarded": False,
        "fetched_page_text_is_only_active_evidence": True,
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    validate_receipt(receipt)
    return {"page_batches": [*first_pages, *second_pages, *rescue_pages], "receipt": receipt}


def validate_receipt(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    policy = value.get("rescue_policy")
    total_before = value.get("total_before_rescue")
    rescue = value.get("rescue")
    total = value.get("total")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
        or not isinstance(policy, Mapping)
        or not isinstance(total_before, Mapping)
        or not isinstance(rescue, Mapping)
        or not isinstance(total, Mapping)
        or value.get("hosted_search_requests_added_by_rescue") != 0
        or value.get("same_response_deterministic_tail_only") is not True
        or value.get("provider_narrative_or_snippet_forwarded") is not False
        or value.get("fetched_page_text_is_only_active_evidence") is not True
        or value.get("contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.42.89 rescue receipt identity drifted")
    RescuePolicy(**dict(policy)).validate()
    two_wave = value.get("two_wave_policy")
    first = value.get("first_wave")
    second = value.get("second_wave")
    if not isinstance(two_wave, Mapping) or not isinstance(first, Mapping) or not isinstance(second, Mapping):
        raise ValueError("V2.42.89 nested policy or wave is absent")
    frozen_two_wave = TwoWavePolicy(**dict(two_wave))
    frozen_two_wave.validate()
    _validate_wave(first, label="first")
    _validate_wave(second, label="second")
    _validate_total(total_before, label="pre-rescue")
    _validate_total(total, label="final")
    controller = value.get("controller")
    if not isinstance(controller, Mapping):
        raise ValueError("V2.42.89 controller receipt is absent")
    validate_controller_receipt(controller)
    if dict(controller.get("policy") or {}) != dict(two_wave):
        raise ValueError("V2.42.89 controller policy binding drifted")
    if (
        controller.get("first_wave", {}).get("queries_executed") != first["queries_executed"]
        or controller.get("first_wave", {}).get("sources_discovered") != first["sources_discovered"]
        or controller.get("first_wave", {}).get("fetches_attempted") != first["fetches_attempted"]
        or controller.get("first_wave", {}).get("usable_pages") != first["usable_pages"]
        or controller.get("first_wave", {}).get("novel_pages") != first["novel_pages"]
        or controller.get("first_wave", {}).get("unique_hosts") != first["new_unique_hosts"]
        or controller.get("first_wave", {}).get("content_chars") != first["content_chars"]
        or controller.get("first_wave", {}).get("search_seconds") != first["search_seconds"]
        or controller.get("first_wave", {}).get("fetch_seconds") != first["fetch_seconds"]
        or controller.get("first_wave", {}).get("unrecoverable_search_failures")
        != first["unrecoverable_search_failures"]
    ):
        raise ValueError("V2.42.89 controller observation binding drifted")
    if set(rescue) != RESCUE_KEYS or not isinstance(rescue.get("triggered"), bool) or rescue.get("reason") not in RESCUE_REASONS:
        raise ValueError("V2.42.89 rescue stage schema drifted")
    for name in RESCUE_KEYS - {"triggered", "reason", "fetch_seconds"}:
        _nonnegative_integer(rescue.get(name), label=f"rescue {name}")
    _nonnegative_number(rescue.get("fetch_seconds"), label="rescue fetch seconds")
    if (
        rescue["usable_pages"] > rescue["fetches_attempted"]
        or rescue["novel_pages"] > rescue["usable_pages"]
        or rescue["new_unique_hosts"] > rescue["usable_pages"]
    ):
        raise ValueError("V2.42.89 rescue stage accounting drifted")
    before_expected = {
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
    if any(total_before[name] != expected for name, expected in before_expected.items()):
        raise ValueError("V2.42.89 pre-rescue total does not equal its waves")
    if total_before["unique_hosts"] != first["new_unique_hosts"] + second["new_unique_hosts"]:
        raise ValueError("V2.42.89 pre-rescue host accounting drifted")
    decision = controller.get("decision")
    if decision == "stop" and any(second[name] for name in WAVE_KEYS):
        raise ValueError("V2.42.89 stop decision retained a second-wave effect")
    if decision == "expand" and second["queries_executed"] != controller.get("delta_budget", {}).get("queries"):
        raise ValueError("V2.42.89 expand decision did not consume its query delta")
    rescue_config = RescuePolicy(**dict(policy))
    low = _low_coverage(total_before, columns=int(value.get("required_column_count", 0)), policy=rescue_config)
    latency_ok = (
        float(total_before["search_seconds"]) + float(total_before["fetch_seconds"])
        <= rescue_config.maximum_pre_rescue_retrieval_seconds
    )
    remaining = max(0, frozen_two_wave.wave1_fetches + frozen_two_wave.wave2_fetches - int(total_before["fetches_attempted"]))
    should_trigger = decision == "expand" and low and latency_ok and rescue["tail_candidates"] > 0 and remaining > 0
    expected_fetches = min(rescue_config.maximum_rescue_fetches, remaining, int(rescue["tail_candidates"])) if should_trigger else 0
    expected_reason = (
        "low_coverage_tail_available" if should_trigger else
        "controller_stop" if decision == "stop" else
        "coverage_sufficient" if not low else
        "latency_ceiling" if not latency_ok else
        "no_tail_or_remaining_budget"
    )
    if rescue["triggered"] != should_trigger or rescue["fetches_attempted"] != expected_fetches or rescue["reason"] != expected_reason:
        raise ValueError("V2.42.89 rescue trigger predicate drifted")
    for name in (
        "controller_search_invocations_before_rescue",
        "controller_search_invocations_after_rescue",
        "provider_search_calls_before_rescue",
        "provider_search_calls_after_rescue",
        "hosted_search_requests_added_by_rescue",
    ):
        _nonnegative_integer(value.get(name), label=name)
    if (
        int(rescue.get("fetches_attempted", -1)) > int(policy["maximum_rescue_fetches"])
        or int(total["queries_executed"]) != int(total_before["queries_executed"])
        or int(total["fetches_attempted"]) != int(total_before["fetches_attempted"]) + int(rescue["fetches_attempted"])
        or int(total["fetches_attempted"]) > 10
        or int(total["usable_pages"]) != int(total_before["usable_pages"]) + int(rescue["usable_pages"])
        or int(total["content_chars"]) != int(total_before["content_chars"]) + int(rescue["content_chars"])
        or (not rescue.get("triggered") and int(rescue["fetches_attempted"]) != 0)
        or (rescue.get("triggered") and value.get("controller", {}).get("decision") != "expand")
        or value["controller_search_invocations_before_rescue"]
        != value["controller_search_invocations_after_rescue"]
        or value["provider_search_calls_before_rescue"]
        != value["provider_search_calls_after_rescue"]
        or value["hosted_search_requests_added_by_rescue"] != 0
    ):
        raise ValueError("V2.42.89 rescue accounting drifted")


__all__ = [
    "POLICY_ID",
    "RescuePolicy",
    "run_low_coverage_rescue",
    "validate_receipt",
]
