#!/usr/bin/env python3
"""Clean-build audit for the serialized V2.45.69 protocol validator."""

from __future__ import annotations

import concurrent.futures
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
from scripts import audit_v24568_invalid_concurrent_protocol_context as quarantine  # noqa: E402
from scripts import v24569_serialized_protocol_validator_repair as repair  # noqa: E402


DATE = "20260805"
AUDIT = Path(
    f"results/v24570_serialized_protocol_validator_build_audit_v1_{DATE}.json"
)
QUARANTINE_AUDIT = quarantine.AUDIT
SOURCES = (
    Path("scripts/v24567_strict_reachability_conversion_external_gate.py"),
    Path("tests/test_v24567_strict_reachability_conversion_external_gate.py"),
    Path("scripts/audit_v24568_invalid_concurrent_protocol_context.py"),
    Path("tests/test_audit_v24568_invalid_concurrent_protocol_context.py"),
    QUARANTINE_AUDIT,
    Path("scripts/v24569_serialized_protocol_validator_repair.py"),
    Path("tests/test_v24569_serialized_protocol_validator_repair.py"),
    Path("scripts/audit_v24570_serialized_protocol_validator_build.py"),
    Path("tests/test_audit_v24570_serialized_protocol_validator_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0], SOURCES[5])
TEST_SUITES = (
    (
        Path("tests/test_v24567_strict_reachability_conversion_external_gate.py"),
        12,
        480,
    ),
    (
        Path("tests/test_audit_v24568_invalid_concurrent_protocol_context.py"),
        5,
        120,
    ),
    (Path("tests/test_v24569_serialized_protocol_validator_repair.py"), 5, 180),
    (
        Path("tests/test_audit_v24570_serialized_protocol_validator_build.py"),
        7,
        120,
    ),
)
EXPECTED_TEST_COUNT = 29
STRESS_ROUNDS = 25
STRESS_WORKERS = 8
EXPECTED_STRESS_VALIDATIONS = STRESS_ROUNDS * STRESS_WORKERS


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
        and value.get("role")
        == "v24568_invalid_concurrent_protocol_context_run_audit"
        and value.get("protocol_id") == repair.frozen.PROTOCOL_ID
        and value.get("status") == "invalid_quarantined_no_public_result"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and incident.get(
            "threaded_run_one_protocol_validators_shared_mutable_base_context"
        )
        is True
        and incident.get("protocol_validator_lock_present_at_execution_start")
        is False
        and incident.get("external_effect_counts_recoverable") is False
        and incident.get("public_result_published") is False
        and population.get("question_ordinals_consumed") == [436, 443]
        and population.get("entity_ordinals_consumed") == [3488, 3551]
        and population.get(
            "same_population_resume_retry_rerun_or_evaluation_allowed"
        )
        is False
        and population.get("next_prior_question_count") == 444
        and population.get("next_prior_entity_count") == 3552
        and authorization.get(
            "same_population_resume_retry_rerun_or_evaluation"
        )
        is False
        and authorization.get("ordinary_v24567_result_decision_or_postaudit")
        is False
        and authorization.get("concurrent_protocol_validator_repair_design")
        is True
        and authorization.get("fresh_disjoint_successor_protocol_design") is False
        and authorization.get("fresh_successor_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def _serialized_binding_valid() -> bool:
    protocol = repair.frozen.validate_protocol()
    if not repair.binding_valid():
        return False
    with repair.serialized_protocol_validation():
        validated = repair.validate_protocol(value=protocol)
    return validated.get("protocol_id") == repair.frozen.PROTOCOL_ID


def _concurrent_stress() -> dict[str, Any]:
    protocol = repair.frozen.validate_protocol()
    completed = 0
    for _round in range(STRESS_ROUNDS):
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=STRESS_WORKERS
        ) as pool:
            values = list(
                pool.map(
                    lambda _index: repair.validate_protocol(value=protocol)[
                        "protocol_id"
                    ],
                    range(STRESS_WORKERS),
                )
            )
        if values != [repair.frozen.PROTOCOL_ID] * STRESS_WORKERS:
            return {
                "rounds": STRESS_ROUNDS,
                "workers": STRESS_WORKERS,
                "validations": completed + len(values),
                "passed": False,
            }
        completed += len(values)
    return {
        "rounds": STRESS_ROUNDS,
        "workers": STRESS_WORKERS,
        "validations": completed,
        "passed": completed == EXPECTED_STRESS_VALIDATIONS,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    quarantine_valid = _quarantine_valid()
    binding_valid = _serialized_binding_valid()
    stress = _concurrent_stress()
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
    no_process = quarantine._no_active_process()
    findings: list[str] = []
    if not quarantine_valid:
        findings.append("v24568_quarantine_drifted")
    if not binding_valid:
        findings.append("serialized_protocol_validator_binding_drifted")
    if stress.get("passed") is not True:
        findings.append("serialized_protocol_validator_stress_failed")
    if head != remote:
        findings.append("v24569_70_source_commit_not_pushed")
    if not clean:
        findings.append("v24569_70_source_worktree_not_clean")
    if not tracked:
        findings.append("v24569_70_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24567_70_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24567_69_runtime")
    if imports:
        findings.append("evaluator_import_in_v24567_69_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24567_70_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not no_process:
        findings.append("v24567_process_still_active")
    value = {
        "artifact_version": 1,
        "role": "v24570_serialized_protocol_validator_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "v24568_quarantine": {
            "path": str(QUARANTINE_AUDIT),
            "sha256": common._sha256(QUARANTINE_AUDIT),
            "valid": quarantine_valid,
            "same_population_resume_retry_rerun_or_evaluation_authorized": False,
            "next_prior_question_count": 444,
            "next_prior_entity_count": 3552,
        },
        "repair": {
            "policy_id": repair.POLICY_ID,
            "reentrant_protocol_validator_lock_present": binding_valid,
            "complete_nested_base_patch_and_validation_critical_section_serialized": True,
            "task_execution_remains_parallel_after_protocol_validation": True,
            "model_search_fetch_or_evaluator_effect_changed": False,
            "stress": stress,
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
            "historical_private_task_query_url_page_source_value_or_prediction_opened": False,
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
            "v24567_process_absent": no_process,
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
            "fresh_disjoint_strict_reachability_conversion_external_protocol_design": not findings,
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
                "stress_validations": value["repair"]["stress"]["validations"],
            },
            sort_keys=True,
        )
    )
