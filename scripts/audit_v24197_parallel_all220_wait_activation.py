#!/usr/bin/env python3
"""Audit the activated V2.41.97 planner at its pre-capacity wait boundary."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from scripts.activate_v24197_parallel_all220 import validate_activation  # noqa: E402
from scripts.preregister_v24197_parallel_all220 import (  # noqa: E402
    ACTIVATION,
    BUNDLE,
    CAPACITY_FREEZE,
    CAPACITY_REPORT,
    OUTPUT,
    PLAN,
    STATE,
    WAIT_AUDIT,
    payload_sha256,
    protected_processes,
    publish_new,
    read_object,
    sha256,
    validate_protocol,
)


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
    unsigned = {key: item for key, item in state.items() if key != "state_payload_sha256"}
    capacity_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (CAPACITY_REPORT, CAPACITY_FREEZE)
    )
    downstream_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (BUNDLE, PLAN)
    )
    frozen_processes = protocol["value"]["safe_wait_boundary"][
        "protected_processes"
    ]
    live_processes = protected_processes(proc_root)
    if (
        state.get("role") != "v24197_parallel_all220_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or state.get("status") != "waiting_for_capacity_freeze"
        or state.get("reason") != "v24196_capacity_pair_absent"
        or state.get("capacity_pair_opened") is not False
        or state.get("candidate_bundle_opened") is not False
        or state.get("opaque_id_files_opened") is not False
        or state.get("candidate_manifest_bytes_hashed") is not False
        or state.get("parallel_plan_created") is not False
        or state.get("shared_api_lease_acquired") is not False
        or state.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or state.get(
            "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted"
        )
        is not False
        or state.get("mapping_gold_category_question_type_evaluator_score_read") is not False
        or state.get("credential_value_read_persisted_hashed_or_emitted") is not False
        or state.get("process_signal_restart_resume_rerun_skip_or_selective_retry") is not False
        or state.get("current_r1_or_quality_chain_forward_config_changed") is not False
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get("terminal") is not False
        or state.get("state_payload_sha256") != payload_sha256(unsigned)
        or not capacity_absent
        or not downstream_absent
        or live_processes != frozen_processes
    ):
        raise RuntimeError("V2.41.97 wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24197_parallel_all220_wait_activation_audit",
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
            "executor_pid": activation["value"]["executor"]["pid"],
            "executor_start_ticks": activation["value"]["executor"]["start_ticks"],
        },
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": sha256(state_path),
            "status": state["status"],
        },
        "boundary": {
            "v24196_capacity_report_and_freeze_absent": True,
            "candidate_bundle_and_parallel_plan_absent": True,
            "capacity_candidate_or_opaque_id_contents_opened": False,
            "candidate_manifest_bytes_hashed": False,
            "all_protocol_protected_process_identities_preserved": True,
            "protected_processes": live_processes,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted": False,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "wait_only_planner_active": True,
            "parallel_plan_creation_active": False,
            "future_plan_requires_capacity_and_candidate_go_bundle": True,
            "future_executor_requires_separate_preregistration_and_activation": True,
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
        raise RuntimeError("V2.41.97 wait-audit path drifted")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
