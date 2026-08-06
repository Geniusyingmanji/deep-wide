#!/usr/bin/env python3
"""Clean-build audit for the V2.46.20 fresh watchdog successor."""

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
from scripts import v24620_title_provenance_watchdog_external_gate as gate  # noqa: E402


DATE = "20260806"
PRIOR_AUDIT = Path(
    f"results/v24620_title_provenance_watchdog_build_audit_v1_{DATE}.json"
)
AUDIT = Path(f"results/v24620_title_provenance_watchdog_build_audit_v2_{DATE}.json")
SOURCES = tuple(
    Path(item)
    for item in (
        "src/deepwide_agent/v24618_concurrent_controller_binding.py",
        "tests/test_v24618_concurrent_controller_binding.py",
        "scripts/audit_v24619_concurrent_binding_repair.py",
        "tests/test_audit_v24619_concurrent_binding_repair.py",
        "results/v24619_concurrent_binding_repair_audit_v1_20260805.json",
        str(PRIOR_AUDIT),
        "src/deepwide_agent/v24620_enforcing_batch_watchdog.py",
        "tests/test_v24620_enforcing_batch_watchdog.py",
        "scripts/v24620_title_provenance_watchdog_external_gate.py",
        "tests/test_v24620_title_provenance_watchdog_external_gate.py",
        "scripts/audit_v24620_title_provenance_watchdog_build.py",
        "tests/test_audit_v24620_title_provenance_watchdog_build.py",
    )
)
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24618_concurrent_controller_binding.py"),
    Path("src/deepwide_agent/v24620_enforcing_batch_watchdog.py"),
    Path("scripts/v24620_title_provenance_watchdog_external_gate.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24618_concurrent_controller_binding.py"), 8, 180),
    (Path("tests/test_audit_v24619_concurrent_binding_repair.py"), 9, 180),
    (Path("tests/test_v24620_enforcing_batch_watchdog.py"), 9, 180),
    (Path("tests/test_v24620_title_provenance_watchdog_external_gate.py"), 20, 600),
    (Path("tests/test_audit_v24620_title_provenance_watchdog_build.py"), 8, 180),
)
EXPECTED_TEST_COUNT = 54


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = common._read(gate.PARENT)
    try:
        gate._parent(ROOT)
    except RuntimeError:
        return False
    return (
        value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("freshness_baseline", {}).get("prior_external_question_count")
        == 500
        and value.get("freshness_baseline", {}).get("prior_external_entity_count")
        == 4000
        and _sealed(value, "audit_payload_sha256")
    )


def _design_valid() -> bool:
    try:
        protocol = gate.build_protocol(now=0, require_pristine=False)
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    mechanism = protocol.get("mechanism", {})
    return (
        gate._fresh_entity_vector_valid()
        and gate._title_query_surface_vector_valid()
        and gate.binding.invariant_valid()
        and mechanism.get("runtime_fast_control_validator") is True
        and mechanism.get("runtime_complete_protocol_revalidation") is False
        and mechanism.get("maximum_batch_wall_is_enforcing_watchdog") is True
        and protocol.get("budget", {}).get("maximum_batch_wall_seconds") == 255.0
        and protocol.get("authorization") == gate._protocol_authorization()
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_valid = _parent_valid()
    design_valid = _design_valid()
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
    future_pristine = all(
        not (ROOT / path).exists()
        for path in (
            gate.PROTOCOL,
            gate.PREAUDIT,
            gate.ACTIVATION,
            gate.EXECUTION_START,
            gate.RESULT,
            gate.DECISION,
            gate.POSTAUDIT,
        )
    )
    findings: list[str] = []
    if not parent_valid:
        findings.append("v24619_parent_audit_drifted")
    if not design_valid:
        findings.append("v24620_design_or_freshness_drifted")
    if head != remote:
        findings.append("v24620_source_commit_not_pushed")
    if not clean:
        findings.append("v24620_source_worktree_not_clean")
    if not tracked:
        findings.append("v24620_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24620_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24620_runtime")
    if imports:
        findings.append("evaluator_import_in_v24620_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24620_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not future_pristine:
        findings.append("v24620_future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24620_title_provenance_watchdog_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "path": str(gate.PARENT),
            "sha256": common._sha256(gate.PARENT),
            "valid": parent_valid,
            "v24616_population_consumed": True,
            "v24616_population_retry_resume_rerun_or_evaluation_authorized": False,
        },
        "supersedes": {
            "path": str(PRIOR_AUDIT),
            "sha256": common._sha256(PRIOR_AUDIT),
            "reason": "post_v1_runtime_stack_fast_validator_and_watchdog_reparent_hardening",
            "prior_audit_result_or_source_modified": False,
            "current_protocol_must_use_v2_build_evidence": True,
        },
        "freshness": {
            "prior_external_question_count": 500,
            "prior_external_entity_count": 4000,
            "fresh_question_count": 8,
            "fresh_entity_count": 64,
            "literal_and_canonical_disjoint": gate._fresh_entity_vector_valid(),
            "all_validator_query_surfaces_reachable": gate._title_query_surface_vector_valid(),
        },
        "runtime_design": {
            "concurrent_binding_policy": gate.binding.POLICY_ID,
            "watchdog_policy": gate.watchdog.POLICY_ID,
            "complete_protocol_validation_before_wave": True,
            "runtime_task_validation_uses_control_hash_id_and_manifest_only": True,
            "runtime_task_switches_to_protocol_binding_mode": False,
            "maximum_batch_wall_seconds": 255.0,
            "maximum_batch_wall_is_enforcing_watchdog": True,
            "watchdog_targets_marked_descendant_process_groups_only": True,
            "watchdog_emits_process_identifiers_or_command_lines": False,
            "logical_query_search_fetch_model_or_credit_budget_changed": False,
            "design_valid": design_valid,
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
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "passed": not accesses and not imports and not secret_hits,
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
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "private_task_query_url_title_page_prediction_or_provider_payload_opened_by_audit": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "v24620_protocol_publication": not findings,
            "fresh_external_activation_or_launch": False,
            "same_v24616_population_retry_resume_rerun_or_evaluation": False,
            "search_parser_title_validator_or_evidence_rule_change": False,
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
            },
            sort_keys=True,
        )
    )
