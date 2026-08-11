"""Pure page-self-identified record representation for open-world rows.

The visible question supplies only an output schema.  A row identity may be
discovered from one already-fetched page only when the same identity is bound
to an exact URL path segment, an exact row-label occurrence in the page title,
and either the leading page surface or an exact row-label field.  Every target
field must occur exactly once under an exact visible label on that same page.

The result prepends one source/identity/target-coherent compact record to the
same fixed-size raw prefix.  Missing, ambiguous, conflicting, oversized, or
weakly bound observations return the parent prefix byte-for-byte.  This module
has no file, environment, process, network, search, model, benchmark label,
evaluator, score, reward, history, or credential capability.  Entropy and
information gain remain shadow-only and assign no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

from . import v24980_late_page_bound_projection as parent
from . import v25004_identity_bound_detail_fields as detail


POLICY_ID = "v25049_page_self_identified_record_representation_v1"
ROLE = "v25049_page_self_identified_record_representation"
RECEIPT_ROLE = "v25049_content_free_page_self_identified_record_receipt"
PAGE_CHARACTER_CAP = parent.PAGE_CHARACTER_CAP
MAXIMUM_INPUT_PAGE_CHARACTERS = parent.MAXIMUM_INPUT_PAGE_CHARACTERS
MAXIMUM_IDENTITY_CHARACTERS = 256
MAXIMUM_LEADING_LINES = 12
_IDENTITY_SEPARATOR = re.compile(r"[\s._+\-/]+", re.UNICODE)
_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_schema_column_count",
    "visible_target_field_count",
    "title_identity_candidate_count",
    "leading_identity_candidate_count",
    "row_label_identity_candidate_count",
    "url_path_identity_candidate_count",
    "jointly_bound_identity_count",
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


def _identity_key(value: object) -> str:
    text = _IDENTITY_SEPARATOR.sub(" ", _canonical(value)).strip(" ,:;|()[]{}")
    return " ".join(text.split())


def _safe_identity(value: object) -> str | None:
    text = _normalize(value).strip(" \t\r\n|:;,-–—")
    key = _identity_key(text)
    if (
        not text
        or not key
        or len(text) > MAXIMUM_IDENTITY_CHARACTERS
        or "\x00" in text
        or any(ord(character) < 32 for character in text)
        or key in {"unknown", "n a", "na", "none", "null"}
        or re.fullmatch(r"[-.:;,/]+", text) is not None
    ):
        return None
    return text


def _labelled_identity(value: object, row_label: str) -> str | None:
    """Extract an exact row-label suffix without guessing title templates."""

    text = _normalize(value)
    label = _normalize(row_label)
    if not text or not label:
        return None
    pattern = re.compile(
        rf"(?<!\w){re.escape(label)}(?!\w)"
        rf"(?:\s*[:#=|–—-]\s*|\s+)(?P<identity>.+?)\s*$",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        return None
    identity = _safe_identity(matches[0].group("identity"))
    if identity is None or any(mark in identity for mark in (" | ", " — ", " – ")):
        return None
    return identity


def _surface_candidates(
    title: str, text: str, row_label: str
) -> tuple[dict[str, str], dict[str, str]]:
    title_values: dict[str, str] = {}
    title_identity = _labelled_identity(title, row_label)
    if title_identity is not None:
        title_values[_identity_key(title_identity)] = title_identity
    leading_values: dict[str, str] = {}
    lines = [line for line in str(text).splitlines() if _normalize(line)]
    for line in lines[:MAXIMUM_LEADING_LINES]:
        identity = _labelled_identity(line, row_label)
        if identity is None:
            continue
        key = _identity_key(identity)
        previous = leading_values.get(key)
        if previous is None:
            leading_values[key] = identity
    return title_values, leading_values


def _row_label_candidates(text: str, row_label: str) -> dict[str, str]:
    fields, _raw, _target, conflicts = detail._field_map(text, [row_label])
    if conflicts != 0 or set(fields) != {row_label}:
        return {}
    identity = _safe_identity(fields[row_label])
    return {_identity_key(identity): identity} if identity is not None else {}


def _url_identity_keys(url: str) -> set[str]:
    parsed = urlsplit(str(url))
    values: list[str] = [unquote(part) for part in parsed.path.split("/") if part]
    values.extend(unquote(value) for _key, value in parse_qsl(parsed.query))
    output: set[str] = set()
    for raw in values:
        safe = _safe_identity(raw)
        if safe is not None:
            output.add(_identity_key(safe))
        # A final public-document extension is transport syntax, not identity.
        stem = re.sub(r"\.(?:html?|json|xml|txt)$", "", raw, flags=re.IGNORECASE)
        if stem != raw:
            safe_stem = _safe_identity(stem)
            if safe_stem is not None:
                output.add(_identity_key(safe_stem))
    return output


def _bound_identity(
    *, title: str, text: str, url: str, row_label: str
) -> tuple[str | None, dict[str, int]]:
    titles, leading = _surface_candidates(title, text, row_label)
    row_fields = _row_label_candidates(text, row_label)
    path_keys = _url_identity_keys(url)
    all_keys = set(titles) | set(leading) | set(row_fields)
    joint = [
        key
        for key in sorted(all_keys)
        if key in path_keys
        and key in titles
        and (key in leading or key in row_fields)
    ]
    identity = None
    if len(joint) == 1:
        key = joint[0]
        identity = titles.get(key) or leading.get(key) or row_fields.get(key)
    return identity, {
        "title_identity_candidate_count": len(titles),
        "leading_identity_candidate_count": len(leading),
        "row_label_identity_candidate_count": len(row_fields),
        "url_path_identity_candidate_count": len(path_keys),
        "jointly_bound_identity_count": len(joint),
    }


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "exact_parent_prefix_handoff": bool(value["exact_parent_prefix_handoff"]),
        "identity_discovered_from_page_not_question_enumeration": True,
        "identity_bound_to_url_title_and_leading_or_row_label_surface": True,
        "source_url_record_identity_target_and_value_atomically_bound": True,
        "target_fields_exact_label_unique_and_same_page": True,
        "compact_record_atomic_and_unsplit": True,
        "same_forward_decoded_page_only": True,
        "parent_page_character_cap_preserved": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
        "contains_question_identity_url_title_page_record_value_prediction_answer_hash_or_credential": False,
        "file_environment_process_network_search_model_or_evaluator_accessed": False,
        "benchmark_or_evaluator_launch_authorized": False,
    }
    output["receipt_payload_sha256"] = parent.payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    bool_fields = (
        "candidate_evidence_changed", "mechanism_engaged",
        "exact_parent_prefix_handoff",
    )
    true_flags = (
        "identity_discovered_from_page_not_question_enumeration",
        "identity_bound_to_url_title_and_leading_or_row_label_surface",
        "source_url_record_identity_target_and_value_atomically_bound",
        "target_fields_exact_label_unique_and_same_page",
        "compact_record_atomic_and_unsplit",
        "same_forward_decoded_page_only",
        "parent_page_character_cap_preserved",
    )
    false_flags = (
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read",
        "contains_question_identity_url_title_page_record_value_prediction_answer_hash_or_credential",
        "file_environment_process_network_search_model_or_evaluator_accessed",
        "benchmark_or_evaluator_launch_authorized",
    )
    expected = {
        "artifact_version", "role", "policy_id", *_COUNT_FIELDS,
        *bool_fields, *true_flags, *false_flags, "receipt_payload_sha256",
    }
    counts_valid = all(
        not isinstance(copied.get(name), bool)
        and isinstance(copied.get(name), int)
        and copied[name] >= 0
        for name in _COUNT_FIELDS
    )
    retained = copied.get("retained_record_count") == 1
    coherent = bool(
        counts_valid
        and copied.get("visible_schema_column_count", 0) >= 2
        and copied.get("visible_target_field_count")
        == copied.get("visible_schema_column_count") - 1
        and copied.get("jointly_bound_identity_count") == 1
        and copied.get("duplicate_or_conflicting_target_count") == 0
        and copied.get("discovered_record_count") == 1
        and copied.get("admissible_record_count") == 1
        and copied.get("admissible_bound_observation_count")
        == copied.get("visible_target_field_count")
        and copied.get("retained_bound_observation_count")
        == copied.get("visible_target_field_count")
        and copied.get("compact_prefix_characters", 0) > 0
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not counts_valid
        or copied["input_page_count"] != 1
        or copied["visible_target_field_count"]
        != max(0, copied["visible_schema_column_count"] - 1)
        or copied["jointly_bound_identity_count"] > 1
        or copied["retained_record_count"] > copied["admissible_record_count"]
        or copied["retained_bound_observation_count"]
        > copied["admissible_bound_observation_count"]
        or copied["output_characters"] > PAGE_CHARACTER_CAP
        or copied["positive_signed_credit_count"] != 0
        or retained is not coherent
        or copied.get("candidate_evidence_changed") is not retained
        or copied.get("mechanism_engaged") is not retained
        or copied.get("exact_parent_prefix_handoff") is retained
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.49 page-self record receipt drifted")
    return copied


def build_representation(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.49 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.50.49 parent page cap drifted")
    normalized_page, raw_text = detail._page(page)
    raw_prefix = raw_text[:PAGE_CHARACTER_CAP]
    schema = detail._schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    identity = None
    identity_counts = {
        "title_identity_candidate_count": 0,
        "leading_identity_candidate_count": 0,
        "row_label_identity_candidate_count": 0,
        "url_path_identity_candidate_count": 0,
        "jointly_bound_identity_count": 0,
    }
    fields: dict[str, str] = {}
    raw_candidates = target_candidates = conflicts = failure = 0
    try:
        if len(schema) >= 2:
            identity, identity_counts = _bound_identity(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
                row_label=schema[0],
            )
            fields, raw_candidates, target_candidates, conflicts = detail._field_map(
                raw_text, targets
            )
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        identity = None
        fields = {}
        raw_candidates = target_candidates = conflicts = 0
        identity_counts = {name: 0 for name in identity_counts}
    complete = bool(
        identity is not None
        and len(schema) >= 2
        and identity_counts["jointly_bound_identity_count"] == 1
        and conflicts == 0
        and set(fields) == set(targets)
        and failure == 0
    )
    representation = raw_prefix
    compact_chars = 0
    raw_retained = len(raw_prefix)
    if complete:
        compact = "\n".join(
            (
                "[PAGE-SELF-IDENTIFIED SOURCE-BOUND RECORD]",
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
                                + _identity_key(identity)
                            ).encode("utf-8")
                        ).hexdigest()[:24],
                        "row": identity,
                        "cells": [[target, fields[target]] for target in targets],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "[/PAGE-SELF-IDENTIFIED SOURCE-BOUND RECORD]",
            )
        )
        marker = "\n[INHERITED RAW PAGE PREFIX]\n"
        raw_budget = len(raw_prefix) - len(compact) - len(marker)
        if raw_budget >= parent.MINIMUM_RAW_PREFIX_CHARACTERS:
            representation = compact + marker + raw_text[:raw_budget]
            compact_chars = len(compact)
            raw_retained = min(len(raw_text), raw_budget)
    changed = representation != raw_prefix
    retained = int(changed and complete)
    retained_observations = len(targets) if retained else 0
    counts = {
        "input_page_count": 1,
        "input_content_characters": len(raw_text),
        "input_characters_beyond_parent_prefix": max(
            0, len(raw_text) - PAGE_CHARACTER_CAP
        ),
        "visible_schema_column_count": len(schema),
        "visible_target_field_count": len(targets),
        **identity_counts,
        "raw_detail_candidate_line_count": raw_candidates,
        "target_detail_candidate_count": target_candidates,
        "duplicate_or_conflicting_target_count": conflicts,
        "discovered_record_count": int(complete),
        "admissible_record_count": int(complete),
        "admissible_bound_observation_count": len(targets) if complete else 0,
        "retained_record_count": retained,
        "retained_bound_observation_count": retained_observations,
        "compact_prefix_characters": compact_chars if retained else 0,
        "raw_prefix_characters_retained": raw_retained if retained else len(raw_prefix),
        "output_characters": len(representation),
        "projection_failure_count": failure,
        "positive_signed_credit_count": 0,
        "candidate_evidence_changed": changed,
        "mechanism_engaged": bool(retained),
        "exact_parent_prefix_handoff": not changed,
    }
    receipt = _receipt(counts)
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
            "output_characters": len(representation),
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
        "control_evidence": raw_prefix,
        "candidate_evidence": representation,
        "control_evidence_sha256": hashlib.sha256(raw_prefix.encode()).hexdigest(),
        "candidate_evidence_sha256": hashlib.sha256(
            representation.encode()
        ).hexdigest(),
        "content_free_receipt": parent_receipt,
        "page_self_record_receipt": receipt,
        "same_forward_decoded_page_only": True,
        "same_exact_character_budget": len(raw_prefix) == len(representation),
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
        "file_environment_process_network_search_model_or_evaluator_accessed": False,
        "benchmark_or_evaluator_launch_authorized": False,
    }
    value["artifact_payload_sha256"] = parent.payload_sha256(value)
    return validate_representation(
        value,
        question=question,
        page=page,
        page_character_cap=page_character_cap,
        replay=False,
    )


def validate_representation(
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
    control = copied.get("control_evidence")
    candidate = copied.get("candidate_evidence")
    parent_receipt = copied.get("content_free_receipt")
    receipt = copied.get("page_self_record_receipt")
    expected = {
        "artifact_version", "role", "policy_id", "control_evidence",
        "candidate_evidence", "control_evidence_sha256",
        "candidate_evidence_sha256", "content_free_receipt",
        "page_self_record_receipt", "same_forward_decoded_page_only",
        "same_exact_character_budget",
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read",
        "file_environment_process_network_search_model_or_evaluator_accessed",
        "benchmark_or_evaluator_launch_authorized", "artifact_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(control, str)
        or not isinstance(candidate, str)
        or len(control) != len(candidate)
        or len(control) > page_character_cap
        or copied.get("control_evidence_sha256")
        != hashlib.sha256(control.encode()).hexdigest()
        or copied.get("candidate_evidence_sha256")
        != hashlib.sha256(candidate.encode()).hexdigest()
        or not isinstance(parent_receipt, Mapping)
        or parent.validate_receipt(parent_receipt) != dict(parent_receipt)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or parent_receipt["output_characters"] != len(candidate)
        or receipt["output_characters"] != len(candidate)
        or receipt["visible_schema_column_count"]
        != parent_receipt["visible_schema_column_count"]
        or receipt["discovered_record_count"]
        != parent_receipt["discovered_record_count"]
        or receipt["retained_record_count"]
        != parent_receipt["retained_record_count"]
        or receipt["retained_bound_observation_count"]
        != parent_receipt["retained_bound_observation_count"]
        or receipt["candidate_evidence_changed"] is not (candidate != control)
        or copied.get("same_forward_decoded_page_only") is not True
        or copied.get("same_exact_character_budget") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
                "entropy_or_information_gain_assigns_signed_credit",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read",
                "file_environment_process_network_search_model_or_evaluator_accessed",
                "benchmark_or_evaluator_launch_authorized",
            )
        )
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.49 page-self record representation drifted")
    if replay and copied != build_representation(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError("V2.50.49 page-self record representation is not reproducible")
    return copied


__all__ = [
    "MAXIMUM_INPUT_PAGE_CHARACTERS", "PAGE_CHARACTER_CAP", "POLICY_ID", "ROLE",
    "build_representation", "validate_receipt", "validate_representation",
]
