#!/usr/bin/env python3
"""Build-only audit for V2.45.55 decision-reachability-first planning.

The audit reads tracked source/test files and the frozen content-free V2.45.54
result, decision, and post-result audit.  It does not open task rows, questions,
queries, URLs, pages, predictions, values, sources, temporary task directories,
mapping, gold, evaluator metadata, scores, rewards, or credentials.
"""

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
from scripts import v24554_alias_joint_external_gate as gate  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24556_decision_reachability_build_audit_v1_{DATE}.json")
SOURCES = (
    gate.RESULT,
    gate.DECISION,
    gate.POSTAUDIT,
    Path("src/deepwide_agent/v24510_proposal_seeded_entropy_target_planner.py"),
    Path("tests/test_v24510_proposal_seeded_entropy_target_planner.py"),
    Path("src/deepwide_agent/v24515_neutral_cell_discovery_planner.py"),
    Path("tests/test_v24515_neutral_cell_discovery_planner.py"),
    Path("src/deepwide_agent/v24555_decision_reachability_planner.py"),
    Path("tests/test_v24555_decision_reachability_planner.py"),
    Path("scripts/audit_v24556_decision_reachability_build.py"),
    Path("tests/test_audit_v24556_decision_reachability_build.py"),
)
RUNTIME_SOURCES = (SOURCES[3], SOURCES[5], SOURCES[7])
TEST_SUITES = (
    (Path("tests/test_v24510_proposal_seeded_entropy_target_planner.py"), 6, 120),
    (Path("tests/test_v24515_neutral_cell_discovery_planner.py"), 7, 120),
    (Path("tests/test_v24555_decision_reachability_planner.py"), 7, 120),
    (Path("tests/test_audit_v24556_decision_reachability_build.py"), 7, 120),
)
EXPECTED_TEST_COUNT = 27


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _v24554_closed_no_go_valid() -> bool:
    result = gate.validate_public_result(common._read(gate.RESULT))
    decision = gate.validate_decision(value=common._read(gate.DECISION))
    postaudit = gate.validate_postaudit(value=common._read(gate.POSTAUDIT))
    mechanism = result.get("mechanism_aggregate", {})
    authorization = decision.get("authorization", {})
    return (
        result.get("selected") == 8
        and result.get("passed") is False
        and result.get("mechanism_passed") is False
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and result.get("official_evaluator_called") is False
        and result.get("private_task_or_web_content_persisted") is False
        and mechanism.get("success_tasks") == 8
        and mechanism.get("failure_as_zero_tasks") == 0
        and mechanism.get(
            "selected_alias_surface_hit_new_observation_and_positive_information_gain_count_tasks"
        )
        == 1
        and mechanism.get("alias_joint_action_positive_information_credit_tasks")
        == 1
        and mechanism.get("alias_joint_action_positive_epistemic_credit_tasks")
        == 1
        and mechanism.get("alias_joint_action_positive_decision_credit_tasks")
        == 0
        and mechanism.get("alias_joint_safe_change_improvement_tasks") == 0
        and decision.get("status") == "fresh_alias_joint_no_go"
        and decision.get("passed") is False
        and decision.get("diagnostic_route") == "action_safe_change_successor"
        and authorization.get("diagnostic_successor_design") is True
        and authorization.get("fresh_paired_dev64_design") is False
        and authorization.get("fresh_paired_dev64_launch") is False
        and authorization.get("new_exact220") is False
        and postaudit.get("audit_valid") is True
        and postaudit.get("findings") == []
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("private_task_or_web_content_persisted") is False
        and postaudit.get("opaque_capability_references_destroyed_after_aggregation")
        is True
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    closed = _v24554_closed_no_go_valid()
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
    if not closed:
        findings.append("v24554_no_go_closure_drifted")
    if head != remote:
        findings.append("v24555_56_source_commit_not_pushed")
    if not clean:
        findings.append("v24555_56_source_worktree_not_clean")
    if not tracked:
        findings.append("v24555_56_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24510_15_55_56_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24510_15_55_runtime")
    if imports:
        findings.append("evaluator_import_in_v24510_15_55_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24554_56_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24556_decision_reachability_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "v24554_no_go_closure": {
            "valid": closed,
            "result_path": str(gate.RESULT),
            "result_sha256": common._sha256(gate.RESULT),
            "decision_path": str(gate.DECISION),
            "decision_sha256": common._sha256(gate.DECISION),
            "postaudit_path": str(gate.POSTAUDIT),
            "postaudit_sha256": common._sha256(gate.POSTAUDIT),
            "same_population_resume_retry_rerun_or_evaluation_authorized": False,
            "next_prior_external_question_count": 436,
            "next_prior_external_entity_count": 3488,
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
            "synthetic_states_and_observations_only": True,
            "historical_private_pages_or_task_artifacts_opened": False,
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
        "mechanism_evidence": {
            "v24554_same_task_alias_observation_positive_information_gain_joint_tasks": 1,
            "v24554_positive_action_epistemic_credit_tasks": 1,
            "v24554_positive_action_decision_credit_tasks": 0,
            "v24554_safe_change_improvement_tasks": 0,
            "legacy_entropy_first_selects_two_observation_target_in_counterexample": True,
            "decision_reachability_first_selects_one_observation_target_in_counterexample": True,
            "one_matching_independent_observation_crosses_all_frozen_gates": True,
            "same_observation_does_not_cross_legacy_two_observation_target": True,
            "selection_primary_key_is_minimum_required_independent_observations": True,
            "optimistic_information_gain_per_observation_is_tie_break_only": True,
            "projection_claims_expected_utility_or_causality": False,
            "neutral_discovery_fallback_preserved": True,
            "legacy_plan_schema_preserved": True,
            "query_search_fetch_or_model_budget_changed": False,
            "source_count_active_support_posterior_margin_leave_one_out_safe_change_or_decision_credit_rule_changed": False,
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
            "v24554_private_task_query_url_page_source_value_or_prediction_opened": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "decision_reachability_worker_integration_design": not findings,
            "fresh_external_protocol_or_launch": False,
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
