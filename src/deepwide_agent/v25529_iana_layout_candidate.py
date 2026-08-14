"""Pure IANA delegation-layout candidate for one selected multirow table.

The independent V2.55.28 snapshot showed that production HTML extraction
does not render IANA detail records as ``TLD Type | value`` and ``TLD Manager
| value``.  It renders a unique identity-bound sequence instead::

    Delegation Record for .ROW
    (Generic top-level domain)
    Sponsoring Organisation
    Registry Name

This successor retains every V2.55.20 URL, row, page-surface, quote,
coordinate, materiality, list, and table-shape guard.  It adds only the
source-specific grammar above: the parenthetical delegation kind maps to the
exact visible ``Type`` column, and the exact ``Sponsoring Organisation``
field maps to the exact visible ``TLD Manager`` column.  The heading, source
surfaces, and bounded adjacent value must occur in the delegation header
before ``Administrative Contact``.  Duplicate or conflicting coordinates
still fail closed.

This module performs no I/O and reads no benchmark label, truth, evaluator,
score, credential, or historical outcome.  Entropy/information gain assigns
zero signed credit and this build authorizes no launch.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25432_source_authoritative_field_candidate as source
from . import v25464_row_key_bound_structured_source_candidate as row_bound
from . import v25483_row_key_iana_detail_candidate as grammar
from . import v25520_multirow_iana_detail_candidate as parent


POLICY_ID = "v25529_iana_delegation_layout_candidate_v1"
ROLE = "v25529_iana_delegation_layout_candidate"
RECEIPT_ROLE = "v25529_content_free_iana_delegation_layout_receipt"
MAXIMUM_DIRECT_PAGES = parent.MAXIMUM_DIRECT_PAGES
PAGE_KEYS = parent.PAGE_KEYS
_TYPE = re.compile(
    r"\((?P<value>[A-Za-z][A-Za-z-]*(?: [A-Za-z][A-Za-z-]*){0,5}) top-level domain\)",
    re.ASCII,
)
_LAYOUT_COUNT_FIELDS = (
    "iana_delegation_heading_surface_count",
    "iana_parenthetical_type_surface_count",
    "iana_sponsoring_organisation_surface_count",
    "iana_layout_complete_page_count",
)
_COUNT_FIELDS = tuple(parent._COUNT_FIELDS) + _LAYOUT_COUNT_FIELDS
payload_sha256 = source.payload_sha256


def _column(
    columns: Sequence[str], expected: str
) -> tuple[int, str] | None:
    matches = [
        (index, str(value))
        for index, value in enumerate(columns)
        if source._column_key(value) == source._column_key(expected)
    ]
    return matches[0] if len(matches) == 1 and matches[0][0] > 0 else None


def _layout_observations(
    page: Mapping[str, str],
    *,
    rows: Sequence[Sequence[str]],
    row_index: int,
    columns: Sequence[str],
    counts: Counter[str],
) -> list[dict[str, Any]]:
    lines = source._line_spans(str(page["content"]))
    row_identity = str(rows[row_index][0])
    expected_heading = source._key(f"Delegation Record for {row_identity}")
    headings = [
        index
        for index, (_start, _end, line) in enumerate(lines)
        if source._key(grammar._clean_label(line)) == expected_heading
    ]
    counts["iana_delegation_heading_surface_count"] += len(headings)
    if len(headings) != 1:
        return []
    heading = headings[0]
    boundaries = [
        index
        for index in range(heading + 1, len(lines))
        if source._key(grammar._clean_label(lines[index][2]))
        == "administrative contact"
    ]
    if len(boundaries) != 1:
        return []
    stop = boundaries[0]
    if stop <= heading + 1 or stop > heading + 16:
        return []

    type_column = _column(columns, "Type")
    manager_column = _column(columns, "TLD Manager")
    type_rows: list[tuple[int, re.Match[str]]] = []
    manager_rows: list[int] = []
    for index in range(heading + 1, stop):
        clean = grammar._clean_label(lines[index][2])
        matched = _TYPE.fullmatch(clean)
        if matched is not None:
            type_rows.append((index, matched))
        if source._key(clean) == "sponsoring organisation":
            manager_rows.append(index)
    counts["iana_parenthetical_type_surface_count"] += len(type_rows)
    counts["iana_sponsoring_organisation_surface_count"] += len(manager_rows)
    if (
        len(type_rows) != 1
        or len(manager_rows) != 1
        or type_rows[0][0] >= manager_rows[0]
    ):
        return []

    output: list[dict[str, Any]] = []
    if type_column is not None:
        column_index, field = type_column
        for index, matched in type_rows:
            start, end, line = lines[index]
            parent._offer(
                output,
                counts,
                page=page,
                rows=rows,
                row_index=row_index,
                column_index=column_index,
                field=field,
                grammar="iana_delegation_parenthetical_type",
                source_field=line.strip(),
                source_value=matched.group("value"),
                quote_start=start,
                quote_end=end,
                source_kind="iana_delegation_parenthetical_type",
            )

    manager_value_count = 0
    if manager_column is not None:
        column_index, field = manager_column
        for index in manager_rows:
            following = next(
                (
                    (cursor, lines[cursor])
                    for cursor in range(index + 1, min(stop, index + 4))
                    if lines[cursor][2].strip()
                ),
                None,
            )
            if following is None:
                counts["raw_field_surface_count"] += 1
                counts["missing_or_next_field_rejected_surface_count"] += 1
                continue
            cursor, (_value_start, value_end, value_line) = following
            if (
                any(lines[position][2].strip() for position in range(index + 1, cursor))
                or source._key(grammar._clean_label(value_line))
                in {
                    "administrative contact",
                    "technical contact",
                    "name servers",
                    "registry information",
                }
            ):
                counts["raw_field_surface_count"] += 1
                counts["missing_or_next_field_rejected_surface_count"] += 1
                continue
            start, _end, source_line = lines[index]
            before = len(output)
            parent._offer(
                output,
                counts,
                page=page,
                rows=rows,
                row_index=row_index,
                column_index=column_index,
                field=field,
                grammar="iana_sponsoring_organisation_alias",
                source_field=source_line.strip(),
                source_value=value_line.strip(),
                quote_start=start,
                quote_end=value_end,
                source_kind="iana_sponsoring_organisation_bounded_value",
            )
            manager_value_count += int(len(output) > before)

    complete = (
        len(type_rows) == 1
        and len(manager_rows) == 1
        and manager_value_count == 1
        and type_column is not None
        and manager_column is not None
        and len(output) == 2
        and len(
            {
                (int(value["row_index"]), int(value["column_index"]))
                for value in output
            }
        )
        == 2
    )
    counts["iana_layout_complete_page_count"] += int(complete)
    return output if complete else []


def _observations(
    page: Mapping[str, str],
    *,
    rows: Sequence[Sequence[str]],
    row_index: int,
    columns: Sequence[str],
    counts: Counter[str],
) -> list[dict[str, Any]]:
    generic = parent._observations(
        page,
        rows=rows,
        row_index=row_index,
        columns=columns,
        counts=counts,
    )
    layout = _layout_observations(
        page,
        rows=rows,
        row_index=row_index,
        columns=columns,
        counts=counts,
    )
    return [*generic, *layout]


def _receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "selected_page_url_not_synthesized_or_discovered_here": True,
        "exact_https_iana_host_arbitrary_tld_path_visible_row_and_page_surface_required": True,
        "generic_exact_mechanical_labels_and_strict_iana_delegation_layout_supported": True,
        "iana_type_maps_only_to_exact_type_column": True,
        "iana_sponsoring_organisation_maps_only_to_exact_tld_manager_column": True,
        "delegation_heading_type_manager_and_value_are_pre_administrative_contact": True,
        "source_value_is_exact_same_line_or_bounded_adjacent_text": True,
        "duplicate_conflict_unknown_surface_equivalent_list_collapse_or_shape_change_fails_closed": True,
        "content_free_stage_counters_separate_layout_parser_observation_rejection_and_materiality": True,
        "contains_question_url_title_page_quote_identity_field_value_prediction_answer_hash_or_credential": False,
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
        "selected_page_url_not_synthesized_or_discovered_here",
        "exact_https_iana_host_arbitrary_tld_path_visible_row_and_page_surface_required",
        "generic_exact_mechanical_labels_and_strict_iana_delegation_layout_supported",
        "iana_type_maps_only_to_exact_type_column",
        "iana_sponsoring_organisation_maps_only_to_exact_tld_manager_column",
        "delegation_heading_type_manager_and_value_are_pre_administrative_contact",
        "source_value_is_exact_same_line_or_bounded_adjacent_text",
        "duplicate_conflict_unknown_surface_equivalent_list_collapse_or_shape_change_fails_closed",
        "content_free_stage_counters_separate_layout_parser_observation_rejection_and_materiality",
    )
    false_flags = (
        "contains_question_url_title_page_quote_identity_field_value_prediction_answer_hash_or_credential",
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
    parser_rejections = sum(
        copied.get(name, 0)
        for name in (
            "unsafe_value_rejected_surface_count",
            "nonunique_or_unbound_quote_rejected_surface_count",
            "missing_or_next_field_rejected_surface_count",
        )
    )
    coordinate_rejections = sum(
        copied.get(name, 0)
        for name in (
            "ambiguous_same_value_coordinate_count",
            "conflicting_value_coordinate_count",
            "unchanged_coordinate_count",
            "surface_equivalent_rejected_coordinate_count",
            "list_collapse_rejected_coordinate_count",
        )
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
        or not 1 <= copied["base_row_count"] <= 64
        or not 2 <= copied["visible_column_count"] <= 32
        or copied["provided_page_count"] not in {0, 1}
        or copied["exact_iana_url_page_count"] > copied["provided_page_count"]
        or copied["url_row_key_bound_page_count"]
        > copied["exact_iana_url_page_count"]
        or copied["identity_surface_bound_page_count"]
        > copied["url_row_key_bound_page_count"]
        or copied["iana_layout_complete_page_count"]
        > copied["identity_surface_bound_page_count"]
        or copied["raw_field_surface_count"]
        != copied["evidence_closed_observation_count"] + parser_rejections
        or copied["coordinate_group_count"]
        != copied["available_candidate_count"] + coordinate_rejections
        or copied["available_candidate_count"]
        != copied["applied_coordinate_count"]
        or copied["available_candidate_count"]
        > copied["visible_column_count"] - 1
        or copied["positive_signed_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.29 receipt drifted")
    return copied


def _construct(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("V2.55.29 page vector is not a sequence")
    if len(pages) > MAXIMUM_DIRECT_PAGES:
        raise ValueError("V2.55.29 accepts at most one selected detail page")
    required, rows, row_map = parent._table(str(base_prediction), columns)
    counts: Counter[str] = Counter(
        base_row_count=len(rows),
        visible_column_count=len(required),
        provided_page_count=len(pages),
    )
    bound = (
        parent._bound_page(pages[0], rows=rows, row_map=row_map, counts=counts)
        if pages
        else None
    )
    observations = (
        _observations(
            bound[0],
            rows=rows,
            row_index=bound[1],
            columns=required,
            counts=counts,
        )
        if bound is not None
        else []
    )
    grouped: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        grouped[
            (int(observation["row_index"]), int(observation["column_index"]))
        ].append(observation)
    counts["coordinate_group_count"] = len(grouped)
    retained: list[dict[str, Any]] = []
    for coordinate in sorted(grouped):
        values = grouped[coordinate]
        normalized = {source._key(value["exact_value"]) for value in values}
        if len(values) != 1:
            counts[
                "conflicting_value_coordinate_count"
                if len(normalized) > 1
                else "ambiguous_same_value_coordinate_count"
            ] += 1
            continue
        observation = values[0]
        if source._key(observation["old_value"]) == source._key(
            observation["exact_value"]
        ):
            counts["unchanged_coordinate_count"] += 1
            continue
        if row_bound._surface_equivalent(
            observation["field"],
            observation["old_value"],
            observation["exact_value"],
        ):
            counts["surface_equivalent_rejected_coordinate_count"] += 1
            continue
        if (
            source._column_key(observation["field"]) in source.LIST_COLUMN_KEYS
            and source._list_cardinality(observation["old_value"]) >= 2
            and source._list_cardinality(observation["exact_value"])
            < source._list_cardinality(observation["old_value"])
        ):
            counts["list_collapse_rejected_coordinate_count"] += 1
            continue
        retained.append(observation)

    edited = copy.deepcopy(rows)
    for observation in retained:
        edited[int(observation["row_index"])][
            int(observation["column_index"])
        ] = str(observation["exact_value"])
    candidate = source.table_parent._render_table(required, edited)
    counts["available_candidate_count"] = len(retained)
    counts["applied_coordinate_count"] = len(retained)
    counts["positive_signed_credit_count"] = 0
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "base_prediction": str(base_prediction),
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode()
        ).hexdigest(),
        "candidate_prediction": candidate,
        "candidate_prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "candidate_prediction_changed": bool(retained),
        "columns": list(required),
        "private_bound_row_identity": (
            str(rows[bound[1]][0]) if bound is not None else None
        ),
        "private_pages": copy.deepcopy(list(pages)),
        "private_observations": copy.deepcopy(retained),
        "content_free_receipt": _receipt(counts),
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return value


def build_candidate(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return validate_candidate(
        _construct(str(base_prediction), columns=columns, pages=pages)
    )


def validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "base_prediction",
        "base_prediction_sha256",
        "candidate_prediction",
        "candidate_prediction_sha256",
        "candidate_prediction_changed",
        "columns",
        "private_bound_row_identity",
        "private_pages",
        "private_observations",
        "content_free_receipt",
        "artifact_payload_sha256",
    }
    base = copied.get("base_prediction")
    columns = copied.get("columns")
    pages = copied.get("private_pages")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(base, str)
        or not isinstance(columns, list)
        or not isinstance(pages, list)
        or not isinstance(copied.get("private_observations"), list)
        or not isinstance(copied.get("content_free_receipt"), Mapping)
        or validate_receipt(copied["content_free_receipt"])
        != copied["content_free_receipt"]
        or copied.get("base_prediction_sha256")
        != hashlib.sha256(base.encode()).hexdigest()
        or not isinstance(copied.get("candidate_prediction"), str)
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(copied["candidate_prediction"].encode()).hexdigest()
        or copied.get("candidate_prediction_changed")
        is not (copied["candidate_prediction"] != base)
        or copied.get("candidate_prediction_changed")
        is not (copied["content_free_receipt"]["applied_coordinate_count"] > 0)
        or copied.get("artifact_payload_sha256")
        != payload_sha256(
            {
                name: copy.deepcopy(item)
                for name, item in copied.items()
                if name != "artifact_payload_sha256"
            }
        )
    ):
        raise ValueError("V2.55.29 candidate drifted")
    if _construct(base, columns=columns, pages=pages) != copied:
        raise ValueError("V2.55.29 candidate replay drifted")
    return copied


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "validated_parent_policy_id": parent.POLICY_ID,
        "input_is_one_already_selected_exact_detail_page": True,
        "multirow_arbitrary_length_tld_binding": True,
        "supported_generic_source_shapes": parent.integration_contract()[
            "supported_source_shapes"
        ],
        "supported_iana_layout": [
            "unique_delegation_record_heading",
            "parenthetical_top_level_domain_type",
            "sponsoring_organisation_bounded_adjacent_value",
        ],
        "source_specific_column_mapping": {
            "parenthetical_delegation_type": "Type",
            "Sponsoring Organisation": "TLD Manager",
        },
        "additional_provider_effects": 0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "PAGE_KEYS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_candidate",
    "integration_contract",
    "validate_candidate",
    "validate_receipt",
]
