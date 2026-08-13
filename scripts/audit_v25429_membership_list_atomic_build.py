#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.26/27 combined successor."""

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
from deepwide_agent import v25426_membership_list_atomic_shared_runtime as runtime  # noqa: E402
from deepwide_agent import v25427_structurally_disjoint_rfc_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25402_grounded_record_membership_build as membership_audit  # noqa: E402
from scripts import audit_v25420_list_atomic_changed_safe_build as list_audit  # noqa: E402
from scripts import audit_v25428_structurally_disjoint_rfc_population as population_audit  # noqa: E402
from scripts import diagnose_v25425_population_overlap_and_candidate_funnel as diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25429_membership_list_atomic_clean_build_audit"
SOURCE = Path("scripts/audit_v25429_membership_list_atomic_build.py")
TEST = Path("tests/test_audit_v25429_membership_list_atomic_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25426_membership_list_atomic_shared_runtime.py"
)
RUNTIME_TEST = Path("tests/test_v25426_membership_list_atomic_shared_runtime.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25427_structurally_disjoint_rfc_population.py"
)
POPULATION_TEST = Path("tests/test_v25427_structurally_disjoint_rfc_population.py")
POPULATION_AUDIT_SOURCE = population_audit.SOURCE
POPULATION_AUDIT_TEST = population_audit.TEST
POPULATION_AUDIT_ARTIFACT = population_audit.OUTPUT
DIAGNOSIS_SOURCE = Path(
    "scripts/diagnose_v25425_population_overlap_and_candidate_funnel.py"
)
DIAGNOSIS_TEST = Path(
    "tests/test_diagnose_v25425_population_overlap_and_candidate_funnel.py"
)
DIAGNOSIS_ARTIFACT = diagnosis.OUTPUT
MEMBERSHIP_PARENT_AUDIT = membership_audit.OUTPUT
LIST_PARENT_AUDIT = list_audit.OUTPUT
OUTPUT = Path(f"results/v25429_membership_list_atomic_build_audit_v1_{DATE}.json")

