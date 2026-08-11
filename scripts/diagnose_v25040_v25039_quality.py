#!/usr/bin/env python3
"""Counts-only post-freeze diagnosis of the V2.50.39 quality NO-GO."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25039_batching_external_contract as contract  # noqa: E402
from scripts import evaluate_v25039_batching_external as evaluator  # noqa: E402


DATE = "20260811"
OUTPUT = Path(f"results/v25040_v25039_paired_quality_diagnosis_v1_{DATE}.json")


def _field_correctness(prediction: str, gold: dict[str, Any]) -> tuple[bool, bool, bool]:
    columns, rows = evaluator._matrix(prediction)
    if columns != list(contract.COLUMNS) or len(rows) != 1 or len(rows[0]) != 4:
        return False, False, False
    row = rows[0]
    if evaluator._normalize_package(row[0]) != evaluator._normalize_package(
        gold["package"]
    ):
        return False, False, False
    return (
        evaluator._normalize_value(row[1])
        == evaluator._normalize_value(gold["version"]),
        evaluator._normalize_value(row[2])
        == evaluator._normalize_value(gold["date"]),
        evaluator._normalize_requires_python(row[3])
        == evaluator._normalize_requires_python(gold["requires_python"]),
    )


def build(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    if require_clean and (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.50.40 diagnosis requires clean pushed HEAD")
    result = evaluator.validate_result(
        evaluator._read(contract.RESULT, tracked=True)
    )
    audit = evaluator._read(contract.POSTAUDIT, tracked=True)
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("batching_external_quality_gate_go") is not False
        or not contract.sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.40 requires clean V2.50.39 NO-GO audit")
    rows = [
        evaluator.runner.validate_task_row(row)
        for row in evaluator._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]
    gold_snapshot = evaluator._read(contract.GOLD_SNAPSHOT, tracked=True)
    gold_rows = evaluator.validate_gold_rows(gold_snapshot["rows"])
    gold = {row["opaque_id"]: row for row in gold_rows}
    control, candidate = contract.CONTROL_ARM, contract.CANDIDATE_ARM
    counts = {
        "tasks": contract.TASK_COUNT,
        "prediction_changed": 0,
        "prediction_unchanged": 0,
        "candidate_exact_gain": 0,
        "candidate_exact_loss": 0,
        "exact_same_both": 0,
        "exact_same_neither": 0,
        "candidate_item_gain": 0,
        "candidate_item_loss": 0,
        "candidate_item_tie": 0,
    }
    field_delta = {"latest_version": 0, "latest_release_date": 0, "requires_python": 0}
    changed_case_signatures: list[dict[str, Any]] = []
    for row in rows:
        expected = gold[row["opaque_id"]]
        metrics = {
            arm: evaluator.evaluate_prediction(row["predictions"][arm], expected)
            for arm in contract.ARMS
        }
        correct = {
            arm: _field_correctness(row["predictions"][arm], expected)
            for arm in contract.ARMS
        }
        counts[
            "prediction_changed" if row["prediction_changed"] else "prediction_unchanged"
        ] += 1
        control_exact = int(metrics[control]["exact_table_success"])
        candidate_exact = int(metrics[candidate]["exact_table_success"])
        if candidate_exact > control_exact:
            counts["candidate_exact_gain"] += 1
        elif candidate_exact < control_exact:
            counts["candidate_exact_loss"] += 1
        elif candidate_exact:
            counts["exact_same_both"] += 1
        else:
            counts["exact_same_neither"] += 1
        control_items = sum(correct[control])
        candidate_items = sum(correct[candidate])
        if candidate_items > control_items:
            counts["candidate_item_gain"] += 1
        elif candidate_items < control_items:
            counts["candidate_item_loss"] += 1
        else:
            counts["candidate_item_tie"] += 1
        for index, name in enumerate(field_delta):
            field_delta[name] += int(correct[candidate][index]) - int(
                correct[control][index]
            )
        if row["prediction_changed"]:
            changed_case_signatures.append(
                {
                    "control_exact": control_exact,
                    "candidate_exact": candidate_exact,
                    "control_correct_field_mask": [int(value) for value in correct[control]],
                    "candidate_correct_field_mask": [int(value) for value in correct[candidate]],
                }
            )
    changed_case_signatures.sort(
        key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
    )
    value = {
        "artifact_version": 1,
        "role": "v25040_v25039_paired_quality_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_protocol_id": contract.PROTOCOL_ID,
        "parent_result_sha256": contract.sha256(ROOT / contract.RESULT),
        "parent_postresult_audit_sha256": contract.sha256(ROOT / contract.POSTAUDIT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "gold_snapshot_sha256": contract.sha256(ROOT / contract.GOLD_SNAPSHOT),
        "counts": counts,
        "candidate_minus_control_correct_field_counts": field_delta,
        "changed_case_signatures": changed_case_signatures,
        "contains_opaque_id_project_query_url_page_prediction_gold_value_or_credential": False,
        "network_model_search_fetch_or_evaluator_calls": 0,
        "same_evaluated_forward_feedback_or_revaluation": False,
        "claim_scope": {
            "postfreeze_diagnosis_only": True,
            "paired_same_forward_quality_difference_measured": True,
            "causal_quality_effect_established": False,
            "adaptive_second_wave_measured": False,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        },
        "authorization": {
            "direct_one_shot_replacement": False,
            "fresh_successor_design": True,
            "deepwidebench_dev64_exact220": False,
            "retry_refetch_rerun_or_revaluation": False,
        },
    }
    return contract.seal(value, "diagnosis_payload_sha256")


def validate(value: dict[str, Any]) -> dict[str, Any]:
    counts = value.get("counts") or {}
    field_delta = value.get("candidate_minus_control_correct_field_counts") or {}
    if (
        value.get("role") != "v25040_v25039_paired_quality_diagnosis"
        or counts.get("tasks") != contract.TASK_COUNT
        or counts.get("prediction_changed") + counts.get("prediction_unchanged")
        != contract.TASK_COUNT
        or counts.get("candidate_exact_gain") != 0
        or counts.get("candidate_exact_loss") != 0
        or counts.get("candidate_item_gain") != 1
        or counts.get("candidate_item_loss") != 3
        or field_delta
        != {
            "latest_version": -1,
            "latest_release_date": -1,
            "requires_python": 0,
        }
        or value.get("network_model_search_fetch_or_evaluator_calls") != 0
        or value.get("authorization", {}).get("deepwidebench_dev64_exact220")
        is not False
        or not contract.sealed(value, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.50.40 diagnosis drifted")
    return value


def _publish(value: dict[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    value = validate(build(require_clean=True))
    _publish(value)
    print(json.dumps({"path": str(OUTPUT), "counts": value["counts"], "field_delta": value["candidate_minus_control_correct_field_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
