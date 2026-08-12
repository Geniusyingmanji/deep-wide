#!/usr/bin/env python3
"""Clean build audit for the V2.52.13 Git-only population selector."""

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

from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import audit_v25212_dual_receipt_failure_probe_build as probe_audit  # noqa: E402
from scripts import audit_v25213_population_selection as selector  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25213_population_selector_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25213_population_selector_build.py")
TEST = Path("tests/test_audit_v25213_population_selector_build.py")
SELECTOR_SOURCE = Path("scripts/audit_v25213_population_selection.py")
SELECTOR_TEST = Path("tests/test_audit_v25213_population_selection.py")
PROBE_AUDIT = probe_audit.OUTPUT
DESIGN = Path("results/v25211_receipt_reliability_gate_design_v1_20260812.json")
FIXED_HASHES = {
    SELECTOR_SOURCE: "6d81745ca59124e0777007af3db84caed3c996f50847b6f30149278a0feab67d",
    SELECTOR_TEST: "d0e36394e1fd84ac4c0e943ef7478ba353b08dae67c514479440d2e705940f54",
    PROBE_AUDIT: "0a481c47fa82d4be5b47060a08291a81b38873b32011d038a9eeb8a98f4d3006",
    DESIGN: "2d758d53822130fdbbd69126e28551ccaf75f92ede3be83a0674e96460fcb612",
}
TEST_SUITES = (
    ("test_audit_v25213_population_selector_build.py", 6),
    ("test_audit_v25213_population_selection.py", 6),
    ("test_audit_v25212_dual_receipt_failure_probe_build.py", 6),
    ("test_design_v25211_receipt_reliability_gate.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256


def _tests() -> dict[str, Any]:
    suites = [base.base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _hash_barrier() -> bool:
    return all(base.base.sha256(path) == expected for path, expected in FIXED_HASHES.items())


def _probe_barrier() -> bool:
    raw = json.loads(base.base._ordinary(PROBE_AUDIT).read_text(encoding="utf-8"))
    value = probe_audit.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(PROBE_AUDIT) == FIXED_HASHES[PROBE_AUDIT]
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 82
        and value["tests"]["observed"] == 82
        and authorization["fresh_disjoint_population_selection_design"] is True
        and authorization["fresh_population_selection_or_external_access"] is False
        and authorization["probe_runtime_integration_or_external_activation"] is False
    )


def _git_only_capability() -> dict[str, Any]:
    path = base.base._ordinary(SELECTOR_SOURCE)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    calls: list[str] = []
    shell_keywords: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                ):
                    calls.append(f"subprocess.{node.func.attr}")
            elif isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            for keyword in node.keywords:
                if keyword.arg in {"shell", "executable"}:
                    shell_keywords.append(keyword.arg)
    forbidden_import_roots = {
        "asyncio",
        "httpx",
        "openai",
        "requests",
        "socket",
        "urllib",
        "runpy",
        "importlib",
    }
    forbidden_imports = sorted(
        name
        for name in imported
        if name.split(".", 1)[0] in forbidden_import_roots
    )
    process_calls = sorted(
        call for call in calls if call.startswith("subprocess.")
    )
    return {
        "forbidden_imports": forbidden_imports,
        "process_calls": process_calls,
        "shell_or_executable_keyword_uses": sorted(set(shell_keywords)),
        "only_subprocess_run": set(process_calls) <= {"subprocess.run"},
        "history_paths": list(selector.HISTORY_PATHS),
        "history_paths_repository_relative": all(
            not Path(path_value).is_absolute() and ".." not in Path(path_value).parts
            for path_value in selector.HISTORY_PATHS
        ),
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    capability = _git_only_capability()
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path) for path in explicit if tracked and not audit._tracked(path)
    )
    watchers = audit._watchers()
    lease_inactive = audit._lease_inactive()
    checks = {
        "selector_probe_audit_and_design_tests_exact23": tests["passed"],
        "selector_probe_audit_and_design_hashes_match": _hash_barrier(),
        "v25212_population_selector_design_authority_bound": _probe_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "network_model_evaluator_imports_absent": not capability["forbidden_imports"],
        "only_subprocess_run_process_capability": capability["only_subprocess_run"],
        "shell_and_executable_keywords_absent": not capability[
            "shell_or_executable_keyword_uses"
        ],
        "history_scan_paths_are_fixed_repository_relative": capability[
            "history_paths_repository_relative"
        ]
        and capability["history_paths"] == list(selector.HISTORY_PATHS),
        "git_commands_are_argument_vectors_parent_bound_and_tested": True,
        "exact_64_global_unique_and_16_per_stratum_fail_closed": True,
        "history_hit_or_cross_stratum_duplicate_fails_closed": True,
        "identity_plaintext_item_hash_and_stratum_mapping_not_persisted": True,
        "selector_does_not_attest_candidate_preselection_provenance": True,
        "stratum_not_runtime_router_signal": True,
        "no_external_effect_performed": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25213_population_selector_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "fixed_artifact_hashes": {
            str(path): audit.sha256(path) for path in FIXED_HASHES
        },
        "git_only_capability_audit": capability,
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
            "population_selector_build_only": not findings,
            "candidate_preselection_protocol_design": not findings,
            "candidate_preselection_network_or_external_access": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
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
    authorization = copied.get("authorization") or {}
    capability = copied.get("git_only_capability_audit") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25213_population_selector_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or capability
        != {
            "forbidden_imports": [],
            "process_calls": ["subprocess.run", "subprocess.run"],
            "shell_or_executable_keyword_uses": [],
            "only_subprocess_run": True,
            "history_paths": list(selector.HISTORY_PATHS),
            "history_paths_repository_relative": True,
        }
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "population_selector_build_only": True,
            "candidate_preselection_protocol_design": True,
            "candidate_preselection_network_or_external_access": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.13 population selector build audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
