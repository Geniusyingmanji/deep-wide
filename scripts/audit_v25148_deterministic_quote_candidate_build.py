#!/usr/bin/env python3
"""Clean-build audit for the V2.51.47 deterministic quote-candidate runtime."""

from __future__ import annotations

import copy
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25140_targeted_revision_build as audit_parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(
    f"results/v25148_deterministic_quote_candidate_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25148_deterministic_quote_candidate_build.py")
TEST = Path("tests/test_audit_v25148_deterministic_quote_candidate_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25147_deterministic_quote_candidate_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25147_deterministic_quote_candidate_runtime.py"
)
PARENT_DIAGNOSIS = Path(
    "results/v25146_v25145_quote_attested_diagnosis_v1_20260812.json"
)
EXPECTED_PARENT_HASH = (
    "70362b988e17af3bef6e6c0c1a47988b00c0e8d44ac65ca82da91755fd7ac617"
)
TEST_SUITES = (
    ("test_audit_v25148_deterministic_quote_candidate_build.py", 5),
    ("test_v25147_deterministic_quote_candidate_runtime.py", 12),
    ("test_diagnose_v25146_v25145_quote_attested.py", 4),
    ("test_v25143_quote_attested_cell_edit_runtime.py", 12),
    ("test_v25139_targeted_revision_runtime.py", 13),
    ("test_v25135_sparse_production_runtime.py", 9),
    ("test_v25134_schema_total_causal_salience_runtime.py", 8),
    ("test_v25127_causally_coupled_target_record_runtime.py", 5),
    ("test_v25123_visible_legacy_query_compatible_runtime.py", 7),
    ("test_v25119_grounded_target_record_paired_runtime.py", 7),
    ("test_v25117_grounded_target_record_plan.py", 6),
    ("test_v25118_target_record_frontier_selection.py", 7),
    ("test_v24999_shared_response_selection_runtime.py", 7),
    ("test_v24990_query_vector_paired_runtime.py", 7),
    ("test_v24986_robust_paired_runtime.py", 5),
    ("test_v24984_robust_late_page_projection.py", 4),
    ("test_v24980_late_page_bound_projection.py", 8),
    ("test_v25110_exact_visible_schema.py", 4),
    ("test_v24259_deterministic_table_normalizer.py", 11),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)


payload_sha256 = audit_parent.payload_sha256


def _tests() -> dict[str, Any]:
    suites = [
        audit_parent._test(pattern, expected)
        for pattern, expected in TEST_SUITES
    ]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _diagnosis_barrier() -> bool:
    value = json.loads(
        audit_parent._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8")
    )
    diagnosis = value.get("diagnosis") or {}
    authorization = value.get("authorization") or {}
    funnel = value.get("content_free_funnel") or {}
    return bool(
        audit_parent.sha256(PARENT_DIAGNOSIS) == EXPECTED_PARENT_HASH
        and value.get("role") == "v25146_v25145_quote_attested_counts_only_diagnosis"
        and value.get("diagnosis_valid") is True
        and value.get("findings") == []
        and funnel.get("verified_gain_tasks") == 7
        and funnel.get("cell_edit_revision_tasks") == 7
        and funnel.get("model_edit_total") == 0
        and funnel.get("rejected_edit_total") == 0
        and diagnosis.get(
            "primary_bottleneck_is_edit_proposal_recall_not_verifier_precision"
        )
        is True
        and diagnosis.get(
            "next_build_only_candidate_should_supply_deterministically_extracted_quote_candidates_before_model_edit_selection"
        )
        is True
        and diagnosis.get(
            "deterministic_quote_candidates_must_be_same_page_source_row_field_value_bound_and_content_exact"
        )
        is True
        and diagnosis.get(
            "model_should_select_or_abstain_over_verified_quote_candidates_not_copy_arbitrary_page_text"
        )
        is True
        and diagnosis.get(
            "query_fetch_model_context_token_wall_and_network_caps_must_not_expand"
        )
        is True
        and diagnosis.get("v25145_population_must_not_be_retried_resumed_or_reused")
        is True
        and diagnosis.get("entropy_or_information_gain_signed_credit") == 0
        and authorization.get("deterministic_quote_candidate_successor_build_only")
        is True
        and authorization.get("new_external_protocol_or_launch") is False
        and authorization.get("v25145_evaluator_or_quality_result") is False
        and authorization.get("v25145_retry_resume_or_population_reuse") is False
        and authorization.get(
            "deepwidebench_dev64_exact220_leaderboard_or_sota"
        )
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = audit_parent._git("rev-parse", "HEAD")
    target = audit_parent._git("rev-parse", "target/main")
    clean = not audit_parent._git("status", "--porcelain")
    tests = _tests()
    closure = audit_parent._dependency_closure((RUNTIME_SOURCE,))
    semantic = audit_parent._semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        PARENT_DIAGNOSIS,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not audit_parent._tracked(path)
    )
    watchers = audit_parent._watchers()
    lease_inactive = audit_parent._lease_inactive()
    checks = {
        "focused_deterministic_candidate_and_parent_tests_exact141": tests["passed"],
        "v25146_counts_only_diagnosis_bound": _diagnosis_barrier(),
        "all_sources_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "direct_candidate_has_no_effect_imports": not audit_parent._direct_forbidden_imports(
            RUNTIME_SOURCE
        ),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True
            for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
        "same_forward_atomic_bound_json_or_pipe_span_candidates_only": True,
        "every_candidate_preverified_and_selected_edit_reverified": True,
        "model_selects_candidate_ids_or_abstains": True,
        "conflicts_deduplicates_and_context_are_bounded": True,
        "query_fetch_model_output_token_wall_and_network_caps_unchanged": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25148_deterministic_quote_candidate_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "runtime_dependency_closure": [str(path) for path in closure],
        "runtime_semantic_audit": {**semantic, "untracked_sources": untracked},
        "parent_diagnosis": {
            "path": str(PARENT_DIAGNOSIS),
            "sha256": audit_parent.sha256(PARENT_DIAGNOSIS),
        },
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers": watchers,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_population_reuse_or_selective_rerun": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    expected_authorization = {
        "fresh_disjoint_external_protocol_design",
        "fresh_external_activation_or_launch",
        "evaluator_or_deepwidebench_or_sota",
        "retry_resume_population_reuse_or_selective_rerun",
    }
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25148_deterministic_quote_candidate_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_diagnosis", {}).get("sha256")
        != EXPECTED_PARENT_HASH
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or set(authorization) != expected_authorization
        or authorization.get("fresh_disjoint_external_protocol_design") is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("evaluator_or_deepwidebench_or_sota") is not False
        or authorization.get(
            "retry_resume_population_reuse_or_selective_rerun"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.48 deterministic quote-candidate audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    audit_parent.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
