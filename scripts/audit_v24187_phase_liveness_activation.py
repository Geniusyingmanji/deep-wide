#!/usr/bin/env python3
"""Audit activation of the V2.41.87 observation-only watcher."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from scripts.audit_v24187_phase_liveness import (
    CREDENTIAL_LIKE,
    OPAQUE_ID,
    actual_python_script,
    payload_sha,
    process_snapshot,
    sha256,
)
from scripts.preregister_v24187_phase_liveness import (
    DEFAULT_ACTIVATION,
    DEFAULT_PROTOCOL,
    DEFAULT_STATE,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parents[1]
ROLE = "v24187_phase_liveness_activation_audit"
MARKER = "scripts/watch_v24187_phase_liveness.py"


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.41.87 activation expected an ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.87 activation expected an object")
    return value


def _process(proc_root: Path) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script == MARKER or (script and script.endswith("/" + MARKER)):
            matches.append(row)
    return {
        "present": bool(matches),
        "match_count": len(matches),
        "pids": sorted(int(row["pid"]) for row in matches),
        "isolated_no_bytecode_count": sum(
            "-I" in (row.get("argv") or []) and "-B" in (row.get("argv") or [])
            for row in matches
        ),
        "command_lines_emitted": False,
    }


def build_activation(
    root: Path = ROOT,
    *,
    protocol_path: Path = DEFAULT_PROTOCOL,
    state_path: Path = DEFAULT_STATE,
    proc_root: Path = Path("/proc"),
    created_at_unix: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    verified = validate_protocol(root, protocol_path)
    raw_state = state_path if state_path.is_absolute() else root / state_path
    if raw_state.resolve(strict=False) != (root / DEFAULT_STATE).resolve(strict=False):
        raise RuntimeError("V2.41.87 activation state path is noncanonical")
    state = _read(raw_state)
    process = _process(proc_root)
    if (
        state.get("role") != "v24187_phase_liveness_audit"
        or state.get("protocol", {}).get("sha256") != verified["sha256"]
        or state.get("critical_findings") != []
        or state.get("overall_status")
        not in {"healthy", "degraded_forward_healthy_manual_review_only"}
        or state.get("source_policy", {}).get(
            "runtime_task_state_question_answer_evidence_or_prediction_rows_opened"
        )
        is not False
        or state.get("source_policy", {}).get(
            "mapping_gold_category_question_type_evaluator_or_score_read"
        )
        is not False
        or state.get("source_policy", {}).get("credential_value_or_keyring_read")
        is not False
        or state.get("source_policy", {}).get("network_or_api_called") is not False
        or process["match_count"] != 1
        or process["isolated_no_bytecode_count"] != 1
    ):
        raise RuntimeError("V2.41.87 activation boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind": True,
        "protocol": {
            "path": str(verified["path"].relative_to(root)),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
            "control_manifest_sha256": verified["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
        "state": {
            "path": str(raw_state.relative_to(root)),
            "sha256": sha256(raw_state),
            "overall_status": state["overall_status"],
            "current_phase": state["current_phase"]["phase"],
            "critical_findings": [],
            "degraded_findings": state["degraded_findings"],
            "contents_emitted": False,
        },
        "watcher_process": process,
        "boundary": {
            "immutable_parent_and_control_bytes_live_revalidated": True,
            "current_phase_safe_state_fresh_and_executor_unique": True,
            "taxonomy_manual_review_does_not_authorize_policy_change": True,
            "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read": False,
            "runtime_task_state_question_answer_evidence_or_prediction_rows_opened": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "network_model_search_fetch_evaluator_or_benchmark_api_called": False,
            "process_signal_restart_resume_rerun_skip_or_launch_performed": False,
        },
        "claims": {
            "benchmark_score_available": state["claims"]["benchmark_score_available"],
            "benchmark_improvement_observed": False,
            "avg_at_4_available": state["claims"]["avg_at_4_available"],
            "entropy_or_credit_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "activation_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if OPAQUE_ID.search(encoded) or CREDENTIAL_LIKE.search(encoded):
        raise RuntimeError("V2.41.87 activation emitted forbidden content")
    value["audit_payload_sha256"] = payload_sha(value)
    return value


def validate_activation(
    root: Path, path: Path = DEFAULT_ACTIVATION
) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    value = _read(raw)
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        raw.resolve(strict=False) != (root / DEFAULT_ACTIVATION).resolve(strict=False)
        or value.get("role") != ROLE
        or value.get("activation_valid") is not True
        or seal != payload_sha(unsigned)
    ):
        raise RuntimeError("V2.41.87 activation audit is invalid")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--output", default=str(DEFAULT_ACTIVATION))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    if output.resolve(strict=False) != (root / DEFAULT_ACTIVATION).resolve(strict=False):
        raise RuntimeError("V2.41.87 activation output path is noncanonical")
    value = build_activation(
        root,
        protocol_path=Path(args.protocol),
        state_path=Path(args.state),
        proc_root=Path(args.proc_root),
    )
    publish_new(output, value)
    print(json.dumps({"output": str(output), "sha256": sha256(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
