#!/usr/bin/env python3
"""Publish the inert V2.47.84 projection-funnel mechanism protocol.

This preregistration binds the fresh V2.47.83 visible population to the frozen
V2.47.78 staged-fallback runtime and specifies a future trusted-child adapter
that observes its fully validated private semantic catalog exactly once with
the V2.47.81 counts-only funnel.  It does not implement or launch that adapter.

Publication never opens the V2.47.83 evaluator-only population or any consumed
V2.47.80 output.  It cannot acquire the shared lease, call a model or search
endpoint, run a benchmark forward, open quality/evaluator surfaces, or
authorize dev64, exact-220, entropy credit, leaderboard, or SOTA claims.
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

from deepwide_agent import v24778_staged_fetch_fallback_runtime as base_runtime  # noqa: E402
from deepwide_agent import v24781_projection_conversion_funnel as funnel  # noqa: E402
from deepwide_agent import v24783_projection_funnel_contract as visible  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24783_projection_funnel_population_freeze as freeze  # noqa: E402
from scripts import design_v24783_projection_funnel_population as population_design  # noqa: E402


DATE = "20260807"
PROTOCOL_ID = "v24784_projection_funnel_external_v1"
OUTPUT = Path(
    f"results/v24784_projection_funnel_external_preregistration_v1_{DATE}.json"
)
POPULATION = population_design.OUTPUT
POPULATION_FREEZE_AUDIT = freeze.AUDIT
VISIBLE_CONTRACT = population_design.CONTRACT
BASE_RUNTIME = Path("src/deepwide_agent/v24778_staged_fetch_fallback_runtime.py")
BASE_RUNTIME_TEST = Path("tests/test_v24778_staged_fetch_fallback_runtime.py")
FUNNEL = Path("src/deepwide_agent/v24781_projection_conversion_funnel.py")
FUNNEL_TEST = Path("tests/test_v24781_projection_conversion_funnel.py")
SOURCE = Path("scripts/preregister_v24784_projection_funnel_external.py")
TEST = Path("tests/test_preregister_v24784_projection_funnel_external.py")
DEPENDENCIES = (
    POPULATION,
    POPULATION_FREEZE_AUDIT,
    VISIBLE_CONTRACT,
    BASE_RUNTIME,
    BASE_RUNTIME_TEST,
    FUNNEL,
    FUNNEL_TEST,
    SOURCE,
    TEST,
)
FUTURE_SURFACES = (
    OUTPUT,
    Path(f"results/v24784_projection_funnel_integration_build_audit_v1_{DATE}.json"),
    Path(f"results/v24784_projection_funnel_package_audit_v1_{DATE}.json"),
    Path(f"results/v24784_projection_funnel_preactivation_audit_v1_{DATE}.json"),
    Path(f"results/v24784_projection_funnel_activation_v1_{DATE}.json"),
    Path(f"results/v24784_projection_funnel_execution_start_v1_{DATE}.json"),
    Path(f"results/v24784_projection_funnel_forward_result_v1_{DATE}.json"),
    Path(f"results/v24784_projection_funnel_forward_audit_v1_{DATE}.json"),
    Path(f"outputs/v24784_projection_funnel_external_v1_{DATE}"),
)
PROTECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
TASK_COUNT = 8
ROWS_PER_TASK = 4
TASK_EXECUTORS = 8
GLOBAL_MODEL_SLOT_CAP = 8
PARENT_TIMEOUT_SECONDS = 195
EXPERIMENT_WALL_CEILING_SECONDS = 210
MODEL_CALLS_PER_TASK = 2
LOGICAL_QUERIES_PER_TASK = 4
INITIAL_FETCH_CAP_PER_TASK = 8
RESERVE_FETCH_CAP_PER_TASK = 2
TOTAL_FETCH_CAP_PER_TASK = 10
FAILED_URL_RETRY_CAP_PER_TASK = 0
FUNNEL_STATUSES = (
    "validated",
    "private_catalog_absent",
    "base_runtime_failure",
    "funnel_validation_failure",
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
        raise RuntimeError(f"V2.47.84 expected ordinary public JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.84 expected public JSON object")
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
        or relative.parts[:1] in {("evaluation",), ("outputs",)}
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or not tracked
    ):
        raise RuntimeError(f"V2.47.84 expected tracked public dependency: {relative}")
    return path


def dependency_manifest() -> dict[str, str]:
    return {
        str(relative): sha256(_tracked_ordinary(relative))
        for relative in DEPENDENCIES
    }


def _parents() -> tuple[dict[str, Any], dict[str, Any]]:
    population = _read(ROOT / POPULATION)
    audit = _read(ROOT / POPULATION_FREEZE_AUDIT)
    population_design.validate_public(population)
    freeze.validate_audit(audit)
    if (
        population.get("role")
        != "v24783_projection_funnel_population_design"
        or population.get("freshness", {}).get("historical_visible_entity_count")
        != 4_784
        or population.get("freshness", {}).get("selected_entity_count") != 32
        or population.get("freshness", {}).get("literal_overlap_with_history") != 0
        or population.get("freshness", {}).get("canonical_overlap_with_history")
        != 0
        or population.get("eligibility_and_selection", {}).get("country_cap") != 7
        or population.get("eligibility_and_selection", {}).get(
            "selected_country_count_vector_sorted"
        )
        != [4, 7, 7, 7, 7]
        or population.get("authorization", {}).get("inert_v24784_protocol_design")
        is not True
        or population.get("authorization", {}).get("activation_or_external_launch")
        is not False
        or audit.get("role")
        != "v24783_projection_funnel_population_freeze_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get(
            "inert_v24784_protocol_publication"
        )
        is not True
        or audit.get("authorization", {}).get("runtime_or_control_plane_build")
        is not False
        or audit.get("source_policy", {}).get(
            "v24783_private_population_bytes_opened_parsed_imported_copied_or_hashed"
        )
        is not False
        or audit.get("source_policy", {}).get(
            "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed"
        )
        is not False
        or not _sealed(population, "design_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.84 public parent surface drifted")
    return population, audit


def _future_pristine() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in FUTURE_SURFACES
    )


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
        raise RuntimeError("V2.47.84 protocol requires clean pushed HEAD")
    if require_pristine and not _future_pristine():
        raise FileExistsError("V2.47.84 protocol or future surface exists")
    population, audit = _parents()
    tasks = visible.task_vector()
    if (
        len(tasks) != TASK_COUNT
        or any(set(task) != {"opaque_id", "question"} for task in tasks)
        or len({task["opaque_id"] for task in tasks}) != TASK_COUNT
    ):
        raise RuntimeError("V2.47.84 visible task vector drifted")
    manifest = dependency_manifest()
    value = {
        "artifact_version": 1,
        "role": "v24784_projection_funnel_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parents": {
            "population_design_sha256": sha256(ROOT / POPULATION),
            "population_freeze_audit_sha256": sha256(
                ROOT / POPULATION_FREEZE_AUDIT
            ),
            "visible_contract_sha256": sha256(ROOT / VISIBLE_CONTRACT),
            "public_population_seal_valid": True,
            "public_freeze_audit_seal_valid": True,
            "private_population_opened_or_hashed": False,
            "v24780_output_opened_or_hashed": False,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "population": {
            "scope": "fresh_projection_conversion_mechanism_localization",
            "historical_entity_count": population["freshness"][
                "historical_visible_entity_count"
            ],
            "fresh_entity_count": population["freshness"][
                "selected_entity_count"
            ],
            "task_count": TASK_COUNT,
            "rows_per_task": ROWS_PER_TASK,
            "country_count": population["eligibility_and_selection"][
                "selected_country_count"
            ],
            "country_max": population["eligibility_and_selection"][
                "selected_country_max"
            ],
            "country_count_vector_sorted": population[
                "eligibility_and_selection"
            ]["selected_country_count_vector_sorted"],
            "search_model_prediction_quality_or_evaluator_outcome_used_for_selection": False,
            "mechanism_localization_population_not_quality_sample": True,
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "private_truth_provenance_quality_category_split_or_score_field_present": False,
            "task_count": len(tasks),
            "row_count": len(tasks) * ROWS_PER_TASK,
            "columns": ["Organization", "Founded", "Country"],
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        },
        "base_runtime_effect_envelope": {
            "implementation": base_runtime.POLICY_ID,
            "task_executors": TASK_EXECUTORS,
            "global_model_slot_cap": GLOBAL_MODEL_SLOT_CAP,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "model_calls_per_task": MODEL_CALLS_PER_TASK,
            "logical_queries_per_task": LOGICAL_QUERIES_PER_TASK,
            "initial_fetch_cap_per_task": INITIAL_FETCH_CAP_PER_TASK,
            "conditional_reserve_fetch_cap_per_task": RESERVE_FETCH_CAP_PER_TASK,
            "maximum_physical_fetches_per_task": TOTAL_FETCH_CAP_PER_TASK,
            "failed_url_retry_cap_per_task": FAILED_URL_RETRY_CAP_PER_TASK,
            "same_model_query_and_total_fetch_caps_as_v24780_mechanism": True,
            "all_tasks_submitted_once": True,
            "experiment_level_resume_retry_skip_or_selective_rerun": False,
        },
        "future_trusted_child_integration": {
            "implementation_status": "not_built",
            "base_task_function": "run_v24778_task",
            "base_result_validator": "validate_result",
            "funnel_function": "build_projection_conversion_funnel",
            "funnel_receipt_validator": "validate_receipt",
            "ordered_steps": [
                "run_base_runtime_once",
                "fully_validate_base_result_once",
                "read_validated_private_semantic_catalog_inside_same_child_only",
                "build_and_validate_v24781_funnel_at_most_once",
                "emit_base_predictions_plus_fixed_vocabulary_counts_only_receipt",
            ],
            "catalog_source": "validated_v24778_private_semantic_catalog_inside_same_child",
            "catalog_or_private_content_serialized_to_parent_or_public_receipt": False,
            "question_identity_field_value_query_url_host_page_prediction_or_private_content_hash_in_funnel_receipt": False,
            "funnel_status_vocabulary": list(FUNNEL_STATUSES),
            "absent_or_failed_funnel_fabricates_zero_counts": False,
            "base_predictions_or_semantic_projector_changed_by_observer": False,
            "additional_model_search_fetch_or_evaluator_effect": 0,
            "positive_entropy_or_task_credit_assigned": False,
        },
        "funnel_observation_schema": {
            "policy_id": funnel.POLICY_ID,
            "role": funnel.ROLE,
            "fixed_count_fields": list(funnel.COUNT_FIELDS),
            "fixed_reason_partition": list(funnel.REASONS),
            "reason_partition_exact_required": True,
            "projection_source_partition_exact_required": True,
            "projection_receipt_replay_exact_required": True,
            "same_private_catalog_observed_without_projection_change_required": True,
            "frozen_projector_support_and_conflict_rules_unchanged_required": True,
        },
        "forward_health_gate": {
            "fixed_task_denominator": TASK_COUNT,
            "terminal_result_or_failure_as_zero_required_per_task": True,
            "all_task_ordinals_submitted_once": True,
            "maximum_total_model_calls": TASK_COUNT * MODEL_CALLS_PER_TASK,
            "maximum_total_physical_fetch_count": TASK_COUNT
            * TOTAL_FETCH_CAP_PER_TASK,
            "failed_url_retry_count_required": 0,
            "all_predictions_frozen_before_any_private_truth_or_quality_read": True,
            "no_task_level_resume_retry_skip_or_selective_rerun": True,
            "experiment_wall_within_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "protected_watchers": [
                {"pid": pid, "start_ticks": ticks, "marker": marker}
                for pid, ticks, marker in PROTECTED_WATCHERS
            ],
        },
        "mechanism_gate_before_private_truth": {
            "validated_funnel_receipt_count_required": TASK_COUNT,
            "private_catalog_absent_count_required": 0,
            "base_runtime_failure_count_required": 0,
            "funnel_validation_failure_count_required": 0,
            "minimum_projection_emitted_task_count": 1,
            "minimum_projection_backed_support_task_count": 1,
            "minimum_unconflicted_projection_backed_unknown_proposal_task_count": 1,
            "minimum_changed_task_count": 1,
            "minimum_changed_cell_count": 1,
            "nonunknown_changed_cell_count_required": 0,
            "minimum_task_local_joint_projection_backed_safe_change_task_count": 1,
            "task_local_joint_definition": [
                "validated_v24781_funnel_receipt",
                "projection_backed_eligible_support_set_count_at_least_one",
                "unconflicted_projection_backed_unknown_proposal_count_at_least_one",
                "v24778_semantic_final_changed_cell_count_at_least_one",
                "candidate_changes_only_baseline_unknown_cells",
                "two_independent_sources_and_conflict_abstention_unchanged",
            ],
            "cross_task_aggregate_cooccurrence_may_substitute_for_task_local_joint": False,
            "joint_activation_is_causal_or_quality_proof": False,
            "zero_trigger_stops_without_private_truth_quality_or_evaluator_read": True,
            "strict_go_authorizes_only_task_cluster_disjoint_paired_dev64_design": True,
        },
        "diagnostic_scope_if_gate_fails": {
            "fixed_reason_counts_may_localize_conversion_stage": True,
            "counts_may_select_or_tune_a_same_population_retry": False,
            "failed_or_scored_population_may_be_rerun": False,
            "mechanism_no_go_not_a_benchmark_quality_result": True,
        },
        "entropy_credit_scope": {
            "credit_assignment_experiment": False,
            "projection_count_is_positive_credit": False,
            "coverage_gain_is_positive_credit": False,
            "entropy_drop_is_positive_credit": False,
            "prediction_change_is_positive_credit": False,
            "outer_quality_or_intervention_required_before_any_future_credit_claim": True,
        },
        "source_policy": {
            "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "v24783_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_publication": False,
            "question_entity_field_value_url_page_prediction_or_answer_emitted": False,
        },
        "claim_scope": {
            "benchmark_external_mechanism_localization_only": True,
            "projection_funnel_effect_measured": False,
            "deepwidebench_dev64_or_exact220_score": False,
            "entropy_or_credit_validated": False,
            "leaderboard_or_sota": False,
        },
        "authorization": {
            "protocol_published": True,
            "append_only_trusted_child_integration_build": True,
            "runner_or_control_plane_build": False,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_or_evaluator_surface_open": False,
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
    population = copied.get("population", {})
    task = copied.get("task_contract", {})
    envelope = copied.get("base_runtime_effect_envelope", {})
    integration = copied.get("future_trusted_child_integration", {})
    schema = copied.get("funnel_observation_schema", {})
    health = copied.get("forward_health_gate", {})
    mechanism = copied.get("mechanism_gate_before_private_truth", {})
    if (
        copied.get("role") != "v24784_projection_funnel_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest()
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or population.get("historical_entity_count") != 4_784
        or population.get("fresh_entity_count") != 32
        or population.get("task_count") != TASK_COUNT
        or population.get("country_count_vector_sorted") != [4, 7, 7, 7, 7]
        or task.get("runtime_input_keys") != ["opaque_id", "question"]
        or task.get("private_truth_provenance_quality_category_split_or_score_field_present")
        is not False
        or task.get("task_count") != TASK_COUNT
        or task.get("row_count") != TASK_COUNT * ROWS_PER_TASK
        or envelope.get("implementation") != base_runtime.POLICY_ID
        or envelope.get("task_executors") != TASK_EXECUTORS
        or envelope.get("global_model_slot_cap") != GLOBAL_MODEL_SLOT_CAP
        or envelope.get("model_calls_per_task") != MODEL_CALLS_PER_TASK
        or envelope.get("logical_queries_per_task") != LOGICAL_QUERIES_PER_TASK
        or envelope.get("initial_fetch_cap_per_task")
        != INITIAL_FETCH_CAP_PER_TASK
        or envelope.get("conditional_reserve_fetch_cap_per_task")
        != RESERVE_FETCH_CAP_PER_TASK
        or envelope.get("maximum_physical_fetches_per_task")
        != TOTAL_FETCH_CAP_PER_TASK
        or envelope.get("failed_url_retry_cap_per_task")
        != FAILED_URL_RETRY_CAP_PER_TASK
        or envelope.get("experiment_level_resume_retry_skip_or_selective_rerun")
        is not False
        or integration.get("implementation_status") != "not_built"
        or integration.get("funnel_status_vocabulary") != list(FUNNEL_STATUSES)
        or integration.get("absent_or_failed_funnel_fabricates_zero_counts")
        is not False
        or integration.get("base_predictions_or_semantic_projector_changed_by_observer")
        is not False
        or integration.get("additional_model_search_fetch_or_evaluator_effect") != 0
        or integration.get("positive_entropy_or_task_credit_assigned") is not False
        or schema.get("fixed_count_fields") != list(funnel.COUNT_FIELDS)
        or schema.get("fixed_reason_partition") != list(funnel.REASONS)
        or any(
            schema.get(name) is not True
            for name in (
                "reason_partition_exact_required",
                "projection_source_partition_exact_required",
                "projection_receipt_replay_exact_required",
                "same_private_catalog_observed_without_projection_change_required",
                "frozen_projector_support_and_conflict_rules_unchanged_required",
            )
        )
        or health.get("fixed_task_denominator") != TASK_COUNT
        or health.get("maximum_total_model_calls")
        != TASK_COUNT * MODEL_CALLS_PER_TASK
        or health.get("maximum_total_physical_fetch_count")
        != TASK_COUNT * TOTAL_FETCH_CAP_PER_TASK
        or health.get("failed_url_retry_count_required") != 0
        or mechanism.get("validated_funnel_receipt_count_required") != TASK_COUNT
        or mechanism.get("private_catalog_absent_count_required") != 0
        or mechanism.get("base_runtime_failure_count_required") != 0
        or mechanism.get("funnel_validation_failure_count_required") != 0
        or mechanism.get("minimum_projection_emitted_task_count") != 1
        or mechanism.get("minimum_projection_backed_support_task_count") != 1
        or mechanism.get(
            "minimum_unconflicted_projection_backed_unknown_proposal_task_count"
        )
        != 1
        or mechanism.get("minimum_changed_task_count") != 1
        or mechanism.get("minimum_changed_cell_count") != 1
        or mechanism.get("nonunknown_changed_cell_count_required") != 0
        or mechanism.get(
            "minimum_task_local_joint_projection_backed_safe_change_task_count"
        )
        != 1
        or mechanism.get(
            "cross_task_aggregate_cooccurrence_may_substitute_for_task_local_joint"
        )
        is not False
        or mechanism.get("joint_activation_is_causal_or_quality_proof") is not False
        or copied.get("entropy_credit_scope", {}).get("credit_assignment_experiment")
        is not False
        or copied.get("source_policy")
        != {
            "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "v24783_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_publication": False,
            "question_entity_field_value_url_page_prediction_or_answer_emitted": False,
        }
        or copied.get("claim_scope")
        != {
            "benchmark_external_mechanism_localization_only": True,
            "projection_funnel_effect_measured": False,
            "deepwidebench_dev64_or_exact220_score": False,
            "entropy_or_credit_validated": False,
            "leaderboard_or_sota": False,
        }
        or copied.get("authorization")
        != {
            "protocol_published": True,
            "append_only_trusted_child_integration_build": True,
            "runner_or_control_plane_build": False,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_or_evaluator_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.84 protocol drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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
    publish_new(ROOT / OUTPUT, protocol)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "protocol_id": PROTOCOL_ID,
                "task_count": protocol["task_contract"]["task_count"],
                "trusted_child_integration_build": protocol["authorization"][
                    "append_only_trusted_child_integration_build"
                ],
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
