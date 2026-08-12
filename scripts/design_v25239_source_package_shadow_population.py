#!/usr/bin/env python3
"""Design an entity-disjoint source-package population successor.

This is design-only.  The aggregate capacity probe was computed from the
local dpkg database and emitted no package identity or item hash.  Formal
selection, history scanning, task persistence, model/search execution, and
benchmark evaluation remain unauthorized.
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

from scripts import diagnose_v25209_v25208_exact220 as base  # noqa: E402


DATE = "20260812"
ROLE = "v25239_source_package_shadow_population_design"
OUTPUT = Path(f"results/v25239_source_package_shadow_population_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25239_source_package_shadow_population.py")
TEST = Path("tests/test_design_v25239_source_package_shadow_population.py")
POSTATTEMPT = Path(
    f"results/v25238_v25237_local_population_postattempt_audit_v1_{DATE}.json"
)
SHADOW_AUDIT = Path(f"results/v25233_header_totality_shadow_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    str(POSTATTEMPT): "054cf11aba1450891eeec9671278733c2e81fde967a918cc218e46fc99fcefb4",
    str(SHADOW_AUDIT): "eebbc5577f46998c5a97f75e0e76afac9aa7b3399f6f7a9a78d3256ced130fc2",
}
STRATA = (
    "short_alpha",
    "long_alpha",
    "single_hyphen_alpha",
    "digit_bearing",
)
CAPACITY_PROBE = {
    "installed_binary_unique": 2045,
    "source_name_disjoint_from_all_installed_binary_names": 564,
    "short_alpha": 173,
    "long_alpha": 101,
    "single_hyphen_alpha": 119,
    "digit_bearing": 92,
    "excluded_other": 79,
}
PACKAGES_PER_TASK = 4
TASKS_PER_STRATUM = 16
PACKAGES_PER_STRATUM = PACKAGES_PER_TASK * TASKS_PER_STRATUM
TASK_COUNT = len(STRATA) * TASKS_PER_STRATUM
HISTORY_PATHS = ("src", "evaluation", "scripts", "tests", "results", "outputs")
DPKG_ARGUMENT_VECTOR = (
    "dpkg-query",
    "-W",
    "-f=${db:Status-Abbrev}\\t${Package}\\t${source:Package}\\n",
)


def _parents() -> dict[str, str]:
    observed = {str(path): base.sha256(path) for path in (POSTATTEMPT, SHADOW_AUDIT)}
    if observed != FIXED_HASHES:
        raise RuntimeError("V2.52.39 fixed parent hash drifted")
    post = json.loads(base._ordinary(POSTATTEMPT).read_text(encoding="utf-8"))
    shadow = json.loads(base._ordinary(SHADOW_AUDIT).read_text(encoding="utf-8"))
    if (
        post.get("role") != "v25238_v25237_local_population_postattempt_audit"
        or post.get("disposition", {}).get("status") != "terminal_no_result"
        or post.get("authorization", {}).get("same_v25237_population_freeze_or_second_attempt") is not False
        or post.get("authorization", {}).get("fresh_entity_disjoint_successor_design") is not True
        or shadow.get("role") != "v25233_header_totality_shadow_clean_build_audit"
        or shadow.get("audit_valid") is not True
        or shadow.get("findings") != []
    ):
        raise RuntimeError("V2.52.39 parent authority drifted")
    return observed


def build_design(*, now: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_artifact_hashes": _parents(),
        "pre_design_capacity_probe": {
            "aggregate_only": True,
            "local_dpkg_query_called": True,
            "identity_plaintext_or_item_hash_emitted_or_persisted": False,
            "counts": copy.deepcopy(CAPACITY_PROBE),
            "counts_are_mutually_exclusive_and_conserve_total": True,
            "formal_ranking_history_scan_selection_or_task_freeze_performed": False,
        },
        "source_contract": {
            "source": "local_dpkg_installed_binary_to_source_index",
            "argument_vector": list(DPKG_ARGUMENT_VECTOR),
            "accepted_status_abbrev": "ii ",
            "shell": False,
            "canonical_binary_snapshot_is_sorted_unique": True,
            "canonical_source_snapshot_is_sorted_unique": True,
            "admitted_source_name_must_not_equal_any_installed_binary_name": True,
            "entity_disjoint_from_v25235_binary_population_by_construction": True,
            "package_name_regex": "^[a-z0-9][a-z0-9+.-]*$",
            "maximum_package_name_characters": 48,
            "package_version_description_architecture_or_installed_file_read": False,
            "network_or_external_snapshot_endpoint": False,
        },
        "stratum_contract": {
            "names": list(STRATA),
            "mutually_exclusive_over_admitted_population": True,
            "short_alpha": "ascii_lowercase_only_length_5_to_8",
            "long_alpha": "ascii_lowercase_only_length_9_to_16",
            "single_hyphen_alpha": "exactly_two_nonempty_ascii_alpha_segments",
            "digit_bearing": "contains_ascii_digit_length_4_to_48",
            "all_other_source_name_shapes_excluded": True,
            "stratum_removed_before_runtime_task_vector": True,
            "stratum_is_population_balance_not_benchmark_label_or_runtime_router_signal": True,
        },
        "selection_contract": {
            "tasks_per_stratum": TASKS_PER_STRATUM,
            "packages_per_task": PACKAGES_PER_TASK,
            "packages_per_stratum": PACKAGES_PER_STRATUM,
            "task_count": TASK_COUNT,
            "ranking": "sha256_v25239_source_snapshot_stratum_package_then_package",
            "history_parent_is_clean_pushed_selection_head": True,
            "history_paths": list(HISTORY_PATHS),
            "history_scan_is_git_log_case_insensitive_literal_pickaxe": True,
            "all_admitted_candidates_checked_once_with_bounded_concurrency": True,
            "history_scan_worker_cap": 16,
            "per_candidate_subprocess_timeout_seconds": 30,
            "whole_selection_wall_ceiling_seconds": 240,
            "subprocess_returncode_timeout_and_stderr_are_terminal_receipt_fields": True,
            "first_64_ranked_history_zero_packages_per_stratum": True,
            "fewer_than_64_history_zero_packages_in_any_stratum": "whole_population_no_go",
            "any_subprocess_timeout_nonzero_return_or_stderr": "whole_population_no_go",
            "manual_choice_reorder_replacement_or_selective_backfill": False,
            "v25237_command_population_or_rank_salt_reused": False,
        },
        "task_contract": {
            "task_vector_persists_visible_package_names_inside_visible_questions": True,
            "runtime_keys_exactly_opaque_id_and_question": True,
            "hidden_identity_mapping_or_stratum_field_persisted": False,
            "each_question_lists_exactly_four_packages_in_frozen_order": True,
            "requested_columns_exactly_package_latest_stable_version_license_short_purpose": True,
            "one_row_per_package_in_given_order_and_unknown_marker_requested": True,
            "opaque_id_is_hash_derived_and_contains_no_stratum": True,
            "no_gold_answer_evaluator_quality_or_historical_prediction": True,
        },
        "future_shadow_gate": {
            "single_cold_forward_on_all_64_tasks": True,
            "executor_concurrency": 32,
            "model_slot_cap": 16,
            "failure_as_zero_fixed_denominator": True,
            "evaluator_or_quality_metric": False,
            "shadow_candidate_never_changes_parent_prediction": True,
            "minimum_natural_no_bindable_header_shadow_entry": 1,
            "minimum_natural_safe_shadow_candidate": 1,
            "maximum_shadow_observer_failure": 0,
            "maximum_parent_behavior_drift": 0,
            "same_population_retry_resume_rerun_replacement_or_evaluation": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "source_package_selector_implementation_build_only": True,
            "formal_dpkg_query_history_scan_selection_or_task_freeze": False,
            "shadow_external_protocol_or_launch": False,
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
    strata = copied.get("stratum_contract") or {}
    selection = copied.get("selection_contract") or {}
    task = copied.get("task_contract") or {}
    gate = copied.get("future_shadow_gate") or {}
    authorization = copied.get("authorization") or {}
    expected_top = {
        "artifact_version", "role", "created_at_unix", "fixed_artifact_hashes",
        "pre_design_capacity_probe", "source_contract", "stratum_contract",
        "selection_contract", "task_contract", "future_shadow_gate",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_or_information_gain_assigns_signed_credit", "authorization",
        "design_payload_sha256",
    }
    expected_probe = {
        "aggregate_only", "local_dpkg_query_called",
        "identity_plaintext_or_item_hash_emitted_or_persisted", "counts",
        "counts_are_mutually_exclusive_and_conserve_total",
        "formal_ranking_history_scan_selection_or_task_freeze_performed",
    }
    expected_source = {
        "source", "argument_vector", "accepted_status_abbrev", "shell",
        "canonical_binary_snapshot_is_sorted_unique",
        "canonical_source_snapshot_is_sorted_unique",
        "admitted_source_name_must_not_equal_any_installed_binary_name",
        "entity_disjoint_from_v25235_binary_population_by_construction",
        "package_name_regex", "maximum_package_name_characters",
        "package_version_description_architecture_or_installed_file_read",
        "network_or_external_snapshot_endpoint",
    }
    expected_strata = {
        "names", "mutually_exclusive_over_admitted_population", "short_alpha",
        "long_alpha", "single_hyphen_alpha", "digit_bearing",
        "all_other_source_name_shapes_excluded",
        "stratum_removed_before_runtime_task_vector",
        "stratum_is_population_balance_not_benchmark_label_or_runtime_router_signal",
    }
    expected_selection = {
        "tasks_per_stratum", "packages_per_task", "packages_per_stratum",
        "task_count", "ranking", "history_parent_is_clean_pushed_selection_head",
        "history_paths", "history_scan_is_git_log_case_insensitive_literal_pickaxe",
        "all_admitted_candidates_checked_once_with_bounded_concurrency",
        "history_scan_worker_cap", "per_candidate_subprocess_timeout_seconds",
        "whole_selection_wall_ceiling_seconds",
        "subprocess_returncode_timeout_and_stderr_are_terminal_receipt_fields",
        "first_64_ranked_history_zero_packages_per_stratum",
        "fewer_than_64_history_zero_packages_in_any_stratum",
        "any_subprocess_timeout_nonzero_return_or_stderr",
        "manual_choice_reorder_replacement_or_selective_backfill",
        "v25237_command_population_or_rank_salt_reused",
    }
    expected_task = {
        "task_vector_persists_visible_package_names_inside_visible_questions",
        "runtime_keys_exactly_opaque_id_and_question",
        "hidden_identity_mapping_or_stratum_field_persisted",
        "each_question_lists_exactly_four_packages_in_frozen_order",
        "requested_columns_exactly_package_latest_stable_version_license_short_purpose",
        "one_row_per_package_in_given_order_and_unknown_marker_requested",
        "opaque_id_is_hash_derived_and_contains_no_stratum",
        "no_gold_answer_evaluator_quality_or_historical_prediction",
    }
    expected_gate = {
        "single_cold_forward_on_all_64_tasks", "executor_concurrency",
        "model_slot_cap", "failure_as_zero_fixed_denominator",
        "evaluator_or_quality_metric", "shadow_candidate_never_changes_parent_prediction",
        "minimum_natural_no_bindable_header_shadow_entry",
        "minimum_natural_safe_shadow_candidate", "maximum_shadow_observer_failure",
        "maximum_parent_behavior_drift",
        "same_population_retry_resume_rerun_replacement_or_evaluation",
    }
    if (
        set(copied) != expected_top
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_artifact_hashes") != FIXED_HASHES
        or set(probe) != expected_probe
        or set(source) != expected_source
        or set(strata) != expected_strata
        or set(selection) != expected_selection
        or set(task) != expected_task
        or set(gate) != expected_gate
        or probe.get("counts") != CAPACITY_PROBE
        or sum(CAPACITY_PROBE[name] for name in (*STRATA, "excluded_other"))
        != CAPACITY_PROBE["source_name_disjoint_from_all_installed_binary_names"]
        or probe.get("aggregate_only") is not True
        or probe.get("identity_plaintext_or_item_hash_emitted_or_persisted") is not False
        or probe.get("formal_ranking_history_scan_selection_or_task_freeze_performed") is not False
        or source.get("argument_vector") != list(DPKG_ARGUMENT_VECTOR)
        or source.get("admitted_source_name_must_not_equal_any_installed_binary_name") is not True
        or source.get("entity_disjoint_from_v25235_binary_population_by_construction") is not True
        or source.get("network_or_external_snapshot_endpoint") is not False
        or strata.get("names") != list(STRATA)
        or strata.get("mutually_exclusive_over_admitted_population") is not True
        or strata.get("stratum_removed_before_runtime_task_vector") is not True
        or selection.get("tasks_per_stratum") != TASKS_PER_STRATUM
        or selection.get("packages_per_task") != PACKAGES_PER_TASK
        or selection.get("packages_per_stratum") != PACKAGES_PER_STRATUM
        or selection.get("task_count") != TASK_COUNT
        or selection.get("history_paths") != list(HISTORY_PATHS)
        or selection.get("history_scan_worker_cap") != 16
        or selection.get("whole_selection_wall_ceiling_seconds") != 240
        or selection.get("subprocess_returncode_timeout_and_stderr_are_terminal_receipt_fields") is not True
        or selection.get("manual_choice_reorder_replacement_or_selective_backfill") is not False
        or selection.get("v25237_command_population_or_rank_salt_reused") is not False
        or task.get("runtime_keys_exactly_opaque_id_and_question") is not True
        or task.get("hidden_identity_mapping_or_stratum_field_persisted") is not False
        or gate.get("executor_concurrency") != 32
        or gate.get("model_slot_cap") != 16
        or gate.get("minimum_natural_no_bindable_header_shadow_entry") != 1
        or gate.get("minimum_natural_safe_shadow_candidate") != 1
        or gate.get("maximum_shadow_observer_failure") != 0
        or gate.get("maximum_parent_behavior_drift") != 0
        or gate.get("evaluator_or_quality_metric") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization != {
            "source_package_selector_implementation_build_only": True,
            "formal_dpkg_query_history_scan_selection_or_task_freeze": False,
            "shadow_external_protocol_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.39 source package population design drifted")
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
    print(json.dumps({
        "path": str(OUTPUT),
        "task_count": value["selection_contract"]["task_count"],
        "implementation_build_only": value["authorization"]["source_package_selector_implementation_build_only"],
        "formal_selection": value["authorization"]["formal_dpkg_query_history_scan_selection_or_task_freeze"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
