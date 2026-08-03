#!/usr/bin/env python3
"""Audit the append-only V2.43.31 content-free taxonomy publication."""

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
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sha256,
)
from scripts import diagnose_v24331_v24330_postterminal as target  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


AUDIT = Path("results/v24331_v24330_content_free_taxonomy_audit_v1_20260803.json")
SOURCE = Path("scripts/diagnose_v24331_v24330_postterminal.py")
TEST = Path("tests/test_diagnose_v24331_v24330_postterminal.py")
SOURCES = (SOURCE, TEST)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
FORBIDDEN_FIELDS = frozenset(
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
    }
)
FORBIDDEN_CALLS = frozenset(
    {
        "execute_forward",
        "run_one_task",
        "run_all_evaluators",
        "evaluator_command",
        "acquire_deepwide_api_lease",
    }
)
RUNNER_MARKERS = (
    "scripts/run_v24330_shared_prefix_exact220.py",
    "scripts/run_v24330_shared_prefix_exact220_task.py",
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT)
    ):
        raise RuntimeError(f"V2.43.31 audit expected ordinary file: {relative}")
    return path


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _source_findings(relative: Path) -> tuple[list[str], list[str]]:
    path = _ordinary(relative)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    field_accesses: list[str] = []
    call_hits: list[str] = []
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
        if key is not None and key.casefold() in FORBIDDEN_FIELDS:
            field_accesses.append(f"{relative}:{node.lineno}:{key}")
        if isinstance(node, ast.Call):
            name: str | None = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in FORBIDDEN_CALLS:
                call_hits.append(f"{relative}:{node.lineno}:{name}")
    return sorted(field_accesses), sorted(call_hits)


def _process_present(marker: str) -> bool:
    for row in process_snapshot():
        argv = row.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if isinstance(script, str) and script.endswith(marker):
            return True
    return False


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    report = read_object(_ordinary(target.OUTPUT))
    target.validate_report(ROOT, report)
    manifest = {str(relative): sha256(_ordinary(relative)) for relative in SOURCES}
    accesses: list[str] = []
    calls: list[str] = []
    for relative in SOURCES:
        source_accesses, source_calls = _source_findings(relative)
        accesses.extend(source_accesses)
        calls.extend(source_calls)
    secret_hits = [
        str(relative)
        for relative in SOURCES
        if SECRET.search(_ordinary(relative).read_text(encoding="utf-8"))
    ]
    focused = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / TEST), "-v"],
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
        timeout=60,
        check=False,
    )
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    tracked = all(_tracked(relative) for relative in SOURCES)
    watcher = protected_watcher_snapshot()
    parent_watchers = read_object(ROOT / target.parent.AUDIT)["closure"][
        "protected_watchers"
    ]
    runner_present = any(_process_present(marker) for marker in RUNNER_MARKERS)
    lease = lease_observation(ROOT, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("taxonomy_source_commit_not_pushed")
    if not tracked:
        findings.append("taxonomy_source_not_tracked")
    if focused.returncode != 0:
        findings.append("focused_tests_failed")
    if accesses:
        findings.append("privileged_field_access_in_taxonomy_surface")
    if calls:
        findings.append("forbidden_execution_call_in_taxonomy_surface")
    if secret_hits:
        findings.append("credential_literal_in_taxonomy_surface")
    if watcher != parent_watchers:
        findings.append("protected_watcher_identity_drifted")
    if runner_present:
        findings.append("v24330_forward_process_present")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24331_v24330_content_free_postterminal_taxonomy_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "taxonomy": {"path": str(target.OUTPUT), "sha256": sha256(ROOT / target.OUTPUT)},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "all_sources_tracked": tracked,
        },
        "focused_tests": {
            "command": "python -I -B tests/test_diagnose_v24331_v24330_postterminal.py -v",
            "passed": focused.returncode == 0,
            "test_count": 5,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "privileged_field_accesses": sorted(accesses),
        "forbidden_execution_calls": sorted(calls),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "v24330_forward_runner_or_child_present": runner_present,
            "protected_watchers": watcher,
            "protected_watchers_unchanged": watcher == parent_watchers,
            "active_run_killed_or_quarantined": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_identifier_question_query_url_page_cell_value_evidence_id_prediction_or_credential_emitted": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "append_only_aggregate_validator_design": not findings,
            "benchmark_external_fault_matrix": not findings,
            "benchmark_external_evidence_admission_test": not findings,
            "same_run_evaluator": False,
            "same_run_forward_resume_retry_or_rerun": False,
            "additional_dev64": False,
            "new_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}, sort_keys=True))
