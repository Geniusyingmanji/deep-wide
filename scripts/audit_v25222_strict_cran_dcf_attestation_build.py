#!/usr/bin/env python3
"""Clean build audit for V2.52.22 strict CRAN DCF body attestation."""

from __future__ import annotations

import ast
import copy
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25222_strict_cran_dcf_attestation as attestor  # noqa: E402
from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import audit_v25220_content_type_disposition_build as observer_audit  # noqa: E402
from scripts import design_v25221_cran_repository_format_evidence as design  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25222_strict_cran_dcf_attestation_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25222_strict_cran_dcf_attestation_build.py")
TEST = Path("tests/test_audit_v25222_strict_cran_dcf_attestation_build.py")
ATTESTOR_SOURCE = Path("src/deepwide_agent/v25222_strict_cran_dcf_attestation.py")
ATTESTOR_TEST = Path("tests/test_v25222_strict_cran_dcf_attestation.py")
DESIGN = design.OUTPUT
OBSERVER_AUDIT = observer_audit.OUTPUT
OBSERVER_SOURCE = Path("src/deepwide_agent/v25220_content_type_disposition.py")
TRANSPORT_SOURCE = Path("src/deepwide_agent/v25217_single_snapshot_transport.py")
FIXED_HASHES = {
    ATTESTOR_SOURCE: "12665386ed26af983de2ccc2e0a209726dc95937609d53241c8590c1167af0a1",
    ATTESTOR_TEST: "b4c1083ae24e3af7a91b05a565e66b5cdb6ab71b5c7a8e3f1460eeaa7785e53e",
    DESIGN: "d3e106735d70f9c827a9727f37eb9ad5162c33d31da98d54fcb84d0990fa59b9",
    OBSERVER_AUDIT: "4ce79154f88d835faf6f80287ce0c2b66d249287d7d5ee1dcd1bed3d39ddcb5a",
    OBSERVER_SOURCE: "4fa28fd85c31fe70349122ba34c83a4eef582a908a16103f0ee25d4f277e609f",
    TRANSPORT_SOURCE: "946e8ddee6f1f4819b9f5df018e42009b9f2616685b2008a83162e6e667c411e",
}
TEST_SUITES = (
    ("test_audit_v25222_strict_cran_dcf_attestation_build.py", 7),
    ("test_v25222_strict_cran_dcf_attestation.py", 11),
    ("test_design_v25221_cran_repository_format_evidence.py", 6),
    ("test_audit_v25220_content_type_disposition_build.py", 6),
    ("test_v25220_content_type_disposition.py", 8),
    ("test_v25217_single_snapshot_transport.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256

TOP_LEVEL_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "git",
        "tests",
        "fixed_artifact_hashes",
        "dependency_closure",
        "direct_capability_audit",
        "semantic_audit",
        "runtime_state",
        "checks",
        "findings",
        "audit_valid",
        "known_safe_alternate_mime_allowlist_count",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "audit_payload_sha256",
    }
)
GIT_FIELDS = frozenset({"head", "target_main", "equal", "clean"})
TESTS_FIELDS = frozenset({"expected", "observed", "passed", "suites"})
SUITE_FIELDS = frozenset(
    {"pattern", "expected", "observed", "returncode", "passed", "output_sha256"}
)
CAPABILITY_FIELDS = frozenset(
    {
        "imports",
        "top_level_effect_calls",
        "filesystem_process_environment_network_model_search_evaluator_imports",
    }
)
SEMANTIC_FIELDS = frozenset(
    {
        "privileged_runtime_field_accesses",
        "evaluator_capabilities",
        "credential_literal_hits",
        "allowed_provider_rank_access",
        "untracked_sources",
    }
)
RUNTIME_STATE_FIELDS = frozenset(
    {"shared_api_lease_inactive", "protected_watchers"}
)
WATCHER_FIELDS = frozenset(
    {"present", "start_ticks", "matches_frozen_identity"}
)
CHECK_FIELDS = frozenset(
    {
        "attestor_design_observer_transport_tests_exact46",
        "attestor_parent_and_design_hashes_match",
        "v25221_official_repository_format_design_bound",
        "v25220_empty_alternate_allowlist_observer_bound",
        "all_sources_tests_and_parent_artifacts_tracked",
        "git_clean_head_equals_target_main",
        "dependency_closure_exactly_one_pure_attestor",
        "direct_effect_capability_imports_absent",
        "import_time_effect_calls_absent",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "provider_rank_score_exception_zero",
        "body_length_and_sha256_binding_before_parse",
        "strict_utf8_control_newline_dcf_and_duplicate_field_checks",
        "minimum_64_distinct_valid_record_coverage",
        "oversize_and_malformed_input_have_finite_failure_receipts",
        "attestation_never_changes_mime_or_transport_acceptance",
        "receipt_contains_only_body_hash_length_and_aggregate_counts",
        "no_external_effect_performed",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
    }
)
AUTHORIZATION_FIELDS = frozenset(
    {
        "strict_cran_dcf_body_attestation_build_only",
        "content_type_or_transport_acceptance_change",
        "fresh_transport_observability_protocol_design",
        "public_snapshot_network_access_or_execution_start",
        "v25219_retry_refetch_backfill_replacement_or_second_batch",
        "real_identity_selection_or_population_freeze",
        "probe_runtime_integration_external_forward_or_activation",
        "runtime_compatibility_validator_relaxation_or_prediction_change",
        "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota",
    }
)


