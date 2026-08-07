"""Visible-entity-fair acquisition with strict semantic Unknown recovery.

V2.47.65 issued four logical queries but collapsed all returned URLs into one
task union before taking the first ten leads.  This append-only successor uses
the same effect caps while replacing only that allocation policy:

* derive exactly one query per explicitly visible entity;
* classify exact full-entity matches from public title or normalized URL
  hostname/path surfaces (never from query text);
* allocate the ten fetch slots round-robin across the four visible entities,
  then fill unused capacity without page-content ranking;
* replay fetched pages through the frozen V2.43.65 target-segment projector;
* change only baseline Unknown cells having one unconflicted value supported
  by at least two registrably independent sources.

The parent still performs exactly two model calls, one four-query hosted-search
call, and at most ten fetches.  The scheduler and semantic replay add no model,
search, fetch, evaluator, or benchmark effect and assign no positive task or
entropy credit.  Runtime input remains exactly ``{opaque_id, question}``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24269_task_union_discovery import _action_sources, _source_lead
from .v24333_programmatic_support_catalog import CellTarget
from .v24365_entity_segment_projection import (
    build_target_segment_catalog,
    validate_target_segment_catalog,
)
from .v24547_alias_surface_observability import classify_alias_surface
from .v24743_generic_record_binding import (
    UNKNOWN,
    _baseline_matrix,
    _canonical_text,
    _render_table,
    _safe_text,
    _source_key,
)
from .v24756_zero_effect_structured_integration import (
    payload_sha256,
    run_v24756_task,
    validate_result as validate_parent_result,
)
from .v24286_visible_schema_runtime import extract_robust_visible_columns


POLICY_ID = "v24770_visible_entity_fair_semantic_unknown_recovery_v1"
ROLE = "v24770_visible_entity_fair_semantic_task_result"
SCHEDULER_ROLE = "v24770_visible_entity_fair_scheduler_receipt"
SEMANTIC_ROLE = "v24770_strict_semantic_unknown_recovery_receipt"
ARMS = ("baseline", "entity_fair_semantic")
VISIBLE_ENTITY_COUNT = 4
LOGICAL_QUERY_COUNT = 4
FETCH_TARGET_CAP = 10
EXPECTED_COLUMNS = ("Organization", "Founded", "Country")
FULL_SURFACE_MODE = "normalized_full_surface"
SCHEDULER_COUNT_FIELDS = (
    "search_invocation_count",
    "fetch_invocation_count",
    "planner_query_count",
    "generated_entity_query_count",
    "submitted_entity_query_count",
    "raw_batch_count",
    "query_local_result_count",
    "action_source_count",
    "input_unique_url_count",
    "input_independent_source_count",
    "exact_aligned_unique_url_count",
    "selected_fetch_lead_count",
    "fetch_request_count",
    "selected_unique_source_count",
    "selected_exact_aligned_lead_count",
    "round_robin_assignment_count",
    "post_round_robin_fill_count",
    "visible_entities_with_zero_selected_aligned_sources",
    "visible_entities_with_one_selected_aligned_source",
    "visible_entities_with_two_or_more_selected_aligned_sources",
    "visible_entities_with_zero_requested_aligned_sources",
    "visible_entities_with_one_requested_aligned_source",
    "visible_entities_with_two_or_more_requested_aligned_sources",
    "provider_search_failure_count",
)
SCHEDULER_VECTOR_FIELDS = (
    "aligned_independent_source_count_vector",
    "round_robin_assignment_count_vector",
    "selected_aligned_source_count_vector",
    "requested_aligned_source_count_vector",
)
SCHEDULER_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "visible_entity_count",
        "logical_query_cap",
        "fetch_target_cap",
        *SCHEDULER_COUNT_FIELDS,
        *SCHEDULER_VECTOR_FIELDS,
    "generated_query_vector_has_one_query_per_visible_entity",
    "all_generated_entity_queries_submitted_when_search_invoked",
        "planner_queries_forwarded_to_search",
        "query_text_used_to_establish_alignment",
        "exact_full_visible_entity_surface_required_for_alignment",
        "title_and_normalized_url_host_path_used_for_alignment",
        "url_query_fragment_userinfo_or_port_used_for_alignment",
        "query_local_provenance_used_for_alignment",
        "provider_narrative_snippet_or_page_content_used_for_selection",
        "round_robin_precedes_unaligned_capacity_fill",
        "same_model_query_fetch_caps_as_parent",
        "question_query_entity_title_url_host_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
PRIVATE_SCHEDULER_KEYS = frozenset(
    {
        "visible_entities",
        "entity_queries",
        "input_leads",
        "selected_leads",
        "fetch_requests",
        "search_invocation_count",
        "fetch_invocation_count",
        "planner_query_count",
        "raw_batch_count",
        "query_local_result_count",
        "action_source_count",
        "provider_search_failure_count",
    }
)
SEMANTIC_COUNT_FIELDS = (
    "baseline_value_cell_count",
    "baseline_unknown_cell_count",
    "semantic_boundary_target_count",
    "semantic_unknown_target_count",
    "semantic_catalog_projection_count",
    "semantic_catalog_distinct_target_value_projection_count",
    "semantic_unknown_projection_count",
    "semantic_unknown_distinct_target_value_projection_count",
    "semantic_catalog_candidate_target_value_group_count",
    "semantic_catalog_eligible_support_set_count",
    "semantic_unknown_eligible_support_set_count",
    "projection_backed_eligible_support_set_count",
    "semantic_unconflicted_proposal_cell_count",
    "semantic_conflicting_cell_count",
    "parent_exact_adapter_changed_cell_count",
    "parent_and_semantic_same_value_cell_count",
    "parent_and_semantic_value_conflict_cell_count",
    "final_conflict_abstention_cell_count",
    "final_changed_cell_count",
)
SEMANTIC_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "identity_surface_eligible",
        "catalog_status",
        *SEMANTIC_COUNT_FIELDS,
        "candidate_changes_only_baseline_unknown_cells",
        "semantic_candidate_requires_projection_binding",
        "semantic_candidate_requires_two_independent_sources",
        "any_same_cell_value_conflict_abstains",
        "parent_exact_adapter_safety_preserved",
        "new_model_search_fetch_or_evaluator_effect",
        "positive_entropy_or_task_credit_assigned",
        "postfreeze_outer_utility_observed",
        "question_query_entity_url_host_page_prediction_value_or_credential_emitted",
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


def extract_visible_entities(question: str) -> list[str]:
    """Parse the numbered entity block from the visible prompt only."""

    match = re.search(
        r"(?:^|\n)<ENTITIES>\n(.*?)\n</ENTITIES>(?:\n|$)",
        str(question),
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError("V2.47.70 visible entity block absent")
    values: list[str] = []
    for index, line in enumerate(match.group(1).splitlines(), 1):
        prefix = f"{index}. "
        if not line.startswith(prefix):
            raise ValueError("V2.47.70 visible entity numbering drifted")
        value = " ".join(line[len(prefix) :].split()).strip()
        if (
            not value
            or len(value) > 300
            or any(character in value for character in "\r\n|\0")
        ):
            raise ValueError("V2.47.70 visible entity is unsafe")
        values.append(value)
    if (
        len(values) != VISIBLE_ENTITY_COUNT
        or len({unicodedata.normalize("NFKC", value).casefold() for value in values})
        != len(values)
    ):
        raise ValueError("V2.47.70 visible entity vector drifted")
    return values


def visible_entity_query_vector(question: str, limit: int) -> list[str]:
    if limit != LOGICAL_QUERY_COUNT:
        raise ValueError("V2.47.70 requires the unchanged four-query cap")
    entities = extract_visible_entities(question)
    if tuple(extract_robust_visible_columns(question) or ()) != EXPECTED_COLUMNS:
        raise ValueError("V2.47.70 visible schema is outside the frozen scope")
    return [f'"{entity}" founded established country' for entity in entities]


def _lead_source(lead: Mapping[str, Any]) -> str:
    canonical = canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
    host = (urlsplit(canonical).hostname or "").casefold().strip(".")
    return _source_key(host)


def _lead(raw: Mapping[str, Any]) -> dict[str, str] | None:
    projected = _source_lead(raw)
    if projected is None:
        return None
    canonical = canonicalize_url(projected["url"])
    if not canonical:
        return None
    value = {
        "title": str(projected.get("title", ""))[:500],
        "url": canonical,
        "fetch_url": str(projected.get("fetch_url") or canonical),
        "content": "",
        "raw_content": "",
        "score": None,
        "source_type": "visible_entity_fair_discovery_lead",
    }
    try:
        _lead_source(value)
    except ValueError:
        return None
    return value


def _collect_leads(raw: object) -> tuple[list[dict[str, str]], dict[str, int]]:
    batches = (
        [batch for batch in raw if isinstance(batch, Mapping)]
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes))
        else []
    )
    query_local: list[Mapping[str, Any]] = []
    actions: list[Mapping[str, Any]] = []
    for batch in batches:
        query_local.extend(
            item
            for item in (batch.get("results") or [])
            if isinstance(item, Mapping)
        )
        actions.extend(_action_sources(batch))
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_lead in [*query_local, *actions]:
        lead = _lead(raw_lead)
        if lead is None or lead["url"] in seen:
            continue
        seen.add(lead["url"])
        output.append(lead)
    return output, {
        "raw_batch_count": len(batches),
        "query_local_result_count": len(query_local),
        "action_source_count": len(actions),
    }


def _exact_alignment(lead: Mapping[str, Any], entity: str) -> tuple[bool, bool]:
    match = classify_alias_surface({**dict(lead), "query": ""}, entity)
    return (
        FULL_SURFACE_MODE in match["title_modes"],
        FULL_SURFACE_MODE in match["url_modes"],
    )


def _normalized_leads(leads: object) -> list[dict[str, str]]:
    if not isinstance(leads, Sequence) or isinstance(leads, (str, bytes)):
        raise ValueError("V2.47.70 lead vector drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in leads:
        if not isinstance(raw, Mapping):
            continue
        lead = _lead(raw)
        if lead is None or lead["url"] in seen:
            continue
        seen.add(lead["url"])
        output.append(lead)
    return output


def _maximum_entity_source_round(
    buckets: Sequence[Sequence[dict[str, str]]],
    *,
    excluded_sources: set[str],
) -> dict[int, dict[str, str]]:
    """Return a deterministic maximum-cardinality entity/source matching."""

    source_owner: dict[str, int] = {}
    source_lead: dict[str, dict[str, str]] = {}

    def augment(entity_index: int, visited: set[str]) -> bool:
        for lead in buckets[entity_index]:
            source = _lead_source(lead)
            if source in excluded_sources or source in visited:
                continue
            visited.add(source)
            prior = source_owner.get(source)
            if prior is None or augment(prior, visited):
                source_owner[source] = entity_index
                source_lead[source] = lead
                return True
        return False

    for entity_index in range(len(buckets)):
        augment(entity_index, set())
    output: dict[int, dict[str, str]] = {}
    for source, entity_index in source_owner.items():
        if entity_index in output:
            raise RuntimeError("V2.47.70 entity/source matching drifted")
        output[entity_index] = copy.deepcopy(source_lead[source])
    return output


def select_visible_entity_fair_leads(
    leads: object,
    *,
    entities: Sequence[str],
    limit: int = FETCH_TARGET_CAP,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Select title/URL-aligned source representatives in entity round-robin."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit != FETCH_TARGET_CAP
        or isinstance(entities, (str, bytes))
        or len(entities) != VISIBLE_ENTITY_COUNT
        or any(not str(entity).strip() for entity in entities)
    ):
        raise ValueError("V2.47.70 fair-selection configuration drifted")
    values = _normalized_leads(leads)
    buckets: list[list[dict[str, str]]] = []
    aligned_sources: list[set[str]] = []
    for entity in entities:
        by_source: dict[str, tuple[tuple[Any, ...], dict[str, str]]] = {}
        for lead in values:
            title_hit, url_hit = _exact_alignment(lead, str(entity))
            if not (title_hit or url_hit):
                continue
            source = _lead_source(lead)
            rank = (
                not title_hit,
                not url_hit,
                source,
                lead["url"],
                lead["title"],
            )
            current = by_source.get(source)
            if current is None or rank < current[0]:
                by_source[source] = (rank, lead)
        ranked = [copy.deepcopy(item[1]) for item in sorted(by_source.values())]
        buckets.append(ranked)
        aligned_sources.append(set(by_source))

    selected: list[dict[str, str]] = []
    selected_urls: set[str] = set()
    selected_sources: set[str] = set()
    assignments = [0] * len(buckets)
    while len(selected) < limit:
        matched = _maximum_entity_source_round(
            buckets, excluded_sources=selected_sources
        )
        if not matched:
            break
        for index in range(len(buckets)):
            lead = matched.get(index)
            if lead is None:
                continue
            source = _lead_source(lead)
            if lead["url"] in selected_urls or source in selected_sources:
                raise RuntimeError("V2.47.70 matched source was already selected")
            selected.append(copy.deepcopy(lead))
            selected_urls.add(lead["url"])
            selected_sources.add(source)
            assignments[index] += 1
            if len(selected) >= limit:
                break

    round_robin_count = len(selected)
    remaining = [lead for lead in values if lead["url"] not in selected_urls]
    new_source_first: list[dict[str, str]] = []
    deferred: list[dict[str, str]] = []
    newly_reserved: set[str] = set()
    for lead in remaining:
        source = _lead_source(lead)
        if source not in selected_sources and source not in newly_reserved:
            new_source_first.append(lead)
            newly_reserved.add(source)
        else:
            deferred.append(lead)
    fill_order = [*new_source_first, *deferred]
    for lead in fill_order:
        if len(selected) >= limit:
            break
        if lead["url"] in selected_urls:
            continue
        selected.append(copy.deepcopy(lead))
        selected_urls.add(lead["url"])
        selected_sources.add(_lead_source(lead))

    selected_aligned_vectors: list[int] = []
    for entity in entities:
        sources = {
            _lead_source(lead)
            for lead in selected
            if any(_exact_alignment(lead, str(entity)))
        }
        selected_aligned_vectors.append(len(sources))
    aligned_urls = {
        lead["url"]
        for lead in values
        if any(any(_exact_alignment(lead, str(entity))) for entity in entities)
    }
    selected_exact = sum(
        lead["url"] in aligned_urls for lead in selected
    )
    counts = Counter(selected_aligned_vectors)
    diagnostic = {
        "input_unique_url_count": len(values),
        "input_independent_source_count": len({_lead_source(lead) for lead in values}),
        "exact_aligned_unique_url_count": len(aligned_urls),
        "selected_fetch_lead_count": len(selected),
        "selected_unique_source_count": len({_lead_source(lead) for lead in selected}),
        "selected_exact_aligned_lead_count": selected_exact,
        "round_robin_assignment_count": round_robin_count,
        "post_round_robin_fill_count": len(selected) - round_robin_count,
        "visible_entities_with_zero_selected_aligned_sources": counts[0],
        "visible_entities_with_one_selected_aligned_source": counts[1],
        "visible_entities_with_two_or_more_selected_aligned_sources": sum(
            count for coverage, count in counts.items() if coverage >= 2
        ),
        "aligned_independent_source_count_vector": [
            len(values) for values in aligned_sources
        ],
        "round_robin_assignment_count_vector": assignments,
        "selected_aligned_source_count_vector": selected_aligned_vectors,
    }
    return selected, diagnostic


def _scheduler_receipt(state: Mapping[str, Any]) -> dict[str, Any]:
    if set(state) != PRIVATE_SCHEDULER_KEYS:
        raise ValueError("V2.47.70 private scheduler state drifted")
    selected, diagnostic = select_visible_entity_fair_leads(
        state["input_leads"],
        entities=state["visible_entities"],
        limit=FETCH_TARGET_CAP,
    )
    if selected != state["selected_leads"]:
        raise ValueError("V2.47.70 selected lead replay drifted")
    requested = list(state["fetch_requests"])
    if requested != selected[: len(requested)]:
        raise ValueError("V2.47.70 requested lead prefix replay drifted")
    requested_aligned_vectors = [
        len(
            {
                _lead_source(lead)
                for lead in requested
                if any(_exact_alignment(lead, str(entity)))
            }
        )
        for entity in state["visible_entities"]
    ]
    requested_counts = Counter(requested_aligned_vectors)
    value = {
        "artifact_version": 1,
        "role": SCHEDULER_ROLE,
        "policy_id": POLICY_ID,
        "visible_entity_count": VISIBLE_ENTITY_COUNT,
        "logical_query_cap": LOGICAL_QUERY_COUNT,
        "fetch_target_cap": FETCH_TARGET_CAP,
        "search_invocation_count": int(state["search_invocation_count"]),
        "fetch_invocation_count": int(state["fetch_invocation_count"]),
        "planner_query_count": int(state["planner_query_count"]),
        "generated_entity_query_count": len(state["entity_queries"]),
        "submitted_entity_query_count": (
            len(state["entity_queries"]) * int(state["search_invocation_count"])
        ),
        "raw_batch_count": int(state["raw_batch_count"]),
        "query_local_result_count": int(state["query_local_result_count"]),
        "action_source_count": int(state["action_source_count"]),
        **diagnostic,
        "fetch_request_count": len(requested),
        "visible_entities_with_zero_requested_aligned_sources": requested_counts[0],
        "visible_entities_with_one_requested_aligned_source": requested_counts[1],
        "visible_entities_with_two_or_more_requested_aligned_sources": sum(
            count for coverage, count in requested_counts.items() if coverage >= 2
        ),
        "requested_aligned_source_count_vector": requested_aligned_vectors,
        "provider_search_failure_count": int(state["provider_search_failure_count"]),
        "generated_query_vector_has_one_query_per_visible_entity": True,
        "all_generated_entity_queries_submitted_when_search_invoked": True,
        "planner_queries_forwarded_to_search": False,
        "query_text_used_to_establish_alignment": False,
        "exact_full_visible_entity_surface_required_for_alignment": True,
        "title_and_normalized_url_host_path_used_for_alignment": True,
        "url_query_fragment_userinfo_or_port_used_for_alignment": False,
        "query_local_provenance_used_for_alignment": False,
        "provider_narrative_snippet_or_page_content_used_for_selection": False,
        "round_robin_precedes_unaligned_capacity_fill": True,
        "same_model_query_fetch_caps_as_parent": True,
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
        "round_robin_precedes_unaligned_capacity_fill",
        "same_model_query_fetch_caps_as_parent",
    )
    false_fields = (
        "planner_queries_forwarded_to_search",
        "query_text_used_to_establish_alignment",
        "url_query_fragment_userinfo_or_port_used_for_alignment",
        "query_local_provenance_used_for_alignment",
        "provider_narrative_snippet_or_page_content_used_for_selection",
        "question_query_entity_title_url_host_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != SCHEDULER_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != SCHEDULER_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("visible_entity_count") != VISIBLE_ENTITY_COUNT
        or copied.get("logical_query_cap") != LOGICAL_QUERY_COUNT
        or copied.get("fetch_target_cap") != FETCH_TARGET_CAP
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in SCHEDULER_COUNT_FIELDS
        )
        or any(
            not isinstance(copied.get(name), list)
            or len(copied[name]) != VISIBLE_ENTITY_COUNT
            or any(
                isinstance(number, bool) or not isinstance(number, int) or number < 0
                for number in copied[name]
            )
            for name in SCHEDULER_VECTOR_FIELDS
        )
        or copied["search_invocation_count"] not in {0, 1}
        or copied["fetch_invocation_count"] not in {0, 1}
        or copied["provider_search_failure_count"] not in {0, 1}
        or copied["planner_query_count"]
        != copied["search_invocation_count"] * LOGICAL_QUERY_COUNT
        or copied["generated_entity_query_count"] != LOGICAL_QUERY_COUNT
        or copied["submitted_entity_query_count"]
        != copied["search_invocation_count"] * LOGICAL_QUERY_COUNT
        or copied["provider_search_failure_count"]
        > copied["search_invocation_count"]
        or copied["selected_fetch_lead_count"] > FETCH_TARGET_CAP
        or copied["fetch_request_count"] > copied["selected_fetch_lead_count"]
        or copied["fetch_invocation_count"]
        != int(copied["fetch_request_count"] > 0)
        or copied["search_invocation_count"] == 0
        and any(
            copied[name] != 0
            for name in (
                "raw_batch_count",
                "query_local_result_count",
                "action_source_count",
                "input_unique_url_count",
                "selected_fetch_lead_count",
                "fetch_request_count",
            )
        )
        or copied["provider_search_failure_count"] > 0
        and any(
            copied[name] != 0
            for name in (
                "raw_batch_count",
                "query_local_result_count",
                "action_source_count",
                "input_unique_url_count",
                "selected_fetch_lead_count",
                "fetch_request_count",
            )
        )
        or copied["selected_unique_source_count"]
        > copied["selected_fetch_lead_count"]
        or copied["selected_unique_source_count"]
        > copied["input_independent_source_count"]
        or copied["exact_aligned_unique_url_count"]
        > copied["input_unique_url_count"]
        or copied["selected_exact_aligned_lead_count"]
        > copied["selected_fetch_lead_count"]
        or copied["round_robin_assignment_count"]
        + copied["post_round_robin_fill_count"]
        != copied["selected_fetch_lead_count"]
        or sum(copied["round_robin_assignment_count_vector"])
        != copied["round_robin_assignment_count"]
        or any(
            assigned > aligned
            for assigned, aligned in zip(
                copied["round_robin_assignment_count_vector"],
                copied["aligned_independent_source_count_vector"],
                strict=True,
            )
        )
        or any(
            requested > selected
            for requested, selected in zip(
                copied["requested_aligned_source_count_vector"],
                copied["selected_aligned_source_count_vector"],
                strict=True,
            )
        )
        or copied["visible_entities_with_zero_selected_aligned_sources"]
        + copied["visible_entities_with_one_selected_aligned_source"]
        + copied["visible_entities_with_two_or_more_selected_aligned_sources"]
        != VISIBLE_ENTITY_COUNT
        or copied["visible_entities_with_zero_requested_aligned_sources"]
        + copied["visible_entities_with_one_requested_aligned_source"]
        + copied["visible_entities_with_two_or_more_requested_aligned_sources"]
        != VISIBLE_ENTITY_COUNT
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.70 scheduler receipt drifted")
    return copied


class VisibleEntityFairSearchClient:
    """Intercept one parent search, preserving counters and fetch behavior."""

    def __init__(self, inner: Any, *, visible_question: str) -> None:
        self.inner = inner
        self._entities = extract_visible_entities(visible_question)
        self._queries = visible_entity_query_vector(
            visible_question, LOGICAL_QUERY_COUNT
        )
        self._state: dict[str, Any] = {
            "visible_entities": list(self._entities),
            "entity_queries": list(self._queries),
            "input_leads": [],
            "selected_leads": [],
            "fetch_requests": [],
            "search_invocation_count": 0,
            "fetch_invocation_count": 0,
            "planner_query_count": 0,
            "raw_batch_count": 0,
            "query_local_result_count": 0,
            "action_source_count": 0,
            "provider_search_failure_count": 0,
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
            raise ValueError("V2.47.70 parent search contract drifted")
        self._state["search_invocation_count"] = 1
        self._state["planner_query_count"] = len(planner)
        try:
            raw = self.inner.search_many(self._queries, **kwargs)
        except BaseException:
            self._state["provider_search_failure_count"] = 1
            raise
        leads, counts = _collect_leads(raw)
        selected, _diagnostic = select_visible_entity_fair_leads(
            leads, entities=self._entities, limit=FETCH_TARGET_CAP
        )
        self._state.update(counts)
        self._state["input_leads"] = copy.deepcopy(leads)
        self._state["selected_leads"] = copy.deepcopy(selected)
        if not selected:
            return []
        return [
            {
                "query": "visible-entity-fair task discovery",
                "answer": "",
                "results": copy.deepcopy(selected),
                "error": None,
                "provider": "azure-responses-visible-entity-fair-union",
            }
        ]

    def fetch_urls(self, requests: Sequence[dict[str, str]]) -> Any:
        values = list(requests)
        expected = [
            canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
            for lead in self._state["selected_leads"]
        ]
        actual = [
            canonicalize_url(str(lead.get("url") or "")) for lead in values
        ]
        if (
            self._state["fetch_invocation_count"] != 0
            or len(actual) > len(expected)
            or actual != expected[: len(actual)]
        ):
            raise ValueError("V2.47.70 fetch vector drifted")
        self._state["fetch_invocation_count"] = 1
        self._state["fetch_requests"] = copy.deepcopy(
            self._state["selected_leads"][: len(values)]
        )
        return self.inner.fetch_urls(values)

    def private_state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def receipt(self) -> dict[str, Any]:
        return _scheduler_receipt(self.private_state())


def _unknown(value: object) -> bool:
    return _canonical_text(value).casefold() in UNKNOWN


def _semantic_pages(parent: Mapping[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for page in parent["private_replay_pages"]:
        host = (urlsplit(str(page["final_url"])).hostname or "").casefold()
        output.append(
            {
                "host": host,
                "content": str(page["content"]),
                "fetch_integrity": page["fetch_integrity"],
            }
        )
    return output


def _semantic_targets(
    baseline: str, entities: Sequence[str]
) -> tuple[
    list[str],
    list[list[str]],
    list[CellTarget],
    list[CellTarget],
    bool,
]:
    columns, rows = _baseline_matrix(baseline)
    if tuple(columns) != EXPECTED_COLUMNS:
        raise ValueError("V2.47.70 baseline schema drifted")
    identity_eligible = (
        len(rows) == len(entities)
        and [row[0] for row in rows] == list(entities)
        and len(columns) >= 2
    )
    boundary_targets = [
        CellTarget(row[0], columns[column], row[column])
        for row in rows
        for column in range(1, len(columns))
    ]
    unknown_targets = [
        target for target in boundary_targets if target.baseline_unknown
    ]
    return columns, rows, boundary_targets, unknown_targets, identity_eligible


def _projection_backed_proposals(
    catalog: Mapping[str, Any],
) -> tuple[dict[str, str], set[str], dict[str, int]]:
    validated = validate_target_segment_catalog(catalog)
    catalog_targets = [
        CellTarget(
            str(item["row_key"]),
            str(item["column"]),
            None if item["old_value"] is None else str(item["old_value"]),
        )
        for item in validated["targets"]
    ]
    unknown_bindings = {
        item.binding_sha256 for item in catalog_targets if item.baseline_unknown
    }
    projection_values: dict[str, set[str]] = defaultdict(set)
    for item in validated["projections"]:
        binding = str(item["target_binding_sha256"])
        if binding in unknown_bindings:
            projection_values[binding].add(str(item["normalized_value_sha256"]))
    projection_pairs = {
        (item["target_binding_sha256"], item["normalized_value_sha256"])
        for item in validated["projections"]
    }
    projection_sources: dict[tuple[str, str], set[str]] = defaultdict(set)
    core_pages = validated["original_core_pages"]
    reserve_pages = validated["original_reserve_pages"]
    for item in validated["projections"]:
        pages = core_pages if item["scope"] == "core" else reserve_pages
        ordinal = int(item["page_ordinal"])
        if ordinal < 1 or ordinal > len(pages):
            raise ValueError("V2.47.70 projection page binding drifted")
        source = _source_key(str(pages[ordinal - 1]["host"]))
        projection_sources[
            (
                str(item["target_binding_sha256"]),
                str(item["normalized_value_sha256"]),
            )
        ].add(hashlib.sha256(source.encode("utf-8")).hexdigest())
    base = validated["active_catalog"]["base_catalog"]
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    projection_backed = 0
    for support in base["support_sets"]:
        if support["baseline_cell_unknown"] is not True:
            continue
        pair = (
            str(support["target_binding_sha256"]),
            str(support["candidate_value_sha256"]),
        )
        if pair not in projection_pairs:
            continue
        support_sources = {
            str(item["source_key_sha256"])
            for item in support["evidence_source_bindings"]
        }
        if (
            len(support_sources) < 2
            or not support_sources.issubset(projection_sources[pair])
        ):
            continue
        if (
            int(support["independent_source_count"]) < 2
            or int(support["required_source_count"]) < 2
        ):
            raise ValueError("V2.47.70 eligible semantic support drifted")
        try:
            safe = _safe_text(support["candidate_value"])
        except ValueError:
            continue
        projection_backed += 1
        normalized = _canonical_text(safe).casefold()
        grouped[str(support["target_binding_sha256"])][normalized] = safe
    proposals: dict[str, str] = {}
    conflicts: set[str] = {
        binding for binding, values in projection_values.items() if len(values) > 1
    }
    for binding, values in grouped.items():
        if binding in conflicts:
            continue
        if len(values) == 1:
            proposals[binding] = next(iter(values.values()))
        elif values:
            conflicts.add(binding)
    for binding in conflicts:
        proposals.pop(binding, None)
    return proposals, conflicts, {
        "projection_backed_eligible_support_set_count": projection_backed,
        "semantic_unconflicted_proposal_cell_count": len(proposals),
        "semantic_conflicting_cell_count": len(conflicts),
    }


def _semantic_candidate(
    parent: Mapping[str, Any],
    *,
    entities: Sequence[str],
    catalog: Mapping[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    baseline = str(parent["predictions"]["baseline"])
    exact = str(parent["predictions"]["generic_structured"])
    columns, rows, boundary_targets, unknown_targets, identity_eligible = _semantic_targets(
        baseline, entities
    )
    exact_columns, exact_rows = _baseline_matrix(exact)
    if exact_columns != columns or len(exact_rows) != len(rows):
        raise ValueError("V2.47.70 parent candidate shape drifted")
    target_by_coordinate: dict[tuple[int, int], CellTarget] = {}
    for row_index, row in enumerate(rows):
        for column_index in range(1, len(columns)):
            if not _unknown(row[column_index]):
                continue
            target = CellTarget(row[0], columns[column_index], row[column_index])
            target_by_coordinate[(row_index, column_index)] = target

    proposals: dict[str, str] = {}
    semantic_conflicts: set[str] = set()
    proposal_counts = {
        "projection_backed_eligible_support_set_count": 0,
        "semantic_unconflicted_proposal_cell_count": 0,
        "semantic_conflicting_cell_count": 0,
    }
    projection_count = distinct_projection_count = candidate_group_count = 0
    unknown_projection_count = unknown_distinct_projection_count = 0
    catalog_eligible_support_count = 0
    if catalog is not None:
        validated = validate_target_segment_catalog(catalog)
        proposals, semantic_conflicts, proposal_counts = (
            _projection_backed_proposals(validated)
        )
        projection_count = int(validated["semantic_projection_count"])
        distinct_projection_count = len(
            {
                (item["target_binding_sha256"], item["normalized_value_sha256"])
                for item in validated["projections"]
            }
        )
        base = validated["active_catalog"]["base_catalog"]
        candidate_group_count = int(base["candidate_groups_considered"])
        catalog_eligible_support_count = int(base["eligible_support_set_count"])
        unknown_bindings = {target.binding_sha256 for target in unknown_targets}
        unknown_projections = [
            item
            for item in validated["projections"]
            if str(item["target_binding_sha256"]) in unknown_bindings
        ]
        unknown_projection_count = len(unknown_projections)
        unknown_distinct_projection_count = len(
            {
                (item["target_binding_sha256"], item["normalized_value_sha256"])
                for item in unknown_projections
            }
        )
    unknown_eligible_support_count = int(
        proposal_counts["projection_backed_eligible_support_set_count"]
    )

    output_rows = [list(row) for row in rows]
    parent_changes: dict[tuple[int, int], str] = {}
    for row_index, (before, after) in enumerate(zip(rows, exact_rows, strict=True)):
        if before[0] != after[0]:
            raise ValueError("V2.47.70 parent identity drifted")
        for column_index in range(1, len(columns)):
            if _canonical_text(before[column_index]).casefold() == _canonical_text(
                after[column_index]
            ).casefold():
                continue
            if not _unknown(before[column_index]):
                raise ValueError("V2.47.70 parent changed non-Unknown cell")
            parent_changes[(row_index, column_index)] = after[column_index]

    effective_parent_changes = parent_changes if identity_eligible else {}

    same = parent_semantic_conflicts = final_conflicts = changed = 0
    for coordinate, target in target_by_coordinate.items():
        values: dict[str, str] = {}
        parent_value = effective_parent_changes.get(coordinate)
        semantic_value = proposals.get(target.binding_sha256)
        if parent_value is not None:
            values[_canonical_text(parent_value).casefold()] = parent_value
        if semantic_value is not None:
            values[_canonical_text(semantic_value).casefold()] = semantic_value
        semantic_has_conflict = target.binding_sha256 in semantic_conflicts
        if parent_value is not None and semantic_value is not None and len(values) == 1:
            same += 1
        if parent_value is not None and semantic_value is not None and len(values) > 1:
            parent_semantic_conflicts += 1
        if semantic_has_conflict or len(values) > 1:
            final_conflicts += 1
            continue
        if len(values) == 1:
            output_rows[coordinate[0]][coordinate[1]] = next(iter(values.values()))
            changed += 1

    candidate = _render_table(columns, output_rows)
    value_count = len(rows) * max(0, len(columns) - 1)
    receipt = {
        "artifact_version": 1,
        "role": SEMANTIC_ROLE,
        "policy_id": POLICY_ID,
        "identity_surface_eligible": identity_eligible,
        "catalog_status": (
            "identity_surface_ineligible"
            if not identity_eligible
            else "built_eligible"
            if unknown_eligible_support_count
            else "built_empty"
        ),
        "baseline_value_cell_count": value_count,
        "baseline_unknown_cell_count": len(unknown_targets),
        "semantic_boundary_target_count": (
            len(rows) * max(0, len(columns) - 1) if identity_eligible else 0
        ),
        "semantic_unknown_target_count": (
            len(unknown_targets) if identity_eligible else 0
        ),
        "semantic_catalog_projection_count": projection_count,
        "semantic_catalog_distinct_target_value_projection_count": distinct_projection_count,
        "semantic_unknown_projection_count": unknown_projection_count,
        "semantic_unknown_distinct_target_value_projection_count": unknown_distinct_projection_count,
        "semantic_catalog_candidate_target_value_group_count": candidate_group_count,
        "semantic_catalog_eligible_support_set_count": catalog_eligible_support_count,
        "semantic_unknown_eligible_support_set_count": unknown_eligible_support_count,
        **proposal_counts,
        "parent_exact_adapter_changed_cell_count": len(parent_changes),
        "parent_and_semantic_same_value_cell_count": same,
        "parent_and_semantic_value_conflict_cell_count": parent_semantic_conflicts,
        "final_conflict_abstention_cell_count": final_conflicts,
        "final_changed_cell_count": changed,
        "candidate_changes_only_baseline_unknown_cells": True,
        "semantic_candidate_requires_projection_binding": True,
        "semantic_candidate_requires_two_independent_sources": True,
        "any_same_cell_value_conflict_abstains": True,
        "parent_exact_adapter_safety_preserved": True,
        "new_model_search_fetch_or_evaluator_effect": False,
        "positive_entropy_or_task_credit_assigned": False,
        "postfreeze_outer_utility_observed": False,
        "question_query_entity_url_host_page_prediction_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    return candidate, validate_semantic_receipt(receipt)


def validate_semantic_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    true_fields = (
        "candidate_changes_only_baseline_unknown_cells",
        "semantic_candidate_requires_projection_binding",
        "semantic_candidate_requires_two_independent_sources",
        "any_same_cell_value_conflict_abstains",
        "parent_exact_adapter_safety_preserved",
    )
    false_fields = (
        "new_model_search_fetch_or_evaluator_effect",
        "positive_entropy_or_task_credit_assigned",
        "postfreeze_outer_utility_observed",
        "question_query_entity_url_host_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != SEMANTIC_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != SEMANTIC_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("catalog_status")
        not in {"identity_surface_ineligible", "built_empty", "built_eligible"}
        or not isinstance(copied.get("identity_surface_eligible"), bool)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in SEMANTIC_COUNT_FIELDS
        )
        or copied["semantic_boundary_target_count"]
        > copied["baseline_value_cell_count"]
        or copied["identity_surface_eligible"]
        and copied["semantic_boundary_target_count"]
        != copied["baseline_value_cell_count"]
        or not copied["identity_surface_eligible"]
        and copied["semantic_boundary_target_count"] != 0
        or copied["semantic_unknown_target_count"]
        > copied["baseline_unknown_cell_count"]
        or copied["semantic_unknown_projection_count"]
        > copied["semantic_catalog_projection_count"]
        or copied["semantic_unknown_distinct_target_value_projection_count"]
        > copied["semantic_catalog_distinct_target_value_projection_count"]
        or copied["semantic_unknown_distinct_target_value_projection_count"]
        > copied["semantic_unknown_projection_count"]
        or copied["identity_surface_eligible"]
        and copied["semantic_unknown_target_count"]
        != copied["baseline_unknown_cell_count"]
        or not copied["identity_surface_eligible"]
        and copied["semantic_unknown_target_count"] != 0
        or copied["semantic_unconflicted_proposal_cell_count"]
        + copied["semantic_conflicting_cell_count"]
        > copied["semantic_unknown_target_count"]
        or copied["projection_backed_eligible_support_set_count"]
        > copied["semantic_catalog_eligible_support_set_count"]
        or copied["semantic_unknown_eligible_support_set_count"]
        != copied["projection_backed_eligible_support_set_count"]
        or copied["final_changed_cell_count"]
        > copied["baseline_unknown_cell_count"]
        or copied["parent_and_semantic_same_value_cell_count"]
        + copied["parent_and_semantic_value_conflict_cell_count"]
        > min(
            copied["parent_exact_adapter_changed_cell_count"],
            copied["semantic_unconflicted_proposal_cell_count"],
        )
        or copied["parent_and_semantic_value_conflict_cell_count"]
        > copied["final_conflict_abstention_cell_count"]
        or copied["final_conflict_abstention_cell_count"]
        > copied["baseline_unknown_cell_count"]
        or not copied["identity_surface_eligible"]
        and any(
            copied[name] != 0
            for name in (
                "semantic_catalog_projection_count",
                "semantic_catalog_distinct_target_value_projection_count",
                "semantic_unknown_projection_count",
                "semantic_unknown_distinct_target_value_projection_count",
                "semantic_catalog_candidate_target_value_group_count",
                "semantic_catalog_eligible_support_set_count",
                "semantic_unknown_eligible_support_set_count",
                "projection_backed_eligible_support_set_count",
                "semantic_unconflicted_proposal_cell_count",
                "semantic_conflicting_cell_count",
                "parent_and_semantic_same_value_cell_count",
                "parent_and_semantic_value_conflict_cell_count",
                "final_conflict_abstention_cell_count",
                "final_changed_cell_count",
            )
        )
        or (copied["catalog_status"] == "built_eligible")
        != (copied["semantic_unknown_eligible_support_set_count"] > 0)
        or copied["identity_surface_eligible"]
        != (copied["catalog_status"] != "identity_surface_ineligible")
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.70 semantic receipt drifted")
    return copied


def run_v24770_task(
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
        raise ValueError("V2.47.70 fixed effect envelope drifted")
    entities = extract_visible_entities(visible["question"])
    scheduler = VisibleEntityFairSearchClient(
        search, visible_question=visible["question"]
    )
    parent = validate_parent_result(
        run_v24756_task(
            visible,
            model=model,
            search=scheduler,
            limits=limits,
            monotonic=monotonic,
        )
    )
    baseline = str(parent["predictions"]["baseline"])
    _columns, _rows, boundary_targets, _unknown_targets, identity_eligible = _semantic_targets(
        baseline, entities
    )
    catalog = (
        build_target_segment_catalog(
            boundary_targets, _semantic_pages(parent), []
        )
        if identity_eligible
        else None
    )
    candidate, semantic_receipt = _semantic_candidate(
        parent, entities=entities, catalog=catalog
    )
    predictions = {"baseline": baseline, "entity_fair_semantic": candidate}
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "parent_result": copy.deepcopy(parent),
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
    parent = copied.get("parent_result")
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
        or not isinstance(parent, Mapping)
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
        raise ValueError("V2.47.70 task result surface drifted")
    validated_parent = validate_parent_result(parent)
    visible = validate_visible_task(private_task)
    if (
        copied.get("opaque_id") != validated_parent["opaque_id"]
        or copied.get("opaque_id") != visible["opaque_id"]
        or extract_visible_entities(visible["question"]) != entities
        or visible_entity_query_vector(visible["question"], LOGICAL_QUERY_COUNT)
        != list(state.get("entity_queries", []))
        or predictions["baseline"] != validated_parent["predictions"]["baseline"]
        or list(state.get("visible_entities", [])) != entities
        or list(state.get("entity_queries", []))
        != [f'"{entity}" founded established country' for entity in entities]
        or copied.get("scheduler_receipt") != _scheduler_receipt(state)
    ):
        raise ValueError("V2.47.70 parent or scheduler replay drifted")
    validate_scheduler_receipt(copied["scheduler_receipt"])
    baseline = str(predictions["baseline"])
    _columns, _rows, boundary_targets, _unknown_targets, identity_eligible = _semantic_targets(
        baseline, entities
    )
    if identity_eligible:
        if not isinstance(catalog, Mapping):
            raise ValueError("V2.47.70 semantic catalog absent")
        validate_target_segment_catalog(catalog)
        expected_catalog = build_target_segment_catalog(
            boundary_targets, _semantic_pages(validated_parent), []
        )
        if dict(catalog) != expected_catalog:
            raise ValueError("V2.47.70 semantic catalog replay drifted")
    elif catalog is not None:
        raise ValueError("V2.47.70 ineligible semantic catalog persisted")
    candidate, semantic_receipt = _semantic_candidate(
        validated_parent, entities=entities, catalog=catalog
    )
    if (
        predictions["entity_fair_semantic"] != candidate
        or copied.get("semantic_receipt") != semantic_receipt
    ):
        raise ValueError("V2.47.70 semantic candidate replay drifted")
    validate_semantic_receipt(copied["semantic_receipt"])
    return copied


__all__ = [
    "ARMS",
    "POLICY_ID",
    "VisibleEntityFairSearchClient",
    "extract_visible_entities",
    "run_v24770_task",
    "select_visible_entity_fair_leads",
    "validate_result",
    "validate_scheduler_receipt",
    "validate_semantic_receipt",
    "visible_entity_query_vector",
]
