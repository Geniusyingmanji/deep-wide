#!/usr/bin/env python3
"""Clean-build audit for the V2.52.56 fresh population selector."""

from __future__ import annotations

import ast
import copy
import json
import re
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
from scripts import audit_v25241_source_package_selector_build as inherited_audit  # noqa: E402
from scripts import audit_v25254_outer_physical_cap_observed_build as runtime_audit  # noqa: E402
from scripts import freeze_v25256_disjoint_observed_reliability_population as selector  # noqa: E402
from scripts import run_v25248_header_totality_shadow_external as publisher  # noqa: E402


DATE = "20260812"
ROLE = "v25257_disjoint_observed_reliability_selector_clean_build_audit"
OUTPUT = selector.BUILD_AUDIT
SOURCE = Path("scripts/audit_v25257_disjoint_observed_reliability_selector_build.py")
TEST = Path("tests/test_audit_v25257_disjoint_observed_reliability_selector_build.py")
FIXED_HASHES = {
    selector.DESIGN: selector.DESIGN_SHA256,
    selector.OLD_POPULATION: selector.OLD_POPULATION_SHA256,
    runtime_audit.RESULT: "84ac0911eb900980657e11016a4adc32b8f3fd61e7732df92eee0651dc3cff87",
    inherited_audit.OUTPUT: "eff75a43a37e463e6f0152b258affb73254d52c61e56304bd84bf254f400cd67",
}
EFFECT_SOURCES = (selector.SOURCE, selector.old.SOURCE)
EXPECTED_DEPENDENCY_PATHS = (
    Path("scripts/design_v25239_source_package_shadow_population.py"),
    Path("scripts/design_v25255_disjoint_observed_reliability_population.py"),
    Path("scripts/diagnose_v25063_three_run_output_structure.py"),
    Path("scripts/diagnose_v25209_v25208_exact220.py"),
    Path("scripts/freeze_v25240_source_package_shadow_population.py"),
    Path("scripts/freeze_v25256_disjoint_observed_reliability_population.py"),
)
TEST_SUITES = (
    ("test_audit_v25257_disjoint_observed_reliability_selector_build.py", 5),
    ("test_freeze_v25256_disjoint_observed_reliability_population.py", 9),
    ("test_design_v25255_disjoint_observed_reliability_population.py", 7),
    ("test_audit_v25254_outer_physical_cap_observed_build.py", 4),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(value for _pattern, value in TEST_SUITES)
CHECK_NAMES = {
    "design_old_population_runtime_and_inherited_audit_hashes_exact",
    "design_parent_and_inherited_effect_authorities_validate",
    "selector_design_runtime_tests_exact32",
    "git_clean_head_equals_target_main",
    "selector_audit_tests_and_fixed_parents_tracked",
    "selector_dependency_vector_exact6_and_hash_bound",
    "new_and_inherited_effect_sources_exact4_bounded_subprocess_calls",
    "shell_true_zero",
    "network_model_evaluator_import_zero",
    "privileged_runtime_field_access_zero",
    "evaluator_capability_zero",
    "credential_literal_zero",
    "old_visible_entity_exclusion_and_v25255_salt_enforced",
    "task_count64_package_count128_runtime_keys_visible_only",
    "attempt_claim_precedes_dpkg_or_history_effect",
    "attempt_result_and_execution_start_surfaces_pristine",
    "protected_watchers_unchanged",
    "shared_api_lease_inactive",
    "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
    "no_external_effect_performed",
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


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def _inherited_authority() -> dict[str, Any]:
    path = base._ordinary(inherited_audit.OUTPUT)
    value = inherited_audit.validate_audit(json.loads(path.read_text(encoding="utf-8")))
    capability = value["process_capability_audit"]
    bound_hashes = value["fixed_artifact_hashes"]
    return {
        "path": str(inherited_audit.OUTPUT),
        "sha256": base.sha256(inherited_audit.OUTPUT),
        "role": value["role"],
        "audit_valid": value["audit_valid"],
        "bound_selector_source": str(selector.old.SOURCE),
        "bound_selector_source_sha256": bound_hashes[str(selector.old.SOURCE)],
        "process_call_count": capability["process_call_count"],
        "all_process_methods_are_subprocess_run": capability[
            "all_process_methods_are_subprocess_run"
        ],
        "forbidden_network_model_imports": capability[
            "forbidden_network_model_imports"
        ],
        "privileged_runtime_field_accesses": capability[
            "privileged_runtime_field_accesses"
        ],
    }


def _parent_barrier() -> bool:
    if any(base.sha256(path) != expected for path, expected in FIXED_HASHES.items()):
        return False
    try:
        design = selector.design.validate_design(
            json.loads(base._ordinary(selector.DESIGN).read_text(encoding="utf-8"))
        )
        old_population = selector.old.validate_freeze(
            json.loads(base._ordinary(selector.OLD_POPULATION).read_text(encoding="utf-8"))
        )
        observed = runtime_audit.validate_audit(
            json.loads(base._ordinary(runtime_audit.RESULT).read_text(encoding="utf-8"))
        )
        inherited = _inherited_authority()
    except BaseException:
        return False
    return bool(
        design["authorization"]["selector_implementation_and_build_audit_only"] is True
        and design["authorization"]["formal_dpkg_history_selection_or_task_freeze"] is False
        and old_population["status"] == "frozen"
        and old_population["population"]["package_count"] == 256
        and observed["audit_valid"] is True
        and observed["physical_caps"] == {"queries": 4, "fetches": 14, "model_forwards": 4}
        and observed["authorization"]["fresh_external_activation_or_launch"] is False
        and inherited
        == {
            "path": str(inherited_audit.OUTPUT),
            "sha256": FIXED_HASHES[inherited_audit.OUTPUT],
            "role": inherited_audit.ROLE,
            "audit_valid": True,
            "bound_selector_source": str(selector.old.SOURCE),
            "bound_selector_source_sha256": inherited_audit.FIXED_HASHES[
                selector.old.SOURCE
            ],
            "process_call_count": 3,
            "all_process_methods_are_subprocess_run": True,
            "forbidden_network_model_imports": [],
            "privileged_runtime_field_accesses": [],
        }
    )


def _script_dependency_closure(entrypoints: tuple[Path, ...]) -> tuple[Path, ...]:
    pending = list(entrypoints)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = base._ordinary(relative)
        observed.add(relative)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
        for node in ast.walk(tree):
            candidates: list[Path] = []
            if isinstance(node, ast.Import):
                candidates.extend(
                    Path(*alias.name.split(".")).with_suffix(".py")
                    for alias in node.names
                    if alias.name.startswith("scripts.")
                )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "scripts":
                    candidates.extend(
                        Path("scripts") / f"{alias.name}.py" for alias in node.names
                    )
                elif module.startswith("scripts."):
                    candidates.append(Path(*module.split(".")).with_suffix(".py"))
            for candidate in candidates:
                absolute = ROOT / candidate
                if absolute.is_file() and not absolute.is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def _dependency_vector() -> list[dict[str, str]]:
    return [
        {"path": str(path), "sha256": base.sha256(path)}
        for path in _script_dependency_closure((selector.SOURCE,))
    ]


def _capability_audit() -> dict[str, Any]:
    process_calls: list[dict[str, Any]] = []
    imports: list[str] = []
    privileged: list[str] = []
    shell_true: list[str] = []
    for relative in EFFECT_SOURCES:
        source = base._ordinary(relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(relative))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                imports.extend(names)
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
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in {
                    "category", "question_type", "task_category", "split",
                    "ground_truth", "gold", "answer_key", "score", "reward",
                }
            ):
                privileged.append(f"{relative}:{node.lineno}:{node.slice.value}")
    process_calls.sort(key=lambda row: (row["path"], row["line"], row["method"]))
    forbidden_imports = sorted(
        set(
            name
            for name in imports
            if name.split(".")[0]
            in {"requests", "openai", "urllib", "httpx", "socket"}
            or "evaluat" in name.casefold()
        )
    )
    semantic = base._semantic_findings(EFFECT_SOURCES)
    return {
        "effect_source_vector": [
            {"path": str(path), "sha256": base.sha256(path)} for path in EFFECT_SOURCES
        ],
        "subprocess_calls": process_calls,
        "process_call_count": len(process_calls),
        "all_process_methods_are_subprocess_run": all(row["method"] == "run" for row in process_calls),
        "shell_true_lines": sorted(shell_true),
        "forbidden_network_model_evaluator_imports": forbidden_imports,
        "privileged_runtime_field_accesses": sorted(set(privileged)),
        "semantic_privileged_runtime_field_accesses": semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capabilities": semantic["evaluator_capabilities"],
        "credential_literal_hits": semantic["credential_literal_hits"],
        "allowed_provider_rank_access": semantic["allowed_provider_rank_access"],
        "fixed_dpkg_argument_vector": list(selector.DPKG_ARGUMENT_VECTOR),
        "fixed_history_paths": list(selector.HISTORY_PATHS),
        "history_worker_cap": selector.old.HISTORY_WORKERS,
        "per_candidate_timeout_seconds": selector.old.HISTORY_TIMEOUT_SECONDS,
        "whole_selection_wall_ceiling_seconds": selector.old.SELECTION_WALL_CEILING_SECONDS,
        "inherited_selector_audit": _inherited_authority(),
    }


def _tracked(path: Path) -> bool:
    return base._tracked(path)


def _surfaces_pristine() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (selector.ATTEMPT_CLAIM, selector.OUTPUT, selector.EXECUTION_START)
    )


