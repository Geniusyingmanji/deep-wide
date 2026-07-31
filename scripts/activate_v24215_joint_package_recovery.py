#!/usr/bin/env python3
"""Bind V2.42.15 to one isolated recovery watcher."""

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

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    _start_ticks,
    publish_new,
    sha256,
)
from scripts.preregister_v24215_joint_package_recovery import (  # noqa: E402
    ACTIVATION,
    FAILED_AUDIT_PATH,
    FAILED_AUDIT_SHA256,
    OUTPUT,
    WATCHER_MARKER,
    validate_protocol,
)


ROLE = "v24215_selected_joint_package_recovery_activation"


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
        raise RuntimeError("V2.42.15 watcher process identity is invalid")
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
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "activation_valid": True,
        "protocol": {"path": str(OUTPUT), "sha256": verified["sha256"]},
        "recovery_parent": {
            "path": FAILED_AUDIT_PATH,
            "sha256": FAILED_AUDIT_SHA256,
        },
        "watcher": {
            "marker": WATCHER_MARKER,
            "pid": pid,
            "start_ticks": _start_ticks(proc_root, pid),
            "python_isolated_no_bytecode": True,
        },
        "parent_safe_state_envelope_read_allowed": True,
        "selected_content_read_only_after_parent_terminal": True,
        "corrected_single_deepest_graph_publication_allowed_after_parent_terminal": True,
        "v24214_namespace_reuse_overwrite_resume_or_retry_allowed": False,
        "component_directory_overlay_allowed": False,
        "package_gate_evaluation_or_launch_allowed": False,
        "dev64_launch_allowed": False,
        "shared_api_lease_acquire_allowed": False,
        "network_model_search_fetch_evaluator_or_api_call_allowed": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
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
        raise RuntimeError("V2.42.15 activation path is noncanonical")
    verified = validate_protocol(root, protocol_path)
    live = _watcher(process_snapshot(proc_root))
    watcher = value.get("watcher") or {}
    unsigned = {
        key: item for key, item in value.items() if key != "activation_payload_sha256"
    }
    false_fields = (
        "v24214_namespace_reuse_overwrite_resume_or_retry_allowed",
        "component_directory_overlay_allowed",
        "package_gate_evaluation_or_launch_allowed",
        "dev64_launch_allowed",
        "shared_api_lease_acquire_allowed",
        "network_model_search_fetch_evaluator_or_api_call_allowed",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
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
        or value.get("recovery_parent")
        != {"path": FAILED_AUDIT_PATH, "sha256": FAILED_AUDIT_SHA256}
        or watcher.get("marker") != WATCHER_MARKER
        or watcher.get("pid") != live["pid"]
        or watcher.get("start_ticks") != _start_ticks(proc_root, live["pid"])
        or watcher.get("python_isolated_no_bytecode") is not True
        or value.get("selected_content_read_only_after_parent_terminal") is not True
        or any(value.get(field) is not False for field in false_fields)
        or value.get("activation_payload_sha256") != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.15 activation contract is invalid")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ACTIVATION))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / ACTIVATION).resolve(strict=False):
        raise RuntimeError("V2.42.15 activation output drifted")
    publish_new(target, build_activation())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
