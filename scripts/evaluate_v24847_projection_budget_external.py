#!/usr/bin/env python3
"""Post-freeze evaluator and audit for V2.48.47."""

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

from deepwide_agent import v24847_projection_budget_external_contract as contract  # noqa: E402


PRIVATE = Path(
    "evaluation/v24829_target_cell_disjoint_worldbank_population_private_v1_20260807.json"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v24847_projection_budget_external_evaluator_preregistration_v1_{contract.DATE}.json"
)
RESULT = Path(
    f"results/v24847_projection_budget_external_result_v1_{contract.DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24847_projection_budget_external_postresult_audit_v1_{contract.DATE}.json"
)


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("V2.48.47 evaluator expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.47 evaluator expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def clean() -> None:
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git("rev-parse", "target/main"):
        raise RuntimeError("V2.48.47 evaluator requires clean pushed HEAD")


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _numeric_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).strip()) == Decimal(str(right).strip())
    except (InvalidOperation, ValueError):
        return False


def _columns() -> list[str]:
    return [
        "Country",
        *(f"{target['label']} [{target['indicator']}] @{target['year']}" for target in contract.TARGETS),
    ]


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|") and line.strip().endswith("|")]
    if len(lines) < 2:
        return [], []
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    columns = cells[0]
    rows = [row for row in cells[2:] if len(row) == len(columns)]
    return columns, rows


def _gold(private: Mapping[str, Any]) -> dict[str, list[dict[str, str]]]:
    groups = private.get("groups")
    if not isinstance(groups, list) or len(groups) != 32:
        raise RuntimeError("V2.48.47 private denominator drifted")
    output = {}
    for index, group in enumerate(groups, 1):
        rows = []
        for item in group:
            records = {(str(record["indicator"]), str(record["year"])): str(record["value"]) for record in item["records"]}
            rows.append(
                {
                    "Country": str(item["name"]),
                    **{
                        f"{target['label']} [{target['indicator']}] @{target['year']}": records[(target["indicator"], target["year"])]
                        for target in contract.TARGETS
                    },
                }
            )
        output[f"task_{0x248470 + index:024x}"] = rows
    return output


