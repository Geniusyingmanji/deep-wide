"""Pure same-origin, index-attested child-detail link selection.

The completed search-response prefix is common and non-displaceable.  Control
fills the remaining slots from public first-wave page links in canonical,
stable first-seen order.  Candidate promotes only a link for which the same
forward visibly establishes this URL-only chain:

``authority-bound attesting page -> same-origin strict child path -> exact
tagged-identity path token -> not already represented by the search prefix``.

The attesting page URL and child URL are the only ranking inputs.  Page text,
title, anchor text, provider prose/snippets, query text, scores, labels, gold,
predictions, rewards, and historical outcomes are ignored.  The component is
pure and performs no file, environment, network, DNS, process, model, search,
benchmark, evaluator, or credential operation.  Entropy/IG assign no credit.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

from .clients import canonicalize_url
from .v24263_global_model_limiter import payload_sha256
from .v24998_identity_authority_action_selection import (
    _authority_tokens,
    _identity_vectors,
    _url_path_tokens,
    _url_tokens,
    select_matched_prefixes,
)


POLICY_ID = "v25010_same_origin_attested_child_detail_selection_v1"
RECEIPT_ROLE = "v25010_content_free_attested_child_detail_selection_receipt"
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
    "authority_bound_attesting_page_count",
    "same_origin_strict_child_link_count",
    "exact_identity_child_link_count",
    "attested_child_detail_link_count",
    "available_attested_child_detail_link_count",
    "control_selected_visible_link_count",
    "candidate_selected_visible_link_count",
    "control_attested_child_detail_link_count",
    "candidate_attested_child_detail_link_count",
    "attested_child_detail_link_gain",
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
    value = str(raw or "").strip()
    if not value or "\x00" in value:
        return "", "invalid"
    try:
        absolute = urljoin(base_url, value)
        parsed = urlsplit(absolute)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
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


def _attesting_base(page: Mapping[str, Any]) -> tuple[str, str]:
    for name in ("url", "requested_url", "fetch_url"):
        raw = str(page.get(name) or "").strip()
        canonical = canonicalize_url(raw)
        if canonical:
            return raw, canonical
    return "", ""


def _origin(url: str) -> tuple[str, str, int] | None:
    canonical = canonicalize_url(url)
    if not canonical:
        return None
    try:
        parsed = urlsplit(canonical)
        scheme = parsed.scheme.casefold()
        host = (parsed.hostname or "").rstrip(".").casefold()
        port = parsed.port
    except ValueError:
        return None
    if scheme not in {"http", "https"} or not host:
        return None
    return scheme, host, int(port or (443 if scheme == "https" else 80))


def _collection_prefix(url: str) -> str:
    canonical = canonicalize_url(url)
    if not canonical:
        return ""
    path = unquote(urlsplit(canonical).path or "/")
    if path.endswith("/"):
        return path
    leaf = path.rsplit("/", 1)[-1]
    if "." in leaf:
        directory = path.rsplit("/", 1)[0]
        return (directory or "") + "/"
    return path + "/"


def _strict_same_origin_child(parent_url: str, child_url: str) -> bool:
    parent_origin = _origin(parent_url)
    child_origin = _origin(child_url)
    if parent_origin is None or child_origin != parent_origin:
        return False
    prefix = _collection_prefix(parent_url)
    child_path = unquote(urlsplit(canonicalize_url(child_url)).path or "/")
    return bool(prefix and child_path.startswith(prefix) and child_path != prefix)


def _identity_path_bound(url: str, *, question: str) -> bool:
    path_tokens = _url_path_tokens(url)
    return any(set(vector).issubset(path_tokens) for vector in _identity_vectors(question))


def _authority_url_bound(url: str, *, question: str) -> bool:
    url_tokens = _url_tokens(url)
    return any(token in url_tokens for token in _authority_tokens(question))


def _visible_links(
    page_batches: object,
    *,
    question: str,
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
        authority_bound = bool(parent_url and _authority_url_bound(parent_url, question=question))
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
            identity_child = bool(
                same_origin_child and _identity_path_bound(canonical, question=question)
            )
            attested = bool(authority_bound and identity_child)
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
                        "source_type": "same_run_attested_child_detail_link",
                        "member_label": "",
                    },
                    "same_origin_child": same_origin_child,
                    "identity_child": identity_child,
                    "attested": attested,
                }
                continue
            prior = by_url[canonical]
            prior["same_origin_child"] = bool(prior["same_origin_child"] or same_origin_child)
            prior["identity_child"] = bool(prior["identity_child"] or identity_child)
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
        "exact_identity_child_link_count": sum(
            bool(value["identity_child"]) for value in links
        ),
        "attested_child_detail_link_count": sum(bool(value["attested"]) for value in links),
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
        "relative_links_resolved_against_attesting_page": True,
        "stable_first_seen_canonical_url_deduplication": True,
        "duplicate_child_attestations_merged_without_reordering": True,
        "attesting_page_requires_exact_distinctive_authority_url_token": True,
        "child_requires_exact_scheme_host_and_effective_port_origin": True,
        "child_requires_strict_collection_path_descendant": True,
        "child_requires_exact_tagged_identity_path_tokens": True,
        "shared_search_prefix_and_canonical_equivalents_excluded_before_ranking": True,
        "same_complete_visible_link_set_before_cap": True,
        "same_matched_prefix_cost": True,
        "stable_order_preserved_within_attested_and_other_partitions": True,
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
        "relative_links_resolved_against_attesting_page",
        "stable_first_seen_canonical_url_deduplication",
        "duplicate_child_attestations_merged_without_reordering",
        "attesting_page_requires_exact_distinctive_authority_url_token",
        "child_requires_exact_scheme_host_and_effective_port_origin",
        "child_requires_strict_collection_path_descendant",
        "child_requires_exact_tagged_identity_path_tokens",
        "shared_search_prefix_and_canonical_equivalents_excluded_before_ranking",
        "same_complete_visible_link_set_before_cap",
        "same_matched_prefix_cost",
        "stable_order_preserved_within_attested_and_other_partitions",
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
        or copied["exact_identity_child_link_count"]
        > copied["same_origin_strict_child_link_count"]
        or copied["attested_child_detail_link_count"]
        > copied["exact_identity_child_link_count"]
        or copied["unique_visible_link_count_before_exclusion"]
        != copied["available_visible_link_count"]
        + copied["excluded_original_or_selected_link_count"]
        or copied["available_attested_child_detail_link_count"]
        > copied["attested_child_detail_link_count"]
        or copied["available_attested_child_detail_link_count"]
        > copied["available_visible_link_count"]
        or copied["control_selected_visible_link_count"]
        != copied["candidate_selected_visible_link_count"]
        or copied["control_selected_visible_link_count"]
        > copied["visible_link_prefix_cap"]
        or copied["control_attested_child_detail_link_count"]
        > copied["control_selected_visible_link_count"]
        or copied["candidate_attested_child_detail_link_count"]
        > copied["candidate_selected_visible_link_count"]
        or copied["candidate_attested_child_detail_link_count"]
        > copied["available_attested_child_detail_link_count"]
        or copied["candidate_attested_child_detail_link_count"]
        < copied["control_attested_child_detail_link_count"]
        or copied["attested_child_detail_link_gain"]
        != copied["candidate_attested_child_detail_link_count"]
        - copied["control_attested_child_detail_link_count"]
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
        != int(copied["attested_child_detail_link_gain"] > 0)
        or copied["strategy_eligible"]
        is not bool(
            copied["available_attested_child_detail_link_count"] > 0
            and copied["visible_link_prefix_cap"] > 0
        )
        or copied["mechanism_engaged"] is not bool(copied["selection_changed"])
        or copied["mechanism_engaged"] and not copied["strategy_eligible"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.10 attested child-detail receipt drifted")
    return copied


def select_attested_child_detail_prefixes(
    first_wave_page_batches: object,
    second_wave_raw: object,
    *,
    question: str,
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.10 visible question is absent")
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.50.10 prefix cap is invalid")
    if isinstance(exclude_urls, (str, bytes)):
        raise ValueError("V2.50.10 exclusion vector is invalid")
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
        first_wave_page_batches, question=question
    )
    unique_before = len(links)
    all_excluded = excluded | shared_urls | first_page_urls
    available = [value for value in links if value["lead"]["url"] not in all_excluded]
    attested = [value for value in available if value["attested"]]
    attested_urls = {value["lead"]["url"] for value in attested}
    other = [value for value in available if value["lead"]["url"] not in attested_urls]
    link_cap = cap - len(shared_prefix)
    control_values = available[:link_cap]
    candidate_values = [*attested, *other][:link_cap]
    control_attested = sum(value["lead"]["url"] in attested_urls for value in control_values)
    candidate_attested = sum(
        value["lead"]["url"] in attested_urls for value in candidate_values
    )
    if candidate_attested <= control_attested:
        candidate_values = list(control_values)
        candidate_attested = control_attested
    control_links = [copy.deepcopy(value["lead"]) for value in control_values]
    candidate_links = [copy.deepcopy(value["lead"]) for value in candidate_values]
    control = [*copy.deepcopy(shared_prefix), *copy.deepcopy(control_links)]
    candidate = [*copy.deepcopy(shared_prefix), *copy.deepcopy(candidate_links)]
    available_urls = [value["lead"]["url"] for value in available]
    partition_urls = [value["lead"]["url"] for value in (*attested, *other)]
    if (
        len(set(available_urls)) != len(available_urls)
        or len(partition_urls) != len(available_urls)
        or set(partition_urls) != set(available_urls)
        or len(control) != len(candidate)
        or len(control) > cap
        or control[: len(shared_prefix)] != shared_prefix
        or candidate[: len(shared_prefix)] != shared_prefix
    ):
        raise RuntimeError("V2.50.10 matched prefix invariant drifted")
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
            "excluded_original_or_selected_link_count": unique_before - len(available),
            "available_visible_link_count": len(available),
            "visible_link_prefix_cap": link_cap,
            "available_attested_child_detail_link_count": len(attested),
            "control_selected_visible_link_count": len(control_links),
            "candidate_selected_visible_link_count": len(candidate_links),
            "control_attested_child_detail_link_count": control_attested,
            "candidate_attested_child_detail_link_count": candidate_attested,
            "attested_child_detail_link_gain": candidate_attested - control_attested,
            "control_total_selected_url_count": len(control),
            "candidate_total_selected_url_count": len(candidate),
            "selection_changed": int(selection_changed),
            "strategy_eligible": bool(attested and link_cap > 0),
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
        raise ValueError("V2.50.10 selection receipt is absent")
    validate_receipt(receipt)
    expected = select_attested_child_detail_prefixes(
        first_wave_page_batches,
        second_wave_raw,
        question=question,
        cap=cap,
        exclude_urls=exclude_urls,
    )
    if copied != expected:
        raise ValueError("V2.50.10 selection replay drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "select_attested_child_detail_prefixes",
    "validate_receipt",
    "validate_result",
]
