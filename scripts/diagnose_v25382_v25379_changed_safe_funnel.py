#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.53.79 changed-safe funnel.

The diagnostic validates sealed task rows and published result/audit artifacts,
then emits only population aggregates.  It never writes task identifiers,
questions, predictions, pages, queries, URLs, labels, gold, evaluator rows,
per-task scores, or per-task correctness.  Published all-220 metrics are read
only after the prediction and evaluation freeze.  It performs no model, search,
fetch, evaluator execution, network, process, environment, credential, or
signed-credit action.
"""

from __future__ import annotations

import argparse
import collections
import copy
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25376_changed_safe_exact220_contract as contract  # noqa: E402
from scripts import run_v25376_changed_safe_exact220 as runner  # noqa: E402


DATE = "20260813"
OUTPUT = Path(
    f"results/v25382_v25379_changed_safe_funnel_diagnosis_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v25382_v25379_changed_safe_funnel.py")
FORWARD_AUDIT = contract.FORWARD_AUDIT
RESULT = contract.RESULT
POSTAUDIT = contract.POSTAUDIT
ROLE = "v25382_v25379_changed_safe_content_free_funnel_diagnosis"


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.82 expected one JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(runner.validate_task_row(json.loads(line)))
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.53.82 task denominator drifted")
    return rows


def _artifact_barrier() -> dict[str, Any]:
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    forward_audit = _read(FORWARD_AUDIT)
    result = _read(RESULT)
    post = _read(POSTAUDIT)
    if (
        forward_audit.get("audit_valid") is not True
        or forward_audit.get("findings") != []
        or forward_audit.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or result.get("status") != "exact220_single_rollout_complete"
        or result.get("selected") != contract.TASK_COUNT
        or result.get("claims", {}).get("sota") is not False
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or post.get("checks", {}).get("joined_official_merged_rows_exact220")
        is not True
        or post.get("checks", {}).get("no_selective_retry_or_revaluation")
        is not True
    ):
        raise RuntimeError("V2.53.82 frozen artifact barrier drifted")
    return {"forward": forward, "result": result}


def _funnel(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row["runtime_result"] for row in rows if row["runtime_completed"]]
    receipts = [
        value["private_parent_result"]["content_free_receipt"]
        for value in completed
    ]
    edits = [value["changed_safe_edit_receipt"] for value in receipts]
    schema_sources = collections.Counter(
        value["schema_totality_receipt"]["selected_schema_source"]
        for value in completed
    )
    normalizers = collections.Counter(
        value["private_parent_result"]["normalizer_status"][
            contract.runtime.CANDIDATE_ARM
        ]
        for value in completed
    )
    health: collections.Counter[str] = collections.Counter()
    for row in rows:
        health.update(row["effect_health"])
    failures: collections.Counter[str] = collections.Counter()
    for value in receipts:
        synthesis = value["failure_types"]["synthesis"]
        if synthesis is not None:
            failures[f"synthesis:{synthesis}"] += 1
    counts = {
        "task_count": len(rows),
        "runtime_completed_tasks": len(completed),
        "model_generated_tasks": sum(
            value["private_parent_result"]["model_success"]
            [contract.runtime.CANDIDATE_ARM]
            for value in completed
        ),
        "first_wave_completed_tasks": sum(
            value["first_wave_completed"] for value in receipts
        ),
        "second_wave_completed_tasks": sum(
            value["second_wave_completed"] for value in receipts
        ),
        "grounded_plan_attempted_tasks": sum(
            value["grounded_plan_model_call_attempted"] for value in receipts
        ),
        "grounded_plan_success_tasks": sum(
            value["grounded_plan_model_call_success"] for value in receipts
        ),
        "grounded_strategy_applied_tasks": sum(
            value["grounded_plan_strategy_applied"] for value in receipts
        ),
        "base_synthesis_attempted_tasks": sum(
            value["base_synthesis_attempted"] for value in receipts
        ),
        "base_synthesis_success_tasks": sum(
            value["base_synthesis_model_success"] for value in receipts
        ),
        "base_exact_canonical_tasks": sum(
            value["base_table_exact_canonical"] for value in receipts
        ),
        "record_model_attempted_tasks": sum(
            value["model_call_attempted"] for value in edits
        ),
        "record_output_strict_valid_tasks": sum(
            value["record_output_strictly_valid"] for value in edits
        ),
        "parsed_record_tasks": sum(value["parsed_record_count"] > 0 for value in edits),
        "parsed_record_count": sum(value["parsed_record_count"] for value in edits),
        "parsed_field_tasks": sum(value["parsed_field_count"] > 0 for value in edits),
        "parsed_field_count": sum(value["parsed_field_count"] for value in edits),
        "verified_record_tasks": sum(value["verified_record_count"] > 0 for value in edits),
        "verified_record_count": sum(value["verified_record_count"] for value in edits),
        "verified_field_tasks": sum(value["verified_field_count"] > 0 for value in edits),
        "verified_field_count": sum(value["verified_field_count"] for value in edits),
        "verified_coordinate_tasks": sum(
            value["verified_table_coordinate_count"] > 0 for value in edits
        ),
        "verified_coordinate_count": sum(
            value["verified_table_coordinate_count"] for value in edits
        ),
        "changed_safe_tasks": sum(
            value["changed_safe_coordinate_count"] > 0 for value in edits
        ),
        "changed_safe_coordinate_count": sum(
            value["changed_safe_coordinate_count"] for value in edits
        ),
        "unchanged_verified_coordinate_count": sum(
            value["unchanged_verified_coordinate_count"] for value in edits
        ),
        "missing_row_rejected_field_count": sum(
            value["missing_row_rejected_field_count"] for value in edits
        ),
        "all_other_rejected_field_count": sum(
            value[name]
            for value in edits
            for name in (
                "table_or_schema_rejected_field_count",
                "ambiguous_row_rejected_field_count",
                "missing_or_key_column_rejected_field_count",
                "multiple_source_coordinate_rejected_field_count",
                "conflicting_source_coordinate_rejected_field_count",
                "unsafe_or_unknown_value_rejected_field_count",
            )
        ),
        "prediction_changed_tasks": sum(
            value["prediction_changed"] for value in completed
        ),
        "attributable_prediction_changed_tasks": sum(
            value["attributable_prediction_change"] for value in completed
        ),
        "unattributable_prediction_changed_tasks": sum(
            value["private_parent_result"]["unattributable_prediction_change"]
            for value in completed
        ),
        "editor_validation_failure_tasks": sum(
            value["editor_validation_failed"] for value in receipts
        ),
        "positive_signed_credit_count": sum(
            value["positive_signed_credit_count"] for value in receipts
        ),
    }
    return {
        "counts": counts,
        "schema_source_counts": dict(sorted(schema_sources.items())),
        "normalizer_status_counts": dict(sorted(normalizers.items())),
        "synthesis_failure_type_counts": dict(sorted(failures.items())),
        "effect_health_counts": dict(sorted(health.items())),
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    barrier = _artifact_barrier()
    rows = _read_rows()
    funnel = _funnel(rows)
    counts = funnel["counts"]
    metrics = barrier["result"]["metrics"]["all_220"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_bindings": {
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / FORWARD_AUDIT),
            "result_sha256": contract.sha256(ROOT / RESULT),
            "postresult_audit_sha256": contract.sha256(ROOT / POSTAUDIT),
        },
        "funnel": funnel,
        "published_all220_metrics": {
            "selected": int(metrics["selected"]),
            "whole_table_successes": int(metrics["whole_table_successes"]),
            "score": float(metrics["score"]),
            "entity_acc": float(metrics["entity_acc"]),
            "f1_by_row": float(metrics["f1_by_row"]),
            "f1_by_item": float(metrics["f1_by_item"]),
            "column_f1": float(metrics["column_f1"]),
            "quality_composite": float(metrics["quality_composite"]),
            "evaluator_valid": int(metrics["evaluator_valid"]),
            "evaluator_invalid_or_not_run": int(
                metrics["evaluator_invalid_or_not_run"]
            ),
        },
        "diagnosis": {
            "runtime_totality_and_budget_safety_established": (
                counts["runtime_completed_tasks"] == contract.TASK_COUNT
                and counts["editor_validation_failure_tasks"] == 0
                and counts["unattributable_prediction_changed_tasks"] == 0
            ),
            "record_proposal_is_first_large_conversion_loss": (
                counts["record_model_attempted_tasks"] == 209
                and counts["parsed_record_tasks"] == 12
            ),
            "quote_verification_further_reduces_coverage": (
                counts["parsed_record_tasks"] == 12
                and counts["verified_record_tasks"] == 6
            ),
            "missing_base_row_is_dominant_postverification_rejection": (
                counts["missing_row_rejected_field_count"] == 7
                and counts["all_other_rejected_field_count"] == 0
            ),
            "changed_safe_natural_exposure_is_one_of_220": (
                counts["changed_safe_tasks"] == 1
                and counts["changed_safe_coordinate_count"] == 1
                and counts["attributable_prediction_changed_tasks"] == 1
            ),
            "cross_rollout_quality_delta_is_not_attributable_to_one_edit": True,
            "entropy_information_gain_credit_evidence_absent": (
                counts["positive_signed_credit_count"] == 0
            ),
        },
        "decision": {
            "v25379_quality": "no_go",
            "repeat_or_selective_rerun_of_v25379": False,
            "next_build_priority": "source_bound_record_proposal_coverage_then_missing_row_safe_bridge",
            "next_gate_requires_fresh_external_shared_prefix_population": True,
            "public_exact220_successor_authorized": False,
            "entropy_or_information_gain_signed_credit_authorized": False,
        },
        "content_free_aggregate_only": True,
        "contains_question_opaque_id_query_url_page_quote_record_value_prediction_gold_label_per_task_score_or_per_task_correctness": False,
        "model_search_fetch_evaluator_network_or_external_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "next_build_only": True,
            "new_external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    counts = copied.get("funnel", {}).get("counts", {})
    diagnosis = copied.get("diagnosis") or {}
    decision = copied.get("decision") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or counts.get("task_count") != contract.TASK_COUNT
        or counts.get("runtime_completed_tasks") != contract.TASK_COUNT
        or counts.get("record_model_attempted_tasks") != 209
        or counts.get("parsed_record_tasks") != 12
        or counts.get("verified_record_tasks") != 6
        or counts.get("verified_coordinate_count") != 9
        or counts.get("missing_row_rejected_field_count") != 7
        or counts.get("changed_safe_tasks") != 1
        or counts.get("attributable_prediction_changed_tasks") != 1
        or counts.get("unattributable_prediction_changed_tasks") != 0
        or counts.get("positive_signed_credit_count") != 0
        or not diagnosis
        or not all(diagnosis.values())
        or decision
        != {
            "v25379_quality": "no_go",
            "repeat_or_selective_rerun_of_v25379": False,
            "next_build_priority": "source_bound_record_proposal_coverage_then_missing_row_safe_bridge",
            "next_gate_requires_fresh_external_shared_prefix_population": True,
            "public_exact220_successor_authorized": False,
            "entropy_or_information_gain_signed_credit_authorized": False,
        }
        or copied.get("content_free_aggregate_only") is not True
        or copied.get("contains_question_opaque_id_query_url_page_quote_record_value_prediction_gold_label_per_task_score_or_per_task_correctness")
        is not False
        or copied.get("model_search_fetch_evaluator_network_or_external_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "next_build_only": True,
            "new_external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.82 diagnosis drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    value = build_diagnosis()
    if not args.validate_only:
        _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis": value["diagnosis"],
                "decision": value["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