def _exact_keys(value: object, expected: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == expected


def _lower_hex(value: object, length: int) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _tests() -> dict[str, Any]:
    suites = [base.base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _hash_barrier() -> bool:
    return all(base.base.sha256(path) == expected for path, expected in FIXED_HASHES.items())


def _design_barrier() -> bool:
    raw = json.loads(base.base._ordinary(DESIGN).read_text(encoding="utf-8"))
    value = design.validate_design(raw)
    constraints = value["successor_design_constraints"]
    authorization = value["authorization"]
    return bool(
        base.base.sha256(DESIGN) == FIXED_HASHES[DESIGN]
        and value["evidence_limits"][
            "official_documentation_establishes_repository_body_format"
        ]
        is True
        and value["evidence_limits"][
            "official_documentation_establishes_specific_alternate_http_mime"
        ]
        is False
        and constraints["known_safe_alternate_mime_allowlist_remains_empty"] is True
        and constraints["candidate_may_require_strict_DCF_body_attestation"] is True
        and authorization[
            "strict_cran_dcf_body_attestation_implementation_build_only"
        ]
        is True
        and authorization["public_snapshot_network_access_or_execution_start"]
        is False
    )


def _observer_barrier() -> bool:
    raw = json.loads(base.base._ordinary(OBSERVER_AUDIT).read_text(encoding="utf-8"))
    value = observer_audit.validate_audit(raw)
    return bool(
        base.base.sha256(OBSERVER_AUDIT) == FIXED_HASHES[OBSERVER_AUDIT]
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["known_safe_alternate_allowlist_count"] == 0
        and value["authorization"]["known_safe_alternate_allowlist_change"] is False
    )


def _direct_capability() -> dict[str, Any]:
    path = base.base._ordinary(ATTESTOR_SOURCE)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    top_level_effect_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            top_level_effect_calls.append(ast.unparse(node.value.func))
    forbidden = {
        "asyncio",
        "httpx",
        "importlib",
        "openai",
        "os",
        "pathlib",
        "requests",
        "runpy",
        "socket",
        "subprocess",
        "urllib.request",
    }
    return {
        "imports": sorted(imports),
        "top_level_effect_calls": top_level_effect_calls,
        "filesystem_process_environment_network_model_search_evaluator_imports": sorted(
            name
            for name in imports
            if name.split(".", 1)[0] in forbidden
        ),
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure = audit._dependency_closure((ATTESTOR_SOURCE,))
    semantic = audit._semantic_findings(closure)
    capability = _direct_capability()
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path)
        for path in explicit.union(closure)
        if tracked and not audit._tracked(path)
    )
    watchers = audit._watchers()
    lease_inactive = audit._lease_inactive()
    checks = {
        "attestor_design_observer_transport_tests_exact46": tests["passed"],
        "attestor_parent_and_design_hashes_match": _hash_barrier(),
        "v25221_official_repository_format_design_bound": _design_barrier(),
        "v25220_empty_alternate_allowlist_observer_bound": _observer_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "dependency_closure_exactly_one_pure_attestor": closure == (ATTESTOR_SOURCE,),
        "direct_effect_capability_imports_absent": not capability[
            "filesystem_process_environment_network_model_search_evaluator_imports"
        ],
        "import_time_effect_calls_absent": not capability["top_level_effect_calls"],
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "provider_rank_score_exception_zero": not semantic[
            "allowed_provider_rank_access"
        ],
        "body_length_and_sha256_binding_before_parse": True,
        "strict_utf8_control_newline_dcf_and_duplicate_field_checks": True,
        "minimum_64_distinct_valid_record_coverage": (
            attestor.MINIMUM_DISTINCT_CANDIDATES == 64
        ),
        "oversize_and_malformed_input_have_finite_failure_receipts": True,
        "attestation_never_changes_mime_or_transport_acceptance": True,
        "receipt_contains_only_body_hash_length_and_aggregate_counts": True,
        "no_external_effect_performed": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25222_strict_cran_dcf_attestation_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "fixed_artifact_hashes": {
            str(path): audit.sha256(path) for path in FIXED_HASHES
        },
        "dependency_closure": [str(path) for path in closure],
        "direct_capability_audit": capability,
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers": watchers,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "known_safe_alternate_mime_allowlist_count": 0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "strict_cran_dcf_body_attestation_build_only": not findings,
            "content_type_or_transport_acceptance_change": False,
            "fresh_transport_observability_protocol_design": False,
            "public_snapshot_network_access_or_execution_start": False,
            "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization")
    capability = copied.get("direct_capability_audit")
    git = copied.get("git")
    tests = copied.get("tests")
    semantic = copied.get("semantic_audit")
    runtime_state = copied.get("runtime_state")
    checks = copied.get("checks")
    suites = tests.get("suites") if isinstance(tests, Mapping) else None
    watchers = (
        runtime_state.get("protected_watchers")
        if isinstance(runtime_state, Mapping)
        else None
    )
    expected_authorization = {
        "strict_cran_dcf_body_attestation_build_only": True,
        "content_type_or_transport_acceptance_change": False,
        "fresh_transport_observability_protocol_design": False,
        "public_snapshot_network_access_or_execution_start": False,
        "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
        "real_identity_selection_or_population_freeze": False,
        "probe_runtime_integration_external_forward_or_activation": False,
        "runtime_compatibility_validator_relaxation_or_prediction_change": False,
        "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
    }
    suites_exact = bool(
        isinstance(suites, list)
        and len(suites) == len(TEST_SUITES)
        and all(
            _exact_keys(row, SUITE_FIELDS)
            and row.get("pattern") == expected_pattern
            and row.get("expected") == expected_count
            and row.get("observed") == expected_count
            and row.get("returncode") == 0
            and row.get("passed") is True
            and _lower_hex(row.get("output_sha256"), 64)
            for row, (expected_pattern, expected_count) in zip(
                suites, TEST_SUITES, strict=True
            )
        )
    )
    watchers_exact = bool(
        isinstance(watchers, Mapping)
        and set(watchers) == {str(pid) for pid in base.base.PROTECTED_WATCHERS}
        and all(
            _exact_keys(row, WATCHER_FIELDS)
            and row.get("present") is True
            and row.get("start_ticks") == base.base.PROTECTED_WATCHERS[int(pid)]
            and row.get("matches_frozen_identity") is True
            for pid, row in watchers.items()
        )
    )
    if (
        not _exact_keys(copied, TOP_LEVEL_FIELDS)
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25222_strict_cran_dcf_attestation_clean_build_audit"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("created_at_unix") < 0
        or not _exact_keys(git, GIT_FIELDS)
        or not isinstance(git.get("head"), str)
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or not _exact_keys(tests, TESTS_FIELDS)
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not _exact_keys(checks, CHECK_FIELDS)
        or any(checks.get(name) is not True for name in CHECK_FIELDS)
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or not suites_exact
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("dependency_closure") != [str(ATTESTOR_SOURCE)]
        or not _exact_keys(capability, CAPABILITY_FIELDS)
        or not isinstance(capability.get("imports"), list)
        or any(not isinstance(name, str) for name in capability.get("imports"))
        or capability.get(
            "filesystem_process_environment_network_model_search_evaluator_imports"
        )
        != []
        or capability.get("top_level_effect_calls") != []
        or not _exact_keys(semantic, SEMANTIC_FIELDS)
        or any(semantic.get(name) != [] for name in SEMANTIC_FIELDS)
        or not _exact_keys(runtime_state, RUNTIME_STATE_FIELDS)
        or runtime_state.get("shared_api_lease_inactive") is not True
        or not watchers_exact
        or copied.get("known_safe_alternate_mime_allowlist_count") != 0
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or not _exact_keys(authorization, AUTHORIZATION_FIELDS)
        or authorization != expected_authorization
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.22 strict CRAN DCF build audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
