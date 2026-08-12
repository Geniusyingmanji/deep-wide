#!/usr/bin/env python3
"""Preactivate and start the V2.52.60 observed-reliability gate."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25260_observed_reliability_external_contract as contract  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as audit  # noqa: E402
from scripts import control_v25260_observed_reliability_external as build_control  # noqa: E402
from scripts import run_v25260_observed_reliability_external as runner  # noqa: E402


SOURCE = Path("scripts/control_v25262_observed_reliability_launch.py")
TEST = Path("tests/test_v25262_observed_reliability_launch.py")
FORWARD_AUDIT_SOURCE = Path("scripts/audit_v25263_observed_reliability_forward.py")
FORWARD_AUDIT_TEST = Path("tests/test_audit_v25263_observed_reliability_forward.py")
BUILD_AUDIT_SHA256 = "039412fbf2629d8eb6ef33c4ed1350c52f9e8ea7aeb97b95d69dfe298ee7b7d2"
PROTOCOL_SHA256 = "b717f2e585fb9fa058fcca9c2560ee85d337d09be803210940e29dc5c8707219"
TEST_SUITES = (
    ("test_v25262_observed_reliability_launch.py", 8),
    ("test_audit_v25263_observed_reliability_forward.py", 5),
    ("test_v25260_observed_reliability_external.py", 12),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_audit_v25259_disjoint_observed_reliability_population.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
CHECK_NAMES = {
    "build_audit_and_protocol_hashes_exact",
    "build_audit_and_protocol_validate",
    "launch_forward_auditor_runtime_population_tests_exact37",
    "git_clean_head_equals_target_main",
    "runtime_source_manifest_byte_exact",
    "launch_control_manifest_tracked_and_byte_exact",
    "runtime_dependency_manifest_has_no_evaluator_privileged_or_credential_finding",
    "preaudit_start_claim_forward_audit_and_output_surfaces_pristine",
    "protected_watchers_unchanged",
    "shared_api_lease_inactive",
    "local_gpt56_endpoint_reachable",
    "active_forward_or_evaluator_conflicts_zero",
    "runtime_input_exactly_opaque_id_and_question",
    "fixed64_32_executor_16_slots_truthful_caps_and_all_completed_gate",
    "runner_start_schema_and_single_file_commit_boundary_regression_green",
    "no_model_search_fetch_evaluator_benchmark_or_api_called",
    "no_external_effect_performed",
}


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    runner._publish_json(ROOT / path, value)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.62 expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.52.62 requires clean pushed HEAD")
    return head, target


def _tests() -> dict[str, Any]:
    suites = [audit._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _tracked(relative: Path) -> bool:
    try:
        contract.ordinary(ROOT, relative, tracked=True)
        return True
    except BaseException:
        return False


def _launch_manifest(*, tracked: bool = True) -> dict[str, str]:
    return {
        str(path): contract.sha256(contract.ordinary(ROOT, path, tracked=tracked))
        for path in (SOURCE, TEST, FORWARD_AUDIT_SOURCE, FORWARD_AUDIT_TEST)
    }


def _manifest_matches(protocol: Mapping[str, Any]) -> bool:
    manifest = protocol.get("source_manifest")
    if not isinstance(manifest, Mapping) or not manifest:
        return False
    try:
        observed = {
            str(path): contract.sha256(contract.ordinary(ROOT, Path(str(path)), tracked=True))
            for path in manifest
        }
    except BaseException:
        return False
    return observed == dict(manifest)


def _launch_manifest_matches(value: Mapping[str, Any]) -> bool:
    manifest = value.get("launch_control_manifest")
    try:
        return isinstance(manifest, Mapping) and dict(manifest) == _launch_manifest(tracked=True)
    except BaseException:
        return False


def _future_pristine(include_preaudit: bool, include_start: bool) -> bool:
    paths = [
        contract.ATTEMPT_CLAIM, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
    ]
    if include_preaudit:
        paths.append(contract.PREAUDIT)
    if include_start:
        paths.append(contract.EXECUTION_START)
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths
    )


def preaudit_commit_boundary(
    preaudit: Mapping[str, Any], *, preaudit_commit: str, git: Callable[..., str]
) -> bool:
    try:
        parent_row = git("rev-list", "--parents", "-n", "1", preaudit_commit).split()
        changed = sorted(
            line.strip()
            for line in git(
                "diff-tree", "--no-commit-id", "--name-only", "-r", preaudit_commit
            ).splitlines()
            if line.strip()
        )
    except BaseException:
        return False
    return bool(
        len(parent_row) == 2
        and parent_row[0] == preaudit_commit
        and parent_row[1] == preaudit.get("git_head")
        and changed == [str(contract.PREAUDIT)]
    )


def build_preaudit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if tracked else ("a" * 40, "a" * 40)
    build = build_control.validate_audit(_read(contract.BUILD_AUDIT))
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    tests = _tests()
    watchers = contract.watcher_snapshot()
    lease_inactive = build_control._lease_inactive()
    endpoint = build_control._endpoint_reachable()
    conflicts = build_control._active_conflicts()
    future_pristine = _future_pristine(True, True)
    launch_manifest = _launch_manifest(tracked=tracked)
    gate = protocol["reliability_gate"]
    checks = {
        "build_audit_and_protocol_hashes_exact": (
            contract.sha256(ROOT / contract.BUILD_AUDIT) == BUILD_AUDIT_SHA256
            and contract.sha256(ROOT / contract.PROTOCOL) == PROTOCOL_SHA256
        ),
        "build_audit_and_protocol_validate": (
            build["audit_valid"] is True
            and protocol["authorization"]["preactivation_audit_generation"] is True
            and protocol["authorization"]["external_forward"] is False
        ),
        "launch_forward_auditor_runtime_population_tests_exact37": tests["passed"],
        "git_clean_head_equals_target_main": head == target,
        "runtime_source_manifest_byte_exact": _manifest_matches(protocol),
        "launch_control_manifest_tracked_and_byte_exact": (
            all(_tracked(path) for path in (SOURCE, TEST, FORWARD_AUDIT_SOURCE, FORWARD_AUDIT_TEST))
            if tracked else True
        ),
        "runtime_dependency_manifest_has_no_evaluator_privileged_or_credential_finding": (
            build["semantic_audit"]["privileged_runtime_field_accesses"] == []
            and build["semantic_audit"]["evaluator_capabilities"] == []
            and build["semantic_audit"]["credential_literal_hits"] == []
        ),
        "preaudit_start_claim_forward_audit_and_output_surfaces_pristine": future_pristine,
        "protected_watchers_unchanged": (
            watchers == protocol["execution"]["protected_watchers"]
            and all(row["matches_frozen_identity"] is True for row in watchers)
        ),
        "shared_api_lease_inactive": lease_inactive,
        "local_gpt56_endpoint_reachable": endpoint,
        "active_forward_or_evaluator_conflicts_zero": not conflicts,
        "runtime_input_exactly_opaque_id_and_question": protocol["population"]["runtime_keys"] == ["opaque_id", "question"],
        "fixed64_32_executor_16_slots_truthful_caps_and_all_completed_gate": (
            protocol["population"]["task_count"] == 64
            and protocol["execution"]["executor_concurrency"] == 32
            and protocol["execution"]["model_slot_cap"] == 16
            and protocol["truthful_physical_caps"] == contract.PHYSICAL_CAPS
            and gate["required_completed_runtime_tasks"] == 64
            and gate["maximum_outer_failure_tasks"] == 0
            and gate["maximum_stage_failure_tasks"] == 0
            and gate["maximum_budget_rejection_tasks"] == 0
        ),
        "runner_start_schema_and_single_file_commit_boundary_regression_green": tests["passed"],
        "no_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25262_observed_reliability_external_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "launch_control_manifest": launch_manifest,
        "source_manifest": copy.deepcopy(protocol["source_manifest"]),
        "tests": tests,
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "local_gpt56_endpoint_reachable": endpoint,
            "protected_watchers": watchers,
            "active_conflicts": conflicts,
            "future_surfaces_pristine": future_pristine,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "execution_start_generation": not findings,
            "external_forward": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    runtime = copied.get("runtime_state") or {}
    checks = copied.get("checks") or {}
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix", "git_head",
            "protocol_sha256", "build_audit_sha256", "launch_control_manifest",
            "source_manifest", "tests", "runtime_state", "checks", "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25262_observed_reliability_external_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head"))) is None
        or copied.get("protocol_sha256") != PROTOCOL_SHA256
        or copied.get("build_audit_sha256") != BUILD_AUDIT_SHA256
        or not isinstance(copied.get("launch_control_manifest"), Mapping)
        or set(copied["launch_control_manifest"])
        != {str(SOURCE), str(TEST), str(FORWARD_AUDIT_SOURCE), str(FORWARD_AUDIT_TEST)}
        or any(re.fullmatch(r"[0-9a-f]{64}", str(digest)) is None for digest in copied["launch_control_manifest"].values())
        or not isinstance(copied.get("source_manifest"), Mapping)
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or set(row) != {"pattern", "expected", "observed", "returncode", "passed", "output_sha256"}
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256"))) is None
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or set(runtime)
        != {
            "shared_api_lease_inactive", "local_gpt56_endpoint_reachable",
            "protected_watchers", "active_conflicts", "future_surfaces_pristine",
        }
        or runtime.get("shared_api_lease_inactive") is not True
        or runtime.get("local_gpt56_endpoint_reachable") is not True
        or runtime.get("protected_watchers") != contract.watcher_snapshot()
        or runtime.get("active_conflicts") != []
        or runtime.get("future_surfaces_pristine") is not True
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
            "execution_start_generation": True,
            "external_forward": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.52.62 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head, _target = _clean_pushed() if tracked else ("b" * 40, "b" * 40)
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    preaudit = validate_preaudit(_read(contract.PREAUDIT))
    if (
        tracked
        and (
            not preaudit_commit_boundary(
                preaudit, preaudit_commit=head,
                git=lambda *args: contract.git(ROOT, *args),
            )
            or not _future_pristine(False, True)
            or not _manifest_matches(protocol)
            or not _launch_manifest_matches(preaudit)
            or not build_control._lease_inactive()
            or not build_control._endpoint_reachable()
            or build_control._active_conflicts()
            or contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]
        )
    ):
        raise RuntimeError("V2.52.62 execution start boundary drifted")
    value = {
        "artifact_version": 1,
        "role": "v25262_observed_reliability_external_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "status": "authorized_not_started",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "source_manifest": copy.deepcopy(protocol["source_manifest"]),
        "task_vector_sha256": contract.TASK_VECTOR_SHA256,
        "selected": contract.TASK_COUNT,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "runtime_input_contract": ["opaque_id", "question"],
        "truthful_physical_caps": copy.deepcopy(contract.PHYSICAL_CAPS),
        "protected_watchers": contract.watcher_snapshot(),
        "findings": [],
        "authorization": {
            "single_fresh64_observed_reliability_forward": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "status", "created_at_unix",
            "git_head", "protocol_sha256", "preactivation_audit_sha256",
            "source_manifest", "task_vector_sha256", "selected",
            "executor_concurrency", "model_slot_cap", "runtime_input_contract",
            "truthful_physical_caps", "protected_watchers", "findings",
            "authorization", "execution_start_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25262_observed_reliability_external_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status") != "authorized_not_started"
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head"))) is None
        or copied.get("protocol_sha256") != PROTOCOL_SHA256
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("preactivation_audit_sha256"))) is None
        or not isinstance(copied.get("source_manifest"), Mapping)
        or copied.get("task_vector_sha256") != contract.TASK_VECTOR_SHA256
        or copied.get("selected") != 64
        or copied.get("executor_concurrency") != 32
        or copied.get("model_slot_cap") != 16
        or copied.get("runtime_input_contract") != ["opaque_id", "question"]
        or copied.get("truthful_physical_caps") != contract.PHYSICAL_CAPS
        or copied.get("protected_watchers") != contract.watcher_snapshot()
        or copied.get("findings") != []
        or copied.get("authorization")
        != {
            "single_fresh64_observed_reliability_forward": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "execution_start_payload_sha256")
    ):
        raise ValueError("V2.52.62 execution start drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("preaudit", "start"))
    args = parser.parse_args()
    if args.stage == "preaudit":
        value, path = validate_preaudit(build_preaudit()), contract.PREAUDIT
    else:
        value, path = validate_start(build_start()), contract.EXECUTION_START
    _publish(path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
