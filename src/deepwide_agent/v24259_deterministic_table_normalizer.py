"""Label-blind deterministic Markdown normalization for score-first output.

The normalizer may repair table *structure* using only the visible required
columns and the model candidate produced during the same forward pass.  It
never invents or rewrites a non-empty factual cell.  Ambiguous extra columns
remain unrecoverable and fall through to the existing bounded model repair.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import parse_json_object
from .v24257_score_first_runtime import (
    POLICY_ID as PARENT_POLICY_ID,
    ScoreFirstLimits,
    _model_text,
    _normalize_column,
    _validated_plan,
    build_score_first_fallback_result,
    extract_visible_columns,
    run_score_first_task,
    validate_score_first_result,
    validate_visible_task,
)


POLICY_ID = "v24259_deterministic_table_normalizer_v1"
RESULT_ROLE = "v24259_score_first_task_result"
NORMALIZED_KINDS = frozenset({"normalized_primary", "normalized_repaired"})
ALL_KINDS = frozenset(
    {
        "primary",
        "repaired",
        "normalized_primary",
        "normalized_repaired",
        "best_effort_fallback",
        "hard_deadline_fallback",
        "worker_failure_fallback",
    }
)
INDEX_HEADERS = frozenset(
    {
        "#",
        "no",
        "no.",
        "number",
        "index",
        "序号",
        "编号",
        "行号",
    }
)
SEPARATOR = re.compile(r":?-{3,}:?")


def _split_pipe_row(line: str) -> list[str]:
    """Split one Markdown pipe row while preserving escaped literal pipes."""

    raw = str(line).strip()
    if "|" not in raw:
        return []
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in raw:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(current).strip())
    if raw.startswith("|") and cells and cells[0] == "":
        cells.pop(0)
    if raw.endswith("|") and cells and cells[-1] == "":
        cells.pop()
    return cells if len(cells) >= 2 else []


def _is_separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(
        SEPARATOR.fullmatch(str(cell).replace(" ", "")) is not None
        for cell in cells
    )


def _groups(text: str) -> list[list[list[str]]]:
    groups: list[list[list[str]]] = []
    current: list[list[str]] = []
    for raw in str(text or "").replace("\r\n", "\n").splitlines():
        cells = _split_pipe_row(raw)
        if cells:
            current.append(cells)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _header_plan(
    header: Sequence[str], required: Sequence[str]
) -> tuple[str, list[int], int] | None:
    source = [_normalize_column(value) for value in header]
    target = [_normalize_column(value) for value in required]
    if not all(source) or not all(target) or len(set(target)) != len(target):
        return None
    if source == target:
        return "exact", list(range(len(required))), 4
    if len(source) == len(target) and len(set(source)) == len(source):
        if set(source) == set(target):
            return "reordered", [source.index(value) for value in target], 3
        # The prompt already fixed the exact output order.  Equal arity permits
        # positional header replacement but never changes non-empty row cells.
        return "positional_header", list(range(len(required))), 2
    first = str(header[0]).strip().casefold() if header else ""
    if len(source) == len(target) + 1 and first in INDEX_HEADERS:
        remaining = source[1:]
        if remaining == target:
            return "drop_index", list(range(1, len(header))), 3
        if len(set(remaining)) == len(remaining) and set(remaining) == set(target):
            return "drop_index_reordered", [1 + remaining.index(v) for v in target], 3
    return None


def normalize_candidate_table(
    text: str,
    columns: Sequence[str],
    *,
    unknown_marker: str,
) -> tuple[str | None, dict[str, Any]]:
    """Return a canonical table plus content-free structural diagnostics."""

    required = [str(value).strip() for value in columns if str(value).strip()]
    if not required or len(required) > 20 or len(set(map(_normalize_column, required))) != len(required):
        return None, {
            "status": "unrecoverable",
            "mode": "invalid_required_columns",
            "candidate_group_count": 0,
            "input_column_count": 0,
            "output_column_count": len(required),
            "input_row_count": 0,
            "output_row_count": 0,
            "dropped_row_count": 0,
            "filled_empty_cell_count": 0,
        }
    candidates: list[tuple[tuple[int, int, int], list[list[str]], dict[str, Any]]] = []
    groups = _groups(text)
    for group_index, group in enumerate(groups):
        for separator_index, separator in enumerate(group):
            if separator_index < 1 or not _is_separator(separator):
                continue
            header = group[separator_index - 1]
            plan = _header_plan(header, required)
            if plan is None or len(separator) != len(header):
                continue
            mode, mapping, rank = plan
            source_rows = [
                row for row in group[separator_index + 1 :] if not _is_separator(row)
            ]
            normalized_rows: list[list[str]] = []
            dropped = 0
            filled = 0
            for row in source_rows:
                if len(row) == len(header):
                    values = [row[index].strip() for index in mapping]
                elif mode.startswith("drop_index") and len(row) == len(required):
                    # Some generators label an index column but omit it in data.
                    values = [row[index - 1].strip() for index in mapping]
                else:
                    dropped += 1
                    continue
                # The frozen parent validator is intentionally simple and
                # splits escaped pipes as delimiters.  Replacing them with an
                # entity would rewrite a non-empty cell, so defer instead.
                if any("\\|" in value for value in values):
                    dropped += 1
                    continue
                filled += sum(not value for value in values)
                values = [value or unknown_marker for value in values]
                normalized_rows.append(values)
            # Partial row deletion could silently trade completion for recall.
            # Keep the operation all-or-nothing and defer malformed rows to the
            # existing bounded model repair.
            if not normalized_rows or dropped:
                continue
            diagnostics = {
                "status": "normalized",
                "mode": mode,
                "candidate_group_count": len(groups),
                "input_column_count": len(header),
                "output_column_count": len(required),
                "input_row_count": len(source_rows),
                "output_row_count": len(normalized_rows),
                "dropped_row_count": dropped,
                "filled_empty_cell_count": filled,
            }
            candidates.append(
                ((rank, len(normalized_rows), -group_index), normalized_rows, diagnostics)
            )
    if not candidates:
        return None, {
            "status": "unrecoverable",
            "mode": "no_unambiguous_pipe_table",
            "candidate_group_count": len(groups),
            "input_column_count": 0,
            "output_column_count": len(required),
            "input_row_count": 0,
            "output_row_count": 0,
            "dropped_row_count": 0,
            "filled_empty_cell_count": 0,
        }
    _, rows, diagnostics = max(candidates, key=lambda item: item[0])
    table = [
        "| " + " | ".join(required) + " |",
        "| " + " | ".join("---" for _ in required) + " |",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]
    canonical = "```markdown\n" + "\n".join(table) + "\n```"
    diagnostics["status"] = (
        "exact" if str(text or "").strip() == canonical else "normalized"
    )
    return canonical, diagnostics


@dataclasses.dataclass(frozen=True)
class _TextResult:
    text: str


def _replace_text(value: Any, text: str) -> Any:
    if isinstance(value, str):
        return text
    if dataclasses.is_dataclass(value):
        return dataclasses.replace(value, text=text)
    return _TextResult(text=text)


class DeterministicNormalizingModel:
    """Transparent model proxy that rewrites only recoverable table structure."""

    def __init__(
        self,
        inner: Any,
        *,
        question: str,
        limits: ScoreFirstLimits,
    ) -> None:
        self.inner = inner
        self.question = question
        self.limits = limits
        self.columns = extract_visible_columns(question) or []
        self.normalization_enabled = bool(self.columns)
        self.events: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        value = self.inner.complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if json_mode:
            try:
                plan = _validated_plan(
                    parse_json_object(_model_text(value)), self.question, self.limits
                )
            except (TypeError, ValueError):
                return value
            if self.normalization_enabled:
                self.columns = list(plan["columns"])
            return value
        stage = "synthesis" if not self.events else "repair"
        if not self.normalization_enabled:
            self.events.append(
                {
                    "stage": stage,
                    "status": "unrecoverable",
                    "mode": "no_explicit_visible_columns",
                    "candidate_group_count": 0,
                    "input_column_count": 0,
                    "output_column_count": 0,
                    "input_row_count": 0,
                    "output_row_count": 0,
                    "dropped_row_count": 0,
                    "filled_empty_cell_count": 0,
                }
            )
            return value
        marker = "未知" if re.search(r"[\u4e00-\u9fff]", self.question) else "Unknown"
        normalized, diagnostics = normalize_candidate_table(
            _model_text(value),
            self.columns or ["Result"],
            unknown_marker=marker,
        )
        self.events.append({"stage": stage, **diagnostics})
        return _replace_text(value, normalized) if normalized is not None else value


def _promote_result(
    value: Mapping[str, Any], events: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    result = dict(value)
    kind = str(result.get("completion_kind"))
    by_stage = {str(event.get("stage")): event for event in events}
    if kind == "primary" and by_stage.get("synthesis", {}).get("status") == "normalized":
        kind = "normalized_primary"
    elif kind == "repaired" and by_stage.get("repair", {}).get("status") == "normalized":
        kind = "normalized_repaired"
    result["role"] = RESULT_ROLE
    result["policy_id"] = POLICY_ID
    result["completion_kind"] = kind
    result["normalization"] = {
        "parent_policy_id": PARENT_POLICY_ID,
        "events": [dict(event) for event in events],
        "question_candidate_or_cell_content_emitted": False,
        "nonempty_factual_cell_rewritten": False,
        "mapping_gold_category_question_type_evaluator_score_read": False,
    }
    result["prediction_sha256"] = hashlib.sha256(
        str(result["prediction"]).encode("utf-8")
    ).hexdigest()
    return result


def run_v24259_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    monotonic: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    policy = limits or ScoreFirstLimits()
    policy.validate()
    proxy = DeterministicNormalizingModel(
        model, question=visible["question"], limits=policy
    )
    kwargs: dict[str, Any] = {
        "model": proxy,
        "search": search,
        "limits": policy,
        "progress": progress,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent = run_score_first_task(visible, **kwargs)
    result = _promote_result(parent, proxy.events)
    validate_v24259_result(result)
    return result


def build_v24259_fallback_result(
    task: Mapping[str, Any], **kwargs: Any
) -> dict[str, Any]:
    parent = build_score_first_fallback_result(task, **kwargs)
    result = _promote_result(parent, [])
    validate_v24259_result(result)
    return result


def validate_v24259_result(value: Mapping[str, Any]) -> None:
    if value.get("role") != RESULT_ROLE or value.get("policy_id") != POLICY_ID:
        raise ValueError("V2.42.59 result identity drifted")
    kind = value.get("completion_kind")
    if kind not in ALL_KINDS:
        raise ValueError("V2.42.59 completion kind drifted")
    normalization = value.get("normalization")
    if (
        not isinstance(normalization, Mapping)
        or normalization.get("parent_policy_id") != PARENT_POLICY_ID
        or normalization.get("question_candidate_or_cell_content_emitted") is not False
        or normalization.get("nonempty_factual_cell_rewritten") is not False
        or normalization.get(
            "mapping_gold_category_question_type_evaluator_score_read"
        )
        is not False
        or not isinstance(normalization.get("events"), list)
    ):
        raise ValueError("V2.42.59 normalization receipt drifted")
    allowed_event_keys = {
        "stage",
        "status",
        "mode",
        "candidate_group_count",
        "input_column_count",
        "output_column_count",
        "input_row_count",
        "output_row_count",
        "dropped_row_count",
        "filled_empty_cell_count",
    }
    for event in normalization["events"]:
        if (
            not isinstance(event, Mapping)
            or set(event) != allowed_event_keys
            or event.get("stage") not in {"synthesis", "repair"}
            or event.get("status") not in {"exact", "normalized", "unrecoverable"}
        ):
            raise ValueError("V2.42.59 normalization event is not content-free")
    parent = dict(value)
    parent.pop("normalization", None)
    parent["role"] = "v24257_score_first_task_result"
    parent["policy_id"] = PARENT_POLICY_ID
    if kind == "normalized_primary":
        parent["completion_kind"] = "primary"
    elif kind == "normalized_repaired":
        parent["completion_kind"] = "repaired"
    validate_score_first_result(parent)
