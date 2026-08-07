#!/usr/bin/env python3
"""One-shot post-freeze evaluator for V2.48.24."""

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

from deepwide_agent import v24824_quality_first_external_contract as contract  # noqa: E402
from deepwide_agent.v24686_worldbank_target_value_runtime import (  # noqa: E402
    _matrix,
    _visible_contract,
)
from deepwide_agent.v24819_quality_first_controller import ARMS  # noqa: E402


EVALUATOR_PROTOCOL = Path(
    f"results/v24824_quality_first_external_evaluator_preregistration_v1_{contract.DATE}.json"
)
RESULT = Path(
    f"results/v24824_quality_first_external_result_v1_{contract.DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24824_quality_first_external_postresult_audit_v1_{contract.DATE}.json"
)
PRIVATE = contract.POPULATION_PRIVATE
METRICS = (
    "exact_table_successes",
    "entity_recall",
    "row_f1",
    "item_f1",
    "column_f1",
    "composite",
)


def read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.48.24 evaluator expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.24 evaluator expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def git(*args: str) -> str:
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


def clean() -> None:
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.24 evaluator requires clean pushed HEAD")


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _numeric_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).strip()) == Decimal(str(right).strip())
    except (InvalidOperation, ValueError):
        return False


def _private_gold(
    private: Mapping[str, Any],
) -> dict[str, list[dict[str, str]]]:
    groups = private.get("groups")
    if not isinstance(groups, list) or len(groups) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.48.24 private denominator drifted")
    output: dict[str, list[dict[str, str]]] = {}
    for index, group in enumerate(groups, 1):
        opaque = f"task_{0x248240 + index:024x}"
        rows = []
        if not isinstance(group, list) or len(group) != 4:
            raise RuntimeError("V2.48.24 private group drifted")
        for item in group:
            records = item.get("records") if isinstance(item, Mapping) else None
            if not isinstance(records, list) or len(records) != 2:
                raise RuntimeError("V2.48.24 private record vector drifted")
            by_target: dict[tuple[str, str], str] = {}
            for record in records:
                value = record.get("value") if isinstance(record, Mapping) else None
                if value is None:
                    raise RuntimeError("V2.48.24 complete population contains null gold")
                by_target[(str(record["indicator"]), str(record["year"]))] = str(
                    value
                )
            rows.append(
                {
                    "Country": str(item["name"]),
                    **{
                        f"{target['label']} [{target['indicator']}] @{target['year']}": by_target[
                            (target["indicator"], target["year"])
                        ]
                        for target in contract.TARGETS
                    },
                }
            )
        output[opaque] = rows
    return output


def evaluate_prediction(
    prediction: str,
    question: str,
    gold: Sequence[Mapping[str, str]],
) -> dict[str, float | int]:
    visible = _visible_contract(question)
    columns, rows = _matrix(prediction, visible["columns"])
    if columns != visible["columns"]:
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
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    item_true = 0
    for key, row in predicted.items():
        if key in expected:
            item_true += sum(
                _numeric_equal(row[index], expected[key][columns[index]])
                for index in (1, 2)
            )
    predicted_items = len(predicted) * 2
    gold_items = len(expected) * 2
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
    column_f1 = 1.0 if columns == visible["columns"] else 0.0
    composite = (recall + row_f1 + item_f1 + column_f1) / 4
    return {
        "exact_table_success": exact,
        "entity_recall": recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": composite,
    }


def evaluate_rows(
    predictions: Sequence[Mapping[str, Any]],
    protocol: Mapping[str, Any],
    gold: Mapping[str, Sequence[Mapping[str, str]]],
) -> dict[str, Any]:
    questions = {
        row["opaque_id"]: row["question"] for row in protocol["visible_tasks"]
    }
    by_arm: dict[str, list[dict[str, float | int]]] = {arm: [] for arm in ARMS}
    seen: set[str] = set()
    task_level_equal = 0
    for row in predictions:
        opaque = str(row.get("opaque_id", ""))
        arms = row.get("predictions")
        if (
            opaque in seen
            or opaque not in questions
            or opaque not in gold
            or not isinstance(arms, Mapping)
            or set(arms) != set(ARMS)
        ):
            raise RuntimeError("V2.48.24 frozen prediction drifted")
        seen.add(opaque)
        task_level_equal += int(
            arms["coverage_risk_adaptive"] == arms["fixed_full_budget"]
        )
        for arm in ARMS:
            by_arm[arm].append(
                evaluate_prediction(str(arms[arm]), questions[opaque], gold[opaque])
            )
    if len(seen) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.48.24 evaluator denominator drifted")
    aggregate = {}
    for arm, rows in by_arm.items():
        aggregate[arm] = {
            "tasks": contract.SELECTED_COUNT,
            "exact_table_successes": sum(
                row["exact_table_success"] for row in rows
            ),
            **{
                name: sum(float(row[name]) for row in rows)
                / contract.SELECTED_COUNT
                for name in (
                    "entity_recall",
                    "row_f1",
                    "item_f1",
                    "column_f1",
                    "composite",
                )
            },
        }
    fixed = {
        name: aggregate["fixed_full_budget"][name]
        - aggregate["first_wave_only"][name]
        for name in METRICS
    }
    adaptive = {
        name: aggregate["coverage_risk_adaptive"][name]
        - aggregate["first_wave_only"][name]
        for name in METRICS
    }
    adaptive_fixed = {
        name: aggregate["coverage_risk_adaptive"][name]
        - aggregate["fixed_full_budget"][name]
        for name in METRICS
    }
    gate = (
        fixed["exact_table_successes"] > 0
        and fixed["composite"] > 0
        and fixed["item_f1"] > 0
        and task_level_equal == contract.SELECTED_COUNT
        and all(value == 0 for value in adaptive_fixed.values())
    )
    return {
        "arms": aggregate,
        "fixed_full_minus_first_wave": fixed,
        "adaptive_minus_first_wave": adaptive,
        "adaptive_minus_fixed_full": adaptive_fixed,
        "adaptive_prediction_equals_fixed_full_tasks": task_level_equal,
        "quality_first_mechanism_gate_passed": gate,
    }


