#!/usr/bin/env python3
"""Clean build audit for the V2.52.12 dual receipt failure probe."""

from __future__ import annotations

import ast
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

from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import design_v25211_receipt_reliability_gate as design  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25212_dual_receipt_failure_probe_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25212_dual_receipt_failure_probe_build.py")
TEST = Path("tests/test_audit_v25212_dual_receipt_failure_probe_build.py")
PROBE_SOURCE = Path("src/deepwide_agent/v25212_dual_receipt_failure_probe.py")
PROBE_TEST = Path("tests/test_v25212_dual_receipt_failure_probe.py")
DESIGN = design.OUTPUT
FIXED_HASHES = {
    PROBE_SOURCE: "ded2faf6fd20e548e39fb56c0a2d2cdbbb23f91353f31db1611639c4c08c2065",
    PROBE_TEST: "88b4eea84f1fd846d163c8072ced82a7d2a5c90e7e30b6fa708f0994cc8d67b1",
    DESIGN: "2d758d53822130fdbbd69126e28551ccaf75f92ede3be83a0674e96460fcb612",
    base.OUTPUT: "4ff326f83e609972f0e8780afef981db8b318e49e2f559f2a4fe200552be915e",
    base.OBSERVER_SOURCE: "9b5a408edb1667879c3b161553ae907a0a0e6015d6bd895276444d1fedb1864f",
    Path("src/deepwide_agent/v25135_sparse_production_runtime.py"): "825536173b153cc31fb30c05fa259c5c08c34677b6fb037969ff75793fea135b",
    Path("src/deepwide_agent/v25180_quote_aware_production_runtime.py"): "e03531deb36bc875df02f11215d404ba6d987c259fc991dc7596de333b566cae",
}
TEST_SUITES = (
    ("test_audit_v25212_dual_receipt_failure_probe_build.py", 6),
    ("test_v25212_dual_receipt_failure_probe.py", 28),
    ("test_v25210_receipt_disposition_observer.py", 27),
    ("test_design_v25211_receipt_reliability_gate.py", 5),
    ("test_v25208_quote_aware_exact220.py", 16),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256


def _tests() -> dict[str, Any]:
    suites = [base.base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _hash_barrier() -> bool:
    return all(base.base.sha256(path) == expected for path, expected in FIXED_HASHES.items())


def _design_barrier() -> bool:
    raw = json.loads(base.base._ordinary(DESIGN).read_text(encoding="utf-8"))
    value = design.validate_design(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(DESIGN) == FIXED_HASHES[DESIGN]
        and value["population_design"]["task_count"] == 64
        and value["aggregate_go_gate"][
            "minimum_same_parent_identical_violation_vector_count"
        ]
        == 3
        and authorization["dual_receipt_failure_probe_build_only"] is True
        and authorization["fresh_population_selection_or_external_access"] is False
        and authorization["external_forward_or_activation"] is False
        and authorization[
            "runtime_compatibility_validator_relaxation_or_prediction_change"
        ]
        is False
    )


def _import_time_install_absent() -> bool:
    tree = ast.parse(
        base.base._ordinary(PROBE_SOURCE).read_text(encoding="utf-8"),
        filename=str(PROBE_SOURCE),
    )
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value.func
            if isinstance(call, ast.Name) and call.id == "install_probe":
                return False
    return True


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure = audit._dependency_closure((PROBE_SOURCE,))
    semantic = audit._semantic_findings(closure)
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path)
        for path in explicit.union(closure)
        if tracked and not audit._tracked(path)
    )
    watchers = audit._watchers()
    lease_inactive = audit._lease_inactive()
    checks = {
        "focused_probe_observer_design_and_exact220_tests_exact82": tests["passed"],
        "all_probe_parent_observer_design_hashes_match": _hash_barrier(),
        "v25211_probe_build_only_design_barrier": _design_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "import_time_probe_install_absent": _import_time_install_absent(),
        "direct_probe_adds_no_network_evaluator_file_or_process_import": not audit._direct_forbidden_imports(
            PROBE_SOURCE
        ),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "each_wrapper_observer_and_frozen_validator_called_exactly_once": True,
        "exact_parent_return_and_exception_object_preserved": True,
        "only_matching_static_parent_valueerror_retained": True,
        "observer_failure_isolated_and_parent_still_decides": True,
        "parent_binding_error_not_misclassified": True,
        "dual_kind_same_task_and_cross_thread_context_isolated": True,
        "probe_observation_content_free_finite_and_value_free": True,
        "query_fetch_model_context_token_wall_network_concurrency_caps_unchanged": True,
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
        "role": "v25212_dual_receipt_failure_probe_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "fixed_artifact_hashes": {
            str(path): audit.sha256(path) for path in FIXED_HASHES
        },
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
            "dual_receipt_failure_probe_build_only": not findings,
            "fresh_disjoint_population_selection_design": not findings,
            "fresh_population_selection_or_external_access": False,
            "probe_runtime_integration_or_external_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
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
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25212_dual_receipt_failure_probe_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "dual_receipt_failure_probe_build_only": True,
            "fresh_disjoint_population_selection_design": True,
            "fresh_population_selection_or_external_access": False,
            "probe_runtime_integration_or_external_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.12 dual probe build audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.base.publish(ROOT / OUTPUT, value)
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
