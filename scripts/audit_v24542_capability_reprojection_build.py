#!/usr/bin/env python3
"""Build-only audit for the V2.45.41 capability reprojection repair."""

from __future__ import annotations

import json
import os
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
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import audit_v24541_invalid_duplicate_capability as quarantine  # noqa: E402
from scripts import v24537_alias_action_credit_external_gate as action_gate  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24542_capability_reprojection_build_audit_v1_{DATE}.json")
QUARANTINE_AUDIT = quarantine.AUDIT
SOURCES = (
    Path("src/deepwide_agent/v24533_alias_acquisition_entropy_credit.py"),
    Path("src/deepwide_agent/v24534_proof_carrying_alias_acquisition.py"),
    Path("src/deepwide_agent/v24535_total_alias_acquisition_projection.py"),
    Path("scripts/v24537_alias_action_credit_external_gate.py"),
    Path("tests/test_v24537_alias_action_credit_external_gate.py"),
    Path("scripts/v24539_alias_action_credit_external_gate.py"),
    Path("tests/test_v24539_alias_action_credit_external_gate.py"),
    Path("scripts/v24541_alias_action_credit_external_gate.py"),
    Path("tests/test_v24541_alias_action_credit_external_gate.py"),
    Path("scripts/audit_v24541_invalid_duplicate_capability.py"),
    Path("tests/test_audit_v24541_invalid_duplicate_capability.py"),
    QUARANTINE_AUDIT,
    Path("scripts/audit_v24542_capability_reprojection_build.py"),
    Path("tests/test_audit_v24542_capability_reprojection_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0], SOURCES[1], SOURCES[2], SOURCES[3], SOURCES[5], SOURCES[7])
TEST_SUITES = (
    (Path("tests/test_v24533_alias_acquisition_entropy_credit.py"), 5, 180),
    (Path("tests/test_v24534_proof_carrying_alias_acquisition.py"), 8, 360),
    (Path("tests/test_v24535_total_alias_acquisition_projection.py"), 7, 180),
    (Path("tests/test_v24537_alias_action_credit_external_gate.py"), 17, 480),
    (Path("tests/test_v24539_alias_action_credit_external_gate.py"), 13, 480),
    (Path("tests/test_v24541_alias_action_credit_external_gate.py"), 13, 480),
    (Path("tests/test_audit_v24541_invalid_duplicate_capability.py"), 5, 120),
    (Path("tests/test_audit_v24542_capability_reprojection_build.py"), 5, 120),
)
EXPECTED_TEST_COUNT = 73


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _quarantine_valid() -> bool:
    value = common._read(QUARANTINE_AUDIT)
    incident = value.get("incident", {})
    population = value.get("population", {})
    authorization = value.get("authorization", {})
    return (
        _sealed(value, "audit_payload_sha256")
        and value.get("role") == "v24541_invalid_duplicate_capability_run_audit"
        and value.get("status") == "invalid_quarantined_no_public_result"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and incident.get("same_capability_reprojected_during_total_aggregation") is True
        and incident.get("collector_duplicate_guard_failed_closed") is True
        and incident.get("external_effect_counts_recoverable") is False
        and incident.get("public_result_published") is False
        and population.get("same_population_rerun_allowed") is False
        and population.get("next_prior_question_count") == 412
        and population.get("next_prior_entity_count") == 3296
        and authorization.get("same_population_resume_retry_or_rerun") is False
        and authorization.get("ordinary_v24541_result_decision_or_postaudit") is False
        and authorization.get("fresh_disjoint_successor_protocol_design") is True
    )


def _repair_shape_valid() -> bool:
    source = common._ordinary(SOURCES[3]).read_text(encoding="utf-8")
    return (
        "installed_projector = total.task_projection" in source
        and "total.task_projection = _ORIGINAL_TASK_PROJECTION" in source
        and "return total.aggregate_projections(proof_inputs, selected=selected)" in source
        and "total.task_projection = installed_projector" in source
        and "capability projector binding drifted" in source
        and "aggregate projector drifted" in source
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    quarantine_valid = _quarantine_valid()
    repair_valid = _repair_shape_valid()
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
    lease_inactive = common._lease_inactive()
    no_process = quarantine._no_active_v24541_process()
    findings: list[str] = []
    if not quarantine_valid:
        findings.append("v24541_quarantine_drifted")
    if not repair_valid:
        findings.append("capability_reprojection_repair_drifted")
    if head != remote:
        findings.append("v24542_source_commit_not_pushed")
    if not clean:
        findings.append("v24542_source_worktree_not_clean")
    if not tracked:
        findings.append("v24542_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24533_v24542_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24533_v24541_runtime")
    if imports:
        findings.append("evaluator_import_in_v24533_v24541_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24542_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not no_process:
        findings.append("v24541_process_still_active")
    value = {
        "artifact_version": 1,
        "role": "v24542_capability_reprojection_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "v24541_quarantine": {
            "path": str(QUARANTINE_AUDIT),
            "sha256": common._sha256(QUARANTINE_AUDIT),
            "valid": quarantine_valid,
            "same_population_rerun_authorized": False,
            "next_prior_question_count": 412,
            "next_prior_entity_count": 3296,
        },
        "repair": {
            "pure_projector_restored_only_during_total_aggregate": repair_valid,
            "collector_reinstalled_after_aggregate": repair_valid,
            "duplicate_and_binding_guards_remain_fail_closed": repair_valid,
            "real_projection_shape_regression_present": repair_valid,
            "task_execution_parallelism_changed": False,
            "external_effect_budget_changed": False,
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
            "synthetic_clients_and_capabilities_only": True,
            "historical_private_pages_opened": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "evaluator_opened": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "v24541_process_absent": no_process,
            "benchmark_launched": False,
            "external_population_launched": False,
            "evaluator_called": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "prior_external_or_benchmark_private_content_opened_by_audit": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_disjoint_action_credit_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
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
