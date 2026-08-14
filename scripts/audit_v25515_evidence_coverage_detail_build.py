#!/usr/bin/env python3
"""Clean pushed build audit for the V2.55.13/14 coverage successor."""

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
from deepwide_agent import v25513_evidence_coverage_deficit_selection as selector  # noqa: E402
from deepwide_agent import v25514_evidence_coverage_detail_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25512_v25511_literal_unknown_no_go as diagnosis  # noqa: E402


DATE = "20260814"
ROLE = "v25515_evidence_coverage_detail_clean_build_audit"
IMPLEMENTATION_COMMITS = (
    "5e6a36eb42d3ab1ec76eefbd770442f5e38be621",
    "e9734c195910ad2b44b4bf819f04d99799256683",
)
SOURCE = Path("scripts/audit_v25515_evidence_coverage_detail_build.py")
TEST = Path("tests/test_audit_v25515_evidence_coverage_detail_build.py")
SELECTOR_SOURCE = Path(
    "src/deepwide_agent/v25513_evidence_coverage_deficit_selection.py"
)
SELECTOR_TEST = Path(
    "tests/test_v25513_evidence_coverage_deficit_selection.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25514_evidence_coverage_detail_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25514_evidence_coverage_detail_runtime.py"
)
DIAGNOSIS = diagnosis.OUTPUT
DIAGNOSIS_SHA256 = (
    "1c0e049e81282a3b2332df6143f0d330c210a51e6f11bf6861f664efe730fdd1"
)
OUTPUT = Path(
    f"results/v25515_evidence_coverage_detail_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    SELECTOR_SOURCE: "0c68bee658155d95de91b04f48a9e47fc9608eb6f7da64f36f09db5ed3832fda",
    SELECTOR_TEST: "ccb3daaf16c8e60076b8416622fed5530e91fe5c40dd01176ecd4d7222ac64df",
    RUNTIME_SOURCE: "4ae718b84f99d3b46051faa29362d29b48c7183ca8428cdfecbc896f004e0bd3",
    RUNTIME_TEST: "f1b9f004dfe9176b62911aeaa03e1580f34389abfd3ec69e87b709e66de1cf17",
}
TEST_SUITES = (
    ("test_audit_v25515_evidence_coverage_detail_build.py", 4),
    ("test_v25514_evidence_coverage_detail_runtime.py", 7),
    ("test_v25513_evidence_coverage_deficit_selection.py", 7),
    ("test_v25507_visible_uncertainty_detail_runtime.py", 8),
    ("test_v25506_visible_uncertainty_detail_selection.py", 6),
    ("test_v25499_generic_mechanical_field_candidate.py", 7),
    ("test_v25492_visible_row_key_detail_runtime.py", 7),
    ("test_v25491_visible_row_key_detail_selection.py", 7),
    ("test_v25472_qualified_source_label_runtime.py", 6),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 96
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "fa1ec55e32837fc57dcce3e0e9a6f705f5825dc929a6a2675e4ca062c06c91fb"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "86eaf1e9a85f4a29134900616d3fcd6486387d87369455d670a7abe7f1bfd071"
)
CHECK_NAMES = frozenset(
    {
        "literal_unknown_diagnosis_hash_role_seal_and_build_authority_bound",
        "fixed_successor_source_and_test_hashes_match",
        "implementation_commits_in_head_history",
        "focused_successor_parent_and_audit_tests_exact66",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_and_closure_files_tracked",
        "runtime_dependency_vector_exact96_and_hash_bound",
        "direct_selector_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "parent_public_link_and_per_row_ambiguity_rules_preserved",
        "row_local_missing_source_coordinate_is_only_positive_priority",
        "maximum_deficit_then_stable_table_order_priority_exact",
        "matched_control_uses_parent_pages_only",
        "candidate_adds_at_most_one_exact_detail_page",
        "unique_coordinate_conflict_and_shape_guards_preserved",
        "query4_fetch14_model3_final_caps",
        "candidate_additional_query_and_model_zero_fetch_at_most_one",
        "runtime_inputs_exactly_opaque_id_and_question",
        "entropy_information_gain_gets_zero_signed_credit",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_external_effect_performed",
    }
)


