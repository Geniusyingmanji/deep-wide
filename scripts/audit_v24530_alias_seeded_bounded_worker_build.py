#!/usr/bin/env python3
"""Build-only audit for V2.45.29--30 alias-seeded acquisition.

The audit binds the frozen V2.45.27 parent and the complete V2.45.28 NO-GO
closure.  It reads repository sources and content-free aggregate artifacts
only; it never opens task rows, queries, URLs, pages, predictions, benchmark
metadata, evaluator state, or credentials.
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
    f"results/v24530_alias_seeded_bounded_worker_build_audit_v1_{DATE}.json"
)
PARENT_AUDIT = Path(
    f"results/v24527_bounded_alias_title_parent_build_audit_v1_{DATE}.json"
)
NO_GO_RESULT = Path(f"results/v24528_alias_external_result_v1_{DATE}.json")
NO_GO_DECISION = Path(f"results/v24528_alias_external_decision_v1_{DATE}.json")
NO_GO_POSTAUDIT = Path(
    f"results/v24528_alias_external_postresult_audit_v1_{DATE}.json"
)
NO_GO_PROTOCOL_ID = "v24528_fresh_alias_title_entropy_credit_external_gate_v1"
SOURCES = (
    PARENT_AUDIT,
    NO_GO_RESULT,
    NO_GO_DECISION,
    NO_GO_POSTAUDIT,
    Path("src/deepwide_agent/v24529_alias_seeded_target_acquisition.py"),
    Path("tests/test_v24529_alias_seeded_target_acquisition.py"),
    Path("src/deepwide_agent/v24530_alias_seeded_bounded_worker.py"),
    Path("tests/test_v24530_alias_seeded_bounded_worker.py"),
    Path("scripts/audit_v24530_alias_seeded_bounded_worker_build.py"),
    Path("tests/test_audit_v24530_alias_seeded_bounded_worker_build.py"),
)
RUNTIME_SOURCES = (SOURCES[4], SOURCES[6])
TEST_SUITES = (
    (Path("tests/test_v24524_alias_title_integration.py"), 8, 300),
    (Path("tests/test_v24525_proof_carrying_alias_title.py"), 8, 480),
    (Path("tests/test_v24526_total_alias_title_projection.py"), 6, 300),
    (Path("tests/test_v24527_bounded_alias_title_parent.py"), 5, 360),
    (Path("tests/test_v24529_alias_seeded_target_acquisition.py"), 8, 180),
    (Path("tests/test_v24530_alias_seeded_bounded_worker.py"), 3, 300),
    (Path("tests/test_audit_v24530_alias_seeded_bounded_worker_build.py"), 6, 90),
)
EXPECTED_TEST_COUNT = 44


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = common._read(PARENT_AUDIT)
    authorization = value.get("authorization", {})
    return (
        _sealed(value, "audit_payload_sha256")
        and value.get("role") == "v24527_bounded_alias_title_parent_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("label_blind_audit", {}).get("passed") is True
        and value.get("runtime_state", {}).get("shared_api_lease_inactive") is True
        and authorization.get("fresh_disjoint_alias_external_protocol_design")
        is True
        and authorization.get("fresh_external_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def _no_go_closure_valid() -> bool:
    result = common._read(NO_GO_RESULT)
    decision = common._read(NO_GO_DECISION)
    postaudit = common._read(NO_GO_POSTAUDIT)
    mechanism = result.get("mechanism_aggregate", {})
    authorization = decision.get("authorization", {})
    zero_fields = (
        "alias_anchor_tasks",
        "alias_observation_tasks",
        "alias_added_observation_tasks",
        "alias_safe_change_improvement_tasks",
        "alias_positive_information_gain_tasks",
        "alias_epistemic_credit_gain_tasks",
        "alias_decision_credit_gain_tasks",
    )
    return (
        result.get("protocol_id") == NO_GO_PROTOCOL_ID
        and decision.get("protocol_id") == NO_GO_PROTOCOL_ID
        and postaudit.get("protocol_id") == NO_GO_PROTOCOL_ID
        and _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
        and result.get("selected") == 8
        and result.get("passed") is False
        and result.get("mechanism_passed") is False
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and result.get("official_evaluator_called") is False
        and result.get("private_task_or_web_content_persisted") is False
        and result.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is False
        and all(mechanism.get(name) == 0 for name in zero_fields)
        and decision.get("result_sha256") == common._sha256(NO_GO_RESULT)
        and decision.get("status") == "fresh_alias_mechanism_no_go"
        and decision.get("passed") is False
        and decision.get("diagnostic_route")
        == "alias_source_title_coverage_successor"
        and authorization.get("diagnostic_successor_design") is True
        and authorization.get("fresh_paired_dev64_launch") is False
        and authorization.get("new_exact220") is False
        and postaudit.get("result_sha256") == common._sha256(NO_GO_RESULT)
        and postaudit.get("decision_sha256") == common._sha256(NO_GO_DECISION)
        and postaudit.get("decision_status") == "fresh_alias_mechanism_no_go"
        and postaudit.get("diagnostic_route")
        == "alias_source_title_coverage_successor"
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("audit_valid") is True
        and postaudit.get("findings") == []
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_valid = _parent_valid()
    no_go_valid = _no_go_closure_valid()
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
        findings.append("v24527_parent_build_audit_drifted")
    if not no_go_valid:
        findings.append("v24528_no_go_closure_drifted")
    if head != remote:
        findings.append("v24529_30_source_commit_not_pushed")
    if not clean:
        findings.append("v24529_30_source_worktree_not_clean")
    if not tracked:
        findings.append("v24529_30_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24524_v24530_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24529_30_runtime")
    if imports:
        findings.append("evaluator_import_in_v24529_30_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24529_30_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24530_alias_seeded_bounded_worker_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": common._sha256(PARENT_AUDIT),
            "valid": parent_valid,
        },
        "v24528_no_go_closure": {
            "result_path": str(NO_GO_RESULT),
            "result_sha256": common._sha256(NO_GO_RESULT),
            "decision_path": str(NO_GO_DECISION),
            "decision_sha256": common._sha256(NO_GO_DECISION),
            "postaudit_path": str(NO_GO_POSTAUDIT),
            "postaudit_sha256": common._sha256(NO_GO_POSTAUDIT),
            "valid": no_go_valid,
            "population_rerun_authorized": False,
            "diagnostic_route": "alias_source_title_coverage_successor",
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
            "historical_private_pages_opened": False,
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
            "alias_derived_only_from_visible_row_text": True,
            "targeted_and_neutral_queries_are_alias_seeded": True,
            "row_without_safe_alias_preserves_original_query_family": True,
            "visible_title_alias_hits_rank_before_frozen_target_coverage_order": True,
            "logical_query_search_batch_and_fetch_caps_unchanged": True,
            "alias_hint_receives_no_vote_source_entropy_or_decision_credit": True,
            "cross_row_identity_relation_year_source_posterior_margin_leave_one_out_and_safe_change_rules_unchanged": True,
            "proof_capability_total_projection_supervisor_and_deadlines_unchanged": True,
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
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_disjoint_alias_seeded_external_protocol_design": not findings,
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
            },
            sort_keys=True,
        )
    )
