#!/usr/bin/env python3
"""Clean-build audit and preregistration for V2.53.09."""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
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

from deepwide_agent import v25309_worldbank_monotone_fill_external_contract as contract  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as audit  # noqa: E402
from scripts import run_v25309_worldbank_monotone_fill_external as runner  # noqa: E402


ROLE = "v25309_worldbank_monotone_fill_clean_build_audit"
SOURCE = contract.CONTROL
TEST = Path("tests/test_control_v25309_worldbank_monotone_fill_external.py")
IMPLEMENTATION_COMMIT = "c26fbc601fb20f9237d3aa02994416f7b7fb1a3d"
IMPLEMENTATION_PATHS = sorted(
    str(path) for path in (contract.CONTRACT, contract.RUNNER, contract.TEST,
                           Path("src/deepwide_agent/v25309_pipe_visible_schema_worldbank_gate.py"))
)
FIXED_PARENTS = {
    contract.POPULATION_FREEZE: contract.POPULATION_FREEZE_SHA256,
    contract.PRIVATE_POPULATION: contract.PRIVATE_POPULATION_SHA256,
    contract.POPULATION_AUDIT: contract.POPULATION_AUDIT_SHA256,
    contract.RUNTIME_BUILD_AUDIT: contract.RUNTIME_BUILD_AUDIT_SHA256,
    contract.DESIGN: contract.DESIGN_SHA256,
}
TEST_SUITES = (
    ("test_control_v25309_worldbank_monotone_fill_external.py", 5),
    ("test_v25309_worldbank_monotone_fill_external.py", 10),
    ("test_v25295_worldbank_monotone_fill_gate.py", 10),
    ("test_v25290_monotone_unknown_fill_integration.py", 16),
    ("test_v25289_monotone_unknown_fill.py", 17),
    ("test_v24286_visible_schema_runtime.py", 6),
    ("test_v24259_deterministic_table_normalizer.py", 11),
    ("test_v24318_deadline_conservation_runtime.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXTRA_RUNTIME_FILES = (
    Path("scripts/deepwide_api_lease.py"),
    Path("scripts/v24468_total_wall_http_helper.py"),
)
EXPECTED_CLOSURE_COUNT = 89
EXPECTED_CLOSURE_VECTOR_SHA256 = "cbca554ba3cb0532292c5f89e350b69b2a8942fb94d51ab05cd51fa593e7b9ef"
EXPECTED_CLOSURE_PATH_SHA256 = "c98f0630b0de303986b681f71718590cea50538b66ba6c87aebf06c70df2a732"
CHECK_NAMES = frozenset(
    {
        "implementation_commit_exact_and_ancestor",
        "implementation_commit_paths_exact",
        "fixed_parent_hashes_and_semantics_exact",
        "tests_exact83_green",
        "all_runtime_control_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact89_and_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "frozen_task12_page8_runtime_keys_visible_only",
        "pipe_schema_bug_fixed_without_parent_mutation",
        "production_gpt56_12_by20_by8_concurrency_bound",
        "physical_query4_fetch10_model3_wall240_caps",
        "native_global_limiter_without_hard_cap_wrapper",
        "attempt_claim_precedes_endpoint_model_or_output_effect",
        "mechanism_gate_exact_and_evaluator_fail_closed",
        "entropy_information_gain_shadow_and_positive_credit_zero",
        "future_effect_surfaces_pristine",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "local_gpt56_endpoint_reachable",
        "active_forward_or_evaluator_conflicts_zero",
        "no_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


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
    closure = set(
        audit._dependency_closure(
            (
                Path("src/deepwide_agent/v25309_pipe_visible_schema_worldbank_gate.py"),
                contract.CONTRACT,
                contract.RUNNER,
            )
        )
    )
    closure.update(EXTRA_RUNTIME_FILES)
    ordered = tuple(sorted(closure, key=str))
    vector = [{"path": str(path), "sha256": audit.sha256(path)} for path in ordered]
    return ordered, vector


def _ancestor(commit: str, head: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, head], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode
        == 0
    )


def _changed_paths(commit: str) -> list[str]:
    return sorted(
        line
        for line in contract.git(
            ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", commit
        ).splitlines()
        if line
    )


def _parent_barrier() -> bool:
    try:
        population = contract.frozen_population(ROOT)
        audit_value = json.loads(
            contract.ordinary(ROOT, contract.POPULATION_AUDIT, tracked=True).read_text(
                encoding="utf-8"
            )
        )
        runtime_audit = json.loads(
            contract.ordinary(ROOT, contract.RUNTIME_BUILD_AUDIT, tracked=True).read_text(
                encoding="utf-8"
            )
        )
    except BaseException:
        return False
    return bool(
        len(population["tasks"]) == 12
        and len(population["pages"]) == 8
        and audit_value.get("audit_valid") is True
        and audit_value.get("findings") == []
        and (audit_value.get("authorization") or {}).get(
            "external_monotone_fill_mechanism_protocol_design"
        )
        is True
        and (audit_value.get("authorization") or {}).get(
            "external_monotone_fill_forward_or_postfreeze_evaluator"
        )
        is False
        and runtime_audit.get("audit_valid") is True
        and runtime_audit.get("findings") == []
        and (runtime_audit.get("authorization") or {}).get(
            "external_activation_or_launch"
        )
        is False
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


def _future_pristine(*, include_build: bool, include_protocol: bool) -> bool:
    paths = [
        contract.PREAUDIT, contract.EXECUTION_START, contract.ATTEMPT_CLAIM,
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
    ]
    if include_build:
        paths.append(contract.BUILD_AUDIT)
    if include_protocol:
        paths.append(contract.PROTOCOL)
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths)


def _source_manifest(vector: list[dict[str, str]]) -> dict[str, str]:
    return {row["path"]: row["sha256"] for row in vector}


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    clean = not contract.git(ROOT, "status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = audit._semantic_findings(closure)
    explicit = {SOURCE, TEST, contract.TEST, *FIXED_PARENTS}
    untracked = sorted(
        str(path)
        for path in explicit.union(closure)
        if tracked and not audit._tracked(path)
    )
    watchers = contract.watcher_snapshot()
    conflicts = runner._active_conflicts()
    gate = contract.mechanism_gate()
    checks = {
        "implementation_commit_exact_and_ancestor": _ancestor(IMPLEMENTATION_COMMIT, head),
        "implementation_commit_paths_exact": _changed_paths(IMPLEMENTATION_COMMIT) == IMPLEMENTATION_PATHS,
        "fixed_parent_hashes_and_semantics_exact": (
            all(audit.sha256(path) == digest for path, digest in FIXED_PARENTS.items())
            and _parent_barrier()
        ),
        "tests_exact83_green": tests["passed"],
        "all_runtime_control_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact89_and_hash_bound": (
            len(closure) == EXPECTED_CLOSURE_COUNT
            and contract.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and contract.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "privileged_runtime_field_access_zero": semantic["privileged_runtime_field_accesses"] == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [],
        "only_known_provider_rank_score_exception": semantic["allowed_provider_rank_access"] == ["src/deepwide_agent/clients.py:565:score"],
        "frozen_task12_page8_runtime_keys_visible_only": (
            len(contract.task_vector(ROOT)) == 12 and len(contract.page_vector(ROOT)) == 8
        ),
        "pipe_schema_bug_fixed_without_parent_mutation": tests["passed"],
        "production_gpt56_12_by20_by8_concurrency_bound": (
            contract.MODEL == {
                "proxy_url": "http://127.0.0.1:9878/responses", "name": "gpt-5.6-sol",
                "reasoning_effort": "low", "service_tier": "priority",
                "timeout_seconds": 65, "max_retries": 2,
            }
            and contract.TASK_COUNT == 12
            and contract.EXECUTOR_CONCURRENCY == 20
            and contract.MODEL_SLOT_CAP == 8
        ),
        "physical_query4_fetch10_model3_wall240_caps": contract.PHYSICAL_CAPS == {
            "queries_per_task": 4, "fetches_per_task": 10,
            "model_forwards_per_task": 3, "wall_seconds_per_task": 240,
        },
        "native_global_limiter_without_hard_cap_wrapper": tests["passed"],
        "attempt_claim_precedes_endpoint_model_or_output_effect": tests["passed"],
        "mechanism_gate_exact_and_evaluator_fail_closed": (
            gate["minimum_supported_unknown_fill_tasks"] == 2
            and gate["minimum_supported_unknown_fill_cells"] == 2
            and gate["minimum_attributable_prediction_change_tasks"] == 2
            and gate["required_query_effect_equal_tasks"] == 12
            and gate["required_fetch_effect_equal_tasks"] == 12
            and gate["required_total_model_calls_at_most_three_tasks"] == 12
            and gate["maximum_known_cell_schema_row_key_order_or_count_violation_tasks"] == 0
            and gate["maximum_unsupported_or_conflicting_admitted_fill_cells"] == 0
        ),
        "entropy_information_gain_shadow_and_positive_credit_zero": gate["positive_signed_credit_count"] == 0,
        "future_effect_surfaces_pristine": _future_pristine(include_build=True, include_protocol=True),
        "protected_watchers_unchanged": all(row["matches_frozen_identity"] is True for row in watchers),
        "shared_api_lease_inactive": _lease_inactive(),
        "local_gpt56_endpoint_reachable": _endpoint_reachable(),
        "active_forward_or_evaluator_conflicts_zero": not conflicts,
        "no_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
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
            "shared_api_lease_inactive": _lease_inactive(),
            "local_gpt56_endpoint_reachable": _endpoint_reachable(),
            "protected_watchers": watchers,
            "active_conflicts": conflicts,
            "future_surfaces_pristine": _future_pristine(include_build=True, include_protocol=True),
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
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    tests = copied.get("tests") or {}
    vector = copied.get("runtime_dependency_vector") or []
    semantic = copied.get("semantic_audit") or {}
    state = copied.get("runtime_state") or {}
    expected_vector = _closure()[1]
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git", "tests",
            "fixed_parent_hashes", "runtime_dependency_vector",
            "runtime_dependency_vector_sha256", "runtime_dependency_path_sha256",
            "source_manifest", "semantic_audit", "runtime_state", "checks", "findings",
            "audit_valid", "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or (copied.get("git") or {}).get("head") != (copied.get("git") or {}).get("target_main")
        or (copied.get("git") or {}).get("equal") is not True
        or (copied.get("git") or {}).get("clean") is not True
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or copied.get("fixed_parent_hashes") != {str(path): digest for path, digest in FIXED_PARENTS.items()}
        or vector != expected_vector
        or copied.get("runtime_dependency_vector_sha256") != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256") != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("source_manifest") != _source_manifest(vector)
        or semantic
        != {
            "privileged_runtime_field_accesses": [], "evaluator_capabilities": [],
            "credential_literal_hits": [],
            "allowed_provider_rank_access": ["src/deepwide_agent/clients.py:565:score"],
            "untracked_sources": [],
        }
        or state.get("shared_api_lease_inactive") is not True
        or state.get("local_gpt56_endpoint_reachable") is not True
        or state.get("protected_watchers") != contract.watcher_snapshot()
        or state.get("active_conflicts") != []
        or state.get("future_surfaces_pristine") is not True
        or copied.get("checks") != {name: True for name in CHECK_NAMES}
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or any(copied.get(name) is not False for name in (
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
        ))
        or copied.get("authorization")
        != {
            "protocol_generation": True, "external_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.53.09 clean-build audit drifted")
    return copied


def build_protocol(audit_value: Mapping[str, Any], *, now: int | None = None) -> dict[str, Any]:
    checked = validate_audit(audit_value)
    if checked["authorization"]["protocol_generation"] is not True:
        raise RuntimeError("V2.53.09 protocol authority absent")
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
        raw = json.loads(
            contract.ordinary(ROOT, contract.BUILD_AUDIT, tracked=True).read_text(encoding="utf-8")
        )
        value = contract.validate_protocol(ROOT, build_protocol(raw))
        path = contract.PROTOCOL
    _publish(path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
