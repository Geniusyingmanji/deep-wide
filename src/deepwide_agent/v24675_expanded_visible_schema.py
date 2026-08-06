"""Append-only visible-schema grammar expansion.

The frozen V2.42.86 parser recognizes explicit column declarations for most
DeepWideBench questions, but misses several ordinary prompt forms such as
``table must contain the following columns`` and ``with the columns, in this
exact order``.  This successor always delegates to the frozen parser first and
uses a conservative fallback only for explicit visible declarations.

The parser accepts only question text.  It has no benchmark-label, mapping,
gold, evaluator, score, reward, file, network, model, search, fetch, process,
or credential capability.  Ambiguous or absent declarations remain empty.
"""

from __future__ import annotations

import re

from .v24257_score_first_runtime import _normalize_column
from .v24286_visible_schema_runtime import (
    _clean_column,
    _column_clause,
    _SEGMENT_INSTRUCTION_CUE,
    _top_level_split,
    extract_robust_visible_columns,
)


POLICY_ID = "v24675_expanded_explicit_visible_schema_v1"
MAXIMUM_COLUMN_COUNT = 20
MAXIMUM_COLUMN_CHARACTERS = 80
_DOT_SENTINEL = "\uff0e"

# Every expression ends at an explicit declaration boundary.  None infers
# fields from task semantics, entities, benchmark identity, or output history.
_FALLBACK_ANCHORS = (
    re.compile(
        r"(?:表格中?)?(?:需|需要|应|必须)?(?:包含|包括)(?:以下)?(?:列|字段)\s*[：:]\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:表格中的)?(?:列名|栏名|列标题)(?:依次)?(?:为|是)\s*(?:[：:]\s*)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"表头(?:信息)?(?:依次)?(?:为|是)\s*(?:[：:]\s*)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:需要整理的|待整理的)?(?:信息|数据)(?:包括|包含)\s*(?:[：:]\s*)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:one\s+)?markdown\s+table\s+with\s+(?:the\s+)?columns?"
        r"(?:\s+labeled)?(?:\s*,\s*in\s+(?:this\s+)?(?:exact\s+)?order)?\s*[：:]\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:present|display|organize|output|provide|compile)[^:\n]{0,120}"
        r"(?:table\s+)?with\s+(?:the\s+)?(?:following\s+)?columns?"
        r"(?:\s+labeled)?(?:\s*,\s*in\s+(?:this\s+)?(?:exact\s+)?order)?\s*[：:]\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"columns?\s+names?\s+(?:are|is)\s+as\s+follows\s*[：:]\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:specified\s+column\s+order|following\s+(?:column\s+)?names)\s*[：:]\s*",
        re.IGNORECASE,
    ),
)


def _explicit_columns_after(visible: str, end: int) -> list[str]:
    suffix = visible[end:]
    # The frozen clause boundary treats a period as a possible sentence end.
    # Protect only conventional multi-letter dotted abbreviations such as
    # ``U.S.`` while parsing, then restore their original ASCII periods.
    protected = re.sub(
        r"(?:[A-Za-z]\.){2,}",
        lambda match: match.group(0).replace(".", _DOT_SENTINEL),
        suffix,
    )
    clause = _column_clause(protected).replace(_DOT_SENTINEL, ".")
    columns: list[str] = []
    for raw_value in _top_level_split(clause):
        value = _clean_column(raw_value)
        if not value:
            continue
        if _SEGMENT_INSTRUCTION_CUE.match(value):
            break
        columns.append(value)
    normalized = [_normalize_column(value) for value in columns]
    if (
        1 <= len(columns) <= MAXIMUM_COLUMN_COUNT
        and all(len(value) <= MAXIMUM_COLUMN_CHARACTERS for value in columns)
        and all(normalized)
        and len(set(normalized)) == len(normalized)
    ):
        return columns
    return []


def extract_expanded_visible_columns(question: str) -> list[str]:
    """Return explicit visible columns while preserving frozen behavior first."""

    visible = str(question or "")
    frozen = extract_robust_visible_columns(visible)
    if frozen:
        return frozen
    matches: list[tuple[int, int]] = []
    for pattern in _FALLBACK_ANCHORS:
        matches.extend((match.start(), match.end()) for match in pattern.finditer(visible))
    for _start, end in sorted(matches):
        columns = _explicit_columns_after(visible, end)
        if columns:
            return columns
    return []


__all__ = [
    "MAXIMUM_COLUMN_CHARACTERS",
    "MAXIMUM_COLUMN_COUNT",
    "POLICY_ID",
    "extract_expanded_visible_columns",
]
