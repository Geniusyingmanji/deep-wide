"""Fail-closed same-response citation-title backfill for task-union search.

Hosted Responses payloads can carry an empty title on an action source while a
``url_citation`` in the *same response* carries a title for the same canonical
URL.  The task-union transport keeps action sources when query-local citation
mapping fails, so losing that title can prevent a useful discovery lead from
passing a title-based selector.

This append-only successor changes only the copied action trace attached by the
multi-query single-shot transport.  An empty action title is filled iff exactly
one distinct, non-empty citation title exists for that canonical URL in the
same provider payload.  Existing titles, conflicting citation titles, invalid
URLs, other responses, and titles learned by a later page fetch are never used.
The provider payload and the frozen V2.42.80 implementation are not mutated.

The legacy ``single_shot_receipt`` remains byte-schema compatible for existing
proof validators.  A separate content-free receipt distinguishes transformed
action sources from backfilled sources that actually survive query-local-first
URL deduplication as task-union leads.  It contains counts only and adds no
search, fetch, model, process, evaluator, or credit effect.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import SearchRequestError, canonicalize_url
from .native_search import (
    NATIVE_SEARCH_PROVIDER,
    AzureNativeSearchClient,
    _response_text_and_annotations,
    _web_search_actions,
)
from .v24280_task_union_single_shot import (
    MAPPING_FAILURE,
    OMITTED_MARKER,
    TaskUnionSingleShotHardDeadlineNativeSearchClient,
    TaskUnionSingleShotNativeSearchClient,
)
from .v24468_total_wall_transport import HardTotalWallNativeSearchClient
from .v24470_bounded_adaptive_integration import (
    HardTotalWallUncertaintyNativeSearchClient,
)
from .v24474_nominal_hard_total_wall_search import (
    NominalCompatibleHardTotalWallUncertaintyNativeSearchClient,
    validate_compatibility_class,
)
from .v24391_uncertainty_active_evidence_runner import (
    UncertaintyDeadlineAwareNativeSearchClient,
)


POLICY_ID = "v24627_same_response_citation_title_backfill_v1"
RECEIPT_ROLE = "v24627_same_response_citation_title_backfill_receipt"
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
        "artifact_version",
        "role",
        "policy_id",
        *COUNT_FIELDS,
        "same_provider_response_only",
        "canonical_url_match_only",
        "unique_nonempty_citation_title_only",
        "existing_action_title_preserved",
        "conflicting_citation_titles_fail_closed",
        "provider_payload_mutated",
        "post_fetch_title_used",
        "cross_response_state_used",
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
    """Return response-local titles keyed by canonical URL.

    The same parser boundary used by native search supplies annotations.  A
    citation must have the existing native parser's integer offset shape, but
    need not map to a query section: that mapping failure is precisely the
    recoverable case for this successor.
    """

    _text, annotations = _response_text_and_annotations(dict(payload))
    values: dict[str, set[str]] = {}
    count = 0
    nonempty = 0
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
    payload: Mapping[str, Any],
    query_local_values: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    """Build a copied trace and classify which backfills survive union dedup."""

    actions = copy.deepcopy(_web_search_actions(dict(payload)))
    observation = {name: 0 for name in COUNT_FIELDS}
    observation["multi_query_payload_count"] = 1
    if not actions:
        return None, observation

    titles, citation_count, citation_nonempty = _citation_titles(payload)
    observation["citation_count"] = citation_count
    observation["citation_nonempty_title_count"] = citation_nonempty
    observation["conflicting_citation_url_count"] = sum(
        len(values) > 1 for values in titles.values()
    )

    backfilled_positions: set[tuple[int, int]] = set()
    backfilled_urls: set[str] = set()
    for action_index, action in enumerate(actions):
        sources = action.get("sources", []) or []
        for source_index, source in enumerate(sources):
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
            # The value is written only to the normalized deep copy returned by
            # _web_search_actions; the provider payload remains untouched.
            source["title"] = next(iter(candidates))[:500]
            backfilled_positions.add((action_index, source_index))
            backfilled_urls.add(url)
            observation["backfilled_action_source_count"] += 1

    observation["backfilled_unique_url_count"] = len(backfilled_urls)
    query_local_urls = {
        canonicalize_url(str(item.get("fetch_url") or item.get("url") or "").strip())
        for item in query_local_values
        if isinstance(item, Mapping)
    }
    query_local_urls.discard("")

    first_action_position: dict[str, tuple[int, int]] = {}
    for action_index, action in enumerate(actions):
        for source_index, source in enumerate(action.get("sources", []) or []):
            if not isinstance(source, Mapping):
                continue
            url = canonicalize_url(str(source.get("url", "")).strip())
            if url:
                first_action_position.setdefault(url, (action_index, source_index))

    for url in backfilled_urls:
        if url in query_local_urls:
            observation["query_local_shadowed_backfilled_url_count"] += 1
        elif first_action_position.get(url) in backfilled_positions:
            observation["surviving_backfilled_union_lead_count"] += 1
        else:
            observation["earlier_action_shadowed_backfilled_url_count"] += 1

    trace = {
        "response_id": str(payload.get("id", "")),
        "search_call_ids": [
            str(action.get("id", ""))
            for action in actions
            if str(action.get("id", ""))
        ],
        "actions": actions,
    }
    return trace, observation


def parse_same_response_citation_title_backfill(
    client: AzureNativeSearchClient,
    queries: Sequence[str],
    payload: Mapping[str, Any],
    *,
    max_results: int,
) -> tuple[list[dict[str, Any]], bool, int, int, dict[str, int]]:
    """Parse one native chunk and backfill only its copied multi-query trace."""

    logical_queries = list(queries)
    batches, complete = client._parse_batch(
        logical_queries, dict(payload), max_results=max_results
    )
    zero = {name: 0 for name in COUNT_FIELDS}
    if len(logical_queries) <= 1:
        return batches, complete, 0, 0, zero

    for batch in batches:
        batch.pop("hosted_search_trace", None)
    query_local_values = [
        result
        for batch in batches
        for result in (batch.get("results") or [])
        if isinstance(result, Mapping)
    ]
    trace, observation = _backfilled_action_trace(payload, query_local_values)
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


class SameResponseCitationTitleBackfillMixin:
    """Pre-fetch action-trace backfill with a legacy-compatible base receipt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name in COUNT_FIELDS:
            setattr(self, f"citation_backfill_{name}", 0)

    def _add_backfill_observation(self, value: Mapping[str, int]) -> None:
        for name in COUNT_FIELDS:
            self._increment(
                f"citation_backfill_{name}",
                int(value.get(name, 0)),
            )

    def _run_chunk(
        self, queries: list[str], max_results: int
    ) -> list[dict[str, Any]]:
        try:
            payload = self._request(queries)
            batches, complete, normalized, attachments, observation = (
                parse_same_response_citation_title_backfill(
                    self, queries, payload, max_results=max_results
                )
            )
        except SearchRequestError as exc:
            self._increment("failures", len(queries))
            return [
                {
                    "query": query,
                    "answer": "",
                    "results": [],
                    "error": str(exc),
                    "provider": NATIVE_SEARCH_PROVIDER,
                }
                for query in queries
            ]

        self._add_backfill_observation(observation)
        if len(queries) > 1:
            self._increment("multi_query_chunks")
            if not complete:
                self._increment("incomplete_mapping_chunks")
            self._increment("mapping_failure_rows_normalized", normalized)
            self._increment("action_trace_attachments", attachments)
        for batch in batches:
            if batch.get("error"):
                self._increment("failures")
        # Backfill is complete before this frozen fetch boundary.  Titles
        # learned by _enrich_pages therefore cannot enter the action trace.
        self._enrich_pages(batches)
        return batches

    def citation_title_backfill_receipt(self) -> dict[str, Any]:
        value = {
            "artifact_version": 1,
            "role": RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            **{
                name: int(getattr(self, f"citation_backfill_{name}"))
                for name in COUNT_FIELDS
            },
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


class SameResponseCitationTitleBackfillNativeSearchClient(
    SameResponseCitationTitleBackfillMixin,
    TaskUnionSingleShotNativeSearchClient,
):
    """Basic native-search successor for task-local source union."""


class SameResponseCitationTitleBackfillHardDeadlineNativeSearchClient(
    SameResponseCitationTitleBackfillMixin,
    TaskUnionSingleShotHardDeadlineNativeSearchClient,
):
    """Hard-fetch-deadline variant of the backfill successor."""


class SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient(
    SameResponseCitationTitleBackfillMixin,
    NominalCompatibleHardTotalWallUncertaintyNativeSearchClient,
):
    """Current bounded-worker nominal/hard-total-wall compatible successor."""


def validate_compatibility_successor() -> None:
    validate_compatibility_class()
    cls = SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient
    mro = cls.__mro__
    request_owner = next(base for base in mro if "_request" in base.__dict__)
    run_chunk_owner = next(base for base in mro if "_run_chunk" in base.__dict__)
    if (
        not issubclass(cls, NominalCompatibleHardTotalWallUncertaintyNativeSearchClient)
        or not issubclass(cls, HardTotalWallUncertaintyNativeSearchClient)
        or not issubclass(cls, UncertaintyDeadlineAwareNativeSearchClient)
        or request_owner is not HardTotalWallNativeSearchClient
        or run_chunk_owner is not SameResponseCitationTitleBackfillMixin
    ):
        raise RuntimeError("V2.46.27 compatibility successor MRO drifted")


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    for name in COUNT_FIELDS:
        amount = copied.get(name)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError(f"V2.46.27 {name} is invalid")
    true_fields = (
        "same_provider_response_only",
        "canonical_url_match_only",
        "unique_nonempty_citation_title_only",
        "existing_action_title_preserved",
        "conflicting_citation_titles_fail_closed",
    )
    false_fields = (
        "provider_payload_mutated",
        "post_fetch_title_used",
        "cross_response_state_used",
        "legacy_single_shot_receipt_changed",
        "additional_search_fetch_model_process_evaluator_or_credit_effect",
        "raw_task_question_query_url_title_page_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied["empty_action_source_count"]
        + copied["nonempty_action_source_preserved_count"]
        != copied["action_source_count"]
        or copied["citation_nonempty_title_count"] > copied["citation_count"]
        or copied["backfilled_action_source_count"]
        > copied["empty_action_source_count"]
        or copied["backfilled_unique_url_count"]
        > copied["backfilled_action_source_count"]
        or copied["surviving_backfilled_union_lead_count"]
        + copied["query_local_shadowed_backfilled_url_count"]
        + copied["earlier_action_shadowed_backfilled_url_count"]
        != copied["backfilled_unique_url_count"]
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.46.27 citation-title backfill receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS",
    "POLICY_ID",
    "SameResponseCitationTitleBackfillHardDeadlineNativeSearchClient",
    "SameResponseCitationTitleBackfillMixin",
    "SameResponseCitationTitleBackfillNativeSearchClient",
    "SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient",
    "parse_same_response_citation_title_backfill",
    "validate_compatibility_successor",
    "validate_receipt",
]
