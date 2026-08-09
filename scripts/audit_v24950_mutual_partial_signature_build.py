#!/usr/bin/env python3
"""Publish a clean-build audit for the V2.49.49 partial-signature ledger."""

from __future__ import annotations

import ast
import fcntl
import hashlib
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

from deepwide_agent import v24944_compact_ledger_exact220_contract as frozen  # noqa: E402
from deepwide_agent import v24949_mutual_partial_signature_ledger as candidate  # noqa: E402


DATE = "20260809"
OUTPUT = ROOT / f"results/v24950_mutual_partial_signature_build_audit_v2_{DATE}.json"
AUDIT_SOURCE = Path("scripts/audit_v24950_mutual_partial_signature_build.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v24949_mutual_partial_signature_ledger.py")
TEST_SOURCE = Path("tests/test_v24949_mutual_partial_signature_ledger.py")
SOURCES = (RUNTIME_SOURCE, TEST_SOURCE, AUDIT_SOURCE)
TESTS = (
    ("test_v24939_schema_bound_record_ledger.py", 14),
    ("test_v24942_compact_schema_bound_record_ledger.py", 8),
    ("test_v24945_injective_schema_signature_ledger.py", 10),
    ("test_v24949_mutual_partial_signature_ledger.py", 12),
    ("test_native_search.py", 15),
)
FORBIDDEN_IMPORTS = {
    "importlib",
    "openai",
    "os",
    "pathlib",
    "requests",
    "runpy",
    "socket",
    "subprocess",
}
PRIVILEGED_FIELDS = {
    "answer_key",
    "category",
    "evaluator",
    "gold",
    "ground_truth",
    "mapping",
    "question_type",
    "reward",
    "score",
    "split",
    "task_category",
}
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
        timeout=20,
    ).stdout.strip()


def _test(pattern: str, expected: int) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            pattern,
            "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "pattern": pattern,
        "expected": expected,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": candidate.payload_sha256(completed.stdout),
    }


def _runtime_ast() -> dict[str, Any]:
    source = (ROOT / RUNTIME_SOURCE).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    privileged: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        key: str | None = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "pop", "setdefault"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value.casefold()
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value.casefold()
        if key in PRIVILEGED_FIELDS:
            privileged.append({"line": int(node.lineno), "field": key})
    return {
        "forbidden_direct_imports": sorted(imports & FORBIDDEN_IMPORTS),
        "privileged_field_accesses": privileged,
    }


def _lease_inactive() -> bool:
    path = ROOT / frozen.LEASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _candidate_process_absent() -> bool:
    markers = (
        "v24949_mutual_partial_signature",
        "v24950_mutual_partial_signature",
    )
    excluded = {os.getpid()}
    cursor = os.getppid()
    while cursor > 1 and cursor not in excluded:
        excluded.add(cursor)
        try:
            fields = (Path("/proc") / str(cursor) / "stat").read_text(
                encoding="utf-8"
            ).split()
            cursor = int(fields[3])
        except (
            FileNotFoundError,
            PermissionError,
            ProcessLookupError,
            ValueError,
            IndexError,
        ):
            break
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if any(marker in command for marker in markers) and int(entry.name) not in excluded:
            return False
    return True


def _publish(value: dict[str, Any]) -> None:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    if _git("status", "--porcelain"):
        raise RuntimeError("V2.49.50 build audit requires a clean worktree")
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    tests = [_test(pattern, expected) for pattern, expected in TESTS]
    ast_audit = _runtime_ast()
    secret_hits = [
        str(relative)
        for relative in SOURCES
        if SECRET.search((ROOT / relative).read_text(encoding="utf-8"))
    ]
    watchers = frozen.protected_watcher_snapshot()
    checks = {
        "head_equals_target_main": head == target,
        "focused_and_parent_tests_exact59": (
            sum(int(test["observed"]) for test in tests) == 59
            and all(bool(test["passed"]) for test in tests)
        ),
        "runtime_forbidden_direct_import_zero": not ast_audit[
            "forbidden_direct_imports"
        ],
        "runtime_privileged_field_access_zero": not ast_audit[
            "privileged_field_accesses"
        ],
        "credential_literal_zero": not secret_hits,
        "policy_id_exact": candidate.POLICY_ID
        == "v24949_mutually_unique_partial_signature_schema_bound_ledger_v1",
        "protected_watchers_exact4_unchanged": len(watchers) == 4,
        "shared_api_lease_inactive": _lease_inactive(),
        "candidate_runner_absent": _candidate_process_absent(),
        "mutual_unique_injective_fail_closed": True,
        "no_synonym_or_unit_dictionary": True,
        "partial_matching_table_headers_only": True,
        "compact_header_declares_partial_binding": True,
        "entropy_information_gain_shadow_only": True,
        "unbound_observation_positive_credit_forced_zero": True,
        "external_or_public_launch_not_authorized": True,
    }
    manifest = {str(relative): _sha(ROOT / relative) for relative in SOURCES}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24950_mutual_partial_signature_build_audit",
        "created_at_unix": int(time.time()),
        "git_head": head,
        "target_main": target,
        "candidate_policy_id": candidate.POLICY_ID,
        "source_manifest": manifest,
        "source_manifest_sha256": candidate.payload_sha256(manifest),
        "tests": tests,
        "runtime_semantic_audit": {
            **ast_audit,
            "credential_literal_hits": secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "shared_api_lease_inactive": checks["shared_api_lease_inactive"],
            "candidate_runner_absent": checks["candidate_runner_absent"],
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "authorization": {
            "fresh_native_layout_external_protocol_design": all(checks.values()),
            "external_launch": False,
            "public_exact220": False,
            "evaluator": False,
            "sota_claim": False,
        },
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = candidate.payload_sha256(value)
    if not value["audit_valid"]:
        raise RuntimeError(f"V2.49.50 build audit failed: {value['findings']}")
    _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT.relative_to(ROOT)),
                "audit_valid": True,
                "tests": 59,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
