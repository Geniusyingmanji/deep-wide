#!/usr/bin/env python3
"""Post-freeze evaluator for the V2.49.23 external gate."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24923_target_value_external_contract as contract  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.49.23 evaluator expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.23 evaluator expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.49.23 evaluator expected ordinary JSONL")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.49.23 evaluator expected JSONL objects")
    return rows


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.23 evaluator requires clean pushed HEAD")


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _numeric_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).strip()) == Decimal(str(right).strip())
    except (InvalidOperation, ValueError):
        return False


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(lines) < 2:
        return [], []
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    columns = cells[0]
    rows = [row for row in cells[2:] if len(row) == len(columns)]
    return columns, rows


def build_gold(
    tasks: Sequence[Mapping[str, Any]],
    pages: Mapping[str, Any],
) -> dict[str, list[dict[str, str]]]:
    page_values: list[dict[str, str]] = []
    raw_pages = pages.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != len(contract.TARGETS):
        raise RuntimeError("V2.49.23 evaluator page vector drifted")
    for page in raw_pages:
        if not isinstance(page, Mapping):
            raise RuntimeError("V2.49.23 evaluator page drifted")
        columns, rows = _matrix(str(page.get("content", "")))
        if len(columns) != 3:
            raise RuntimeError("V2.49.23 evaluator source table drifted")
        values = {}
        for row in rows:
            if len(row) == 3 and len(row[1]) == 3:
                values[row[1]] = row[2]
        page_values.append(values)
    output: dict[str, list[dict[str, str]]] = {}
    for task in contract.validate_task_vector(tasks):
        output[task["opaque_id"]] = [
            {
                "Country": name,
                **{
                    contract.visible_columns()[index + 1]: page_values[index][iso3]
                    for index in range(len(contract.TARGETS))
                },
            }
            for name, iso3 in contract.parse_visible_countries(task["question"])
        ]
    return output


def evaluate_prediction(
    prediction: str, gold: Sequence[Mapping[str, str]]
) -> dict[str, float | int]:
    expected_columns = contract.visible_columns()
    columns, rows = _matrix(prediction)
    if columns != expected_columns:
        rows = []
    expected = {_norm(row["Country"]): row for row in gold}
    predicted = {
        _norm(row[0]): row
        for row in rows
        if len(row) == len(columns) and _norm(row[0])
    }
    true_entities = len(set(expected) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(expected)
    row_f1 = (
        2 * precision * recall / (precision + recall) if precision + recall else 0.0
    )
    item_true = 0
    for key, row in predicted.items():
        if key not in expected:
            continue
        item_true += sum(
            _numeric_equal(row[index], expected[key][columns[index]])
            for index in range(1, len(columns))
        )
    predicted_items = len(predicted) * len(contract.TARGETS)
    gold_items = len(expected) * len(contract.TARGETS)
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = (
        2 * item_precision * item_recall / (item_precision + item_recall)
        if item_precision + item_recall
        else 0.0
    )
    exact = int(
        len(rows) == len(expected)
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
    rows: Sequence[Mapping[str, Any]],
    gold: Mapping[str, Sequence[Mapping[str, str]]],
) -> dict[str, Any]:
    values = {arm: [] for arm in contract.ARMS}
    seen = set()
    for row in rows:
        opaque = str(row.get("opaque_id", ""))
        predictions = row.get("predictions")
        if (
            opaque in seen
            or opaque not in gold
            or not isinstance(predictions, Mapping)
            or set(predictions) != set(contract.ARMS)
        ):
            raise RuntimeError("V2.49.23 prediction row drifted")
        seen.add(opaque)
        for arm in contract.ARMS:
            values[arm].append(
                evaluate_prediction(str(predictions[arm]), gold[opaque])
            )
    if len(seen) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.49.23 evaluation denominator drifted")
    aggregate = {}
    for arm, metrics in values.items():
        aggregate[arm] = {
            "tasks": contract.SELECTED_COUNT,
            "exact_table_successes": sum(
                row["exact_table_success"] for row in metrics
            ),
            **{
                key: sum(float(row[key]) for row in metrics)
                / contract.SELECTED_COUNT
                for key in (
                    "entity_recall",
                    "row_f1",
                    "item_f1",
                    "column_f1",
                    "composite",
                )
            },
        }
    delta = {
        key: aggregate["target_value_30k"][key] - aggregate["parent_30k"][key]
        for key in (
            "exact_table_successes",
            "entity_recall",
            "row_f1",
            "item_f1",
            "column_f1",
            "composite",
        )
    }
    return {"arms": aggregate, "target_value_30k_minus_parent_30k": delta}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "evaluate", "postaudit"))
    args = parser.parse_args()
    _clean_pushed()
    protocol = _read(ROOT / contract.PROTOCOL)
    forward = _read(ROOT / contract.FORWARD_RESULT)
    audit = _read(ROOT / contract.FORWARD_AUDIT)
    if (
        protocol.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(protocol, "protocol_payload_sha256")
        or not contract.sealed(forward, "result_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol"
        )
        is not True
        or audit.get("mechanism_gate", {}).get("passed") is not True
        or forward.get("all_predictions_terminal_before_evaluator_open") is not True
    ):
        raise RuntimeError("V2.49.23 evaluator parent drifted")
    if args.command == "preregister":
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": "v24923_target_value_external_evaluator_preregistration",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected_tasks": contract.SELECTED_COUNT,
            "selected_arm_predictions": contract.SELECTED_COUNT * len(contract.ARMS),
            "primary_comparison": "target_value_30k_minus_parent_30k",
            "go_rule": "mechanism_engaged_and_strict_exact_gain_and_all_quality_nonregression_and_zero_failure_increase",
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
            "gold_derived_only_after_prediction_freeze_from_frozen_public_pages": True,
            "authorization": {
                "one_external_evaluation": True,
                "public_exact220": False,
                "sota_claim": False,
            },
        }
        value["protocol_payload_sha256"] = contract.payload_sha256(value)
        path = contract.EVALUATOR_PROTOCOL
    elif args.command == "evaluate":
        evaluator = _read(ROOT / contract.EVALUATOR_PROTOCOL)
        if (
            not contract.sealed(evaluator, "protocol_payload_sha256")
            or evaluator.get("authorization", {}).get("one_external_evaluation")
            is not True
        ):
            raise RuntimeError("V2.49.23 evaluator protocol drifted")
        tasks = _read_jsonl(ROOT / contract.VISIBLE_TASKS)
        pages = _read(ROOT / contract.FROZEN_PAGES)
        predictions = _read_jsonl(ROOT / contract.PREDICTIONS)
        metrics = evaluate_rows(predictions, build_gold(tasks, pages))
        delta = metrics["target_value_30k_minus_parent_30k"]
        passed = (
            forward.get("candidate_mechanism_engaged") is True
            and forward.get("projection_unequal_tasks", 0) >= 4
            and forward.get("failure_as_zero_tasks") == 0
            and delta["exact_table_successes"] > 0
            and all(
                delta[key] >= 0
                for key in (
                    "entity_recall",
                    "row_f1",
                    "item_f1",
                    "column_f1",
                    "composite",
                )
            )
        )
        value = {
            "artifact_version": 1,
            "role": "v24923_target_value_external_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "status": "target_value_external_go"
            if passed
            else "target_value_external_no_go",
            "passed": passed,
            "metrics": metrics,
            "mechanism": {
                "projection_unequal_tasks": forward["projection_unequal_tasks"],
                "supported_target_value_pairs": forward[
                    "candidate_supported_target_value_pairs"
                ],
                "retained_target_value_pairs": forward[
                    "candidate_retained_target_value_pairs"
                ],
                "engaged": forward["candidate_mechanism_engaged"],
            },
            "fixed_denominator_failure_as_zero": True,
            "claim_scope": {
                "benchmark_external_quality_measured": True,
                "deepwidebench_quality_measured": False,
                "entropy_or_signed_credit_validated": False,
                "sota_supported": False,
            },
            "authorization": {
                "public_exact220_candidate_design": passed,
                "public_exact220_launch": False,
                "sota_claim": False,
            },
        }
        value["result_payload_sha256"] = contract.payload_sha256(value)
        path = contract.RESULT
    else:
        result = _read(ROOT / contract.RESULT)
        findings = []
        if not contract.sealed(result, "result_payload_sha256"):
            findings.append("result_seal_invalid")
        if result.get("fixed_denominator_failure_as_zero") is not True:
            findings.append("failure_policy_drifted")
        value = {
            "artifact_version": 1,
            "role": "v24923_target_value_external_postresult_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "result_sha256": contract.sha256(ROOT / contract.RESULT),
            "findings": findings,
            "audit_valid": not findings,
            "protected_watchers": contract.protected_watcher_snapshot(),
            "network_model_fetch_or_deepwidebench_evaluator_called_by_audit": False,
            "authorization": {
                "public_exact220_candidate_design": not findings
                and result.get("passed") is True,
                "public_exact220_launch": False,
                "sota_claim": False,
            },
        }
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        path = contract.POSTAUDIT
    _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "status": value.get("status"),
                "passed": value.get("passed"),
                "metrics": value.get("metrics"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
