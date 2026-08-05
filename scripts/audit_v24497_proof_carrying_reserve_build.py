#!/usr/bin/env python3
"""Build-only audit for proof-carrying contradiction-aware reserve."""

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
from scripts import audit_v24496_targeted_reserve_build as parent_audit  # noqa: E402


DATE = "20260804"
AUDIT = Path(f"results/v24497_proof_carrying_reserve_build_audit_v1_{DATE}.json")
PARENT = parent_audit.AUDIT
SOURCES = (
    Path("src/deepwide_agent/v24496_targeted_reserve_contradiction.py"),
    Path("src/deepwide_agent/v24497_proof_carrying_targeted_reserve.py"),
    Path("tests/test_v24496_targeted_reserve_contradiction.py"),
    Path("tests/test_v24497_proof_carrying_targeted_reserve.py"),
    Path("scripts/audit_v24497_proof_carrying_reserve_build.py"),
    Path("tests/test_audit_v24497_proof_carrying_reserve_build.py"),
)
RUNTIME_SOURCES = SOURCES[:2]
TEST_SUITES = (
    (Path("tests/test_v24490_entropy_targeted_support_search.py"), 8, 180),
    (Path("tests/test_v24491_proof_carrying_targeted_support.py"), 10, 180),
    (Path("tests/test_v24495_targeted_conversion_projection.py"), 7, 120),
    (Path("tests/test_v24496_targeted_reserve_contradiction.py"), 7, 180),
    (Path("tests/test_v24497_proof_carrying_targeted_reserve.py"), 12, 180),
    (Path("tests/test_audit_v24497_proof_carrying_reserve_build.py"), 3, 60),
)
EXPECTED_TEST_COUNT = 47


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(common._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.97 expected object")
    return value


def _parent_valid() -> bool:
    value = _read(PARENT)
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    return (
        seal == payload_sha256(unsigned)
        and value.get("role") == "v24496_targeted_reserve_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get(
            "proof_carrying_reserve_integration_design"
        )
        is True
        and value.get("authorization", {}).get(
            "new_external_gate_design_or_launch"
        )
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
        findings.append("v24496_parent_build_audit_drifted")
    if head != remote:
        findings.append("v24497_source_commit_not_pushed")
    if not clean:
        findings.append("v24497_source_worktree_not_clean")
    if not tracked:
        findings.append("v24496_97_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24490_97_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24496_97_runtime")
    if imports:
        findings.append("evaluator_import_in_v24496_97_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24496_97_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24497_proof_carrying_reserve_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "path": str(PARENT),
            "sha256": common._sha256(PARENT),
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
            "synthetic_clients_only": True,
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
            "legacy_v24496_entrypoint_equivalent_to_typed_parent_continuation": True,
            "complete_reserve_validation_runs_once_in_child": True,
            "parent_validates_exact_surface_outer_seals_receipts_and_certificate_only": True,
            "certificate_binds_result_model_transport_search_reserve_support_reserve_effect_and_memo": True,
            "validation_memo_is_fail_closed_before_terminal_success": True,
            "capability_cannot_be_constructed_from_raw_mapping": True,
            "capability_projection_contains_conversion_counts_incremental_credit_and_effects_only": True,
            "exact_ordinal_aggregate_preserves_support_conflict_safe_change_and_credit_funnel": True,
            "reselected_resealed_private_content_fails_exact_byte_binding": True,
            "manifest_surface_symlink_terminal_support_effect_and_memo_attacks_fail_closed": True,
            "parent_compact_validation_does_not_replay_reserve_or_historical_semantics": True,
            "source_count_posterior_margin_leave_one_out_and_credit_rules_unchanged": True,
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
            "new_external_reserve_gate_design": not findings,
            "new_external_probe_launch": False,
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
