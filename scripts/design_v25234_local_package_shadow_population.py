#!/usr/bin/env python3
"""Design a network-free fresh population for the V2.52.32 shadow gate.

Candidate identities will come from the local dpkg installed-package index,
not from a public snapshot endpoint.  Four mutually-exclusive visible name
morphologies are used only for balanced population construction and are never
passed as runtime labels.  Formal selection and task persistence are not
authorized by this design artifact.
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
ROLE = "v25234_local_package_shadow_population_design"
OUTPUT = Path(
    f"results/v25234_local_package_shadow_population_design_v1_{DATE}.json"
)
SOURCE = Path("scripts/design_v25234_local_package_shadow_population.py")
TEST = Path("tests/test_design_v25234_local_package_shadow_population.py")
SHADOW_AUDIT = Path(
    f"results/v25233_header_totality_shadow_build_audit_v1_{DATE}.json"
)
HELPER_AUDIT = Path(f"results/v25231_header_totality_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    str(SHADOW_AUDIT): "eebbc5577f46998c5a97f75e0e76afac9aa7b3399f6f7a9a78d3256ced130fc2",
    str(HELPER_AUDIT): "459a275d482a62d0ea94b5d4566d33961c80a387147048e2e273150e2325fbd6",
}
MORPHOLOGIES = (
    "compact_alpha",
    "single_hyphen_alpha",
    "multi_hyphen_alpha",
    "digit_bearing",
)
PACKAGES_PER_TASK = 4
TASKS_PER_MORPHOLOGY = 16
TASK_COUNT = len(MORPHOLOGIES) * TASKS_PER_MORPHOLOGY
PACKAGES_PER_MORPHOLOGY = PACKAGES_PER_TASK * TASKS_PER_MORPHOLOGY
HISTORY_PATHS = ("src", "evaluation", "scripts", "tests", "results", "outputs")
DPKG_ARGUMENT_VECTOR = (
    "dpkg-query",
    "-W",
    "-f=${db:Status-Abbrev}\\t${Package}\\n",
)
CAPACITY_PROBE = {
    "installed_unique": 2045,
    "compact_alpha": 116,
    "single_hyphen_alpha": 353,
    "multi_hyphen_alpha": 370,
    "digit_bearing": 1122,
    "excluded_other": 84,
}


def _parents() -> dict[str, str]:
    observed = {
        str(path): base.sha256(path) for path in (SHADOW_AUDIT, HELPER_AUDIT)
    }
    if observed != FIXED_HASHES:
        raise RuntimeError("V2.52.34 fixed parent hash drifted")
    shadow = json.loads(base._ordinary(SHADOW_AUDIT).read_text(encoding="utf-8"))
    helper = json.loads(base._ordinary(HELPER_AUDIT).read_text(encoding="utf-8"))
    if (
        shadow.get("role") != "v25233_header_totality_shadow_clean_build_audit"
        or shadow.get("audit_valid") is not True
        or shadow.get("findings") != []
        or shadow.get("authorization", {}).get(
            "fresh_artifact_disjoint_shadow_reliability_protocol_design"
        )
        is not True
        or shadow.get("authorization", {}).get(
            "candidate_activation_or_prediction_change"
        )
        is not False
        or helper.get("role")
        != "v25231_header_totality_normalizer_clean_build_audit"
        or helper.get("audit_valid") is not True
    ):
        raise RuntimeError("V2.52.34 parent authority drifted")
    return observed


def build_design(*, now: int | None = None) -> dict[str, Any]:
    parents = _parents()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_artifact_hashes": parents,
        "pre_design_capacity_probe": {
            "aggregate_only": True,
            "dpkg_query_called": True,
            "package_identity_plaintext_or_hash_emitted_or_persisted": False,
            "counts": copy.deepcopy(CAPACITY_PROBE),
            "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
            "formal_ranking_history_scan_selection_or_task_freeze_performed": False,
        },
        "source_contract": {
            "source": "local_dpkg_installed_package_index",
            "argument_vector": list(DPKG_ARGUMENT_VECTOR),
            "shell": False,
            "accepted_status_abbrev": "ii ",
            "package_name_regex": "^[a-z0-9][a-z0-9+.-]*$",
            "maximum_package_name_characters": 36,
            "canonical_snapshot_is_sorted_unique_accepted_package_names": True,
            "snapshot_hash_is_sha256_of_canonical_json_vector": True,
            "network_or_external_snapshot_endpoint": False,
            "package_version_description_architecture_or_installed_file_read": False,
        },
        "morphology_contract": {
            "names": list(MORPHOLOGIES),
            "mutually_exclusive_and_exhaustive_over_admitted_population": True,
            "compact_alpha": "ascii_lowercase_only_length_5_to_12",
            "single_hyphen_alpha": "no_digit_length_7_to_36_exactly_one_hyphen",
            "multi_hyphen_alpha": "no_digit_length_7_to_36_at_least_two_hyphens",
            "digit_bearing": "contains_ascii_digit_length_4_to_36",
            "plus_dot_without_required_hyphen_and_other_shapes_excluded": True,
            "morphology_removed_before_runtime_task_vector": True,
            "morphology_is_population_balance_not_benchmark_label_or_runtime_router_signal": True,
        },
        "selection_contract": {
            "tasks_per_morphology": TASKS_PER_MORPHOLOGY,
            "packages_per_task": PACKAGES_PER_TASK,
            "packages_per_morphology": PACKAGES_PER_MORPHOLOGY,
            "task_count": TASK_COUNT,
            "ranking": "sha256_v25234_snapshot_morphology_package_then_package",
            "history_parent_is_clean_pushed_selection_head": True,
            "history_paths": list(HISTORY_PATHS),
            "history_scan_is_git_log_case_insensitive_literal_pickaxe": True,
            "first_64_ranked_history_zero_packages_per_morphology": True,
            "history_filter_is_predeclared_deterministic_not_manual_backfill": True,
            "fewer_than_64_history_zero_packages_in_any_morphology": "whole_population_no_go",
            "cross_morphology_or_global_identity_collision": "whole_population_no_go",
            "manual_choice_reorder_replacement_or_selective_backfill": False,
        },
        "task_contract": {
            "task_vector_persists_visible_package_names_inside_visible_questions": True,
            "hidden_identity_mapping_or_morphology_field_persisted": False,
            "runtime_keys_exactly_opaque_id_and_question": True,
            "each_question_lists_exactly_four_packages_in_frozen_order": True,
            "requested_columns_exactly_package_latest_stable_version_license_short_purpose": True,
            "one_row_per_package_in_given_order_and_unknown_marker_requested": True,
            "opaque_id_is_hash_derived_and_contains_no_morphology": True,
            "task_vector_interleaves_morphologies_but_runtime_receives_no_morphology": True,
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
            "activation_design_only_if_all_mechanism_checks_pass": True,
            "same_population_retry_resume_rerun_replacement_or_evaluation": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "local_population_selector_implementation_build_only": True,
            "formal_dpkg_query_history_scan_or_population_freeze": False,
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
    morphology = copied.get("morphology_contract") or {}
    selection = copied.get("selection_contract") or {}
    task = copied.get("task_contract") or {}
    gate = copied.get("future_shadow_gate") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "fixed_artifact_hashes",
            "pre_design_capacity_probe",
            "source_contract",
            "morphology_contract",
            "selection_contract",
            "task_contract",
            "future_shadow_gate",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "design_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_artifact_hashes") != FIXED_HASHES
        or probe.get("counts") != CAPACITY_PROBE
        or probe.get("aggregate_only") is not True
        or probe.get("package_identity_plaintext_or_hash_emitted_or_persisted")
        is not False
        or probe.get("formal_ranking_history_scan_selection_or_task_freeze_performed")
        is not False
        or source.get("argument_vector") != list(DPKG_ARGUMENT_VECTOR)
        or source.get("shell") is not False
        or source.get("network_or_external_snapshot_endpoint") is not False
        or morphology.get("names") != list(MORPHOLOGIES)
        or morphology.get("mutually_exclusive_and_exhaustive_over_admitted_population")
        is not True
        or morphology.get("morphology_removed_before_runtime_task_vector") is not True
        or selection.get("tasks_per_morphology") != TASKS_PER_MORPHOLOGY
        or selection.get("packages_per_task") != PACKAGES_PER_TASK
        or selection.get("packages_per_morphology") != PACKAGES_PER_MORPHOLOGY
        or selection.get("task_count") != TASK_COUNT
        or selection.get("history_paths") != list(HISTORY_PATHS)
        or selection.get("manual_choice_reorder_replacement_or_selective_backfill")
        is not False
        or task.get("runtime_keys_exactly_opaque_id_and_question") is not True
        or task.get("hidden_identity_mapping_or_morphology_field_persisted") is not False
        or gate.get("executor_concurrency") != 32
        or gate.get("model_slot_cap") != 16
        or gate.get("minimum_natural_no_bindable_header_shadow_entry") != 1
        or gate.get("minimum_natural_safe_shadow_candidate") != 1
        or gate.get("maximum_shadow_observer_failure") != 0
        or gate.get("maximum_parent_behavior_drift") != 0
        or gate.get("evaluator_or_quality_metric") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "local_population_selector_implementation_build_only": True,
            "formal_dpkg_query_history_scan_or_population_freeze": False,
            "shadow_external_protocol_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.34 local package population design drifted")
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
    value = build_design()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "task_count": value["selection_contract"]["task_count"],
                "implementation_build_only": value["authorization"][
                    "local_population_selector_implementation_build_only"
                ],
                "formal_selection": value["authorization"][
                    "formal_dpkg_query_history_scan_or_population_freeze"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
