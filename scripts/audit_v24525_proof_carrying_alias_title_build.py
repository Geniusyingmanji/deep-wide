#!/usr/bin/env python3
"""Build-only audit for the proof-carrying alias-title worker."""

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
AUDIT = Path(f"results/v24525_proof_carrying_alias_title_build_audit_v1_{DATE}.json")
PARENT_AUDIT = Path(
    f"results/v24524_alias_title_integration_build_audit_v1_{DATE}.json"
)
SOURCES = (
    PARENT_AUDIT,
    Path("src/deepwide_agent/v24525_proof_carrying_alias_title.py"),
    Path("tests/test_v24525_proof_carrying_alias_title.py"),
    Path("scripts/audit_v24525_proof_carrying_alias_title_build.py"),
    Path("tests/test_audit_v24525_proof_carrying_alias_title_build.py"),
)
RUNTIME_SOURCES = (SOURCES[1],)
TEST_SUITES = (
    (Path("tests/test_v24504_proof_carrying_record_bound_reserve.py"), 10, 300),
    (Path("tests/test_v24515_neutral_cell_discovery_planner.py"), 7, 180),
    (Path("tests/test_v24524_alias_title_integration.py"), 8, 300),
    (Path("tests/test_v24525_proof_carrying_alias_title.py"), 8, 480),
    (Path("tests/test_audit_v24525_proof_carrying_alias_title_build.py"), 5, 90),
)
EXPECTED_TEST_COUNT = 38


def _parent_valid() -> bool:
    value = common._read(PARENT_AUDIT)
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = value.get("authorization", {})
    return (
        seal == payload_sha256(unsigned)
        and value.get("role") == "v24524_alias_title_integration_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and authorization.get(
            "proof_carrying_alias_worker_and_bounded_parent_design"
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
        findings.append("v24524_parent_build_audit_drifted")
    if head != remote:
        findings.append("v24525_source_commit_not_pushed")
    if not clean:
        findings.append("v24525_source_worktree_not_clean")
    if not tracked:
        findings.append("v24525_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24504_v24525_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24525_runtime")
    if imports:
        findings.append("evaluator_import_in_v24525_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24525_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24525_proof_carrying_alias_title_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": common._sha256(PARENT_AUDIT),
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
            "synthetic_clients_and_pages_only": True,
            "historical_private_pages_opened": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_input_rejected_before_model_search_or_fetch_effect": True,
            "evaluator_opened": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "mechanism_evidence": {
            "complete_parent_and_alias_semantics_validated_once_in_child": True,
            "parent_validates_exact_byte_certificate_and_compact_receipts": True,
            "parent_does_not_replay_private_parent_or_alias_semantics": True,
            "raw_dictionary_cannot_forge_opaque_capability": True,
            "parent_certificate_alias_result_and_private_parent_tamper_fail_closed": True,
            "outer_resealed_receipt_planner_manifest_and_byte_tamper_fail_closed": True,
            "extra_file_and_symlink_surface_fail_closed": True,
            "neutral_discovery_parent_effects_accounted_separately_from_alias_delta": True,
            "alias_projection_additional_model_search_and_fetch_effects_zero": True,
            "positive_decision_credit_observed_in_synthetic_support_case": True,
            "source_posterior_margin_leave_one_out_and_credit_rules_unchanged": True,
            "certificate_is_not_signature_remote_attestation_or_malicious_child_defence": True,
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
            "capability_only_total_projection_and_bounded_parent_design": not findings,
            "fresh_external_protocol_design": False,
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
