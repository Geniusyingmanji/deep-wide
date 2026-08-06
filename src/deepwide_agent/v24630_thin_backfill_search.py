"""Thin hard-total-wall implementation of same-response title backfill.

This exact-220 surface implements the V2.46.27 transformation without
importing the later uncertainty/targeted-support compatibility stack.  It
fills an empty copied action-source title only when the same provider response
contains exactly one non-empty citation title for the same canonical URL.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import SearchRequestError, canonicalize_url
from .native_search import (
    NATIVE_SEARCH_PROVIDER,
    _response_text_and_annotations,
    _web_search_actions,
)
from .v24280_task_union_single_shot import (
    MAPPING_FAILURE,
    OMITTED_MARKER,
    TaskUnionSingleShotMixin,
)
from .v24468_total_wall_transport import HardTotalWallNativeSearchClient


POLICY_ID = "v24630_thin_same_response_citation_title_backfill_v1"
RECEIPT_ROLE = "v24630_thin_same_response_citation_title_backfill_receipt"
COUNT_FIELDS = (
    "multi_query_payload_count",
    "action_source_count",
    "empty_action_source_count",
    "nonempty_action_source_preserved_count",
    "citation_count",
    "citation_nonempty_title_count",
    "conflicting_citation_url_count",
    "backfilled_action_source_count",
    "backfilled_unique_url_count",
    "surviving_backfilled_union_lead_count",
    "query_local_shadowed_backfilled_url_count",
    "earlier_action_shadowed_backfilled_url_count",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version", "role", "policy_id", *COUNT_FIELDS,
        "same_provider_response_only", "canonical_url_match_only",
        "unique_nonempty_citation_title_only", "existing_action_title_preserved",
        "conflicting_citation_titles_fail_closed", "provider_payload_mutated",
        "post_fetch_title_used", "cross_response_state_used",
        "legacy_single_shot_receipt_changed",
        "additional_search_fetch_model_process_evaluator_or_credit_effect",
        "raw_task_question_query_url_title_page_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _title(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _citation_titles(payload: Mapping[str, Any]) -> tuple[dict[str, set[str]], int, int]:
    _text, annotations = _response_text_and_annotations(dict(payload))
    values: dict[str, set[str]] = {}
    count = nonempty = 0
    for annotation in annotations:
        if not isinstance(annotation, Mapping) or annotation.get("type") != "url_citation":
            continue
        try:
            int(annotation["start_index"])
            int(annotation["end_index"])
        except (KeyError, TypeError, ValueError):
            continue
        url = canonicalize_url(str(annotation.get("url", "")).strip())
        if not url:
            continue
        title = _title(annotation.get("title"))
        count += 1
        nonempty += int(bool(title))
        if title:
            values.setdefault(url, set()).add(title)
    return values, count, nonempty


def _backfilled_action_trace(
    payload: Mapping[str, Any], query_local_values: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    actions = copy.deepcopy(_web_search_actions(dict(payload)))
    observation = {name: 0 for name in COUNT_FIELDS}
    observation["multi_query_payload_count"] = 1
    if not actions:
        return None, observation
    titles, citations, nonempty = _citation_titles(payload)
    observation["citation_count"] = citations
    observation["citation_nonempty_title_count"] = nonempty
    observation["conflicting_citation_url_count"] = sum(
        len(value) > 1 for value in titles.values()
    )
    positions: set[tuple[int, int]] = set()
    urls: set[str] = set()
    for action_index, action in enumerate(actions):
        for source_index, source in enumerate(action.get("sources", []) or []):
            if not isinstance(source, dict):
                continue
            observation["action_source_count"] += 1
            if _title(source.get("title")):
                observation["nonempty_action_source_preserved_count"] += 1
                continue
            observation["empty_action_source_count"] += 1
            url = canonicalize_url(str(source.get("url", "")).strip())
            candidates = titles.get(url, set()) if url else set()
            if len(candidates) != 1:
                continue
            source["title"] = next(iter(candidates))[:500]
            positions.add((action_index, source_index))
            urls.add(url)
            observation["backfilled_action_source_count"] += 1
    observation["backfilled_unique_url_count"] = len(urls)
    local_urls = {
        canonicalize_url(str(item.get("fetch_url") or item.get("url") or "").strip())
        for item in query_local_values if isinstance(item, Mapping)
    } - {""}
    first: dict[str, tuple[int, int]] = {}
    for action_index, action in enumerate(actions):
        for source_index, source in enumerate(action.get("sources", []) or []):
            if isinstance(source, Mapping):
                url = canonicalize_url(str(source.get("url", "")).strip())
                if url:
                    first.setdefault(url, (action_index, source_index))
    for url in urls:
        if url in local_urls:
            observation["query_local_shadowed_backfilled_url_count"] += 1
        elif first.get(url) in positions:
            observation["surviving_backfilled_union_lead_count"] += 1
        else:
            observation["earlier_action_shadowed_backfilled_url_count"] += 1
    return {
        "response_id": str(payload.get("id", "")),
        "search_call_ids": [
            str(action.get("id", "")) for action in actions if str(action.get("id", ""))
        ],
        "actions": actions,
    }, observation


def parse_same_response_citation_title_backfill(
    client: Any, queries: Sequence[str], payload: Mapping[str, Any], *, max_results: int
) -> tuple[list[dict[str, Any]], bool, int, int, dict[str, int]]:
    logical = list(queries)
    batches, complete = client._parse_batch(logical, dict(payload), max_results=max_results)
    zero = {name: 0 for name in COUNT_FIELDS}
    if len(logical) <= 1:
        return batches, complete, 0, 0, zero
    for batch in batches:
        batch.pop("hosted_search_trace", None)
    local = [
        result for batch in batches for result in (batch.get("results") or [])
        if isinstance(result, Mapping)
    ]
    trace, observation = _backfilled_action_trace(payload, local)
    attachments = 0
    if trace is not None and batches:
        batches[0]["hosted_search_trace"] = trace
        attachments = 1
    normalized = 0
    if not complete:
        for batch in batches:
            if not batch.get("results") and batch.get("error") == OMITTED_MARKER:
                batch["error"] = MAPPING_FAILURE
                normalized += 1
    return batches, complete, normalized, attachments, observation


class ThinSameResponseCitationTitleBackfillMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name in COUNT_FIELDS:
            setattr(self, f"citation_backfill_{name}", 0)

    def _run_chunk(self, queries: list[str], max_results: int) -> list[dict[str, Any]]:
        try:
            payload = self._request(queries)
            batches, complete, normalized, attachments, observation = (
                parse_same_response_citation_title_backfill(
                    self, queries, payload, max_results=max_results
                )
            )
        except SearchRequestError as error:
            self._increment("failures", len(queries))
            return [
                {"query": query, "answer": "", "results": [], "error": str(error),
                 "provider": NATIVE_SEARCH_PROVIDER}
                for query in queries
            ]
        for name in COUNT_FIELDS:
            self._increment(f"citation_backfill_{name}", int(observation.get(name, 0)))
        if len(queries) > 1:
            self._increment("multi_query_chunks")
            if not complete:
                self._increment("incomplete_mapping_chunks")
            self._increment("mapping_failure_rows_normalized", normalized)
            self._increment("action_trace_attachments", attachments)
        for batch in batches:
            if batch.get("error"):
                self._increment("failures")
        self._enrich_pages(batches)
        return batches

    def citation_title_backfill_receipt(self) -> dict[str, Any]:
        value = {
            "artifact_version": 1, "role": RECEIPT_ROLE, "policy_id": POLICY_ID,
            **{name: int(getattr(self, f"citation_backfill_{name}")) for name in COUNT_FIELDS},
            "same_provider_response_only": True,
            "canonical_url_match_only": True,
            "unique_nonempty_citation_title_only": True,
            "existing_action_title_preserved": True,
            "conflicting_citation_titles_fail_closed": True,
            "provider_payload_mutated": False,
            "post_fetch_title_used": False,
            "cross_response_state_used": False,
            "legacy_single_shot_receipt_changed": False,
            "additional_search_fetch_model_process_evaluator_or_credit_effect": False,
            "raw_task_question_query_url_title_page_prediction_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        return validate_receipt(value)


class ThinSameResponseCitationTitleBackfillSearchClient(
    ThinSameResponseCitationTitleBackfillMixin,
    TaskUnionSingleShotMixin,
    HardTotalWallNativeSearchClient,
):
    """Minimal hard-total-wall task-union title-backfill search."""


def validate_thin_search_class() -> None:
    cls = ThinSameResponseCitationTitleBackfillSearchClient
    request_owner = next(base for base in cls.__mro__ if "_request" in base.__dict__)
    chunk_owner = next(base for base in cls.__mro__ if "_run_chunk" in base.__dict__)
    if (
        request_owner is not HardTotalWallNativeSearchClient
        or chunk_owner is not ThinSameResponseCitationTitleBackfillMixin
        or not issubclass(cls, TaskUnionSingleShotMixin)
    ):
        raise RuntimeError("V2.46.30 thin backfill-search MRO drifted")


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    for name in COUNT_FIELDS:
        amount = copied.get(name)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError(f"V2.46.30 {name} is invalid")
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied["empty_action_source_count"] + copied["nonempty_action_source_preserved_count"]
        != copied["action_source_count"]
        or copied["citation_nonempty_title_count"] > copied["citation_count"]
        or copied["backfilled_action_source_count"] > copied["empty_action_source_count"]
        or copied["backfilled_unique_url_count"] > copied["backfilled_action_source_count"]
        or copied["surviving_backfilled_union_lead_count"]
        + copied["query_local_shadowed_backfilled_url_count"]
        + copied["earlier_action_shadowed_backfilled_url_count"]
        != copied["backfilled_unique_url_count"]
        or any(copied.get(name) is not True for name in (
            "same_provider_response_only", "canonical_url_match_only",
            "unique_nonempty_citation_title_only", "existing_action_title_preserved",
            "conflicting_citation_titles_fail_closed"))
        or any(copied.get(name) is not False for name in (
            "provider_payload_mutated", "post_fetch_title_used", "cross_response_state_used",
            "legacy_single_shot_receipt_changed",
            "additional_search_fetch_model_process_evaluator_or_credit_effect",
            "raw_task_question_query_url_title_page_prediction_or_credential_emitted",
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
            "benchmark_launch_or_evaluator_authorized"))
    ):
        raise ValueError("V2.46.30 thin backfill receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS", "POLICY_ID", "ThinSameResponseCitationTitleBackfillSearchClient",
    "parse_same_response_citation_title_backfill", "validate_receipt",
    "validate_thin_search_class",
]
