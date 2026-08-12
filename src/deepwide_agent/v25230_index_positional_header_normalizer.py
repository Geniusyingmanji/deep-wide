"""Pure header-totality normalizer for one narrow structural state.

This append-only helper composes two operations already admitted separately by
the frozen V2.42.59 normalizer: dropping one explicitly generic leading index
column and equal-arity positional header replacement.  It accepts only the
new composition, requires exactly one complete candidate, and preserves every
remaining non-empty cell after the frozen parser's outer whitespace trim.

The content-free receipt contains only structural counts.  It never contains
response text, headers, cells, task identity, question, URL, prediction,
semantic hashes, credentials, labels, evaluator metadata, or scores.  This
module is build-only and grants no runtime or benchmark authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24259_deterministic_table_normalizer as parent
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25230_index_positional_header_normalizer_v1"
RECEIPT_ROLE = "v25230_content_free_index_positional_header_receipt"
INTERNAL_PIPE_ENTITY = "&#124;"
MODE = "drop_explicit_generic_index_then_positional_header"
DISPOSITION_NAMES = (
    "accepted",
    "invalid_input_reject",
    "invalid_required_columns_reject",
    "no_pipe_group_reject",
    "no_separator_row_reject",
    "no_generic_leading_index_header_reject",
    "no_positional_after_index_header_reject",
    "separator_width_mismatch_reject",
    "missing_data_rows_reject",
    "malformed_data_width_reject",
    "escaped_pipe_reject",
    "internal_entity_collision_reject",
    "exact_parser_roundtrip_reject",
    "multiple_structural_candidates_reject",
)
COUNT_NAMES = (
    "required_column_count",
    "pipe_group_count",
    "separator_row_count",
    "required_plus_index_header_count",
    "generic_leading_index_header_count",
    "positional_after_index_header_count",
    "separator_width_bound_count",
    "data_bearing_candidate_count",
    "missing_data_candidate_count",
    "malformed_width_candidate_count",
    "escaped_pipe_candidate_count",
    "internal_entity_collision_candidate_count",
    "structurally_safe_candidate_count",
    "exact_parser_roundtrip_candidate_count",
    "exact_parser_roundtrip_data_row_count",
    "exact_parser_roundtrip_filled_empty_cell_count",
    "accepted_data_row_count",
    "filled_empty_cell_count",
)


def _required_columns(columns: object) -> tuple[str, ...] | None:
    if isinstance(columns, (str, bytes)) or not isinstance(columns, Sequence):
        return None
    try:
        required = tuple(
            str(value).strip() for value in columns if str(value).strip()
        )
        normalized = [score._normalize_column(value) for value in required]
    except Exception:
        return None
    if (
        not required
        or len(required) > 20
        or not all(normalized)
        or len(set(normalized)) != len(required)
    ):
        return None
    return required


def _valid_unknown_marker(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    marker = value.strip()
    if (
        not marker
        or "|" in marker
        or "\r" in marker
        or "\n" in marker
        or "\x00" in marker
        or "```" in marker
        or INTERNAL_PIPE_ENTITY in marker
    ):
        return None
    return marker


def _render(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def _receipt(
    *,
    disposition: str,
    counts: Mapping[str, int],
) -> dict[str, Any]:
    dispositions = {
        name: int(name == disposition) for name in DISPOSITION_NAMES
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "mode": MODE,
        **{name: int(counts.get(name, 0)) for name in COUNT_NAMES},
        "disposition_counts": dispositions,
        "accepted": disposition == "accepted",
        "one_generic_leading_index_column_dropped": disposition == "accepted",
        "remaining_header_replaced_positionally": disposition == "accepted",
        "remaining_nonempty_cells_preserved_after_outer_trim": disposition
        == "accepted",
        "missing_data_malformed_width_escaped_pipe_collision_and_ambiguity_fail_closed": True,
        "parent_normalizer_or_observer_modified": False,
        "contains_response_header_cell_question_identity_url_page_prediction_semantic_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "runtime_integration_prediction_change_or_external_launch_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def normalize_index_positional_header_table(
    text: object,
    columns: object,
    *,
    unknown_marker: object,
) -> tuple[str | None, dict[str, Any]]:
    """Return a canonical table only for the exact V2.52.29 safe state."""

    counts = {name: 0 for name in COUNT_NAMES}
    if not isinstance(text, str):
        return None, _receipt(disposition="invalid_input_reject", counts=counts)
    required = _required_columns(columns)
    marker = _valid_unknown_marker(unknown_marker)
    if required is None or marker is None:
        return None, _receipt(
            disposition="invalid_required_columns_reject", counts=counts
        )
    counts["required_column_count"] = len(required)
    try:
        groups = parent._groups(text)
    except Exception:
        return None, _receipt(disposition="invalid_input_reject", counts=counts)
    counts["pipe_group_count"] = len(groups)
    candidates: list[tuple[str, int, int]] = []
    roundtrip_failures = 0
    for group in groups:
        for separator_index, separator in enumerate(group):
            if separator_index < 1 or not parent._is_separator(separator):
                continue
            counts["separator_row_count"] += 1
            header = group[separator_index - 1]
            if len(header) != len(required) + 1:
                continue
            counts["required_plus_index_header_count"] += 1
            first = str(header[0]).strip().casefold()
            if first not in parent.INDEX_HEADERS:
                continue
            counts["generic_leading_index_header_count"] += 1
            plan = parent._header_plan(header[1:], required)
            if plan is None or plan[0] != "positional_header":
                continue
            counts["positional_after_index_header_count"] += 1
            if len(separator) != len(header):
                continue
            counts["separator_width_bound_count"] += 1
            source_rows = [
                row
                for row in group[separator_index + 1 :]
                if not parent._is_separator(row)
            ]
            if not source_rows:
                counts["missing_data_candidate_count"] += 1
                continue
            counts["data_bearing_candidate_count"] += 1
            if any(len(row) != len(header) for row in source_rows):
                counts["malformed_width_candidate_count"] += 1
                continue
            remaining = [
                [str(value).strip() for value in row[1:]] for row in source_rows
            ]
            if any("\\|" in value for row in remaining for value in row):
                counts["escaped_pipe_candidate_count"] += 1
                continue
            if any(
                INTERNAL_PIPE_ENTITY in value for row in remaining for value in row
            ):
                counts["internal_entity_collision_candidate_count"] += 1
                continue
            filled = sum(not value for row in remaining for value in row)
            normalized_rows = [
                [value or marker for value in row] for row in remaining
            ]
            counts["structurally_safe_candidate_count"] += 1
            canonical = _render(required, normalized_rows)
            checked, _errors = score.extract_valid_markdown_table(
                canonical, required
            )
            if checked != canonical:
                roundtrip_failures += 1
                continue
            counts["exact_parser_roundtrip_candidate_count"] += 1
            counts["exact_parser_roundtrip_data_row_count"] += len(
                normalized_rows
            )
            counts["exact_parser_roundtrip_filled_empty_cell_count"] += filled
            candidates.append((canonical, len(normalized_rows), filled))

    if len(candidates) == 1:
        canonical, rows, filled = candidates[0]
        counts["accepted_data_row_count"] = rows
        counts["filled_empty_cell_count"] = filled
        return canonical, _receipt(disposition="accepted", counts=counts)
    if len(candidates) > 1:
        disposition = "multiple_structural_candidates_reject"
    elif roundtrip_failures:
        disposition = "exact_parser_roundtrip_reject"
    elif counts["internal_entity_collision_candidate_count"]:
        disposition = "internal_entity_collision_reject"
    elif counts["escaped_pipe_candidate_count"]:
        disposition = "escaped_pipe_reject"
    elif counts["malformed_width_candidate_count"]:
        disposition = "malformed_data_width_reject"
    elif counts["missing_data_candidate_count"]:
        disposition = "missing_data_rows_reject"
    elif counts["positional_after_index_header_count"] and not counts[
        "separator_width_bound_count"
    ]:
        disposition = "separator_width_mismatch_reject"
    elif counts["pipe_group_count"] == 0:
        disposition = "no_pipe_group_reject"
    elif counts["separator_row_count"] == 0:
        disposition = "no_separator_row_reject"
    elif counts["generic_leading_index_header_count"] == 0:
        disposition = "no_generic_leading_index_header_reject"
    elif counts["positional_after_index_header_count"] == 0:
        disposition = "no_positional_after_index_header_reject"
    else:
        disposition = "no_positional_after_index_header_reject"
    return None, _receipt(disposition=disposition, counts=counts)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    dispositions = copied.get("disposition_counts")
    active = (
        {name for name, count in dispositions.items() if count == 1}
        if isinstance(dispositions, Mapping)
        else set()
    )
    accepted = active == {"accepted"}
    accepted_flags = (
        "accepted",
        "one_generic_leading_index_column_dropped",
        "remaining_header_replaced_positionally",
        "remaining_nonempty_cells_preserved_after_outer_trim",
    )
    true_flags = (
        "missing_data_malformed_width_escaped_pipe_collision_and_ambiguity_fail_closed",
    )
    false_flags = (
        "parent_normalizer_or_observer_modified",
        "contains_response_header_cell_question_identity_url_page_prediction_semantic_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_or_information_gain_assigns_signed_credit",
        "runtime_integration_prediction_change_or_external_launch_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "mode",
        *COUNT_NAMES,
        "disposition_counts",
        *accepted_flags,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("mode") != MODE
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in COUNT_NAMES
        )
        or not isinstance(dispositions, Mapping)
        or set(dispositions) != set(DISPOSITION_NAMES)
        or any(
            isinstance(count, bool)
            or not isinstance(count, int)
            or count not in {0, 1}
            for count in dispositions.values()
        )
        or sum(dispositions.values()) != 1
        or any(not isinstance(copied.get(name), bool) for name in (*accepted_flags, *true_flags, *false_flags))
        or any(copied[name] is not accepted for name in accepted_flags)
        or accepted
        and (
            copied["structurally_safe_candidate_count"] != 1
            or copied["exact_parser_roundtrip_candidate_count"] != 1
            or copied["accepted_data_row_count"] <= 0
            or copied["accepted_data_row_count"]
            != copied["exact_parser_roundtrip_data_row_count"]
            or copied["filled_empty_cell_count"]
            != copied["exact_parser_roundtrip_filled_empty_cell_count"]
        )
        or not accepted
        and (
            copied["accepted_data_row_count"] != 0
            or copied["filled_empty_cell_count"] != 0
        )
        or active == {"multiple_structural_candidates_reject"}
        and copied["exact_parser_roundtrip_candidate_count"] <= 1
        or active == {"missing_data_rows_reject"}
        and copied["missing_data_candidate_count"] == 0
        or active == {"malformed_data_width_reject"}
        and copied["malformed_width_candidate_count"] == 0
        or active == {"escaped_pipe_reject"}
        and copied["escaped_pipe_candidate_count"] == 0
        or active == {"internal_entity_collision_reject"}
        and copied["internal_entity_collision_candidate_count"] == 0
        or active == {"exact_parser_roundtrip_reject"}
        and copied["structurally_safe_candidate_count"]
        <= copied["exact_parser_roundtrip_candidate_count"]
        or active == {"no_pipe_group_reject"}
        and copied["pipe_group_count"] != 0
        or active == {"no_separator_row_reject"}
        and copied["separator_row_count"] != 0
        or active == {"no_generic_leading_index_header_reject"}
        and copied["generic_leading_index_header_count"] != 0
        or active == {"no_positional_after_index_header_reject"}
        and copied["positional_after_index_header_count"] != 0
        or active == {"separator_width_mismatch_reject"}
        and copied["separator_width_bound_count"] != 0
        or copied["exact_parser_roundtrip_candidate_count"]
        > copied["structurally_safe_candidate_count"]
        or copied["generic_leading_index_header_count"]
        > copied["required_plus_index_header_count"]
        or copied["positional_after_index_header_count"]
        > copied["generic_leading_index_header_count"]
        or copied["separator_width_bound_count"]
        > copied["positional_after_index_header_count"]
        or copied["missing_data_candidate_count"]
        + copied["data_bearing_candidate_count"]
        != copied["separator_width_bound_count"]
        or copied["malformed_width_candidate_count"]
        + copied["escaped_pipe_candidate_count"]
        + copied["internal_entity_collision_candidate_count"]
        + copied["structurally_safe_candidate_count"]
        != copied["data_bearing_candidate_count"]
        or copied["exact_parser_roundtrip_data_row_count"]
        < copied["exact_parser_roundtrip_candidate_count"]
        or copied["exact_parser_roundtrip_filled_empty_cell_count"]
        > copied["exact_parser_roundtrip_data_row_count"]
        * copied["required_column_count"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.30 header-totality receipt drifted")
    return copied


__all__ = [
    "COUNT_NAMES",
    "DISPOSITION_NAMES",
    "MODE",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "normalize_index_positional_header_table",
    "validate_receipt",
]
