#!/usr/bin/env python3
"""Content-free identifiability diagnosis for the V2.52.86 checkpoint seam."""

from __future__ import annotations

import ast
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

from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25287_legacy_outcome_checkpoint_build as build_audit  # noqa: E402
from scripts import diagnose_v25270_v25267_production_only_reliability as production_diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25288_legacy_checkpoint_quality_identifiability_diagnosis"
OUTPUT = Path(
    f"results/v25288_legacy_checkpoint_identifiability_diagnosis_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v25288_legacy_checkpoint_identifiability.py")
TEST = Path("tests/test_diagnose_v25288_legacy_checkpoint_identifiability.py")
CHECKPOINT_AUDIT = build_audit.OUTPUT
PRODUCTION_DIAGNOSIS = production_diagnosis.OUTPUT
LEGACY_FORWARD_AUDIT = Path(
    "results/v24857_pacing_aware_exact220_forward_audit_v1_20260808.json"
)
LEGACY_RUN_SUMMARY = Path(
    "outputs/v24857_pacing_aware_exact220_v1_20260808/run_summary.json"
)
CHECKPOINT_RUNTIME = Path(
    "src/deepwide_agent/v25286_legacy_outcome_checkpoint.py"
)
LEGACY_INTEGRATION = Path(
    "src/deepwide_agent/v24630_exact220_task_integration.py"
)
LEGACY_CHILD = Path("scripts/run_v24635_exact220_task.py")
PACING_CHILD = Path("scripts/run_v24857_pacing_aware_exact220_task.py")
FIXED_HASHES = {
    CHECKPOINT_AUDIT: (
        "01e902d3bb3548a27a9e5c5ca69137a506b3ed5421cfc5845ede3a80fca93863"
    ),
    PRODUCTION_DIAGNOSIS: (
        "b298439d5f4987771a2e660913647be29eddafcc38e491cc89cb7840e5ab7a12"
    ),
    LEGACY_FORWARD_AUDIT: (
        "dacd35b31f78a8e04ee39b23efbd275a0c44a367e62e8ca90e7caf21bc092fe0"
    ),
    LEGACY_RUN_SUMMARY: (
        "f34fc04629b4424bf87aa8284a2188f7d9edcada8768da34732863b3db39de38"
    ),
    CHECKPOINT_RUNTIME: (
        "60191055ea4ac0baa7579ecb80488149556b01519c0f781c18713e93daf43e99"
    ),
    LEGACY_INTEGRATION: (
        "12aee7eb8f147514ee9a4dbfc8c536c52df6647ab1bf156289b233d5a813eb22"
    ),
    LEGACY_CHILD: (
        "5cba2e0cf8c2f6345880a37098da5f73a4bfb3965ff4813fb704b63673a2e97f"
    ),
    PACING_CHILD: (
        "a2f21b87fda0c975db5e6eec1605814267b1ef5f00b0b964363277fcd665992b"
    ),
}


