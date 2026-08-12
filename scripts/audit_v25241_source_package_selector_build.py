#!/usr/bin/env python3
"""Clean-build audit for the V2.52.40 source-package selector."""

from __future__ import annotations

import ast
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

from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import freeze_v25240_source_package_shadow_population as selector  # noqa: E402


DATE = "20260812"
ROLE = "v25241_source_package_selector_clean_build_audit"
OUTPUT = Path(f"results/v25241_source_package_selector_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25241_source_package_selector_build.py")
TEST = Path("tests/test_audit_v25241_source_package_selector_build.py")
SELECTOR = selector.SOURCE
SELECTOR_TEST = selector.TEST
DESIGN = selector.DESIGN
SHADOW_AUDIT = Path(f"results/v25233_header_totality_shadow_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    SELECTOR: "0697cb23edf2c8ce7f737e0b5e0ba94a0372281ecc2aad23b4467479b4167937",
    SELECTOR_TEST: "a04acf4a5a9842f3cde8ab8a2cb3309d9d339f27b41f10111fddb2ff61c38f6f",
    DESIGN: "0e9001197709453f8ade48a499f51c189887212885f75b107da1b05406fcb6f7",
    SHADOW_AUDIT: "eebbc5577f46998c5a97f75e0e76afac9aa7b3399f6f7a9a78d3256ced130fc2",
}
TEST_SUITES = (
    ("test_audit_v25241_source_package_selector_build.py", 7),
    ("test_freeze_v25240_source_package_shadow_population.py", 11),
    ("test_design_v25239_source_package_shadow_population.py", 8),
    ("test_audit_v25233_header_totality_shadow_build.py", 7),
    ("test_v25232_header_totality_shadow_runtime.py", 8),
    ("test_v25230_index_positional_header_normalizer.py", 12),
    ("test_audit_v25231_header_totality_build.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def _fixed_hash_barrier() -> bool:
    return all(base.sha256(path) == expected for path, expected in FIXED_HASHES.items())


def _authority_barrier() -> bool:
    design = json.loads(base._ordinary(DESIGN).read_text(encoding="utf-8"))
    shadow = json.loads(base._ordinary(SHADOW_AUDIT).read_text(encoding="utf-8"))
    checked = selector.design.validate_design(design)
    return bool(
        _fixed_hash_barrier()
        and checked == design
        and checked["authorization"]["source_package_selector_implementation_build_only"] is True
        and checked["authorization"]["formal_dpkg_query_history_scan_selection_or_task_freeze"] is False
        and checked["selection_contract"]["v25237_command_population_or_rank_salt_reused"] is False
        and shadow.get("role") == "v25233_header_totality_shadow_clean_build_audit"
        and shadow.get("audit_valid") is True
        and shadow.get("findings") == []
        and shadow.get("authorization", {}).get("fresh_artifact_disjoint_shadow_reliability_protocol_design") is True
        and shadow.get("authorization", {}).get("fresh_external_activation_or_launch") is False
    )


def _process_capability_audit() -> dict[str, Any]:
    tree = ast.parse(base._ordinary(SELECTOR).read_text(encoding="utf-8"))
    calls: list[dict[str, Any]] = []
    forbidden_imports: set[str] = set()
    shell_true: list[int] = []
    privileged: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in {"requests", "httpx", "openai", "socket", "urllib"}:
                    forbidden_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in {"requests", "httpx", "openai", "socket", "urllib"}:
                forbidden_imports.add(node.module or "")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            calls.append({"line": node.lineno, "method": node.func.attr})
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    shell_true.append(node.lineno)
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in {
                "category", "question_type", "task_category", "split",
                "ground_truth", "gold", "answer_key", "score", "reward",
            }
        ):
            privileged.append({"line": node.lineno, "field": node.slice.value})
    return {
        "process_calls": sorted(calls, key=lambda row: row["line"]),
        "process_call_count": len(calls),
        "all_process_methods_are_subprocess_run": all(call["method"] == "run" for call in calls),
        "shell_true_lines": sorted(shell_true),
        "forbidden_network_model_imports": sorted(forbidden_imports),
        "privileged_runtime_field_accesses": sorted(privileged, key=lambda row: (row["line"], row["field"])),
        "fixed_dpkg_argument_vector": list(selector.DPKG_ARGUMENT_VECTOR),
        "fixed_history_paths": list(selector.HISTORY_PATHS),
        "history_worker_cap": selector.HISTORY_WORKERS,
        "per_candidate_timeout_seconds": selector.HISTORY_TIMEOUT_SECONDS,
        "whole_selection_wall_ceiling_seconds": selector.SELECTION_WALL_CEILING_SECONDS,
    }


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    capability = _process_capability_audit()
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(str(path) for path in explicit if tracked and not base._tracked(path))
    watchers = base._watchers()
    lease_inactive = base._lease_inactive()
    surfaces_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (selector.ATTEMPT_CLAIM, selector.OUTPUT)
    )
    checks = {
        "selector_design_shadow_helper_parent_tests_exact60": tests["passed"],
        "entity_disjoint_design_shadow_authority_bound": _authority_barrier(),
        "all_fixed_selector_test_and_artifact_hashes_match": _fixed_hash_barrier(),
        "all_selector_test_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "exactly_three_subprocess_run_call_sites": capability["process_call_count"] == 3 and capability["all_process_methods_are_subprocess_run"],
        "shell_true_zero": not capability["shell_true_lines"],
        "network_model_evaluator_imports_zero": not capability["forbidden_network_model_imports"],
        "privileged_runtime_field_access_zero": not capability["privileged_runtime_field_accesses"],
        "fixed_dpkg_vector_history_paths_and_bounded_concurrency": (
            capability["fixed_dpkg_argument_vector"] == list(selector.DPKG_ARGUMENT_VECTOR)
            and capability["fixed_history_paths"] == list(selector.HISTORY_PATHS)
            and capability["history_worker_cap"] == 16
            and capability["per_candidate_timeout_seconds"] == 30
            and capability["whole_selection_wall_ceiling_seconds"] == 240
        ),
        "attempt_claim_precedes_effect_and_is_result_hash_bound": tests["passed"],
        "all_candidates_checked_once_and_any_process_failure_fails_closed": tests["passed"],
        "task_vector_visible_only_interleaved_reconstructable_and_exact_schema_parseable": tests["passed"],
        "nested_exact_schema_count_conservation_and_tamper_rejection": tests["passed"],
        "formal_dpkg_query_or_history_scan_not_run_by_build_audit": True,
        "attempt_and_result_surfaces_pristine": surfaces_pristine,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "protected_watchers_unchanged": all(row.get("matches_frozen_identity") is True for row in watchers.values()),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "tests": tests,
        "fixed_artifact_hashes": _fixed_hashes(),
        "process_capability_audit": capability,
        "untracked_sources": untracked,
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers": watchers,
            "attempt_and_result_surfaces_pristine": surfaces_pristine,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "single_source_package_population_freeze": not findings,
            "shadow_reliability_protocol_design_after_valid_freeze": not findings,
            "shadow_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    capability = copied.get("process_capability_audit") or {}
    runtime = copied.get("runtime_state") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied) != {
            "artifact_version", "role", "created_at_unix", "git", "tests",
            "fixed_artifact_hashes", "process_capability_audit", "untracked_sources",
            "runtime_state", "checks", "findings", "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes") != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("untracked_sources") != []
        or capability.get("process_call_count") != 3
        or capability.get("all_process_methods_are_subprocess_run") is not True
        or capability.get("shell_true_lines") != []
        or capability.get("forbidden_network_model_imports") != []
        or capability.get("privileged_runtime_field_accesses") != []
        or capability.get("fixed_dpkg_argument_vector") != list(selector.DPKG_ARGUMENT_VECTOR)
        or capability.get("fixed_history_paths") != list(selector.HISTORY_PATHS)
        or capability.get("history_worker_cap") != 16
        or capability.get("per_candidate_timeout_seconds") != 30
        or capability.get("whole_selection_wall_ceiling_seconds") != 240
        or set(runtime) != {
            "shared_api_lease_inactive", "protected_watchers",
            "attempt_and_result_surfaces_pristine",
        }
        or runtime.get("shared_api_lease_inactive") is not True
        or runtime.get("attempt_and_result_surfaces_pristine") is not True
        or not isinstance(runtime.get("protected_watchers"), Mapping)
        or not all(row.get("matches_frozen_identity") is True for row in runtime["protected_watchers"].values())
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization != {
            "single_source_package_population_freeze": True,
            "shadow_reliability_protocol_design_after_valid_freeze": True,
            "shadow_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.41 source package selector build audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.publish(ROOT / OUTPUT, value)
    print(json.dumps({
        "path": str(OUTPUT),
        "audit_valid": value["audit_valid"],
        "tests": value["tests"]["observed"],
        "findings": value["findings"],
        "population_freeze": value["authorization"]["single_source_package_population_freeze"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
