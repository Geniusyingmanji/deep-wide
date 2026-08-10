"""Label-blind source-only batching primitives for a fresh external gate.

This module changes only the physical grouping of an already fixed visible
query vector.  It records whether provider action traces preserve every exact
query, selects a bounded first-seen URL union, builds fixed-budget evidence
from deterministic fetched pages, and conservatively normalizes a table.
It has no file, environment, subprocess, benchmark, gold, or evaluator access.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .native_search import _web_search_actions
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v25032_single_column_table_normalizer import normalize_candidate_table
from .v25036_source_only_hosted_search import (
    SourceOnlyRobustLatePageBoundSearchClient,
)


POLICY_ID = "v25038_source_only_query_batching_v1"
ARMS = ("split_2_plus_2", "one_shot_4")
QUERY_COUNT = 4
LEAD_CAP = 10
SPLIT_WAVE_CAPS = (6, 4)


def normalized_query(value: object) -> str:
    return " ".join(str(value).split()).strip()


def query_chunks(queries: Sequence[str], arm: str) -> tuple[tuple[str, ...], ...]:
    logical = tuple(normalized_query(value) for value in queries)
    if (
        len(logical) != QUERY_COUNT
        or any(not value or len(value) > 2_000 for value in logical)
        or len({value.casefold() for value in logical}) != QUERY_COUNT
        or arm not in ARMS
    ):
        raise ValueError("V2.50.38 query batching input drifted")
    chunks = (
        (logical[:2], logical[2:])
        if arm == "split_2_plus_2"
        else (logical,)
    )
    if tuple(value for chunk in chunks for value in chunk) != logical:
        raise RuntimeError("V2.50.38 query batching schedule drifted")
    return tuple(tuple(chunk) for chunk in chunks)


class ActionQueryObservedSourceOnlySearchClient(
    SourceOnlyRobustLatePageBoundSearchClient
):
    """Observe exact action-query coverage without retaining query values."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.observed_action_query_count = 0
        self.observed_exact_action_query_count = 0
        self.fully_observed_request_query_vectors = 0

    def _request(self, queries: list[str]) -> dict[str, Any]:
        payload = super()._request(queries)
        observed: set[str] = set()
        for action in _web_search_actions(payload):
            query = normalized_query(action.get("query"))
            if query:
                observed.add(query)
            observed.update(
                item
                for value in action.get("queries") or []
                if (item := normalized_query(value))
            )
        expected = {normalized_query(value) for value in queries}
        exact = expected.intersection(observed)
        self._increment("observed_action_query_count", len(observed))
        self._increment("observed_exact_action_query_count", len(exact))
        self._increment(
            "fully_observed_request_query_vectors", int(exact == expected)
        )
        return payload


def run_search_arm(
    client: ActionQueryObservedSourceOnlySearchClient,
    queries: Sequence[str],
    arm: str,
    *,
    max_results: int = 3,
    lead_cap: int = LEAD_CAP,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if lead_cap <= 0 or lead_cap > 20 or max_results <= 0 or max_results > 10:
        raise ValueError("V2.50.38 search cap drifted")
    union = TaskUnionDiscoverySearchClient(client)
    discovered: list[dict[str, str]] = []
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for chunk_index, chunk in enumerate(query_chunks(queries, arm)):
        wave: list[dict[str, str]] = []
        batches = union.search_many(
            chunk,
            max_results=max_results,
            search_depth="advanced",
            include_raw_content=False,
        )
        for batch in batches:
            if not isinstance(batch, Mapping):
                continue
            for raw in batch.get("results") or []:
                if not isinstance(raw, Mapping):
                    continue
                fetch_url = str(raw.get("fetch_url") or raw.get("url") or "").strip()
                url = canonicalize_url(fetch_url)
                if not url or url in seen:
                    continue
                seen.add(url)
                lead = (
                    {
                        "url": url,
                        "fetch_url": fetch_url,
                        "title": str(raw.get("title") or "")[:500],
                    }
                )
                discovered.append(lead)
                wave.append(lead)
        wave_cap = SPLIT_WAVE_CAPS[chunk_index] if arm == "split_2_plus_2" else lead_cap
        selected.extend(wave[:wave_cap])
    leads = selected[:lead_cap]
    receipt = union.receipt()
    observation = {
        "arm": arm,
        "logical_query_count": int(receipt["logical_query_count"]),
        "raw_query_local_result_count": int(
            receipt["raw_query_local_result_count"]
        ),
        "raw_action_source_count": int(receipt["raw_action_source_count"]),
        "raw_mapping_failure_count": int(
            receipt["raw_query_local_mapping_failure_count"]
        ),
        "raw_unrecoverable_failure_count": int(
            receipt["raw_unrecoverable_failure_count"]
        ),
        "union_source_count": int(receipt["union_source_count"]),
        "selected_lead_count": len(leads),
        "provider_calls": int(client.calls),
        "provider_attempts": int(client.hosted_search_attempts),
        "tool_calls": int(client.tool_calls),
        "input_tokens": int(client.input_tokens),
        "output_tokens": int(client.output_tokens),
        "total_tokens": int(client.total_tokens),
        "observed_action_query_count": int(client.observed_action_query_count),
        "observed_exact_action_query_count": int(
            client.observed_exact_action_query_count
        ),
        "fully_observed_request_query_vectors": int(
            client.fully_observed_request_query_vectors
        ),
        "recursive_split_requests": int(client.recursive_split_requests),
        "transport_failures": int(client.transport_failures),
        "hard_total_wall_timeouts": int(client.hard_total_wall_timeouts),
    }
    validate_search_observation(observation)
    return leads, observation


def validate_search_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    numeric = set(copied).difference({"arm"})
    if (
        copied.get("arm") not in ARMS
        or numeric
        != {
            "logical_query_count", "raw_query_local_result_count",
            "raw_action_source_count", "raw_mapping_failure_count",
            "raw_unrecoverable_failure_count", "union_source_count",
            "selected_lead_count", "provider_calls", "provider_attempts",
            "tool_calls", "input_tokens", "output_tokens", "total_tokens",
            "observed_action_query_count", "observed_exact_action_query_count",
            "fully_observed_request_query_vectors", "recursive_split_requests",
            "transport_failures", "hard_total_wall_timeouts",
        }
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in numeric
        )
        or copied["selected_lead_count"] > LEAD_CAP
        or copied["observed_exact_action_query_count"] > QUERY_COUNT
    ):
        raise ValueError("V2.50.38 search observation drifted")
    return copied


