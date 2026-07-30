#!/usr/bin/env python3
"""Freeze the append-only tie-aware true-continuation Gate-2A consumer."""

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
from scripts.preregister_v24160_true_continuation_liveness_schema import (  # noqa: E402
    RUNNER_MARKER,
)
from scripts.preregister_v24162_canonical_gate2a_consumer import (  # noqa: E402
    CONSUMER_MARKER as PARENT_CONSUMER_MARKER,
)
from scripts.v24159_true_continuation_reachability import (  # noqa: E402
    object_sha256,
    process_report,
    process_snapshot,
    publish_new,
    read_object,
    sha256,
)


ROLE = "v24190_tie_aware_gate2a_consumer_preregistration"
PROTOCOL_ID = "v24190_tie_aware_true_continuation_gate2a_consumer_v1"
OUTPUT = Path(
    "results/v24190_tie_aware_gate2a_consumer_preregistration_v1_20260730.json"
)
STATE = Path("outputs/v24190_tie_aware_gate2a_consumer_state_v1_20260730.json")
REPORT = Path(
    "results/v24190_tie_aware_true_continuation_gate2a_report_v1_20260730.json"
)
ACTIVATION = Path(
    "results/v24190_tie_aware_gate2a_consumer_activation_audit_v1_20260730.json"
)
SOURCE_STATE = Path(
    "outputs/v24159_true_continuation_reachability_state_v1_20260729.json"
)
PARENT_STATE = Path(
    "outputs/v24162_canonical_gate2a_consumer_state_v1_20260729.json"
)
PARENT_REPORT = Path(
    "results/v24162_canonical_strict_true_continuation_gate2a_report_v1_20260729.json"
)
CONSUMER_MARKER = "scripts/watch_v24190_tie_aware_gate2a.py"
PHASE_LIVENESS_MARKER = "scripts/watch_v24187_phase_liveness.py"
PHASE_LIVENESS_STATE = Path(
    "outputs/v24187_phase_liveness_watcher_state_v1_20260730.json"
)

FROZEN_PARENTS = {
    "results/v24161_strict_gate2a_consumer_preregistration_v1_20260729.json": "b5c1174d8a02bb3d3719d6e212c76ff690d87e4e5d85320ed3b38c5c13d67023",
    "results/v24162_canonical_gate2a_consumer_preregistration_v1_20260729.json": "98f2405ce41ca140c9d486040611cc65952306eae85ff0a6ab1b16ea1e4d85b6",
    "results/v24162_canonical_gate2a_consumer_activation_audit_v1_20260729.json": "af1ea8f03cf1171cb3353a01982003e6f288a62332085de25d582b82d3141122",
    "src/deepwide_agent/v24161_strict_gate2a.py": "dc870de1db1184a86f18f2606fabaf9d50947f02b82c96f847b8fa3ec63208d3",
    "scripts/watch_v24162_canonical_gate2a_consumer.py": "cb7e41a6912674b9154415aa2dc9096fec8cb8f5fb6e38e046873f9b356585b9",
    "results/v24187_phase_liveness_preregistration_v1_20260730.json": "873f42369f6f5ac7d1b619510257f8cc7c932140b734dd14d23c4a5c6e45d34c",
    "results/v24187_phase_liveness_activation_audit_v1_20260730.json": "b57bdc1fbcce3911111f9c571c77dd37f1d1ecbf1030b1658638c0062cbaa4b2",
    "scripts/watch_v24187_phase_liveness.py": "83789b1cc2eb1e6e87969894409b09039028e0e13b53ba8de90776171bf567d3",
}
CONTROL_FILES = (
    "src/deepwide_agent/v24190_tie_aware_gate2a.py",
    "scripts/preregister_v24190_tie_aware_gate2a.py",
    "scripts/watch_v24190_tie_aware_gate2a.py",
    "scripts/audit_v24190_tie_aware_gate2a_activation.py",
    "tests/test_v24190_tie_aware_gate2a.py",
    "tests/test_v24190_tie_aware_consumer.py",
    "tests/test_v24190_tie_aware_activation.py",
)
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
DECISION_FIELDS = (
    "protocol_id",
    "parents",
    "scientific_defect",
    "tie_aware_contract",
    "source_release_gate",
    "execution",
    "source_policy",
    "authorization",
    "control_surface",
)


