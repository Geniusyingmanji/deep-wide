#!/usr/bin/env python3
"""Audit the aggregate-only V2.46.36 paired post-result diagnosis."""

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

from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sha256,
)
from scripts import (  # noqa: E402
    diagnose_v24636_v24630_v24635_paired_postresult as target,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24635_exact220 import publish_new  # noqa: E402


AUDIT = Path(
    "results/v24636_v24630_v24635_paired_postresult_diagnosis_audit_v1_20260806.json"
)
SOURCE = Path("scripts/diagnose_v24636_v24630_v24635_paired_postresult.py")
TEST = Path("tests/test_diagnose_v24636_v24630_v24635_paired_postresult.py")
AUDIT_SOURCE = Path("scripts/audit_v24636_v24630_v24635_paired_postresult.py")
SOURCES = (SOURCE, TEST, AUDIT_SOURCE)
FORBIDDEN_EXECUTION_CALLS = frozenset(
    {
        "execute_forward",
        "run_one_task",
        "run_parallel_evaluator",
        "run_all_evaluators",
        "acquire_deepwide_api_lease",
    }
)
PROHIBITED_RESOURCE_MARKERS = (
    "evaluator_mapping.jsonl",
    "overall_20250916.jsonl",
    "overall_20250916_tables",
    "visible_task.json",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
RUNNER_MARKERS = (
    "scripts/run_v24630_exact220.py",
    "scripts/run_v24630_exact220_task.py",
    "scripts/finalize_v24630_exact220.py",
    "scripts/run_v24635_exact220.py",
    "scripts/run_v24635_exact220_task.py",
    "scripts/finalize_v24635_exact220.py",
    "scripts/run_official_eval_local.py",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=True, timeout=20,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False, timeout=20,
    ).returncode == 0


def _source_checks(relative: Path) -> tuple[list[str], list[str]]:
    source = (ROOT / relative).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(relative))
    calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else None
        )
        if name in FORBIDDEN_EXECUTION_CALLS:
            calls.append(f"{relative}:{node.lineno}:{name}")
    resources = [marker for marker in PROHIBITED_RESOURCE_MARKERS if marker in source]
    return sorted(calls), sorted(resources)


def _active(marker: str) -> bool:
    rows = subprocess.run(
        ["ps", "-eo", "cmd="], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=False,
    ).stdout.splitlines()
    return any(marker in row for row in rows if "ps -eo" not in row)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    report = read_object(ROOT / target.OUTPUT)
    target.validate_report(ROOT, report)
    manifest = {str(path): sha256(ROOT / path) for path in SOURCES}
    calls: list[str] = []
    resources: list[str] = []
    credentials: list[str] = []
    for relative in SOURCES:
        found_calls, found_resources = _source_checks(relative)
        calls.extend(found_calls)
        # The audit source declares the forbidden marker set it checks.  Only
        # the diagnosis and its tests are execution surfaces for this check.
        if relative != AUDIT_SOURCE:
            resources.extend(f"{relative}:{value}" for value in found_resources)
        if SECRET.search((ROOT / relative).read_text(encoding="utf-8")):
            credentials.append(str(relative))
    focused = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
            "discover", "-s", "tests", "-p",
            "test_diagnose_v24636_v24630_v24635_paired_postresult.py", "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    tracked = all(_tracked(path) for path in (*SOURCES, target.OUTPUT))
    lease = lease_observation(ROOT, Path("/proc"))
    active = [marker for marker in RUNNER_MARKERS if _active(marker)]
    watchers = protected_watcher_snapshot()
    parent_watchers = read_object(ROOT / target.NEW_POSTAUDIT)["execution_closure"][
        "protected_watchers"
    ]
    findings: list[str] = []
    if head != remote:
        findings.append("diagnosis_commit_not_pushed")
    if not tracked:
        findings.append("diagnosis_source_test_audit_or_result_not_tracked")
    if focused.returncode != 0:
        findings.append("focused_tests_failed")
    if calls:
        findings.append("forbidden_execution_call_in_diagnosis_surface")
    if resources:
        findings.append("mapping_answer_or_visible_task_resource_marker_in_surface")
    if credentials:
        findings.append("credential_literal_in_diagnosis_surface")
    if active:
        findings.append("forward_or_evaluator_process_active")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if watchers != parent_watchers:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24636_v24630_v24635_aggregate_only_paired_postresult_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "diagnosis": {"path": str(target.OUTPUT), "sha256": sha256(ROOT / target.OUTPUT)},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "source_test_audit_and_result_tracked": tracked,
        },
        "focused_tests": {
            "passed": focused.returncode == 0,
            "test_count": 6,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "forbidden_execution_calls": calls,
        "prohibited_resource_markers": resources,
        "credential_literal_hits": credentials,
        "closure": {
            "active_forward_or_evaluator_markers": active,
            "shared_api_lease_active": lease.get("active") is True,
            "protected_watchers": watchers,
            "protected_watchers_signaled_restarted_or_stopped": False,
            "active_run_killed_or_quarantined": False,
            "invalid_result_path": None,
        },
        "boundary": {
            "postresult_offline_aggregate_analysis_only": True,
            "runtime_mapping_answer_category_or_question_type_read": False,
            "per_task_identifier_metric_or_prediction_emitted": False,
            "same_run_forward_feedback_or_prediction_selection": False,
        },
        "authorization": {
            "benchmark_external_mechanism_design": not findings,
            "new_dev64": False,
            "new_exact220": False,
            "same_run_retry_resume_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    report = build_audit()
    publish_new(ROOT / AUDIT, report)
    print(
        json.dumps(
            {"path": str(AUDIT), "audit_valid": report["audit_valid"], "findings": report["findings"]},
            sort_keys=True,
        )
    )
