#!/usr/bin/env python3
"""Freeze the staged design for a fresh receipt-reliability gate."""

from __future__ import annotations

import copy
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25210_receipt_disposition_observer_build as parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25211_receipt_reliability_gate_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25211_receipt_reliability_gate.py")
TEST = Path("tests/test_design_v25211_receipt_reliability_gate.py")
PARENT_AUDIT = parent.OUTPUT
EXPECTED_PARENT_AUDIT_SHA256 = (
    "4ff326f83e609972f0e8780afef981db8b318e49e2f559f2a4fe200552be915e"
)
RISK_STRATA = (
    "single_authority_exact_record",
    "single_authority_multivalue_record",
    "same_identity_multipage_record",
    "sparse_ambiguous_open_web_record",
)
TASKS_PER_STRATUM = 16
TASK_COUNT = len(RISK_STRATA) * TASKS_PER_STRATUM
EXECUTOR_CONCURRENCY = 32
MODEL_SLOT_CAP = 32
payload_sha256 = parent.payload_sha256


def _parent_barrier() -> bool:
    raw = json.loads(parent.base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    value = parent.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        parent.base.sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_SHA256
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 104
        and value["tests"]["observed"] == 104
        and value["historical_stage_sensitive_parent_suite"][
            "observer_regression"
        ]
        is False
        and value["runtime_dependency_closure"]
        == ["src/deepwide_agent/v25210_receipt_disposition_observer.py"]
        and authorization["observer_build_only"] is True
        and authorization["fresh_disjoint_reliability_gate_protocol_design"]
        is True
        and authorization[
            "runtime_integration_validator_compatibility_or_prediction_change"
        ]
        is False
        and authorization["fresh_external_activation_or_launch"] is False
        and authorization[
            "retry_resume_replacement_selective_rerun_or_revaluation"
        ]
        is False
    )


