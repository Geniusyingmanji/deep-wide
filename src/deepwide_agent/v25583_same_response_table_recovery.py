"""Fail-closed structural table recovery from one existing model response.

V2.55.82 found that six V2.55.81 fallbacks had a successful third provider
response and an exact outer JSON envelope, but the frozen Markdown table
normalizer could not recover the envelope's ``table`` string.  This module is
an append-only, task-local candidate for that representation gap.

The frozen V2.49.86 normalizer always runs first.  Only when it returns
``unrecoverable`` may this candidate inspect the same response bytes.  It can
recover one unambiguous rectangular table in four conservative forms:

* pipe rows whose required header is followed by data but no separator;
* pipe rows with a syntactically weak one/two-dash separator;
* strict CSV or TSV with the exact required header set; or
* strict JSON records / a ``columns`` plus ``rows`` matrix containing only
  string or null cells.

Every data row must survive, required columns must map injectively, row order
is preserved, and non-empty cells are never inferred from pages or rewritten
apart from format decoding and outer whitespace removal.  Ambiguity, extra
keys, ragged rows, embedded pipes/newlines, non-string JSON values, excessive
size, or any competing parse fails closed.  No model/search/fetch/network
effect, membership inference, benchmark metadata, evaluator, mapping, gold,
score, reward, historical result, filesystem, environment, process, or
credential is available.  Entropy/information gain is shadow-only and assigns
no signed credit.  This build authorizes no external or benchmark execution.
"""

from __future__ import annotations

import copy
import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24259_deterministic_table_normalizer as frozen_normalizer
from . import v24986_robust_paired_runtime as frozen_robust
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25583_same_response_structural_table_recovery_v1"
RECEIPT_ROLE = "v25583_content_free_same_response_table_recovery_receipt"
MAXIMUM_INPUT_CHARACTERS = 120_000
MAXIMUM_OUTPUT_CHARACTERS = 120_000
MAXIMUM_ROWS = 512
MAXIMUM_COLUMNS = 20
MAXIMUM_CELL_CHARACTERS = 2_000

PARENT_MODES = frozenset({"parent_exact", "parent_normalized"})
RECOVERY_MODES = frozenset(
    {
        "recovered_missing_pipe_separator",
        "recovered_weak_pipe_separator",
        "recovered_csv",
        "recovered_tsv",
        "recovered_json_records",
        "recovered_json_matrix",
    }
)
MODES = PARENT_MODES | RECOVERY_MODES | {"unrecoverable"}

_FENCE = re.compile(
    r"\A\s*```(?:json|csv|tsv|text|markdown|md)?[ \t]*\n"
    r"(?P<body>.*?)\n```\s*\Z",
    re.IGNORECASE | re.DOTALL,
)
_WEAK_SEPARATOR = re.compile(r":?-{1,}:?")


def _required_columns(columns: Sequence[object]) -> tuple[str, ...]:
    if isinstance(columns, (str, bytes)):
        return ()
    values = tuple(str(value).strip() for value in columns)
    keys = tuple(score._normalize_column(value) for value in values)
    if (
        not 1 <= len(values) <= MAXIMUM_COLUMNS
        or any(not value or len(value) > 160 for value in values)
        or any(not key for key in keys)
        or len(set(keys)) != len(keys)
        or any(any(character in value for character in "|\x00\r\n") for value in values)
    ):
        return ()
    return values


def _body(text: str) -> str | None:
    value = str(text or "")
    if not value or len(value) > MAXIMUM_INPUT_CHARACTERS or "\x00" in value:
        return None
    match = _FENCE.fullmatch(value)
    if value.lstrip().startswith("```"):
        return match.group("body") if match is not None else None
    return value.strip()


def _header_mapping(
    header: Sequence[object], required: Sequence[str]
) -> tuple[int, ...] | None:
    if len(header) != len(required):
        return None
    source = tuple(score._normalize_column(str(value)) for value in header)
    target = tuple(score._normalize_column(value) for value in required)
    if (
        any(not value for value in source)
        or len(set(source)) != len(source)
        or set(source) != set(target)
    ):
        return None
    return tuple(source.index(value) for value in target)


