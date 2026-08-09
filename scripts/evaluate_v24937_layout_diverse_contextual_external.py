#!/usr/bin/env python3
"""Corrected post-freeze evaluator for the V2.49.37 external gate."""

from __future__ import annotations

import copy
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24937_layout_diverse_contextual_external_contract as contract  # noqa: E402
from scripts import evaluate_v24923_target_value_external as base  # noqa: E402


_COLON = re.compile(r"^(.+?)\s+\[([A-Z]{3})\]:\s*(\S.*)$")
_BULLET_EQUALS = re.compile(r"^-\s+(.+?)\s+\[([A-Z]{3})\]\s*=\s*(\S.*)$")
_INHERITED_PUBLISH = base._publish


def build_gold(
    tasks: Sequence[Mapping[str, Any]], pages: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    raw_pages = pages.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != len(contract.TARGETS):
        raise RuntimeError("V2.49.37 evaluator page vector drifted")
    page_values: list[dict[str, str]] = []
    for page, target in zip(raw_pages, contract.TARGETS, strict=True):
        if not isinstance(page, Mapping) or page.get("layout") != target["layout"]:
            raise RuntimeError("V2.49.37 evaluator page layout drifted")
        pattern = (
            _COLON
            if target["layout"] == "markdown_heading_colon_records"
            else _BULLET_EQUALS
        )
        values: dict[str, str] = {}
        for line in str(page.get("content", "")).splitlines():
            match = pattern.match(line.strip())
            if match is not None and match.group(2) not in values:
                values[match.group(2)] = match.group(3).strip()
        if len(values) < 170:
            raise RuntimeError("V2.49.37 evaluator observation capacity drifted")
        page_values.append(values)
    output: dict[str, dict[str, Any]] = {}
    for task in contract.validate_task_vector(tasks):
        entities = contract.parse_visible_entities(task["question"])
        output[task["opaque_id"]] = {
            "entities": [list(item) for item in entities],
            "rows": [
                {
                    "Country": name,
                    **{
                        contract.visible_columns()[index + 1]: page_values[index][iso3]
                        for index in range(len(contract.TARGETS))
                    },
                }
                for name, iso3 in entities
            ],
        }
    return output


def _canonical(rendered: str, entities: Sequence[tuple[str, str]]) -> str | None:
    key = base._norm(rendered)
    matches = {
        base._norm(name)
        for name, iso3 in entities
        if key in {base._norm(name), base._norm(f"{name} [{iso3}]")}
    }
    return next(iter(matches)) if len(matches) == 1 else None


def evaluate_prediction(
    prediction: str,
    gold: Sequence[Mapping[str, str]],
    entities: Sequence[tuple[str, str]],
) -> dict[str, float | int]:
    expected_columns = contract.visible_columns()
    columns, rows = base._matrix(prediction)
    if columns != expected_columns:
        rows = []
    expected = {base._norm(row["Country"]): row for row in gold}
    predicted: dict[str, list[str]] = {}
    duplicates = 0
    for row in rows:
        if len(row) != len(columns):
            continue
        canonical = _canonical(row[0], entities)
        if canonical is None:
            continue
        if canonical in predicted:
            duplicates += 1
            continue
        predicted[canonical] = row
    true_entities = len(set(expected) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(expected)
    row_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    item_true = 0
    for key, row in predicted.items():
        if key in expected:
            item_true += sum(
                base._numeric_equal(row[index], expected[key][columns[index]])
                for index in range(1, len(columns))
            )
    predicted_items = len(predicted) * len(contract.TARGETS)
    gold_items = len(expected) * len(contract.TARGETS)
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = 2 * item_precision * item_recall / (item_precision + item_recall) if item_precision + item_recall else 0.0
    exact = int(
        duplicates == 0
        and len(rows) == len(expected)
        and len(predicted) == len(expected)
        and true_entities == len(expected)
        and item_true == gold_items
    )
    column_f1 = 1.0 if columns == expected_columns else 0.0
    return {
        "exact_table_success": exact,
        "entity_recall": recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": (recall + row_f1 + item_f1 + column_f1) / 4,
    }


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], gold: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    values: dict[str, list[dict[str, float | int]]] = {arm: [] for arm in contract.ARMS}
    seen: set[str] = set()
    for row in rows:
        opaque = str(row.get("opaque_id", ""))
        predictions = row.get("predictions")
        if opaque in seen or opaque not in gold or not isinstance(predictions, Mapping) or set(predictions) != set(contract.ARMS):
            raise RuntimeError("V2.49.37 prediction row drifted")
        seen.add(opaque)
        bundle = gold[opaque]
        entities = [tuple(item) for item in bundle["entities"]]
        for arm in contract.ARMS:
            values[arm].append(evaluate_prediction(str(predictions[arm]), bundle["rows"], entities))
    if len(seen) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.49.37 evaluation denominator drifted")
    aggregate: dict[str, Any] = {}
    for arm, metrics in values.items():
        aggregate[arm] = {
            "tasks": contract.SELECTED_COUNT,
            "exact_table_successes": sum(int(row["exact_table_success"]) for row in metrics),
            **{
                key: sum(float(row[key]) for row in metrics) / contract.SELECTED_COUNT
                for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")
            },
        }
    delta = {
        key: aggregate["target_value_30k"][key] - aggregate["parent_30k"][key]
        for key in ("exact_table_successes", "entity_recall", "row_f1", "item_f1", "column_f1", "composite")
    }
    return {"arms": aggregate, "target_value_30k_minus_parent_30k": delta}


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    copied = copy.deepcopy(dict(value))
    if path == ROOT / contract.EVALUATOR_PROTOCOL:
        copied["role"] = "v24937_layout_diverse_contextual_external_evaluator_preregistration"
        copied["primary_comparison"] = "contextual_record_30k_minus_unicode_total_30k"
        copied["corrected_visible_identity_contract"] = "exact_name_or_exact_name_with_matching_iso3"
        seal = "protocol_payload_sha256"
    elif path == ROOT / contract.RESULT:
        copied["role"] = "v24937_layout_diverse_contextual_external_result"
        copied["status"] = "layout_diverse_contextual_external_go" if copied.get("passed") is True else "layout_diverse_contextual_external_no_go"
        copied["corrected_visible_identity_contract"] = "exact_name_or_exact_name_with_matching_iso3"
        seal = "result_payload_sha256"
    elif path == ROOT / contract.POSTAUDIT:
        copied["role"] = "v24937_layout_diverse_contextual_external_postresult_audit"
        seal = "audit_payload_sha256"
    else:
        raise RuntimeError("V2.49.37 evaluator attempted unknown output")
    copied.pop(seal, None)
    copied[seal] = contract.payload_sha256(copied)
    _INHERITED_PUBLISH(path, copied)


def configure() -> None:
    base.contract = contract
    base.build_gold = build_gold
    base.evaluate_rows = evaluate_rows
    base._publish = _publish


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
