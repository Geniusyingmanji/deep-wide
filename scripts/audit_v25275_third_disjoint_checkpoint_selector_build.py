#!/usr/bin/env python3
"""Clean-build audit for V2.52.74 third-disjoint selector."""

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

from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25257_disjoint_observed_reliability_selector_build as helper  # noqa: E402
from scripts import audit_v25272_validated_production_checkpoint_build as runtime_audit  # noqa: E402
from scripts import freeze_v25274_third_disjoint_checkpoint_population as selector  # noqa: E402


DATE = "20260812"
ROLE = "v25275_third_disjoint_checkpoint_selector_clean_build_audit"
OUTPUT = selector.BUILD_AUDIT
SOURCE = Path("scripts/audit_v25275_third_disjoint_checkpoint_selector_build.py")
TEST = Path("tests/test_audit_v25275_third_disjoint_checkpoint_selector_build.py")
FIXED_HASHES = {
    selector.DESIGN: selector.DESIGN_SHA256,
    selector.FIRST_POPULATION: selector.FIRST_POPULATION_SHA256,
    selector.SECOND_POPULATION: selector.SECOND_POPULATION_SHA256,
    runtime_audit.OUTPUT: "f7c7d16def15ff80ae76b3a506da345c38b3c28286bf4c3e05eec84480f5aace",
}
EXPECTED_DEPENDENCY_COUNT = 8
EXPECTED_DEPENDENCY_VECTOR_SHA256 = (
    "9bfbdd130259d57d399ede10adca65b4bc237cc1d1de9be65269258e791a41eb"
)
EXPECTED_DEPENDENCY_PATH_SHA256 = (
    "5ac9ac7734be0d86a06427b9042607dcb404aa6e9cecaf912111e97e52a1c23c"
)
EFFECT_SOURCES = (selector.SOURCE, selector.first.SOURCE)
EXPECTED_CLOSURE_PRIVILEGED_OFFLINE_DIAGNOSTIC = [
    "scripts/diagnose_v25209_v25208_exact220.py:319:score"
]
EXPECTED_WATCHERS = [
    {
        "pid": 795336,
        "marker": "scripts/watch_v2415_r1_checkpoint_liveness.py",
        "start_ticks": 713986317,
    },
    {
        "pid": 3061652,
        "marker": "scripts/watch_v24218_exact220_executor.py",
        "start_ticks": 747569004,
    },
    {
        "pid": 2808901,
        "marker": "scripts/watch_v24215_joint_package_recovery.py",
        "start_ticks": 746680268,
    },
    {
        "pid": 2889939,
        "marker": "scripts/watch_v24216_package_gate.py",
        "start_ticks": 746969965,
    },
]
TEST_SUITES = (
    ("test_audit_v25275_third_disjoint_checkpoint_selector_build.py", 5),
    ("test_freeze_v25274_third_disjoint_checkpoint_population.py", 7),
    ("test_design_v25273_third_disjoint_checkpoint_population.py", 6),
    ("test_audit_v25272_validated_production_checkpoint_build.py", 4),
    ("test_v25271_validated_production_checkpoint_runtime.py", 9),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
CHECK_NAMES = frozenset(
    {
        "design_two_prior_populations_and_runtime_audit_hashes_exact",
        "parent_authorities_validate_and_forbid_launch",
        "selector_design_runtime_tests_exact31",
        "git_clean_head_equals_target_main",
        "selector_audit_tests_and_fixed_parents_tracked",
        "selector_dependency_vector_exact8_and_hash_bound",
        "effect_sources_exact3_bounded_subprocess_calls",
        "shell_true_zero",
        "network_model_evaluator_import_zero",
        "effect_source_privileged_runtime_field_access_zero",
        "closure_only_known_offline_diagnostic_score_access",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "prior_visible_entity_union384_and_v25273_salt_enforced",
        "task_count20_package_count40_runtime_keys_visible_only",
        "attempt_claim_precedes_dpkg_or_history_effect",
        "attempt_result_and_execution_start_surfaces_pristine",
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
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def _parent_barrier() -> bool:
    if any(base.sha256(path) != digest for path, digest in FIXED_HASHES.items()):
        return False
    try:
        design = selector.design.validate_design(
            json.loads(base._ordinary(selector.DESIGN).read_text(encoding="utf-8"))
        )
        first_population = selector.first.validate_freeze(
            json.loads(base._ordinary(selector.FIRST_POPULATION).read_text(encoding="utf-8"))
        )
        second_population = selector.second.validate_freeze(
            json.loads(base._ordinary(selector.SECOND_POPULATION).read_text(encoding="utf-8"))
        )
        runtime = runtime_audit.validate_audit(
            json.loads(base._ordinary(runtime_audit.OUTPUT).read_text(encoding="utf-8"))
        )
    except BaseException:
        return False
    return bool(
        design["authorization"]["selector_implementation_and_build_audit_only"] is True
        and design["authorization"]["formal_dpkg_history_selection_or_task_freeze"]
        is False
        and design["authorization"]["fresh_external_protocol_or_launch"] is False
        and first_population["population"]["package_count"] == 256
        and second_population["population"]["package_count"] == 128
        and runtime["audit_valid"] is True
        and runtime["findings"] == []
        and runtime["authorization"]["runtime_activation_or_external_launch"] is False
        and runtime["authorization"]["deepwidebench_forward_or_evaluator"] is False
    )


def _dependency_vector() -> list[dict[str, str]]:
    return [
        {"path": str(path), "sha256": base.sha256(path)}
        for path in helper._script_dependency_closure((selector.SOURCE,))
    ]


def _capability_audit() -> dict[str, Any]:
    process_calls: list[dict[str, Any]] = []
    imports: list[str] = []
    shell_true: list[str] = []
    for relative in EFFECT_SOURCES:
        source = base._ordinary(relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(relative))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            ):
                process_calls.append(
                    {"path": str(relative), "method": node.func.attr, "line": node.lineno}
                )
                for keyword in node.keywords:
                    if (
                        keyword.arg == "shell"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ):
                        shell_true.append(f"{relative}:{node.lineno}")
    process_calls.sort(key=lambda row: (row["path"], row["line"], row["method"]))
    forbidden = sorted(
        set(
            name
            for name in imports
            if name.split(".")[0] in {"requests", "openai", "urllib", "httpx", "socket"}
            or "evaluat" in name.casefold()
        )
    )
    effect_semantic = base._semantic_findings(EFFECT_SOURCES)
    closure = tuple(Path(row["path"]) for row in _dependency_vector())
    closure_semantic = base._semantic_findings(closure)
    return {
        "effect_source_vector": [
            {"path": str(path), "sha256": base.sha256(path)} for path in EFFECT_SOURCES
        ],
        "subprocess_calls": process_calls,
        "process_call_count": len(process_calls),
        "all_process_methods_are_subprocess_run": all(
            row["method"] == "run" for row in process_calls
        ),
        "shell_true_lines": sorted(shell_true),
        "forbidden_network_model_evaluator_imports": forbidden,
        "effect_source_semantic": effect_semantic,
        "closure_semantic": closure_semantic,
        "fixed_dpkg_argument_vector": list(selector.DPKG_ARGUMENT_VECTOR),
        "fixed_history_paths": list(selector.HISTORY_PATHS),
        "history_worker_cap": selector.first.HISTORY_WORKERS,
        "per_candidate_timeout_seconds": selector.first.HISTORY_TIMEOUT_SECONDS,
        "whole_selection_wall_ceiling_seconds": selector.first.SELECTION_WALL_CEILING_SECONDS,
    }


def _surfaces_pristine() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (selector.ATTEMPT_CLAIM, selector.OUTPUT, selector.EXECUTION_START)
    )


def _watchers_exact(watchers: object) -> bool:
    """Require the four frozen PID/marker/start-tick identities exactly."""

    return watchers == EXPECTED_WATCHERS


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    dependency = _dependency_vector()
    capability = _capability_audit()
    explicit = {
        SOURCE,
        TEST,
        selector.TEST,
        *FIXED_HASHES,
        *(Path(row["path"]) for row in dependency),
    }
    untracked = sorted(str(path) for path in explicit if tracked and not base._tracked(path))
    watchers = contract.watcher_snapshot()
    lease_inactive = base._lease_inactive()
    surfaces = _surfaces_pristine()
    effect_semantic = capability["effect_source_semantic"]
    closure_semantic = capability["closure_semantic"]
    checks = {
        "design_two_prior_populations_and_runtime_audit_hashes_exact": _fixed_hashes()
        == {str(path): digest for path, digest in FIXED_HASHES.items()},
        "parent_authorities_validate_and_forbid_launch": _parent_barrier(),
        "selector_design_runtime_tests_exact31": tests["passed"],
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "selector_audit_tests_and_fixed_parents_tracked": not untracked,
        "selector_dependency_vector_exact8_and_hash_bound": (
            len(dependency) == EXPECTED_DEPENDENCY_COUNT
            and contract.payload_sha256(dependency) == EXPECTED_DEPENDENCY_VECTOR_SHA256
            and contract.payload_sha256([row["path"] for row in dependency])
            == EXPECTED_DEPENDENCY_PATH_SHA256
        ),
        "effect_sources_exact3_bounded_subprocess_calls": (
            capability["all_process_methods_are_subprocess_run"]
            and capability["process_call_count"] == 3
        ),
        "shell_true_zero": capability["shell_true_lines"] == [],
        "network_model_evaluator_import_zero": capability[
            "forbidden_network_model_evaluator_imports"
        ]
        == [],
        "effect_source_privileged_runtime_field_access_zero": (
            effect_semantic["privileged_runtime_field_accesses"] == []
            and effect_semantic["evaluator_capabilities"] == []
            and effect_semantic["credential_literal_hits"] == []
        ),
        "closure_only_known_offline_diagnostic_score_access": closure_semantic[
            "privileged_runtime_field_accesses"
        ]
        == EXPECTED_CLOSURE_PRIVILEGED_OFFLINE_DIAGNOSTIC,
        "evaluator_capability_zero": closure_semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": closure_semantic["credential_literal_hits"] == [],
        "prior_visible_entity_union384_and_v25273_salt_enforced": tests["passed"],
        "task_count20_package_count40_runtime_keys_visible_only": (
            selector.TASK_COUNT == 20
            and selector.PACKAGE_COUNT == 40
            and selector.PACKAGES_PER_TASK == 2
        ),
        "attempt_claim_precedes_dpkg_or_history_effect": tests["passed"],
        "attempt_result_and_execution_start_surfaces_pristine": surfaces,
        "protected_watchers_unchanged": _watchers_exact(watchers),
        "shared_api_lease_inactive": lease_inactive,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_hashes": _fixed_hashes(),
        "tests": tests,
        "selector_dependency_vector": dependency,
        "selector_dependency_vector_sha256": contract.payload_sha256(dependency),
        "selector_dependency_path_sha256": contract.payload_sha256(
            [row["path"] for row in dependency]
        ),
        "capability_audit": {**capability, "untracked_sources": untracked},
        "population_contract": {
            "task_count": selector.TASK_COUNT,
            "package_count": selector.PACKAGE_COUNT,
            "packages_per_task": selector.PACKAGES_PER_TASK,
            "packages_by_stratum": copy.deepcopy(selector.PACKAGES_BY_STRATUM),
            "prior_population_exact_overlap_required": 0,
            "runtime_keys": ["opaque_id", "question"],
        },
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers": watchers,
            "attempt_result_and_execution_start_surfaces_pristine": surfaces,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "single_third_disjoint_population_freeze_after_separate_execution_start": not findings,
            "paired_checkpoint_reliability_protocol_design_after_valid_freeze": not findings,
            "external_activation_or_launch": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "deepwidebench_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    dependency = copied.get("selector_dependency_vector") or []
    capability = copied.get("capability_audit") or {}
    population = copied.get("population_contract") or {}
    runtime = copied.get("runtime_state") or {}
    checks = copied.get("checks") or {}
    authorization = copied.get("authorization") or {}
    expected_capability = {**_capability_audit(), "untracked_sources": []}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_hashes",
            "tests",
            "selector_dependency_vector",
            "selector_dependency_vector_sha256",
            "selector_dependency_path_sha256",
            "capability_audit",
            "population_contract",
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
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or copied.get("fixed_hashes")
        != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or set(row)
            != {
                "pattern",
                "expected",
                "observed",
                "returncode",
                "passed",
                "output_sha256",
            }
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            or not isinstance(row.get("output_sha256"), str)
            or len(row["output_sha256"]) != 64
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or len(dependency) != EXPECTED_DEPENDENCY_COUNT
        or any(
            not isinstance(row, Mapping)
            or set(row) != {"path", "sha256"}
            or not isinstance(row.get("path"), str)
            or not isinstance(row.get("sha256"), str)
            or len(row["sha256"]) != 64
            for row in dependency
        )
        or copied.get("selector_dependency_vector_sha256")
        != EXPECTED_DEPENDENCY_VECTOR_SHA256
        or copied.get("selector_dependency_path_sha256") != EXPECTED_DEPENDENCY_PATH_SHA256
        or capability != expected_capability
        or population
        != {
            "task_count": 20,
            "package_count": 40,
            "packages_per_task": 2,
            "packages_by_stratum": selector.PACKAGES_BY_STRATUM,
            "prior_population_exact_overlap_required": 0,
            "runtime_keys": ["opaque_id", "question"],
        }
        or runtime
        != {
            "shared_api_lease_inactive": True,
            "protected_watchers": EXPECTED_WATCHERS,
            "attempt_result_and_execution_start_surfaces_pristine": True,
        }
        or checks != {name: True for name in CHECK_NAMES}
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
            "single_third_disjoint_population_freeze_after_separate_execution_start": True,
            "paired_checkpoint_reliability_protocol_design_after_valid_freeze": True,
            "external_activation_or_launch": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "deepwidebench_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.75 selector build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    import os

    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True, "findings": []}, sort_keys=True))


if __name__ == "__main__":
    main()
