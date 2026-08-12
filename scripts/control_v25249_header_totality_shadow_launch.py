#!/usr/bin/env python3
"""Preactivate and start the revoked-start-safe V2.52.48 shadow gate."""

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

from deepwide_agent import v25248_header_totality_shadow_external_contract as contract  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as audit  # noqa: E402
from scripts import control_v25248_header_totality_shadow_external as build_control  # noqa: E402
from scripts import run_v25248_header_totality_shadow_external as runner  # noqa: E402


SOURCE = Path("scripts/control_v25249_header_totality_shadow_launch.py")
TEST = Path("tests/test_v25249_header_totality_shadow_launch.py")
FORWARD_AUDIT_SOURCE = Path("scripts/audit_v25250_header_totality_shadow_forward.py")
FORWARD_AUDIT_TEST = Path("tests/test_audit_v25250_header_totality_shadow_forward.py")
BUILD_AUDIT_SHA256 = "bc68112117e0e5cd5f5d627095990d9a162e1a516701cf1b8f9c4f489a7555a8"
PROTOCOL_SHA256 = "09bd7d6276c137dc20e1ff3e6a653b2e39c50d8b99f1e5393c0a16c67f007695"
TEST_SUITES = (
    ("test_v25249_header_totality_shadow_launch.py", 8),
    ("test_audit_v25250_header_totality_shadow_forward.py", 5),
    ("test_v25248_header_totality_shadow_external.py", 13),
    ("test_v25232_header_totality_shadow_runtime.py", 8),
    ("test_audit_v25233_header_totality_shadow_build.py", 7),
    ("test_v25230_index_positional_header_normalizer.py", 12),
    ("test_audit_v25231_header_totality_build.py", 7),
    ("test_audit_v25243_source_package_population_freeze.py", 6),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
CHECK_NAMES = {
    "build_audit_and_protocol_hashes_exact",
    "build_audit_protocol_and_revocation_validate",
    "launch_control_auditor_runtime_parent_tests_exact66",
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
    "fixed64_32_executor_16_model_slots_and_all_completed_gate",
    "runner_start_schema_and_single_file_commit_boundary_regression_green",
    "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
    "no_external_effect_performed",
}
payload_sha256 = contract.payload_sha256


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    runner._publish_json(ROOT / path, value)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.49 expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.52.49 requires clean pushed HEAD")
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
        contract.ATTEMPT_CLAIM,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    ]
    if include_preaudit:
        paths.append(contract.PREAUDIT)
    if include_start:
        paths.append(contract.EXECUTION_START)
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths)


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
    revocation = contract.validate_revoked_parent(ROOT)
    tests = _tests()
    watchers = contract.watcher_snapshot()
    lease_inactive = build_control._lease_inactive()
    endpoint_reachable = build_control._endpoint_reachable()
    conflicts = build_control._active_conflicts()
    future_pristine = _future_pristine(True, True)
    launch_manifest = _launch_manifest(tracked=tracked)
    checks = {
        "build_audit_and_protocol_hashes_exact": (
            contract.sha256(ROOT / contract.BUILD_AUDIT) == BUILD_AUDIT_SHA256
            and contract.sha256(ROOT / contract.PROTOCOL) == PROTOCOL_SHA256
        ),
        "build_audit_protocol_and_revocation_validate": (
            build["audit_valid"] is True
            and protocol["authorization"]["preactivation_audit_generation"] is True
            and protocol["authorization"]["external_forward"] is False
            and revocation["failure"]["status"] == "pre_effect_no_go"
            and revocation["revocation"]["old_execution_start_authority_revoked"] is True
            and revocation["authorization"]["retry_resume_reuse_or_reseal_v25244_execution_start"] is False
        ),
        "launch_control_auditor_runtime_parent_tests_exact66": tests["passed"],
        "git_clean_head_equals_target_main": head == target,
        "runtime_source_manifest_byte_exact": _manifest_matches(protocol),
        "launch_control_manifest_tracked_and_byte_exact": (
            all(
                _tracked(path)
                for path in (SOURCE, TEST, FORWARD_AUDIT_SOURCE, FORWARD_AUDIT_TEST)
            )
            if tracked
            else True
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
        "local_gpt56_endpoint_reachable": endpoint_reachable,
        "active_forward_or_evaluator_conflicts_zero": not conflicts,
        "runtime_input_exactly_opaque_id_and_question": (
            protocol["population"]["runtime_keys"] == ["opaque_id", "question"]
        ),
        "fixed64_32_executor_16_model_slots_and_all_completed_gate": (
            protocol["population"]["task_count"] == 64
            and protocol["execution"]["executor_concurrency"] == 32
            and protocol["execution"]["model_slot_cap"] == 16
            and protocol["mechanism_gate"]["required_completed_runtime_tasks"] == 64
        ),
        "runner_start_schema_and_single_file_commit_boundary_regression_green": tests["passed"],
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25249_header_totality_shadow_external_preactivation_audit",
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
            "local_gpt56_endpoint_reachable": endpoint_reachable,
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
        or copied.get("role") != "v25249_header_totality_shadow_external_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head") or "")) is None
        or copied.get("protocol_sha256") != PROTOCOL_SHA256
        or copied.get("build_audit_sha256") != BUILD_AUDIT_SHA256
        or not isinstance(copied.get("launch_control_manifest"), Mapping)
        or set(copied["launch_control_manifest"])
        != {str(SOURCE), str(TEST), str(FORWARD_AUDIT_SOURCE), str(FORWARD_AUDIT_TEST)}
        or any(re.fullmatch(r"[0-9a-f]{64}", str(value or "")) is None for value in copied["launch_control_manifest"].values())
        or not isinstance(copied.get("source_manifest"), Mapping)
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256") or "")) is None
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or set(runtime)
        != {
            "shared_api_lease_inactive", "local_gpt56_endpoint_reachable",
            "protected_watchers", "active_conflicts", "future_surfaces_pristine",
        }
        or runtime.get("shared_api_lease_inactive") is not True
        or runtime.get("local_gpt56_endpoint_reachable") is not True
        or runtime.get("active_conflicts") != []
        or runtime.get("future_surfaces_pristine") is not True
        or runtime.get("protected_watchers") != contract.watcher_snapshot()
        or set(checks) != CHECK_NAMES
        or not all(checks.values())
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("authorization")
        != {
            "execution_start_generation": True,
            "external_forward": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.52.49 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head, _target = _clean_pushed() if tracked else ("b" * 40, "b" * 40)
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    preaudit = validate_preaudit(_read(contract.PREAUDIT))
    if (
        tracked
        and (
            not preaudit_commit_boundary(
                preaudit, preaudit_commit=head, git=lambda *args: contract.git(ROOT, *args)
            )
            or not _future_pristine(False, True)
            or not _manifest_matches(protocol)
            or not _launch_manifest_matches(preaudit)
            or contract.validate_revoked_parent(ROOT)["failure"]["status"] != "pre_effect_no_go"
            or not build_control._lease_inactive()
            or not build_control._endpoint_reachable()
            or build_control._active_conflicts()
            or contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]
        )
    ):
        raise RuntimeError("V2.52.49 execution start boundary drifted")
    value = {
        "artifact_version": 1,
        "role": "v25248_header_totality_shadow_external_execution_start",
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
        "protected_watchers": contract.watcher_snapshot(),
        "findings": [],
        "authorization": {
            "single_fresh64_shadow_forward": True,
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
            "protected_watchers", "findings", "authorization",
            "execution_start_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25248_header_totality_shadow_external_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status") != "authorized_not_started"
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head") or "")) is None
        or copied.get("protocol_sha256") != PROTOCOL_SHA256
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("preactivation_audit_sha256") or "")) is None
        or not isinstance(copied.get("source_manifest"), Mapping)
        or copied.get("task_vector_sha256") != contract.TASK_VECTOR_SHA256
        or copied.get("selected") != 64
        or copied.get("executor_concurrency") != 32
        or copied.get("model_slot_cap") != 16
        or copied.get("runtime_input_contract") != ["opaque_id", "question"]
        or copied.get("protected_watchers") != contract.watcher_snapshot()
        or copied.get("findings") != []
        or copied.get("authorization")
        != {
            "single_fresh64_shadow_forward": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "execution_start_payload_sha256")
    ):
        raise ValueError("V2.52.49 execution start drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("preaudit", "start"))
    args = parser.parse_args()
    if args.stage == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    else:
        value, path = validate_start(build_start()), contract.EXECUTION_START
    _publish(path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
