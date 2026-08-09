"""Registrable-source-fair ordering for task-local hosted-search leads.

The V2.49.58 live gate showed that action-group round-robin changes too few
production-shaped selections.  This successor keeps the exact same URL set
but moves the first representative of every conservatively attributable
registrable source ahead of same-source duplicates.  Within that independent
source phase, V2.49.57's query-local priority and action-group round-robin
order is preserved.

The transformation reads URL hostnames only.  It never reads page content,
provider narrative, task labels, predictions, evaluator data, or scores.  It
adds no network/model/fetch/evaluator effect and grants no launch authority.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url
from .v24743_generic_record_binding import _source_key
from .v24957_action_fair_discovery import order_action_fair_leads


POLICY_ID = "v24959_registrable_source_fair_task_union_v1"
ORDERING_POLICY = (
    "query_local_action_fair_order_then_first_representative_per_registrable_source"
)
RECEIPT_ROLE = "v24959_source_fair_prefix_receipt"
COUNT_FIELDS = (
    "input_unique_url_count",
    "registrable_source_count",
    "unattributable_url_count",
    "independent_source_phase_url_count",
    "deferred_same_source_or_unattributable_url_count",
    "prefix_cap",
    "stable_prefix_url_count",
    "candidate_prefix_url_count",
    "stable_prefix_registrable_source_count",
    "candidate_prefix_registrable_source_count",
    "registrable_source_coverage_gain",
    "stable_prefix_action_group_count",
    "candidate_prefix_action_group_count",
    "action_group_coverage_delta",
    "selection_changed",
)


def _lead_source(lead: Mapping[str, Any]) -> str | None:
    canonical = canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
    host = (urlsplit(canonical).hostname or "").casefold() if canonical else ""
    if not host:
        return None
    try:
        return _source_key(host)
    except ValueError:
        return None


def order_source_fair_leads(
    raw: object,
    *,
    prior_sources: Sequence[str] | set[str] | frozenset[str] = (),
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    """Return the same URL set ordered for maximal independent-source prefix.

    ``prior_sources`` is private task-local state from an earlier retrieval
    wave.  Sources already represented there are deferred behind every newly
    attributable source in the current response.
    """

    if isinstance(prior_sources, (str, bytes)):
        raise ValueError("V2.49.59 prior source vector is invalid")
    prior = {str(value).strip().casefold() for value in prior_sources if str(value).strip()}
    action_fair, parent_observation, memberships = order_action_fair_leads(raw)
    by_url = {
        canonicalize_url(str(lead.get("url", ""))): copy.deepcopy(dict(lead))
        for lead in action_fair
        if canonicalize_url(str(lead.get("url", "")))
    }
    stable_urls = [canonicalize_url(str(url)) for url in parent_observation["stable_urls"]]
    action_urls = [canonicalize_url(str(url)) for url in parent_observation["fair_urls"]]
    if (
        "" in stable_urls
        or "" in action_urls
        or len(stable_urls) != len(set(stable_urls))
        or len(action_urls) != len(set(action_urls))
        or set(stable_urls) != set(action_urls)
        or set(action_urls) != set(by_url)
    ):
        raise RuntimeError("V2.49.59 parent source set drifted")

    source_by_url = {url: _lead_source(by_url[url]) for url in action_urls}
    seen_sources = set(prior)
    independent: list[str] = []
    deferred: list[str] = []
    for url in action_urls:
        source = source_by_url[url]
        if source is not None and source not in seen_sources:
            independent.append(url)
            seen_sources.add(source)
        else:
            deferred.append(url)
    candidate_urls = [*independent, *deferred]
    if set(candidate_urls) != set(stable_urls) or len(candidate_urls) != len(stable_urls):
        raise RuntimeError("V2.49.59 source-fair ordering changed the URL set")

    attributable = {source for source in source_by_url.values() if source is not None}
    observation = {
        "input_unique_url_count": len(candidate_urls),
        "registrable_source_count": len(attributable),
        "unattributable_url_count": sum(source is None for source in source_by_url.values()),
        "independent_source_phase_url_count": len(independent),
        "deferred_same_source_or_unattributable_url_count": len(deferred),
        "raw_action_group_count": int(parent_observation["raw_action_group_count"]),
        "raw_action_source_count": int(parent_observation["raw_action_source_count"]),
        "stable_urls": tuple(stable_urls),
        "action_fair_urls": tuple(action_urls),
        "source_fair_urls": tuple(candidate_urls),
        "local_urls": frozenset(parent_observation["local_urls"]),
    }
    private = {
        "source_by_url": copy.deepcopy(source_by_url),
        "action_memberships": copy.deepcopy(memberships),
        "prior_sources": frozenset(prior),
    }
    return [copy.deepcopy(by_url[url]) for url in candidate_urls], observation, private


def _prefix_sources(
    urls: Sequence[str], source_by_url: Mapping[str, str | None]
) -> set[str]:
    return {
        source
        for url in urls
        if (source := source_by_url.get(url)) is not None
    }


def _prefix_actions(
    urls: Sequence[str], memberships: Mapping[str, frozenset[int]]
) -> set[int]:
    return {
        action
        for url in urls
        for action in memberships.get(url, frozenset())
    }


def compare_prefixes(
    raw: object,
    *,
    cap: int,
    prior_control_urls: Sequence[str] | set[str] | frozenset[str] = (),
    prior_candidate_urls: Sequence[str] | set[str] | frozenset[str] = (),
    prior_candidate_sources: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    """Replay stable and source-fair matched-cost prefixes from one response."""

    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.49.59 prefix cap is invalid")
    ordered, observation, private = order_source_fair_leads(
        raw, prior_sources=prior_candidate_sources
    )
    by_url = {
        canonicalize_url(str(lead.get("url", ""))): copy.deepcopy(dict(lead))
        for lead in ordered
    }
    stable_order = list(observation["stable_urls"])
    candidate_order = list(observation["source_fair_urls"])
    control_excluded = {
        canonicalize_url(str(url)) for url in prior_control_urls if canonicalize_url(str(url))
    }
    candidate_excluded = {
        canonicalize_url(str(url)) for url in prior_candidate_urls if canonicalize_url(str(url))
    }

    def choose(order: Sequence[str], excluded: set[str]) -> list[str]:
        output: list[str] = []
        for url in order:
            if url in excluded:
                continue
            output.append(url)
            if len(output) >= cap:
                break
        return output

    stable_urls = choose(stable_order, control_excluded)
    candidate_urls = choose(candidate_order, candidate_excluded)
    matched = min(len(stable_urls), len(candidate_urls))
    stable_urls = stable_urls[:matched]
    candidate_urls = candidate_urls[:matched]
    source_by_url = private["source_by_url"]
    memberships = private["action_memberships"]
    stable_sources = _prefix_sources(stable_urls, source_by_url)
    candidate_sources = _prefix_sources(candidate_urls, source_by_url)
    stable_actions = _prefix_actions(stable_urls, memberships)
    candidate_actions = _prefix_actions(candidate_urls, memberships)
    if len(candidate_sources) < len(stable_sources):
        raise RuntimeError("V2.49.59 source-fair prefix reduced source coverage")
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{
            name: int(observation[name])
            for name in (
                "input_unique_url_count",
                "registrable_source_count",
                "unattributable_url_count",
                "independent_source_phase_url_count",
                "deferred_same_source_or_unattributable_url_count",
            )
        },
        "prefix_cap": cap,
        "stable_prefix_url_count": len(stable_urls),
        "candidate_prefix_url_count": len(candidate_urls),
        "stable_prefix_registrable_source_count": len(stable_sources),
        "candidate_prefix_registrable_source_count": len(candidate_sources),
        "registrable_source_coverage_gain": len(candidate_sources) - len(stable_sources),
        "stable_prefix_action_group_count": len(stable_actions),
        "candidate_prefix_action_group_count": len(candidate_actions),
        "action_group_coverage_delta": len(candidate_actions) - len(stable_actions),
        "selection_changed": int(stable_urls != candidate_urls),
        "ordering_policy": ORDERING_POLICY,
        "same_url_set_before_cap": True,
        "matched_prefix_cost": len(stable_urls) == len(candidate_urls),
        "registrable_source_coverage_non_decreasing": True,
        "query_text_provider_narrative_snippet_page_content_or_score_used_for_ordering": False,
        "additional_search_fetch_model_evaluator_or_benchmark_effect": False,
        "contains_question_query_url_host_page_prediction_answer_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    validate_receipt(receipt)
    return {
        "stable": [copy.deepcopy(by_url[url]) for url in stable_urls],
        "candidate": [copy.deepcopy(by_url[url]) for url in candidate_urls],
        "candidate_sources": frozenset(candidate_sources),
        "receipt": receipt,
    }


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.49.59 {label} is not a nonnegative integer")
    return value


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *COUNT_FIELDS,
        "ordering_policy",
        "same_url_set_before_cap",
        "matched_prefix_cost",
        "registrable_source_coverage_non_decreasing",
        "query_text_provider_narrative_snippet_page_content_or_score_used_for_ordering",
        "additional_search_fetch_model_evaluator_or_benchmark_effect",
        "contains_question_query_url_host_page_prediction_answer_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    for name in COUNT_FIELDS:
        _nonnegative_integer(copied.get(name), name)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("ordering_policy") != ORDERING_POLICY
        or any(
            copied.get(name) is not True
            for name in (
                "same_url_set_before_cap",
                "matched_prefix_cost",
                "registrable_source_coverage_non_decreasing",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "query_text_provider_narrative_snippet_page_content_or_score_used_for_ordering",
                "additional_search_fetch_model_evaluator_or_benchmark_effect",
                "contains_question_query_url_host_page_prediction_answer_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or copied["input_unique_url_count"]
        != copied["independent_source_phase_url_count"]
        + copied["deferred_same_source_or_unattributable_url_count"]
        or copied["independent_source_phase_url_count"]
        > copied["registrable_source_count"]
        or copied["stable_prefix_url_count"] != copied["candidate_prefix_url_count"]
        or copied["stable_prefix_url_count"] > copied["prefix_cap"]
        or copied["candidate_prefix_registrable_source_count"]
        < copied["stable_prefix_registrable_source_count"]
        or copied["registrable_source_coverage_gain"]
        != copied["candidate_prefix_registrable_source_count"]
        - copied["stable_prefix_registrable_source_count"]
        or copied["selection_changed"] not in {0, 1}
    ):
        raise ValueError("V2.49.59 source-fair receipt drifted")
    return copied


__all__ = [
    "ORDERING_POLICY",
    "POLICY_ID",
    "compare_prefixes",
    "order_source_fair_leads",
    "validate_receipt",
]
