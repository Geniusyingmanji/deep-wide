"""Post-freeze evaluator-only utilities for the V2.46.42 ROR gate."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24640_ror_external_evaluator import evaluate_prediction
from .v24642_ror_external_contract import ENTITY_GROUPS, SELECTED_COUNT, visible_task


GOLD = Path("evaluation/v24642_ror_gold_v1.csv")
PROVENANCE = Path("evaluation/v24642_ror_gold_provenance_v1.json")
ARMS = ("baseline", "deterministic_pair")
COLUMNS = ("Organization", "ROR ID", "Country code")


def gold_rows(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or tuple(reader.fieldnames) != ("opaque_id", *COLUMNS):
        raise ValueError("V2.46.42 gold schema drifted")
    rows = [{key: str(value or "").strip() for key, value in row.items()} for row in reader]
    pairs = [
        (visible_task(index)["opaque_id"], entity)
        for index, group in enumerate(ENTITY_GROUPS, 1)
        for entity in group
    ]
    if len(rows) != 48 or [(row["opaque_id"], row["Organization"]) for row in rows] != pairs:
        raise ValueError("V2.46.42 gold denominator or identity drifted")
    return rows


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
        if opaque_id not in by_task or not isinstance(arms, Mapping) or set(arms) != set(ARMS):
            raise ValueError("V2.46.42 frozen prediction drifted")
        for arm in ARMS:
            metrics[arm].append(evaluate_prediction(str(arms[arm]), by_task[opaque_id]))
    if len(predictions) != SELECTED_COUNT:
        raise ValueError("V2.46.42 fixed denominator drifted")
    aggregates = {}
    for arm, rows in metrics.items():
        aggregates[arm] = {
            "tasks": SELECTED_COUNT,
            "exact_table_successes": sum(row["exact_table_success"] for row in rows),
            **{
                key: sum(float(row[key]) for row in rows) / SELECTED_COUNT
                for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")
            },
            "unknown_value_cells": sum(row["unknown_value_cells"] for row in rows),
        }
    baseline = aggregates["baseline"]
    candidate = aggregates["deterministic_pair"]
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
