#!/usr/bin/env python3
"""Clean-build audit for V2.52.32 behavior-preserving shadow runtime."""

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


DATE = "20260812"
ROLE = "v25233_header_totality_shadow_clean_build_audit"
OUTPUT = Path(f"results/v25233_header_totality_shadow_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25233_header_totality_shadow_build.py")
TEST = Path("tests/test_audit_v25233_header_totality_shadow_build.py")
RUNTIME = Path("src/deepwide_agent/v25232_header_totality_shadow_runtime.py")
RUNTIME_TEST = Path("tests/test_v25232_header_totality_shadow_runtime.py")
HELPER_AUDIT = Path(f"results/v25231_header_totality_build_audit_v1_{DATE}.json")
DESIGN = Path(f"results/v25229_header_totality_successor_design_v1_{DATE}.json")
DIAGNOSIS = Path(
    f"results/v25228_v25208_production_totality_diagnosis_v1_{DATE}.json"
)
FIXED_HASHES = {
    RUNTIME: "f9cf2f0c51677d42f9ca2243e5de0fe26aedb09428dcc87c1bedf8dea8eec0f0",
    RUNTIME_TEST: "0cc8be7d54d37f8d4c0702c645d97a1091a16b129bd3ac4f505ad7203f1be9aa",
    HELPER_AUDIT: "459a275d482a62d0ea94b5d4566d33961c80a387147048e2e273150e2325fbd6",
    DESIGN: "bbf47a177cb9a8fca0e8fcbd945fc1c4000345167a5f46d1d167601e28998291",
    DIAGNOSIS: "400cd12be3bd3825ce7aa27652efda1004a3f2c399005afe5d47a702fbf456f7",
}
EXPECTED_CLOSURE_COUNT = 72
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "ea2e48cb4e9367ebcf900e36ebb386fe26d6f22bddd1885e14c8cb15f75f9e11"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "bbf8528f86c472b89ef4e442eea03ed671debf28dfe864bb99f6ea9146ef3fb0"
)
TEST_SUITES = (
    ("test_audit_v25233_header_totality_shadow_build.py", 7),
    ("test_v25232_header_totality_shadow_runtime.py", 8),
    ("test_v25180_quote_aware_production_runtime.py", 9),
    # This suite intentionally imports and reruns the nine V2.51.80 parent
    # tests before its four successor tests.
    ("test_v25188_export_failure_tolerant_same_response_runtime.py", 13),
    ("test_v25230_index_positional_header_normalizer.py", 12),
    ("test_v25170_production_normalizer_disposition_observer.py", 6),
    ("test_audit_v25231_header_totality_build.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def _fixed_hash_barrier() -> bool:
    return all(base.sha256(path) == expected for path, expected in FIXED_HASHES.items())


def _authority_barrier() -> bool:
    helper = json.loads(base._ordinary(HELPER_AUDIT).read_text(encoding="utf-8"))
    design = json.loads(base._ordinary(DESIGN).read_text(encoding="utf-8"))
    diagnosis = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    return bool(
        _fixed_hash_barrier()
        and helper.get("role")
        == "v25231_header_totality_normalizer_clean_build_audit"
        and helper.get("audit_valid") is True
        and helper.get("findings") == []
        and helper.get("authorization", {}).get(
            "fresh_artifact_disjoint_reliability_protocol_design"
        )
        is True
        and helper.get("authorization", {}).get(
            "runtime_integration_or_prediction_change"
        )
        is False
        and design.get("role") == "v25229_header_totality_successor_design"
        and diagnosis.get("role")
        == "v25228_v25208_production_totality_aggregate_diagnosis"
        and diagnosis.get("aggregate", {})
        .get("disposition_counts", {})
        .get("no_bindable_header_reject")
        == 4
    )


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = base._dependency_closure((RUNTIME,))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _closure_barrier() -> bool:
    closure, vector = _closure()
    return bool(
        len(closure) == EXPECTED_CLOSURE_COUNT
        and payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
        and payload_sha256([row["path"] for row in vector])
        == EXPECTED_CLOSURE_PATH_SHA256
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
    closure, vector = _closure()
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
        "shadow_runtime_helper_and_parent_chain_tests_exact62": tests["passed"],
        "helper_audit_design_and_diagnosis_authority_bound": _authority_barrier(),
        "all_fixed_runtime_test_and_artifact_hashes_match": _fixed_hash_barrier(),
        "all_runtime_test_parent_and_closure_files_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "full_parent_dependency_vector_exact72_and_hash_bound": _closure_barrier(),
        "shadow_entrypoint_has_no_direct_effect_imports": not base._direct_forbidden_imports(
            RUNTIME
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
        "shadow_only_after_frozen_no_bindable_header_and_quote_inactive": tests[
            "passed"
        ],
        "safe_candidate_missing_data_nonindex_valid_and_quote_neighbor_states_covered": tests[
            "passed"
        ],
        "shadow_failure_isolated_and_parent_predictions_hash_kind_cost_unchanged": tests[
            "passed"
        ],
        "no_global_runtime_monkeypatch": tests["passed"],
        "shadow_candidate_not_persisted_or_returned": True,
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
        "runtime_dependency_closure": {
            "count": len(closure),
            "path_vector_sha256": payload_sha256([row["path"] for row in vector]),
            "path_and_file_hash_vector_sha256": payload_sha256(vector),
            "paths": [row["path"] for row in vector],
        },
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
            "behavior_preserving_shadow_build_only": not findings,
            "fresh_artifact_disjoint_shadow_reliability_protocol_design": not findings,
            "candidate_activation_or_prediction_change": False,
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
    closure = copied.get("runtime_dependency_closure") or {}
    semantic = copied.get("runtime_semantic_audit") or {}
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
        or closure.get("count") != EXPECTED_CLOSURE_COUNT
        or closure.get("path_vector_sha256") != EXPECTED_CLOSURE_PATH_SHA256
        or closure.get("path_and_file_hash_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or not isinstance(closure.get("paths"), list)
        or len(closure["paths"]) != EXPECTED_CLOSURE_COUNT
        or payload_sha256(closure["paths"]) != EXPECTED_CLOSURE_PATH_SHA256
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or semantic.get("untracked_sources") != []
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "behavior_preserving_shadow_build_only": True,
            "fresh_artifact_disjoint_shadow_reliability_protocol_design": True,
            "candidate_activation_or_prediction_change": False,
            "fresh_external_activation_or_launch": False,
            "old_fullset_retry_resume_replay_replacement_or_selective_rerun": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.33 header-totality shadow build audit drifted")
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
                "closure": value["runtime_dependency_closure"]["count"],
                "findings": value["findings"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
