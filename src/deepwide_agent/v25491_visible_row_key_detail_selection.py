"""Pure same-forward visible-link selection for one row-key detail fetch.

The completed parent table supplies the exact visible row keys.  Candidate
URLs come only from ``page_links`` returned by pages fetched in that same
forward pass.  A link is eligible only when it is a public, same-origin strict
child of the attesting page and both its URL path and visible anchor text bind
exactly one identical parent row key.  Already-fetched URLs are excluded.

At most one globally unambiguous URL is returned.  Multiple URLs for one row,
multiple otherwise eligible rows, missing bindings, and malformed/private
links all fail closed.  No URL is synthesized from a row key and no question,
authority vocabulary, model inference, score, evaluator, benchmark label, or
historical outcome participates.  This module performs no I/O and authorizes
no launch.  Entropy/information gain remains shadow-only with zero credit.
"""

from __future__ import annotations

import copy
import hashlib
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from . import v25004_identity_bound_detail_fields as identity_surface
from . import v25010_attested_child_detail_selection as visible_links
from . import v25432_source_authoritative_field_candidate as table_source
from . import v25464_row_key_bound_structured_source_candidate as row_bound


POLICY_ID = "v25491_visible_row_key_detail_selection_v1"
ROLE = "v25491_visible_row_key_detail_selection"
RECEIPT_ROLE = "v25491_content_free_visible_row_key_detail_selection_receipt"
MAXIMUM_DIRECT_REQUESTS = 1
REQUEST_QUERY = "same-run visible row-key-bound detail page"
_REQUEST_KEYS = frozenset({"url", "query", "title", "member_label"})
_CANDIDATE_KEYS = frozenset(
    {"url", "row_identity", "anchor_text", "attesting_page_url"}
)
_COUNT_FIELDS = (
    "base_row_count",
    "visible_column_count",
    "raw_fetch_batch_count",
    "raw_fetched_page_count",
    "raw_page_visible_link_count",
    "resolved_public_http_link_count",
    "rejected_invalid_or_non_http_link_count",
    "rejected_private_or_credential_link_count",
    "same_origin_strict_child_link_count",
    "url_path_bound_link_count",
    "anchor_surface_bound_link_count",
    "joint_bound_link_count",
    "ambiguous_joint_link_count",
    "already_fetched_link_count",
    "duplicate_valid_occurrence_count",
    "conflicting_url_identity_count",
    "unique_joint_bound_link_count",
    "ambiguous_row_link_count",
    "eligible_unique_link_count",
    "global_multi_candidate_handoff_count",
    "logical_request_count",
    "positive_signed_credit_count",
)


payload_sha256 = table_source.payload_sha256


def _sequence(value: object) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return list(value)


def _page_results(fetch_batches: object) -> list[Mapping[str, Any]]:
    return [
        result
        for batch in _sequence(fetch_batches)
        if isinstance(batch, Mapping)
        for result in _sequence(batch.get("results"))
        if isinstance(result, Mapping)
    ]


def _attesting_base(page: Mapping[str, Any]) -> tuple[str, str]:
    for name in ("url", "requested_url", "fetch_url"):
        raw = str(page.get(name) or "").strip()
        canonical = canonicalize_url(raw)
        if canonical:
            return raw, canonical
    return "", ""


def _page_urls(page: Mapping[str, Any]) -> set[str]:
    output: set[str] = set()
    for name in ("url", "requested_url", "fetch_url"):
        canonical = canonicalize_url(str(page.get(name) or ""))
        if canonical:
            output.add(canonical)
    return output


def _joint_identity(
    url: str,
    anchor_text: str,
    identities: Sequence[str],
) -> tuple[str | None, bool, bool, bool]:
    path_matches = [
        identity
        for identity in identities
        if row_bound._identity_path_bound(url, identity)
    ]
    surface_matches = [
        identity
        for identity in identities
        if identity_surface._page_identity_bound(
            {"url": url, "title": anchor_text, "content": ""}, identity
        )
    ]
    joint = [
        identity
        for identity in identities
        if identity in path_matches and identity in surface_matches
    ]
    return (
        joint[0] if len(joint) == 1 else None,
        bool(path_matches),
        bool(surface_matches),
        len(joint) > 1,
    )


