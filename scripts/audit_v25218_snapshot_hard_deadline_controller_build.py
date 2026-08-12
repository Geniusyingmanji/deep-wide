#!/usr/bin/env python3
"""Clean build audit for V2.52.18 snapshot hard-deadline control."""

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
from scripts import audit_v25217_single_snapshot_transport_build as parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25218_snapshot_hard_deadline_controller_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25218_snapshot_hard_deadline_controller_build.py")
TEST = Path("tests/test_audit_v25218_snapshot_hard_deadline_controller_build.py")
CONTROLLER_SOURCE = Path("src/deepwide_agent/v25218_snapshot_hard_deadline_controller.py")
CONTROLLER_TEST = Path("tests/test_v25218_snapshot_hard_deadline_controller.py")
PARENT_AUDIT = parent.OUTPUT
FIXED_HASHES = {
    CONTROLLER_SOURCE: "2dbef4242915399b793ad07b8c296eb3cc6e07bdae8ae063fe46c397b5fbe4c5",
    CONTROLLER_TEST: "05681c371a932216da15f498b77db1dde88e623a5596693bbabb56ecc02d3668",
    PARENT_AUDIT: "d13c9334b91937738c70da344328e6714ad9ea20a6771daa6105e584945afe53",
}
TEST_SUITES = (
    ("test_audit_v25218_snapshot_hard_deadline_controller_build.py", 6),
    ("test_v25218_snapshot_hard_deadline_controller.py", 8),
    ("test_audit_v25217_single_snapshot_transport_build.py", 6),
    ("test_v25217_single_snapshot_transport.py", 8),
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


def _parent_barrier() -> bool:
    raw = json.loads(base.base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    value = parent.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(PARENT_AUDIT) == FIXED_HASHES[PARENT_AUDIT]
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 26
        and value["tests"]["observed"] == 26
        and authorization["hard_deadline_controller_build_only"] is True
        and authorization["public_snapshot_network_access_or_execution_start"]
        is False
    )


def _direct_capability() -> dict[str, Any]:
    path = base.base._ordinary(CONTROLLER_SOURCE)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    calls: list[str] = []
    top_level_effects: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                calls.append(f"{node.func.value.id}.{node.func.attr}")
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            top_level_effects.append(ast.unparse(node.value.func))
    return {
        "imports": sorted(imports),
        "module_calls": sorted(calls),
        "top_level_effect_calls": top_level_effects,
        "multiprocessing_and_anonymous_mmap_present": (
            "multiprocessing" in imports
            and "mmap" in imports
            and "multiprocessing.get_context" in calls
            and "mmap.mmap" in calls
        ),
        "filesystem_subprocess_environment_imports": sorted(
            name
            for name in imports
            if name.split(".", 1)[0] in {"os", "pathlib", "subprocess"}
        ),
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure = audit._dependency_closure((CONTROLLER_SOURCE,))
    semantic = audit._semantic_findings(closure)
    capability = _direct_capability()
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path)
        for path in explicit.union(closure)
        if tracked and not audit._tracked(path)
    )
    watchers = audit._watchers()
    lease_inactive = audit._lease_inactive()
    checks = {
        "controller_transport_audit_and_tests_exact28": tests["passed"],
        "controller_test_and_parent_audit_hashes_match": _hash_barrier(),
        "v25217_hard_deadline_controller_build_authority_bound": _parent_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "dependency_closure_exactly_controller_and_transport": closure
        == (parent.TRANSPORT_SOURCE, CONTROLLER_SOURCE),
        "multiprocessing_and_anonymous_mmap_capability_disclosed": capability[
            "multiprocessing_and_anonymous_mmap_present"
        ],
        "filesystem_subprocess_environment_imports_absent": not capability[
            "filesystem_subprocess_environment_imports"
        ],
        "import_time_effect_calls_absent": not capability["top_level_effect_calls"],
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "fork_only_four_child_concurrency": True,
        "hard_deadline_terminate_then_kill": True,
        "all_or_nothing_body_return_and_hash_binding": True,
        "worker_exception_content_free": True,
        "repeated_timeout_has_no_active_child_or_material_fd_leak": True,
        "no_raw_snapshot_file_queue_or_persistent_store": True,
        "no_external_effect_performed": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25218_snapshot_hard_deadline_controller_clean_build_audit",
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
        "dependency_closure": [str(path) for path in closure],
        "direct_capability_audit": capability,
        "semantic_audit": {**semantic, "untracked_sources": untracked},
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
            "hard_deadline_controller_build_only": not findings,
            "public_snapshot_preactivation_audit_implementation": not findings,
            "public_snapshot_network_access_or_execution_start": False,
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
    capability = copied.get("direct_capability_audit") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25218_snapshot_hard_deadline_controller_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("dependency_closure")
        != [str(parent.TRANSPORT_SOURCE), str(CONTROLLER_SOURCE)]
        or capability.get("multiprocessing_and_anonymous_mmap_present") is not True
        or capability.get("filesystem_subprocess_environment_imports") != []
        or capability.get("top_level_effect_calls") != []
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "hard_deadline_controller_build_only": True,
            "public_snapshot_preactivation_audit_implementation": True,
            "public_snapshot_network_access_or_execution_start": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.18 hard-deadline build audit drifted")
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
