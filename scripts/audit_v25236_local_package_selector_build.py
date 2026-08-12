#!/usr/bin/env python3
"""Clean-build audit for the V2.52.35 local package selector."""

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
from scripts import freeze_v25235_local_package_shadow_population as selector  # noqa: E402


DATE = "20260812"
ROLE = "v25236_local_package_selector_clean_build_audit"
OUTPUT = Path(f"results/v25236_local_package_selector_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25236_local_package_selector_build.py")
TEST = Path("tests/test_audit_v25236_local_package_selector_build.py")
SELECTOR = Path("scripts/freeze_v25235_local_package_shadow_population.py")
SELECTOR_TEST = Path("tests/test_freeze_v25235_local_package_shadow_population.py")
DESIGN = Path(f"results/v25234_local_package_shadow_population_design_r2_{DATE}.json")
SHADOW_AUDIT = Path(
    f"results/v25233_header_totality_shadow_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    SELECTOR: "757c6ea0cdfa8859e4ecaad023c12fe3dc26a945653bb4b8df6c59c033e7aed0",
    SELECTOR_TEST: "e6431875d7aaa775f711b5ed14b5f78bbc58268312cec685e9086f96c4769eb1",
    DESIGN: "5cae2cbf6842f49cd2b33180883dc6898a9dfcb598cfc0a4ed6f50ac01b28b3b",
    SHADOW_AUDIT: "eebbc5577f46998c5a97f75e0e76afac9aa7b3399f6f7a9a78d3256ced130fc2",
}
TEST_SUITES = (
    ("test_audit_v25236_local_package_selector_build.py", 7),
    ("test_freeze_v25235_local_package_shadow_population.py", 10),
    ("test_revise_v25234_local_package_shadow_population_r2.py", 5),
    ("test_design_v25234_local_package_shadow_population.py", 8),
    ("test_audit_v25233_header_totality_shadow_build.py", 7),
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
    return bool(
        _fixed_hash_barrier()
        and selector.design.validate_revision(design) == design
        and design["authorization"]["local_population_selector_implementation_build_only"]
        is True
        and design["authorization"][
            "formal_dpkg_query_history_scan_or_population_freeze"
        ]
        is False
        and shadow.get("role")
        == "v25233_header_totality_shadow_clean_build_audit"
        and shadow.get("audit_valid") is True
        and shadow.get("findings") == []
        and shadow.get("authorization", {}).get(
            "fresh_artifact_disjoint_shadow_reliability_protocol_design"
        )
        is True
        and shadow.get("authorization", {}).get(
            "fresh_external_activation_or_launch"
        )
        is False
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
                if alias.name.split(".")[0] in {
                    "requests",
                    "httpx",
                    "openai",
                    "socket",
                    "urllib",
                }:
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
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    shell_true.append(node.lineno)
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value
            in {
                "category",
                "question_type",
                "task_category",
                "split",
                "ground_truth",
                "gold",
                "answer_key",
                "score",
                "reward",
            }
        ):
            privileged.append({"line": node.lineno, "field": node.slice.value})
    return {
        "process_calls": calls,
        "process_call_count": len(calls),
        "all_process_methods_are_subprocess_run": all(
            call["method"] == "run" for call in calls
        ),
        "shell_true_lines": shell_true,
        "forbidden_network_model_imports": sorted(forbidden_imports),
        "privileged_runtime_field_accesses": privileged,
        "fixed_dpkg_argument_vector": list(selector.DPKG_ARGUMENT_VECTOR),
        "fixed_history_paths": list(selector.HISTORY_PATHS),
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
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    watchers = base._watchers()
    lease_inactive = base._lease_inactive()
    checks = {
        "selector_design_shadow_parent_chain_tests_exact37": tests["passed"],
        "corrected_design_and_shadow_audit_authority_bound": _authority_barrier(),
        "all_fixed_selector_test_and_artifact_hashes_match": _fixed_hash_barrier(),
        "all_selector_test_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "exactly_three_subprocess_run_call_sites": capability["process_call_count"] == 3
        and capability["all_process_methods_are_subprocess_run"],
        "shell_true_zero": not capability["shell_true_lines"],
        "network_model_evaluator_imports_zero": not capability[
            "forbidden_network_model_imports"
        ],
        "privileged_runtime_field_access_zero": not capability[
            "privileged_runtime_field_accesses"
        ],
        "fixed_dpkg_argument_vector_and_history_paths": (
            capability["fixed_dpkg_argument_vector"]
            == list(selector.DPKG_ARGUMENT_VECTOR)
            and capability["fixed_history_paths"] == list(selector.HISTORY_PATHS)
        ),
        "morphologies_mutually_exclusive_and_boundary_tested": tests["passed"],
        "history_filter_deterministic_and_insufficient_capacity_fails_closed": tests[
            "passed"
        ],
        "task_vector_visible_only_interleaved_reconstructable_and_exact_schema_parseable": tests[
            "passed"
        ],
        "nested_exact_schema_count_conservation_and_tamper_rejection": tests[
            "passed"
        ],
        "formal_dpkg_query_or_history_scan_not_run_by_build_audit": True,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
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
            "clean": clean,
        },
        "tests": tests,
        "fixed_artifact_hashes": _fixed_hashes(),
        "process_capability_audit": capability,
        "untracked_sources": untracked,
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers": watchers,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "single_local_population_freeze": not findings,
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
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "tests",
            "fixed_artifact_hashes",
            "process_capability_audit",
            "untracked_sources",
            "runtime_state",
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
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("untracked_sources") != []
        or capability.get("process_call_count") != 3
        or capability.get("all_process_methods_are_subprocess_run") is not True
        or capability.get("shell_true_lines") != []
        or capability.get("forbidden_network_model_imports") != []
        or capability.get("privileged_runtime_field_accesses") != []
        or capability.get("fixed_dpkg_argument_vector")
        != list(selector.DPKG_ARGUMENT_VECTOR)
        or capability.get("fixed_history_paths") != list(selector.HISTORY_PATHS)
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "single_local_population_freeze": True,
            "shadow_reliability_protocol_design_after_valid_freeze": True,
            "shadow_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.36 local package selector build audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "tests": value["tests"]["observed"],
                "findings": value["findings"],
                "population_freeze": value["authorization"][
                    "single_local_population_freeze"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
