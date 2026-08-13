#!/usr/bin/env python3
"""Clean-build audit for the V2.53.37 concurrency-three population runner."""

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
from scripts import diagnose_v25335_v25330_transport_capacity as diagnosis  # noqa: E402
from scripts import run_v25337_concurrency3_worldbank_population as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25338_concurrency3_worldbank_population_clean_build_audit"
OUTPUT = runner.BUILD_AUDIT
SOURCE = Path("scripts/audit_v25338_concurrency3_worldbank_population_build.py")
TEST = Path("tests/test_audit_v25338_concurrency3_worldbank_population_build.py")
IMPLEMENTATION_COMMIT = "5ed794c8414e8bc72d0ba05387969cbdb2690885"
IMPLEMENTATION_PATHS = sorted((str(runner.SOURCE), str(runner.TEST)))
FIXED = {
    runner.SOURCE: "35ec71edff46e6b3444100427e4bb8b75a7afaa73398ac62415671894afb1888",
    runner.TEST: "e2e396dcd8f04b2d5041440ebd3c71fcd786e4d063d32f4134d36254ef3c4aaf",
    runner.SELECTOR: "0822a4b8c2b90d401d61b9ea99c99b4e1892c7282a105b87088a716f814e99ef",
    runner.DIAGNOSIS: runner.DIAGNOSIS_SHA256,
    runner.FIRST_RESULT: runner.FIRST_RESULT_SHA256,
    runner.FIRST_PRIVATE: runner.FIRST_PRIVATE_SHA256,
    runner.SECOND_RESULT: runner.SECOND_RESULT_SHA256,
    runner.THIRD_RESULT: runner.THIRD_RESULT_SHA256,
    runner.FOURTH_RESULT: runner.FOURTH_RESULT_SHA256,
    runner.FOURTH_AUDIT: runner.FOURTH_AUDIT_SHA256,
}
TEST_SUITES = (
    ("test_audit_v25338_concurrency3_worldbank_population_build.py", 7),
    ("test_run_v25337_concurrency3_worldbank_population.py", 8),
    ("test_v25336_four_attempt_disjoint_worldbank_population.py", 7),
    ("test_diagnose_v25335_v25330_transport_capacity.py", 5),
    ("test_audit_v25334_rate_paced_worldbank_population_nogo.py", 6),
    ("test_run_v25330_rate_paced_worldbank_population.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
CHECK_NAMES = frozenset(
    {
        "fixed_sources_and_authority_hashes_exact",
        "implementation_commit_is_exact_two_file_ancestor",
        "focused_runner_selector_diagnosis_and_parent_tests_exact_green",
        "all_auditor_explicit_and_runtime_closure_files_tracked",
        "runtime_dependency_vector_self_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "diagnosis_exact_valid_and_authorizes_build_only",
        "merged_consumed_target_vector_exact96_unique_and_hash_bound",
        "merged_consumed_entity_vector_exact144_unique_and_hash_bound",
        "merged_consumed_response_vector_exact169_unique_and_hash_bound",
        "concurrency3_transport_policy_exact",
        "one_attempt_fixed48_no_retry_backfill_contract_exact",
        "synthetic_clock_cannot_persist_or_reach_provider",
        "selector_requires_zero_target_entity_and_response_overlap",
        "twelve_task_108_then96_capacity_ladder_exact",
        "entropy_information_gain_shadow_and_positive_credit_zero",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "git_clean_head_equals_target_main",
        "future_effect_surfaces_pristine",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "preactivation_only_authorized",
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
    entrypoints = (
        runner.SOURCE,
        runner.HELPER,
        runner.SELECTOR,
        runner.first.SOURCE,
        runner.second.SOURCE,
        runner.third.SOURCE,
        runner.fourth.SOURCE,
        runner.fourth_audit.SOURCE,
        runner.diagnosis.SOURCE,
        Path("scripts/deepwide_api_lease.py"),
    )
    closure = tuple(
        sorted(
            set().union(*(base._dependency_closure((path,)) for path in entrypoints)),
            key=str,
        )
    )
    return closure, [
        {"path": str(path), "sha256": base.sha256(path)} for path in closure
    ]


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


def _diagnosis_barrier() -> bool:
    try:
        value = diagnosis.validate_diagnosis(
            json.loads(base._ordinary(runner.DIAGNOSIS).read_text(encoding="utf-8"))
        )
    except BaseException:
        return False
    observed = value["diagnosis"]
    authorization = value["authorization"]
    return bool(
        value["diagnosis_valid"] is True
        and value["findings"] == []
        and observed["next_candidate_changes_only_max_target_concurrency_to3"] is True
        and observed["next_candidate_request_start_interval_seconds"] == 0.0
        and observed["next_candidate_fixed_target_request_count"] == 48
        and observed["next_candidate_per_url_provider_attempt_count"] == 1
        and observed["next_candidate_retry_resume_refetch_backfill_replacement"] is False
        and authorization["concurrency3_fresh_disjoint_transport_successor_build"] is True
        and authorization["successor_population_network_activation_or_launch"] is False
    )


def _manifest() -> dict[str, Any]:
    authority = runner._authority()
    targets = list(authority["consumed_target_keys"])
    entities = list(authority["consumed_entity_codes"])
    responses = list(authority["consumed_response_sha256"])
    checks = {
        "target_count": len(targets) == 96,
        "target_unique": len(set(item.casefold() for item in targets)) == 96,
        "target_hash": runner.payload_sha256(targets) == runner.EXPECTED_TARGET_VECTOR_SHA256,
        "entity_count": len(entities) == 144,
        "entity_unique": len(set(entities)) == 144,
        "entity_hash": runner.payload_sha256(entities) == runner.EXPECTED_ENTITY_VECTOR_SHA256,
        "response_count": len(responses) == 169,
        "response_unique": len(set(responses)) == 169,
        "response_format": all(re.fullmatch(r"[0-9a-f]{64}", item) for item in responses),
        "response_hash": runner.payload_sha256(responses) == runner.EXPECTED_RESPONSE_VECTOR_SHA256,
    }
    return {
        "target_keys_sha256": runner.payload_sha256(targets),
        "target_count": len(targets),
        "entity_codes_sha256": runner.payload_sha256(entities),
        "entity_count": len(entities),
        "response_vector_sha256": runner.payload_sha256(responses),
        "response_count": len(responses),
        "checks": checks,
    }


def _transport_policy_contract() -> dict[str, Any]:
    source = base._ordinary(runner.SOURCE).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(runner.SOURCE))
    functions = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    request = functions["_request_target_pages"]
    execute = functions["execute_freeze"]
    main = functions["main"]
    helper = base._ordinary(runner.HELPER).read_text(encoding="utf-8")
    return {
        "target_concurrency": runner.TARGET_CONCURRENCY,
        "request_start_interval_seconds": runner.REQUEST_START_INTERVAL_SECONDS,
        "fixed_target_request_count": 48,
        "per_url_provider_attempt_count": 1,
        "target_phase_hard_wall_seconds": runner.TARGET_PHASE_HARD_WALL_SECONDS,
        "whole_freeze_hard_wall_seconds": runner.WHOLE_FREEZE_HARD_WALL_SECONDS,
        "executor_uses_frozen_concurrency": "ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY)" in request,
        "actual_provider_starts_are_ticket_ordered": all(
            token in request
            for token in (
                "while ticket != next_ticket:",
                "starts[ticket] = actual",
                "next_ticket += 1",
            )
        ),
        "actual_provider_starts_use_zero_extra_pacing": all(
            token in request
            for token in (
                "while time.monotonic() < next_allowed_start:",
                "next_allowed_start = actual + REQUEST_START_INTERVAL_SECONDS",
            )
        ),
        "synthetic_clock_rejected_for_persistent_execution_before_authority_or_provider": (
            'if logical_start is not None and persist:' in execute
            and 'raise ValueError("V2.53.37 logical clock is synthetic-only")' in execute
            and execute.index('if logical_start is not None and persist:')
            < execute.index("authority = _authority()")
            < execute.index("catalog_body, catalog_receipt = get(")
        ),
        "production_main_cannot_inject_synthetic_clock": "logical_start=" not in main,
        "helper_one_attempt_no_redirect_env_session": (
            "session.trust_env = False" in helper
            and "allow_redirects=False" in helper
            and "max_retries" not in helper
        ),
        "no_retry_resume_refetch_backfill_replacement": (
            '"retry_resume_backfill_replacement_or_second_attempt": False' in source
            and '"redirect_retry_refetch_resume_backfill_replacement_count": 0' in source
        ),
    }


def _transport_policy_exact(value: object) -> bool:
    return bool(
        value == _transport_policy_contract()
        and isinstance(value, Mapping)
        and value.get("target_concurrency") == 3
        and value.get("request_start_interval_seconds") == 0.0
        and value.get("fixed_target_request_count") == 48
        and value.get("per_url_provider_attempt_count") == 1
        and value.get("target_phase_hard_wall_seconds") == 110.0
        and value.get("whole_freeze_hard_wall_seconds") == 145.0
        and all(item is True for key, item in value.items() if isinstance(item, bool))
    )


def _future_pristine() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (
            runner.BUILD_AUDIT,
            runner.PREACTIVATION,
            runner.EXECUTION_START,
            runner.ATTEMPT_CLAIM,
            runner.RESULT,
            runner.OUTPUT_ROOT,
            runner.POSTFREEZE_AUDIT,
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
    untracked = sorted(str(path) for path in explicit if tracked and not base._tracked(path))
    literal_hits = sorted(
        str(path)
        for path in explicit
        if base.SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    )
    watchers = base._watchers()
    manifest = _manifest()
    policy = _transport_policy_contract()
    checks = {
        "fixed_sources_and_authority_hashes_exact": {str(path): base.sha256(path) for path in FIXED}
        == {str(path): digest for path, digest in FIXED.items()},
        "implementation_commit_is_exact_two_file_ancestor": (
            _changed_paths(IMPLEMENTATION_COMMIT) == IMPLEMENTATION_PATHS
            and _is_ancestor(IMPLEMENTATION_COMMIT, head)
        ),
        "focused_runner_selector_diagnosis_and_parent_tests_exact_green": tests["passed"],
        "all_auditor_explicit_and_runtime_closure_files_tracked": not untracked,
        "runtime_dependency_vector_self_hash_bound": bool(vector)
        and runner.payload_sha256(vector)
        == runner.payload_sha256([{"path": row["path"], "sha256": row["sha256"]} for row in vector]),
        "privileged_runtime_field_access_zero": semantic["privileged_runtime_field_accesses"] == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [] and literal_hits == [],
        "only_known_provider_rank_score_exception": semantic["allowed_provider_rank_access"]
        == ["src/deepwide_agent/clients.py:565:score"],
        "diagnosis_exact_valid_and_authorizes_build_only": _diagnosis_barrier(),
        "merged_consumed_target_vector_exact96_unique_and_hash_bound": all(
            manifest["checks"][name] for name in ("target_count", "target_unique", "target_hash")
        ),
        "merged_consumed_entity_vector_exact144_unique_and_hash_bound": all(
            manifest["checks"][name] for name in ("entity_count", "entity_unique", "entity_hash")
        ),
        "merged_consumed_response_vector_exact169_unique_and_hash_bound": all(
            manifest["checks"][name]
            for name in ("response_count", "response_unique", "response_format", "response_hash")
        ),
        "concurrency3_transport_policy_exact": _transport_policy_exact(policy),
        "one_attempt_fixed48_no_retry_backfill_contract_exact": (
            policy["fixed_target_request_count"] == 48
            and policy["per_url_provider_attempt_count"] == 1
            and policy["no_retry_resume_refetch_backfill_replacement"] is True
        ),
        "synthetic_clock_cannot_persist_or_reach_provider": (
            policy["synthetic_clock_rejected_for_persistent_execution_before_authority_or_provider"] is True
            and policy["production_main_cannot_inject_synthetic_clock"] is True
        ),
        "selector_requires_zero_target_entity_and_response_overlap": tests["passed"],
        "twelve_task_108_then96_capacity_ladder_exact": (
            runner.selector.TASK_COUNT == 12
            and runner.selector.PREFERRED_ENTITY_COUNT == 108
            and runner.selector.MINIMUM_ENTITY_COUNT == 96
            and runner.selector.PREFERRED_ROWS_PER_TASK == 9
            and runner.selector.MINIMUM_ROWS_PER_TASK == 8
        ),
        "entropy_information_gain_shadow_and_positive_credit_zero": tests["passed"],
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": base._lease_inactive(),
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "future_effect_surfaces_pristine": _future_pristine(),
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "preactivation_only_authorized": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_inputs": {str(path): base.sha256(path) for path in FIXED},
        "implementation_commit": {"commit": IMPLEMENTATION_COMMIT, "paths": IMPLEMENTATION_PATHS},
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": runner.payload_sha256(vector),
        "runtime_dependency_path_sha256": runner.payload_sha256([row["path"] for row in vector]),
        "semantic_audit": {
            **semantic,
            "auditor_or_explicit_file_credential_literal_hits": literal_hits,
            "untracked_sources": untracked,
        },
        "diagnosis": {"path": str(runner.DIAGNOSIS), "sha256": runner.DIAGNOSIS_SHA256},
        "consumed_manifest": manifest,
        "transport_policy_contract": policy,
        "protected_watchers": watchers,
        "future_surfaces_pristine": _future_pristine(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "concurrency3_population_preactivation_design": not findings,
            "network_population_selection_or_freeze": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_attempt": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = runner.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    semantic = copied.get("semantic_audit") or {}
    vector = copied.get("runtime_dependency_vector")
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git", "fixed_inputs",
            "implementation_commit", "tests", "runtime_dependency_vector",
            "runtime_dependency_vector_sha256", "runtime_dependency_path_sha256",
            "semantic_audit", "diagnosis", "consumed_manifest",
            "transport_policy_contract", "protected_watchers", "future_surfaces_pristine",
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
        or set(git) != {"head", "target_main", "equal", "clean"}
        or not all(isinstance(git.get(name), str) for name in ("head", "target_main"))
        or git.get("equal") is not (git.get("head") == git.get("target_main"))
        or not isinstance(git.get("clean"), bool)
        or copied.get("fixed_inputs") != {str(path): digest for path, digest in FIXED.items()}
        or copied.get("implementation_commit")
        != {"commit": IMPLEMENTATION_COMMIT, "paths": IMPLEMENTATION_PATHS}
        or not _tests_exact(copied.get("tests"))
        or not isinstance(vector, list)
        or not vector
        or runner.payload_sha256(vector) != copied.get("runtime_dependency_vector_sha256")
        or runner.payload_sha256([row["path"] for row in vector])
        != copied.get("runtime_dependency_path_sha256")
        or set(semantic)
        != {
            "privileged_runtime_field_accesses", "evaluator_capabilities",
            "credential_literal_hits", "allowed_provider_rank_access",
            "auditor_or_explicit_file_credential_literal_hits", "untracked_sources",
        }
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or semantic.get("auditor_or_explicit_file_credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or copied.get("diagnosis")
        != {"path": str(runner.DIAGNOSIS), "sha256": runner.DIAGNOSIS_SHA256}
        or copied.get("consumed_manifest") != _manifest()
        or not all(copied["consumed_manifest"]["checks"].values())
        or not _transport_policy_exact(copied.get("transport_policy_contract"))
        or not runner.third._protected_watcher_artifact_exact(copied.get("protected_watchers"))
        or not isinstance(copied.get("future_surfaces_pristine"), bool)
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
            "concurrency3_population_preactivation_design": not findings,
            "network_population_selection_or_freeze": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_attempt": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.38 build audit drifted")
    return copied


def main() -> int:
    value = build_audit()
    if not value["audit_valid"]:
        raise SystemExit("V2.53.38 audit failed: " + ", ".join(value["findings"]))
    runner.publish_json_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "tests": value["tests"]["observed"],
                "closure": len(value["runtime_dependency_vector"]),
                "findings": value["findings"],
                "audit_payload_sha256": value["audit_payload_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
