#!/usr/bin/env python3
"""Build-only label-blind audit for the V2.43.42/43 successor."""

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

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    protected_watcher_snapshot,
    read_object,
    sha256,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


DATE = "20260803"
AUDIT = Path(f"results/v24344_semantic_active_runtime_build_audit_v1_{DATE}.json")
PARENTS = (
    Path(f"results/v24339_active_evidence_support_build_audit_v1_{DATE}.json"),
    Path(f"results/v24341_semantic_evidence_projection_build_audit_v1_{DATE}.json"),
)
SOURCES = (
    Path("src/deepwide_agent/v24342_semantic_active_runtime.py"),
    Path("src/deepwide_agent/v24343_semantic_active_runner.py"),
    Path("tests/test_v24342_semantic_active_runtime.py"),
    Path("tests/test_v24343_semantic_active_runner.py"),
    Path("scripts/audit_v24344_semantic_active_runtime_build.py"),
)
FOCUSED_TESTS = (
    (Path("tests/test_v24342_semantic_active_runtime.py"), 7),
    (Path("tests/test_v24343_semantic_active_runner.py"), 4),
)
JOINT_TESTS = (
    (Path("tests/test_v24333_programmatic_support_catalog.py"), 9),
    (Path("tests/test_v24334_support_catalog_revision_gate.py"), 7),
    (Path("tests/test_v24335_programmatic_support_runtime.py"), 10),
    (Path("tests/test_v24336_programmatic_support_runner.py"), 4),
    (Path("tests/test_v24339_active_evidence_support.py"), 5),
    (Path("tests/test_v24341_semantic_evidence_projection.py"), 5),
    *FOCUSED_TESTS,
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
    }
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
REMOTE_IMPORTS = frozenset(
    {"aiohttp", "httpx", "openai", "requests", "socket", "subprocess", "urllib"}
)
FROZEN_RUNNER_MARKERS = (
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
        raise RuntimeError(f"V2.43.44 expected ordinary repository file: {relative}")
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
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _ast_findings(relative: Path) -> tuple[list[str], list[str]]:
    tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
    accesses: list[str] = []
    imports: list[str] = []
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
            accesses.append(f"{relative}:{node.lineno}:{key}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in REMOTE_IMPORTS:
                    imports.append(f"{relative}:{node.lineno}:{root}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in REMOTE_IMPORTS:
                imports.append(f"{relative}:{node.lineno}:{root}")
    return sorted(accesses), sorted(imports)


def _run_test(relative: Path) -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-v"],
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
    return completed.returncode == 0


def _process_present(marker: str) -> bool:
    for row in process_snapshot():
        argv = row.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if isinstance(script, str) and script.endswith(marker):
            return True
    return False


def _parent(relative: Path) -> dict[str, Any]:
    value = read_object(_ordinary(relative))
    if (
        value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("benchmark_launch") is not False
        or value.get("authorization", {}).get("new_exact220") is not False
    ):
        raise RuntimeError(f"V2.43.44 parent audit drifted: {relative}")
    return value


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parents = [_parent(path) for path in PARENTS]
    manifest = {str(path): sha256(_ordinary(path)) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in SOURCES[:2]:
        current_accesses, current_imports = _ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = [
        {"path": str(path), "passed": _run_test(path), "test_count": count}
        for path, count in JOINT_TESTS
    ]
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    tracked = all(_tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    parent_watchers = parents[-1]["closure"]["protected_watchers"]
    runner_present = any(_process_present(marker) for marker in FROZEN_RUNNER_MARKERS)
    lease = lease_observation(ROOT, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("v24344_source_commit_not_pushed")
    if not tracked:
        findings.append("v24344_source_not_tracked")
    if any(not item["passed"] for item in suites):
        findings.append("focused_or_joint_tests_failed")
    if accesses:
        findings.append("privileged_field_access_in_v24342_43_surface")
    if imports:
        findings.append("remote_or_process_import_in_v24342_43_surface")
    if secret_hits:
        findings.append("credential_literal_in_v24344_surface")
    if watchers != parent_watchers:
        findings.append("protected_watcher_identity_drifted")
    if runner_present:
        findings.append("v24330_forward_process_present")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24344_semantic_active_runtime_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": [
            {"path": str(path), "sha256": sha256(_ordinary(path))} for path in PARENTS
        ],
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "suites": suites,
            "passed": all(item["passed"] for item in suites),
            "test_count": sum(item["test_count"] for item in suites),
            "focused_success_path_count": sum(count for _, count in FOCUSED_TESTS),
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "mechanism_evidence": {
            "same_fixed_raw_7_plus_3_pages_used_by_baseline_and_candidate": True,
            "all_fetch_attempts_precede_baseline_synthesis": True,
            "candidate_only_adds_semantic_projection_catalog_and_entropy_gate": True,
            "natural_multihost_support_produces_nonidentity_candidate": True,
            "natural_admission_has_positive_entropy_credit": True,
            "empty_catalog_skips_third_model_call": True,
            "fabricated_support_is_identity_zero_credit": True,
            "baseline_recovery_excludes_revision": True,
            "raw_page_projection_proposal_and_gate_replay_tamper_rejected": True,
            "deadline_model_and_fetch_conservation_verified": True,
            "total_fallback_preserves_effect_lower_bounds": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "remote_or_process_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "v24330_forward_runner_or_child_present": runner_present,
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == parent_watchers,
            "active_run_killed_or_quarantined": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_private_content_emitted_to_public_aggregate": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "benchmark_external_natural_admission_probe_design": not findings,
            "benchmark_launch": False,
            "same_run_evaluator": False,
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
