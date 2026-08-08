#!/usr/bin/env python3
"""Post-freeze evaluator for the V2.49.25 sparse target--value gate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24925_sparse_target_value_external_contract as contract  # noqa: E402
from scripts import evaluate_v24923_target_value_external as base  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("V2.49.25 evaluator expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.25 evaluator expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20, check=True).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.49.25 evaluator requires clean pushed HEAD")


def build_gold(tasks: list[dict[str, Any]], pages: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    # Reuse only the generic Markdown/numeric evaluator primitives; bind them
    # to the V2.49.25 task and column contract here.
    page_values = []
    raw_pages = pages.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != len(contract.TARGETS):
        raise RuntimeError("V2.49.25 evaluator page vector drifted")
    for page in raw_pages:
        columns, rows = base._matrix(str(page.get("content", "")))
        if len(columns) != 3:
            raise RuntimeError("V2.49.25 evaluator source table drifted")
        page_values.append({row[1]: row[2] for row in rows if len(row) == 3 and len(row[1]) == 3})
    output = {}
    for task in contract.validate_task_vector(tasks):
        output[task["opaque_id"]] = [
            {
                "Country": name,
                **{contract.visible_columns()[index + 1]: page_values[index][iso3] for index in range(len(contract.TARGETS))},
            }
            for name, iso3 in contract.parse_visible_countries(task["question"])
        ]
    return output


def evaluate_prediction(prediction: str, gold: list[dict[str, str]]) -> dict[str, float | int]:
    columns, rows = base._matrix(prediction)
    expected_columns = contract.visible_columns()
    if columns != expected_columns:
        rows = []
    expected = {base._norm(row["Country"]): row for row in gold}
    predicted = {base._norm(row[0]): row for row in rows if len(row) == len(columns) and base._norm(row[0])}
    true_entities = len(set(expected) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(expected)
    row_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    item_true = 0
    for key, row in predicted.items():
        if key in expected:
            item_true += sum(base._numeric_equal(row[index], expected[key][columns[index]]) for index in range(1, len(columns)))
    predicted_items = len(predicted) * len(contract.TARGETS)
    gold_items = len(expected) * len(contract.TARGETS)
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = 2 * item_precision * item_recall / (item_precision + item_recall) if item_precision + item_recall else 0.0
    exact = int(len(rows) == len(expected) and true_entities == len(expected) and item_true == gold_items)
    column_f1 = 1.0 if columns == expected_columns else 0.0
    return {"exact_table_success": exact, "entity_recall": recall, "row_f1": row_f1, "item_f1": item_f1, "column_f1": column_f1, "composite": (recall + row_f1 + item_f1 + column_f1) / 4}


def evaluate_rows(rows: list[dict[str, Any]], gold: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    values = {arm: [] for arm in contract.ARMS}
    seen = set()
    for row in rows:
        opaque, predictions = str(row.get("opaque_id", "")), row.get("predictions")
        if opaque in seen or opaque not in gold or not isinstance(predictions, dict) or set(predictions) != set(contract.ARMS):
            raise RuntimeError("V2.49.25 prediction row drifted")
        seen.add(opaque)
        for arm in contract.ARMS:
            values[arm].append(evaluate_prediction(str(predictions[arm]), gold[opaque]))
    if len(seen) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.49.25 evaluation denominator drifted")
    aggregate = {}
    for arm, metrics in values.items():
        aggregate[arm] = {"tasks": contract.SELECTED_COUNT, "exact_table_successes": sum(row["exact_table_success"] for row in metrics), **{key: sum(float(row[key]) for row in metrics) / contract.SELECTED_COUNT for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")}}
    delta = {key: aggregate[contract.ARMS[1]][key] - aggregate[contract.ARMS[0]][key] for key in ("exact_table_successes", "entity_recall", "row_f1", "item_f1", "column_f1", "composite")}
    return {"arms": aggregate, "sparse_target_value_30k_minus_target_value_30k": delta}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "evaluate", "postaudit"))
    args = parser.parse_args()
    _clean_pushed()
    protocol, forward, audit = _read(ROOT / contract.PROTOCOL), _read(ROOT / contract.FORWARD_RESULT), _read(ROOT / contract.FORWARD_AUDIT)
    if (
        protocol.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(protocol, "protocol_payload_sha256")
        or not contract.sealed(forward, "result_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("authorization", {}).get("postfreeze_external_evaluator_protocol") is not True
        or audit.get("mechanism_gate", {}).get("passed") is not True
    ):
        raise RuntimeError("V2.49.25 evaluator parent drifted")
    if args.command == "preregister":
        value = {
            "artifact_version": 1,
            "role": "v24925_sparse_target_value_external_evaluator_preregistration",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected_tasks": contract.SELECTED_COUNT,
            "selected_arm_predictions": contract.SELECTED_COUNT * len(contract.ARMS),
            "primary_comparison": "sparse_target_value_30k_minus_target_value_30k",
            "go_rule": "mechanism_engaged_and_strict_exact_gain_and_all_quality_nonregression_and_zero_failure_increase",
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
            "gold_derived_only_after_prediction_freeze_from_frozen_public_pages": True,
            "authorization": {"one_external_evaluation": True, "public_exact220": False, "sota_claim": False},
        }
        value["protocol_payload_sha256"] = contract.payload_sha256(value)
        path = contract.EVALUATOR_PROTOCOL
    elif args.command == "evaluate":
        evaluator_protocol = _read(ROOT / contract.EVALUATOR_PROTOCOL)
        if not contract.sealed(evaluator_protocol, "protocol_payload_sha256") or evaluator_protocol.get("authorization", {}).get("one_external_evaluation") is not True:
            raise RuntimeError("V2.49.25 evaluator protocol drifted")
        tasks = _read_jsonl(ROOT / contract.VISIBLE_TASKS)
        pages = _read(ROOT / contract.FROZEN_PAGES)
        predictions = _read_jsonl(ROOT / contract.PREDICTIONS)
        metrics = evaluate_rows(predictions, build_gold(tasks, pages))
        delta = metrics["sparse_target_value_30k_minus_target_value_30k"]
        passed = (
            forward.get("candidate_mechanism_engaged") is True
            and forward.get("projection_unequal_tasks", 0) >= 8
            and forward.get("failure_as_zero_tasks") == 0
            and delta["exact_table_successes"] > 0
            and all(delta[key] >= 0 for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite"))
        )
        value = {
            "artifact_version": 1,
            "role": "v24925_sparse_target_value_external_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "status": "sparse_target_value_external_go" if passed else "sparse_target_value_external_no_go",
            "passed": passed,
            "metrics": metrics,
            "mechanism": {"projection_unequal_tasks": forward["projection_unequal_tasks"], "dropped_table_rows": forward["candidate_dropped_table_rows"], "engaged": forward["candidate_mechanism_engaged"]},
            "fixed_denominator_failure_as_zero": True,
            "claim_scope": {"benchmark_external_quality_measured": True, "deepwidebench_quality_measured": False, "entropy_or_signed_credit_validated": False, "sota_supported": False},
            "authorization": {"public_exact220_candidate_design": passed, "public_exact220_launch": False, "sota_claim": False},
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
            "role": "v24925_sparse_target_value_external_postresult_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "result_sha256": contract.sha256(ROOT / contract.RESULT),
            "findings": findings,
            "audit_valid": not findings,
            "protected_watchers": contract.protected_watcher_snapshot(),
            "network_model_fetch_or_deepwidebench_evaluator_called_by_audit": False,
            "authorization": {"public_exact220_candidate_design": not findings and result.get("passed") is True, "public_exact220_launch": False, "sota_claim": False},
        }
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        path = contract.POSTAUDIT
    _publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "status": value.get("status"), "passed": value.get("passed"), "metrics": value.get("metrics"), "authorization": value.get("authorization")}, sort_keys=True))


if __name__ == "__main__":
    main()
