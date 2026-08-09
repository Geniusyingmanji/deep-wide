"""Bound late-page records before the inherited 5k page boundary.

The frozen production fetch helper returns only the first 5,000 characters of
each decoded public page.  That makes a later runtime projector unable to see
structured rows that occur after the prefix.  This pure append-only primitive
operates on the complete text decoded by the *same* fetch effect, discovers
records using the existing conservative schema ledger, and emits at most the
same 5,000 characters expected by the parent runtime.

Every compact row is bound to the canonical source URL, one page-local record
identity, the visible row-key label, and visible target columns.  Conflicting
coordinates are omitted.  Compact rows are never split.  Any absence of a
safe binding, parser failure, or capacity failure returns the exact inherited
5k prefix.  The component has no filesystem, environment, process, network,
model, benchmark-label, evaluator, score, reward, or credential capability.
Entropy and information gain remain shadow-only and assign no credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as structure
from . import v24939_schema_bound_record_ledger as ledger
from . import v24949_mutual_partial_signature_ledger as discovery
from .clients import canonicalize_url


POLICY_ID = "v24980_identity_target_bound_late_page_projection_v1"
ROLE = "v24980_identity_target_bound_late_page_projection"
RECEIPT_ROLE = "v24980_content_free_late_page_projection_receipt"
PAGE_CHARACTER_CAP = 5_000
MAXIMUM_INPUT_PAGE_CHARACTERS = 3_000_000
MINIMUM_RAW_PREFIX_CHARACTERS = 512
MAXIMUM_COMPACT_RECORD_CHARACTERS = 1_200
MAXIMUM_VISIBLE_GROUPS = 64
MAXIMUM_QUERY_TERMS = 96

_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_schema_column_count",
    "discovered_record_count",
    "discovered_row_key_count",
    "conflicting_coordinate_count",
    "admissible_record_count",
    "admissible_bound_observation_count",
    "retained_record_count",
    "retained_bound_observation_count",
    "oversized_record_count",
    "compact_prefix_characters",
    "raw_prefix_characters_retained",
    "output_characters",
    "projection_failure_count",
    "positive_signed_credit_count",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _page(raw: Mapping[str, Any]) -> tuple[dict[str, str], str]:
    if not isinstance(raw, Mapping):
        raise ValueError("V2.49.80 page is not a mapping")
    url = canonicalize_url(str(raw.get("url") or ""))
    title = " ".join(str(raw.get("title") or "").split())[:500]
    value = raw.get("text")
    if value is None:
        value = raw.get("raw_content")
    if value is None:
        value = raw.get("content")
    text = str(value or "")
    if (
        not url
        or not text
        or "\x00" in text
        or len(text) > MAXIMUM_INPUT_PAGE_CHARACTERS
    ):
        raise ValueError("V2.49.80 page identity or text drifted")
    return {"title": title, "url": url, "content": text}, text


def _contains(value: str, phrase: str) -> bool:
    return structure._contains(value, phrase)


def _record_line(record: Mapping[str, Any], fields: Sequence[Mapping[str, Any]]) -> str:
    return json.dumps(
        {
            "record_id": str(record["record_id"]),
            "row": str(record["row_key"]),
            "cells": [
                [str(field["target_label"]), str(field["value"])]
                for field in fields
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _eligible_records(
    records: Sequence[Mapping[str, Any]],
    conflicts: set[tuple[str, int]],
) -> tuple[list[dict[str, Any]], int, int]:
    output: list[dict[str, Any]] = []
    observation_count = 0
    oversized = 0
    seen: set[tuple[str, str, int, str]] = set()
    for record in records:
        row = ledger._canonical(record["row_key"])
        fields: list[Mapping[str, Any]] = []
        for field in record["fields"]:
            target = int(field["target_index"])
            identity = (
                str(record["source_url"]),
                row,
                target,
                ledger._canonical(field["value"]),
            )
            if (row, target) in conflicts or identity in seen:
                continue
            fields.append(field)
            seen.add(identity)
        if not fields:
            continue
        line = _record_line(record, fields)
        if len(line) > MAXIMUM_COMPACT_RECORD_CHARACTERS:
            oversized += 1
            continue
        output.append(
            {
                "line": line,
                "row": str(record["row_key"]),
                "fields": [dict(field) for field in fields],
                "page_ordinal": int(record["source_page_ordinal"]),
                "group_ordinal": int(record["structure_group_ordinal"]),
                "record_id": str(record["record_id"]),
            }
        )
        observation_count += len(fields)
    return output, observation_count, oversized


def _ranked(
    records: Sequence[Mapping[str, Any]],
    *,
    question: str,
) -> list[dict[str, Any]]:
    groups = structure.visible_requirement_groups(
        question, maximum_groups=MAXIMUM_VISIBLE_GROUPS
    )
    terms = structure._query_terms(question, MAXIMUM_QUERY_TERMS)

    def key(record: Mapping[str, Any]) -> tuple[Any, ...]:
        surface = " ".join(
            (
                str(record["row"]),
                *(
                    f"{field['target_label']} {field['value']}"
                    for field in record["fields"]
                ),
            )
        )
        return (
            -sum(_contains(surface, group) for group in groups),
            -sum(_contains(surface, term) for term in terms),
            -len(record["fields"]),
            int(record["page_ordinal"]),
            int(record["group_ordinal"]),
            str(record["record_id"]),
        )

    return [dict(value) for value in sorted(records, key=key)]


def _compact_header(page: Mapping[str, str], schema: Sequence[Mapping[str, Any]]) -> str:
    return "\n".join(
        (
            "[IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]",
            "untrusted_public_page_records=true",
            "source_url=" + str(page["url"]),
            "row_key_label=" + json.dumps(str(schema[0]["display"]), ensure_ascii=False),
            "target_columns="
            + json.dumps(
                [str(column["display"]) for column in schema[1:]],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
    )


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "exact_parent_prefix_handoff": bool(value["exact_parent_prefix_handoff"]),
        "canonical_source_identity_bound": True,
        "visible_target_schema_bound": True,
        "page_local_record_identity_bound": True,
        "conflicting_coordinates_omitted": True,
        "compact_records_atomic_and_unsplit": True,
        "same_forward_decoded_page_only": True,
        "parent_page_character_cap_preserved": True,
        "parent_page_character_count_preserved": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_url_title_page_record_value_prediction_answer_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        "candidate_evidence_changed",
        "mechanism_engaged",
        "exact_parent_prefix_handoff",
        "canonical_source_identity_bound",
        "visible_target_schema_bound",
        "page_local_record_identity_bound",
        "conflicting_coordinates_omitted",
        "compact_records_atomic_and_unsplit",
        "same_forward_decoded_page_only",
        "parent_page_character_cap_preserved",
        "parent_page_character_count_preserved",
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_information_gain_shadow_only",
        "entropy_or_information_gain_assigns_signed_credit",
        "contains_question_url_title_page_record_value_prediction_answer_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    true_flags = (
        "canonical_source_identity_bound",
        "visible_target_schema_bound",
        "page_local_record_identity_bound",
        "conflicting_coordinates_omitted",
        "compact_records_atomic_and_unsplit",
        "same_forward_decoded_page_only",
        "parent_page_character_cap_preserved",
        "parent_page_character_count_preserved",
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
        or any(
            not isinstance(copied.get(name), bool)
            for name in (
                "candidate_evidence_changed",
                "mechanism_engaged",
                "exact_parent_prefix_handoff",
            )
        )
        or copied["input_page_count"] != 1
        or copied["input_characters_beyond_parent_prefix"]
        != max(0, copied["input_content_characters"] - PAGE_CHARACTER_CAP)
        or copied["retained_record_count"] > copied["admissible_record_count"]
        or copied["retained_bound_observation_count"]
        > copied["admissible_bound_observation_count"]
        or copied["output_characters"] > PAGE_CHARACTER_CAP
        or copied["output_characters"]
        != min(copied["input_content_characters"], PAGE_CHARACTER_CAP)
        or copied["raw_prefix_characters_retained"] > PAGE_CHARACTER_CAP
        or copied["positive_signed_credit_count"] != 0
        or copied["projection_failure_count"] not in {0, 1}
        or copied["mechanism_engaged"]
        is not (
            copied["retained_record_count"] > 0
            and copied["retained_bound_observation_count"] > 0
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
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.80 late-page receipt drifted")
    return copied


def build_projection(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.80 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.49.80 parent page cap drifted")
    normalized_page, raw_text = _page(page)
    raw_prefix = raw_text[:PAGE_CHARACTER_CAP]
    schema: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    conflicts: set[tuple[str, int]] = set()
    eligible: list[dict[str, Any]] = []
    observations = 0
    oversized = 0
    failure = 0
    try:
        stable = structure._stable_pages([normalized_page])
        if len(stable) != 1 or stable[0]["url"] != normalized_page["url"]:
            raise ValueError("V2.49.80 stable page identity drifted")
        schema = ledger._visible_schema(question)
        if schema:
            records, _counts = discovery._discover(stable, schema)
            conflicts, _hosts, _urls = ledger._coordinate_summary(records)
            eligible, observations, oversized = _eligible_records(records, conflicts)
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        schema = []
        records = []
        conflicts = set()
        eligible = []
        observations = 0
        oversized = 0

    ranked = _ranked(eligible, question=question) if eligible and schema else []
    retained: list[dict[str, Any]] = []
    projection = raw_prefix
    compact_chars = 0
    raw_retained = len(raw_prefix)
    if ranked and schema and failure == 0:
        header = _compact_header(normalized_page, schema)
        footer = "[/IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]"
        raw_marker = "\n[INHERITED RAW PAGE PREFIX]\n"
        output_budget = len(raw_prefix)
        fixed = len(header) + 1 + len(footer) + len(raw_marker)
        for record in ranked:
            line = str(record["line"])
            line_cost = len(line) + 1
            used = fixed + sum(len(str(item["line"])) + 1 for item in retained)
            if used + line_cost + MINIMUM_RAW_PREFIX_CHARACTERS <= output_budget:
                retained.append(record)
        if retained:
            compact = header + "\n" + "\n".join(
                str(record["line"]) for record in retained
            ) + "\n" + footer
            raw_budget = output_budget - len(compact) - len(raw_marker)
            if raw_budget >= MINIMUM_RAW_PREFIX_CHARACTERS:
                projection = compact + raw_marker + raw_text[:raw_budget]
                compact_chars = len(compact)
                raw_retained = min(len(raw_text), raw_budget)
            else:
                retained = []

    changed = projection != raw_prefix
    if not changed:
        retained = []
        compact_chars = 0
        raw_retained = len(raw_prefix)
        projection = raw_prefix
    retained_observations = sum(len(record["fields"]) for record in retained)
    receipt = _receipt(
        {
            "input_page_count": 1,
            "input_content_characters": len(raw_text),
            "input_characters_beyond_parent_prefix": max(
                0, len(raw_text) - PAGE_CHARACTER_CAP
            ),
            "visible_schema_column_count": len(schema),
            "discovered_record_count": len(records),
            "discovered_row_key_count": len(
                {ledger._canonical(record["row_key"]) for record in records}
            ),
            "conflicting_coordinate_count": len(conflicts),
            "admissible_record_count": len(eligible),
            "admissible_bound_observation_count": observations,
            "retained_record_count": len(retained),
            "retained_bound_observation_count": retained_observations,
            "oversized_record_count": oversized,
            "compact_prefix_characters": compact_chars,
            "raw_prefix_characters_retained": raw_retained,
            "output_characters": len(projection),
            "projection_failure_count": failure,
            "positive_signed_credit_count": 0,
            "candidate_evidence_changed": changed,
            "mechanism_engaged": bool(retained) and changed and failure == 0,
            "exact_parent_prefix_handoff": not changed,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode("utf-8")).hexdigest(),
        "content_free_receipt": receipt,
        "same_forward_decoded_page_only": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
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
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(projection, str)
        or len(projection) > page_character_cap
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode("utf-8")).hexdigest()
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt.get("output_characters") != len(projection)
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
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.80 late-page projection drifted")
    if replay and copied != build_projection(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError("V2.49.80 late-page projection is not reproducible")
    return copied


__all__ = [
    "MAXIMUM_INPUT_PAGE_CHARACTERS",
    "PAGE_CHARACTER_CAP",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_projection",
    "payload_sha256",
    "validate_projection",
    "validate_receipt",
]
