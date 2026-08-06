"""Evaluator-only utilities for the V2.47.33 dual-namespace gate."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .v24640_ror_external_evaluator import evaluate_prediction as evaluate_ror_prediction
from .v24733_dual_namespace_contract import TASK_COUNT, TASKS_PER_CLUSTER, visible_task


ROR_GOLD = Path("evaluation/v24733_ror_gold_v1.csv")
WORLD_BANK_GOLD = Path("evaluation/v24733_worldbank_gold_v1.csv")
PROVENANCE = Path("evaluation/v24733_dual_namespace_gold_provenance_v1.json")
ARMS = ("baseline", "candidate")
ROR_COLUMNS = ("Organization", "ROR ID", "Country code")
WORLD_BANK_COLUMNS = ('Country',
 'Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022',
 'Life expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022')


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _numeric_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).strip()) == Decimal(str(right).strip())
    except (InvalidOperation, ValueError):
        return False


def _csv_rows(text: str, columns: tuple[str, ...], expected: int) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or tuple(reader.fieldnames) != ("opaque_id", *columns):
        raise ValueError("V2.47.33 gold schema drifted")
    rows = [{key: str(value or "").strip() for key, value in row.items()} for row in reader]
    if len(rows) != expected:
        raise ValueError("V2.47.33 gold denominator drifted")
    return rows


def gold_rows(ror_text: str, worldbank_text: str) -> dict[str, list[dict[str, str]]]:
    ror = _csv_rows(ror_text, ROR_COLUMNS, TASKS_PER_CLUSTER * 4)
    worldbank = _csv_rows(worldbank_text, WORLD_BANK_COLUMNS, TASKS_PER_CLUSTER * 4)
    expected_ror = {visible_task(index)["opaque_id"] for index in range(1, TASKS_PER_CLUSTER + 1)}
    expected_wb = {visible_task(index)["opaque_id"] for index in range(TASKS_PER_CLUSTER + 1, TASK_COUNT + 1)}
    if {row["opaque_id"] for row in ror} != expected_ror or {row["opaque_id"] for row in worldbank} != expected_wb:
        raise ValueError("V2.47.33 gold task identity drifted")
    return {"ror": ror, "worldbank": worldbank}


def evaluate_worldbank_prediction(prediction: str, expected: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    lines = [line.strip() for line in str(prediction).replace("\r\n", "\n").splitlines()]
    rows = [[cell.strip() for cell in line[1:-1].split("|")] for line in lines if line.startswith("|") and line.endswith("|")]
    if len(rows) < 3 or tuple(rows[0]) != WORLD_BANK_COLUMNS:
        return {"exact_table_success": 0, "entity_recall": 0.0, "row_f1": 0.0, "item_f1": 0.0, "column_f1": 0.0, "composite": 0.0, "unknown_value_cells": 0}
    data = [row for row in rows[2:] if len(row) == len(WORLD_BANK_COLUMNS) and all(row)]
    gold = {_norm(row["Country"]): row for row in expected}
    predicted = {_norm(row[0]): row for row in data if _norm(row[0])}
    true_entities = len(set(gold) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(gold)
    row_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    item_true = 0
    unknown = 0
    for key, row in predicted.items():
        unknown += sum(cell.casefold() in {"unknown", "未知", "n/a", "na", "-", "—"} for cell in row[1:])
        if key in gold:
            item_true += sum(_numeric_equal(row[index], gold[key][WORLD_BANK_COLUMNS[index]]) for index in (1, 2))
    predicted_items = len(predicted) * 2
    gold_items = len(gold) * 2
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = 2 * item_precision * item_recall / (item_precision + item_recall) if item_precision + item_recall else 0.0
    exact = int(len(data) == len(expected) and true_entities == len(expected) and item_true == gold_items)
    composite = (recall + row_f1 + item_f1 + 1.0) / 4
    return {"exact_table_success": exact, "entity_recall": recall, "row_f1": row_f1, "item_f1": item_f1, "column_f1": 1.0, "composite": composite, "unknown_value_cells": unknown}


def evaluate_frozen_rows(predictions: Sequence[Mapping[str, Any]], gold: Mapping[str, Sequence[Mapping[str, str]]]) -> dict[str, Any]:
    by_task = {str(row["opaque_id"]): ("ror", row) for row in gold["ror"]}
    for row in gold["worldbank"]:
        by_task[str(row["opaque_id"])] = ("worldbank", row)
    grouped: dict[str, list[Mapping[str, str]]] = {}
    namespaces: dict[str, str] = {}
    for namespace, rows in gold.items():
        for row in rows:
            opaque_id = str(row["opaque_id"])
            grouped.setdefault(opaque_id, []).append(row)
            namespaces[opaque_id] = namespace
    metrics = {namespace: {arm: [] for arm in ARMS} for namespace in ("ror", "worldbank")}
    seen = set()
    for row in predictions:
        opaque_id = str(row.get("opaque_id", "")); arms = row.get("predictions")
        if opaque_id in seen or opaque_id not in grouped or not isinstance(arms, Mapping) or set(arms) != set(ARMS):
            raise ValueError("V2.47.33 frozen prediction drifted")
        seen.add(opaque_id); namespace = namespaces[opaque_id]
        for arm in ARMS:
            metric = evaluate_ror_prediction(str(arms[arm]), grouped[opaque_id]) if namespace == "ror" else evaluate_worldbank_prediction(str(arms[arm]), grouped[opaque_id])
            metrics[namespace][arm].append(metric)
    if len(seen) != TASK_COUNT:
        raise ValueError("V2.47.33 prediction denominator drifted")
    output = {}
    for namespace in metrics:
        output[namespace] = {}
        for arm, rows in metrics[namespace].items():
            output[namespace][arm] = {
                "tasks": TASKS_PER_CLUSTER,
                "exact_table_successes": sum(row["exact_table_success"] for row in rows),
                **{key: sum(float(row[key]) for row in rows) / TASKS_PER_CLUSTER for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")},
                "unknown_value_cells": sum(row["unknown_value_cells"] for row in rows),
            }
        output[namespace]["candidate_minus_baseline"] = {key: output[namespace]["candidate"][key] - output[namespace]["baseline"][key] for key in ("exact_table_successes", "entity_recall", "row_f1", "item_f1", "column_f1", "composite")}
    output["gate_passed"] = all(
        output[namespace]["candidate_minus_baseline"]["exact_table_successes"] > 0
        and output[namespace]["candidate_minus_baseline"]["composite"] >= 0
        and output[namespace]["candidate_minus_baseline"]["item_f1"] >= 0
        for namespace in ("ror", "worldbank")
    )
    return output


__all__ = ["ARMS", "PROVENANCE", "ROR_GOLD", "WORLD_BANK_GOLD", "evaluate_frozen_rows", "evaluate_worldbank_prediction", "gold_rows"]
