"""Visible-only identity/authority binding inside action-source selection.

The legacy task-union path correctly keeps query-local citations first, then
flattens provider action sources in stable first-seen order.  This pure
component preserves that query-local prefix and the complete pre-cap URL set.
Only action-only URLs whose *host/path* contains both an exact tagged identity
token and an exact distinctive token from an explicit visible authority phrase
are moved ahead of other action-only URLs.  Stable order is preserved within
both partitions.

The policy does not inspect page text, provider prose/snippets, query text,
scores, benchmark metadata, predictions, or historical outcomes.  It performs
no I/O, adds no effect budget, assigns no entropy/information-gain credit, and
grants no benchmark or evaluator authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import unquote, urlsplit

from .clients import canonicalize_url
from .v24263_global_model_limiter import payload_sha256
from .v24269_task_union_discovery import _source_lead
from .v24992_hybrid_authority_queries import _authorities, _identities


POLICY_ID = "v24998_visible_identity_authority_action_selection_v1"
RECEIPT_ROLE = "v24998_content_free_identity_authority_selection_receipt"
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_GENERIC_AUTHORITY_TOKENS = frozenset(
    {
        "and",
        "database",
        "directory",
        "from",
        "index",
        "list",
        "official",
        "page",
        "public",
        "record",
        "registry",
        "root",
        "search",
        "site",
        "source",
        "table",
        "the",
        "using",
        "web",
        "website",
        "zone",
    }
)
_COUNT_FIELDS = (
    "prefix_cap",
    "tagged_identity_count",
    "explicit_authority_phrase_count",
    "distinctive_authority_token_count",
    "raw_query_local_source_count",
    "raw_action_source_count",
    "unique_url_count_before_exclusion",
    "excluded_prior_url_count",
    "available_unique_url_count",
    "available_query_local_url_count",
    "available_action_only_url_count",
    "identity_authority_bound_action_url_count",
    "control_selected_url_count",
    "candidate_selected_url_count",
    "selected_query_local_url_count",
    "control_bound_action_url_count",
    "candidate_bound_action_url_count",
    "bound_action_url_gain",
    "selection_changed",
)


def _tokens(value: object) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return tuple(token for token in _TOKEN.findall(normalized) if token)


def _identity_vectors(question: str) -> tuple[tuple[str, ...], ...]:
    output: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for value in _identities(question):
        vector = tuple(token for token in _tokens(value) if len(token) >= 2)
        if vector and vector not in seen:
            output.append(vector)
            seen.add(vector)
    return tuple(output)


def _authority_tokens(question: str) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()
    for authority in _authorities(question):
        for token in _tokens(authority):
            if (
                len(token) < 3
                or token in _GENERIC_AUTHORITY_TOKENS
                or token in seen
            ):
                continue
            output.append(token)
            seen.add(token)
    return tuple(output)


def _url_tokens(raw: object) -> frozenset[str]:
    canonical = canonicalize_url(str(raw or ""))
    if not canonical:
        return frozenset()
    parsed = urlsplit(canonical)
    # A leading-dot identity such as ``.ch`` must not match a site's TLD.
    # Host labels remain useful only for authority binding; identity matching
    # below uses path tokens exclusively.
    host = unquote(parsed.hostname or "")
    path = unquote(parsed.path or "")
    return frozenset(_tokens(f"{host} {path}"))


def _url_path_tokens(raw: object) -> frozenset[str]:
    canonical = canonicalize_url(str(raw or ""))
    if not canonical:
        return frozenset()
    return frozenset(_tokens(unquote(urlsplit(canonical).path or "")))


def identity_authority_bound(
    lead_or_url: Mapping[str, Any] | str,
    *,
    question: str,
) -> bool:
    """Return true only for an exact visible identity+authority URL binding."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.98 visible question is absent")
    raw = (
        str(lead_or_url.get("fetch_url") or lead_or_url.get("url") or "")
        if isinstance(lead_or_url, Mapping)
        else str(lead_or_url)
    )
    url_tokens = _url_tokens(raw)
    path_tokens = _url_path_tokens(raw)
    identities = _identity_vectors(question)
    authorities = _authority_tokens(question)
    identity_match = any(set(vector).issubset(path_tokens) for vector in identities)
    authority_match = any(token in url_tokens for token in authorities)
    return bool(identity_match and authority_match)


