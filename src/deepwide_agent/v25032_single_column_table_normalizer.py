"""Append-only, label-blind recovery for one-column Markdown tables.

The frozen V2.42.59 normalizer intentionally treats rows with fewer than two
cells as non-tables.  That makes a canonical one-column Markdown shape such
as ``| Name |`` unreachable whenever its header needs structural repair.

This successor preserves the frozen implementation byte-for-byte and only
adds a conservative one-column path.  It accepts boundary-pipe rows, requires
one header, one separator, and at least one complete data row, rejects
multiple candidate tables, and never rewrites a non-empty factual cell.
There are no model, search, fetch, file, environment, process, or evaluator
effects in this module.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from .v24257_score_first_runtime import _normalize_column
from .v24259_deterministic_table_normalizer import (
    normalize_candidate_table as normalize_parent_candidate_table,
)


POLICY_ID = "v25032_single_column_table_normalizer_v1"
SEPARATOR = re.compile(r":?-{3,}:?")


def _diagnostics(
    *,
    status: str,
    mode: str,
    candidate_group_count: int,
    input_column_count: int,
    input_row_count: int,
    output_row_count: int,
    filled_empty_cell_count: int,
    candidate_table_count: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "mode": mode,
        "candidate_group_count": candidate_group_count,
        "input_column_count": input_column_count,
        "output_column_count": 1,
        "input_row_count": input_row_count,
        "output_row_count": output_row_count,
        "dropped_row_count": 0,
        "filled_empty_cell_count": filled_empty_cell_count,
        "single_column_candidate_table_count": candidate_table_count,
        "parent_policy_id": "v24259_deterministic_table_normalizer_v1",
        "policy_id": POLICY_ID,
        "nonempty_factual_cell_rewrite_count": 0,
        "additional_model_search_or_fetch_call_count": 0,
    }


def _split_boundary_single_cell(line: str) -> list[str]:
    """Parse exactly one boundary-pipe cell, preserving escaped characters.

    Requiring both boundary pipes avoids treating ordinary prose or a lone
    inline pipe as a one-column table.  Any unescaped interior pipe creates a
    second cell and is rejected by this one-column-only parser.
    """

    raw = str(line).strip()
    if len(raw) < 2 or not raw.startswith("|") or not raw.endswith("|"):
        return []
    body = raw[1:-1]
    escaped = False
    cells: list[str] = []
    current: list[str] = []
    for character in body:
        if character == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        if character == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(current).strip())
    return cells if len(cells) == 1 else []


def _groups(text: str) -> list[list[list[str]]]:
    groups: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in str(text or "").replace("\r\n", "\n").splitlines():
        cells = _split_boundary_single_cell(line)
        if cells:
            current.append(cells)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _is_separator(cells: Sequence[str]) -> bool:
    return len(cells) == 1 and SEPARATOR.fullmatch(
        str(cells[0]).replace(" ", "")
    ) is not None


def normalize_candidate_table(
    text: str,
    columns: Sequence[str],
    *,
    unknown_marker: str,
) -> tuple[str | None, dict[str, Any]]:
    """Normalize a table, adding only a strict one-column recovery path."""

    # Preserve every existing multi-column decision and any future parent
    # exact recovery.  The new parser is reachable only for one valid visible
    # column after the frozen parent returns no table.
    parent_table, parent_diagnostics = normalize_parent_candidate_table(
        text, columns, unknown_marker=unknown_marker
    )
    required = [str(value).strip() for value in columns if str(value).strip()]
    if parent_table is not None or len(required) != 1:
        return parent_table, parent_diagnostics
    target = _normalize_column(required[0])
    if (
        not target
        or parent_diagnostics.get("mode") == "invalid_required_columns"
        or not isinstance(unknown_marker, str)
        or not unknown_marker.strip()
        or any(character in unknown_marker for character in "|\r\n\x00")
    ):
        return None, parent_diagnostics

    groups = _groups(text)
    candidates: list[tuple[str, str, int, int]] = []
    # Each tuple is canonical table, mode, row count, and filled-empty count.
    for group in groups:
        for separator_index, separator in enumerate(group):
            if separator_index < 1 or not _is_separator(separator):
                continue
            header = group[separator_index - 1]
            if len(header) != 1 or not _normalize_column(header[0]):
                continue
            mode = (
                "single_column_exact_header"
                if _normalize_column(header[0]) == target
                else "single_column_positional_header"
            )
            source_rows = [
                row
                for row in group[separator_index + 1 :]
                if not _is_separator(row)
            ]
            if not source_rows:
                continue
            values: list[str] = []
            filled = 0
            malformed = False
            for row in source_rows:
                if len(row) != 1:
                    malformed = True
                    break
                value = row[0].strip()
                # The inherited exact parser treats escaped pipes as column
                # delimiters.  Re-encoding them would alter a non-empty cell,
                # so this successor must continue to fail closed.
                if "\\|" in value or "\x00" in value:
                    malformed = True
                    break
                if not value:
                    value = unknown_marker.strip()
                    filled += 1
                values.append(value)
            if malformed or not values:
                continue
            table = [
                f"| {required[0]} |",
                "| --- |",
                *(f"| {value} |" for value in values),
            ]
            candidates.append(
                ("```markdown\n" + "\n".join(table) + "\n```", mode, len(values), filled)
            )

    if len(candidates) != 1:
        return None, _diagnostics(
            status="unrecoverable",
            mode=(
                "ambiguous_single_column_tables"
                if len(candidates) > 1
                else "no_unambiguous_single_column_table"
            ),
            candidate_group_count=len(groups),
            input_column_count=0,
            input_row_count=0,
            output_row_count=0,
            filled_empty_cell_count=0,
            candidate_table_count=len(candidates),
        )

    canonical, mode, row_count, filled = candidates[0]
    status = "exact" if str(text or "").strip() == canonical else "normalized"
    return canonical, _diagnostics(
        status=status,
        mode=mode,
        candidate_group_count=len(groups),
        input_column_count=1,
        input_row_count=row_count,
        output_row_count=row_count,
        filled_empty_cell_count=filled,
        candidate_table_count=1,
    )


__all__ = ["POLICY_ID", "normalize_candidate_table"]
