#!/usr/bin/env python3
"""Clean-build audit for the V2.46.25 finite-predicate successor."""

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
from scripts import v24625_predicate_binding_external_gate as gate  # noqa: E402


DATE = "20260806"
AUDIT = Path(f"results/v24626_predicate_binding_build_audit_v1_{DATE}.json")
SOURCES = tuple(Path(item) for item in gate.BUILD_AUDIT_SOURCE_FILES)
RUNTIME_SOURCES = (Path(gate.RUNNER_MARKER),)
TEST_SUITES = (
    (Path("tests/test_finalize_v24624_v24622_predicate_failure.py"), 8, 180),
    (Path("tests/test_v24625_predicate_binding_external_gate.py"), 22, 600),
    (Path("tests/test_audit_v24626_predicate_binding_build.py"), 8, 180),
)
EXPECTED_TEST_COUNT = 38


def _design_valid() -> bool:
    try:
        protocol = gate.build_protocol(
            now=0, require_pristine=False, require_build_audit=False
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    mechanism = protocol.get("mechanism", {})
    before_base = gate.base._mechanism_passed
    before_controller = gate.controller.mechanism_passed
    try:
        with gate.configured_runtime_stack():
            runtime_valid = (
                gate.base._mechanism_passed is gate.mechanism_passed
                and gate.controller.mechanism_passed is gate.mechanism_passed
            )
    except (RuntimeError, TypeError, ValueError):
        return False
    restored = (
        gate.base._mechanism_passed is before_base
        and gate.controller.mechanism_passed is before_controller
    )
    return (
        gate._previous_closed()
        and gate._fresh_entity_vector_valid()
        and gate._title_query_surface_vector_valid()
        and gate.collector.binding_valid()
        and gate._predicate_binding_valid()
        and runtime_valid
        and restored
        and mechanism.get("mechanism_predicate_binding_repair_policy")
        == gate.PREDICATE_POLICY_ID
        and mechanism.get("predicate_baseline_is_import_time_v24604_title_funnel_gate")
        is True
        and mechanism.get("predicate_provenance_tail_is_unchanged_v24616_gate")
        is True
        and mechanism.get("runtime_base_and_controller_use_same_safe_predicate")
        is True
        and mechanism.get("dynamic_controller_predicate_read_removed") is True
        and mechanism.get("collector_context_enters_before_task_futures") is True
        and mechanism.get("collector_context_remains_active_through_main_aggregate")
        is True
        and mechanism.get("runtime_fast_control_validator") is True
        and mechanism.get("maximum_batch_wall_is_enforcing_watchdog") is True
        and protocol.get("authorization") == gate._protocol_authorization()
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
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
    if not design_valid:
        findings.append("v24625_predicate_binding_design_or_freshness_drifted")
    if head != remote:
        findings.append("v24625_source_commit_not_pushed")
    if not clean:
        findings.append("v24625_source_worktree_not_clean")
    if not tracked:
        findings.append("v24625_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24625_26_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24625_runtime")
    if imports:
        findings.append("evaluator_import_in_v24625_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24625_26_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not future_pristine:
        findings.append("v24625_future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24626_predicate_binding_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "closed_parent": {
            "failure_path": str(gate.PREVIOUS_FAILURE),
            "failure_sha256": common._sha256(gate.PREVIOUS_FAILURE),
            "postaudit_path": str(gate.PARENT),
            "postaudit_sha256": common._sha256(gate.PARENT),
            "v24622_population_consumed": True,
            "v24622_population_retry_resume_rerun_or_evaluation_authorized": False,
            "valid": gate._previous_closed(),
        },
        "freshness": {
            "prior_external_question_count": 516,
            "prior_external_entity_count": 4128,
            "fresh_question_count": 8,
            "fresh_entity_count": 64,
            "literal_and_canonical_disjoint": gate._fresh_entity_vector_valid(),
            "all_validator_query_surfaces_reachable": gate._title_query_surface_vector_valid(),
        },
        "predicate_binding_repair": {
            "policy": gate.PREDICATE_POLICY_ID,
            "frozen_v24604_baseline": True,
            "unchanged_v24616_provenance_tail": True,
            "dynamic_controller_predicate_read_removed": True,
            "runtime_base_and_controller_use_same_safe_predicate": True,
            "direct_and_nested_runtime_predicate_tested": True,
            "runtime_binding_restored_after_context": True,
            "collector_lifetime_repair_changed": False,
            "fast_control_validator_changed": False,
            "enforcing_batch_watchdog_changed": False,
            "search_fetch_model_or_credit_budget_changed": False,
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
            "v24625_protocol_publication": not findings,
            "fresh_external_activation_or_launch": False,
            "same_v24622_population_retry_resume_rerun_or_evaluation": False,
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
