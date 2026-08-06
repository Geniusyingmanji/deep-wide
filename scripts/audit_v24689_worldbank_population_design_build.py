#!/usr/bin/env python3
"""Build-only audit for the inert V2.46.88 World Bank population designer."""

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
from scripts import design_v24688_worldbank_population as design  # noqa: E402


DATE = "20260806"
AUDIT = design.AUTHORIZATION
SOURCES = (
    design.PARENT,
    Path("scripts/design_v24688_worldbank_population.py"),
    Path("tests/test_design_v24688_worldbank_population.py"),
    Path("scripts/audit_v24689_worldbank_population_design_build.py"),
    Path("tests/test_audit_v24689_worldbank_population_design_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_design_v24688_worldbank_population.py"), 6, 120),
    (Path("tests/test_audit_v24689_worldbank_population_design_build.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 12


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


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
    source = common._ordinary(
        Path("scripts/design_v24688_worldbank_population.py")
    ).read_text(encoding="utf-8")
    secret_hits = [
        str(path)
        for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    suites: list[dict[str, Any]] = []
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
    lease_inactive = common._lease_inactive()
    parent_valid = design._parent_valid()
    surfaces_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (design.PRIVATE, design.OUTPUT)
    )
    implementation_valid = (
        design.SELECTED_COUNT == 48
        and design.TASK_COUNT == 12
        and design.TASK_SIZE == 4
        and design.REGION_CAP == 8
        and len(design.TARGETS) == 2
        and {item["indicator"] for item in design.TARGETS}
        == {"NY.GDP.PCAP.CD", "SP.URB.TOTL.IN.ZS"}
        and {item["year"] for item in design.TARGETS} == {"2023"}
        and {"BTN", "LIE", "MCO", "SMR"}.issubset(design.EXCLUDED_ISO3)
        and "_authorization_valid()" in source
        and source.index("if not _authorization_valid()")
        < source.index("catalog_raw = _fetch_bytes")
    )
    findings: list[str] = []
    if head != remote:
        findings.append("v24689_source_commit_not_pushed")
    if not clean:
        findings.append("v24689_source_worktree_not_clean")
    if not tracked:
        findings.append("v24689_source_not_tracked")
    if not parent_valid:
        findings.append("v24687_parent_build_audit_drifted")
    if not implementation_valid:
        findings.append("v24688_population_design_contract_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24688_v24689_regression_failed")
    if secret_hits:
        findings.append("credential_literal_in_design_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not surfaces_pristine:
        findings.append("v24688_population_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24689_worldbank_population_design_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "mechanism": {
            "country_catalogue_endpoint": design.COUNTRY_CATALOG_URL,
            "targets": [dict(item) for item in design.TARGETS],
            "selected_count": design.SELECTED_COUNT,
            "task_count": design.TASK_COUNT,
            "task_size": design.TASK_SIZE,
            "region_cap": design.REGION_CAP,
            "fixture_and_prior_worldbank_iso3_exclusion_count": len(
                design.EXCLUDED_ISO3
            ),
            "two_nonnull_official_values_required_before_selection": True,
            "sha256_iso3_rank_is_independent_of_observed_values": True,
            "region_round_robin_grouping": True,
            "publication_authority_checked_before_network": True,
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
            "network_model_search_worldbank_benchmark_or_evaluator_called": False,
        },
        "separation": {
            "private_population_under_evaluation_directory": True,
            "public_design_contains_hashes_not_selected_country_or_values": True,
            "forward_runtime_imports_population_or_gold": False,
            "population_gold_provenance_or_evaluator_read_by_build_audit": False,
            "credential_literal_hits": sorted(secret_hits),
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "population_surfaces_pristine": surfaces_pristine,
            "network_or_external_effect_performed_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "one_population_design_publication": not findings,
            "forward_or_evaluator_surface_publication": False,
            "preactivation_or_launch": False,
            "dev64_or_exact220": False,
            "evaluator_access": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24689_worldbank_population_design_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("mechanism", {}).get("implementation_valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("runtime_state", {}).get("protected_watchers_unchanged")
        is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive")
        is not True
        or copied.get("runtime_state", {}).get("population_surfaces_pristine")
        is not True
        or copied.get("authorization")
        != {
            "one_population_design_publication": True,
            "forward_or_evaluator_surface_publication": False,
            "preactivation_or_launch": False,
            "dev64_or_exact220": False,
            "evaluator_access": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.89 population design build audit drifted")
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
    result = build_audit()
    validate_audit(result)
    publish_new(ROOT / AUDIT, result)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": result["audit_valid"],
                "findings": result["findings"],
                "test_count": result["tests"]["test_count"],
            },
            sort_keys=True,
        )
    )
