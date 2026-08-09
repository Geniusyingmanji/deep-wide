"""Pure selection over links visibly attested by same-run fetched pages.

The completed second-wave search prefix is common to both arms and can never
be displaced.  Only the remaining fetch slots are filled from ``page_links``
attached to the already-fetched first-wave pages.  The control uses stable
first-seen link order.  The candidate uses V2.49.98's exact URL-path identity
plus distinctive authority-token binding, preserving stable order within the
bound and unbound partitions.  If that reordering does not strictly increase
the number of bound links inside the matched prefix, the candidate is an exact
copy of the control.

This component is deliberately pure.  It resolves relative links, rejects
syntactically non-public destinations, canonicalizes and deduplicates URLs,
but performs no DNS, network, file, process, model, evaluator, or benchmark
operation.  Page text, page titles, provider prose, snippets, scores, labels,
gold, rewards, and historical outcomes are not selection inputs.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urljoin, urlsplit

from .clients import canonicalize_url
from .v24263_global_model_limiter import payload_sha256
from .v24998_identity_authority_action_selection import (
    identity_authority_bound,
    select_matched_prefixes,
)


POLICY_ID = "v25001_page_visible_link_selection_v1"
RECEIPT_ROLE = "v25001_content_free_page_visible_link_selection_receipt"
_MAXIMUM_LINK_TEXT_CHARACTERS = 1_000
_COUNT_FIELDS = (
    "prefix_cap",
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
    "identity_authority_bound_visible_link_count",
    "control_selected_visible_link_count",
    "candidate_selected_visible_link_count",
    "control_bound_visible_link_count",
    "candidate_bound_visible_link_count",
    "bound_visible_link_gain",
    "control_total_selected_url_count",
    "candidate_total_selected_url_count",
    "selection_changed",
)


def _sequence(value: object) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return list(value)


def _page_results(page_batches: object) -> list[Mapping[str, Any]]:
    return [
        result
        for batch in _sequence(page_batches)
        if isinstance(batch, Mapping)
        for result in _sequence(batch.get("results"))
        if isinstance(result, Mapping)
    ]


def _public_link(raw: object, *, base_url: str) -> tuple[str, str]:
    """Return ``(canonical, rejection_class)`` without DNS or I/O."""

    value = str(raw or "").strip()
    if not value or "\x00" in value:
        return "", "invalid"
    try:
        absolute = urljoin(base_url, value)
        parsed = urlsplit(absolute)
        if (
            parsed.scheme.casefold() not in {"http", "https"}
            or not parsed.hostname
        ):
            return "", "invalid"
        if parsed.username or parsed.password:
            return "", "private_or_credential"
        _ = parsed.port
    except ValueError:
        return "", "invalid"
    hostname = (parsed.hostname or "").rstrip(".").casefold()
    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    ):
        return "", "private_or_credential"
    try:
        address = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        return "", "private_or_credential"
    canonical = canonicalize_url(absolute)
    if not canonical:
        return "", "invalid"
    return canonical, "ok"


def _page_urls(page: Mapping[str, Any]) -> set[str]:
    output: set[str] = set()
    for name in ("requested_url", "fetch_url", "url"):
        canonical = canonicalize_url(str(page.get(name) or ""))
        if canonical:
            output.add(canonical)
    return output


def _visible_links(
    page_batches: object,
) -> tuple[list[dict[str, str]], dict[str, int], set[str]]:
    pages = _page_results(page_batches)
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    page_urls: set[str] = set()
    raw_count = 0
    resolved_count = 0
    invalid_count = 0
    private_count = 0
    for page in pages:
        source_urls = _page_urls(page)
        page_urls.update(source_urls)
        # Keep the attested spelling (notably a trailing slash) for RFC 3986
        # relative resolution.  Canonicalization is only the validity gate and
        # the final deduplication representation.
        base = ""
        for name in ("url", "requested_url", "fetch_url"):
            raw_base = str(page.get(name) or "").strip()
            if canonicalize_url(raw_base):
                base = raw_base
                break
        raw_links = _sequence(page.get("page_links"))
        if not base:
            raw_count += len(raw_links)
            invalid_count += len(raw_links)
            continue
        for raw_link in raw_links:
            if not isinstance(raw_link, Mapping):
                invalid_count += 1
                raw_count += 1
                continue
            raw_count += 1
            canonical, status = _public_link(raw_link.get("url"), base_url=base)
            if status == "private_or_credential":
                private_count += 1
                continue
            if status != "ok":
                invalid_count += 1
                continue
            resolved_count += 1
            if canonical in seen:
                continue
            label = re.sub(r"\s+", " ", str(raw_link.get("text") or "")).strip()
            output.append(
                {
                    "title": label[:500],
                    "url": canonical,
                    "fetch_url": canonical,
                    "content": "",
                    "raw_content": "",
                    "score": None,
                    "source_type": "same_run_page_visible_link",
                    "member_label": label[:_MAXIMUM_LINK_TEXT_CHARACTERS],
                }
            )
            seen.add(canonical)
    counts = {
        "raw_first_wave_page_count": len(pages),
        "raw_page_visible_link_count": raw_count,
        "resolved_public_http_link_count": resolved_count,
        "rejected_invalid_or_non_http_link_count": invalid_count,
        "rejected_private_or_credential_link_count": private_count,
    }
    return output, counts, page_urls


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
        "relative_links_resolved_against_attesting_page": True,
        "stable_first_seen_canonical_url_deduplication": True,
        "same_complete_visible_link_set_before_cap": True,
        "same_matched_prefix_cost": True,
        "candidate_uses_v24998_exact_url_identity_authority_binding": True,
        "stable_order_preserved_within_bound_and_unbound_partitions": True,
        "page_body_title_provider_narrative_snippet_query_or_score_used_for_link_ranking": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "additional_search_fetch_model_token_context_byte_wall_or_network_cap": False,
        "contains_question_identity_authority_query_url_anchor_page_prediction_answer_hash_opaque_id_or_credential": False,
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
        "relative_links_resolved_against_attesting_page",
        "stable_first_seen_canonical_url_deduplication",
        "same_complete_visible_link_set_before_cap",
        "same_matched_prefix_cost",
        "candidate_uses_v24998_exact_url_identity_authority_binding",
        "stable_order_preserved_within_bound_and_unbound_partitions",
    )
    false_flags = (
        "page_body_title_provider_narrative_snippet_query_or_score_used_for_link_ranking",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_token_context_byte_wall_or_network_cap",
        "contains_question_identity_authority_query_url_anchor_page_prediction_answer_hash_opaque_id_or_credential",
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
        or copied["original_response_selected_url_count"] > copied["prefix_cap"]
        or copied["visible_link_prefix_cap"]
        != copied["prefix_cap"] - copied["original_response_selected_url_count"]
        or copied["resolved_public_http_link_count"]
        + copied["rejected_invalid_or_non_http_link_count"]
        + copied["rejected_private_or_credential_link_count"]
        != copied["raw_page_visible_link_count"]
        or copied["unique_visible_link_count_before_exclusion"]
        != copied["available_visible_link_count"]
        + copied["excluded_original_or_selected_link_count"]
        or copied["identity_authority_bound_visible_link_count"]
        > copied["available_visible_link_count"]
        or copied["control_selected_visible_link_count"]
        != copied["candidate_selected_visible_link_count"]
        or copied["control_selected_visible_link_count"]
        > copied["visible_link_prefix_cap"]
        or copied["control_bound_visible_link_count"]
        > copied["control_selected_visible_link_count"]
        or copied["candidate_bound_visible_link_count"]
        > copied["candidate_selected_visible_link_count"]
        or copied["candidate_bound_visible_link_count"]
        < copied["control_bound_visible_link_count"]
        or copied["bound_visible_link_gain"]
        != copied["candidate_bound_visible_link_count"]
        - copied["control_bound_visible_link_count"]
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
        != int(copied["bound_visible_link_gain"] > 0)
        or copied["mechanism_engaged"] is not bool(copied["selection_changed"])
        or copied["mechanism_engaged"] and not copied["strategy_eligible"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.01 page-visible-link receipt drifted")
    return copied


def select_page_visible_link_prefixes(
    first_wave_page_batches: object,
    second_wave_raw: object,
    *,
    question: str,
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    """Return matched full prefixes and the link-only treatment projection."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.01 visible question is absent")
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.50.01 prefix cap is invalid")
    if isinstance(exclude_urls, (str, bytes)):
        raise ValueError("V2.50.01 exclusion vector is invalid")
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
    # The stable control projection is the completed-search common prefix.
    # The prior V2.49.98 candidate is intentionally not composed here.
    shared_prefix = copy.deepcopy(original["control"])
    shared_urls = {
        canonicalize_url(str(value.get("url") or ""))
        for value in shared_prefix
        if isinstance(value, Mapping)
        and canonicalize_url(str(value.get("url") or ""))
    }
    links, link_counts, first_page_urls = _visible_links(first_wave_page_batches)
    unique_before = len(links)
    all_excluded = excluded | shared_urls | first_page_urls
    available = [value for value in links if value["url"] not in all_excluded]
    bound = [
        value
        for value in available
        if identity_authority_bound(value, question=question)
    ]
    bound_urls = {value["url"] for value in bound}
    unbound = [value for value in available if value["url"] not in bound_urls]
    link_cap = cap - len(shared_prefix)
    control_links = copy.deepcopy(available[:link_cap])
    candidate_links = copy.deepcopy([*bound, *unbound][:link_cap])
    control_bound = sum(value["url"] in bound_urls for value in control_links)
    candidate_bound = sum(value["url"] in bound_urls for value in candidate_links)
    if candidate_bound <= control_bound:
        candidate_links = copy.deepcopy(control_links)
        candidate_bound = control_bound
    control = [*copy.deepcopy(shared_prefix), *copy.deepcopy(control_links)]
    candidate = [*copy.deepcopy(shared_prefix), *copy.deepcopy(candidate_links)]
    if (
        len(control) != len(candidate)
        or len(control) > cap
        or control[: len(shared_prefix)] != shared_prefix
        or candidate[: len(shared_prefix)] != shared_prefix
    ):
        raise RuntimeError("V2.50.01 matched prefix invariant drifted")
    selection_changed = control != candidate
    original_receipt = original["content_free_receipt"]
    receipt = _receipt(
        {
            "prefix_cap": cap,
            "original_response_selected_url_count": len(shared_prefix),
            "original_response_query_local_url_count": min(
                int(original_receipt["available_query_local_url_count"]), cap
            ),
            **link_counts,
            "unique_visible_link_count_before_exclusion": unique_before,
            "excluded_original_or_selected_link_count": unique_before
            - len(available),
            "available_visible_link_count": len(available),
            "visible_link_prefix_cap": link_cap,
            "identity_authority_bound_visible_link_count": len(bound),
            "control_selected_visible_link_count": len(control_links),
            "candidate_selected_visible_link_count": len(candidate_links),
            "control_bound_visible_link_count": control_bound,
            "candidate_bound_visible_link_count": candidate_bound,
            "bound_visible_link_gain": candidate_bound - control_bound,
            "control_total_selected_url_count": len(control),
            "candidate_total_selected_url_count": len(candidate),
            "selection_changed": int(selection_changed),
            "strategy_eligible": bool(bound and link_cap > 0),
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
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
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
        raise ValueError("V2.50.01 selection receipt is absent")
    validate_receipt(receipt)
    expected = select_page_visible_link_prefixes(
        first_wave_page_batches,
        second_wave_raw,
        question=question,
        cap=cap,
        exclude_urls=exclude_urls,
    )
    if copied != expected:
        raise ValueError("V2.50.01 selection replay drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "select_page_visible_link_prefixes",
    "validate_receipt",
    "validate_result",
]