def _ordinary(root: Path, relative: str | Path, expected: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.90 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
    ):
        raise RuntimeError(f"V2.41.90 expected an ordinary file: {relative}")
    if expected is not None and sha256(path) != expected:
        raise RuntimeError(f"V2.41.90 frozen parent drifted: {relative}")
    return path


def validate_frozen_parents(root: Path) -> dict[str, Any]:
    parents = {
        relative: {"sha256": sha256(_ordinary(root, relative, digest))}
        for relative, digest in FROZEN_PARENTS.items()
    }
    v61 = read_object(
        root
        / "results/v24161_strict_gate2a_consumer_preregistration_v1_20260729.json"
    )
    v62 = read_object(
        root
        / "results/v24162_canonical_gate2a_consumer_preregistration_v1_20260729.json"
    )
    activation = read_object(
        root
        / "results/v24162_canonical_gate2a_consumer_activation_audit_v1_20260729.json"
    )
    if (
        v61.get("protocol_id")
        != "v24161_strict_true_continuation_gate2a_consumer_v1"
        or v61.get("strict_consumer_contract", {}).get("settings")
        != DEFAULT_SETTINGS
        or v62.get("protocol_id")
        != "v24162_canonical_strict_gate2a_consumer_v1"
        or v62.get("strict_consumer_contract", {}).get(
            "identical_to_v24161_scientific_contract"
        )
        is not True
        or activation.get("role")
        != "v24162_canonical_gate2a_consumer_activation_audit"
        or activation.get("activation_valid") is not True
    ):
        raise RuntimeError("V2.41.90 frozen parent semantics drifted")
    return parents


