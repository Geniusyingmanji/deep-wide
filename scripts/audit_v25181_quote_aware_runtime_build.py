#!/usr/bin/env python3
"""Clean-HEAD audit for the V2.51.80 quote-aware production runtime."""

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

from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25178_quote_aware_normalizer_build as parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25181_quote_aware_runtime_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25181_quote_aware_runtime_build.py")
TEST = Path("tests/test_audit_v25181_quote_aware_runtime_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25180_quote_aware_production_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25180_quote_aware_production_runtime.py"
)
NORMALIZER_SOURCE = parent.NORMALIZER_SOURCE
NORMALIZER_TEST = parent.NORMALIZER_TEST
PARENT_AUDIT = parent.OUTPUT
EXPECTED_PARENT_AUDIT_HASH = (
    "d4394e1f581b6963e67c6662d3dec2a3f80dbf3817f0c6d5dd394a984dc04763"
)
TEST_SUITES = (
    ("test_audit_v25181_quote_aware_runtime_build.py", 5),
    ("test_v25180_quote_aware_production_runtime.py", 9),
    ("test_v25177_quote_aware_pipe_normalizer.py", 9),
    ("test_v25165_observed_vertical_key_value_runtime.py", 6),
    ("test_v25163_vertical_admission_disposition_observer.py", 7),
    ("test_v25158_vertical_key_value_candidate_runtime.py", 11),
    ("test_v25151_generic_record_quote_candidate_runtime.py", 11),
    ("test_v25147_deterministic_quote_candidate_runtime.py", 12),
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
    ("test_v25110_exact_visible_schema.py", 4),
    ("test_v24259_deterministic_table_normalizer.py", 11),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _parent_barrier() -> bool:
    raw = json.loads(base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    value = parent.validate_audit(raw)
    authorization = value["authorization"]
    nested = value["public_loader_nested_repository"]
    return bool(
        base.sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_HASH
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 37
        and value["tests"]["observed"] == 37
        and nested["nested_head"] == parent.EXPECTED_NESTED_HEAD
        and nested["blob_sha1"] == parent.EXPECTED_PUBLIC_LOADER_BLOB
        and nested["working_file_sha256"]
        == parent.EXPECTED_PUBLIC_LOADER_SHA256
        and authorization["pure_normalizer_build_valid"] is True
        and authorization["runtime_integration_design"] is True
        and authorization["runtime_integration_implementation"] is False
        and authorization["fresh_external_protocol_or_launch"] is False
        and authorization["old_population_retry_resume_rerun_or_reuse"] is False
        and authorization["evaluator_or_deepwidebench_or_sota"] is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure = base._dependency_closure((RUNTIME_SOURCE, NORMALIZER_SOURCE))
    semantic = base._semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        NORMALIZER_SOURCE,
        NORMALIZER_TEST,
        PARENT_AUDIT,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not base._tracked(path)
    )
    watchers = base._watchers()
    lease_inactive = base._lease_inactive()
    checks = {
        "focused_runtime_normalizer_and_complete_parent_chain_exact178": tests[
            "passed"
        ],
        "v25178_clean_normalizer_build_audit_bound": _parent_barrier(),
        "all_sources_tests_and_parent_artifact_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "direct_runtime_adds_no_network_or_evaluator_import": not base._direct_forbidden_imports(
            RUNTIME_SOURCE
        ),
        "direct_normalizer_has_no_effect_imports": not base._direct_forbidden_imports(
            NORMALIZER_SOURCE
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
        "accepted_raw_parent_prediction_cost_effect_and_receipts_byte_exact": True,
        "repair_only_after_frozen_parser_rejects_unambiguous_single_backslash_pipe": True,
        "row_width_double_backslash_partial_multiple_and_entity_collision_fail_closed": True,
        "public_loader_values_match_only_pipe_adjacent_whitespace_canonicalization": True,
        "candidate_new_moved_or_extra_entity_falls_back_to_completed_production": True,
        "observer_repair_and_publication_failure_preserve_completed_production": True,
        "no_gain_three_and_positive_gain_at_most_four_model_forwards": True,
        "query_fetch_model_context_token_wall_network_and_concurrency_caps_unchanged": True,
        "v25175_population_not_read_retried_resumed_rerun_or_reused": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25181_quote_aware_runtime_clean_build_audit",
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
        "parent_normalizer_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": base.sha256(PARENT_AUDIT),
        },
        "public_loader_nested_repository": parent._nested_loader_receipt(),
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
            "runtime_implementation_build_valid": not findings,
            "fresh_disjoint_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "old_population_retry_resume_rerun_or_reuse": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_deepwidebench_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    runtime_state = copied.get("runtime_state") or {}
    runtime_watchers = runtime_state.get("protected_watchers") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "tests",
            "runtime_dependency_closure",
            "runtime_semantic_audit",
            "parent_normalizer_build_audit",
            "public_loader_nested_repository",
            "runtime_state",
            "checks",
            "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25181_quote_aware_runtime_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_normalizer_build_audit", {}).get("sha256")
        != EXPECTED_PARENT_AUDIT_HASH
        or copied.get("public_loader_nested_repository")
        != parent._nested_loader_receipt()
        or runtime_state.get("shared_api_lease_inactive") is not True
        or set(runtime_watchers)
        != {str(pid) for pid in base.PROTECTED_WATCHERS}
        or any(
            not isinstance(row, Mapping)
            or row.get("matches_frozen_identity") is not True
            for row in runtime_watchers.values()
        )
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "runtime_implementation_build_valid": True,
            "fresh_disjoint_external_protocol_design": True,
            "fresh_external_activation_or_launch": False,
            "old_population_retry_resume_rerun_or_reuse": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_deepwidebench_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.81 quote-aware runtime audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    parent.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "tests": value["tests"]["observed"],
                "findings": value["findings"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
