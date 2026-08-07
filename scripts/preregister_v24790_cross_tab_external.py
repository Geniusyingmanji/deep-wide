#!/usr/bin/env python3
"""Publish the inert V2.47.90 selected-Unknown cross-tab protocol.

One future trusted child will run the frozen V2.47.78 base exactly once.  Only
after its baseline and candidate predictions are materialized and validated,
the child deterministically selects the first baseline Unknown value cell in
canonical row-major order.  It rebuilds a one-target semantic catalog from the
same already-fetched pages, constructs a one-cell baseline/candidate slice,
and invokes the pure V2.47.86 cross-tab observer.  The base predictions are
never changed and the observation adds no model/search/fetch/evaluator effect.

Publication consumes tracked public surfaces only.  It never opens the
V2.47.89 evaluator-only population or V2.47.84 outputs and authorizes only a
separate append-only trusted-child integration build, not a runner or launch.
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
from deepwide_agent import v24786_projection_support_cross_tab_observer as observer  # noqa: E402
from deepwide_agent import v24789_cross_tab_population_contract as visible  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24789_cross_tab_population_freeze as freeze  # noqa: E402
from scripts import design_v24789_cross_tab_population as population_design  # noqa: E402


DATE = "20260807"
PROTOCOL_ID = "v24790_selected_unknown_cross_tab_external_v1"
OUTPUT = Path(f"results/v24790_cross_tab_external_preregistration_v1_{DATE}.json")
POPULATION = population_design.OUTPUT
POPULATION_FREEZE_AUDIT = freeze.AUDIT
VISIBLE_CONTRACT = population_design.CONTRACT
BASE_RUNTIME = Path("src/deepwide_agent/v24778_staged_fetch_fallback_runtime.py")
BASE_RUNTIME_TEST = Path("tests/test_v24778_staged_fetch_fallback_runtime.py")
OBSERVER = Path("src/deepwide_agent/v24786_projection_support_cross_tab_observer.py")
OBSERVER_TEST = Path("tests/test_v24786_projection_support_cross_tab_observer.py")
SOURCE = Path("scripts/preregister_v24790_cross_tab_external.py")
TEST = Path("tests/test_preregister_v24790_cross_tab_external.py")
DEPENDENCIES = (
    POPULATION,
    POPULATION_FREEZE_AUDIT,
    VISIBLE_CONTRACT,
    BASE_RUNTIME,
    BASE_RUNTIME_TEST,
    OBSERVER,
    OBSERVER_TEST,
    SOURCE,
    TEST,
)
FUTURE_SURFACES = (
    OUTPUT,
    Path(f"results/v24790_cross_tab_integration_build_audit_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_package_audit_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_preactivation_audit_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_activation_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_execution_start_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_forward_result_v1_{DATE}.json"),
    Path(f"results/v24790_cross_tab_forward_audit_v1_{DATE}.json"),
    Path(f"outputs/v24790_cross_tab_external_v1_{DATE}"),
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
TOTAL_FETCH_CAP_PER_TASK = 10
STATUSES = (
    "validated",
    "no_baseline_unknown_target",
    "private_catalog_absent",
    "base_runtime_failure",
    "selected_catalog_or_observer_failure",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.90 expected public JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.90 expected public JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _tracked_ordinary(relative: Path) -> Path:
    path = ROOT / relative
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0
    if (
        relative.is_absolute() or ".." in relative.parts
        or relative.parts[:1] in {("evaluation",), ("outputs",)}
        or path.is_symlink() or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve()) or not tracked
    ):
        raise RuntimeError(f"V2.47.90 expected tracked public dependency: {relative}")
    return path


def dependency_manifest() -> dict[str, str]:
    return {str(path): sha256(_tracked_ordinary(path)) for path in DEPENDENCIES}


def _parents() -> tuple[dict[str, Any], dict[str, Any]]:
    population = _read(ROOT / POPULATION)
    audit = _read(ROOT / POPULATION_FREEZE_AUDIT)
    population_design.validate_public(population)
    freeze.validate_audit(audit)
    if (
        population.get("role") != "v24789_cross_tab_population_design"
        or population.get("freshness", {}).get("historical_visible_entity_count") != 4_816
        or population.get("freshness", {}).get("selected_entity_count") != 32
        or population.get("freshness", {}).get("literal_overlap_with_history") != 0
        or population.get("freshness", {}).get("canonical_overlap_with_history") != 0
        or population.get("future_target_selection_contract", {}).get(
            "maximum_selected_baseline_unknown_target_per_task"
        ) != 1
        or population.get("authorization", {}).get(
            "append_only_inert_successor_protocol_design"
        ) is not True
        or population.get("authorization", {}).get("activation_or_external_launch") is not False
        or audit.get("role") != "v24789_cross_tab_population_freeze_audit"
        or audit.get("audit_valid") is not True or audit.get("findings") != []
        or audit.get("authorization", {}).get("inert_v24790_protocol_publication") is not True
        or audit.get("authorization", {}).get("trusted_child_integration_or_runner_build") is not False
        or audit.get("source_policy", {}).get(
            "v24789_private_population_bytes_opened_parsed_imported_copied_or_hashed"
        ) is not False
        or not _sealed(population, "design_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.90 public parent surface drifted")
    return population, audit


def _future_pristine() -> bool:
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in FUTURE_SURFACES)


def build_protocol(*, now: int | None = None, require_clean: bool = True, require_pristine: bool = True) -> dict[str, Any]:
    if require_clean and (_git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")):
        raise RuntimeError("V2.47.90 protocol requires clean pushed HEAD")
    if require_pristine and not _future_pristine():
        raise FileExistsError("V2.47.90 protocol or future surface exists")
    population, _audit = _parents()
    tasks = visible.task_vector()
    if len(tasks) != TASK_COUNT or any(set(task) != {"opaque_id", "question"} for task in tasks) or len({task["opaque_id"] for task in tasks}) != TASK_COUNT:
        raise RuntimeError("V2.47.90 visible task vector drifted")
    manifest = dependency_manifest()
    value = {
        "artifact_version": 1,
        "role": "v24790_cross_tab_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parents": {
            "population_design_sha256": sha256(ROOT / POPULATION),
            "population_freeze_audit_sha256": sha256(ROOT / POPULATION_FREEZE_AUDIT),
            "visible_contract_sha256": sha256(ROOT / VISIBLE_CONTRACT),
            "private_population_opened_or_hashed": False,
            "v24784_output_opened_or_hashed": False,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "population": {
            "historical_entity_count": 4_816,
            "fresh_entity_count": 32,
            "task_count": TASK_COUNT,
            "rows_per_task": ROWS_PER_TASK,
            "country_count_vector_sorted": population["eligibility_and_selection"]["selected_country_count_vector_sorted"],
            "mechanism_localization_population_not_quality_sample": True,
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "task_count": TASK_COUNT,
            "row_count": TASK_COUNT * ROWS_PER_TASK,
            "columns": ["Organization", "Founded", "Country"],
            "private_truth_provenance_quality_category_split_or_score_field_present": False,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        },
        "base_runtime_effect_envelope": {
            "implementation": base_runtime.POLICY_ID,
            "task_executors": TASK_EXECUTORS,
            "global_model_slot_cap": GLOBAL_MODEL_SLOT_CAP,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "model_calls_per_task": MODEL_CALLS_PER_TASK,
            "logical_queries_per_task": LOGICAL_QUERIES_PER_TASK,
            "maximum_physical_fetches_per_task": TOTAL_FETCH_CAP_PER_TASK,
            "all_tasks_submitted_once": True,
            "experiment_level_resume_retry_skip_or_selective_rerun": False,
        },
        "future_trusted_child_integration": {
            "implementation_status": "not_built",
            "status_vocabulary": list(STATUSES),
            "ordered_steps": [
                "run_and_validate_v24778_base_once",
                "materialize_base_predictions_without_private_truth",
                "select_first_baseline_unknown_value_cell_in_canonical_row_major_order",
                "if_no_unknown_emit_explicit_no_target_status",
                "rebuild_one_target_catalog_from_same_already_fetched_pages",
                "construct_one_row_two_column_baseline_candidate_slice",
                "build_and_validate_v24786_cross_tab_once",
                "emit_unchanged_full_base_predictions_plus_counts_only_receipt",
            ],
            "maximum_selected_target_per_task": 1,
            "target_selection_uses_private_truth_quality_or_evaluator": False,
            "target_selection_changes_acquisition_or_base_predictions": False,
            "same_already_fetched_pages_reused": True,
            "additional_model_search_fetch_or_evaluator_effect": 0,
            "observer_receipt_contains_private_identity_field_value_host_page_prediction_or_hash": False,
            "positive_entropy_or_task_credit_assigned": False,
        },
        "cross_tab_schema": {
            "policy_id": observer.POLICY_ID,
            "role": observer.ROLE,
            "fixed_catalog_dispositions": list(observer.CATALOG_DISPOSITIONS),
            "fixed_catalog_quarantine_dispositions": list(observer.CATALOG_QUARANTINE_DISPOSITIONS),
            "fixed_proposal_dispositions": list(observer.PROPOSAL_DISPOSITIONS),
            "fixed_group_change_dispositions": list(observer.GROUP_CHANGE_DISPOSITIONS),
            "target_count_required_per_valid_receipt": 1,
            "unknown_target_count_required_per_valid_receipt": 1,
            "cross_task_or_cross_group_margins_may_substitute_for_joint": False,
        },
        "forward_health_gate": {
            "fixed_task_denominator": TASK_COUNT,
            "terminal_result_or_failure_as_zero_required_per_task": True,
            "maximum_total_model_calls": TASK_COUNT * MODEL_CALLS_PER_TASK,
            "maximum_total_physical_fetch_count": TASK_COUNT * TOTAL_FETCH_CAP_PER_TASK,
            "experiment_wall_within_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "all_predictions_frozen_before_private_truth_or_quality": True,
            "no_retry_resume_skip_or_selective_rerun": True,
            "protected_watchers": [{"pid": pid, "start_ticks": ticks, "marker": marker} for pid, ticks, marker in PROTECTED_WATCHERS],
        },
        "mechanism_gate_before_private_truth": {
            "validated_selected_target_receipt_count_required": TASK_COUNT,
            "no_baseline_unknown_target_count_required": 0,
            "private_catalog_absent_count_required": 0,
            "base_runtime_failure_count_required": 0,
            "selected_catalog_or_observer_failure_count_required": 0,
            "minimum_unknown_projection_group_task_count": 1,
            "minimum_unknown_two_or_more_source_projection_group_task_count": 1,
            "minimum_projection_backed_support_group_task_count": 1,
            "minimum_unconflicted_unknown_proposal_group_task_count": 1,
            "minimum_changed_target_task_count": 1,
            "minimum_strict_joint_safe_change_task_count": 1,
            "strict_joint_requires_same_target_value_group": True,
            "cross_task_aggregate_cooccurrence_may_substitute_for_joint": False,
            "zero_trigger_stops_without_private_truth_quality_or_evaluator": True,
            "strict_go_authorizes_only_task_cluster_disjoint_paired_dev64_design": True,
        },
        "diagnostic_scope_if_gate_fails": {
            "fixed_cross_tab_counts_may_localize_closure_stage": True,
            "same_population_retry_resume_or_tuning": False,
            "mechanism_no_go_is_benchmark_quality_result": False,
        },
        "entropy_credit_scope": {
            "credit_assignment_experiment": False,
            "projection_or_source_count_is_positive_credit": False,
            "entropy_drop_or_prediction_change_is_positive_credit": False,
            "outer_quality_or_intervention_required_for_future_credit": True,
        },
        "source_policy": {
            "v24784_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "v24789_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_publication": False,
        },
        "claim_scope": {
            "benchmark_external_mechanism_localization_only": True,
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
    integration = copied.get("future_trusted_child_integration", {})
    schema = copied.get("cross_tab_schema", {})
    gate = copied.get("mechanism_gate_before_private_truth", {})
    if (
        copied.get("role") != "v24790_cross_tab_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(manifest, Mapping) or dict(manifest) != dependency_manifest()
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("population", {}).get("historical_entity_count") != 4_816
        or copied.get("population", {}).get("fresh_entity_count") != 32
        or copied.get("task_contract", {}).get("runtime_input_keys") != ["opaque_id", "question"]
        or copied.get("task_contract", {}).get("task_count") != TASK_COUNT
        or copied.get("base_runtime_effect_envelope", {}).get("implementation") != base_runtime.POLICY_ID
        or copied.get("base_runtime_effect_envelope", {}).get("task_executors") != TASK_EXECUTORS
        or copied.get("base_runtime_effect_envelope", {}).get("global_model_slot_cap") != GLOBAL_MODEL_SLOT_CAP
        or integration.get("implementation_status") != "not_built"
        or integration.get("status_vocabulary") != list(STATUSES)
        or integration.get("maximum_selected_target_per_task") != 1
        or integration.get("target_selection_uses_private_truth_quality_or_evaluator") is not False
        or integration.get("target_selection_changes_acquisition_or_base_predictions") is not False
        or integration.get("same_already_fetched_pages_reused") is not True
        or integration.get("additional_model_search_fetch_or_evaluator_effect") != 0
        or integration.get("positive_entropy_or_task_credit_assigned") is not False
        or schema.get("fixed_catalog_dispositions") != list(observer.CATALOG_DISPOSITIONS)
        or schema.get("fixed_catalog_quarantine_dispositions") != list(observer.CATALOG_QUARANTINE_DISPOSITIONS)
        or schema.get("fixed_proposal_dispositions") != list(observer.PROPOSAL_DISPOSITIONS)
        or schema.get("fixed_group_change_dispositions") != list(observer.GROUP_CHANGE_DISPOSITIONS)
        or schema.get("target_count_required_per_valid_receipt") != 1
        or schema.get("unknown_target_count_required_per_valid_receipt") != 1
        or schema.get("cross_task_or_cross_group_margins_may_substitute_for_joint") is not False
        or gate.get("validated_selected_target_receipt_count_required") != TASK_COUNT
        or gate.get("no_baseline_unknown_target_count_required") != 0
        or gate.get("minimum_unknown_two_or_more_source_projection_group_task_count") != 1
        or gate.get("minimum_projection_backed_support_group_task_count") != 1
        or gate.get("minimum_unconflicted_unknown_proposal_group_task_count") != 1
        or gate.get("minimum_changed_target_task_count") != 1
        or gate.get("minimum_strict_joint_safe_change_task_count") != 1
        or gate.get("strict_joint_requires_same_target_value_group") is not True
        or gate.get("cross_task_aggregate_cooccurrence_may_substitute_for_joint") is not False
        or copied.get("entropy_credit_scope", {}).get("credit_assignment_experiment") is not False
        or copied.get("source_policy") != {
            "v24784_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
            "v24789_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_publication": False,
        }
        or copied.get("claim_scope") != {
            "benchmark_external_mechanism_localization_only": True,
            "deepwidebench_dev64_or_exact220_score": False,
            "entropy_or_credit_validated": False,
            "leaderboard_or_sota": False,
        }
        or copied.get("authorization") != {
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
        raise RuntimeError("V2.47.90 protocol drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    protocol = build_protocol()
    publish_new(ROOT / OUTPUT, protocol)
    print(json.dumps({"output": str(OUTPUT), "protocol_id": PROTOCOL_ID, "task_count": TASK_COUNT, "integration_build": True, "runner_build": False, "external_launch": False}, sort_keys=True))