def evaluate_prediction(prediction: str, gold: Sequence[Mapping[str, str]]) -> dict[str, float | int]:
    expected_columns = _columns()
    columns, rows = _matrix(prediction)
    if columns != expected_columns:
        rows = []
    expected = {_norm(row["Country"]): row for row in gold}
    predicted = {_norm(row[0]): row for row in rows if len(row) == len(columns) and _norm(row[0])}
    true_entities = len(set(expected) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(expected)
    row_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    item_true = 0
    for key, row in predicted.items():
        if key in expected:
            item_true += sum(_numeric_equal(row[index], expected[key][columns[index]]) for index in (1, 2))
    predicted_items = len(predicted) * 2
    gold_items = len(expected) * 2
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = 2 * item_precision * item_recall / (item_precision + item_recall) if item_precision + item_recall else 0.0
    exact = int(len(rows) == len(expected) and true_entities == len(expected) and item_true == gold_items)
    column_f1 = 1.0 if columns == expected_columns else 0.0
    return {
        "exact_table_success": exact, "entity_recall": recall, "row_f1": row_f1,
        "item_f1": item_f1, "column_f1": column_f1,
        "composite": (recall + row_f1 + item_f1 + column_f1) / 4,
    }


def evaluate_rows(rows: Sequence[Mapping[str, Any]], gold: Mapping[str, Sequence[Mapping[str, str]]]) -> dict[str, Any]:
    values = {arm: [] for arm in contract.ARMS}
    seen = set()
    for row in rows:
        opaque = str(row.get("opaque_id", ""))
        predictions = row.get("predictions")
        if opaque in seen or opaque not in gold or not isinstance(predictions, Mapping) or set(predictions) != set(contract.ARMS):
            raise RuntimeError("V2.48.47 prediction row drifted")
        seen.add(opaque)
        for arm in contract.ARMS:
            values[arm].append(evaluate_prediction(str(predictions[arm]), gold[opaque]))
    if len(seen) != 32:
        raise RuntimeError("V2.48.47 evaluation denominator drifted")
    aggregate = {}
    for arm, metrics in values.items():
        aggregate[arm] = {
            "tasks": 32,
            "exact_table_successes": sum(row["exact_table_success"] for row in metrics),
            **{
                key: sum(float(row[key]) for row in metrics) / 32
                for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")
            },
        }
    delta = {
        key: aggregate["atomic_30k"][key] - aggregate["atomic_16k"][key]
        for key in ("exact_table_successes", "entity_recall", "row_f1", "item_f1", "column_f1", "composite")
    }
    return {"arms": aggregate, "atomic_30k_minus_16k": delta}


def _parent() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = read(ROOT / contract.PROTOCOL)
    forward = read(ROOT / contract.FORWARD_RESULT)
    audit = read(ROOT / contract.FORWARD_AUDIT)
    if (
        protocol.get("protocol_id") != contract.PROTOCOL_ID
        or not sealed(protocol, "protocol_payload_sha256")
        or not sealed(forward, "result_payload_sha256")
        or audit.get("audit_valid") is not True or audit.get("findings") != []
        or not sealed(audit, "audit_payload_sha256")
        or forward.get("all_predictions_terminal_before_private_evaluator_open") is not True
    ):
        raise RuntimeError("V2.48.47 evaluator parent drifted")
    return protocol, forward, audit


def preregister(*, now: int | None = None) -> dict[str, Any]:
    _parent()
    private = read(ROOT / PRIVATE)
    gold = _gold(private)
    value = {
        "artifact_version": 1, "role": "v24847_projection_budget_external_evaluator_preregistration",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now),
        "selected_tasks": 32, "selected_arm_predictions": 64,
        "primary_comparison": "atomic_30k_minus_atomic_16k",
        "go_rule": "strict_exact_gain_and_all_composite_entity_row_item_column_nonregression_and_no_failure_cost_or_orphan_increase",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
        "private_population_sha256": contract.sha256(ROOT / PRIVATE),
        "gold_opened_only_after_prediction_freeze_and_pushed_audit": True,
        "authorization": {"one_external_evaluation": True, "public_dev64_or_exact220": False, "sota_claim": False},
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return value


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    evaluator = read(ROOT / EVALUATOR_PROTOCOL)
    if not sealed(evaluator, "protocol_payload_sha256") or evaluator.get("authorization", {}).get("one_external_evaluation") is not True:
        raise RuntimeError("V2.48.47 evaluator protocol drifted")
    _protocol, forward, _audit = _parent()
    predictions = [json.loads(line) for line in (ROOT / contract.PREDICTIONS).read_text(encoding="utf-8").splitlines() if line]
    metrics = evaluate_rows(predictions, _gold(read(ROOT / PRIVATE)))
    delta = metrics["atomic_30k_minus_16k"]
    summary = read(ROOT / contract.RUN_SUMMARY)
    triggers = summary["projection_trigger_counts"]
    passed = (
        delta["exact_table_successes"] > 0
        and all(delta[key] >= 0 for key in ("composite", "entity_recall", "row_f1", "item_f1", "column_f1"))
        and forward["failure_as_zero_tasks"] == 0
        and triggers["atomic_30k"]["orphans"] == 0
        and triggers["atomic_30k"]["dependency_additions"] > 0
        and triggers["atomic_30k"]["rendered_chars"] > triggers["atomic_16k"]["rendered_chars"]
    )
    value = {
        "artifact_version": 1, "role": "v24847_projection_budget_external_result",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "projection_budget_external_go" if passed else "projection_budget_external_no_go",
        "passed": passed, "metrics": metrics, "projection_trigger_counts": triggers,
        "fixed_denominator_failure_as_zero": True,
        "quality_evaluation_executed_once_after_prediction_freeze": True,
        "claim_scope": {
            "benchmark_external_quality_measured": True, "target_cell_disjoint": True,
            "entity_disjoint": False, "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False, "sota_supported": False,
        },
        "authorization": {"public_exact220_candidate_design": passed, "public_exact220_launch": False, "sota_claim": False},
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    return value


def postaudit(*, now: int | None = None) -> dict[str, Any]:
    result = read(ROOT / RESULT)
    findings = []
    if not sealed(result, "result_payload_sha256"):
        findings.append("result_seal_invalid")
    if result.get("fixed_denominator_failure_as_zero") is not True:
        findings.append("failure_policy_drifted")
    value = {
        "artifact_version": 1, "role": "v24847_projection_budget_external_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": contract.sha256(ROOT / RESULT), "findings": findings,
        "audit_valid": not findings, "protected_watchers": contract.protected_watcher_snapshot(),
        "network_model_fetch_or_benchmark_evaluator_called_by_audit": False,
        "authorization": {"public_exact220_candidate_design": not findings and result.get("passed") is True, "public_exact220_launch": False, "sota_claim": False},
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "evaluate", "postaudit"))
    args = parser.parse_args()
    clean()
    if args.command == "preregister":
        value, path = preregister(), EVALUATOR_PROTOCOL
    elif args.command == "evaluate":
        value, path = evaluate(), RESULT
    else:
        value, path = postaudit(), POSTAUDIT
    publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "status": value.get("status"), "passed": value.get("passed"), "metrics": value.get("metrics"), "authorization": value.get("authorization")}, sort_keys=True))


if __name__ == "__main__":
    main()
