#!/usr/bin/env python3
"""Freeze V2.42.02 as an independent baseline arm, not a mainline component."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROLE = "v24202_webswarm_baseline_only_disposition"
OUTPUT = Path("results/v24202_webswarm_baseline_only_disposition_v1_20260731.json")
V24200_PROTOCOL = Path(
    "results/v24200_hierarchical_successor_preregistration_v1_20260731.json"
)
V24200_PROTOCOL_SHA256 = (
    "d04d64ae2d05dc3daa934cc92a292b8541dce565e948df10c292a815b6a92ae3"
)
V24202_AUDIT = Path(
    "results/v24202_label_blind_webswarm_adapter_audit_v1_20260731.json"
)
V24202_AUDIT_SHA256 = (
    "c046c9ca5a774356433c0c8a5c7312aca5e82fdfff539c0eecc033197d99d1a6"
)
CONTROL_FILES = (
    "scripts/dispose_v24202_webswarm_baseline_only.py",
    "tests/test_dispose_v24202_webswarm_baseline_only.py",
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
SECRET_LITERAL = re.compile(
    r"(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ordinary(root: Path, relative: Path, expected: str | None = None) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.02 disposition path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.02 disposition expected an ordinary file: {relative}")
    if expected is not None and sha256(path) != expected:
        raise RuntimeError(f"V2.42.02 disposition parent drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.02 disposition expected one JSON object")
    return value


def build_disposition(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.02 disposition may only use the canonical workspace")
    v24200_path = ordinary(root, V24200_PROTOCOL, V24200_PROTOCOL_SHA256)
    v24202_path = ordinary(root, V24202_AUDIT, V24202_AUDIT_SHA256)
    v24200 = read_object(v24200_path)
    v24202 = read_object(v24202_path)
    if (
        v24200.get("role") != "v24200_hierarchical_successor_preregistration"
        or v24200.get("protocol_id")
        != "v24200_hierarchical_baseline_integrated_package_gate_v1"
        or v24200.get("component_contract", {}).get(
            "component_go_means_build_and_package_gate_eligibility_only"
        )
        is not True
        or v24200.get("component_contract", {}).get(
            "nonempty_component_set_requires_new_package_gate"
        )
        is not True
        or v24202.get("role") != "v24202_label_blind_webswarm_adapter_audit"
        or v24202.get("audit_valid") is not True
        or v24202.get("build_only") is not True
        or v24202.get("claims", {}).get(
            "webswarm_adapter_quality_effect_observed"
        )
        is not False
        or v24202.get("scientific_scope", {}).get(
            "sibling_trajectory_experience_injected"
        )
        is not False
    ):
        raise RuntimeError("V2.42.02 disposition parent contract is invalid")
    manifest = {
        relative: sha256(ordinary(root, Path(relative)))
        for relative in CONTROL_FILES
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "parents": {
            str(V24200_PROTOCOL): {
                "sha256": V24200_PROTOCOL_SHA256,
                "role": v24200["role"],
            },
            str(V24202_AUDIT): {
                "sha256": V24202_AUDIT_SHA256,
                "role": v24202["role"],
            },
        },
        "disposition": {
            "decision": "baseline_only_not_mainline_component",
            "v24200_component_registry_or_quality_source_modified": False,
            "v24200_outcome_before_selection_modified": False,
            "v24202_has_independent_quality_go": False,
            "v24202_eligible_for_v24200_component_set": False,
            "v24202_eligible_for_integrated_candidate_package": False,
            "v24202_eligible_for_candidate_freeze_or_full220": False,
            "future_use": "independent_label_blind_no_entropy_system_baseline_arm",
            "future_arm_must_derive_from_selected_baseline_bytes": True,
            "future_dev64_is_engineering_and_same_budget_gate_only": True,
            "future_reportable_score_requires_fresh_exact220": True,
            "future_official_evaluator_required": True,
            "future_failure_as_zero_required": True,
            "future_new_output_roots_required": True,
            "future_resume_or_selective_retry_forbidden": True,
            "future_same_model_search_backend_user_prompt_output_contract_budget_and_attempts_required": True,
            "future_method_specific_system_instructions_frozen_and_disclosed": True,
            "future_all_system_instruction_input_tokens_counted": True,
            "future_capacity_freeze_inherited_exactly": True,
            "future_single_owner_executor_preregistration_required": True,
        },
        "implementation_boundary": {
            "available": [
                "strict_label_blind_payload_schema",
                "atom_deep_wide_entity_collect_modes",
                "visible_state_bound_planner_context",
                "root_scope_and_active_provenance_contract",
                "observed_web_topology_tactic",
                "exact_contract_duplicate_removal",
                "recursion_batch_and_child_caps",
                "all_to_deep_all_to_wide_no_recursive_ablations",
            ],
            "not_available": [
                "production_runtime_integration",
                "model_search_or_fetch_execution",
                "sibling_trajectory_experience_reuse",
                "no_web_probing_ablation",
                "unseen_mass_or_open_world_completeness_estimator",
                "entropy_or_information_gain_controller",
                "quality_cost_or_benchmark_effect",
            ],
            "unimplemented_features_must_not_be_reported_as_ablations": True,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
        },
        "source_policy": {
            "frozen_parent_protocol_and_build_only_audit_only": True,
            "runtime_task_state_question_answer_evidence_url_or_prediction_opened": False,
            "benchmark_subset_category_question_type_label_or_split_read": False,
            "mapping_gold_evaluator_score_reward_or_result_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "active_forward_code_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "candidate_build_materialization_or_package_gate": False,
            "benchmark_forward_dev64_full220_or_evaluator_launch": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "webswarm_adapter_quality_or_cost_effect_observed": False,
            "entropy_or_credit_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "disposition_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if OPAQUE_ID.search(encoded) or SECRET_LITERAL.search(encoded):
        raise RuntimeError("V2.42.02 disposition would expose forbidden content")
    value["disposition_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    if target != (ROOT / OUTPUT).resolve(strict=False) or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.02 disposition output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    target = target if target.is_absolute() else ROOT / target
    value = build_disposition()
    publish_new(target, value)
    print(
        json.dumps(
            {
                "path": str(target),
                "sha256": sha256(target),
                "decision": value["disposition"]["decision"],
            }
        )
    )


if __name__ == "__main__":
    main()
