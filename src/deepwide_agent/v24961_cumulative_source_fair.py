"""Cumulative two-wave conservation for registrable-source-fair prefixes.

V2.49.60 correctly prioritised sources not seen by the candidate in wave one,
but V2.49.59's local assertion compared only the second-wave source sets.  A
candidate can therefore have fewer *current-wave* sources while retaining
equal or greater *cumulative* source coverage.  This append-only wrapper makes
both arms' prior source sets explicit and validates the cumulative invariant.

The source order, URL set, per-wave cap, and external effects are unchanged.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .v24959_source_fair_discovery import (
    _prefix_actions,
    _prefix_sources,
    order_source_fair_leads,
)


POLICY_ID = "v24961_cumulative_registrable_source_fair_v1"
RECEIPT_ROLE = "v24961_cumulative_source_fair_prefix_receipt"
COUNT_FIELDS = (
    "prefix_cap",
    "stable_prefix_url_count",
    "candidate_prefix_url_count",
    "prior_control_registrable_source_count",
    "prior_candidate_registrable_source_count",
    "stable_current_registrable_source_count",
    "candidate_current_registrable_source_count",
    "stable_cumulative_registrable_source_count",
    "candidate_cumulative_registrable_source_count",
    "cumulative_registrable_source_coverage_gain",
    "stable_prefix_action_group_count",
    "candidate_prefix_action_group_count",
    "selection_changed",
)


def compare_cumulative_prefixes(
    raw: object,
    *,
    cap: int,
    prior_control_urls: Sequence[str] | set[str] | frozenset[str] = (),
    prior_candidate_urls: Sequence[str] | set[str] | frozenset[str] = (),
    prior_control_sources: Sequence[str] | set[str] | frozenset[str] = (),
    prior_candidate_sources: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.49.61 prefix cap is invalid")
    vectors = (prior_control_urls, prior_candidate_urls, prior_control_sources, prior_candidate_sources)
    if any(isinstance(value, (str, bytes)) for value in vectors):
        raise ValueError("V2.49.61 prior vector is invalid")
    control_prior_sources = {
        str(value).strip().casefold()
        for value in prior_control_sources
        if str(value).strip()
    }
    candidate_prior_sources = {
        str(value).strip().casefold()
        for value in prior_candidate_sources
        if str(value).strip()
    }
    ordered, observation, private = order_source_fair_leads(
        raw, prior_sources=candidate_prior_sources
    )
    by_url = {
        canonicalize_url(str(lead.get("url", ""))): copy.deepcopy(dict(lead))
        for lead in ordered
        if canonicalize_url(str(lead.get("url", "")))
    }
    stable_order = list(observation["stable_urls"])
    candidate_order = list(observation["source_fair_urls"])
    control_excluded = {
        canonicalize_url(str(value))
        for value in prior_control_urls
        if canonicalize_url(str(value))
    }
    candidate_excluded = {
        canonicalize_url(str(value))
        for value in prior_candidate_urls
        if canonicalize_url(str(value))
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
    stable_current = _prefix_sources(stable_urls, source_by_url)
    candidate_current = _prefix_sources(candidate_urls, source_by_url)
    stable_cumulative = control_prior_sources | stable_current
    candidate_cumulative = candidate_prior_sources | candidate_current
    if len(candidate_cumulative) < len(stable_cumulative):
        raise RuntimeError("V2.49.61 cumulative source coverage regressed")
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "prefix_cap": cap,
        "stable_prefix_url_count": len(stable_urls),
        "candidate_prefix_url_count": len(candidate_urls),
        "prior_control_registrable_source_count": len(control_prior_sources),
        "prior_candidate_registrable_source_count": len(candidate_prior_sources),
        "stable_current_registrable_source_count": len(stable_current),
        "candidate_current_registrable_source_count": len(candidate_current),
        "stable_cumulative_registrable_source_count": len(stable_cumulative),
        "candidate_cumulative_registrable_source_count": len(candidate_cumulative),
        "cumulative_registrable_source_coverage_gain": len(candidate_cumulative)
        - len(stable_cumulative),
        "stable_prefix_action_group_count": len(
            _prefix_actions(stable_urls, memberships)
        ),
        "candidate_prefix_action_group_count": len(
            _prefix_actions(candidate_urls, memberships)
        ),
        "selection_changed": int(stable_urls != candidate_urls),
        "current_wave_candidate_source_count_may_be_lower": True,
        "cumulative_source_coverage_non_decreasing": True,
        "same_url_set_before_cap": True,
        "matched_prefix_cost": len(stable_urls) == len(candidate_urls),
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
        "control_cumulative_sources": frozenset(stable_cumulative),
        "candidate_cumulative_sources": frozenset(candidate_cumulative),
        "receipt": receipt,
    }


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.49.61 {label} is invalid")
    return value


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *COUNT_FIELDS,
        "current_wave_candidate_source_count_may_be_lower",
        "cumulative_source_coverage_non_decreasing",
        "same_url_set_before_cap",
        "matched_prefix_cost",
        "query_text_provider_narrative_snippet_page_content_or_score_used_for_ordering",
        "additional_search_fetch_model_evaluator_or_benchmark_effect",
        "contains_question_query_url_host_page_prediction_answer_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    for name in COUNT_FIELDS:
        _count(copied.get(name), name)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            copied.get(name) is not True
            for name in (
                "current_wave_candidate_source_count_may_be_lower",
                "cumulative_source_coverage_non_decreasing",
                "same_url_set_before_cap",
                "matched_prefix_cost",
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
        or copied["stable_prefix_url_count"] != copied["candidate_prefix_url_count"]
        or copied["stable_prefix_url_count"] > copied["prefix_cap"]
        or copied["stable_cumulative_registrable_source_count"]
        < copied["prior_control_registrable_source_count"]
        or copied["candidate_cumulative_registrable_source_count"]
        < copied["prior_candidate_registrable_source_count"]
        or copied["candidate_cumulative_registrable_source_count"]
        < copied["stable_cumulative_registrable_source_count"]
        or copied["cumulative_registrable_source_coverage_gain"]
        != copied["candidate_cumulative_registrable_source_count"]
        - copied["stable_cumulative_registrable_source_count"]
        or copied["selection_changed"] not in {0, 1}
    ):
        raise ValueError("V2.49.61 cumulative receipt drifted")
    return copied


__all__ = ["POLICY_ID", "compare_cumulative_prefixes", "validate_receipt"]
