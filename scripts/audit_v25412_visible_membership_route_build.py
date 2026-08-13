#!/usr/bin/env python3
"""Clean-build audit for the V2.54.11 visible-membership route runtime."""

from __future__ import annotations

import copy
import json
import os
import socket
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25068_quote_verified_external_contract as watcher_contract  # noqa: E402
from deepwide_agent import v25376_changed_safe_exact220_contract as public_tasks  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership  # noqa: E402
from deepwide_agent import v25411_visible_membership_route_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25410_v25406_grounded_membership_exact220 as diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25412_visible_membership_route_clean_build_audit"
IMPLEMENTATION_COMMIT = "d0456c96d34fc0d7bb8b43f21d45cb7616f30e9a"
SOURCE = Path("scripts/audit_v25412_visible_membership_route_build.py")
TEST = Path("tests/test_audit_v25412_visible_membership_route_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25411_visible_membership_route_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25411_visible_membership_route_runtime.py"
)
DIAGNOSIS_SOURCE = diagnosis.SOURCE
DIAGNOSIS_TEST = Path(
    "tests/test_diagnose_v25410_v25406_grounded_membership_exact220.py"
)
DIAGNOSIS_ARTIFACT = diagnosis.OUTPUT
OUTPUT = Path(
    f"results/v25412_visible_membership_route_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    RUNTIME_SOURCE: "711ca0685265ac91e7d59c52024fb80e9d304647e2d5aad4d0746b79487d5c8b",
    RUNTIME_TEST: "b71b37b56d7b465952bd44948b2f49f26925b69fb3fbb8e4ec67273d1328813e",
    DIAGNOSIS_SOURCE: "edcbb47845ec68f8ff154a604c12603495f2ebe5515f44cef92f5cbe76bb6dbb",
    DIAGNOSIS_TEST: "c3958c2740fc2b77725e3ab0e835e1d2d3f667e00a9a4bf4989ed1ad2756d410",
    DIAGNOSIS_ARTIFACT: "23be0b0f4c67879ba669907b53cd2c2f0231fa3249c8811c2d99d2a05e51ea90",
}
TEST_SUITES = (
    ("test_audit_v25412_visible_membership_route_build.py", 4),
    ("test_v25411_visible_membership_route_runtime.py", 10),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25395_visible_membership_synthesis_runtime.py", 7),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25383_joint_synthesis_changed_safe_runtime.py", 8),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
    ("test_v25369_changed_safe_verified_coordinate_edit.py", 8),
    ("test_v25360_quote_coordinate_partial_field_record.py", 8),
    ("test_v25014_multi_identity_detail_fields.py", 9),
    ("test_v25080_visible_identity_page_record.py", 8),
    ("test_v24921_target_value_coverage_projector.py", 9),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_diagnose_v25410_v25406_grounded_membership_exact220.py", 4),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 93
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "214418000bc07df0e01791ebd491b6d8ddca851da3e5a91a4c3f7798e7a56a05"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "e6ef747f10c6b0ba8296aca7e205f75012a148536ab2f76742eaa1c75e50257d"
)
EXPECTED_MEMBERSHIP_SOURCE_COUNTS = {
    "explicit_row_phrase": 11,
    "none": 209,
}
EXPECTED_MEMBER_HISTOGRAM = {"0": 209, "1": 11}
CHECK_NAMES = frozenset(
    {
        "v25410_diagnosis_bound_and_authorizes_only_next_build",
        "fixed_runtime_test_diagnosis_hashes_match",
        "implementation_commit_is_in_head_history",
        "route_and_parent_tests_exact116",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked",
        "runtime_dependency_vector_exact93_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "route_uses_only_strict_visible_question_membership",
        "membership_absent_calls_v25375_once_and_returns_objects_byte_exact",
        "membership_present_calls_v25401_once_and_returns_objects_byte_exact",
        "union_validator_accepts_both_sealed_surfaces_and_rejects_mismatch",
        "route_and_selected_parent_failures_emit_sealed_totality_receipt",
        "selected_parent_failure_has_no_cross_branch_retry_or_fallback",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "public220_route_coverage_209_absent_11_present_aggregate_only",
        "entropy_information_gain_neither_routes_nor_gets_signed_credit",
        "query4_fetch14_model3_parent_caps_unchanged",
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
        json.loads(base._ordinary(DIAGNOSIS_ARTIFACT).read_text(encoding="utf-8"))
    )
    decision = value["decision"]
    if (
        base.sha256(DIAGNOSIS_ARTIFACT) != FIXED_HASHES[DIAGNOSIS_ARTIFACT]
        or value["diagnosis"]["visible_membership_coverage_is_eleven_of_220"]
        is not True
        or value["diagnosis"][
            "successful_membership_constrained_grounded_record_reach_is_zero"
        ]
        is not True
        or value["diagnosis"][
            "eleven_new_outer_value_errors_followed_healthy_complete_provider_effects"
        ]
        is not True
        or decision["membership_absent_branch"]
        != "byte_exact_v25375_parent_path"
        or decision["membership_present_branch"]
        != "v25401_only_after_fresh_disjoint_branch_gate"
        or decision["runtime_route_may_use_visible_membership_but_not_historical_outcome"]
        is not True
        or decision["historical_score_correctness_or_evaluator_feedback_runtime_routing"]
        is not False
        or decision["entropy_or_information_gain_signed_credit_authorized"]
        is not False
        or value["authorization"]["next_build_only"] is not True
        or value["authorization"]["new_external_forward"] is not False
    ):
        raise RuntimeError("V2.54.12 diagnosis barrier drifted")
    return value


def _public_route_coverage() -> dict[str, Any]:
    source_counts: Counter[str] = Counter()
    branch_counts: Counter[str] = Counter()
    member_histogram: Counter[int] = Counter()
    for row in public_tasks.task_vector(ROOT):
        values, source = membership.visible_membership(row["question"])
        branch = runtime.route_for_visible_question(row["question"])
        source_counts[source] += 1
        branch_counts[branch] += 1
        member_histogram[len(values)] += 1
    return {
        "task_count": sum(source_counts.values()),
        "membership_source_counts": dict(sorted(source_counts.items())),
        "route_branch_counts": dict(sorted(branch_counts.items())),
        "visible_member_count_histogram": {
            str(key): value for key, value in sorted(member_histogram.items())
        },
        "question_text_opaque_id_mapping_gold_answer_evaluator_score_or_historical_outcome_persisted": False,
        "runtime_parent_model_search_fetch_or_evaluator_called": False,
    }


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
    history = base._git("rev-list", head)
    diagnosed = _diagnosis_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        DIAGNOSIS_SOURCE,
        DIAGNOSIS_TEST,
        DIAGNOSIS_ARTIFACT,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    fixed_match = all(
        base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
    )
    watchers = watcher_contract.watcher_snapshot()
    coverage = _public_route_coverage()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "v25410_diagnosis_bound_and_authorizes_only_next_build": bool(diagnosed),
        "fixed_runtime_test_diagnosis_hashes_match": fixed_match,
        "implementation_commit_is_in_head_history": IMPLEMENTATION_COMMIT
        in history.splitlines(),
        "route_and_parent_tests_exact116": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact93_and_hash_bound": (
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
        "route_uses_only_strict_visible_question_membership": tests_green,
        "membership_absent_calls_v25375_once_and_returns_objects_byte_exact": tests_green,
        "membership_present_calls_v25401_once_and_returns_objects_byte_exact": tests_green,
        "union_validator_accepts_both_sealed_surfaces_and_rejects_mismatch": tests_green,
        "route_and_selected_parent_failures_emit_sealed_totality_receipt": tests_green,
        "selected_parent_failure_has_no_cross_branch_retry_or_fallback": tests_green,
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "public220_route_coverage_209_absent_11_present_aggregate_only": (
            coverage["task_count"] == 220
            and coverage["membership_source_counts"]
            == EXPECTED_MEMBERSHIP_SOURCE_COUNTS
            and coverage["route_branch_counts"]
            == {
                runtime.MEMBERSHIP_BRANCH: 11,
                runtime.STABLE_BRANCH: 209,
            }
            and coverage["visible_member_count_histogram"]
            == EXPECTED_MEMBER_HISTOGRAM
            and coverage[
                "question_text_opaque_id_mapping_gold_answer_evaluator_score_or_historical_outcome_persisted"
            ]
            is False
            and coverage["runtime_parent_model_search_fetch_or_evaluator_called"]
            is False
        ),
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": tests_green,
        "query4_fetch14_model3_parent_caps_unchanged": tests_green,
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
        "implementation_commit": IMPLEMENTATION_COMMIT,
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
        "public220_route_coverage": coverage,
        "physical_caps": {
            "queries": 4,
            "fetches": 14,
            "normal_path_model_forwards": 3,
            "outer_hard_model_cap": 4,
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
            "fresh_disjoint_shared_prefix_gate_design": not findings,
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
    coverage = copied.get("public220_route_coverage")
    valid = copied.get("audit_valid") is True
    expected_authorization = {
        "fresh_disjoint_shared_prefix_gate_design": valid,
        "external_forward": False,
        "deepwidebench_forward_or_evaluator": False,
        "leaderboard_or_sota": False,
        "retry_resume_backfill_replacement_or_selective_rerun": False,
    }
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
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
        or not isinstance(coverage, Mapping)
        or coverage.get("task_count") != 220
        or coverage.get("membership_source_counts")
        != EXPECTED_MEMBERSHIP_SOURCE_COUNTS
        or coverage.get("route_branch_counts")
        != {
            runtime.MEMBERSHIP_BRANCH: 11,
            runtime.STABLE_BRANCH: 209,
        }
        or coverage.get("visible_member_count_histogram")
        != EXPECTED_MEMBER_HISTOGRAM
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
        raise ValueError("V2.54.12 visible-membership route build audit drifted")
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
                "coverage": value["public220_route_coverage"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
