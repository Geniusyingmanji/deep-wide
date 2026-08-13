#!/usr/bin/env python3
"""Aggregate-only diagnosis of the V2.53.93 hybrid row-overlap funnel."""

from __future__ import annotations

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

from deepwide_agent import v25393_rfc_hybrid_external_contract as contract  # noqa: E402
from scripts import run_v25393_rfc_hybrid_external as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25394_v25393_content_free_hybrid_row_overlap_diagnosis"
SOURCE = Path("scripts/diagnose_v25394_v25393_hybrid_row_overlap.py")
TEST = Path("tests/test_diagnose_v25394_v25393_hybrid_row_overlap.py")
OUTPUT = Path(
    f"results/v25394_v25393_hybrid_row_overlap_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT = contract.FORWARD_RESULT
FORWARD_AUDIT = contract.FORWARD_AUDIT
TASK_ROWS = contract.TASK_ROWS
PREDICTION_FREEZE = contract.PREDICTION_FREEZE
PREDECESSOR_DIAGNOSIS = Path(
    "results/v25388_v25387_joint_record_suppression_diagnosis_v1_20260813.json"
)
FIXED_HASHES = {
    FORWARD_RESULT: "5b5b8f84713dc830c44d42dda17bbf53d4d645d7752c09f9a99bcbc5e12f95bf",
    FORWARD_AUDIT: "8c570e1f1e05c04dd469643bd26b86c46acfdbade7e76bb907eaa52924a25e0b",
    TASK_ROWS: "95630b6a5dbda10259150587c3fff50237ba27b066dee8de19d41c9aacaea959",
    PREDICTION_FREEZE: "e5dbdaddbd57939c12dd7499a8eadd394ff1714b1869a9cc9fb013235b24d3ef",
    PREDECESSOR_DIAGNOSIS: "811ecbf473ed2823d0ba2766f330406724713c2d13e7a9d5359ba5dccb62c5e2",
}


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.94 expected a JSON object")
    return value


def _histogram(values: list[int]) -> dict[str, int]:
    output: dict[str, int] = {}
    for value in values:
        key = str(int(value))
        output[key] = output.get(key, 0) + 1
    return dict(sorted(output.items(), key=lambda item: int(item[0])))


def _barrier() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if any(
        contract.sha256(ROOT / path) != expected
        for path, expected in FIXED_HASHES.items()
    ):
        raise RuntimeError("V2.53.94 fixed artifact hash drifted")
    forward = runner.validate_forward_result(_read(FORWARD_RESULT))
    audit = _read(FORWARD_AUDIT)
    rows = [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(TASK_ROWS, tracked=True)
    ]
    aggregate = runner.aggregate_rows(
        rows, wall_seconds=float(forward["aggregate"]["batch_wall_seconds"])
    )
    if (
        audit.get("role") != "v25393_rfc_hybrid_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or audit.get("forward_result_sha256")
        != contract.sha256(ROOT / FORWARD_RESULT)
        or len(rows) != contract.TASK_COUNT
        or aggregate != forward["aggregate"]
        or forward["mechanism_decision"]["mechanism_gate_passed"] is not False
    ):
        raise RuntimeError("V2.53.94 forward audit barrier drifted")
    return forward, rows


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, rows = _barrier()
    receipts = [
        row["content_free_stage_receipt"]["hybrid_record_fallback_receipt"]
        for row in rows
    ]
    verified_fields = sum(row["verified_field_count"] for row in receipts)
    missing = sum(row["missing_row_rejected_field_count"] for row in receipts)
    unchanged = sum(
        row["unchanged_verified_coordinate_count"] for row in receipts
    )
    changed = sum(row["changed_safe_coordinate_count"] for row in receipts)
    disposition_total = missing + unchanged + changed
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_bindings": {
            str(path): contract.sha256(ROOT / path) for path in FIXED_HASHES
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": {
            "task_count": len(receipts),
            "completed_runtime_tasks": sum(
                row["runtime_completed"] for row in rows
            ),
            "joint_source_tasks": sum(
                row["record_source"] == "joint" for row in receipts
            ),
            "grounded_source_tasks": sum(
                row["record_source"] == "grounded" for row in receipts
            ),
            "no_source_tasks": sum(
                row["record_source"] == "none" for row in receipts
            ),
            "grounded_raw_record_tasks": sum(
                row["grounded_raw_record_count"] > 0 for row in receipts
            ),
            "grounded_raw_record_count_total": sum(
                row["grounded_raw_record_count"] for row in receipts
            ),
            "selected_raw_record_tasks": sum(
                row["selected_raw_record_count"] > 0 for row in receipts
            ),
            "selected_raw_record_count_total": sum(
                row["selected_raw_record_count"] for row in receipts
            ),
            "verified_record_tasks": sum(
                row["verified_record_count"] > 0 for row in receipts
            ),
            "verified_record_count_total": sum(
                row["verified_record_count"] for row in receipts
            ),
            "verified_field_count_total": verified_fields,
            "missing_row_rejected_field_count_total": missing,
            "unchanged_verified_coordinate_count_total": unchanged,
            "changed_safe_coordinate_count_total": changed,
            "verified_field_disposition_total": disposition_total,
            "verified_field_disposition_is_exhaustive": (
                disposition_total == verified_fields
            ),
            "missing_row_task_count": sum(
                row["missing_row_rejected_field_count"] > 0
                for row in receipts
            ),
            "missing_row_count_histogram": _histogram(
                [row["missing_row_rejected_field_count"] for row in receipts]
            ),
            "verified_field_count_histogram": _histogram(
                [row["verified_field_count"] for row in receipts]
            ),
            "changed_safe_coordinate_count_histogram": _histogram(
                [row["changed_safe_coordinate_count"] for row in receipts]
            ),
            "attributable_prediction_changed_tasks": sum(
                row["attributable_prediction_change"] for row in rows
            ),
        },
        "diagnosis": {
            "hybrid_fallback_recovers_nonzero_grounded_record_coverage": True,
            "selected_record_and_quote_verification_gates_pass": True,
            "verified_fields_are_fully_partitioned_by_editor_dispositions": True,
            "missing_base_row_is_the_only_rejection_disposition_observed": True,
            "remaining_mechanism_gap_is_verified_source_row_to_base_row_overlap": True,
            "next_build_may_use_only_pre_synthesis_quote_verified_row_constraints": True,
            "post_synthesis_row_append_or_table_shape_change_is_forbidden": True,
            "raw_unverified_grounded_record_injection_is_forbidden": True,
            "joint_and_grounded_record_union_or_postverification_fallthrough_is_forbidden": True,
            "quality_or_deepwidebench_improvement_established": False,
            "entropy_information_gain_signed_credit_evidence_present": False,
        },
        "contains_question_query_url_page_quote_record_identity_field_value_prediction_answer_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "pre_synthesis_verified_row_constraint_build_only": True,
            "new_external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    funnel = copied.get("content_free_funnel")
    diagnosis = copied.get("diagnosis")
    expected_funnel = {
        "task_count": 20,
        "completed_runtime_tasks": 20,
        "joint_source_tasks": 0,
        "grounded_source_tasks": 9,
        "no_source_tasks": 11,
        "grounded_raw_record_tasks": 9,
        "grounded_raw_record_count_total": 11,
        "selected_raw_record_tasks": 9,
        "selected_raw_record_count_total": 11,
        "verified_record_tasks": 9,
        "verified_record_count_total": 10,
        "verified_field_count_total": 27,
        "missing_row_rejected_field_count_total": 10,
        "unchanged_verified_coordinate_count_total": 11,
        "changed_safe_coordinate_count_total": 6,
        "verified_field_disposition_total": 27,
        "verified_field_disposition_is_exhaustive": True,
        "missing_row_task_count": 4,
        "missing_row_count_histogram": {"0": 16, "2": 2, "3": 2},
        "verified_field_count_histogram": {"0": 11, "2": 3, "3": 5, "6": 1},
        "changed_safe_coordinate_count_histogram": {"0": 17, "1": 1, "2": 1, "3": 1},
        "attributable_prediction_changed_tasks": 3,
    }
    expected_diagnosis = {
        "hybrid_fallback_recovers_nonzero_grounded_record_coverage": True,
        "selected_record_and_quote_verification_gates_pass": True,
        "verified_fields_are_fully_partitioned_by_editor_dispositions": True,
        "missing_base_row_is_the_only_rejection_disposition_observed": True,
        "remaining_mechanism_gap_is_verified_source_row_to_base_row_overlap": True,
        "next_build_may_use_only_pre_synthesis_quote_verified_row_constraints": True,
        "post_synthesis_row_append_or_table_shape_change_is_forbidden": True,
        "raw_unverified_grounded_record_injection_is_forbidden": True,
        "joint_and_grounded_record_union_or_postverification_fallthrough_is_forbidden": True,
        "quality_or_deepwidebench_improvement_established": False,
        "entropy_information_gain_signed_credit_evidence_present": False,
    }
    expected_authorization = {
        "pre_synthesis_verified_row_constraint_build_only": True,
        "new_external_forward": False,
        "deepwidebench_forward_or_evaluator": False,
        "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        "leaderboard_or_sota": False,
    }
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("source_bindings")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or funnel != expected_funnel
        or diagnosis != expected_diagnosis
        or copied.get(
            "contains_question_query_url_page_quote_record_identity_field_value_prediction_answer_or_credential"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization") != expected_authorization
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.94 hybrid row-overlap diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
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


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "content_free_funnel": value["content_free_funnel"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
