"""Equal-budget staged fetch fallback for visible-entity evidence recovery.

V2.47.77 found that 24 of 80 selected URL fetches produced no usable page,
while many under-covered visible entities still had an unfetched,
title-or-URL-aligned source in the already-returned search response.  This
append-only successor changes only acquisition scheduling:

* preserve the same two model calls, four logical queries, one search effect,
  and at most ten distinct URL fetch targets;
* fetch the first eight entity-fair leads;
* inspect successful page text only for exact visible-identity presence;
* spend at most two remaining slots on previously unfetched, registrably-new,
  exact-aligned sources for the lowest-covered visible entities;
* never retry a failed URL and never route on a field, candidate value,
  benchmark label, ground truth, score, reward, or evaluator output.

The frozen V2.43.65 semantic projector and strict two-independent-source
support gate remain unchanged.  Thus this is one acquisition intervention,
not a parser-plus-retrieval bundle.  Runtime input remains exactly
``{opaque_id, question}``.
"""

from __future__ import annotations

import copy
import hashlib
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24365_entity_segment_projection import (
    build_target_segment_catalog,
    validate_target_segment_catalog,
)
from .v24743_generic_record_binding import _source_key
from .v24756_zero_effect_structured_integration import (
    _adapter_pages,
    run_v24756_task,
    validate_result as validate_parent_result,
)
from . import v24770_visible_entity_fair_semantic_runtime as semantic


