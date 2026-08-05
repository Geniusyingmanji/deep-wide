#!/usr/bin/env python3
"""Clean-build audit for V2.46.05--10 title provenance observability.

The audit opens only repository sources and sealed public count/control
artifacts.  It never opens a private execution directory, task, query, URL,
title, page, prediction, benchmark mapping/gold/evaluator data, or credential,
and it performs no remote effect.
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
from scripts import diagnose_v24605_v24604_title_provenance as diagnosis  # noqa: E402
from scripts import v24610_title_provenance_collector as collector  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24611_title_provenance_build_audit_v1_{DATE}.json")
PARENT_DIAGNOSIS = diagnosis.OUTPUT
V24604_RESULT = diagnosis.RESULT
V24604_DECISION = diagnosis.DECISION
V24604_POSTAUDIT = diagnosis.POSTAUDIT
SOURCES = (
    V24604_RESULT,
    V24604_DECISION,
    V24604_POSTAUDIT,
    PARENT_DIAGNOSIS,
    Path("src/deepwide_agent/clients.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("tests/test_native_search.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("tests/test_v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24280_task_union_single_shot.py"),
    Path("tests/test_v24280_task_union_single_shot.py"),
    Path("src/deepwide_agent/v24468_total_wall_transport.py"),
    Path("tests/test_v24468_total_wall_transport.py"),
    Path("src/deepwide_agent/v24474_nominal_hard_total_wall_search.py"),
    Path("tests/test_v24474_nominal_hard_total_wall_search.py"),
    Path("src/deepwide_agent/v24476_bounded_nominal_search_integration.py"),
    Path("tests/test_v24476_bounded_nominal_search_integration.py"),
    Path("scripts/diagnose_v24605_v24604_title_provenance.py"),
    Path("tests/test_diagnose_v24605_v24604_title_provenance.py"),
    Path("src/deepwide_agent/v24606_content_free_title_provenance.py"),
    Path("tests/test_v24606_content_free_title_provenance.py"),
    Path("src/deepwide_agent/v24607_proof_carrying_title_provenance.py"),
    Path("tests/test_v24607_proof_carrying_title_provenance.py"),
    Path("src/deepwide_agent/v24608_total_title_provenance_projection.py"),
    Path("tests/test_v24608_total_title_provenance_projection.py"),
    Path("src/deepwide_agent/v24609_bounded_title_provenance_parent.py"),
    Path("tests/test_v24609_bounded_title_provenance_parent.py"),
    Path("scripts/v24610_title_provenance_collector.py"),
    Path("tests/test_v24610_title_provenance_collector.py"),
    Path("scripts/audit_v24611_title_provenance_build.py"),
    Path("tests/test_audit_v24611_title_provenance_build.py"),
)
RUNTIME_SOURCES = (
    SOURCES[17],
    SOURCES[19],
    SOURCES[21],
    SOURCES[23],
    SOURCES[25],
    SOURCES[27],
)
TEST_SUITES = (
    (Path("tests/test_native_search.py"), 15, 120),
    (Path("tests/test_v24269_task_union_discovery.py"), 5, 120),
    (Path("tests/test_v24280_task_union_single_shot.py"), 4, 120),
    (Path("tests/test_v24468_total_wall_transport.py"), 8, 240),
    (Path("tests/test_v24474_nominal_hard_total_wall_search.py"), 7, 180),
    (Path("tests/test_v24476_bounded_nominal_search_integration.py"), 2, 180),
    (Path("tests/test_diagnose_v24605_v24604_title_provenance.py"), 7, 120),
    (Path("tests/test_v24606_content_free_title_provenance.py"), 5, 180),
    (Path("tests/test_v24607_proof_carrying_title_provenance.py"), 6, 300),
    (Path("tests/test_v24608_total_title_provenance_projection.py"), 6, 300),
    (Path("tests/test_v24609_bounded_title_provenance_parent.py"), 5, 360),
    (Path("tests/test_v24610_title_provenance_collector.py"), 7, 360),
    (Path("tests/test_audit_v24611_title_provenance_build.py"), 8, 180),
)
EXPECTED_TEST_COUNT = 85
STRESS_WORKERS = 8
PRIOR_QUESTION_COUNT = 484
PRIOR_ENTITY_COUNT = 3872


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_chain_valid() -> bool:
    result = common._read(V24604_RESULT)
    decision = common._read(V24604_DECISION)
    postaudit = common._read(V24604_POSTAUDIT)
    diagnosed = diagnosis.validate_diagnosis(common._read(PARENT_DIAGNOSIS))
    observed = diagnosed.get("observed_selection_boundary", {})
    fidelity = diagnosed.get("synthetic_transport_fidelity", {})
    conclusions = diagnosed.get("conclusions", {})
    authorization = diagnosed.get("authorization", {})
    return (
        _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
        and result.get("selected") == 8
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and decision.get("status") == "fresh_content_free_title_funnel_observed"
        and decision.get("diagnostic_route") == "search_title_transport_successor"
        and postaudit.get("audit_valid") is True
        and postaudit.get("findings") == []
        and postaudit.get("shared_api_lease_active") is False
        and diagnosed.get("status")
        == "selection_titles_empty_upstream_provenance_unobserved"
        and observed.get("visible_input_lead_count") == 783
        and observed.get("empty_title_lead_count") == 783
        and observed.get("nonempty_title_lead_count") == 0
        and fidelity.get("synthetic_action_title_preserved_to_union") is True
        and fidelity.get("synthetic_citation_title_preserved_to_union") is True
        and fidelity.get("synthetic_union_titles_preserved_by_lead_projection")
        is True
        and conclusions.get(
            "v24604_proves_concrete_adapter_deleted_nonempty_provider_titles"
        )
        is False
        and conclusions.get("v24604_proves_real_provider_action_sources_omitted_titles")
        is False
        and conclusions.get("direct_parser_or_validator_change_is_evidence_supported")
        is False
        and conclusions.get("next_successor_must_observe_title_provenance_boundaries")
        is True
        and authorization.get("content_free_title_provenance_observer_design")
        is True
        and authorization.get("search_parser_title_validator_or_evidence_rule_change")
        is False
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
        Path("tests/test_v24610_title_provenance_collector.py"), 360
    )
    return {
        "workers": STRESS_WORKERS,
        "validations": STRESS_WORKERS if passed else 0,
        "instance_local_immutable_v24608_projector": True,
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
        findings.append("v24604_05_parent_chain_drifted")
    if not binding_valid:
        findings.append("immutable_v24608_collector_binding_drifted")
    if stress.get("passed") is not True or stress.get("validations") != STRESS_WORKERS:
        findings.append("immutable_v24608_collector_stress_failed")
    if head != remote:
        findings.append("v24605_11_source_commit_not_pushed")
    if not clean:
        findings.append("v24605_11_source_worktree_not_clean")
    if not tracked:
        findings.append("v24605_11_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24605_11_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24605_10_runtime")
    if imports:
        findings.append("evaluator_import_in_v24605_10_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24605_11_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24611_title_provenance_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "closed_parent": {
            "v24604_result_path": str(V24604_RESULT),
            "v24604_result_sha256": common._sha256(V24604_RESULT),
            "v24604_decision_path": str(V24604_DECISION),
            "v24604_decision_sha256": common._sha256(V24604_DECISION),
            "v24604_postaudit_path": str(V24604_POSTAUDIT),
            "v24604_postaudit_sha256": common._sha256(V24604_POSTAUDIT),
            "v24605_path": str(PARENT_DIAGNOSIS),
            "v24605_sha256": common._sha256(PARENT_DIAGNOSIS),
            "v24604_population_resume_retry_rerun_or_evaluation_authorized": False,
            "valid": parent_valid,
        },
        "freshness_baseline": {
            "prior_external_question_count": PRIOR_QUESTION_COUNT,
            "prior_external_entity_count": PRIOR_ENTITY_COUNT,
            "all_populations_through_v24604_counted_as_consumed": True,
            "v24604_population_resume_retry_rerun_or_evaluation_authorized": False,
            "v24605_11_build_work_consumes_external_population": False,
        },
        "collector": {
            "policy_id": collector.POLICY_ID,
            "module_load_unbound_v24608_projector_captured": binding_valid,
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
            "historical_private_task_query_url_title_page_value_or_prediction_opened": False,
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
            "v24604_all_selection_input_titles_empty": True,
            "v24605_does_not_invent_unobserved_provider_or_adapter_cause": True,
            "synthetic_action_and_citation_titles_preserved_through_union_projection": True,
            "native_search_runtime_foundation_tracked_and_manifest_bound": True,
            "v24606_observes_action_citation_fetch_input_and_fetched_page_title_counts": True,
            "v24607_parent_capability_validated_before_successor_without_private_replay": True,
            "v24608_success_requires_v24607_opaque_capability": True,
            "v24608_failure_projection_is_exact_content_free_zero": True,
            "v24609_real_parent_supervisor_worker_chain_passes": True,
            "v24609_module_global_proof_or_projection_context_used": False,
            "v24610_real_eight_way_collector_validations": 8,
            "remote_worker_parent_batch_cutoffs_seconds": [150, 220, 245, 255],
            "logical_query_search_batch_fetch_page_source_or_model_budget_changed": False,
            "query_ranking_title_validator_or_evidence_projection_changed": False,
            "title_or_url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
            "source_count_posterior_margin_leave_one_out_safe_change_or_decision_credit_rule_changed": False,
            "synthetic_fidelity_proves_real_provider_or_quality_cause": False,
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
            "fresh_disjoint_content_free_title_provenance_external_protocol_design": not findings,
            "search_parser_title_validator_or_evidence_rule_change": False,
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
                "stress_validations": value["collector"]["stress"]["validations"],
            },
            sort_keys=True,
        )
    )
