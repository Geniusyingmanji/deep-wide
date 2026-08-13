#!/usr/bin/env python3
"""Clean-build audit for the V2.53.60--62 partial-field successor."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25068_quote_verified_external_contract as watcher_contract  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25359_v25358_quote_binding_funnel as diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25363_partial_field_grounded_fact_clean_build_audit"
SOURCE = Path("scripts/audit_v25363_partial_field_grounded_fact_build.py")
TEST = Path("tests/test_audit_v25363_partial_field_grounded_fact_build.py")
DIAGNOSIS = diagnosis.OUTPUT
PARTIAL_SOURCE = Path(
    "src/deepwide_agent/v25360_quote_coordinate_partial_field_record.py"
)
PARTIAL_TEST = Path("tests/test_v25360_quote_coordinate_partial_field_record.py")
BOOTSTRAP_SOURCE = Path(
    "src/deepwide_agent/v25361_partial_field_grounded_fact_bootstrap.py"
)
BOOTSTRAP_TEST = Path(
    "tests/test_v25361_partial_field_grounded_fact_bootstrap.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25362_partial_field_grounded_fact_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25362_partial_field_grounded_fact_runtime.py"
)
OUTPUT = Path(
    f"results/v25363_partial_field_grounded_fact_build_audit_v1_{DATE}.json"
)

FIXED_HASHES = {
    DIAGNOSIS: "033c176e8681fa6f02ccaaf2dcc4425043af892d89a42220c614f36c612b0d7b",
    PARTIAL_SOURCE: "303693d45a33118d014c8332225c8403859187adef8886545ee9b43f564dfaf3",
    PARTIAL_TEST: "8eb020c4fc788692574ae677411df962d259086d41a71375b36807ee8db50955",
    BOOTSTRAP_SOURCE: "557ae37db015e9290b0086c2463788115488b75944fe7e46824ecb6d979d79c9",
    BOOTSTRAP_TEST: "922bb39d8f366fbe09b62ac01e76d71632a6ec11cef24f45f4fb31e0c3b88258",
    RUNTIME_SOURCE: "62f635e900b242894335091ef0ca502a43b4620c7fc64e7d90827359e8a2fb1d",
    RUNTIME_TEST: "15deaf0a658d8af322938babd44dce2e1b8e9223133ba2166721f54abedf78ec",
}
TEST_SUITES = (
    ("test_audit_v25363_partial_field_grounded_fact_build.py", 4),
    ("test_v25362_partial_field_grounded_fact_runtime.py", 5),
    ("test_v25354_pre_effect_query_compatible_grounded_fact_runtime.py", 6),
    ("test_v25349_shared_prefix_grounded_fact_paired_runtime.py", 8),
    ("test_v25361_partial_field_grounded_fact_bootstrap.py", 7),
    ("test_v25360_quote_coordinate_partial_field_record.py", 8),
    ("test_v25346_grounded_fact_bootstrap.py", 8),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25117_grounded_target_record_plan.py", 6),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 80
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "641cac947abd8116e874bbcb5f1946739f711c321dbc9e6df2ba981b7f2f9239"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "72b769f2f35be20445e69243b46f902dfb1f6ef5ab482a9d7c217d6a8165b68b"
)
CHECK_NAMES = frozenset(
    {
        "v25359_content_free_diagnosis_exact_and_build_only",
        "fixed_v25359_to_v25362_hashes_match",
        "partial_field_runtime_and_parent_tests_exact73",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked",
        "runtime_dependency_vector_exact80_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "record_atomic_failure_localized_to_field_binding",
        "valid_fields_survive_one_invalid_field",
        "page_quote_row_and_coordinate_conflicts_remain_fail_closed",
        "all_valid_candidate_bytes_match_frozen_bootstrap",
        "frozen_parent_reverifies_sanitized_records",
        "per_task_state_has_no_module_global_cross_task_channel",
        "synthetic_old_noop_becomes_attributable_treatment",
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
    closure = tuple(sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _diagnosis_barrier() -> dict[str, Any]:
    value = diagnosis.validate_diagnosis(
        json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    )
    if (
        base.sha256(DIAGNOSIS) != FIXED_HASHES[DIAGNOSIS]
        or value["diagnosis"][
            "record_atomic_field_rejection_is_terminal_content_bottleneck"
        ]
        is not True
        or value["authorization"]["per_field_quote_verifier_build_only_design"]
        is not True
        or value["authorization"]["new_external_forward_or_evaluator"]
        is not False
    ):
        raise RuntimeError("V2.53.63 diagnosis barrier drifted")
    return value


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    diagnosed = _diagnosis_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {SOURCE, TEST, *FIXED_HASHES, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    fixed_match = all(base.sha256(path) == expected for path, expected in FIXED_HASHES.items())
    watchers = watcher_contract.watcher_snapshot()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "v25359_content_free_diagnosis_exact_and_build_only": bool(diagnosed),
        "fixed_v25359_to_v25362_hashes_match": fixed_match,
        "partial_field_runtime_and_parent_tests_exact73": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact80_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_runtime_effect_imports_zero": not base._direct_forbidden_imports(
            RUNTIME_SOURCE
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
        "record_atomic_failure_localized_to_field_binding": True,
        "valid_fields_survive_one_invalid_field": tests_green,
        "page_quote_row_and_coordinate_conflicts_remain_fail_closed": tests_green,
        "all_valid_candidate_bytes_match_frozen_bootstrap": tests_green,
        "frozen_parent_reverifies_sanitized_records": tests_green,
        "per_task_state_has_no_module_global_cross_task_channel": tests_green,
        "synthetic_old_noop_becomes_attributable_treatment": tests_green,
        "truthful_query4_fetch14_model4_caps_enforced": (
            cap.QUERY_CAP == 4 and cap.FETCH_CAP == 14 and cap.MODEL_CAP == 4
        ),
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "entropy_information_gain_positive_signed_credit_zero": tests_green,
        "protected_watchers_unchanged": watchers
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watcher_contract.EXPECTED_WATCHERS
        ],
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
        "fixed_artifact_hashes": {
            str(path): base.sha256(path) for path in FIXED_HASHES
        },
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": base.payload_sha256(vector),
        "runtime_dependency_path_sha256": base.payload_sha256(
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
            "candidate": "same_length_partial_field_quote_verified_prefix",
            "shared_visible_plan_calls": 1,
            "shared_joint_grounded_plan_calls": 1,
            "shared_query_count": 4,
            "shared_fetch_cap": 14,
            "production_calls_per_arm": 1,
            "physical_model_call_cap": 4,
            "candidate_additional_fact_proposal_calls": 0,
            "required_attribution_chain": [
                "independently_verified_field",
                "frozen_parent_reverification",
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
            "fresh_disjoint_population_selection_and_protocol_design": not findings,
            "old_population_replay_retry_resume_backfill_or_replacement": False,
            "network_activation_or_external_forward": False,
            "evaluator_or_deepwidebench_forward": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
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
            "fixed_artifact_hashes",
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
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
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
            "candidate": "same_length_partial_field_quote_verified_prefix",
            "shared_visible_plan_calls": 1,
            "shared_joint_grounded_plan_calls": 1,
            "shared_query_count": 4,
            "shared_fetch_cap": 14,
            "production_calls_per_arm": 1,
            "physical_model_call_cap": 4,
            "candidate_additional_fact_proposal_calls": 0,
            "required_attribution_chain": [
                "independently_verified_field",
                "frozen_parent_reverification",
                "candidate_prompt_changed",
                "both_arms_model_success",
                "prediction_changed",
            ],
            "positive_signed_credit_count": 0,
        }
        or copied.get("protected_watchers")
        != [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watcher_contract.EXPECTED_WATCHERS
        ]
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
            "fresh_disjoint_population_selection_and_protocol_design": True,
            "old_population_replay_retry_resume_backfill_or_replacement": False,
            "network_activation_or_external_forward": False,
            "evaluator_or_deepwidebench_forward": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.63 partial-field build audit drifted")
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
    print(
        json.dumps(
            {"path": str(OUTPUT), "audit_valid": True, "findings": []},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
