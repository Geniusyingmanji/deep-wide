"""Pure version-qualified consensus successor for long detail pages.

Some public software detail pages identify their primary record as
``<name> <semantic-version>`` in both the HTML title and a body heading, while
the stable URL path contains only ``<name>``.  V2.50.59 deliberately rejects
that non-exact surface.  This append-only successor admits it only when the
same normalized name and the same semantic version occur in two independent
page surfaces and the name is an exact public URL path component.

The exact and labelled V2.50.59 identity routes remain available.  All target
fields still require exact, unique, same-page labels, and at least one complete
target observation must start beyond the inherited 5,000-character prefix.
Ambiguity, a version mismatch, query-only identity, title echo without an
independent body heading, or any field conflict returns the parent prefix
byte-for-byte.

The module is a pure representation function.  It has no file, environment,
process, network, search, model, benchmark-label, evaluator, score, reward,
historical-result, or credential capability.  Entropy and information gain
remain shadow-only and assign no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from . import v24980_late_page_bound_projection as projection_parent
from . import v25004_identity_bound_detail_fields as detail
from . import v25049_page_self_identified_record as labelled_parent
from . import v25059_consensus_late_record as parent


POLICY_ID = "v25060_version_qualified_consensus_late_record_v1"
ROLE = "v25060_version_qualified_consensus_late_record"
RECEIPT_ROLE = "v25060_content_free_version_qualified_late_record_receipt"
PAGE_CHARACTER_CAP = parent.PAGE_CHARACTER_CAP
MAXIMUM_INPUT_PAGE_CHARACTERS = parent.MAXIMUM_INPUT_PAGE_CHARACTERS
_VERSIONED_SURFACE = re.compile(
    r"^(?P<identity>.+?)(?:\s+|-)v?"
    r"(?P<version>\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z][0-9A-Za-z.-]*)?)$",
    re.IGNORECASE,
)
_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_schema_column_count",
    "visible_target_field_count",
    "labelled_identity_binding_count",
    "exact_consensus_identity_binding_count",
    "url_identity_candidate_count",
    "qualified_title_identity_candidate_count",
    "qualified_leading_identity_candidate_count",
    "version_qualified_consensus_binding_count",
    "unique_bound_identity_count",
    "target_detail_candidate_count",
    "uniquely_bound_target_field_count",
    "duplicate_or_conflicting_target_count",
    "late_target_field_count",
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


def _versioned_segments(value: object) -> dict[tuple[str, str], str]:
    """Return exact identity/version pairs from delimiter-bounded segments."""

    text = parent._normalize(value).strip("#*_=~ \t\r\n")
    if not text:
        return {}
    output: dict[tuple[str, str], str] = {}
    for raw in parent._TITLE_SEPARATOR.split(text):
        segment = raw.strip("#*_=~ [](){}")
        match = _VERSIONED_SURFACE.fullmatch(segment)
        if match is None:
            continue
        identity = parent._identity_candidate(match.group("identity"))
        if identity is None:
            continue
        version = match.group("version").casefold()
        key = (labelled_parent._identity_key(identity), version)
        output.setdefault(key, identity)
    return output


def _version_qualified_consensus(
    *, title: str, text: str, url: str
) -> tuple[str | None, dict[str, int]]:
    urls = parent._url_candidates(url)
    titles = _versioned_segments(title)
    leading: dict[tuple[str, str], str] = {}
    lines = [line for line in str(text).splitlines() if parent._normalize(line)]
    title_echo_excluded = False
    content_lines: list[str] = []
    for line in lines:
        if not title_echo_excluded and parent._normalize(line) == parent._normalize(title):
            title_echo_excluded = True
            continue
        content_lines.append(line)
    for line in content_lines[: parent.MAXIMUM_LEADING_LINES]:
        for key, identity in _versioned_segments(line).items():
            leading.setdefault(key, identity)
    joint: list[tuple[str, str]] = []
    for identity_key in sorted(set(urls)):
        title_versions = {
            version for name, version in titles if name == identity_key
        }
        leading_versions = {
            version for name, version in leading if name == identity_key
        }
        if (
            len(title_versions) == 1
            and title_versions == leading_versions
        ):
            joint.append((identity_key, next(iter(title_versions))))
    identity = urls[joint[0][0]] if len(joint) == 1 else None
    return identity, {
        "url_identity_candidate_count": len(urls),
        "qualified_title_identity_candidate_count": len(titles),
        "qualified_leading_identity_candidate_count": len(leading),
        "version_qualified_consensus_binding_count": len(joint),
    }


def _bound_record(
    question: str, page: Mapping[str, Any]
) -> tuple[dict[str, str] | None, dict[str, int], dict[str, str], str]:
    normalized_page, raw_text = detail._page(page)
    schema = detail._schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    labelled_identity = None
    labelled_count = 0
    exact_identity = None
    exact_count = 0
    qualified_identity = None
    qualified_counts = {
        "url_identity_candidate_count": 0,
        "qualified_title_identity_candidate_count": 0,
        "qualified_leading_identity_candidate_count": 0,
        "version_qualified_consensus_binding_count": 0,
    }
    fields: dict[str, str] = {}
    positions: dict[str, int] = {}
    target_candidates = conflicts = failure = 0
    try:
        if len(schema) >= 2:
            labelled_identity, labelled = labelled_parent._bound_identity(
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
            qualified_identity, qualified_counts = _version_qualified_consensus(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
            )
            fields, positions, target_candidates, conflicts = (
                parent._field_map_with_positions(raw_text, targets)
            )
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        labelled_identity = exact_identity = qualified_identity = None
        labelled_count = exact_count = 0
        qualified_counts = {name: 0 for name in qualified_counts}
        fields = {}
        positions = {}
        target_candidates = conflicts = 0

    identities: dict[str, str] = {}
    for identity in (labelled_identity, exact_identity, qualified_identity):
        if identity is not None:
            identities.setdefault(labelled_parent._identity_key(identity), identity)
    identity = next(iter(identities.values())) if len(identities) == 1 else None
    unique_fields = len(fields)
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
    admissible = bool(complete and late_fields >= 1)
    record = (
        {schema[0]: identity, **{target: fields[target] for target in targets}}
        if admissible
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
        **qualified_counts,
        "unique_bound_identity_count": len(identities),
        "target_detail_candidate_count": target_candidates,
        "uniquely_bound_target_field_count": unique_fields,
        "duplicate_or_conflicting_target_count": conflicts,
        "late_target_field_count": late_fields,
        "discovered_record_count": int(complete),
        "admissible_record_count": int(admissible),
        "admissible_bound_observation_count": len(targets) if admissible else 0,
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
        "exact_and_labelled_parent_identity_routes_preserved": True,
        "version_qualified_route_requires_exact_url_name_and_same_version_on_two_page_surfaces": True,
        "one_exact_decoder_title_echo_excluded_from_leading_surface": True,
        "query_parameters_never_supply_identity": True,
        "target_fields_exact_label_unique_and_same_page": True,
        "at_least_one_complete_target_observation_beyond_parent_prefix_required": True,
        "source_url_record_identity_target_and_value_atomically_bound": True,
        "compact_record_atomic_and_unsplit": True,
        "same_forward_decoded_page_only": True,
        "parent_page_character_cap_and_count_preserved": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
        "contains_question_identity_url_title_page_record_value_prediction_answer_hash_or_credential": False,
        "file_environment_process_network_search_model_or_evaluator_accessed": False,
        "benchmark_or_evaluator_launch_authorized": False,
    }
    output["receipt_payload_sha256"] = projection_parent.payload_sha256(output)
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
        "exact_and_labelled_parent_identity_routes_preserved",
        "version_qualified_route_requires_exact_url_name_and_same_version_on_two_page_surfaces",
        "one_exact_decoder_title_echo_excluded_from_leading_surface",
        "query_parameters_never_supply_identity",
        "target_fields_exact_label_unique_and_same_page",
        "at_least_one_complete_target_observation_beyond_parent_prefix_required",
        "source_url_record_identity_target_and_value_atomically_bound",
        "compact_record_atomic_and_unsplit",
        "same_forward_decoded_page_only",
        "parent_page_character_cap_and_count_preserved",
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
    discovered = bool(
        counts_valid
        and copied.get("unique_bound_identity_count") == 1
        and target_count > 0
        and copied.get("uniquely_bound_target_field_count") == target_count
        and copied.get("duplicate_or_conflicting_target_count") == 0
        and copied.get("projection_failure_count") == 0
    )
    admissible = bool(discovered and copied.get("late_target_field_count", 0) >= 1)
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
        or copied["version_qualified_consensus_binding_count"]
        > min(
            copied["url_identity_candidate_count"],
            copied["qualified_title_identity_candidate_count"],
            copied["qualified_leading_identity_candidate_count"],
        )
        or copied["unique_bound_identity_count"] > 3
        or copied["late_target_field_count"]
        > copied["uniquely_bound_target_field_count"]
        or copied["discovered_record_count"] != int(discovered)
        or copied["admissible_record_count"] != int(admissible)
        or copied["admissible_bound_observation_count"]
        != (target_count if admissible else 0)
        or copied["retained_record_count"] > copied["admissible_record_count"]
        or copied["retained_bound_observation_count"]
        != (target_count if retained else 0)
        or copied["output_characters"]
        != min(copied["input_content_characters"], PAGE_CHARACTER_CAP)
        or copied["raw_prefix_characters_retained"] > PAGE_CHARACTER_CAP
        or copied["projection_failure_count"] not in {0, 1}
        or copied["positive_signed_credit_count"] != 0
        or copied["candidate_evidence_changed"] is not retained
        or copied["mechanism_engaged"] is not retained
        or copied["exact_parent_prefix_handoff"] is retained
        or retained and copied["compact_prefix_characters"] <= 0
        or copied["exact_parent_prefix_handoff"]
        and (
            copied["compact_prefix_characters"] != 0
            or copied["retained_record_count"] != 0
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != projection_parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.60 version-qualified late-record receipt drifted")
    return copied


def extract_record(question: str, page: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.60 visible question is absent")
    record, _counts, _normalized, _text = _bound_record(question, page)
    if record is None:
        raise ValueError("V2.50.60 version-qualified record is not admissible")
    return record


def build_representation(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.60 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.50.60 parent page cap drifted")
    record, counts, normalized_page, raw_text = _bound_record(question, page)
    schema = detail._schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    raw_prefix = raw_text[:PAGE_CHARACTER_CAP]
    representation = raw_prefix
    compact_chars = 0
    raw_retained = len(raw_prefix)
    if record is not None:
        identity = record[schema[0]]
        compact = "\n".join(
            (
                "[VERSION-QUALIFIED CONSENSUS-BOUND LATE RECORD]",
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
                                + labelled_parent._identity_key(identity)
                            ).encode("utf-8")
                        ).hexdigest()[:24],
                        "row": identity,
                        "cells": [[target, record[target]] for target in targets],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "[/VERSION-QUALIFIED CONSENSUS-BOUND LATE RECORD]",
            )
        )
        marker = "\n[INHERITED RAW PAGE PREFIX]\n"
        raw_budget = len(raw_prefix) - len(compact) - len(marker)
        if raw_budget >= projection_parent.MINIMUM_RAW_PREFIX_CHARACTERS:
            representation = compact + marker + raw_text[:raw_budget]
            compact_chars = len(compact)
            raw_retained = min(len(raw_text), raw_budget)
    changed = representation != raw_prefix
    retained = int(changed and record is not None)
    target_count = len(targets)
    counts.update(
        {
            "retained_record_count": retained,
            "retained_bound_observation_count": target_count if retained else 0,
            "compact_prefix_characters": compact_chars if retained else 0,
            "raw_prefix_characters_retained": (
                raw_retained if retained else len(raw_prefix)
            ),
            "output_characters": len(representation),
            "positive_signed_credit_count": 0,
            "candidate_evidence_changed": changed,
            "mechanism_engaged": bool(retained),
            "exact_parent_prefix_handoff": not changed,
        }
    )
    receipt = _receipt(counts)
    inherited = projection_parent._receipt(
        {
            "input_page_count": 1,
            "input_content_characters": len(raw_text),
            "input_characters_beyond_parent_prefix": max(
                0, len(raw_text) - PAGE_CHARACTER_CAP
            ),
            "visible_schema_column_count": len(schema),
            "discovered_record_count": counts["discovered_record_count"],
            "discovered_row_key_count": counts["discovered_record_count"],
            "conflicting_coordinate_count": counts[
                "duplicate_or_conflicting_target_count"
            ],
            "admissible_record_count": counts["admissible_record_count"],
            "admissible_bound_observation_count": counts[
                "admissible_bound_observation_count"
            ],
            "retained_record_count": retained,
            "retained_bound_observation_count": target_count if retained else 0,
            "oversized_record_count": 0,
            "compact_prefix_characters": compact_chars if retained else 0,
            "raw_prefix_characters_retained": (
                raw_retained if retained else len(raw_prefix)
            ),
            "output_characters": len(representation),
            "projection_failure_count": counts["projection_failure_count"],
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
        "content_free_receipt": inherited,
        "version_qualified_late_record_receipt": receipt,
        "same_forward_decoded_page_only": True,
        "same_exact_character_budget": len(raw_prefix) == len(representation),
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
        "file_environment_process_network_search_model_or_evaluator_accessed": False,
        "benchmark_or_evaluator_launch_authorized": False,
    }
    value["artifact_payload_sha256"] = projection_parent.payload_sha256(value)
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
    inherited = copied.get("content_free_receipt")
    receipt = copied.get("version_qualified_late_record_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "control_evidence",
        "candidate_evidence",
        "control_evidence_sha256",
        "candidate_evidence_sha256",
        "content_free_receipt",
        "version_qualified_late_record_receipt",
        "same_forward_decoded_page_only",
        "same_exact_character_budget",
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
        or not isinstance(inherited, Mapping)
        or projection_parent.validate_receipt(inherited) != dict(inherited)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or inherited["output_characters"] != len(candidate)
        or receipt["output_characters"] != len(candidate)
        or inherited["visible_schema_column_count"]
        != receipt["visible_schema_column_count"]
        or inherited["discovered_record_count"]
        != receipt["discovered_record_count"]
        or inherited["admissible_record_count"]
        != receipt["admissible_record_count"]
        or inherited["retained_record_count"] != receipt["retained_record_count"]
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
        or seal != projection_parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.60 version-qualified representation drifted")
    if replay and copied != build_representation(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError("V2.50.60 version-qualified representation is not reproducible")
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
