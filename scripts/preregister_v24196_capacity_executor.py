#!/usr/bin/env python3
"""Freeze a V2.41.94-compatible executor behind V2.41.95 liveness."""

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

from deepwide_agent.v24194_capacity_ladder import (  # noqa: E402
    payload_sha256,
    settings_from_dict,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)


ROLE = "v24196_capacity_executor_preregistration"
PROTOCOL_ID = "v24196_v24194_capacity_executor_successor_v1"
OUTPUT = Path("results/v24196_capacity_executor_preregistration_v1_20260731.json")
STATE = Path("outputs/v24196_capacity_executor_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24196_capacity_executor_activation_v1_20260731.json")
REPORT = Path("results/v24196_capacity_ladder_report_v1_20260731.json")
FREEZE = Path("results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json")
WAIT_AUDIT = Path("results/v24196_capacity_executor_wait_activation_audit_v1_20260731.json")
WATCHER_MARKER = "scripts/watch_v24196_capacity_executor.py"
LEGACY_CAPACITY_WATCHER_MARKER = "scripts/watch_v24194_capacity_ladder.py"
PROTECTED_PROCESS_MARKERS = {
    "v24187_phase_watcher": "scripts/watch_v24187_phase_liveness.py",
    "v24194_capacity_watcher": LEGACY_CAPACITY_WATCHER_MARKER,
    "v24195_compatibility_watcher": (
        "scripts/watch_v24195_lease_owner_compatibility.py"
    ),
    "r1_forward": "scripts/run_deepwide_agent.py",
    "r1_launcher": "scripts/launch_frozen_deepwide.py",
}
V24194_PROTOCOL = Path(
    "results/v24194_capacity_ladder_preregistration_v1_20260731.json"
)
V24194_PROTOCOL_SHA256 = (
    "5da63416e800a73afa49ae479351f83e30892947e987e5d390011b02face4681"
)
V24195_PROTOCOL = Path(
    "results/v24195_lease_owner_compatibility_preregistration_v1_20260731.json"
)
V24195_PROTOCOL_SHA256 = (
    "60d431acda5a95a0ee8d5ea75b970fcdd42ca3190d6d6e6c6b30a0e79978b4d7"
)
V24195_STATE = Path(
    "outputs/v24195_lease_owner_compatibility_watcher_state_v1_20260731.json"
)
R1_STATE = Path("outputs/v24118_r1_finalization_watchdog_state_v1_20260728.json")
V24194_STATE = Path("outputs/v24194_capacity_ladder_watcher_state_v1_20260731.json")
LEASE_OWNER = "v24194_neutral_gpt56_capacity_ladder_v1"
LEASE_PURPOSE = "neutral_capacity_for_next_fresh_all220_freeze"

