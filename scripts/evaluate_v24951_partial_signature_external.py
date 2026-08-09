#!/usr/bin/env python3
"""Post-freeze evaluator adapter for V2.49.51 native-layout pages."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24951_partial_signature_external_contract as contract  # noqa: E402
from scripts import evaluate_v24940_open_world_ledger_external as parent  # noqa: E402


def _source_rows(page: Mapping[str, Any]) -> list[dict[str, str]]:
    lines = [line for line in str(page.get("content", "")).splitlines() if line]
    if not lines:
        raise RuntimeError("V2.49.51 frozen source page absent")
    headers = [value.strip() for value in lines[0].split("|")]
    expected_native = contract.native_page_columns()
    if headers[: len(expected_native)] != expected_native:
        raise RuntimeError("V2.49.51 native source schema drifted")
    visible = contract.visible_columns()
    output: list[dict[str, str]] = []
    for line in lines[1:]:
        cells = [value.strip() for value in line.split("|")]
        if len(cells) != len(headers):
            raise RuntimeError("V2.49.51 native source row width drifted")
        output.append(
            {
                visible[0]: cells[0],
                visible[1]: cells[1],
                visible[2]: cells[2],
                visible[3]: cells[3],
            }
        )
    if len(output) != contract.PAGE_ROWS_PER_TASK:
        raise RuntimeError("V2.49.51 native source row denominator drifted")
    return output


def _canonical(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _numeric_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).strip()) == Decimal(str(right).strip())
    except (InvalidOperation, ValueError):
        return False


def build_gold(
    tasks: Sequence[Mapping[str, Any]], pages: Mapping[str, Any]
) -> dict[str, list[dict[str, str]]]:
    raw_pages = pages.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.49.51 evaluator page vector drifted")
    validated = contract.validate_task_vector(tasks)
    columns = contract.visible_columns()
    output: dict[str, list[dict[str, str]]] = {}
    seen_entities: set[str] = set()
    for task, page in zip(validated, raw_pages, strict=True):
        cohort = contract.parse_visible_cohort(str(task["question"]))
        selected = [row for row in _source_rows(page) if row[columns[1]] == cohort]
        if len(selected) != contract.ROWS_PER_TASK:
            raise RuntimeError("V2.49.51 evaluator target denominator drifted")
        identities = {_canonical(row[columns[0]]) for row in selected}
        if len(identities) != contract.ROWS_PER_TASK or identities & seen_entities:
            raise RuntimeError("V2.49.51 evaluator target identity drifted")
        seen_entities.update(identities)
        output[str(task["opaque_id"])] = [
            {column: row[column] for column in columns} for row in selected
        ]
    if len(seen_entities) != contract.SELECTED_ENTITY_COUNT:
        raise RuntimeError("V2.49.51 evaluator global target denominator drifted")
    return output


def evaluate_prediction(
    prediction: str, gold: Sequence[Mapping[str, str]]
) -> dict[str, float | int]:
    columns = contract.visible_columns()
    observed_columns, rows = parent._matrix(prediction)
    if observed_columns != columns:
        rows = []
    expected = {_canonical(row[columns[0]]): row for row in gold}
    predicted = {
        _canonical(row[0]): row
        for row in rows
        if len(row) == len(columns) and _canonical(row[0])
    }
    true_entities = len(set(expected) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(expected)
    row_f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    item_true = 0
    for key, row in predicted.items():
        if key not in expected:
            continue
        item_true += int(row[1] == expected[key][columns[1]])
        item_true += int(row[2] == expected[key][columns[2]])
        item_true += int(_numeric_equal(row[3], expected[key][columns[3]]))
    value_columns = len(columns) - 1
    predicted_items = len(predicted) * value_columns
    gold_items = len(expected) * value_columns
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = (
        2 * item_precision * item_recall / (item_precision + item_recall)
        if item_precision + item_recall
        else 0.0
    )
    exact = int(
        len(rows) == len(expected)
        and [_canonical(row[0]) for row in rows] == list(expected)
        and true_entities == len(expected)
        and item_true == gold_items
    )
    column_f1 = 1.0 if observed_columns == columns else 0.0
    return {
        "exact_table_success": exact,
        "entity_recall": recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": (recall + row_f1 + item_f1 + column_f1) / 4,
    }


def main() -> None:
    parent.contract = contract
    parent._source_rows = _source_rows
    parent.build_gold = build_gold
    parent.evaluate_prediction = evaluate_prediction
    parent.main()


if __name__ == "__main__":
    main()
