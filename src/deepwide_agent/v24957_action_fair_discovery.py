"""Action-group-fair ordering for task-local hosted-search discovery.

The production keyless transport often returns many action-level sources but
few query-local citation spans.  The frozen task-union path safely discards
provider prose, yet its stable first-seen prefix can let the first search
action consume the six/four fetch slots.  This append-only candidate keeps the
same task-local provenance boundary and orders action sources round-robin by
provider action before the unchanged budget cap is applied.

No query is inferred from an action, no source is broadcast to a logical
query, and only deterministically fetched page text may become active
evidence.  The module adds no provider, fetch, model, evaluator, or benchmark
effect and grants no launch authority.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .v24269_task_union_discovery import (
    COUNTERS,
    TaskUnionDiscoverySearchClient,
    _counter_delta,
    _counter_snapshot,
    _source_lead,
)
from .v24270_budget_equivalent_union import (
    SELECTION_POLICY as PARENT_SELECTION_POLICY,
    payload_sha256,
    validate_receipt as validate_budget_receipt,
)


POLICY_ID = "v24957_action_group_fair_task_union_v1"
ORDERING_POLICY = "query_local_prefix_then_action_group_round_robin"
ACTION_RECEIPT_ROLE = "v24957_action_fair_discovery_receipt"
BUDGET_RECEIPT_ROLE = "v24957_action_fair_budget_receipt"
ACTION_COUNT_FIELDS = (
    "search_invocations",
    "logical_query_count",
    "raw_query_local_source_count",
    "raw_action_group_count",
    "nonempty_action_group_count",
    "raw_action_source_count",
    "ordered_query_local_lead_count",
    "ordered_action_lead_count",
    "action_groups_with_ordered_lead_count",
    "duplicate_source_count",
)
BUDGET_COUNT_FIELDS = (
    "search_invocations",
    "logical_query_count",
    "declared_query_result_capacity",
    "global_fetch_cap",
    "pre_cap_source_count",
    "post_cap_source_count",
    "truncated_source_count",
    "selected_query_local_lead_count",
    "selected_action_lead_count",
    "available_action_group_count",
    "stable_prefix_action_group_count",
    "fair_prefix_action_group_count",
    "action_group_coverage_gain",
    "selection_changed_invocation_count",
    "remaining_global_fetch_capacity",
)


def _raw_batches(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _query_local_values(
    batches: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [
        result
        for batch in batches
        for result in (batch.get("results") or [])
        if isinstance(result, Mapping)
    ]


def _action_groups(
    batches: Sequence[Mapping[str, Any]],
) -> list[list[Mapping[str, Any]]]:
    groups: list[list[Mapping[str, Any]]] = []
    for batch in batches:
        trace = batch.get("hosted_search_trace")
        if not isinstance(trace, Mapping):
            continue
        for action in trace.get("actions") or []:
            if not isinstance(action, Mapping):
                continue
            groups.append(
                [
                    source
                    for source in (action.get("sources") or [])
                    if isinstance(source, Mapping)
                ]
            )
    return groups


def _lead(value: Mapping[str, Any]) -> dict[str, str] | None:
    projected = _source_lead(value)
    if projected is None:
        return None
    return {
        "title": str(projected.get("title", ""))[:500],
        "url": str(projected["url"]),
        "fetch_url": str(projected.get("fetch_url") or projected["url"]),
        "content": "",
        "raw_content": "",
        "score": None,
        "source_type": "action_fair_task_local_discovery_lead",
    }


def _unique_leads(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in values:
        lead = _lead(value)
        if lead is None or lead["url"] in seen:
            continue
        seen.add(lead["url"])
        output.append(lead)
    return output


def order_action_fair_leads(
    raw: object,
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, frozenset[int]]]:
    """Return a prefix-fair task union plus content-free observations.

    Query-local citations retain their historical priority.  Remaining action
    sources are emitted one per non-empty action group per round.  A URL is
    emitted once globally, while its membership in every action group remains
    available in memory for aggregate coverage accounting.
    """

    batches = _raw_batches(raw)
    local_values = _query_local_values(batches)
    groups = _action_groups(batches)
    local = _unique_leads(local_values)

    normalized_groups: list[list[dict[str, str]]] = []
    memberships: dict[str, set[int]] = {}
    raw_action_sources = 0
    for index, values in enumerate(groups):
        raw_action_sources += len(values)
        normalized = _unique_leads(values)
        normalized_groups.append(normalized)
        for lead in normalized:
            memberships.setdefault(lead["url"], set()).add(index)

    stable: list[dict[str, str]] = []
    stable_seen: set[str] = set()
    for lead in [*local, *(lead for group in normalized_groups for lead in group)]:
        if lead["url"] in stable_seen:
            continue
        stable_seen.add(lead["url"])
        stable.append(copy.deepcopy(lead))

    fair = [copy.deepcopy(lead) for lead in local]
    fair_seen = {lead["url"] for lead in fair}
    offsets = [0 for _ in normalized_groups]
    while True:
        emitted = False
        for group_index, group in enumerate(normalized_groups):
            while offsets[group_index] < len(group):
                lead = group[offsets[group_index]]
                offsets[group_index] += 1
                if lead["url"] in fair_seen:
                    continue
                fair.append(copy.deepcopy(lead))
                fair_seen.add(lead["url"])
                emitted = True
                break
        if not emitted:
            break

    if {lead["url"] for lead in stable} != {lead["url"] for lead in fair}:
        raise RuntimeError("V2.49.57 fair ordering changed the source set")
    local_urls = {lead["url"] for lead in local}
    action_urls = set(memberships) - local_urls
    observation = {
        "raw_query_local_source_count": len(local_values),
        "raw_action_group_count": len(groups),
        "nonempty_action_group_count": sum(bool(group) for group in normalized_groups),
        "raw_action_source_count": raw_action_sources,
        "ordered_query_local_lead_count": sum(
            lead["url"] in local_urls for lead in fair
        ),
        "ordered_action_lead_count": sum(
            lead["url"] in action_urls for lead in fair
        ),
        "action_groups_with_ordered_lead_count": len(
            {index for indexes in memberships.values() for index in indexes}
        ),
        "duplicate_source_count": len(local_values)
        + raw_action_sources
        - len(fair),
        "stable_urls": tuple(lead["url"] for lead in stable),
        "fair_urls": tuple(lead["url"] for lead in fair),
        "local_urls": frozenset(local_urls),
    }
    frozen_memberships = {
        url: frozenset(indexes) for url, indexes in memberships.items()
    }
    return fair, observation, frozen_memberships


def _mapping_failures(batches: Sequence[Mapping[str, Any]]) -> int:
    return sum(
        str(batch.get("error", ""))
        == "hosted search returned no query-local URL citation"
        and not bool(batch.get("results"))
        for batch in batches
    )


def _unrecoverable_failures(batches: Sequence[Mapping[str, Any]]) -> int:
    return sum(
        bool(batch.get("error"))
        and str(batch.get("error", ""))
        != "hosted search returned no query-local URL citation"
        for batch in batches
    )


class ActionFairTaskUnionDiscoverySearchClient(TaskUnionDiscoverySearchClient):
    """Task-union client whose every prefix is fair across search actions."""

    def __init__(self, inner: Any) -> None:
        super().__init__(inner)
        for name in ACTION_COUNT_FIELDS:
            setattr(self, f"action_fair_{name}", 0)
        self.last_observation: dict[str, Any] = {}
        self.last_memberships: dict[str, frozenset[int]] = {}

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        logical_queries = list(queries)
        before = _counter_snapshot(self.inner)
        raw: Any = []
        try:
            raw = self.inner.search_many(logical_queries, **kwargs)
        finally:
            after = _counter_snapshot(self.inner)
        batches = _raw_batches(raw)
        mapping_failures = _mapping_failures(batches)
        unrecoverable_failures = _unrecoverable_failures(batches)
        leads, observation, memberships = order_action_fair_leads(batches)
        recovered = mapping_failures if leads else 0
        self._add_delta(
            _counter_delta(after, before), recovered_mapping_failures=recovered
        )

        raw_local = int(observation["raw_query_local_source_count"])
        raw_action = int(observation["raw_action_source_count"])
        self.search_invocations += 1
        self.logical_query_count += len(logical_queries)
        self.raw_batch_count += len(batches)
        self.raw_query_local_result_count += raw_local
        self.raw_action_source_count += raw_action
        self.raw_query_local_mapping_failure_count += mapping_failures
        self.raw_unrecoverable_failure_count += unrecoverable_failures
        self.union_source_count += len(leads)
        self.duplicate_source_count += max(0, raw_local + raw_action - len(leads))
        self.union_recovery_invocation_count += int(bool(leads) and bool(mapping_failures))
        self.returned_union_batch_count += int(bool(leads))

        self.action_fair_search_invocations += 1
        self.action_fair_logical_query_count += len(logical_queries)
        for name in ACTION_COUNT_FIELDS[2:]:
            self.__dict__[f"action_fair_{name}"] += int(observation[name])
        self.last_observation = copy.deepcopy(observation)
        self.last_memberships = copy.deepcopy(memberships)
        if not leads:
            return []
        return [
            {
                "query": "action-fair task-local discovery union",
                "answer": "",
                "results": copy.deepcopy(leads),
                "error": None,
                "provider": "azure-responses-action-fair-task-union",
            }
        ]

    def action_fair_receipt(self) -> dict[str, Any]:
        value = {
            "artifact_version": 1,
            "role": ACTION_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            **{
                name: int(getattr(self, f"action_fair_{name}"))
                for name in ACTION_COUNT_FIELDS
            },
            "ordering_policy": ORDERING_POLICY,
            "query_local_citation_priority_preserved": True,
            "action_identity_or_order_used_but_action_query_text_used": False,
            "provider_narrative_snippet_or_page_content_used_for_ordering": False,
            "source_broadcast_to_logical_queries": False,
            "fetched_page_text_is_only_active_evidence": True,
            "additional_search_fetch_model_evaluator_or_benchmark_effect": False,
            "contains_question_query_url_host_page_prediction_answer_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        return validate_action_receipt(value)


class ActionFairBudgetEquivalentTaskUnionSearchClient:
    """Apply the unchanged per-query/global caps to action-fair ordering."""

    def __init__(
        self,
        inner: Any,
        *,
        search_results_per_query: int,
        global_fetch_cap: int,
    ) -> None:
        if (
            isinstance(search_results_per_query, bool)
            or not isinstance(search_results_per_query, int)
            or search_results_per_query <= 0
            or isinstance(global_fetch_cap, bool)
            or not isinstance(global_fetch_cap, int)
            or global_fetch_cap <= 0
        ):
            raise ValueError("V2.49.57 cap configuration is invalid")
        self.parent = ActionFairTaskUnionDiscoverySearchClient(inner)
        self.search_results_per_query = search_results_per_query
        self.global_fetch_cap = global_fetch_cap
        for name in BUDGET_COUNT_FIELDS:
            setattr(self, name, 0)
        self.global_fetch_cap = global_fetch_cap

    def __getattr__(self, name: str) -> Any:
        return getattr(self.parent, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        values = list(queries)
        if kwargs.get("max_results") != self.search_results_per_query:
            raise ValueError("V2.49.57 per-query result cap drifted")
        batches = self.parent.search_many(values, **kwargs)
        candidates = [
            dict(result)
            for batch in batches
            if isinstance(batch, Mapping)
            for result in (batch.get("results") or [])
            if isinstance(result, Mapping)
        ]
        remaining = max(0, self.global_fetch_cap - self.post_cap_source_count)
        query_capacity = len(values) * self.search_results_per_query
        admitted = min(len(candidates), query_capacity, remaining)
        selected = candidates[:admitted]
        observation = self.parent.last_observation
        memberships = self.parent.last_memberships
        stable_urls = list(observation.get("stable_urls") or ())[:admitted]
        fair_urls = [canonicalize_url(str(item.get("url", ""))) for item in selected]
        stable_groups = {
            group
            for url in stable_urls
            for group in memberships.get(url, frozenset())
        }
        fair_groups = {
            group
            for url in fair_urls
            for group in memberships.get(url, frozenset())
        }
        if len(fair_groups) < len(stable_groups):
            raise RuntimeError("V2.49.57 fair prefix reduced action-group coverage")
        local_urls = set(observation.get("local_urls") or ())

        self.search_invocations += 1
        self.logical_query_count += len(values)
        self.declared_query_result_capacity += query_capacity
        self.pre_cap_source_count += len(candidates)
        self.post_cap_source_count += len(selected)
        self.truncated_source_count += len(candidates) - len(selected)
        self.selected_query_local_lead_count += sum(url in local_urls for url in fair_urls)
        self.selected_action_lead_count += sum(url not in local_urls for url in fair_urls)
        available = int(observation.get("action_groups_with_ordered_lead_count", 0))
        self.available_action_group_count += available
        self.stable_prefix_action_group_count += len(stable_groups)
        self.fair_prefix_action_group_count += len(fair_groups)
        self.action_group_coverage_gain += len(fair_groups) - len(stable_groups)
        self.selection_changed_invocation_count += int(stable_urls != fair_urls)
        self.remaining_global_fetch_capacity = max(
            0, self.global_fetch_cap - self.post_cap_source_count
        )
        if not selected:
            return []
        return [
            {
                "query": "budget-equivalent action-fair task-local discovery union",
                "answer": "",
                "results": copy.deepcopy(selected),
                "error": None,
                "provider": "azure-responses-budget-equivalent-action-fair-union",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        return self.parent.fetch_urls(requests_)

    def receipt(self) -> dict[str, Any]:
        parent_receipt = self.parent.receipt()
        value = {
            "artifact_version": 1,
            "role": "v24270_budget_equivalent_union_receipt",
            "search_invocations": self.search_invocations,
            "logical_query_count": self.logical_query_count,
            "search_results_per_query": self.search_results_per_query,
            "declared_query_result_capacity": self.declared_query_result_capacity,
            "global_fetch_cap": self.global_fetch_cap,
            "pre_cap_source_count": self.pre_cap_source_count,
            "post_cap_source_count": self.post_cap_source_count,
            "truncated_source_count": self.truncated_source_count,
            "remaining_global_fetch_capacity": max(
                0, self.global_fetch_cap - self.post_cap_source_count
            ),
            "selection_policy": PARENT_SELECTION_POLICY,
            "parent_discovery_receipt_sha256": payload_sha256(parent_receipt),
            "content_score_url_host_or_benchmark_metadata_used_for_selection": False,
            "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        validate_budget_receipt(value)
        return value

    def action_fair_budget_receipt(self) -> dict[str, Any]:
        value = {
            "artifact_version": 1,
            "role": BUDGET_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            **{name: int(getattr(self, name)) for name in BUDGET_COUNT_FIELDS},
            "ordering_policy": ORDERING_POLICY,
            "query_local_citation_priority_preserved": True,
            "same_source_set_as_stable_first_seen_before_cap": True,
            "same_per_query_and_global_fetch_caps": True,
            "provider_action_query_text_used_for_selection": False,
            "provider_narrative_snippet_page_content_or_score_used_for_selection": False,
            "additional_search_fetch_model_evaluator_or_benchmark_effect": False,
            "contains_question_query_url_host_page_prediction_answer_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        return validate_budget_fair_receipt(value)


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.49.57 {label} is not a nonnegative integer")
    return value


def validate_action_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *ACTION_COUNT_FIELDS,
        "ordering_policy",
        "query_local_citation_priority_preserved",
        "action_identity_or_order_used_but_action_query_text_used",
        "provider_narrative_snippet_or_page_content_used_for_ordering",
        "source_broadcast_to_logical_queries",
        "fetched_page_text_is_only_active_evidence",
        "additional_search_fetch_model_evaluator_or_benchmark_effect",
        "contains_question_query_url_host_page_prediction_answer_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    for name in ACTION_COUNT_FIELDS:
        _nonnegative_integer(copied.get(name), name)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ACTION_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("ordering_policy") != ORDERING_POLICY
        or copied.get("query_local_citation_priority_preserved") is not True
        or copied.get("fetched_page_text_is_only_active_evidence") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "action_identity_or_order_used_but_action_query_text_used",
                "provider_narrative_snippet_or_page_content_used_for_ordering",
                "source_broadcast_to_logical_queries",
                "additional_search_fetch_model_evaluator_or_benchmark_effect",
                "contains_question_query_url_host_page_prediction_answer_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or copied["nonempty_action_group_count"] > copied["raw_action_group_count"]
        or copied["action_groups_with_ordered_lead_count"]
        > copied["nonempty_action_group_count"]
    ):
        raise ValueError("V2.49.57 action-fair receipt drifted")
    return copied


def validate_budget_fair_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *BUDGET_COUNT_FIELDS,
        "ordering_policy",
        "query_local_citation_priority_preserved",
        "same_source_set_as_stable_first_seen_before_cap",
        "same_per_query_and_global_fetch_caps",
        "provider_action_query_text_used_for_selection",
        "provider_narrative_snippet_page_content_or_score_used_for_selection",
        "additional_search_fetch_model_evaluator_or_benchmark_effect",
        "contains_question_query_url_host_page_prediction_answer_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    for name in BUDGET_COUNT_FIELDS:
        _nonnegative_integer(copied.get(name), name)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != BUDGET_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("ordering_policy") != ORDERING_POLICY
        or any(
            copied.get(name) is not True
            for name in (
                "query_local_citation_priority_preserved",
                "same_source_set_as_stable_first_seen_before_cap",
                "same_per_query_and_global_fetch_caps",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "provider_action_query_text_used_for_selection",
                "provider_narrative_snippet_page_content_or_score_used_for_selection",
                "additional_search_fetch_model_evaluator_or_benchmark_effect",
                "contains_question_query_url_host_page_prediction_answer_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or copied["post_cap_source_count"] > copied["pre_cap_source_count"]
        or copied["post_cap_source_count"] > copied["global_fetch_cap"]
        or copied["truncated_source_count"]
        != copied["pre_cap_source_count"] - copied["post_cap_source_count"]
        or copied["selected_query_local_lead_count"]
        + copied["selected_action_lead_count"]
        != copied["post_cap_source_count"]
        or copied["fair_prefix_action_group_count"]
        < copied["stable_prefix_action_group_count"]
        or copied["action_group_coverage_gain"]
        != copied["fair_prefix_action_group_count"]
        - copied["stable_prefix_action_group_count"]
        or copied["remaining_global_fetch_capacity"]
        != copied["global_fetch_cap"] - copied["post_cap_source_count"]
    ):
        raise ValueError("V2.49.57 action-fair budget receipt drifted")
    return copied


__all__ = [
    "ActionFairBudgetEquivalentTaskUnionSearchClient",
    "ActionFairTaskUnionDiscoverySearchClient",
    "ORDERING_POLICY",
    "POLICY_ID",
    "order_action_fair_leads",
    "validate_action_receipt",
    "validate_budget_fair_receipt",
]
