#!/usr/bin/env python3
"""Clean-build audit for the V2.46.79 fixed-denominator dev64 runtime.

This audit reads only repository sources, the aggregate-only V2.46.78 build
receipt, git/process/lease state, and synthetic non-evaluator tests.  It does
not open the visible task manifest, ID source, questions, predictions,
mapping, category, split, gold, score, reward, or evaluator resources, and it
performs no model, search, fetch, benchmark, or evaluator effect.
"""

from __future__ import annotations

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
from deepwide_agent.v24319_runner_integration import (  # noqa: E402
    validate_projected_parent_result,
)
from deepwide_agent import v24318_deadline_conservation_runtime as conservation  # noqa: E402
from deepwide_agent import v24679_schema_dev64_contract as contract  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import audit_v24678_expanded_schema_runtime_build as parent_audit  # noqa: E402
from scripts import run_v24679_schema_dev64 as runner  # noqa: E402


DATE = "20260806"
PARENT = parent_audit.AUDIT
AUDIT = Path(f"results/v24680_schema_dev64_runtime_build_audit_v1_{DATE}.json")
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24679_schema_dev64_contract.py"),
    Path("scripts/run_v24679_schema_dev64_task.py"),
    Path("scripts/run_v24679_schema_dev64.py"),
)
SOURCES = (
    PARENT,
    *RUNTIME_SOURCES,
    Path("tests/test_v24679_schema_dev64.py"),
    Path("scripts/audit_v24680_schema_dev64_runtime_build.py"),
    Path("tests/test_audit_v24680_schema_dev64_runtime_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24286_visible_schema_runtime.py"), 6, 180),
    (Path("tests/test_v24318_deadline_conservation_runtime.py"), 8, 180),
    (Path("tests/test_v24319_runner_integration.py"), 7, 180),
    (Path("tests/test_v24630_thin_backfill_search.py"), 2, 120),
    (Path("tests/test_v24630_exact220.py"), 5, 180),
    (Path("tests/test_v24675_expanded_visible_schema.py"), 8, 120),
    (Path("tests/test_v24677_expanded_visible_schema_runtime.py"), 8, 180),
    (Path("tests/test_v24679_schema_dev64.py"), 9, 180),
    (Path("tests/test_audit_v24680_schema_dev64_runtime_build.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 59


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    try:
        value = json.loads(common._ordinary(PARENT).read_text(encoding="utf-8"))
        parent_audit.validate_audit(value)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        value.get("role") == "v24678_expanded_schema_runtime_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("fresh_paired_dev64_protocol_design")
        is True
        and value.get("authorization", {}).get("fresh_paired_dev64_launch")
        is False
        and _sealed(value, "audit_payload_sha256")
    )


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
            "HOME": os.environ.get("HOME", str(Path.home())),
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


def _synthetic_task(*, treated: bool) -> dict[str, str]:
    question = (
        "Please output one Markdown table with the columns, in this exact order:\n"
        "Name | Date\nDo not omit cells."
        if treated
        else "Return one table. The column names are: Name, Date."
    )
    return {"opaque_id": "task_0123456789abcdef01234567", "question": question}


def _implementation_valid() -> bool:
    original = conservation.extract_robust_visible_columns
    frozen = _synthetic_task(treated=False)
    treated = _synthetic_task(treated=True)
    fallback = runner._fallback(
        frozen,
        failure="SyntheticFailure",
        elapsed=0.01,
        progress={},
        model_receipt=None,
        timed_out=False,
    )
    validate_projected_parent_result(fallback)
    outcome = runner.TaskOutcome(
        "baseline",
        1,
        dict(frozen),
        fallback,
        None,
        False,
        False,
        0,
        0,
        False,
        runner._empty_transport(),
        False,
        False,
    )
    row = runner._runtime_row(outcome, reused=False)
    return (
        contract.SELECTED_COUNT == 64
        and contract.EXPECTED_TREATED_COUNT == 8
        and contract.TOTAL_CHILD_RUNS == 72
        and contract.EXECUTOR_CONCURRENCY == 20
        and contract.MODEL_SLOT_CAP == 8
        and contract.is_treated_task(frozen) is False
        and contract.is_treated_task(treated) is True
        and row["status"] == "completed"
        and row["forward_success"] is False
        and bool(row["prediction"])
        and row["completion_kind"] == "worker_failure_fallback"
        and conservation.extract_robust_visible_columns is original
    )


def _active(marker: str) -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        marker in line
        for line in completed.stdout.splitlines()
        if "ps -eo" not in line and "audit_v24680" not in line
    )


