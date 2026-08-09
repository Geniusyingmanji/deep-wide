"""Pure per-page projection for visible multi-identity detail tasks.

The frozen V2.50.04 projector deliberately accepts exactly one visible tagged
identity.  This append-only successor handles a different visible contract: a
question enumerates two or more row identities, while each already-fetched
authority detail page describes exactly one of those rows.

Identity enumeration must be either one consecutively numbered visible block
(``<ENTITIES>``, ``<ROWS>``, or another plural uppercase tag) or two or more
repetitions of one inline uppercase tag.  A page is admissible only when one
and only one enumerated identity jointly binds to exact URL-path tokens and to
the title/leading-page surface.  The authority URL token and every exact target
field must bind on that same page.  Each compact record is admitted atomically;
ambiguous identities, missing/duplicate/conflicting fields, or insufficient
space return the inherited 5,000-character prefix byte-for-byte.

The component consumes only its question and caller-supplied page.  It has no
file, environment, process, network, search, model, benchmark-label,
evaluator, score, reward, historical-result, or credential capability.
Entropy and information gain are shadow-only and assign no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from . import v24980_late_page_bound_projection as parent
from . import v25004_identity_bound_detail_fields as single


POLICY_ID = "v25014_multi_identity_detail_field_projection_v1"
ROLE = "v25014_multi_identity_detail_field_projection"
RECEIPT_ROLE = "v25014_content_free_multi_identity_detail_field_receipt"
PAGE_CHARACTER_CAP = parent.PAGE_CHARACTER_CAP
MAXIMUM_INPUT_PAGE_CHARACTERS = parent.MAXIMUM_INPUT_PAGE_CHARACTERS
MAXIMUM_VISIBLE_IDENTITIES = 32
MAXIMUM_IDENTITY_CHARACTERS = 200
_BLOCK = re.compile(
    r"<(?P<tag>[A-Z][A-Z0-9_]{1,31})>\s*\n(?P<body>.*?)\n</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
_INLINE = re.compile(
    r"<(?P<tag>[A-Z][A-Z0-9_]{1,31})>\s*"
    r"(?P<value>[^<>\r\n]{1,200}?)\s*</(?P=tag)>",
    re.IGNORECASE,
)
_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_identity_count",
    "visible_schema_column_count",
    "visible_target_field_count",
    "identity_url_path_match_count",
    "identity_page_surface_match_count",
    "joint_identity_path_surface_match_count",
    "ambiguous_joint_identity_binding_count",
    "authority_url_token_match_count",
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


def _identity(value: object) -> str | None:
    text = " ".join(unicodedata.normalize("NFKC", str(value or "")).split())
    text = text.strip(" |\t\r\n")
    if (
        not text
        or len(text) > MAXIMUM_IDENTITY_CHARACTERS
        or any(character in text for character in "<>|\x00\r\n")
        or any(ord(character) < 32 for character in text)
        or single._canonical(text) in {"unknown", "n/a", "na", "none", "null", "-"}
    ):
        return None
    return text


def _unique(values: list[str]) -> tuple[str, ...]:
    if not 2 <= len(values) <= MAXIMUM_VISIBLE_IDENTITIES:
        return ()
    keys = [single._canonical(value) for value in values]
    return tuple(values) if len(set(keys)) == len(keys) else ()


def _numbered_identities(body: str) -> tuple[str, ...]:
    lines = body.splitlines()
    values: list[str] = []
    for ordinal, raw in enumerate(lines, 1):
        prefix = f"{ordinal}. "
        if not raw.startswith(prefix):
            return ()
        value = _identity(raw[len(prefix) :])
        if value is None:
            return ()
        values.append(value)
    return _unique(values)


def visible_identities(question: str) -> tuple[str, ...]:
    """Return one strict visible multi-row identity vector or fail closed."""

    if not isinstance(question, str) or not question.strip():
        return ()
    blocks = list(_BLOCK.finditer(question))
    valid_blocks = [
        match
        for match in blocks
        if match.group("tag").upper().endswith("S")
        and _numbered_identities(match.group("body"))
    ]
    if blocks:
        if len(blocks) != 1 or len(valid_blocks) != 1:
            return ()
        # A second inline tag outside the numbered block makes ownership of the
        # row identity vector ambiguous, even when its text happens to match.
        outside = question[: blocks[0].start()] + question[blocks[0].end() :]
        if _INLINE.search(outside) is not None:
            return ()
        return _numbered_identities(valid_blocks[0].group("body"))

    inline = list(_INLINE.finditer(question))
    if len(inline) < 2 or len({match.group("tag").casefold() for match in inline}) != 1:
        return ()
    values: list[str] = []
    for match in inline:
        value = _identity(match.group("value"))
        if value is None:
            return ()
        values.append(value)
    return _unique(values)


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "exact_parent_prefix_handoff": bool(value["exact_parent_prefix_handoff"]),
        "identities_come_only_from_one_visible_numbered_or_repeated_tag_vector": True,
        "schema_comes_only_from_robust_visible_question_parser": True,
        "one_page_requires_exactly_one_joint_visible_identity_binding": True,
        "identity_bound_to_exact_url_path_tokens_and_page_surface": True,
        "authority_bound_to_exact_distinctive_url_token": True,
        "target_fields_exact_label_unique_and_same_page": True,
        "compact_record_atomic_and_unsplit": True,
        "same_forward_decoded_page_only": True,
        "parent_page_character_cap_and_count_preserved": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_identity_url_title_page_record_value_prediction_answer_hash_or_credential": False,
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
        "identities_come_only_from_one_visible_numbered_or_repeated_tag_vector",
        "schema_comes_only_from_robust_visible_question_parser",
        "one_page_requires_exactly_one_joint_visible_identity_binding",
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
        "contains_question_identity_url_title_page_record_value_prediction_answer_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
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
    identity_count = copied.get("visible_identity_count")
    path_count = copied.get("identity_url_path_match_count")
    surface_count = copied.get("identity_page_surface_match_count")
    joint_count = copied.get("joint_identity_path_surface_match_count")
    target_count = copied.get("visible_target_field_count")
    complete = bool(
        isinstance(identity_count, int)
        and identity_count >= 2
        and isinstance(target_count, int)
        and target_count > 0
        and copied.get("authority_url_token_match_count") == 1
        and joint_count == 1
        and copied.get("duplicate_or_conflicting_target_count") == 0
        and copied.get("admissible_bound_observation_count") == target_count
        and copied.get("projection_failure_count") == 0
    )
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
        or copied["visible_identity_count"] > MAXIMUM_VISIBLE_IDENTITIES
        or copied["visible_schema_column_count"] > 64
        or copied["raw_detail_candidate_line_count"]
        < copied["target_detail_candidate_count"]
        or path_count > identity_count
        or surface_count > identity_count
        or joint_count > min(path_count, surface_count)
        or copied["ambiguous_joint_identity_binding_count"]
        != int(joint_count > 1)
        or copied["authority_url_token_match_count"] not in {0, 1}
        or copied["discovered_record_count"] not in {0, 1}
        or copied["admissible_record_count"] not in {0, 1}
        or copied["retained_record_count"] not in {0, 1}
        or copied["admissible_record_count"] > copied["discovered_record_count"]
        or copied["retained_record_count"] > copied["admissible_record_count"]
        or copied["admissible_bound_observation_count"] > target_count
        or copied["retained_bound_observation_count"]
        > copied["admissible_bound_observation_count"]
        or copied["output_characters"]
        != min(copied["input_content_characters"], PAGE_CHARACTER_CAP)
        or copied["positive_signed_credit_count"] != 0
        or copied["projection_failure_count"] not in {0, 1}
        or copied["discovered_record_count"] != int(complete)
        or copied["admissible_record_count"] != copied["discovered_record_count"]
        or copied["admissible_bound_observation_count"]
        != (target_count if copied["admissible_record_count"] == 1 else 0)
        or copied["retained_bound_observation_count"]
        != (target_count if copied["retained_record_count"] == 1 else 0)
        or copied["candidate_evidence_changed"]
        is not (copied["retained_record_count"] == 1)
        or copied["mechanism_engaged"]
        is not (
            copied["retained_record_count"] == 1
            and copied["retained_bound_observation_count"] == target_count
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
        raise ValueError("V2.50.14 multi-identity detail-field receipt drifted")
    return copied


def build_projection(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.14 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.50.14 parent page cap drifted")
    normalized_page, raw_text = single._page(page)
    raw_prefix = raw_text[:PAGE_CHARACTER_CAP]
    identities = visible_identities(question)
    schema = single._schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    authorities = single._authority_tokens(question)
    path_matches: list[str] = []
    surface_matches: list[str] = []
    joint_matches: list[str] = []
    authority_bound = False
    fields: dict[str, str] = {}
    raw_key_values = 0
    target_key_values = 0
    conflicts = 0
    failure = 0
    try:
        if len(identities) >= 2 and len(schema) >= 2 and authorities:
            for identity in identities:
                path_bound, bound_authority = single._url_bindings(
                    normalized_page["url"],
                    identity=identity,
                    authority_tokens=authorities,
                )
                surface_bound = single._page_identity_bound(normalized_page, identity)
                authority_bound = authority_bound or bound_authority
                if path_bound:
                    path_matches.append(identity)
                if surface_bound:
                    surface_matches.append(identity)
                if path_bound and surface_bound:
                    joint_matches.append(identity)
            fields, raw_key_values, target_key_values, conflicts = single._field_map(
                raw_text, targets
            )
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        path_matches = []
        surface_matches = []
        joint_matches = []
        authority_bound = False
        fields = {}
        raw_key_values = target_key_values = conflicts = 0
    complete = bool(
        len(identities) >= 2
        and len(schema) >= 2
        and len(joint_matches) == 1
        and authority_bound
        and conflicts == 0
        and set(fields) == set(targets)
        and failure == 0
    )
    projection = raw_prefix
    compact_chars = 0
    raw_retained = len(raw_prefix)
    if complete:
        matched_identity = joint_matches[0]
        compact = "\n".join(
            (
                # Preserve the frozen parent compact-record wire format so the
                # production runtime counts this one page-local row without a
                # parser fork.  Multi-identity semantics live in the stricter
                # receipt and page binding, not in a new marker string.
                "[IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]",
                "untrusted_public_page_record=true",
                "source_url=" + normalized_page["url"],
                "row_key_label=" + json.dumps(schema[0], ensure_ascii=False),
                "target_columns="
                + json.dumps(list(targets), ensure_ascii=False, separators=(",", ":")),
                json.dumps(
                    {
                        "record_id": hashlib.sha256(
                            (
                                normalized_page["url"]
                                + "\x1f"
                                + single._canonical(matched_identity)
                            ).encode()
                        ).hexdigest()[:24],
                        "row": matched_identity,
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
            "identity_url_path_match_count": len(path_matches),
            "identity_page_surface_match_count": len(surface_matches),
            "joint_identity_path_surface_match_count": len(joint_matches),
            "ambiguous_joint_identity_binding_count": int(len(joint_matches) > 1),
            "authority_url_token_match_count": int(authority_bound),
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
        "content_free_receipt": parent_receipt,
        "multi_identity_detail_receipt": detail_receipt,
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
    detail = copied.get("multi_identity_detail_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "projection",
            "projection_sha256",
            "content_free_receipt",
            "multi_identity_detail_receipt",
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
        or not isinstance(detail, Mapping)
        or validate_receipt(detail) != dict(detail)
        or detail["output_characters"] != len(projection)
        or detail["input_content_characters"] != receipt["input_content_characters"]
        or detail["visible_schema_column_count"]
        != receipt["visible_schema_column_count"]
        or detail["discovered_record_count"] != receipt["discovered_record_count"]
        or detail["admissible_record_count"] != receipt["admissible_record_count"]
        or detail["admissible_bound_observation_count"]
        != receipt["admissible_bound_observation_count"]
        or detail["retained_record_count"] != receipt["retained_record_count"]
        or detail["retained_bound_observation_count"]
        != receipt["retained_bound_observation_count"]
        or detail["compact_prefix_characters"] != receipt["compact_prefix_characters"]
        or detail["raw_prefix_characters_retained"]
        != receipt["raw_prefix_characters_retained"]
        or detail["projection_failure_count"] != receipt["projection_failure_count"]
        or detail["candidate_evidence_changed"] != receipt["candidate_evidence_changed"]
        or detail["mechanism_engaged"] != receipt["mechanism_engaged"]
        or detail["exact_parent_prefix_handoff"] != receipt["exact_parent_prefix_handoff"]
        or copied.get("same_forward_decoded_page_only") is not True
        or copied.get(
            "additional_search_fetch_model_token_context_wall_or_network_byte_cap"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.14 multi-identity detail-field projection drifted")
    if replay and copied != build_projection(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError("V2.50.14 multi-identity detail-field projection is not reproducible")
    return copied


__all__ = [
    "MAXIMUM_INPUT_PAGE_CHARACTERS",
    "MAXIMUM_VISIBLE_IDENTITIES",
    "PAGE_CHARACTER_CAP",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_projection",
    "validate_projection",
    "validate_receipt",
    "visible_identities",
]
