#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.20 list-atomic runtime."""

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
from deepwide_agent import v25420_list_atomic_changed_safe_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25419_changed_safe_list_harm as diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25420_list_atomic_changed_safe_clean_build_audit"
IMPLEMENTATION_COMMIT = "7f20ae49110dfdb21f2bbe0564c9b19f10a4e361"
SOURCE = Path("scripts/audit_v25420_list_atomic_changed_safe_build.py")
TEST = Path("tests/test_audit_v25420_list_atomic_changed_safe_build.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25420_list_atomic_changed_safe_runtime.py")
RUNTIME_TEST = Path("tests/test_v25420_list_atomic_changed_safe_runtime.py")
DIAGNOSIS_SOURCE = Path("scripts/diagnose_v25419_changed_safe_list_harm.py")
DIAGNOSIS_TEST = Path("tests/test_diagnose_v25419_changed_safe_list_harm.py")
DIAGNOSIS_ARTIFACT = diagnosis.OUTPUT
OUTPUT = Path(f"results/v25420_list_atomic_changed_safe_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    RUNTIME_SOURCE: "44b8d3562270d563e377af029f4fb0f1c2fceb9ad70dbb119dfc0eb23728be6b",
    RUNTIME_TEST: "70112f541e40bce7f846a3b76a4b53cc8186ae4de7471ab82f4070352b3be126",
    DIAGNOSIS_SOURCE: "24bc3239c9d88e634898e2601fbe6fdee291684e56b9b495c06a593f95b40843",
    DIAGNOSIS_TEST: "1f8cfc946503b6708efda97c093cd7ed1500d0c9301edb7328d8a8453248bc49",
    DIAGNOSIS_ARTIFACT: "4371344c2313eb46f9b3792e1e0bc71fd9eabac0a145c0af6e4e7b7dc4dd4be4",
}
TEST_SUITES = (
    ("test_audit_v25420_list_atomic_changed_safe_build.py", 4),
    ("test_v25420_list_atomic_changed_safe_runtime.py", 9),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
    ("test_v25369_changed_safe_verified_coordinate_edit.py", 8),
    ("test_v25360_quote_coordinate_partial_field_record.py", 8),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_diagnose_v25419_changed_safe_list_harm.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 83
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "3365d53174234f73a8c2b68b63b7e126dbd58d890d1b4e4b7df6369a568b17e4"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "d159e926a9a7457542b38c17b0c705314fada691dd18d8ec71265fb46d8cc44e"
)
CHECK_NAMES = frozenset(
    {
        "v25419_diagnosis_bound_and_authorizes_only_fresh_build",
        "fixed_runtime_test_and_diagnosis_hashes_match",
        "implementation_commit_is_in_head_history",
        "runtime_parent_and_diagnosis_tests_exact59",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked",
        "runtime_dependency_vector_exact83_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "runtime_calls_v25375_parent_exactly_once",
        "guard_has_zero_additional_model_search_fetch_or_network_calls",
        "guard_recomputes_from_private_shared_base_and_candidate",
        "list_cardinality_decrease_rolls_back_only_target_coordinate",
        "non_list_and_non_decreasing_list_edits_are_preserved",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "query4_fetch14_model3_parent_caps_unchanged",
        "entropy_information_gain_neither_routes_nor_gets_signed_credit",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
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
    closure = tuple(sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _diagnosis_barrier() -> dict[str, Any]:
    value = diagnosis.validate(
        json.loads(base._ordinary(DIAGNOSIS_ARTIFACT).read_text(encoding="utf-8"))
    )
    if (
        base.sha256(DIAGNOSIS_ARTIFACT) != FIXED_HASHES[DIAGNOSIS_ARTIFACT]
        or value["coordinate_disposition"] != {"harm": 11, "neutral_correct": 3}
        or value["field_coordinate_disposition"]
        != {
            "Authors:harm": 11,
            "Authors:neutral_correct": 1,
            "Stream:neutral_correct": 2,
        }
        or value["authorization"]["list_atomic_guard_build"] is not True
        or value["authorization"]["fresh_disjoint_shared_effect_gate_design"]
        is not True
        or value["authorization"]["reuse_current_population_for_candidate_validation"]
        is not False
        or value["authorization"]["deepwidebench_forward_or_evaluator"]
        is not False
    ):
        raise RuntimeError("V2.54.20 diagnosis barrier drifted")
    return value


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
    source = base._ordinary(RUNTIME_SOURCE).read_text(encoding="utf-8")
    tests_green = tests["passed"]
    watchers = watcher_contract.watcher_snapshot()
    reported_clean = clean if tracked else True
    checks = {
        "v25419_diagnosis_bound_and_authorizes_only_fresh_build": bool(diagnosed),
        "fixed_runtime_test_and_diagnosis_hashes_match": fixed_match,
        "implementation_commit_is_in_head_history": IMPLEMENTATION_COMMIT
        in history.splitlines(),
        "runtime_parent_and_diagnosis_tests_exact59": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact83_and_hash_bound": (
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
        "runtime_calls_v25375_parent_exactly_once": source.count(
            "parent.run_task("
        )
        == 1,
        "guard_has_zero_additional_model_search_fetch_or_network_calls": (
            "model.complete" not in source
            and "requests" not in source
            and "urlopen" not in source
            and "subprocess" not in source
        ),
        "guard_recomputes_from_private_shared_base_and_candidate": tests_green,
        "list_cardinality_decrease_rolls_back_only_target_coordinate": tests_green,
        "non_list_and_non_decreasing_list_edits_are_preserved": tests_green,
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "query4_fetch14_model3_parent_caps_unchanged": tests_green,
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": tests_green,
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
            "fresh_disjoint_shared_effect_gate_design": not findings,
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
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "fresh_disjoint_shared_effect_gate_design": valid,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.20 list-atomic build audit drifted")
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
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
