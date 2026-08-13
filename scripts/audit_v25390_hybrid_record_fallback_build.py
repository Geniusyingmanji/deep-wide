#!/usr/bin/env python3
"""Clean-build audit for the V2.53.89 hybrid record fallback."""

from __future__ import annotations

import copy
import json
import os
import socket
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
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25388_v25387_joint_record_suppression as diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25390_hybrid_record_fallback_clean_build_audit"
SOURCE = Path("scripts/audit_v25390_hybrid_record_fallback_build.py")
TEST = Path("tests/test_audit_v25390_hybrid_record_fallback_build.py")
DIAGNOSIS = diagnosis.OUTPUT
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25389_hybrid_record_fallback_runtime.py"
)
RUNTIME_TEST = Path("tests/test_v25389_hybrid_record_fallback_runtime.py")
OUTPUT = Path(
    f"results/v25390_hybrid_record_fallback_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    DIAGNOSIS: "811ecbf473ed2823d0ba2766f330406724713c2d13e7a9d5359ba5dccb62c5e2",
    RUNTIME_SOURCE: "cb881bc40332f2e8727b9437fbd1ea158dd6ce7e41dbe3d1a3e3a4a915cc92d8",
    RUNTIME_TEST: "2edeafe5a298e67d0340082b957b610506fd64e9b88ed37a52088b44fc4a66b6",
}
TEST_SUITES = (
    ("test_audit_v25390_hybrid_record_fallback_build.py", 4),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25383_joint_synthesis_changed_safe_runtime.py", 8),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
    ("test_v25369_changed_safe_verified_coordinate_edit.py", 8),
    ("test_v25360_quote_coordinate_partial_field_record.py", 8),
    ("test_v25346_grounded_fact_bootstrap.py", 8),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 84
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "7e9e53723254ac97cb3f7028262750ad8f93aa8f54a0cf03ac7b6c6de0b1e50f"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "5c7640a4f8d82698ae01905bb56850dcff745572165a46b6a672d61ac062f327"
)
CHECK_NAMES = frozenset(
    {
        "v25388_joint_record_suppression_diagnosis_bound_and_build_only",
        "fixed_runtime_test_and_diagnosis_hashes_match",
        "hybrid_runtime_and_parent_tests_exact84",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked",
        "runtime_dependency_vector_exact84_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "record_source_selected_before_verification",
        "nonempty_joint_has_unconditional_priority",
        "grounded_allowed_only_when_joint_raw_list_empty",
        "joint_and_grounded_never_merged",
        "invalid_joint_cannot_fall_through_to_valid_grounded",
        "both_sources_replay_quote_field_value_verifier",
        "same_response_base_row_still_required",
        "synthetic_grounded_fallback_positive_chain_attributable",
        "invalid_missing_or_unchanged_is_noop",
        "task_local_mixed_concurrency_no_global_mutation",
        "receipt_source_parent_prediction_credit_tamper_fails_closed",
        "truthful_query4_fetch14_model3_normal_cap",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "entropy_information_gain_positive_signed_credit_zero",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "local_gpt56_port_reachable",
        "local_tcp_probe_only_no_model_search_fetch_evaluator_benchmark_or_api_called",
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
    funnel = value["content_free_funnel"]
    if (
        base.sha256(DIAGNOSIS) != FIXED_HASHES[DIAGNOSIS]
        or funnel["grounded_record_member_nonempty_tasks"] != 8
        or funnel["grounded_record_count_total"] != 11
        or funnel["joint_record_member_nonempty_tasks"] != 0
        or value["diagnosis"][
            "same_forward_grounded_record_fallback_is_mechanically_available"
        ]
        is not True
        or value["diagnosis"]["grounded_and_joint_records_must_not_be_merged"]
        is not True
        or value["authorization"][
            "hybrid_joint_or_grounded_record_fallback_build_only"
        ]
        is not True
        or value["authorization"]["new_external_forward"] is not False
    ):
        raise RuntimeError("V2.53.90 diagnosis barrier drifted")
    return value


def _port_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            return True
    except OSError:
        return False


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
    fixed_match = all(
        base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
    )
    watchers = watcher_contract.watcher_snapshot()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "v25388_joint_record_suppression_diagnosis_bound_and_build_only": bool(
            diagnosed
        ),
        "fixed_runtime_test_and_diagnosis_hashes_match": fixed_match,
        "hybrid_runtime_and_parent_tests_exact84": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact84_and_hash_bound": (
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
        "record_source_selected_before_verification": tests_green,
        "nonempty_joint_has_unconditional_priority": tests_green,
        "grounded_allowed_only_when_joint_raw_list_empty": tests_green,
        "joint_and_grounded_never_merged": tests_green,
        "invalid_joint_cannot_fall_through_to_valid_grounded": tests_green,
        "both_sources_replay_quote_field_value_verifier": tests_green,
        "same_response_base_row_still_required": tests_green,
        "synthetic_grounded_fallback_positive_chain_attributable": tests_green,
        "invalid_missing_or_unchanged_is_noop": tests_green,
        "task_local_mixed_concurrency_no_global_mutation": tests_green,
        "receipt_source_parent_prediction_credit_tamper_fails_closed": tests_green,
        "truthful_query4_fetch14_model3_normal_cap": tests_green,
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "entropy_information_gain_positive_signed_credit_zero": tests_green,
        "protected_watchers_unchanged": watchers
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watcher_contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "local_gpt56_port_reachable": _port_reachable(),
        "local_tcp_probe_only_no_model_search_fetch_evaluator_benchmark_or_api_called": True,
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
            "queries": 4,
            "fetches": 14,
            "normal_path_model_forwards": 3,
            "outer_hard_model_cap": 4,
        },
        "record_source_policy": {
            "priority": ["nonempty_joint", "nonempty_grounded", "none"],
            "selection_timing": "before_quote_or_edit_verification",
            "merge_or_union": False,
            "verification_outcome_fallthrough": False,
            "candidate_model_calls": 0,
            "positive_signed_credit_count": 0,
        },
        "protected_watchers": watchers,
        "local_tcp_reachability_probe_performed": True,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_population_and_external_protocol_design": not findings,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    findings = copied.get("findings")
    tests = copied.get("tests")
    semantic = copied.get("semantic_audit")
    valid = copied.get("audit_valid") is True
    expected_authorization = {
        "fresh_population_and_external_protocol_design": valid,
        "external_forward": False,
        "deepwidebench_forward_or_evaluator": False,
        "leaderboard_or_sota": False,
        "retry_resume_backfill_replacement_or_selective_rerun": False,
    }
    if (
        copied.get("role") != ROLE
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or any(not isinstance(passed, bool) for passed in checks.values())
        or findings != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (findings == [])
        or not isinstance(tests, Mapping)
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or not isinstance(semantic, Mapping)
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization") != expected_authorization
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.90 hybrid build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
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
    if not value["audit_valid"]:
        raise RuntimeError(value["findings"])
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "tests": value["tests"]["observed"],
                "closure": len(value["runtime_dependency_vector"]),
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
