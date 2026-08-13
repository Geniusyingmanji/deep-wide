#!/usr/bin/env python3
"""Preactivation audit and start builder for the V2.53.23 population attempt."""

from __future__ import annotations

import ast
import copy
import json
import os
import re
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

from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25324_low_concurrency_worldbank_population_build as build  # noqa: E402
from scripts import run_v25323_low_concurrency_worldbank_population as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25325_low_concurrency_worldbank_population_preactivation_audit"
OUTPUT = runner.PREACTIVATION
SOURCE = Path(
    "scripts/audit_v25325_low_concurrency_worldbank_population_preactivation.py"
)
TEST = Path(
    "tests/test_audit_v25325_low_concurrency_worldbank_population_preactivation.py"
)
IMPLEMENTATION_COMMIT = build.IMPLEMENTATION_COMMIT
IMPLEMENTATION_PATHS = build.IMPLEMENTATION_PATHS
HARDENING_COMMITS = build.HARDENING_COMMITS
BUILD_AUDIT_SHA256 = (
    "1a25fd0176ffe6e6a6626abff2b1fa6267085c792a37e560313c011bb2b346b3"
)
FIXED = {
    runner.SOURCE: "9871626a6121aca242f0e99cbea405ff5d785e8e686a3a7570f367081e1543dd",
    runner.TEST: "23a08d962374eff69231593ce5d2c3dcd4f5862b5918822c495e82dcde984c8a",
    runner.HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
    runner.SELECTOR: "31a0fca9f235059eacf44163b4f719e6e11722f3c6e45c2c212e25ec416f1b2f",
    runner.FIRST_RUNNER: "d6cac9b0393018fac13a9899219b0a22ebd4493e783b0fb434cc47bcb1854be0",
    runner.SECOND_RUNNER: "16bd593dd7dcec23069bc012c5e1a535ea20cacf3c2cb4f678e23da2aab6dc8f",
    runner.PRIOR_AUDIT_SOURCE: "def1fbffef9f5e94c5d9cd04537fb77f7f142efd2c59df26f3a0bd94b2c86892",
    runner.DIAGNOSIS_SOURCE: "55676fe3da52abeb51cb1b4a782f4e366a97fde9a4248d156b5ba08c980cb670",
    runner.LEASE_SOURCE: "8d9cffa78617b458172307d3558c76e9370f045f531c2f5aaaceb866f5a78c7d",
    runner.second.PARENT_TRANSPORT: "d6cac9b0393018fac13a9899219b0a22ebd4493e783b0fb434cc47bcb1854be0",
    runner.BUILD_AUDIT: BUILD_AUDIT_SHA256,
}
TEST_SUITES = (
    ("test_audit_v25325_low_concurrency_worldbank_population_preactivation.py", 7),
    ("test_audit_v25324_low_concurrency_worldbank_population_build.py", 7),
    ("test_run_v25323_low_concurrency_worldbank_population.py", 9),
    ("test_v25322_twice_disjoint_worldbank_population.py", 7),
    ("test_diagnose_v25321_v25317_transport_capacity.py", 5),
    ("test_run_v25317_disjoint_worldbank_population.py", 11),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 101
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "bfea0681f73e4ce4ec0bf6d86b10fa8f51e2a951c2955de2a3a9094ef284ed40"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "f6d35d90e8ad8f3e56126d09f70c4372a623be16c81035c106ebd5f7512b4c2c"
)
FUTURE_SURFACES = (
    runner.PREACTIVATION,
    runner.EXECUTION_START,
    runner.ATTEMPT_CLAIM,
    runner.RESULT,
    runner.OUTPUT_ROOT,
    runner.POSTFREEZE_AUDIT,
)
CHECK_NAMES = runner.PREACTIVATION_CHECK_NAMES


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _tests_exact(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    suites = value.get("suites")
    return bool(
        set(value) == {"expected", "observed", "passed", "suites"}
        and value.get("expected") == EXPECTED_TESTS
        and value.get("observed") == EXPECTED_TESTS
        and value.get("passed") is True
        and isinstance(suites, list)
        and len(suites) == len(TEST_SUITES)
        and all(
            isinstance(row, Mapping)
            and set(row)
            == {
                "pattern",
                "expected",
                "observed",
                "returncode",
                "passed",
                "output_sha256",
            }
            and row.get("pattern") == pattern
            and row.get("expected") == expected
            and row.get("observed") == expected
            and row.get("returncode") == 0
            and row.get("passed") is True
            and re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256")))
            is not None
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
    )


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    return build._closure()


def _changed_paths(commit: str) -> list[str]:
    return build._changed_paths(commit)


def _is_ancestor(older: str, newer: str) -> bool:
    return build._is_ancestor(older, newer)


def _build_barrier() -> bool:
    try:
        value = build.validate_audit(
            json.loads(base._ordinary(runner.BUILD_AUDIT).read_text(encoding="utf-8"))
        )
    except BaseException:
        return False
    authorization = value["authorization"]
    return bool(
        base.sha256(runner.BUILD_AUDIT) == BUILD_AUDIT_SHA256
        and value["audit_valid"] is True
        and value["findings"] == []
        and authorization["low_concurrency_population_preactivation_design"]
        is True
        and authorization["network_population_selection_or_freeze"] is False
        and authorization["external_forward_or_evaluator"] is False
    )


def _source_manifest() -> dict[str, str]:
    return runner._source_manifest()


def _source_invariants() -> dict[str, bool]:
    source = base._ordinary(runner.SOURCE).read_text(encoding="utf-8")
    helper = base._ordinary(runner.HELPER).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(runner.SOURCE))
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    main = ast.get_source_segment(source, functions["main"]) or ""
    execute = ast.get_source_segment(source, functions["execute_freeze"]) or ""
    validate = ast.get_source_segment(source, functions["validate_result"]) or ""
    request = ast.get_source_segment(
        source, functions["_request_target_pages"]
    ) or ""
    return {
        "claim_before_execute": main.index(
            "publish_json_exclusive(ROOT / ATTEMPT_CLAIM"
        )
        < main.index("execute_freeze("),
        "lease_wraps_claim_execute_result": main.index(
            "with acquire_deepwide_api_lease("
        )
        < main.index("publish_json_exclusive(ROOT / ATTEMPT_CLAIM")
        < main.index("execute_freeze(")
        < main.index("publish_json_exclusive(ROOT / RESULT"),
        "all48_required": (
            "len(target_rows) != 48" in execute
            and "len(candidate_bodies) != selector.MINIMUM_TARGET_OVERSAMPLE"
            in execute
            and "any(row[\"outcome\"] != \"success\"" in execute
        ),
        "target_concurrency_exact6": (
            runner.TARGET_CONCURRENCY == 6
            and "ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY)" in request
        ),
        "body_receipt_mismatch_checked_before_population": (
            "response_body_receipt_mismatch_count" in execute
            and "response_body_receipt_mismatch" in execute
            and execute.index("response_body_receipt_mismatch_count")
            < execute.index("selector.select_and_render_population(")
        ),
        "consumed_response_overlap_checked_before_population": (
            "consumed_response_overlap_count" in execute
            and execute.index("consumed_response_overlap_count")
            < execute.index("selector.select_and_render_population(")
        ),
        "go_requires_zero_overlap_and_exact_population": all(
            token in validate
            for token in (
                'target.get("response_body_receipt_mismatch_count") != 0',
                'target.get("consumed_response_overlap_count") != 0',
                'population.get("selected_target_overlap_count") != 0',
                'population.get("selected_entity_overlap_count") != 0',
                'population.get("selected_response_overlap_count") != 0',
                'population.get("entity_count") not in {96, 108}',
                'population.get("task_count") != 12',
            )
        ),
        "helper_zero_redirect_retry_and_env": (
            "session.trust_env = False" in helper
            and "allow_redirects=False" in helper
            and "max_retries" not in helper
        ),
        "retry_resume_backfill_replacement_zero": (
            '"retry_resume_backfill_replacement_or_second_attempt": False'
            in source
            and '"redirect_retry_refetch_resume_backfill_replacement_count": 0'
            in source
        ),
        "visible_only_and_credit_zero": (
            '"mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False'
            in source
            and '"entropy_or_information_gain_assigns_signed_credit": False'
            in source
        ),
    }


def _future_pristine() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in FUTURE_SURFACES
    )


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    )
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        pid_text, command = parts
        argv = command.split()
        runner_entry = any(
            token.endswith("/scripts/run_v25323_low_concurrency_worldbank_population.py")
            or token == "scripts/run_v25323_low_concurrency_worldbank_population.py"
            for token in argv[:6]
        )
        helper_entry = any(
            token.endswith("/scripts/v25297_worldbank_get_helper.py")
            or token == "scripts/v25297_worldbank_get_helper.py"
            for token in argv[:6]
        )
        if pid_text.isdigit() and (runner_entry or helper_entry):
            output.append(int(pid_text))
    return sorted(output)


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {SOURCE, TEST, *FIXED, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    literal_hits = sorted(
        str(path)
        for path in explicit
        if base.SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    )
    watchers = base._watchers()
    invariants = _source_invariants()
    conflicts = _active_conflicts()
    checks = {
        "fixed_sources_build_audit_and_implementation_commit_exact": (
            {str(path): base.sha256(path) for path in FIXED}
            == {str(path): digest for path, digest in FIXED.items()}
            and _changed_paths(IMPLEMENTATION_COMMIT) == IMPLEMENTATION_PATHS
            and _is_ancestor(IMPLEMENTATION_COMMIT, head)
            and all(
                _changed_paths(commit) == paths and _is_ancestor(commit, head)
                for commit, paths in HARDENING_COMMITS
            )
        ),
        "focused_parent_and_transport_tests_exact_green": tests["passed"],
        "runtime_dependency_closure_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and runner.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and runner.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "all_explicit_and_closure_files_tracked": not untracked,
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == []
        and literal_hits == [],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "build_audit_authorizes_preactivation_only": _build_barrier(),
        "source_manifest_binds_all_direct_runtime_sources": (
            _source_manifest()
            == {
                str(path): base.sha256(path)
                for path in map(Path, runner._source_manifest())
            }
        ),
        "claim_precedes_catalog_or_target_effect": invariants[
            "claim_before_execute"
        ],
        "shared_lease_wraps_claim_network_and_result": invariants[
            "lease_wraps_claim_execute_result"
        ],
        "single_catalog_and_exact48_target_batch_all_or_nothing": invariants[
            "all48_required"
        ],
        "target_concurrency_exact6_and_only_transport_policy_change": (
            invariants["target_concurrency_exact6"]
            and build._transport_policy_exact(build._transport_policy_contract())
        ),
        "body_receipt_and_consumed_response_hashes_both_checked": invariants[
            "body_receipt_mismatch_checked_before_population"
        ]
        and invariants["consumed_response_overlap_checked_before_population"],
        "consumed_48_target_144_entity_84_response_contract_exact": (
            runner._consumed_manifest_contract()
            == {
                "target_count": 48,
                "entity_count": 144,
                "response_count": 84,
                "preferred_entity_count": 108,
                "minimum_entity_count": 96,
                "task_count": 12,
                "all_overlap_counts_must_be_zero": True,
            }
            and invariants["go_requires_zero_overlap_and_exact_population"]
        ),
        "twelve_task_108_then96_disjoint_capacity_contract_exact": (
            runner.selector.TASK_COUNT == 12
            and runner.selector.PREFERRED_ENTITY_COUNT == 108
            and runner.selector.MINIMUM_ENTITY_COUNT == 96
            and invariants["go_requires_zero_overlap_and_exact_population"]
        ),
        "helper_exact_url_allowlist_zero_redirect_retry_and_trust_env": invariants[
            "helper_zero_redirect_retry_and_env"
        ],
        "failure_no_go_without_retry_resume_backfill_or_replacement": invariants[
            "retry_resume_backfill_replacement_zero"
        ],
        "future_start_claim_result_output_and_postaudit_pristine": _future_pristine(),
        "protected_watchers_unchanged": runner._protected_watcher_artifact_exact(
            watchers
        ),
        "shared_api_lease_inactive": base._lease_inactive(),
        "active_population_forward_or_evaluator_conflicts_zero": not conflicts,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "entropy_information_gain_shadow_and_positive_credit_zero": invariants[
            "visible_only_and_credit_zero"
        ],
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
        "fixed_inputs": {str(path): base.sha256(path) for path in FIXED},
        "implementation_commit": {
            "commit": IMPLEMENTATION_COMMIT,
            "paths": IMPLEMENTATION_PATHS,
            "hardening_commits": [
                {"commit": commit, "paths": paths}
                for commit, paths in HARDENING_COMMITS
            ],
        },
        "build_audit": {
            "path": str(runner.BUILD_AUDIT),
            "sha256": BUILD_AUDIT_SHA256,
        },
        "source_manifest": _source_manifest(),
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": runner.payload_sha256(vector),
        "runtime_dependency_path_sha256": runner.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {
            **semantic,
            "auditor_or_explicit_file_credential_literal_hits": literal_hits,
            "untracked_sources": untracked,
        },
        "runtime_invariants": invariants,
        "consumed_manifest_contract": runner._consumed_manifest_contract(),
        "protected_watchers": watchers,
        "shared_api_lease_inactive": checks["shared_api_lease_inactive"],
        "active_conflicts": conflicts,
        "future_surfaces_pristine": _future_pristine(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "execution_start_generation": not findings,
            "single_low_concurrency_population_freeze": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_attempt": False,
        },
    }
    value["audit_payload_sha256"] = runner.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    vector = copied.get("runtime_dependency_vector")
    semantic = copied.get("semantic_audit") or {}
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_inputs",
            "implementation_commit",
            "build_audit",
            "source_manifest",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "runtime_invariants",
            "consumed_manifest_contract",
            "protected_watchers",
            "shared_api_lease_inactive",
            "active_conflicts",
            "future_surfaces_pristine",
            "checks",
            "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or not isinstance(copied.get("git"), Mapping)
        or set(copied["git"]) != {"head", "target_main", "equal", "clean"}
        or copied["git"].get("equal")
        is not (copied["git"].get("head") == copied["git"].get("target_main"))
        or not isinstance(copied["git"].get("clean"), bool)
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in FIXED.items()}
        or copied.get("implementation_commit")
        != {
            "commit": IMPLEMENTATION_COMMIT,
            "paths": IMPLEMENTATION_PATHS,
            "hardening_commits": [
                {"commit": commit, "paths": paths}
                for commit, paths in HARDENING_COMMITS
            ],
        }
        or copied.get("build_audit")
        != {"path": str(runner.BUILD_AUDIT), "sha256": BUILD_AUDIT_SHA256}
        or copied.get("source_manifest") != _source_manifest()
        or not _tests_exact(copied.get("tests"))
        or not isinstance(vector, list)
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or runner.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or runner.payload_sha256([row["path"] for row in vector])
        != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or set(semantic)
        != {
            "privileged_runtime_field_accesses",
            "evaluator_capabilities",
            "credential_literal_hits",
            "allowed_provider_rank_access",
            "auditor_or_explicit_file_credential_literal_hits",
            "untracked_sources",
        }
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("auditor_or_explicit_file_credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or copied.get("runtime_invariants") != _source_invariants()
        or copied.get("consumed_manifest_contract")
        != runner._consumed_manifest_contract()
        or not runner._protected_watcher_artifact_exact(
            copied.get("protected_watchers")
        )
        or copied.get("shared_api_lease_inactive") is not True
        or copied.get("active_conflicts") != []
        or copied.get("future_surfaces_pristine") is not True
        or set(checks) != CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("audit_valid") is not (not expected_findings)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "execution_start_generation": not expected_findings,
            "single_low_concurrency_population_freeze": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_attempt": False,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.25 preactivation audit drifted")
    return copied


