#!/usr/bin/env python3
"""Build-only audit authorizing one V2.46.91 separated surface publication."""

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
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import build_v24691_worldbank_surfaces as builder  # noqa: E402


DATE = "20260806"
AUDIT = builder.AUTHORIZATION
SOURCES = (
    builder.design.PRIVATE,
    builder.design.OUTPUT,
    Path("scripts/build_v24691_worldbank_surfaces.py"),
    Path("tests/test_build_v24691_worldbank_surfaces.py"),
    Path("scripts/audit_v24692_worldbank_surface_build.py"),
    Path("tests/test_audit_v24692_worldbank_surface_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24686_worldbank_target_value_runtime.py"), 10, 120),
    (Path("tests/test_build_v24691_worldbank_surfaces.py"), 6, 180),
    (Path("tests/test_audit_v24692_worldbank_surface_build.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 22


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _run_test(path: Path, timeout: int) -> tuple[bool, int]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
            "discover", "-s", "tests", "-p", path.name,
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=timeout, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode == 0, int(match.group(1)) if match else 0


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    suites = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed = _run_test(path, timeout)
        suites.append({
            "path": str(path), "expected_test_count": expected,
            "observed_test_count": observed, "passed": passed and observed == expected,
        })
    test_count = sum(item["observed_test_count"] for item in suites)
    secret_hits = [
        str(path) for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    head = common._git("rev-parse", "HEAD")
    remote = common._git("rev-parse", "target/main")
    clean = common._git("status", "--porcelain") == ""
    tracked = all(common._tracked(path) for path in SOURCES)
    watchers = [
        {"pid": pid, "start_ticks": ticks, "marker": marker,
         "identity_valid": common._watcher(pid, ticks, marker)}
        for pid, ticks, marker in common.EXPECTED_WATCHERS
    ]
    lease_inactive = common._lease_inactive()
    pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (builder.CONTRACT, builder.EVALUATOR, builder.GOLD, builder.PROVENANCE)
    )
    parent_valid = True
    try:
        builder._validate_parents()
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        parent_valid = False
    surfaces = builder.build_surfaces() if parent_valid else {}
    surface_valid = (
        set(surfaces) == {builder.CONTRACT, builder.EVALUATOR, builder.GOLD, builder.PROVENANCE}
        and len(surfaces.get(builder.GOLD, "").splitlines()) == 49
        and "evaluation/" not in surfaces.get(builder.CONTRACT, "")
        and "external_evaluator" not in surfaces.get(builder.CONTRACT, "")
        and "target_value_minus_expanded" in surfaces.get(builder.EVALUATOR, "")
    )
    findings: list[str] = []
    if head != remote: findings.append("v24692_source_commit_not_pushed")
    if not clean: findings.append("v24692_source_worktree_not_clean")
    if not tracked: findings.append("v24692_source_not_tracked")
    if not parent_valid: findings.append("v24690_population_parent_drifted")
    if not surface_valid: findings.append("v24691_surface_contract_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24686_v24691_v24692_regression_failed")
    if secret_hits: findings.append("credential_literal_in_surface_build")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive: findings.append("shared_api_lease_active")
    if not pristine: findings.append("v24691_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24692_worldbank_surface_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "surface_design": {
            "visible_contract_country_count": 48,
            "task_count": 12,
            "gold_row_count": 48,
            "gold_value_count": 96,
            "provenance_record_count": 96,
            "three_arms": ["frozen_parser", "expanded_parser", "target_value"],
            "numeric_semantic_equivalence_in_evaluator": True,
            "exact_table_primary_metric": True,
            "target_value_gate_requires_strict_exact_gain": True,
            "surface_valid": surface_valid,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {"head": head, "target_main": remote,
                "head_equals_target_main": head == remote, "worktree_clean": clean,
                "all_sources_tracked": tracked},
        "tests": {"suites": suites, "test_count": test_count,
                  "passed": all(item["passed"] for item in suites)
                  and test_count == EXPECTED_TEST_COUNT,
                  "network_model_search_worldbank_benchmark_or_evaluator_called": False},
        "separation": {
            "visible_contract_contains_no_private_value_response_hash_or_evaluator_path": True,
            "gold_provenance_and_evaluator_are_separate_surfaces": True,
            "forward_import_or_runtime_read_authorized": False,
            "gold_or_evaluator_open_before_prediction_freeze_authorized": False,
            "credential_literal_hits": sorted(secret_hits),
        },
        "runtime_state": {"protected_watchers": watchers,
                          "protected_watchers_unchanged": all(item["identity_valid"] for item in watchers),
                          "shared_api_lease_inactive": lease_inactive,
                          "surface_pristine": pristine,
                          "external_effect_performed_by_audit": False},
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "one_surface_publication": not findings,
            "external_protocol_design": False,
            "preactivation_or_launch": False,
            "evaluator_execution": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24692_worldbank_surface_build_audit"
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or copied.get("surface_design", {}).get("surface_valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("runtime_state", {}).get("protected_watchers_unchanged") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("surface_pristine") is not True
        or copied.get("authorization") != {
            "one_surface_publication": True, "external_protocol_design": False,
            "preactivation_or_launch": False, "evaluator_execution": False,
            "dev64_or_exact220": False, "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.92 surface build audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    result = build_audit(); validate_audit(result); publish_new(ROOT / AUDIT, result)
    print(json.dumps({"path": str(AUDIT), "audit_valid": result["audit_valid"],
                      "findings": result["findings"],
                      "test_count": result["tests"]["test_count"]}, sort_keys=True))
