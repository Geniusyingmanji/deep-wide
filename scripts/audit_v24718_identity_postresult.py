#!/usr/bin/env python3
"""Post-result closure audit for the V2.47.18 identity full-220 result."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24714_sparse_full220_order_join as contract  # noqa: E402
from scripts import project_v24718_identity_full220_result as projector  # noqa: E402


AUDIT = projector.POSTAUDIT


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active_runner() -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    return any(
        contract.RUNNER_MARKER in line for line in completed.stdout.splitlines()
        if "ps -eo" not in line and "audit_v24718_identity_postresult.py" not in line
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    result = projector.validate_result(projector._read(projector.RESULT))
    identity = projector.prediction_identity()
    control = projector._control_valid()
    nogo = projector._forward_nogo_valid()
    watchers = contract.protected_watcher_snapshot()
    lease = _lease_inactive()
    active = _active_runner()
    clean = _git("status", "--porcelain") == ""
    remote = _git("rev-parse", "HEAD") == _git("rev-parse", "target/main")
    tracked = _tracked(projector.RESULT)
    findings: list[str] = []
    if identity.get("identity_complete") is not True:
        findings.append("candidate_control_prediction_identity_drifted")
    if result.get("metrics") != control.get("metrics"):
        findings.append("identity_result_metrics_differ_from_control")
    if any(value != 0 and value != 0.0 for value in result["delta_vs_v24267_control"].values()):
        findings.append("nonzero_delta_under_prediction_identity")
    if result.get("evaluation", {}).get("new_evaluator_calls") != 0:
        findings.append("unexpected_new_evaluator_calls")
    if result.get("claims", {}).get("benchmark_improvement") is not False:
        findings.append("invalid_improvement_claim")
    if result.get("claims", {}).get("sota") is not False:
        findings.append("invalid_sota_claim")
    if nogo.get("authorization", {}).get("evaluator_execution") is not False:
        findings.append("forward_nogo_evaluator_authorization_drifted")
    if not clean or not remote or not tracked:
        findings.append("result_not_clean_pushed_and_tracked")
    if not lease:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("forward_runner_active")
    value = {
        "artifact_version": 1,
        "role": "v24718_v24714_identity_full220_postresult_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": contract.sha256(ROOT / projector.RESULT),
        "forward_audit_sha256": contract.sha256(ROOT / projector.FORWARD_AUDIT),
        "control_result_sha256": contract.sha256(ROOT / projector.CONTROL_RESULT),
        "identity": identity,
        "metrics_equal_control": result.get("metrics") == control.get("metrics"),
        "new_evaluator_calls": result["evaluation"]["new_evaluator_calls"],
        "whole_table_successes": result["metrics"]["whole_table_successes"],
        "score": result["metrics"]["score"],
        "quality_composite": result["metrics"]["quality_composite"],
        "runtime_state": {
            "protected_watchers": watchers,
            "shared_api_lease_inactive": lease,
            "forward_runner_active": active,
        },
        "source_policy": {
            "postfreeze_control_result_and_evaluator_hashes_opened": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_used_by_forward": False,
            "network_model_search_forward_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "additional_forward_resume_retry_or_rerun": False,
            "additional_evaluator_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != "v24718_v24714_identity_full220_postresult_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("identity", {}).get("identity_complete") is not True
        or value.get("metrics_equal_control") is not True
        or value.get("new_evaluator_calls") != 0
        or value.get("whole_table_successes") != 7
        or value.get("score") != 7 / 220
        or value.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or value.get("runtime_state", {}).get("forward_runner_active") is not False
        or value.get("authorization")
        != {
            "additional_forward_resume_retry_or_rerun": False,
            "additional_evaluator_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or not contract.sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.18 postresult audit drifted")
    return dict(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    validate_audit(value)
    publish(ROOT / AUDIT, value)
    print(json.dumps({"path": str(AUDIT), "audit_valid": value["audit_valid"],
                      "findings": value["findings"], "score": value["score"]}, sort_keys=True))
