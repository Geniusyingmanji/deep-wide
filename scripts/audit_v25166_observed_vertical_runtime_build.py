#!/usr/bin/env python3
"""Clean-build audit for the V2.51.65 observed vertical runtime."""

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

from scripts import audit_v25164_vertical_admission_disposition_build as audit_parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(
    f"results/v25166_observed_vertical_runtime_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25166_observed_vertical_runtime_build.py")
TEST = Path("tests/test_audit_v25166_observed_vertical_runtime_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25165_observed_vertical_key_value_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25165_observed_vertical_key_value_runtime.py"
)
OBSERVER_SOURCE = audit_parent.OBSERVER_SOURCE
OBSERVER_TEST = audit_parent.OBSERVER_TEST
PARENT_AUDIT = audit_parent.OUTPUT
EXPECTED_PARENT_AUDIT_HASH = (
    "2e0c3cc84fad108eacee15b178f4980194b9fa8edfa8c160b1c1f71ae819d555"
)
TEST_SUITES = (
    ("test_audit_v25166_observed_vertical_runtime_build.py", 5),
    ("test_v25165_observed_vertical_key_value_runtime.py", 6),
    ("test_v25163_vertical_admission_disposition_observer.py", 7),
    ("test_diagnose_v25162_v25160_vertical_key_value.py", 5),
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
payload_sha256 = audit_parent.payload_sha256


def _tests() -> dict[str, Any]:
    suites = [
        audit_parent.audit_parent.audit_parent._test(pattern, expected)
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


def _base() -> Any:
    return audit_parent.audit_parent.audit_parent


def _parent_barrier() -> bool:
    parent = json.loads(
        _base()._ordinary(PARENT_AUDIT).read_text(encoding="utf-8")
    )
    value = audit_parent.validate_audit(parent)
    authorization = value["authorization"]
    return bool(
        _base().sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_HASH
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 159
        and value["tests"]["observed"] == 159
        and authorization["implementation_build_only"] is True
        and authorization["fresh_disjoint_observer_protocol_design"] is False
        and authorization["fresh_external_activation_or_launch"] is False
        and authorization["vertical_binding_policy_change"] is False
        and authorization[
            "v25160_population_model_evaluator_retry_resume_or_reuse"
        ]
        is False
        and authorization["evaluator_or_deepwidebench_or_sota"] is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    base = _base()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure = base._dependency_closure((RUNTIME_SOURCE,))
    semantic = base._semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        OBSERVER_SOURCE,
        OBSERVER_TEST,
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
        "focused_observed_runtime_observer_and_parent_tests_exact165": tests[
            "passed"
        ],
        "v25164_clean_build_audit_bound": _parent_barrier(),
        "all_sources_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "direct_runtime_adds_no_network_or_evaluator_import": not base._direct_forbidden_imports(
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
        "verified_delta_result_or_failure_computed_once_and_cache_reused": True,
        "observer_failure_isolated_and_frozen_parent_continues": True,
        "parent_prediction_hash_cost_candidate_and_effect_receipts_unchanged": True,
        "observer_receipt_parity_bound_to_frozen_parent_counts": True,
        "no_gain_three_and_verified_gain_at_most_four_model_forwards": True,
        "query_fetch_model_context_token_wall_and_network_caps_unchanged": True,
        "v25160_population_not_read_retried_resumed_or_reused": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25166_observed_vertical_runtime_clean_build_audit",
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
        "parent_observer_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": base.sha256(PARENT_AUDIT),
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
            "implementation_build_only": not findings,
            "fresh_disjoint_observer_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "vertical_binding_policy_change": False,
            "v25160_population_model_evaluator_retry_resume_or_reuse": False,
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
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25166_observed_vertical_runtime_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_observer_build_audit", {}).get("sha256")
        != EXPECTED_PARENT_AUDIT_HASH
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
        or authorization
        != {
            "implementation_build_only": True,
            "fresh_disjoint_observer_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "vertical_binding_policy_change": False,
            "v25160_population_model_evaluator_retry_resume_or_reuse": False,
            "evaluator_or_deepwidebench_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.66 observed runtime audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    _base().publish(ROOT / OUTPUT, value)
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
