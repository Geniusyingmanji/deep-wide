"""Visible-only exact-column declaration successor.

V2.51.08 exposed a narrow parser gap: the public task wording used
``Columns exactly: A | B | C`` while the frozen robust parser recognized pipe
separators but not the ``Columns exactly:`` anchor.  This pure append-only
successor adds that anchor and otherwise delegates to the frozen parser.  It
has no I/O, benchmark metadata, evaluator, credential, or launch capability.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24286_visible_schema_runtime as parent
from . import v24986_robust_paired_runtime as robust


POLICY_ID = "v25110_exact_visible_schema_v1"
_EXACT_ANCHORS = (
    re.compile(r"(?:the\s+)?columns?\s+exactly\s*[：:]\s*", re.IGNORECASE),
    re.compile(r"exact\s+(?:output\s+)?columns?\s*[：:]\s*", re.IGNORECASE),
)


def _validated_clause(visible: str, end: int) -> list[str]:
    clause = parent._column_clause(visible[end:])
    columns: list[str] = []
    for raw_value in parent._top_level_split(clause):
        value = parent._clean_column(raw_value)
        if not value:
            continue
        if parent._SEGMENT_INSTRUCTION_CUE.match(value):
            break
        columns.append(value)
    normalized = [score._normalize_column(value) for value in columns]
    if (
        1 <= len(columns) <= 20
        and all(len(value) <= 80 for value in columns)
        and all(normalized)
        and len(set(normalized)) == len(normalized)
    ):
        return columns
    return []


def extract_exact_visible_columns(question: str) -> list[str]:
    """Return one unambiguous column vector from visible question text only."""

    visible = str(question or "")
    inherited = parent.extract_robust_visible_columns(visible)
    if inherited:
        return inherited
    matches: list[tuple[int, int]] = []
    for pattern in _EXACT_ANCHORS:
        matches.extend((match.start(), match.end()) for match in pattern.finditer(visible))
    for _start, end in sorted(matches):
        columns = _validated_clause(visible, end)
        if columns:
            return columns
    return []


def validated_exact_plan(
    value: Mapping[str, Any],
    question: str,
    limits: score.ScoreFirstLimits,
) -> dict[str, Any]:
    """Apply the exact visible schema without changing the frozen query policy."""

    plan = robust.validated_robust_plan(value, question, limits)
    columns = extract_exact_visible_columns(question)
    if columns:
        plan["columns"] = columns
        plan["robust_visible_schema_column_count"] = len(columns)
    return plan


__all__ = ["POLICY_ID", "extract_exact_visible_columns", "validated_exact_plan"]