POLICY_ID = "v24778_staged_visible_entity_fetch_fallback_v1"
ROLE = "v24778_staged_fetch_fallback_task_result"
SCHEDULER_ROLE = "v24778_staged_fetch_fallback_scheduler_receipt"
ARMS = ("baseline", "staged_fallback_semantic")
INITIAL_FETCH_CAP = 8
RESERVE_FETCH_CAP = 2
FETCH_TARGET_CAP = INITIAL_FETCH_CAP + RESERVE_FETCH_CAP
VISIBLE_ENTITY_COUNT = semantic.VISIBLE_ENTITY_COUNT
LOGICAL_QUERY_COUNT = semantic.LOGICAL_QUERY_COUNT
EXPECTED_COLUMNS = semantic.EXPECTED_COLUMNS
STATE_KEYS = frozenset(
    {
        "visible_entities",
        "entity_queries",
        "input_leads",
        "provisional_leads",
        "initial_fetch_requests",
        "reserve_fetch_requests",
        "actual_fetch_requests",
        "initial_identity_sources",
        "reserve_identity_sources",
        "initial_replay_bindings",
        "reserve_replay_bindings",
        "search_invocation_count",
        "outer_fetch_invocation_count",
        "underlying_fetch_batch_count",
        "planner_query_count",
        "raw_batch_count",
        "query_local_result_count",
        "action_source_count",
        "provider_search_failure_count",
        "initial_usable_page_count",
        "reserve_usable_page_count",
        "initial_fetch_exception_count",
        "reserve_fetch_exception_count",
    }
)
COUNT_FIELDS = (
    "search_invocation_count",
    "outer_fetch_invocation_count",
    "underlying_fetch_batch_count",
    "planner_query_count",
    "raw_batch_count",
    "query_local_result_count",
    "action_source_count",
    "provider_search_failure_count",
    "input_unique_url_count",
    "input_independent_source_count",
    "provisional_fetch_lead_count",
    "provisional_unique_source_count",
    "initial_fetch_request_count",
    "reserve_fetch_request_count",
    "actual_fetch_request_count",
    "initial_usable_page_count",
    "reserve_usable_page_count",
    "actual_usable_page_count",
    "initial_fetch_exception_count",
    "reserve_fetch_exception_count",
    "initial_entities_with_zero_usable_identity_sources",
    "initial_entities_with_one_usable_identity_source",
    "initial_entities_with_two_or_more_usable_identity_sources",
    "final_entities_with_zero_usable_identity_sources",
    "final_entities_with_one_usable_identity_source",
    "final_entities_with_two_or_more_usable_identity_sources",
    "reserve_target_entity_count",
    "reserve_replaced_provisional_tail_count",
    "failed_url_retry_count",
)
VECTOR_FIELDS = (
    "initial_usable_identity_source_count_vector",
    "reserve_usable_identity_source_count_vector",
    "final_usable_identity_source_count_vector",
    "provisional_aligned_source_count_vector",
    "reserve_candidate_source_count_vector",
    "reserve_request_alignment_count_vector",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "visible_entity_count",
        "logical_query_cap",
        "fetch_target_cap",
        "initial_fetch_cap",
        "reserve_fetch_cap",
        *COUNT_FIELDS,
        *VECTOR_FIELDS,
        "generated_query_vector_has_one_query_per_visible_entity",
        "all_generated_entity_queries_submitted_when_search_invoked",
        "planner_queries_forwarded_to_search",
        "query_text_used_to_establish_alignment",
        "exact_full_visible_entity_surface_required_for_alignment",
        "title_and_normalized_url_host_path_used_for_alignment",
        "initial_success_page_text_used_for_reserve_routing_only_via_exact_visible_identity_coverage",
        "field_label_candidate_value_or_model_judgment_used_for_reserve_routing",
        "reserve_leads_come_from_same_preexisting_search_response",
        "reserve_urls_previously_unfetched",
        "reserve_sources_registrably_new_against_initial_requests",
        "reserve_sources_registrably_new_against_initial_successful_identity_sources",
        "failed_url_retried",
        "same_model_query_and_total_fetch_target_caps_as_parent",
        "strict_two_independent_same_value_gate_changed",
        "question_query_entity_title_url_host_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "parent_result",
        "predictions",
        "prediction_sha256",
        "scheduler_receipt",
        "semantic_receipt",
        "private_visible_entities",
        "private_visible_task",
        "private_scheduler_state",
        "private_semantic_catalog",
        "private_content_emitted_to_public_receipts",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "result_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return semantic.payload_sha256(value)


def _entity_pattern(entity: str) -> re.Pattern[str]:
    needle = unicodedata.normalize("NFKC", str(entity)).strip()
    if len(needle) < 2:
        raise ValueError("V2.47.78 visible identity is too short")
    return re.compile(rf"(?<![\w]){re.escape(needle)}(?![\w])", re.IGNORECASE)


def _entity_hits(content: str, entities: Sequence[str]) -> set[int]:
    text = unicodedata.normalize("NFKC", str(content))
    return {
        index
        for index, entity in enumerate(entities)
        if _entity_pattern(str(entity)).search(text)
    }


def _lead_url(lead: Mapping[str, Any]) -> str:
    value = canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
    if not value:
        raise ValueError("V2.47.78 lead URL is invalid")
    return value


def _fetch_request(lead: Mapping[str, Any]) -> dict[str, str]:
    return {
        "url": str(lead.get("fetch_url") or lead.get("url") or ""),
        "query": "visible-entity staged fallback",
        "title": str(lead.get("title", ""))[:500],
        "member_label": "",
    }


def _validate_fetched_batches(
    batches: object, *, requests: Sequence[Mapping[str, Any]]
) -> None:
    """Require every returned content page to name an authorized request URL."""

    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        raise ValueError("V2.47.78 fetch batch vector drifted")
    allowed = {_lead_url(request) for request in requests}
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        results = batch.get("results") or []
        if not isinstance(results, Sequence) or isinstance(results, (str, bytes)):
            continue
        for result in results:
            if not isinstance(result, Mapping):
                continue
            content = str(result.get("raw_content") or result.get("content") or "").strip()
            if not content:
                continue
            requested = canonicalize_url(
                str(result.get("requested_url") or result.get("fetch_url") or "")
            )
            if requested not in allowed:
                raise ValueError("V2.47.78 fetched page escaped authorized requests")


def _replay_binding(page: Mapping[str, Any]) -> dict[str, str]:
    final_url = canonicalize_url(str(page.get("final_url") or ""))
    content = str(page.get("content") or "")
    if not final_url or not content or page.get("fetch_integrity") is not True:
        raise ValueError("V2.47.78 replay page binding drifted")
    return {
        "final_url_sha256": hashlib.sha256(final_url.encode()).hexdigest(),
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
    }


def _identity_sources_from_replay(
    pages: Sequence[Mapping[str, Any]], entities: Sequence[str]
) -> list[list[str]]:
    sources: list[set[str]] = [set() for _ in entities]
    for page in pages:
        final_url = canonicalize_url(str(page.get("final_url") or ""))
        host = (urlsplit(final_url).hostname or "").casefold().strip(".")
        source = _source_key(host)
        for index in _entity_hits(str(page.get("content") or ""), entities):
            sources[index].add(source)
    return [sorted(values) for values in sources]


def select_staged_reserve_leads(
    leads: object,
    *,
    entities: Sequence[str],
    initial_requests: Sequence[Mapping[str, Any]],
    initial_identity_sources: Sequence[Sequence[str]],
    limit: int = RESERVE_FETCH_CAP,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Select unfetched exact-aligned sources for lowest successful coverage."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 0 <= limit <= RESERVE_FETCH_CAP
        or isinstance(entities, (str, bytes))
        or len(entities) != VISIBLE_ENTITY_COUNT
        or len(initial_identity_sources) != VISIBLE_ENTITY_COUNT
        or any(
            isinstance(values, (str, bytes))
            or any(not str(source).strip() for source in values)
            for values in initial_identity_sources
        )
    ):
        raise ValueError("V2.47.78 staged reserve configuration drifted")
    values = semantic._normalized_leads(leads)
    initial_urls = {_lead_url(lead) for lead in initial_requests}
    initial_sources = {
        semantic._lead_source(lead) for lead in initial_requests
    }.union(
        str(source)
        for values in initial_identity_sources
        for source in values
    )
    buckets: list[list[dict[str, str]]] = []
    candidate_counts: list[int] = []
    for entity in entities:
        by_source: dict[str, tuple[tuple[Any, ...], dict[str, str]]] = {}
        for lead in values:
            if _lead_url(lead) in initial_urls:
                continue
            source = semantic._lead_source(lead)
            if source in initial_sources:
                continue
            title_hit, url_hit = semantic._exact_alignment(lead, str(entity))
            if not (title_hit or url_hit):
                continue
            rank = (not title_hit, not url_hit, source, lead["url"], lead["title"])
            current = by_source.get(source)
            if current is None or rank < current[0]:
                by_source[source] = (rank, lead)
        ranked = [copy.deepcopy(item[1]) for item in sorted(by_source.values())]
        buckets.append(ranked)
        candidate_counts.append(len(ranked))

    coverage = [len(set(str(source) for source in values)) for values in initial_identity_sources]
    selected: list[dict[str, str]] = []
    selected_urls: set[str] = set()
    selected_sources: set[str] = set()
    assignments = [0] * len(entities)
    while len(selected) < limit:
        choices = [
            (
                coverage[entity_index] + assignments[entity_index],
                coverage[entity_index],
                entity_index,
                choice,
            )
            for entity_index in range(len(entities))
            if (
                choice := next(
                    (
                        lead
                        for lead in buckets[entity_index]
                        if _lead_url(lead) not in selected_urls
                        and semantic._lead_source(lead) not in selected_sources
                    ),
                    None,
                )
            )
            is not None
        ]
        if not choices:
            break
        _projected, _initial, entity_index, choice = min(
            choices, key=lambda item: (item[0], item[1], item[2])
        )
        selected.append(copy.deepcopy(choice))
        selected_urls.add(_lead_url(choice))
        selected_sources.add(semantic._lead_source(choice))
        assignments[entity_index] += 1
    return selected, {
        "initial_coverage_count_vector": coverage,
        "reserve_candidate_source_count_vector": candidate_counts,
        "reserve_request_alignment_count_vector": assignments,
    }


def _coverage_counts(vector: Sequence[int], prefix: str) -> dict[str, int]:
    counts = Counter(vector)
    return {
        f"{prefix}_entities_with_zero_usable_identity_sources": counts[0],
        f"{prefix}_entities_with_one_usable_identity_source": counts[1],
        f"{prefix}_entities_with_two_or_more_usable_identity_sources": sum(
            amount for coverage, amount in counts.items() if coverage >= 2
        ),
    }


def _scheduler_receipt(state: Mapping[str, Any]) -> dict[str, Any]:
    if set(state) != STATE_KEYS:
        raise ValueError("V2.47.78 private scheduler state drifted")
    entities = [str(value) for value in state["visible_entities"]]
    if len(entities) != VISIBLE_ENTITY_COUNT:
        raise ValueError("V2.47.78 private visible entity count drifted")
    provisional, provisional_diagnostic = semantic.select_visible_entity_fair_leads(
        state["input_leads"], entities=entities, limit=FETCH_TARGET_CAP
    )
    if provisional != state["provisional_leads"]:
        raise ValueError("V2.47.78 provisional lead replay drifted")
    initial = list(state["initial_fetch_requests"])
    if initial != provisional[: min(INITIAL_FETCH_CAP, len(provisional))]:
        raise ValueError("V2.47.78 initial request replay drifted")
    reserve_limit = min(
        RESERVE_FETCH_CAP, max(0, len(provisional) - len(initial))
    )
    candidate_reserve, reserve_diagnostic = select_staged_reserve_leads(
        state["input_leads"],
        entities=entities,
        initial_requests=initial,
        initial_identity_sources=state["initial_identity_sources"],
        limit=reserve_limit,
    )
    reserve = (
        []
        if int(state["initial_fetch_exception_count"]) > 0
        else candidate_reserve
    )
    if reserve != state["reserve_fetch_requests"]:
        raise ValueError("V2.47.78 reserve request replay drifted")
    actual = [*initial, *reserve]
    if actual != state["actual_fetch_requests"]:
        raise ValueError("V2.47.78 actual request replay drifted")
    initial_sources = [set(values) for values in state["initial_identity_sources"]]
    reserve_sources = [set(values) for values in state["reserve_identity_sources"]]
    initial_vector = [len(values) for values in initial_sources]
    reserve_vector = [len(values) for values in reserve_sources]
    final_vector = [
        len(initial_sources[index].union(reserve_sources[index]))
        for index in range(VISIBLE_ENTITY_COUNT)
    ]
    reserve_alignment = (
        [0] * VISIBLE_ENTITY_COUNT
        if int(state["initial_fetch_exception_count"]) > 0
        else list(reserve_diagnostic["reserve_request_alignment_count_vector"])
    )
    provisional_tail = {_lead_url(lead) for lead in provisional[INITIAL_FETCH_CAP:]}
    replaced_tail = sum(_lead_url(lead) not in provisional_tail for lead in reserve)
    reserve_target_count = sum(value > 0 for value in reserve_alignment)
    value = {
        "artifact_version": 1,
        "role": SCHEDULER_ROLE,
        "policy_id": POLICY_ID,
        "visible_entity_count": VISIBLE_ENTITY_COUNT,
        "logical_query_cap": LOGICAL_QUERY_COUNT,
        "fetch_target_cap": FETCH_TARGET_CAP,
        "initial_fetch_cap": INITIAL_FETCH_CAP,
        "reserve_fetch_cap": RESERVE_FETCH_CAP,
        "search_invocation_count": int(state["search_invocation_count"]),
        "outer_fetch_invocation_count": int(state["outer_fetch_invocation_count"]),
        "underlying_fetch_batch_count": int(state["underlying_fetch_batch_count"]),
        "planner_query_count": int(state["planner_query_count"]),
        "raw_batch_count": int(state["raw_batch_count"]),
        "query_local_result_count": int(state["query_local_result_count"]),
        "action_source_count": int(state["action_source_count"]),
        "provider_search_failure_count": int(state["provider_search_failure_count"]),
        "input_unique_url_count": len(semantic._normalized_leads(state["input_leads"])),
        "input_independent_source_count": len(
            {semantic._lead_source(lead) for lead in semantic._normalized_leads(state["input_leads"])}
        ),
        "provisional_fetch_lead_count": len(provisional),
        "provisional_unique_source_count": len(
            {semantic._lead_source(lead) for lead in provisional}
        ),
        "initial_fetch_request_count": len(initial),
        "reserve_fetch_request_count": len(reserve),
        "actual_fetch_request_count": len(actual),
        "initial_usable_page_count": int(state["initial_usable_page_count"]),
        "reserve_usable_page_count": int(state["reserve_usable_page_count"]),
        "actual_usable_page_count": int(state["initial_usable_page_count"])
        + int(state["reserve_usable_page_count"]),
        "initial_fetch_exception_count": int(state["initial_fetch_exception_count"]),
        "reserve_fetch_exception_count": int(state["reserve_fetch_exception_count"]),
        **_coverage_counts(initial_vector, "initial"),
        **_coverage_counts(final_vector, "final"),
        "reserve_target_entity_count": reserve_target_count,
        "reserve_replaced_provisional_tail_count": replaced_tail,
        "failed_url_retry_count": 0,
        "initial_usable_identity_source_count_vector": initial_vector,
        "reserve_usable_identity_source_count_vector": reserve_vector,
        "final_usable_identity_source_count_vector": final_vector,
        "provisional_aligned_source_count_vector": list(
            provisional_diagnostic["selected_aligned_source_count_vector"]
        ),
        "reserve_candidate_source_count_vector": list(
            reserve_diagnostic["reserve_candidate_source_count_vector"]
        ),
        "reserve_request_alignment_count_vector": reserve_alignment,
        "generated_query_vector_has_one_query_per_visible_entity": True,
        "all_generated_entity_queries_submitted_when_search_invoked": True,
        "planner_queries_forwarded_to_search": False,
        "query_text_used_to_establish_alignment": False,
        "exact_full_visible_entity_surface_required_for_alignment": True,
        "title_and_normalized_url_host_path_used_for_alignment": True,
        "initial_success_page_text_used_for_reserve_routing_only_via_exact_visible_identity_coverage": True,
        "field_label_candidate_value_or_model_judgment_used_for_reserve_routing": False,
        "reserve_leads_come_from_same_preexisting_search_response": True,
        "reserve_urls_previously_unfetched": True,
        "reserve_sources_registrably_new_against_initial_requests": True,
        "reserve_sources_registrably_new_against_initial_successful_identity_sources": True,
        "failed_url_retried": False,
        "same_model_query_and_total_fetch_target_caps_as_parent": True,
        "strict_two_independent_same_value_gate_changed": False,
        "question_query_entity_title_url_host_page_prediction_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_scheduler_receipt(value)


def validate_scheduler_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    true_fields = (
        "generated_query_vector_has_one_query_per_visible_entity",
        "all_generated_entity_queries_submitted_when_search_invoked",
        "exact_full_visible_entity_surface_required_for_alignment",
        "title_and_normalized_url_host_path_used_for_alignment",
        "initial_success_page_text_used_for_reserve_routing_only_via_exact_visible_identity_coverage",
        "reserve_leads_come_from_same_preexisting_search_response",
        "reserve_urls_previously_unfetched",
        "reserve_sources_registrably_new_against_initial_requests",
        "reserve_sources_registrably_new_against_initial_successful_identity_sources",
        "same_model_query_and_total_fetch_target_caps_as_parent",
    )
    false_fields = (
        "planner_queries_forwarded_to_search",
        "query_text_used_to_establish_alignment",
        "field_label_candidate_value_or_model_judgment_used_for_reserve_routing",
        "failed_url_retried",
        "strict_two_independent_same_value_gate_changed",
        "question_query_entity_title_url_host_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != SCHEDULER_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("visible_entity_count") != VISIBLE_ENTITY_COUNT
        or copied.get("logical_query_cap") != LOGICAL_QUERY_COUNT
        or copied.get("fetch_target_cap") != FETCH_TARGET_CAP
        or copied.get("initial_fetch_cap") != INITIAL_FETCH_CAP
        or copied.get("reserve_fetch_cap") != RESERVE_FETCH_CAP
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in COUNT_FIELDS
        )
        or any(
            not isinstance(copied.get(name), list)
            or len(copied[name]) != VISIBLE_ENTITY_COUNT
            or any(
                isinstance(number, bool) or not isinstance(number, int) or number < 0
                for number in copied[name]
            )
            for name in VECTOR_FIELDS
        )
        or copied["search_invocation_count"] not in {0, 1}
        or copied["outer_fetch_invocation_count"] not in {0, 1}
        or copied["provider_search_failure_count"] not in {0, 1}
        or copied["initial_fetch_exception_count"] not in {0, 1}
        or copied["reserve_fetch_exception_count"] not in {0, 1}
        or copied["planner_query_count"]
        != copied["search_invocation_count"] * LOGICAL_QUERY_COUNT
        or copied["initial_fetch_request_count"] > INITIAL_FETCH_CAP
        or copied["reserve_fetch_request_count"] > RESERVE_FETCH_CAP
        or copied["actual_fetch_request_count"]
        != copied["initial_fetch_request_count"] + copied["reserve_fetch_request_count"]
        or copied["actual_fetch_request_count"] > FETCH_TARGET_CAP
        or copied["actual_fetch_request_count"]
        > copied["provisional_fetch_lead_count"]
        or copied["initial_usable_page_count"] > copied["initial_fetch_request_count"]
        or copied["reserve_usable_page_count"] > copied["reserve_fetch_request_count"]
        or copied["actual_usable_page_count"]
        != copied["initial_usable_page_count"] + copied["reserve_usable_page_count"]
        or copied["underlying_fetch_batch_count"]
        != int(copied["initial_fetch_request_count"] > 0)
        + int(copied["reserve_fetch_request_count"] > 0)
        or copied["initial_fetch_exception_count"] > 0
        and copied["reserve_fetch_request_count"] != 0
        or copied["outer_fetch_invocation_count"]
        != int(copied["initial_fetch_request_count"] > 0)
        or copied["reserve_target_entity_count"]
        != sum(value > 0 for value in copied["reserve_request_alignment_count_vector"])
        or copied["reserve_fetch_request_count"]
        != sum(copied["reserve_request_alignment_count_vector"])
        or copied["failed_url_retry_count"] != 0
        or copied["initial_entities_with_zero_usable_identity_sources"]
        + copied["initial_entities_with_one_usable_identity_source"]
        + copied["initial_entities_with_two_or_more_usable_identity_sources"]
        != VISIBLE_ENTITY_COUNT
        or copied["final_entities_with_zero_usable_identity_sources"]
        + copied["final_entities_with_one_usable_identity_source"]
        + copied["final_entities_with_two_or_more_usable_identity_sources"]
        != VISIBLE_ENTITY_COUNT
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.78 scheduler receipt drifted")
    return copied


class StagedFetchFallbackSearchClient:
    """Intercept one parent search and split its ten target slots into 8+2."""

    def __init__(
        self, inner: Any, *, visible_question: str, page_chars: int
    ) -> None:
        self.inner = inner
        if isinstance(page_chars, bool) or not isinstance(page_chars, int) or page_chars <= 0:
            raise ValueError("V2.47.78 page character cap drifted")
        self._page_chars = page_chars
        entities = semantic.extract_visible_entities(visible_question)
        queries = semantic.visible_entity_query_vector(
            visible_question, LOGICAL_QUERY_COUNT
        )
        self._state: dict[str, Any] = {
            "visible_entities": entities,
            "entity_queries": queries,
            "input_leads": [],
            "provisional_leads": [],
            "initial_fetch_requests": [],
            "reserve_fetch_requests": [],
            "actual_fetch_requests": [],
            "initial_identity_sources": [[] for _ in entities],
            "reserve_identity_sources": [[] for _ in entities],
            "initial_replay_bindings": [],
            "reserve_replay_bindings": [],
            "search_invocation_count": 0,
            "outer_fetch_invocation_count": 0,
            "underlying_fetch_batch_count": 0,
            "planner_query_count": 0,
            "raw_batch_count": 0,
            "query_local_result_count": 0,
            "action_source_count": 0,
            "provider_search_failure_count": 0,
            "initial_usable_page_count": 0,
            "reserve_usable_page_count": 0,
            "initial_fetch_exception_count": 0,
            "reserve_fetch_exception_count": 0,
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        planner = list(queries)
        if (
            self._state["search_invocation_count"] != 0
            or len(planner) != LOGICAL_QUERY_COUNT
            or kwargs.get("max_results") != 3
        ):
            raise ValueError("V2.47.78 parent search contract drifted")
        self._state["search_invocation_count"] = 1
        self._state["planner_query_count"] = len(planner)
        try:
            raw = self.inner.search_many(self._state["entity_queries"], **kwargs)
        except BaseException:
            self._state["provider_search_failure_count"] = 1
            raise
        leads, counts = semantic._collect_leads(raw)
        provisional, _diagnostic = semantic.select_visible_entity_fair_leads(
            leads,
            entities=self._state["visible_entities"],
            limit=FETCH_TARGET_CAP,
        )
        self._state.update(counts)
        self._state["input_leads"] = copy.deepcopy(leads)
        self._state["provisional_leads"] = copy.deepcopy(provisional)
        if not provisional:
            return []
        return [
            {
                "query": "visible-entity staged-fallback discovery",
                "answer": "",
                "results": copy.deepcopy(provisional),
                "error": None,
                "provider": "azure-responses-visible-entity-staged-fallback-union",
            }
        ]

    def fetch_urls(self, requests: Sequence[dict[str, str]]) -> Any:
        values = list(requests)
        expected = [_lead_url(lead) for lead in self._state["provisional_leads"]]
        actual = [canonicalize_url(str(lead.get("url") or "")) for lead in values]
        if (
            self._state["outer_fetch_invocation_count"] != 0
            or actual != expected
        ):
            raise ValueError("V2.47.78 parent fetch vector drifted")
        self._state["outer_fetch_invocation_count"] = 1
        initial_count = min(INITIAL_FETCH_CAP, len(values))
        initial_leads = copy.deepcopy(self._state["provisional_leads"][:initial_count])
        self._state["initial_fetch_requests"] = initial_leads
        initial_batches: Any = []
        initial_sources: list[list[str]] = [
            [] for _ in self._state["visible_entities"]
        ]
        initial_usable = 0
        if initial_count:
            self._state["underlying_fetch_batch_count"] += 1
            try:
                initial_batches = self.inner.fetch_urls(values[:initial_count])
                _validate_fetched_batches(
                    initial_batches, requests=initial_leads
                )
                initial_replay = _adapter_pages(
                    initial_batches, page_chars=self._page_chars
                )
                initial_sources = _identity_sources_from_replay(
                    initial_replay, self._state["visible_entities"]
                )
                initial_usable = len(initial_replay)
                self._state["initial_replay_bindings"] = [
                    _replay_binding(page) for page in initial_replay
                ]
            except Exception:
                self._state["initial_fetch_exception_count"] = 1
                initial_batches = []
        self._state["initial_identity_sources"] = initial_sources
        self._state["initial_usable_page_count"] = initial_usable
        reserve_leads: list[dict[str, str]] = []
        reserve_limit = min(
            RESERVE_FETCH_CAP, max(0, len(values) - initial_count)
        )
        if self._state["initial_fetch_exception_count"] == 0 and reserve_limit > 0:
            reserve_leads, _diagnostic = select_staged_reserve_leads(
                self._state["input_leads"],
                entities=self._state["visible_entities"],
                initial_requests=initial_leads,
                initial_identity_sources=initial_sources,
                limit=reserve_limit,
            )
        reserve_batches: Any = []
        reserve_sources: list[list[str]] = [
            [] for _ in self._state["visible_entities"]
        ]
        reserve_usable = 0
        if reserve_leads:
            self._state["underlying_fetch_batch_count"] += 1
            try:
                reserve_batches = self.inner.fetch_urls(
                    [_fetch_request(lead) for lead in reserve_leads]
                )
                _validate_fetched_batches(
                    reserve_batches, requests=reserve_leads
                )
                combined_replay = _adapter_pages(
                    [*list(initial_batches), *list(reserve_batches)],
                    page_chars=self._page_chars,
                )
                initial_bindings = list(self._state["initial_replay_bindings"])
                combined_bindings = [
                    _replay_binding(page) for page in combined_replay
                ]
                if combined_bindings[: len(initial_bindings)] != initial_bindings:
                    raise ValueError("V2.47.78 initial replay prefix drifted")
                reserve_replay = combined_replay[len(initial_bindings) :]
                reserve_sources = _identity_sources_from_replay(
                    reserve_replay, self._state["visible_entities"]
                )
                reserve_usable = len(reserve_replay)
                self._state["reserve_replay_bindings"] = [
                    _replay_binding(page) for page in reserve_replay
                ]
            except Exception:
                self._state["reserve_fetch_exception_count"] = 1
                reserve_batches = []
        self._state["reserve_fetch_requests"] = copy.deepcopy(reserve_leads)
        self._state["actual_fetch_requests"] = copy.deepcopy(
            [*initial_leads, *reserve_leads]
        )
        self._state["reserve_identity_sources"] = reserve_sources
        self._state["reserve_usable_page_count"] = reserve_usable
        return [*list(initial_batches), *list(reserve_batches)]

    def private_state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def receipt(self) -> dict[str, Any]:
        return _scheduler_receipt(self.private_state())


def run_v24778_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    if (
        limits.model_calls != 2
        or limits.search_queries != LOGICAL_QUERY_COUNT
        or limits.fetch_targets != FETCH_TARGET_CAP
        or limits.search_results_per_query != 3
    ):
        raise ValueError("V2.47.78 fixed effect envelope drifted")
    entities = semantic.extract_visible_entities(visible["question"])
    scheduler = StagedFetchFallbackSearchClient(
        search,
        visible_question=visible["question"],
        page_chars=limits.page_chars,
    )
    parent_result = validate_parent_result(
        run_v24756_task(
            visible,
            model=model,
            search=scheduler,
            limits=limits,
            monotonic=monotonic,
        )
    )
    baseline = str(parent_result["predictions"]["baseline"])
    _columns, _rows, boundary_targets, _unknown_targets, identity_eligible = (
        semantic._semantic_targets(baseline, entities)
    )
    catalog = (
        build_target_segment_catalog(
            boundary_targets, semantic._semantic_pages(parent_result), []
        )
        if identity_eligible
        else None
    )
    candidate, semantic_receipt = semantic._semantic_candidate(
        parent_result, entities=entities, catalog=catalog
    )
    predictions = {"baseline": baseline, "staged_fallback_semantic": candidate}
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "parent_result": copy.deepcopy(parent_result),
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "scheduler_receipt": scheduler.receipt(),
        "semantic_receipt": semantic_receipt,
        "private_visible_entities": list(entities),
        "private_visible_task": copy.deepcopy(visible),
        "private_scheduler_state": scheduler.private_state(),
        "private_semantic_catalog": copy.deepcopy(catalog),
        "private_content_emitted_to_public_receipts": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["result_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    parent_result = copied.get("parent_result")
    entities = copied.get("private_visible_entities")
    private_task = copied.get("private_visible_task")
    state = copied.get("private_scheduler_state")
    catalog = copied.get("private_semantic_catalog")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    if (
        set(copied) != RESULT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(parent_result, Mapping)
        or not isinstance(private_task, Mapping)
        or not isinstance(entities, list)
        or len(entities) != VISIBLE_ENTITY_COUNT
        or not isinstance(state, Mapping)
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(ARMS)
        or any(not isinstance(predictions[arm], str) for arm in ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or copied.get("private_content_emitted_to_public_receipts") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.78 task result surface drifted")
    validated_parent = validate_parent_result(parent_result)
    visible = validate_visible_task(private_task)
    scheduler_receipt = _scheduler_receipt(state)
    if (
        copied.get("opaque_id") != validated_parent["opaque_id"]
        or copied.get("opaque_id") != visible["opaque_id"]
        or semantic.extract_visible_entities(visible["question"]) != entities
        or semantic.visible_entity_query_vector(visible["question"], LOGICAL_QUERY_COUNT)
        != list(state.get("entity_queries", []))
        or predictions["baseline"] != validated_parent["predictions"]["baseline"]
        or copied.get("scheduler_receipt") != scheduler_receipt
        or validated_parent["receipt"]["admitted_fetch_targets"]
        != scheduler_receipt["provisional_fetch_lead_count"]
        or scheduler_receipt["actual_usable_page_count"]
        != len(validated_parent["private_replay_pages"])
    ):
        raise ValueError("V2.47.78 parent or scheduler replay drifted")
    validate_scheduler_receipt(copied["scheduler_receipt"])
    initial_count = scheduler_receipt["initial_usable_page_count"]
    replay_pages = validated_parent["private_replay_pages"]
    expected_initial_sources = _identity_sources_from_replay(
        replay_pages[:initial_count], entities
    )
    expected_reserve_sources = _identity_sources_from_replay(
        replay_pages[initial_count:], entities
    )
    if (
        expected_initial_sources != state.get("initial_identity_sources")
        or expected_reserve_sources != state.get("reserve_identity_sources")
        or [_replay_binding(page) for page in replay_pages[:initial_count]]
        != state.get("initial_replay_bindings")
        or [_replay_binding(page) for page in replay_pages[initial_count:]]
        != state.get("reserve_replay_bindings")
    ):
        raise ValueError("V2.47.78 successful identity coverage replay drifted")
    baseline = str(predictions["baseline"])
    _columns, _rows, boundary_targets, _unknown_targets, identity_eligible = (
        semantic._semantic_targets(baseline, entities)
    )
    if identity_eligible:
        if not isinstance(catalog, Mapping):
            raise ValueError("V2.47.78 semantic catalog absent")
        validate_target_segment_catalog(catalog)
        expected_catalog = build_target_segment_catalog(
            boundary_targets, semantic._semantic_pages(validated_parent), []
        )
        if dict(catalog) != expected_catalog:
            raise ValueError("V2.47.78 semantic catalog replay drifted")
    elif catalog is not None:
        raise ValueError("V2.47.78 ineligible semantic catalog persisted")
    candidate, expected_semantic = semantic._semantic_candidate(
        validated_parent, entities=entities, catalog=catalog
    )
    if (
        predictions["staged_fallback_semantic"] != candidate
        or copied.get("semantic_receipt") != expected_semantic
    ):
        raise ValueError("V2.47.78 semantic candidate replay drifted")
    semantic.validate_semantic_receipt(copied["semantic_receipt"])
    return copied


__all__ = [
    "ARMS",
    "POLICY_ID",
    "StagedFetchFallbackSearchClient",
    "run_v24778_task",
    "select_staged_reserve_leads",
    "validate_result",
    "validate_scheduler_receipt",
]