FROZEN_EVIDENCE = {
    str(V24194_PROTOCOL): V24194_PROTOCOL_SHA256,
    str(V24195_PROTOCOL): V24195_PROTOCOL_SHA256,
    "results/v24194_capacity_ladder_wait_activation_audit_v1_20260731.json": (
        "0cd11a6e60aa2fa25cc7b9adbc3b33f6e3988df32f5dc001c79c37043825b548"
    ),
    "results/v24195_lease_owner_compatibility_wait_activation_audit_v1_20260731.json": (
        "d2959a0123d0778b4b09e540371440ff93ffcebc9039b0aeadb982e54039ac6a"
    ),
    "scripts/deepwide_api_lease.py": (
        "8d9cffa78617b458172307d3558c76e9370f045f531c2f5aaaceb866f5a78c7d"
    ),
    "src/deepwide_agent/v24194_capacity_ladder.py": (
        "a2cf25db534dbdf9b44a39a2bb0d7160d8e46e0be466376e0eab50a7c38354be"
    ),
    "src/deepwide_agent/clients.py": (
        "339d923973f07ebcd33cb12cee2c26103df70ed3aea1fc0a737ffd675ac06fbc"
    ),
}
CONTROL_FILES = (
    "scripts/preregister_v24196_capacity_executor.py",
    "scripts/watch_v24196_capacity_executor.py",
    "scripts/activate_v24196_capacity_executor.py",
    "scripts/audit_v24196_capacity_executor_wait_activation.py",
    "tests/test_preregister_v24196_capacity_executor.py",
    "tests/test_watch_v24196_capacity_executor.py",
    "tests/test_activate_v24196_capacity_executor.py",
    "tests/test_audit_v24196_capacity_executor_wait_activation.py",
)
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
DECISION_FIELDS = (
    "protocol_id",
    "parents",
    "frozen_evidence",
    "capacity_contract",
    "release_and_compatibility_gate",
    "execution",
    "source_policy",
    "authorization",
    "control_surface",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ordinary(root: Path, relative: str | Path, digest: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.96 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or root not in (path, *path.parents)
    ):
        raise RuntimeError(f"V2.41.96 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.41.96 frozen evidence drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.41.96 expected an ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.96 expected a JSON object")
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


def _successor_process_absent(proc_root: Path = Path("/proc")) -> bool:
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (
            script == WATCHER_MARKER or script.endswith("/" + WATCHER_MARKER)
        ):
            return False
    return True


def _start_ticks(proc_root: Path, pid: int) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.41.96 process stat is truncated")
    return int(suffix[19])


def _protected_processes(proc_root: Path) -> dict[str, Any]:
    rows = process_snapshot(proc_root)
    records: dict[str, Any] = {}
    for name, marker in PROTECTED_PROCESS_MARKERS.items():
        matches: list[int] = []
        isolated = 0
        for row in rows:
            argv = [str(value) for value in row.get("argv") or []]
            script = actual_python_script(argv)
            if script is not None and (
                script == marker or script.endswith("/" + marker)
            ):
                matches.append(int(row["pid"]))
                isolated += int("-I" in argv and "-B" in argv)
        require_isolated = name in {
            "v24187_phase_watcher",
            "v24194_capacity_watcher",
            "v24195_compatibility_watcher",
        }
        if len(matches) != 1 or (require_isolated and isolated != 1):
            raise RuntimeError(
                f"V2.41.96 protected process identity is invalid: {name}"
            )
        pid = matches[0]
        records[name] = {
            "marker": marker,
            "pid": pid,
            "start_ticks": _start_ticks(proc_root, pid),
            "python_isolated_no_bytecode_required": require_isolated,
            "command_line_emitted": False,
        }
    return records


def _safe_boundary(root: Path, proc_root: Path) -> dict[str, Any]:
    r1 = read_object(ordinary(root, R1_STATE))
    v94 = read_object(ordinary(root, V24194_STATE))
    v95 = read_object(ordinary(root, V24195_STATE))
    aggregate = r1.get("aggregate") or {}
    if (
        r1.get("role") != "v24118_r1_finalization_watchdog_state"
        or r1.get("status") != "waiting_for_r1_exact_terminal_220"
        or aggregate.get("selected") != 220
        or aggregate.get("exact_terminal_220") is not False
        or aggregate.get("terminal")
        != int(aggregate.get("completed", -1)) + int(aggregate.get("failed", -1))
        or not 0 <= int(aggregate.get("terminal", -1)) < 220
        or r1.get("mapping_or_gold_read") is not False
        or r1.get("evaluator_or_score_read") is not False
        or r1.get("benchmark_forward_api_called") is not False
        or v94.get("role") != "v24194_capacity_ladder_watcher_state"
        or v94.get("status") != "waiting_for_r1_release"
        or v94.get("shared_api_lease_acquired") is not False
        or v94.get("neutral_capacity_model_api_called") is not False
        or v95.get("role") != "v24195_lease_owner_compatibility_audit"
        or v95.get("overall_status")
        not in {"healthy", "degraded_forward_healthy_manual_review_only"}
        or v95.get("critical_findings") != []
        or v95.get("compatibility", {}).get("mode")
        != "parent_authoritative_inactive_lease"
        or v95.get("shared_api_lease", {}).get("active") is not False
        or not _successor_process_absent(proc_root)
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (OUTPUT, STATE, ACTIVATION, REPORT, FREEZE, WAIT_AUDIT)
        )
    ):
        raise RuntimeError("V2.41.96 safe wait-only boundary is invalid")
    return {
        "r1_status": r1["status"],
        "r1_terminal": aggregate["terminal"],
        "v24194_status": v94["status"],
        "v24195_mode": v95["compatibility"]["mode"],
        "shared_api_lease_active": False,
        "successor_process_and_outputs_absent": True,
        "protected_processes": _protected_processes(proc_root),
    }


