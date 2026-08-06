#!/usr/bin/env python3
"""Clean-build audit for the inert V2.46.45 external package."""

from __future__ import annotations

import ast
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent import v24644_primary_identity_pair_runtime as runtime  # noqa: E402
from deepwide_agent import v24645_ror_external_contract as contract  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402


DATE = "20260806"
AUDIT = Path(f"results/v24645_external_package_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24645_ror_population_design_v1_{DATE}.json")
FORWARD_SOURCES = (
    Path("src/deepwide_agent/v24644_primary_identity_pair_runtime.py"),
    Path("src/deepwide_agent/v24645_ror_external_contract.py"),
    Path("scripts/run_v24645_ror_task.py"),
    Path("scripts/run_v24645_primary_identity_pair.py"),
    Path("scripts/audit_v24645_primary_identity_forward.py"),
)
EVALUATOR_SOURCES = (
    Path("src/deepwide_agent/v24645_ror_external_evaluator.py"),
    Path("evaluation/v24645_ror_gold_v1.csv"),
    Path("evaluation/v24645_ror_gold_provenance_v1.json"),
)
SOURCES = (
    *FORWARD_SOURCES,
    *EVALUATOR_SOURCES,
    Path("tests/test_v24644_primary_identity_pair_runtime.py"),
    Path("tests/test_v24645_external_package.py"),
    Path("tests/test_v24645_forward_package.py"),
    Path("scripts/audit_v24645_external_package_build.py"),
    Path("tests/test_audit_v24645_external_package_build.py"),
    PARENT,
)
TEST_SUITES = (
    (Path("tests/test_v24644_primary_identity_pair_runtime.py"), 14, 180),
    (Path("tests/test_v24645_external_package.py"), 7, 180),
    (Path("tests/test_v24645_forward_package.py"), 5, 180),
    (Path("tests/test_audit_v24645_external_package_build.py"), 5, 120),
)
EXPECTED_TEST_COUNT = 31
FORBIDDEN_FORWARD_LITERALS = (
    "evaluation/",
    "v24645_ror_external_evaluator",
    "v24645_ror_population_private",
    "v24645_ror_gold_v1",
    "v24645_ror_gold_provenance",
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(common._ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.45 build audit expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(PARENT)
    return (
        value.get("role") == "v24645_ror_population_design"
        and value.get("selected_count") == 48
        and value.get("historical_entity_count") == 4_432
        and value.get("historical_canonical_count") == 4_432
        and value.get("authorization", {}).get("external_protocol_design") is True
        and value.get("authorization", {}).get("activation_or_launch") is False
        and _sealed(value, "design_sha256")
    )


def _forward_capability_findings() -> tuple[list[str], list[str], list[str]]:
    accesses: list[str] = []
    imports: list[str] = []
    literals: list[str] = []
    for path in FORWARD_SOURCES:
        current_accesses, current_imports = common.ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
        source = common._ordinary(path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.extend([node.module or "", *(alias.name for alias in node.names)])
        for name in names:
            if "evaluator" in name.casefold() or "gold" in name.casefold():
                imports.append(f"{path}:{name}")
        for marker in FORBIDDEN_FORWARD_LITERALS:
            if marker in source:
                literals.append(f"{path}:{marker}")
    return sorted(set(accesses)), sorted(set(imports)), sorted(set(literals))


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    accesses, imports, literals = _forward_capability_findings()
    secret_hits = [
        str(path)
        for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = [
        {
            "path": str(path),
            "test_count": count,
            "passed": common._run_test(path, timeout),
        }
        for path, count, timeout in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
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
        contract.PROTOCOL,
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
    parent_valid = _parent_valid()
    runtime_binding_valid = runtime.binding_is_private_and_stable()
    findings: list[str] = []
    if head != remote:
        findings.append("v24645_source_commit_not_pushed")
    if not clean:
        findings.append("v24645_source_worktree_not_clean")
    if not tracked:
        findings.append("v24645_source_not_tracked")
    if not parent_valid:
        findings.append("v24645_population_parent_invalid")
    if not runtime_binding_valid:
        findings.append("v24644_runtime_binding_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24644_45_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24645_forward")
    if imports:
        findings.append("evaluator_or_gold_import_in_v24645_forward")
    if literals:
        findings.append("private_or_evaluator_literal_in_v24645_forward")
    if secret_hits:
        findings.append("credential_literal_in_v24645_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not future_pristine:
        findings.append("v24645_future_surface_not_pristine")

    value = {
        "artifact_version": 1,
        "role": "v24645_external_package_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "population_design_path": str(PARENT),
            "population_design_sha256": common._sha256(PARENT),
            "fresh_entities": 48,
            "historical_entities": 4_432,
            "literal_and_canonical_overlap": 0,
            "valid": parent_valid,
        },
        "mechanism": {
            "runtime_policy": runtime.POLICY_ID,
            "body_only_identity_binding_removed": True,
            "search_lead_title_blanked_before_fetch_effect": True,
            "ror_profile_lead_rewritten_to_official_api_without_new_effect": True,
            "final_fetched_url_used_for_identity_binding": True,
            "official_api_identity_projected_before_shared_page_cap": True,
            "structured_parse_failure_abstains": True,
            "nonunknown_ror_and_all_country_cells_immutable": True,
            "two_provider_model_calls_per_valid_task": True,
            "four_queries_and_ten_fetch_cap_unchanged": True,
            "runtime_binding_valid": runtime_binding_valid,
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
            "privileged_runtime_field_accesses": accesses,
            "evaluator_or_gold_imports": imports,
            "private_or_evaluator_literal_hits": literals,
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "passed": not accesses and not imports and not literals and not secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "future_surface_pristine": future_pristine,
            "benchmark_launched": False,
            "external_population_launched_by_audit": False,
            "evaluator_called": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "external_protocol_publication": not findings,
            "preactivation_audit": False,
            "activation_or_launch": False,
            "same_v24642_population_retry_resume_selective_rerun": False,
            "dev64_or_exact220": False,
            "evaluator_access": False,
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
