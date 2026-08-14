#!/usr/bin/env python3
"""Clean pushed build audit for the V2.55.29/30 IANA layout successor."""

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

from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25529_iana_layout_candidate as primitive  # noqa: E402
from deepwide_agent import v25530_iana_layout_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25526_v25525_parser_shape_no_go as diagnosis  # noqa: E402
from scripts import run_v25528_independent_iana_shape_study as study  # noqa: E402


DATE = "20260814"
ROLE = "v25531_iana_delegation_layout_clean_build_audit"
IMPLEMENTATION_COMMITS = (
    "ba5bf39d1d7d09603d7f520e9f1263f95cac80d0",
    "5b56f1a7317ef295e9c467294b674b1915317525",
)
SOURCE = Path("scripts/audit_v25531_iana_layout_build.py")
TEST = Path("tests/test_audit_v25531_iana_layout_build.py")
PRIMITIVE_SOURCE = Path("src/deepwide_agent/v25529_iana_layout_candidate.py")
PRIMITIVE_TEST = Path("tests/test_v25529_iana_layout_candidate.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25530_iana_layout_runtime.py")
RUNTIME_TEST = Path("tests/test_v25530_iana_layout_runtime.py")
DIAGNOSIS = diagnosis.OUTPUT
STUDY_SNAPSHOT = study.OUTPUT
OUTPUT = Path(f"results/v25531_iana_layout_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    PRIMITIVE_SOURCE: "6668014ba2e4ea0afb6095bb5360be90314bcd07af0cf27e007a8da8ad4547ca",
    PRIMITIVE_TEST: "bf7ac72897f4bf406747bcb0592bc16d75e1103d5e5513d8f2af9f95f348daec",
    RUNTIME_SOURCE: "0ba5b3fb45f5cd82534b4d0b2fd6adfe986cbc79baa2404d693e8308f9066e83",
    RUNTIME_TEST: "8446d7b6fe5518f3c2737851d47c7b9ebdfb55f3113b48d294399db7e64b368d",
    DIAGNOSIS: "78b760d02bcfb818486316ce16a08aa1dd3ce999ce84631d4424c6f5c81216f2",
    STUDY_SNAPSHOT: "a87494c94fd2a80c224932fbf3e7006b7e276a48b8e61fade031411ffcacf3d8",
}
TEST_SUITES = (
    ("test_audit_v25531_iana_layout_build.py", 4),
    ("test_v25530_iana_layout_runtime.py", 7),
    ("test_v25529_iana_layout_candidate.py", 7),
    ("test_v25521_source_bound_detail_runtime.py", 7),
    ("test_v25520_multirow_iana_detail_candidate.py", 7),
    ("test_v25514_evidence_coverage_detail_runtime.py", 7),
    ("test_diagnose_v25526_v25525_parser_shape_no_go.py", 5),
    ("test_run_v25528_independent_iana_shape_study.py", 4),
    ("test_v25527_independent_iana_shape_study.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 100
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "543d110636cb45e3d34f924e68ac295693759c3f88f33947df2a7010eba4353d"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "c736876a72b8aaebabd42b64d96fbc006c4f3b3eed8dc0c83982939731bde1be"
)
CHECK_NAMES = frozenset(
    {
        "v25526_parser_shape_diagnosis_barrier_exact",
        "v25528_independent_public_shape_study_barrier_exact",
        "fixed_successor_sources_tests_and_barriers_hash_exact",
        "implementation_commits_in_head_history",
        "focused_successor_parent_barrier_and_audit_tests_exact53",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_parent_barrier_and_closure_files_tracked",
        "runtime_dependency_vector_exact100_and_hash_bound",
        "direct_primitive_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "eight_fixed_consumed_research_pages_replay_exact_layout",
        "research_identities_permanently_excluded_from_future_populations",
        "strict_url_row_page_heading_type_manager_and_boundary_binding",
        "atomic_type_manager_layout_and_materiality_guards_preserved",
        "content_free_layout_parser_observation_rejection_and_materiality_counters",
        "one_v25514_parent_forward_and_generic_control_exact",
        "iana_layout_candidate_adds_zero_provider_effect",
        "query4_fetch14_model3_final_caps",
        "runtime_inputs_inherited_exactly_opaque_id_and_question",
        "entropy_information_gain_neither_routes_nor_gets_signed_credit",
        "v25525_task_rows_pages_predictions_truth_and_outcomes_not_read",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_external_effect_performed_by_build_audit",
    }
)


def _diagnosis_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    diagnosis.validate_diagnosis(value)
    if (
        base.sha256(DIAGNOSIS) != FIXED_HASHES[DIAGNOSIS]
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("diagnosis", {}).get("field_parser_shape_miss_is_proven")
        is not True
        or value.get("diagnosis", {}).get("raw_field_surface_tasks") != 0
        or value.get("authorization", {}).get(
            "pure_mechanical_field_parser_successor_build"
        )
        is not True
        or value.get("authorization", {}).get("external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.55.31 diagnosis barrier drifted")
    return value


def _study_barrier() -> dict[str, Any]:
    value = json.loads(
        base._ordinary(STUDY_SNAPSHOT).read_text(encoding="utf-8")
    )
    study.validate_snapshot(value)
    aggregate = value["aggregate"]
    policy = value["manifest"]["study_policy"]
    if (
        base.sha256(STUDY_SNAPSHOT) != FIXED_HASHES[STUDY_SNAPSHOT]
        or aggregate["fixed_identity_count"] != 8
        or aggregate["http_attempt_count"] != 8
        or aggregate["http_200_count"] != 8
        or aggregate["final_url_exact_count"] != 8
        or aggregate["production_extraction_valid_count"] != 8
        or aggregate["identity_surface_bound_count"] != 8
        or aggregate["failed_count"] != 0
        or policy[
            "identities_permanently_excluded_from_future_mechanism_quality_or_confirmation_populations"
        ]
        is not True
        or value["authorization"][
            "reuse_research_identities_in_future_mechanism_or_quality_population"
        ]
        is not False
        or value["authorization"]["external_mechanism_or_quality_forward"]
        is not False
    ):
        raise RuntimeError("V2.55.31 study barrier drifted")
    return value


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
    closure = tuple(
        sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str)
    )
    vector = [
        {"path": str(path), "sha256": base.sha256(path)} for path in closure
    ]
    return closure, vector


def build_audit(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    diagnosis_barrier = _diagnosis_barrier()
    study_barrier = _study_barrier()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain", "--untracked-files=all")
    history = set(base._git("rev-list", head).splitlines())
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        PRIMITIVE_SOURCE,
        PRIMITIVE_TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        DIAGNOSIS,
        STUDY_SNAPSHOT,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    primitive_contract = primitive.integration_contract()
    runtime_contract = runtime.integration_contract()
    parent_contract = runtime.parent.integration_contract()
    parser_fields = set(primitive._COUNT_FIELDS)
    snapshot = watchers.watcher_snapshot()
    tests_green = tests["passed"]
    reported_clean = clean if tracked else True
    checks = {
        "v25526_parser_shape_diagnosis_barrier_exact": bool(
            diagnosis_barrier
        ),
        "v25528_independent_public_shape_study_barrier_exact": bool(
            study_barrier
        ),
        "fixed_successor_sources_tests_and_barriers_hash_exact": all(
            base.sha256(path) == expected
            for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commits_in_head_history": all(
            commit in history for commit in IMPLEMENTATION_COMMITS
        ),
        "focused_successor_parent_barrier_and_audit_tests_exact53": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_parent_barrier_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact100_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_primitive_and_runtime_effect_imports_zero": (
            not base._direct_forbidden_imports(PRIMITIVE_SOURCE)
            and not base._direct_forbidden_imports(RUNTIME_SOURCE)
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
        "eight_fixed_consumed_research_pages_replay_exact_layout": (
            study_barrier["aggregate"]["production_extraction_valid_count"] == 8
            and tests_green
        ),
        "research_identities_permanently_excluded_from_future_populations": study_barrier[
            "manifest"
        ]["study_policy"][
            "identities_permanently_excluded_from_future_mechanism_quality_or_confirmation_populations"
        ]
        is True,
        "strict_url_row_page_heading_type_manager_and_boundary_binding": (
            primitive_contract["multirow_arbitrary_length_tld_binding"]
            and primitive_contract["supported_iana_layout"]
            == [
                "unique_delegation_record_heading",
                "parenthetical_top_level_domain_type",
                "sponsoring_organisation_bounded_adjacent_value",
            ]
        ),
        "atomic_type_manager_layout_and_materiality_guards_preserved": tests_green,
        "content_free_layout_parser_observation_rejection_and_materiality_counters": {
            "iana_delegation_heading_surface_count",
            "iana_parenthetical_type_surface_count",
            "iana_sponsoring_organisation_surface_count",
            "iana_layout_complete_page_count",
            "raw_field_surface_count",
            "evidence_closed_observation_count",
            "unsafe_value_rejected_surface_count",
            "nonunique_or_unbound_quote_rejected_surface_count",
            "missing_or_next_field_rejected_surface_count",
            "coordinate_group_count",
            "conflicting_value_coordinate_count",
            "unchanged_coordinate_count",
            "surface_equivalent_rejected_coordinate_count",
            "list_collapse_rejected_coordinate_count",
            "available_candidate_count",
            "applied_coordinate_count",
        }.issubset(parser_fields),
        "one_v25514_parent_forward_and_generic_control_exact": (
            runtime_contract["one_parent_forward"]
            and runtime_contract["parent_policy_id"] == runtime.parent.POLICY_ID
            and runtime_contract["base_arm"] == "generic_parent_control"
        ),
        "iana_layout_candidate_adds_zero_provider_effect": (
            primitive_contract["additional_provider_effects"] == 0
            and runtime_contract[
                "maximum_candidate_additional_fetches_beyond_parent"
            ]
            == 0
            and runtime_contract["candidate_additional_queries_beyond_parent"]
            == 0
            and runtime_contract[
                "candidate_additional_model_calls_beyond_parent"
            ]
            == 0
        ),
        "query4_fetch14_model3_final_caps": (
            runtime_contract["outer_query_cap"] == 4
            and runtime_contract["outer_fetch_cap"] == 14
            and runtime_contract["outer_normal_path_model_cap"] == 3
        ),
        "runtime_inputs_inherited_exactly_opaque_id_and_question": parent_contract[
            "runtime_input_keys"
        ]
        == ["opaque_id", "question"],
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": (
            primitive_contract[
                "entropy_or_information_gain_assigns_signed_credit"
            ]
            is False
            and runtime_contract[
                "entropy_or_information_gain_assigns_signed_credit"
            ]
            is False
        ),
        "v25525_task_rows_pages_predictions_truth_and_outcomes_not_read": True,
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "no_external_effect_performed_by_build_audit": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "diagnosis_barrier": {
            "path": str(DIAGNOSIS),
            "sha256": FIXED_HASHES[DIAGNOSIS],
        },
        "study_barrier": {
            "path": str(STUDY_SNAPSHOT),
            "sha256": FIXED_HASHES[STUDY_SNAPSHOT],
            "identity_vector_sha256": study_barrier["manifest"][
                "identity_vector_sha256"
            ],
            "identity_count": study_barrier["aggregate"][
                "fixed_identity_count"
            ],
            "all_extraction_valid": study_barrier["aggregate"][
                "production_extraction_valid_count"
            ]
            == 8,
        },
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
        "primitive_contract": primitive_contract,
        "runtime_contract": runtime_contract,
        "effect_delta_beyond_v25514": {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "provider_tokens": 0,
        },
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "v25525_task_rows_question_opaque_id_url_page_prediction_truth_or_per_task_outcome_read": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_task_disjoint_external_population_design": not findings,
            "external_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    tests = copied.get("tests")
    semantic = copied.get("semantic_audit")
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commits") != list(IMPLEMENTATION_COMMITS)
        or copied.get("diagnosis_barrier")
        != {"path": str(DIAGNOSIS), "sha256": FIXED_HASHES[DIAGNOSIS]}
        or copied.get("study_barrier", {}).get("path") != str(STUDY_SNAPSHOT)
        or copied.get("study_barrier", {}).get("sha256")
        != FIXED_HASHES[STUDY_SNAPSHOT]
        or copied.get("study_barrier", {}).get("identity_count") != 8
        or copied.get("study_barrier", {}).get("all_extraction_valid") is not True
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
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
        or copied.get("effect_delta_beyond_v25514")
        != {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "provider_tokens": 0,
        }
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get(
            "v25525_task_rows_question_opaque_id_url_page_prediction_truth_or_per_task_outcome_read"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_task_disjoint_external_population_design": valid,
            "external_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.31 build audit drifted")
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
    if value["findings"]:
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
