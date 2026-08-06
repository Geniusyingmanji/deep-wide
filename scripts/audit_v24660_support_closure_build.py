#!/usr/bin/env python3
"""Clean-build audit for the inert V2.46.59 support-closure candidate."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent import v24659_support_closure_runtime as runtime  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from deepwide_agent.v24657_forward_contract import protected_watcher_snapshot  # noqa: E402


DATE = "20260806"
PARENT_RESULT = Path(f"results/v24657_paired_dev64_result_v1_{DATE}.json")
PARENT_AUDIT = Path(f"results/v24657_paired_dev64_postresult_audit_v1_{DATE}.json")
AUDIT = Path(f"results/v24660_support_closure_build_audit_v1_{DATE}.json")
SOURCES = (
    PARENT_RESULT,
    PARENT_AUDIT,
    Path("src/deepwide_agent/v24655_unknown_cell_targeted_runtime.py"),
    Path("src/deepwide_agent/v24659_support_closure_runtime.py"),
    Path("tests/test_v24655_unknown_cell_targeted_runtime.py"),
    Path("tests/test_v24659_support_closure_runtime.py"),
    Path("scripts/audit_v24660_support_closure_build.py"),
    Path("tests/test_audit_v24660_support_closure_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24655_unknown_cell_targeted_runtime.py"), 8),
    (Path("tests/test_v24659_support_closure_runtime.py"), 7),
    (Path("tests/test_audit_v24660_support_closure_build.py"), 6),
)
EXPECTED_TEST_COUNT = 21
PRIVILEGED = frozenset(
    {
        "benchmark_question_type", "question_type", "task_category", "category",
        "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator",
        "score", "reward", "results.csv",
    }
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: str | Path) -> Path:
    raw = Path(relative)
    path = ROOT / raw
    if raw.is_absolute() or ".." in raw.parts or path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.46.60 expected ordinary file: {relative}")
    return path


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with _ordinary(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
        check=False,
    ).returncode == 0


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    result = json.loads(_ordinary(PARENT_RESULT).read_text(encoding="utf-8"))
    audit = json.loads(_ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    return (
        result.get("role") == "v24657_unknown_cell_targeted_paired_dev64_result"
        and result.get("status") == "development_gate_no_go"
        and _sealed(result, "result_payload_sha256")
        and result.get("mechanism", {}).get("selected_unknown_target_tasks") == 15
        and result.get("mechanism", {}).get("changed_candidate_tasks") == 0
        and result.get("mechanism", {}).get("admitted_cell_changes") == 0
        and result.get("mechanism", {}).get("entropy_task_credit_nats") == 0.0
        and audit.get("role")
        == "v24657_unknown_cell_targeted_paired_dev64_postresult_audit"
        and audit.get("audit_valid") is True
        and audit.get("findings") == []
        and audit.get("authorization", {}).get("fresh_exact220_design") is False
        and audit.get("authorization", {}).get("fresh_exact220_launch") is False
        and _sealed(audit, "audit_payload_sha256")
    )


def _ast_findings() -> tuple[list[str], list[str]]:
    path = _ordinary("src/deepwide_agent/v24659_support_closure_runtime.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fields: list[str] = []
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
            fields.append(f"{path}:{node.lineno}:{key}")
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            names = []
        imports.extend(
            f"{path}:{name}"
            for name in names
            if any(token in name.casefold() for token in ("evaluator", "mapping", "gold"))
        )
    return sorted(fields), sorted(imports)


def _run_test(path: Path) -> tuple[bool, int]:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
         "discover", "-s", "tests", "-p", path.name],
        cwd=ROOT,
        env={
            "HOME": str(Path.home()), "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=180, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode == 0, int(match.group(1)) if match else 0


def _implementation_valid() -> bool:
    closure = runtime.deterministic_support_closure(
        row_key="Alpha Phone",
        new_value="2024-09-20",
        declared_evidence_ids=["R0001"],
        targeted_pages=[
            {
                "evidence_id": f"R{index:04d}",
                "host": f"source-{index}.example",
                "content": "Alpha Phone official Release Date 2024-09-20",
            }
            for index in (1, 2)
        ],
    )
    return (
        runtime.MINIMUM_INDEPENDENT_SUPPORT_SOURCES == 2
        and closure["closed_evidence_ids"] == ["R0001", "R0002"]
        and closure["added_evidence_id_count"] == 1
        and closure["minimum_independent_support_sources_unchanged"] is True
        and closure["uses_only_already_fetched_targeted_pages"] is True
        and closure["proposal_value_changed"] is False
        and closure[
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        ]
        is False
        and closure["entropy_or_task_credit_used"] is False
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in SOURCES}
    fields, imports = _ast_findings()
    suites: list[dict[str, Any]] = []
    for path, expected in TEST_SUITES:
        passed, observed = _run_test(path)
        suites.append(
            {"path": str(path), "expected_test_count": expected,
             "observed_test_count": observed, "passed": passed and observed == expected}
        )
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    parent_valid = _parent_valid()
    implementation_valid = _implementation_valid()
    lease = lease_observation(ROOT, Path("/proc"))
    watchers = protected_watcher_snapshot()
    secret_hits = [
        str(path) for path in SOURCES
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    findings: list[str] = []
    if head != remote: findings.append("v24660_source_commit_not_pushed")
    if not clean: findings.append("v24660_source_worktree_not_clean")
    if not all(_tracked(path) for path in SOURCES): findings.append("v24660_source_not_tracked")
    if not parent_valid: findings.append("v24657_no_go_parent_drifted")
    if not implementation_valid: findings.append("v24659_support_closure_contract_drifted")
    if fields: findings.append("privileged_runtime_field_access")
    if imports: findings.append("evaluator_or_gold_import_in_runtime")
    if secret_hits: findings.append("credential_literal_in_build_surface")
    if any(not suite["passed"] for suite in suites): findings.append("regression_failed_or_count_drifted")
    if sum(suite["observed_test_count"] for suite in suites) != EXPECTED_TEST_COUNT:
        findings.append("total_test_count_drifted")
    if lease.get("active") is not False: findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24660_support_closure_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "v24657_result_sha256": _sha256(PARENT_RESULT),
            "v24657_postaudit_sha256": _sha256(PARENT_AUDIT),
            "valid_no_go": parent_valid,
            "exact220_authorized": False,
        },
        "mechanism": {
            "policy_id": runtime.POLICY_ID,
            "minimum_independent_support_sources": 2,
            "support_threshold_relaxed": False,
            "proposal_value_changed_by_closure": False,
            "new_search_fetch_or_model_effect": False,
            "closure_uses_only_already_fetched_targeted_pages": True,
            "entropy_or_task_credit_used": False,
            "implementation_valid": implementation_valid,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {"head": head, "target_main": remote,
                "head_equals_target_main": head == remote, "worktree_clean": clean,
                "all_sources_tracked": all(_tracked(path) for path in SOURCES)},
        "tests": {"suites": suites,
                  "test_count": sum(suite["observed_test_count"] for suite in suites),
                  "passed": all(suite["passed"] for suite in suites),
                  "network_model_search_fetch_benchmark_or_evaluator_called": False},
        "label_blind_audit": {
            "runtime_boundary": ["opaque_id", "question", "same_pass_targeted_pages"],
            "privileged_runtime_field_accesses": fields,
            "evaluator_or_gold_imports": imports,
            "credential_literal_hits": secret_hits,
            "passed": not fields and not imports and not secret_hits,
        },
        "runtime_state": {"shared_api_lease_active": lease.get("active"),
                          "protected_watchers": watchers,
                          "benchmark_launched_by_audit": False,
                          "evaluator_called_by_audit": False},
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_external_design": not findings,
            "fresh_external_launch": False,
            "paired_dev64_design": False,
            "paired_dev64_launch": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24660_support_closure_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("mechanism", {}).get("implementation_valid") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_active") is not False
        or copied.get("authorization")
        != {"fresh_external_design": True, "fresh_external_launch": False,
            "paired_dev64_design": False, "paired_dev64_launch": False,
            "exact220": False, "leaderboard_or_sota": False}
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.60 build audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    validate_audit(value)
    publish_new(ROOT / AUDIT, value)
    print(json.dumps({"path": str(AUDIT), "audit_valid": value["audit_valid"],
                      "findings": value["findings"],
                      "test_count": value["tests"]["test_count"]}, sort_keys=True))