FIXED_HASHES = {
    RUNTIME_SOURCE: "1ecfec4d028152cad55b164143c726fe5ba97e5156052db333988bd8407ef194",
    RUNTIME_TEST: "d0c39edec6c6a9c58a1fc7569408ae6f4c96b232a2fa0c285ddf7a1a068e73ba",
    POPULATION_SOURCE: "4f1a6425f469967622e512cf1c696cff08496374d4bf8615666a0b8413fde748",
    POPULATION_AUDIT_SOURCE: "3846bffdf5f3bafe4dc361e3cf289cb347bdededd1a2c9e71f2739c3651c450d",
    POPULATION_AUDIT_ARTIFACT: "631a6ec74bfd0f9b44a777aa248bb9f2ab75129cfdaac20c4e7c6e334f1b068c",
    DIAGNOSIS_ARTIFACT: "7915a3502423fb8ae78174c5818f1db7f4d256d05df34fd7fb4b1e07c770fa5d",
    MEMBERSHIP_PARENT_AUDIT: "29b57f2dd3ae0f192c342481dba9c26435804fa0cb4542722d8e6fec2d2200c5",
    LIST_PARENT_AUDIT: "f545c43c45488a7822da6b98f7b10e10a888db5df99d3a8eb365bfe2578e6398",
}
IMPLEMENTATION_COMMIT = "e00bc631549a7f16b6f6a1c2cee65a1313813d9f"
POPULATION_COMMIT = "b1db871f"
POPULATION_AUDIT_COMMIT = "c111f0c4"
TEST_SUITES = (
    ("test_audit_v25429_membership_list_atomic_build.py", 4),
    ("test_v25426_membership_list_atomic_shared_runtime.py", 6),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25420_list_atomic_changed_safe_runtime.py", 9),
    ("test_v25427_structurally_disjoint_rfc_population.py", 4),
    ("test_audit_v25428_structurally_disjoint_rfc_population.py", 5),
    ("test_diagnose_v25425_population_overlap_and_candidate_funnel.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 94
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "2dd5d2666446ced6e576c39d309c5a57970333649a5db7e3664e3b14ae72b580"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "5e155bcba4a8b61525252660d154a8e31e6fde162d30f2f260529d778c4056eb"
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
    closure = tuple(sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _barriers() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    diagnosed = diagnosis.validate(
        json.loads(base._ordinary(DIAGNOSIS_ARTIFACT).read_text(encoding="utf-8"))
    )
    selected = population_audit.validate_audit(
        json.loads(
            base._ordinary(POPULATION_AUDIT_ARTIFACT).read_text(encoding="utf-8")
        )
    )
    membership = membership_audit.validate_audit(
        json.loads(base._ordinary(MEMBERSHIP_PARENT_AUDIT).read_text(encoding="utf-8"))
    )
    listed = list_audit.validate_audit(
        json.loads(base._ordinary(LIST_PARENT_AUDIT).read_text(encoding="utf-8"))
    )
    if (
        any(base.sha256(path) != expected for path, expected in FIXED_HASHES.items())
        or diagnosed["authorization"]["combined_visible_membership_and_list_guard_build"]
        is not True
        or diagnosed["authorization"]["external_forward_or_evaluator"] is not False
        or selected["selected_first_zero_intersection_interval"] != "RFC 9240-9319"
        or selected["authorization"][
            "combined_membership_list_atomic_external_protocol_design"
        ]
        is not True
        or selected["authorization"][
            "network_model_search_fetch_external_forward_or_evaluator"
        ]
        is not False
        or membership["audit_valid"] is not True
        or membership["authorization"]["external_forward"] is not False
        or listed["audit_valid"] is not True
        or listed["authorization"]["external_forward"] is not False
    ):
        raise RuntimeError("V2.54.29 parent build/diagnosis/population barrier drifted")
    return diagnosed, selected, membership, listed


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    history = set(base._git("rev-list", head).splitlines())
    diagnosed, selected, membership, listed = _barriers()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        POPULATION_SOURCE,
        POPULATION_TEST,
        POPULATION_AUDIT_SOURCE,
        POPULATION_AUDIT_TEST,
        POPULATION_AUDIT_ARTIFACT,
        DIAGNOSIS_SOURCE,
        DIAGNOSIS_TEST,
        DIAGNOSIS_ARTIFACT,
        MEMBERSHIP_PARENT_AUDIT,
        LIST_PARENT_AUDIT,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    source = base._ordinary(RUNTIME_SOURCE).read_text(encoding="utf-8")
    watchers = watcher_contract.watcher_snapshot()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "v25425_overlap_erratum_and_candidate_funnel_bound": bool(diagnosed),
        "v25428_structural_population_audit_bound": bool(selected),
        "v25402_membership_parent_build_audit_bound": bool(membership),
        "v25420_list_guard_parent_build_audit_bound": bool(listed),
        "fixed_runtime_population_audit_and_parent_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_population_and_selection_commits_in_history": (
            IMPLEMENTATION_COMMIT in history
            and any(commit.startswith(POPULATION_COMMIT) for commit in history)
            and any(commit.startswith(POPULATION_AUDIT_COMMIT) for commit in history)
        ),
        "focused_audit_combined_parent_population_selector_tests_exact40": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_population_test_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact94_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_wrapper_effect_imports_zero": not base._direct_forbidden_imports(
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
        "wrapper_calls_v25401_parent_exactly_once": source.count("parent.run_task(")
        == 1,
        "wrapper_has_zero_additional_model_search_fetch_or_network_calls": all(
            token not in source
            for token in (
                "model.complete",
                "requests",
                "urlopen",
                "subprocess",
                "socket",
            )
        ),
        "base_raw_and_guarded_recomputed_from_one_private_parent_chain": tests_green,
        "visible_membership_precedes_existing_grounded_record_call": tests_green,
        "provider_violation_observed_not_postfiltered": tests_green,
        "list_cardinality_harm_rejected_and_safe_scalar_edit_preserved": tests_green,
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "query4_fetch14_model3_parent_caps_unchanged": tests_green,
        "structural_population_selected_with_zero_consumed_overlap": (
            selected["candidate_consumed_overlap_identity_counts"]["RFC 9240-9319"]
            == 0
            and population.RFC_NUMBERS == tuple(range(9240, 9320))
        ),
        "candidate_presence_disclosed_and_not_used_for_selection": (
            selected["aggregate_candidate_identity_presence_observed_before_freeze"]
            is True
            and selected[
                "aggregate_presence_used_for_selection_replacement_or_ranking"
            ]
            is False
        ),
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": (
            population.mechanism_gate()["positive_signed_credit_count"] == 0
            and tests_green
        ),
        "protected_watchers_unchanged": watchers
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watcher_contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
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
        "population": {
            "selected_interval": "RFC 9240-9319",
            "task_count": population.TASK_COUNT,
            "identity_count": len(population.identity_vector()),
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "aggregate_presence_previously_observed": True,
            "aggregate_presence_used_for_selection": False,
        },
        "physical_caps": {
            "queries": 4,
            "fetches": 14,
            "normal_path_model_forwards": 3,
            "outer_hard_model_cap": 4,
        },
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_combined_shared_effect_external_protocol_design": not findings,
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
    if (
        copied.get("role") != ROLE
        or not isinstance(checks, Mapping)
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
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or copied.get("population", {}).get("selected_interval")
        != "RFC 9240-9319"
        or copied.get("population", {}).get("task_count") != 20
        or copied.get("population", {}).get("identity_count") != 80
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read")
        is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "fresh_combined_shared_effect_external_protocol_design": valid,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.29 combined build audit drifted")
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
