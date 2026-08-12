r"""Pure quote-aware repair for unambiguous Markdown escaped-pipe cells.

The frozen DeepWide parser treats every literal pipe as a delimiter, while
models commonly emit ``\|`` inside a factual Markdown cell.  This append-only
module repairs only a single exact-header table whose rows are otherwise
complete and width-correct.  It exposes two representations in memory:

* a reversible pipe-free internal table accepted by the frozen parent parser;
* a CSV-quoted final table whose literal pipes remain in one evaluator column.

No question, response, cell, column, prediction, semantic hash, or credential
is included in the content-free receipt.  Ambiguity always fails closed.
"""

from __future__ import annotations

import copy
import csv
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from . import v24257_score_first_runtime as score
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25177_quote_aware_pipe_normalizer_v1"
RECEIPT_ROLE = "v25177_content_free_quote_aware_pipe_normalizer_receipt"
INTERNAL_PIPE_ENTITY = "&#124;"
SEPARATOR = re.compile(r":?-{3,}:?")
MAXIMUM_CELL_CHARACTERS = 20_000


def _required_columns(columns: Sequence[str]) -> tuple[str, ...]:
    if isinstance(columns, (str, bytes)):
        raise TypeError("V2.51.77 columns must be a sequence")
    required = tuple(str(value).strip() for value in columns if str(value).strip())
    normalized = [score._normalize_column(value) for value in required]
    if (
        not required
        or len(required) > 20
        or not all(normalized)
        or len(set(normalized)) != len(required)
    ):
        raise ValueError("V2.51.77 required columns drifted")
    return required


def _split_row(line: str) -> tuple[list[str], int] | None:
    r"""Split one pipe row and decode only an unambiguous single ``\|``."""

    raw = str(line).strip()
    if "|" not in raw:
        return None
    cells: list[str] = []
    current: list[str] = []
    escaped_pipes = 0
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == "\\":
            end = index
            while end < len(raw) and raw[end] == "\\":
                end += 1
            run = end - index
            if end < len(raw) and raw[end] == "|":
                if run != 1:
                    return None
                current.append("|")
                escaped_pipes += 1
                index = end + 1
                continue
            current.extend("\\" * run)
            index = end
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    cells.append("".join(current).strip())
    if raw.startswith("|") and cells and cells[0] == "":
        cells.pop(0)
    if raw.endswith("|") and cells and cells[-1] == "":
        cells.pop()
    return (cells, escaped_pipes) if len(cells) >= 2 else None


def _groups(text: str) -> tuple[list[list[tuple[list[str], int]]], int]:
    groups: list[list[tuple[list[str], int]]] = []
    current: list[tuple[list[str], int]] = []
    malformed_pipe_lines = 0
    for raw in str(text or "").replace("\r\n", "\n").splitlines():
        parsed = _split_row(raw)
        if parsed is not None:
            current.append(parsed)
        else:
            if "|" in raw:
                malformed_pipe_lines += 1
            if current:
                groups.append(current)
                current = []
    if current:
        groups.append(current)
    return groups, malformed_pipe_lines


def _is_separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(
        SEPARATOR.fullmatch(str(value).replace(" ", "")) is not None
        for value in cells
    )


def _safe_semantic_cell(value: str) -> bool:
    return bool(
        value
        and len(value) <= MAXIMUM_CELL_CHARACTERS
        and INTERNAL_PIPE_ENTITY not in value
        and "\r" not in value
        and "\n" not in value
        and "\x00" not in value
        and "```" not in value
    )


def _render(
    columns: Sequence[str], rows: Sequence[Sequence[str]]
) -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def _csv_quote(value: str) -> str:
    return (
        '"' + value.replace('"', '""') + '"'
        if "|" in value or '"' in value
        else value
    )


def _public_loader_like_values(markdown: str) -> list[list[str]]:
    """Mirror the released loader's public line/split/CSV shape semantics."""

    fenced = str(markdown).replace("```markdown", "").replace("```", "")
    lines = [line.strip() for line in fenced.splitlines()]
    rows = [
        "|".join(part.strip() for part in line.split("|"))
        for line in lines
        if "|" in line and not set(line.strip()).issubset(set("|- :"))
    ]
    parsed = list(csv.reader(StringIO("\n".join(rows)), delimiter="|"))
    return [
        [value.strip() for value in row if value.strip()]
        for row in parsed
    ]


