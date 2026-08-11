"""Visible-authority resolution for strict identity-bound partial records.

V2.50.88 exposed four tasks but discarded nine other tasks because more than
one fetched page independently passed the strict identity URL and page-surface
checks.  This pure successor keeps every strict check.  When, and only when,
there are multiple strict identity pages, it selects one page if the visible
question names exactly one preregistered public authority and exactly one of
those pages has that authority's exact host.  Otherwise it fails closed.

The selected page is still the only page shown to the field proposer.  This
module performs no I/O and has no benchmark-label, mapping, gold, evaluator,
score, reward, credential, history, entropy-credit, or launch capability.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from . import v25065_quote_verified_record_binding as quote_parent
from . import v25080_visible_identity_page_record as identity_parent
from . import v25085_identity_bound_partial_field_record as field_parent
from .clients import canonicalize_url
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25090_visible_authority_resolved_partial_field_record_v1"
ROLE = "v25090_visible_authority_resolved_partial_field_record_representation"
RECEIPT_ROLE = "v25090_content_free_visible_authority_partial_field_receipt"
SELECTION_RECEIPT_ROLE = "v25090_content_free_visible_authority_page_selection_receipt"

MAXIMUM_PAGE_COUNT = field_parent.MAXIMUM_PAGE_COUNT
MAXIMUM_PAGE_CHARACTERS = field_parent.MAXIMUM_PAGE_CHARACTERS
MAXIMUM_PROPOSAL_INPUT_CHARACTERS = field_parent.MAXIMUM_PROPOSAL_INPUT_CHARACTERS
PROPOSAL_OUTPUT_TOKEN_CAP = field_parent.PROPOSAL_OUTPUT_TOKEN_CAP
MAXIMUM_PROPOSED_RECORDS = field_parent.MAXIMUM_PROPOSED_RECORDS
MAXIMUM_FIELDS_PER_RECORD = field_parent.MAXIMUM_FIELDS_PER_RECORD
MAXIMUM_TOTAL_FIELDS = field_parent.MAXIMUM_TOTAL_FIELDS
MAXIMUM_FIELD_QUOTE_CHARACTERS = field_parent.MAXIMUM_FIELD_QUOTE_CHARACTERS
MAXIMUM_RECORD_PREFIX_CHARACTERS = field_parent.MAXIMUM_RECORD_PREFIX_CHARACTERS
MAXIMUM_CONTROL_EVIDENCE_CHARACTERS = field_parent.MAXIMUM_CONTROL_EVIDENCE_CHARACTERS
SYSTEM_PROMPT = field_parent.SYSTEM_PROMPT

_AUTHORITY_PATTERNS = (
    ("pypi", re.compile(r"\bPyPI\b|Python\s+Package\s+Index", re.IGNORECASE)),
    ("github", re.compile(r"\bGitHub\b|github\.com", re.IGNORECASE)),
    (
        "cran",
        re.compile(r"\bCRAN\b|Comprehensive\s+R\s+Archive\s+Network", re.IGNORECASE),
    ),
)
_AUTHORITY_HOSTS = {
    "pypi": frozenset({"pypi.org"}),
    "github": frozenset({"github.com", "api.github.com"}),
    "cran": frozenset({"cran.r-project.org"}),
}


def _visible_authorities(question: str) -> tuple[str, ...]:
    visible = str(question or "")
    return tuple(name for name, pattern in _AUTHORITY_PATTERNS if pattern.search(visible))


def _authority_host_match(url: object, authority: str) -> bool:
    canonical = canonicalize_url(str(url or ""))
    if not canonical or authority not in _AUTHORITY_HOSTS:
        return False
    try:
        host = (urlsplit(canonical).hostname or "").casefold().rstrip(".")
    except ValueError:
        return False
    return host in _AUTHORITY_HOSTS[authority]


def _strict_pages(
    pages: Sequence[Mapping[str, Any]], identity: str
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("V2.50.90 page vector is invalid")
    eligible: list[dict[str, Any]] = []
    seen: set[str] = set()
    input_count = 0
    url_matches = 0
    surface_matches = 0
    for ordinal, raw in enumerate(pages, 1):
        input_count += 1
        if not isinstance(raw, Mapping):
            continue
        url = canonicalize_url(str(raw.get("url") or ""))
        content = quote_parent._text(raw.get("content") or raw.get("raw_content") or "")
        title = quote_parent._text(raw.get("title") or "")[:300]
        if not url or not content or url in seen:
            continue
        seen.add(url)
        url_match = identity_parent._url_identity_match(url, identity)
        surface_match = identity_parent._page_surface_match(title, content, identity)
        url_matches += int(url_match)
        surface_matches += int(surface_match)
        if not (url_match and surface_match):
            continue
        chosen = content[:MAXIMUM_PAGE_CHARACTERS]
        if chosen:
            eligible.append(
                {
                    "page_ordinal": ordinal,
                    "title": title,
                    "url": url,
                    "content": chosen,
                }
            )
    return eligible, {
        "input_page_count": input_count,
        "identity_url_match_page_count": url_matches,
        "identity_surface_match_page_count": surface_matches,
        "joint_identity_bound_page_count": len(eligible),
    }


def _select_page(
    eligible: Sequence[Mapping[str, Any]], question: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    authorities = _visible_authorities(question)
    authority_matches: list[Mapping[str, Any]] = []
    if len(authorities) == 1:
        authority_matches = [
            page
            for page in eligible
            if _authority_host_match(page.get("url"), authorities[0])
        ]
    unique_identity_selected = len(eligible) == 1
    tiebreak_eligible = len(eligible) > 1 and len(authorities) == 1
    tiebreak_selected = tiebreak_eligible and len(authority_matches) == 1
    selected_raw: Sequence[Mapping[str, Any]]
    if unique_identity_selected:
        selected_raw = eligible
    elif tiebreak_selected:
        selected_raw = authority_matches
    else:
        selected_raw = ()
    selected = [copy.deepcopy(dict(page)) for page in selected_raw]
    return selected, {
        "strict_identity_page_count": len(eligible),
        "visible_authority_count": len(authorities),
        "authority_matching_strict_page_count": len(authority_matches),
        "selected_page_count": len(selected),
        "unique_identity_page_selected": unique_identity_selected,
        "authority_tiebreak_eligible": tiebreak_eligible,
        "authority_tiebreak_selected": tiebreak_selected,
    }


def prepare_record_proposal(
    question: str,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    visible = quote_parent._text(question)
    identity = identity_parent.visible_identity(question)
    if not visible or len(visible) > 100_000 or "\x00" in visible:
        raise ValueError("V2.50.90 visible question contract drifted")
    required = quote_parent._safe_columns(columns)
    eligible: list[dict[str, Any]] = []
    counts = {
        "input_page_count": len(pages) if isinstance(pages, Sequence) else 0,
        "identity_url_match_page_count": 0,
        "identity_surface_match_page_count": 0,
        "joint_identity_bound_page_count": 0,
    }
    if identity is not None:
        eligible, counts = _strict_pages(pages, identity)
    selected, selection = _select_page(eligible, visible)
    rendered = []
    for page in selected:
        ordinal = int(page["page_ordinal"])
        rendered.append(
            f"[UNTRUSTED IDENTITY_BOUND PAGE {ordinal}]\n"
            f"title={page['title']}\ncontent={page['content']}\n"
            f"[/UNTRUSTED IDENTITY_BOUND PAGE {ordinal}]"
        )
    user = (
        "VISIBLE QUESTION:\n"
        + visible
        + "\n\nREQUESTED COLUMNS IN EXACT ORDER:\n"
        + json.dumps(list(required), ensure_ascii=False)
        + "\n\nIDENTITY-BOUND SAME-FORWARD PAGES:\n"
        + ("\n\n".join(rendered) if rendered else "No uniquely resolved identity-bound page was available.")
    )
    return {
        "artifact_version": 1,
        "role": "v25090_private_visible_authority_partial_field_state",
        "system": SYSTEM_PROMPT,
        "user": user,
        "question": visible,
        "columns": required,
        "identity": identity,
        "pages": tuple(copy.deepcopy(selected)),
        **counts,
        "bounded_page_count": len(selected),
        "bounded_page_characters": sum(len(str(page["content"])) for page in selected),
        **selection,
    }


def _selection_receipt(prepared: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": SELECTION_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{
            name: int(prepared[name])
            for name in (
                "strict_identity_page_count",
                "visible_authority_count",
                "authority_matching_strict_page_count",
                "selected_page_count",
            )
        },
        **{
            name: bool(prepared[name])
            for name in (
                "unique_identity_page_selected",
                "authority_tiebreak_eligible",
                "authority_tiebreak_selected",
            )
        },
        "authority_resolution_runs_only_after_strict_identity_url_and_surface_binding": True,
        "authority_is_read_only_from_visible_question": True,
        "authority_match_requires_exact_preregistered_host": True,
        "multiple_pages_require_exactly_one_authority_and_one_matching_page": True,
        "page_content_title_query_provider_score_or_rank_used_for_authority_selection": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_selection_receipt(output)


def validate_selection_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integers = (
        "strict_identity_page_count",
        "visible_authority_count",
        "authority_matching_strict_page_count",
        "selected_page_count",
    )
    bools = (
        "unique_identity_page_selected",
        "authority_tiebreak_eligible",
        "authority_tiebreak_selected",
    )
    true_flags = (
        "authority_resolution_runs_only_after_strict_identity_url_and_surface_binding",
        "authority_is_read_only_from_visible_question",
        "authority_match_requires_exact_preregistered_host",
        "multiple_pages_require_exactly_one_authority_and_one_matching_page",
    )
    false_flags = (
        "page_content_title_query_provider_score_or_rank_used_for_authority_selection",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *integers,
        *bools,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    strict = copied.get("strict_identity_page_count")
    authorities = copied.get("visible_authority_count")
    matches = copied.get("authority_matching_strict_page_count")
    selected = copied.get("selected_page_count")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != SELECTION_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integers
        )
        or any(not isinstance(copied.get(name), bool) for name in bools)
        or authorities > len(_AUTHORITY_PATTERNS)
        or matches > strict
        or selected not in {0, 1}
        or copied["unique_identity_page_selected"] is not (strict == 1 and selected == 1)
        or copied["authority_tiebreak_eligible"] is not (strict > 1 and authorities == 1)
        or copied["authority_tiebreak_selected"]
        is not (strict > 1 and authorities == 1 and matches == 1 and selected == 1)
        or strict == 1
        and selected != 1
        or strict != 1
        and not copied["authority_tiebreak_selected"]
        and selected != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.90 authority selection receipt drifted")
    return copied


def _parent_prepared(prepared: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(prepared))
    copied["role"] = "v25085_private_identity_bound_partial_field_state"
    copied["joint_identity_bound_page_count"] = int(copied["bounded_page_count"])
    for name in (
        "strict_identity_page_count",
        "visible_authority_count",
        "authority_matching_strict_page_count",
        "selected_page_count",
        "unique_identity_page_selected",
        "authority_tiebreak_eligible",
        "authority_tiebreak_selected",
    ):
        copied.pop(name, None)
    return copied


def build_representation(
    prepared: Mapping[str, Any],
    model_output: object,
    *,
    control_evidence: str,
    model_call_attempted: bool,
) -> dict[str, Any]:
    if (
        prepared.get("artifact_version") != 1
        or prepared.get("role") != "v25090_private_visible_authority_partial_field_state"
    ):
        raise ValueError("V2.50.90 prepared state drifted")
    parent_result = field_parent.build_representation(
        _parent_prepared(prepared),
        model_output,
        control_evidence=control_evidence,
        model_call_attempted=model_call_attempted,
    )
    parent_receipt = field_parent.validate_receipt(parent_result["content_free_receipt"])
    selection = _selection_receipt(prepared)
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "model_call_attempted": parent_receipt["model_call_attempted"],
        "model_output_strictly_valid": parent_receipt["model_output_strictly_valid"],
        "candidate_evidence_changed": parent_receipt["candidate_evidence_changed"],
        "authority_selection_receipt": selection,
        "partial_field_receipt": parent_receipt,
        "only_treatment_is_visible_authority_resolution_among_strict_identity_pages": True,
        "partial_field_disposition_and_conflict_policy_unchanged": True,
        "query_fetch_model_context_token_wall_or_network_byte_caps_unchanged": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "candidate_evidence": str(parent_result["candidate_evidence"]),
        "content_free_receipt": validate_receipt(receipt),
    }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    selection = copied.get("authority_selection_receipt")
    partial = copied.get("partial_field_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "model_call_attempted",
        "model_output_strictly_valid",
        "candidate_evidence_changed",
        "authority_selection_receipt",
        "partial_field_receipt",
        "only_treatment_is_visible_authority_resolution_among_strict_identity_pages",
        "partial_field_disposition_and_conflict_policy_unchanged",
        "query_fetch_model_context_token_wall_or_network_byte_caps_unchanged",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(selection, Mapping)
        or validate_selection_receipt(selection) != dict(selection)
        or not isinstance(partial, Mapping)
        or field_parent.validate_receipt(partial) != dict(partial)
        or any(
            copied.get(name) is not partial[name]
            for name in (
                "model_call_attempted",
                "model_output_strictly_valid",
                "candidate_evidence_changed",
            )
        )
        or partial["joint_identity_bound_page_count"] != selection["selected_page_count"]
        or selection["selected_page_count"] != partial["bounded_page_count"]
        or copied.get("only_treatment_is_visible_authority_resolution_among_strict_identity_pages")
        is not True
        or copied.get("partial_field_disposition_and_conflict_policy_unchanged") is not True
        or copied.get("query_fetch_model_context_token_wall_or_network_byte_caps_unchanged")
        is not True
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.90 authority partial-field receipt drifted")
    return copied


__all__ = [
    "MAXIMUM_CONTROL_EVIDENCE_CHARACTERS",
    "MAXIMUM_PAGE_CHARACTERS",
    "MAXIMUM_PROPOSAL_INPUT_CHARACTERS",
    "POLICY_ID",
    "PROPOSAL_OUTPUT_TOKEN_CAP",
    "RECEIPT_ROLE",
    "ROLE",
    "SYSTEM_PROMPT",
    "build_representation",
    "prepare_record_proposal",
    "validate_receipt",
    "validate_selection_receipt",
]
