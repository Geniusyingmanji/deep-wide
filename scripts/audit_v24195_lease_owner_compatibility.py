#!/usr/bin/env python3
"""Audit the append-only V2.41.95 lease-owner compatibility contract."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    EXPECTED_LEASE_OWNERS,
    actual_python_script,
    build_report as build_parent_report,
    process_snapshot,
)
from scripts.preregister_v24195_lease_owner_compatibility import (  # noqa: E402
    EXECUTOR_MARKER,
    EXPECTED_PARENT_FINDING,
    LEASE,
    OUTPUT,
    REGISTERED_OWNER,
    REGISTERED_PURPOSE,
    STATE,
    V24196_ACTIVATION,
    V24196_PROTOCOL,
    ordinary,
    payload_sha,
    publish_new,
    read_object,
    sha256,
    validate_protocol,
)


ROLE = "v24195_lease_owner_compatibility_audit"
V24194_PROTOCOL = Path(
    "results/v24194_capacity_ladder_preregistration_v1_20260731.json"
)
V24194_PROTOCOL_SHA256 = (
    "5da63416e800a73afa49ae479351f83e30892947e987e5d390011b02face4681"
)
SUCCESSOR_PROTOCOL_ID = "v24196_v24194_capacity_executor_successor_v1"


def _start_ticks(proc_root: Path, pid: int) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.41.95 process stat is truncated")
    return int(suffix[19])


def _lock_holders(path: Path, proc_root: Path) -> list[int]:
    stat = path.stat()
    identity = f"{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}:{stat.st_ino}"
    holders: set[int] = set()
    locks = proc_root / "locks"
    try:
        lines = locks.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        fields = line.split()
        if len(fields) >= 6 and fields[1] == "FLOCK" and fields[5] == identity:
            try:
                holders.add(int(fields[4]))
            except ValueError:
                continue
    return sorted(holders)


def lease_observation(root: Path, proc_root: Path) -> dict[str, Any]:
    path = root / LEASE
    if not path.exists() and not path.is_symlink():
        return {
            "present": False,
            "active": False,
            "ordinary": True,
            "record_valid": True,
            "owner": None,
            "purpose": None,
            "pid": None,
            "lock_holder_pids": [],
        }
    if path.is_symlink() or not path.is_file():
        return {
            "present": True,
            "active": None,
            "ordinary": False,
            "record_valid": False,
            "owner": None,
            "purpose": None,
            "pid": None,
            "lock_holder_pids": [],
        }
    with path.open("r", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            active = True
        else:
            active = False
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.seek(0)
        try:
            value = json.loads(handle.read(4096) or "{}")
        except json.JSONDecodeError:
            value = {}
    if not isinstance(value, dict):
        value = {}
    pid = value.get("pid")
    owner = value.get("owner")
    purpose = value.get("purpose")
    record_valid = bool(
        not active
        or (
            value.get("role") == "deepwide_shared_benchmark_api_lease"
            and value.get("label_blind") is True
            and value.get(
                "benchmark_question_prediction_mapping_gold_score_read"
            )
            is False
            and isinstance(owner, str)
            and bool(owner)
            and isinstance(purpose, str)
            and bool(purpose)
            and isinstance(pid, int)
            and not isinstance(pid, bool)
            and (proc_root / str(pid)).is_dir()
        )
    )
    return {
        "present": True,
        "active": active,
        "ordinary": True,
        "record_valid": record_valid,
        "owner": owner if active else None,
        "purpose": purpose if active else None,
        "pid": pid if active and isinstance(pid, int) else None,
        "lock_holder_pids": _lock_holders(path, proc_root) if active else [],
    }


def _successor_protocol(root: Path, compatibility_sha: str) -> dict[str, Any]:
    path = ordinary(root, V24196_PROTOCOL)
    value = read_object(path)
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("role") != "v24196_capacity_executor_preregistration"
        or value.get("protocol_id") != SUCCESSOR_PROTOCOL_ID
        or value.get("label_blind") is not True
        or value.get("parents", {}).get("v24195_compatibility")
        != {"path": str(OUTPUT), "sha256": compatibility_sha}
        or value.get("parents", {}).get("v24194_capacity")
        != {"path": str(V24194_PROTOCOL), "sha256": V24194_PROTOCOL_SHA256}
        or value.get("execution", {}).get("shared_lease_owner")
        != REGISTERED_OWNER
        or value.get("execution", {}).get("shared_lease_purpose")
        != REGISTERED_PURPOSE
        or value.get("execution", {}).get("watcher_marker") != EXECUTOR_MARKER
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != payload_sha(manifest)
    ):
        raise RuntimeError("V2.41.95 successor protocol contract is invalid")
    for relative, digest in manifest.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise RuntimeError("V2.41.95 successor control manifest is invalid")
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.41.95 successor control surface drifted")
    return {"path": path, "sha256": sha256(path), "value": value}


def _matching_processes(
    rows: list[dict[str, Any]], marker: str = EXECUTOR_MARKER
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for row in rows:
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (script == marker or script.endswith("/" + marker)):
            matches.append(
                {
                    "pid": int(row["pid"]),
                    "isolated_no_bytecode": "-I" in argv and "-B" in argv,
                }
            )
    return sorted(matches, key=lambda row: row["pid"])


def validate_successor_identity(
    root: Path,
    *,
    compatibility_sha: str,
    lease: dict[str, Any],
    proc_root: Path,
    processes: list[dict[str, Any]],
) -> dict[str, Any]:
    findings: list[str] = []
    protocol_sha: str | None = None
    activation_sha: str | None = None
    activation_pid: int | None = None
    activation_ticks: int | None = None
    try:
        protocol = _successor_protocol(root, compatibility_sha)
        protocol_sha = protocol["sha256"]
    except (KeyError, OSError, RuntimeError, ValueError):
        protocol = None
        findings.append("successor_protocol")
    try:
        activation_path = ordinary(root, V24196_ACTIVATION)
        activation = read_object(activation_path)
        activation_sha = sha256(activation_path)
    except (OSError, RuntimeError, ValueError):
        activation = None
        findings.append("successor_activation")
    if activation is not None:
        unsigned = dict(activation)
        seal = unsigned.pop("activation_payload_sha256", None)
        executor = activation.get("executor") or {}
        activation_pid = executor.get("pid")
        activation_ticks = executor.get("start_ticks")
        if (
            activation.get("role") != "v24196_capacity_executor_activation"
            or activation.get("activation_valid") is not True
            or protocol_sha is None
            or activation.get("protocol")
            != {"path": str(V24196_PROTOCOL), "sha256": protocol_sha}
            or activation.get("compatibility")
            != {"path": str(OUTPUT), "sha256": compatibility_sha}
            or activation.get("registered_shared_lease_owner")
            != REGISTERED_OWNER
            or activation.get("registered_shared_lease_purpose")
            != REGISTERED_PURPOSE
            or executor.get("marker") != EXECUTOR_MARKER
            or not isinstance(activation_pid, int)
            or isinstance(activation_pid, bool)
            or not isinstance(activation_ticks, int)
            or isinstance(activation_ticks, bool)
            or activation.get(
                "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
            )
            is not False
            or activation.get(
                "credential_value_read_persisted_hashed_or_emitted"
            )
            is not False
            or activation.get(
                "network_model_search_fetch_or_evaluator_api_called"
            )
            is not False
            or seal != payload_sha(unsigned)
        ):
            findings.append("successor_activation_contract")
    process_matches = _matching_processes(processes)
    matches = [row["pid"] for row in process_matches]
    if len(matches) != 1:
        findings.append("successor_executor_identity")
    if any(row["isolated_no_bytecode"] is not True for row in process_matches):
        findings.append("successor_executor_python_flags")
    if activation_pid is not None:
        if matches != [activation_pid]:
            findings.append("successor_executor_pid")
        try:
            live_ticks = _start_ticks(proc_root, activation_pid)
        except (OSError, RuntimeError, ValueError):
            live_ticks = None
        if live_ticks != activation_ticks:
            findings.append("successor_executor_start_ticks")
    if lease.get("owner") != REGISTERED_OWNER:
        findings.append("lease_owner")
    if lease.get("purpose") != REGISTERED_PURPOSE:
        findings.append("lease_purpose")
    if lease.get("pid") != activation_pid:
        findings.append("lease_pid")
    if lease.get("lock_holder_pids") != [activation_pid]:
        findings.append("lease_lock_holder")
    if lease.get("ordinary") is not True or lease.get("record_valid") is not True:
        findings.append("lease_record")
    findings = sorted(set(findings))
    return {
        "valid": not findings,
        "findings": findings,
        "successor_protocol_sha256": protocol_sha,
        "successor_activation_sha256": activation_sha,
        "executor_pid": activation_pid,
        "executor_start_ticks": activation_ticks,
    }


def build_report(
    root: Path = ROOT,
    protocol_path: Path = OUTPUT,
    *,
    now: int | None = None,
    freshness_seconds: int = 180,
    transition_grace_seconds: int = 180,
    proc_root: Path = Path("/proc"),
    processes: list[dict[str, Any]] | None = None,
    parent_builder: Callable[..., dict[str, Any]] = build_parent_report,
    observed_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    verified = validate_protocol(root, protocol_path)
    created = int(time.time()) if now is None else int(now)
    rows = process_snapshot(proc_root) if processes is None else processes
    lease = (
        lease_observation(root, proc_root)
        if observed_lease is None
        else dict(observed_lease)
    )
    parent = parent_builder(
        root,
        now=created,
        freshness_seconds=freshness_seconds,
        transition_grace_seconds=transition_grace_seconds,
        proc_root=proc_root,
        processes=rows,
    )
    parent_critical = list(parent.get("critical_findings") or [])
    critical = list(parent_critical)
    degraded = list(parent.get("degraded_findings") or [])
    mode = "parent_authoritative_inactive_lease"
    suppressed: list[str] = []
    identity: dict[str, Any] = {
        "valid": False,
        "findings": [],
        "successor_protocol_sha256": None,
        "successor_activation_sha256": None,
        "executor_pid": None,
        "executor_start_ticks": None,
    }
    if lease.get("active") is True:
        owner = lease.get("owner")
        if owner == REGISTERED_OWNER:
            mode = "registered_successor_active"
            identity = validate_successor_identity(
                root,
                compatibility_sha=verified["sha256"],
                lease=lease,
                proc_root=proc_root,
                processes=rows,
            )
            if identity["valid"] and EXPECTED_PARENT_FINDING in critical:
                critical.remove(EXPECTED_PARENT_FINDING)
                suppressed = [EXPECTED_PARENT_FINDING]
            elif identity["valid"]:
                critical.append("v24195:parent_expected_finding_absent")
            else:
                critical.append("v24195:registered_successor_identity_invalid")
        elif owner in EXPECTED_LEASE_OWNERS:
            mode = "frozen_parent_registered_owner_active"
        else:
            mode = "unknown_lease_owner_active"
            critical.append("v24195:unknown_lease_owner")
    elif lease.get("active") is not False or lease.get("ordinary") is not True:
        mode = "invalid_lease_observation"
        critical.append("v24195:lease_observation_invalid")
    critical = sorted(set(critical))
    degraded = sorted(set(degraded))
    result: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": created,
        "label_blind": True,
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
        "parent_v24187": {
            "role": parent.get("role"),
            "audit_payload_sha256": parent.get("audit_payload_sha256"),
            "overall_status": parent.get("overall_status"),
            "critical_findings": parent_critical,
            "degraded_findings": list(parent.get("degraded_findings") or []),
            "contents_emitted": False,
        },
        "compatibility": {
            "mode": mode,
            "registered_successor_active": mode == "registered_successor_active",
            "active_owner_matches_registered_successor": bool(
                lease.get("active") is True
                and lease.get("owner") == REGISTERED_OWNER
            ),
            "active_purpose_matches_registered_successor": bool(
                lease.get("active") is True
                and lease.get("purpose") == REGISTERED_PURPOSE
            ),
            "successor_identity_valid": identity["valid"],
            "successor_identity_findings": identity["findings"],
            "successor_protocol_sha256": identity["successor_protocol_sha256"],
            "successor_activation_sha256": identity[
                "successor_activation_sha256"
            ],
            "successor_executor_pid": identity["executor_pid"],
            "successor_executor_start_ticks": identity["executor_start_ticks"],
            "suppressed_expected_parent_findings": suppressed,
            "unrelated_parent_critical_findings_preserved": all(
                item in critical
                for item in parent_critical
                if item != EXPECTED_PARENT_FINDING
            ),
        },
        "shared_api_lease": {
            "present": lease.get("present"),
            "active": lease.get("active"),
            "ordinary": lease.get("ordinary"),
            "record_valid": lease.get("record_valid"),
            "pid": lease.get("pid") if lease.get("active") else None,
            "lock_holder_count": len(lease.get("lock_holder_pids") or []),
            "owner_purpose_hostname_or_contents_emitted": False,
        },
        "overall_status": (
            "critical_manual_audit_required_no_automatic_mutation"
            if critical
            else "degraded_forward_healthy_manual_review_only"
            if degraded
            else "healthy"
        ),
        "critical_findings": critical,
        "degraded_findings": degraded,
        "source_policy": {
            "parent_label_blind_liveness_recomputed_live": True,
            "shared_lease_metadata_lock_holder_and_proc_identity_only": True,
            "runtime_task_question_answer_evidence_prediction_or_url_opened": False,
            "mapping_gold_category_question_type_evaluator_or_score_read": False,
            "credential_value_or_keyring_read": False,
            "network_or_api_called": False,
            "process_command_lines_or_environment_emitted": False,
        },
        "authorization": {
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "shared_api_lease_acquire": False,
            "execution_activation_publish": False,
            "network_model_search_fetch_evaluator_or_api_call": False,
            "benchmark_forward_or_full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "entropy_or_credit_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "next_action": (
            "manual_read_only_audit_without_process_mutation"
            if critical
            else "continue_existing_frozen_execution"
        ),
    }
    result["audit_payload_sha256"] = payload_sha(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--output", default=str(STATE))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    target = Path(args.output)
    target = target if target.is_absolute() else root / target
    if target.resolve(strict=False) != (root / STATE).resolve(strict=False):
        raise RuntimeError("V2.41.95 audit output path drifted")
    value = build_report(
        root,
        Path(args.protocol),
        proc_root=Path(args.proc_root),
    )
    publish_new(target, value)
    print(
        json.dumps(
            {
                "path": str(target),
                "overall_status": value["overall_status"],
                "compatibility_mode": value["compatibility"]["mode"],
            }
        )
    )


if __name__ == "__main__":
    main()