def build_execution_start(
    audit_value: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    checked = validate_audit(audit_value)
    if checked["authorization"]["execution_start_generation"] is not True:
        raise RuntimeError("V2.53.25 execution-start authority absent")
    parent = base._git("rev-parse", "HEAD")
    if (
        base._git("status", "--porcelain")
        or parent != base._git("rev-parse", "target/main")
        or base._git("rev-parse", f"{parent}^") != checked["git"]["head"]
        or _changed_paths(parent) != [str(runner.PREACTIVATION)]
    ):
        raise RuntimeError(
            "V2.53.25 start requires the clean pushed single-file preactivation commit"
        )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25326_low_concurrency_worldbank_population_execution_start",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_parent": parent,
        "preactivation_audit": {
            "path": str(runner.PREACTIVATION),
            "sha256": runner.sha256(ROOT / runner.PREACTIVATION),
        },
        "source_manifest": checked["source_manifest"],
        "runtime_state": {
            "protected_watchers": list(runner.EXPECTED_WATCHERS),
            "shared_api_lease_inactive": True,
        },
        "transport_contract": {
            "catalog_url": runner.CATALOG_URL,
            "catalog_provider_attempt_count": 1,
            "candidate_target_count": 24,
            "target_provider_attempt_count": 48,
            "target_concurrency": runner.TARGET_CONCURRENCY,
            "catalog_phase_hard_wall_seconds": runner.CATALOG_PHASE_HARD_WALL_SECONDS,
            "target_phase_hard_wall_seconds": runner.TARGET_PHASE_HARD_WALL_SECONDS,
            "whole_freeze_hard_wall_seconds": runner.WHOLE_FREEZE_HARD_WALL_SECONDS,
        },
        "consumed_manifest_contract": copy.deepcopy(
            checked["consumed_manifest_contract"]
        ),
        "fixed_attempt_claim_path": str(runner.ATTEMPT_CLAIM),
        "fixed_result_path": str(runner.RESULT),
        "fixed_output_root": str(runner.OUTPUT_ROOT),
        "single_catalog_then_single_48_target_response_batch": True,
        "retry_resume_refetch_backfill_replacement_or_second_attempt": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "single_low_concurrency_population_freeze": True,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
        },
    }
    value["start_payload_sha256"] = runner.payload_sha256(value)
    return runner._validate_execution_start(value, current_head="0" * 40)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    runner.publish_json_exclusive(path, value)


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) == 2 else "audit"
    if stage == "audit":
        value = build_audit()
        path = runner.PREACTIVATION
    elif stage == "start":
        raw = json.loads(
            base._ordinary(runner.PREACTIVATION).read_text(encoding="utf-8")
        )
        value = build_execution_start(raw)
        path = runner.EXECUTION_START
    else:
        raise SystemExit("usage: audit_v25325...py [audit|start]")
    _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "output": str(path),
                "role": value["role"],
                "audit_valid": value.get("audit_valid"),
                "tests": value.get("tests", {}).get("observed"),
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
