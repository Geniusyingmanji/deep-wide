#!/usr/bin/env python3
"""Freeze the append-only policy-value true-continuation Gate-2A consumer."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24161_strict_gate2a import DEFAULT_SETTINGS  # noqa: E402
from deepwide_agent.v24191_policy_value_gate2a import (  # noqa: E402
    DEFAULT_POLICY_SETTINGS,
    VALUE_ADVANTAGES,
)
from scripts.preregister_v24160_true_continuation_liveness_schema import (  # noqa: E402
    RUNNER_MARKER,
)
from scripts.preregister_v24190_tie_aware_gate2a import (  # noqa: E402
    CONSUMER_MARKER as PARENT_CONSUMER_MARKER,
    REPORT as PARENT_REPORT,
    STATE as PARENT_STATE,
)
from scripts.v24159_true_continuation_reachability import (  # noqa: E402
    object_sha256,
    process_report,
    process_snapshot,
    publish_new,
    read_object,
    sha256,
)


ROLE = "v24191_policy_value_gate2a_consumer_preregistration"
PROTOCOL_ID = "v24191_policy_value_true_continuation_gate2a_consumer_v1"
OUTPUT = Path(
    "results/v24191_policy_value_gate2a_consumer_preregistration_v1_20260730.json"
)
STATE = Path("outputs/v24191_policy_value_gate2a_consumer_state_v1_20260730.json")
REPORT = Path(
    "results/v24191_policy_value_true_continuation_gate2a_report_v1_20260730.json"
)
ACTIVATION = Path(
    "results/v24191_policy_value_gate2a_consumer_activation_audit_v1_20260730.json"
)
CONSUMER_MARKER = "scripts/watch_v24191_policy_value_gate2a.py"
PHASE_LIVENESS_MARKER = "scripts/watch_v24187_phase_liveness.py"
PHASE_LIVENESS_STATE = Path(
    "outputs/v24187_phase_liveness_watcher_state_v1_20260730.json"
)

FROZEN_PARENTS = {
    "results/v24190_tie_aware_gate2a_consumer_preregistration_v1_20260730.json": "e978988b6a7617bba702ced578cf1eb47fc0392a32fc7298ae136add922927ac",
    "results/v24190_tie_aware_gate2a_consumer_activation_audit_v1_20260730.json": "c3166f1d08c535945e58130d941d39b33fc9b48aeca1eeef00f4ed1c9e416449",
    "src/deepwide_agent/v24190_tie_aware_gate2a.py": "8295feda84a6689b82a62ae1db062701bb679cafa616b5be40cf4ed033afb268",
    "scripts/watch_v24190_tie_aware_gate2a.py": "6d1d797ece6950b3b742f5a496366fe84ff8b48e96236cc3981dcce8489325de",
    "src/deepwide_agent/v24123_release.py": "49838bbcd450e995e9bbfbf0f0de9414bf98ef876945bd6830e0a79b38f21ed7",
    "results/v2413_gate3a_controller_design_preregistration_v1_20260727.json": "c71303fb04208733b4786dc60d1f1db7fd86be3345cc75461fdb0b82af51a338",
    "results/v24187_phase_liveness_preregistration_v1_20260730.json": "873f42369f6f5ac7d1b619510257f8cc7c932140b734dd14d23c4a5c6e45d34c",
    "results/v24187_phase_liveness_activation_audit_v1_20260730.json": "b57bdc1fbcce3911111f9c571c77dd37f1d1ecbf1030b1658638c0062cbaa4b2",
    "scripts/watch_v24187_phase_liveness.py": "83789b1cc2eb1e6e87969894409b09039028e0e13b53ba8de90776171bf567d3",
}
CONTROL_FILES = (
    "src/deepwide_agent/v24191_policy_value_gate2a.py",
    "scripts/preregister_v24191_policy_value_gate2a.py",
    "scripts/watch_v24191_policy_value_gate2a.py",
    "scripts/audit_v24191_policy_value_gate2a_activation.py",
    "tests/test_v24191_policy_value_gate2a.py",
    "tests/test_v24191_policy_value_consumer.py",
    "tests/test_v24191_policy_value_activation.py",
)
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
DECISION_FIELDS = (
    "protocol_id",
    "parents",
    "scientific_defect",
    "policy_value_contract",
    "source_release_gate",
    "execution",
    "source_policy",
    "authorization",
    "control_surface",
)


def _ordinary(root: Path, relative: str | Path, expected: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.91 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
    ):
        raise RuntimeError(f"V2.41.91 expected an ordinary file: {relative}")
    if expected is not None and sha256(path) != expected:
        raise RuntimeError(f"V2.41.91 frozen parent drifted: {relative}")
    return path


def validate_frozen_parents(root: Path) -> dict[str, Any]:
    parents = {
        relative: {"sha256": sha256(_ordinary(root, relative, digest))}
        for relative, digest in FROZEN_PARENTS.items()
    }
    v90 = read_object(
        root
        / "results/v24190_tie_aware_gate2a_consumer_preregistration_v1_20260730.json"
    )
    activation = read_object(
        root
        / "results/v24190_tie_aware_gate2a_consumer_activation_audit_v1_20260730.json"
    )
    gate3a = read_object(
        root / "results/v2413_gate3a_controller_design_preregistration_v1_20260727.json"
    )
    if (
        v90.get("protocol_id")
        != "v24190_tie_aware_true_continuation_gate2a_consumer_v1"
        or v90.get("tie_aware_contract", {}).get("settings") != DEFAULT_SETTINGS
        or activation.get("activation_valid") is not True
        or gate3a.get("controller_policy_design", {}).get("ranking_rule")
        != (
            "maximize strictly-positive predicted_task_risk_reduction / "
            "predicted_system_tokens; tie-break by larger risk reduction, lower "
            "tokens, then preregistered context action order"
        )
        or gate3a.get("controller_policy_design", {}).get("stop_rule")
        != (
            "stop when every available action has non-positive predicted task-risk "
            "reduction; forced budget stop is recorded separately"
        )
        or gate3a.get("controller_policy_design", {}).get(
            "branch_specific_action_selection"
        )
        is not True
        or gate3a.get("controller_policy_design", {}).get(
            "maximum_one_action_per_context"
        )
        is not True
        or gate3a.get("controller_policy_design", {}).get(
            "maximum_executed_actions_per_task"
        )
        != 3
    ):
        raise RuntimeError("V2.41.91 frozen parent semantics drifted")
    return parents


def _safe_preterminal_boundary(root: Path, proc_root: Path) -> dict[str, Any]:
    parent = read_object(_ordinary(root, PARENT_STATE))
    phase = read_object(_ordinary(root, PHASE_LIVENESS_STATE))
    rows = process_snapshot(proc_root)
    runner = process_report(rows, RUNNER_MARKER)
    phase_liveness = process_report(rows, PHASE_LIVENESS_MARKER)
    old = process_report(rows, PARENT_CONSUMER_MARKER)
    replacement = process_report(rows, CONSUMER_MARKER)
    truth = parent.get("source_truth") or {}
    if (
        parent.get("role") != "v24190_tie_aware_gate2a_consumer_state"
        or parent.get("status") != "waiting_for_true_continuation_audit_terminal"
        or parent.get("source_status")
        != "waiting_for_p12_trial2_exact220_release"
        or parent.get("source_terminal") is not False
        or set(truth)
        != {
            "mapping_or_gold_read",
            "evaluator_or_score_read",
            "api_or_benchmark_forward_called",
            "shared_api_lease_acquired",
        }
        or any(value is not False for value in truth.values())
        or parent.get("terminal") is not False
        or parent.get("activation_ready") is not True
        or parent.get("manifest_prediction_or_outcome_opened") is not False
        or parent.get(
            "mapping_gold_category_question_type_evaluator_score_or_outcome_read_by_consumer"
        )
        is not False
        or parent.get(
            "network_model_search_fetch_or_evaluator_api_called_by_consumer"
        )
        is not False
        or parent.get("tie_aware_gate2a_evaluated") is not False
        or parent.get("tie_aware_gate2a_passed") is not False
        or parent.get("parent_strict_gate2a_evaluated") is not False
        or parent.get("controller_design_allowed") is not False
        or parent.get("controller_implementation_or_pilot_launch_allowed") is not False
        or parent.get("training_credit_allowed") is not False
        or parent.get("full220_controller_launch_allowed") is not False
        or parent.get("benchmark_or_sota_claim") is not False
        or phase.get("role") != "v24187_phase_liveness_audit"
        or phase.get("overall_status")
        not in {"healthy", "degraded_forward_healthy_manual_review_only"}
        or phase.get("critical_findings") != []
        or phase.get("current_phase", {}).get("phase") != "r1_full220"
        or phase.get("current_phase", {}).get("valid") is not True
        or runner["match_count"] != 1
        or phase_liveness["match_count"] != 1
        or old["match_count"] != 1
        or replacement["present"]
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (STATE, REPORT, ACTIVATION)
        )
        or (root / PARENT_REPORT).exists()
        or (root / PARENT_REPORT).is_symlink()
    ):
        raise RuntimeError("V2.41.91 preterminal boundary is not safe")
    return {
        "parent_status": parent["status"],
        "parent_source_status": parent["source_status"],
        "parent_source_truth_fields_all_false": True,
        "parent_activation_ready": True,
        "source_runner_exactly_one": True,
        "authoritative_phase_liveness_exactly_one": True,
        "authoritative_phase_state_safe": True,
        "v24190_parent_consumer_exactly_one": True,
        "v24191_consumer_absent_before_freeze": True,
        "parent_and_successor_reports_absent": True,
        "successor_state_and_activation_absent": True,
    }


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.91 may only freeze the canonical workspace")
    if any((root / path).exists() or (root / path).is_symlink() for path in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.91 unattested Python bootstrap path appeared")
    parents = validate_frozen_parents(root)
    boundary = (
        _safe_preterminal_boundary(root, proc_root)
        if require_pristine
        else {
            "parent_status": "waiting_for_true_continuation_audit_terminal",
            "parent_source_status": "waiting_for_p12_trial2_exact220_release",
            "parent_source_truth_fields_all_false": True,
            "parent_activation_ready": True,
            "source_runner_exactly_one": True,
            "authoritative_phase_liveness_exactly_one": True,
            "authoritative_phase_state_safe": True,
            "v24190_parent_consumer_exactly_one": True,
            "v24191_consumer_absent_before_freeze": True,
            "parent_and_successor_reports_absent": True,
            "successor_state_and_activation_absent": True,
        }
    )
    manifest = {relative: sha256(_ordinary(root, relative)) for relative in CONTROL_FILES}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind_before_parent_terminal": True,
        "parents": parents,
        "scientific_defect": {
            "v24190_top2_hit_is_not_executed_policy_value": True,
            "v24190_can_pass_while_argmax_policy_is_worse_than_random": True,
            "v24190_does_not_apply_stop_at_nonpositive_prediction": True,
            "v24190_does_not_replay_gain_per_predicted_cost_ranking": True,
            "v24123_prediction_seal_serializes_only_full_branch_cost": True,
            "no_entropy_cost_must_be_replayed_from_frozen_preoutcome_model": True,
            "v24190_frozen_bytes_modified": False,
            "source_true_continuation_forward_or_evaluator_changed": False,
        },
        "policy_value_contract": {
            "parent_settings": dict(DEFAULT_SETTINGS),
            "parent_settings_sha256": object_sha256(DEFAULT_SETTINGS),
            "settings": dict(DEFAULT_POLICY_SETTINGS),
            "settings_sha256": object_sha256(DEFAULT_POLICY_SETTINGS),
            "parent_v24190_pass_required": True,
            "deployment_ranking_rule": "strictly-positive predicted contribution divided by branch-specific predicted action tokens",
            "deployment_tie_break": [
                "larger predicted contribution",
                "lower predicted action tokens",
                "preregistered context action order",
            ],
            "stop_when_all_predictions_nonpositive": True,
            "stop_actual_value": 0.0,
            "one_action_per_checkpoint": True,
            "gate3a_maximum_actions_per_task_diagnostic": 3,
            "full_cost_source": "serialized full-model prediction seal",
            "no_entropy_cost_source": "live replay of frozen pre-outcome no-entropy model branch",
            "heuristic_cost_source": "same no-entropy cost branch; full entropy cost forbidden",
            "actual_selected_value_from_sealed_terminal_contribution": True,
            "single_checkpoint_decision_rule_replayed_exactly": True,
            "multi_context_closed_loop_policy_effect_requires_gate3a": True,
            "policy_value_advantage_family": list(VALUE_ADVANTAGES),
            "shared_cluster_bootstrap_minimum_lower_strictly_positive": True,
            "task_clusters_equal_weighted": True,
            "oracle_regret_top1_and_gain_per_cost_reported": True,
            "parent_v24190_result_diagnostic_only_without_v24191": True,
            "canonical_module_identity_checked_before_wait_and_evaluation": True,
        },
        "source_release_gate": {
            "parent_state_path": str(PARENT_STATE),
            "required_parent_terminal": True,
            "required_parent_evaluated": True,
            "parent_report_path": str(PARENT_REPORT),
            "authoritative_phase_state_path": str(PHASE_LIVENESS_STATE),
            "authoritative_phase_watcher_marker": PHASE_LIVENESS_MARKER,
            "activation_required_before_scientific_inputs_opened": True,
            "all_manifest_model_predictions_and_aggregates_live_replayed": True,
            "no_manifest_model_prediction_or_outcome_opened_before_parent_terminal": True,
            "preterminal_boundary": boundary,
        },
        "execution": {
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "proc_root": "/proc",
            "consumer_marker": CONSUMER_MARKER,
            "state_path": str(STATE),
            "report_path": str(REPORT),
            "activation_path": str(ACTIVATION),
            "canonical_module_names": [
                "deepwide_agent.v24123_release",
                "deepwide_agent.v24190_tie_aware_gate2a",
                "deepwide_agent.v24191_policy_value_gate2a",
            ],
        },
        "source_policy": {
            "preterminal_safe_parent_and_phase_state_envelopes_only": True,
            "post_terminal_sealed_manifest_model_predictions_and_aggregates_only": True,
            "direct_mapping_gold_category_question_type_read": False,
            "raw_question_prediction_evidence_url_answer_or_score_emitted": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_or_evaluator_api_called": False,
        },
        "authorization": {
            "read_only_waiter_and_post_terminal_offline_consumer": True,
            "source_or_parent_process_signal_restart_resume_rerun_skip": False,
            "active_r1_p12_schema76_schema77_avg4_or_quality_chain_mutation": False,
            "forward_code_prompt_model_search_budget_or_threshold_change": False,
            "controller_design_only_after_v24191_gate_pass": True,
            "controller_implementation_or_pilot_launch": False,
            "training_credit": False,
            "full220_controller_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": object_sha256(manifest),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
        },
        "claims": {
            "policy_value_gate2a_result_available": False,
            "entropy_action_value_identified": False,
            "controller_or_training_enabled": False,
            "benchmark_score_or_sota": False,
        },
    }
    value["decision_contract_sha256"] = object_sha256(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    if (
        raw.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or raw.is_symlink()
        or not raw.is_file()
    ):
        raise RuntimeError("V2.41.91 protocol path is noncanonical")
    value = read_object(raw)
    rebuilt = build_protocol(
        root,
        created_at_unix=int(value.get("created_at_unix", -1)),
        require_pristine=False,
    )
    if value != rebuilt:
        raise RuntimeError("V2.41.91 protocol differs from live rebuild")
    return {"path": raw, "sha256": sha256(raw), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--proc-root", default="/proc")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    if output.resolve(strict=False) != (root / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.41.91 output path drifted")
    value = build_protocol(root, proc_root=Path(args.proc_root))
    publish_new(output, value)
    print(
        json.dumps(
            {
                "output": str(output),
                "protocol_id": value["protocol_id"],
                "decision_contract_sha256": value["decision_contract_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()
