#!/usr/bin/env python3
"""Bind V2.42.17 to one isolated capacity-successor watcher."""

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

from deepwide_agent.v24217_capacity_successor import payload_sha256  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    _start_ticks,
    publish_new,
    sha256,
)
from scripts.preregister_v24217_capacity_successor import (  # noqa: E402
    ACTIVATION,
    LEASE_OWNER,
    LEASE_PURPOSE,
    OUTPUT,
    WATCHER_MARKER,
    validate_protocol,
)


ROLE = "v24217_capacity_successor_activation"


def _watcher(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matches = []
    for row in rows:
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (
            script == WATCHER_MARKER or script.endswith("/" + WATCHER_MARKER)
        ):
            matches.append(
                {
                    "pid": int(row["pid"]),
                    "isolated": all(flag in argv for flag in ("-I", "-B")),
                }
            )
    if len(matches) != 1 or matches[0]["isolated"] is not True:
        raise RuntimeError("V2.42.17 watcher process identity is invalid")
    return matches[0]


def build_activation(
    root: Path = ROOT,
    *,
    protocol_path: Path = OUTPUT,
    proc_root: Path = Path("/proc"),
    created_at_unix: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    verified = validate_protocol(root, protocol_path)
    watcher = _watcher(process_snapshot(proc_root))
    pid = watcher["pid"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "activation_valid": True,
        "protocol": {"path": str(OUTPUT), "sha256": verified["sha256"]},
        "watcher": {
            "marker": WATCHER_MARKER,
            "pid": pid,
            "start_ticks": _start_ticks(proc_root, pid),
            "python_isolated_no_bytecode": True,
        },
        "registered_shared_lease_owner": LEASE_OWNER,
        "registered_shared_lease_purpose": LEASE_PURPOSE,
        "parent_safe_state_envelope_read_allowed": True,
        "neutral_capacity_only_after_parent_go_and_two_quiet_observations": True,
        "legacy_capacity_watchers_preserved_without_signal_restart_or_modification": True,
        "execution_start_required_before_client_or_api": True,
        "retry_resume_or_selective_rerun_allowed": False,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "search_fetch_or_evaluator_api_call_allowed": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def validate_activation(
    root: Path,
    path: Path = ACTIVATION,
    *,
    protocol_path: Path = OUTPUT,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    target = path if path.is_absolute() else root / path
    value = (
        json.loads(target.read_text(encoding="utf-8"))
        if target.is_file() and not target.is_symlink()
        else None
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.17 activation path is noncanonical")
    verified = validate_protocol(root, protocol_path)
    live = _watcher(process_snapshot(proc_root))
    watcher = value.get("watcher") or {}
    unsigned = dict(value)
    seal = unsigned.pop("activation_payload_sha256", None)
    false_fields = (
        "retry_resume_or_selective_rerun_allowed",
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read",
        "search_fetch_or_evaluator_api_call_allowed",
        "benchmark_forward_or_full220_launch_allowed",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "leaderboard_submission_or_sota_claim",
    )
    if (
        target.resolve(strict=False) != (root / ACTIVATION).resolve(strict=False)
        or value.get("role") != ROLE
        or value.get("activation_valid") is not True
        or value.get("protocol")
        != {"path": str(OUTPUT), "sha256": verified["sha256"]}
        or watcher.get("marker") != WATCHER_MARKER
        or watcher.get("pid") != live["pid"]
        or watcher.get("start_ticks") != _start_ticks(proc_root, live["pid"])
        or watcher.get("python_isolated_no_bytecode") is not True
        or value.get("registered_shared_lease_owner") != LEASE_OWNER
        or value.get("registered_shared_lease_purpose") != LEASE_PURPOSE
        or value.get("neutral_capacity_only_after_parent_go_and_two_quiet_observations")
        is not True
        or value.get("execution_start_required_before_client_or_api") is not True
        or any(value.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.17 activation contract is invalid")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ACTIVATION))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / ACTIVATION).resolve(strict=False):
        raise RuntimeError("V2.42.17 activation output drifted")
    publish_new(target, build_activation())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
