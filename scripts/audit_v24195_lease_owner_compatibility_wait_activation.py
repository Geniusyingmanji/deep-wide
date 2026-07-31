#!/usr/bin/env python3
"""Audit the V2.41.95 wait-only launch before any successor activation."""

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

from scripts.audit_v24194_capacity_ladder_wait_activation import (  # noqa: E402
    _start_ticks,
)
from scripts.preregister_v24195_lease_owner_compatibility import (  # noqa: E402
    EXECUTOR_MARKER,
    OUTPUT,
    STATE,
    V24196_ACTIVATION,
    WAIT_ACTIVATION,
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


ROLE = "v24195_lease_owner_compatibility_wait_activation_audit"
V24194_WATCHER_MARKER = "scripts/watch_v24194_capacity_ladder.py"
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
    state = read_object(root / state_path)
    rows = process_snapshot(proc_root)
    compatibility = process_report(rows, WATCHER_MARKER)
    capacity = process_report(rows, V24194_WATCHER_MARKER)
    forward = process_report(rows, R1_FORWARD_MARKER)
    launcher = process_report(rows, R1_LAUNCHER_MARKER)
    successor = process_report(rows, EXECUTOR_MARKER)
    if (
        state.get("role") != "v24195_lease_owner_compatibility_audit"
        or state.get("protocol", {}).get("sha256") != verified["sha256"]
        or state.get("compatibility", {}).get("mode")
        != "parent_authoritative_inactive_lease"
        or state.get("compatibility", {}).get("registered_successor_active")
        is not False
        or state.get("compatibility", {}).get(
            "suppressed_expected_parent_findings"
        )
        != []
        or state.get("shared_api_lease", {}).get("active") is not False
        or state.get("shared_api_lease", {}).get("ordinary") is not True
        or state.get("critical_findings") != []
        or state.get("source_policy", {}).get(
            "runtime_task_question_answer_evidence_prediction_or_url_opened"
        )
        is not False
        or state.get("source_policy", {}).get(
            "mapping_gold_category_question_type_evaluator_or_score_read"
        )
        is not False
        or state.get("source_policy", {}).get("network_or_api_called") is not False
        or state.get("authorization", {}).get("shared_api_lease_acquire") is not False
        or state.get("authorization", {}).get("execution_activation_publish")
        is not False
        or state.get("authorization", {}).get("benchmark_forward_or_full220_launch")
        is not False
        or state.get("claims", {}).get("benchmark_score_available") is not False
        or state.get("claims", {}).get("sota") is not False
        or state.get("audit_payload_sha256")
        != payload_sha(
            {key: value for key, value in state.items() if key != "audit_payload_sha256"}
        )
        or compatibility["match_count"] != 1
        or capacity["match_count"] != 1
        or forward["match_count"] != 1
        or launcher["match_count"] != 1
        or successor["match_count"] != 0
        or (root / V24196_ACTIVATION).exists()
        or (root / V24196_ACTIVATION).is_symlink()
    ):
        raise RuntimeError("V2.41.95 wait-only activation boundary is invalid")
    pids = {
        "compatibility_watcher": compatibility["pids"][0],
        "v24194_capacity_watcher": capacity["pids"][0],
        "r1_forward": forward["pids"][0],
        "r1_launcher": launcher["pids"][0],
    }
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
            "compatibility_mode": state["compatibility"]["mode"],
            "overall_status": state["overall_status"],
        },
        "processes": {
            name: {"pid": pid, "start_ticks": _start_ticks(proc_root, pid)}
            for name, pid in pids.items()
        }
        | {"command_lines_emitted": False},
        "boundary": {
            "healthy_running_benchmark_and_watchers_preserved": True,
            "compatibility_watcher_exactly_one": True,
            "successor_executor_absent": True,
            "successor_activation_absent": True,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_or_evaluator_api_called": False,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "authorization": {
            "wait_only_compatibility_active": True,
            "capacity_execution_active": False,
            "future_successor_requires_new_frozen_protocol_and_activation": True,
            "future_all220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha(value)
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
    target = target if target.is_absolute() else root / target
    if target.resolve(strict=False) != (root / WAIT_ACTIVATION).resolve(strict=False):
        raise RuntimeError("V2.41.95 activation output path drifted")
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
