#!/usr/bin/env python3
"""Aggregate-only stop diagnosis for the V2.55.38 IANA-layout NO-GO."""

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

from deepwide_agent import v25538_iana_layout_external_contract as contract  # noqa: E402
from scripts import run_v25538_iana_layout_external as runner  # noqa: E402


DATE = "20260814"
ROLE = "v25539_v25538_iana_layout_no_go_aggregate_diagnosis"
OUTPUT = Path(
    f"results/v25539_v25538_iana_layout_no_go_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT_SHA256 = (
    "2b0f954cac9cee3932ad13071855ed621f90f88a419cbfd50962ab22a8ba073e"
)
FORWARD_AUDIT_SHA256 = (
    "1d255a0da4c5805cac42ee77a95901a16b37ce11a1a5873ba0b561fe3cef5385"
)
TRANSFER_AUDIT = Path(
    "results/v25490_iana_detail_exact220_transfer_audit_v1_20260814.json"
)
TRANSFER_AUDIT_SHA256 = (
    "b35f5c695e91bbb2a74c8527a8db240ae3172e25b3e9c20074829c320a4f7970"
)
FROZEN_INPUTS = {
    str(contract.FORWARD_RESULT): FORWARD_RESULT_SHA256,
    str(contract.FORWARD_AUDIT): FORWARD_AUDIT_SHA256,
    str(TRANSFER_AUDIT): TRANSFER_AUDIT_SHA256,
}


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.39 expected JSON object")
    return value


