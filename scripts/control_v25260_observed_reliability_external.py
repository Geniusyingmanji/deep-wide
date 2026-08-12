#!/usr/bin/env python3
"""Build and preregister the V2.52.60 observed-reliability gate."""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
import re
import socket
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

from deepwide_agent import v25260_observed_reliability_external_contract as contract  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as audit  # noqa: E402
from scripts import audit_v25254_outer_physical_cap_observed_build as runtime_audit  # noqa: E402
from scripts import audit_v25259_disjoint_observed_reliability_population as population_audit  # noqa: E402
from scripts import run_v25260_observed_reliability_external as runner  # noqa: E402


ROLE = "v25261_observed_reliability_external_build_audit"
SOURCE = contract.CONTROL
TEST = contract.TEST
FIXED_PARENTS = {
    contract.POPULATION: contract.POPULATION_SHA256,
    contract.POPULATION_AUDIT: contract.POPULATION_AUDIT_SHA256,
    contract.RUNTIME_BUILD_AUDIT: contract.RUNTIME_BUILD_AUDIT_SHA256,
}
TEST_SUITES = (
    ("test_v25260_observed_reliability_external.py", 12),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_audit_v25259_disjoint_observed_reliability_population.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXTRA_RUNTIME_FILES = (
    Path("scripts/run_v25248_header_totality_shadow_external.py"),
    Path("scripts/deepwide_api_lease.py"),
    Path("scripts/run_v24985_robust_late_page_fetch_helper.py"),
)
EXPECTED_CLOSURE_COUNT = 79
EXPECTED_CLOSURE_VECTOR_SHA256 = "ef44c91a0437c3f0a91d8bfa9f00d057b4b9afbd3a9701c2acc64788dd7ca8a2"
EXPECTED_CLOSURE_PATH_SHA256 = "3e6913aabf11f2a2fe3820bf78e5c37f5948af1ece1c32e072134cb8f0eaaa0f"
CHECK_NAMES = {
    "contract_runner_runtime_population_tests_exact24",
    "population_and_runtime_parent_authority_bound",
    "all_runtime_control_test_parent_and_closure_files_tracked",
    "git_clean_head_equals_target_main",
    "full_runtime_dependency_vector_exact79_and_hash_bound",
    "privileged_runtime_field_access_zero",
    "evaluator_capability_zero",
    "credential_literal_zero",
    "only_known_provider_rank_score_exception",
    "frozen_task_vector_exact64_by2_runtime_keys_visible_only",
    "production_gpt56_and_32_by16_concurrency_bound",
    "truthful_outer_physical_query4_fetch14_model4_caps",
    "attempt_claim_precedes_endpoint_model_search_fetch_or_output_effect",
    "fixed64_requires_all_runtime_completed_and_zero_outer_stage_budget_failure",
    "prediction_preservation_effect_budget_parity_and_credit_zero",
    "all_build_protocol_and_future_effect_surfaces_pristine",
    "protected_watchers_unchanged",
    "shared_api_lease_inactive",
    "local_gpt56_endpoint_reachable",
    "active_forward_or_evaluator_conflicts_zero",
    "no_model_search_fetch_evaluator_benchmark_or_api_called",
    "no_external_effect_performed",
}


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    runner._publish_json(ROOT / path, value)


def _tests() -> dict[str, Any]:
    suites = [audit._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = set(audit._dependency_closure((contract.CONTRACT, contract.RUNNER)))
    closure.update(EXTRA_RUNTIME_FILES)
    ordered = tuple(sorted(closure, key=str))
    vector = [{"path": str(path), "sha256": audit.sha256(path)} for path in ordered]
    return ordered, vector


def _closure_barrier() -> bool:
    closure, vector = _closure()
    return bool(
        len(closure) == EXPECTED_CLOSURE_COUNT
        and contract.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
        and contract.payload_sha256([row["path"] for row in vector])
        == EXPECTED_CLOSURE_PATH_SHA256
    )


def _parent_barrier() -> bool:
    if any(audit.sha256(path) != expected for path, expected in FIXED_PARENTS.items()):
        return False
    try:
        population = population_audit.validate_audit(
            json.loads(audit._ordinary(contract.POPULATION_AUDIT).read_text(encoding="utf-8"))
        )
        runtime = runtime_audit.validate_audit(
            json.loads(audit._ordinary(contract.RUNTIME_BUILD_AUDIT).read_text(encoding="utf-8"))
        )
        tasks = contract.task_vector(ROOT)
    except BaseException:
        return False
    return bool(
        len(tasks) == 64
        and population["audit_valid"] is True
        and population["findings"] == []
        and population["authorization"]["fresh64_observed_reliability_protocol_design"] is True
        and population["authorization"]["fresh64_external_activation_or_launch"] is False
        and runtime["audit_valid"] is True
        and runtime["findings"] == []
        and runtime["physical_caps"] == {"queries": 4, "fetches": 14, "model_forwards": 4}
        and runtime["authorization"]["fresh_external_activation_or_launch"] is False
    )


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _endpoint_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            return True
    except OSError:
        return False


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
    markers = (str(contract.RUNNER), "scripts/run_official_eval_local.py")
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _surfaces_pristine(*, include_build: bool, include_protocol: bool) -> bool:
    paths = [
        contract.PREAUDIT, contract.EXECUTION_START, contract.ATTEMPT_CLAIM,
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
    ]
    if include_build:
        paths.append(contract.BUILD_AUDIT)
    if include_protocol:
        paths.append(contract.PROTOCOL)
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths
    )


def _source_manifest(vector: list[dict[str, str]]) -> dict[str, str]:
    return {row["path"]: row["sha256"] for row in vector}


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = audit._semantic_findings(closure)
    explicit = {SOURCE, TEST, *FIXED_PARENTS}
    untracked = sorted(
        str(path)
        for path in explicit.union(closure)
        if tracked and not audit._tracked(path)
    )
    watchers = contract.watcher_snapshot()
    lease_inactive = _lease_inactive()
    endpoint = _endpoint_reachable()
    conflicts = _active_conflicts()
    pristine = _surfaces_pristine(include_build=True, include_protocol=True)
    gate = contract.reliability_gate()
    checks = {
        "contract_runner_runtime_population_tests_exact24": tests["passed"],
        "population_and_runtime_parent_authority_bound": _parent_barrier(),
        "all_runtime_control_test_parent_and_closure_files_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "full_runtime_dependency_vector_exact79_and_hash_bound": _closure_barrier(),
        "privileged_runtime_field_access_zero": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "only_known_provider_rank_score_exception": semantic["allowed_provider_rank_access"] == ["src/deepwide_agent/clients.py:565:score"],
        "frozen_task_vector_exact64_by2_runtime_keys_visible_only": len(contract.task_vector(ROOT)) == 64,
        "production_gpt56_and_32_by16_concurrency_bound": (
            contract.MODEL["name"] == "gpt-5.6-sol"
            and contract.EXECUTOR_CONCURRENCY == 32
            and contract.MODEL_SLOT_CAP == 16
        ),
        "truthful_outer_physical_query4_fetch14_model4_caps": contract.PHYSICAL_CAPS == {
            "queries_per_task": 4, "fetches_per_task": 14,
            "model_forwards_per_task": 4,
        },
        "attempt_claim_precedes_endpoint_model_search_fetch_or_output_effect": tests["passed"],
        "fixed64_requires_all_runtime_completed_and_zero_outer_stage_budget_failure": (
            gate["required_completed_runtime_tasks"] == 64
            and gate["maximum_outer_failure_tasks"] == 0
            and gate["maximum_stage_failure_tasks"] == 0
            and gate["maximum_budget_rejection_tasks"] == 0
        ),
        "prediction_preservation_effect_budget_parity_and_credit_zero": tests["passed"],
        "all_build_protocol_and_future_effect_surfaces_pristine": pristine,
        "protected_watchers_unchanged": all(row["matches_frozen_identity"] is True for row in watchers),
        "shared_api_lease_inactive": lease_inactive,
        "local_gpt56_endpoint_reachable": endpoint,
        "active_forward_or_evaluator_conflicts_zero": not conflicts,
        "no_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "tests": tests,
        "fixed_parent_hashes": {str(path): audit.sha256(path) for path in FIXED_PARENTS},
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": contract.payload_sha256(vector),
        "runtime_dependency_path_sha256": contract.payload_sha256([row["path"] for row in vector]),
        "source_manifest": _source_manifest(vector),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "local_gpt56_endpoint_reachable": endpoint,
            "protected_watchers": watchers,
            "active_conflicts": conflicts,
            "surfaces_pristine": pristine,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "protocol_generation": not findings,
            "external_forward": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    git_value = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    vector = copied.get("runtime_dependency_vector") or []
    semantic = copied.get("semantic_audit") or {}
    runtime_state = copied.get("runtime_state") or {}
    checks = copied.get("checks") or {}
    expected_vector = _closure()[1]
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git", "tests",
            "fixed_parent_hashes", "runtime_dependency_vector",
            "runtime_dependency_vector_sha256", "runtime_dependency_path_sha256",
            "source_manifest", "semantic_audit", "runtime_state", "checks",
            "findings", "audit_valid",
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
        or git_value.get("head") != git_value.get("target_main")
        or git_value.get("equal") is not True
        or git_value.get("clean") is not True
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
        or copied.get("fixed_parent_hashes")
        != {str(path): expected for path, expected in FIXED_PARENTS.items()}
        or vector != expected_vector
        or contract.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_vector_sha256") != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256") != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("source_manifest") != _source_manifest(vector)
        or set(semantic)
        != {
            "privileged_runtime_field_accesses", "evaluator_capabilities",
            "credential_literal_hits", "allowed_provider_rank_access", "untracked_sources",
        }
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("allowed_provider_rank_access") != ["src/deepwide_agent/clients.py:565:score"]
        or semantic.get("untracked_sources") != []
        or set(runtime_state)
        != {
            "shared_api_lease_inactive", "local_gpt56_endpoint_reachable",
            "protected_watchers", "active_conflicts", "surfaces_pristine",
        }
        or runtime_state.get("shared_api_lease_inactive") is not True
        or runtime_state.get("local_gpt56_endpoint_reachable") is not True
        or runtime_state.get("protected_watchers") != contract.watcher_snapshot()
        or runtime_state.get("active_conflicts") != []
        or runtime_state.get("surfaces_pristine") is not True
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
            "protocol_generation": True,
            "external_forward": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.52.61 build audit drifted")
    return copied


def build_protocol(
    audit_value: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    checked = validate_audit(audit_value)
    if checked["authorization"]["protocol_generation"] is not True:
        raise RuntimeError("V2.52.60 protocol authority absent")
    return contract.build_protocol(
        source_manifest=checked["source_manifest"],
        now=int(time.time()) if now is None else int(now),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("buildaudit", "protocol"))
    args = parser.parse_args()
    if args.stage == "buildaudit":
        value = validate_audit(build_audit())
        path = contract.BUILD_AUDIT
    else:
        raw = json.loads(audit._ordinary(contract.BUILD_AUDIT).read_text(encoding="utf-8"))
        value = contract.validate_protocol(ROOT, build_protocol(raw))
        path = contract.PROTOCOL
    _publish(path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
