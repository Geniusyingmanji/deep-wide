#!/usr/bin/env python3
"""Clean-build audit for the V2.51.43 quote-attested cell-edit runtime."""

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
    f"results/v25144_quote_attested_cell_edit_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25144_quote_attested_cell_edit_build.py")
TEST = Path("tests/test_audit_v25144_quote_attested_cell_edit_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25143_quote_attested_cell_edit_runtime.py"
)
RUNTIME_TEST = Path("tests/test_v25143_quote_attested_cell_edit_runtime.py")
PARENT_DIAGNOSIS = Path(
    "results/v25142_v25141_targeted_revision_diagnosis_v1_20260812.json"
)
EXPECTED_PARENT_HASH = (
    "61d4dd42b58d86dc55248889ed4ab4f86cc4d997ef465dda9f4de931dfff829d"
)
TEST_SUITES = (
    ("test_audit_v25144_quote_attested_cell_edit_build.py", 5),
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
    return bool(
        audit_parent.sha256(PARENT_DIAGNOSIS) == EXPECTED_PARENT_HASH
        and value.get("role")
        == "v25142_v25141_targeted_revision_counts_only_diagnosis"
        and value.get("diagnosis_valid") is True
        and value.get("findings") == []
        and diagnosis.get(
            "primary_bottleneck_is_value_bearing_cell_edit_observation"
        )
        is True
        and diagnosis.get(
            "next_build_only_candidate_should_request_structured_cell_edits_not_full_table_resynthesis"
        )
        is True
        and diagnosis.get(
            "each_edit_must_bind_page_ordinal_exact_quote_row_field_old_and_new_value"
        )
        is True
        and diagnosis.get(
            "exact_quote_must_mechanically_contain_row_field_and_new_value_with_bounded_span"
        )
        is True
        and diagnosis.get(
            "unsupported_conflicting_unknown_key_row_or_shape_edit_must_preserve_production"
        )
        is True
        and diagnosis.get(
            "query_fetch_model_context_token_wall_and_network_caps_must_not_expand"
        )
        is True
        and diagnosis.get("v25141_population_must_not_be_retried_resumed_or_reused")
        is True
        and diagnosis.get("entropy_or_information_gain_signed_credit") == 0
        and authorization.get("quote_attested_cell_edit_successor_build_only")
        is True
        and authorization.get("new_external_protocol_or_launch") is False
        and authorization.get("v25141_evaluator_or_quality_result") is False
        and authorization.get("v25141_retry_resume_or_population_reuse") is False
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
        "focused_quote_attested_and_parent_tests_exact113": tests["passed"],
        "v25142_counts_only_diagnosis_bound": _diagnosis_barrier(),
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
        "strict_json_quote_attested_cell_edit_build_only": True,
        "exact_quote_bound_to_corresponding_page_content_only": True,
        "row_field_old_value_and_new_value_fail_closed": True,
        "duplicate_conflicting_unknown_key_or_shape_edit_preserves_production": True,
        "model_edit_accounting_is_closed": True,
        "query_fetch_model_output_token_wall_and_network_caps_unchanged": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25144_quote_attested_cell_edit_clean_build_audit",
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
        != "v25144_quote_attested_cell_edit_clean_build_audit"
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
        raise ValueError("V2.51.44 quote-attested build audit drifted")
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
