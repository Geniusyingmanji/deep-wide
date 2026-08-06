"""Post-freeze evaluator-only utilities for the V2.46.40 ROR gate."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24640_ror_external_contract import ENTITY_GROUPS, SELECTED_COUNT, visible_task


GOLD = Path("evaluation/v24640_ror_gold_v1.csv")
PROVENANCE = Path("evaluation/v24640_ror_gold_provenance_v1.json")
ARMS = ("baseline", "evidence_constrained")
COLUMNS = ("Organization", "ROR ID", "Country code")


def gold_rows(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or tuple(reader.fieldnames) != ("opaque_id", *COLUMNS):
        raise ValueError("V2.46.40 gold schema drifted")
    rows = [
        {key: str(value or "").strip() for key, value in row.items()} for row in reader
    ]
    pairs = [
        (visible_task(index)["opaque_id"], entity)
        for index, group in enumerate(ENTITY_GROUPS, 1)
        for entity in group
    ]
    if len(rows) != 48 or [
        (row["opaque_id"], row["Organization"]) for row in rows
    ] != pairs:
        raise ValueError("V2.46.40 gold denominator or identity drifted")
    return rows


def evaluate_prediction(
    prediction: str, expected: Sequence[Mapping[str, str]]
) -> dict[str, Any]:
    lines = [
        line.strip() for line in str(prediction).replace("\r\n", "\n").splitlines()
    ]
    rows = [
        [cell.strip() for cell in line[1:-1].split("|")]
        for line in lines
        if line.startswith("|") and line.endswith("|")
    ]
    if len(rows) < 3 or tuple(rows[0]) != COLUMNS:
        return {
            "exact_table_success": 0,
            "entity_recall": 0.0,
            "row_f1": 0.0,
            "item_f1": 0.0,
            "column_f1": 0.0,
            "composite": 0.0,
            "unknown_value_cells": 0,
        }
    data = [row for row in rows[2:] if len(row) == 3 and all(row)]

    def norm(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value).casefold())

    def norm_ror(value: object) -> str:
        raw = str(value).strip().casefold().rstrip("/")
        if raw.startswith("https://ror.org/"):
            raw = raw.rsplit("/", 1)[-1]
        return norm(raw)

    gold = {norm(row["Organization"]): row for row in expected}
    predicted = {norm(row[0]): row for row in data if norm(row[0])}
    true_entities = len(set(gold) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(gold)
    row_f1 = (
        2 * precision * recall / (precision + recall) if precision + recall else 0.0
    )
    item_true = 0
    unknown = 0
    for key, row in predicted.items():
        unknown += sum(
            cell.casefold() in {"unknown", "未知", "n/a", "na", "-", "—"}
            for cell in row[1:]
        )
        if key in gold:
            item_true += int(norm_ror(row[1]) == norm_ror(gold[key]["ROR ID"]))
            item_true += int(norm(row[2]) == norm(gold[key]["Country code"]))
    predicted_items = len(predicted) * 2
    gold_items = len(gold) * 2
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = (
        2 * item_precision * item_recall / (item_precision + item_recall)
        if item_precision + item_recall
        else 0.0
    )
    exact = int(
        len(data) == len(expected)
        and true_entities == len(expected)
        and item_true == gold_items
    )
    composite = (recall + row_f1 + item_f1 + 1.0) / 4
    return {
        "exact_table_success": exact,
        "entity_recall": recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": 1.0,
        "composite": composite,
        "unknown_value_cells": unknown,
    }


def evaluate_frozen_rows(
    predictions: Sequence[Mapping[str, Any]], gold: Sequence[Mapping[str, str]]
) -> dict[str, Any]:
    by_task: dict[str, list[Mapping[str, str]]] = {}
    for row in gold:
        by_task.setdefault(str(row["opaque_id"]), []).append(row)
    metrics = {arm: [] for arm in ARMS}
    for row in predictions:
        opaque_id = str(row.get("opaque_id", ""))
        arms = row.get("predictions")
        if (
            opaque_id not in by_task
            or not isinstance(arms, Mapping)
            or set(arms) != set(ARMS)
        ):
            raise ValueError("V2.46.40 frozen prediction drifted")
        for arm in ARMS:
            metrics[arm].append(evaluate_prediction(str(arms[arm]), by_task[opaque_id]))
    if len(predictions) != SELECTED_COUNT:
        raise ValueError("V2.46.40 fixed denominator drifted")
    aggregates = {}
    for arm, rows in metrics.items():
        aggregates[arm] = {
            "tasks": SELECTED_COUNT,
            "exact_table_successes": sum(row["exact_table_success"] for row in rows),
            **{
                key: sum(float(row[key]) for row in rows) / SELECTED_COUNT
                for key in (
                    "entity_recall",
                    "row_f1",
                    "item_f1",
                    "column_f1",
                    "composite",
                )
            },
            "unknown_value_cells": sum(row["unknown_value_cells"] for row in rows),
        }
    baseline = aggregates["baseline"]
    candidate = aggregates["evidence_constrained"]
    delta = {
        key: candidate[key] - baseline[key]
        for key in (
            "exact_table_successes",
            "entity_recall",
            "row_f1",
            "item_f1",
            "column_f1",
            "composite",
        )
    }
    return {
        "arms": aggregates,
        "candidate_minus_baseline": delta,
        "gate_passed": delta["exact_table_successes"] > 0
        and delta["composite"] >= 0
        and delta["item_f1"] >= 0,
    }


__all__ = [
    "ARMS",
    "COLUMNS",
    "GOLD",
    "PROVENANCE",
    "evaluate_frozen_rows",
    "evaluate_prediction",
    "gold_rows",
]
