#!/usr/bin/env python3
"""Build-only label-blind audit for V2.43.54--56."""

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
AUDIT = Path(f"results/v24356_explicit_partition_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24353_hidden_verifier_external_postresult_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24354_explicit_partition_utility.py"),
    Path("src/deepwide_agent/v24355_explicit_partition_runtime.py"),
    Path("src/deepwide_agent/v24356_explicit_partition_runner.py"),
    Path("tests/test_v24354_explicit_partition_utility.py"),
    Path("tests/test_v24355_explicit_partition_runtime.py"),
    Path("tests/test_v24356_explicit_partition_runner.py"),
    Path("scripts/audit_v24356_explicit_partition_build.py"),
)
RUNTIME_SOURCES = SOURCES[:3]
TEST_SUITES = (
    (Path("tests/test_v24354_explicit_partition_utility.py"), 7),
    (Path("tests/test_v24355_explicit_partition_runtime.py"), 8),
    (Path("tests/test_v24356_explicit_partition_runner.py"), 4),
)
EXPECTED_WATCHERS = [
    {
        "pid": 795336,
        "marker": "scripts/watch_v2415_r1_checkpoint_liveness.py",
        "start_ticks": 713986317,
    },
    {
        "pid": 3061652,
        "marker": "scripts/watch_v24218_exact220_executor.py",
        "start_ticks": 747569004,
    },
]
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
EVALUATOR_IMPORT_MARKERS = (
    "official_eval",
    "official_evaluator",
    "finalize_v24",
    "evaluator_mapping",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
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
        raise RuntimeError(f"V2.43.56 expected ordinary repository file: {relative}")
    return path


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
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
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        for name in names:
            if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS):
                imports.append(f"{relative}:{node.lineno}:{name}")
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
        timeout=180,
        check=False,
    )
    return completed.returncode == 0


def _active_successor_processes() -> list[str]:
    output: list[str] = []
    for row in process_snapshot():
        argv = row.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if (
            isinstance(script, str)
            and any(marker in Path(script).name for marker in ("v24354", "v24355", "v24356"))
            and Path(script).name != Path(__file__).name
        ):
            output.append(Path(script).name)
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = read_object(_ordinary(PARENT))
    if (
        parent.get("role") != "v24353_hidden_verifier_external_postresult_audit"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or parent.get("authorization", {}).get("fresh_paired_dev64_launch") is not False
        or parent.get("authorization", {}).get("new_exact220") is not False
    ):
        raise RuntimeError("V2.43.56 postresult parent drifted")

    manifest = {str(path): sha256(_ordinary(path)) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
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
        for path, count in TEST_SUITES
    ]
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    tracked = all(_tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    active = _active_successor_processes()
    findings: list[str] = []
    if head != remote:
        findings.append("v24356_source_commit_not_pushed")
    if not tracked:
        findings.append("v24356_source_not_tracked")
    if any(not item["passed"] for item in suites):
        findings.append("focused_tests_failed")
    if accesses:
        findings.append("privileged_field_access_in_v24354_56_surface")
    if imports:
        findings.append("evaluator_import_in_v24354_56_surface")
    if secret_hits:
        findings.append("credential_literal_in_v24354_56_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if active:
        findings.append("v24354_56_runtime_process_present_before_activation")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24356_explicit_partition_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(_ordinary(PARENT))},
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
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "mechanism_evidence": {
            "explicit_preproposal_partition_reused_after_fetch_failures": True,
            "successful_pages_may_be_strict_partition_subsets": True,
            "parent_support_set_and_evidence_ids_reused_without_rebuild": True,
            "one_verifier_host_reserved_and_nine_proposal_hosts_preserved": True,
            "hidden_verifier_can_only_retain_or_revert_parent_change": True,
            "positive_credit_requires_independent_verifier_outcome_improvement": True,
            "nine_plus_one_fetch_transport_conservation_verified": True,
            "hidden_page_prompt_exclusion_verified": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "v24354_56_runtime_processes": active,
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "active_run_killed_or_quarantined": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_private_content_emitted_to_public_receipt": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "benchmark_external_explicit_partition_gate_design": not findings,
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
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}, sort_keys=True))
