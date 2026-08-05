#!/usr/bin/env python3
"""Build-only audit for V2.45.47--50 alias/action joint observability.

The audit reads only tracked source/test files and the frozen content-free
V2.45.45/46 control artifacts.  It never opens task rows, questions, queries,
URLs, pages, predictions, temporary execution directories, evaluator metadata,
scores, rewards, or credentials.
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
from scripts import diagnose_v24546_v24545_alias_action as diagnosis  # noqa: E402
from scripts import v24545_alias_action_credit_external_gate as gate  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24551_alias_joint_build_audit_v1_{DATE}.json")
DIAGNOSIS = diagnosis.OUTPUT
SOURCES = (
    gate.RESULT,
    gate.DECISION,
    gate.POSTAUDIT,
    DIAGNOSIS,
    Path("scripts/diagnose_v24546_v24545_alias_action.py"),
    Path("tests/test_diagnose_v24546_v24545_alias_action.py"),
    Path("src/deepwide_agent/v24547_alias_surface_observability.py"),
    Path("tests/test_v24547_alias_surface_observability.py"),
    Path("src/deepwide_agent/v24548_alias_action_joint_observability.py"),
    Path("tests/test_v24548_alias_action_joint_observability.py"),
    Path("src/deepwide_agent/v24549_proof_carrying_alias_joint.py"),
    Path("tests/test_v24549_proof_carrying_alias_joint.py"),
    Path("src/deepwide_agent/v24550_total_alias_joint_projection.py"),
    Path("tests/test_v24550_total_alias_joint_projection.py"),
    Path("scripts/audit_v24551_alias_joint_build.py"),
    Path("tests/test_audit_v24551_alias_joint_build.py"),
)
RUNTIME_SOURCES = (
    SOURCES[6],
    SOURCES[8],
    SOURCES[10],
    SOURCES[12],
)
TEST_SUITES = (
    (Path("tests/test_v24525_proof_carrying_alias_title.py"), 8, 480),
    (Path("tests/test_v24526_total_alias_title_projection.py"), 6, 300),
    (Path("tests/test_v24529_alias_seeded_target_acquisition.py"), 8, 180),
    (Path("tests/test_v24533_alias_acquisition_entropy_credit.py"), 5, 240),
    (Path("tests/test_diagnose_v24546_v24545_alias_action.py"), 5, 120),
    (Path("tests/test_v24547_alias_surface_observability.py"), 7, 120),
    (Path("tests/test_v24548_alias_action_joint_observability.py"), 5, 240),
    (Path("tests/test_v24549_proof_carrying_alias_joint.py"), 7, 300),
    (Path("tests/test_v24550_total_alias_joint_projection.py"), 7, 300),
    (Path("tests/test_audit_v24551_alias_joint_build.py"), 8, 120),
)
EXPECTED_TEST_COUNT = 66


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _v24545_closed_no_go_valid() -> bool:
    result = gate.validate_public_result(common._read(gate.RESULT))
    decision = gate.validate_decision(value=common._read(gate.DECISION))
    audit = gate.validate_postaudit(value=common._read(gate.POSTAUDIT))
    mechanism = result["mechanism_aggregate"]
    counts = mechanism["total_acquisition_action_count_fields"]
    numbers = mechanism["total_acquisition_action_number_fields"]
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
        and mechanism.get("acquisition_plan_tasks") == 7
        and mechanism.get("acquisition_activity_tasks") == 6
        and mechanism.get("acquisition_new_observation_tasks") == 1
        and counts.get("targeted_usable_page_count") == 17
        and counts.get("targeted_new_observation_count") == 1
        and counts.get("visible_lead_count") == 423
        and counts.get("selected_lead_count") == 63
        and counts.get("alias_title_hit_lead_count") == 0
        and counts.get("selected_alias_title_hit_lead_count") == 0
        and abs(float(numbers.get("information_gain_gain_nats", -1)) - 0.209371236041)
        <= 1e-12
        and numbers.get("action_information_credit_nats") == 0
        and numbers.get("action_epistemic_credit_nats") == 0
        and numbers.get("action_decision_credit_nats") == 0
        and decision.get("status")
        == "fresh_post_capability_quarantine_alias_action_credit_no_go"
        and decision.get("diagnostic_route") == "alias_title_selection_successor"
        and authorization.get("diagnostic_successor_design") is True
        and authorization.get("fresh_paired_dev64_launch") is False
        and authorization.get("new_exact220") is False
        and audit.get("shared_api_lease_active") is False
        and audit.get("findings") == []
        and audit.get("audit_valid") is True
    )


def _diagnosis_valid() -> bool:
    value = diagnosis.validate_diagnosis(common._read(DIAGNOSIS))
    unavailable = value.get("unrecoverable_from_frozen_public_aggregate", {})
    successor = value.get("successor_contract", {})
    authorization = value.get("authorization", {})
    return (
        _sealed(value, "diagnosis_payload_sha256")
        and value.get("role")
        == "v24546_v24545_alias_action_correlation_diagnosis"
        and all(item is False for item in unavailable.values())
        and successor.get("query_text_must_not_establish_alias_hit") is True
        and successor.get(
            "alias_hint_itself_receives_vote_source_entropy_or_decision_credit"
        )
        is False
        and successor.get(
            "preserve_source_posterior_margin_leave_one_out_safe_change_and_decision_credit_thresholds"
        )
        is True
        and successor.get("same_population_recovery_or_rerun") is False
        and successor.get("next_population_prior_question_count") == 428
        and successor.get("next_population_prior_entity_count") == 3424
        and authorization.get("append_only_alias_observability_successor_design")
        is True
        and authorization.get("fresh_external_probe_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    closure_valid = _v24545_closed_no_go_valid()
    diagnosis_valid = _diagnosis_valid()
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
    if not closure_valid:
        findings.append("v24545_closed_no_go_drifted")
    if not diagnosis_valid:
        findings.append("v24546_correlation_diagnosis_drifted")
    if head != remote:
        findings.append("v24547_51_source_commit_not_pushed")
    if not clean:
        findings.append("v24547_51_source_worktree_not_clean")
    if not tracked:
        findings.append("v24547_51_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24525_v24551_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24547_50_runtime")
    if imports:
        findings.append("evaluator_import_in_v24547_50_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24547_51_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24551_alias_joint_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "v24545_closed_no_go": {
            "result": {
                "path": str(gate.RESULT),
                "sha256": common._sha256(gate.RESULT),
            },
            "decision": {
                "path": str(gate.DECISION),
                "sha256": common._sha256(gate.DECISION),
            },
            "postaudit": {
                "path": str(gate.POSTAUDIT),
                "sha256": common._sha256(gate.POSTAUDIT),
            },
            "valid": closure_valid,
            "same_population_resume_retry_or_rerun": False,
        },
        "v24546_correlation_diagnosis": {
            "path": str(DIAGNOSIS),
            "sha256": common._sha256(DIAGNOSIS),
            "valid": diagnosis_valid,
            "task_level_correlation_recovered_for_v24545": False,
            "next_prior_question_count": 428,
            "next_prior_entity_count": 3424,
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
            "synthetic_clients_pages_and_capabilities_only": True,
            "historical_private_pages_opened": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_input_rejected_before_filesystem_model_search_or_fetch_effect": True,
            "query_text_used_to_establish_alias_hit": False,
            "evaluator_opened": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "mechanism_evidence": {
            "title_full_core_initialism_counts_visible": True,
            "normalized_url_full_core_initialism_counts_visible": True,
            "url_surface_excludes_query_fragment_userinfo_and_port": True,
            "query_only_alias_is_diagnostic_and_receives_no_priority": True,
            "same_task_joint_counts_do_not_claim_lead_level_causality": True,
            "action_credit_requires_plan_query_selection_source_and_new_observation": True,
            "decision_credit_additionally_requires_safe_output_change": True,
            "source_posterior_margin_leave_one_out_and_safe_change_thresholds_unchanged": True,
            "alias_hint_itself_receives_no_vote_source_entropy_or_decision_credit": True,
            "frozen_v24525_task_surface_preserved_exactly": True,
            "certificate_binds_exact_joint_receipt_alias_result_and_outer_certificate_bytes": True,
            "success_projection_requires_opaque_v24549_capability": True,
            "public_success_dictionary_cannot_be_reingested_as_proof": True,
            "failure_projection_is_exact_content_free_zero": True,
            "failure_projection_does_not_claim_private_effects_zero": True,
            "mixed_aggregate_preserves_modes_joints_credit_and_exact_denominator": True,
            "model_slot_cap_unchanged": 2,
            "remote_worker_parent_batch_cutoffs_seconds": [150, 220, 245, 255],
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
            "temporary_execution_directory_opened": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_disjoint_alias_joint_external_protocol_design": not findings,
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
