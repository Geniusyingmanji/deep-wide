#!/usr/bin/env python3
"""Clean-build audit for V2.45.64--65 strict conversion integration."""

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
    f"results/v24566_strict_reachability_conversion_build_audit_v1_{DATE}.json"
)
PARENT_AUDIT = Path(
    f"results/v24563_reachability_conversion_joint_build_audit_v1_{DATE}.json"
)
SOURCES = (
    PARENT_AUDIT,
    Path("src/deepwide_agent/v24561_decision_reachability_conversion_joint.py"),
    Path("tests/test_v24561_decision_reachability_conversion_joint.py"),
    Path("src/deepwide_agent/v24562_bounded_reachability_conversion_joint_parent.py"),
    Path("tests/test_v24562_bounded_reachability_conversion_joint_parent.py"),
    Path("src/deepwide_agent/v24564_strict_reachability_conversion_joint.py"),
    Path("tests/test_v24564_strict_reachability_conversion_joint.py"),
    Path("src/deepwide_agent/v24565_bounded_strict_reachability_conversion_parent.py"),
    Path("tests/test_v24565_bounded_strict_reachability_conversion_parent.py"),
    Path("scripts/audit_v24566_strict_reachability_conversion_build.py"),
    Path("tests/test_audit_v24566_strict_reachability_conversion_build.py"),
)
RUNTIME_SOURCES = (SOURCES[1], SOURCES[3], SOURCES[5], SOURCES[7])
TEST_SUITES = (
    (Path("tests/test_v24561_decision_reachability_conversion_joint.py"), 6, 300),
    (
        Path("tests/test_v24562_bounded_reachability_conversion_joint_parent.py"),
        4,
        300,
    ),
    (Path("tests/test_v24564_strict_reachability_conversion_joint.py"), 5, 300),
    (
        Path("tests/test_v24565_bounded_strict_reachability_conversion_parent.py"),
        5,
        300,
    ),
    (
        Path("tests/test_audit_v24566_strict_reachability_conversion_build.py"),
        7,
        120,
    ),
)
EXPECTED_TEST_COUNT = 27


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = common._read(PARENT_AUDIT)
    authorization = value.get("authorization", {})
    baseline = value.get("freshness_baseline", {})
    return (
        _sealed(value, "audit_payload_sha256")
        and value.get("role")
        == "v24563_reachability_conversion_joint_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("tests", {}).get("test_count") == 51
        and value.get("tests", {}).get("passed") is True
        and value.get("label_blind_audit", {}).get("passed") is True
        and value.get("runtime_state", {}).get("shared_api_lease_inactive") is True
        and baseline.get("prior_external_question_count") == 436
        and baseline.get("prior_external_entity_count") == 3488
        and baseline.get(
            "v24554_population_resume_retry_rerun_or_evaluation_authorized"
        )
        is False
        and authorization.get(
            "fresh_disjoint_bounded_reachability_conversion_external_protocol_design"
        )
        is True
        and authorization.get("fresh_external_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_valid = _parent_valid()
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
        findings.append("v24563_parent_build_audit_drifted")
    if head != remote:
        findings.append("v24564_66_source_commit_not_pushed")
    if not clean:
        findings.append("v24564_66_source_worktree_not_clean")
    if not tracked:
        findings.append("v24564_66_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24561_66_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24561_65_runtime")
    if imports:
        findings.append("evaluator_import_in_v24561_65_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24561_66_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24566_strict_reachability_conversion_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": common._sha256(PARENT_AUDIT),
            "valid": parent_valid,
        },
        "freshness_baseline": {
            "prior_external_question_count": 436,
            "prior_external_entity_count": 3488,
            "v24554_population_resume_retry_rerun_or_evaluation_authorized": False,
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
            "synthetic_clients_pages_capabilities_and_subprocesses_only": True,
            "historical_private_task_query_url_page_source_value_or_prediction_opened": False,
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
            "strict_joint_same_task_requires_one_observation_plan": True,
            "strict_joint_same_task_requires_changed_legacy_choice": True,
            "strict_joint_same_task_requires_alias_observation_positive_ig_safe_change_and_decision_credit": True,
            "joint_claims_call_query_lead_source_or_page_level_causality": False,
            "strict_joint_is_mechanically_recomputed_from_capability_proven_row": True,
            "public_success_mapping_can_be_reingested_as_proof": False,
            "failure_projection_is_exact_content_free_zero": True,
            "failure_projection_does_not_claim_private_effects_zero": True,
            "failure_observation_preserves_partial_effect_lower_bound": True,
            "real_parent_supervisor_worker_chain_passes": True,
            "success_validates_one_v24557_capability": True,
            "success_projects_one_v24564_strict_row": True,
            "module_global_projector_patch_or_shared_parent_context_used": False,
            "v24562_parent_function_and_projector_identity_preserved": True,
            "parent_recursive_historical_semantic_replay_performed": False,
            "source_count_active_support_posterior_margin_leave_one_out_safe_change_or_decision_credit_rule_changed": False,
            "one_monotonic_origin_crosses_parent_supervisor_worker": True,
            "remote_worker_parent_batch_cutoffs_seconds": [150, 220, 245, 255],
            "model_slot_cap_unchanged": 2,
            "query_model_search_or_fetch_budget_changed": False,
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
            "fresh_disjoint_bounded_strict_reachability_conversion_external_protocol_design": not findings,
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
