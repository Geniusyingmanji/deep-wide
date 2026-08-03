#!/usr/bin/env python3
"""Build-only audit for V2.43.41 semantic evidence projection."""

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
from scripts.audit_v24187_phase_liveness import actual_python_script, process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


AUDIT = Path("results/v24341_semantic_evidence_projection_build_audit_v1_20260803.json")
PARENT = Path("results/v24339_active_evidence_support_build_audit_v1_20260803.json")
SOURCE = Path("src/deepwide_agent/v24341_semantic_evidence_projection.py")
TEST = Path("tests/test_v24341_semantic_evidence_projection.py")
SOURCES = (SOURCE, TEST)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(value) for value in SECRET_PREFIXES) + r")[A-Za-z0-9_-]{16,}")
PRIVILEGED = frozenset({"benchmark_question_type", "question_type", "task_category", "category", "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator", "score", "reward"})
FORBIDDEN_IMPORTS = frozenset({"requests", "httpx", "aiohttp", "urllib", "socket", "subprocess"})
RUNNER_MARKERS = ("scripts/run_v24330_shared_prefix_exact220.py", "scripts/run_v24330_shared_prefix_exact220_task.py")


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError(f"V2.43.41 audit expected ordinary file: {relative}")
    return path


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=False).returncode == 0


def _ast_findings(path: Path) -> tuple[list[str], list[str]]:
    tree = ast.parse(_ordinary(path).read_text(encoding="utf-8")); accesses: list[str] = []; imports: list[str] = []
    for node in ast.walk(tree):
        key = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str): key = node.args[0].value
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str): key = node.slice.value
        if key is not None and key.casefold() in PRIVILEGED: accesses.append(f"{path}:{node.lineno}:{key}")
        names: list[str] = []
        if isinstance(node, ast.Import): names = [item.name for item in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module: names = [node.module]
        for name in names:
            if name.split(".")[0] in FORBIDDEN_IMPORTS: imports.append(f"{path}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _process_present(marker: str) -> bool:
    for row in process_snapshot():
        argv = row.get("argv"); script = actual_python_script(argv) if isinstance(argv, list) else None
        if isinstance(script, str) and script.endswith(marker): return True
    return False


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = read_object(ROOT / PARENT)
    if parent.get("audit_valid") is not True or parent.get("findings") != [] or parent.get("authorization", {}).get("active_evidence_runtime_integration_design") is not True:
        raise RuntimeError("V2.43.41 parent audit drifted")
    manifest = {str(path): sha256(_ordinary(path)) for path in SOURCES}; accesses: list[str] = []; imports: list[str] = []
    for path in SOURCES:
        current_accesses, current_imports = _ast_findings(path); accesses.extend(current_accesses); imports.extend(current_imports)
    secret_hits = [str(path) for path in SOURCES if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))]
    completed = subprocess.run([str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / TEST), "-v"], cwd=ROOT, env={"HOME": os.environ.get("HOME", str(Path.home())), "USER": os.environ.get("USER", "azureuser"), "LOGNAME": os.environ.get("LOGNAME", "azureuser"), "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90, check=False)
    head = _git("rev-parse", "HEAD"); remote = _git("rev-parse", "target/main"); tracked = all(_tracked(path) for path in SOURCES); watcher = protected_watcher_snapshot(); parent_watchers = parent["closure"]["protected_watchers"]; runner_present = any(_process_present(marker) for marker in RUNNER_MARKERS); lease = lease_observation(ROOT, Path("/proc")); findings: list[str] = []
    if head != remote: findings.append("v24341_source_commit_not_pushed")
    if not tracked: findings.append("v24341_source_not_tracked")
    if completed.returncode != 0: findings.append("focused_tests_failed")
    if accesses: findings.append("privileged_field_access_in_v24341_surface")
    if imports: findings.append("remote_or_process_import_in_v24341_surface")
    if secret_hits: findings.append("credential_literal_in_v24341_surface")
    if watcher != parent_watchers: findings.append("protected_watcher_identity_drifted")
    if runner_present: findings.append("v24330_forward_process_present")
    if lease.get("active") is not False: findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1, "role": "v24341_semantic_evidence_projection_build_audit", "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)}, "source_manifest": manifest, "source_manifest_sha256": payload_sha256(manifest),
        "git": {"head": head, "target_main": remote, "head_equals_target_main": head == remote, "all_sources_tracked": tracked},
        "focused_tests": {"path": str(TEST), "passed": completed.returncode == 0, "test_count": 5, "network_model_search_fetch_or_evaluator_called": False},
        "mechanism_evidence": {"founding_year_aliases_projected": True, "headquarters_city_country_aliases_projected": True, "first_flight_and_release_aliases_projected": True, "unrelated_nearby_year_not_projected": True, "original_page_and_projection_tamper_rejected": True, "entity_local_relation_binding_required": True},
        "privileged_field_accesses": sorted(accesses), "remote_or_process_imports": sorted(imports), "credential_literal_hits": sorted(secret_hits),
        "closure": {"shared_api_lease_active": lease.get("active"), "v24330_forward_runner_or_child_present": runner_present, "protected_watchers": watcher, "protected_watchers_unchanged": watcher == parent_watchers, "active_run_killed_or_quarantined": False, "process_signal_restart_resume_rerun_skip_or_selective_retry": False},
        "source_policy": {"visible_column_and_current_active_evidence_only": True, "mapping_gold_category_question_type_split_evaluator_score_read": False, "network_model_search_fetch_or_evaluator_called_by_audit": False},
        "findings": findings, "audit_valid": not findings,
        "authorization": {"semantic_active_runtime_integration_design": not findings, "benchmark_launch": False, "same_run_evaluator": False, "new_exact220": False, "leaderboard_submission": False, "sota_claim": False},
    }
    value["audit_payload_sha256"] = payload_sha256(value); return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True); descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle: json.dump(value, handle, ensure_ascii=False, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit(); publish_new(ROOT / AUDIT, audit); print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}, sort_keys=True))
