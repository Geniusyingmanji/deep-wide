#!/usr/bin/env python3
"""Design a third repository-history-disjoint checkpoint reliability population.

The design records only aggregate capacity from a completed bounded local
``dpkg-query`` plus Git-history probe.  It does not persist package identities,
per-item hashes, rankings, selections, questions, or a task vector.  Formal
selection and any model/search execution require later, separately pushed
authorities.
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

from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from scripts import diagnose_v25209_v25208_exact220 as base  # noqa: E402


DATE = "20260812"
ROLE = "v25273_third_disjoint_checkpoint_population_design"
OUTPUT = Path(f"results/v25273_third_disjoint_checkpoint_population_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25273_third_disjoint_checkpoint_population.py")
TEST = Path("tests/test_design_v25273_third_disjoint_checkpoint_population.py")

BUILD_AUDIT = Path(f"results/v25272_validated_production_checkpoint_build_audit_v1_{DATE}.json")
DIAGNOSIS = Path(f"results/v25270_v25267_production_only_reliability_diagnosis_v1_{DATE}.json")
FIRST_POPULATION = Path(f"results/v25240_source_package_shadow_population_freeze_v1_{DATE}.json")
FIRST_AUDIT = Path(f"results/v25243_source_package_population_postfreeze_audit_v1_{DATE}.json")
SECOND_POPULATION = Path(f"results/v25256_disjoint_observed_reliability_population_freeze_v1_{DATE}.json")
SECOND_AUDIT = Path(f"results/v25259_disjoint_observed_reliability_population_postfreeze_audit_v1_{DATE}.json")
FIXED_HASHES = {
    BUILD_AUDIT: "f7c7d16def15ff80ae76b3a506da345c38b3c28286bf4c3e05eec84480f5aace",
    DIAGNOSIS: "b298439d5f4987771a2e660913647be29eddafcc38e491cc89cb7840e5ab7a12",
    FIRST_POPULATION: "45604e8e4c1d0670890289f9a165f9539bf7dcd50add3cfac4b62d1e638ddcdf",
    FIRST_AUDIT: "b53609e617dd7107d57ffa4a109354ec41982ff14265e3d190778557c7a31fa2",
    SECOND_POPULATION: "f383ecf184174bb16dd757899a3c48fd9d3d2bc3e2fb58f2e804fb2d888dd31b",
    SECOND_AUDIT: "b23301c0b160d998bc3b30d7a1d0870da8aaaf3fac6784b9cc6ce15f484d6b98",
}

STRATA = ("short_alpha", "long_alpha", "single_hyphen_alpha")
PACKAGES_BY_STRATUM = {
    "short_alpha": 20,
    "long_alpha": 4,
    "single_hyphen_alpha": 16,
}
TASKS_BY_STRATUM = {name: count // 2 for name, count in PACKAGES_BY_STRATUM.items()}
PACKAGES_PER_TASK = 2
PACKAGE_COUNT = sum(PACKAGES_BY_STRATUM.values())
TASK_COUNT = sum(TASKS_BY_STRATUM.values())
HISTORY_PATHS = ("src", "evaluation", "scripts", "tests", "results", "outputs")
DPKG_ARGUMENT_VECTOR = (
    "dpkg-query",
    "-W",
    "-f=${db:Status-Abbrev}\t${Package}\t${source:Package}\n",
)
CAPACITY_PROBE = {
    "probe_parent_commit": "dd75e10dddfbfea9084895787099293ccfb15b1c",
    "canonical_source_snapshot_sha256": "ca4bb77c4fadfaffa4e0c214b57c92e36a927f84e72b7bea37937ec28a2ff242",
    "source_candidate_count": 564,
    "admitted_stratum_candidate_count": 485,
    "excluded_other_count": 79,
    "history_zero_total": 60,
    "history_zero_by_stratum": {
        "short_alpha": 35,
        "long_alpha": 5,
        "single_hyphen_alpha": 19,
        "digit_bearing": 1,
    },
    "history_positive_by_stratum": {
        "short_alpha": 138,
        "long_alpha": 96,
        "single_hyphen_alpha": 100,
        "digit_bearing": 91,
    },
    "submitted_history_probe_count": 564,
    "completed_history_probe_count": 564,
    "timeout_nonzero_stderr_incomplete_or_cancelled_count": 0,
}


def _parents() -> dict[str, str]:
    observed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    expected = {str(path): digest for path, digest in FIXED_HASHES.items()}
    if observed != expected:
        raise RuntimeError("V2.52.73 fixed parent hash drifted")
    build = json.loads(base._ordinary(BUILD_AUDIT).read_text(encoding="utf-8"))
    diagnosis = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    first = json.loads(base._ordinary(FIRST_POPULATION).read_text(encoding="utf-8"))
    first_audit = json.loads(base._ordinary(FIRST_AUDIT).read_text(encoding="utf-8"))
    second = json.loads(base._ordinary(SECOND_POPULATION).read_text(encoding="utf-8"))
    second_audit = json.loads(base._ordinary(SECOND_AUDIT).read_text(encoding="utf-8"))
    if (
        build.get("role") != "v25272_validated_production_checkpoint_clean_build_audit"
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or build.get("authorization", {}).get(
            "fresh_benchmark_external_reliability_protocol_design"
        )
        is not True
        or build.get("authorization", {}).get("runtime_activation_or_external_launch")
        is not False
        or diagnosis.get("role")
        != "v25270_v25267_production_only_content_free_reliability_diagnosis"
        or diagnosis.get("authorization", {}).get(
            "external_forward_or_new_deepwidebench_rollout"
        )
        is not False
        or first.get("role") != "v25240_source_package_shadow_population_freeze"
        or first.get("population", {}).get("package_count") != 256
        or first_audit.get("audit_valid") is not True
        or first_audit.get("findings") != []
        or second.get("role") != "v25256_disjoint_observed_reliability_population_freeze"
        or second.get("population", {}).get("package_count") != 128
        or second_audit.get("audit_valid") is not True
        or second_audit.get("findings") != []
    ):
        raise RuntimeError("V2.52.73 parent authority drifted")
    return observed


def build_design(*, now: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_artifact_hashes": _parents(),
        "pre_design_capacity_probe": {
            "aggregate_only": True,
            "local_dpkg_and_bounded_git_history_probe_called": True,
            "identity_plaintext_or_item_hash_emitted_or_persisted": False,
            "counts": copy.deepcopy(CAPACITY_PROBE),
            "formal_ranking_selection_or_task_freeze_performed": False,
            "supports_fixed_20_tasks_with_2_unique_entities": True,
            "digit_bearing_excluded_because_pair_capacity_is_one": True,
        },
        "source_contract": {
            "source": "local_dpkg_installed_binary_to_source_index",
            "argument_vector": list(DPKG_ARGUMENT_VECTOR),
            "accepted_status_abbrev": "ii ",
            "shell": False,
            "admitted_source_name_must_not_equal_any_installed_binary_name": True,
            "selected_entity_must_have_zero_literal_history_hits_through_selection_parent": True,
            "history_zero_includes_all_tracked_prior_populations_and_public_task_artifacts": True,
            "repository_history_disjoint_does_not_claim_conceptual_or_unseen_benchmark_identity": True,
            "exact_entity_overlap_with_first_and_second_populations_must_be_zero": True,
            "package_name_regex": "^[a-z0-9][a-z0-9+.-]*$",
            "maximum_package_name_characters": 48,
            "package_version_description_architecture_or_installed_file_read": False,
            "network_or_external_snapshot_endpoint": False,
        },
        "selection_contract": {
            "strata": list(STRATA),
            "packages_by_stratum": copy.deepcopy(PACKAGES_BY_STRATUM),
            "tasks_by_stratum": copy.deepcopy(TASKS_BY_STRATUM),
            "packages_per_task": PACKAGES_PER_TASK,
            "package_count": PACKAGE_COUNT,
            "task_count": TASK_COUNT,
            "ranking": "sha256_v25273_source_snapshot_stratum_package_then_package",
            "history_parent_is_clean_pushed_selection_head": True,
            "history_paths": list(HISTORY_PATHS),
            "history_scan_is_git_log_case_insensitive_literal_pickaxe": True,
            "all_admitted_candidates_checked_once_with_bounded_concurrency": True,
            "history_scan_worker_cap": 16,
            "per_candidate_subprocess_timeout_seconds": 30,
            "whole_selection_wall_ceiling_seconds": 240,
            "timeout_nonzero_stderr_incomplete_or_cancelled_fails_whole_freeze": True,
            "insufficient_history_zero_capacity_in_any_selected_stratum_fails_whole_freeze": True,
            "manual_choice_reorder_cross_stratum_fill_replacement_or_selective_backfill": False,
            "first_or_second_population_rank_salt_or_entity_reuse": False,
        },
        "task_contract": {
            "runtime_keys_exactly_opaque_id_and_question": True,
            "hidden_identity_mapping_or_stratum_field_persisted": False,
            "each_question_lists_exactly_two_same_stratum_packages_in_frozen_order": True,
            "all_40_visible_package_entities_are_globally_unique": True,
            "requested_columns_exactly_package_latest_stable_version_license_short_purpose": True,
            "one_row_per_package_in_given_order_and_unknown_marker_requested": True,
            "opaque_id_is_hash_derived_and_contains_no_stratum": True,
            "no_gold_answer_evaluator_quality_or_historical_prediction": True,
        },
        "future_paired_reliability_gate": {
            "single_cold_forward_on_all_20_tasks": True,
            "one_live_provider_search_execution_per_task": True,
            "same_checkpoint_exports_clean_control_and_three_local_fault_variants": True,
            "local_fault_variants": [
                "parent_prediction_binding",
                "result_envelope_build",
                "result_envelope_validate",
            ],
            "required_clean_control_terminal": 20,
            "required_injected_variants_terminal": 60,
            "prediction_cost_and_effect_must_be_byte_identical_across_variants": True,
            "additional_model_search_or_fetch_effect_for_fault_variants": False,
            "untrusted_checkpoint_acceptance_count": 0,
            "normal_path_parent_behavior_drift_count": 0,
            "physical_query_cap_per_task": 4,
            "physical_fetch_cap_per_task": 14,
            "physical_model_forward_cap_per_task": 4,
            "budget_rejection_task_count": 0,
            "failure_as_zero_fixed_denominator": True,
            "evaluator_or_quality_metric": False,
            "same_population_retry_resume_rerun_replacement_or_evaluation": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "selector_implementation_and_build_audit_only": True,
            "formal_dpkg_history_selection_or_task_freeze": False,
            "fresh_external_protocol_or_launch": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = contract.payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    probe = copied.get("pre_design_capacity_probe") or {}
    source = copied.get("source_contract") or {}
    selection = copied.get("selection_contract") or {}
    task = copied.get("task_contract") or {}
    gate = copied.get("future_paired_reliability_gate") or {}
    authorization = copied.get("authorization") or {}
    expected_probe = {
        "aggregate_only",
        "local_dpkg_and_bounded_git_history_probe_called",
        "identity_plaintext_or_item_hash_emitted_or_persisted",
        "counts",
        "formal_ranking_selection_or_task_freeze_performed",
        "supports_fixed_20_tasks_with_2_unique_entities",
        "digit_bearing_excluded_because_pair_capacity_is_one",
    }
    expected_source = {
        "source",
        "argument_vector",
        "accepted_status_abbrev",
        "shell",
        "admitted_source_name_must_not_equal_any_installed_binary_name",
        "selected_entity_must_have_zero_literal_history_hits_through_selection_parent",
        "history_zero_includes_all_tracked_prior_populations_and_public_task_artifacts",
        "repository_history_disjoint_does_not_claim_conceptual_or_unseen_benchmark_identity",
        "exact_entity_overlap_with_first_and_second_populations_must_be_zero",
        "package_name_regex",
        "maximum_package_name_characters",
        "package_version_description_architecture_or_installed_file_read",
        "network_or_external_snapshot_endpoint",
    }
    expected_selection = {
        "strata",
        "packages_by_stratum",
        "tasks_by_stratum",
        "packages_per_task",
        "package_count",
        "task_count",
        "ranking",
        "history_parent_is_clean_pushed_selection_head",
        "history_paths",
        "history_scan_is_git_log_case_insensitive_literal_pickaxe",
        "all_admitted_candidates_checked_once_with_bounded_concurrency",
        "history_scan_worker_cap",
        "per_candidate_subprocess_timeout_seconds",
        "whole_selection_wall_ceiling_seconds",
        "timeout_nonzero_stderr_incomplete_or_cancelled_fails_whole_freeze",
        "insufficient_history_zero_capacity_in_any_selected_stratum_fails_whole_freeze",
        "manual_choice_reorder_cross_stratum_fill_replacement_or_selective_backfill",
        "first_or_second_population_rank_salt_or_entity_reuse",
    }
    expected_task = {
        "runtime_keys_exactly_opaque_id_and_question",
        "hidden_identity_mapping_or_stratum_field_persisted",
        "each_question_lists_exactly_two_same_stratum_packages_in_frozen_order",
        "all_40_visible_package_entities_are_globally_unique",
        "requested_columns_exactly_package_latest_stable_version_license_short_purpose",
        "one_row_per_package_in_given_order_and_unknown_marker_requested",
        "opaque_id_is_hash_derived_and_contains_no_stratum",
        "no_gold_answer_evaluator_quality_or_historical_prediction",
    }
    expected_gate = {
        "single_cold_forward_on_all_20_tasks",
        "one_live_provider_search_execution_per_task",
        "same_checkpoint_exports_clean_control_and_three_local_fault_variants",
        "local_fault_variants",
        "required_clean_control_terminal",
        "required_injected_variants_terminal",
        "prediction_cost_and_effect_must_be_byte_identical_across_variants",
        "additional_model_search_or_fetch_effect_for_fault_variants",
        "untrusted_checkpoint_acceptance_count",
        "normal_path_parent_behavior_drift_count",
        "physical_query_cap_per_task",
        "physical_fetch_cap_per_task",
        "physical_model_forward_cap_per_task",
        "budget_rejection_task_count",
        "failure_as_zero_fixed_denominator",
        "evaluator_or_quality_metric",
        "same_population_retry_resume_rerun_replacement_or_evaluation",
    }
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "fixed_artifact_hashes",
            "pre_design_capacity_probe",
            "source_contract",
            "selection_contract",
            "task_contract",
            "future_paired_reliability_gate",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "design_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_artifact_hashes")
        != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or set(probe) != expected_probe
        or set(source) != expected_source
        or set(selection) != expected_selection
        or set(task) != expected_task
        or set(gate) != expected_gate
        or probe.get("counts") != CAPACITY_PROBE
        or probe.get("aggregate_only") is not True
        or probe.get("identity_plaintext_or_item_hash_emitted_or_persisted") is not False
        or probe.get("formal_ranking_selection_or_task_freeze_performed") is not False
        or probe.get("supports_fixed_20_tasks_with_2_unique_entities") is not True
        or probe.get("digit_bearing_excluded_because_pair_capacity_is_one") is not True
        or sum(CAPACITY_PROBE["history_zero_by_stratum"].values()) != 60
        or any(
            CAPACITY_PROBE["history_zero_by_stratum"][name]
            < PACKAGES_BY_STRATUM[name]
            for name in STRATA
        )
        or source.get("argument_vector") != list(DPKG_ARGUMENT_VECTOR)
        or source.get("selected_entity_must_have_zero_literal_history_hits_through_selection_parent")
        is not True
        or source.get("history_zero_includes_all_tracked_prior_populations_and_public_task_artifacts")
        is not True
        or source.get("repository_history_disjoint_does_not_claim_conceptual_or_unseen_benchmark_identity")
        is not True
        or source.get("exact_entity_overlap_with_first_and_second_populations_must_be_zero")
        is not True
        or source.get("network_or_external_snapshot_endpoint") is not False
        or selection.get("strata") != list(STRATA)
        or selection.get("packages_by_stratum") != PACKAGES_BY_STRATUM
        or selection.get("tasks_by_stratum") != TASKS_BY_STRATUM
        or selection.get("packages_per_task") != 2
        or selection.get("package_count") != 40
        or selection.get("task_count") != 20
        or selection.get("history_paths") != list(HISTORY_PATHS)
        or selection.get("history_scan_worker_cap") != 16
        or selection.get("per_candidate_subprocess_timeout_seconds") != 30
        or selection.get("whole_selection_wall_ceiling_seconds") != 240
        or selection.get("manual_choice_reorder_cross_stratum_fill_replacement_or_selective_backfill")
        is not False
        or task.get("runtime_keys_exactly_opaque_id_and_question") is not True
        or task.get("hidden_identity_mapping_or_stratum_field_persisted") is not False
        or task.get("each_question_lists_exactly_two_same_stratum_packages_in_frozen_order")
        is not True
        or gate.get("required_clean_control_terminal") != 20
        or gate.get("required_injected_variants_terminal") != 60
        or gate.get("local_fault_variants")
        != ["parent_prediction_binding", "result_envelope_build", "result_envelope_validate"]
        or gate.get("prediction_cost_and_effect_must_be_byte_identical_across_variants")
        is not True
        or gate.get("additional_model_search_or_fetch_effect_for_fault_variants") is not False
        or gate.get("untrusted_checkpoint_acceptance_count") != 0
        or gate.get("normal_path_parent_behavior_drift_count") != 0
        or (
            gate.get("physical_query_cap_per_task"),
            gate.get("physical_fetch_cap_per_task"),
            gate.get("physical_model_forward_cap_per_task"),
        )
        != (4, 14, 4)
        or gate.get("budget_rejection_task_count") != 0
        or gate.get("evaluator_or_quality_metric") is not False
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "selector_implementation_and_build_audit_only": True,
            "formal_dpkg_history_selection_or_task_freeze": False,
            "fresh_external_protocol_or_launch": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.73 population design drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_design()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "task_count": TASK_COUNT,
                "package_count": PACKAGE_COUNT,
                "formal_selection": False,
                "external_launch": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
