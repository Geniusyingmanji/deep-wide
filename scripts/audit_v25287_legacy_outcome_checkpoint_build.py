#!/usr/bin/env python3
"""Clean-build audit for the V2.52.86 legacy-outcome checkpoint seam."""

from __future__ import annotations

import copy
import hashlib
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

from deepwide_agent import v24635_exact220_contract as frozen_contract  # noqa: E402
from deepwide_agent import v24857_pacing_aware_exact220_contract as legacy_contract  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from deepwide_agent import v25280_paired_checkpoint_reliability_external_contract as reliability_contract  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25283_paired_checkpoint_reliability_forward as reliability_audit  # noqa: E402
from scripts import audit_v25285_natural_checkpoint_quality_build as quality_audit  # noqa: E402


DATE = "20260813"
ROLE = "v25287_legacy_outcome_checkpoint_clean_build_audit"
OUTPUT = Path(f"results/v25287_legacy_outcome_checkpoint_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25287_legacy_outcome_checkpoint_build.py")
TEST = Path("tests/test_audit_v25287_legacy_outcome_checkpoint_build.py")
RUNTIME = Path("src/deepwide_agent/v25286_legacy_outcome_checkpoint.py")
RUNTIME_TEST = Path("tests/test_v25286_legacy_outcome_checkpoint.py")
HISTORICAL_TEST = "test_v24857_pacing_aware_exact220.py"
HISTORICAL_TEST_COUNT = 13
HISTORICAL_OK_COUNT = 12
HISTORICAL_ERROR_TEST = "test_visible_vector_is_exact220_and_label_blind"
HISTORICAL_ERROR = (
    "RuntimeError: V2.46.35 frozen dependency drifted: "
    "src/deepwide_agent/native_search.py"
)
FROZEN_NATIVE_SEARCH_SHA256 = (
    "cd0d6bfccf4b345b11274558bdcffb39d279697d183242baf811dfd56ac71e50"
)
CURRENT_NATIVE_SEARCH_SHA256 = (
    "685f54137e4584832bb1df41226805997ea57220837d1db497a79509f9f91a51"
)
NATIVE_SEARCH = Path("src/deepwide_agent/native_search.py")
NATIVE_SEARCH_CHANGE_COMMIT = "795d38216b47e29dd7d03624ad392cefd6e3d2d8"
V25286_COMMIT = "10ae6f835713eaae8f424eea0f962946a1b0acee"
V25286_COMMIT_PATHS = [str(RUNTIME), str(RUNTIME_TEST)]
FIXED_PARENTS = {
    reliability_contract.FORWARD_AUDIT: (
        "8c1bd6cd12e32be50ae9e9dbb1706ebb145fda699c392b26ee0e656d8f13bc2a"
    ),
    quality_audit.OUTPUT: (
        "3341a6e5680bbdc8dc54cdd4fa5438ce7b0b685efc5409b73cd77943684609ea"
    ),
}
DIRECT_TEST_SUITES = (
    ("test_audit_v25287_legacy_outcome_checkpoint_build.py", 6),
    ("test_v25286_legacy_outcome_checkpoint.py", 6),
    ("test_v24856_pacing_aware_admission.py", 7),
    ("test_v24630_exact220.py", 5),
    ("test_v24319_runner_integration.py", 7),
)
EXPECTED_DIRECT_TESTS = sum(expected for _pattern, expected in DIRECT_TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 33
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "c647b7eb6b058c5fe62d95b7c101ca8c2f70e81c9f6f5ff15de583c102ae17a4"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "8c39d5bec4e02f99fd4baacfb3169da60ff4e1ea52055c91302ba6d22c105f23"
)
EXPECTED_RUNTIME_SHA256 = (
    "60191055ea4ac0baa7579ecb80488149556b01519c0f781c18713e93daf43e99"
)
EXPECTED_RUNTIME_TEST_SHA256 = (
    "bf5c7ada069f14cdcf3aecea4356e26e62771ab5ed08c54a4954a6b905e73f42"
)
EXPECTED_WATCHERS = {
    "795336": 713986317,
    "2808901": 746680268,
    "2889939": 746969965,
    "3061652": 747569004,
}
CHECK_NAMES = frozenset(
    {
        "fixed_parent_audits_valid_and_design_only",
        "v25286_commit_is_exact_and_ancestor_of_clean_head",
        "direct_runtime_and_auditor_tests_exact31_green",
        "historical_v24857_suite_is_exactly_12_green_plus_one_registered_drift",
        "historical_native_search_drift_predates_and_is_not_touched_by_v25286",
        "historical_drift_is_not_misreported_as_current_green",
        "all_runtime_auditor_test_parent_and_closure_files_tracked",
        "runtime_and_test_hashes_exact",
        "runtime_dependency_vector_exact33_and_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "clean_path_is_byte_identical_to_legacy_envelope",
        "postcheckpoint_build_or_validate_failure_recovers_same_outcome",
        "checkpoint_receipt_and_recovery_resealed_tamper_fail_closed",
        "nested_failure_stage_and_type_are_exactly_bound",
        "precheckpoint_untrusted_outcome_fails_closed",
        "additional_query_fetch_model_token_and_signed_credit_zero",
        "legacy_query4_fetch10_model3_and_concurrency_unchanged",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "git_clean_head_equals_target_main",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


def _direct_tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in DIRECT_TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_DIRECT_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_DIRECT_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _test_environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def _historical_contract_test() -> dict[str, Any]:
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
            HISTORICAL_TEST,
            "-v",
        ],
        cwd=ROOT,
        env=_test_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
        check=False,
    )
    output = completed.stdout
    match = re.search(r"Ran (\d+) tests?", output)
    observed = int(match.group(1)) if match else 0
    ok_count = len(re.findall(r"\.\.\. ok$", output, flags=re.MULTILINE))
    status_error_count = len(
        re.findall(r"\.\.\. ERROR$", output, flags=re.MULTILINE)
    )
    traceback_error_count = len(
        re.findall(r"^ERROR: ", output, flags=re.MULTILINE)
    )
    exact_registered_shape = bool(
        completed.returncode == 1
        and observed == HISTORICAL_TEST_COUNT
        and ok_count == HISTORICAL_OK_COUNT
        and status_error_count == 1
        and traceback_error_count == 1
        and "FAILED (errors=1)" in output
        and "FAILED (failures=" not in output
        and HISTORICAL_ERROR_TEST in output
        and HISTORICAL_ERROR in output
        and "v25286_legacy_outcome_checkpoint" not in output
        and base.SECRET.search(output) is None
    )
    return {
        "pattern": HISTORICAL_TEST,
        "expected": HISTORICAL_TEST_COUNT,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": False,
        "ok_count": ok_count,
        "failure_count": 0,
        "error_count": status_error_count,
        "traceback_error_count": traceback_error_count,
        "only_nonpassing_test": HISTORICAL_ERROR_TEST,
        "only_nonpassing_error": HISTORICAL_ERROR,
        "exact_registered_shape": exact_registered_shape,
        "classified_as_current_green": False,
        "output_contains_credential_literal": base.SECRET.search(output) is not None,
        "output_sha256": base.payload_sha256(output),
    }


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(sorted(base._dependency_closure((RUNTIME,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _fixed_parents() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_PARENTS}


def _parent_barrier() -> bool:
    if _fixed_parents() != {str(path): digest for path, digest in FIXED_PARENTS.items()}:
        return False
    try:
        reliability = reliability_audit.validate_audit(
            json.loads(
                base._ordinary(reliability_contract.FORWARD_AUDIT).read_text(
                    encoding="utf-8"
                )
            )
        )
        quality = quality_audit.validate_audit(
            json.loads(base._ordinary(quality_audit.OUTPUT).read_text(encoding="utf-8"))
        )
    except BaseException:
        return False
    return bool(
        reliability["audit_valid"] is True
        and reliability["findings"] == []
        and reliability["reliability_decision"]["reliability_gate_passed"] is True
        and reliability["authorization"][
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"
        ]
        is False
        and quality["audit_valid"] is True
        and quality["findings"] == []
        and quality["authorization"][
            "fresh_disjoint_natural_checkpoint_quality_population_and_protocol_design"
        ]
        is True
        and quality["authorization"]["external_activation_or_launch"] is False
        and quality["authorization"][
            "deepwidebench_dev64_exact220_forward_or_evaluator"
        ]
        is False
    )


def _git_blob_sha256(revision: str, relative: Path) -> str:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def _changed_paths(commit: str) -> list[str]:
    output = base._git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", commit
    )
    return sorted(line for line in output.splitlines() if line)


def _is_ancestor(older: str, newer: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", older, newer],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _historical_drift(head: str) -> dict[str, Any]:
    parent_revision = NATIVE_SEARCH_CHANGE_COMMIT + "^"
    paths = _changed_paths(V25286_COMMIT)
    return {
        "frozen_contract": str(frozen_contract.FORWARD_CONTRACT),
        "dependency_path": str(NATIVE_SEARCH),
        "frozen_expected_sha256": FROZEN_NATIVE_SEARCH_SHA256,
        "current_sha256": base.sha256(NATIVE_SEARCH),
        "modifying_commit": NATIVE_SEARCH_CHANGE_COMMIT,
        "modifying_commit_parent_blob_sha256": _git_blob_sha256(
            parent_revision, NATIVE_SEARCH
        ),
        "modifying_commit_blob_sha256": _git_blob_sha256(
            NATIVE_SEARCH_CHANGE_COMMIT, NATIVE_SEARCH
        ),
        "v25286_commit": V25286_COMMIT,
        "v25286_commit_paths": paths,
        "modifying_commit_predates_v25286": _is_ancestor(
            NATIVE_SEARCH_CHANGE_COMMIT, V25286_COMMIT
        ),
        "v25286_predates_audit_head": _is_ancestor(V25286_COMMIT, head),
        "v25286_commit_touches_dependency": str(NATIVE_SEARCH) in paths,
        "classification": (
            "historical_protocol_closure_drift_not_v25286_behavior_regression"
        ),
        "historical_contract_live_validation_green": False,
        "current_runtime_dependency_semantically_audited_separately": True,
    }


def _historical_drift_exact(value: Mapping[str, Any]) -> bool:
    return bool(
        value.get("frozen_contract") == str(frozen_contract.FORWARD_CONTRACT)
        and value.get("dependency_path") == str(NATIVE_SEARCH)
        and value.get("frozen_expected_sha256") == FROZEN_NATIVE_SEARCH_SHA256
        and value.get("current_sha256") == CURRENT_NATIVE_SEARCH_SHA256
        and value.get("modifying_commit") == NATIVE_SEARCH_CHANGE_COMMIT
        and value.get("modifying_commit_parent_blob_sha256")
        == FROZEN_NATIVE_SEARCH_SHA256
        and value.get("modifying_commit_blob_sha256")
        == CURRENT_NATIVE_SEARCH_SHA256
        and value.get("v25286_commit") == V25286_COMMIT
        and value.get("v25286_commit_paths") == sorted(V25286_COMMIT_PATHS)
        and value.get("modifying_commit_predates_v25286") is True
        and value.get("v25286_predates_audit_head") is True
        and value.get("v25286_commit_touches_dependency") is False
        and value.get("classification")
        == "historical_protocol_closure_drift_not_v25286_behavior_regression"
        and value.get("historical_contract_live_validation_green") is False
        and value.get("current_runtime_dependency_semantically_audited_separately")
        is True
    )


def _historical_test_exact(value: Mapping[str, Any]) -> bool:
    return bool(
        set(value)
        == {
            "pattern",
            "expected",
            "observed",
            "returncode",
            "passed",
            "ok_count",
            "failure_count",
            "error_count",
            "traceback_error_count",
            "only_nonpassing_test",
            "only_nonpassing_error",
            "exact_registered_shape",
            "classified_as_current_green",
            "output_contains_credential_literal",
            "output_sha256",
        }
        and value.get("pattern") == HISTORICAL_TEST
        and value.get("expected") == HISTORICAL_TEST_COUNT
        and value.get("observed") == HISTORICAL_TEST_COUNT
        and value.get("returncode") == 1
        and value.get("passed") is False
        and value.get("ok_count") == HISTORICAL_OK_COUNT
        and value.get("failure_count") == 0
        and value.get("error_count") == 1
        and value.get("traceback_error_count") == 1
        and value.get("only_nonpassing_test") == HISTORICAL_ERROR_TEST
        and value.get("only_nonpassing_error") == HISTORICAL_ERROR
        and value.get("exact_registered_shape") is True
        and value.get("classified_as_current_green") is False
        and value.get("output_contains_credential_literal") is False
        and isinstance(value.get("output_sha256"), str)
        and len(value["output_sha256"]) == 64
    )


def _source_invariants() -> bool:
    source = base._ordinary(RUNTIME).read_text(encoding="utf-8")
    checkpoint = source.find("checkpoint = build_checkpoint(outcome)")
    legacy_build = source.find("parent.build_envelope(outcome, arm=ARM)")
    return bool(
        checkpoint >= 0
        and legacy_build > checkpoint
        and source.count("parent.build_envelope(outcome, arm=ARM)") == 1
        and source.count("parent.validate_envelope(envelope)") == 1
        and "run_v24630_task(" not in source
    )


def _watchers_exact(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != set(EXPECTED_WATCHERS):
        return False
    return all(
        isinstance(value.get(pid), Mapping)
        and set(value[pid])
        == {"present", "start_ticks", "matches_frozen_identity"}
        and value[pid].get("present") is True
        and value[pid].get("start_ticks") == start
        and value[pid].get("matches_frozen_identity") is True
        for pid, start in EXPECTED_WATCHERS.items()
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    direct_tests = _direct_tests()
    historical_test = _historical_contract_test()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    historical_drift = _historical_drift(head)
    explicit = {SOURCE, TEST, RUNTIME, RUNTIME_TEST, *FIXED_PARENTS, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    direct_green = direct_tests["passed"]
    historical_exact = _historical_test_exact(historical_test)
    drift_exact = _historical_drift_exact(historical_drift)
    legacy_caps_exact = bool(
        legacy_contract.EXECUTOR_CONCURRENCY == 20
        and legacy_contract.MODEL_SLOT_CAP == 8
        and legacy_contract.TAVILY_KEY_SLOT_CAP == 12
        and legacy_contract.LIMITS["search_queries"] == 4
        and legacy_contract.LIMITS["fetch_targets"] == 10
        and legacy_contract.LIMITS["model_calls"] == 3
    )
    checks = {
        "fixed_parent_audits_valid_and_design_only": _parent_barrier(),
        "v25286_commit_is_exact_and_ancestor_of_clean_head": (
            _changed_paths(V25286_COMMIT) == sorted(V25286_COMMIT_PATHS)
            and _is_ancestor(V25286_COMMIT, head)
        ),
        "direct_runtime_and_auditor_tests_exact31_green": direct_green,
        "historical_v24857_suite_is_exactly_12_green_plus_one_registered_drift": historical_exact,
        "historical_native_search_drift_predates_and_is_not_touched_by_v25286": drift_exact,
        "historical_drift_is_not_misreported_as_current_green": historical_exact
        and historical_test["classified_as_current_green"] is False,
        "all_runtime_auditor_test_parent_and_closure_files_tracked": not untracked,
        "runtime_and_test_hashes_exact": (
            base.sha256(RUNTIME) == EXPECTED_RUNTIME_SHA256
            and base.sha256(RUNTIME_TEST) == EXPECTED_RUNTIME_TEST_SHA256
        ),
        "runtime_dependency_vector_exact33_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and seal.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and seal.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "clean_path_is_byte_identical_to_legacy_envelope": direct_green
        and _source_invariants(),
        "postcheckpoint_build_or_validate_failure_recovers_same_outcome": direct_green
        and _source_invariants(),
        "checkpoint_receipt_and_recovery_resealed_tamper_fail_closed": direct_green,
        "nested_failure_stage_and_type_are_exactly_bound": direct_green,
        "precheckpoint_untrusted_outcome_fails_closed": direct_green,
        "additional_query_fetch_model_token_and_signed_credit_zero": direct_green,
        "legacy_query4_fetch10_model3_and_concurrency_unchanged": legacy_caps_exact,
        "protected_watchers_unchanged": _watchers_exact(base._watchers()),
        "shared_api_lease_inactive": base._lease_inactive(),
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
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
            "v25286_commit": V25286_COMMIT,
        },
        "fixed_parents": _fixed_parents(),
        "direct_tests": direct_tests,
        "historical_contract_test": historical_test,
        "historical_dependency_drift": historical_drift,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": seal.payload_sha256(vector),
        "runtime_dependency_path_sha256": seal.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "checkpoint_behavior": {
            "input": "validated_IntegratedExact220TaskOutcome",
            "checkpoint_position": "after_parent_cross_artifact_validation_before_legacy_envelope",
            "clean_path": "byte_identical_legacy_envelope",
            "recoverable_stages": [
                "legacy_envelope_build",
                "legacy_envelope_validate",
            ],
            "precheckpoint_failure": "fail_closed",
            "recovery_prediction_cost_and_parent_receipts": "same_checkpoint",
            "additional_queries": 0,
            "additional_fetches": 0,
            "additional_model_forwards": 0,
            "additional_system_total_tokens": 0,
            "positive_signed_credit_count": 0,
        },
        "future_protocol_requirements": {
            "fresh_benchmark_external_population": True,
            "disjoint_from_all_prior_checkpoint_populations": True,
            "shared_single_legacy_outcome_per_task": True,
            "control": "ordinary_legacy_envelope_or_visible_failure_as_zero",
            "candidate": "same_outcome_with_v25286_checkpoint_totality",
            "fault_injection_for_quality_gain": False,
            "runtime_keys": ["opaque_id", "question"],
            "fixed_denominator_failure_as_zero": True,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "normal_path_prediction_cost_effect_and_receipts_byte_equal": True,
            "quality_go": {
                "natural_postcheckpoint_recovery_nonzero": True,
                "candidate_exact_strictly_greater": True,
                "entity_row_item_column_composite_nonregression": True,
                "fallback_outer_failure_evaluator_invalid_nonincrease": True,
            },
            "zero_natural_recovery_is_mechanism_no_go": True,
            "direct_public_220_after_build": False,
        },
        "legacy_execution_envelope": {
            "executor_concurrency": legacy_contract.EXECUTOR_CONCURRENCY,
            "model_slots": legacy_contract.MODEL_SLOT_CAP,
            "search_slots": legacy_contract.TAVILY_KEY_SLOT_CAP,
            "queries_per_task": legacy_contract.LIMITS["search_queries"],
            "fetches_per_task": legacy_contract.LIMITS["fetch_targets"],
            "model_forwards_per_task": legacy_contract.LIMITS["model_calls"],
        },
        "protected_watchers": base._watchers(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read_for_runtime_routing": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_legacy_checkpoint_quality_population_and_protocol_design": not findings,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "candidate_quality_or_prediction_improvement_claim": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = seal.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    direct = copied.get("direct_tests") or {}
    suites = direct.get("suites") or []
    historical_test = copied.get("historical_contract_test") or {}
    drift = copied.get("historical_dependency_drift") or {}
    vector = copied.get("runtime_dependency_vector") or []
    semantic = copied.get("semantic_audit") or {}
    checks = copied.get("checks") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_parents",
            "direct_tests",
            "historical_contract_test",
            "historical_dependency_drift",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "checkpoint_behavior",
            "future_protocol_requirements",
            "legacy_execution_envelope",
            "protected_watchers",
            "checks",
            "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read_for_runtime_routing",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or set(git) != {"head", "target_main", "equal", "clean", "v25286_commit"}
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or git.get("v25286_commit") != V25286_COMMIT
        or copied.get("fixed_parents")
        != {str(path): digest for path, digest in FIXED_PARENTS.items()}
        or set(direct) != {"expected", "observed", "passed", "suites"}
        or direct.get("expected") != EXPECTED_DIRECT_TESTS
        or direct.get("observed") != EXPECTED_DIRECT_TESTS
        or direct.get("passed") is not True
        or len(suites) != len(DIRECT_TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or set(row)
            != {
                "pattern",
                "expected",
                "observed",
                "returncode",
                "passed",
                "output_sha256",
            }
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            for row, (pattern, expected) in zip(
                suites, DIRECT_TEST_SUITES, strict=True
            )
        )
        or not _historical_test_exact(historical_test)
        or not _historical_drift_exact(drift)
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or any(
            not isinstance(row, Mapping)
            or set(row) != {"path", "sha256"}
            or not isinstance(row.get("path"), str)
            or not isinstance(row.get("sha256"), str)
            or len(row["sha256"]) != 64
            for row in vector
        )
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or semantic
        != {
            "privileged_runtime_field_accesses": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
            "allowed_provider_rank_access": [
                "src/deepwide_agent/clients.py:565:score"
            ],
            "untracked_sources": [],
        }
        or copied.get("checkpoint_behavior")
        != {
            "input": "validated_IntegratedExact220TaskOutcome",
            "checkpoint_position": "after_parent_cross_artifact_validation_before_legacy_envelope",
            "clean_path": "byte_identical_legacy_envelope",
            "recoverable_stages": [
                "legacy_envelope_build",
                "legacy_envelope_validate",
            ],
            "precheckpoint_failure": "fail_closed",
            "recovery_prediction_cost_and_parent_receipts": "same_checkpoint",
            "additional_queries": 0,
            "additional_fetches": 0,
            "additional_model_forwards": 0,
            "additional_system_total_tokens": 0,
            "positive_signed_credit_count": 0,
        }
        or copied.get("future_protocol_requirements")
        != {
            "fresh_benchmark_external_population": True,
            "disjoint_from_all_prior_checkpoint_populations": True,
            "shared_single_legacy_outcome_per_task": True,
            "control": "ordinary_legacy_envelope_or_visible_failure_as_zero",
            "candidate": "same_outcome_with_v25286_checkpoint_totality",
            "fault_injection_for_quality_gain": False,
            "runtime_keys": ["opaque_id", "question"],
            "fixed_denominator_failure_as_zero": True,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "normal_path_prediction_cost_effect_and_receipts_byte_equal": True,
            "quality_go": {
                "natural_postcheckpoint_recovery_nonzero": True,
                "candidate_exact_strictly_greater": True,
                "entity_row_item_column_composite_nonregression": True,
                "fallback_outer_failure_evaluator_invalid_nonincrease": True,
            },
            "zero_natural_recovery_is_mechanism_no_go": True,
            "direct_public_220_after_build": False,
        }
        or copied.get("legacy_execution_envelope")
        != {
            "executor_concurrency": 20,
            "model_slots": 8,
            "search_slots": 12,
            "queries_per_task": 4,
            "fetches_per_task": 10,
            "model_forwards_per_task": 3,
        }
        or not _watchers_exact(copied.get("protected_watchers"))
        or checks != {name: True for name in CHECK_NAMES}
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read_for_runtime_routing",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or copied.get("authorization")
        != {
            "fresh_disjoint_legacy_checkpoint_quality_population_and_protocol_design": True,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "candidate_quality_or_prediction_improvement_claim": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or signature != seal.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.87 legacy outcome checkpoint build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True}, sort_keys=True))


if __name__ == "__main__":
    main()
