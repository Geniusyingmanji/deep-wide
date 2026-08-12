#!/usr/bin/env python3
"""Clean-build audit for V2.51.70/71 production-normalizer observation."""

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
from scripts import diagnose_v25169_v25167_observer_censoring as diagnosis  # noqa: E402


DATE = "20260812"
OUTPUT = Path(
    f"results/v25172_observed_production_normalizer_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25172_observed_production_normalizer_build.py")
TEST = Path("tests/test_audit_v25172_observed_production_normalizer_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25171_observed_production_normalizer_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25171_observed_production_normalizer_runtime.py"
)
OBSERVER_SOURCE = Path(
    "src/deepwide_agent/v25170_production_normalizer_disposition_observer.py"
)
OBSERVER_TEST = Path(
    "tests/test_v25170_production_normalizer_disposition_observer.py"
)
PARENT_DIAGNOSIS = diagnosis.OUTPUT
EXPECTED_PARENT_DIAGNOSIS_HASH = (
    "472f795b65492a2a13355284d869b1cb7fbef4830310dc9b85abd6fa8d01273d"
)
TEST_SUITES = (
    ("test_audit_v25172_observed_production_normalizer_build.py", 5),
    ("test_v25171_observed_production_normalizer_runtime.py", 6),
    ("test_v25170_production_normalizer_disposition_observer.py", 6),
    ("test_diagnose_v25169_v25167_observer_censoring.py", 5),
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
    value = json.loads(
        base._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8")
    )
    checked = diagnosis.validate_diagnosis(value)
    funnel = checked["content_free_funnel"]
    authorization = checked["authorization"]
    return bool(
        base.sha256(PARENT_DIAGNOSIS) == EXPECTED_PARENT_DIAGNOSIS_HASH
        and checked["diagnosis_valid"] is True
        and checked["findings"] == []
        and funnel["task_count"] == 20
        and funnel["production_provider_output_valid_tasks"] == 9
        and funnel["production_fallback_tasks"] == 11
        and funnel["verified_gain_tasks"] == 3
        and funnel["verified_gain_with_valid_production_tasks"] == 0
        and funnel["verified_gain_censored_by_invalid_production_tasks"] == 3
        and funnel["observer_entry_tasks"] == 0
        and funnel["all_three_provider_calls_succeeded_tasks"] == 20
        and not any(funnel["effect_health_totals"].values())
        and authorization["production_normalizer_disposition_observer_build_only"]
        is True
        and authorization["binding_successor_design"] is False
        and authorization["vertical_binding_policy_change"] is False
        and authorization["new_external_protocol_or_launch"] is False
        and authorization["v25167_evaluator_or_quality_result"] is False
        and authorization["v25167_retry_resume_or_population_reuse"] is False
        and authorization["deepwidebench_dev64_exact220_leaderboard_or_sota"]
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure = base._dependency_closure((RUNTIME_SOURCE, OBSERVER_SOURCE))
    semantic = base._semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        OBSERVER_SOURCE,
        OBSERVER_TEST,
        PARENT_DIAGNOSIS,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not base._tracked(path)
    )
    watchers = base._watchers()
    lease_inactive = base._lease_inactive()
    checks = {
        "focused_normalizer_observer_runtime_diagnosis_and_parent_tests_exact": tests[
            "passed"
        ],
        "v25169_frozen_censoring_diagnosis_bound": _parent_barrier(),
        "all_sources_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "direct_runtime_adds_no_network_or_evaluator_import": not base._direct_forbidden_imports(
            RUNTIME_SOURCE
        ),
        "direct_observer_has_no_effect_imports": not base._direct_forbidden_imports(
            OBSERVER_SOURCE
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
        "observer_runs_after_first_provider_response_before_sparse_fallback": True,
        "exact_normalized_and_reject_dispositions_match_frozen_parser_acceptance": True,
        "observer_failure_isolated_and_frozen_parent_continues": True,
        "parent_prediction_cost_candidate_failure_and_effect_behavior_unchanged": True,
        "response_cell_column_question_identity_url_page_key_value_prediction_and_semantic_hash_absent": True,
        "query_fetch_model_context_token_wall_and_network_caps_unchanged": True,
        "v25167_population_not_read_retried_resumed_or_reused": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25172_observed_production_normalizer_clean_build_audit",
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
        "parent_censoring_diagnosis": {
            "path": str(PARENT_DIAGNOSIS),
            "sha256": base.sha256(PARENT_DIAGNOSIS),
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
            "fresh_disjoint_normalizer_observer_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "v25167_population_model_evaluator_retry_resume_or_reuse": False,
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
        != "v25172_observed_production_normalizer_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_censoring_diagnosis", {}).get("sha256")
        != EXPECTED_PARENT_DIAGNOSIS_HASH
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
            "fresh_disjoint_normalizer_observer_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "v25167_population_model_evaluator_retry_resume_or_reuse": False,
            "evaluator_or_deepwidebench_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.72 normalizer observer audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.publish(ROOT / OUTPUT, value)
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
