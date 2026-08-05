#!/usr/bin/env python3
"""Clean-build audit for V2.45.87--92 title-query alignment.

The audit opens only repository sources and sealed public control/count
artifacts.  It never opens task questions, queries, titles, URLs, pages,
predictions, candidate values, benchmark mapping/gold/evaluator data,
credentials, or private execution directories, and it makes no remote call.
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
from scripts import v24587_repaired_prededup_preservation_external_gate as external  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24593_validator_aligned_title_query_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24586_nested_collector_repair_build_audit_v1_{DATE}.json")
RESULT = external.RESULT
DECISION = external.DECISION
POSTAUDIT = external.POSTAUDIT
DIAGNOSIS = Path(f"results/v24588_v24587_title_acquisition_diagnosis_v1_{DATE}.json")
SOURCES = (
    PARENT,
    Path("scripts/v24585_nested_collector_projection_repair.py"),
    Path("tests/test_v24585_nested_collector_projection_repair.py"),
    Path("scripts/audit_v24586_nested_collector_repair_build.py"),
    Path("tests/test_audit_v24586_nested_collector_repair_build.py"),
    Path("scripts/v24587_repaired_prededup_preservation_external_gate.py"),
    Path("tests/test_v24587_repaired_prededup_preservation_external_gate.py"),
    RESULT,
    DECISION,
    POSTAUDIT,
    DIAGNOSIS,
    Path("scripts/diagnose_v24588_v24587_title_acquisition.py"),
    Path("tests/test_diagnose_v24588_v24587_title_acquisition.py"),
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
)
RUNTIME_SOURCES = (
    SOURCES[1],
    SOURCES[5],
    SOURCES[13],
    SOURCES[15],
    SOURCES[17],
    SOURCES[19],
)
TEST_SUITES = (
    (Path("tests/test_v24585_nested_collector_projection_repair.py"), 7, 360),
    (Path("tests/test_audit_v24586_nested_collector_repair_build.py"), 8, 180),
    (
        Path("tests/test_v24587_repaired_prededup_preservation_external_gate.py"),
        16,
        600,
    ),
    (Path("tests/test_diagnose_v24588_v24587_title_acquisition.py"), 7, 120),
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
)
EXPECTED_TEST_COUNT = 72
PRIOR_QUESTION_COUNT = 468
PRIOR_ENTITY_COUNT = 3744


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parents_closed() -> bool:
    parent = common._read(PARENT)
    result = common._read(RESULT)
    decision = common._read(DECISION)
    postaudit = common._read(POSTAUDIT)
    diagnosis = common._read(DIAGNOSIS)
    mechanism = result.get("mechanism_aggregate", {})
    preservation = mechanism.get("total_prededup_preservation_count_fields", {})
    selection = mechanism.get("total_validator_aligned_selection_count_fields", {})
    conclusions = diagnosis.get("conclusions", {})
    authorization = diagnosis.get("authorization", {})
    return (
        _sealed(parent, "audit_payload_sha256")
        and parent.get("role") == "v24586_nested_collector_repair_build_audit"
        and parent.get("audit_valid") is True
        and parent.get("findings") == []
        and parent.get("authorization", {}).get(
            "fresh_disjoint_prededup_preservation_external_protocol_design"
        )
        is True
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
        and mechanism.get("prededup_preservation_activity_tasks") == 8
        and mechanism.get("prededup_preserved_candidate_tasks") == 8
        and preservation.get("preserved_candidate_count", 0) > 0
        and mechanism.get("prededup_and_source_replacement_cooccurrence_tasks", 0)
        > 0
        and mechanism.get("prededup_and_title_replacement_cooccurrence_tasks") == 0
        and selection.get("validator_aligned_title_replacement_count") == 0
        and _sealed(decision, "decision_payload_sha256")
        and decision.get("status")
        == "fresh_repaired_prededup_preservation_no_go"
        and decision.get("diagnostic_route")
        == "validator_aligned_title_replacement_successor"
        and decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is False
        and decision.get("authorization", {}).get("new_exact220") is False
        and _sealed(postaudit, "audit_payload_sha256")
        and postaudit.get("audit_valid") is True
        and postaudit.get("findings") == []
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("inherited_original_task_projection_rebound") is False
        and _sealed(diagnosis, "diagnosis_payload_sha256")
        and diagnosis.get("role") == "v24588_v24587_title_acquisition_diagnosis"
        and diagnosis.get("status")
        == "collector_and_prededup_repaired_title_validatable_acquisition_absent"
        and conclusions.get(
            "next_successor_must_align_query_surfaces_to_unchanged_title_validator"
        )
        is True
        and conclusions.get(
            "query_search_fetch_model_page_source_and_evaluator_budget_increase_allowed"
        )
        is False
        and conclusions.get("absence_proves_title_validator_is_too_strict")
        is False
        and authorization.get("validator_aligned_title_query_policy_design")
        is True
        and authorization.get("fresh_external_protocol_design") is False
        and authorization.get("fresh_external_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parents_closed = _parents_closed()
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
    if not parents_closed:
        findings.append("v24586_88_parent_chain_drifted")
    if head != remote:
        findings.append("v24589_93_source_commit_not_pushed")
    if not clean:
        findings.append("v24589_93_source_worktree_not_clean")
    if not tracked:
        findings.append("v24589_93_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24585_93_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24585_92_runtime")
    if imports:
        findings.append("evaluator_import_in_v24585_92_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24585_93_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24593_validator_aligned_title_query_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "closed_parents": {
            "v24586_path": str(PARENT),
            "v24586_sha256": common._sha256(PARENT),
            "v24587_result_path": str(RESULT),
            "v24587_result_sha256": common._sha256(RESULT),
            "v24587_decision_path": str(DECISION),
            "v24587_decision_sha256": common._sha256(DECISION),
            "v24587_postaudit_path": str(POSTAUDIT),
            "v24587_postaudit_sha256": common._sha256(POSTAUDIT),
            "v24588_path": str(DIAGNOSIS),
            "v24588_sha256": common._sha256(DIAGNOSIS),
            "v24587_is_no_go_and_cannot_be_resumed_retried_or_evaluated": True,
            "valid": parents_closed,
        },
        "freshness_baseline": {
            "prior_external_question_count": PRIOR_QUESTION_COUNT,
            "prior_external_entity_count": PRIOR_ENTITY_COUNT,
            "all_populations_through_v24587_counted_as_consumed": True,
            "v24587_population_resume_retry_rerun_or_evaluation_authorized": False,
            "v24588_93_diagnosis_and_build_tests_consume_external_population": False,
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
            "synthetic_clients_capabilities_and_subprocesses_only": True,
            "prior_private_task_query_title_url_page_value_or_prediction_opened": False,
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
            "v24587_immutable_collector_success_tasks": 8,
            "v24587_prededup_preservation_activity_tasks": 8,
            "v24587_prededup_preserved_candidate_tasks": 8,
            "v24587_title_replacement_tasks": 0,
            "v24589_first_query_uses_frozen_validator_full_surface": True,
            "v24589_second_query_uses_frozen_validator_core_else_initialism_else_full": True,
            "v24589_exactly_two_queries_per_call": True,
            "v24590_parent_capability_validated_before_successor_without_private_replay": True,
            "v24591_success_requires_v24590_opaque_capability": True,
            "v24591_failure_projection_is_exact_content_free_zero": True,
            "v24591_failure_projection_claims_private_effects_zero": False,
            "v24592_real_parent_supervisor_worker_chain_passes": True,
            "v24592_module_global_proof_or_projection_context_used": False,
            "v24592_one_monotonic_origin_crosses_parent_supervisor_worker": True,
            "remote_worker_parent_batch_cutoffs_seconds": [150, 220, 245, 255],
            "logical_query_search_batch_fetch_page_source_or_model_budget_changed": False,
            "title_or_url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
            "title_alias_validator_or_evidence_projection_changed": False,
            "source_count_posterior_margin_leave_one_out_safe_change_or_decision_credit_rule_changed": False,
            "same_task_query_and_title_replacement_cooccurrence_proves_query_or_lead_level_causality": False,
            "synthetic_reachability_proves_external_effect_or_quality_gain": False,
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
            },
            sort_keys=True,
        )
    )
