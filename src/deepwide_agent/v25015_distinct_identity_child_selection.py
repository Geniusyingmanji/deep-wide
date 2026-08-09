"""Pure authority-attested child selection by distinct visible-row coverage.

V2.50.13 showed that ranking one detail link for one visible identity is mostly
redundant with direct search.  This append-only selector targets visible
multi-row tasks.  It preserves the completed search prefix and the full public
first-wave link set, but fills remaining slots with at most one first-seen,
same-origin, authority-attested child for each *uncovered* visible identity
before considering duplicate-identity or unrelated links.

Coverage is derived only from the strict visible identity vector and canonical
URL path tokens produced in the same forward pass.  A URL that matches zero or
more than one visible identity receives no identity credit.  Search-prefix,
previously fetched, and caller-excluded URLs define prior coverage.  Candidate
selection is applied only when its number of newly covered distinct identities
strictly exceeds stable-first-seen control; otherwise it is an exact handoff.

Page text, title, anchor text, provider prose, query text, score, prediction,
benchmark labels, evaluator outputs, and historical outcomes are not ranking
inputs.  The module performs no I/O or effects.  Entropy/IG assign no credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .v24263_global_model_limiter import payload_sha256
from .v24998_identity_authority_action_selection import (
    _tokens,
    _url_path_tokens,
    select_matched_prefixes,
)
from .v25010_attested_child_detail_selection import (
    _attesting_base,
    _authority_url_bound,
    _page_results,
    _page_urls,
    _public_link,
    _sequence,
    _strict_same_origin_child,
)
from .v25014_multi_identity_detail_fields import visible_identities


POLICY_ID = "v25015_distinct_visible_identity_attested_child_selection_v1"
RECEIPT_ROLE = "v25015_content_free_distinct_identity_child_selection_receipt"
_COUNT_FIELDS = (
    "prefix_cap",
    "visible_identity_count",
    "original_response_selected_url_count",
    "original_response_query_local_url_count",
    "raw_first_wave_page_count",
    "raw_page_visible_link_count",
    "resolved_public_http_link_count",
    "rejected_invalid_or_non_http_link_count",
    "rejected_private_or_credential_link_count",
    "unique_visible_link_count_before_exclusion",
    "excluded_original_or_selected_link_count",
    "available_visible_link_count",
    "visible_link_prefix_cap",
    "authority_bound_attesting_page_count",
    "same_origin_strict_child_link_count",
    "unique_identity_child_link_count",
    "ambiguous_identity_child_link_count",
    "attested_unique_identity_child_link_count",
    "available_attested_unique_identity_child_link_count",
    "prior_covered_distinct_identity_count",
    "available_uncovered_attested_distinct_identity_count",
    "control_selected_visible_link_count",
    "candidate_selected_visible_link_count",
    "control_attested_child_link_count",
    "candidate_attested_child_link_count",
    "control_new_distinct_identity_count",
    "candidate_new_distinct_identity_count",
    "new_distinct_identity_gain",
    "control_total_selected_url_count",
    "candidate_total_selected_url_count",
    "selection_changed",
)


def _identity_vectors(question: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    identities = visible_identities(question)
    output: list[tuple[str, tuple[str, ...]]] = []
    for identity in identities:
        vector = tuple(token for token in _tokens(identity) if len(token) >= 2)
        if vector:
            output.append((identity, vector))
    # Coverage optimization must represent the entire visible row vector.  It
    # may not silently discard an identity that lacks a safe URL-path token.
    return tuple(output) if len(output) == len(identities) else ()


def _identity_matches(
    url: str, vectors: Sequence[tuple[str, tuple[str, ...]]]
) -> tuple[int, ...]:
    path_tokens = _url_path_tokens(url)
    return tuple(
        index
        for index, (_identity, vector) in enumerate(vectors)
        if set(vector).issubset(path_tokens)
    )


def _covered_identities(
    urls: Sequence[str] | set[str] | frozenset[str],
    vectors: Sequence[tuple[str, tuple[str, ...]]],
) -> set[int]:
    covered: set[int] = set()
    for url in urls:
        matches = _identity_matches(str(url), vectors)
        if len(matches) == 1:
            covered.add(matches[0])
    return covered


def _visible_links(
    page_batches: object,
    *,
    question: str,
    vectors: Sequence[tuple[str, tuple[str, ...]]],
) -> tuple[list[dict[str, Any]], dict[str, int], set[str]]:
    pages = _page_results(page_batches)
    by_url: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    page_urls: set[str] = set()
    raw_count = 0
    resolved_count = 0
    invalid_count = 0
    private_count = 0
    authority_pages = 0
    for page in pages:
        source_urls = _page_urls(page)
        page_urls.update(source_urls)
        raw_base, parent_url = _attesting_base(page)
        authority_bound = bool(
            parent_url and _authority_url_bound(parent_url, question=question)
        )
        authority_pages += int(authority_bound)
        raw_links = _sequence(page.get("page_links"))
        if not raw_base:
            raw_count += len(raw_links)
            invalid_count += len(raw_links)
            continue
        for raw_link in raw_links:
            raw_count += 1
            if not isinstance(raw_link, Mapping):
                invalid_count += 1
                continue
            canonical, status = _public_link(raw_link.get("url"), base_url=raw_base)
            if status == "private_or_credential":
                private_count += 1
                continue
            if status != "ok":
                invalid_count += 1
                continue
            resolved_count += 1
            same_origin_child = _strict_same_origin_child(parent_url, canonical)
            # Identity ownership belongs to the canonical child URL itself;
            # authority attestation belongs to this particular parent-child
            # occurrence.  Keeping these separate lets a first unbound
            # occurrence gain a later valid attestation without reordering.
            matches = _identity_matches(canonical, vectors)
            unique_identity = matches[0] if len(matches) == 1 else None
            ambiguous_identity = len(matches) > 1
            attested = bool(
                authority_bound
                and same_origin_child
                and unique_identity is not None
            )
            if canonical not in by_url:
                order.append(canonical)
                by_url[canonical] = {
                    "lead": {
                        "title": "",
                        "url": canonical,
                        "fetch_url": canonical,
                        "content": "",
                        "raw_content": "",
                        "score": None,
                        "source_type": "same_run_distinct_identity_attested_child",
                        "member_label": "",
                    },
                    "same_origin_child": same_origin_child,
                    "unique_identity": unique_identity,
                    "ambiguous_identity": ambiguous_identity,
                    "attested": attested,
                }
                continue
            prior = by_url[canonical]
            prior["same_origin_child"] = bool(
                prior["same_origin_child"] or same_origin_child
            )
            # URL-path identity ownership is independent of the attesting page.
            # A duplicate can gain authority attestation but cannot change owner.
            prior["attested"] = bool(prior["attested"] or attested)
    links = [by_url[url] for url in order]
    counts = {
        "raw_first_wave_page_count": len(pages),
        "raw_page_visible_link_count": raw_count,
        "resolved_public_http_link_count": resolved_count,
        "rejected_invalid_or_non_http_link_count": invalid_count,
        "rejected_private_or_credential_link_count": private_count,
        "authority_bound_attesting_page_count": authority_pages,
        "same_origin_strict_child_link_count": sum(
            bool(value["same_origin_child"]) for value in links
        ),
        "unique_identity_child_link_count": sum(
            value["same_origin_child"] and value["unique_identity"] is not None
            for value in links
        ),
        "ambiguous_identity_child_link_count": sum(
            value["same_origin_child"] and bool(value["ambiguous_identity"])
            for value in links
        ),
        "attested_unique_identity_child_link_count": sum(
            bool(value["attested"]) for value in links
        ),
    }
    return links, counts, page_urls


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "strategy_eligible": bool(value["strategy_eligible"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "completed_search_prefix_identical_and_first_in_both_arms": True,
        "original_first_wave_pages_excluded_from_refetch": True,
        "prior_coverage_uses_only_unique_visible_identity_url_path_binding": True,
        "relative_links_resolved_against_attesting_page": True,
        "stable_first_seen_canonical_url_deduplication": True,
        "duplicate_child_attestations_merged_without_reordering": True,
        "attesting_page_requires_exact_distinctive_authority_url_token": True,
        "child_requires_exact_scheme_host_and_effective_port_origin": True,
        "child_requires_strict_collection_path_descendant": True,
        "child_requires_exactly_one_visible_identity_path_binding": True,
        "candidate_first_pass_uses_at_most_one_link_per_uncovered_identity": True,
        "shared_search_prefix_and_canonical_equivalents_excluded_before_ranking": True,
        "same_complete_visible_link_set_before_cap": True,
        "same_matched_prefix_cost": True,
        "stable_order_preserved_within_distinct_identity_and_remainder_partitions": True,
        "page_body_title_anchor_text_provider_narrative_snippet_query_score_or_field_value_used_for_ranking": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "additional_search_fetch_model_token_context_byte_wall_or_network_cap": False,
        "contains_question_identity_authority_query_url_anchor_page_record_value_prediction_answer_hash_opaque_id_or_credential": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    bool_fields = ("strategy_eligible", "mechanism_engaged")
    true_flags = (
        "completed_search_prefix_identical_and_first_in_both_arms",
        "original_first_wave_pages_excluded_from_refetch",
        "prior_coverage_uses_only_unique_visible_identity_url_path_binding",
        "relative_links_resolved_against_attesting_page",
        "stable_first_seen_canonical_url_deduplication",
        "duplicate_child_attestations_merged_without_reordering",
        "attesting_page_requires_exact_distinctive_authority_url_token",
        "child_requires_exact_scheme_host_and_effective_port_origin",
        "child_requires_strict_collection_path_descendant",
        "child_requires_exactly_one_visible_identity_path_binding",
        "candidate_first_pass_uses_at_most_one_link_per_uncovered_identity",
        "shared_search_prefix_and_canonical_equivalents_excluded_before_ranking",
        "same_complete_visible_link_set_before_cap",
        "same_matched_prefix_cost",
        "stable_order_preserved_within_distinct_identity_and_remainder_partitions",
    )
    false_flags = (
        "page_body_title_anchor_text_provider_narrative_snippet_query_score_or_field_value_used_for_ranking",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_token_context_byte_wall_or_network_cap",
        "contains_question_identity_authority_query_url_anchor_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *bool_fields,
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
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or not 2 <= copied["visible_identity_count"] <= 32
        or copied["original_response_selected_url_count"] > copied["prefix_cap"]
        or copied["visible_link_prefix_cap"]
        != copied["prefix_cap"] - copied["original_response_selected_url_count"]
        or copied["resolved_public_http_link_count"]
        + copied["rejected_invalid_or_non_http_link_count"]
        + copied["rejected_private_or_credential_link_count"]
        != copied["raw_page_visible_link_count"]
        or copied["authority_bound_attesting_page_count"]
        > copied["raw_first_wave_page_count"]
        or copied["same_origin_strict_child_link_count"]
        > copied["unique_visible_link_count_before_exclusion"]
        or copied["unique_identity_child_link_count"]
        + copied["ambiguous_identity_child_link_count"]
        > copied["same_origin_strict_child_link_count"]
        or copied["attested_unique_identity_child_link_count"]
        > copied["unique_identity_child_link_count"]
        or copied["unique_visible_link_count_before_exclusion"]
        != copied["available_visible_link_count"]
        + copied["excluded_original_or_selected_link_count"]
        or copied["available_attested_unique_identity_child_link_count"]
        > copied["attested_unique_identity_child_link_count"]
        or copied["available_attested_unique_identity_child_link_count"]
        > copied["available_visible_link_count"]
        or copied["prior_covered_distinct_identity_count"]
        > copied["visible_identity_count"]
        or copied["available_uncovered_attested_distinct_identity_count"]
        > copied["visible_identity_count"]
        - copied["prior_covered_distinct_identity_count"]
        or copied["control_selected_visible_link_count"]
        != copied["candidate_selected_visible_link_count"]
        or copied["control_selected_visible_link_count"]
        > copied["visible_link_prefix_cap"]
        or copied["control_attested_child_link_count"]
        > copied["control_selected_visible_link_count"]
        or copied["candidate_attested_child_link_count"]
        > copied["candidate_selected_visible_link_count"]
        or copied["control_new_distinct_identity_count"]
        > copied["control_attested_child_link_count"]
        or copied["candidate_new_distinct_identity_count"]
        > copied["candidate_attested_child_link_count"]
        or copied["new_distinct_identity_gain"]
        != copied["candidate_new_distinct_identity_count"]
        - copied["control_new_distinct_identity_count"]
        or copied["control_total_selected_url_count"]
        != copied["original_response_selected_url_count"]
        + copied["control_selected_visible_link_count"]
        or copied["candidate_total_selected_url_count"]
        != copied["original_response_selected_url_count"]
        + copied["candidate_selected_visible_link_count"]
        or copied["control_total_selected_url_count"]
        != copied["candidate_total_selected_url_count"]
        or copied["selection_changed"] not in {0, 1}
        or copied["selection_changed"]
        != int(copied["new_distinct_identity_gain"] > 0)
        or copied["strategy_eligible"]
        is not bool(
            copied["available_uncovered_attested_distinct_identity_count"] > 0
            and copied["visible_link_prefix_cap"] > 0
        )
        or copied["mechanism_engaged"] is not bool(copied["selection_changed"])
        or copied["mechanism_engaged"] and not copied["strategy_eligible"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.15 distinct-identity selection receipt drifted")
    return copied


def select_distinct_identity_child_prefixes(
    first_wave_page_batches: object,
    second_wave_raw: object,
    *,
    question: str,
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.15 visible question is absent")
    vectors = _identity_vectors(question)
    if len(vectors) < 2:
        raise ValueError("V2.50.15 strict visible multi-identity vector is absent")
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.50.15 prefix cap is invalid")
    if isinstance(exclude_urls, (str, bytes)):
        raise ValueError("V2.50.15 exclusion vector is invalid")
    excluded = {
        canonicalize_url(str(value))
        for value in exclude_urls
        if canonicalize_url(str(value))
    }
    original = select_matched_prefixes(
        second_wave_raw,
        question=question,
        cap=cap,
        exclude_urls=excluded,
    )
    shared_prefix = copy.deepcopy(original["control"])
    shared_urls = {
        canonicalize_url(str(value.get("url") or ""))
        for value in shared_prefix
        if isinstance(value, Mapping)
        and canonicalize_url(str(value.get("url") or ""))
    }
    links, link_counts, first_page_urls = _visible_links(
        first_wave_page_batches,
        question=question,
        vectors=vectors,
    )
    unique_before = len(links)
    prior_urls = excluded | shared_urls | first_page_urls
    prior_covered = _covered_identities(prior_urls, vectors)
    available = [value for value in links if value["lead"]["url"] not in prior_urls]
    available_attested = [value for value in available if value["attested"]]
    uncovered_attested = [
        value
        for value in available_attested
        if value["unique_identity"] not in prior_covered
    ]
    uncovered_identity_set = {
        int(value["unique_identity"]) for value in uncovered_attested
    }
    link_cap = cap - len(shared_prefix)
    control_values = available[:link_cap]
    first_per_identity: list[dict[str, Any]] = []
    selected_identity_indices: set[int] = set()
    for value in uncovered_attested:
        identity_index = int(value["unique_identity"])
        if identity_index in selected_identity_indices:
            continue
        first_per_identity.append(value)
        selected_identity_indices.add(identity_index)
    first_urls = {value["lead"]["url"] for value in first_per_identity}
    remainder = [value for value in available if value["lead"]["url"] not in first_urls]
    candidate_values = [*first_per_identity, *remainder][:link_cap]

    def selected_counts(values: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
        attested_count = sum(bool(value["attested"]) for value in values)
        identities = {
            int(value["unique_identity"])
            for value in values
            if value["attested"]
            and value["unique_identity"] is not None
            and int(value["unique_identity"]) not in prior_covered
        }
        return attested_count, len(identities)

    control_attested, control_distinct = selected_counts(control_values)
    candidate_attested, candidate_distinct = selected_counts(candidate_values)
    if candidate_distinct <= control_distinct:
        candidate_values = list(control_values)
        candidate_attested = control_attested
        candidate_distinct = control_distinct
    control_links = [copy.deepcopy(value["lead"]) for value in control_values]
    candidate_links = [copy.deepcopy(value["lead"]) for value in candidate_values]
    control = [*copy.deepcopy(shared_prefix), *copy.deepcopy(control_links)]
    candidate = [*copy.deepcopy(shared_prefix), *copy.deepcopy(candidate_links)]
    available_urls = [value["lead"]["url"] for value in available]
    if (
        len(set(available_urls)) != len(available_urls)
        or len(control) != len(candidate)
        or len(control) > cap
        or control[: len(shared_prefix)] != shared_prefix
        or candidate[: len(shared_prefix)] != shared_prefix
    ):
        raise RuntimeError("V2.50.15 matched prefix invariant drifted")
    selection_changed = control != candidate
    identity_gain = candidate_distinct - control_distinct
    if selection_changed is not (identity_gain > 0):
        raise RuntimeError("V2.50.15 distinct identity gain invariant drifted")
    original_receipt = original["content_free_receipt"]
    receipt = _receipt(
        {
            "prefix_cap": cap,
            "visible_identity_count": len(vectors),
            "original_response_selected_url_count": len(shared_prefix),
            "original_response_query_local_url_count": min(
                int(original_receipt["available_query_local_url_count"]), cap
            ),
            **link_counts,
            "unique_visible_link_count_before_exclusion": unique_before,
            "excluded_original_or_selected_link_count": unique_before - len(available),
            "available_visible_link_count": len(available),
            "visible_link_prefix_cap": link_cap,
            "available_attested_unique_identity_child_link_count": len(
                available_attested
            ),
            "prior_covered_distinct_identity_count": len(prior_covered),
            "available_uncovered_attested_distinct_identity_count": len(
                uncovered_identity_set
            ),
            "control_selected_visible_link_count": len(control_links),
            "candidate_selected_visible_link_count": len(candidate_links),
            "control_attested_child_link_count": control_attested,
            "candidate_attested_child_link_count": candidate_attested,
            "control_new_distinct_identity_count": control_distinct,
            "candidate_new_distinct_identity_count": candidate_distinct,
            "new_distinct_identity_gain": identity_gain,
            "control_total_selected_url_count": len(control),
            "candidate_total_selected_url_count": len(candidate),
            "selection_changed": int(selection_changed),
            "strategy_eligible": bool(uncovered_identity_set and link_cap > 0),
            "mechanism_engaged": selection_changed,
        }
    )
    result: dict[str, Any] = {
        "artifact_version": 1,
        "policy_id": POLICY_ID,
        "shared_search_prefix": shared_prefix,
        "control_visible_links": control_links,
        "candidate_visible_links": candidate_links,
        "control": control,
        "candidate": candidate,
        "content_free_receipt": receipt,
    }
    result["artifact_payload_sha256"] = hashlib.sha256(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return result


def validate_result(
    value: Mapping[str, Any],
    *,
    first_wave_page_batches: object,
    second_wave_raw: object,
    question: str,
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    receipt = copied.get("content_free_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("V2.50.15 selection receipt is absent")
    validate_receipt(receipt)
    expected = select_distinct_identity_child_prefixes(
        first_wave_page_batches,
        second_wave_raw,
        question=question,
        cap=cap,
        exclude_urls=exclude_urls,
    )
    if copied != expected:
        raise ValueError("V2.50.15 selection replay drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "select_distinct_identity_child_prefixes",
    "validate_receipt",
    "validate_result",
]
