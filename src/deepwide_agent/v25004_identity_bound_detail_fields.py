"""Pure identity-bound detail-page field projection.

This append-only projector handles an official directory pattern that the
table/record ledger intentionally does not: an index page links to one detail
page, and the detail page exposes one visible record as exact ``Label: | Value``
lines, an exact field heading followed by one value line, or
``Exact label value.``.  It derives identity and schema only from the question,
requires exact URL-path and page-title/leading-text identity binding, and
requires every visible target field to occur exactly once on that same page.

No authority name, host, path template, package name, field label, or target
value is hard-coded.  Missing, duplicate, conflicting, unsafe, or unbound
fields return the inherited 5,000-character prefix byte-for-byte.  The module
has no file, environment, process, network, search, model, benchmark-label,
evaluator, score, reward, historical-result, or credential capability.
Entropy and information gain remain shadow-only and assign no signed credit.
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

from . import v24980_late_page_bound_projection as parent
from . import v24984_robust_late_page_projection as robust
from .clients import canonicalize_url
from .v24992_hybrid_authority_queries import _authorities, _identities


POLICY_ID = "v25004_identity_bound_detail_field_projection_v1"
ROLE = "v25004_identity_bound_detail_field_projection"
RECEIPT_ROLE = "v25004_content_free_identity_bound_detail_field_receipt"
PAGE_CHARACTER_CAP = parent.PAGE_CHARACTER_CAP
MAXIMUM_INPUT_PAGE_CHARACTERS = parent.MAXIMUM_INPUT_PAGE_CHARACTERS
MAXIMUM_FIELD_VALUE_CHARACTERS = 1_000
MAXIMUM_LEADING_IDENTITY_LINES = 8
_LINE = re.compile(r"^(?P<label>[^|\r\n]{1,240}?)\s*:\s*\|\s*(?P<value>.+?)\s*$")
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_GENERIC_AUTHORITY_TOKENS = frozenset(
    {
        "and", "database", "directory", "from", "index", "list", "official",
        "package", "page", "public", "record", "registry", "root", "search",
        "site", "source", "table", "the", "using", "web", "website", "zone",
    }
)
_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_identity_count",
    "visible_schema_column_count",
    "visible_target_field_count",
    "identity_url_path_match_count",
    "authority_url_token_match_count",
    "identity_page_surface_match_count",
    "raw_detail_candidate_line_count",
    "target_detail_candidate_count",
    "duplicate_or_conflicting_target_count",
    "discovered_record_count",
    "admissible_record_count",
    "admissible_bound_observation_count",
    "retained_record_count",
    "retained_bound_observation_count",
    "compact_prefix_characters",
    "raw_prefix_characters_retained",
    "output_characters",
    "projection_failure_count",
    "positive_signed_credit_count",
)


def _normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _canonical(value: object) -> str:
    return _normalize(value).casefold()


def _tokens(value: object) -> tuple[str, ...]:
    return tuple(_TOKEN.findall(_canonical(value)))


def _safe_surface(value: object, *, maximum: int) -> str | None:
    text = _normalize(value).strip(" |\t\r\n")
    if (
        not text
        or len(text) > maximum
        or "\x00" in text
        or any(ord(character) < 32 for character in text)
        or _canonical(text) in {"unknown", "n/a", "na", "none", "null", "-"}
    ):
        return None
    return text


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


def _page(raw: Mapping[str, Any]) -> tuple[dict[str, str], str]:
    normalized, text = parent._page(raw)
    title = _normalize(raw.get("title") or normalized.get("title") or "")[:500]
    return {"url": normalized["url"], "title": title, "content": text}, text


def _url_bindings(
    url: str, *, identity: str, authority_tokens: Sequence[str]
) -> tuple[bool, bool]:
    canonical = canonicalize_url(url)
    if not canonical:
        return False, False
    parsed = urlsplit(canonical)
    path_tokens = frozenset(_tokens(unquote(parsed.path or "")))
    url_tokens = frozenset(
        _tokens(f"{unquote(parsed.hostname or '')} {unquote(parsed.path or '')}")
    )
    identity_tokens = frozenset(_tokens(identity))
    identity_bound = bool(identity_tokens and identity_tokens.issubset(path_tokens))
    authority_bound = any(token in url_tokens for token in authority_tokens)
    return identity_bound, authority_bound


def _page_identity_bound(page: Mapping[str, str], identity: str) -> bool:
    identity_tokens = frozenset(_tokens(identity))
    if not identity_tokens:
        return False
    title_tokens = frozenset(_tokens(page.get("title") or ""))
    title_bound = bool(identity_tokens and identity_tokens.issubset(title_tokens))
    leading = "\n".join(
        str(page.get("content") or "").splitlines()[:MAXIMUM_LEADING_IDENTITY_LINES]
    )
    leading_bound = identity_tokens.issubset(frozenset(_tokens(leading)))
    return bool(title_bound or leading_bound)


def _schema(question: str) -> tuple[str, ...]:
    return tuple(str(value) for value in robust.extract_robust_visible_columns(question))


def _field_map(
    text: str, targets: Sequence[str]
) -> tuple[dict[str, str], int, int, int]:
    aliases = {_canonical(target): str(target) for target in targets}
    values: dict[str, list[str]] = {key: [] for key in aliases}
    lines = [_normalize(raw) for raw in text.splitlines()]
    raw_count = 0
    target_count = 0
    for index, line in enumerate(lines):
        if not line:
            continue
        match = _LINE.fullmatch(line)
        if match is not None:
            raw_count += 1
            key = _canonical(match.group("label"))
            if key in aliases:
                target_count += 1
                safe = _safe_surface(
                    match.group("value"), maximum=MAXIMUM_FIELD_VALUE_CHARACTERS
                )
                if safe is not None:
                    values[key].append(safe)
            continue
        key = _canonical(line)
        if key in aliases:
            raw_count += 1
            target_count += 1
            following = next((value for value in lines[index + 1 :] if value), "")
            safe = _safe_surface(following, maximum=MAXIMUM_FIELD_VALUE_CHARACTERS)
            if safe is not None and _canonical(safe) not in aliases:
                values[key].append(safe)
            continue
        for alias, display in aliases.items():
            label_pattern = re.escape(_normalize(display)).replace(r"\ ", r"\s+")
            sentence = re.fullmatch(
                rf"{label_pattern}\s+(?P<value>.+?)\.", line, re.IGNORECASE
            )
            if sentence is None:
                continue
            raw_count += 1
            target_count += 1
            safe = _safe_surface(
                sentence.group("value"), maximum=MAXIMUM_FIELD_VALUE_CHARACTERS
            )
            if safe is not None:
                values[alias].append(safe)
            break
    conflicts = sum(
        len(items) != 1 or len({_canonical(value) for value in items}) != 1
        for items in values.values()
    )
    output = {
        aliases[key]: items[0]
        for key, items in values.items()
        if len(items) == 1
    }
    return output, raw_count, target_count, conflicts


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "exact_parent_prefix_handoff": bool(value["exact_parent_prefix_handoff"]),
        "identity_comes_only_from_visible_tagged_question_span": True,
        "schema_comes_only_from_robust_visible_question_parser": True,
        "identity_bound_to_exact_url_path_tokens_and_page_surface": True,
        "authority_bound_to_exact_distinctive_url_token": True,
        "target_fields_exact_label_unique_and_same_page": True,
        "compact_record_atomic_and_unsplit": True,
        "same_forward_decoded_page_only": True,
        "parent_page_character_cap_and_count_preserved": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_url_title_page_record_value_prediction_answer_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = parent.payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    bool_fields = (
        "candidate_evidence_changed",
        "mechanism_engaged",
        "exact_parent_prefix_handoff",
    )
    true_flags = (
        "identity_comes_only_from_visible_tagged_question_span",
        "schema_comes_only_from_robust_visible_question_parser",
        "identity_bound_to_exact_url_path_tokens_and_page_surface",
        "authority_bound_to_exact_distinctive_url_token",
        "target_fields_exact_label_unique_and_same_page",
        "compact_record_atomic_and_unsplit",
        "same_forward_decoded_page_only",
        "parent_page_character_cap_and_count_preserved",
        "entropy_information_gain_shadow_only",
    )
    false_flags = (
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "contains_question_url_title_page_record_value_prediction_answer_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version", "role", "policy_id", *_COUNT_FIELDS, *bool_fields,
        *true_flags, *false_flags, "receipt_payload_sha256",
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
        or copied["input_page_count"] != 1
        or copied["input_characters_beyond_parent_prefix"]
        != max(0, copied["input_content_characters"] - PAGE_CHARACTER_CAP)
        or copied["visible_target_field_count"]
        != max(0, copied["visible_schema_column_count"] - 1)
        or copied["visible_identity_count"] > 8
        or copied["visible_schema_column_count"] > 64
        or copied["raw_detail_candidate_line_count"]
        < copied["target_detail_candidate_count"]
        or copied["identity_url_path_match_count"] not in {0, 1}
        or copied["authority_url_token_match_count"] not in {0, 1}
        or copied["identity_page_surface_match_count"] not in {0, 1}
        or copied["discovered_record_count"] not in {0, 1}
        or copied["admissible_record_count"] not in {0, 1}
        or copied["retained_record_count"] not in {0, 1}
        or copied["admissible_record_count"]
        > copied["discovered_record_count"]
        or copied["retained_record_count"] > copied["admissible_record_count"]
        or copied["admissible_bound_observation_count"]
        > copied["visible_target_field_count"]
        or copied["retained_bound_observation_count"]
        > copied["admissible_bound_observation_count"]
        or copied["output_characters"]
        != min(copied["input_content_characters"], PAGE_CHARACTER_CAP)
        or copied["positive_signed_credit_count"] != 0
        or copied["projection_failure_count"] not in {0, 1}
        or copied["discovered_record_count"]
        is not int(
            copied["visible_identity_count"] == 1
            and copied["visible_target_field_count"] > 0
            and copied["identity_url_path_match_count"] == 1
            and copied["authority_url_token_match_count"] == 1
            and copied["identity_page_surface_match_count"] == 1
            and copied["duplicate_or_conflicting_target_count"] == 0
            and copied["admissible_bound_observation_count"]
            == copied["visible_target_field_count"]
            and copied["projection_failure_count"] == 0
        )
        or copied["admissible_record_count"]
        != copied["discovered_record_count"]
        or copied["admissible_bound_observation_count"]
        != (
            copied["visible_target_field_count"]
            if copied["admissible_record_count"] == 1
            else 0
        )
        or copied["retained_bound_observation_count"]
        != (
            copied["visible_target_field_count"]
            if copied["retained_record_count"] == 1
            else 0
        )
        or copied["candidate_evidence_changed"]
        is not (copied["retained_record_count"] == 1)
        or copied["mechanism_engaged"]
        is not (
            copied["retained_record_count"] == 1
            and copied["retained_bound_observation_count"]
            == copied["visible_target_field_count"]
            and copied["candidate_evidence_changed"] is True
            and copied["projection_failure_count"] == 0
        )
        or copied["exact_parent_prefix_handoff"]
        is not (copied["candidate_evidence_changed"] is False)
        or copied["exact_parent_prefix_handoff"]
        and (
            copied["compact_prefix_characters"] != 0
            or copied["retained_record_count"] != 0
            or copied["retained_bound_observation_count"] != 0
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.04 detail-field receipt drifted")
    return copied


def build_projection(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.04 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.50.04 parent page cap drifted")
    normalized_page, raw_text = _page(page)
    raw_prefix = raw_text[:PAGE_CHARACTER_CAP]
    identities = _identities(question)
    schema = _schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    authorities = _authority_tokens(question)
    path_bound = False
    authority_bound = False
    surface_bound = False
    fields: dict[str, str] = {}
    raw_key_values = 0
    target_key_values = 0
    conflicts = 0
    failure = 0
    try:
        if len(identities) == 1 and len(schema) >= 2 and authorities:
            path_bound, authority_bound = _url_bindings(
                normalized_page["url"],
                identity=identities[0],
                authority_tokens=authorities,
            )
            surface_bound = _page_identity_bound(normalized_page, identities[0])
            fields, raw_key_values, target_key_values, conflicts = _field_map(
                raw_text, targets
            )
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        path_bound = authority_bound = surface_bound = False
        fields = {}
        raw_key_values = target_key_values = conflicts = 0
    complete = bool(
        len(identities) == 1
        and len(schema) >= 2
        and path_bound
        and authority_bound
        and surface_bound
        and conflicts == 0
        and set(fields) == set(targets)
        and failure == 0
    )
    projection = raw_prefix
    compact_chars = 0
    raw_retained = len(raw_prefix)
    if complete:
        compact = "\n".join(
            (
                "[IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]",
                "untrusted_public_page_record=true",
                "source_url=" + normalized_page["url"],
                "row_key_label=" + json.dumps(schema[0], ensure_ascii=False),
                "target_columns=" + json.dumps(
                    list(targets), ensure_ascii=False, separators=(",", ":")
                ),
                json.dumps(
                    {
                        "record_id": hashlib.sha256(
                            (
                                normalized_page["url"]
                                + "\x1f"
                                + _canonical(identities[0])
                            ).encode()
                        ).hexdigest()[:24],
                        "row": identities[0],
                        "cells": [[target, fields[target]] for target in targets],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "[/IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]",
            )
        )
        marker = "\n[INHERITED RAW PAGE PREFIX]\n"
        raw_budget = len(raw_prefix) - len(compact) - len(marker)
        if raw_budget >= parent.MINIMUM_RAW_PREFIX_CHARACTERS:
            projection = compact + marker + raw_text[:raw_budget]
            compact_chars = len(compact)
            raw_retained = min(len(raw_text), raw_budget)
    changed = projection != raw_prefix
    retained = int(changed and complete)
    retained_observations = len(targets) if retained else 0
    detail_receipt = _receipt(
        {
            "input_page_count": 1,
            "input_content_characters": len(raw_text),
            "input_characters_beyond_parent_prefix": max(
                0, len(raw_text) - PAGE_CHARACTER_CAP
            ),
            "visible_identity_count": len(identities),
            "visible_schema_column_count": len(schema),
            "visible_target_field_count": len(targets),
            "identity_url_path_match_count": int(path_bound),
            "authority_url_token_match_count": int(authority_bound),
            "identity_page_surface_match_count": int(surface_bound),
            "raw_detail_candidate_line_count": raw_key_values,
            "target_detail_candidate_count": target_key_values,
            "duplicate_or_conflicting_target_count": conflicts,
            "discovered_record_count": int(complete),
            "admissible_record_count": int(complete),
            "admissible_bound_observation_count": len(targets) if complete else 0,
            "retained_record_count": retained,
            "retained_bound_observation_count": retained_observations,
            "compact_prefix_characters": compact_chars if retained else 0,
            "raw_prefix_characters_retained": raw_retained if retained else len(raw_prefix),
            "output_characters": len(projection),
            "projection_failure_count": failure,
            "positive_signed_credit_count": 0,
            "candidate_evidence_changed": changed,
            "mechanism_engaged": bool(retained),
            "exact_parent_prefix_handoff": not changed,
        }
    )
    parent_receipt = parent._receipt(
        {
            "input_page_count": 1,
            "input_content_characters": len(raw_text),
            "input_characters_beyond_parent_prefix": max(
                0, len(raw_text) - PAGE_CHARACTER_CAP
            ),
            "visible_schema_column_count": len(schema),
            "discovered_record_count": int(complete),
            "discovered_row_key_count": int(complete),
            "conflicting_coordinate_count": conflicts,
            "admissible_record_count": int(complete),
            "admissible_bound_observation_count": len(targets) if complete else 0,
            "retained_record_count": retained,
            "retained_bound_observation_count": retained_observations,
            "oversized_record_count": 0,
            "compact_prefix_characters": compact_chars if retained else 0,
            "raw_prefix_characters_retained": raw_retained if retained else len(raw_prefix),
            "output_characters": len(projection),
            "projection_failure_count": failure,
            "positive_signed_credit_count": 0,
            "candidate_evidence_changed": changed,
            "mechanism_engaged": bool(retained),
            "exact_parent_prefix_handoff": not changed,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode()).hexdigest(),
        # Byte/schema compatible with the frozen V2.49.81 helper boundary.
        "content_free_receipt": parent_receipt,
        "detail_field_receipt": detail_receipt,
        "same_forward_decoded_page_only": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["artifact_payload_sha256"] = parent.payload_sha256(value)
    return validate_projection(
        value,
        question=question,
        page=page,
        page_character_cap=page_character_cap,
        replay=False,
    )


def validate_projection(
    value: Mapping[str, Any],
    *,
    question: str,
    page: Mapping[str, Any],
    page_character_cap: int = PAGE_CHARACTER_CAP,
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    projection = copied.get("projection")
    receipt = copied.get("content_free_receipt")
    detail_receipt = copied.get("detail_field_receipt")
    if (
        set(copied)
        != {
            "artifact_version", "role", "policy_id", "projection",
            "projection_sha256", "content_free_receipt", "detail_field_receipt",
            "same_forward_decoded_page_only",
            "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
            "entropy_or_information_gain_assigns_signed_credit",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "file_environment_network_model_search_fetch_or_process_accessed",
            "artifact_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(projection, str)
        or len(projection) > page_character_cap
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode()).hexdigest()
        or not isinstance(receipt, Mapping)
        or parent.validate_receipt(receipt) != dict(receipt)
        or receipt["output_characters"] != len(projection)
        or not isinstance(detail_receipt, Mapping)
        or validate_receipt(detail_receipt) != dict(detail_receipt)
        or detail_receipt["output_characters"] != len(projection)
        or detail_receipt["input_content_characters"]
        != receipt["input_content_characters"]
        or detail_receipt["visible_schema_column_count"]
        != receipt["visible_schema_column_count"]
        or detail_receipt["discovered_record_count"]
        != receipt["discovered_record_count"]
        or detail_receipt["admissible_record_count"]
        != receipt["admissible_record_count"]
        or detail_receipt["admissible_bound_observation_count"]
        != receipt["admissible_bound_observation_count"]
        or detail_receipt["retained_record_count"]
        != receipt["retained_record_count"]
        or detail_receipt["retained_bound_observation_count"]
        != receipt["retained_bound_observation_count"]
        or detail_receipt["compact_prefix_characters"]
        != receipt["compact_prefix_characters"]
        or detail_receipt["raw_prefix_characters_retained"]
        != receipt["raw_prefix_characters_retained"]
        or detail_receipt["projection_failure_count"]
        != receipt["projection_failure_count"]
        or detail_receipt["candidate_evidence_changed"]
        != receipt["candidate_evidence_changed"]
        or detail_receipt["mechanism_engaged"] != receipt["mechanism_engaged"]
        or detail_receipt["exact_parent_prefix_handoff"]
        != receipt["exact_parent_prefix_handoff"]
        or copied.get("same_forward_decoded_page_only") is not True
        or copied.get("additional_search_fetch_model_token_context_wall_or_network_byte_cap")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read")
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.04 detail-field projection drifted")
    if replay and copied != build_projection(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError("V2.50.04 detail-field projection is not reproducible")
    return copied


__all__ = [
    "MAXIMUM_INPUT_PAGE_CHARACTERS",
    "PAGE_CHARACTER_CAP",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_projection",
    "validate_projection",
    "validate_receipt",
]
