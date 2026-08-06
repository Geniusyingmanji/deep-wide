#!/usr/bin/env python3
"""Seal the effect-free V2.46.79 launch failure and revoke its start."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24679_schema_dev64_contract as contract  # noqa: E402
from scripts import v24679_schema_dev64_control as old_control  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260806"
FAILURE = Path(f"results/v24681_v24679_zero_effect_start_failure_v1_{DATE}.json")
LOG = Path(f"outputs/v24679_schema_dev64_runner_v1_{DATE}.log")
RUNNER = Path("scripts/run_v24679_schema_dev64.py")
SESSION = "deepwide-v24679-schema-dev64-v1"
EXPECTED_ERROR = "NameError: name 'FORWARD_AUDIT' is not defined"


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == contract.payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _active(marker: str) -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        marker in line
        for line in completed.stdout.splitlines()
        if "ps -eo" not in line and "audit_v24681" not in line
    )


def _session_absent() -> bool:
    return subprocess.run(
        ["tmux", "has-session", "-t", SESSION],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0


def _missing_binding_before_lease(source: str) -> bool:
    tree = ast.parse(source)
    imported: set[str] = set()
    used_lines: list[int] = []
    lease_lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.update(alias.asname or alias.name for alias in node.names)
        if isinstance(node, ast.Name) and node.id == "FORWARD_AUDIT":
            used_lines.append(node.lineno)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "acquire_deepwide_api_lease"
        ):
            lease_lines.append(node.lineno)
    return (
        "FORWARD_AUDIT" not in imported
        and bool(used_lines)
        and bool(lease_lines)
        and min(used_lines) < min(lease_lines)
    )


def build_receipt(*, now: int | None = None) -> dict[str, Any]:
    root = ROOT.resolve()
    forward = contract.validate_forward_contract(root)
    start = old_control.validate_execution_start(root)
    log_path = root / LOG
    runner_path = root / RUNNER
    if (
        log_path.is_symlink()
        or not log_path.is_file()
        or runner_path.is_symlink()
        or not runner_path.is_file()
    ):
        raise RuntimeError("V2.46.81 expected ordinary failure evidence")
    log = log_path.read_text(encoding="utf-8")
    source = runner_path.read_text(encoding="utf-8")
    lease = lease_observation(root, Path("/proc"))
    surfaces = {
        "output_root_absent": not (root / contract.OUTPUT_ROOT).exists()
        and not (root / contract.OUTPUT_ROOT).is_symlink(),
        "forward_result_absent": not (root / contract.FORWARD_RESULT).exists()
        and not (root / contract.FORWARD_RESULT).is_symlink(),
        "forward_audit_absent": not (root / contract.FORWARD_AUDIT).exists()
        and not (root / contract.FORWARD_AUDIT).is_symlink(),
    }
    active = _active(contract.RUNNER_MARKER) or _active(contract.CHILD_MARKER)
    source_proves_prelease = _missing_binding_before_lease(source)
    error_exact = EXPECTED_ERROR in log and "root / FORWARD_AUDIT" in log
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    watchers = contract.protected_watcher_snapshot()
    findings: list[str] = []
    if not error_exact:
        findings.append("unexpected_start_failure")
    if not source_proves_prelease:
        findings.append("missing_binding_order_not_proven")
    if not all(surfaces.values()):
        findings.append("forward_effect_surface_present")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v24679_process_still_active")
    if not _session_absent():
        findings.append("v24679_tmux_session_still_active")
    if watchers != forward["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if head != remote:
        findings.append("failure_audit_source_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    value = {
        "artifact_version": 1,
        "role": "v24681_v24679_zero_effect_start_failure",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "failure": {
            "stage": "runner_prelease_surface_preflight",
            "exception_type": "NameError",
            "missing_name": "FORWARD_AUDIT",
            "expected_error_observed": error_exact,
            "missing_binding_precedes_lease_acquisition_in_frozen_source": source_proves_prelease,
            "runner_log_path": str(LOG),
            "runner_log_sha256": contract.sha256(log_path),
            "runner_source_sha256": contract.sha256(runner_path),
        },
        "effect_boundary": {
            **surfaces,
            "shared_api_lease_acquired": False,
            "child_process_started": False,
            "child_terminal_receipt_created": False,
            "http_api_model_search_fetch_or_evaluator_effect": False,
            "tcp_reachability_probe_before_failure": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        },
        "control": {
            "forward_contract_sha256": contract.sha256(root / contract.FORWARD_CONTRACT),
            "protocol_sha256": contract.sha256(root / contract.PROTOCOL),
            "preaudit_sha256": contract.sha256(root / contract.PREAUDIT),
            "activation_sha256": contract.sha256(root / contract.ACTIVATION),
            "execution_start_sha256": contract.sha256(root / contract.EXECUTION_START),
            "execution_start_commit": start["activation_base_commit"],
            "old_execution_start_reusable": False,
        },
        "runtime_state": {
            "shared_api_lease_active": lease.get("active"),
            "v24679_process_active": active,
            "v24679_tmux_session_absent": _session_absent(),
            "protected_watchers": watchers,
        },
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "reuse_v24679_execution_start": False,
            "restart_or_resume_v24679": False,
            "append_only_recovery_design": not findings,
            "forward_launch": False,
            "evaluator": False,
            "exact220": False,
        },
    }
    value["receipt_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    boundary = copied.get("effect_boundary") or {}
    if (
        copied.get("role") != "v24681_v24679_zero_effect_start_failure"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("failure", {}).get("missing_name") != "FORWARD_AUDIT"
        or copied.get("failure", {}).get("expected_error_observed") is not True
        or copied.get("failure", {}).get(
            "missing_binding_precedes_lease_acquisition_in_frozen_source"
        )
        is not True
        or any(
            boundary.get(name) is not True
            for name in (
                "output_root_absent",
                "forward_result_absent",
                "forward_audit_absent",
            )
        )
        or any(
            boundary.get(name) is not False
            for name in (
                "shared_api_lease_acquired",
                "child_process_started",
                "child_terminal_receipt_created",
                "http_api_model_search_fetch_or_evaluator_effect",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
            )
        )
        or copied.get("control", {}).get("old_execution_start_reusable") is not False
        or copied.get("runtime_state", {}).get("shared_api_lease_active") is not False
        or copied.get("runtime_state", {}).get("v24679_process_active") is not False
        or copied.get("runtime_state", {}).get("v24679_tmux_session_absent") is not True
        or copied.get("authorization")
        != {
            "reuse_v24679_execution_start": False,
            "restart_or_resume_v24679": False,
            "append_only_recovery_design": True,
            "forward_launch": False,
            "evaluator": False,
            "exact220": False,
        }
        or not _sealed(copied, "receipt_payload_sha256")
    ):
        raise RuntimeError("V2.46.81 zero-effect start failure receipt drifted")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    receipt = build_receipt()
    validate_receipt(receipt)
    publish(ROOT / FAILURE, receipt)
    print(
        json.dumps(
            {
                "path": str(FAILURE),
                "audit_valid": receipt["audit_valid"],
                "findings": receipt["findings"],
            },
            sort_keys=True,
        )
    )
