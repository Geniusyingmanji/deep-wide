#!/usr/bin/env python3
"""Bind V2.41.99 status-only selection to one isolated watcher process."""

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

from deepwide_agent.v24199_candidate_selector import payload_sha256  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24199_candidate_selector import (  # noqa: E402
    ACTIVATION,
    OUTPUT,
    PARENT_PROTOCOL,
    PARENT_PROTOCOL_SHA256,
    SELECTOR_PROTOCOL,
    WATCHER_MARKER,
    publish_new,
    sha256,
    validate_protocol,
)


ROLE = "v24199_candidate_selector_activation"


def start_ticks(proc_root: Path, pid: int) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.41.99 process stat is truncated")
    return int(suffix[19])


def _selector(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for row in rows:
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (
            script == WATCHER_MARKER or script.endswith("/" + WATCHER_MARKER)
        ):
            matches.append(
                {
                    "pid": int(row["pid"]),
                    "isolated_no_bytecode": "-I" in argv and "-B" in argv,
                }
            )
    if len(matches) != 1 or matches[0]["isolated_no_bytecode"] is not True:
        raise RuntimeError("V2.41.99 selector process identity is invalid")
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
    selector = _selector(process_snapshot(proc_root))
    pid = selector["pid"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "activation_valid": True,
        "protocol": {"path": str(OUTPUT), "sha256": verified["sha256"]},
        "selector_protocol": verified["value"]["selector_protocol"],
        "bundle_compiler_parent": {
            "path": str(PARENT_PROTOCOL),
            "sha256": PARENT_PROTOCOL_SHA256,
        },
        "selector": {
            "marker": WATCHER_MARKER,
            "pid": pid,
            "start_ticks": start_ticks(proc_root, pid),
            "python_isolated_no_bytecode": True,
        },
        "candidate_code_build_merge_or_freeze_generation_allowed": False,
        "shared_api_lease_acquire_allowed": False,
        "network_model_search_fetch_evaluator_or_api_call_allowed": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "mapping_gold_category_question_type_evaluator_score_read": False,
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
        raise RuntimeError("V2.41.99 activation path is noncanonical")
    verified = validate_protocol(root, protocol_path)
    unsigned = {
        key: item for key, item in value.items() if key != "activation_payload_sha256"
    }
    selector = value.get("selector") or {}
    live = _selector(process_snapshot(proc_root))
    pid = selector.get("pid")
    if (
        target.resolve(strict=False) != (root / ACTIVATION).resolve(strict=False)
        or value.get("role") != ROLE
        or value.get("activation_valid") is not True
        or value.get("protocol")
        != {"path": str(OUTPUT), "sha256": verified["sha256"]}
        or value.get("selector_protocol") != verified["value"]["selector_protocol"]
        or value.get("bundle_compiler_parent")
        != {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256}
        or selector.get("marker") != WATCHER_MARKER
        or live.get("pid") != pid
        or not isinstance(pid, int)
        or isinstance(pid, bool)
        or selector.get("start_ticks") != start_ticks(proc_root, pid)
        or selector.get("python_isolated_no_bytecode") is not True
        or value.get("candidate_code_build_merge_or_freeze_generation_allowed")
        is not False
        or value.get("shared_api_lease_acquire_allowed") is not False
        or value.get("network_model_search_fetch_evaluator_or_api_call_allowed")
        is not False
        or value.get("benchmark_forward_or_full220_launch_allowed") is not False
        or value.get("process_signal_restart_resume_rerun_skip_or_selective_retry")
        is not False
        or value.get("mapping_gold_category_question_type_evaluator_score_read")
        is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
        or value.get("activation_payload_sha256") != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.41.99 activation contract is invalid")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    parser.add_argument("--output", default=str(ACTIVATION))
    parser.add_argument("--proc-root", default="/proc")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    target = Path(args.output)
    target = target if target.is_absolute() else root / target
    if target.resolve(strict=False) != (root / ACTIVATION).resolve(strict=False):
        raise RuntimeError("V2.41.99 activation output path drifted")
    value = build_activation(
        root,
        protocol_path=Path(args.protocol),
        proc_root=Path(args.proc_root),
    )
    publish_new(target, value)
    validate_activation(
        root,
        target,
        protocol_path=Path(args.protocol),
        proc_root=Path(args.proc_root),
    )
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