def build_design(*, now: int | None = None) -> dict[str, Any]:
    if not _parent_barrier():
        raise RuntimeError("V2.52.11 parent build audit barrier failed")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25211_fresh_disjoint_receipt_reliability_gate_design",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": parent.base.sha256(PARENT_AUDIT),
        },
        "motivation": {
            "frozen_exact220_outer_failures": 11,
            "v25135_receipt_validation_failures": 10,
            "v25180_receipt_validation_failures": 1,
            "observer_dependency_closure_file_count": 1,
            "representative_single_field_parity_cases": 2411,
            "strict_build_test_count": 104,
            "historical_outcome_used_as_runtime_router_signal": False,
        },
        "staged_protocol": [
            {
                "stage": "dual_probe_build",
                "authorization_after_prior_stage": "build_only",
                "requirements": [
                    "wrap_exact_frozen_v25135_and_v25180_validators_only_after_explicit_install",
                    "compute_v25210_observation_before_calling_each_frozen_validator_exactly_once",
                    "retain_observation_only_for_the_matching_static_parent_valueerror",
                    "preserve_exact_parent_return_or_exception_and_isolate_observer_failure",
                    "task_and_thread_local_content_free_observation_slots",
                    "no_import_time_install_and_no_runtime_prediction_budget_router_or_credit_change",
                ],
            },
            {
                "stage": "fresh_population_freeze",
                "authorization_after_prior_stage": "separate_population_audit_required",
                "requirements": [
                    "exactly_64_visible_identity_tasks_with_16_per_frozen_risk_stratum",
                    "exact_identity_history_hit_count_zero_before_population_commit",
                    "identities_selected_without_model_prediction_evaluator_or_quality_outcome",
                    "risk_stratum_never_passed_as_hidden_runtime_input_or_router_signal",
                    "runtime_task_boundary_exactly_opaque_id_and_visible_question",
                    "no_prior_external_or_deepwidebench_population_reuse",
                ],
            },
            {
                "stage": "single_observation_forward",
                "authorization_after_prior_stage": "separate_preactivation_audit_required",
                "requirements": [
                    "single_cold_forward_with_exact_production_isomorphic_parent_and_probe_only",
                    "fixed_64_denominator_concurrency_32_model_slots_32",
                    "failure_as_zero_no_retry_resume_skip_replacement_or_selective_completion",
                    "no_mapping_gold_category_split_evaluator_metric_score_reward_or_quality_feedback",
                    "no_prediction_selection_or_runtime_routing_from_observer_output",
                    "predictions_are_not_evaluated_and_cannot_support_quality_or_sota_claims",
                ],
            },
            {
                "stage": "aggregate_disposition_gate",
                "authorization_after_prior_stage": "postforward_audit_required",
                "requirements": [
                    "emit_only_parent_kind_primary_code_ordered_code_vector_and_aggregate_counts",
                    "no_task_identity_question_page_url_prediction_receipt_value_hash_or_exception_text",
                    "all_parent_accepts_have_empty_violation_vectors",
                    "all_matching_parent_rejects_have_nonempty_finite_violation_vectors",
                    "observer_failure_count_zero_and_exactly_64_terminal_rows",
                    "same_parent_and_identical_violation_vector_natural_count_at_least_3",
                ],
            },
            {
                "stage": "candidate_specific_safe_state_observer",
                "authorization_after_prior_stage": "build_only_if_aggregate_gate_go",
                "requirements": [
                    "prove_completed_production_and_prediction_preservation_without_emitting_prediction",
                    "prove_candidate_dynamic_effect_absent_or_already_terminal_as_applicable",
                    "reject_every_adjacent_unsafe_single_field_mutation",
                    "no_compatibility_install_until_another_fresh_disjoint_matched_gate",
                    "entropy_or_information_gain_cannot_create_or_flip_signed_credit",
                ],
            },
        ],
        "population_design": {
            "risk_strata": list(RISK_STRATA),
            "tasks_per_stratum": TASKS_PER_STRATUM,
            "task_count": TASK_COUNT,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "probability_at_least_one_event_if_event_rate_is_five_percent": 0.962475860497,
            "population_is_mechanism_coverage_gate_not_quality_benchmark": True,
            "strata_are_visible_external_design_factors_not_benchmark_labels": True,
        },
        "aggregate_go_gate": {
            "terminal_rows": TASK_COUNT,
            "observer_failures": 0,
            "minimum_matching_parent_rejections": 3,
            "minimum_same_parent_identical_violation_vector_count": 3,
            "accepted_parent_with_nonempty_violation_vector": 0,
            "rejected_parent_with_empty_violation_vector": 0,
            "prediction_or_quality_metric_read": False,
            "positive_signed_credit_count": 0,
        },
        "stop_rules": {
            "zero_or_fewer_than_three_reproductions": "no_safe_state_or_compatibility_design",
            "heterogeneous_vectors_without_three_exact_matches": "no_safe_state_or_compatibility_design",
            "observer_parent_parity_failure": "quarantine_forward_and_fix_observer_only",
            "label_gold_evaluator_or_score_access": "kill_and_quarantine_as_invalid",
            "same_population_retry_or_selective_completion": "quarantine_as_invalid",
            "future_expansion": "requires_new_history_disjoint_population_and_separate_authorization",
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "dual_receipt_failure_probe_build_only": True,
            "fresh_population_selection_or_external_access": False,
            "external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    population = copied.get("population_design") or {}
    gate = copied.get("aggregate_go_gate") or {}
    authorization = copied.get("authorization") or {}
    stages = copied.get("staged_protocol") or []
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25211_fresh_disjoint_receipt_reliability_gate_design"
        or copied.get("parent_build_audit", {}).get("sha256")
        != EXPECTED_PARENT_AUDIT_SHA256
        or [row.get("stage") for row in stages]
        != [
            "dual_probe_build",
            "fresh_population_freeze",
            "single_observation_forward",
            "aggregate_disposition_gate",
            "candidate_specific_safe_state_observer",
        ]
        or population.get("risk_strata") != list(RISK_STRATA)
        or population.get("tasks_per_stratum") != TASKS_PER_STRATUM
        or population.get("task_count") != TASK_COUNT
        or population.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or population.get("model_slot_cap") != MODEL_SLOT_CAP
        or population.get("population_is_mechanism_coverage_gate_not_quality_benchmark")
        is not True
        or gate
        != {
            "terminal_rows": TASK_COUNT,
            "observer_failures": 0,
            "minimum_matching_parent_rejections": 3,
            "minimum_same_parent_identical_violation_vector_count": 3,
            "accepted_parent_with_nonempty_violation_vector": 0,
            "rejected_parent_with_empty_violation_vector": 0,
            "prediction_or_quality_metric_read": False,
            "positive_signed_credit_count": 0,
        }
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "dual_receipt_failure_probe_build_only": True,
            "fresh_population_selection_or_external_access": False,
            "external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.11 receipt reliability gate design drifted")
    return copied


def main() -> None:
    value = build_design()
    parent.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "task_count": value["population_design"]["task_count"],
                "probe_build_only": value["authorization"][
                    "dual_receipt_failure_probe_build_only"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
