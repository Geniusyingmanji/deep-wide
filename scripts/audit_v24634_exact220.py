#!/usr/bin/env python3
"""Strict label-blind preactivation audit for V2.46.34 exact-220."""

from __future__ import annotations

import ast
import json
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

from deepwide_agent.v24634_exact220_contract import (  # noqa: E402
    ACTIVATION, CAPACITY_AUDIT, CAPACITY_DECISION, CAPACITY_RESULT,
    CHILD_MARKER, EXECUTION_START, FORWARD_CONTRACT, FORWARD_RESULT,
    OUTPUT_ROOT, PREAUDIT, PROTOCOL_ID, RUNNER_MARKER, payload_sha256,
    protected_watcher_snapshot, sha256, validate_forward_contract,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24634_exact220 import publish_new  # noqa: E402


FORBIDDEN = frozenset(
    {"category", "question_type", "task_category", "split", "ground_truth",
     "gold", "answer_key", "mapping", "evaluator", "score", "reward"}
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
TESTS = (
    "test_v24634_exact220.py",
    "test_v24630_thin_backfill_search.py",
    "test_v24629_backfill_runner_integration.py",
    "test_v24628_backfill_search_integration.py",
    "test_v24627_same_response_citation_title_backfill.py",
    "test_v24319_runner_integration.py",
    "test_v24468_total_wall_transport.py",
)


def _accesses(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    output: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "pop", "setdefault"} and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            key = node.args[0].value
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            key = node.slice.value
        if isinstance(key, str) and key.casefold() in FORBIDDEN:
            output.append(f"{path.relative_to(root)}:{node.lineno}:{key}")
    return output


def _test(filename: str) -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
         "discover", "-s", "tests", "-p", filename],
        cwd=ROOT,
        env={"HOME": str(Path.home()), "USER": "azureuser", "LOGNAME": "azureuser",
             "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
             "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"},
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=300, check=False,
    )
    return completed.returncode == 0


def _active(marker: str) -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=False,
    )
    return any(marker in line for line in completed.stdout.splitlines() if "ps -eo" not in line)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=True, timeout=20,
    ).stdout.strip()


def _tracked(root: Path, relative: str | Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False, timeout=20,
    ).returncode == 0


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    accesses: list[str] = []
    secrets: list[str] = []
    evaluator_imports: list[str] = []
    for relative in contract["dependency_manifest"]:
        path = root / relative
        accesses.extend(_accesses(path, root))
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(relative)
        if relative in {RUNNER_MARKER, CHILD_MARKER} and any(
            marker in source for marker in
            ("run_official_eval_local", "evaluator_mapping.jsonl", "finalize_fullset_rollout")
        ):
            evaluator_imports.append(relative)
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    unexpected = sorted(set(accesses) - allowed)
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    tracked = all(
        _tracked(root, relative)
        for relative in (
            FORWARD_CONTRACT,
            CAPACITY_RESULT,
            CAPACITY_DECISION,
            CAPACITY_AUDIT,
            *contract["dependency_manifest"],
        )
    )
    try:
        protected = protected_watcher_snapshot()
    except RuntimeError:
        protected = []
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if head != remote:
        findings.append("forward_contract_commit_not_pushed")
    if not tracked:
        findings.append("forward_contract_or_dependency_not_tracked")
    if _active(RUNNER_MARKER) or _active(CHILD_MARKER):
        findings.append("v24634_forward_process_already_active")
    for marker in (
        "scripts/run_v24630_exact220.py",
        "scripts/finalize_v24630_exact220.py",
        "scripts/run_official_eval_local.py",
    ):
        if _active(marker):
            findings.append("conflicting_benchmark_or_evaluator_process_active")
            break
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)
    ):
        findings.append("future_surface_not_pristine")
    if unexpected:
        findings.append("privileged_runtime_field_access")
    if secrets:
        findings.append("credential_literal_in_forward_surface")
    if evaluator_imports:
        findings.append("forward_evaluator_capability_present")
    tests = [{"file": name, "passed": _test(name)} for name in TESTS]
    if not all(item["passed"] for item in tests):
        findings.append("focused_tests_failed")
    value = {
        "artifact_version": 1,
        "role": "v24634_exact220_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "runtime_boundary": ["opaque_id", "question"],
        "selected": 220,
        "field_accesses": sorted(set(accesses)),
        "allowed_provider_result_rank_accesses": sorted(set(accesses).intersection(allowed)),
        "unexpected_privileged_runtime_field_accesses": unexpected,
        "credential_literal_hits": sorted(secrets),
        "evaluator_imports_in_forward_surface": sorted(evaluator_imports),
        "focused_tests": tests,
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "forward_contract_and_dependencies_tracked": tracked,
        },
        "shared_api_lease_active": lease.get("active") is True,
        "protected_watchers": protected,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "fixed_denominator_fallback_allows_postfreeze_evaluation": True,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "findings": findings,
        "launch_authorized": False,
        "audit_valid": not findings,
        "authorization": {
            "activation_design": not findings,
            "exact220_launch": False,
            "evaluator_call": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / PREAUDIT, report)
    print(json.dumps({"path": str(PREAUDIT), "launch_authorized": report["launch_authorized"], "findings": report["findings"]}, sort_keys=True))
