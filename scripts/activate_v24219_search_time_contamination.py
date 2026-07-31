#!/usr/bin/env python3
"""Bind one isolated watcher to the V2.42.19 frozen audit protocol."""

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
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24219_search_time_contamination import payload_sha256  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24219_search_time_contamination import (  # noqa: E402
    ACTIVATION,
    PROTOCOL,
    STATE,
    _publish_new,
    validate_protocol,
)


WATCHER = "scripts/watch_v24219_search_time_contamination.py"


def _start_ticks(proc_root: Path, pid: int) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.42.19 process stat is truncated")
    return int(suffix[19])


def _watcher(rows: list[dict[str, Any]], proc_root: Path = Path("/proc")) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for row in rows:
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (script == WATCHER or script.endswith("/" + WATCHER)):
            matches.append({"pid": int(row["pid"]), "argv": argv})
    if len(matches) != 1 or not all(flag in matches[0]["argv"] for flag in ("-I", "-B")):
        raise RuntimeError("V2.42.19 watcher process identity is invalid")
    pid = matches[0]["pid"]
    return {
        "marker": WATCHER,
        "pid": pid,
        "start_ticks": _start_ticks(proc_root, pid),
        "python_isolated_no_bytecode": True,
        "command_line_emitted": False,
    }


def build_activation(
    root: Path = ROOT, *, created_at_unix: int | None = None, proc_root: Path = Path("/proc")
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.19 activation boundary drifted")
    verified = validate_protocol(root, PROTOCOL)
    _validate_preactivation_state(root, verified["sha256"])
    watcher = _watcher(process_snapshot(proc_root), proc_root)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24219_search_time_contamination_activation",
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "protocol": {"path": str(PROTOCOL), "sha256": verified["sha256"]},
        "watcher": watcher,
        "parent_state_or_result_opened_before_activation": False,
        "post_terminal_label_blind_offline_audit_only": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "shared_api_lease_acquired": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def _validate_preactivation_state(root: Path, protocol_sha: str) -> None:
    path = root / STATE
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.19 preactivation state is noncanonical")
    state = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "parent_safe_state_envelope_opened",
        "parent_terminal_result_and_barrier_validated",
        "task_manifest_or_evidence_opened",
        "audit_started",
        "report_created",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "network_model_search_fetch_evaluator_or_api_called",
        "shared_api_lease_acquired",
        "forward_result_evaluator_or_watcher_modified",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    if (
        state.get("role") != "v24219_search_time_contamination_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol_sha
        or state.get("execution_activation") is not None
        or state.get("status") != "waiting_for_execution_activation"
        or state.get("reason") != "activation_absent"
        or any(state.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.19 preactivation state is unsafe")


def validate_activation(
    root: Path = ROOT,
    path: Path = ACTIVATION,
    *,
    protocol_path: Path = PROTOCOL,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    target = root / path
    if target.is_symlink() or not target.is_file():
        raise RuntimeError("V2.42.19 activation is not an ordinary file")
    observed = json.loads(target.read_text(encoding="utf-8"))
    unsigned = dict(observed)
    seal = unsigned.pop("activation_payload_sha256", None)
    protocol = validate_protocol(root, protocol_path)
    watcher = observed.get("watcher") or {}
    live = _watcher(process_snapshot(proc_root), proc_root)
    if (
        observed.get("role") != "v24219_search_time_contamination_activation"
        or observed.get("protocol") != {"path": str(PROTOCOL), "sha256": protocol["sha256"]}
        or seal != payload_sha256(unsigned)
        or watcher.get("marker") != WATCHER
        or watcher.get("pid") != live["pid"]
        or watcher.get("start_ticks") != live["start_ticks"]
        or watcher.get("python_isolated_no_bytecode") is not True
        or observed.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.42.19 activation is invalid")
    return {
        "value": observed,
        "sha256": __import__("hashlib").sha256(target.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ACTIVATION))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / ACTIVATION).resolve(strict=False):
        raise RuntimeError("V2.42.19 activation output drifted")
    value = build_activation()
    _publish_new(target, value)
    print(json.dumps({"path": str(target), "watcher_pid": value["watcher"]["pid"]}))


if __name__ == "__main__":
    main()