def _safe_cell(value: object, unknown_marker: str) -> tuple[str | None, bool]:
    if value is None:
        return unknown_marker, True
    if not isinstance(value, str):
        return None, False
    stripped = value.strip()
    if (
        len(stripped) > MAXIMUM_CELL_CHARACTERS
        or any(character in stripped for character in "|\x00\r\n")
    ):
        return None, False
    return (stripped, False) if stripped else (unknown_marker, True)


def _mapped_rows(
    rows: Sequence[Sequence[object]],
    mapping: Sequence[int],
    source_width: int,
    unknown_marker: str,
) -> tuple[list[list[str]], int] | None:
    if not 1 <= len(rows) <= MAXIMUM_ROWS:
        return None
    output: list[list[str]] = []
    filled = 0
    for raw in rows:
        if isinstance(raw, (str, bytes)) or len(raw) != source_width:
            return None
        row: list[str] = []
        for index in mapping:
            value, was_filled = _safe_cell(raw[index], unknown_marker)
            if value is None:
                return None
            row.append(value)
            filled += int(was_filled)
        output.append(row)
    return output, filled


def _render(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> str | None:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]
    value = "```markdown\n" + "\n".join(lines) + "\n```"
    return value if len(value) <= MAXIMUM_OUTPUT_CHARACTERS else None


def _candidate(
    mode: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[object]],
    mapping: Sequence[int],
    source_width: int,
    unknown_marker: str,
) -> dict[str, Any] | None:
    mapped = _mapped_rows(rows, mapping, source_width, unknown_marker)
    if mapped is None:
        return None
    normalized, filled = mapped
    table = _render(columns, normalized)
    if table is None:
        return None
    exact, errors = score.extract_valid_markdown_table(table, columns)
    if exact != table or errors:
        return None
    return {
        "mode": mode,
        "table": table,
        "input_row_count": len(rows),
        "output_row_count": len(normalized),
        "filled_empty_cell_count": filled,
    }


def _pipe_candidate(
    body: str, columns: Sequence[str], unknown_marker: str
) -> dict[str, Any] | None:
    if re.search(r"\n[ \t]*\n", body):
        return None
    lines = [line for line in body.splitlines() if line.strip()]
    group = [frozen_normalizer._split_pipe_row(line) for line in lines]
    # Recovery never skips prose, malformed rows, or a second table-shaped
    # region.  Every nonempty line must participate in the one rectangle.
    if not lines or any(not row for row in group):
        return None
    if len(group) < 2:
        return None
    mapping = _header_mapping(group[0], columns)
    if mapping is None:
        return None
    data_start = 1
    mode = "recovered_missing_pipe_separator"
    if all(
        _WEAK_SEPARATOR.fullmatch(str(value).replace(" ", "")) is not None
        for value in group[1]
    ):
        if frozen_normalizer._is_separator(group[1]):
            # A strong separator belongs to the frozen parent.  If the parent
            # rejected it, this successor must not reinterpret malformed rows.
            return None
        data_start = 2
        mode = "recovered_weak_pipe_separator"
    rows = group[data_start:]
    if any(frozen_normalizer._is_separator(row) for row in rows):
        return None
    return _candidate(
        mode,
        columns,
        rows,
        mapping,
        len(group[0]),
        unknown_marker,
    )


