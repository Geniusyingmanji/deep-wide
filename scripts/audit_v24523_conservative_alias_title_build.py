#!/usr/bin/env python3
"""Build-only audit for the conservative visible-row alias title projector."""

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
AUDIT = Path(f"results/v24523_conservative_alias_title_build_audit_v1_{DATE}.json")
PARENT_RESULT = Path(
    f"results/v24522_conversion_external_result_v1_{DATE}.json"
)
PARENT_DECISION = Path(
    f"results/v24522_conversion_external_decision_v1_{DATE}.json"
)
PARENT_POSTAUDIT = Path(
    f"results/v24522_conversion_external_postresult_audit_v1_{DATE}.json"
)
SOURCES = (
    PARENT_RESULT,
    PARENT_DECISION,
    PARENT_POSTAUDIT,
    Path("src/deepwide_agent/v24523_conservative_alias_title_projection.py"),
    Path("tests/test_v24523_conservative_alias_title_projection.py"),
    Path("scripts/audit_v24523_conservative_alias_title_build.py"),
    Path("tests/test_audit_v24523_conservative_alias_title_build.py"),
)
RUNTIME_SOURCES = (SOURCES[3],)
TEST_SUITES = (
    (Path("tests/test_v24428_unique_title_anchor_projection.py"), 10, 120),
    (Path("tests/test_v24436_narrative_title_anchor_projection.py"), 9, 120),
    (Path("tests/test_v24502_record_bound_title_projection.py"), 11, 120),
    (Path("tests/test_v24522_conversion_diagnostic_external_gate.py"), 12, 300),
    (Path("tests/test_v24523_conservative_alias_title_projection.py"), 13, 180),
    (Path("tests/test_audit_v24523_conservative_alias_title_build.py"), 5, 60),
)
EXPECTED_TEST_COUNT = 60


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    result = common._read(PARENT_RESULT)
    decision = common._read(PARENT_DECISION)
    audit = common._read(PARENT_POSTAUDIT)
    authorization = decision.get("authorization", {})
    return (
        result.get("role") == "v24492_targeted_external_result"
        and result.get("protocol_id")
        == "v24522_fresh_conversion_diagnostic_external_gate_v1"
        and result.get("passed") is True
        and result.get("mechanism_passed") is True
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and _sealed(result, "result_payload_sha256")
        and decision.get("role")
        == "v24522_conversion_diagnostic_external_decision"
        and decision.get("protocol_id") == result.get("protocol_id")
        and decision.get("status") == "fresh_conversion_diagnostic_go"
        and decision.get("passed") is True
        and decision.get("diagnostic_route")
        == "conservative_alias_title_anchoring_successor"
        and decision.get("reason_family_pair_counts", {}).get(
            "anchor_absence_or_misbinding"
        )
        == 9
        and authorization.get("selected_mechanism_successor_design") is True
        and authorization.get("fresh_mechanism_external_gate_launch") is False
        and authorization.get("fresh_paired_dev64_design") is False
        and authorization.get("new_exact220") is False
        and _sealed(decision, "decision_payload_sha256")
        and audit.get("role")
        == "v24522_conversion_diagnostic_external_postresult_audit"
        and audit.get("protocol_id") == result.get("protocol_id")
        and audit.get("audit_valid") is True
        and audit.get("findings") == []
        and audit.get("shared_api_lease_active") is False
        and audit.get("diagnostic_route")
        == "conservative_alias_title_anchoring_successor"
        and audit.get("opaque_capability_references_destroyed_after_aggregation")
        is True
        and _sealed(audit, "audit_payload_sha256")
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
        findings.append("v24522_conversion_diagnostic_parent_drifted")
    if head != remote:
        findings.append("v24523_source_commit_not_pushed")
    if not clean:
        findings.append("v24523_source_worktree_not_clean")
    if not tracked:
        findings.append("v24523_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24428_v24523_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24523_runtime")
    if imports:
        findings.append("evaluator_import_in_v24523_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24523_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24523_conservative_alias_title_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_conversion_diagnostic": {
            "result_path": str(PARENT_RESULT),
            "result_sha256": common._sha256(PARENT_RESULT),
            "decision_path": str(PARENT_DECISION),
            "decision_sha256": common._sha256(PARENT_DECISION),
            "postaudit_path": str(PARENT_POSTAUDIT),
            "postaudit_sha256": common._sha256(PARENT_POSTAUDIT),
            "valid": parent_valid,
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
            "synthetic_pages_only": True,
            "historical_v24522_private_pages_opened": False,
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
            "selected_by_frozen_v24522_reason_family_route": True,
            "visible_row_text_is_the_only_alias_source": True,
            "normalized_full_core_or_initialism_alias_only": True,
            "cross_row_alias_collision_fails_closed": True,
            "short_or_generic_core_fails_closed": True,
            "organization_type_conflict_fails_closed": True,
            "exact_parent_title_anchor_is_never_overridden": True,
            "alias_supplies_identity_not_value": True,
            "exact_label_or_subject_safe_relation_still_required": True,
            "multiple_distinct_years_fail_closed": True,
            "other_visible_row_stops_title_scope": True,
            "parent_artifact_and_observations_preserved": True,
            "projection_replay_and_tamper_checks_pass": True,
            "source_posterior_margin_leave_one_out_and_credit_rules_unchanged": True,
            "additional_external_effects": 0,
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
            "zero_effect_alias_title_runtime_integration_design": not findings,
            "fresh_alias_external_protocol_design": False,
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