def _future_pristine() -> bool:
    return not any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            contract.FORWARD_CONTRACT,
            contract.PREAUDIT,
            contract.ACTIVATION,
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = common.ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed = _run_test(path, timeout)
        suites.append(
            {
                "path": str(path),
                "expected_test_count": expected,
                "observed_test_count": observed,
                "passed": passed and observed == expected,
            }
        )
    test_count = sum(item["observed_test_count"] for item in suites)
    head = common._git("rev-parse", "HEAD")
    remote = common._git("rev-parse", "target/main")
    clean = common._git("status", "--porcelain") == ""
    tracked = all(common._tracked(path) for path in SOURCES)
    watchers = [
        {
            "pid": pid,
            "start_ticks": ticks,
            "marker": marker,
            "identity_valid": common._watcher(pid, ticks, marker),
        }
        for pid, ticks, marker in common.EXPECTED_WATCHERS
    ]
    parent_valid = _parent_valid()
    implementation_valid = _implementation_valid()
    lease_inactive = common._lease_inactive()
    active_runner = _active(contract.RUNNER_MARKER) or _active(contract.CHILD_MARKER)
    future_pristine = _future_pristine()
    findings: list[str] = []
    if head != remote:
        findings.append("v24680_source_commit_not_pushed")
    if not clean:
        findings.append("v24680_source_worktree_not_clean")
    if not tracked:
        findings.append("v24680_source_not_tracked")
    if not parent_valid:
        findings.append("v24678_build_audit_drifted")
    if not implementation_valid:
        findings.append("v24679_fixed_denominator_runtime_contract_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24679_parent_bound_regression_failed")
    if accesses:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_import_in_runtime")
    if secret_hits:
        findings.append("credential_literal_in_build_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if active_runner:
        findings.append("v24679_forward_process_already_active")
    if not future_pristine:
        findings.append("v24679_future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24680_schema_dev64_runtime_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "v24678_build_audit_path": str(PARENT),
            "v24678_build_audit_sha256": common._sha256(PARENT),
            "valid": parent_valid,
            "visible_manifest_id_source_or_question_reopened_by_build_audit": False,
        },
        "mechanism": {
            "selected_pair_tasks": contract.SELECTED_COUNT,
            "fresh_baseline_children": contract.SELECTED_COUNT,
            "fresh_candidate_children": contract.EXPECTED_TREATED_COUNT,
            "real_child_runs": contract.TOTAL_CHILD_RUNS,
            "same_run_baseline_reused_candidate_tasks": (
                contract.SELECTED_COUNT - contract.EXPECTED_TREATED_COUNT
            ),
            "failure_projects_nonempty_terminal_fallback": True,
            "fixed_denominator_per_arm": contract.SELECTED_COUNT,
            "module_global_parser_mutation": False,
            "implementation_valid": implementation_valid,
        },
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
            "suites": suites,
            "test_count": test_count,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "passed": not accesses and not imports and not secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "v24679_forward_process_active": active_runner,
            "v24679_future_surface_pristine": future_pristine,
            "dev64_or_exact220_launched_by_audit": False,
            "evaluator_called_by_audit": False,
        },
        "source_policy": {
            "mapping_gold_category_split_question_type_score_reward_or_evaluator_read": False,
            "task_question_query_url_page_prediction_or_provider_payload_opened_by_audit": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "forward_contract_publication": not findings,
            "preactivation_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24680_schema_dev64_runtime_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("parent", {}).get("valid") is not True
        or copied.get("mechanism", {}).get("implementation_valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("v24679_forward_process_active")
        is not False
        or copied.get("runtime_state", {}).get("v24679_future_surface_pristine")
        is not True
        or copied.get("authorization")
        != {
            "forward_contract_publication": True,
            "preactivation_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.80 build audit drifted")
    return copied


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
    audit = build_audit()
    validate_audit(audit)
    publish_new(ROOT / AUDIT, audit)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
                "test_count": audit["tests"]["test_count"],
            },
            sort_keys=True,
        )
    )