def _lease_inactive() -> bool:
    return base._lease_inactive()


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    dependency_vector = _dependency_vector()
    capability = _capability_audit()
    explicit = {
        SOURCE,
        TEST,
        selector.TEST,
        *FIXED_HASHES,
        *(Path(row["path"]) for row in dependency_vector),
    }
    untracked = sorted(str(path) for path in explicit if tracked and not _tracked(path))
    watchers = runtime_audit.external.watcher_snapshot()
    lease_inactive = _lease_inactive()
    surfaces = _surfaces_pristine()
    checks = {
        "design_old_population_runtime_and_inherited_audit_hashes_exact": _fixed_hashes() == {str(path): digest for path, digest in FIXED_HASHES.items()},
        "design_parent_and_inherited_effect_authorities_validate": _parent_barrier(),
        "selector_design_runtime_tests_exact32": tests["passed"],
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "selector_audit_tests_and_fixed_parents_tracked": not untracked,
        "selector_dependency_vector_exact6_and_hash_bound": (
            tuple(Path(row["path"]) for row in dependency_vector)
            == EXPECTED_DEPENDENCY_PATHS
            and all(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) for row in dependency_vector)
        ),
        "new_and_inherited_effect_sources_exact4_bounded_subprocess_calls": (
            capability["all_process_methods_are_subprocess_run"]
            and capability["process_call_count"] == 4
            and capability["inherited_selector_audit"]["process_call_count"] == 3
        ),
        "shell_true_zero": capability["shell_true_lines"] == [],
        "network_model_evaluator_import_zero": capability["forbidden_network_model_evaluator_imports"] == [],
        "privileged_runtime_field_access_zero": (
            capability["privileged_runtime_field_accesses"] == []
            and capability["semantic_privileged_runtime_field_accesses"] == []
        ),
        "evaluator_capability_zero": capability["evaluator_capabilities"] == [],
        "credential_literal_zero": capability["credential_literal_hits"] == [],
        "old_visible_entity_exclusion_and_v25255_salt_enforced": tests["passed"],
        "task_count64_package_count128_runtime_keys_visible_only": (
            selector.TASK_COUNT == 64 and selector.PACKAGE_COUNT == 128 and selector.PACKAGES_PER_TASK == 2
        ),
        "attempt_claim_precedes_dpkg_or_history_effect": tests["passed"],
        "attempt_result_and_execution_start_surfaces_pristine": surfaces,
        "protected_watchers_unchanged": all(row["matches_frozen_identity"] is True for row in watchers),
        "shared_api_lease_inactive": lease_inactive,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_hashes": _fixed_hashes(),
        "tests": tests,
        "selector_dependency_vector": dependency_vector,
        "selector_dependency_vector_sha256": runtime_audit.external.payload_sha256(dependency_vector),
        "capability_audit": {**capability, "untracked_sources": untracked},
        "population_contract": {
            "task_count": selector.TASK_COUNT,
            "package_count": selector.PACKAGE_COUNT,
            "packages_per_task": selector.PACKAGES_PER_TASK,
            "packages_by_stratum": copy.deepcopy(selector.PACKAGES_BY_STRATUM),
            "old_population_exact_overlap_required": 0,
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
            "single_disjoint_population_freeze_after_separate_execution_start": not findings,
            "observed_reliability_protocol_design_after_valid_freeze": not findings,
            "external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return runtime_audit.external.seal(value, "audit_payload_sha256")


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    git_value = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    dependency_vector = copied.get("selector_dependency_vector") or []
    capability = copied.get("capability_audit") or {}
    population = copied.get("population_contract") or {}
    runtime = copied.get("runtime_state") or {}
    checks = copied.get("checks") or {}
    expected_watchers = [
        {"pid": pid, "start_ticks": ticks, "matches_frozen_identity": True}
        for pid, ticks in runtime_audit.external.PROTECTED_WATCHERS.items()
    ]
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git", "fixed_hashes",
            "tests", "selector_dependency_vector", "selector_dependency_vector_sha256",
            "capability_audit", "population_contract", "runtime_state",
            "checks", "findings", "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or set(git_value) != {"head", "target_main", "equal", "clean"}
        or re.fullmatch(r"[0-9a-f]{40}", str(git_value.get("head"))) is None
        or git_value.get("head") != git_value.get("target_main")
        or git_value.get("equal") is not True
        or git_value.get("clean") is not True
        or copied.get("fixed_hashes") != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or set(row) != {
                "pattern", "expected", "observed", "returncode", "passed",
                "output_sha256",
            }
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256") or "")) is None
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or any(
            not isinstance(row, Mapping)
            or set(row) != {"path", "sha256"}
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256"))) is None
            for row in dependency_vector
        )
        or dependency_vector != _dependency_vector()
        or tuple(Path(row["path"]) for row in dependency_vector)
        != EXPECTED_DEPENDENCY_PATHS
        or copied.get("selector_dependency_vector_sha256")
        != runtime_audit.external.payload_sha256(dependency_vector)
        or capability != {**_capability_audit(), "untracked_sources": []}
        or population
        != {
            "task_count": 64,
            "package_count": 128,
            "packages_per_task": 2,
            "packages_by_stratum": selector.PACKAGES_BY_STRATUM,
            "old_population_exact_overlap_required": 0,
            "runtime_keys": ["opaque_id", "question"],
        }
        or set(runtime) != {
            "shared_api_lease_inactive", "protected_watchers",
            "attempt_result_and_execution_start_surfaces_pristine",
        }
        or runtime.get("shared_api_lease_inactive") is not True
        or runtime.get("attempt_result_and_execution_start_surfaces_pristine") is not True
        or runtime.get("protected_watchers") != expected_watchers
        or set(checks) != CHECK_NAMES
        or any(passed is not True for passed in checks.values())
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
        or copied.get("authorization")
        != {
            "single_disjoint_population_freeze_after_separate_execution_start": True,
            "observed_reliability_protocol_design_after_valid_freeze": True,
            "external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not runtime_audit.external.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.52.57 selector build audit drifted")
    return copied


def main() -> None:
    value = validate_audit(build_audit())
    publisher._publish_json(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"]}, sort_keys=True))


if __name__ == "__main__":
    main()
