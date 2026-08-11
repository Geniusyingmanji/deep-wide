"""Pure consensus-bound late-record representation.

V2.50.57 observed zero natural exposure from the stricter V2.50.49 identity
surface, while V2.50.53 showed that changing evidence on short pages where the
same fields were already visible in the inherited prefix did not change any
prediction.  This append-only successor addresses both failure boundaries.

One row identity may be discovered from an already-fetched page when exactly
one normalized public URL component is also an exact segment of both the HTML
title and the leading decoded page surface.  The older explicit row-label
binding remains an allowed route.  Every visible target field must still have
one safe value under an exact same-page label, and at least one complete target
observation must start beyond the inherited 5,000-character prefix.  Otherwise
the parent prefix is returned byte-for-byte.

The module consumes only a visible question and one caller-supplied page.  It
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

from . import v24980_late_page_bound_projection as projection_parent
from . import v25004_identity_bound_detail_fields as detail
from . import v25049_page_self_identified_record as parent


POLICY_ID = "v25059_consensus_bound_late_record_representation_v1"
ROLE = "v25059_consensus_bound_late_record_representation"
RECEIPT_ROLE = "v25059_content_free_consensus_bound_late_record_receipt"
PAGE_CHARACTER_CAP = parent.PAGE_CHARACTER_CAP
MAXIMUM_INPUT_PAGE_CHARACTERS = parent.MAXIMUM_INPUT_PAGE_CHARACTERS
MAXIMUM_LEADING_LINES = 12
_TITLE_SEPARATOR = re.compile(r"\s+(?:\||·|–|—|-)\s+|:\s+")
_PIPE_FIELD = re.compile(
    r"^(?P<label>[^|\r\n]{1,240}?)\s*:?[ \t]*\|[ \t]*"
    r"(?P<value>[^|\r\n]+?)\s*$"
)
_COLON_FIELD = re.compile(
    r"^(?P<label>[^|:\r\n]{1,240}?)\s*:\s+(?P<value>[^|\r\n]+?)\s*$"
)
_GENERIC_IDENTITY_SEGMENTS = frozenset(
    {
        "about",
        "details",
        "detail",
        "docs",
        "documentation",
        "download",
        "home",
        "html",
        "index",
        "latest",
        "official",
        "overview",
        "package",
        "packages",
        "project",
        "projects",
        "readme",
        "release",
        "releases",
        "search",
        "site",
        "web",
        "www",
    }
)
_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_schema_column_count",
    "visible_target_field_count",
    "labelled_identity_binding_count",
    "url_identity_candidate_count",
    "title_segment_identity_candidate_count",
    "leading_segment_identity_candidate_count",
    "consensus_identity_binding_count",
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


def _normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _identity_candidate(value: object) -> str | None:
    safe = parent._safe_identity(value)
    if safe is None:
        return None
    key = parent._identity_key(safe)
    tokens = tuple(key.split())
    if (
        key in _GENERIC_IDENTITY_SEGMENTS
        or tokens and all(token in _GENERIC_IDENTITY_SEGMENTS for token in tokens)
        or len(key) < 2
        or key.isdecimal()
        or re.fullmatch(r"v?\d+(?:[._-]\d+)+", key, re.IGNORECASE) is not None
    ):
        return None
    return safe


def _surface_segments(value: object) -> dict[str, str]:
    """Return exact safe title/heading segments without token containment."""

    text = _normalize(value).strip("#*_=~ \t\r\n")
    if not text:
        return {}
    raw_segments = _TITLE_SEPARATOR.split(text)
    output: dict[str, str] = {}
    for raw in raw_segments:
        candidate = _identity_candidate(raw.strip("#*_=~ [](){}"))
        if candidate is None:
            continue
        key = parent._identity_key(candidate)
        output.setdefault(key, candidate)
    return output


def _url_candidates(url: str) -> dict[str, str]:
    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return {}
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return {}
    # Query values often echo a search term and do not identify the page's
    # primary record.  Only public path components may enter identity consensus.
    raw_values = [unquote(part) for part in parsed.path.split("/") if part]
    output: dict[str, str] = {}
    for raw in raw_values:
        stem = re.sub(
            r"\.(?:html?|json|xml|txt|php|aspx?)$",
            "",
            raw,
            flags=re.IGNORECASE,
        )
        candidate = _identity_candidate(stem)
        if candidate is None:
            continue
        key = parent._identity_key(candidate)
        output.setdefault(key, candidate)
    return output


def _consensus_identity(
    *, title: str, text: str, url: str
) -> tuple[str | None, dict[str, int]]:
    urls = _url_candidates(url)
    titles = _surface_segments(title)
    leading: dict[str, str] = {}
    lines = [line for line in str(text).splitlines() if _normalize(line)]
    title_echo_excluded = False
    content_lines: list[str] = []
    for line in lines:
        if not title_echo_excluded and _normalize(line) == _normalize(title):
            # ``html_to_document`` includes the HTML <title> in decoded text.
            # Exclude one exact echo so title and body heading are not counted
            # as two independent surfaces when only one source node exists.
            title_echo_excluded = True
            continue
        content_lines.append(line)
    for line in content_lines[:MAXIMUM_LEADING_LINES]:
        for key, value in _surface_segments(line).items():
            leading.setdefault(key, value)
    joint = sorted(set(urls) & set(titles) & set(leading))
    identity = titles[joint[0]] if len(joint) == 1 else None
    return identity, {
        "url_identity_candidate_count": len(urls),
        "title_segment_identity_candidate_count": len(titles),
        "leading_segment_identity_candidate_count": len(leading),
        "consensus_identity_binding_count": len(joint),
    }


def _line_vector(text: str) -> list[tuple[int, str]]:
    output: list[tuple[int, str]] = []
    offset = 0
    for raw in str(text).splitlines(keepends=True):
        output.append((offset, _normalize(raw)))
        offset += len(raw)
    if not output and text:
        output.append((0, _normalize(text)))
    return output


def _field_map_with_positions(
    text: str, targets: Sequence[str]
) -> tuple[dict[str, str], dict[str, int], int, int]:
    """Bind exact target labels and retain conservative observation offsets."""

    aliases = {detail._canonical(target): str(target) for target in targets}
    if len(aliases) != len(targets):
        return {}, {}, 0, len(targets)
    values: dict[str, list[tuple[str, int]]] = {key: [] for key in aliases}
    lines = _line_vector(text)
    target_candidates = 0

    def safe_field(raw: object) -> str | None:
        safe = detail._safe_surface(
            raw, maximum=detail.MAXIMUM_FIELD_VALUE_CHARACTERS
        )
        return safe if safe is not None and "|" not in safe else None

    for index, (offset, line) in enumerate(lines):
        if not line:
            continue
        direct = _PIPE_FIELD.fullmatch(line) or _COLON_FIELD.fullmatch(line)
        if direct is not None:
            key = detail._canonical(direct.group("label"))
            if key not in aliases:
                continue
            target_candidates += 1
            safe = safe_field(direct.group("value"))
            if safe is not None and detail._canonical(safe) not in aliases:
                values[key].append((safe, offset))
            continue
        key = detail._canonical(line)
        if key not in aliases:
            for alias, display in aliases.items():
                label_pattern = re.escape(_normalize(display)).replace(
                    r"\ ", r"\s+"
                )
                sentence = re.fullmatch(
                    rf"{label_pattern}\s+(?P<value>.+?)\.", line, re.IGNORECASE
                )
                if sentence is None:
                    continue
                target_candidates += 1
                safe = safe_field(sentence.group("value"))
                if safe is not None:
                    values[alias].append((safe, offset))
                break
            continue
        target_candidates += 1
        following = next(
            (
                (next_offset, next_line)
                for next_offset, next_line in lines[index + 1 :]
                if next_line
            ),
            None,
        )
        if following is None:
            continue
        next_offset, next_line = following
        safe = safe_field(next_line)
        if safe is not None and detail._canonical(safe) not in aliases:
            values[key].append((safe, next_offset))
    conflicts = sum(
        len(items) != 1
        or len({detail._canonical(value) for value, _offset in items}) != 1
        for items in values.values()
    )
    fields = {
        aliases[key]: items[0][0]
        for key, items in values.items()
        if len(items) == 1
    }
    positions = {
        aliases[key]: items[0][1]
        for key, items in values.items()
        if len(items) == 1
    }
    return fields, positions, target_candidates, conflicts


def _bound_record(
    question: str, page: Mapping[str, Any]
) -> tuple[dict[str, str] | None, dict[str, int], dict[str, str], str]:
    normalized_page, raw_text = detail._page(page)
    schema = detail._schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    labelled_identity = None
    labelled_count = 0
    consensus_identity = None
    consensus_counts = {
        "url_identity_candidate_count": 0,
        "title_segment_identity_candidate_count": 0,
        "leading_segment_identity_candidate_count": 0,
        "consensus_identity_binding_count": 0,
    }
    fields: dict[str, str] = {}
    positions: dict[str, int] = {}
    target_candidates = conflicts = failure = 0
    try:
        if len(schema) >= 2:
            labelled_identity, labelled = parent._bound_identity(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
                row_label=schema[0],
            )
            labelled_count = int(
                labelled_identity is not None
                and labelled["jointly_bound_identity_count"] == 1
            )
            consensus_identity, consensus_counts = _consensus_identity(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
            )
            fields, positions, target_candidates, conflicts = (
                _field_map_with_positions(raw_text, targets)
            )
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        labelled_identity = consensus_identity = None
        labelled_count = 0
        consensus_counts = {name: 0 for name in consensus_counts}
        fields = {}
        positions = {}
        target_candidates = conflicts = 0

    identities: dict[str, str] = {}
    for identity in (labelled_identity, consensus_identity):
        if identity is not None:
            identities.setdefault(parent._identity_key(identity), identity)
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
        **consensus_counts,
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
        "identity_discovered_only_from_same_page_url_title_and_leading_surface": True,
        "explicit_labelled_identity_route_preserved": True,
        "unlabelled_identity_requires_exact_three_surface_consensus": True,
        "one_exact_decoder_title_echo_excluded_from_leading_surface": True,
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
        "identity_discovered_only_from_same_page_url_title_and_leading_surface",
        "explicit_labelled_identity_route_preserved",
        "unlabelled_identity_requires_exact_three_surface_consensus",
        "one_exact_decoder_title_echo_excluded_from_leading_surface",
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
        or copied["consensus_identity_binding_count"]
        > min(
            copied["url_identity_candidate_count"],
            copied["title_segment_identity_candidate_count"],
            copied["leading_segment_identity_candidate_count"],
        )
        or copied["unique_bound_identity_count"] > 2
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
        raise ValueError("V2.50.59 consensus late-record receipt drifted")
    return copied


def extract_record(question: str, page: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.59 visible question is absent")
    record, _counts, _normalized, _text = _bound_record(question, page)
    if record is None:
        raise ValueError("V2.50.59 consensus late record is not admissible")
    return record


def build_representation(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.59 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.50.59 parent page cap drifted")
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
                "[CONSENSUS-BOUND LATE SOURCE RECORD]",
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
                "[/CONSENSUS-BOUND LATE SOURCE RECORD]",
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
    inherited_receipt = projection_parent._receipt(
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
        "content_free_receipt": inherited_receipt,
        "consensus_late_record_receipt": receipt,
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
    receipt = copied.get("consensus_late_record_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "control_evidence",
        "candidate_evidence",
        "control_evidence_sha256",
        "candidate_evidence_sha256",
        "content_free_receipt",
        "consensus_late_record_receipt",
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
        raise ValueError("V2.50.59 consensus late-record representation drifted")
    if replay and copied != build_representation(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError(
            "V2.50.59 consensus late-record representation is not reproducible"
        )
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
