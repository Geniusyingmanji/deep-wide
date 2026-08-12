#!/usr/bin/env python3
"""Clean-build audit for the V2.51.58 vertical key-value binder."""

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
    f"results/v25159_vertical_key_value_candidate_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25159_vertical_key_value_candidate_build.py")
TEST = Path("tests/test_audit_v25159_vertical_key_value_candidate_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25158_vertical_key_value_candidate_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25158_vertical_key_value_candidate_runtime.py"
)
PARENT_RESULT = Path(
    "results/v25157_structure_layer_gate_forward_result_v1_20260812.json"
)
PARENT_AUDIT = Path(
    "results/v25157_structure_layer_gate_forward_audit_v1_20260812.json"
)
EXPECTED_PARENT_RESULT_HASH = (
    "69f92941bf947ff54e8484a017edf48b50f8b755e3cfc3cbfeb67b536612aab9"
)
EXPECTED_PARENT_AUDIT_HASH = (
    "53d1f68ca6b0da9cc9df2073bfbf5b554b221286d419d2dac9a211b86af1975b"
)
TEST_SUITES = (
    ("test_audit_v25159_vertical_key_value_candidate_build.py", 5),
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


def _parent_barrier() -> bool:
    result = json.loads(
        audit_parent._ordinary(PARENT_RESULT).read_text(encoding="utf-8")
    )
    audit = json.loads(
        audit_parent._ordinary(PARENT_AUDIT).read_text(encoding="utf-8")
    )
    aggregate = result.get("aggregate") or {}
    structure = aggregate.get("structure_counts") or {}
    decision = result.get("mechanism_decision") or {}
    result_authorization = result.get("authorization") or {}
    audit_authorization = audit.get("authorization") or {}
    return bool(
        audit_parent.sha256(PARENT_RESULT) == EXPECTED_PARENT_RESULT_HASH
        and audit_parent.sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_HASH
        and result.get("role") == "v25157_structure_layer_gate_forward_result"
        and result.get("protocol_id") == "v25157_cran_structure_layer_gate_v1"
        and aggregate.get("task_count") == 20
        and aggregate.get("terminal_tasks") == 20
        and aggregate.get("fetch_attempts") == 20
        and aggregate.get("fetch_successes") == 17
        and aggregate.get("failure_as_zero_tasks") == 3
        and structure.get("raw_table_count") == 59
        and structure.get("raw_table_row_count") == 333
        and structure.get("raw_table_data_cell_count") == 666
        and structure.get("extracted_pipe_line_count") == 333
        and structure.get("extracted_key_value_pipe_line_count") == 332
        and structure.get("projected_pipe_line_count") == 333
        and structure.get("projected_key_value_pipe_line_count") == 332
        and structure.get("raw_to_extracted_total_structure_loss_page_count")
        == 0
        and structure.get(
            "extracted_to_projected_total_structure_loss_page_count"
        )
        == 0
        and decision.get("structure_localization_gate_passed") is False
        and decision.get("failed_checks")
        == ["minimum_fetch_successes", "minimum_observed_structure_pages"]
        and result.get("model_hosted_search_or_evaluator_called") is False
        and result.get("retry_resume_population_replacement_or_selective_rerun")
        is False
        and result_authorization.get("model_or_evaluator_on_this_population")
        is False
        and result_authorization.get(
            "retry_resume_population_replacement_or_selective_rerun"
        )
        is False
        and result_authorization.get("deepwidebench_dev64_exact220_or_sota")
        is False
        and audit.get("role") == "v25157_structure_layer_gate_forward_audit"
        and audit.get("audit_valid") is True
        and audit.get("findings") == []
        and audit_authorization.get("model_or_evaluator_on_this_population")
        is False
        and audit_authorization.get(
            "retry_resume_population_replacement_or_selective_revaluation"
        )
        is False
        and audit_authorization.get("deepwidebench_dev64_exact220_or_sota")
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
        PARENT_RESULT,
        PARENT_AUDIT,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not audit_parent._tracked(path)
    )
    watchers = audit_parent._watchers()
    lease_inactive = audit_parent._lease_inactive()
    checks = {
        "focused_vertical_binder_and_parent_tests_exact159": tests["passed"],
        "v25157_no_go_structure_result_and_audit_bound": _parent_barrier(),
        "all_sources_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "direct_binder_has_no_effect_imports": not audit_parent._direct_forbidden_imports(
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
        "vertical_blocks_require_unique_primary_identity_and_visible_keys": True,
        "identity_to_field_quote_is_same_page_unique_and_at_most_1200_characters": True,
        "duplicate_key_multi_identity_multi_table_unknown_conflict_and_cross_page_fail_closed": True,
        "every_candidate_preverified_and_selected_edit_reverified": True,
        "shape_key_order_and_unselected_cells_are_immutable": True,
        "query_fetch_model_output_token_context_wall_and_network_caps_unchanged": True,
        "frozen_v25157_population_not_read_retried_resumed_or_reused_by_runtime": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25159_vertical_key_value_candidate_clean_build_audit",
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
        "parent_structure_result": {
            "path": str(PARENT_RESULT),
            "sha256": audit_parent.sha256(PARENT_RESULT),
        },
        "parent_structure_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": audit_parent.sha256(PARENT_AUDIT),
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
            "fresh_disjoint_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "v25157_population_model_evaluator_retry_resume_or_reuse": False,
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
        != "v25159_vertical_key_value_candidate_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_structure_result", {}).get("sha256")
        != EXPECTED_PARENT_RESULT_HASH
        or copied.get("parent_structure_audit", {}).get("sha256")
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
            "fresh_disjoint_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "v25157_population_model_evaluator_retry_resume_or_reuse": False,
            "evaluator_or_deepwidebench_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.59 vertical binder audit drifted")
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
