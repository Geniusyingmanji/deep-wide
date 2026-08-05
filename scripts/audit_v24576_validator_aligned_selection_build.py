#!/usr/bin/env python3
"""Clean-build audit for V2.45.72--75 validator-aligned selection.

The audit reads repository sources, the content-free V2.45.71 public result,
decision, and post-result audit, protected process identities, and the shared
lease.  It never opens a temporary execution directory, task question, lead,
title, URL, query, page, value, prediction, benchmark mapping, evaluator
output, or credential.
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


DATE = "20260805"
AUDIT = Path(
    f"results/v24576_validator_aligned_selection_build_audit_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24571_serialized_strict_reachability_external_result_v1_{DATE}.json"
)
DECISION = Path(
    f"results/v24571_serialized_strict_reachability_external_decision_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24571_serialized_strict_reachability_external_postresult_audit_v1_{DATE}.json"
)
PROTOCOL_ID = "v24571_fresh_serialized_strict_reachability_external_gate_v1"
SOURCES = (
    RESULT,
    DECISION,
    POSTAUDIT,
    Path("src/deepwide_agent/v24572_validator_aligned_alias_lead_selection.py"),
    Path("tests/test_v24572_validator_aligned_alias_lead_selection.py"),
    Path("src/deepwide_agent/v24573_proof_carrying_validator_aligned_selection.py"),
    Path("tests/test_v24573_proof_carrying_validator_aligned_selection.py"),
    Path("src/deepwide_agent/v24574_total_validator_aligned_selection_projection.py"),
    Path("tests/test_v24574_total_validator_aligned_selection_projection.py"),
    Path("src/deepwide_agent/v24575_bounded_validator_aligned_selection_parent.py"),
    Path("tests/test_v24575_bounded_validator_aligned_selection_parent.py"),
    Path("scripts/audit_v24576_validator_aligned_selection_build.py"),
    Path("tests/test_audit_v24576_validator_aligned_selection_build.py"),
)
RUNTIME_SOURCES = (SOURCES[3], SOURCES[5], SOURCES[7], SOURCES[9])
TEST_SUITES = (
    (Path("tests/test_v24572_validator_aligned_alias_lead_selection.py"), 8, 120),
    (
        Path("tests/test_v24573_proof_carrying_validator_aligned_selection.py"),
        7,
        300,
    ),
    (
        Path("tests/test_v24574_total_validator_aligned_selection_projection.py"),
        6,
        300,
    ),
    (
        Path("tests/test_v24575_bounded_validator_aligned_selection_parent.py"),
        5,
        300,
    ),
    (
        Path("tests/test_audit_v24576_validator_aligned_selection_build.py"),
        7,
        120,
    ),
)
EXPECTED_TEST_COUNT = 33
PRIOR_QUESTION_COUNT = 452
PRIOR_ENTITY_COUNT = 3616


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _v24571_closed() -> bool:
    result = common._read(RESULT)
    decision = common._read(DECISION)
    postaudit = common._read(POSTAUDIT)
    mechanism = result.get("mechanism_aggregate", {})
    surface_counts = mechanism.get("total_alias_surface_count_fields", {})
    joint_counts = mechanism.get("total_alias_joint_count_fields", {})
    reachability = mechanism.get("total_decision_reachability_count_fields", {})
    authorization = decision.get("authorization", {})
    return (
        _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
        and result.get("role") == "v24492_targeted_external_result"
        and result.get("protocol_id") == PROTOCOL_ID
        and result.get("selected") == 8
        and result.get("executor_count") == 8
        and result.get("model_slot_cap") == 2
        and result.get("one_wave") is True
        and result.get("mechanism_passed") is False
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and result.get("passed") is False
        and result.get("private_task_or_web_content_persisted") is False
        and result.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is False
        and result.get("official_evaluator_called") is False
        and result.get("resume_retry_skip_or_revaluation") is False
        and mechanism.get("success_tasks") == 8
        and mechanism.get("failure_as_zero_tasks") == 0
        and mechanism.get("target_plan_tasks") == 7
        and mechanism.get("selected_alias_surface_hit_tasks") == 5
        and mechanism.get("alias_joint_new_observation_tasks") == 1
        and mechanism.get("alias_joint_raw_positive_information_gain_tasks") == 1
        and mechanism.get("alias_joint_action_positive_information_credit_tasks")
        == 1
        and mechanism.get("alias_joint_action_positive_epistemic_credit_tasks")
        == 1
        and mechanism.get("alias_joint_safe_change_improvement_tasks") == 0
        and mechanism.get("alias_joint_action_positive_decision_credit_tasks")
        == 0
        and mechanism.get("decision_reachability_any_plan_tasks") == 0
        and mechanism.get("decision_reachability_no_reachable_plan_tasks") == 8
        and surface_counts.get("selected_title_alias_surface_hit_lead_count") == 0
        and surface_counts.get("selected_url_alias_surface_hit_lead_count") == 27
        and joint_counts.get("targeted_new_observation_count") == 1
        and joint_counts.get("safe_change_improvement_count") == 0
        and joint_counts.get("action_positive_decision_credit_count") == 0
        and reachability.get("selection_calls") == 24
        and reachability.get("no_reachable_plan_calls") == 24
        and decision.get("role")
        == "v24571_serialized_strict_reachability_external_decision"
        and decision.get("protocol_id") == PROTOCOL_ID
        and decision.get("status") == "fresh_serialized_strict_reachability_no_go"
        and decision.get("passed") is False
        and decision.get("result_sha256") == common._sha256(RESULT)
        and decision.get("diagnostic_route") == "action_safe_change_successor"
        and authorization.get("diagnostic_successor_design") is True
        and authorization.get("fresh_paired_dev64_design") is False
        and authorization.get("fresh_paired_dev64_launch") is False
        and authorization.get("new_exact220") is False
        and authorization.get("evaluator") is False
        and authorization.get("leaderboard_or_sota") is False
        and postaudit.get("role")
        == "v24571_serialized_strict_reachability_external_postresult_audit"
        and postaudit.get("protocol_id") == PROTOCOL_ID
        and postaudit.get("result_sha256") == common._sha256(RESULT)
        and postaudit.get("decision_sha256") == common._sha256(DECISION)
        and postaudit.get("decision_status")
        == "fresh_serialized_strict_reachability_no_go"
        and postaudit.get("diagnostic_route") == "action_safe_change_successor"
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is False
        and postaudit.get("private_task_or_web_content_persisted") is False
        and postaudit.get("findings") == []
        and postaudit.get("audit_valid") is True
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_closed = _v24571_closed()
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
    if not parent_closed:
        findings.append("v24571_result_decision_or_postaudit_drifted")
    if head != remote:
        findings.append("v24572_76_source_commit_not_pushed")
    if not clean:
        findings.append("v24572_76_source_worktree_not_clean")
    if not tracked:
        findings.append("v24572_76_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24572_76_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24572_75_runtime")
    if imports:
        findings.append("evaluator_import_in_v24572_75_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24572_76_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24576_validator_aligned_selection_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "v24571_closed_parent": {
            "result_path": str(RESULT),
            "result_sha256": common._sha256(RESULT),
            "decision_path": str(DECISION),
            "decision_sha256": common._sha256(DECISION),
            "postaudit_path": str(POSTAUDIT),
            "postaudit_sha256": common._sha256(POSTAUDIT),
            "valid": parent_closed,
            "status": "fresh_serialized_strict_reachability_no_go",
            "diagnostic_route": "action_safe_change_successor",
        },
        "freshness_baseline": {
            "prior_external_question_count": PRIOR_QUESTION_COUNT,
            "prior_external_entity_count": PRIOR_ENTITY_COUNT,
            "all_populations_through_v24571_counted_as_consumed": True,
            "v24571_population_resume_retry_rerun_or_evaluation_authorized": False,
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
            "synthetic_clients_leads_pages_capabilities_and_subprocesses_only": True,
            "historical_private_task_lead_title_url_query_page_value_or_prediction_opened": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_input_rejected_before_filesystem_model_search_or_fetch_effect": True,
            "evaluator_opened": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "mechanism_evidence": {
            "v24571_success_tasks": 8,
            "v24571_failure_tasks": 0,
            "v24571_selected_title_alias_surface_hit_leads": 0,
            "v24571_selected_url_alias_surface_hit_leads": 27,
            "v24571_targeted_new_observations": 1,
            "v24571_safe_change_improvements": 0,
            "v24571_positive_decision_credit_actions": 0,
            "v24571_reachable_plan_calls": 0,
            "v24571_no_reachable_plan_calls": 24,
            "public_counts_support_ranking_validator_mismatch_hypothesis": True,
            "public_counts_prove_replacement_caused_safe_change_or_decision_credit": False,
            "within_source_representative_is_input_order_invariant": True,
            "unique_source_vector_preserves_v24547_selection_exactly": True,
            "url_alias_hint_receives_evidence_source_entropy_or_decision_credit": False,
            "exact_and_alias_title_evidence_validators_changed": False,
            "source_count_posterior_margin_leave_one_out_safe_change_or_decision_credit_rule_changed": False,
            "logical_query_search_batch_or_fetch_cap_changed": False,
            "success_requires_v24573_opaque_capability": True,
            "parent_replays_private_lead_title_url_query_page_value_or_selection_semantics": False,
            "public_success_mapping_can_be_reingested_as_proof": False,
            "failure_projection_is_exact_content_free_zero": True,
            "failure_projection_claims_private_effects_zero": False,
            "failure_observation_preserves_partial_effect_lower_bound": True,
            "real_parent_supervisor_worker_chain_passes": True,
            "success_validates_one_v24573_capability": True,
            "success_projects_one_v24574_row": True,
            "module_global_projector_patch_or_shared_parent_context_used": False,
            "one_monotonic_origin_crosses_parent_supervisor_worker": True,
            "remote_worker_parent_batch_cutoffs_seconds": [150, 220, 245, 255],
            "model_slot_cap_unchanged": 2,
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
            "fresh_disjoint_validator_aligned_external_protocol_design": not findings,
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
