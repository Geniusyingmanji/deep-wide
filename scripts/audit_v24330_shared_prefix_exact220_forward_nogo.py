#!/usr/bin/env python3
"""Closure and label-blind audit for the V2.43.30 forward NO-GO."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    ARMS,
    EVALUATOR_GATE,
    EVALUATOR_ROOT,
    EVALUATOR_START,
    FINAL_RESULT,
    FORWARD_RESULT,
    PAIR_SUMMARY,
    POSTAUDIT,
    PREDICTION_FREEZE,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sha256,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.publish_v24330_shared_prefix_exact220_forward_nogo import (  # noqa: E402
    AUDIT,
    DIAGNOSTIC,
    EVALUATOR_SURFACES,
    RESULT,
    RUNNER_MARKERS,
    _publish_new,
    validate_diagnostic,
    validate_result,
)


SOURCE = Path("scripts/publish_v24330_shared_prefix_exact220_forward_nogo.py")
AUDIT_SOURCE = Path("scripts/audit_v24330_shared_prefix_exact220_forward_nogo.py")
TEST = Path("tests/test_v24330_shared_prefix_exact220_forward_nogo.py")
SOURCES = (SOURCE, AUDIT_SOURCE, TEST)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
PRIVILEGED = frozenset(
    {
        "benchmark_question_type",
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
        "results.csv",
    }
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _field_accesses(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in ast.walk(tree):
        key: str | None = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key is not None and key.casefold() in PRIVILEGED:
            hits.append(f"{path.relative_to(ROOT)}:{node.lineno}:{key}")
    return sorted(hits)


def _process_present(marker: str) -> bool:
    for row in process_snapshot():
        argv = row.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if isinstance(script, str) and script.endswith(marker):
            return True
    return False


def build_audit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = read_object(root / RESULT)
    diagnostic = read_object(root / DIAGNOSTIC)
    validate_result(root, result, diagnostic=diagnostic)
    validate_diagnostic(root, diagnostic)
    manifest = {str(path): sha256(root / path) for path in SOURCES}
    accesses = _field_accesses(root / SOURCE)
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search((root / path).read_text(encoding="utf-8"))
    ]
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    tracked = all(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
        for path in SOURCES
    )
    lease = lease_observation(root, Path("/proc"))
    watcher = protected_watcher_snapshot()
    runner_present = any(_process_present(marker) for marker in RUNNER_MARKERS)
    evaluator_surface = any(
        (root / path).exists() or (root / path).is_symlink()
        for path in EVALUATOR_SURFACES
    )
    success_surface = any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (FORWARD_RESULT, PAIR_SUMMARY)
    )
    freezes_valid = all(
        read_object(root / PREDICTION_FREEZE[arm]).get("terminal") == 220
        for arm in ARMS
    )
    findings: list[str] = []
    if head != remote:
        findings.append("recovery_code_commit_not_pushed")
    if not tracked:
        findings.append("recovery_source_not_tracked")
    if accesses:
        findings.append("privileged_field_access_in_recovery_surface")
    if secret_hits:
        findings.append("credential_literal_in_recovery_surface")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active_after_forward")
    if runner_present:
        findings.append("forward_runner_or_child_present_after_terminal")
    if evaluator_surface:
        findings.append("evaluator_surface_exists_after_forward_nogo")
    if success_surface:
        findings.append("success_forward_surface_exists_after_forward_nogo")
    if not freezes_valid:
        findings.append("both_arm_prediction_freeze_invalid")
    if result.get("evaluation_authorized") is not False:
        findings.append("result_incorrectly_authorized_evaluator")
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_forward_nogo_audit",
        "protocol_id": result["protocol_id"],
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_nogo": {"path": str(RESULT), "sha256": sha256(root / RESULT)},
        "diagnostic": {
            "path": str(DIAGNOSTIC),
            "sha256": sha256(root / DIAGNOSTIC),
        },
        "prediction_freeze_sha256": {
            arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "all_recovery_sources_tracked": tracked,
        },
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "forward_runner_or_child_present": runner_present,
            "success_forward_surface_absent": not success_surface,
            "evaluator_side_surface_absent": not evaluator_surface,
            "both_arm_prediction_freeze_valid": freezes_valid,
            "protected_watchers": watcher,
            "active_run_killed_or_quarantined": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "privileged_field_accesses": accesses,
        "credential_literal_hits": secret_hits,
        "source_policy": {
            "all_220_pair_predictions_frozen_before_audit": True,
            "task_question_query_url_page_prediction_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_selection": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "append_only_accounting_fix_design": not findings,
            "same_run_evaluator": False,
            "same_run_forward_resume_retry_or_rerun": False,
            "additional_rollout": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_audit(root, value, result=result, diagnostic=diagnostic)
    return value


def validate_audit(
    root: Path,
    value: dict[str, Any],
    *,
    result: dict[str, Any] | None = None,
    diagnostic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    frozen_result = result or read_object(root / RESULT)
    frozen_diagnostic = diagnostic or read_object(root / DIAGNOSTIC)
    if (
        value.get("role")
        != "v24330_shared_prefix_exact220_forward_nogo_audit"
        or value.get("protocol_id") != frozen_result["protocol_id"]
        or value.get("forward_nogo")
        != {"path": str(RESULT), "sha256": sha256(root / RESULT)}
        or value.get("diagnostic")
        != {"path": str(DIAGNOSTIC), "sha256": sha256(root / DIAGNOSTIC)}
        or value.get("prediction_freeze_sha256")
        != {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("closure", {}).get("shared_api_lease_active") is not False
        or value.get("closure", {}).get("forward_runner_or_child_present") is not False
        or value.get("closure", {}).get("success_forward_surface_absent") is not True
        or value.get("closure", {}).get("evaluator_side_surface_absent") is not True
        or value.get("closure", {}).get("both_arm_prediction_freeze_valid") is not True
        or value.get("privileged_field_accesses") != []
        or value.get("credential_literal_hits") != []
        or value.get("authorization", {}).get("same_run_evaluator") is not False
        or value.get("authorization", {}).get(
            "same_run_forward_resume_retry_or_rerun"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.30 forward NO-GO audit drifted")
    validate_result(root, frozen_result, diagnostic=frozen_diagnostic)
    return dict(value)


if __name__ == "__main__":
    audit = build_audit(ROOT)
    _publish_new(ROOT / AUDIT, audit)
    print(
        json.dumps(
            {"path": str(AUDIT), "audit_valid": audit["audit_valid"]},
            sort_keys=True,
        )
    )
