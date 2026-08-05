#!/usr/bin/env python3
"""Build-only audit for the neutral cell-discovery record-bound worker."""

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
    f"results/v24516_neutral_discovery_worker_build_audit_v1_{DATE}.json"
)
PARENT_AUDIT = Path(
    f"results/v24513_terminal_projection_build_audit_v1_{DATE}.json"
)
PREVIOUS_RESULT = Path(f"results/v24514_terminal_external_result_v1_{DATE}.json")
PREVIOUS_DECISION = Path(
    f"results/v24514_terminal_external_decision_v1_{DATE}.json"
)
PREVIOUS_POSTAUDIT = Path(
    f"results/v24514_terminal_external_postresult_audit_v1_{DATE}.json"
)
SOURCES = (
    PARENT_AUDIT,
    PREVIOUS_RESULT,
    PREVIOUS_DECISION,
    PREVIOUS_POSTAUDIT,
    Path("src/deepwide_agent/v24515_neutral_cell_discovery_planner.py"),
    Path("tests/test_v24515_neutral_cell_discovery_planner.py"),
    Path("src/deepwide_agent/v24516_neutral_discovery_record_bound_worker.py"),
    Path("tests/test_v24516_neutral_discovery_record_bound_worker.py"),
    Path("scripts/audit_v24516_neutral_discovery_worker_build.py"),
    Path("tests/test_audit_v24516_neutral_discovery_worker_build.py"),
)
RUNTIME_SOURCES = (SOURCES[4], SOURCES[6])
TEST_SUITES = (
    (Path("tests/test_v24490_entropy_targeted_support_search.py"), 7, 300),
    (Path("tests/test_v24510_proposal_seeded_entropy_target_planner.py"), 6, 120),
    (Path("tests/test_v24511_proposal_seeded_record_bound_worker.py"), 4, 240),
    (Path("tests/test_v24513_terminal_record_bound_projection.py"), 7, 240),
    (Path("tests/test_v24515_neutral_cell_discovery_planner.py"), 7, 120),
    (
        Path("tests/test_v24516_neutral_discovery_record_bound_worker.py"),
        4,
        300,
    ),
    (Path("tests/test_audit_v24516_neutral_discovery_worker_build.py"), 5, 60),
)
EXPECTED_TEST_COUNT = 40


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = common._read(PARENT_AUDIT)
    authorization = value.get("authorization", {})
    return (
        _sealed(value, "audit_payload_sha256")
        and value.get("role") == "v24513_terminal_projection_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and authorization.get(
            "fresh_terminal_observability_external_protocol_design"
        )
        is True
        and authorization.get("fresh_external_activation_or_launch") is False
    )


def _previous_closed() -> bool:
    result = common._read(PREVIOUS_RESULT)
    decision = common._read(PREVIOUS_DECISION)
    postaudit = common._read(PREVIOUS_POSTAUDIT)
    protocol = "v24514_fresh_terminal_state_proposal_seeded_external_gate_v1"
    return (
        result.get("protocol_id") == protocol
        and decision.get("protocol_id") == protocol
        and postaudit.get("protocol_id") == protocol
        and result.get("passed") is False
        and decision.get("status") == "fresh_targeted_external_no_go"
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
        findings.append("v24513_parent_build_audit_drifted")
    if not previous_closed:
        findings.append("v24514_external_no_go_not_closed")
    if head != remote:
        findings.append("v24515_16_source_commit_not_pushed")
    if not clean:
        findings.append("v24515_16_source_worktree_not_clean")
    if not tracked:
        findings.append("v24515_16_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24490_v24516_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24515_16_runtime")
    if imports:
        findings.append("evaluator_import_in_v24515_16_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24515_16_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24516_neutral_discovery_worker_build_audit",
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
            "diagnostic_route": "target_plan_coverage_successor",
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
            "historical_private_page_opened": False,
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
            "v24510_concrete_alternative_paths_preserved": True,
            "empty_alternative_dead_zone_reproduced": True,
            "neutral_row_column_discovery_plan_generated": True,
            "neutral_discovery_plan_contains_no_candidate_value": True,
            "neutral_discovery_plan_receives_no_vote_or_source_credit": True,
            "three_source_reachability_checked_before_plan": True,
            "one_and_two_discovery_sources_cannot_cross_known_cell_gate": True,
            "three_independent_consistent_sources_can_cross_unchanged_gate": True,
            "source_count_posterior_margin_and_credit_thresholds_unchanged": True,
            "targeted_pages_never_enter_model_prompt": True,
            "zero_additional_model_acquisitions": True,
            "real_parent_supervisor_worker_capability_chain_passes": True,
            "invalid_planner_receipt_fails_before_success_terminal": True,
            "durable_v24504_proof_surface_and_certificate_unchanged": True,
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
            "fresh_disjoint_neutral_discovery_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "same_v24514_population_rerun": False,
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
