#!/usr/bin/env python3
"""Audit the V2.41.94 wait-only launch before any capacity API call."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.preregister_v24194_capacity_ladder import (  # noqa: E402
    EXECUTION_ACTIVATION,
    FREEZE,
    OUTPUT,
    REPORT,
    R1_STATE,
    STATE,
    WAIT_ACTIVATION,
    WATCHER_MARKER,
    publish_new,
    sha256,
    validate_protocol,
)
from scripts.v24159_true_continuation_reachability import (  # noqa: E402
    object_sha256,
    process_report,
    process_snapshot,
)


ROLE = "v24194_capacity_ladder_wait_activation_audit"
FORWARD_MARKER = "scripts/run_deepwide_agent.py"
LAUNCHER_MARKER = "scripts/launch_frozen_deepwide.py"


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.41.94 activation source is noncanonical: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.94 activation source is not an object")
    return value


def _start_ticks(proc_root: Path, pid: int) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    # The comm field can contain spaces and parentheses.  Split after its last
    # closing parenthesis; starttime is field 22, or index 19 in this suffix.
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.41.94 process stat is truncated")
    return int(suffix[19])


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
    state = _read(root / state_path)
    rows = process_snapshot(proc_root)
    watcher = process_report(rows, WATCHER_MARKER)
    forward = process_report(rows, FORWARD_MARKER)
    launcher = process_report(rows, LAUNCHER_MARKER)
    r1 = _read(root / R1_STATE)
    aggregate = r1.get("aggregate") or {}
    if (
        state.get("role") != "v24194_capacity_ladder_watcher_state"
        or state.get("protocol", {}).get("sha256") != verified["sha256"]
        or state.get("status") != "waiting_for_r1_release"
        or state.get("reason") != "r1_not_exact220_released"
        or state.get("r1_release") is not None
        or state.get("execution_activation") is not None
        or state.get("consecutive_quiet_observations") != 0
        or state.get("shared_api_lease_acquired") is not False
        or state.get("neutral_capacity_model_api_called") is not False
        or state.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or state.get("runtime_task_state_answer_evidence_or_url_opened") is not False
        or state.get("credential_value_read_persisted_hashed_or_emitted") is not False
        or state.get("search_fetch_or_evaluator_api_called") is not False
        or state.get("response_text_or_response_id_persisted") is not False
        or state.get(
            "current_r1_or_quality_chain_process_signal_restart_resume_rerun_skip"
        )
        is not False
        or state.get(
            "current_r1_or_quality_chain_forward_config_concurrency_changed"
        )
        is not False
        or state.get("full220_launch_allowed") is not False
        or state.get("leaderboard_submission_or_sota_claim") is not False
        or state.get("terminal") is not False
        or state.get("state_payload_sha256")
        != object_sha256(
            {
                key: value
                for key, value in state.items()
                if key != "state_payload_sha256"
            }
        )
        or watcher["match_count"] != 1
        or forward["match_count"] != 1
        or launcher["match_count"] != 1
        or r1.get("status") != "waiting_for_r1_exact_terminal_220"
        or aggregate.get("selected") != 220
        or aggregate.get("exact_terminal_220") is not False
        or not 0 <= int(aggregate.get("terminal", -1)) < 220
        or r1.get("mapping_or_gold_read") is not False
        or r1.get("evaluator_or_score_read") is not False
        or r1.get("process_signal_restart_resume_rerun_skip_or_selective_retry")
        is not False
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (REPORT, FREEZE, EXECUTION_ACTIVATION)
        )
    ):
        raise RuntimeError("V2.41.94 wait-only activation boundary is invalid")
    watcher_pid = watcher["pids"][0]
    forward_pid = forward["pids"][0]
    launcher_pid = launcher["pids"][0]
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
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": sha256(root / STATE),
            "status": state["status"],
        },
        "processes": {
            "capacity_watcher": {
                "pid": watcher_pid,
                "start_ticks": _start_ticks(proc_root, watcher_pid),
            },
            "r1_forward": {
                "pid": forward_pid,
                "start_ticks": _start_ticks(proc_root, forward_pid),
            },
            "r1_launcher": {
                "pid": launcher_pid,
                "start_ticks": _start_ticks(proc_root, launcher_pid),
            },
            "command_lines_emitted": False,
        },
        "boundary": {
            "r1_forward_and_launcher_preserved": True,
            "capacity_watcher_exactly_one": True,
            "shared_api_lease_acquired": False,
            "neutral_capacity_model_api_called": False,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "network_model_search_fetch_or_evaluator_api_called": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "current_r1_forward_config_or_concurrency_changed": False,
            "capacity_report_freeze_or_execution_activation_present": False,
        },
        "authorization": {
            "wait_only_launch_active": True,
            "capacity_execution_active": False,
            "future_execution_activation_requires_quality_campaign_terminal": True,
            "future_execution_activation_requires_registered_lease_owner": True,
            "future_all220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["activation_payload_sha256"] = object_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--output", default=str(WAIT_ACTIVATION))
    parser.add_argument("--proc-root", default="/proc")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    target = Path(args.output)
    if not target.is_absolute():
        target = root / target
    if target.resolve(strict=False) != (root / WAIT_ACTIVATION).resolve(strict=False):
        raise RuntimeError("V2.41.94 activation output path drifted")
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