def _inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    for relative, digest in FROZEN_INPUTS.items():
        if contract.sha256(ROOT / relative) != digest:
            raise RuntimeError("V2.55.39 frozen input hash drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    transfer = _read(TRANSFER_AUDIT)
    if (
        audit.get("role") != "v25538_iana_layout_external_forward_audit"
        or audit.get("protocol_id") != contract.PROTOCOL_ID
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or audit.get("aggregate") != forward["aggregate"]
        or audit.get("mechanism_decision") != forward["mechanism_decision"]
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not False
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or not contract.sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.55.39 forward-audit barrier drifted")
    if (
        transfer.get("role")
        != "v25490_iana_detail_exact220_visible_transfer_audit"
        or transfer.get("audit_valid") is not True
        or transfer.get("findings") != []
        or transfer.get("visible_transfer", {}).get("task_count") != 220
        or transfer.get("visible_transfer", {}).get(
            "exact_intervention_reachable_upper_bound_tasks"
        )
        != 0
        or transfer.get("transfer_decision", {}).get(
            "fixed_exact220_exact_intervention"
        )
        != "no_go"
        or transfer.get("authorization", {}).get(
            "deepwidebench_forward_or_evaluator"
        )
        is not False
    ):
        raise RuntimeError("V2.55.39 transfer barrier drifted")
    return forward, audit, transfer


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit, transfer = _inputs()
    aggregate = runner.validate_aggregate(forward["aggregate"])
    decision = forward["mechanism_decision"]
    failure_free = (
        aggregate["completed_runtime_tasks"] == aggregate["task_count"] == 20
        and aggregate["failure_as_zero_tasks"] == 0
        and aggregate["outer_failure_tasks"] == 0
        and aggregate["naked_outer_failure_tasks"] == 0
        and aggregate["budget_rejection_tasks"] == 0
        and aggregate["candidate_application_failure_tasks"] == 0
        and aggregate["parent_control_application_failure_tasks"] == 0
        and aggregate["parent_detail_fetch_failure_tasks"] == 0
        and aggregate["parent_generic_candidate_application_failure_tasks"] == 0
    )
    layout_parser_repaired = (
        aggregate["exact_iana_url_page_tasks"] == 8
        and aggregate["iana_delegation_heading_surface_tasks"] == 8
        and aggregate["iana_parenthetical_type_surface_tasks"] == 8
        and aggregate["iana_sponsoring_organisation_surface_tasks"] == 8
        and aggregate["iana_layout_complete_page_tasks"] == 8
        and aggregate["raw_field_surface_tasks"] == 8
        and aggregate["evidence_closed_observation_tasks"] == 8
        and aggregate["detail_raw_field_surface_count_total"] == 16
        and aggregate["detail_evidence_closed_observation_count_total"] == 16
    )
    materiality_bottleneck = (
        layout_parser_repaired
        and aggregate["detail_coordinate_group_count_total"] == 16
        and aggregate["detail_unchanged_coordinate_count_total"] == 14
        and aggregate["detail_available_candidate_count_total"] == 2
        and aggregate["detail_applied_coordinate_count_total"] == 2
        and aggregate["treatment_changed_tasks"] == 2
        and aggregate["treatment_changed_coordinate_count_total"] == 2
    )
    transfer_unreachable = transfer["visible_transfer"][
        "exact_intervention_reachable_upper_bound_tasks"
    ] == 0
    failed_checks = copy.deepcopy(decision["failed_checks"])
    diagnosis = {
        "mechanism_gate_passed": decision["mechanism_gate_passed"],
        "failed_checks": failed_checks,
        "task_count": aggregate["task_count"],
        "terminal_tasks": aggregate["terminal_tasks"],
        "completed_runtime_tasks": aggregate["completed_runtime_tasks"],
        "batch_wall_seconds": aggregate["batch_wall_seconds"],
        "physical_queries": aggregate["all_physical_queries"],
        "physical_fetches": aggregate["all_physical_fetches"],
        "physical_model_forwards": aggregate["all_physical_model_forwards"],
        "system_total_tokens": aggregate["system_total_tokens"],
        "multirow_eligible_link_tasks": aggregate["multirow_eligible_link_tasks"],
        "exact_iana_url_page_tasks": aggregate["exact_iana_url_page_tasks"],
        "iana_layout_complete_page_tasks": aggregate[
            "iana_layout_complete_page_tasks"
        ],
        "raw_field_surface_tasks": aggregate["raw_field_surface_tasks"],
        "evidence_closed_observation_tasks": aggregate[
            "evidence_closed_observation_tasks"
        ],
        "observation_count_total": aggregate[
            "detail_evidence_closed_observation_count_total"
        ],
        "unchanged_coordinate_count_total": aggregate[
            "detail_unchanged_coordinate_count_total"
        ],
        "material_candidate_tasks": aggregate["material_candidate_tasks"],
        "applied_coordinate_count_total": aggregate[
            "detail_applied_coordinate_count_total"
        ],
        "treatment_changed_tasks": aggregate["treatment_changed_tasks"],
        "treatment_changed_coordinate_count_total": aggregate[
            "treatment_changed_coordinate_count_total"
        ],
        "runtime_failure_is_not_the_observed_cause": failure_free,
        "iana_layout_parser_shape_repair_is_proven": layout_parser_repaired,
        "observation_to_materiality_is_the_primary_bottleneck": materiality_bottleneck,
        "exact220_intervention_reachable_upper_bound_tasks": 0,
        "exact220_transfer_is_provably_unreachable": transfer_unreachable,
        "primary_bottleneck": (
            "sixteen_valid_layout_observations_yield_fourteen_unchanged_"
            "coordinates_and_only_two_material_changes"
        ),
        "decision": "stop_iana_layout_population_line_and_return_to_production_visible_generic_search",
        "next_design_obligations": [
            "do_not_open_v25538_task_rows_pages_predictions_or_truth_for_tuning",
            "do_not_retry_resume_rerun_replace_or_reuse_the_v25538_population",
            "do_not_lower_multirow_or_four_coordinate_mechanism_thresholds_posthoc",
            "do_not_run_v25538_quality_evaluator_or_deepwidebench_transfer",
            "do_not_consume_another_iana_only_population_for_the_same_intervention",
            "select_the_next_mechanism_from_question_visible_and_same_forward_production_signals",
            "require_nonzero_reach_on_the_frozen_exact220_visible_surface_before_external_population",
            "retain_query4_fetch14_model3_failure_as_zero_and_zero_signed_entropy_credit",
        ],
    }
    checks = {
        "frozen_forward_audit_and_transfer_hashes_exact": True,
        "forward_result_and_content_free_aggregate_validate": True,
        "forward_audit_valid_and_quality_not_authorized": True,
        "all_twenty_tasks_terminal_without_failure_budget_or_application_loss": failure_free,
        "layout_heading_type_manager_and_complete_page_funnel_exact_eight": layout_parser_repaired,
        "sixteen_observations_split_into_fourteen_unchanged_and_two_material": materiality_bottleneck,
        "mechanism_failed_only_multirow_and_four_coordinate_thresholds": failed_checks
        == [
            "minimum_applied_coordinate_count_total",
            "minimum_multirow_eligible_link_tasks",
            "minimum_treatment_changed_coordinate_count_total",
        ],
        "exact220_visible_transfer_reach_zero_of_220": transfer_unreachable,
        "positive_signed_credit_zero": (
            aggregate["positive_signed_credit_count"] == 0
            and aggregate["detail_parser_positive_signed_credit_count_total"] == 0
        ),
        "task_rows_question_opaque_id_url_page_prediction_truth_or_per_task_outcome_not_opened": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_absent": True,
        "network_model_search_fetch_evaluator_benchmark_or_api_not_called": True,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "frozen_inputs": copy.deepcopy(FROZEN_INPUTS),
        "content_free_aggregate_and_prior_transfer_only": True,
        "diagnosis": diagnosis,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "task_rows_question_opaque_id_url_page_prediction_truth_evaluator_or_per_task_outcome_read": False,
        "mapping_gold_category_question_type_split_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "v25538_quality_or_truth": False,
            "v25538_retry_resume_rerun_replacement_or_threshold_relaxation": False,
            "another_iana_only_population_or_protocol": False,
            "open_v25538_task_rows_pages_predictions_or_truth_for_tuning": False,
            "production_visible_generic_successor_design": not findings,
            "new_external_protocol_or_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    diagnosis = copied.get("diagnosis") or {}
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("frozen_inputs") != FROZEN_INPUTS
        or copied.get("content_free_aggregate_and_prior_transfer_only") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("task_count") != 20
        or diagnosis.get("completed_runtime_tasks") != 20
        or diagnosis.get("exact_iana_url_page_tasks") != 8
        or diagnosis.get("iana_layout_complete_page_tasks") != 8
        or diagnosis.get("observation_count_total") != 16
        or diagnosis.get("unchanged_coordinate_count_total") != 14
        or diagnosis.get("applied_coordinate_count_total") != 2
        or diagnosis.get("treatment_changed_tasks") != 2
        or diagnosis.get("treatment_changed_coordinate_count_total") != 2
        or diagnosis.get("iana_layout_parser_shape_repair_is_proven") is not True
        or diagnosis.get("observation_to_materiality_is_the_primary_bottleneck")
        is not True
        or diagnosis.get("exact220_transfer_is_provably_unreachable") is not True
        or diagnosis.get("exact220_intervention_reachable_upper_bound_tasks") != 0
        or diagnosis.get("decision")
        != "stop_iana_layout_population_line_and_return_to_production_visible_generic_search"
        or copied.get(
            "task_rows_question_opaque_id_url_page_prediction_truth_evaluator_or_per_task_outcome_read"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "v25538_quality_or_truth": False,
            "v25538_retry_resume_rerun_replacement_or_threshold_relaxation": False,
            "another_iana_only_population_or_protocol": False,
            "open_v25538_task_rows_pages_predictions_or_truth_for_tuning": False,
            "production_visible_generic_successor_design": valid,
            "new_external_protocol_or_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.39 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
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
    value = build_diagnosis()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "diagnosis": value["diagnosis"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
