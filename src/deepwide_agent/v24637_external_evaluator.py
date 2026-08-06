"""Post-freeze evaluator-only contracts for the V2.46.37 external gate."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24637_external_contract import ENTITY_GROUPS, SELECTED_COUNT, visible_task


GOLD = Path("evaluation/v24637_ourairports_gold_v1.csv")
OURAIRPORTS_COMMIT = "fbe34ca80026cb3aa4e4b221046e08585881c82b"
OURAIRPORTS_SNAPSHOT_SHA256 = "7b8ee15a5e0943e4f395742c9c274524ec89b4707376939f4198b1343fe078f9"
OURAIRPORTS_URL = f"https://raw.githubusercontent.com/davidmegginson/ourairports-data/{OURAIRPORTS_COMMIT}/airports.csv"
ARMS = ("baseline", "coverage_ledger")
COLUMNS = ("Airport", "ICAO code", "IATA code")
UNKNOWN = frozenset({"", "-", "—", "?", "n/a", "na", "none", "null", "unknown", "未知", "不详"})


def gold_rows(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    expected = {"opaque_id", *COLUMNS}
    if reader.fieldnames is None or set(reader.fieldnames) != expected:
        raise ValueError("V2.46.37 gold schema drifted")
    rows = [{key: str(value or "").strip() for key, value in row.items()} for row in reader]
    if len(rows) != SELECTED_COUNT * 8:
        raise ValueError("V2.46.37 gold row count drifted")
    pairs = [(visible_task(index)["opaque_id"], entity) for index, group in enumerate(ENTITY_GROUPS, 1) for entity in group]
    if [(row["opaque_id"], row["Airport"]) for row in rows] != pairs:
        raise ValueError("V2.46.37 gold identity vector drifted")
    if any(re.fullmatch(r"[A-Z0-9]{4}", row["ICAO code"]) is None or re.fullmatch(r"[A-Z]{3}", row["IATA code"]) is None for row in rows):
        raise ValueError("V2.46.37 gold code value drifted")
    return rows


def _cells(line: str) -> list[str]:
    raw = line.strip()
    if not raw.startswith("|") or not raw.endswith("|"):
        return []
    return [item.strip() for item in raw[1:-1].split("|")]


def parse_table(prediction: str) -> tuple[list[str], list[list[str]]] | None:
    lines = [line.strip() for line in str(prediction).replace("\r\n", "\n").splitlines()]
    rows = [_cells(line) for line in lines if line.startswith("|") and line.endswith("|")]
    if len(rows) < 3 or tuple(rows[0]) != COLUMNS:
        return None
    if len(rows[1]) != len(COLUMNS) or any(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is None for cell in rows[1]):
        return None
    values = [row for row in rows[2:] if len(row) == len(COLUMNS) and all(row)]
    return rows[0], values


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def evaluate_prediction(prediction: str, expected: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    parsed = parse_table(prediction)
    if parsed is None:
        return {
            "parse_ok": False, "exact_table_success": 0, "entity_recall": 0.0,
            "row_f1": 0.0, "item_f1": 0.0, "column_f1": 0.0,
            "composite": 0.0, "unknown_value_cells": 0,
        }
    header, rows = parsed
    gold_by_entity = {_norm(row["Airport"]): row for row in expected}
    pred_by_entity = {_norm(row[0]): row for row in rows if _norm(row[0])}
    entity_tp = len(set(gold_by_entity) & set(pred_by_entity))
    precision = entity_tp / len(pred_by_entity) if pred_by_entity else 0.0
    recall = entity_tp / len(gold_by_entity) if gold_by_entity else 0.0
    row_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    value_tp = 0
    value_pred = len(pred_by_entity) * 2
    value_gold = len(gold_by_entity) * 2
    unknown = 0
    for key, pred in pred_by_entity.items():
        expected_row = gold_by_entity.get(key)
        unknown += sum(str(cell).casefold() in UNKNOWN for cell in pred[1:])
        if expected_row is None:
            continue
        value_tp += int(_norm(pred[1]) == _norm(expected_row["ICAO code"]))
        value_tp += int(_norm(pred[2]) == _norm(expected_row["IATA code"]))
    item_precision = value_tp / value_pred if value_pred else 0.0
    item_recall = value_tp / value_gold if value_gold else 0.0
    item_f1 = 2 * item_precision * item_recall / (item_precision + item_recall) if item_precision + item_recall else 0.0
    entity_recall = recall
    column_f1 = 1.0 if tuple(header) == COLUMNS else 0.0
    exact = int(len(rows) == len(expected) and entity_tp == len(expected) and value_tp == value_gold)
    composite = (entity_recall + row_f1 + item_f1 + column_f1) / 4
    return {
        "parse_ok": True, "exact_table_success": exact,
        "entity_recall": round(entity_recall, 12), "row_f1": round(row_f1, 12),
        "item_f1": round(item_f1, 12), "column_f1": round(column_f1, 12),
        "composite": round(composite, 12), "unknown_value_cells": unknown,
    }


def evaluate_frozen_rows(predictions: Sequence[Mapping[str, Any]], gold: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    gold_by_task: dict[str, list[Mapping[str, str]]] = {}
    for row in gold:
        gold_by_task.setdefault(str(row["opaque_id"]), []).append(row)
    per_arm = {arm: [] for arm in ARMS}
    for row in predictions:
        opaque_id = str(row.get("opaque_id", ""))
        arms = row.get("predictions")
        if opaque_id not in gold_by_task or not isinstance(arms, Mapping) or set(arms) != set(ARMS):
            raise ValueError("V2.46.37 frozen prediction row drifted")
        for arm in ARMS:
            metrics = evaluate_prediction(str(arms[arm]), gold_by_task[opaque_id])
            per_arm[arm].append(metrics)
    if len(predictions) != SELECTED_COUNT:
        raise ValueError("V2.46.37 frozen denominator drifted")
    aggregates: dict[str, dict[str, Any]] = {}
    for arm, rows in per_arm.items():
        aggregates[arm] = {
            "tasks": SELECTED_COUNT,
            "exact_table_successes": sum(row["exact_table_success"] for row in rows),
            "exact_table_success_rate": sum(row["exact_table_success"] for row in rows) / SELECTED_COUNT,
            **{key: sum(float(row[key]) for row in rows) / SELECTED_COUNT for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")},
            "unknown_value_cells": sum(row["unknown_value_cells"] for row in rows),
        }
    base, candidate = aggregates[ARMS[0]], aggregates[ARMS[1]]
    delta = {
        "exact_table_successes": candidate["exact_table_successes"] - base["exact_table_successes"],
        "composite": candidate["composite"] - base["composite"],
        "entity_recall": candidate["entity_recall"] - base["entity_recall"],
        "row_f1": candidate["row_f1"] - base["row_f1"],
        "item_f1": candidate["item_f1"] - base["item_f1"],
        "column_f1": candidate["column_f1"] - base["column_f1"],
    }
    go = delta["exact_table_successes"] > 0 and delta["composite"] >= 0
    return {"arms": aggregates, "candidate_minus_baseline": delta, "gate_passed": go}


__all__ = [
    "ARMS", "COLUMNS", "GOLD", "OURAIRPORTS_COMMIT", "OURAIRPORTS_SNAPSHOT_SHA256",
    "OURAIRPORTS_URL", "evaluate_frozen_rows", "evaluate_prediction", "gold_rows", "parse_table",
]
