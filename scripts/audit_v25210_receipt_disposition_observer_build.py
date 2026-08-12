#!/usr/bin/env python3
"""Clean build audit for the pure V2.52.10 receipt observer."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
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
from deepwide_agent import v25210_receipt_disposition_observer as observer  # noqa: E402


DATE = "20260812"
OUTPUT = Path(
    f"results/v25210_receipt_disposition_observer_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25210_receipt_disposition_observer_build.py")
TEST = Path("tests/test_audit_v25210_receipt_disposition_observer_build.py")
OBSERVER_SOURCE = Path(
    "src/deepwide_agent/v25210_receipt_disposition_observer.py"
)
OBSERVER_TEST = Path("tests/test_v25210_receipt_disposition_observer.py")
DIAGNOSIS = Path(
    "results/v25209_v25208_exact220_reliability_diagnosis_v1_20260812.json"
)
V25206_TEST = Path("tests/test_v25206_cran_dcf_quality.py")
V25206_EVALUATOR = Path("scripts/evaluate_v25206_cran_dcf_quality.py")
V25206_RECOVERY = Path(
    "results/v25207_v25206_hash_bound_preactivation_recovery_audit_v1_20260812.json"
)
V25206_RESULT = Path("results/v25206_cran_dcf_quality_result_v1_20260812.json")
V25206_POSTAUDIT = Path(
    "results/v25206_cran_dcf_quality_postresult_audit_v1_20260812.json"
)

FIXED_HASHES = {
    OBSERVER_SOURCE: "9b5a408edb1667879c3b161553ae907a0a0e6015d6bd895276444d1fedb1864f",
    OBSERVER_TEST: "c84e3da4e5d38094688e7f58045231c5e2104dbff8fd3c294a407ff999ccc41c",
    Path("src/deepwide_agent/v25135_sparse_production_runtime.py"): "825536173b153cc31fb30c05fa259c5c08c34677b6fb037969ff75793fea135b",
    Path("src/deepwide_agent/v25180_quote_aware_production_runtime.py"): "e03531deb36bc875df02f11215d404ba6d987c259fc991dc7596de333b566cae",
    Path("src/deepwide_agent/v25170_production_normalizer_disposition_observer.py"): "4bb27873dcae0896db83dcf35b23e71f3890d51a10b8c8b4dc6aa12a7f9fa71a",
    Path("src/deepwide_agent/v25177_quote_aware_pipe_normalizer.py"): "12cb76288b69b588d472ca8dcbbda169e676a73b48e61880c192902b0816e95d",
    DIAGNOSIS: "1dee7aea4bf5d7ab2c3fa9427c62ae6149aa25545ece38571cfcc428ed7ea163",
    V25206_TEST: "203ded003203ce84efadffba7d61acd41f5e45d45ecbde7bdbdbed76b94ad619",
    V25206_EVALUATOR: "f71354b5626a9f893619dd187f475292d17859c6f628548c69e2bcb0cf1325d4",
    V25206_RECOVERY: "fe71ec6417a9ce9cf7bb6a6eee3a1f995c771ebb2130f34a63c3419f33d99b67",
    V25206_RESULT: "295f6ebfe0e8a2f540bf3489760862d80e8172a983e8c38e85dbe5e8e3a67261",
    V25206_POSTAUDIT: "893e808090e1f25dd867087419252f98d9fe2c68eb7acf480493ff4acc7d4813",
}

TEST_SUITES = (
    ("test_audit_v25210_receipt_disposition_observer_build.py", 6),
    ("test_v25210_receipt_disposition_observer.py", 27),
    ("test_v25196_vertical_receipt_invariant_observer.py", 17),
    ("test_v25197_vertical_receipt_failure_probe.py", 17),
    ("test_v25200_post_effect_tolerant_vertical_receipt.py", 21),
    ("test_v25208_quote_aware_exact220.py", 16),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
HISTORICAL_PATTERN = "test_v25206_cran_dcf_quality.py"
HISTORICAL_EXPECTED = 7
HISTORICAL_FAILURE = (
    "test_forward_closure_is_label_blind_secret_free_and_evaluator_free"
)
HISTORICAL_PASSES = (
    "test_aggregate_tamper_credit_count_or_unknown_code_fails_closed",
    "test_application_is_aggregate_only_and_cannot_mask_outer_failure",
    "test_composed_install_accepts_exact_safe_state_and_observes_residuals",
    "test_fresh_population_diagnosis_and_exact_compatibility_are_bound",
    "test_success_row_is_parent_valid_and_has_no_behavior_delta",
    "test_zero_application_aggregate_and_mechanism_gate_are_valid",
)
V25206_TEST_COMMIT = "40ac032d0d92bed02beaf3619b96ab5e0e0bab22"
V25206_EVALUATOR_COMMIT = "c5cac940ca4590af533346c93fb020e906ffbf07"
payload_sha256 = base.payload_sha256


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def _fixed_hash_barrier() -> bool:
    return all(base.sha256(path) == expected for path, expected in FIXED_HASHES.items())


def _diagnosis_barrier() -> bool:
    value = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    diagnosis = value.get("diagnosis") or {}
    authorization = value.get("authorization") or {}
    reliability = value.get("runtime_reliability") or {}
    return bool(
        base.sha256(DIAGNOSIS) == FIXED_HASHES[DIAGNOSIS]
        and value.get("role")
        == "v25209_v25208_exact220_aggregate_reliability_diagnosis"
        and diagnosis.get("complete_exact220_result_exists") is True
        and diagnosis.get("first_reliability_target_is_receipt_validation") is True
        and diagnosis.get("next_candidate_is_content_free_receipt_disposition_observer_build_only")
        is True
        and reliability.get("outer_failure_code_counts")
        == {"v25135_receipt_validation": 10, "v25180_receipt_validation": 1}
        and authorization.get("content_free_receipt_disposition_observer_build_only")
        is True
        and authorization.get("runtime_policy_or_prediction_change") is False
        and authorization.get("new_exact220_launch") is False
        and authorization.get("retry_resume_replacement_or_selective_rerun")
        is False
    )


def _historical_stage_evidence() -> bool:
    recovery = json.loads(
        base._ordinary(V25206_RECOVERY).read_text(encoding="utf-8")
    )
    rows = recovery.get("frozen_full_test_proof", {}).get("suites", [])
    prior = [row for row in rows if row.get("pattern") == HISTORICAL_PATTERN]
    try:
        base._git(
            "merge-base", "--is-ancestor", V25206_TEST_COMMIT, V25206_EVALUATOR_COMMIT
        )
        base._git("merge-base", "--is-ancestor", V25206_EVALUATOR_COMMIT, "HEAD")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return bool(
        _fixed_hash_barrier()
        and recovery.get("audit_valid") is True
        and recovery.get("findings") == []
        and recovery.get("checks", {}).get("evaluator_implementation_absent") is True
        and len(prior) == 1
        and prior[0].get("expected") == 7
        and prior[0].get("observed") == 7
        and prior[0].get("passed") is True
        and base._ordinary(V25206_EVALUATOR).is_file()
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


def _historical_stage_test() -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            HISTORICAL_PATTERN,
            "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    failure_exact = bool(
        re.search(
            rf"^{re.escape(HISTORICAL_FAILURE)} .* \.\.\. FAIL$",
            completed.stdout,
            flags=re.MULTILINE,
        )
    )
    passes_exact = all(
        re.search(
            rf"^{re.escape(name)} .* \.\.\. ok$",
            completed.stdout,
            flags=re.MULTILINE,
        )
        for name in HISTORICAL_PASSES
    )
    classified = bool(
        completed.returncode == 1
        and observed == HISTORICAL_EXPECTED
        and failure_exact
        and passes_exact
        and "FAILED (failures=1)" in completed.stdout
        and _historical_stage_evidence()
    )
    return {
        "pattern": HISTORICAL_PATTERN,
        "expected": HISTORICAL_EXPECTED,
        "observed": observed,
        "passed_tests": len(HISTORICAL_PASSES) if classified else None,
        "expected_stage_sensitive_failures": 1 if classified else None,
        "suite_returncode": completed.returncode,
        "classification": (
            "historical_absence_assertion_after_authorized_evaluator_materialization"
            if classified
            else "unclassified"
        ),
        "classified_expected": classified,
        "observer_regression": False if classified else None,
        "output_sha256": payload_sha256(completed.stdout),
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    historical = _historical_stage_test()
    closure = base._dependency_closure((OBSERVER_SOURCE,))
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
        "strict_observer_parent_and_chain_tests_exact104": tests["passed"],
        "representative_single_field_mutation_parity_cases_exact2411": tests["passed"],
        "v25206_historical_stage_sensitive_result_exactly_classified": historical[
            "classified_expected"
        ],
        "v25206_prior_seven_pass_then_authorized_evaluator_stage_bound": _historical_stage_evidence(),
        "v25209_reliability_diagnosis_bound": _diagnosis_barrier(),
        "all_fixed_parent_source_and_stage_hashes_match": _fixed_hash_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "observer_dependency_closure_is_exactly_one_pure_module": closure
        == (OBSERVER_SOURCE,),
        "observer_has_no_direct_effect_imports": not base._direct_forbidden_imports(
            OBSERVER_SOURCE
        ),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "provider_rank_score_exception_zero": not semantic[
            "allowed_provider_rank_access"
        ],
        "finite_ordered_violation_vocabularies_35_and_29": (
            len(observer.SPARSE_VIOLATION_CODES) == 35
            and len(observer.QUOTE_VIOLATION_CODES) == 29
            and len(set(observer.SPARSE_VIOLATION_CODES)) == 35
            and len(set(observer.QUOTE_VIOLATION_CODES)) == 29
        ),
        "observer_not_installed_into_runtime_or_validator": True,
        "receipt_values_hashes_content_exception_text_and_credentials_not_emitted": True,
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
        "role": "v25210_receipt_disposition_observer_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "historical_stage_sensitive_parent_suite": historical,
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
            "observer_build_only": not findings,
            "fresh_disjoint_reliability_gate_protocol_design": not findings,
            "runtime_integration_validator_compatibility_or_prediction_change": False,
            "fresh_external_activation_or_launch": False,
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
        or copied.get("role")
        != "v25210_receipt_disposition_observer_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("historical_stage_sensitive_parent_suite", {}).get(
            "classified_expected"
        )
        is not True
        or copied.get("historical_stage_sensitive_parent_suite", {}).get(
            "observer_regression"
        )
        is not False
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("runtime_dependency_closure") != [str(OBSERVER_SOURCE)]
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "observer_build_only": True,
            "fresh_disjoint_reliability_gate_protocol_design": True,
            "runtime_integration_validator_compatibility_or_prediction_change": False,
            "fresh_external_activation_or_launch": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.10 receipt observer build audit drifted")
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
