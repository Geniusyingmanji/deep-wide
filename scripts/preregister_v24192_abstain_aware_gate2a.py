#!/usr/bin/env python3
"""Freeze the append-only abstain-aware true-continuation Gate-2A consumer."""

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
from deepwide_agent.v24192_abstain_aware_gate2a import (  # noqa: E402
    DEFAULT_ABSTAIN_SETTINGS,
)
from scripts.preregister_v24160_true_continuation_liveness_schema import (  # noqa: E402
    RUNNER_MARKER,
)
from scripts.preregister_v24190_tie_aware_gate2a import (  # noqa: E402
    CONSUMER_MARKER as GRANDPARENT_CONSUMER_MARKER,
)
from scripts.preregister_v24191_policy_value_gate2a import (  # noqa: E402
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


ROLE = "v24192_abstain_aware_gate2a_consumer_preregistration"
PROTOCOL_ID = "v24192_abstain_aware_true_continuation_gate2a_consumer_v1"
OUTPUT = Path(
    "results/v24192_abstain_aware_gate2a_consumer_preregistration_v1_20260730.json"
)
STATE = Path("outputs/v24192_abstain_aware_gate2a_consumer_state_v1_20260730.json")
REPORT = Path(
    "results/v24192_abstain_aware_true_continuation_gate2a_report_v1_20260730.json"
)
ACTIVATION = Path(
    "results/v24192_abstain_aware_gate2a_consumer_activation_audit_v1_20260730.json"
)
CONSUMER_MARKER = "scripts/watch_v24192_abstain_aware_gate2a.py"
PHASE_LIVENESS_MARKER = "scripts/watch_v24187_phase_liveness.py"
PHASE_LIVENESS_STATE = Path(
    "outputs/v24187_phase_liveness_watcher_state_v1_20260730.json"
)

FROZEN_PARENTS = {
    "results/v24191_policy_value_gate2a_consumer_preregistration_v1_20260730.json": "ad775fcb6b1de5377651e828c954ab1835c210b85aa81d63447cd4ed26fe1c72",
    "results/v24191_policy_value_gate2a_consumer_activation_audit_v1_20260730.json": "08c5335e48fbdc0bd9e1c97afbea6efccc3bf2ca98100383281d5f4ffafbb852",
    "src/deepwide_agent/v24191_policy_value_gate2a.py": "fc0bf3b3c1ff9f266bd5c4edaba970ca81cba7e78c4ee6629a8363729d28a2e0",
    "scripts/watch_v24191_policy_value_gate2a.py": "261032fa7a8882c7b42faaf8d865281470fafcabb3b0f20275afc35e7d4a3448",
    "src/deepwide_agent/v24123_release.py": "49838bbcd450e995e9bbfbf0f0de9414bf98ef876945bd6830e0a79b38f21ed7",
    "results/v2413_gate3a_controller_design_preregistration_v1_20260727.json": "c71303fb04208733b4786dc60d1f1db7fd86be3345cc75461fdb0b82af51a338",
    "results/v24187_phase_liveness_preregistration_v1_20260730.json": "873f42369f6f5ac7d1b619510257f8cc7c932140b734dd14d23c4a5c6e45d34c",
    "results/v24187_phase_liveness_activation_audit_v1_20260730.json": "b57bdc1fbcce3911111f9c571c77dd37f1d1ecbf1030b1658638c0062cbaa4b2",
    "scripts/watch_v24187_phase_liveness.py": "83789b1cc2eb1e6e87969894409b09039028e0e13b53ba8de90776171bf567d3",
}
CONTROL_FILES = (
    "src/deepwide_agent/v24192_abstain_aware_gate2a.py",
    "scripts/preregister_v24192_abstain_aware_gate2a.py",
    "scripts/watch_v24192_abstain_aware_gate2a.py",
    "scripts/audit_v24192_abstain_aware_gate2a_activation.py",
    "tests/test_v24192_abstain_aware_gate2a.py",
    "tests/test_v24192_abstain_aware_consumer.py",
    "tests/test_v24192_abstain_aware_activation.py",
)
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
DECISION_FIELDS = (
    "protocol_id",
    "parents",
    "scientific_defect",
    "abstain_aware_contract",
    "source_release_gate",
    "execution",
    "source_policy",
    "authorization",
    "control_surface",
)


def _ordinary(root: Path, relative: str | Path, expected: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.92 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
    ):
        raise RuntimeError(f"V2.41.92 expected an ordinary file: {relative}")
    if expected is not None and sha256(path) != expected:
        raise RuntimeError(f"V2.41.92 frozen parent drifted: {relative}")
    return path


def validate_frozen_parents(root: Path) -> dict[str, Any]:
    parents = {
        relative: {"sha256": sha256(_ordinary(root, relative, digest))}
        for relative, digest in FROZEN_PARENTS.items()
    }
    v91 = read_object(
        root
        / "results/v24191_policy_value_gate2a_consumer_preregistration_v1_20260730.json"
    )
    activation = read_object(
        root
        / "results/v24191_policy_value_gate2a_consumer_activation_audit_v1_20260730.json"
    )
    gate3a = read_object(
        root / "results/v2413_gate3a_controller_design_preregistration_v1_20260727.json"
    )
    policy = gate3a.get("controller_policy_design", {})
    if (
        v91.get("protocol_id")
        != "v24191_policy_value_true_continuation_gate2a_consumer_v1"
        or v91.get("policy_value_contract", {}).get("parent_settings")
        != DEFAULT_SETTINGS
        or v91.get("policy_value_contract", {}).get("settings")
        != DEFAULT_POLICY_SETTINGS
        or activation.get("activation_valid") is not True
        or policy.get("missing_signal_rule")
        != {
            "anchor_full": "abstain unless anchor risk and anchor entropy are available",
            "anchor_no_entropy": "abstain unless anchor risk is available",
            "late_0": "abstain unless coverage risk is available",
            "late_1": "abstain unless row or cell risk is available",
        }
        or policy.get("observation_only_decisions") != ["stop", "abstain"]
        or policy.get("branch_specific_action_selection") is not True
        or policy.get("maximum_one_action_per_context") is not True
    ):
        raise RuntimeError("V2.41.92 frozen parent semantics drifted")
    return parents


def _safe_preterminal_boundary(root: Path, proc_root: Path) -> dict[str, Any]:
    parent = read_object(_ordinary(root, PARENT_STATE))
    phase = read_object(_ordinary(root, PHASE_LIVENESS_STATE))
    rows = process_snapshot(proc_root)
    runner = process_report(rows, RUNNER_MARKER)
    phase_liveness = process_report(rows, PHASE_LIVENESS_MARKER)
    grandparent = process_report(rows, GRANDPARENT_CONSUMER_MARKER)
    old = process_report(rows, PARENT_CONSUMER_MARKER)
    replacement = process_report(rows, CONSUMER_MARKER)
    if (
        parent.get("role") != "v24191_policy_value_gate2a_consumer_state"
        or parent.get("status") != "waiting_for_v24190_tie_aware_gate2a_terminal"
        or parent.get("parent_status")
        != "waiting_for_true_continuation_audit_terminal"
        or parent.get("parent_source_status")
        != "waiting_for_p12_trial2_exact220_release"
        or parent.get("parent_source_truth_fields_all_false") is not True
        or parent.get("parent_terminal") is not False
        or parent.get("parent_tie_aware_gate2a_evaluated") is not False
        or parent.get("terminal") is not False
        or parent.get("activation_ready") is not True
        or parent.get("manifest_model_prediction_or_outcome_opened") is not False
        or parent.get(
            "mapping_gold_category_question_type_evaluator_score_or_outcome_read_by_consumer"
        )
        is not False
        or parent.get(
            "network_model_search_fetch_or_evaluator_api_called_by_consumer"
        )
        is not False
        or parent.get("policy_value_gate2a_evaluated") is not False
        or parent.get("policy_value_gate2a_passed") is not False
        or parent.get("v24190_authoritative_for_controller_design") is not False
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
        or grandparent["match_count"] != 1
        or old["match_count"] != 1
        or replacement["present"]
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (STATE, REPORT, ACTIVATION)
        )
        or (root / PARENT_REPORT).exists()
        or (root / PARENT_REPORT).is_symlink()
    ):
        raise RuntimeError("V2.41.92 preterminal boundary is not safe")
    return {
        "parent_status": parent["status"],
        "ancestor_status": parent["parent_status"],
        "ancestor_source_status": parent["parent_source_status"],
        "parent_activation_ready": True,
        "source_runner_exactly_one": True,
        "authoritative_phase_liveness_exactly_one": True,
        "authoritative_phase_state_safe": True,
        "v24190_grandparent_consumer_exactly_one": True,
        "v24191_parent_consumer_exactly_one": True,
        "v24192_consumer_absent_before_freeze": True,
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
        raise RuntimeError("V2.41.92 may only freeze the canonical workspace")
    if any((root / path).exists() or (root / path).is_symlink() for path in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.92 unattested Python bootstrap path appeared")
    parents = validate_frozen_parents(root)
    boundary = (
        _safe_preterminal_boundary(root, proc_root)
        if require_pristine
        else {
            "parent_status": "waiting_for_v24190_tie_aware_gate2a_terminal",
            "ancestor_status": "waiting_for_true_continuation_audit_terminal",
            "ancestor_source_status": "waiting_for_p12_trial2_exact220_release",
            "parent_activation_ready": True,
            "source_runner_exactly_one": True,
            "authoritative_phase_liveness_exactly_one": True,
            "authoritative_phase_state_safe": True,
            "v24190_grandparent_consumer_exactly_one": True,
            "v24191_parent_consumer_exactly_one": True,
            "v24192_consumer_absent_before_freeze": True,
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
            "v24122_capture_is_stage_based_not_signal_availability_gated": True,
            "v24123_manifest_accepts_canonical_missing_features": True,
            "v24191_ranks_actions_without_gate3a_missing_signal_abstain": True,
            "v24191_can_pass_when_full_branch_must_abstain": True,
            "full_and_no_entropy_missing_signal_rules_differ_at_anchor": True,
            "canonical_zero_must_not_be_treated_as_observed_signal": True,
            "v24191_frozen_bytes_modified": False,
            "source_true_continuation_forward_or_evaluator_changed": False,
        },
        "abstain_aware_contract": {
            "parent_settings": dict(DEFAULT_SETTINGS),
            "parent_settings_sha256": object_sha256(DEFAULT_SETTINGS),
            "policy_settings": dict(DEFAULT_POLICY_SETTINGS),
            "policy_settings_sha256": object_sha256(DEFAULT_POLICY_SETTINGS),
            "settings": dict(DEFAULT_ABSTAIN_SETTINGS),
            "settings_sha256": object_sha256(DEFAULT_ABSTAIN_SETTINGS),
            "branch_specific_missing_signal_rule": {
                "anchor_full": "anchor risk and anchor entropy required",
                "anchor_no_entropy": "anchor risk required",
                "anchor_fixed_heuristic": "anchor risk required",
                "late_0_all_branches": "coverage risk required",
                "late_1_all_branches": "row-eligibility or cell-value risk required",
            },
            "decisions": ["action", "stop", "abstain"],
            "stop_and_abstain_checkpoint_contribution": 0.0,
            "stop_and_abstain_separately_reported": True,
            "missing_signal_checkpoints_retained_in_primary_estimand": True,
            "availability_matched_random_and_oracle_baselines": True,
            "unconstrained_oracle_diagnostic_only": True,
            "full_signal_available_minimum_support_required": True,
            "overall_policy_value_advantage_family": list(VALUE_ADVANTAGES),
            "full_signal_available_action_value_advantage_family": list(
                VALUE_ADVANTAGES
            ),
            "both_shared_cluster_bootstrap_minimum_lowers_strictly_positive": True,
            "parent_v24190_pass_required": True,
            "parent_v24191_result_diagnostic_only_without_v24192": True,
            "single_checkpoint_decision_rule_replayed_exactly": True,
            "multi_context_closed_loop_policy_effect_requires_gate3a": True,
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
                "deepwide_agent.v24191_policy_value_gate2a",
                "deepwide_agent.v24192_abstain_aware_gate2a",
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
            "controller_design_only_after_v24192_gate_pass": True,
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
            "abstain_aware_gate2a_result_available": False,
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
        raise RuntimeError("V2.41.92 protocol path is noncanonical")
    value = read_object(raw)
    rebuilt = build_protocol(
        root,
        created_at_unix=int(value.get("created_at_unix", -1)),
        require_pristine=False,
    )
    if value != rebuilt:
        raise RuntimeError("V2.41.92 protocol differs from live rebuild")
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
        raise RuntimeError("V2.41.92 output path drifted")
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
