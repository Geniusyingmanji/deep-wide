#!/usr/bin/env python3
"""Create-exclusive activation audit for the V2.41.91 read-only consumer."""

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

from scripts.preregister_v24160_true_continuation_liveness_schema import (  # noqa: E402
    RUNNER_MARKER,
)
from scripts.preregister_v24190_tie_aware_gate2a import (  # noqa: E402
    CONSUMER_MARKER as PARENT_CONSUMER_MARKER,
    STATE as PARENT_STATE,
)
from scripts.preregister_v24191_policy_value_gate2a import (  # noqa: E402
    ACTIVATION,
    CONSUMER_MARKER,
    OUTPUT,
    PHASE_LIVENESS_MARKER,
    PHASE_LIVENESS_STATE,
    REPORT,
    STATE,
    validate_protocol,
)
from scripts.v24159_true_continuation_reachability import (  # noqa: E402
    object_sha256,
    process_report,
    process_snapshot,
    publish_new,
    read_object,
    sha256,
)


def build_report(
    root: Path = ROOT,
    *,
    proc_root: Path = Path("/proc"),
    created_at_unix: int | None = None,
    processes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    verified = validate_protocol(root, OUTPUT)
    state_path = root / STATE
    state = read_object(state_path)
    parent_state_path = root / PARENT_STATE
    parent_state = read_object(parent_state_path)
    phase = read_object(root / PHASE_LIVENESS_STATE)
    rows = process_snapshot(proc_root) if processes is None else processes
    runner = process_report(rows, RUNNER_MARKER)
    phase_liveness = process_report(rows, PHASE_LIVENESS_MARKER)
    parent = process_report(rows, PARENT_CONSUMER_MARKER)
    successor = process_report(rows, CONSUMER_MARKER)
    report_absent = not (root / REPORT).exists() and not (root / REPORT).is_symlink()
    parent_truth = parent_state.get("source_truth") or {}
    parent_state_safe = bool(
        parent_state.get("role") == "v24190_tie_aware_gate2a_consumer_state"
        and parent_state.get("status")
        == "waiting_for_true_continuation_audit_terminal"
        and parent_state.get("source_status")
        == "waiting_for_p12_trial2_exact220_release"
        and parent_state.get("source_terminal") is False
        and set(parent_truth)
        == {
            "mapping_or_gold_read",
            "evaluator_or_score_read",
            "api_or_benchmark_forward_called",
            "shared_api_lease_acquired",
        }
        and all(value is False for value in parent_truth.values())
        and parent_state.get("terminal") is False
        and parent_state.get("activation_ready") is True
        and parent_state.get("manifest_prediction_or_outcome_opened") is False
        and parent_state.get("tie_aware_gate2a_evaluated") is False
        and parent_state.get("controller_design_allowed") is False
        and parent_state.get("training_credit_allowed") is False
        and parent_state.get("full220_controller_launch_allowed") is False
    )
    boundary_valid = bool(
        state.get("role") == "v24191_policy_value_gate2a_consumer_state"
        and state.get("protocol", {}).get("sha256") == verified["sha256"]
        and state.get("status") == "waiting_for_v24190_tie_aware_gate2a_terminal"
        and state.get("parent_status")
        == "waiting_for_true_continuation_audit_terminal"
        and state.get("parent_source_status")
        == "waiting_for_p12_trial2_exact220_release"
        and state.get("parent_source_truth_fields_all_false") is True
        and state.get("parent_terminal") is False
        and state.get("parent_tie_aware_gate2a_evaluated") is False
        and state.get("manifest_model_prediction_or_outcome_opened") is False
        and state.get(
            "mapping_gold_category_question_type_evaluator_score_or_outcome_read_by_consumer"
        )
        is False
        and state.get(
            "network_model_search_fetch_or_evaluator_api_called_by_consumer"
        )
        is False
        and state.get("policy_value_gate2a_evaluated") is False
        and state.get("policy_value_gate2a_passed") is False
        and state.get("activation_ready") is False
        and state.get("v24190_authoritative_for_controller_design") is False
        and state.get("controller_design_allowed") is False
        and state.get("controller_implementation_or_pilot_launch_allowed") is False
        and state.get("training_credit_allowed") is False
        and state.get("full220_controller_launch_allowed") is False
        and state.get("benchmark_or_sota_claim") is False
        and state.get("terminal") is False
        and report_absent
        and parent_state_safe
        and phase.get("role") == "v24187_phase_liveness_audit"
        and phase.get("overall_status")
        in {"healthy", "degraded_forward_healthy_manual_review_only"}
        and phase.get("critical_findings") == []
        and phase.get("current_phase", {}).get("phase") == "r1_full220"
        and phase.get("current_phase", {}).get("valid") is True
        and runner["match_count"] == 1
        and phase_liveness["match_count"] == 1
        and parent["match_count"] == 1
        and successor["match_count"] == 1
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24191_policy_value_gate2a_consumer_activation_audit",
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
        },
        "state": {
            "path": str(STATE),
            "sha256": sha256(state_path),
            "status": state.get("status"),
            "parent_status": state.get("parent_status"),
            "contents_emitted": False,
        },
        "parent_state": {
            "path": str(PARENT_STATE),
            "sha256": sha256(parent_state_path),
            "safe_preterminal": parent_state_safe,
            "contents_emitted": False,
        },
        "processes": {
            "source_runner": runner,
            "authoritative_phase_liveness": phase_liveness,
            "v24190_parent_consumer": parent,
            "v24191_consumer": successor,
        },
        "boundary": {
            "safe_preterminal_wait": boundary_valid,
            "v24190_parent_state_live_revalidated": parent_state_safe,
            "v24190_parent_consumer_preserved": parent["match_count"] == 1,
            "v24191_consumer_exactly_one": successor["match_count"] == 1,
            "policy_value_report_absent_before_parent_terminal": report_absent,
            "manifest_model_prediction_or_outcome_opened": False,
            "mapping_gold_category_question_type_evaluator_score_or_outcome_read": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "network_model_search_fetch_or_evaluator_api_called": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "r1_p12_schema76_schema77_avg4_or_quality_chain_modified": False,
        },
        "claims": {
            "policy_value_consumer_wait_chain_active": boundary_valid,
            "policy_value_gate2a_result_available": False,
            "entropy_action_value_identified": False,
            "controller_or_training_enabled": False,
            "benchmark_score_available": False,
            "sota": False,
        },
        "activation_valid": boundary_valid,
    }
    value["audit_payload_sha256"] = object_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(ACTIVATION))
    parser.add_argument("--proc-root", default="/proc")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    if output.resolve(strict=False) != (root / ACTIVATION).resolve(strict=False):
        raise RuntimeError("V2.41.91 activation output path drifted")
    value = build_report(root, proc_root=Path(args.proc_root))
    if not value["activation_valid"]:
        raise RuntimeError("V2.41.91 activation boundary is invalid")
    publish_new(output, value)
    print(json.dumps({"output": str(output), "activation_valid": True}))


if __name__ == "__main__":
    main()
