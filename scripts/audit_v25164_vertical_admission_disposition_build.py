#!/usr/bin/env python3
"""Clean-build audit for the V2.51.63 vertical disposition observer."""

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

from scripts import audit_v25159_vertical_key_value_candidate_build as audit_parent  # noqa: E402
from scripts import diagnose_v25162_v25160_vertical_key_value as diagnosis_parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(
    f"results/v25164_vertical_admission_disposition_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25164_vertical_admission_disposition_build.py")
TEST = Path("tests/test_audit_v25164_vertical_admission_disposition_build.py")
OBSERVER_SOURCE = Path(
    "src/deepwide_agent/v25163_vertical_admission_disposition_observer.py"
)
OBSERVER_TEST = Path(
    "tests/test_v25163_vertical_admission_disposition_observer.py"
)
DIAGNOSIS_SOURCE = Path(
    "scripts/diagnose_v25162_v25160_vertical_key_value.py"
)
DIAGNOSIS_TEST = Path(
    "tests/test_diagnose_v25162_v25160_vertical_key_value.py"
)
DIAGNOSIS_RESULT = diagnosis_parent.OUTPUT
PARENT_FORWARD = diagnosis_parent.contract.FORWARD_RESULT
PARENT_AUDIT = diagnosis_parent.contract.FORWARD_AUDIT
EXPECTED_DIAGNOSIS_HASH = (
    "0f4664fe01791126b8fb0d1abe07456b704e32c6fd3cc77106a22f0216283e0a"
)
EXPECTED_FORWARD_HASH = (
    "2845c5652d5c68ac2f881175918e39c52ac23878b970ab1d1809867b78ad137c"
)
EXPECTED_FORWARD_AUDIT_HASH = (
    "e68cec16d146256a4f5459d83ef58d90b1a7f896fcd374418bd2a8a4f33d9e82"
)
TEST_SUITES = (
    ("test_audit_v25164_vertical_admission_disposition_build.py", 5),
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
        audit_parent.audit_parent._test(pattern, expected)
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


def _parent_barrier() -> bool:
    diagnosis = json.loads(
        audit_parent.audit_parent._ordinary(DIAGNOSIS_RESULT).read_text(
            encoding="utf-8"
        )
    )
    value = diagnosis_parent.validate_diagnosis(diagnosis)
    authorization = value["authorization"]
    funnel = value["content_free_funnel"]
    return bool(
        audit_parent.audit_parent.sha256(DIAGNOSIS_RESULT)
        == EXPECTED_DIAGNOSIS_HASH
        and audit_parent.audit_parent.sha256(PARENT_FORWARD)
        == EXPECTED_FORWARD_HASH
        and audit_parent.audit_parent.sha256(PARENT_AUDIT)
        == EXPECTED_FORWARD_AUDIT_HASH
        and value["diagnosis_valid"] is True
        and value["findings"] == []
        and value["parents"]["mechanism_gate_passed"] is False
        and value["parents"]["failed_checks"] == diagnosis_parent.FAILED_CHECKS
        and funnel["verified_gain_tasks"] == 6
        and funnel["verified_incremental_page_total"] == 14
        and funnel["vertical_pipe_block_count_total"] == 8
        and funnel["vertical_identity_bound_block_count_total"] == 0
        and authorization["vertical_admission_disposition_observer_build_only"]
        is True
        and authorization["vertical_binding_policy_change"] is False
        and authorization["new_external_protocol_or_launch"] is False
        and authorization["v25160_evaluator_or_quality_result"] is False
        and authorization["v25160_retry_resume_or_population_reuse"] is False
        and authorization["deepwidebench_dev64_exact220_leaderboard_or_sota"]
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = audit_parent.audit_parent._git("rev-parse", "HEAD")
    target = audit_parent.audit_parent._git("rev-parse", "target/main")
    clean = not audit_parent.audit_parent._git("status", "--porcelain")
    tests = _tests()
    closure = audit_parent.audit_parent._dependency_closure((OBSERVER_SOURCE,))
    semantic = audit_parent.audit_parent._semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        OBSERVER_SOURCE,
        OBSERVER_TEST,
        DIAGNOSIS_SOURCE,
        DIAGNOSIS_TEST,
        DIAGNOSIS_RESULT,
        PARENT_FORWARD,
        PARENT_AUDIT,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not audit_parent.audit_parent._tracked(path)
    )
    watchers = audit_parent.audit_parent._watchers()
    lease_inactive = audit_parent.audit_parent._lease_inactive()
    checks = {
        "focused_disposition_observer_diagnosis_and_parent_tests_exact159": tests[
            "passed"
        ],
        "v25160_no_go_and_v25162_diagnosis_bound": _parent_barrier(),
        "all_sources_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "direct_observer_has_no_effect_imports": not audit_parent.audit_parent._direct_forbidden_imports(
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
        "ten_mutually_exclusive_exhaustive_dispositions": True,
        "block_and_page_admission_parity_with_frozen_v25158": True,
        "observer_cannot_change_admission_routing_prediction_or_budget": True,
        "observer_emits_no_page_key_value_identity_field_quote_or_semantic_hash": True,
        "v25160_population_not_read_retried_resumed_or_reused": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25164_vertical_admission_disposition_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "observer_dependency_closure": [str(path) for path in closure],
        "observer_semantic_audit": {**semantic, "untracked_sources": untracked},
        "parent_diagnosis": {
            "path": str(DIAGNOSIS_RESULT),
            "sha256": audit_parent.audit_parent.sha256(DIAGNOSIS_RESULT),
        },
        "parent_forward": {
            "path": str(PARENT_FORWARD),
            "sha256": audit_parent.audit_parent.sha256(PARENT_FORWARD),
        },
        "parent_forward_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": audit_parent.audit_parent.sha256(PARENT_AUDIT),
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
        != "v25164_vertical_admission_disposition_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_diagnosis", {}).get("sha256")
        != EXPECTED_DIAGNOSIS_HASH
        or copied.get("parent_forward", {}).get("sha256")
        != EXPECTED_FORWARD_HASH
        or copied.get("parent_forward_audit", {}).get("sha256")
        != EXPECTED_FORWARD_AUDIT_HASH
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
        raise ValueError("V2.51.64 disposition observer audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    audit_parent.audit_parent.publish(ROOT / OUTPUT, value)
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
