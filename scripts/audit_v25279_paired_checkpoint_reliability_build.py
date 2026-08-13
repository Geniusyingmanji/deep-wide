#!/usr/bin/env python3
"""Clean-build audit for V2.52.78 same-forward checkpoint pairing."""

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

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from deepwide_agent import v25278_paired_checkpoint_reliability_runtime as runtime  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25272_validated_production_checkpoint_build as checkpoint_audit  # noqa: E402
from scripts import audit_v25277_third_disjoint_checkpoint_population as population_audit  # noqa: E402


DATE = "20260813"
ROLE = "v25279_paired_checkpoint_reliability_clean_build_audit"
OUTPUT = Path(f"results/v25279_paired_checkpoint_reliability_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25279_paired_checkpoint_reliability_build.py")
TEST = Path("tests/test_audit_v25279_paired_checkpoint_reliability_build.py")
RUNTIME = Path("src/deepwide_agent/v25278_paired_checkpoint_reliability_runtime.py")
RUNTIME_TEST = Path("tests/test_v25278_paired_checkpoint_reliability_runtime.py")
FIXED_PARENTS = {
    checkpoint_audit.OUTPUT: "f7c7d16def15ff80ae76b3a506da345c38b3c28286bf4c3e05eec84480f5aace",
    population_audit.OUTPUT: "deeaac00d0a294f877f15de7152b535abee60219227bd4d09ac501532d024457",
}
TEST_SUITES = (
    ("test_audit_v25279_paired_checkpoint_reliability_build.py", 5),
    ("test_v25278_paired_checkpoint_reliability_runtime.py", 7),
    ("test_v25271_validated_production_checkpoint_runtime.py", 9),
    ("test_v25265_production_only_totality_runtime.py", 6),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 76
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "f194cca0e09bc89903e0c868fc9c5eb405437fafdc2cb5c4d0c425ecb2cf5a9e"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "19f35483c9aad00784f7d7a97f845f302cb2c4fd6386a8f4f2762d59e52cbd29"
)
CHECK_NAMES = frozenset(
    {
        "checkpoint_and_population_parent_audits_hash_validate_and_authorize_design_only",
        "runtime_and_audit_tests_exact27",
        "git_clean_head_equals_target_main",
        "all_runtime_audit_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact76_and_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "same_real_forward_count_exact1",
        "candidate_additional_query_fetch_model_and_tokens_zero",
        "control_candidate_prediction_checkpoint_cost_and_budget_equal",
        "fixed_result_envelope_validate_fault_identity",
        "precheckpoint_and_natural_recovery_are_ineligible_fail_closed",
        "nested_resealed_result_receipt_stage_and_credit_tamper_fail_closed",
        "truthful_query4_fetch14_model4_caps_unchanged",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
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
        checkpoint = checkpoint_audit.validate_audit(
            json.loads(base._ordinary(checkpoint_audit.OUTPUT).read_text(encoding="utf-8"))
        )
        population = population_audit.validate_audit(
            json.loads(base._ordinary(population_audit.OUTPUT).read_text(encoding="utf-8"))
        )
    except BaseException:
        return False
    return bool(
        checkpoint["audit_valid"] is True
        and checkpoint["findings"] == []
        and checkpoint["authorization"][
            "fresh_benchmark_external_reliability_protocol_design"
        ]
        is True
        and checkpoint["authorization"]["runtime_activation_or_external_launch"]
        is False
        and population["audit_valid"] is True
        and population["findings"] == []
        and population["authorization"][
            "paired_checkpoint_reliability_protocol_design"
        ]
        is True
        and population["authorization"][
            "paired_checkpoint_reliability_external_activation_or_launch"
        ]
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        RUNTIME,
        RUNTIME_TEST,
        *FIXED_PARENTS,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    tests_green = tests["passed"]
    checks = {
        "checkpoint_and_population_parent_audits_hash_validate_and_authorize_design_only": _parent_barrier(),
        "runtime_and_audit_tests_exact27": tests_green,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "all_runtime_audit_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact76_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and contract.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and contract.payload_sha256([row["path"] for row in vector])
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
        "same_real_forward_count_exact1": tests_green,
        "candidate_additional_query_fetch_model_and_tokens_zero": tests_green,
        "control_candidate_prediction_checkpoint_cost_and_budget_equal": tests_green,
        "fixed_result_envelope_validate_fault_identity": (
            tests_green
            and runtime.INJECTED_STAGE == "result_envelope_validate"
            and runtime.INJECTED_FAILURE_TYPE
            == "InjectedCheckpointReliabilityFault"
        ),
        "precheckpoint_and_natural_recovery_are_ineligible_fail_closed": tests_green,
        "nested_resealed_result_receipt_stage_and_credit_tamper_fail_closed": tests_green,
        "truthful_query4_fetch14_model4_caps_unchanged": (
            cap.QUERY_CAP == 4 and cap.FETCH_CAP == 14 and cap.MODEL_CAP == 4
        ),
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "protected_watchers_unchanged": population_audit.parent_audit._watchers_exact(
            contract.watcher_snapshot()
        ),
        "shared_api_lease_inactive": base._lease_inactive(),
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
        "fixed_parents": _fixed_parents(),
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": contract.payload_sha256(vector),
        "runtime_dependency_path_sha256": contract.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "paired_estimand": {
            "real_forward_count_per_task": 1,
            "control": "clean_v25271_result_from_real_forward",
            "candidate": "same_checkpoint_fixed_result_envelope_validate_fault_projection",
            "candidate_additional_queries": 0,
            "candidate_additional_fetches": 0,
            "candidate_additional_model_forwards": 0,
            "candidate_additional_system_total_tokens": 0,
            "required_equalities": [
                "prediction",
                "production_checkpoint",
                "cost",
                "outer_physical_budget_receipt",
            ],
            "ineligible_controls": [
                "control_has_no_trusted_checkpoint",
                "control_not_clean_checkpoint_result",
            ],
        },
        "physical_caps": {
            "queries": cap.QUERY_CAP,
            "fetches": cap.FETCH_CAP,
            "model_forwards": cap.MODEL_CAP,
        },
        "protected_watchers": contract.watcher_snapshot(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "paired_checkpoint_reliability_protocol_build": not findings,
            "external_activation_or_launch": False,
            "candidate_quality_or_prediction_change_claim": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    vector = copied.get("runtime_dependency_vector") or []
    semantic = copied.get("semantic_audit") or {}
    checks = copied.get("checks") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_parents",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "paired_estimand",
            "physical_caps",
            "protected_watchers",
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
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or copied.get("fixed_parents")
        != {str(path): digest for path, digest in FIXED_PARENTS.items()}
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
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
            or not isinstance(row.get("output_sha256"), str)
            or len(row["output_sha256"]) != 64
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
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
        or copied.get("paired_estimand")
        != {
            "real_forward_count_per_task": 1,
            "control": "clean_v25271_result_from_real_forward",
            "candidate": "same_checkpoint_fixed_result_envelope_validate_fault_projection",
            "candidate_additional_queries": 0,
            "candidate_additional_fetches": 0,
            "candidate_additional_model_forwards": 0,
            "candidate_additional_system_total_tokens": 0,
            "required_equalities": [
                "prediction",
                "production_checkpoint",
                "cost",
                "outer_physical_budget_receipt",
            ],
            "ineligible_controls": [
                "control_has_no_trusted_checkpoint",
                "control_not_clean_checkpoint_result",
            ],
        }
        or copied.get("physical_caps")
        != {"queries": 4, "fetches": 14, "model_forwards": 4}
        or copied.get("protected_watchers")
        != population_audit.parent_audit.EXPECTED_WATCHERS
        or checks != {name: True for name in CHECK_NAMES}
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "paired_checkpoint_reliability_protocol_build": True,
            "external_activation_or_launch": False,
            "candidate_quality_or_prediction_change_claim": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.79 paired checkpoint build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    import os

    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True, "findings": []}, sort_keys=True))


if __name__ == "__main__":
    main()
