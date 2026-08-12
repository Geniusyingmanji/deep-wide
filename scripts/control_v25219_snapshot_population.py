#!/usr/bin/env python3
"""Preactivate and authorize the one-shot V2.52.19 snapshot population."""

from __future__ import annotations

import argparse
import copy
import json
import multiprocessing
import os
import subprocess
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
from scripts import audit_v25218_snapshot_hard_deadline_controller_build as parent  # noqa: E402
from scripts import run_v25219_snapshot_population as runner  # noqa: E402


DATE = "20260812"
PREAUDIT = Path(f"results/v25219_snapshot_population_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = runner.EXECUTION_START
RESULT = Path(f"results/v25219_snapshot_population_freeze_v1_{DATE}.json")
SOURCE = Path("scripts/control_v25219_snapshot_population.py")
RUNNER = Path("scripts/run_v25219_snapshot_population.py")
TEST = Path("tests/test_control_v25219_snapshot_population.py")
RUNNER_TEST = Path("tests/test_run_v25219_snapshot_population.py")
PARENT_AUDIT = parent.OUTPUT
EXPECTED_PARENT_AUDIT_SHA256 = (
    "988185da358ad0a9b13e846c1abc735152a4a4cf60a103bc74ee6b7c4ba86edc"
)
SOURCE_FILES = runner.SOURCE_FILES
TEST_SUITES = (
    ("test_control_v25219_snapshot_population.py", 6),
    ("test_run_v25219_snapshot_population.py", 13),
    ("test_audit_v25218_snapshot_hard_deadline_controller_build.py", 6),
    ("test_v25218_snapshot_hard_deadline_controller.py", 8),
    ("test_v25215_offline_candidate_discovery.py", 8),
    ("test_audit_v25213_population_selection.py", 6),
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


def _parent_barrier() -> bool:
    raw = json.loads(base.base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    value = parent.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_SHA256
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 28
        and value["tests"]["observed"] == 28
        and authorization["public_snapshot_preactivation_audit_implementation"]
        is True
        and authorization["public_snapshot_network_access_or_execution_start"]
        is False
    )


def _manifest() -> dict[str, str]:
    return {str(path): base.base.sha256(path) for path in SOURCE_FILES}


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    output: list[int] = []
    marker = "scripts/run_v25219_snapshot_population.py"
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and marker in parts[2]
        ):
            output.append(int(parts[0]))
    return sorted(output)


def build_preactivation(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    manifest = _manifest()
    closure = audit._dependency_closure((RUNNER,))
    semantic = audit._semantic_findings(closure)
    explicit = {TEST, RUNNER_TEST, PARENT_AUDIT, *SOURCE_FILES}
    untracked = sorted(
        str(path) for path in explicit if tracked and not audit._tracked(path)
    )
    watchers = audit._watchers()
    lease_inactive = audit._lease_inactive()
    conflicts = _active_conflicts()
    surfaces_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (EXECUTION_START, RESULT, runner.ATTEMPT_CLAIM)
    )
    checks = {
        "control_runner_parent_controller_discovery_selector_tests_exact47": tests[
            "passed"
        ],
        "v25218_controller_build_audit_bound": _parent_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "fork_start_method_available": "fork" in multiprocessing.get_all_start_methods(),
        "source_manifest_complete": set(manifest) == {str(path) for path in SOURCE_FILES},
        "runtime_dependency_closure_exact": closure == runner.RUNTIME_SOURCE_FILES,
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "execution_start_and_result_surfaces_pristine": surfaces_pristine,
        "active_v25219_snapshot_runner_conflicts_zero": not conflicts,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
        "no_public_snapshot_network_or_api_called_before_execution_start": True,
        "no_model_hosted_search_tavily_evaluator_or_benchmark_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25219_snapshot_population_preactivation_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "source_manifest": manifest,
        "parent_controller_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": audit.sha256(PARENT_AUDIT),
        },
        "dependency_closure": [str(path) for path in closure],
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers": watchers,
            "active_conflicts": conflicts,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "public_snapshot_network_or_api_called": False,
        "model_hosted_search_tavily_evaluator_or_benchmark_called": False,
        "parent_receipt_effect_disclosure": copy.deepcopy(
            runner.PARENT_RECEIPT_EFFECT_DISCLOSURE
        ),
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "execution_start_generation": not findings,
            "single_public_snapshot_population_batch": False,
            "real_identity_selection_and_conditional_population_freeze": False,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_preactivation(value)


def validate_preactivation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    expected_fields = {
        "artifact_version",
        "role",
        "created_at_unix",
        "git",
        "tests",
        "source_manifest",
        "parent_controller_build_audit",
        "dependency_closure",
        "semantic_audit",
        "runtime_state",
        "checks",
        "findings",
        "audit_valid",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "public_snapshot_network_or_api_called",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "parent_receipt_effect_disclosure",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "audit_payload_sha256",
    }
    git = copied.get("git")
    tests = copied.get("tests")
    parent_audit = copied.get("parent_controller_build_audit")
    semantic = copied.get("semantic_audit")
    runtime = copied.get("runtime_state")
    checks = copied.get("checks")
    expected_checks = {
        "control_runner_parent_controller_discovery_selector_tests_exact47",
        "v25218_controller_build_audit_bound",
        "all_sources_tests_and_parent_artifacts_tracked",
        "git_clean_head_equals_target_main",
        "fork_start_method_available",
        "source_manifest_complete",
        "runtime_dependency_closure_exact",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "execution_start_and_result_surfaces_pristine",
        "active_v25219_snapshot_runner_conflicts_zero",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_public_snapshot_network_or_api_called_before_execution_start",
        "no_model_hosted_search_tavily_evaluator_or_benchmark_called",
        "no_external_effect_performed",
    }
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25219_snapshot_population_preactivation_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not isinstance(git, Mapping)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or git.get("equal") is not True
        or git.get("clean") is not True
        or git.get("head") != git.get("target_main")
        or not isinstance(tests, Mapping)
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or not isinstance(tests.get("suites"), list)
        or len(tests["suites"]) != len(TEST_SUITES)
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
            for row, (pattern, expected) in zip(
                tests["suites"], TEST_SUITES, strict=True
            )
        )
        or not isinstance(checks, Mapping)
        or set(checks) != expected_checks
        or any(checks.get(name) is not True for name in expected_checks)
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("source_manifest") != _manifest()
        or copied.get("dependency_closure")
        != [str(path) for path in runner.RUNTIME_SOURCE_FILES]
        or not isinstance(parent_audit, Mapping)
        or set(parent_audit) != {"path", "sha256"}
        or parent_audit.get("path") != str(PARENT_AUDIT)
        or parent_audit.get("sha256")
        != EXPECTED_PARENT_AUDIT_SHA256
        or not isinstance(semantic, Mapping)
        or set(semantic)
        != {
            "privileged_runtime_field_accesses",
            "evaluator_capabilities",
            "credential_literal_hits",
            "allowed_provider_rank_access",
            "untracked_sources",
        }
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("allowed_provider_rank_access") != []
        or semantic.get("untracked_sources") != []
        or not isinstance(runtime, Mapping)
        or set(runtime)
        != {"shared_api_lease_inactive", "protected_watchers", "active_conflicts"}
        or runtime.get("shared_api_lease_inactive") is not True
        or runtime.get("active_conflicts") != []
        or not isinstance(runtime.get("protected_watchers"), Mapping)
        or set(runtime["protected_watchers"])
        != {str(pid) for pid in runner.PROTECTED_WATCHERS}
        or not all(
            isinstance(row, Mapping)
            and set(row) == {"present", "start_ticks", "matches_frozen_identity"}
            and row.get("present") is True
            and row.get("start_ticks") == runner.PROTECTED_WATCHERS[int(pid)]
            and row.get("matches_frozen_identity") is True
            for pid, row in runtime["protected_watchers"].items()
        )
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("public_snapshot_network_or_api_called")
        is not False
        or copied.get(
            "model_hosted_search_tavily_evaluator_or_benchmark_called"
        )
        is not False
        or copied.get("parent_receipt_effect_disclosure")
        != runner.PARENT_RECEIPT_EFFECT_DISCLOSURE
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "execution_start_generation": True,
            "single_public_snapshot_population_batch": False,
            "real_identity_selection_and_conditional_population_freeze": False,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.19 preactivation audit drifted")
    return copied