def _parents(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = {
        relative: {"sha256": sha256(ordinary(root, relative, digest))}
        for relative, digest in FROZEN_EVIDENCE.items()
    }
    v94 = read_object(root / V24194_PROTOCOL)
    v95 = read_object(root / V24195_PROTOCOL)
    if (
        v94.get("protocol_id") != "v24194_neutral_gpt56_capacity_ladder_v1"
        or v94.get("execution", {}).get("shared_lease_owner") != LEASE_OWNER
        or v94.get("execution", {}).get("shared_lease_purpose") != LEASE_PURPOSE
        or v95.get("protocol_id") != "v24195_v24194_lease_owner_compatibility_v1"
        or v95.get("compatibility_contract", {}).get("registered_owner")
        != LEASE_OWNER
        or v95.get("compatibility_contract", {}).get("registered_purpose")
        != LEASE_PURPOSE
    ):
        raise RuntimeError("V2.41.96 frozen parent semantics drifted")
    parents = {
        "v24195_compatibility": {
            "path": str(V24195_PROTOCOL),
            "sha256": V24195_PROTOCOL_SHA256,
        },
        "v24194_capacity": {
            "path": str(V24194_PROTOCOL),
            "sha256": V24194_PROTOCOL_SHA256,
        },
    }
    return parents, evidence


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.96 may only freeze the canonical workspace")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.96 unattested Python bootstrap path appeared")
    parents, evidence = _parents(root)
    parent_capacity = read_object(root / V24194_PROTOCOL)
    contract = parent_capacity["capacity_contract"]
    settings = settings_from_dict(contract["settings"])
    settings.validate()
    boundary = _safe_boundary(root, proc_root) if require_pristine else {
        "r1_status": "waiting_for_r1_exact_terminal_220",
        "r1_terminal": 0,
        "v24194_status": "waiting_for_r1_release",
        "v24195_mode": "parent_authoritative_inactive_lease",
        "shared_api_lease_active": False,
        "successor_process_and_outputs_absent": True,
        "protected_processes": {},
    }
    manifest = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "parents": parents,
        "frozen_evidence": evidence,
        "capacity_contract": {
            "settings": settings.as_dict(),
            "settings_sha256": payload_sha256(settings.as_dict()),
            "endpoint": contract["endpoint"],
            "model": contract["model"],
            "reasoning_effort": contract["reasoning_effort"],
            "service_tier": contract["service_tier"],
            "request_timeout_seconds": contract["request_timeout_seconds"],
            "client_max_retries": contract["client_max_retries"],
            "first_attempt_exact_nontruncated_success_required": True,
            "stop_at_first_unsafe_level": True,
            "selected_level_is_highest_consecutive_safe_level": True,
            "fixed_selected_concurrency_for_entire_future_all220": True,
            "inherited_v24194_contract_exact": True,
        },
        "release_and_compatibility_gate": {
            "r1_exact220_release_required": True,
            "quality_campaign_terminal_required": True,
            "active_api_workers_absent_required": True,
            "legacy_v24194_watcher_absent_before_lease_required": True,
            "legacy_v24194_watcher_may_not_be_signaled_or_restarted": True,
            "quiet_observations_before_lease": 2,
            "execution_activation_required": True,
            "post_lease_v24195_live_compatibility_required": True,
            "post_lease_v24195_watcher_observation_required": True,
            "post_lease_parent_only_expected_owner_finding_required": True,
            "post_lease_compatibility_timeout_seconds": 45,
            "safe_wait_boundary": boundary,
        },
        "execution": {
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "proc_root": "/proc",
            "watcher_marker": WATCHER_MARKER,
            "protected_legacy_capacity_watcher_marker": (
                LEGACY_CAPACITY_WATCHER_MARKER
            ),
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "report_path": str(REPORT),
            "freeze_path": str(FREEZE),
            "wait_audit_path": str(WAIT_AUDIT),
            "shared_lease_owner": LEASE_OWNER,
            "shared_lease_purpose": LEASE_PURPOSE,
            "v24195_state_path": str(V24195_STATE),
            "active_api_worker_markers": list(
                parent_capacity["execution"]["active_api_worker_markers"]
            ),
        },
        "source_policy": {
            "safe_r1_phase_v24195_envelopes_and_proc_identity_only": True,
            "released_result_bytes_hashed_for_seal_but_not_parsed": True,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "runtime_task_state_answer_evidence_or_url_opened": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "neutral_payload_only_after_all_gates": True,
            "search_fetch_or_evaluator_api_called": False,
            "response_text_or_response_id_persisted": False,
        },
        "authorization": {
            "wait_only_before_exact220_release_and_activation": True,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "current_r1_or_quality_chain_forward_config_change": False,
            "network_model_api_before_all_gates": False,
            "network_model_api_under_registered_shared_lease_only": True,
            "neutral_capacity_measurement_after_all_gates": True,
            "future_all220_freeze_generation_after_measurement": True,
            "future_all220_launch": False,
            "benchmark_forward_or_evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha(manifest),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
        },
    }
    value["decision_contract_sha256"] = payload_sha(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    if (
        raw.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or raw.is_symlink()
        or not raw.is_file()
    ):
        raise RuntimeError("V2.41.96 protocol path is noncanonical")
    value = read_object(raw)
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or value.get("parents", {}).get("v24195_compatibility")
        != {"path": str(V24195_PROTOCOL), "sha256": V24195_PROTOCOL_SHA256}
        or value.get("parents", {}).get("v24194_capacity")
        != {"path": str(V24194_PROTOCOL), "sha256": V24194_PROTOCOL_SHA256}
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or control.get("file_count") != len(CONTROL_FILES)
        or control.get("manifest_sha256") != payload_sha(manifest)
        or set(control.get("must_remain_absent") or []) != set(MUST_REMAIN_ABSENT)
        or value.get("decision_contract_sha256")
        != payload_sha({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.41.96 protocol contract is invalid")
    _parents(root)
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.41.96 control surface drifted")
    return {"path": raw, "sha256": sha256(raw), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.41.96 output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
