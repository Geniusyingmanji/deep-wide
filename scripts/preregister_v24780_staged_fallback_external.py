#!/usr/bin/env python3
"""Publish the inert V2.47.80 staged-fallback mechanism protocol.

This preregistration binds the fresh V2.47.79 visible-only population to the
clean-built V2.47.78 equal-budget 8+2 acquisition runtime.  It fixes forward
health and mechanism gates before any external execution or evaluator access.
Publication cannot acquire the shared lease, launch, evaluate, or authorize a
DeepWideBench dev64/exact-220 run.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24779_staged_fallback_contract as visible  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import design_v24779_staged_fallback_population as population_design  # noqa: E402
from scripts import diagnose_v24777_v24775_fetch_fallback as diagnosis  # noqa: E402


DATE = "20260807"
PROTOCOL_ID = "v24780_staged_fetch_fallback_external_v1"
OUTPUT = Path(f"results/v24780_staged_fallback_external_preregistration_v1_{DATE}.json")
POPULATION = population_design.OUTPUT
DIAGNOSIS = diagnosis.OUTPUT
CONTRACT = Path("src/deepwide_agent/v24779_staged_fallback_contract.py")
RUNTIME = Path("src/deepwide_agent/v24778_staged_fetch_fallback_runtime.py")
FUTURE_SURFACES = (
    Path(f"results/v24780_staged_fallback_control_plane_readiness_v1_{DATE}.json"),
    Path(f"results/v24780_staged_fallback_package_audit_v1_{DATE}.json"),
    Path(f"results/v24780_staged_fallback_preactivation_audit_v1_{DATE}.json"),
    Path(f"results/v24780_staged_fallback_activation_v1_{DATE}.json"),
    Path(f"results/v24780_staged_fallback_execution_start_v1_{DATE}.json"),
    Path(f"results/v24780_staged_fallback_forward_result_v1_{DATE}.json"),
    Path(f"results/v24780_staged_fallback_forward_audit_v1_{DATE}.json"),
    Path(f"results/v24780_staged_fallback_quality_result_v1_{DATE}.json"),
    Path(f"outputs/v24780_staged_fallback_external_v1_{DATE}"),
)
DEPENDENCIES = (
    POPULATION,
    DIAGNOSIS,
    CONTRACT,
    RUNTIME,
    Path("tests/test_v24778_staged_fetch_fallback_runtime.py"),
    Path("scripts/preregister_v24780_staged_fallback_external.py"),
    Path("tests/test_preregister_v24780_staged_fallback_external.py"),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.80 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.80 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _tracked_ordinary(relative: Path) -> Path:
    path = ROOT / relative
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or not tracked
    ):
        raise RuntimeError(f"V2.47.80 expected tracked dependency: {relative}")
    return path


def dependency_manifest() -> dict[str, str]:
    return {
        str(relative): sha256(_tracked_ordinary(relative))
        for relative in DEPENDENCIES
    }


def _parents() -> tuple[dict[str, Any], dict[str, Any]]:
    population = population_design.validate_public(_read(ROOT / POPULATION))
    diagnosed = diagnosis.validate_diagnosis(_read(ROOT / DIAGNOSIS))
    if (
        population.get("freshness", {}).get("historical_visible_entity_count")
        != 4_752
        or population.get("freshness", {}).get("selected_entity_count") != 32
        or population.get("freshness", {}).get("literal_overlap_with_history") != 0
        or population.get("freshness", {}).get("canonical_overlap_with_history")
        != 0
        or population.get("task_shape", {}).get("task_count") != 8
        or population.get("task_shape", {}).get("rows_per_task") != 4
        or population.get("claim_scope", {}).get(
            "benchmark_external_mechanism_population_only"
        )
        is not True
        or population.get("authorization", {}).get(
            "activation_or_external_launch"
        )
        is not False
        or not _sealed(population, "design_payload_sha256")
        or diagnosed.get("status")
        != "staged_eight_plus_two_fallback_is_next_equal_budget_falsification"
        or diagnosed.get("fetch_accounting", {}).get("fetch_failure_count") != 24
        or diagnosed.get("record_scope_sensitivity", {})
        .get("strict_exact_record", {})
        .get("safe_two_source_same_value_pair_count")
        != 0
        or diagnosed.get("diagnosis", {}).get(
            "reserve_source_is_known_to_be_fetchable_or_same_value"
        )
        is not False
        or diagnosed.get("authorization", {}).get(
            "append_only_equal_budget_staged_fetch_runtime_design"
        )
        is not True
        or diagnosed.get("authorization", {}).get("exact220") is not False
        or not _sealed(diagnosed, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.47.80 parent chain drifted")
    return population, diagnosed


def build_protocol(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.47.80 publication requires clean pushed HEAD")
    if require_pristine and (
        (ROOT / OUTPUT).exists()
        or (ROOT / OUTPUT).is_symlink()
        or any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in FUTURE_SURFACES
        )
    ):
        raise RuntimeError("V2.47.80 protocol/future surface is not pristine")
    population, diagnosed = _parents()
    tasks = visible.task_vector()
    if (
        len(tasks) != 8
        or any(set(task) != {"opaque_id", "question"} for task in tasks)
        or len({task["opaque_id"] for task in tasks}) != 8
    ):
        raise RuntimeError("V2.47.80 visible task vector drifted")
    manifest = dependency_manifest()
    value = {
        "artifact_version": 1,
        "role": "v24780_staged_fallback_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parents": {
            "v24777_diagnosis_sha256": sha256(ROOT / DIAGNOSIS),
            "v24779_population_design_sha256": sha256(ROOT / POPULATION),
            "v24779_visible_contract_sha256": sha256(ROOT / CONTRACT),
            "v24778_runtime_sha256": sha256(ROOT / RUNTIME),
            "population_public_seal_valid": _sealed(
                population, "design_payload_sha256"
            ),
            "diagnosis_public_seal_valid": _sealed(
                diagnosed, "diagnosis_payload_sha256"
            ),
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "population": {
            "scope": "fresh_staged_fetch_fallback_mechanism_falsification",
            "historical_entity_count": 4_752,
            "fresh_entity_count": 32,
            "task_count": 8,
            "rows_per_task": 4,
            "country_count": population["freshness"]["selected_country_count"],
            "country_max": population["freshness"]["selected_country_max"],
            "geographically_balanced_quality_sample": False,
            "search_or_quality_outcome_used_for_selection": False,
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "task_count": 8,
            "row_count": 32,
            "columns": ["Organization", "Founded", "Country"],
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
            "private_truth_provenance_or_quality_field_present": False,
        },
        "runtime": {
            "implementation": "v24778_staged_visible_entity_fetch_fallback_v1",
            "single_wave": True,
            "task_executors": 8,
            "global_model_slot_cap": 8,
            "parent_timeout_seconds": 195,
            "experiment_wall_ceiling_seconds": 210,
            "all_tasks_submitted_once": True,
            "experiment_level_resume_retry_skip_or_selective_rerun": False,
            "model_calls_per_task": 2,
            "visible_entity_queries_per_task": 4,
            "maximum_physical_fetches_per_task": 10,
            "initial_fetch_cap_per_task": 8,
            "conditional_reserve_fetch_cap_per_task": 2,
            "failed_url_retry_cap_per_task": 0,
            "reserve_routing_uses_only_successful_exact_identity_coverage": True,
            "reserve_routing_uses_field_candidate_value_or_model_judgment": False,
            "semantic_projector_changed_from_v24775": False,
            "strict_two_source_gate_changed_from_v24775": False,
            "model": {
                "proxy_url": "http://127.0.0.1:9878/responses",
                "name": "gpt-5.6-sol",
                "reasoning_effort": "low",
                "service_tier": "priority",
                "timeout_seconds": 65,
                "max_retries": 2,
            },
            "search": {
                "proxy_url": "http://127.0.0.1:9878/responses",
                "model": "gpt-5.6-sol",
                "workers": 1,
                "batch_size": 8,
                "context_size": "medium",
                "max_output_tokens": 7_000,
                "timeout_seconds": 65,
                "max_retries": 2,
                "fetch_workers": 10,
                "fetch_timeout_seconds": 20,
                "hard_fetch_deadline_seconds": 25,
            },
            "limits": {
                "wall_seconds": 180,
                "model_calls": 2,
                "search_queries": 4,
                "fetch_targets": 10,
                "search_results_per_query": 3,
                "evidence_chars": 60_000,
                "page_chars": 5_000,
                "plan_output_tokens": 4_000,
                "synthesis_output_tokens": 30_000,
                "repair_output_tokens": 12_000,
            },
        },
        "forward_health_gate": {
            "fixed_task_denominator": 8,
            "terminal_result_or_failure_as_zero_required_per_task": True,
            "no_task_level_resume_retry_skip_or_selective_rerun": True,
            "all_prediction_pairs_frozen_before_quality_surface_open": True,
            "maximum_total_physical_fetch_count": 80,
            "maximum_total_model_calls": 16,
            "protected_watchers": [
                {
                    "pid": 795336,
                    "start_ticks": 713986317,
                    "marker": "scripts/watch_v2415_r1_checkpoint_liveness.py",
                },
                {
                    "pid": 3061652,
                    "start_ticks": 747569004,
                    "marker": "scripts/watch_v24218_exact220_executor.py",
                },
            ],
            "required_checks": [
                "eight_of_eight_terminal_ordinals",
                "fixed_denominator_failure_as_zero",
                "exactly_one_submission_per_task",
                "physical_fetches_at_most_ten_per_task",
                "failed_url_retry_count_zero",
                "prediction_freeze_precedes_private_truth_or_quality_read",
                "public_forward_aggregate_is_content_free",
                "experiment_wall_within_210_seconds",
            ],
        },
        "mechanism_gate_before_private_truth": {
            "minimum_changed_task_count": 1,
            "minimum_changed_cell_count": 1,
            "minimum_projection_backed_support_set_count": 1,
            "minimum_reserve_fetch_request_count": 1,
            "minimum_reserve_usable_page_count": 1,
            "minimum_entity_slots_brought_to_two_sources_by_reserve": 1,
            "minimum_final_entity_slots_with_two_usable_identity_sources": 4,
            "nonunknown_cell_change_count_required": 0,
            "only_baseline_unknown_cells_mutable": True,
            "same_cell_value_conflict_abstains": True,
            "ordinary_cell_requires_two_registrably_independent_hosts": True,
            "failed_url_retry_count_required": 0,
            "query_text_cannot_establish_entity_alignment": True,
            "reserve_routing_cannot_use_field_or_candidate_value": True,
            "zero_trigger_stops_without_private_truth_or_quality_read": True,
            "reserve_coverage_and_safe_change_joint_activation_is_causal_proof": False,
        },
        "quality_gate_after_prediction_freeze": {
            "fixed_task_denominator": 8,
            "primary_metric": "exact_table_success_count",
            "required_exact_table_success_delta": 1,
            "candidate_cell_accuracy_nonregression": True,
            "candidate_incorrect_cell_count_nonincrease": True,
            "candidate_exact_correct_cell_count_strict_increase": True,
            "candidate_runtime_failure_count_nonincrease": True,
            "failure_as_zero": True,
            "selective_revaluation_or_error_rerun": False,
            "go_authorizes_only_task_cluster_disjoint_paired_dev64_design": True,
        },
        "entropy_credit_scope": {
            "credit_assignment_experiment": False,
            "unknown_reduction_is_positive_credit": False,
            "prediction_change_is_positive_credit": False,
            "entropy_drop_is_positive_credit": False,
            "coverage_gain_is_positive_credit": False,
            "observational_counts_may_be_reported_postfreeze": True,
            "outer_quality_or_intervention_required_before_any_future_credit_claim": True,
        },
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "private_population_truth_provenance_or_quality_file_opened_or_hashed": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_or_benchmark_forward_called_by_publication": False,
            "question_entity_url_page_prediction_or_answer_emitted": False,
        },
        "claim_scope": {
            "benchmark_external_mechanism_only": True,
            "deepwidebench_dev64_or_exact220_score": False,
            "leaderboard_or_sota": False,
            "entropy_or_credit_validated": False,
        },
        "authorization": {
            "protocol_published": True,
            "runner_or_control_plane_build": True,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value)


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    manifest = copied.get("dependency_manifest")
    runtime = copied.get("runtime", {})
    mechanism = copied.get("mechanism_gate_before_private_truth", {})
    if (
        copied.get("role") != "v24780_staged_fallback_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest()
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("population", {}).get("historical_entity_count") != 4_752
        or copied.get("population", {}).get("fresh_entity_count") != 32
        or copied.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or copied.get("task_contract", {}).get("task_count") != 8
        or copied.get("task_contract", {}).get("row_count") != 32
        or copied.get("task_contract", {}).get(
            "private_truth_provenance_or_quality_field_present"
        )
        is not False
        or runtime.get("implementation")
        != "v24778_staged_visible_entity_fetch_fallback_v1"
        or runtime.get("task_executors") != 8
        or runtime.get("global_model_slot_cap") != 8
        or runtime.get("model_calls_per_task") != 2
        or runtime.get("visible_entity_queries_per_task") != 4
        or runtime.get("maximum_physical_fetches_per_task") != 10
        or runtime.get("initial_fetch_cap_per_task") != 8
        or runtime.get("conditional_reserve_fetch_cap_per_task") != 2
        or runtime.get("failed_url_retry_cap_per_task") != 0
        or runtime.get("reserve_routing_uses_field_candidate_value_or_model_judgment")
        is not False
        or runtime.get("semantic_projector_changed_from_v24775") is not False
        or runtime.get("strict_two_source_gate_changed_from_v24775") is not False
        or runtime.get("limits", {}).get("model_calls") != 2
        or runtime.get("limits", {}).get("search_queries") != 4
        or runtime.get("limits", {}).get("fetch_targets") != 10
        or mechanism.get("minimum_changed_task_count") != 1
        or mechanism.get("minimum_changed_cell_count") != 1
        or mechanism.get("minimum_projection_backed_support_set_count") != 1
        or mechanism.get("minimum_reserve_fetch_request_count") != 1
        or mechanism.get("minimum_reserve_usable_page_count") != 1
        or mechanism.get("minimum_entity_slots_brought_to_two_sources_by_reserve")
        != 1
        or mechanism.get("failed_url_retry_count_required") != 0
        or mechanism.get("nonunknown_cell_change_count_required") != 0
        or mechanism.get("reserve_coverage_and_safe_change_joint_activation_is_causal_proof")
        is not False
        or copied.get("entropy_credit_scope", {}).get(
            "credit_assignment_experiment"
        )
        is not False
        or copied.get("claim_scope")
        != {
            "benchmark_external_mechanism_only": True,
            "deepwidebench_dev64_or_exact220_score": False,
            "leaderboard_or_sota": False,
            "entropy_or_credit_validated": False,
        }
        or copied.get("authorization")
        != {
            "protocol_published": True,
            "runner_or_control_plane_build": True,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.80 protocol drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
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
    protocol = build_protocol()
    _publish(ROOT / OUTPUT, protocol)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "protocol_id": PROTOCOL_ID,
                "task_count": protocol["task_contract"]["task_count"],
                "runner_build": protocol["authorization"][
                    "runner_or_control_plane_build"
                ],
                "external_launch": protocol["authorization"][
                    "one_external_forward_launch"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
