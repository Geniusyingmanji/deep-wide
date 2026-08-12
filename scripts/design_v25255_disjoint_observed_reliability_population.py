#!/usr/bin/env python3
"""Design a fresh entity-disjoint population for observed reliability only."""

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

from scripts import diagnose_v25209_v25208_exact220 as base  # noqa: E402


DATE = "20260812"
ROLE = "v25255_disjoint_observed_reliability_population_design"
OUTPUT = Path(f"results/v25255_disjoint_observed_reliability_population_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25255_disjoint_observed_reliability_population.py")
TEST = Path("tests/test_design_v25255_disjoint_observed_reliability_population.py")
BUILD_AUDIT = Path(f"results/v25254_outer_physical_cap_observed_build_audit_v1_{DATE}.json")
OLD_POPULATION = Path(f"results/v25240_source_package_shadow_population_freeze_v1_{DATE}.json")
OLD_POPULATION_AUDIT = Path(f"results/v25243_source_package_population_postfreeze_audit_v1_{DATE}.json")
DIAGNOSIS = Path(f"results/v25252_v25248_shadow_no_go_diagnosis_v1_{DATE}.json")
FIXED_HASHES = {
    BUILD_AUDIT: "84ac0911eb900980657e11016a4adc32b8f3fd61e7732df92eee0651dc3cff87",
    OLD_POPULATION: "45604e8e4c1d0670890289f9a165f9539bf7dcd50add3cfac4b62d1e638ddcdf",
    OLD_POPULATION_AUDIT: "b53609e617dd7107d57ffa4a109354ec41982ff14265e3d190778557c7a31fa2",
    DIAGNOSIS: "f9c0eb558092ff92c16a939bc951da2fbde2989b54dbebb91fdd794dd22fe4ec",
}
STRATA = ("short_alpha", "long_alpha", "single_hyphen_alpha", "digit_bearing")
PACKAGES_BY_STRATUM = {
    "short_alpha": 48,
    "long_alpha": 24,
    "single_hyphen_alpha": 32,
    "digit_bearing": 24,
}
TASKS_BY_STRATUM = {name: count // 2 for name, count in PACKAGES_BY_STRATUM.items()}
PACKAGES_PER_TASK = 2
TASK_COUNT = sum(TASKS_BY_STRATUM.values())
PACKAGE_COUNT = sum(PACKAGES_BY_STRATUM.values())
HISTORY_PATHS = ("src", "evaluation", "scripts", "tests", "results", "outputs")
DPKG_ARGUMENT_VECTOR = (
    "dpkg-query",
    "-W",
    "-f=${db:Status-Abbrev}\t${Package}\t${source:Package}\n",
)
CAPACITY_PROBE = {
    "probe_parent_commit": "15ba425c17dc35833dfaf1a3c9a02f19f4270eee",
    "admitted_candidate_count": 485,
    "v25240_visible_used_entity_count": 256,
    "remaining_history_zero_total": 188,
    "remaining_by_stratum": {
        "short_alpha": 83,
        "long_alpha": 29,
        "single_hyphen_alpha": 51,
        "digit_bearing": 25,
    },
    "submitted_history_probe_count": 485,
    "completed_history_probe_count": 485,
    "timeout_nonzero_stderr_incomplete_or_cancelled_count": 0,
}


def _parents() -> dict[str, str]:
    observed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    if observed != {str(path): digest for path, digest in FIXED_HASHES.items()}:
        raise RuntimeError("V2.52.55 fixed parent hash drifted")
    build = json.loads(base._ordinary(BUILD_AUDIT).read_text(encoding="utf-8"))
    old = json.loads(base._ordinary(OLD_POPULATION).read_text(encoding="utf-8"))
    old_audit = json.loads(base._ordinary(OLD_POPULATION_AUDIT).read_text(encoding="utf-8"))
    diagnosis = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    if (
        build.get("role") != "v25254_outer_physical_cap_observed_clean_build_audit"
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or build.get("authorization", {}).get("fresh_artifact_disjoint_observed_reliability_protocol_design") is not True
        or build.get("authorization", {}).get("fresh_external_activation_or_launch") is not False
        or old.get("role") != "v25240_source_package_shadow_population_freeze"
        or old.get("status") != "frozen"
        or old.get("population", {}).get("package_count") != 256
        or old_audit.get("role") != "v25243_source_package_population_postfreeze_audit"
        or old_audit.get("audit_valid") is not True
        or diagnosis.get("role") != "v25252_v25248_shadow_no_go_content_free_diagnosis"
        or diagnosis.get("authorization", {}).get("retry_resume_reuse_or_replacement_of_v25248_population") is not False
    ):
        raise RuntimeError("V2.52.55 parent authority drifted")
    return observed


def build_design(*, now: int | None = None) -> dict[str, Any]:
    value = {
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
            "supports_64_tasks_with_3_unique_entities": False,
            "supports_64_tasks_with_2_unique_entities": True,
        },
        "source_contract": {
            "source": "local_dpkg_installed_binary_to_source_index",
            "argument_vector": list(DPKG_ARGUMENT_VECTOR),
            "accepted_status_abbrev": "ii ",
            "shell": False,
            "admitted_source_name_must_not_equal_any_installed_binary_name": True,
            "selected_source_name_must_not_appear_in_v25240_visible_questions": True,
            "entity_disjoint_from_v25240_by_exact_visible_identity": True,
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
            "ranking": "sha256_v25255_source_snapshot_stratum_package_then_package",
            "history_parent_is_clean_pushed_selection_head": True,
            "history_paths": list(HISTORY_PATHS),
            "history_scan_is_git_log_case_insensitive_literal_pickaxe": True,
            "all_admitted_candidates_checked_once_with_bounded_concurrency": True,
            "history_scan_worker_cap": 16,
            "per_candidate_subprocess_timeout_seconds": 30,
            "whole_selection_wall_ceiling_seconds": 240,
            "subprocess_timeout_nonzero_stderr_incomplete_or_cancelled_fails_whole_freeze": True,
            "insufficient_history_zero_disjoint_capacity_in_any_stratum_fails_whole_freeze": True,
            "manual_choice_reorder_replacement_or_selective_backfill": False,
            "v25240_rank_salt_or_selected_entity_reuse": False,
        },
        "task_contract": {
            "runtime_keys_exactly_opaque_id_and_question": True,
            "hidden_identity_mapping_or_stratum_field_persisted": False,
            "each_question_lists_exactly_two_packages_in_frozen_order": True,
            "all_128_visible_package_entities_are_globally_unique": True,
            "requested_columns_exactly_package_latest_stable_version_license_short_purpose": True,
            "one_row_per_package_in_given_order_and_unknown_marker_requested": True,
            "opaque_id_is_hash_derived_and_contains_no_stratum": True,
            "no_gold_answer_evaluator_quality_or_historical_prediction": True,
        },
        "future_reliability_gate": {
            "single_cold_forward_on_all_64_tasks": True,
            "executor_concurrency": 32,
            "model_slot_cap": 16,
            "failure_as_zero_fixed_denominator": True,
            "required_runtime_completed_tasks": 64,
            "physical_query_cap_per_task": 4,
            "physical_fetch_cap_per_task": 14,
            "physical_model_forward_cap_per_task": 4,
            "failure_stage_vocabulary": [
                "boundary", "sparse_parent_run_and_validate", "effect_rebuild",
                "parent_freeze", "shadow_receipt", "result_envelope_validate",
            ],
            "evaluator_or_quality_metric": False,
            "header_totality_entry_or_candidate_gate_removed": True,
            "same_population_retry_resume_rerun_replacement_or_evaluation": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "selector_implementation_and_build_audit_only": True,
            "formal_dpkg_history_selection_or_task_freeze": False,
            "fresh_external_protocol_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = base.payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    probe = copied.get("pre_design_capacity_probe") or {}
    source = copied.get("source_contract") or {}
    selection = copied.get("selection_contract") or {}
    task = copied.get("task_contract") or {}
    gate = copied.get("future_reliability_gate") or {}
    authorization = copied.get("authorization") or {}
    expected_probe = {
        "aggregate_only", "local_dpkg_and_bounded_git_history_probe_called",
        "identity_plaintext_or_item_hash_emitted_or_persisted", "counts",
        "formal_ranking_selection_or_task_freeze_performed",
        "supports_64_tasks_with_3_unique_entities",
        "supports_64_tasks_with_2_unique_entities",
    }
    expected_source = {
        "source", "argument_vector", "accepted_status_abbrev", "shell",
        "admitted_source_name_must_not_equal_any_installed_binary_name",
        "selected_source_name_must_not_appear_in_v25240_visible_questions",
        "entity_disjoint_from_v25240_by_exact_visible_identity",
        "package_name_regex", "maximum_package_name_characters",
        "package_version_description_architecture_or_installed_file_read",
        "network_or_external_snapshot_endpoint",
    }
    expected_selection = {
        "strata", "packages_by_stratum", "tasks_by_stratum",
        "packages_per_task", "package_count", "task_count", "ranking",
        "history_parent_is_clean_pushed_selection_head", "history_paths",
        "history_scan_is_git_log_case_insensitive_literal_pickaxe",
        "all_admitted_candidates_checked_once_with_bounded_concurrency",
        "history_scan_worker_cap", "per_candidate_subprocess_timeout_seconds",
        "whole_selection_wall_ceiling_seconds",
        "subprocess_timeout_nonzero_stderr_incomplete_or_cancelled_fails_whole_freeze",
        "insufficient_history_zero_disjoint_capacity_in_any_stratum_fails_whole_freeze",
        "manual_choice_reorder_replacement_or_selective_backfill",
        "v25240_rank_salt_or_selected_entity_reuse",
    }
    expected_task = {
        "runtime_keys_exactly_opaque_id_and_question",
        "hidden_identity_mapping_or_stratum_field_persisted",
        "each_question_lists_exactly_two_packages_in_frozen_order",
        "all_128_visible_package_entities_are_globally_unique",
        "requested_columns_exactly_package_latest_stable_version_license_short_purpose",
        "one_row_per_package_in_given_order_and_unknown_marker_requested",
        "opaque_id_is_hash_derived_and_contains_no_stratum",
        "no_gold_answer_evaluator_quality_or_historical_prediction",
    }
    expected_gate = {
        "single_cold_forward_on_all_64_tasks", "executor_concurrency",
        "model_slot_cap", "failure_as_zero_fixed_denominator",
        "required_runtime_completed_tasks", "physical_query_cap_per_task",
        "physical_fetch_cap_per_task", "physical_model_forward_cap_per_task",
        "failure_stage_vocabulary", "evaluator_or_quality_metric",
        "header_totality_entry_or_candidate_gate_removed",
        "same_population_retry_resume_rerun_replacement_or_evaluation",
    }
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "fixed_artifact_hashes",
            "pre_design_capacity_probe", "source_contract", "selection_contract",
            "task_contract", "future_reliability_gate",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
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
        or probe.get("supports_64_tasks_with_3_unique_entities") is not False
        or probe.get("supports_64_tasks_with_2_unique_entities") is not True
        or sum(CAPACITY_PROBE["remaining_by_stratum"].values()) != CAPACITY_PROBE["remaining_history_zero_total"]
        or any(CAPACITY_PROBE["remaining_by_stratum"][name] < PACKAGES_BY_STRATUM[name] for name in STRATA)
        or source.get("argument_vector") != list(DPKG_ARGUMENT_VECTOR)
        or source.get("selected_source_name_must_not_appear_in_v25240_visible_questions") is not True
        or source.get("entity_disjoint_from_v25240_by_exact_visible_identity") is not True
        or source.get("network_or_external_snapshot_endpoint") is not False
        or selection.get("strata") != list(STRATA)
        or selection.get("packages_by_stratum") != PACKAGES_BY_STRATUM
        or selection.get("tasks_by_stratum") != TASKS_BY_STRATUM
        or selection.get("packages_per_task") != 2
        or selection.get("package_count") != 128
        or selection.get("task_count") != 64
        or selection.get("history_paths") != list(HISTORY_PATHS)
        or selection.get("history_scan_worker_cap") != 16
        or selection.get("per_candidate_subprocess_timeout_seconds") != 30
        or selection.get("whole_selection_wall_ceiling_seconds") != 240
        or selection.get("manual_choice_reorder_replacement_or_selective_backfill") is not False
        or selection.get("v25240_rank_salt_or_selected_entity_reuse") is not False
        or task.get("runtime_keys_exactly_opaque_id_and_question") is not True
        or task.get("hidden_identity_mapping_or_stratum_field_persisted") is not False
        or task.get("each_question_lists_exactly_two_packages_in_frozen_order") is not True
        or gate.get("required_runtime_completed_tasks") != 64
        or (gate.get("physical_query_cap_per_task"), gate.get("physical_fetch_cap_per_task"), gate.get("physical_model_forward_cap_per_task")) != (4, 14, 4)
        or gate.get("header_totality_entry_or_candidate_gate_removed") is not True
        or gate.get("evaluator_or_quality_metric") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "selector_implementation_and_build_audit_only": True,
            "formal_dpkg_history_selection_or_task_freeze": False,
            "fresh_external_protocol_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.55 population design drifted")
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
    print(json.dumps({"path": str(OUTPUT), "task_count": TASK_COUNT, "formal_selection": False}, sort_keys=True))


if __name__ == "__main__":
    main()
