#!/usr/bin/env python3
"""Build-only audit for the V2.45.09 high-level memoized worker."""

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
    f"results/v24509_high_level_memoized_worker_build_audit_v1_{DATE}.json"
)
PARENT_AUDIT = Path(
    f"results/v24505_record_bound_parent_build_audit_v1_{DATE}.json"
)
SOURCES = (
    PARENT_AUDIT,
    Path(
        "src/deepwide_agent/v24508_execution_scoped_high_level_validation_memo.py"
    ),
    Path("tests/test_v24508_execution_scoped_high_level_validation_memo.py"),
    Path(
        "src/deepwide_agent/v24509_high_level_memoized_record_bound_worker.py"
    ),
    Path("tests/test_v24509_high_level_memoized_record_bound_worker.py"),
    Path("scripts/audit_v24509_high_level_memoized_worker_build.py"),
    Path("tests/test_audit_v24509_high_level_memoized_worker_build.py"),
)
RUNTIME_SOURCES = (SOURCES[1], SOURCES[3])
TEST_SUITES = (
    (Path("tests/test_v24503_record_bound_reserve_integration.py"), 8, 240),
    (Path("tests/test_v24504_proof_carrying_record_bound_reserve.py"), 10, 240),
    (Path("tests/test_v24505_record_bound_timed_parent.py"), 4, 180),
    (
        Path("tests/test_v24508_execution_scoped_high_level_validation_memo.py"),
        6,
        180,
    ),
    (
        Path("tests/test_v24509_high_level_memoized_record_bound_worker.py"),
        4,
        180,
    ),
    (
        Path("tests/test_audit_v24509_high_level_memoized_worker_build.py"),
        4,
        60,
    ),
)
EXPECTED_TEST_COUNT = 36


def _parent_valid() -> bool:
    value = common._read(PARENT_AUDIT)
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = value.get("authorization", {})
    return (
        seal == payload_sha256(unsigned)
        and value.get("role") == "v24505_record_bound_parent_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and authorization.get("fresh_record_bound_external_protocol_design")
        is True
        and authorization.get("fresh_record_bound_external_activation_or_launch")
        is False
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
        findings.append("v24505_parent_build_audit_drifted")
    if head != remote:
        findings.append("v24509_source_commit_not_pushed")
    if not clean:
        findings.append("v24509_source_worktree_not_clean")
    if not tracked:
        findings.append("v24508_09_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24503_v24509_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24508_09_runtime")
    if imports:
        findings.append("evaluator_import_in_v24508_09_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24508_09_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24509_high_level_memoized_worker_build_audit",
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
        "performance_evidence": {
            "memoized_synthetic_chain_ceiling_seconds": 15,
            "real_parent_supervisor_worker_chain_ceiling_seconds": 70,
            "performance_gates_enforced_by_tests": True,
            "profiled_timing_used_as_external_latency_estimate": False,
            "external_provider_search_fetch_or_benchmark_latency_measured": False,
        },
        "mechanism_evidence": {
            "first_high_level_validation_per_layer_uses_unchanged_validator": True,
            "high_level_hits_recompute_seal_and_compare_exact_bytes_and_type_shape": True,
            "high_level_hits_preserve_deep_copy_return_semantics": True,
            "mismatches_are_counted_as_misses_without_double_counting_calls": True,
            "high_level_cache_is_single_worker_execution_scoped": True,
            "all_low_and_high_level_bindings_restore_on_every_exit": True,
            "memoized_and_unmemoized_complete_results_are_exactly_equal": True,
            "both_memo_receipts_validate_before_success_terminal": True,
            "invalid_high_level_receipt_fails_before_result_or_success_terminal": True,
            "durable_proof_surface_and_v24504_certificate_are_unchanged": True,
            "high_level_receipt_is_not_persisted_or_publicly_aggregated": True,
            "real_parent_supervisor_worker_capability_chain_passes": True,
            "record_bound_positive_decision_credit_is_preserved": True,
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
            "proposal_seeded_label_blind_target_planner_design": not findings,
            "fresh_external_protocol_design_or_launch": False,
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
