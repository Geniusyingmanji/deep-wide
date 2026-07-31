#!/usr/bin/env python3
"""Audit V2.41.96 in its pre-release, wait-only state."""

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

from scripts.activate_v24196_capacity_executor import (  # noqa: E402
    start_ticks,
    validate_activation,
)
from scripts.preregister_v24196_capacity_executor import (  # noqa: E402
    ACTIVATION,
    FREEZE,
    OUTPUT,
    REPORT,
    STATE,
    WAIT_AUDIT,
    WATCHER_MARKER,
    payload_sha,
    publish_new,
    read_object,
    sha256,
    validate_protocol,
)
from scripts.v24159_true_continuation_reachability import (  # noqa: E402
    process_report,
    process_snapshot,
)


ROLE = "v24196_capacity_executor_wait_activation_audit"
V24195_WAIT_AUDIT = Path(
    "results/v24195_lease_owner_compatibility_wait_activation_audit_v1_20260731.json"
)
V24195_WAIT_AUDIT_SHA256 = (
    "d2959a0123d0778b4b09e540371440ff93ffcebc9039b0aeadb982e54039ac6a"
)
V24187_WATCHER_MARKER = "scripts/watch_v24187_phase_liveness.py"
V24194_WATCHER_MARKER = "scripts/watch_v24194_capacity_ladder.py"
V24195_WATCHER_MARKER = "scripts/watch_v24195_lease_owner_compatibility.py"
R1_FORWARD_MARKER = "scripts/run_deepwide_agent.py"
R1_LAUNCHER_MARKER = "scripts/launch_frozen_deepwide.py"


def build_audit(
    root: Path = ROOT,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    proc_root: Path = Path("/proc"),
    created_at_unix: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    verified = validate_protocol(root, protocol_path)
    activation = validate_activation(
        root,
        ACTIVATION,
        protocol_path=protocol_path,
        proc_root=proc_root,
    )
    state = read_object(root / state_path)
    rows = process_snapshot(proc_root)
    watcher = process_report(rows, WATCHER_MARKER)
    protected = {
        "v24187_phase_watcher": process_report(rows, V24187_WATCHER_MARKER),
        "v24194_capacity_watcher": process_report(rows, V24194_WATCHER_MARKER),
        "v24195_compatibility_watcher": process_report(rows, V24195_WATCHER_MARKER),
        "r1_forward": process_report(rows, R1_FORWARD_MARKER),
        "r1_launcher": process_report(rows, R1_LAUNCHER_MARKER),
    }
    wait_path = root / V24195_WAIT_AUDIT
    wait = read_object(wait_path)
    recorded = wait.get("processes") or {}
    protocol_recorded = verified["value"]["release_and_compatibility_gate"][
        "safe_wait_boundary"
    ]["protected_processes"]
    protected_identity_valid = bool(
        sha256(wait_path) == V24195_WAIT_AUDIT_SHA256
        and wait.get("role")
        == "v24195_lease_owner_compatibility_wait_activation_audit"
        and wait.get("activation_valid") is True
        and all(report.get("match_count") == 1 for report in protected.values())
        and set(protocol_recorded) == set(protected)
        and all(
            isinstance(protocol_recorded[name], dict)
            and protected[name]["pids"] == [protocol_recorded[name]["pid"]]
            and start_ticks(proc_root, protocol_recorded[name]["pid"])
            == protocol_recorded[name]["start_ticks"]
            for name in protected
        )
        and protected["v24194_capacity_watcher"]["pids"]
        == [recorded["v24194_capacity_watcher"]["pid"]]
        and protected["v24195_compatibility_watcher"]["pids"]
        == [recorded["compatibility_watcher"]["pid"]]
        and protected["r1_forward"]["pids"] == [recorded["r1_forward"]["pid"]]
        and protected["r1_launcher"]["pids"] == [recorded["r1_launcher"]["pid"]]
    )
    if (
        state.get("role") != "v24196_capacity_executor_watcher_state"
        or state.get("protocol", {}).get("sha256") != verified["sha256"]
        or state.get("status") != "waiting_for_r1_release"
        or state.get("reason") != "r1_not_exact220_released"
        or state.get("r1_release") is not None
        or state.get("quality_campaign_terminal") is not None
        or state.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or state.get("consecutive_quiet_observations") != 0
        or state.get("shared_api_lease_acquired") is not False
        or state.get("v24195_live_compatibility_valid") is not False
        or state.get("v24195_watcher_observation_valid") is not False
        or state.get("neutral_capacity_model_api_called") is not False
        or state.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or state.get("runtime_task_state_answer_evidence_or_url_opened") is not False
        or state.get("credential_value_read_persisted_hashed_or_emitted") is not False
        or state.get("search_fetch_or_evaluator_api_called") is not False
        or state.get("response_text_or_response_id_persisted") is not False
        or state.get("process_signal_restart_resume_rerun_skip_or_selective_retry")
        is not False
        or state.get("current_r1_or_quality_chain_forward_config_changed") is not False
        or state.get("full220_launch_allowed") is not False
        or state.get("leaderboard_submission_or_sota_claim") is not False
        or state.get("terminal") is not False
        or state.get("state_payload_sha256")
        != payload_sha(
            {key: value for key, value in state.items() if key != "state_payload_sha256"}
        )
        or watcher["match_count"] != 1
        or watcher["pids"] != [activation["value"]["executor"]["pid"]]
        or not protected_identity_valid
        or any((root / path).exists() or (root / path).is_symlink() for path in (REPORT, FREEZE))
    ):
        raise RuntimeError("V2.41.96 wait-only activation boundary is invalid")
    pid = watcher["pids"][0]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "activation_valid": True,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
            "control_manifest_sha256": verified["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
        "execution_activation": {
            "path": str(ACTIVATION),
            "sha256": activation["sha256"],
            "activation_payload_sha256": activation["value"][
                "activation_payload_sha256"
            ],
        },
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": sha256(root / STATE),
            "status": state["status"],
        },
        "executor": {
            "pid": pid,
            "start_ticks": start_ticks(proc_root, pid),
            "python_isolated_no_bytecode": True,
            "command_line_emitted": False,
        },
        "protected_existing_processes": {
            name: {
                "pid": report["pids"][0],
                "start_ticks": start_ticks(proc_root, report["pids"][0]),
            }
            for name, report in protected.items()
        }
        | {
            "v24195_wait_audit_path": str(V24195_WAIT_AUDIT),
            "v24195_wait_audit_sha256": V24195_WAIT_AUDIT_SHA256,
            "command_lines_emitted": False,
        },
        "boundary": {
            "r1_not_exact220_released": True,
            "all_existing_healthy_benchmark_and_watchers_preserved": True,
            "shared_api_lease_acquired": False,
            "v24195_active_compatibility_not_requested": True,
            "neutral_capacity_model_api_called": False,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "capacity_report_or_freeze_present": False,
        },
        "authorization": {
            "wait_only_successor_active": True,
            "capacity_execution_active": False,
            "future_execution_requires_all_frozen_gates": True,
            "future_all220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--output", default=str(WAIT_AUDIT))
    parser.add_argument("--proc-root", default="/proc")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    target = Path(args.output)
    target = target if target.is_absolute() else root / target
    if target.resolve(strict=False) != (root / WAIT_AUDIT).resolve(strict=False):
        raise RuntimeError("V2.41.96 wait audit output path drifted")
    value = build_audit(
        root,
        protocol_path=Path(args.protocol),
        state_path=Path(args.state),
        proc_root=Path(args.proc_root),
    )
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
