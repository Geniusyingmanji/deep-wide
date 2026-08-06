#!/usr/bin/env python3
"""Clean-build audit for the V2.46.73 staged activation control.

This audit reads only repository sources, the public frozen protocol/package
audit, git/process/lease state, and non-evaluator tests.  It never opens or
hashes private population, gold, provenance, mapping, score, or evaluator
surfaces and performs no model, search, fetch, benchmark, or evaluator effect.
"""

from __future__ import annotations

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

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent import v24671_ror_external_contract as contract  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import control_v24673_v24671_activation as control  # noqa: E402


DATE = "20260806"
AUDIT = Path(
    f"results/v24673_v24671_activation_control_build_audit_v1_{DATE}.json"
)
PACKAGE_BUILD = Path(f"results/v24672_external_package_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("scripts/control_v24673_v24671_activation.py"),
    Path("tests/test_control_v24673_v24671_activation.py"),
    Path("scripts/audit_v24673_v24671_activation_control_build.py"),
    Path("tests/test_audit_v24673_v24671_activation_control_build.py"),
    PACKAGE_BUILD,
    contract.PROTOCOL,
)
TEST_SUITES = control.CONTROL_TESTS
EXPECTED_TEST_COUNT = control.EXPECTED_TESTS


def _protocol_valid() -> bool:
    try:
        value = control._validate_protocol()
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        return False
    return (
        value.get("protocol_id") == contract.PROTOCOL_ID
        and value.get("task_contract", {}).get("runtime_input_keys")
        == ["opaque_id", "question"]
        and value.get("mechanism", {}).get(
            "postfreeze_outer_utility_design_requires_positive_epistemic_credit_and_safe_admission"
        )
        is True
    )


def _package_valid() -> bool:
    try:
        value = control._validate_package()
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        return False
    return (
        value.get("audit_valid") is True
        and value.get("label_blind_audit", {}).get("passed") is True
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


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    accesses, imports = common.ast_findings(SOURCES[0])
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
    future = (
        contract.PREAUDIT,
        contract.ACTIVATION,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    future_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in future
    )
    lease_inactive = common._lease_inactive()
    protocol_valid = _protocol_valid()
    package_valid = _package_valid()
    findings: list[str] = []
    if head != remote:
        findings.append("v24673_source_commit_not_pushed")
    if not clean:
        findings.append("v24673_source_worktree_not_clean")
    if not tracked:
        findings.append("v24673_source_not_tracked")
    if not protocol_valid:
        findings.append("v24671_protocol_invalid")
    if not package_valid:
        findings.append("v24672_package_build_invalid")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24668_71_73_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24673_control")
    if imports:
        findings.append("evaluator_import_in_v24673_control")
    if secret_hits:
        findings.append("credential_literal_in_v24673_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not future_pristine:
        findings.append("v24671_future_surface_not_pristine")

    value = {
        "artifact_version": 1,
        "role": "v24673_v24671_activation_control_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": common._sha256(contract.PROTOCOL),
        "package_build_sha256": common._sha256(PACKAGE_BUILD),
        "control": {
            "stages": ["audit", "activate", "start"],
            "run_evaluate_resume_retry_or_protocol_publication_command_present": False,
            "preactivation_excludes_evaluator_and_surface_builder_test_suites": True,
            "preactivation_opens_or_hashes_private_population_gold_provenance_mapping_score_or_evaluator": False,
            "activation_only_authorizes_execution_start_generation": True,
            "execution_start_only_stage_authorizing_one_external_forward": True,
            "outer_utility_requires_positive_epistemic_credit_and_safe_admission": True,
            "runtime_input_contract": ["opaque_id", "question"],
            "protocol_valid": protocol_valid,
            "package_build_valid": package_valid,
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
            "privileged_control_field_accesses": sorted(accesses),
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
            "future_surface_pristine": future_pristine,
            "external_forward_launched": False,
            "evaluator_called": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "preactivation_audit_generation": not findings,
            "activation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
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
