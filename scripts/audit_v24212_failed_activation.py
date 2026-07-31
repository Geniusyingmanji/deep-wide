#!/usr/bin/env python3
"""Seal the fail-closed first V2.42.12 activation without retrying it."""

from __future__ import annotations

import argparse
import hashlib
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

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24212_entropy_component import (  # noqa: E402
    ACTIVATION,
    OUTPUT as PROTOCOL,
    PUBLICATION,
    STATE,
    WATCHER_MARKER,
    protected_processes,
    publish_new,
    sha256,
    validate_protocol,
)
from scripts.publish_v24212_entropy_component import (  # noqa: E402
    ACTION_MODEL,
    CANDIDATE_ROOT,
    GATE2A_REPORT,
)


OUTPUT = Path("results/v24212_selected_entropy_component_failed_activation_audit_v1_20260731.json")
LOG = Path("outputs/v24212_selected_entropy_component_watcher_v1_20260731.log")
EXPECTED_ERROR = "RuntimeError: V2.42.12 search-parent safe envelope drifted"


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.12 failure audit expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.12 failure audit expected one JSON object")
    return value


def _watcher_pids() -> list[int]:
    pids: list[int] = []
    for row in process_snapshot():
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (
            script == WATCHER_MARKER or script.endswith("/" + WATCHER_MARKER)
        ):
            pids.append(int(row["pid"]))
    return sorted(pids)


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, PROTOCOL)
    activation = _read_object(root / ACTIVATION)
    state = _read_object(root / STATE)
    activation_unsigned = dict(activation)
    activation_seal = activation_unsigned.pop("activation_payload_sha256", None)
    state_unsigned = dict(state)
    state_seal = state_unsigned.pop("state_payload_sha256", None)
    log_path = root / LOG
    if log_path.is_symlink() or not log_path.is_file():
        raise RuntimeError("V2.42.12 failure log is unavailable")
    log = log_path.read_text(encoding="utf-8")
    frozen_processes = protocol["value"]["safe_wait_boundary"][
        "protected_processes"
    ]
    live_processes = protected_processes()
    if (
        activation.get("role")
        != "v24212_selected_entropy_component_activation"
        or activation.get("activation_valid") is not True
        or activation.get("protocol")
        != {"path": str(PROTOCOL), "sha256": protocol["sha256"]}
        or activation.get("shared_api_lease_acquire_allowed") is not False
        or activation.get("network_model_search_fetch_evaluator_or_api_call_allowed")
        is not False
        or activation.get("benchmark_forward_or_full220_launch_allowed") is not False
        or activation_seal != payload_sha256(activation_unsigned)
        or state.get("role")
        != "v24212_selected_entropy_component_watcher_state"
        or state.get("status") != "waiting_for_execution_activation"
        or state.get("reason") != "activation_absent"
        or state.get("terminal") is not False
        or state.get("selected_work_order_opened") is not False
        or state.get("gate2a_report_opened") is not False
        or state.get("action_model_opened") is not False
        or state.get("shared_api_lease_acquired") is not False
        or state.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state_seal != payload_sha256(state_unsigned)
        or EXPECTED_ERROR not in log
        or _watcher_pids()
        or live_processes != frozen_processes
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (PUBLICATION, GATE2A_REPORT, ACTION_MODEL)
        )
        or CANDIDATE_ROOT.exists()
        or CANDIDATE_ROOT.is_symlink()
    ):
        raise RuntimeError("V2.42.12 failed-activation boundary drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24212_selected_entropy_component_failed_activation_audit",
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "protocol": {"path": str(PROTOCOL), "sha256": protocol["sha256"]},
        "activation": {
            "path": str(ACTIVATION),
            "sha256": sha256(root / ACTIVATION),
            "watcher_pid": activation["watcher"]["pid"],
            "watcher_start_ticks": activation["watcher"]["start_ticks"],
        },
        "last_state": {
            "path": str(STATE),
            "sha256": sha256(root / STATE),
            "status": state["status"],
            "contents_emitted": False,
        },
        "failure": {
            "classification": "successor_envelope_field_name_mismatch_fail_closed",
            "expected_upstream_field": "mapping_gold_category_question_type_evaluator_score_or_reward_read",
            "mistaken_successor_field": "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing",
            "exception_type": "RuntimeError",
            "exception_message_sha256": hashlib.sha256(
                EXPECTED_ERROR.encode()
            ).hexdigest(),
            "log_path": str(LOG),
            "log_sha256": sha256(log_path),
            "log_or_traceback_emitted_in_audit": False,
        },
        "disposition": {
            "original_watcher_process_absent": True,
            "original_activation_and_state_preserved": True,
            "original_activation_overwrite_or_reuse_allowed": False,
            "same_protocol_restart_or_retry_allowed": False,
            "new_versioned_recovery_protocol_required": True,
            "component_publication_absent": True,
            "candidate_root_absent": True,
            "selected_work_order_report_or_model_opened": False,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "benchmark_forward_or_full220_launch_allowed": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "protected_processes_preserved": live_processes,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.12 failure-audit path drifted")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
