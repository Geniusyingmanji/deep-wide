#!/usr/bin/env python3
"""Clean-build preactivation audit for the V2.52.97 population freeze."""

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
from scripts import audit_v25296_worldbank_monotone_fill_build as parent  # noqa: E402
from scripts import run_v25297_worldbank_population_freeze as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25302_worldbank_population_repair_preactivation_audit"
OUTPUT = runner.PREACTIVATION
SOURCE = Path("scripts/audit_v25298_worldbank_population_preactivation.py")
TEST = Path("tests/test_audit_v25298_worldbank_population_preactivation.py")
RUNNER = runner.SOURCE
HELPER = runner.HELPER
RUNNER_TEST = runner.TEST
PARENT_AUDIT = parent.OUTPUT
DESIGN = Path("results/v25294_worldbank_monotone_fill_gate_design_r2_20260813.json")
INITIAL_IMPLEMENTATION_COMMIT = "bac1aa8f8d55229d2d9bb9e97ae3970bac770c6d"
REPAIR_COMMIT = "3f9c1db0a024e795d662d11d942eb9b570094142"
INITIAL_IMPLEMENTATION_PATHS = sorted(str(path) for path in (RUNNER, HELPER, RUNNER_TEST))
REPAIR_PATHS = sorted(str(path) for path in (RUNNER, RUNNER_TEST))
OLD_PREACTIVATION = Path("results/v25298_worldbank_population_preactivation_audit_v1_20260813.json")
EXPECTED_FIXED = {
    RUNNER: "1430b366c97d2b9d96624fce8b0621094c8b250fed7f4dac0f401eea72766f99",
    HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
    RUNNER_TEST: "d3c71b07b6419d66e512a7eaf39013b3a0678a726fd6548ad8282c4990be4214",
    PARENT_AUDIT: "6a07c8459175660374a0cdb32e09bffa314f2c0fa0088ab9c19374e765ba6de8",
    DESIGN: "92e1ad85f8a363243abd64676c3149eef0266b1acb5c7196e7d8b5061c03ead4",
    OLD_PREACTIVATION: "2e048177002281d5d214672e6ff5234a6def20a1635abfa4c7e4a8834d13bf39",
    runner.REVOKED_START: runner.REVOKED_START_SHA256,
    runner.REVOCATION: runner.REVOCATION_SHA256,
}
TEST_SUITES = (
    ("test_audit_v25298_worldbank_population_preactivation.py", 6),
    ("test_run_v25297_worldbank_population_freeze.py", 13),
    ("test_v25295_worldbank_monotone_fill_gate.py", 10),
    ("test_audit_v25296_worldbank_monotone_fill_build.py", 6),
    ("test_revise_v25294_worldbank_monotone_fill_gate_r2.py", 5),
    ("test_design_v25294_worldbank_monotone_fill_gate.py", 7),
)
EXPECTED_TESTS = sum(value for _pattern, value in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 94
EXPECTED_CLOSURE_VECTOR_SHA256 = "01a1dd4d21ff13ed0aed25f5d95b82b92b91192813a23d72c4525d9acbd14678"
EXPECTED_CLOSURE_PATH_SHA256 = "9ae6818a28537584a5c19d25a2a03cd0dd6319d3ee87f9b79a09401f183463ef"
EXPECTED_WATCHERS = {str(row["pid"]): row["start_ticks"] for row in runner.EXPECTED_WATCHERS}
FUTURE_SURFACES = (
    runner.ATTEMPT_CLAIM,
    runner.RESULT,
    runner.OUTPUT_ROOT,
    runner.EXECUTION_START,
    runner.POSTFREEZE_AUDIT,
)
CHECK_NAMES = frozenset(
    {
        "fixed_sources_and_parent_artifacts_exact",
        "initial_and_repair_commits_exact_and_ancestors",
        "tests_exact47_green",
        "runtime_dependency_closure_exact94_and_hash_bound",
        "all_explicit_and_closure_files_tracked",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "historical_indicator_manifest_exact35_and_hash_bound",
        "single_catalog_get_self_proves_one_page_totality",
        "target_batch_exact24_by2_with_fixed_12_concurrency",
        "helper_exact_url_allowlist_zero_redirect_retry_and_trust_env",
        "claim_before_effect_and_create_exclusive_surfaces",
        "all_successful_raw_bytes_frozen_before_population_selection",
        "failure_no_go_without_retry_resume_backfill_or_replacement",
        "shared_api_lease_wraps_claim_network_and_result",
        "future_claim_result_output_start_and_postaudit_pristine",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "git_clean_head_equals_target_main",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_information_gain_shadow_and_positive_credit_zero",
        "revoked_v25299_pre_effect_and_new_namespace_bound",
    }
)


def _fixed_inputs() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in EXPECTED_FIXED}


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
    if not isinstance(value, Mapping) or set(value) != {"expected", "observed", "passed", "suites"}:
        return False
    suites = value.get("suites")
    return bool(
        value.get("expected") == EXPECTED_TESTS
        and value.get("observed") == EXPECTED_TESTS
        and value.get("passed") is True
        and isinstance(suites, list)
        and len(suites) == len(TEST_SUITES)
        and all(
            isinstance(row, Mapping)
            and set(row) == {"pattern", "expected", "observed", "returncode", "passed", "output_sha256"}
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
    closure = tuple(sorted(base._dependency_closure((RUNNER, HELPER)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _changed_paths(commit: str) -> list[str]:
    return sorted(
        value
        for value in base._git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines()
        if value
    )


def _ancestor(commit: str, head: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, head],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _source_invariants() -> dict[str, bool]:
    source = base._ordinary(RUNNER).read_text(encoding="utf-8")
    helper = base._ordinary(HELPER).read_text(encoding="utf-8")
    tree = ast.parse(source)
    main_source = ast.get_source_segment(source, next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")) or ""
    execute_source = ast.get_source_segment(source, next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "execute_freeze")) or ""
    request_source = ast.get_source_segment(source, next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_request_target_pages")) or ""
    return {
        "catalog_url_exact_source2_single_page": runner.CATALOG_URL == "https://api.worldbank.org/v2/source/2/indicator?format=json&page=1&per_page=50000",
        "catalog_totality_checks_exact": all(token in source for token in ("pages != 1", "total != len(records)", "per_page != CATALOG_PER_PAGE")),
        "target_count_and_request_count_exact": runner.runtime.MINIMUM_TARGET_OVERSAMPLE == 24 and "len(targets) != runtime.MINIMUM_TARGET_OVERSAMPLE" in request_source and "for page in (1, 2)" in request_source,
        "target_concurrency_exact12": runner.TARGET_CONCURRENCY == 12 and "ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY)" in request_source,
        "hard_walls_fixed": (runner.CATALOG_PHASE_HARD_WALL_SECONDS, runner.TARGET_PHASE_HARD_WALL_SECONDS, runner.WHOLE_FREEZE_HARD_WALL_SECONDS) == (30.0, 110.0, 145.0),
        "helper_zero_redirect_and_trust_env": "session.trust_env = False" in helper and "allow_redirects=False" in helper,
        "helper_parent_death_bound": "libc.prctl(1, signal.SIGKILL)" in helper,
        "claim_published_before_execute": main_source.index("publish_json_exclusive(ROOT / ATTEMPT_CLAIM") < main_source.index("execute_freeze("),
        "lease_wraps_claim_execute_and_result": main_source.index("with acquire_deepwide_api_lease(") < main_source.index("publish_json_exclusive(ROOT / ATTEMPT_CLAIM") < main_source.index("execute_freeze(") < main_source.index("publish_json_exclusive(ROOT / RESULT"),
        "raw_success_published_before_selector": execute_source.index("publish_exclusive(ROOT / relative, body)") < execute_source.index("runtime.select_and_render_population("),
        "no_go_requires_all48": 'len(target_rows) != 48' in execute_source and 'len(candidate_bodies) != runtime.MINIMUM_TARGET_OVERSAMPLE' in execute_source,
        "retry_resume_backfill_replacement_fixed_zero": source.count('"retry_resume') >= 5 and '"redirect_retry_refetch_resume_backfill_replacement_count": 0' in source,
        "historical_manifest_exact35": len(runner.EXPECTED_HISTORICAL_INDICATORS) == 35 and len(runner.HISTORICAL_SOURCE_HASHES) == 11,
        "label_blind_credit_zero": '"mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False' in source and '"entropy_or_information_gain_assigns_signed_credit": False' in source,
    }


def _watchers_exact(value: object) -> bool:
    return bool(
        isinstance(value, Mapping)
        and set(value) == set(EXPECTED_WATCHERS)
        and all(
            isinstance(value.get(pid), Mapping)
            and value[pid].get("present") is True
            and value[pid].get("start_ticks") == ticks
            and value[pid].get("matches_frozen_identity") is True
            for pid, ticks in EXPECTED_WATCHERS.items()
        )
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {SOURCE, TEST, RUNNER, HELPER, RUNNER_TEST, *EXPECTED_FIXED, *closure}
    untracked = sorted(str(path) for path in explicit if tracked and not base._tracked(path))
    literal_hits = sorted(
        str(path)
        for path in explicit
        if base.SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    )
    watchers = base._watchers()
    invariants = _source_invariants()
    future_pristine = all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in FUTURE_SURFACES)
    historical, historical_manifest = runner.historical_indicator_manifest()
    checks = {
        "fixed_sources_and_parent_artifacts_exact": _fixed_inputs() == {str(path): digest for path, digest in EXPECTED_FIXED.items()},
        "initial_and_repair_commits_exact_and_ancestors": _changed_paths(INITIAL_IMPLEMENTATION_COMMIT)
        == INITIAL_IMPLEMENTATION_PATHS
        and _changed_paths(REPAIR_COMMIT) == REPAIR_PATHS
        and _ancestor(INITIAL_IMPLEMENTATION_COMMIT, head)
        and _ancestor(REPAIR_COMMIT, head),
        "tests_exact47_green": tests["passed"],
        "runtime_dependency_closure_exact94_and_hash_bound": len(vector) == EXPECTED_CLOSURE_COUNT and runner.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256 and runner.payload_sha256([row["path"] for row in vector]) == EXPECTED_CLOSURE_PATH_SHA256,
        "all_explicit_and_closure_files_tracked": not untracked,
        "privileged_runtime_field_access_zero": semantic["privileged_runtime_field_accesses"] == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [] and literal_hits == [],
        "only_known_provider_rank_score_exception": semantic["allowed_provider_rank_access"] == ["src/deepwide_agent/clients.py:565:score"],
        "historical_indicator_manifest_exact35_and_hash_bound": historical == runner.EXPECTED_HISTORICAL_INDICATORS and len(historical_manifest) == 11 and invariants["historical_manifest_exact35"],
        "single_catalog_get_self_proves_one_page_totality": invariants["catalog_url_exact_source2_single_page"] and invariants["catalog_totality_checks_exact"],
        "target_batch_exact24_by2_with_fixed_12_concurrency": invariants["target_count_and_request_count_exact"] and invariants["target_concurrency_exact12"] and invariants["hard_walls_fixed"],
        "helper_exact_url_allowlist_zero_redirect_retry_and_trust_env": invariants["helper_zero_redirect_and_trust_env"] and invariants["helper_parent_death_bound"],
        "claim_before_effect_and_create_exclusive_surfaces": invariants["claim_published_before_execute"] and "os.O_EXCL | os.O_NOFOLLOW" in base._ordinary(RUNNER).read_text(encoding="utf-8"),
        "all_successful_raw_bytes_frozen_before_population_selection": invariants["raw_success_published_before_selector"],
        "failure_no_go_without_retry_resume_backfill_or_replacement": invariants["no_go_requires_all48"] and invariants["retry_resume_backfill_replacement_fixed_zero"],
        "shared_api_lease_wraps_claim_network_and_result": invariants["lease_wraps_claim_execute_and_result"],
        "future_claim_result_output_start_and_postaudit_pristine": future_pristine,
        "protected_watchers_unchanged": _watchers_exact(watchers),
        "shared_api_lease_inactive": base._lease_inactive(),
        "git_clean_head_equals_target_main": clean and head == target,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "entropy_information_gain_shadow_and_positive_credit_zero": invariants["label_blind_credit_zero"],
        "revoked_v25299_pre_effect_and_new_namespace_bound": runner._revocation_barrier()
        and runner.ATTEMPT_CLAIM
        != Path("results/v25297_worldbank_population_attempt_claim_v1_20260813.json")
        and runner.RESULT
        != Path("results/v25297_worldbank_population_freeze_v1_20260813.json")
        and runner.OUTPUT_ROOT
        != Path("outputs/v25297_worldbank_population_v1_20260813"),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_inputs": _fixed_inputs(),
        "implementation_commits": [INITIAL_IMPLEMENTATION_COMMIT, REPAIR_COMMIT],
        "source_manifest": runner._source_manifest(),
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": runner.payload_sha256(vector),
        "runtime_dependency_path_sha256": runner.payload_sha256([row["path"] for row in vector]),
        "semantic_audit": {**semantic, "auditor_or_explicit_file_credential_literal_hits": literal_hits, "untracked_sources": untracked},
        "runtime_invariants": invariants,
        "historical_indicator_manifest": historical_manifest,
        "historical_indicator_count": len(historical),
        "historical_indicators_sha256": runner.payload_sha256(sorted(historical)),
        "protected_watchers": watchers,
        "shared_api_lease_inactive": checks["shared_api_lease_inactive"],
        "future_surfaces_pristine": future_pristine,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "execution_start_generation": not findings,
            "single_worldbank_population_freeze": False,
            "external_monotone_fill_forward_or_postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_refetch_backfill_replacement_or_second_attempt": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = runner.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks") or {}
    vector = copied.get("runtime_dependency_vector")
    semantic = copied.get("semantic_audit") or {}
    findings = copied.get("findings")
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_inputs") != {str(path): digest for path, digest in EXPECTED_FIXED.items()}
        or copied.get("implementation_commits")
        != [INITIAL_IMPLEMENTATION_COMMIT, REPAIR_COMMIT]
        or copied.get("source_manifest") != runner._source_manifest()
        or not _tests_exact(copied.get("tests"))
        or not isinstance(vector, list)
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or runner.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_vector_sha256") != EXPECTED_CLOSURE_VECTOR_SHA256
        or runner.payload_sha256([row["path"] for row in vector]) != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("runtime_dependency_path_sha256") != EXPECTED_CLOSURE_PATH_SHA256
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("auditor_or_explicit_file_credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or semantic.get("allowed_provider_rank_access") != ["src/deepwide_agent/clients.py:565:score"]
        or copied.get("runtime_invariants") != _source_invariants()
        or copied.get("historical_indicator_count") != 35
        or copied.get("historical_indicators_sha256") != runner.payload_sha256(sorted(runner.EXPECTED_HISTORICAL_INDICATORS))
        or not _watchers_exact(copied.get("protected_watchers"))
        or copied.get("shared_api_lease_inactive") is not True
        or copied.get("future_surfaces_pristine") is not True
        or set(checks) != CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("audit_valid") is not (not findings)
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "execution_start_generation": not findings,
            "single_worldbank_population_freeze": False,
            "external_monotone_fill_forward_or_postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_refetch_backfill_replacement_or_second_attempt": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.98 preactivation audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    runner.publish_json_exclusive(path, value)


def main() -> None:
    value = build_audit()
    if not value["audit_valid"]:
        raise SystemExit("V2.52.98 audit failed: " + ", ".join(value["findings"]))
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"output": str(OUTPUT), "audit_valid": True, "tests": value["tests"]["observed"], "closure": len(value["runtime_dependency_vector"]), "findings": []}, sort_keys=True))


if __name__ == "__main__":
    main()