def _safe_preterminal_boundary(root: Path, proc_root: Path) -> dict[str, Any]:
    source = read_object(_ordinary(root, SOURCE_STATE))
    parent = read_object(_ordinary(root, PARENT_STATE))
    phase = read_object(_ordinary(root, PHASE_LIVENESS_STATE))
    rows = process_snapshot(proc_root)
    runner = process_report(rows, RUNNER_MARKER)
    phase_liveness = process_report(rows, PHASE_LIVENESS_MARKER)
    old = process_report(rows, PARENT_CONSUMER_MARKER)
    replacement = process_report(rows, CONSUMER_MARKER)
    truth_fields = (
        "mapping_or_gold_read",
        "evaluator_or_score_read",
        "api_or_benchmark_forward_called",
        "shared_api_lease_acquired",
    )
    if (
        source.get("role") != "v24159_true_continuation_reachability_state"
        or source.get("status") != "waiting_for_p12_trial2_exact220_release"
        or source.get("terminal") is not False
        or any(source.get(field) is not False for field in truth_fields)
        or parent.get("role") != "v24162_canonical_gate2a_consumer_state"
        or parent.get("status") != "waiting_for_true_continuation_audit_terminal"
        or parent.get("strict_gate2a_evaluated") is not False
        or parent.get("manifest_prediction_or_outcome_opened") is not False
        or parent.get("controller_design_allowed") is not False
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
        raise RuntimeError("V2.41.90 preterminal boundary is not safe")
    return {
        "source_status": source["status"],
        "source_truth_fields_all_false": True,
        "source_runner_exactly_one": True,
        "authoritative_phase_liveness_exactly_one": True,
        "authoritative_phase_state_safe": True,
        "v24162_parent_consumer_exactly_one": True,
        "v24190_consumer_absent_before_freeze": True,
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
        raise RuntimeError("V2.41.90 may only freeze the canonical workspace")
    if any((root / path).exists() or (root / path).is_symlink() for path in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.90 unattested Python bootstrap path appeared")
    parents = validate_frozen_parents(root)
    boundary = (
        _safe_preterminal_boundary(root, proc_root)
        if require_pristine
        else {
            "source_status": "waiting_for_p12_trial2_exact220_release",
            "source_truth_fields_all_false": True,
            "source_runner_exactly_one": True,
            "authoritative_phase_liveness_exactly_one": True,
            "authoritative_phase_state_safe": True,
            "v24162_parent_consumer_exactly_one": True,
            "v24190_consumer_absent_before_freeze": True,
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
        "label_blind_before_source_terminal": True,
        "parents": parents,
        "scientific_defect": {
            "v24161_random_top2_baseline_fixed_at_two_thirds": True,
            "fixed_baseline_is_wrong_when_terminal_best_actions_tie": True,
            "v24161_prediction_top2_uses_action_order_for_boundary_ties": True,
            "deterministic_tie_order_can_create_or_remove_apparent_hit": True,
            "true_continuation_contribution_is_rounded_and_can_tie": True,
            "v24161_v24162_frozen_bytes_modified": False,
            "source_true_continuation_forward_or_evaluator_changed": False,
        },
        "tie_aware_contract": {
            "settings": dict(DEFAULT_SETTINGS),
            "settings_sha256": object_sha256(DEFAULT_SETTINGS),
            "rank_and_non_top2_conditions_inherited_from_v24161": True,
            "rank_unit": "complete_same_checkpoint_three_action_group",
            "bootstrap_unit": "task_cluster_ref_sha256",
            "true_best_tie_policy": "all actions exactly tied at rounded maximum contribution",
            "model_top2_boundary_tie_policy": "uniform sampling without replacement within cutoff score tier",
            "random_top2_baseline": "one minus C(action_count-best_count,2)/C(action_count,2)",
            "action_declaration_order_for_ties": False,
            "paired_full_minus_random_required": True,
            "paired_full_minus_no_entropy_required": True,
            "paired_full_minus_fixed_heuristic_required": True,
            "all_three_cluster_bootstrap_ci_lowers_strictly_positive": True,
            "parent_v24161_v24162_result_diagnostic_only": True,
            "canonical_module_identity_checked_before_wait_and_evaluation": True,
        },
        "source_release_gate": {
            "source_state_path": str(SOURCE_STATE),
            "required_source_status": "audit_terminal",
            "authoritative_phase_state_path": str(PHASE_LIVENESS_STATE),
            "authoritative_phase_watcher_marker": PHASE_LIVENESS_MARKER,
            "retired_v24160_process_required": False,
            "parent_state_path": str(PARENT_STATE),
            "parent_report_path": str(PARENT_REPORT),
            "parent_v24162_terminal_report_required": True,
            "parent_report_may_not_authorize_controller_without_v24190": True,
            "activation_required_before_scientific_inputs_opened": True,
            "all_manifest_predictions_and_aggregates_live_replayed": True,
            "no_manifest_prediction_or_outcome_opened_before_source_audit_terminal": True,
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
                "deepwide_agent.v24121_continuation",
                "deepwide_agent.v24123_release",
                "deepwide_agent.v24161_strict_gate2a",
                "deepwide_agent.v24190_tie_aware_gate2a",
            ],
        },
        "source_policy": {
            "preterminal_safe_source_and_parent_state_envelopes_only": True,
            "post_terminal_sealed_manifest_predictions_and_aggregates_only": True,
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
            "controller_design_only_after_tie_aware_gate_pass": True,
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
            "tie_aware_gate2a_result_available": False,
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
        raise RuntimeError("V2.41.90 protocol path is noncanonical")
    value = read_object(raw)
    rebuilt = build_protocol(
        root,
        created_at_unix=int(value.get("created_at_unix", -1)),
        require_pristine=False,
    )
    if value != rebuilt:
        raise RuntimeError("V2.41.90 protocol differs from live rebuild")
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
        raise RuntimeError("V2.41.90 output path drifted")
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
