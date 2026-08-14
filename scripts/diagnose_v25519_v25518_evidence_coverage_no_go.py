#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.55.18 mechanism NO-GO.

Only the hash-bound forward result and forward audit are opened.  No task row,
question, opaque id, URL, page, source field/value, prediction, truth,
evaluator record, score, reward, or per-task outcome is read.

The aggregate proves that evidence-deficit scheduling repaired action reach:
fifteen tasks requested and fetched an exact detail page without runtime or
budget failure.  It also proves that no candidate changed.  The frozen
aggregate intentionally does *not* expose control-versus-combined parser,
candidate, or rejection counters, so it cannot distinguish a detail-page
grammar miss from an unchanged/equivalent/ambiguous materiality rejection.
This diagnosis preserves that epistemic boundary and authorizes build-only
instrumentation and source-bound parser design, never another forward.
"""

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

from deepwide_agent import v25518_evidence_coverage_external_contract as contract  # noqa: E402
from scripts import run_v25518_evidence_coverage_external as runner  # noqa: E402


DATE = "20260814"
ROLE = "v25519_v25518_evidence_coverage_no_go_aggregate_diagnosis"
OUTPUT = Path(
    f"results/v25519_v25518_evidence_coverage_no_go_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT_SHA256 = (
    "044d11ed103e1c7205cdc97ac92c05908b02fdae2391ef3de3baa725978009c6"
)
FORWARD_AUDIT_SHA256 = (
    "90f97ed0a31570d2b6a0bf930e49191dddfc35fe31edfc9bf6b072a2c572d5c1"
)
FROZEN_INPUTS = {
    str(contract.FORWARD_RESULT): FORWARD_RESULT_SHA256,
    str(contract.FORWARD_AUDIT): FORWARD_AUDIT_SHA256,
}


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.19 expected JSON object")
    return value


def _inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    for relative, digest in FROZEN_INPUTS.items():
        if contract.sha256(ROOT / relative) != digest:
            raise RuntimeError("V2.55.19 frozen input hash drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    if (
        audit.get("role")
        != "v25518_evidence_coverage_external_forward_audit"
        or audit.get("protocol_id") != contract.PROTOCOL_ID
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or audit.get("aggregate") != forward["aggregate"]
        or audit.get("mechanism_decision") != forward["mechanism_decision"]
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not False
        or audit.get("authorization", {}).get("deepwidebench_forward_or_evaluator")
        is not False
        or not contract.sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.55.19 forward-audit barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _inputs()
    aggregate = runner.validate_aggregate(forward["aggregate"])
    deficit_tasks = aggregate["positive_evidence_deficit_candidate_tasks"]
    request_tasks = aggregate["logical_detail_request_tasks"]
    fetch_tasks = aggregate["admitted_detail_fetch_tasks"]
    page_tasks = aggregate["exact_nonredirected_detail_page_tasks"]
    changed_tasks = aggregate["treatment_changed_tasks"]
    failure_free = (
        aggregate["completed_runtime_tasks"] == aggregate["task_count"]
        and aggregate["failure_as_zero_tasks"] == 0
        and aggregate["outer_failure_tasks"] == 0
        and aggregate["control_application_failure_tasks"] == 0
        and aggregate["candidate_fetch_failure_tasks"] == 0
        and aggregate["candidate_application_failure_tasks"] == 0
        and aggregate["budget_rejection_tasks"] == 0
        and aggregate["detail_capacity_shortfall_count_total"] == 0
    )
    action_reach = (
        deficit_tasks == 15
        and request_tasks == 15
        and fetch_tasks == 15
        and page_tasks == 15
    )
    material_edit_absent = (
        changed_tasks == 0
        and aggregate["treatment_changed_coordinate_count_total"] == 0
        and aggregate["prediction_changed_tasks"] == 0
    )
    diagnosis = {
        "mechanism_gate_passed": forward["mechanism_decision"][
            "mechanism_gate_passed"
        ],
        "failed_checks": copy.deepcopy(
            forward["mechanism_decision"]["failed_checks"]
        ),
        "task_count": aggregate["task_count"],
        "terminal_tasks": aggregate["terminal_tasks"],
        "completed_runtime_tasks": aggregate["completed_runtime_tasks"],
        "multirow_eligible_link_tasks": aggregate[
            "multirow_eligible_link_tasks"
        ],
        "eligible_unique_link_count_total": aggregate[
            "eligible_unique_link_count_total"
        ],
        "positive_evidence_deficit_candidate_tasks": deficit_tasks,
        "positive_evidence_deficit_candidate_count_total": aggregate[
            "positive_evidence_deficit_candidate_count_total"
        ],
        "logical_detail_request_tasks": request_tasks,
        "admitted_detail_fetch_tasks": fetch_tasks,
        "exact_nonredirected_detail_page_tasks": page_tasks,
        "combined_generic_observation_tasks": aggregate[
            "combined_generic_observation_tasks"
        ],
        "combined_generic_observation_count_total": aggregate[
            "combined_generic_observation_count_total"
        ],
        "treatment_changed_tasks": changed_tasks,
        "treatment_changed_coordinate_count_total": aggregate[
            "treatment_changed_coordinate_count_total"
        ],
        "evidence_deficit_to_request_task_retention_numerator": request_tasks,
        "evidence_deficit_to_request_task_retention_denominator": deficit_tasks,
        "request_to_exact_page_task_retention_numerator": page_tasks,
        "request_to_exact_page_task_retention_denominator": request_tasks,
        "exact_page_to_material_edit_task_retention_numerator": changed_tasks,
        "exact_page_to_material_edit_task_retention_denominator": page_tasks,
        "runtime_failure_budget_capacity_or_fetch_is_not_the_observed_cause": failure_free,
        "evidence_deficit_action_reach_is_established": action_reach,
        "material_edit_is_absent_after_exact_detail_fetch": material_edit_absent,
        "current_aggregate_can_distinguish_parser_miss_from_materiality_rejection": False,
        "parser_miss_is_proven": False,
        "unchanged_surface_equivalent_conflict_or_list_rejection_is_proven": False,
        "primary_bottleneck": (
            "the_funnel_reaches_fifteen_exact_detail_pages_but_zero_material_"
            "edits;_the_frozen_aggregate_does_not_identify_whether_loss_occurs_"
            "at_detail_field_parsing_or_post_observation_materiality_filtering"
        ),
        "independent_prior_mechanism_evidence": {
            "source": "v25488_iana_detail_shared_parent_quality",
            "detail_page_field_surface_tasks": 20,
            "detail_page_observation_tasks": 20,
            "material_edit_tasks": 2,
            "candidate_exact_table_successes": 20,
            "base_exact_table_successes": 18,
            "scope_transfer_claim": False,
        },
        "next_design_obligations": [
            "do_not_open_v25518_task_rows_pages_predictions_or_truth_for_tuning",
            "do_not_retry_resume_rerun_replace_or_reuse_the_v25518_population",
            "add_content_free_control_and_combined_field_surface_observation_candidate_and_rejection_counters_before_any_new_forward",
            "separate_detail_page_incremental_parser_yield_from_unchanged_surface_equivalent_conflict_and_list_rejections",
            "generalize_the_independently_validated_v25483_source_bound_iana_detail_grammar_to_selected_multirow_arbitrary_length_tld_keys",
            "preserve_exact_url_row_key_page_surface_unique_coordinate_and_materiality_fail_closed_rules",
            "require_a_new_task_disjoint_mechanism_gate_before_quality_or_exact220",
            "retain_query4_fetch14_model3_and_zero_signed_entropy_credit",
        ],
    }
    checks = {
        "frozen_forward_and_audit_hash_exact": True,
        "forward_result_and_content_free_aggregate_validate": True,
        "forward_audit_valid_and_quality_not_authorized": True,
        "all_tasks_terminal_without_runtime_application_budget_capacity_or_fetch_failure": failure_free,
        "deficit_request_fetch_and_exact_page_funnel_exact_fifteen": action_reach,
        "generic_observation_aggregate_exact_three": (
            aggregate["combined_generic_observation_tasks"] == 3
            and aggregate["combined_generic_observation_count_total"] == 3
        ),
        "zero_material_edit_and_prediction_change": material_edit_absent,
        "mechanism_no_go_only_on_treatment_change_floors": (
            forward["mechanism_decision"]["failed_checks"]
            == [
                "minimum_treatment_changed_coordinate_count_total",
                "minimum_treatment_changed_tasks",
            ]
        ),
        "aggregate_epistemic_boundary_preserved": (
            diagnosis[
                "current_aggregate_can_distinguish_parser_miss_from_materiality_rejection"
            ]
            is False
            and diagnosis["parser_miss_is_proven"] is False
            and diagnosis[
                "unchanged_surface_equivalent_conflict_or_list_rejection_is_proven"
            ]
            is False
        ),
        "prior_iana_evidence_is_independent_and_not_claimed_as_transfer": diagnosis[
            "independent_prior_mechanism_evidence"
        ]["scope_transfer_claim"]
        is False,
        "mechanism_no_go_and_truth_quality_unopened": forward[
            "mechanism_decision"
        ]["mechanism_gate_passed"]
        is False,
        "positive_signed_credit_zero": aggregate["positive_signed_credit_count"]
        == 0,
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
        "content_free_aggregate_only": True,
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
            "content_free_stage_instrumentation_successor_build": not findings,
            "source_bound_multirow_iana_parser_successor_build": not findings,
            "relax_unique_coordinate_or_materiality_rules": False,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
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
    valid = copied.get("audit_valid") is True
    diagnosis = copied.get("diagnosis") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("frozen_inputs") != FROZEN_INPUTS
        or copied.get("content_free_aggregate_only") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("positive_evidence_deficit_candidate_tasks") != 15
        or diagnosis.get("logical_detail_request_tasks") != 15
        or diagnosis.get("admitted_detail_fetch_tasks") != 15
        or diagnosis.get("exact_nonredirected_detail_page_tasks") != 15
        or diagnosis.get("combined_generic_observation_tasks") != 3
        or diagnosis.get("treatment_changed_tasks") != 0
        or diagnosis.get("evidence_deficit_action_reach_is_established")
        is not True
        or diagnosis.get("material_edit_is_absent_after_exact_detail_fetch")
        is not True
        or diagnosis.get(
            "current_aggregate_can_distinguish_parser_miss_from_materiality_rejection"
        )
        is not False
        or diagnosis.get("parser_miss_is_proven") is not False
        or diagnosis.get(
            "unchanged_surface_equivalent_conflict_or_list_rejection_is_proven"
        )
        is not False
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
            "content_free_stage_instrumentation_successor_build": valid,
            "source_bound_multirow_iana_parser_successor_build": valid,
            "relax_unique_coordinate_or_materiality_rules": False,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.19 diagnosis drifted")
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
    value = build_diagnosis()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    _publish(value)
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
