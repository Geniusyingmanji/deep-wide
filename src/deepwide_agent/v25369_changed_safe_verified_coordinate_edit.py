"""Deterministic changed-safe edits from quote-verified source coordinates.

V2.53.67 compared two independent syntheses and therefore could not separate
raw-page redundancy from model insensitivity.  This pure successor accepts one
already-produced base table and the V2.53.60 same-forward quote-verifier state.
It returns the base table as control and edits the candidate only when all of
the following are true:

* the base table is already in the exact canonical Markdown form;
* one verified source field maps to exactly one requested non-key column;
* its row identity maps to exactly one base-table row;
* no second verified source coordinate targets that table coordinate; and
* the verified value is safe, non-unknown, and materially differs from the
  base cell.

Missing or duplicate rows, missing columns, cross-coordinate duplication or
conflict, unsafe/unknown values, and noncanonical tables are byte-exact no-ops.
When an edit is admitted, schema, row count/order, row keys, and every other
cell are preserved.  The module has no file, environment, process, network,
model, search, fetch, evaluator, benchmark-label, mapping, gold, score,
reward, credential, or historical-result capability.  Entropy/information
gain assigns no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25065_quote_verified_record_binding as quote_parent
from . import v25360_quote_coordinate_partial_field_record as verifier
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25369_changed_safe_verified_coordinate_edit_v1"
ROLE = "v25369_changed_safe_verified_coordinate_edit_result"
RECEIPT_ROLE = "v25369_content_free_changed_safe_verified_coordinate_edit_receipt"
MAXIMUM_COLUMNS = 20

_COUNT_FIELDS = (
    "parsed_record_count",
    "parsed_field_count",
    "verified_record_count",
    "verified_field_count",
    "verified_table_coordinate_count",
    "changed_safe_coordinate_count",
    "unchanged_verified_coordinate_count",
    "table_or_schema_rejected_field_count",
    "missing_row_rejected_field_count",
    "ambiguous_row_rejected_field_count",
    "missing_or_key_column_rejected_field_count",
    "multiple_source_coordinate_rejected_field_count",
    "conflicting_source_coordinate_rejected_field_count",
    "unsafe_or_unknown_value_rejected_field_count",
    "positive_signed_credit_count",
)
_DYNAMIC_FLAGS = (
    "model_call_attempted",
    "record_output_strictly_valid",
    "base_table_exact_canonical",
    "candidate_prediction_changed",
    "candidate_identity_handoff",
)
_TRUE_FLAGS = (
    "v25360_page_quote_row_and_field_verifier_replayed",
    "one_shared_base_synthesis_is_control",
    "candidate_is_only_a_deterministic_verified_coordinate_edit",
    "unique_base_row_and_exact_requested_non_key_column_required",
    "one_source_coordinate_per_table_coordinate_required",
    "verified_value_must_materially_differ_from_base_cell",
    "unknown_unsafe_conflicting_missing_or_ambiguous_coordinate_is_noop",
    "schema_row_count_row_order_row_keys_and_other_cells_preserved",
    "zero_admission_returns_base_prediction_byte_exact",
    "same_forward_fetched_pages_only",
)
_FALSE_FLAGS = (
    "additional_model_search_fetch_token_context_wall_or_network_budget",
    "contains_question_query_url_title_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    "entropy_or_information_gain_assigns_signed_credit",
    "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
    "benchmark_launch_or_evaluator_authorized",
)


def _safe_columns(columns: Sequence[str]) -> tuple[str, ...]:
    if isinstance(columns, (str, bytes)) or not 2 <= len(columns) <= MAXIMUM_COLUMNS:
        raise ValueError("V2.53.69 requested column vector drifted")
    output = tuple(str(value).strip() for value in columns)
    keys = tuple(quote_parent._key(value) for value in output)
    if (
        any(not value or "|" in value or "\x00" in value for value in output)
        or any(not key for key in keys)
        or len(set(keys)) != len(keys)
    ):
        raise ValueError("V2.53.69 requested columns are unsafe or ambiguous")
    return output


def _safe_value(value: object) -> str | None:
    text = " ".join(str(value or "").split())
    if (
        not text
        or len(text) > quote_parent.MAXIMUM_VALUE_CHARACTERS
        or any(character in text for character in "|\x00\r\n")
        or quote_parent._unknown(text)
    ):
        return None
    return text


def _canonical_table(
    prediction: str, columns: Sequence[str]
) -> tuple[list[list[str]] | None, bool]:
    canonical, _errors = score.extract_valid_markdown_table(prediction, columns)
    if canonical is None or canonical != prediction:
        return None, False
    lines = [
        line.strip()
        for line in canonical.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    matrix = [score._split_table_row(line) for line in lines]
    if (
        len(matrix) < 3
        or any(len(row) != len(columns) for row in matrix)
        or matrix[0] != list(columns)
    ):
        return None, False
    return matrix, True


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


def _verified_records(
    prepared: Mapping[str, Any], record_output: object, *, attempted: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]] | None]:
    if (
        prepared.get("artifact_version") != 1
        or prepared.get("role")
        != "v25360_private_quote_coordinate_partial_field_state"
    ):
        raise ValueError("V2.53.69 private verifier state drifted")
    proposals = verifier.parent._parse_proposals(record_output) if attempted else None
    if proposals is None:
        return [], None
    records, _disposition = verifier._field_dispositions(prepared, proposals)
    return records, proposals


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value.get(name, 0)) for name in _COUNT_FIELDS},
        **{name: bool(value[name]) for name in _DYNAMIC_FLAGS},
        **{name: True for name in _TRUE_FLAGS},
        **{name: False for name in _FALSE_FLAGS},
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def apply_changed_safe_verified_coordinates(
    *,
    base_prediction: object,
    columns: Sequence[str],
    prepared: Mapping[str, Any],
    record_output: object,
    model_call_attempted: bool,
) -> dict[str, Any]:
    """Return a shared-base control and its deterministic verified edit."""

    base = str(base_prediction)
    required = _safe_columns(columns)
    if not base or "\x00" in base:
        raise ValueError("V2.53.69 base prediction drifted")
    records, proposals = _verified_records(
        prepared, record_output, attempted=bool(model_call_attempted)
    )
    verified_fields = [
        (record, field)
        for record in records
        for field in record["fields"]
    ]
    matrix, canonical = _canonical_table(base, required)
    column_index = {
        quote_parent._key(column): index for index, column in enumerate(required)
    }
    groups: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, str]]]] = (
        defaultdict(list)
    )
    for record, field in verified_fields:
        groups[
            (
                quote_parent._key(record["row_identity"]),
                quote_parent._key(field["column"]),
            )
        ].append((record, field))

    counts: defaultdict[str, int] = defaultdict(int)
    edits: list[tuple[int, int, str]] = []
    if matrix is None:
        counts["table_or_schema_rejected_field_count"] = len(verified_fields)
    else:
        data_rows = matrix[2:]
        row_keys: defaultdict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(data_rows):
            row_keys[quote_parent._key(row[0])].append(index)
        for (row_key, column_key), values in groups.items():
            if not row_key or not column_key:
                counts["missing_or_key_column_rejected_field_count"] += len(values)
                continue
            normalized_values = {
                quote_parent._key(field["value"]) for _record, field in values
            }
            if len(values) > 1:
                name = (
                    "conflicting_source_coordinate_rejected_field_count"
                    if len(normalized_values) > 1
                    else "multiple_source_coordinate_rejected_field_count"
                )
                counts[name] += len(values)
                continue
            index = column_index.get(column_key)
            if index is None or index == 0:
                counts["missing_or_key_column_rejected_field_count"] += 1
                continue
            matches = row_keys.get(row_key, [])
            if not matches:
                counts["missing_row_rejected_field_count"] += 1
                continue
            if len(matches) != 1:
                counts["ambiguous_row_rejected_field_count"] += 1
                continue
            value = _safe_value(values[0][1]["value"])
            if value is None:
                counts["unsafe_or_unknown_value_rejected_field_count"] += 1
                continue
            row_index = matches[0]
            base_value = data_rows[row_index][index]
            if quote_parent._key(base_value) == quote_parent._key(value):
                counts["unchanged_verified_coordinate_count"] += 1
                continue
            counts["changed_safe_coordinate_count"] += 1
            edits.append((row_index, index, value))

    candidate = base
    if matrix is not None and edits:
        rows = copy.deepcopy(matrix[2:])
        original_row_keys = [row[0] for row in rows]
        for row_index, column_index_value, value in edits:
            rows[row_index][column_index_value] = value
        candidate = _render(required, rows)
        reparsed, candidate_canonical = _canonical_table(candidate, required)
        if (
            not candidate_canonical
            or reparsed is None
            or len(reparsed[2:]) != len(matrix[2:])
            or [row[0] for row in reparsed[2:]] != original_row_keys
            or any(
                reparsed[2 + row_index][column_index_value] != value
                for row_index, column_index_value, value in edits
            )
        ):
            raise RuntimeError("V2.53.69 post-edit preservation drifted")
        edit_coordinates = {(row, column) for row, column, _value in edits}
        for row_index, (before, after) in enumerate(
            zip(matrix[2:], reparsed[2:], strict=True)
        ):
            for column_index_value, (old, new) in enumerate(
                zip(before, after, strict=True)
            ):
                if (
                    (row_index, column_index_value) not in edit_coordinates
                    and old != new
                ):
                    raise RuntimeError("V2.53.69 non-target cell drifted")

    changed = candidate != base
    receipt = _receipt(
        {
            "parsed_record_count": len(proposals or []),
            "parsed_field_count": sum(
                len(record["fields"]) for record in (proposals or [])
            ),
            "verified_record_count": len(records),
            "verified_field_count": len(verified_fields),
            "verified_table_coordinate_count": len(groups),
            **counts,
            "positive_signed_credit_count": 0,
            "model_call_attempted": bool(model_call_attempted),
            "record_output_strictly_valid": proposals is not None,
            "base_table_exact_canonical": canonical,
            "candidate_prediction_changed": changed,
            "candidate_identity_handoff": not changed,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "control_prediction": base,
        "candidate_prediction": candidate,
        "control_prediction_sha256": hashlib.sha256(base.encode()).hexdigest(),
        "candidate_prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "content_free_receipt": receipt,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *_DYNAMIC_FLAGS,
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    disposition_total = sum(
        copied.get(name, 0)
        for name in (
            "changed_safe_coordinate_count",
            "unchanged_verified_coordinate_count",
            "table_or_schema_rejected_field_count",
            "missing_row_rejected_field_count",
            "ambiguous_row_rejected_field_count",
            "missing_or_key_column_rejected_field_count",
            "multiple_source_coordinate_rejected_field_count",
            "conflicting_source_coordinate_rejected_field_count",
            "unsafe_or_unknown_value_rejected_field_count",
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
        or any(not isinstance(copied.get(name), bool) for name in _DYNAMIC_FLAGS)
        or copied["parsed_record_count"] > verifier.MAXIMUM_PROPOSED_RECORDS
        or copied["parsed_field_count"] > verifier.MAXIMUM_TOTAL_FIELDS
        or copied["verified_record_count"] > copied["parsed_record_count"]
        or copied["verified_field_count"] > copied["parsed_field_count"]
        or copied["verified_table_coordinate_count"]
        > copied["verified_field_count"]
        or disposition_total != copied["verified_field_count"]
        or copied["changed_safe_coordinate_count"]
        > copied["verified_table_coordinate_count"]
        or copied["positive_signed_credit_count"] != 0
        or copied["record_output_strictly_valid"]
        and not copied["model_call_attempted"]
        or copied["candidate_prediction_changed"]
        is not (copied["changed_safe_coordinate_count"] > 0)
        or copied["candidate_identity_handoff"]
        is not (not copied["candidate_prediction_changed"])
        or copied["candidate_prediction_changed"]
        and not copied["base_table_exact_canonical"]
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.69 changed-safe edit receipt drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    control = copied.get("control_prediction")
    candidate = copied.get("candidate_prediction")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "control_prediction",
        "candidate_prediction",
        "control_prediction_sha256",
        "candidate_prediction_sha256",
        "content_free_receipt",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "benchmark_launch_or_evaluator_authorized",
        "artifact_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(control, str)
        or not control
        or not isinstance(candidate, str)
        or not candidate
        or copied.get("control_prediction_sha256")
        != hashlib.sha256(control.encode()).hexdigest()
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(candidate.encode()).hexdigest()
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["candidate_prediction_changed"] is not (control != candidate)
        or any(
            copied.get(name) is not False
            for name in (
                "entropy_or_information_gain_assigns_signed_credit",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.69 changed-safe edit result drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "apply_changed_safe_verified_coordinates",
    "validate_receipt",
    "validate_result",
]