def _receipt(
    *,
    row_count: int,
    escaped_pipe_cell_count: int,
    escaped_pipe_occurrence_count: int,
    quoted_cell_count: int,
    adjacent_pipe_whitespace_count: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "row_count": int(row_count),
        "escaped_pipe_cell_count": int(escaped_pipe_cell_count),
        "escaped_pipe_occurrence_count": int(escaped_pipe_occurrence_count),
        "internal_entity_cell_count": int(escaped_pipe_cell_count),
        "csv_quoted_cell_count": int(quoted_cell_count),
        "adjacent_pipe_whitespace_count": int(adjacent_pipe_whitespace_count),
        "repair_applied": True,
        "single_exact_header_table_only": True,
        "all_rows_nonempty_and_width_exact": True,
        "internal_entity_collision_absent": True,
        "internal_frozen_parser_compatible": True,
        "internal_entity_roundtrip_exact_before_public_loader": True,
        "final_public_loader_column_shape_compatible": True,
        "public_loader_adjacent_pipe_whitespace_canonicalization_measured": True,
        "header_row_count_row_order_nonpipe_cells_and_decoded_values_preserved": True,
        "question_response_cell_column_prediction_or_semantic_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "network_model_search_fetch_or_evaluator_effect": False,
        "benchmark_launch_or_external_protocol_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def normalize_quote_aware_table(
    text: str, columns: Sequence[str]
) -> tuple[str, str, dict[str, Any]] | None:
    """Return internal/final tables only for one unambiguous escaped-pipe table."""

    if not isinstance(text, str):
        raise TypeError("V2.51.77 candidate text must be a string")
    required = _required_columns(columns)
    groups, malformed = _groups(text)
    if malformed:
        return None
    candidates: list[tuple[list[list[str]], int]] = []
    for group in groups:
        if len(group) < 3:
            continue
        for separator_index, (separator, separator_escapes) in enumerate(group):
            if separator_index < 1 or separator_escapes or not _is_separator(separator):
                continue
            header, header_escapes = group[separator_index - 1]
            if (
                header_escapes
                or [score._normalize_column(value) for value in header]
                != [score._normalize_column(value) for value in required]
                or len(separator) != len(header)
            ):
                continue
            source = [
                (row, escaped)
                for row, escaped in group[separator_index + 1 :]
                if not _is_separator(row)
            ]
            if not source:
                continue
            rows: list[list[str]] = []
            escaped_total = 0
            valid = True
            for row, escaped in source:
                if (
                    len(row) != len(header)
                    or not all(_safe_semantic_cell(value) for value in row)
                ):
                    valid = False
                    break
                rows.append([str(value) for value in row])
                escaped_total += escaped
            if valid and escaped_total > 0:
                candidates.append((rows, escaped_total))
    if len(candidates) != 1:
        return None
    semantic_rows, escaped_total = candidates[0]
    escaped_cells = sum("|" in value for row in semantic_rows for value in row)
    if escaped_cells <= 0 or escaped_total < escaped_cells:
        return None
    internal_rows = [
        [value.replace("|", INTERNAL_PIPE_ENTITY) for value in row]
        for row in semantic_rows
    ]
    internal = _render(required, internal_rows)
    checked, _errors = score.extract_valid_markdown_table(internal, required)
    if checked != internal:
        return None
    decoded = [
        [value.replace(INTERNAL_PIPE_ENTITY, "|") for value in row]
        for row in internal_rows
    ]
    if decoded != semantic_rows:
        return None
    final_rows = [[_csv_quote(value) for value in row] for row in decoded]
    final = _render(required, final_rows)
    public = _public_loader_like_values(final)
    if (
        len(public) != len(semantic_rows) + 1
        or public[0] != list(required)
        or any(len(row) != len(required) for row in public[1:])
    ):
        return None
    adjacent = sum(
        len(re.findall(r"\s+\||\|\s+", value))
        for row in semantic_rows
        for value in row
    )
    receipt = _receipt(
        row_count=len(semantic_rows),
        escaped_pipe_cell_count=escaped_cells,
        escaped_pipe_occurrence_count=escaped_total,
        quoted_cell_count=sum(
            "|" in value or '"' in value
            for row in semantic_rows
            for value in row
        ),
        adjacent_pipe_whitespace_count=adjacent,
    )
    return internal, final, receipt


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "row_count",
        "escaped_pipe_cell_count",
        "escaped_pipe_occurrence_count",
        "internal_entity_cell_count",
        "csv_quoted_cell_count",
        "adjacent_pipe_whitespace_count",
    )
    true_flags = (
        "repair_applied",
        "single_exact_header_table_only",
        "all_rows_nonempty_and_width_exact",
        "internal_entity_collision_absent",
        "internal_frozen_parser_compatible",
        "internal_entity_roundtrip_exact_before_public_loader",
        "final_public_loader_column_shape_compatible",
        "public_loader_adjacent_pipe_whitespace_canonicalization_measured",
        "header_row_count_row_order_nonpipe_cells_and_decoded_values_preserved",
    )
    false_flags = (
        "question_response_cell_column_prediction_or_semantic_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "network_model_search_fetch_or_evaluator_effect",
        "benchmark_launch_or_external_protocol_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            *counts,
            *true_flags,
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["row_count"] < 1
        or copied["escaped_pipe_cell_count"] < 1
        or copied["escaped_pipe_occurrence_count"]
        < copied["escaped_pipe_cell_count"]
        or copied["internal_entity_cell_count"]
        != copied["escaped_pipe_cell_count"]
        or copied["csv_quoted_cell_count"]
        < copied["escaped_pipe_cell_count"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.77 quote-aware receipt drifted")
    return copied


__all__ = [
    "INTERNAL_PIPE_ENTITY",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "normalize_quote_aware_table",
    "validate_receipt",
]
