#!/usr/bin/env python3
"""Aggregate-only diagnosis of V2.53.99 membership/record alignment."""

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

from deepwide_agent import v25399_rfc_visible_membership_external_contract as contract  # noqa: E402
from scripts import run_v25399_rfc_visible_membership_external as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25400_v25399_content_free_membership_record_alignment_diagnosis"
SOURCE = Path("scripts/diagnose_v25400_v25399_membership_record_alignment.py")
TEST = Path("tests/test_diagnose_v25400_v25399_membership_record_alignment.py")
OUTPUT = Path(
    f"results/v25400_v25399_membership_record_alignment_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT = contract.FORWARD_RESULT
FORWARD_AUDIT = contract.FORWARD_AUDIT
TASK_ROWS = contract.TASK_ROWS
PREDICTION_FREEZE = contract.PREDICTION_FREEZE
FIXED_HASHES = {
    FORWARD_RESULT: "3c5f3ccb7ddcef4ec71f3b5c781ec3f04cb805a3b652c1a6e65b661f2c22974c",
    FORWARD_AUDIT: "60f8ebe83ea184ff48448c15b77a69d273fb11f173bee3ed1961155637287bfa",
    TASK_ROWS: "0424a255646e3bedb729f697f28c32f3c990ac6327d492ad056dc866f0a7dfab",
    PREDICTION_FREEZE: "d5f87d52f6b78b9b5b580f4a05e2be5919d69d67d0fa04382715eb20a7badd6a",
}


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.00 expected a JSON object")
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
        raise RuntimeError("V2.54.00 fixed artifact hash drifted")
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
        audit.get("role") != "v25399_rfc_visible_membership_forward_audit"
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
        raise RuntimeError("V2.54.00 forward audit barrier drifted")
    return forward, rows


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, rows = _barrier()
    stages = [row["content_free_stage_receipt"] for row in rows]
    memberships = [
        stage["visible_membership_synthesis_receipt"] for stage in stages
    ]
    receipts = [
        stage["parent_stage_receipt"]["hybrid_record_fallback_receipt"]
        for stage in stages
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
            "membership_constraint_applied_tasks": sum(
                row["membership_constraint_applied"] for row in memberships
            ),
            "base_visible_membership_exact_tasks": sum(
                row["base_visible_membership_exact"] for row in memberships
            ),
            "visible_member_count_total": sum(
                row["visible_member_count"] for row in memberships
            ),
            "base_visible_member_match_count_total": sum(
                row["base_visible_member_match_count"] for row in memberships
            ),
            "base_visible_member_missing_count_total": sum(
                row["base_visible_member_missing_count"] for row in memberships
            ),
            "base_nonmember_extra_count_total": sum(
                row["base_nonmember_extra_count"] for row in memberships
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
            "missing_row_selected_record_count": sum(
                row["verified_record_count"]
                for row in receipts
                if row["missing_row_rejected_field_count"] > 0
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
            "visible_membership_constraint_is_exact_on_every_base_table": True,
            "selected_record_and_quote_verification_gates_pass": True,
            "verified_fields_are_fully_partitioned_by_editor_dispositions": True,
            "missing_row_does_not_mean_visible_membership_row_was_omitted": True,
            "remaining_gap_is_grounded_record_identity_outside_visible_membership": True,
            "next_build_may_constrain_existing_grounded_record_proposal_call_with_visible_membership": True,
            "matched_same_population_counterfactual_not_observed": True,
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
            "grounded_record_membership_constraint_build_only": True,
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
        "membership_constraint_applied_tasks": 20,
        "base_visible_membership_exact_tasks": 20,
        "visible_member_count_total": 80,
        "base_visible_member_match_count_total": 80,
        "base_visible_member_missing_count_total": 0,
        "base_nonmember_extra_count_total": 0,
        "joint_source_tasks": 0,
        "grounded_source_tasks": 15,
        "no_source_tasks": 5,
        "grounded_raw_record_tasks": 15,
        "grounded_raw_record_count_total": 19,
        "selected_raw_record_tasks": 15,
        "selected_raw_record_count_total": 19,
        "verified_record_tasks": 13,
        "verified_record_count_total": 17,
        "verified_field_count_total": 48,
        "missing_row_rejected_field_count_total": 21,
        "unchanged_verified_coordinate_count_total": 20,
        "changed_safe_coordinate_count_total": 7,
        "verified_field_disposition_total": 48,
        "verified_field_disposition_is_exhaustive": True,
        "missing_row_task_count": 5,
        "missing_row_selected_record_count": 7,
        "missing_row_count_histogram": {"0": 15, "3": 3, "6": 2},
        "verified_field_count_histogram": {"0": 7, "1": 1, "2": 1, "3": 7, "6": 4},
        "changed_safe_coordinate_count_histogram": {"0": 14, "1": 5, "2": 1},
        "attributable_prediction_changed_tasks": 6,
    }
    expected_diagnosis = {
        "visible_membership_constraint_is_exact_on_every_base_table": True,
        "selected_record_and_quote_verification_gates_pass": True,
        "verified_fields_are_fully_partitioned_by_editor_dispositions": True,
        "missing_row_does_not_mean_visible_membership_row_was_omitted": True,
        "remaining_gap_is_grounded_record_identity_outside_visible_membership": True,
        "next_build_may_constrain_existing_grounded_record_proposal_call_with_visible_membership": True,
        "matched_same_population_counterfactual_not_observed": True,
        "post_synthesis_row_append_or_table_shape_change_is_forbidden": True,
        "raw_unverified_grounded_record_injection_is_forbidden": True,
        "joint_and_grounded_record_union_or_postverification_fallthrough_is_forbidden": True,
        "quality_or_deepwidebench_improvement_established": False,
        "entropy_information_gain_signed_credit_evidence_present": False,
    }
    expected_authorization = {
        "grounded_record_membership_constraint_build_only": True,
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
        raise ValueError("V2.54.00 membership/record diagnosis drifted")
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
