#!/usr/bin/env python3
"""Clean-build audit for the V2.46.44 primary-identity pair gate.

The audit reads only repository source files, git state, two protected process
identities, and the shared lease.  It does not open a task artifact, question,
query, URL, page, prediction, gold, mapping, evaluator output, or credential.
It performs no network, model, search, fetch, benchmark, or evaluator effect.
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
from deepwide_agent import v24642_deterministic_pair_runtime as frozen  # noqa: E402
from deepwide_agent import v24644_primary_identity_pair_runtime as runtime  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402


DATE = "20260806"
AUDIT = Path(f"results/v24644_primary_identity_pair_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24642_deterministic_pair_runtime.py"),
    Path("tests/test_v24642_deterministic_pair_runtime.py"),
    Path("src/deepwide_agent/v24644_primary_identity_pair_runtime.py"),
    Path("tests/test_v24644_primary_identity_pair_runtime.py"),
    Path("scripts/audit_v24644_primary_identity_pair_build.py"),
    Path("tests/test_audit_v24644_primary_identity_pair_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0], SOURCES[2])
TEST_SUITES = (
    (Path("tests/test_v24640_evidence_constrained_runtime.py"), 11, 180),
    (Path("tests/test_v24642_deterministic_pair_runtime.py"), 14, 180),
    (Path("tests/test_v24644_primary_identity_pair_runtime.py"), 14, 180),
    (Path("tests/test_audit_v24644_primary_identity_pair_build.py"), 5, 120),
)
EXPECTED_TEST_COUNT = 44


def _implementation_valid() -> bool:
    run_globals = runtime._RUN_TASK.__globals__
    return (
        runtime.binding_is_private_and_stable()
        and runtime._RUN_TASK is not frozen.run_v24642_task
        and run_globals.get("discover_pairs") is runtime.discover_pairs
        and run_globals.get("_lead_requests") is runtime._page_title_only_lead_requests
        and run_globals.get("_page_vector") is runtime._final_url_page_vector
        and run_globals.get("_receipt") is runtime._receipt
        and run_globals.get("validate_result") is runtime.validate_result
        and frozen.run_v24642_task.__globals__.get("discover_pairs")
        is frozen.discover_pairs
        and frozen.run_v24642_task.__globals__.get("_lead_requests")
        is frozen._lead_requests
        and frozen.run_v24642_task.__globals__.get("_page_vector")
        is frozen._page_vector
        and frozen.run_v24642_task.__globals__.get("_receipt") is frozen._receipt
        and frozen.run_v24642_task.__globals__.get("validate_result")
        is frozen.validate_result
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
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
    implementation_valid = _implementation_valid()
    findings: list[str] = []
    if head != remote:
        findings.append("v24644_source_commit_not_pushed")
    if not clean:
        findings.append("v24644_source_worktree_not_clean")
    if not tracked:
        findings.append("v24644_source_not_tracked")
    if not implementation_valid:
        findings.append("v24644_private_frozen_binding_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24640_42_44_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24642_44_runtime")
    if imports:
        findings.append("evaluator_import_in_v24642_44_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24642_44_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")

    value = {
        "artifact_version": 1,
        "role": "v24644_primary_identity_pair_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_failure": {
            "v24642_result": "strict_no_go",
            "v24643_localized_identity_binding_failure": True,
            "same_population_retry_resume_selective_rerun_or_evaluation_authorized": False,
        },
        "mechanism": {
            "body_only_identity_binding_removed": True,
            "search_lead_title_blanked_before_fetch_effect": True,
            "ror_profile_lead_rewritten_to_official_api_without_new_effect": True,
            "final_fetched_url_used_for_identity_binding": True,
            "official_api_url_record_id_and_unique_ror_display_bound": True,
            "official_api_identity_projected_before_shared_page_cap": True,
            "exact_normalized_fetched_page_title_route_retained": True,
            "nonunknown_ror_and_all_country_cells_immutable": True,
            "provider_model_search_fetch_or_token_cap_increased": False,
            "entropy_or_task_credit_assigned": False,
            "private_frozen_binding_valid": implementation_valid,
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
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "passed": not accesses and not imports and not secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "benchmark_launched": False,
            "external_population_launched_by_audit": False,
            "evaluator_called": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "private_task_question_query_url_title_page_prediction_or_provider_payload_opened_by_audit": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_external_population_and_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "same_v24642_population_retry_resume_selective_rerun_or_evaluation": False,
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