def _raw_batches(raw: object) -> list[Mapping[str, Any]]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [value for value in raw if isinstance(value, Mapping)]


def _action_sources(batch: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    trace = batch.get("hosted_search_trace")
    if not isinstance(trace, Mapping):
        return []
    output: list[Mapping[str, Any]] = []
    for action in trace.get("actions") or []:
        if not isinstance(action, Mapping):
            continue
        output.extend(
            source
            for source in (action.get("sources") or [])
            if isinstance(source, Mapping)
        )
    return output


def _lead(value: Mapping[str, Any]) -> dict[str, str] | None:
    projected = _source_lead(value)
    if projected is None:
        return None
    return {
        "title": str(projected.get("title") or "")[:500],
        "url": str(projected["url"]),
        "fetch_url": str(projected.get("fetch_url") or projected["url"]),
        "content": "",
        "raw_content": "",
        "score": None,
        "source_type": "identity_authority_action_selection_lead",
    }


def _unique(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in values:
        lead = _lead(value)
        if lead is None or lead["url"] in seen:
            continue
        output.append(lead)
        seen.add(lead["url"])
    return output


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "strategy_eligible": bool(value["strategy_eligible"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "query_local_prefix_and_order_preserved": True,
        "stable_order_preserved_within_action_partitions": True,
        "same_complete_url_set_before_cap": True,
        "same_matched_prefix_cost": True,
        "identity_match_uses_exact_path_tokens_not_host_tld_suffix": True,
        "authority_match_uses_exact_distinctive_host_or_path_tokens": True,
        "action_url_must_bind_both_identity_and_authority_to_promote": True,
        "query_text_title_provider_narrative_snippet_page_content_or_score_used_for_selection": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "additional_search_fetch_model_token_context_byte_wall_or_network_cap": False,
        "contains_question_identity_authority_query_url_host_title_page_prediction_answer_hash_opaque_id_or_credential": False,
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
        "query_local_prefix_and_order_preserved",
        "stable_order_preserved_within_action_partitions",
        "same_complete_url_set_before_cap",
        "same_matched_prefix_cost",
        "identity_match_uses_exact_path_tokens_not_host_tld_suffix",
        "authority_match_uses_exact_distinctive_host_or_path_tokens",
        "action_url_must_bind_both_identity_and_authority_to_promote",
    )
    false_flags = (
        "query_text_title_provider_narrative_snippet_page_content_or_score_used_for_selection",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_token_context_byte_wall_or_network_cap",
        "contains_question_identity_authority_query_url_host_title_page_prediction_answer_hash_opaque_id_or_credential",
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
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or copied["control_selected_url_count"]
        != copied["candidate_selected_url_count"]
        or copied["control_selected_url_count"] > copied["prefix_cap"]
        or copied["selected_query_local_url_count"]
        > copied["available_query_local_url_count"]
        or copied["available_unique_url_count"]
        != copied["available_query_local_url_count"]
        + copied["available_action_only_url_count"]
        or copied["unique_url_count_before_exclusion"]
        != copied["available_unique_url_count"] + copied["excluded_prior_url_count"]
        or copied["identity_authority_bound_action_url_count"]
        > copied["available_action_only_url_count"]
        or copied["control_bound_action_url_count"]
        > copied["identity_authority_bound_action_url_count"]
        or copied["candidate_bound_action_url_count"]
        > copied["identity_authority_bound_action_url_count"]
        or copied["candidate_bound_action_url_count"]
        < copied["control_bound_action_url_count"]
        or copied["bound_action_url_gain"]
        != copied["candidate_bound_action_url_count"]
        - copied["control_bound_action_url_count"]
        or copied["selection_changed"] not in {0, 1}
        or copied["selection_changed"]
        != int(copied["bound_action_url_gain"] > 0)
        or copied["mechanism_engaged"] is not bool(copied["selection_changed"])
        or copied["mechanism_engaged"] and not copied["strategy_eligible"]
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.98 identity/authority selection receipt drifted")
    return copied


def select_matched_prefixes(
    raw: object,
    *,
    question: str,
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    """Replay stable control and bound-action candidate from one response."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.98 visible question is absent")
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.49.98 prefix cap is invalid")
    if isinstance(exclude_urls, (str, bytes)):
        raise ValueError("V2.49.98 exclusion vector is invalid")
    excluded = {
        canonicalize_url(str(value))
        for value in exclude_urls
        if canonicalize_url(str(value))
    }
    batches = _raw_batches(raw)
    local_values = [
        result
        for batch in batches
        for result in (batch.get("results") or [])
        if isinstance(result, Mapping)
    ]
    action_values = [source for batch in batches for source in _action_sources(batch)]
    local = _unique(local_values)
    local_urls = {lead["url"] for lead in local}
    action = [lead for lead in _unique(action_values) if lead["url"] not in local_urls]
    stable_all = [*local, *action]
    unique_before = len(stable_all)
    available_local = [lead for lead in local if lead["url"] not in excluded]
    available_action = [lead for lead in action if lead["url"] not in excluded]
    bound = [
        lead
        for lead in available_action
        if identity_authority_bound(lead, question=question)
    ]
    bound_urls = {lead["url"] for lead in bound}
    unbound = [lead for lead in available_action if lead["url"] not in bound_urls]
    control_order = [*available_local, *available_action]
    candidate_order = [*available_local, *bound, *unbound]
    if (
        len(control_order) != len(candidate_order)
        or {lead["url"] for lead in control_order}
        != {lead["url"] for lead in candidate_order}
    ):
        raise RuntimeError("V2.49.98 candidate changed the complete URL set")
    control = [copy.deepcopy(value) for value in control_order[:cap]]
    candidate = [copy.deepcopy(value) for value in candidate_order[:cap]]
    control_urls = [lead["url"] for lead in control]
    candidate_urls = [lead["url"] for lead in candidate]
    control_bound_count = sum(url in bound_urls for url in control_urls)
    candidate_bound_count = sum(url in bound_urls for url in candidate_urls)
    # Reordering without strictly increasing the jointly bound prefix is not
    # a treatment.  Preserve exact identity handoff in that case.
    if candidate_bound_count <= control_bound_count:
        candidate = copy.deepcopy(control)
        candidate_urls = list(control_urls)
        candidate_bound_count = control_bound_count
    identities = _identity_vectors(question)
    authorities = _authorities(question)
    authority_tokens = _authority_tokens(question)
    strategy_eligible = bool(identities and authorities and authority_tokens and bound)
    receipt = _receipt(
        {
            "prefix_cap": cap,
            "tagged_identity_count": len(identities),
            "explicit_authority_phrase_count": len(authorities),
            "distinctive_authority_token_count": len(authority_tokens),
            "raw_query_local_source_count": len(local_values),
            "raw_action_source_count": len(action_values),
            "unique_url_count_before_exclusion": unique_before,
            "excluded_prior_url_count": unique_before - len(control_order),
            "available_unique_url_count": len(control_order),
            "available_query_local_url_count": len(available_local),
            "available_action_only_url_count": len(available_action),
            "identity_authority_bound_action_url_count": len(bound),
            "control_selected_url_count": len(control),
            "candidate_selected_url_count": len(candidate),
            "selected_query_local_url_count": min(len(available_local), cap),
            "control_bound_action_url_count": control_bound_count,
            "candidate_bound_action_url_count": candidate_bound_count,
            "bound_action_url_gain": candidate_bound_count - control_bound_count,
            "selection_changed": int(control_urls != candidate_urls),
            "strategy_eligible": strategy_eligible,
            "mechanism_engaged": bool(control_urls != candidate_urls),
        }
    )
    result = {
        "artifact_version": 1,
        "policy_id": POLICY_ID,
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
    raw: object,
    question: str,
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = select_matched_prefixes(
        raw, question=question, cap=cap, exclude_urls=exclude_urls
    )
    receipt = copied.get("content_free_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("V2.49.98 selection receipt is absent")
    validate_receipt(receipt)
    if copied != expected:
        raise ValueError("V2.49.98 selection replay drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "identity_authority_bound",
    "select_matched_prefixes",
    "validate_receipt",
    "validate_result",
]