def _delimited_candidates(
    body: str, columns: Sequence[str], unknown_marker: str
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for delimiter, mode in ((",", "recovered_csv"), ("\t", "recovered_tsv")):
        try:
            rows = list(csv.reader(StringIO(body, newline=""), delimiter=delimiter, strict=True))
        except (csv.Error, TypeError, ValueError):
            continue
        if not 2 <= len(rows) <= MAXIMUM_ROWS + 1:
            continue
        mapping = _header_mapping(rows[0], columns)
        if mapping is None:
            continue
        candidate = _candidate(
            mode,
            columns,
            rows[1:],
            mapping,
            len(rows[0]),
            unknown_marker,
        )
        if candidate is not None:
            output.append(candidate)
    return output


def _json_candidate(
    body: str, columns: Sequence[str], unknown_marker: str
) -> dict[str, Any] | None:
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if isinstance(parsed, list):
        if not parsed or any(not isinstance(row, Mapping) for row in parsed):
            return None
        header = list(parsed[0])
        mapping = _header_mapping(header, columns)
        if mapping is None or any(list(row) != header for row in parsed):
            return None
        rows = [[row[key] for key in header] for row in parsed]
        return _candidate(
            "recovered_json_records",
            columns,
            rows,
            mapping,
            len(header),
            unknown_marker,
        )
    if not isinstance(parsed, Mapping) or set(parsed) != {"columns", "rows"}:
        return None
    header = parsed.get("columns")
    rows = parsed.get("rows")
    if (
        not isinstance(header, list)
        or not isinstance(rows, list)
        or any(not isinstance(row, list) for row in rows)
    ):
        return None
    mapping = _header_mapping(header, columns)
    if mapping is None:
        return None
    return _candidate(
        "recovered_json_matrix",
        columns,
        rows,
        mapping,
        len(header),
        unknown_marker,
    )


def _receipt(
    *,
    mode: str,
    parent_status: str,
    input_characters: int,
    required_columns: int,
    candidate_parser_count: int,
    input_rows: int,
    output_rows: int,
    filled_empty_cells: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "mode": mode,
        "parent_status": parent_status,
        "input_character_count": input_characters,
        "required_column_count": required_columns,
        "candidate_parser_count": candidate_parser_count,
        "input_row_count": input_rows,
        "output_row_count": output_rows,
        "filled_empty_cell_count": filled_empty_cells,
        "positive_signed_credit_count": 0,
        "parent_output_byte_preserved_when_accepted": True,
        "recovery_runs_only_after_parent_unrecoverable": True,
        "one_existing_same_response_only": True,
        "required_columns_map_injectively": True,
        "recovery_preserves_all_parsed_data_rows_in_order_or_is_rejected": True,
        "recovery_nonempty_cells_are_only_format_decoded_and_outer_whitespace_trimmed": True,
        "recovery_empty_or_null_cells_only_may_receive_visible_language_unknown_marker": True,
        "recovery_does_not_infer_page_fact_membership_row_or_value": True,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "contains_question_column_row_value_prediction_query_url_page_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "historical_per_task_outcome_runtime_routing": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integers = (
        "input_character_count",
        "required_column_count",
        "candidate_parser_count",
        "input_row_count",
        "output_row_count",
        "filled_empty_cell_count",
        "positive_signed_credit_count",
    )
    true_flags = (
        "parent_output_byte_preserved_when_accepted",
        "recovery_runs_only_after_parent_unrecoverable",
        "one_existing_same_response_only",
        "required_columns_map_injectively",
        "recovery_preserves_all_parsed_data_rows_in_order_or_is_rejected",
        "recovery_nonempty_cells_are_only_format_decoded_and_outer_whitespace_trimmed",
        "recovery_empty_or_null_cells_only_may_receive_visible_language_unknown_marker",
        "recovery_does_not_infer_page_fact_membership_row_or_value",
    )
    false_flags = (
        "additional_model_search_fetch_token_context_wall_or_network_budget",
        "contains_question_column_row_value_prediction_query_url_page_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "historical_per_task_outcome_runtime_routing",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "mode",
        "parent_status",
        *integers,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    mode = copied.get("mode")
    parent_status = copied.get("parent_status")
    recovered = mode in RECOVERY_MODES
    parent = mode in PARENT_MODES
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or mode not in MODES
        or parent_status not in {"exact", "normalized", "unrecoverable"}
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integers
        )
        or not 1 <= copied.get("required_column_count", 0) <= MAXIMUM_COLUMNS
        or copied.get("candidate_parser_count", 0) > 4
        or copied.get("input_row_count", 0) > MAXIMUM_ROWS
        or copied.get("output_row_count", 0) > MAXIMUM_ROWS
        or copied.get("filled_empty_cell_count", 0)
        > copied.get("output_row_count", 0) * copied.get("required_column_count", 0)
        or parent is not (parent_status in {"exact", "normalized"})
        or (parent and copied["candidate_parser_count"] != 0)
        or recovered is not (copied["candidate_parser_count"] == 1)
        or (recovered and copied["input_character_count"] > MAXIMUM_INPUT_CHARACTERS)
        or recovered is not (copied["input_row_count"] > 0)
        or recovered is not (
            copied["input_row_count"] == copied["output_row_count"]
            and copied["output_row_count"] > 0
        )
        or (mode == "unrecoverable" and copied["output_row_count"] != 0)
        or copied.get("positive_signed_credit_count") != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.83 table recovery receipt drifted")
    return copied


def normalize_synthesis(
    text: str,
    columns: Sequence[object],
    question: str,
) -> tuple[str | None, dict[str, Any]]:
    """Normalize with frozen-parent priority and one fail-closed local fallback."""

    required = _required_columns(columns)
    visible = str(question or "")
    raw = str(text or "")
    if not required or not visible or "\x00" in visible:
        raise ValueError("V2.55.83 visible normalization input drifted")
    parent_table, parent_status = frozen_robust._normalize_synthesis(
        raw, required, visible
    )
    if parent_table is not None:
        mode = "parent_exact" if parent_status == "exact" else "parent_normalized"
        return parent_table, _receipt(
            mode=mode,
            parent_status=parent_status,
            input_characters=len(raw),
            required_columns=len(required),
            candidate_parser_count=0,
            input_rows=0,
            output_rows=0,
            filled_empty_cells=0,
        )

    candidate_body = _body(raw)
    candidates: list[dict[str, Any]] = []
    if candidate_body is not None:
        marker = "未知" if re.search(r"[\u4e00-\u9fff]", visible) else "Unknown"
        pipe = _pipe_candidate(candidate_body, required, marker)
        if pipe is not None:
            candidates.append(pipe)
        candidates.extend(_delimited_candidates(candidate_body, required, marker))
        structured = _json_candidate(candidate_body, required, marker)
        if structured is not None:
            candidates.append(structured)

    if len(candidates) != 1:
        return None, _receipt(
            mode="unrecoverable",
            parent_status="unrecoverable",
            input_characters=len(raw),
            required_columns=len(required),
            candidate_parser_count=min(len(candidates), 4),
            input_rows=0,
            output_rows=0,
            filled_empty_cells=0,
        )
    selected = candidates[0]
    return str(selected["table"]), _receipt(
        mode=str(selected["mode"]),
        parent_status="unrecoverable",
        input_characters=len(raw),
        required_columns=len(required),
        candidate_parser_count=1,
        input_rows=int(selected["input_row_count"]),
        output_rows=int(selected["output_row_count"]),
        filled_empty_cells=int(selected["filled_empty_cell_count"]),
    )


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_normalizer_policy_id": frozen_robust.POLICY_ID,
        "frozen_parent_always_runs_first": True,
        "same_response_bytes_only": True,
        "recovery_modes": sorted(RECOVERY_MODES),
        "maximum_recovery_input_characters": MAXIMUM_INPUT_CHARACTERS,
        "maximum_rows": MAXIMUM_ROWS,
        "maximum_columns": MAXIMUM_COLUMNS,
        "maximum_cell_characters": MAXIMUM_CELL_CHARACTERS,
        "all_rows_must_survive_in_order": True,
        "required_header_mapping_must_be_injective": True,
        "nonempty_fact_inference_or_page_completion": False,
        "membership_inference_or_row_creation": False,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "historical_per_task_outcome_runtime_routing": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "MODES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "RECOVERY_MODES",
    "integration_contract",
    "normalize_synthesis",
    "validate_receipt",
]
