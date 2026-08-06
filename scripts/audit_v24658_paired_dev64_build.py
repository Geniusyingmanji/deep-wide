#!/usr/bin/env python3
"""Clean-build audit for the V2.46.57 paired-dev64 execution surface.

This audit is repository-local and content-free: it reads tracked source,
Git state, process identities, and the shared lease only.  It performs no
network, model, search, fetch, benchmark, mapping, or evaluator operation.
"""

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

from deepwide_agent.v24657_forward_contract import (  # noqa: E402
    EXECUTOR_CONCURRENCY,
    MODEL_SLOT_CAP,
    PROTECTED_WATCHERS,
    PROTOCOL_ID,
    SELECTED_COUNT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts import v24657_unknown_cell_targeted_dev64_control as control  # noqa: E402


DATE = "20260806"
AUDIT = Path(f"results/v24658_paired_dev64_build_audit_v1_{DATE}.json")
SOURCES = tuple(Path(value) for value in (*control.FORWARD_FILES, *control.CONTROL_FILES)) + (
    Path("scripts/audit_v24658_paired_dev64_build.py"),
    Path("tests/test_audit_v24658_paired_dev64_build.py"),
)
EXPECTED_SOURCES = 53
TEST_SUITES = (
    (Path("tests/test_v24655_unknown_cell_targeted_runtime.py"), 8, 180),
    (Path("tests/test_v24657_runner_integration.py"), 3, 180),
    (Path("tests/test_v24657_unknown_cell_targeted_dev64.py"), 12, 180),
    (Path("tests/test_audit_v24658_paired_dev64_build.py"), 7, 180),
)
EXPECTED_TEST_COUNT = 30
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
REQUIRED_FINALIZER_FUNCTIONS = frozenset(
    {
        "validate_evaluator_gate",
        "validate_evaluator_start",
        "validate_final_result",
        "validate_postaudit",
    }
)


def _ordinary(relative: str | Path) -> Path:
    raw = Path(relative)
    path = ROOT / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.46.58 expected ordinary file: {relative}")
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


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _run_test(path: Path, timeout: int) -> tuple[bool, int]:
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
            path.name,
        ],
        cwd=ROOT,
        env={
            "HOME": str(Path.home()),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode == 0, int(match.group(1)) if match else 0


def _finalizer_findings() -> list[str]:
    path = _ordinary("scripts/finalize_v24657_unknown_cell_targeted_dev64.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    findings = [
        f"missing:{name}"
        for name in sorted(REQUIRED_FINALIZER_FUNCTIONS - set(functions))
    ]
    build = functions.get("build_postaudit")
    if build is not None:
        for node in ast.walk(build):
            if (
                isinstance(node, ast.Dict)
                and any(
                    isinstance(key, ast.Constant)
                    and key.value == "shared_api_lease_active"
                    and isinstance(value, ast.Constant)
                    and value.value is False
                    for key, value in zip(node.keys, node.values, strict=True)
                )
            ):
                findings.append("postaudit_shared_lease_hardcoded_false")
    return sorted(findings)


def _implementation_valid() -> bool:
    return (
        SELECTED_COUNT == 64
        and EXECUTOR_CONCURRENCY == 16
        and MODEL_SLOT_CAP == 8
        and control.DECISION_CONTRACT["minimum_whole_table_success_delta"] == 1
        and control.DECISION_CONTRACT[
            "required_credited_conditional_entropy_reduction_nats"
        ]
        == 0.0
        and control.DECISION_CONTRACT["maximum_failed_pair_tasks"] == 0
        and control.EVALUATOR_WORKERS_PER_ARM == 4
        and control.TOTAL_EVALUATOR_WORKERS == 8
        and not control._field_accesses(ROOT)
        and not control._import_hits(ROOT)
        and not _finalizer_findings()
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): sha256(_ordinary(path)) for path in SOURCES}
    test_rows: list[dict[str, Any]] = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed = _run_test(path, timeout)
        test_rows.append(
            {
                "path": str(path),
                "expected_test_count": expected,
                "observed_test_count": observed,
                "passed": passed and observed == expected,
            }
        )
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    fields = control._field_accesses(ROOT)
    imports = control._import_hits(ROOT)
    finalizer_findings = _finalizer_findings()
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    implementation_valid = _implementation_valid()
    findings: list[str] = []
    if len(SOURCES) != EXPECTED_SOURCES or len(manifest) != EXPECTED_SOURCES:
        findings.append("source_count_drifted")
    if head != remote:
        findings.append("v24658_source_commit_not_pushed")
    if not clean:
        findings.append("v24658_source_worktree_not_clean")
    if not tracked:
        findings.append("v24658_source_not_tracked")
    if any(not row["passed"] for row in test_rows):
        findings.append("v24655_57_58_regression_failed_or_count_drifted")
    if sum(row["observed_test_count"] for row in test_rows) != EXPECTED_TEST_COUNT:
        findings.append("total_test_count_drifted")
    if fields:
        findings.append("privileged_forward_field_access")
    if imports:
        findings.append("evaluator_import_in_forward_surface")
    if finalizer_findings:
        findings.append("finalizer_freeze_or_observation_validator_drifted")
    if secret_hits:
        findings.append("credential_literal_in_build_surface")
    if not implementation_valid:
        findings.append("v24657_implementation_contract_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if watchers != [
        {"pid": pid, "marker": marker, "start_ticks": ticks}
        for (pid, marker), ticks in zip(
            PROTECTED_WATCHERS, (713986317, 747569004), strict=True
        )
    ]:
        findings.append("protected_watcher_identity_drifted")

    value = {
        "artifact_version": 1,
        "role": "v24658_paired_dev64_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "suites": test_rows,
            "test_count": sum(row["observed_test_count"] for row in test_rows),
            "passed": all(row["passed"] for row in test_rows)
            and sum(row["observed_test_count"] for row in test_rows)
            == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "runtime_boundary": ["opaque_id", "question"],
            "privileged_forward_field_accesses": fields,
            "evaluator_imports": imports,
            "credential_literal_hits": secret_hits,
            "passed": not fields and not imports and not secret_hits,
        },
        "mechanism": {
            "selected_pair_tasks": SELECTED_COUNT,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "one_shared_forward_two_frozen_arms": True,
            "fixed_total_model_query_fetch_caps": [3, 4, 10],
            "candidate_is_unknown_cell_targeted": True,
            "entropy_task_credit_nats": 0.0,
            "quality_cost_pareto_not_entropy_ablation": True,
            "whole_table_success_delta_required": 1,
            "all_quality_metrics_nonregression_required": True,
            "failure_as_zero": True,
            "resume_skip_selective_retry_or_revaluation": False,
            "finalizer_findings": finalizer_findings,
            "implementation_valid": implementation_valid,
        },
        "runtime_state": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "benchmark_launched_by_audit": False,
            "evaluator_called_by_audit": False,
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_question_query_url_page_prediction_or_provider_payload_opened_by_audit": False,
            "network_model_search_fetch_benchmark_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "forward_contract_design": not findings,
            "protocol_design": not findings,
            "preactivation_audit_design": not findings,
            "activation_or_forward_launch": False,
            "evaluator_access": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    audit = dict(value)
    unsigned = dict(audit)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        audit.get("artifact_version") != 1
        or audit.get("role") != "v24658_paired_dev64_build_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or audit.get("authorization")
        != {
            "forward_contract_design": True,
            "protocol_design": True,
            "preactivation_audit_design": True,
            "activation_or_forward_launch": False,
            "evaluator_access": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or audit.get("source_policy")
        != {
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_question_query_url_page_prediction_or_provider_payload_opened_by_audit": False,
            "network_model_search_fetch_benchmark_or_evaluator_called_by_audit": False,
        }
        or audit.get("runtime_state", {}).get("shared_api_lease_active") is not False
        or audit.get("tests", {}).get("passed") is not True
        or audit.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or audit.get("label_blind_audit", {}).get("passed") is not True
        or audit.get("mechanism", {}).get("implementation_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.46.58 build audit drifted")
    return audit


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    validate_audit(value)
    publish_new(ROOT / AUDIT, value)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "test_count": value["tests"]["test_count"],
            },
            sort_keys=True,
        )
    )
