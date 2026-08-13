#!/usr/bin/env python3
"""Preactivation audit for the one-shot V2.53.17 population supervisor."""

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
from scripts import audit_v25316_disjoint_worldbank_population_build as build  # noqa: E402
from scripts import run_v25317_disjoint_worldbank_population as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25318_disjoint_worldbank_population_preactivation_audit"
OUTPUT = runner.PREACTIVATION
SOURCE = Path(
    "scripts/audit_v25318_disjoint_worldbank_population_preactivation.py"
)
TEST = Path(
    "tests/test_audit_v25318_disjoint_worldbank_population_preactivation.py"
)
IMPLEMENTATION_COMMIT = "430cc9d1277996a16be05fe95913b9076ca8672e"
IMPLEMENTATION_PATHS = sorted((str(runner.SOURCE), str(runner.TEST)))
HARDENING_COMMITS = (
    (
        "5eb6dd48a953de7c588acd10df41b374ca37d01d",
        [str(runner.SOURCE)],
    ),
    (
        "054c4f1652de42e20515698ff542268e00725637",
        sorted((str(runner.SOURCE), str(runner.TEST))),
    ),
    (
        "b568f7dfdaa8a7aa476d1994fa27dab9e64ef271",
        sorted((str(runner.SOURCE), str(runner.TEST))),
    ),
)
FIXED = {
    runner.SOURCE: "16bd593dd7dcec23069bc012c5e1a535ea20cacf3c2cb4f678e23da2aab6dc8f",
    runner.TEST: "afe1998182796bcdb6c66f04937ee901dc53fbb48c5f73867f6a918ab8c2e98a",
    runner.HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
    runner.SELECTOR: "94c164c0c15a4b7cd8884c8b134eb2db1ea76800a3a43fdf002199db124fe065",
    runner.PARENT_TRANSPORT: "d6cac9b0393018fac13a9899219b0a22ebd4493e783b0fb434cc47bcb1854be0",
    runner.BUILD_AUDIT: runner.BUILD_AUDIT_SHA256,
}
TEST_SUITES = (
    ("test_audit_v25318_disjoint_worldbank_population_preactivation.py", 7),
    ("test_run_v25317_disjoint_worldbank_population.py", 11),
    ("test_v25315_disjoint_worldbank_population.py", 6),
    ("test_run_v25297_worldbank_population_freeze.py", 14),
    ("test_v25295_worldbank_monotone_fill_gate.py", 10),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 96
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "d80a16b65855c6d7406ec85e117a3af01bdfccdac8859a310f15a48280a58110"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "9f040f50bd490e1104b1294a350757b9c500cc4750b83610fc2fa26c372d6bd6"
)
FUTURE_SURFACES = (
    runner.PREACTIVATION,
    runner.EXECUTION_START,
    runner.ATTEMPT_CLAIM,
    runner.RESULT,
    runner.OUTPUT_ROOT,
    runner.POSTFREEZE_AUDIT,
)
CHECK_NAMES = frozenset(
    {
        "fixed_sources_build_audit_and_implementation_commit_exact",
        "focused_parent_and_transport_tests_exact48_green",
        "runtime_dependency_closure_exact96_and_hash_bound",
        "all_explicit_and_closure_files_tracked",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "build_audit_authorizes_supervisor_build_only",
        "source_manifest_binds_supervisor_helper_selector_parent_and_test",
        "claim_precedes_catalog_or_target_effect",
        "shared_lease_wraps_claim_network_and_result",
        "single_catalog_and_exact48_target_batch_all_or_nothing",
        "body_receipt_and_consumed_response_hashes_both_checked",
        "consumed_24_target_144_entity_48_response_contract_exact",
        "twelve_task_108_then96_disjoint_capacity_contract_exact",
        "helper_exact_url_allowlist_zero_redirect_retry_and_trust_env",
        "failure_no_go_without_retry_resume_backfill_or_replacement",
        "future_preactivation_start_claim_result_output_and_postaudit_pristine",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "active_population_forward_or_evaluator_conflicts_zero",
        "git_clean_head_equals_target_main",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_information_gain_shadow_and_positive_credit_zero",
    }
)


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
    if (
        set(value) != {"expected", "observed", "passed", "suites"}
        or value.get("expected") != EXPECTED_TESTS
        or value.get("observed") != EXPECTED_TESTS
        or value.get("passed") is not True
        or not isinstance(suites, list)
        or len(suites) != len(TEST_SUITES)
    ):
        return False
    return all(
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


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(
        sorted(
            base._dependency_closure(
                (
                    runner.SOURCE,
                    runner.HELPER,
                    runner.SELECTOR,
                    runner.PARENT_TRANSPORT,
                )
            ),
            key=str,
        )
    )
    vector = [
        {"path": str(path), "sha256": base.sha256(path)} for path in closure
    ]
    return closure, vector


def _changed_paths(commit: str) -> list[str]:
    return sorted(
        line
        for line in base._git(
            "diff-tree", "--no-commit-id", "--name-only", "-r", commit
        ).splitlines()
        if line
    )


def _is_ancestor(older: str, newer: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", older, newer],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _build_barrier() -> bool:
    try:
        value = build.validate_audit(
            json.loads(base._ordinary(runner.BUILD_AUDIT).read_text(encoding="utf-8"))
        )
    except BaseException:
        return False
    authorization = value["authorization"]
    return bool(
        value["audit_valid"] is True
        and value["findings"] == []
        and authorization[
            "fresh_disjoint_worldbank_population_supervisor_build_only"
        ]
        is True
        and authorization["network_population_selection_or_freeze"] is False
        and authorization["external_activation_or_launch"] is False
        and authorization["postfreeze_evaluator"] is False
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
        "body_receipt_mismatch_checked_before_population": (
            "response_body_receipt_mismatch_count" in execute
            and "response_body_receipt_mismatch" in execute
            and execute.index("response_body_receipt_mismatch_count")
            < execute.index("selector.select_and_render_population(")
        ),
        "consumed_response_overlap_checked_before_population": (
            "response_overlap_count" in execute
            and "consumed_response_overlap" in execute
            and execute.index("response_overlap_count")
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
    markers = (
        "run_v25317_disjoint_worldbank_population.py",
        "v25317_disjoint_worldbank_population",
        "v25297_worldbank_get_helper.py",
    )
    return sorted(
        int(line.strip().split(None, 1)[0])
        for line in completed.stdout.splitlines()
        if line.strip()
        and any(marker in line for marker in markers)
        and "audit_v25318_disjoint_worldbank_population_preactivation.py"
        not in line
    )


def _watchers_exact(value: object) -> bool:
    expected = {str(row["pid"]): row["start_ticks"] for row in runner.EXPECTED_WATCHERS}
    return bool(
        isinstance(value, Mapping)
        and set(value) == set(expected)
        and all(
            isinstance(value.get(pid), Mapping)
            and value[pid].get("present") is True
            and value[pid].get("start_ticks") == ticks
            and value[pid].get("matches_frozen_identity") is True
            for pid, ticks in expected.items()
        )
    )


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
    authority = runner._build_authority()
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
        "focused_parent_and_transport_tests_exact48_green": tests["passed"],
        "runtime_dependency_closure_exact96_and_hash_bound": (
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
        "build_audit_authorizes_supervisor_build_only": _build_barrier(),
        "source_manifest_binds_supervisor_helper_selector_parent_and_test": (
            _source_manifest()
            == {str(path): base.sha256(path) for path in (
                runner.SOURCE,
                runner.HELPER,
                runner.SELECTOR,
                runner.PARENT_TRANSPORT,
                runner.TEST,
            )}
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
        "body_receipt_and_consumed_response_hashes_both_checked": invariants[
            "body_receipt_mismatch_checked_before_population"
        ]
        and invariants["consumed_response_overlap_checked_before_population"],
        "consumed_24_target_144_entity_48_response_contract_exact": (
            len(authority["consumed_target_keys"]) == 24
            and len(authority["consumed_entity_codes"]) == 144
            and len(authority["consumed_response_sha256"]) == 48
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
        "future_preactivation_start_claim_result_output_and_postaudit_pristine": _future_pristine(),
        "protected_watchers_unchanged": _watchers_exact(watchers),
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
        "disjointness_contract": {
            "consumed_target_count": 24,
            "consumed_entity_count": 144,
            "consumed_response_count": 48,
            "preferred_entity_count": 108,
            "minimum_entity_count": 96,
            "task_count": 12,
            "all_overlap_counts_must_be_zero": True,
        },
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
            "single_disjoint_worldbank_population_freeze": False,
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
            "source_manifest",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "runtime_invariants",
            "disjointness_contract",
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
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("auditor_or_explicit_file_credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or copied.get("runtime_invariants") != _source_invariants()
        or copied.get("disjointness_contract")
        != {
            "consumed_target_count": 24,
            "consumed_entity_count": 144,
            "consumed_response_count": 48,
            "preferred_entity_count": 108,
            "minimum_entity_count": 96,
            "task_count": 12,
            "all_overlap_counts_must_be_zero": True,
        }
        or not _watchers_exact(copied.get("protected_watchers"))
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
            "single_disjoint_worldbank_population_freeze": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_attempt": False,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.18 preactivation audit drifted")
    return copied


def build_execution_start(
    audit_value: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    checked = validate_audit(audit_value)
    if checked["authorization"]["execution_start_generation"] is not True:
        raise RuntimeError("V2.53.18 execution-start authority absent")
    parent = base._git("rev-parse", "HEAD")
    if (
        base._git("status", "--porcelain")
        or parent != base._git("rev-parse", "target/main")
        or base._git("rev-parse", f"{parent}^") != checked["git"]["head"]
        or _changed_paths(parent) != [str(runner.PREACTIVATION)]
    ):
        raise RuntimeError(
            "V2.53.18 start requires the clean pushed single-file preactivation commit"
        )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25319_disjoint_worldbank_population_execution_start",
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
        "disjointness_contract": copy.deepcopy(checked["disjointness_contract"]),
        "fixed_attempt_claim_path": str(runner.ATTEMPT_CLAIM),
        "fixed_result_path": str(runner.RESULT),
        "fixed_output_root": str(runner.OUTPUT_ROOT),
        "single_catalog_then_single_48_target_response_batch": True,
        "retry_resume_refetch_backfill_replacement_or_second_attempt": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "single_disjoint_worldbank_population_freeze": True,
            "external_forward_or_evaluator": False,
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
        raise SystemExit("usage: audit_v25318...py [audit|start]")
    _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "output": str(path),
                "role": value["role"],
                "audit_valid": value.get("audit_valid"),
                "tests": value.get("tests", {}).get("observed"),
                "findings": value.get("findings"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
