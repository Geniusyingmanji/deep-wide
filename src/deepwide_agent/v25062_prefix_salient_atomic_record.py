"""Pure prefix-salient atomic-record successor to V2.50.61.

V2.50.61 found that version-qualified identity was reachable on every page in
its fixed external population, while only four target fields were first seen
after the inherited 5,000-character prefix.  This orthogonal successor does
not recover suffix information.  It admits a record only when the identity and
every exact target field are already bound inside the inherited prefix, then
moves one atomic source/identity/target/value record to the front under the
same exact character budget.

The module reads only a visible question and one caller-supplied public page.
Its sole dependency is the capability-small V2.50.61 representation primitive.
It has no file, environment, process, network, search, model, evaluator,
benchmark-label, score, reward, history, or credential capability.  Entropy
and information gain remain shadow-only and assign no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from . import v25061_pure_version_qualified_late_record as parent


POLICY_ID = "v25062_prefix_salient_atomic_record_v1"
ROLE = "v25062_prefix_salient_atomic_record"
RECEIPT_ROLE = "v25062_content_free_prefix_salient_atomic_record_receipt"
PAGE_CHARACTER_CAP = parent.PAGE_CHARACTER_CAP
MAXIMUM_INPUT_PAGE_CHARACTERS = parent.MAXIMUM_INPUT_PAGE_CHARACTERS
MINIMUM_RAW_PREFIX_CHARACTERS = parent.MINIMUM_RAW_PREFIX_CHARACTERS

_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_schema_column_count",
    "visible_target_field_count",
    "labelled_identity_binding_count",
    "exact_consensus_identity_binding_count",
    "version_qualified_consensus_binding_count",
    "unique_bound_identity_count",
    "target_detail_candidate_count",
    "uniquely_bound_target_field_count",
    "prefix_target_field_count",
    "late_target_field_count",
    "duplicate_or_conflicting_target_count",
    "complete_record_count",
    "prefix_complete_record_count",
    "retained_record_count",
    "retained_bound_observation_count",
    "compact_capacity_failure_count",
    "compact_prefix_characters",
    "raw_prefix_characters_retained",
    "output_characters",
    "projection_failure_count",
    "positive_signed_credit_count",
)


def _complete_prefix_record(
    question: str, page: Mapping[str, Any]
) -> tuple[dict[str, str] | None, dict[str, int], dict[str, str], str]:
    normalized_page, raw_text = parent._page(page)
    schema = parent._schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    labelled_identity = None
    labelled_count = 0
    exact_identity = None
    exact_count = 0
    qualified_identity = None
    qualified_count = 0
    fields: dict[str, str] = {}
    positions: dict[str, int] = {}
    target_candidates = conflicts = failure = 0
    try:
        if len(schema) >= 2:
            labelled_identity, labelled = parent._bound_labelled_identity(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
                row_label=schema[0],
            )
            labelled_count = int(
                labelled_identity is not None
                and labelled["jointly_bound_identity_count"] == 1
            )
            exact_identity, exact_counts = parent._consensus_identity(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
            )
            exact_count = int(
                exact_identity is not None
                and exact_counts["consensus_identity_binding_count"] == 1
            )
            qualified_identity, qualified_counts = (
                parent._version_qualified_consensus(
                    title=normalized_page["title"],
                    text=raw_text,
                    url=normalized_page["url"],
                )
            )
            qualified_count = int(
                qualified_identity is not None
                and qualified_counts[
                    "version_qualified_consensus_binding_count"
                ]
                == 1
            )
            fields, positions, target_candidates, conflicts = (
                parent._field_map_with_positions(raw_text, targets)
            )
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        labelled_identity = exact_identity = qualified_identity = None
        labelled_count = exact_count = qualified_count = 0
        fields = {}
        positions = {}
        target_candidates = conflicts = 0

    identities: dict[str, str] = {}
    for identity in (labelled_identity, exact_identity, qualified_identity):
        if identity is not None:
            identities.setdefault(parent._identity_key(identity), identity)
    identity = next(iter(identities.values())) if len(identities) == 1 else None
    unique_fields = len(fields)
    prefix_fields = sum(
        0 <= positions.get(target, -1) < PAGE_CHARACTER_CAP for target in targets
    )
    late_fields = sum(
        positions.get(target, -1) >= PAGE_CHARACTER_CAP for target in targets
    )
    complete = bool(
        identity is not None
        and len(schema) >= 2
        and unique_fields == len(targets)
        and conflicts == 0
        and failure == 0
    )
    prefix_complete = bool(
        complete
        and prefix_fields == len(targets)
        and late_fields == 0
    )
    record = (
        {schema[0]: identity, **{target: fields[target] for target in targets}}
        if prefix_complete
        else None
    )
    counts = {
        "input_page_count": 1,
        "input_content_characters": len(raw_text),
        "input_characters_beyond_parent_prefix": max(
            0, len(raw_text) - PAGE_CHARACTER_CAP
        ),
        "visible_schema_column_count": len(schema),
        "visible_target_field_count": len(targets),
        "labelled_identity_binding_count": labelled_count,
        "exact_consensus_identity_binding_count": exact_count,
        "version_qualified_consensus_binding_count": qualified_count,
        "unique_bound_identity_count": len(identities),
        "target_detail_candidate_count": target_candidates,
        "uniquely_bound_target_field_count": unique_fields,
        "prefix_target_field_count": prefix_fields,
        "late_target_field_count": late_fields,
        "duplicate_or_conflicting_target_count": conflicts,
        "complete_record_count": int(complete),
        "prefix_complete_record_count": int(prefix_complete),
        "projection_failure_count": failure,
    }
    return record, counts, normalized_page, raw_text


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "exact_parent_prefix_handoff": bool(value["exact_parent_prefix_handoff"]),
        "identity_routes_match_v25060": True,
        "complete_target_record_must_already_be_inside_parent_prefix": True,
        "absolute_late_information_recovery_disabled": True,
        "source_url_record_identity_target_and_value_atomically_bound": True,
        "compact_record_atomic_and_unsplit": True,
        "same_forward_decoded_page_only": True,
        "same_exact_parent_character_budget": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
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
        "candidate_evidence_changed",
        "mechanism_engaged",
        "exact_parent_prefix_handoff",
    )
    true_flags = (
        "identity_routes_match_v25060",
        "complete_target_record_must_already_be_inside_parent_prefix",
        "absolute_late_information_recovery_disabled",
        "source_url_record_identity_target_and_value_atomically_bound",
        "compact_record_atomic_and_unsplit",
        "same_forward_decoded_page_only",
        "same_exact_parent_character_budget",
    )
    false_flags = (
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read",
        "contains_question_identity_url_title_page_record_value_prediction_answer_hash_or_credential",
        "file_environment_process_network_search_model_or_evaluator_accessed",
        "benchmark_or_evaluator_launch_authorized",
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
    counts_valid = all(
        not isinstance(copied.get(name), bool)
        and isinstance(copied.get(name), int)
        and copied[name] >= 0
        for name in _COUNT_FIELDS
    )
    target_count = copied.get("visible_target_field_count", 0)
    complete = bool(
        counts_valid
        and copied.get("unique_bound_identity_count") == 1
        and target_count > 0
        and copied.get("uniquely_bound_target_field_count") == target_count
        and copied.get("duplicate_or_conflicting_target_count") == 0
        and copied.get("projection_failure_count") == 0
    )
    prefix_complete = bool(
        complete
        and copied.get("prefix_target_field_count") == target_count
        and copied.get("late_target_field_count") == 0
    )
    retained = copied.get("retained_record_count") == 1
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not counts_valid
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["input_page_count"] != 1
        or copied["input_characters_beyond_parent_prefix"]
        != max(0, copied["input_content_characters"] - PAGE_CHARACTER_CAP)
        or target_count != max(0, copied["visible_schema_column_count"] - 1)
        or copied["labelled_identity_binding_count"] not in {0, 1}
        or copied["exact_consensus_identity_binding_count"] not in {0, 1}
        or copied["version_qualified_consensus_binding_count"] not in {0, 1}
        or copied["unique_bound_identity_count"] > 3
        or copied["prefix_target_field_count"]
        + copied["late_target_field_count"]
        > copied["uniquely_bound_target_field_count"]
        or copied["complete_record_count"] != int(complete)
        or copied["prefix_complete_record_count"] != int(prefix_complete)
        or copied["retained_record_count"] > copied["prefix_complete_record_count"]
        or copied["retained_bound_observation_count"]
        != (target_count if retained else 0)
        or copied["compact_capacity_failure_count"]
        != int(prefix_complete and not retained)
        or copied["output_characters"]
        != min(copied["input_content_characters"], PAGE_CHARACTER_CAP)
        or copied["raw_prefix_characters_retained"] > PAGE_CHARACTER_CAP
        or copied["projection_failure_count"] not in {0, 1}
        or copied["positive_signed_credit_count"] != 0
        or copied["candidate_evidence_changed"] is not retained
        or copied["mechanism_engaged"] is not retained
        or copied["exact_parent_prefix_handoff"] is retained
        or retained
        and (
            copied["compact_prefix_characters"] <= 0
            or copied["late_target_field_count"] != 0
        )
        or copied["exact_parent_prefix_handoff"]
        and (
            copied["compact_prefix_characters"] != 0
            or copied["retained_record_count"] != 0
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.62 prefix-salient receipt drifted")
    return copied


def extract_record(question: str, page: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.62 visible question is absent")
    record, _counts, _normalized, _text = _complete_prefix_record(question, page)
    if record is None:
        raise ValueError("V2.50.62 prefix-complete record is not admissible")
    return record


def build_representation(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.62 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.50.62 parent page cap drifted")
    record, counts, normalized_page, raw_text = _complete_prefix_record(question, page)
    schema = parent._schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    raw_prefix = raw_text[:PAGE_CHARACTER_CAP]
    candidate = raw_prefix
    compact_chars = 0
    raw_retained = len(raw_prefix)
    if record is not None:
        identity = record[schema[0]]
        compact = "\n".join(
            (
                "[PREFIX-SALIENT CONSENSUS-BOUND ATOMIC RECORD]",
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
                                + parent._identity_key(identity)
                            ).encode("utf-8")
                        ).hexdigest()[:24],
                        "row": identity,
                        "cells": [[target, record[target]] for target in targets],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "[/PREFIX-SALIENT CONSENSUS-BOUND ATOMIC RECORD]",
            )
        )
        marker = "\n[INHERITED RAW PAGE PREFIX]\n"
        raw_budget = len(raw_prefix) - len(compact) - len(marker)
        if raw_budget >= MINIMUM_RAW_PREFIX_CHARACTERS:
            candidate = compact + marker + raw_text[:raw_budget]
            compact_chars = len(compact)
            raw_retained = min(len(raw_text), raw_budget)
    changed = candidate != raw_prefix
    retained = int(changed and record is not None)
    target_count = len(targets)
    counts.update(
        {
            "retained_record_count": retained,
            "retained_bound_observation_count": target_count if retained else 0,
            "compact_capacity_failure_count": int(
                record is not None and not retained
            ),
            "compact_prefix_characters": compact_chars if retained else 0,
            "raw_prefix_characters_retained": raw_retained if retained else len(raw_prefix),
            "output_characters": len(candidate),
            "positive_signed_credit_count": 0,
            "candidate_evidence_changed": changed,
            "mechanism_engaged": bool(retained),
            "exact_parent_prefix_handoff": not changed,
        }
    )
    receipt = _receipt(counts)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "control_evidence": raw_prefix,
        "candidate_evidence": candidate,
        "control_evidence_sha256": hashlib.sha256(raw_prefix.encode()).hexdigest(),
        "candidate_evidence_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "prefix_salient_atomic_record_receipt": receipt,
        "same_forward_decoded_page_only": True,
        "same_exact_character_budget": len(raw_prefix) == len(candidate),
        "absolute_late_information_recovery_disabled": True,
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
    receipt = copied.get("prefix_salient_atomic_record_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "control_evidence",
        "candidate_evidence",
        "control_evidence_sha256",
        "candidate_evidence_sha256",
        "prefix_salient_atomic_record_receipt",
        "same_forward_decoded_page_only",
        "same_exact_character_budget",
        "absolute_late_information_recovery_disabled",
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read",
        "file_environment_process_network_search_model_or_evaluator_accessed",
        "benchmark_or_evaluator_launch_authorized",
        "artifact_payload_sha256",
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
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["output_characters"] != len(candidate)
        or receipt["candidate_evidence_changed"] is not (candidate != control)
        or copied.get("same_forward_decoded_page_only") is not True
        or copied.get("same_exact_character_budget") is not True
        or copied.get("absolute_late_information_recovery_disabled") is not True
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
        raise ValueError("V2.50.62 prefix-salient representation drifted")
    if replay and copied != build_representation(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError("V2.50.62 representation is not reproducible")
    return copied


__all__ = [
    "MAXIMUM_INPUT_PAGE_CHARACTERS",
    "PAGE_CHARACTER_CAP",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_representation",
    "extract_record",
    "validate_receipt",
    "validate_representation",
]
