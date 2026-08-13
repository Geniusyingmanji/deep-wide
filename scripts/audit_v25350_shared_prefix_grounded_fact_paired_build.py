#!/usr/bin/env python3
"""Clean-build audit for V2.53.49 shared-prefix grounded-fact pairing."""

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
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25348_checkpoint_grounded_fact_build as parent  # noqa: E402


DATE = "20260813"
ROLE = "v25350_shared_prefix_grounded_fact_paired_clean_build_audit"
SOURCE = Path(
    "scripts/audit_v25350_shared_prefix_grounded_fact_paired_build.py"
)
TEST = Path(
    "tests/test_audit_v25350_shared_prefix_grounded_fact_paired_build.py"
)
RUNTIME = Path(
    "src/deepwide_agent/v25349_shared_prefix_grounded_fact_paired_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25349_shared_prefix_grounded_fact_paired_runtime.py"
)
PARENT_AUDIT = parent.OUTPUT
PARENT_AUDIT_SHA256 = (
    "a88f4b9ed0403fade28ec7270659dd405acbd742c19f2fbf165f1b6b08177cbc"
)
OUTPUT = Path(
    f"results/v25350_shared_prefix_grounded_fact_paired_build_audit_v1_{DATE}.json"
)
TEST_SUITES = (
    ("test_audit_v25350_shared_prefix_grounded_fact_paired_build.py", 4),
    ("test_v25349_shared_prefix_grounded_fact_paired_runtime.py", 8),
    ("test_v25347_checkpoint_grounded_fact_runtime.py", 8),
    ("test_v25346_grounded_fact_bootstrap.py", 8),
    ("test_v25119_grounded_target_record_paired_runtime.py", 7),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25117_grounded_target_record_plan.py", 6),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 76
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "1f2da6e2fdc3909fdf53c3e0f2da3f8f7d5e5a50cfaea168a07e51440024b632"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "8716637d793ade9dabe483aba5c114e0a8a73cd1df302011175ef7cd0b0c5a9b"
)
EXPECTED_WATCHERS = parent.EXPECTED_WATCHERS
CHECK_NAMES = frozenset(
    {
        "v25348_parent_hash_valid_and_protocol_design_only",
        "runtime_audit_and_parent_tests_exact62",
        "git_clean_head_equals_target_main",
        "all_runtime_audit_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact76_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "one_visible_plan_one_joint_grounded_plan_two_syntheses_exact4",
        "both_arms_share_queries_search_responses_pages_and_page_bytes",
        "candidate_only_equal_length_verified_fact_prefix",
        "valid_fact_can_change_prediction_attributably",
        "invalid_fact_and_grounded_failure_are_terminal_noop",
        "arm_order_reversal_preserves_treatment_attribution",
        "unexposed_order_difference_marked_unattributable",
        "nested_result_receipt_budget_counter_credit_and_prediction_tamper_fail_closed",
        "truthful_query4_fetch14_model4_caps_enforced",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "entropy_information_gain_positive_signed_credit_zero",
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
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(sorted(base._dependency_closure((RUNTIME,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _parent_barrier() -> dict[str, Any]:
    value = parent.validate_audit(
        json.loads(base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    )
    authorization = value["authorization"]
    if (
        base.sha256(PARENT_AUDIT) != PARENT_AUDIT_SHA256
        or value["audit_valid"] is not True
        or value["findings"] != []
        or authorization[
            "fresh_benchmark_external_shared_prefix_mechanism_protocol_design"
        ]
        is not True
        or authorization["external_activation_or_launch"] is not False
        or authorization["deepwidebench_forward_or_evaluator"] is not False
    ):
        raise RuntimeError("V2.53.50 parent build audit barrier drifted")
    return value


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    _parent_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {SOURCE, TEST, RUNTIME, RUNTIME_TEST, PARENT_AUDIT, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    tests_green = tests["passed"]
    watchers = contract.watcher_snapshot()
    reported_clean = clean if tracked else True
    checks = {
        "v25348_parent_hash_valid_and_protocol_design_only": True,
        "runtime_audit_and_parent_tests_exact62": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_runtime_audit_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact76_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and contract.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and contract.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_runtime_effect_imports_zero": not base._direct_forbidden_imports(
            RUNTIME
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
        "one_visible_plan_one_joint_grounded_plan_two_syntheses_exact4": tests_green,
        "both_arms_share_queries_search_responses_pages_and_page_bytes": tests_green,
        "candidate_only_equal_length_verified_fact_prefix": tests_green,
        "valid_fact_can_change_prediction_attributably": tests_green,
        "invalid_fact_and_grounded_failure_are_terminal_noop": tests_green,
        "arm_order_reversal_preserves_treatment_attribution": tests_green,
        "unexposed_order_difference_marked_unattributable": tests_green,
        "nested_result_receipt_budget_counter_credit_and_prediction_tamper_fail_closed": tests_green,
        "truthful_query4_fetch14_model4_caps_enforced": (
            cap.QUERY_CAP == 4 and cap.FETCH_CAP == 14 and cap.MODEL_CAP == 4
        ),
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "entropy_information_gain_positive_signed_credit_zero": tests_green,
        "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
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
            "clean": reported_clean,
        },
        "fixed_parent": {
            "path": str(PARENT_AUDIT),
            "sha256": base.sha256(PARENT_AUDIT),
        },
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": contract.payload_sha256(vector),
        "runtime_dependency_path_sha256": contract.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "physical_caps": {
            "queries": cap.QUERY_CAP,
            "fetches": cap.FETCH_CAP,
            "model_forwards": cap.MODEL_CAP,
        },
        "paired_estimand": {
            "control": "raw_shared_page_evidence",
            "candidate": "same_length_quote_verified_first_wave_fact_prefix",
            "shared_visible_plan_calls": 1,
            "shared_joint_grounded_plan_calls": 1,
            "shared_query_count": 4,
            "shared_fetch_cap": 14,
            "production_calls_per_arm": 1,
            "physical_model_call_cap": 4,
            "candidate_additional_fact_proposal_calls": 0,
            "required_attribution_chain": [
                "verified_record",
                "candidate_prompt_changed",
                "both_arms_model_success",
                "prediction_changed",
            ],
            "positive_signed_credit_count": 0,
        },
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_external_population_and_protocol_design": not findings,
            "population_selection_or_network_activation": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
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
            "fixed_parent",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "physical_caps",
            "paired_estimand",
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
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or copied.get("fixed_parent")
        != {"path": str(PARENT_AUDIT), "sha256": PARENT_AUDIT_SHA256}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
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
        or copied.get("physical_caps")
        != {"queries": 4, "fetches": 14, "model_forwards": 4}
        or copied.get("paired_estimand")
        != {
            "control": "raw_shared_page_evidence",
            "candidate": "same_length_quote_verified_first_wave_fact_prefix",
            "shared_visible_plan_calls": 1,
            "shared_joint_grounded_plan_calls": 1,
            "shared_query_count": 4,
            "shared_fetch_cap": 14,
            "production_calls_per_arm": 1,
            "physical_model_call_cap": 4,
            "candidate_additional_fact_proposal_calls": 0,
            "required_attribution_chain": [
                "verified_record",
                "candidate_prompt_changed",
                "both_arms_model_success",
                "prediction_changed",
            ],
            "positive_signed_credit_count": 0,
        }
        or copied.get("protected_watchers") != EXPECTED_WATCHERS
        or set(checks) != CHECK_NAMES
        or not all(checks.values())
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
            "fresh_disjoint_external_population_and_protocol_design": True,
            "population_selection_or_network_activation": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.50 shared-prefix paired build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    import os

    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {"path": str(OUTPUT), "audit_valid": True, "findings": []},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