def _read_object(relative: Path) -> dict[str, Any]:
    path = base._ordinary(relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.88 expected a repository JSON object")
    return value


def _fixed_inputs() -> dict[str, str]:
    observed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    expected = {str(path): digest for path, digest in FIXED_HASHES.items()}
    if observed != expected:
        raise RuntimeError("V2.52.88 fixed input hash drifted")
    return observed


def _parent_barrier() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    checkpoint = build_audit.validate_audit(_read_object(CHECKPOINT_AUDIT))
    production = production_diagnosis.validate_diagnosis(
        _read_object(PRODUCTION_DIAGNOSIS)
    )
    forward = _read_object(LEGACY_FORWARD_AUDIT)
    summary = _read_object(LEGACY_RUN_SUMMARY)
    if (
        checkpoint["audit_valid"] is not True
        or checkpoint["findings"] != []
        or checkpoint["authorization"][
            "fresh_disjoint_legacy_checkpoint_quality_population_and_protocol_design"
        ]
        is not True
        or checkpoint["authorization"]["external_activation_or_launch"] is not False
        or production["aggregate"]["outcome_counts"]
        != {
            "outer_failure": 11,
            "completed_fallback": 7,
            "completed_model_generated": 202,
        }
        or production["aggregate"]["stage_failure_stage_type_counts"]
        != {"sparse_production:ValueError": 11}
        or production["authorization"]["external_forward_or_new_deepwidebench_rollout"]
        is not False
        or forward.get("role") != "v24800_exact220_forward_audit"
        or forward.get("protocol_id")
        != "v24857_same_pass_pacing_aware_fixed_full_budget_exact220_v1"
        or forward.get("audit_valid") is not True
        or forward.get("findings") != []
        or forward.get("selected") != 220
        or forward.get("terminal_predictions") != 220
        or forward.get("model_generated_tables") != 220
        or forward.get("fallback_tables") != 0
        or summary.get("selected") != 220
        or summary.get("completed") != 220
        or summary.get("failed") != 0
        or summary.get("model_generated_tables") != 220
        or summary.get("fallback_tables") != 0
        or summary.get("parent_exit_taxonomy") != {"success": 220}
        or summary.get("official_evaluator_called") is not False
        or summary.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
    ):
        raise RuntimeError("V2.52.88 parent authority drifted")
    return checkpoint, production, forward, summary


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise RuntimeError(f"V2.52.88 expected one function: {name}")
    return matches[0]


def _calls(function: ast.FunctionDef) -> list[str]:
    output: list[str] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            output.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            parts = [node.func.attr]
            current = node.func.value
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            output.append(".".join(reversed(parts)))
    return output


def _source_reachability() -> dict[str, Any]:
    checkpoint_source = base._ordinary(CHECKPOINT_RUNTIME).read_text(encoding="utf-8")
    integration_source = base._ordinary(LEGACY_INTEGRATION).read_text(encoding="utf-8")
    child_source = base._ordinary(LEGACY_CHILD).read_text(encoding="utf-8")
    pacing_source = base._ordinary(PACING_CHILD).read_text(encoding="utf-8")
    checkpoint_tree = ast.parse(checkpoint_source, filename=str(CHECKPOINT_RUNTIME))
    integration_tree = ast.parse(integration_source, filename=str(LEGACY_INTEGRATION))
    child_tree = ast.parse(child_source, filename=str(LEGACY_CHILD))
    pacing_tree = ast.parse(pacing_source, filename=str(PACING_CHILD))
    run_checkpoint = _function(checkpoint_tree, "run_from_validated_outcome")
    build_checkpoint = _function(checkpoint_tree, "build_checkpoint")
    map_outcome = _function(checkpoint_tree, "_outcome_mapping")
    build_envelope = _function(integration_tree, "build_envelope")
    child_main = _function(child_tree, "main")
    pacing_run = _function(pacing_tree, "run_task")
    checkpoint_calls = _calls(run_checkpoint)
    checkpoint_build_calls = _calls(build_checkpoint)
    mapping_calls = _calls(map_outcome)
    envelope_calls = _calls(build_envelope)
    child_calls = _calls(child_main)
    pacing_calls = _calls(pacing_run)
    checkpoint_position = checkpoint_source.find("checkpoint = build_checkpoint(outcome)")
    envelope_position = checkpoint_source.find(
        "parent.build_envelope(outcome, arm=ARM)"
    )
    envelope_validate_position = checkpoint_source.find(
        "parent.validate_envelope(envelope)"
    )
    legacy_forward_position = child_source.find("outcome = run_v24630_task(")
    legacy_receipt_position = child_source.find(
        "_atomic_new(receipt_path, outcome.model_slot_receipt)"
    )
    legacy_envelope_position = child_source.find(
        "_atomic_new(result_path, build_envelope(outcome, arm=ARM))"
    )
    exact = bool(
        0 <= checkpoint_position < envelope_position < envelope_validate_position
        and 0 <= legacy_forward_position < legacy_receipt_position < legacy_envelope_position
        and checkpoint_source.count("parent.build_envelope(outcome, arm=ARM)") == 1
        and checkpoint_source.count("parent.validate_envelope(envelope)") == 1
        and "run_v24630_task" not in checkpoint_calls
        and "parent.validate_cross_artifacts" in mapping_calls
        and "_outcome_mapping" in checkpoint_build_calls
        and "validate_envelope" in envelope_calls
        and "run_v24630_task" in child_calls
        and "run_pacing_aware_task" in pacing_calls
        and "build_envelope" not in pacing_calls
    )
    if not exact:
        raise RuntimeError("V2.52.88 source reachability boundary drifted")
    return {
        "source_hashes": {
            str(path): FIXED_HASHES[path]
            for path in (
                CHECKPOINT_RUNTIME,
                LEGACY_INTEGRATION,
                LEGACY_CHILD,
                PACING_CHILD,
            )
        },
        "legacy_forward_completes_before_envelope_build": True,
        "legacy_effect_receipts_commit_after_forward_before_envelope_build": True,
        "checkpoint_revalidates_parent_cross_artifacts_before_recovery_surface": True,
        "checkpoint_is_built_before_legacy_envelope_build": True,
        "recoverable_surface_exactly": [
            "legacy_envelope_build",
            "legacy_envelope_validate",
        ],
        "recoverable_surface_contains_query_fetch_model_or_network_call": False,
        "recoverable_surface_contains_input_dependent_treatment_branch": False,
        "normal_path_returns_legacy_envelope_byte_identically": True,
        "pacing_child_changes_forward_binding_not_envelope_builder": True,
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    fixed = _fixed_inputs()
    checkpoint, production, _forward, summary = _parent_barrier()
    reachability = _source_reachability()
    observed = {
        "frozen_legacy_task_denominator": 220,
        "legacy_parent_exit_success": summary["parent_exit_taxonomy"]["success"],
        "legacy_model_generated": summary["model_generated_tables"],
        "legacy_fallback": summary["fallback_tables"],
        "legacy_outer_failure": summary["failed"],
        "observed_legacy_envelope_build_or_validate_failure": 0,
        "observed_v25286_natural_recovery": 0,
        "v25286_external_forward_performed": False,
    }
    nontransfer = {
        "production_chain_outer_failure_count": production["aggregate"][
            "outcome_counts"
        ]["outer_failure"],
        "production_chain_failure_stage_type_counts": production["aggregate"][
            "stage_failure_stage_type_counts"
        ],
        "production_chain_runtime_family": "v25265_sparse_production",
        "legacy_checkpoint_runtime_family": "v24630_thin_exact220",
        "failure_stage_equals_v25286_recoverable_stage": False,
        "production_chain_failure_rate_used_as_v25286_event_rate": False,
        "reason": "different_runtime_family_and_pre_legacy_envelope_stage",
    }
    checks = {
        "fixed_inputs_exact": fixed
        == {str(path): digest for path, digest in FIXED_HASHES.items()},
        "checkpoint_build_audit_valid": checkpoint["audit_valid"] is True,
        "legacy_full220_all_parent_exits_succeeded": observed[
            "legacy_parent_exit_success"
        ]
        == 220,
        "legacy_full220_zero_fallback_or_outer_failure": observed[
            "legacy_fallback"
        ]
        == 0
        and observed["legacy_outer_failure"] == 0,
        "v25286_recovery_surface_is_postforward_and_effect_free": reachability[
            "legacy_forward_completes_before_envelope_build"
        ]
        is True
        and reachability[
            "recoverable_surface_contains_query_fetch_model_or_network_call"
        ]
        is False,
        "v25286_has_no_declared_input_dependent_natural_treatment_branch": reachability[
            "recoverable_surface_contains_input_dependent_treatment_branch"
        ]
        is False,
        "v25265_failure_rate_is_not_transferred_to_v25286": nontransfer[
            "failure_stage_equals_v25286_recoverable_stage"
        ]
        is False
        and nontransfer["production_chain_failure_rate_used_as_v25286_event_rate"]
        is False,
        "quality_gate_requires_nonzero_natural_recovery": checkpoint[
            "future_protocol_requirements"
        ]["quality_go"]["natural_postcheckpoint_recovery_nonzero"]
        is True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    decision = {
        "checkpoint_reliability_safeguard_retained": True,
        "fresh_checkpoint_quality_population_or_forward": "no_go_without_launch",
        "reason": "natural_quality_treatment_not_identifiable_on_current_recovery_surface",
        "observed_natural_recovery_lower_bound": 0,
        "observed_natural_recovery_denominator": 220,
        "input_dependent_natural_recovery_trigger_established": False,
        "counterfactual_prediction_change_established": False,
        "quality_delta_can_be_attributed_to_checkpoint": False,
        "fault_injection_may_establish_reliability_not_quality": True,
        "next_candidate_must_change_normal_path_prediction_under_shared_prefix": True,
        "next_candidate_must_use_existing_query_fetch_model_cap": True,
        "next_candidate_requires_fresh_disjoint_external_causal_gate": True,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_inputs": fixed,
        "source_reachability": reachability,
        "observed_legacy_aggregate": observed,
        "nontransferable_failure_evidence": nontransfer,
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "decision": decision,
        "content_policy": {
            "repository_files_opened": [str(path) for path in FIXED_HASHES],
            "aggregate_json_and_source_text_only": True,
            "runtime_task_rows_opened": False,
            "task_identity_question_query_url_page_prediction_answer_opened": False,
            "mapping_gold_category_question_type_split_evaluator_metric_score_or_reward_opened": False,
            "historical_per_task_correctness_used_as_router_signal": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read_for_runtime_routing": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "normal_path_quality_candidate_design_and_build_only": not findings,
            "fresh_external_population_selection_or_protocol": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "candidate_quality_improvement_avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = seal.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("diagnosis_payload_sha256", None)
    reachability = copied.get("source_reachability") or {}
    observed = copied.get("observed_legacy_aggregate") or {}
    nontransfer = copied.get("nontransferable_failure_evidence") or {}
    checks = copied.get("checks") or {}
    decision = copied.get("decision") or {}
    policy = copied.get("content_policy") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "fixed_inputs",
            "source_reachability",
            "observed_legacy_aggregate",
            "nontransferable_failure_evidence",
            "checks",
            "findings",
            "diagnosis_valid",
            "decision",
            "content_policy",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read_for_runtime_routing",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or reachability
        != {
            "source_hashes": {
                str(path): FIXED_HASHES[path]
                for path in (
                    CHECKPOINT_RUNTIME,
                    LEGACY_INTEGRATION,
                    LEGACY_CHILD,
                    PACING_CHILD,
                )
            },
            "legacy_forward_completes_before_envelope_build": True,
            "legacy_effect_receipts_commit_after_forward_before_envelope_build": True,
            "checkpoint_revalidates_parent_cross_artifacts_before_recovery_surface": True,
            "checkpoint_is_built_before_legacy_envelope_build": True,
            "recoverable_surface_exactly": [
                "legacy_envelope_build",
                "legacy_envelope_validate",
            ],
            "recoverable_surface_contains_query_fetch_model_or_network_call": False,
            "recoverable_surface_contains_input_dependent_treatment_branch": False,
            "normal_path_returns_legacy_envelope_byte_identically": True,
            "pacing_child_changes_forward_binding_not_envelope_builder": True,
        }
        or observed
        != {
            "frozen_legacy_task_denominator": 220,
            "legacy_parent_exit_success": 220,
            "legacy_model_generated": 220,
            "legacy_fallback": 0,
            "legacy_outer_failure": 0,
            "observed_legacy_envelope_build_or_validate_failure": 0,
            "observed_v25286_natural_recovery": 0,
            "v25286_external_forward_performed": False,
        }
        or nontransfer
        != {
            "production_chain_outer_failure_count": 11,
            "production_chain_failure_stage_type_counts": {
                "sparse_production:ValueError": 11
            },
            "production_chain_runtime_family": "v25265_sparse_production",
            "legacy_checkpoint_runtime_family": "v24630_thin_exact220",
            "failure_stage_equals_v25286_recoverable_stage": False,
            "production_chain_failure_rate_used_as_v25286_event_rate": False,
            "reason": "different_runtime_family_and_pre_legacy_envelope_stage",
        }
        or checks
        != {
            "fixed_inputs_exact": True,
            "checkpoint_build_audit_valid": True,
            "legacy_full220_all_parent_exits_succeeded": True,
            "legacy_full220_zero_fallback_or_outer_failure": True,
            "v25286_recovery_surface_is_postforward_and_effect_free": True,
            "v25286_has_no_declared_input_dependent_natural_treatment_branch": True,
            "v25265_failure_rate_is_not_transferred_to_v25286": True,
            "quality_gate_requires_nonzero_natural_recovery": True,
            "no_external_effect_performed": True,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or decision
        != {
            "checkpoint_reliability_safeguard_retained": True,
            "fresh_checkpoint_quality_population_or_forward": "no_go_without_launch",
            "reason": "natural_quality_treatment_not_identifiable_on_current_recovery_surface",
            "observed_natural_recovery_lower_bound": 0,
            "observed_natural_recovery_denominator": 220,
            "input_dependent_natural_recovery_trigger_established": False,
            "counterfactual_prediction_change_established": False,
            "quality_delta_can_be_attributed_to_checkpoint": False,
            "fault_injection_may_establish_reliability_not_quality": True,
            "next_candidate_must_change_normal_path_prediction_under_shared_prefix": True,
            "next_candidate_must_use_existing_query_fetch_model_cap": True,
            "next_candidate_requires_fresh_disjoint_external_causal_gate": True,
        }
        or policy
        != {
            "repository_files_opened": [str(path) for path in FIXED_HASHES],
            "aggregate_json_and_source_text_only": True,
            "runtime_task_rows_opened": False,
            "task_identity_question_query_url_page_prediction_answer_opened": False,
            "mapping_gold_category_question_type_split_evaluator_metric_score_or_reward_opened": False,
            "historical_per_task_correctness_used_as_router_signal": False,
        }
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read_for_runtime_routing",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or copied.get("authorization")
        != {
            "normal_path_quality_candidate_design_and_build_only": True,
            "fresh_external_population_selection_or_protocol": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "candidate_quality_improvement_avg_at_4_leaderboard_or_sota": False,
        }
        or signature != seal.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.88 checkpoint identifiability diagnosis drifted")
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
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "checkpoint_quality_gate": value["decision"][
                    "fresh_checkpoint_quality_population_or_forward"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
