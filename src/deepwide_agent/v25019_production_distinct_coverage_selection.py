"""Pure production second-wave selection by distinct visible-row coverage.

The frozen V2.48.57 retrieval chooses its second-wave fetch vector with
``_lead_requests(second_batches, cap)`` and then removes first-wave URLs.  This
module replays that vector byte-for-byte as control.  Candidate may replace
items, but never change the selected count, using only same-run public links
that are strict same-origin children of an authority-bound first-wave page and
bind to exactly one identity in a strict visible multi-row vector.

Candidate is published only when it covers strictly more previously uncovered
visible identities than control.  Otherwise it is an exact identity handoff.
Page body, title, anchor text, provider prose, query text, score, entropy, gold,
evaluator output, and historical correctness are not ranking inputs.  This
module performs no I/O and grants no benchmark or evaluator authority.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .v24257_score_first_runtime import _lead_requests
from .v24263_global_model_limiter import payload_sha256
from .v25015_distinct_identity_child_selection import (
    _covered_identities,
    _identity_matches,
    _identity_vectors,
    _visible_links,
)


POLICY_ID = "v25019_production_distinct_identity_second_wave_selection_v1"
RECEIPT_ROLE = "v25019_content_free_production_distinct_coverage_receipt"
_COUNT_FIELDS = (
    "prefix_cap",
    "visible_identity_count",
    "legacy_control_selected_url_count",
    "candidate_selected_url_count",
    "raw_first_wave_page_count",
    "raw_page_visible_link_count",
    "resolved_public_http_link_count",
    "rejected_invalid_or_non_http_link_count",
    "rejected_private_or_credential_link_count",
    "authority_bound_attesting_page_count",
    "same_origin_strict_child_link_count",
    "unique_identity_child_link_count",
    "ambiguous_identity_child_link_count",
    "attested_unique_identity_child_link_count",
    "available_attested_child_link_count",
    "prior_covered_distinct_identity_count",
    "control_new_distinct_identity_count",
    "candidate_new_distinct_identity_count",
    "new_distinct_identity_gain",
    "selection_changed",
)


def _canonical_urls(values: Sequence[str] | set[str] | frozenset[str]) -> set[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError("V2.50.19 exclusion vector is invalid")
    return {
        canonical
        for value in values
        if (canonical := canonicalize_url(str(value)))
    }


def _request(value: Mapping[str, Any]) -> dict[str, str]:
    raw = str(value.get("fetch_url") or value.get("url") or "")
    canonical = canonicalize_url(raw)
    if not canonical:
        raise ValueError("V2.50.19 selected request URL is invalid")
    return {
        "url": raw,
        "query": str(value.get("query") or ""),
        "title": str(value.get("title") or "")[:500],
        "member_label": str(value.get("member_label") or "")[:1_000],
    }


def _distinct_count(
    values: Sequence[Mapping[str, Any]],
    vectors: Sequence[tuple[str, tuple[str, ...]]],
    prior: set[int],
) -> int:
    identities: set[int] = set()
    for value in values:
        matches = _identity_matches(str(value.get("url") or ""), vectors)
        if len(matches) == 1 and matches[0] not in prior:
            identities.add(matches[0])
    return len(identities)


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "strategy_eligible": bool(value["strategy_eligible"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "control_exactly_replays_frozen_v24857_lead_prefix": True,
        "candidate_fetch_count_equals_control": True,
        "first_wave_urls_excluded_before_both_selections": True,
        "prior_coverage_uses_unique_visible_identity_url_path_binding_only": True,
        "candidate_links_require_same_run_authority_attestation": True,
        "candidate_links_require_strict_same_origin_child_path": True,
        "candidate_links_require_exactly_one_visible_identity_path_binding": True,
        "candidate_published_only_for_strict_distinct_identity_gain": True,
        "stable_order_preserved_within_identity_and_remainder_partitions": True,
        "additional_query_fetch_model_token_context_byte_wall_or_network_cap": False,
        "page_body_title_anchor_provider_narrative_query_score_or_field_value_used_for_ranking": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "contains_question_identity_url_page_prediction_answer_hash_opaque_id_or_credential": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    boolean_fields = ("strategy_eligible", "mechanism_engaged")
    true_flags = (
        "control_exactly_replays_frozen_v24857_lead_prefix",
        "candidate_fetch_count_equals_control",
        "first_wave_urls_excluded_before_both_selections",
        "prior_coverage_uses_unique_visible_identity_url_path_binding_only",
        "candidate_links_require_same_run_authority_attestation",
        "candidate_links_require_strict_same_origin_child_path",
        "candidate_links_require_exactly_one_visible_identity_path_binding",
        "candidate_published_only_for_strict_distinct_identity_gain",
        "stable_order_preserved_within_identity_and_remainder_partitions",
    )
    false_flags = (
        "additional_query_fetch_model_token_context_byte_wall_or_network_cap",
        "page_body_title_anchor_provider_narrative_query_score_or_field_value_used_for_ranking",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "contains_question_identity_url_page_prediction_answer_hash_opaque_id_or_credential",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *boolean_fields,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _COUNT_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or not 0 <= copied["visible_identity_count"] <= 32
        or copied["legacy_control_selected_url_count"]
        != copied["candidate_selected_url_count"]
        or copied["legacy_control_selected_url_count"] > copied["prefix_cap"]
        or copied["resolved_public_http_link_count"]
        + copied["rejected_invalid_or_non_http_link_count"]
        + copied["rejected_private_or_credential_link_count"]
        != copied["raw_page_visible_link_count"]
        or copied["authority_bound_attesting_page_count"]
        > copied["raw_first_wave_page_count"]
        or copied["unique_identity_child_link_count"]
        + copied["ambiguous_identity_child_link_count"]
        > copied["same_origin_strict_child_link_count"]
        or copied["attested_unique_identity_child_link_count"]
        > copied["unique_identity_child_link_count"]
        or copied["available_attested_child_link_count"]
        > copied["attested_unique_identity_child_link_count"]
        or copied["prior_covered_distinct_identity_count"]
        > copied["visible_identity_count"]
        or copied["control_new_distinct_identity_count"]
        > copied["visible_identity_count"]
        - copied["prior_covered_distinct_identity_count"]
        or copied["candidate_new_distinct_identity_count"]
        > copied["visible_identity_count"]
        - copied["prior_covered_distinct_identity_count"]
        or copied["new_distinct_identity_gain"]
        != copied["candidate_new_distinct_identity_count"]
        - copied["control_new_distinct_identity_count"]
        or copied["selection_changed"] not in {0, 1}
        or copied["selection_changed"]
        != int(copied["new_distinct_identity_gain"] > 0)
        or copied["mechanism_engaged"] is not bool(copied["selection_changed"])
        or copied["strategy_eligible"]
        is not bool(
            copied["visible_identity_count"] >= 2
            and copied["available_attested_child_link_count"] > 0
            and copied["legacy_control_selected_url_count"] > 0
        )
        or copied["mechanism_engaged"] and not copied["strategy_eligible"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.19 production distinct-coverage receipt drifted")
    return copied


def select_production_second_wave(
    first_wave_page_batches: object,
    second_wave_batches: Sequence[Mapping[str, Any]],
    *,
    question: str,
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    """Return the exact legacy control and a matched-count candidate vector."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.19 visible question is absent")
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.50.19 prefix cap is invalid")
    excluded = _canonical_urls(exclude_urls)
    raw_control = _lead_requests(list(second_wave_batches), cap)
    control = [
        _request(value)
        for value in raw_control
        if canonicalize_url(str(value.get("url") or "")) not in excluded
    ][:cap]
    vectors = _identity_vectors(question)
    empty_link_counts = {
        "raw_first_wave_page_count": 0,
        "raw_page_visible_link_count": 0,
        "resolved_public_http_link_count": 0,
        "rejected_invalid_or_non_http_link_count": 0,
        "rejected_private_or_credential_link_count": 0,
        "authority_bound_attesting_page_count": 0,
        "same_origin_strict_child_link_count": 0,
        "unique_identity_child_link_count": 0,
        "ambiguous_identity_child_link_count": 0,
        "attested_unique_identity_child_link_count": 0,
    }
    links: list[dict[str, Any]] = []
    page_urls: set[str] = set()
    link_counts = empty_link_counts
    if len(vectors) >= 2:
        links, link_counts, page_urls = _visible_links(
            first_wave_page_batches,
            question=question,
            vectors=vectors,
        )
    prior_urls = excluded | page_urls
    prior = _covered_identities(prior_urls, vectors)
    control_distinct = _distinct_count(control, vectors, prior)
    control_urls = {
        canonicalize_url(str(value.get("url") or "")) for value in control
    } - {""}
    available_links = [
        value
        for value in links
        if value["attested"]
        and value["lead"]["url"] not in prior_urls
        and value["lead"]["url"] not in control_urls
    ]

    # Search leads retain stable priority when they already cover an identity;
    # authority-attested child links displace only redundant/unbound remainder.
    pool: list[dict[str, str]] = [*copy.deepcopy(control)]
    pool.extend(_request(value["lead"]) for value in available_links)
    first_per_identity: list[dict[str, str]] = []
    selected_identities: set[int] = set()
    for value in pool:
        matches = _identity_matches(value["url"], vectors)
        if len(matches) != 1 or matches[0] in prior or matches[0] in selected_identities:
            continue
        first_per_identity.append(value)
        selected_identities.add(matches[0])
    first_urls = {
        canonicalize_url(value["url"]) for value in first_per_identity
    } - {""}
    remainder = [
        value
        for value in pool
        if canonicalize_url(value["url"]) not in first_urls
    ]
    candidate = [
        copy.deepcopy(value)
        for value in [*first_per_identity, *remainder][: len(control)]
    ]
    candidate_distinct = _distinct_count(candidate, vectors, prior)
    if candidate_distinct <= control_distinct:
        candidate = copy.deepcopy(control)
        candidate_distinct = control_distinct
    changed = candidate != control
    gain = candidate_distinct - control_distinct
    if changed is not (gain > 0) or len(candidate) != len(control):
        raise RuntimeError("V2.50.19 matched production selection invariant drifted")
    receipt = _receipt(
        {
            "prefix_cap": cap,
            "visible_identity_count": len(vectors),
            "legacy_control_selected_url_count": len(control),
            "candidate_selected_url_count": len(candidate),
            **link_counts,
            "available_attested_child_link_count": len(available_links),
            "prior_covered_distinct_identity_count": len(prior),
            "control_new_distinct_identity_count": control_distinct,
            "candidate_new_distinct_identity_count": candidate_distinct,
            "new_distinct_identity_gain": gain,
            "selection_changed": int(changed),
            "strategy_eligible": bool(
                len(vectors) >= 2 and available_links and control
            ),
            "mechanism_engaged": changed,
        }
    )
    return {
        "artifact_version": 1,
        "policy_id": POLICY_ID,
        "control": control,
        "candidate": candidate,
        "content_free_receipt": receipt,
    }


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "select_production_second_wave",
    "validate_receipt",
]
