#!/usr/bin/env python3
"""Clean-build audit for the V2.46.97 staged activation control."""

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

from deepwide_agent.v24694_worldbank_external_contract import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    OUTPUT_ROOT,
    PREAUDIT,
    PROTOCOL,
    PROTOCOL_ID,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts import control_v24697_v24694_worldbank_activation as control  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


DATE = "20260806"
AUDIT = control.CONTROL_BUILD
PACKAGE_BUILD = control.PACKAGE_BUILD
SOURCES = (
    Path("scripts/control_v24697_v24694_worldbank_activation.py"),
    Path("tests/test_control_v24697_v24694_worldbank_activation.py"),
    Path("scripts/audit_v24698_v24694_activation_control_build.py"),
    Path("tests/test_audit_v24698_v24694_activation_control_build.py"),
    PACKAGE_BUILD,
    PROTOCOL,
)
TEST_SUITES = control.CONTROL_TESTS
EXPECTED_TEST_COUNT = control.EXPECTED_TESTS


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


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): sha256(ROOT / path) for path in SOURCES}
    fields, imports, markers, secrets = control._forward_findings()
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
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    try:
        protocol_valid = control._validate_protocol()["task_contract"]["runtime_input_keys"] == [
            "opaque_id",
            "question",
        ]
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        protocol_valid = False
    try:
        package_valid = control._validate_package().get("audit_valid") is True
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        package_valid = False
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    future = (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    future_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in future
    )
    findings: list[str] = []
    if head != remote:
        findings.append("v24698_source_commit_not_pushed")
    if not clean:
        findings.append("v24698_source_worktree_not_clean")
    if not tracked:
        findings.append("v24698_source_not_tracked")
    if not protocol_valid:
        findings.append("v24694_protocol_invalid")
    if not package_valid:
        findings.append("v24696_package_build_invalid")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24686_94_97_98_regression_failed_or_count_drifted")
    if fields:
        findings.append("privileged_field_access_in_v24694_forward")
    if imports:
        findings.append("evaluator_gold_or_provenance_import_in_v24694_forward")
    if markers:
        findings.append("private_or_evaluator_marker_in_v24694_forward")
    if secrets:
        findings.append("credential_literal_in_v24694_forward")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not future_pristine:
        findings.append("v24694_future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24698_v24694_activation_control_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "package_build_sha256": sha256(ROOT / PACKAGE_BUILD),
        "control": {
            "stages": ["audit", "activate", "start"],
            "run_evaluate_resume_retry_or_protocol_publication_command_present": False,
            "preactivation_excludes_evaluator_test_suite": True,
            "preactivation_opens_or_hashes_private_population_gold_provenance_mapping_score_or_evaluator": False,
            "activation_only_authorizes_execution_start_generation": True,
            "execution_start_only_stage_authorizing_one_external_forward": True,
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
            "privileged_forward_field_accesses": fields,
            "evaluator_gold_or_provenance_imports": imports,
            "private_or_evaluator_markers": markers,
            "credential_literal_hits": secrets,
            "passed": not fields and not imports and not markers and not secrets,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "shared_api_lease_inactive": lease.get("active") is False,
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


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != "v24698_v24694_activation_control_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "activation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.46.98 control build audit drifted")
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
    if value["findings"]:
        raise RuntimeError("V2.46.98 control build audit rejected")
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