def shared_fetch_requests(
    arm_leads: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    arm_order: Sequence[str] = ARMS,
) -> list[dict[str, str]]:
    if set(arm_leads) != set(ARMS) or tuple(arm_order) not in {ARMS, ARMS[::-1]}:
        raise ValueError("V2.50.38 arm lead map drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for arm in arm_order:
        for lead in arm_leads[arm]:
            fetch_url = str(lead.get("fetch_url") or lead.get("url") or "").strip()
            url = canonicalize_url(fetch_url)
            if not url or url in seen:
                continue
            seen.add(url)
            output.append(
                {
                    "url": fetch_url,
                    "query": "shared source-only batching external fetch",
                    "title": str(lead.get("title") or "")[:500],
                    "member_label": "",
                }
            )
    return output


def fetched_page_map(batches: object) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return output
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        for result in batch.get("results") or []:
            if not isinstance(result, Mapping):
                continue
            requested = canonicalize_url(
                str(
                    result.get("requested_url")
                    or result.get("fetch_url")
                    or result.get("url")
                    or ""
                )
            )
            if requested:
                output[requested] = dict(result)
    return output


def build_fixed_evidence(
    leads: Sequence[Mapping[str, Any]],
    fetched: Mapping[str, Mapping[str, Any]],
    *,
    character_budget: int,
    minimum_usable_pages: int,
    minimum_raw_characters: int,
) -> tuple[str | None, dict[str, int]]:
    if (
        character_budget <= 0
        or character_budget > 100_000
        or minimum_usable_pages <= 0
        or minimum_raw_characters <= 0
    ):
        raise ValueError("V2.50.38 evidence budget drifted")
    sections: list[str] = []
    usable = raw_chars = 0
    for lead in leads:
        url = canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
        page = fetched.get(url) or {}
        text = str(page.get("raw_content") or page.get("content") or "").strip()
        if not text:
            continue
        usable += 1
        raw_chars += len(text)
        title = " ".join(str(page.get("title") or "Fetched page").split())
        sections.append(f"[PAGE {usable}]\nTITLE: {title}\nCONTENT:\n{text}\n")
    joined = "\n".join(sections)
    ready = usable >= minimum_usable_pages and raw_chars >= minimum_raw_characters
    evidence = joined[:character_budget] if ready else None
    observation = {
        "usable_pages": usable,
        "raw_characters": raw_chars,
        "evidence_characters": len(evidence or ""),
        "fixed_budget_filled": int(
            evidence is not None and len(evidence) == character_budget
        ),
    }
    return evidence, observation


def synthesis_prompt(question: str, evidence: str) -> tuple[str, str]:
    system = (
        "Use only the supplied fetched-page text. Return exactly one Markdown "
        "table and no prose. Do not cite URLs, add columns, or add rows. Use "
        "Unknown only when the supplied pages do not establish a requested value."
    )
    user = "VISIBLE TASK:\n" + str(question) + "\n\nFETCHED PAGES:\n" + str(evidence)
    return system, user


def normalize_prediction(
    raw: str,
    columns: Sequence[str],
    *,
    fallback: str,
) -> tuple[str, str]:
    normalized, diagnostics = normalize_candidate_table(
        str(raw), columns, unknown_marker="Unknown"
    )
    if normalized is None:
        return str(fallback), "fallback"
    return normalized, str(diagnostics["status"])


__all__ = [
    "ARMS", "ActionQueryObservedSourceOnlySearchClient", "LEAD_CAP",
    "POLICY_ID", "QUERY_COUNT", "SPLIT_WAVE_CAPS", "build_fixed_evidence", "fetched_page_map",
    "normalize_prediction", "normalized_query", "query_chunks",
    "run_search_arm", "shared_fetch_requests", "synthesis_prompt",
    "validate_search_observation",
]
