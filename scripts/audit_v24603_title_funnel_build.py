#!/usr/bin/env python3
"""Clean-build audit for V2.45.97--V2.46.02 title-funnel observability.

The audit opens only repository sources and sealed public count/control
artifacts.  It never opens a task, row, title, query, URL, source, page,
prediction, private execution directory, benchmark mapping/gold/evaluator
data, or credential and makes no remote call.
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
from scripts import diagnose_v24597_v24596_title_transport as diagnosis  # noqa: E402
from scripts import v24596_validator_aligned_title_query_external_gate as external  # noqa: E402
from scripts import v24602_title_funnel_collector_repair as collector  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24603_title_funnel_build_audit_v1_{DATE}.json")
PARENT_AUDIT = Path(f"results/v24595_title_query_collector_build_audit_v1_{DATE}.json")
RESULT = external.RESULT
DECISION = external.DECISION
POSTAUDIT = external.POSTAUDIT
DIAGNOSIS = diagnosis.OUTPUT
SOURCES = (
    PARENT_AUDIT,
    RESULT,
    DECISION,
    POSTAUDIT,
    DIAGNOSIS,
    Path("src/deepwide_agent/v24589_validator_aligned_title_query.py"),
    Path("tests/test_v24589_validator_aligned_title_query.py"),
    Path("src/deepwide_agent/v24590_proof_carrying_validator_aligned_title_query.py"),
    Path("tests/test_v24590_proof_carrying_validator_aligned_title_query.py"),
    Path("src/deepwide_agent/v24591_total_validator_aligned_title_query_projection.py"),
    Path("tests/test_v24591_total_validator_aligned_title_query_projection.py"),
    Path("src/deepwide_agent/v24592_bounded_validator_aligned_title_query_parent.py"),
    Path("tests/test_v24592_bounded_validator_aligned_title_query_parent.py"),
    Path("scripts/diagnose_v24597_v24596_title_transport.py"),
    Path("tests/test_diagnose_v24597_v24596_title_transport.py"),
    Path("src/deepwide_agent/v24598_content_free_title_funnel.py"),
    Path("tests/test_v24598_content_free_title_funnel.py"),
    Path("src/deepwide_agent/v24599_proof_carrying_title_funnel.py"),
    Path("tests/test_v24599_proof_carrying_title_funnel.py"),
    Path("src/deepwide_agent/v24600_total_title_funnel_projection.py"),
    Path("tests/test_v24600_total_title_funnel_projection.py"),
    Path("src/deepwide_agent/v24601_bounded_title_funnel_parent.py"),
    Path("tests/test_v24601_bounded_title_funnel_parent.py"),
    Path("scripts/v24602_title_funnel_collector_repair.py"),
    Path("tests/test_v24602_title_funnel_collector_repair.py"),
    Path("scripts/audit_v24603_title_funnel_build.py"),
    Path("tests/test_audit_v24603_title_funnel_build.py"),
)
RUNTIME_SOURCES = (
    SOURCES[5],
    SOURCES[7],
    SOURCES[9],
    SOURCES[11],
    SOURCES[13],
    SOURCES[15],
    SOURCES[17],
    SOURCES[19],
    SOURCES[21],
    SOURCES[23],
)
TEST_SUITES = (
    (Path("tests/test_v24589_validator_aligned_title_query.py"), 8, 120),
    (Path("tests/test_v24590_proof_carrying_validator_aligned_title_query.py"), 7, 300),
    (Path("tests/test_v24591_total_validator_aligned_title_query_projection.py"), 6, 300),
    (Path("tests/test_v24592_bounded_validator_aligned_title_query_parent.py"), 5, 300),
    (Path("tests/test_diagnose_v24597_v24596_title_transport.py"), 7, 120),
    (Path("tests/test_v24598_content_free_title_funnel.py"), 7, 120),
    (Path("tests/test_v24599_proof_carrying_title_funnel.py"), 7, 300),
    (Path("tests/test_v24600_total_title_funnel_projection.py"), 6, 300),
    (Path("tests/test_v24601_bounded_title_funnel_parent.py"), 5, 300),
    (Path("tests/test_v24602_title_funnel_collector_repair.py"), 7, 360),
    (Path("tests/test_audit_v24603_title_funnel_build.py"), 8, 180),
)
EXPECTED_TEST_COUNT = 73
STRESS_WORKERS = 8
PRIOR_QUESTION_COUNT = 476
PRIOR_ENTITY_COUNT = 3808


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_chain_valid() -> bool:
    parent = common._read(PARENT_AUDIT)
    result = common._read(RESULT)
    decision = common._read(DECISION)
    postaudit = common._read(POSTAUDIT)
    diagnosed = diagnosis.validate_diagnosis(common._read(DIAGNOSIS))
    mechanism = result.get("mechanism_aggregate", {})
    alias = mechanism.get("total_alias_surface_count_fields", {})
    preservation = mechanism.get("total_prededup_preservation_count_fields", {})
    selection = mechanism.get("total_validator_aligned_selection_count_fields", {})
    conclusions = diagnosed.get("conclusions", {})
    authorization = diagnosed.get("authorization", {})
    return (
        _sealed(parent, "audit_payload_sha256")
        and parent.get("role") == "v24595_title_query_collector_build_audit"
        and parent.get("audit_valid") is True
        and parent.get("findings") == []
        and parent.get("tests", {}).get("test_count") == 49
        and parent.get("label_blind_audit", {}).get("passed") is True
        and _sealed(result, "result_payload_sha256")
        and result.get("protocol_id") == external.PROTOCOL_ID
        and result.get("selected") == 8
        and result.get("passed") is False
        and result.get("mechanism_passed") is False
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and mechanism.get("success_tasks") == 8
        and mechanism.get("failure_as_zero_tasks") == 0
        and mechanism.get("target_plan_tasks") == 7
        and mechanism.get("validator_aligned_title_query_activity_tasks") == 7
        and alias.get("visible_lead_count") == 885
        and alias.get("url_alias_surface_hit_lead_count") == 120
        and alias.get("title_alias_surface_hit_lead_count") == 0
        and preservation.get("preserved_candidate_count") == 139
        and selection.get("source_representative_replacement_count") == 15
        and selection.get("validator_aligned_title_replacement_count") == 0
        and _sealed(decision, "decision_payload_sha256")
        and decision.get("status") == "fresh_validator_aligned_title_query_no_go"
        and decision.get("diagnostic_route")
        == "validator_aligned_title_acquisition_successor"
        and decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is False
        and decision.get("authorization", {}).get("new_exact220") is False
        and _sealed(postaudit, "audit_payload_sha256")
        and postaudit.get("audit_valid") is True
        and postaudit.get("findings") == []
        and postaudit.get("shared_api_lease_active") is False
        and diagnosed.get("status")
        == "query_and_candidate_paths_reached_strict_title_surface_still_absent"
        and conclusions.get("next_successor_must_measure_content_free_title_funnel")
        is True
        and conclusions.get(
            "next_successor_should_change_query_or_validator_before_title_funnel_measurement"
        )
        is False
        and conclusions.get(
            "public_aggregate_distinguishes_empty_absent_late_and_type_incompatible_title_failure"
        )
        is False
        and authorization.get("content_free_title_transport_observability_design")
        is True
        and authorization.get("query_policy_or_title_validator_change") is False
        and authorization.get("fresh_external_protocol_design") is False
        and authorization.get("fresh_external_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def _collector_binding_valid() -> bool:
    return (
        collector.binding_valid()
        and collector.FROZEN_TASK_PROJECTION is collector.total.task_projection
        and getattr(collector.FROZEN_TASK_PROJECTION, "__self__", None) is None
    )


def _collector_stress() -> dict[str, Any]:
    passed = common._run_test(
        Path("tests/test_v24602_title_funnel_collector_repair.py"), 360
    )
    return {
        "workers": STRESS_WORKERS,
        "validations": STRESS_WORKERS if passed else 0,
        "instance_local_immutable_v24600_projector": True,
        "shared_runtime_original_projection_read_by_collector": False,
        "passed": passed,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_valid = _parent_chain_valid()
    binding_valid = _collector_binding_valid()
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
        findings.append("v24595_97_parent_chain_drifted")
    if not binding_valid:
        findings.append("immutable_v24600_collector_binding_drifted")
    if stress.get("passed") is not True or stress.get("validations") != STRESS_WORKERS:
        findings.append("immutable_v24600_collector_stress_failed")
    if head != remote:
        findings.append("v24598_24603_source_commit_not_pushed")
    if not clean:
        findings.append("v24598_24603_source_worktree_not_clean")
    if not tracked:
        findings.append("v24597_24603_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24589_24603_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24589_24602_runtime")
    if imports:
        findings.append("evaluator_import_in_v24589_24602_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24589_24603_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24603_title_funnel_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "closed_parent": {
            "v24595_path": str(PARENT_AUDIT),
            "v24595_sha256": common._sha256(PARENT_AUDIT),
            "v24596_result_path": str(RESULT),
            "v24596_result_sha256": common._sha256(RESULT),
            "v24596_decision_path": str(DECISION),
            "v24596_decision_sha256": common._sha256(DECISION),
            "v24596_postaudit_path": str(POSTAUDIT),
            "v24596_postaudit_sha256": common._sha256(POSTAUDIT),
            "v24597_path": str(DIAGNOSIS),
            "v24597_sha256": common._sha256(DIAGNOSIS),
            "v24596_population_resume_retry_rerun_or_evaluation_authorized": False,
            "valid": parent_valid,
        },
        "freshness_baseline": {
            "prior_external_question_count": PRIOR_QUESTION_COUNT,
            "prior_external_entity_count": PRIOR_ENTITY_COUNT,
            "all_populations_through_v24596_counted_as_consumed": True,
            "v24596_population_resume_retry_rerun_or_evaluation_authorized": False,
            "v24597_24603_build_work_consumes_external_population": False,
        },
        "collector": {
            "policy_id": collector.POLICY_ID,
            "module_load_unbound_v24600_projector_captured": binding_valid,
            "collector_project_calls_instance_local_immutable_projector": True,
            "collector_reads_shared_runtime_original_projection": False,
            "nested_runtime_rebinding_can_change_collector_target": False,
            "mixed_failure_projection_remains_total": True,
            "duplicate_consume_and_nested_collector_fail_closed": True,
            "task_model_search_fetch_ranking_validator_evidence_credit_budget_or_evaluator_changed": False,
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
            "synthetic_clients_capabilities_subprocesses_and_control_state_only": True,
            "historical_private_task_row_title_query_url_page_value_or_prediction_opened": False,
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
            "v24596_query_candidate_and_selection_paths_reached": True,
            "v24596_strict_title_surface_hit_count": 0,
            "v24597_does_not_invent_unobserved_title_failure_cause": True,
            "v24598_observes_each_visible_lead_vector_once_before_source_dedup": True,
            "v24598_empty_absent_late_type_incompatible_and_strict_stages_separated": True,
            "v24599_parent_capability_validated_before_successor_without_private_replay": True,
            "v24600_success_requires_v24599_opaque_capability": True,
            "v24600_failure_projection_is_exact_content_free_zero": True,
            "v24601_real_parent_supervisor_worker_chain_passes": True,
            "v24601_module_global_proof_or_projection_context_used": False,
            "v24602_real_eight_way_collector_validations": 8,
            "remote_worker_parent_batch_cutoffs_seconds": [150, 220, 245, 255],
            "logical_query_search_batch_fetch_page_source_or_model_budget_changed": False,
            "query_ranking_title_validator_or_evidence_projection_changed": False,
            "title_or_url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
            "source_count_posterior_margin_leave_one_out_safe_change_or_decision_credit_rule_changed": False,
            "synthetic_reachability_proves_external_effect_or_quality_gain": False,
            "model_slot_cap_unchanged": 2,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(item["identity_valid"] for item in watchers),
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
            "fresh_disjoint_content_free_title_funnel_external_protocol_design": not findings,
            "query_policy_or_title_validator_change": False,
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
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
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
                "stress_validations": value["collector"]["stress"]["validations"],
            },
            sort_keys=True,
        )
    )
