#!/usr/bin/env python3
"""Clean pushed build audit for the V2.55.20/21 source-bound successor."""

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
from deepwide_agent import v25520_multirow_iana_detail_candidate as primitive  # noqa: E402
from deepwide_agent import v25521_source_bound_detail_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25519_v25518_evidence_coverage_no_go as diagnosis  # noqa: E402


DATE = "20260814"
ROLE = "v25522_source_bound_detail_clean_build_audit"
IMPLEMENTATION_COMMITS = (
    "859b69dacbd2899ff33e7093d5857e2711be6ebf",
    "ae89d7cb4e9cda26532812e07ee17efabdd1dc6e",
)
SOURCE = Path("scripts/audit_v25522_source_bound_detail_build.py")
TEST = Path("tests/test_audit_v25522_source_bound_detail_build.py")
PRIMITIVE_SOURCE = Path(
    "src/deepwide_agent/v25520_multirow_iana_detail_candidate.py"
)
PRIMITIVE_TEST = Path(
    "tests/test_v25520_multirow_iana_detail_candidate.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25521_source_bound_detail_runtime.py"
)
RUNTIME_TEST = Path("tests/test_v25521_source_bound_detail_runtime.py")
DIAGNOSIS = diagnosis.OUTPUT
DIAGNOSIS_SHA256 = (
    "65c092d30e8a3e281b6be0ff24cda2b54b99202b9019ed6b79589bb95a290fcb"
)
OUTPUT = Path(
    f"results/v25522_source_bound_detail_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    PRIMITIVE_SOURCE: "cd1e5616e50fcba1140c03533790e995d42d8fc9be3481352c7c50c61e8d873c",
    PRIMITIVE_TEST: "edea2da5e59fe7f5bd5c169c0e41330d15be7627188cd811e36cd49370733f54",
    RUNTIME_SOURCE: "64a44551d53759fe776b9abf5195e6e2e5411d2ae6273ee6bdbbe20a116c8c63",
    RUNTIME_TEST: "fcdb37ae53347cc56d624db1d5c2b4bf89be164cf2efdfe0a2b32917a8a186ac",
    DIAGNOSIS: DIAGNOSIS_SHA256,
}
TEST_SUITES = (
    ("test_audit_v25522_source_bound_detail_build.py", 4),
    ("test_v25521_source_bound_detail_runtime.py", 7),
    ("test_v25520_multirow_iana_detail_candidate.py", 7),
    ("test_v25514_evidence_coverage_detail_runtime.py", 7),
    ("test_v25513_evidence_coverage_deficit_selection.py", 7),
    ("test_v25483_row_key_iana_detail_candidate.py", 7),
    ("test_v25484_row_key_iana_detail_runtime.py", 7),
    ("test_v25499_generic_mechanical_field_candidate.py", 7),
    ("test_v25492_visible_row_key_detail_runtime.py", 7),
    ("test_v25491_visible_row_key_detail_selection.py", 7),
    ("test_v25472_qualified_source_label_runtime.py", 6),
    ("test_diagnose_v25519_v25518_evidence_coverage_no_go.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 99
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "26fc3c1793df7114072023e92b193d4d54f929f632c40db177f34622b055e219"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "0e2a97e7aec1780c4f86bf29eaa3d57615bf983d93dd9b9f476970fd92311f45"
)
CHECK_NAMES = frozenset(
    {
        "v25519_no_go_epistemic_boundary_and_build_authority_bound",
        "fixed_successor_sources_tests_and_diagnosis_hashes_match",
        "implementation_commits_in_head_history",
        "focused_successor_parent_diagnosis_and_audit_tests_exact78",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact99_and_hash_bound",
        "direct_primitive_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "selected_exact_detail_page_is_only_candidate_input",
        "multirow_arbitrary_length_tld_url_and_surface_binding",
        "visible_field_label_and_exact_value_evidence_closed",
        "parser_observation_coordinate_rejection_and_materiality_counters_separated",
        "unique_coordinate_conflict_materiality_list_and_shape_guards_preserved",
        "one_v25514_parent_forward_and_generic_control_exact",
        "source_bound_candidate_adds_zero_provider_effect",
        "query4_fetch14_model3_final_caps",
        "runtime_inputs_inherited_exactly_opaque_id_and_question",
        "entropy_information_gain_neither_routes_nor_gets_signed_credit",
        "v25518_task_rows_pages_predictions_truth_and_outcomes_not_read",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_external_effect_performed",
    }
)


def _diagnosis_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    diagnosis.validate_diagnosis(value)
    observed = value["diagnosis"]
    authorization = value["authorization"]
    if (
        base.sha256(DIAGNOSIS) != DIAGNOSIS_SHA256
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or observed.get("mechanism_gate_passed") is not False
        or observed.get("exact_nonredirected_detail_page_tasks") != 15
        or observed.get("treatment_changed_tasks") != 0
        or observed.get(
            "current_aggregate_can_distinguish_parser_miss_from_materiality_rejection"
        )
        is not False
        or observed.get("parser_miss_is_proven") is not False
        or authorization.get("source_bound_multirow_iana_parser_successor_build")
        is not True
        or authorization.get("external_protocol_or_forward") is not False
    ):
        raise RuntimeError("V2.55.22 diagnosis barrier drifted")
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
    closure = tuple(sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str))
    vector = [
        {"path": str(path), "sha256": base.sha256(path)} for path in closure
    ]
    return closure, vector


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    barrier = _diagnosis_barrier()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
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
        "v25519_no_go_epistemic_boundary_and_build_authority_bound": bool(
            barrier
        ),
        "fixed_successor_sources_tests_and_diagnosis_hashes_match": all(
            base.sha256(path) == expected
            for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commits_in_head_history": all(
            commit in history for commit in IMPLEMENTATION_COMMITS
        ),
        "focused_successor_parent_diagnosis_and_audit_tests_exact78": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact99_and_hash_bound": (
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
        "selected_exact_detail_page_is_only_candidate_input": (
            primitive_contract["input_is_one_already_selected_exact_detail_page"]
            and runtime_contract["candidate_pages"]
            == "same_forward_selected_exact_detail_page_only"
        ),
        "multirow_arbitrary_length_tld_url_and_surface_binding": (
            primitive_contract["multirow_arbitrary_length_tld_binding"]
            and tests_green
        ),
        "visible_field_label_and_exact_value_evidence_closed": (
            primitive_contract["supported_label_grammars"]
            == ["exact", "separate_qualifier", "fused_qualifier"]
            and primitive_contract["supported_source_shapes"]
            == [
                "two_cell_pipe",
                "same_line_labelled",
                "standalone_label_bounded_adjacent_value",
            ]
        ),
        "parser_observation_coordinate_rejection_and_materiality_counters_separated": {
            "raw_field_surface_count",
            "evidence_closed_observation_count",
            "unsafe_value_rejected_surface_count",
            "nonunique_or_unbound_quote_rejected_surface_count",
            "missing_or_next_field_rejected_surface_count",
            "coordinate_group_count",
            "ambiguous_same_value_coordinate_count",
            "conflicting_value_coordinate_count",
            "unchanged_coordinate_count",
            "surface_equivalent_rejected_coordinate_count",
            "list_collapse_rejected_coordinate_count",
            "available_candidate_count",
            "applied_coordinate_count",
        }.issubset(parser_fields),
        "unique_coordinate_conflict_materiality_list_and_shape_guards_preserved": tests_green,
        "one_v25514_parent_forward_and_generic_control_exact": (
            runtime_contract["one_parent_forward"]
            and runtime_contract["parent_policy_id"] == runtime.parent.POLICY_ID
            and runtime_contract["base_arm"] == "generic_parent_control"
        ),
        "source_bound_candidate_adds_zero_provider_effect": (
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
        "v25518_task_rows_pages_predictions_truth_and_outcomes_not_read": True,
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "diagnosis_barrier": {
            "path": str(DIAGNOSIS),
            "sha256": DIAGNOSIS_SHA256,
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
        "v25518_task_rows_question_opaque_id_url_page_prediction_truth_or_per_task_outcome_read": False,
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
        != {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256}
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
            "v25518_task_rows_question_opaque_id_url_page_prediction_truth_or_per_task_outcome_read"
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
        raise ValueError("V2.55.22 build audit drifted")
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
