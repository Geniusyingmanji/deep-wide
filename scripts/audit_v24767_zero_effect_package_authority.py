#!/usr/bin/env python3
"""One-shot authority for generating the inert V2.47.66 package audit.

This clean-head audit closes the deliberate authorization gap left by
V2.47.64.  Its only positive authority is publication of the V2.47.66
package-audit artifact from the exact pushed source set.  It neither generates
that artifact itself nor authorizes preactivation, launch, private truth,
quality, evaluator, dev64, exact-220, entropy-credit, or leaderboard work.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24765_zero_effect_execution_contract as contract  # noqa: E402


OUTPUT = Path(
    "results/v24767_zero_effect_package_audit_authority_v1_20260807.json"
)
READINESS = contract.READINESS
PACKAGE_AUDIT = contract.PACKAGE_BUILD
SOURCE_AUDIT = Path("scripts/audit_v24766_zero_effect_package_build.py")
SOURCE_AUTHORITY = Path("scripts/audit_v24767_zero_effect_package_authority.py")
TEST_AUTHORITY = Path("tests/test_audit_v24767_zero_effect_package_authority.py")
RUNNER_MARKERS = (
    "scripts/run_v24765_zero_effect_external.py",
    "scripts/run_v24765_zero_effect_task.py",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _package_module():
    from scripts import audit_v24766_zero_effect_package_build as package

    return package


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.67 expected repository file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.67 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _parents_valid() -> bool:
    readiness = _read(READINESS)
    protocol = _read(contract.PROTOCOL)
    return bool(
        readiness.get("role") == "v24764_control_plane_build_readiness"
        and readiness.get("audit_valid") is True
        and readiness.get("findings") == []
        and readiness.get("authorization", {}).get(
            "v24766_package_audit_source_implementation"
        )
        is True
        and readiness.get("authorization", {}).get(
            "package_audit_artifact_generation"
        )
        is False
        and readiness.get("authorization", {}).get("external_launch") is False
        and _sealed(readiness, "audit_payload_sha256")
        and protocol.get("role")
        == "v24763_corrected_zero_effect_external_preregistration"
        and protocol.get("protocol_id") == contract.PROTOCOL_ID
        and protocol.get("task_contract", {}).get("runtime_input_keys")
        == ["opaque_id", "question"]
        and protocol.get("authorization", {}).get("package_audit_generation")
        is False
        and protocol.get("authorization", {}).get("one_external_forward_launch")
        is False
        and _sealed(protocol, "protocol_payload_sha256")
    )


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    package = _package_module()
    rows: list[dict[str, Any]] = []
    observed = 0
    passed = True
    for path, expected, timeout in package.TEST_SUITES:
        ok, count, output_sha = package._run_test(path, timeout)
        row = {
            "path": str(path),
            "expected": expected,
            "observed": count,
            "output_sha256": output_sha,
            "passed": ok and count == expected,
        }
        rows.append(row)
        observed += count
        passed = passed and row["passed"]
    return observed, passed and observed == package.EXPECTED_TEST_COUNT, rows


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active_runners() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or "python" not in parts[1].casefold():
            continue
        if any(marker in parts[2] for marker in RUNNER_MARKERS):
            output.append(int(parts[0]))
    return sorted(output)


def build_authority(*, now: int | None = None) -> dict[str, Any]:
    package = _package_module()
    sources = package.SOURCES
    manifest = {str(path): _sha256(path) for path in sources}
    fields, imports, markers, secrets = package.ast_findings()
    implementation = package.implementation_contract()
    observed, tests_passed, suites = _run_tests()
    parents = _parents_valid()
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(
        _tracked(path)
        for path in (*sources, contract.PROTOCOL, READINESS)
    )
    watchers = contract.protected_watcher_snapshot()
    lease = _lease_inactive()
    runners = _active_runners()
    package_pristine = not (ROOT / PACKAGE_AUDIT).exists() and not (
        ROOT / PACKAGE_AUDIT
    ).is_symlink()
    downstream_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (
            contract.PREAUDIT,
            contract.ACTIVATION,
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    )
    secret_hits = [
        str(path)
        for path in sources
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    findings: list[str] = []
    if not parents:
        findings.append("v24763_or_v24764_parent_drifted")
    if head != remote:
        findings.append("v24767_source_commit_not_pushed")
    if not clean:
        findings.append("v24767_source_worktree_not_clean")
    if not tracked:
        findings.append("v24767_source_not_tracked")
    if not implementation["valid"]:
        findings.append("v24765_implementation_contract_drifted")
    if fields:
        findings.append("privileged_forward_field_access")
    if imports:
        findings.append("evaluator_or_gold_import_in_forward")
    if markers:
        findings.append("private_or_evaluator_marker_in_forward")
    if secrets or secret_hits:
        findings.append("credential_literal_in_package")
    if not tests_passed or observed != package.EXPECTED_TEST_COUNT:
        findings.append("regression_failed_or_count_drifted")
    if not lease:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24765_runner_active")
    if not package_pristine or not downstream_pristine:
        findings.append("package_or_downstream_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24767_zero_effect_package_audit_authority",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "protocol_sha256": _sha256(contract.PROTOCOL),
            "readiness_sha256": _sha256(READINESS),
            "valid": parents,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "implementation_contract": implementation,
        "tests": {
            "expected": package.EXPECTED_TEST_COUNT,
            "observed": observed,
            "suites": suites,
            "passed": tests_passed,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "runtime_input_keys": ["opaque_id", "question"],
            "privileged_forward_field_accesses": fields,
            "evaluator_or_gold_imports": imports,
            "private_or_evaluator_marker_hits": markers,
            "credential_literal_hits": sorted(set(secrets) | set(secret_hits)),
            "passed": not fields
            and not imports
            and not markers
            and not secrets
            and not secret_hits,
        },
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "shared_api_lease_inactive": lease,
            "active_v24765_runner_pids": runners,
            "v24766_package_audit_surface_pristine": package_pristine,
            "downstream_surfaces_pristine": downstream_pristine,
            "external_forward_launched_by_authority": False,
            "evaluator_called_by_authority": False,
        },
        "source_policy": {
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "v24766_package_audit_artifact_generation": not findings,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["authority_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    package = _package_module()
    copied = dict(value)
    if (
        copied.get("role") != "v24767_zero_effect_package_audit_authority"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("parents", {}).get("valid") is not True
        or copied.get("implementation_contract", {}).get("valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != package.EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("git", {}).get("head_equals_target_main") is not True
        or copied.get("git", {}).get("worktree_clean") is not True
        or copied.get("git", {}).get("all_sources_tracked") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive")
        is not True
        or copied.get("runtime_state", {}).get("active_v24765_runner_pids") != []
        or copied.get("runtime_state", {}).get(
            "v24766_package_audit_surface_pristine"
        )
        is not True
        or copied.get("runtime_state", {}).get("downstream_surfaces_pristine")
        is not True
        or copied.get("authorization")
        != {
            "v24766_package_audit_artifact_generation": True,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "authority_payload_sha256")
    ):
        raise RuntimeError("V2.47.67 package authority drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
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
    authority = build_authority()
    validate_authority(authority)
    _publish(ROOT / OUTPUT, authority)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": authority["audit_valid"],
                "findings": authority["findings"],
                "package_audit_artifact_generation": authority["authorization"][
                    "v24766_package_audit_artifact_generation"
                ],
            },
            sort_keys=True,
        )
    )
