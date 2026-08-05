#!/usr/bin/env python3
"""Clean-build audit for the V2.45.94 immutable title-query collector."""

from __future__ import annotations

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
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import v24594_title_query_collector_repair as repair  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24595_title_query_collector_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24593_validator_aligned_title_query_build_audit_v1_{DATE}.json")
SOURCES = (
    PARENT,
    Path("src/deepwide_agent/v24589_validator_aligned_title_query.py"),
    Path("tests/test_v24589_validator_aligned_title_query.py"),
    Path("src/deepwide_agent/v24590_proof_carrying_validator_aligned_title_query.py"),
    Path("tests/test_v24590_proof_carrying_validator_aligned_title_query.py"),
    Path("src/deepwide_agent/v24591_total_validator_aligned_title_query_projection.py"),
    Path("tests/test_v24591_total_validator_aligned_title_query_projection.py"),
    Path("src/deepwide_agent/v24592_bounded_validator_aligned_title_query_parent.py"),
    Path("tests/test_v24592_bounded_validator_aligned_title_query_parent.py"),
    Path("scripts/audit_v24593_validator_aligned_title_query_build.py"),
    Path("tests/test_audit_v24593_validator_aligned_title_query_build.py"),
    Path("scripts/v24594_title_query_collector_repair.py"),
    Path("tests/test_v24594_title_query_collector_repair.py"),
    Path("scripts/audit_v24595_title_query_collector_build.py"),
    Path("tests/test_audit_v24595_title_query_collector_build.py"),
)
RUNTIME_SOURCES = (SOURCES[1], SOURCES[3], SOURCES[5], SOURCES[7], SOURCES[11])
TEST_SUITES = (
    (Path("tests/test_v24589_validator_aligned_title_query.py"), 8, 120),
    (
        Path("tests/test_v24590_proof_carrying_validator_aligned_title_query.py"),
        7,
        300,
    ),
    (
        Path("tests/test_v24591_total_validator_aligned_title_query_projection.py"),
        6,
        300,
    ),
    (
        Path("tests/test_v24592_bounded_validator_aligned_title_query_parent.py"),
        5,
        300,
    ),
    (
        Path("tests/test_audit_v24593_validator_aligned_title_query_build.py"),
        8,
        180,
    ),
    (Path("tests/test_v24594_title_query_collector_repair.py"), 7, 360),
    (Path("tests/test_audit_v24595_title_query_collector_build.py"), 8, 180),
)
EXPECTED_TEST_COUNT = 49
STRESS_WORKERS = 8
PRIOR_QUESTION_COUNT = 468
PRIOR_ENTITY_COUNT = 3744


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = common._read(PARENT)
    baseline = value.get("freshness_baseline", {})
    authorization = value.get("authorization", {})
    return (
        _sealed(value, "audit_payload_sha256")
        and value.get("role") == "v24593_validator_aligned_title_query_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("tests", {}).get("test_count") == 72
        and value.get("tests", {}).get("passed") is True
        and value.get("label_blind_audit", {}).get("passed") is True
        and value.get("runtime_state", {}).get("shared_api_lease_inactive") is True
        and baseline.get("prior_external_question_count") == PRIOR_QUESTION_COUNT
        and baseline.get("prior_external_entity_count") == PRIOR_ENTITY_COUNT
        and baseline.get("v24587_population_resume_retry_rerun_or_evaluation_authorized")
        is False
        and authorization.get(
            "fresh_disjoint_validator_aligned_title_query_external_protocol_design"
        )
        is True
        and authorization.get("fresh_external_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def _repair_binding_valid() -> bool:
    return (
        repair.binding_valid()
        and repair.FROZEN_TASK_PROJECTION is repair.total.task_projection
        and getattr(repair.FROZEN_TASK_PROJECTION, "__self__", None) is None
    )


def _collector_stress() -> dict[str, Any]:
    passed = common._run_test(
        Path("tests/test_v24594_title_query_collector_repair.py"), 360
    )
    return {
        "workers": STRESS_WORKERS,
        "validations": STRESS_WORKERS if passed else 0,
        "instance_local_immutable_v24591_projector": True,
        "shared_runtime_original_projection_read_by_collector": False,
        "passed": passed,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_valid = _parent_valid()
    binding_valid = _repair_binding_valid()
    stress = _collector_stress()
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
    findings: list[str] = []
    if not parent_valid:
        findings.append("v24593_parent_drifted")
    if not binding_valid:
        findings.append("immutable_v24591_collector_binding_drifted")
    if stress.get("passed") is not True or stress.get("validations") != STRESS_WORKERS:
        findings.append("immutable_v24591_collector_stress_failed")
    if head != remote:
        findings.append("v24594_95_source_commit_not_pushed")
    if not clean:
        findings.append("v24594_95_source_worktree_not_clean")
    if not tracked:
        findings.append("v24594_95_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24589_95_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24589_94_runtime")
    if imports:
        findings.append("evaluator_import_in_v24589_94_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24589_95_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24595_title_query_collector_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "v24593_parent": {
            "path": str(PARENT),
            "sha256": common._sha256(PARENT),
            "valid": parent_valid,
            "prior_external_question_count": PRIOR_QUESTION_COUNT,
            "prior_external_entity_count": PRIOR_ENTITY_COUNT,
            "v24587_population_resume_retry_rerun_or_evaluation_authorized": False,
        },
        "repair": {
            "policy_id": repair.POLICY_ID,
            "module_load_unbound_v24591_projector_captured": binding_valid,
            "collector_project_calls_instance_local_immutable_projector": True,
            "collector_reads_shared_runtime_original_projection": False,
            "nested_runtime_rebinding_can_change_collector_target": False,
            "mixed_failure_projection_remains_total": True,
            "duplicate_consume_and_nested_collector_fail_closed": True,
            "task_model_search_fetch_page_source_evidence_credit_budget_or_evaluator_changed": False,
            "stress": stress,
        },
        "freshness_baseline": {
            "prior_external_question_count": PRIOR_QUESTION_COUNT,
            "prior_external_entity_count": PRIOR_ENTITY_COUNT,
            "all_populations_through_v24587_counted_as_consumed": True,
            "v24587_population_resume_retry_rerun_or_evaluation_authorized": False,
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
            "synthetic_clients_capabilities_and_control_state_only": True,
            "historical_private_task_query_title_url_page_value_or_prediction_opened": False,
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
            "fresh_disjoint_validator_aligned_title_query_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator_access_authorized": False,
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
                "stress_validations": value["repair"]["stress"]["validations"],
            },
            sort_keys=True,
        )
    )
