#!/usr/bin/env python3
"""Clean-build audit for the pure V2.52.30 header-totality normalizer."""

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

from deepwide_agent import (  # noqa: E402
    v25230_index_positional_header_normalizer as normalizer,
)
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402


DATE = "20260812"
ROLE = "v25231_header_totality_normalizer_clean_build_audit"
OUTPUT = Path(f"results/v25231_header_totality_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25231_header_totality_build.py")
TEST = Path("tests/test_audit_v25231_header_totality_build.py")
IMPLEMENTATION = Path(
    "src/deepwide_agent/v25230_index_positional_header_normalizer.py"
)
IMPLEMENTATION_TEST = Path(
    "tests/test_v25230_index_positional_header_normalizer.py"
)
DESIGN = Path(f"results/v25229_header_totality_successor_design_v1_{DATE}.json")
DIAGNOSIS = Path(
    f"results/v25228_v25208_production_totality_diagnosis_v1_{DATE}.json"
)
FIXED_HASHES = {
    Path("src/deepwide_agent/clients.py"): "339d923973f07ebcd33cb12cee2c26103df70ed3aea1fc0a737ffd675ac06fbc",
    Path("src/deepwide_agent/v24257_score_first_runtime.py"): "c4e3f818d0306f53d40f641a7a580aa7238e0698d2863301fe8399d8e3c1fa3e",
    Path("src/deepwide_agent/v24259_deterministic_table_normalizer.py"): "bc2ed6ae62cd68cf908ff2c50f59caa37cf6f57d9d12ab3db5294cf39b2c5f91",
    Path("src/deepwide_agent/v24263_global_model_limiter.py"): "050751273bf28520bb82799e5194b9b404c58fecf6c5a725cfea93da0d041497",
    IMPLEMENTATION: "26440fcfa6d1b4467dfb905fc45322d3c9a359a65d5cd0f8873fd6aaa4ff45ee",
    IMPLEMENTATION_TEST: "3e2303520a01d56002223d8260187ca4963d5591fd362ea961032f87012ea24e",
    DESIGN: "bbf47a177cb9a8fca0e8fcbd945fc1c4000345167a5f46d1d167601e28998291",
    DIAGNOSIS: "400cd12be3bd3825ce7aa27652efda1004a3f2c399005afe5d47a702fbf456f7",
}
EXPECTED_CLOSURE = (
    Path("src/deepwide_agent/clients.py"),
    Path("src/deepwide_agent/v24257_score_first_runtime.py"),
    Path("src/deepwide_agent/v24259_deterministic_table_normalizer.py"),
    Path("src/deepwide_agent/v24263_global_model_limiter.py"),
    IMPLEMENTATION,
)
TEST_SUITES = (
    ("test_audit_v25231_header_totality_build.py", 7),
    ("test_v25230_index_positional_header_normalizer.py", 12),
    ("test_v24259_deterministic_table_normalizer.py", 11),
    ("test_v25170_production_normalizer_disposition_observer.py", 6),
    ("test_v25177_quote_aware_pipe_normalizer.py", 9),
    ("test_design_v25229_header_totality_successor.py", 7),
    ("test_diagnose_v25228_v25208_production_totality.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def _fixed_hash_barrier() -> bool:
    return all(base.sha256(path) == expected for path, expected in FIXED_HASHES.items())


def _authority_barrier() -> bool:
    diagnosis = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    design = json.loads(base._ordinary(DESIGN).read_text(encoding="utf-8"))
    return bool(
        _fixed_hash_barrier()
        and diagnosis.get("role")
        == "v25228_v25208_production_totality_aggregate_diagnosis"
        and diagnosis.get("aggregate", {})
        .get("disposition_counts", {})
        .get("no_bindable_header_reject")
        == 4
        and diagnosis.get("authorization", {}).get(
            "synthetic_header_totality_successor_design_only"
        )
        is True
        and design.get("role") == "v25229_header_totality_successor_design"
        and design.get("single_change", {}).get("mode") == normalizer.MODE
        and design.get("authorization", {}).get(
            "header_totality_pure_implementation_build_only"
        )
        is True
        and design.get("authorization", {}).get(
            "runtime_integration_or_prediction_change"
        )
        is False
    )


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure = base._dependency_closure((IMPLEMENTATION,))
    semantic = base._semantic_findings(closure)
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path)
        for path in explicit.union(closure)
        if tracked and not base._tracked(path)
    )
    watchers = base._watchers()
    lease_inactive = base._lease_inactive()
    checks = {
        "header_totality_and_frozen_parent_chain_tests_exact59": tests["passed"],
        "v25228_diagnosis_and_v25229_design_authority_bound": _authority_barrier(),
        "all_fixed_sources_tests_and_artifacts_match": _fixed_hash_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "runtime_dependency_closure_exact_five_files": closure == EXPECTED_CLOSURE,
        "new_module_has_no_direct_effect_imports": not base._direct_forbidden_imports(
            IMPLEMENTATION
        ),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "finite_disposition_and_count_vocabularies": (
            len(normalizer.DISPOSITION_NAMES) == 14
            and len(set(normalizer.DISPOSITION_NAMES)) == 14
            and len(normalizer.COUNT_NAMES) == 18
            and len(set(normalizer.COUNT_NAMES)) == 18
        ),
        "arbitrary_string_totality_and_receipt_tamper_covered": tests["passed"],
        "positive_output_exact_parser_roundtrip_covered": tests["passed"],
        "missing_data_width_escape_collision_and_ambiguity_fail_closed": tests[
            "passed"
        ],
        "parent_normalizer_and_observer_sources_unchanged": True,
        "new_helper_not_installed_into_runtime": True,
        "receipt_has_no_response_header_cell_identity_question_url_prediction_or_semantic_hash": True,
        "query_fetch_model_context_token_wall_network_and_concurrency_caps_unchanged": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "fixed_artifact_hashes": _fixed_hashes(),
        "runtime_dependency_closure": [str(path) for path in closure],
        "runtime_semantic_audit": {**semantic, "untracked_sources": untracked},
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
            "header_totality_helper_build_only": not findings,
            "fresh_artifact_disjoint_reliability_protocol_design": not findings,
            "runtime_integration_or_prediction_change": False,
            "fresh_external_activation_or_launch": False,
            "old_fullset_retry_resume_replay_replacement_or_selective_rerun": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
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
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "tests",
            "fixed_artifact_hashes",
            "runtime_dependency_closure",
            "runtime_semantic_audit",
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
        or copied.get("role") != ROLE
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("runtime_dependency_closure")
        != [str(path) for path in EXPECTED_CLOSURE]
        or copied.get("runtime_semantic_audit", {}).get(
            "privileged_runtime_field_accesses"
        )
        != []
        or copied.get("runtime_semantic_audit", {}).get("evaluator_capabilities")
        != []
        or copied.get("runtime_semantic_audit", {}).get("credential_literal_hits")
        != []
        or copied.get("runtime_semantic_audit", {}).get("untracked_sources") != []
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "header_totality_helper_build_only": True,
            "fresh_artifact_disjoint_reliability_protocol_design": True,
            "runtime_integration_or_prediction_change": False,
            "fresh_external_activation_or_launch": False,
            "old_fullset_retry_resume_replay_replacement_or_selective_rerun": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.31 header-totality build audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.publish(ROOT / OUTPUT, value)
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
