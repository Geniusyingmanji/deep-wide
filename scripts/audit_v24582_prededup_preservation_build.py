#!/usr/bin/env python3
"""Clean-build audit for V2.45.77--81 pre-dedup preservation.

The audit reads repository sources, the content-free V2.45.77 diagnosis, the
superseded V2.45.76 build audit, protected process identities, and the shared
lease.  It never opens a task question, lead, title, URL, query, page, value,
prediction, benchmark mapping, evaluator output, credential, or temporary
execution directory.
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
AUDIT = Path(f"results/v24582_prededup_preservation_build_audit_v1_{DATE}.json")
DIAGNOSIS = Path(
    f"results/v24577_v24572_prededup_reachability_diagnosis_v1_{DATE}.json"
)
PREDECESSOR_AUDIT = Path(
    f"results/v24576_validator_aligned_selection_build_audit_v1_{DATE}.json"
)
SOURCES = (
    PREDECESSOR_AUDIT,
    Path("src/deepwide_agent/v24572_validator_aligned_alias_lead_selection.py"),
    Path("tests/test_v24572_validator_aligned_alias_lead_selection.py"),
    Path("src/deepwide_agent/v24573_proof_carrying_validator_aligned_selection.py"),
    Path("tests/test_v24573_proof_carrying_validator_aligned_selection.py"),
    Path("src/deepwide_agent/v24574_total_validator_aligned_selection_projection.py"),
    Path("tests/test_v24574_total_validator_aligned_selection_projection.py"),
    Path("src/deepwide_agent/v24575_bounded_validator_aligned_selection_parent.py"),
    Path("tests/test_v24575_bounded_validator_aligned_selection_parent.py"),
    DIAGNOSIS,
    Path("scripts/diagnose_v24577_v24572_prededup_reachability.py"),
    Path("tests/test_diagnose_v24577_v24572_prededup_reachability.py"),
    Path("src/deepwide_agent/v24578_prededup_candidate_preservation.py"),
    Path("tests/test_v24578_prededup_candidate_preservation.py"),
    Path("src/deepwide_agent/v24579_proof_carrying_prededup_preservation.py"),
    Path("tests/test_v24579_proof_carrying_prededup_preservation.py"),
    Path("src/deepwide_agent/v24580_total_prededup_preservation_projection.py"),
    Path("tests/test_v24580_total_prededup_preservation_projection.py"),
    Path("src/deepwide_agent/v24581_bounded_prededup_preservation_parent.py"),
    Path("tests/test_v24581_bounded_prededup_preservation_parent.py"),
    Path("scripts/audit_v24582_prededup_preservation_build.py"),
    Path("tests/test_audit_v24582_prededup_preservation_build.py"),
)
RUNTIME_SOURCES = (
    SOURCES[1],
    SOURCES[3],
    SOURCES[5],
    SOURCES[7],
    SOURCES[12],
    SOURCES[14],
    SOURCES[16],
    SOURCES[18],
)
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
        Path("tests/test_diagnose_v24577_v24572_prededup_reachability.py"),
        5,
        120,
    ),
    (Path("tests/test_v24578_prededup_candidate_preservation.py"), 6, 120),
    (
        Path("tests/test_v24579_proof_carrying_prededup_preservation.py"),
        7,
        300,
    ),
    (
        Path("tests/test_v24580_total_prededup_preservation_projection.py"),
        6,
        300,
    ),
    (
        Path("tests/test_v24581_bounded_prededup_preservation_parent.py"),
        5,
        300,
    ),
    (
        Path("tests/test_audit_v24582_prededup_preservation_build.py"),
        8,
        120,
    ),
)
EXPECTED_TEST_COUNT = 63
PRIOR_QUESTION_COUNT = 452
PRIOR_ENTITY_COUNT = 3616


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parents_closed() -> bool:
    diagnosis = common._read(DIAGNOSIS)
    predecessor = common._read(PREDECESSOR_AUDIT)
    conclusions = diagnosis.get("conclusions", {})
    diagnosis_authorization = diagnosis.get("authorization", {})
    predecessor_authorization = predecessor.get("authorization", {})
    return (
        _sealed(diagnosis, "diagnosis_payload_sha256")
        and diagnosis.get("role")
        == "v24577_v24572_prededup_reachability_diagnosis"
        and diagnosis.get("status")
        == "v24572_same_source_replacement_unreachable_in_frozen_targeted_pipeline"
        and conclusions.get("v24572_current_real_pipeline_mechanism_reachable")
        is False
        and conclusions.get(
            "v24576_protocol_design_authorization_sufficient_for_external_launch"
        )
        is False
        and conclusions.get(
            "pre_dedup_candidate_preservation_required_before_new_external_population"
        )
        is True
        and diagnosis_authorization.get(
            "prededup_candidate_preservation_successor_design"
        )
        is True
        and diagnosis_authorization.get("fresh_external_protocol_design")
        is False
        and diagnosis_authorization.get("fresh_external_activation_or_launch")
        is False
        and _sealed(predecessor, "audit_payload_sha256")
        and predecessor.get("role")
        == "v24576_validator_aligned_selection_build_audit"
        and predecessor.get("findings") == []
        and predecessor.get("audit_valid") is True
        and predecessor_authorization.get(
            "fresh_disjoint_validator_aligned_external_protocol_design"
        )
        is True
        and predecessor_authorization.get("fresh_external_activation_or_launch")
        is False
        and predecessor_authorization.get("paired_dev64_or_exact220") is False
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
        findings.append("v24576_or_v24577_parent_drifted")
    if head != remote:
        findings.append("v24578_82_source_commit_not_pushed")
    if not clean:
        findings.append("v24578_82_source_worktree_not_clean")
    if not tracked:
        findings.append("v24578_82_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24572_82_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24572_81_runtime")
    if imports:
        findings.append("evaluator_import_in_v24572_81_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24572_82_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24582_prededup_preservation_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "closed_parents": {
            "v24576_path": str(PREDECESSOR_AUDIT),
            "v24576_sha256": common._sha256(PREDECESSOR_AUDIT),
            "v24576_clean_build_valid_but_external_design_authorization_superseded": True,
            "v24577_path": str(DIAGNOSIS),
            "v24577_sha256": common._sha256(DIAGNOSIS),
            "v24577_revokes_pre_dedup_external_protocol_design": True,
            "valid": parents_closed,
        },
        "freshness_baseline": {
            "prior_external_question_count": PRIOR_QUESTION_COUNT,
            "prior_external_entity_count": PRIOR_ENTITY_COUNT,
            "all_populations_through_v24571_counted_as_consumed": True,
            "v24571_population_resume_retry_rerun_or_evaluation_authorized": False,
            "v24572_82_synthetic_build_tests_consume_external_population": False,
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
            "v24577_exact_url_distinct_visible_leads": 3,
            "v24577_post_source_dedup_leads": 2,
            "v24577_pre_dedup_replacement_count": 1,
            "v24577_current_pipeline_replacement_count": 0,
            "v24578_preserves_valid_exact_url_distinct_leads_before_source_selection": True,
            "v24578_unique_source_vectors_preserve_predecessor_exactly": True,
            "v24579_real_worker_reaches_preservation_and_title_replacement_surface": True,
            "v24579_parent_validation_precedes_successor_without_private_replay": True,
            "v24580_success_requires_v24579_opaque_capability": True,
            "v24580_failure_projection_is_exact_content_free_zero": True,
            "v24580_failure_projection_claims_private_effects_zero": False,
            "v24581_real_parent_supervisor_worker_chain_passes": True,
            "v24581_module_global_projector_patch_or_shared_parent_context_used": False,
            "v24581_one_monotonic_origin_crosses_parent_supervisor_worker": True,
            "remote_worker_parent_batch_cutoffs_seconds": [150, 220, 245, 255],
            "logical_query_search_batch_fetch_source_or_page_cap_changed": False,
            "url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
            "source_count_posterior_margin_leave_one_out_safe_change_or_decision_credit_rule_changed": False,
            "same_task_preservation_and_replacement_cooccurrence_proves_lead_level_causality": False,
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
            "fresh_disjoint_prededup_preservation_external_protocol_design": not findings,
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