def _receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "row_keys_come_only_from_completed_parent_table": True,
        "candidate_urls_come_only_from_same_forward_visible_page_links": True,
        "relative_links_resolved_against_attesting_page": True,
        "public_http_and_no_url_credentials_required": True,
        "same_origin_strict_child_path_required": True,
        "url_path_and_anchor_must_bind_one_identical_parent_row_key": True,
        "already_fetched_urls_excluded": True,
        "one_url_per_row_and_one_global_candidate_required": True,
        "stable_canonical_deduplication_without_ranking": True,
        "url_synthesis_question_authority_vocabulary_or_model_inference_absent": True,
        "contains_question_url_anchor_row_identity_page_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "row_keys_come_only_from_completed_parent_table",
        "candidate_urls_come_only_from_same_forward_visible_page_links",
        "relative_links_resolved_against_attesting_page",
        "public_http_and_no_url_credentials_required",
        "same_origin_strict_child_path_required",
        "url_path_and_anchor_must_bind_one_identical_parent_row_key",
        "already_fetched_urls_excluded",
        "one_url_per_row_and_one_global_candidate_required",
        "stable_canonical_deduplication_without_ranking",
        "url_synthesis_question_authority_vocabulary_or_model_inference_absent",
    )
    false_flags = (
        "contains_question_url_anchor_row_identity_page_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
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
        or copied["resolved_public_http_link_count"]
        + copied["rejected_invalid_or_non_http_link_count"]
        + copied["rejected_private_or_credential_link_count"]
        != copied["raw_page_visible_link_count"]
        or copied["joint_bound_link_count"]
        > copied["same_origin_strict_child_link_count"]
        or copied["unique_joint_bound_link_count"]
        > copied["joint_bound_link_count"]
        or copied["eligible_unique_link_count"]
        > copied["unique_joint_bound_link_count"]
        or copied["logical_request_count"] not in {0, 1}
        or copied["logical_request_count"]
        != int(
            copied["eligible_unique_link_count"] == 1
            and copied["global_multi_candidate_handoff_count"] == 0
        )
        or copied["global_multi_candidate_handoff_count"] not in {0, 1}
        or copied["global_multi_candidate_handoff_count"]
        != int(copied["eligible_unique_link_count"] > 1)
        or copied["positive_signed_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.91 selection receipt drifted")
    return copied


def build_selection(
    base_prediction: str,
    *,
    columns: Sequence[str],
    fetch_batches: object,
) -> dict[str, Any]:
    required, rows = table_source._canonical_table(str(base_prediction), columns)
    identities = [str(row[0]) for row in rows]
    if len({table_source._key(value) for value in identities}) != len(identities):
        raise ValueError("V2.54.91 parent row keys are not unique")
    pages = _page_results(fetch_batches)
    counts: Counter[str] = Counter(
        base_row_count=len(rows),
        visible_column_count=len(required),
        raw_fetch_batch_count=len(_sequence(fetch_batches)),
        raw_fetched_page_count=len(pages),
    )
    fetched_urls = set().union(*(_page_urls(page) for page in pages)) if pages else set()
    occurrences: list[dict[str, str]] = []
    for page in pages:
        raw_base, parent_url = _attesting_base(page)
        raw_links = _sequence(page.get("page_links"))
        if not raw_base:
            counts["raw_page_visible_link_count"] += len(raw_links)
            counts["rejected_invalid_or_non_http_link_count"] += len(raw_links)
            continue
        for raw_link in raw_links:
            counts["raw_page_visible_link_count"] += 1
            if not isinstance(raw_link, Mapping):
                counts["rejected_invalid_or_non_http_link_count"] += 1
                continue
            url, status = visible_links._public_link(
                raw_link.get("url"), base_url=raw_base
            )
            if status == "private_or_credential":
                counts["rejected_private_or_credential_link_count"] += 1
                continue
            if status != "ok":
                counts["rejected_invalid_or_non_http_link_count"] += 1
                continue
            counts["resolved_public_http_link_count"] += 1
            if url in fetched_urls:
                counts["already_fetched_link_count"] += 1
                continue
            if not visible_links._strict_same_origin_child(parent_url, url):
                continue
            counts["same_origin_strict_child_link_count"] += 1
            anchor = " ".join(str(raw_link.get("text") or "").split())[:1_000]
            identity, path_bound, surface_bound, ambiguous = _joint_identity(
                url, anchor, identities
            )
            counts["url_path_bound_link_count"] += int(path_bound)
            counts["anchor_surface_bound_link_count"] += int(surface_bound)
            counts["ambiguous_joint_link_count"] += int(ambiguous)
            if identity is None:
                continue
            counts["joint_bound_link_count"] += 1
            occurrences.append(
                {
                    "url": url,
                    "row_identity": identity,
                    "anchor_text": anchor,
                    "attesting_page_url": parent_url,
                }
            )

    by_url: dict[str, list[dict[str, str]]] = defaultdict(list)
    order: list[str] = []
    for occurrence in occurrences:
        if occurrence["url"] not in by_url:
            order.append(occurrence["url"])
        by_url[occurrence["url"]].append(occurrence)
    unique: list[dict[str, str]] = []
    for url in order:
        values = by_url[url]
        identities_for_url = {item["row_identity"] for item in values}
        if len(identities_for_url) != 1:
            counts["conflicting_url_identity_count"] += 1
            continue
        counts["duplicate_valid_occurrence_count"] += max(0, len(values) - 1)
        unique.append(copy.deepcopy(values[0]))
    counts["unique_joint_bound_link_count"] = len(unique)

    by_row: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for item in unique:
        by_row[table_source._key(item["row_identity"])].append(item)
    eligible: list[dict[str, str]] = []
    for values in by_row.values():
        if len(values) == 1:
            eligible.extend(values)
        else:
            counts["ambiguous_row_link_count"] += len(values)
    counts["eligible_unique_link_count"] = len(eligible)
    counts["global_multi_candidate_handoff_count"] = int(len(eligible) > 1)
    selected = eligible[0] if len(eligible) == 1 else None
    requests = (
        [
            {
                "url": selected["url"],
                "query": REQUEST_QUERY,
                "title": selected["row_identity"],
                "member_label": selected["row_identity"],
            }
        ]
        if selected is not None
        else []
    )
    counts["logical_request_count"] = len(requests)
    counts["positive_signed_credit_count"] = 0
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode()
        ).hexdigest(),
        "columns": list(required),
        "private_candidates": eligible,
        "requests": requests,
        "content_free_receipt": _receipt(counts),
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_selection(value)


