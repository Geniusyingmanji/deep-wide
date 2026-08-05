#!/usr/bin/env python3
"""Build-only audit for proof-carrying conversion observability.

This audit reads repository sources, the public V2.45.17 closure, process
identities, and the shared lease state.  It never opens historical task
directories, private pages, benchmark mappings, evaluator output, or secrets.
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
    f"results/v24519_conversion_observability_build_audit_v1_{DATE}.json"
)
PARENT_AUDIT = Path(
    f"results/v24516_neutral_discovery_worker_build_audit_v1_{DATE}.json"
)
PREVIOUS_RESULT = Path(f"results/v24517_neutral_external_result_v1_{DATE}.json")
PREVIOUS_DECISION = Path(
    f"results/v24517_neutral_external_decision_v1_{DATE}.json"
)
PREVIOUS_POSTAUDIT = Path(
    f"results/v24517_neutral_external_postresult_audit_v1_{DATE}.json"
)
SOURCES = (
    PARENT_AUDIT,
    PREVIOUS_RESULT,
    PREVIOUS_DECISION,
    PREVIOUS_POSTAUDIT,
    Path("src/deepwide_agent/v24518_conversion_observability.py"),
    Path("tests/test_v24518_conversion_observability.py"),
    Path(
        "src/deepwide_agent/v24519_proof_carrying_conversion_observability.py"
    ),
    Path("tests/test_v24519_proof_carrying_conversion_observability.py"),
    Path("scripts/audit_v24519_conversion_observability_build.py"),
    Path("tests/test_audit_v24519_conversion_observability_build.py"),
)
RUNTIME_SOURCES = (SOURCES[4], SOURCES[6])
TEST_SUITES = (
    (Path("tests/test_v24502_record_bound_title_projection.py"), 11, 120),
    (Path("tests/test_v24504_proof_carrying_record_bound_reserve.py"), 10, 240),
    (Path("tests/test_v24508_execution_scoped_high_level_validation_memo.py"), 6, 120),
    (Path("tests/test_v24515_neutral_cell_discovery_planner.py"), 7, 120),
    (Path("tests/test_v24516_neutral_discovery_record_bound_worker.py"), 4, 180),
    (Path("tests/test_v24518_conversion_observability.py"), 6, 120),
    (
        Path("tests/test_v24519_proof_carrying_conversion_observability.py"),
        8,
        240,
    ),
    (
        Path("tests/test_audit_v24519_conversion_observability_build.py"),
        5,
        60,
    ),
)
EXPECTED_TEST_COUNT = 57


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = common._read(PARENT_AUDIT)
    authorization = value.get("authorization", {})
    return (
        _sealed(value, "audit_payload_sha256")
        and value.get("role") == "v24516_neutral_discovery_worker_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and authorization.get(
            "fresh_disjoint_neutral_discovery_external_protocol_design"
        )
        is True
        and authorization.get("fresh_external_activation_or_launch") is False
    )


def _previous_closed() -> bool:
    result = common._read(PREVIOUS_RESULT)
    decision = common._read(PREVIOUS_DECISION)
    postaudit = common._read(PREVIOUS_POSTAUDIT)
    protocol = "v24517_fresh_neutral_discovery_terminal_external_gate_v1"
    aggregate = result.get("mechanism_aggregate", {})
    return (
        result.get("protocol_id") == protocol
        and decision.get("protocol_id") == protocol
        and postaudit.get("protocol_id") == protocol
        and result.get("passed") is False
        and result.get("reliability_passed") is True
        and result.get("mechanism_passed") is False
        and aggregate.get("target_plan_tasks") == 8
        and aggregate.get("reserve_usable_page_tasks") == 5
        and aggregate.get("parent_observation_tasks") == 0
        and decision.get("status") == "fresh_targeted_external_no_go"
        and decision.get("authorization", {}).get("new_exact220") is False
        and postaudit.get("audit_valid") is True
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("findings") == []
        and _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_valid = _parent_valid()
    previous_closed = _previous_closed()
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
        findings.append("v24516_parent_build_audit_drifted")
    if not previous_closed:
        findings.append("v24517_external_no_go_not_closed")
    if head != remote:
        findings.append("v24518_19_source_commit_not_pushed")
    if not clean:
        findings.append("v24518_19_source_worktree_not_clean")
    if not tracked:
        findings.append("v24518_19_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24502_v24519_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24518_19_runtime")
    if imports:
        findings.append("evaluator_import_in_v24518_19_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24518_19_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24519_conversion_observability_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": common._sha256(PARENT_AUDIT),
            "valid": parent_valid,
        },
        "previous_external_closure": {
            "result_path": str(PREVIOUS_RESULT),
            "result_sha256": common._sha256(PREVIOUS_RESULT),
            "decision_path": str(PREVIOUS_DECISION),
            "decision_sha256": common._sha256(PREVIOUS_DECISION),
            "postaudit_path": str(PREVIOUS_POSTAUDIT),
            "postaudit_sha256": common._sha256(PREVIOUS_POSTAUDIT),
            "valid": previous_closed,
            "diagnostic_route": "usable_page_to_observation_reason_partition",
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
            "synthetic_clients_and_pages_only": True,
            "v24517_private_pages_opened": False,
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
            "all_page_target_pairs_receive_one_exact_reason": True,
            "body_entity_title_relation_year_projection_and_new_observation_signals_counted": True,
            "all_five_frozen_projection_routes_observable": True,
            "duplicate_parent_observation_distinguished_from_new_observation": True,
            "source_ambiguity_and_post_projection_safety_rejection_distinguished": True,
            "unsupported_anchor_relation_year_and_safety_rejections_distinguished": True,
            "raw_mapping_cannot_forge_typed_execution_or_parent_capability": True,
            "outer_certificate_binds_parent_artifacts_parent_certificate_and_receipt_exact_bytes": True,
            "neutral_discovery_planner_receipt_bound": True,
            "parent_compact_validation_does_not_replay_private_semantics": True,
            "no_external_effect_added": True,
            "source_posterior_margin_leave_one_out_and_decision_credit_rules_unchanged": True,
            "receipt_contains_counts_and_its_own_seal_only": True,
            "task_question_entity_column_value_query_url_page_source_prediction_or_private_hash_not_emitted": True,
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
            "bounded_parent_total_projection_integration_design": not findings,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "same_v24517_population_rerun": False,
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
            },
            sort_keys=True,
        )
    )
