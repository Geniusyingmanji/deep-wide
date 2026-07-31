#!/usr/bin/env python3
"""Audit V2.42.16 at its parent-preterminal wait boundary."""

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

from deepwide_agent.v24216_package_gate import payload_sha256  # noqa: E402
from scripts.activate_v24216_package_gate import validate_activation  # noqa: E402
from scripts.preregister_v24210_search_component import (  # noqa: E402
    publish_new,
    read_object,
    sha256,
)
from scripts.preregister_v24216_package_gate import (  # noqa: E402
    ACTIVATION,
    BASELINE_RESULT,
    CANDIDATE_RESULT,
    FORWARD_BARRIER,
    GATE_DECISION,
    OUTPUT,
    PAIR_PREPARE,
    PARENT_PUBLICATION,
    PARENT_STATE,
    STATE,
    V24194_EXECUTION_ACTIVATION,
    V24194_FREEZE,
    V24194_REPORT,
    V24196_FREEZE,
    V24196_REPORT,
    WAIT_AUDIT,
    validate_protocol,
)
from scripts.run_v24216_package_gate import ARM_ROOTS  # noqa: E402


def _present(root: Path, path: Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def build_audit(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    activation = validate_activation(root, ACTIVATION, proc_root=proc_root)
    state_path = root / STATE
    state = read_object(state_path)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "parent_publication_opened",
        "r1_release_envelope_opened",
        "capacity_priority_rechecked",
        "paired_roots_materialized",
        "historical_baseline_result_reused",
        "baseline_forward_called",
        "candidate_forward_called",
        "both_forward_arms_exact_terminal_before_mapping",
        "mapping_or_evaluator_opened",
        "baseline_evaluator_called",
        "candidate_evaluator_called",
        "package_gate_evaluated",
        "package_gate_passed",
        "capacity_measurement_allowed",
        "all220_freeze_design_allowed",
        "shared_api_lease_acquired",
        "lease_compatibility_valid",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    future = (
        PARENT_PUBLICATION,
        PAIR_PREPARE,
        FORWARD_BARRIER,
        BASELINE_RESULT,
        CANDIDATE_RESULT,
        GATE_DECISION,
        V24194_EXECUTION_ACTIVATION,
        V24194_REPORT,
        V24194_FREEZE,
        V24196_REPORT,
        V24196_FREEZE,
    )
    if (
        state.get("role") != "v24216_package_gate_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or state.get("status") != "waiting_for_v24215_joint_package_terminal"
        or state.get("reason") != "parent_preterminal"
        or state.get("parent_safe_state_envelope_opened") is not True
        or state.get("parent_state", {}).get("path") != str(PARENT_STATE)
        or state.get("parent_state", {}).get("terminal") is not False
        or any(state.get(field) is not False for field in false_fields)
        or state.get("runtime_forward_inputs_exactly_opaque_id_and_question") is not True
        or seal != payload_sha256(unsigned)
        or any(_present(root, path) for path in future)
        or any(path.exists() or path.is_symlink() for path in ARM_ROOTS.values())
    ):
        raise RuntimeError("V2.42.16 wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24216_package_gate_wait_audit",
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "protocol": {
            "path": str(OUTPUT),
            "sha256": protocol["sha256"],
            "decision_contract_sha256": protocol["value"]["decision_contract_sha256"],
            "control_manifest_sha256": protocol["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": {
            "path": str(ACTIVATION),
            "sha256": activation["sha256"],
            "watcher_pid": activation["value"]["watcher"]["pid"],
            "watcher_start_ticks": activation["value"]["watcher"]["start_ticks"],
        },
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": sha256(state_path),
            "status": state["status"],
        },
        "boundary": {
            "parent_safe_state_envelope_opened": True,
            "parent_terminal": False,
            "parent_publication_absent_and_unopened": True,
            "paired_arm_roots_absent": True,
            "pair_prepare_forward_barrier_arm_results_and_gate_absent": True,
            "v24194_execution_activation_report_and_freeze_absent": True,
            "v24196_report_and_freeze_absent": True,
            "historical_baseline_result_reused": False,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "watcher_active": True,
            "future_parent_publication_read_requires_parent_terminal": True,
            "future_pair_materialization_requires_parent_r1_and_capacity_priority_gates": True,
            "future_dev64_requires_single_shared_lease_and_live_compatibility": True,
            "future_mapping_requires_both_forward_arms_exact_terminal": True,
            "future_capacity_requires_package_gate_go": True,
            "future_all220_requires_capacity_freeze_and_separate_single_owner": True,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(WAIT_AUDIT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / WAIT_AUDIT).resolve(strict=False):
        raise RuntimeError("V2.42.16 wait-audit output drifted")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