def validate_selection(
    value: Mapping[str, Any],
    *,
    base_prediction: str | None = None,
    columns: Sequence[str] | None = None,
    fetch_batches: object | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    candidates = copied.get("private_candidates")
    requests = copied.get("requests")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "base_prediction_sha256",
        "columns",
        "private_candidates",
        "requests",
        "content_free_receipt",
        "artifact_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("base_prediction_sha256"), str)
        or len(copied["base_prediction_sha256"]) != 64
        or not isinstance(copied.get("columns"), list)
        or not copied["columns"]
        or any(not isinstance(item, str) or not item for item in copied["columns"])
        or not isinstance(candidates, list)
        or any(
            not isinstance(item, Mapping)
            or set(item) != _CANDIDATE_KEYS
            or any(not isinstance(item[name], str) or not item[name] for name in _CANDIDATE_KEYS)
            or canonicalize_url(item["url"]) != item["url"]
            or canonicalize_url(item["attesting_page_url"])
            != item["attesting_page_url"]
            for item in candidates
        )
        or not isinstance(requests, list)
        or len(requests) > MAXIMUM_DIRECT_REQUESTS
        or any(
            not isinstance(request, Mapping)
            or set(request) != _REQUEST_KEYS
            or request.get("query") != REQUEST_QUERY
            or canonicalize_url(str(request.get("url") or "")) != request.get("url")
            or not isinstance(request.get("title"), str)
            or request.get("title") != request.get("member_label")
            for request in requests
        )
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["eligible_unique_link_count"] != len(candidates)
        or receipt["logical_request_count"] != len(requests)
        or (
            requests
            and (
                len(candidates) != 1
                or requests[0]["url"] != candidates[0]["url"]
                or requests[0]["title"] != candidates[0]["row_identity"]
            )
        )
        or (not requests and len(candidates) == 1)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.91 visible row-key detail selection drifted")
    if base_prediction is not None:
        if columns is None or fetch_batches is None:
            raise ValueError("V2.54.91 selection replay inputs are incomplete")
        replay = build_selection(
            str(base_prediction), columns=columns, fetch_batches=fetch_batches
        )
        if replay != copied:
            raise ValueError("V2.54.91 selection replay drifted")
    return copied


__all__ = [
    "MAXIMUM_DIRECT_REQUESTS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "REQUEST_QUERY",
    "ROLE",
    "build_selection",
    "payload_sha256",
    "validate_receipt",
    "validate_selection",
]
