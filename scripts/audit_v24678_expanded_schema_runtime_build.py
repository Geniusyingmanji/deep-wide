#!/usr/bin/env python3
"""Clean-build audit for V2.46.75/77 expanded visible-schema runtime.

The audit binds the frozen aggregate-only full-220 coverage receipt, runtime
sources, git/process/lease state, and non-evaluator tests.  It does not open
the visible manifest, task questions, mapping, category, split, gold,
predictions, scores, rewards, or evaluator surfaces, and it performs no model,
search, fetch, benchmark, or evaluator effect.
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
from deepwide_agent import v24318_deadline_conservation_runtime as conservation  # noqa: E402
from deepwide_agent import v24677_expanded_visible_schema_runtime as runtime  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import audit_v24676_full220_visible_schema_coverage as coverage  # noqa: E402


DATE = "20260806"
PARENT = coverage.OUTPUT
AUDIT = Path(f"results/v24678_expanded_schema_runtime_build_audit_v1_{DATE}.json")
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24675_expanded_visible_schema.py"),
    Path("src/deepwide_agent/v24677_expanded_visible_schema_runtime.py"),
)
SOURCES = (
    PARENT,
    *RUNTIME_SOURCES,
    Path("tests/test_v24675_expanded_visible_schema.py"),
    Path("tests/test_v24677_expanded_visible_schema_runtime.py"),
    Path("scripts/audit_v24678_expanded_schema_runtime_build.py"),
    Path("tests/test_audit_v24678_expanded_schema_runtime_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24286_visible_schema_runtime.py"), 6, 180),
    (Path("tests/test_v24318_deadline_conservation_runtime.py"), 8, 180),
    (Path("tests/test_v24319_runner_integration.py"), 7, 180),
    (Path("tests/test_v24630_thin_backfill_search.py"), 2, 120),
    (Path("tests/test_v24675_expanded_visible_schema.py"), 8, 120),
    (Path("tests/test_v24677_expanded_visible_schema_runtime.py"), 8, 180),
    (Path("tests/test_audit_v24678_expanded_schema_runtime_build.py"), 5, 120),
)
EXPECTED_TEST_COUNT = 44


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    try:
        value = json.loads(common._ordinary(PARENT).read_text(encoding="utf-8"))
        coverage.validate_audit(value)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        value.get("coverage", {}).get("fixed_visible_task_denominator") == 220
        and value.get("coverage", {}).get("frozen_parser_covered_task_count") == 194
        and value.get("coverage", {}).get("expanded_parser_covered_task_count") == 215
        and value.get("coverage", {}).get("newly_covered_task_count") == 21
        and value.get("coverage", {}).get("already_covered_task_changed_count") == 0
        and value.get("coverage", {}).get("explicit_ror_namespace_task_count") == 0
        and value.get("authorization")
        == {
            "concurrency_safe_runtime_integration_implementation": True,
            "fresh_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
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


def _implementation_valid() -> bool:
    frozen = "Return one table. The column names are: Name, Date."
    treated = (
        "Please output one Markdown table with the columns, in this exact order:\n"
        "Name | Date\nDo not omit cells."
    )
    absent = "Return a useful table without an explicit field declaration."
    frozen_transition = runtime._transition(frozen)[2]
    treated_transition = runtime._transition(treated)[2]
    absent_transition = runtime._transition(absent)[2]
    original = conservation.extract_robust_visible_columns
    isolated = runtime._isolated_conservation_task()
    isolated_parent = isolated.__globals__.get("_run_parent")
    return (
        runtime.validate_receipt(frozen_transition)["status"]
        == "frozen_schema_preserved"
        and runtime.validate_receipt(treated_transition)["status"]
        == "incremental_explicit_schema"
        and runtime.validate_receipt(absent_transition)["status"]
        == "no_unambiguous_explicit_schema"
        and isolated is not conservation.run_v24318_task
        and callable(isolated_parent)
        and isolated_parent is not conservation._run_parent
        and conservation.extract_robust_visible_columns is original
        and isolated_parent.__globals__.get("extract_robust_visible_columns")
        is not original
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
    findings: list[str] = []
    if head != remote:
        findings.append("v24678_source_commit_not_pushed")
    if not clean:
        findings.append("v24678_source_worktree_not_clean")
    if not tracked:
        findings.append("v24678_source_not_tracked")
    if not parent_valid:
        findings.append("v24676_coverage_audit_drifted")
    if not implementation_valid:
        findings.append("v24677_task_local_runtime_contract_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24286_24318_24319_24630_24675_24677_24678_regression_failed")
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

    value = {
        "artifact_version": 1,
        "role": "v24678_expanded_schema_runtime_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "v24676_coverage_path": str(PARENT),
            "v24676_coverage_sha256": common._sha256(PARENT),
            "valid": parent_valid,
            "visible_manifest_or_question_reopened_by_build_audit": False,
        },
        "mechanism": {
            "runtime_policy": runtime.POLICY_ID,
            "frozen_parser_precedence": True,
            "incremental_explicit_schema_only_when_frozen_parser_empty": True,
            "already_covered_task_behavior_preserved": True,
            "ambiguous_or_absent_declaration_fails_closed": True,
            "task_local_function_namespace": True,
            "module_global_parser_mutation": False,
            "eight_way_mixed_concurrency_regression": True,
            "model_query_fetch_token_deadline_search_or_title_backfill_changed": False,
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
            "fresh_paired_dev64_protocol_design": not findings,
            "fresh_paired_dev64_launch": False,
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
        copied.get("role") != "v24678_expanded_schema_runtime_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("parent", {}).get("valid") is not True
        or copied.get("mechanism", {}).get("implementation_valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("authorization")
        != {
            "fresh_paired_dev64_protocol_design": True,
            "fresh_paired_dev64_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.78 build audit drifted")
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
