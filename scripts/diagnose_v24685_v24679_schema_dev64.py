#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.46.79 schema dev64 result."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24679_schema_dev64_contract as contract  # noqa: E402
from scripts import finalize_v24684_v24679_schema_dev64 as finalizer  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24685_v24679_schema_dev64_diagnosis_v1_{DATE}.json")
METRICS = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == contract.payload_sha256(unsigned)


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    result = finalizer.validate_final_result()
    postaudit = finalizer.validate_postaudit()
    summaries = {
        arm: contract.read_object(ROOT / finalizer.SUMMARY[arm])
        for arm in contract.ARMS
    }
    by_arm = {
        arm: {str(row["opaque_id"]): row for row in summaries[arm]["per_task"]}
        for arm in contract.ARMS
    }
    predictions = {
        arm: [
            json.loads(line)
            for line in (ROOT / contract.RUNTIME_PREDICTIONS[arm])
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        for arm in contract.ARMS
    }
    changed: list[dict[str, float]] = []
    completion_pairs: Counter[tuple[str, str]] = Counter()
    evaluator_valid_pairs: Counter[tuple[bool, bool]] = Counter()
    score_pairs: Counter[tuple[float, float]] = Counter()
    for baseline, candidate in zip(
        predictions["baseline"], predictions["candidate"], strict=True
    ):
        if baseline["prediction_sha256"] == candidate["prediction_sha256"]:
            continue
        opaque_id = str(baseline["opaque_id"])
        left = by_arm["baseline"][opaque_id]
        right = by_arm["candidate"][opaque_id]
        delta = {
            name: float(right["metrics"][name]) - float(left["metrics"][name])
            for name in METRICS
        }
        delta["quality_composite"] = sum(delta[name] for name in METRICS[1:]) / 4
        changed.append(delta)
        completion_pairs[(baseline["completion_kind"], candidate["completion_kind"])] += 1
        evaluator_valid_pairs[(bool(left["evaluator_valid"]), bool(right["evaluator_valid"]))] += 1
        score_pairs[(float(left["metrics"]["score"]), float(right["metrics"]["score"]))] += 1
    transition_status: Counter[str] = Counter()
    result_schema_status: Counter[str] = Counter()
    treatment_applied = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        directory = ROOT / contract.TASK_ROOT / "candidate" / f"task_{position:04d}"
        if not directory.exists():
            continue
        envelope = contract.read_object(directory / "result.json")
        receipt = envelope["schema_transition_receipt"]
        transition_status[str(receipt["status"])] += 1
        treatment_applied += int(receipt["incremental_schema_applied"] is True)
        result_schema_status[str(envelope["result"]["visible_schema"]["status"])] += 1
    metric_signs = {}
    for name in (*METRICS, "quality_composite"):
        values = [delta[name] for delta in changed]
        metric_signs[name] = {
            "positive_changed_tasks": sum(value > 1e-12 for value in values),
            "zero_changed_tasks": sum(abs(value) <= 1e-12 for value in values),
            "negative_changed_tasks": sum(value < -1e-12 for value in values),
            "sum_over_changed_tasks": sum(values),
            "mean_over_fixed64": sum(values) / contract.SELECTED_COUNT,
        }
    value = {
        "artifact_version": 1,
        "role": "v24685_v24679_schema_dev64_aggregate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result_path": str(finalizer.FINAL_RESULT),
            "result_sha256": contract.sha256(ROOT / finalizer.FINAL_RESULT),
            "postaudit_path": str(finalizer.POSTAUDIT),
            "postaudit_sha256": contract.sha256(ROOT / finalizer.POSTAUDIT),
            "result_status": result["status"],
            "postaudit_valid": postaudit["audit_valid"],
        },
        "treatment_reachability": {
            "expected_treatment_tasks": contract.EXPECTED_TREATED_COUNT,
            "candidate_child_receipts": sum(transition_status.values()),
            "incremental_schema_applied_tasks": treatment_applied,
            "transition_status_counts": dict(sorted(transition_status.items())),
            "result_visible_schema_status_counts": dict(
                sorted(result_schema_status.items())
            ),
            "changed_candidate_tasks": len(changed),
            "unchanged_treatment_tasks": contract.EXPECTED_TREATED_COUNT - len(changed),
        },
        "changed_task_outcomes": {
            "changed_tasks": len(changed),
            "evaluator_valid_pair_counts": {
                f"{left}_{right}": count
                for (left, right), count in sorted(evaluator_valid_pairs.items())
            },
            "whole_table_score_pair_counts": {
                f"{left:.1f}_{right:.1f}": count
                for (left, right), count in sorted(score_pairs.items())
            },
            "completion_kind_pair_counts": {
                f"{left}->{right}": count
                for (left, right), count in sorted(completion_pairs.items())
            },
            "metric_sign_and_magnitude": metric_signs,
        },
        "diagnosis": {
            "parser_reachability_failure": False,
            "prediction_change_failure": False,
            "whole_table_utility_gain_failure": True,
            "entity_accuracy_gain_failure": True,
            "local_quality_effect_mixed": True,
            "positive_zero_negative_composite_changed_tasks": [1, 4, 2],
            "primary_bottleneck": (
                "explicit schema changes the rendered prediction on most treated tasks "
                "but does not reliably improve fact correctness or whole-table completion"
            ),
        },
        "next_experiment": {
            "repeat_same_schema_dev64_or_run_exact220": False,
            "schema_parser_as_standalone_candidate": False,
            "schema_parser_as_prerequisite_in_target_value_experiment": True,
            "required_new_treatment": (
                "pair visible schema with addressable target-value evidence, deterministic "
                "cell admission, and an independent whole-table completion check"
            ),
            "required_controls": [
                "frozen parser baseline",
                "expanded parser only",
                "expanded parser plus target-value evidence and admission",
            ],
            "entropy_credit_role": (
                "shadow ranking signal after target-value binding; positive credit requires "
                "post-freeze outer utility or same-state intervention support"
            ),
        },
        "source_policy": {
            "post_prediction_freeze_offline_evaluator_analysis": True,
            "benchmark_category_or_question_type_used": False,
            "diagnosis_fed_back_into_same_forward": False,
            "contains_opaque_id_question_prediction_instance_id_or_evaluator_row": False,
        },
        "claims": {
            "historical_development_population": True,
            "causal_generalization": False,
            "exact220_authorized": False,
            "sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    reach = copied.get("treatment_reachability") or {}
    changed = copied.get("changed_task_outcomes") or {}
    diagnosis = copied.get("diagnosis") or {}
    if (
        copied.get("role") != "v24685_v24679_schema_dev64_aggregate_diagnosis"
        or copied.get("parents", {}).get("result_status")
        != "development_gate_no_go"
        or copied.get("parents", {}).get("postaudit_valid") is not True
        or reach.get("expected_treatment_tasks") != 8
        or reach.get("candidate_child_receipts") != 8
        or reach.get("incremental_schema_applied_tasks") != 8
        or reach.get("changed_candidate_tasks") != 7
        or changed.get("changed_tasks") != 7
        or diagnosis.get("parser_reachability_failure") is not False
        or diagnosis.get("whole_table_utility_gain_failure") is not True
        or diagnosis.get("positive_zero_negative_composite_changed_tasks") != [1, 4, 2]
        or copied.get("next_experiment", {}).get(
            "repeat_same_schema_dev64_or_run_exact220"
        )
        is not False
        or copied.get("source_policy", {}).get("benchmark_category_or_question_type_used")
        is not False
        or copied.get("source_policy", {}).get(
            "contains_opaque_id_question_prediction_instance_id_or_evaluator_row"
        )
        is not False
        or copied.get("claims", {}).get("exact220_authorized") is not False
        or copied.get("claims", {}).get("sota") is not False
        or not _sealed(copied, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.46.85 aggregate diagnosis drifted")
    return copied


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


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    validate_diagnosis(diagnosis)
    publish(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "changed_tasks": diagnosis["changed_task_outcomes"]["changed_tasks"],
                "composite_signs": diagnosis["diagnosis"][
                    "positive_zero_negative_composite_changed_tasks"
                ],
            },
            sort_keys=True,
        )
    )
