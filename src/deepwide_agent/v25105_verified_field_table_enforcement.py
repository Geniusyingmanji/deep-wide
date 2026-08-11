"""Deterministically enforce strictly verified fields in one synthesis table.

The verifier path is exactly V2.51.00 -> V2.50.95.  This component only
rewrites the uniquely identity-matched row of an already valid Markdown table.
It adds no model, search, fetch, token, context, wall, network, evaluator, or
benchmark-label capability.  Content-bearing verified values remain private;
the returned receipt contains counts and booleans only.
"""

from __future__ import annotations

import copy
import datetime as dt
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25065_quote_verified_record_binding as base
from . import v25080_visible_identity_page_record as identity_parent
from . import v25095_value_shape_partial_field_record as verifier
from . import v25100_complete_column_value_shape_record as complete
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25105_verified_field_table_enforcement_v1"
ROLE = "v25105_verified_field_table_enforcement_result"
RECEIPT_ROLE = "v25105_content_free_verified_field_table_enforcement_receipt"

_MONTH_FORMATS = (
    "%b %d, %Y",
    "%B %d, %Y",
    "%b %d %Y",
    "%B %d %Y",
    "%d %b %Y",
    "%d %B %Y",
)


def _verified_record(
    prepared: Mapping[str, Any],
    model_output: object,
    *,
    model_call_attempted: bool,
) -> dict[str, Any] | None:
    if (
        prepared.get("artifact_version") != 1
        or prepared.get("role") != "v25100_private_complete_column_value_shape_state"
    ):
        raise ValueError("V2.51.05 prepared state drifted")
    parsed = (
        complete._parse_complete_proposal(model_output, prepared)
        if model_call_attempted
        else None
    )
    proposals = identity_parent._parse_proposals(complete._parent_output(parsed))
    if proposals is None:
        return None
    records, _dispositions = verifier._field_dispositions(
        complete._parent_prepared(prepared), proposals
    )
    return copy.deepcopy(records[0]) if len(records) == 1 else None


def _canonical_value(column: str, value: object) -> tuple[str | None, bool]:
    text = " ".join(str(value or "").split())
    if not text or "|" in text or "\x00" in text or "\n" in text or "\r" in text:
        return None, False
    if verifier._target_kind(column) != "date":
        return text, False
    if verifier._ISO_DATE.fullmatch(text):
        try:
            return dt.date.fromisoformat(text).isoformat(), False
        except ValueError:
            return None, False
    for pattern in _MONTH_FORMATS:
        try:
            return dt.datetime.strptime(text, pattern).date().isoformat(), True
        except ValueError:
            continue
    return None, False


def _parse_table(prediction: object, columns: Sequence[str]) -> list[list[str]] | None:
    canonical, _errors = score.extract_valid_markdown_table(str(prediction), columns)
    if canonical is None:
        return None
    lines = [line.strip() for line in canonical.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return None
    rows = [score._split_table_row(line) for line in lines]
    if any(len(row) != len(columns) for row in rows):
        return None
    return rows


def _render(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(str(value) for value in columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def enforce_verified_fields(
    prediction: object,
    columns: Sequence[str],
    prepared: Mapping[str, Any],
    model_output: object,
    *,
    model_call_attempted: bool,
) -> dict[str, Any]:
    original = str(prediction)
    required = tuple(str(value) for value in columns)
    if (
        not original
        or not 1 <= len(required) <= 20
        or any(not value.strip() or "|" in value for value in required)
    ):
        raise ValueError("V2.51.05 enforcement input drifted")
    record = _verified_record(
        prepared,
        model_output,
        model_call_attempted=model_call_attempted,
    )
    verified_count = 0 if record is None else len(record["fields"])
    table = _parse_table(original, required)
    table_valid = table is not None
    identity_matches: list[int] = []
    if table is not None and record is not None:
        target_identity = identity_parent._identity_key(record["row_identity"])
        identity_matches = [
            index
            for index, row in enumerate(table[2:])
            if identity_parent._identity_key(row[0]) == target_identity
        ]
    row_match = len(identity_matches) == 1
    column_index = {base._key(column): index for index, column in enumerate(required)}
    applied = changed = normalized_dates = rejected = 0
    output = original
    if table is not None and record is not None and row_match:
        rows = copy.deepcopy(table[2:])
        target = rows[identity_matches[0]]
        for field in record["fields"]:
            index = column_index.get(base._key(field["column"]))
            value, normalized = _canonical_value(str(field["column"]), field["value"])
            if index is None or index == 0 or value is None:
                rejected += 1
                continue
            applied += 1
            normalized_dates += int(normalized)
            if target[index] != value:
                target[index] = value
                changed += 1
        if rejected:
            applied = changed = normalized_dates = 0
        elif applied and changed:
            output = _render(required, rows)
    output_changed = output != original
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "verified_field_count": verified_count,
        "applied_field_count": applied,
        "changed_cell_count": changed,
        "normalized_date_count": normalized_dates,
        "rejected_field_count": rejected,
        "valid_table_present": table_valid,
        "unique_identity_row_matched": row_match,
        "output_changed": output_changed,
        "same_v25100_v25095_verifier_replayed": True,
        "only_exact_requested_non_key_columns_are_rewritten": True,
        "only_unique_visible_identity_row_is_rewritten": True,
        "verified_month_date_is_deterministically_normalized_to_iso": True,
        "ambiguous_or_invalid_table_field_or_identity_fails_closed": True,
        "nonempty_unverified_cell_is_never_rewritten": True,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "contains_question_query_url_title_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "prediction": output,
        "content_free_receipt": validate_receipt(receipt),
    }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "verified_field_count",
        "applied_field_count",
        "changed_cell_count",
        "normalized_date_count",
        "rejected_field_count",
    )
    bools = ("valid_table_present", "unique_identity_row_matched", "output_changed")
    true_flags = (
        "same_v25100_v25095_verifier_replayed",
        "only_exact_requested_non_key_columns_are_rewritten",
        "only_unique_visible_identity_row_is_rewritten",
        "verified_month_date_is_deterministically_normalized_to_iso",
        "ambiguous_or_invalid_table_field_or_identity_fails_closed",
        "nonempty_unverified_cell_is_never_rewritten",
    )
    false_flags = (
        "additional_model_search_fetch_token_context_wall_or_network_budget",
        "contains_question_query_url_title_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        *bools,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
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
            for name in counts
        )
        or any(not isinstance(copied.get(name), bool) for name in bools)
        or copied["applied_field_count"] > copied["verified_field_count"]
        or copied["changed_cell_count"] > copied["applied_field_count"]
        or copied["normalized_date_count"] > copied["applied_field_count"]
        or copied["rejected_field_count"] + copied["applied_field_count"]
        > copied["verified_field_count"]
        or copied["output_changed"] is not (copied["changed_cell_count"] > 0)
        or copied["applied_field_count"]
        and not (copied["valid_table_present"] and copied["unique_identity_row_matched"])
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.05 enforcement receipt drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "enforce_verified_fields",
    "validate_receipt",
]