def build_execution_start(
    preaudit: Mapping[str, Any], *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    checked = validate_preactivation(preaudit)
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    if (
        tracked
        and (
            not clean
            or head != target
            or _manifest() != checked["source_manifest"]
            or not audit._tracked(PREAUDIT)
            or not runner.preactivation_commit_boundary(
                checked,
                preactivation_commit=head,
                git=audit._git,
            )
            or (ROOT / EXECUTION_START).exists()
            or (ROOT / RESULT).exists()
            or (ROOT / runner.ATTEMPT_CLAIM).exists()
            or _active_conflicts()
        )
    ):
        raise RuntimeError("V2.52.19 execution-start boundary drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25219_snapshot_population_execution_start",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "preactivation_audit": {
            "path": str(PREAUDIT),
            "sha256": audit.sha256(PREAUDIT) if tracked else "0" * 64,
        },
        "source_manifest": copy.deepcopy(checked["source_manifest"]),
        "history_parent_commit": head,
        "single_batch_no_retry_refetch_backfill_or_partial_freeze": True,
        "public_snapshot_network_or_api_called": False,
        "model_hosted_search_tavily_evaluator_or_benchmark_called": False,
        "parent_receipt_effect_disclosure": copy.deepcopy(
            runner.PARENT_RECEIPT_EFFECT_DISCLOSURE
        ),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "single_public_snapshot_population_batch": True,
            "real_identity_selection_and_conditional_population_freeze": True,
            "retry_refetch_backfill_or_second_batch": False,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["start_payload_sha256"] = payload_sha256(value)
    return validate_execution_start(value)


def validate_execution_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("start_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    expected_fields = {
        "artifact_version",
        "role",
        "created_at_unix",
        "git",
        "preactivation_audit",
        "source_manifest",
        "history_parent_commit",
        "single_batch_no_retry_refetch_backfill_or_partial_freeze",
        "public_snapshot_network_or_api_called",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "parent_receipt_effect_disclosure",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "start_payload_sha256",
    }
    git = copied.get("git")
    preaudit = copied.get("preactivation_audit")
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25219_snapshot_population_execution_start"
        or not isinstance(git, Mapping)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or git.get("equal") is not True
        or git.get("clean") is not True
        or git.get("head")
        != copied.get("history_parent_commit")
        or git.get("target_main")
        != copied.get("history_parent_commit")
        or not isinstance(preaudit, Mapping)
        or set(preaudit) != {"path", "sha256"}
        or preaudit.get("path") != str(PREAUDIT)
        or not isinstance(preaudit.get("sha256"), str)
        or len(preaudit["sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in preaudit["sha256"]
        )
        or copied.get("source_manifest") != _manifest()
        or not isinstance(copied.get("history_parent_commit"), str)
        or len(copied["history_parent_commit"]) != 40
        or copied.get("single_batch_no_retry_refetch_backfill_or_partial_freeze")
        is not True
        or copied.get("public_snapshot_network_or_api_called") is not False
        or copied.get(
            "model_hosted_search_tavily_evaluator_or_benchmark_called"
        )
        is not False
        or copied.get("parent_receipt_effect_disclosure")
        != runner.PARENT_RECEIPT_EFFECT_DISCLOSURE
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "single_public_snapshot_population_batch": True,
            "real_identity_selection_and_conditional_population_freeze": True,
            "retry_refetch_backfill_or_second_batch": False,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.19 execution start drifted")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
    base.base.publish(ROOT / path, value)


def main() -> None:
    command = argparse.ArgumentParser()
    command.add_argument("stage", choices=("preaudit", "start"))
    args = command.parse_args()
    if args.stage == "preaudit":
        value = build_preactivation()
        publish(PREAUDIT, value)
        path = PREAUDIT
    else:
        raw = json.loads(base.base._ordinary(PREAUDIT).read_text(encoding="utf-8"))
        value = build_execution_start(raw)
        publish(EXECUTION_START, value)
        path = EXECUTION_START
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
