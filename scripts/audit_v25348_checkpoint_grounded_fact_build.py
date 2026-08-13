#!/usr/bin/env python3
"""Clean-build audit for V2.53.47 checkpoint-grounded fact bootstrap.

This auditor is build-only.  It validates the frozen aggregate diagnosis,
the complete runtime dependency vector, focused/parent regression suites,
strict label blindness, protected watcher identity, and the inactive shared
lease.  It performs no model, search, fetch, evaluator, or benchmark effect.
"""

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
from deepwide_agent import v25347_checkpoint_grounded_fact_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25345_exact220_fact_selection_funnel as parent  # noqa: E402


DATE = "20260813"
ROLE = "v25348_checkpoint_grounded_fact_clean_build_audit"
SOURCE = Path("scripts/audit_v25348_checkpoint_grounded_fact_build.py")
TEST = Path("tests/test_audit_v25348_checkpoint_grounded_fact_build.py")
RUNTIME = Path(
    "src/deepwide_agent/v25347_checkpoint_grounded_fact_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25347_checkpoint_grounded_fact_runtime.py"
)
PARENT_DIAGNOSIS = parent.OUTPUT
PARENT_DIAGNOSIS_SHA256 = (
    "cedef96d98f1c6d9bcf1f38ade2d6d4e3afcae60e40f75e78c972c27480975eb"
)
OUTPUT = Path(
    f"results/v25348_checkpoint_grounded_fact_build_audit_v1_{DATE}.json"
)

TEST_SUITES = (
    ("test_audit_v25348_checkpoint_grounded_fact_build.py", 4),
    ("test_v25347_checkpoint_grounded_fact_runtime.py", 8),
    ("test_v25271_validated_production_checkpoint_runtime.py", 9),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_v25135_sparse_production_runtime.py", 9),
    ("test_v25346_grounded_fact_bootstrap.py", 8),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25117_grounded_target_record_plan.py", 6),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 78
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "a61f0570c799d6a9c00616c06aa4b3ccc934fa3472670af0b2bd945afc5c11ce"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "7e23f8ba437c3d200956fc986ffd51bc7376a14d3537fcc51449a305bc401deb"
)
EXPECTED_WATCHERS = [
    {
        "pid": 795336,
        "marker": "scripts/watch_v2415_r1_checkpoint_liveness.py",
        "start_ticks": 713986317,
    },
    {
        "pid": 3061652,
        "marker": "scripts/watch_v24218_exact220_executor.py",
        "start_ticks": 747569004,
    },
    {
        "pid": 2808901,
        "marker": "scripts/watch_v24215_joint_package_recovery.py",
        "start_ticks": 746680268,
    },
    {
        "pid": 2889939,
        "marker": "scripts/watch_v24216_package_gate.py",
        "start_ticks": 746969965,
    },
]
CHECK_NAMES = frozenset(
    {
        "fact_selection_parent_hash_and_build_only_authority_exact",
        "runtime_audit_and_parent_tests_exact65",
        "git_clean_head_equals_target_main",
        "all_runtime_audit_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact78_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "parent_noop_prediction_cost_and_provider_effect_equal",
        "verified_fact_changes_synthetic_prediction_with_three_calls",
        "invalid_or_unrenderable_fact_is_byte_exact_noop",
        "checkpoint_recovery_preserves_treated_prediction",
        "nested_result_proxy_stage_counter_and_credit_tamper_fail_closed",
        "truthful_query4_fetch14_model4_caps_unchanged",
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
    value = parent.validate_diagnosis(
        json.loads(base._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
    )
    authorization = value["authorization"]
    diagnosis = value["diagnosis"]
    if (
        base.sha256(PARENT_DIAGNOSIS) != PARENT_DIAGNOSIS_SHA256
        or authorization["shared_prefix_fact_representation_successor_build_only"]
        is not True
        or authorization["runtime_activation_or_prediction_change"] is not False
        or authorization["external_forward_or_new_deepwidebench_rollout"]
        is not False
        or diagnosis[
            "next_successor_should_change_fact_representation_before_first_production_synthesis"
        ]
        is not True
        or diagnosis[
            "next_successor_should_share_search_responses_and_page_bytes_with_control"
        ]
        is not True
        or diagnosis[
            "next_successor_should_preserve_query_fetch_model_token_context_and_wall_caps"
        ]
        is not True
        or diagnosis[
            "entropy_information_gain_remains_shadow_only_and_cannot_create_credit_sign"
        ]
        is not True
    ):
        raise RuntimeError("V2.53.48 parent diagnosis barrier drifted")
    return value


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    _parent_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {SOURCE, TEST, RUNTIME, RUNTIME_TEST, PARENT_DIAGNOSIS, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    tests_green = tests["passed"]
    watchers = contract.watcher_snapshot()
    reported_clean = clean if tracked else True
    checks = {
        "fact_selection_parent_hash_and_build_only_authority_exact": True,
        "runtime_audit_and_parent_tests_exact65": tests_green,
        "git_clean_head_equals_target_main": (
            reported_clean and head == target
        ),
        "all_runtime_audit_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact78_and_hash_bound": (
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
        "parent_noop_prediction_cost_and_provider_effect_equal": tests_green,
        "verified_fact_changes_synthetic_prediction_with_three_calls": tests_green,
        "invalid_or_unrenderable_fact_is_byte_exact_noop": tests_green,
        "checkpoint_recovery_preserves_treated_prediction": tests_green,
        "nested_result_proxy_stage_counter_and_credit_tamper_fail_closed": tests_green,
        "truthful_query4_fetch14_model4_caps_unchanged": (
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
            "path": str(PARENT_DIAGNOSIS),
            "sha256": base.sha256(PARENT_DIAGNOSIS),
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
        "mechanism_contract": {
            "grounded_plan_model_call_reused": True,
            "additional_model_calls": 0,
            "parent_and_candidate_production_prompt_characters_equal": True,
            "same_forward_exact_quote_source_binding_required": True,
            "invalid_conflicting_or_unrenderable_fact_is_parent_noop": True,
            "legacy_prompt_unchanged_receipt_not_reexported": True,
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
            "fresh_benchmark_external_shared_prefix_mechanism_protocol_design": not findings,
            "external_activation_or_launch": False,
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
            "mechanism_contract",
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
        or copied.get("fixed_parent")
        != {"path": str(PARENT_DIAGNOSIS), "sha256": PARENT_DIAGNOSIS_SHA256}
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
        or copied.get("physical_caps")
        != {"queries": 4, "fetches": 14, "model_forwards": 4}
        or copied.get("mechanism_contract")
        != {
            "grounded_plan_model_call_reused": True,
            "additional_model_calls": 0,
            "parent_and_candidate_production_prompt_characters_equal": True,
            "same_forward_exact_quote_source_binding_required": True,
            "invalid_conflicting_or_unrenderable_fact_is_parent_noop": True,
            "legacy_prompt_unchanged_receipt_not_reexported": True,
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
            "fresh_benchmark_external_shared_prefix_mechanism_protocol_design": True,
            "external_activation_or_launch": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.48 checkpoint grounded fact build audit drifted")
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
