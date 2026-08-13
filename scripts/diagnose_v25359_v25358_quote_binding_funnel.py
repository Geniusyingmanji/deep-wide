#!/usr/bin/env python3
"""Content-free funnel diagnosis for the V2.53.58 repaired mechanism."""

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

from deepwide_agent import v25358_repaired_second_fresh_pep_external_contract as contract  # noqa: E402
from scripts import run_v25358_repaired_second_fresh_pep_external as runner  # noqa: E402


OUTPUT = Path("results/v25359_v25358_quote_binding_funnel_diagnosis_v1_20260813.json")


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.59 expected JSON object")
    return value


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    audit = _read_json(contract.FORWARD_AUDIT)
    rows = [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or forward.get("mechanism_decision", {}).get("mechanism_gate_passed")
        is not False
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.53.59 parent barrier drifted")
    completed = [row for row in rows if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    first = [receipt["first_wave_receipt"] for receipt in receipts]
    second = [receipt["second_wave_receipt"] for receipt in receipts]
    grounded = [receipt["grounded_plan_receipt"] for receipt in receipts]
    facts = [receipt["grounded_fact_receipt"] for receipt in receipts]
    bindings = [fact["record_binding_receipt"] for fact in facts]
    funnel = {
        "terminal_tasks": len(rows),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in rows),
        "pre_effect_projection_completed_tasks": sum(
            row["pre_effect_query_contract_receipt"] is not None for row in rows
        ),
        "first_wave_usable_pages": sum(value["usable_page_count"] for value in first),
        "first_wave_projected_pages": sum(
            value["projected_page_count"] for value in first
        ),
        "first_wave_retained_records": sum(
            value["retained_record_count"] for value in first
        ),
        "second_wave_usable_pages": sum(
            value["physical_union_usable_page_count"] for value in second
        ),
        "second_wave_projected_pages": sum(
            value["projected_page_count"] for value in second
        ),
        "grounded_plan_strict_valid_tasks": sum(
            value["model_output_strictly_valid"] for value in grounded
        ),
        "grounded_plan_strategy_applied_tasks": sum(
            value["strategy_applied"] for value in grounded
        ),
        "records_member_present_tasks": sum(
            value["records_member_present"] for value in facts
        ),
        "record_output_strict_valid_tasks": sum(
            value["record_output_strictly_valid"] for value in facts
        ),
        "parsed_records": sum(value["parsed_record_count"] for value in bindings),
        "parsed_fields": sum(value["parsed_field_count"] for value in bindings),
        "rejected_page_reference_records": sum(
            value["rejected_page_reference_count"] for value in bindings
        ),
        "rejected_nonunique_or_nonverbatim_quote_records": sum(
            value["rejected_nonunique_or_nonverbatim_quote_count"]
            for value in bindings
        ),
        "rejected_row_identity_records": sum(
            value["rejected_row_identity_binding_count"] for value in bindings
        ),
        "rejected_field_binding_records": sum(
            value["rejected_field_binding_count"] for value in bindings
        ),
        "ambiguous_same_quote_records": sum(
            value["ambiguous_same_quote_record_count"] for value in bindings
        ),
        "verified_quote_records": sum(
            value["verified_quote_record_count"] for value in bindings
        ),
        "verified_fields": sum(value["verified_field_count"] for value in bindings),
        "rendered_records": sum(value["rendered_record_count"] for value in bindings),
        "candidate_prompt_changed_tasks": sum(
            row["candidate_production_prompt_changed"] for row in completed
        ),
        "prediction_changed_tasks": sum(
            row["prediction_changed"] for row in completed
        ),
        "attributable_prediction_changed_tasks": sum(
            row["attributable_prediction_change"] for row in completed
        ),
        "search_request_failure_count": sum(
            row["hard_failure_health"]["search_request_failures"] for row in rows
        ),
        "non_search_hard_failure_count": sum(
            amount
            for row in rows
            for name, amount in row["hard_failure_health"].items()
            if name != "search_request_failures"
        ),
    }
    diagnosis = {
        "mechanism_gate_passed": False,
        "pre_effect_query_contract_bug_eliminated": (
            funnel["completed_runtime_tasks"] == 20
            and funnel["failure_as_zero_tasks"] == 0
            and funnel["pre_effect_projection_completed_tasks"] == 20
        ),
        "retrieval_surface_is_nonempty": (
            funnel["first_wave_usable_pages"] == 118
            and funnel["second_wave_usable_pages"] == 78
        ),
        "joint_record_envelope_is_total_and_strict": (
            funnel["records_member_present_tasks"] == 20
            and funnel["record_output_strict_valid_tasks"] == 20
        ),
        "quote_page_and_row_binding_leave_eleven_records_for_field_disposition": (
            funnel["parsed_records"] == 13
            and funnel["rejected_nonunique_or_nonverbatim_quote_records"] == 2
            and funnel["rejected_page_reference_records"] == 0
            and funnel["rejected_row_identity_records"] == 0
            and funnel["rejected_field_binding_records"] == 11
        ),
        "record_atomic_field_rejection_is_terminal_content_bottleneck": (
            funnel["verified_quote_records"] == 0
            and funnel["verified_fields"] == 0
            and funnel["candidate_prompt_changed_tasks"] == 0
        ),
        "next_build_only_candidate_should_apply_per_field_disposition_within_same_quote_page_row_coordinate": True,
        "nonverbatim_quote_page_reference_row_identity_value_and_column_conflicts_must_remain_fail_closed": True,
        "same_quote_same_column_conflicting_values_must_reject_record": True,
        "query_fetch_model_context_token_wall_and_network_caps_must_not_expand": True,
        "same_population_retry_resume_or_replay_forbidden": True,
        "entropy_or_information_gain_signed_credit": 0,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25359_v25358_quote_binding_content_free_funnel_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": funnel,
        "diagnosis": diagnosis,
        "content_policy": {
            "question_query_url_title_page_quote_identity_field_value_prediction_answer_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "only_content_free_counts_failure_classes_and_parent_hashes_aggregated": True,
        },
        "authorization": {
            "per_field_quote_verifier_build_only_design": True,
            "same_population_retry_resume_replay_backfill_or_replacement": False,
            "new_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    funnel = copied.get("content_free_funnel") or {}
    diagnosis = copied.get("diagnosis") or {}
    required_true = (
        "pre_effect_query_contract_bug_eliminated",
        "retrieval_surface_is_nonempty",
        "joint_record_envelope_is_total_and_strict",
        "quote_page_and_row_binding_leave_eleven_records_for_field_disposition",
        "record_atomic_field_rejection_is_terminal_content_bottleneck",
        "next_build_only_candidate_should_apply_per_field_disposition_within_same_quote_page_row_coordinate",
        "nonverbatim_quote_page_reference_row_identity_value_and_column_conflicts_must_remain_fail_closed",
        "same_quote_same_column_conflicting_values_must_reject_record",
        "query_fetch_model_context_token_wall_and_network_caps_must_not_expand",
        "same_population_retry_resume_or_replay_forbidden",
    )
    if (
        copied.get("role")
        != "v25359_v25358_quote_binding_content_free_funnel_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or diagnosis.get("mechanism_gate_passed") is not False
        or any(diagnosis.get(name) is not True for name in required_true)
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or funnel.get("terminal_tasks") != 20
        or funnel.get("completed_runtime_tasks") != 20
        or funnel.get("failure_as_zero_tasks") != 0
        or funnel.get("parsed_records") != 13
        or funnel.get("parsed_fields") != 52
        or funnel.get("rejected_nonunique_or_nonverbatim_quote_records") != 2
        or funnel.get("rejected_field_binding_records") != 11
        or funnel.get("verified_quote_records") != 0
        or funnel.get("candidate_prompt_changed_tasks") != 0
        or copied.get("authorization")
        != {
            "per_field_quote_verifier_build_only_design": True,
            "same_population_retry_resume_replay_backfill_or_replacement": False,
            "new_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        }
        or copied.get("content_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
    ):
        raise RuntimeError("V2.53.59 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    payload = (
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "role": value["role"],
                "content_free_funnel": value["content_free_funnel"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