def validate_parent() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, read(ROOT / contract.PROTOCOL))
    audit = read(ROOT / contract.FORWARD_AUDIT)
    freeze = read(ROOT / contract.PREDICTION_FREEZE)
    if (
        audit.get("role") != "v24824_quality_first_external_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_protocol"
        )
        is not True
        or not sealed(audit, "audit_payload_sha256")
        or not sealed(freeze, "freeze_payload_sha256")
        or freeze.get("predictions_sha256")
        != contract.sha256(ROOT / contract.PREDICTIONS)
    ):
        raise RuntimeError("V2.48.24 evaluator parent drifted")
    return protocol, audit


def preregister(*, now: int | None = None) -> dict[str, Any]:
    _protocol, _audit = validate_parent()
    gold = _private_gold(read(ROOT / PRIVATE))
    value = {
        "artifact_version": 1,
        "role": "v24824_quality_first_external_evaluator_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "selected_tasks": contract.SELECTED_COUNT,
        "selected_arm_predictions": contract.SELECTED_COUNT * contract.ARM_COUNT,
        "primary_comparison": "fixed_full_budget_minus_first_wave_only",
        "secondary_comparison": "coverage_risk_adaptive_minus_fixed_full_budget",
        "go_rule": (
            "strict_positive_fixed_full_exact_composite_and_item_gain_and_"
            "adaptive_prediction_exactly_equals_fixed_full_on_all_32_tasks"
        ),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
        "evaluator_only_private_population_sha256": contract.sha256(
            ROOT / PRIVATE
        ),
        "private_gold_tasks": len(gold),
        "gold_opened_only_after_prediction_freeze_and_pushed_audit": True,
        "authorization": {
            "one_external_evaluation": True,
            "public_dev64_or_exact220": False,
            "sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return value


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    evaluator = read(ROOT / EVALUATOR_PROTOCOL)
    if (
        not sealed(evaluator, "protocol_payload_sha256")
        or evaluator.get("authorization", {}).get("one_external_evaluation")
        is not True
    ):
        raise RuntimeError("V2.48.24 evaluator protocol drifted")
    protocol, _audit = validate_parent()
    predictions = [
        json.loads(line)
        for line in (ROOT / contract.PREDICTIONS)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    metrics = evaluate_rows(
        predictions, protocol, _private_gold(read(ROOT / PRIVATE))
    )
    passed = metrics["quality_first_mechanism_gate_passed"]
    value = {
        "artifact_version": 1,
        "role": "v24824_quality_first_external_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": (
            "target_cell_disjoint_quality_first_mechanism_go"
            if passed
            else "target_cell_disjoint_quality_first_mechanism_no_go"
        ),
        "passed": passed,
        "metrics": metrics,
        "fixed_denominator_failure_as_zero": True,
        "quality_evaluation_executed_once_after_prediction_freeze": True,
        "evaluator_protocol_sha256": contract.sha256(ROOT / EVALUATOR_PROTOCOL),
        "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
        "claim_scope": {
            "benchmark_external_quality_measured": True,
            "mandatory_coverage_effect_measured": True,
            "quality_first_equals_fixed_full_measured": True,
            "country_entity_disjoint": False,
            "target_cell_disjoint": True,
            "cost_sensitive_stopping_validated": False,
            "entropy_or_signed_credit_validated": False,
            "deepwidebench_quality_measured": False,
            "sota_supported": False,
        },
        "authorization": {
            "public_exact220_candidate_design": passed,
            "public_exact220_launch": False,
            "sota_claim": False,
        },
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    return value


def postaudit(*, now: int | None = None) -> dict[str, Any]:
    result = read(ROOT / RESULT)
    evaluator = read(ROOT / EVALUATOR_PROTOCOL)
    findings = []
    if not sealed(result, "result_payload_sha256") or not sealed(
        evaluator, "protocol_payload_sha256"
    ):
        findings.append("result_or_protocol_invalid")
    if (
        result.get("evaluator_protocol_sha256")
        != contract.sha256(ROOT / EVALUATOR_PROTOCOL)
        or result.get("predictions_sha256")
        != contract.sha256(ROOT / contract.PREDICTIONS)
    ):
        findings.append("result_binding_drifted")
    metrics = result.get("metrics", {})
    if metrics.get("adaptive_prediction_equals_fixed_full_tasks") != 32:
        findings.append("adaptive_fixed_equivalence_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24824_quality_first_external_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": contract.sha256(ROOT / RESULT),
        "evaluator_protocol_sha256": contract.sha256(ROOT / EVALUATOR_PROTOCOL),
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_or_official_benchmark_evaluator_called_by_audit": False,
        "authorization": {
            "public_exact220_candidate_design": not findings
            and result.get("passed") is True,
            "public_exact220_launch": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    if findings:
        raise RuntimeError("V2.48.24 postresult audit failed")
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