def _diagnosis_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    if (
        base.sha256(DIAGNOSIS) != DIAGNOSIS_SHA256
        or diagnosis.validate_diagnosis(value) != value
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("diagnosis", {}).get(
            "literal_unknown_is_not_a_reliable_epistemic_uncertainty_proxy"
        )
        is not True
        or value.get("authorization", {}).get(
            "evidence_coverage_deficit_successor_build"
        )
        is not True
        or value.get("authorization", {}).get("external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.55.15 literal-unknown diagnosis barrier drifted")
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
        SELECTOR_SOURCE,
        SELECTOR_TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        DIAGNOSIS,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    integration = runtime.integration_contract()
    scheduling = selector.integration_contract()
    snapshot = watchers.watcher_snapshot()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "literal_unknown_diagnosis_hash_role_seal_and_build_authority_bound": bool(
            barrier
        ),
        "fixed_successor_source_and_test_hashes_match": all(
            base.sha256(path) == expected
            for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commits_in_head_history": all(
            commit in history for commit in IMPLEMENTATION_COMMITS
        ),
        "focused_successor_parent_and_audit_tests_exact66": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact96_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_selector_and_runtime_effect_imports_zero": (
            not base._direct_forbidden_imports(SELECTOR_SOURCE)
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
        "parent_public_link_and_per_row_ambiguity_rules_preserved": scheduling[
            "source_admissibility_and_one_url_per_row_inherited"
        ],
        "row_local_missing_source_coordinate_is_only_positive_priority": scheduling[
            "scheduling_signal"
        ]
        == "row_local_missing_unique_source_bound_coordinate_count",
        "maximum_deficit_then_stable_table_order_priority_exact": scheduling[
            "priority"
        ]
        == "maximum_deficit_then_stable_table_order_then_url",
        "matched_control_uses_parent_pages_only": (
            integration["control_pages"] == "same_forward_parent_pages"
            and integration[
                "one_v25472_parent_forward_shared_by_control_and_candidate"
            ]
        ),
        "candidate_adds_at_most_one_exact_detail_page": (
            integration["candidate_pages"]
            == "same_forward_parent_pages_plus_one_exact_detail"
            and integration["maximum_candidate_additional_fetches"] == 1
        ),
        "unique_coordinate_conflict_and_shape_guards_preserved": tests_green,
        "query4_fetch14_model3_final_caps": (
            integration["maximum_total_queries"] == 4
            and integration["maximum_total_fetches"] == 14
            and integration["maximum_normal_path_model_calls"] == 3
        ),
        "candidate_additional_query_and_model_zero_fetch_at_most_one": (
            integration["candidate_additional_queries"] == 0
            and integration["candidate_additional_model_calls"] == 0
            and integration["maximum_candidate_additional_fetches"] == 1
        ),
        "runtime_inputs_exactly_opaque_id_and_question": integration[
            "runtime_input_keys"
        ]
        == ["opaque_id", "question"],
        "entropy_information_gain_gets_zero_signed_credit": (
            integration["entropy_or_information_gain_assigns_signed_credit"]
            is False
            and scheduling[
                "entropy_or_information_gain_assigns_signed_credit"
            ]
            is False
        ),
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
        "selector_contract": scheduling,
        "runtime_contract": integration,
        "effect_delta_beyond_v25472": {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "maximum_fetch_calls": 1,
            "provider_tokens": 0,
        },
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "v25511_task_rows_question_opaque_id_url_page_prediction_truth_or_per_task_outcome_read": False,
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
        or copied.get("effect_delta_beyond_v25472")
        != {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "maximum_fetch_calls": 1,
            "provider_tokens": 0,
        }
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get(
            "v25511_task_rows_question_opaque_id_url_page_prediction_truth_or_per_task_outcome_read"
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
        raise ValueError("V2.55.15 build audit drifted")
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
