#!/usr/bin/env python3
"""Preactivation audit and start builder for the V2.53.37 population attempt."""

from __future__ import annotations

import ast
import copy
import json
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
from scripts import audit_v25338_concurrency3_worldbank_population_build as build  # noqa: E402
from scripts import run_v25337_concurrency3_worldbank_population as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25339_concurrency3_worldbank_population_preactivation_audit"
OUTPUT = runner.PREACTIVATION
SOURCE = Path("scripts/audit_v25339_concurrency3_worldbank_population_preactivation.py")
TEST = Path("tests/test_audit_v25339_concurrency3_worldbank_population_preactivation.py")
IMPLEMENTATION_COMMIT = build.IMPLEMENTATION_COMMIT
IMPLEMENTATION_PATHS = build.IMPLEMENTATION_PATHS
BUILD_AUDITOR_COMMIT = "21bbc9e1efa55da239d3e4b8cc64cc6a7ea0bab1"
BUILD_AUDITOR_PATHS = sorted((str(build.SOURCE), str(build.TEST)))
BUILD_FREEZE_COMMIT = "612fdff0099b169063a5fe6bbcc78f2ae06233b0"
BUILD_AUDIT_SHA256 = "b876cfe50972ef4e51147dfc6f6b5a7315ca987485530d5cabd1323f7d700bac"
FIXED = {
    runner.SOURCE: "35ec71edff46e6b3444100427e4bb8b75a7afaa73398ac62415671894afb1888",
    runner.TEST: "e2e396dcd8f04b2d5041440ebd3c71fcd786e4d063d32f4134d36254ef3c4aaf",
    runner.HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
    runner.SELECTOR: "0822a4b8c2b90d401d61b9ea99c99b4e1892c7282a105b87088a716f814e99ef",
    runner.first.SOURCE: "d6cac9b0393018fac13a9899219b0a22ebd4493e783b0fb434cc47bcb1854be0",
    runner.second.SOURCE: "16bd593dd7dcec23069bc012c5e1a535ea20cacf3c2cb4f678e23da2aab6dc8f",
    runner.third.SOURCE: "9871626a6121aca242f0e99cbea405ff5d785e8e686a3a7570f367081e1543dd",
    runner.fourth.SOURCE: "0eb4d0eec50dee134a284e67c3fa4f996bbdcde8f399fe8b2ed6cf56835ee0de",
    runner.fourth_audit.SOURCE: "eb538c15b00b23f18700634d03c1e74c8ed03300c9809a61c06be40c76cf7932",
    runner.diagnosis.SOURCE: "b644696558d2a19fe593b00b321c1dc1d897a41ddaf40ed5ece5d12bc2a3c061",
    Path("scripts/deepwide_api_lease.py"): "8d9cffa78617b458172307d3558c76e9370f045f531c2f5aaaceb866f5a78c7d",
    build.SOURCE: "84923387e0c11d60dd4d8be8ce440cefb7a2fb1bf64f01b1dddcd36ead03a401",
    build.TEST: "b2999f6cad5cd26bcbed5a5adbc527fcec4340a7a09cdba08741d9ab23885474",
    runner.BUILD_AUDIT: BUILD_AUDIT_SHA256,
}
TEST_SUITES = (
    ("test_audit_v25339_concurrency3_worldbank_population_preactivation.py", 7),
    ("test_audit_v25338_concurrency3_worldbank_population_build.py", 7),
    ("test_run_v25337_concurrency3_worldbank_population.py", 8),
    ("test_v25336_four_attempt_disjoint_worldbank_population.py", 7),
    ("test_diagnose_v25335_v25330_transport_capacity.py", 5),
    ("test_audit_v25334_rate_paced_worldbank_population_nogo.py", 6),
    ("test_run_v25330_rate_paced_worldbank_population.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 105
EXPECTED_CLOSURE_VECTOR_SHA256 = "004f8a311244394760d2f3baab02f1daac2e2ee3c1acc0922f1270c59461962a"
EXPECTED_CLOSURE_PATH_SHA256 = "c0357417bca38c1e096e827faffd737e3f5369ffb565034c9c760d8b25fad9ac"
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
        "fixed_sources_build_audit_and_commits_exact",
        "focused_parent_and_transport_tests_exact_green",
        "runtime_dependency_closure_hash_bound",
        "all_explicit_and_closure_files_tracked",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "build_audit_authorizes_preactivation_only",
        "source_manifest_binds_all_direct_runtime_sources",
        "claim_precedes_catalog_or_target_effect",
        "shared_lease_wraps_claim_network_and_result",
        "single_catalog_and_exact48_target_batch_all_or_nothing",
        "target_concurrency3_and_zero_extra_pacing_exact",
        "synthetic_clock_cannot_persist_or_reach_provider",
        "body_receipt_and_consumed_response_hashes_both_checked",
        "consumed_96_target_144_entity_169_response_contract_exact",
        "twelve_task_108_then96_disjoint_capacity_contract_exact",
        "helper_exact_url_allowlist_zero_redirect_retry_and_trust_env",
        "failure_no_go_without_retry_resume_backfill_or_replacement",
        "future_start_claim_result_output_and_postaudit_pristine",
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
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
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
            == {"pattern", "expected", "observed", "returncode", "passed", "output_sha256"}
            and row.get("pattern") == pattern
            and row.get("expected") == expected
            and row.get("observed") == expected
            and row.get("returncode") == 0
            and row.get("passed") is True
            and re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256"))) is not None
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
        and value["tests"]["observed"] == 41
        and len(value["runtime_dependency_vector"]) == EXPECTED_CLOSURE_COUNT
        and authorization["concurrency3_population_preactivation_design"] is True
        and authorization["network_population_selection_or_freeze"] is False
        and authorization["external_forward_or_evaluator"] is False
    )


def _source_manifest() -> dict[str, str]:
    return runner._source_manifest()


def _transport_contract() -> dict[str, Any]:
    return {
        "catalog_url": runner.CATALOG_URL,
        "catalog_provider_attempt_count": 1,
        "candidate_target_count": 24,
        "target_provider_attempt_count": 48,
        "target_concurrency": 3,
        "request_start_interval_seconds": 0.0,
        "catalog_phase_hard_wall_seconds": 30.0,
        "target_phase_hard_wall_seconds": 110.0,
        "whole_freeze_hard_wall_seconds": 145.0,
    }


def _consumed_manifest_contract() -> dict[str, Any]:
    return {
        "target_count": 96,
        "entity_count": 144,
        "response_count": 169,
        "preferred_entity_count": 108,
        "minimum_entity_count": 96,
        "task_count": 12,
        "all_overlap_counts_must_be_zero": True,
    }


def _source_invariants() -> dict[str, bool]:
    source = base._ordinary(runner.SOURCE).read_text(encoding="utf-8")
    helper = base._ordinary(runner.HELPER).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(runner.SOURCE))
    functions = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    main = functions["main"]
    execute = functions["execute_freeze"]
    validate = functions["validate_result"]
    request = functions["_request_target_pages"]
    return {
        "claim_before_execute": main.index("publish_json_exclusive(ROOT / ATTEMPT_CLAIM")
        < main.index("execute_freeze("),
        "lease_wraps_claim_execute_result": main.index("with acquire_deepwide_api_lease(")
        < main.index("publish_json_exclusive(ROOT / ATTEMPT_CLAIM")
        < main.index("execute_freeze(")
        < main.index("publish_json_exclusive(ROOT / RESULT"),
        "all48_required": (
            "len(target_rows) != 48" in execute
            and "len(candidate_bodies) != selector.MINIMUM_TARGET_OVERSAMPLE" in execute
            and 'any(row["outcome"] != "success"' in execute
        ),
        "target_concurrency_exact3": (
            runner.TARGET_CONCURRENCY == 3
            and "ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY)" in request
        ),
        "actual_starts_ticket_ordered_and_zero_extra_pacing": (
            runner.REQUEST_START_INTERVAL_SECONDS == 0.0
            and "while ticket != next_ticket:" in request
            and "while time.monotonic() < next_allowed_start:" in request
            and "next_allowed_start = actual + REQUEST_START_INTERVAL_SECONDS" in request
            and "starts[ticket] = actual" in request
        ),
        "synthetic_clock_rejected_before_authority_or_provider": (
            'if logical_start is not None and persist:' in execute
            and execute.index('if logical_start is not None and persist:')
            < execute.index("authority = _authority()")
            < execute.index("catalog_body, catalog_receipt = get(")
            and "logical_start=" not in main
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
            '"retry_resume_backfill_replacement_or_second_attempt": False' in source
            and '"redirect_retry_refetch_resume_backfill_replacement_count": 0' in source
        ),
        "visible_only_and_credit_zero": (
            '"mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False'
            in source
            and '"entropy_or_information_gain_assigns_signed_credit": False' in source
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
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        argv = parts[1].split()
        runner_entry = any(
            token.endswith("/scripts/run_v25337_concurrency3_worldbank_population.py")
            or token == "scripts/run_v25337_concurrency3_worldbank_population.py"
            for token in argv[:8]
        )
        helper_entry = any(
            token.endswith("/scripts/v25297_worldbank_get_helper.py")
            or token == "scripts/v25297_worldbank_get_helper.py"
            for token in argv[:8]
        )
        if runner_entry or helper_entry:
            output.append(int(parts[0]))
    return sorted(output)


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {SOURCE, TEST, *FIXED, *closure}
    untracked = sorted(str(path) for path in explicit if tracked and not base._tracked(path))
    literal_hits = sorted(
        str(path)
        for path in explicit
        if base.SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    )
    watchers = base._watchers()
    invariants = _source_invariants()
    conflicts = _active_conflicts()
    checks = {
        "fixed_sources_build_audit_and_commits_exact": (
            {str(path): base.sha256(path) for path in FIXED}
            == {str(path): digest for path, digest in FIXED.items()}
            and _changed_paths(IMPLEMENTATION_COMMIT) == IMPLEMENTATION_PATHS
            and _changed_paths(BUILD_AUDITOR_COMMIT) == BUILD_AUDITOR_PATHS
            and _changed_paths(BUILD_FREEZE_COMMIT) == [str(runner.BUILD_AUDIT)]
            and all(_is_ancestor(commit, head) for commit in (IMPLEMENTATION_COMMIT, BUILD_AUDITOR_COMMIT, BUILD_FREEZE_COMMIT))
        ),
        "focused_parent_and_transport_tests_exact_green": tests["passed"],
        "runtime_dependency_closure_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and runner.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and runner.payload_sha256([row["path"] for row in vector]) == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "all_explicit_and_closure_files_tracked": not untracked,
        "privileged_runtime_field_access_zero": semantic["privileged_runtime_field_accesses"] == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [] and literal_hits == [],
        "only_known_provider_rank_score_exception": semantic["allowed_provider_rank_access"]
        == ["src/deepwide_agent/clients.py:565:score"],
        "build_audit_authorizes_preactivation_only": _build_barrier(),
        "source_manifest_binds_all_direct_runtime_sources": _source_manifest()
        == {str(path): base.sha256(path) for path in map(Path, runner._source_manifest())},
        "claim_precedes_catalog_or_target_effect": invariants["claim_before_execute"],
        "shared_lease_wraps_claim_network_and_result": invariants["lease_wraps_claim_execute_result"],
        "single_catalog_and_exact48_target_batch_all_or_nothing": invariants["all48_required"],
        "target_concurrency3_and_zero_extra_pacing_exact": (
            invariants["target_concurrency_exact3"]
            and invariants["actual_starts_ticket_ordered_and_zero_extra_pacing"]
            and build._transport_policy_exact(build._transport_policy_contract())
        ),
        "synthetic_clock_cannot_persist_or_reach_provider": invariants["synthetic_clock_rejected_before_authority_or_provider"],
        "body_receipt_and_consumed_response_hashes_both_checked": (
            invariants["body_receipt_mismatch_checked_before_population"]
            and invariants["consumed_response_overlap_checked_before_population"]
        ),
        "consumed_96_target_144_entity_169_response_contract_exact": (
            _consumed_manifest_contract()
            == {
                "target_count": 96,
                "entity_count": 144,
                "response_count": 169,
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
        "helper_exact_url_allowlist_zero_redirect_retry_and_trust_env": invariants["helper_zero_redirect_retry_and_env"],
        "failure_no_go_without_retry_resume_backfill_or_replacement": invariants["retry_resume_backfill_replacement_zero"],
        "future_start_claim_result_output_and_postaudit_pristine": _future_pristine(),
        "protected_watchers_unchanged": runner.third._protected_watcher_artifact_exact(watchers),
        "shared_api_lease_inactive": base._lease_inactive(),
        "active_population_forward_or_evaluator_conflicts_zero": not conflicts,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "entropy_information_gain_shadow_and_positive_credit_zero": invariants["visible_only_and_credit_zero"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_inputs": {str(path): base.sha256(path) for path in FIXED},
        "implementation_commits": {
            "runner": {"commit": IMPLEMENTATION_COMMIT, "paths": IMPLEMENTATION_PATHS},
            "build_auditor": {"commit": BUILD_AUDITOR_COMMIT, "paths": BUILD_AUDITOR_PATHS},
            "build_freeze": {"commit": BUILD_FREEZE_COMMIT, "paths": [str(runner.BUILD_AUDIT)]},
        },
        "build_audit": {"path": str(runner.BUILD_AUDIT), "sha256": BUILD_AUDIT_SHA256},
        "source_manifest": _source_manifest(),
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": runner.payload_sha256(vector),
        "runtime_dependency_path_sha256": runner.payload_sha256([row["path"] for row in vector]),
        "semantic_audit": {
            **semantic,
            "auditor_or_explicit_file_credential_literal_hits": literal_hits,
            "untracked_sources": untracked,
        },
        "runtime_invariants": invariants,
        "transport_contract": _transport_contract(),
        "consumed_manifest_contract": _consumed_manifest_contract(),
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
            "single_concurrency3_population_freeze": False,
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
            "artifact_version", "role", "created_at_unix", "git", "fixed_inputs",
            "implementation_commits", "build_audit", "source_manifest", "tests",
            "runtime_dependency_vector", "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256", "semantic_audit", "runtime_invariants",
            "transport_contract", "consumed_manifest_contract", "protected_watchers",
            "shared_api_lease_inactive", "active_conflicts", "future_surfaces_pristine",
            "checks", "findings", "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or not isinstance(copied.get("git"), Mapping)
        or set(copied["git"]) != {"head", "target_main", "equal", "clean"}
        or copied["git"].get("equal") is not (copied["git"].get("head") == copied["git"].get("target_main"))
        or not isinstance(copied["git"].get("clean"), bool)
        or copied.get("fixed_inputs") != {str(path): digest for path, digest in FIXED.items()}
        or copied.get("implementation_commits")
        != {
            "runner": {"commit": IMPLEMENTATION_COMMIT, "paths": IMPLEMENTATION_PATHS},
            "build_auditor": {"commit": BUILD_AUDITOR_COMMIT, "paths": BUILD_AUDITOR_PATHS},
            "build_freeze": {"commit": BUILD_FREEZE_COMMIT, "paths": [str(runner.BUILD_AUDIT)]},
        }
        or copied.get("build_audit") != {"path": str(runner.BUILD_AUDIT), "sha256": BUILD_AUDIT_SHA256}
        or copied.get("source_manifest") != _source_manifest()
        or not _tests_exact(copied.get("tests"))
        or not isinstance(vector, list)
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or runner.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_vector_sha256") != EXPECTED_CLOSURE_VECTOR_SHA256
        or runner.payload_sha256([row["path"] for row in vector]) != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("runtime_dependency_path_sha256") != EXPECTED_CLOSURE_PATH_SHA256
        or set(semantic)
        != {
            "privileged_runtime_field_accesses", "evaluator_capabilities",
            "credential_literal_hits", "allowed_provider_rank_access",
            "auditor_or_explicit_file_credential_literal_hits", "untracked_sources",
        }
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("auditor_or_explicit_file_credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or semantic.get("allowed_provider_rank_access") != ["src/deepwide_agent/clients.py:565:score"]
        or copied.get("runtime_invariants") != _source_invariants()
        or copied.get("transport_contract") != _transport_contract()
        or copied.get("consumed_manifest_contract") != _consumed_manifest_contract()
        or not runner.third._protected_watcher_artifact_exact(copied.get("protected_watchers"))
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
            "single_concurrency3_population_freeze": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_attempt": False,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.39 preactivation audit drifted")
    return copied


def build_execution_start(
    audit_value: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    checked = validate_audit(audit_value)
    if checked["authorization"]["execution_start_generation"] is not True:
        raise RuntimeError("V2.53.39 execution-start authority absent")
    parent = base._git("rev-parse", "HEAD")
    if (
        base._git("status", "--porcelain")
        or parent != base._git("rev-parse", "target/main")
        or base._git("rev-parse", f"{parent}^") != checked["git"]["head"]
        or _changed_paths(parent) != [str(runner.PREACTIVATION)]
    ):
        raise RuntimeError("V2.53.39 start requires the clean pushed single-file preactivation commit")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25340_concurrency3_worldbank_population_execution_start",
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
        "transport_contract": checked["transport_contract"],
        "consumed_manifest_contract": checked["consumed_manifest_contract"],
        "fixed_attempt_claim_path": str(runner.ATTEMPT_CLAIM),
        "fixed_result_path": str(runner.RESULT),
        "fixed_output_root": str(runner.OUTPUT_ROOT),
        "single_catalog_then_single_48_target_response_batch": True,
        "retry_resume_refetch_backfill_replacement_or_second_attempt": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "single_concurrency3_population_freeze": True,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
        },
    }
    value["start_payload_sha256"] = runner.payload_sha256(value)
    return runner._validate_execution_start(value, current_head="0" * 40)


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) == 2 else "audit"
    if stage == "audit":
        value = build_audit()
        path = runner.PREACTIVATION
    elif stage == "start":
        value = build_execution_start(
            json.loads(base._ordinary(runner.PREACTIVATION).read_text(encoding="utf-8"))
        )
        path = runner.EXECUTION_START
    else:
        raise SystemExit("usage: audit_v25339...py [audit|start]")
    runner.publish_json_exclusive(ROOT / path, value)
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
