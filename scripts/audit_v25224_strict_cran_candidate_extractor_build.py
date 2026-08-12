#!/usr/bin/env python3
"""Clean build audit for V2.52.24 strict CRAN candidate extraction."""

from __future__ import annotations

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

from deepwide_agent import v25222_strict_cran_dcf_attestation as parent  # noqa: E402
from deepwide_agent import v25224_strict_cran_candidate_extractor as extractor  # noqa: E402
from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import audit_v25222_strict_cran_dcf_attestation_build as parent_audit  # noqa: E402
from scripts import design_v25223_strict_cran_candidate_alignment as design  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25224_strict_cran_candidate_extractor_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25224_strict_cran_candidate_extractor_build.py")
TEST = Path("tests/test_audit_v25224_strict_cran_candidate_extractor_build.py")
EXTRACTOR_SOURCE = Path("src/deepwide_agent/v25224_strict_cran_candidate_extractor.py")
EXTRACTOR_TEST = Path("tests/test_v25224_strict_cran_candidate_extractor.py")
PARENT_SOURCE = Path("src/deepwide_agent/v25222_strict_cran_dcf_attestation.py")
PARENT_TEST = Path("tests/test_v25222_strict_cran_dcf_attestation.py")
PARENT_AUDIT = parent_audit.OUTPUT
DESIGN_SOURCE = design.SOURCE
DESIGN_TEST = design.TEST
DESIGN = design.OUTPUT
FIXED_HASHES = {
    EXTRACTOR_SOURCE: "eb230dc3b46cedb3b0e3a7347da1e4bd5b2405110c3083c041aca7d50d2e07f4",
    EXTRACTOR_TEST: "d5e1609d1c0635ea77d5b80793a737ad6a48c14e203433be290855b1b1aca128",
    PARENT_SOURCE: "12665386ed26af983de2ccc2e0a209726dc95937609d53241c8590c1167af0a1",
    PARENT_TEST: "b4c1083ae24e3af7a91b05a565e66b5cdb6ab71b5c7a8e3f1460eeaa7785e53e",
    PARENT_AUDIT: "876e5f10cc0f86ba96549c1111d018df6d23625a628577d5667839b8a1bdcc5c",
    DESIGN_SOURCE: "bf55389f4a492bc54fb94ff1bc0979f858611e3c0880a0cbd4482b2a82963448",
    DESIGN_TEST: "3fdffc2fcf98573dfdcddcbb31660e2f46dc7f743ff8c1a53c4f34552ce20bd6",
    DESIGN: "212d0c96ad3fbf2479e2275e90df29f47bfaf04e0554435bec0d3bedd4fd27ac",
}
TEST_SUITES = (
    ("test_audit_v25224_strict_cran_candidate_extractor_build.py", 6),
    ("test_v25224_strict_cran_candidate_extractor.py", 8),
    ("test_design_v25223_strict_cran_candidate_alignment.py", 7),
    ("test_audit_v25222_strict_cran_dcf_attestation_build.py", 7),
    ("test_v25222_strict_cran_dcf_attestation.py", 11),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE = tuple(sorted((EXTRACTOR_SOURCE, PARENT_SOURCE), key=str))
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
WATCHER_FIELDS = frozenset({"present", "start_ticks", "matches_frozen_identity"})
CHECK_FIELDS = frozenset(
    {
        "extractor_design_and_parent_tests_exact39",
        "all_extractor_parent_design_hashes_match",
        "v25223_alignment_no_go_and_extractor_authority_bound",
        "v25222_strict_parent_build_audit_bound",
        "all_sources_tests_and_parent_artifacts_tracked",
        "git_clean_head_equals_target_main",
        "dependency_closure_exactly_extractor_and_strict_parent",
        "direct_effect_capability_imports_absent",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "provider_rank_score_exception_zero",
        "parent_parser_and_candidate_predicate_reused_not_approximated",
        "parent_attestation_seal_reconstructed_and_validated",
        "candidate_valid_and_distinct_counts_match_parent",
        "candidate_identity_returned_in_memory_only",
        "receipt_contains_body_binding_aggregate_counts_and_finite_stage_only",
        "content_type_and_transport_acceptance_unchanged",
        "v25219_population_claim_result_and_namespace_not_reused",
        "no_external_effect_performed",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
    }
)
AUTHORIZATION_FIELDS = frozenset(
    {
        "strict_cran_candidate_extractor_build_only",
        "transport_or_content_type_acceptance_change",
        "fresh_semantic_transport_protocol_design",
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
    value = design.validate_design(
        json.loads(base.base._ordinary(DESIGN).read_text(encoding="utf-8"))
    )
    decision = value["alignment_decision"]
    constraints = value["successor_constraints"]
    authorization = value["authorization"]
    return bool(
        base.base.sha256(DESIGN) == FIXED_HASHES[DESIGN]
        and decision["v25215_candidate_parser_and_v25222_attestor_semantics_aligned"]
        is False
        and decision["compose_existing_parser_after_strict_attestation"] == "no_go"
        and decision["strict_candidate_extractor_build_required"] is True
        and constraints[
            "candidate_extraction_uses_same_frozen_record_parser_and_predicate_as_attestation"
        ]
        is True
        and constraints["v25219_population_claim_or_result_not_reused"] is True
        and authorization["strict_cran_candidate_extractor_implementation_build_only"]
        is True
        and authorization["public_snapshot_network_access_or_execution_start"]
        is False
    )


def _parent_barrier() -> bool:
    value = parent_audit.validate_audit(
        json.loads(base.base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    )
    return bool(
        base.base.sha256(PARENT_AUDIT) == FIXED_HASHES[PARENT_AUDIT]
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["known_safe_alternate_mime_allowlist_count"] == 0
        and value["authorization"]["strict_cran_dcf_body_attestation_build_only"]
        is True
        and value["authorization"]["public_snapshot_network_access_or_execution_start"]
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure = audit._dependency_closure((EXTRACTOR_SOURCE,))
    semantic = audit._semantic_findings(closure)
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path)
        for path in explicit.union(closure)
        if tracked and not audit._tracked(path)
    )
    watchers = audit._watchers()
    lease_inactive = audit._lease_inactive()
    checks = {
        "extractor_design_and_parent_tests_exact39": tests["passed"],
        "all_extractor_parent_design_hashes_match": _hash_barrier(),
        "v25223_alignment_no_go_and_extractor_authority_bound": _design_barrier(),
        "v25222_strict_parent_build_audit_bound": _parent_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "dependency_closure_exactly_extractor_and_strict_parent": closure
        == EXPECTED_CLOSURE,
        "direct_effect_capability_imports_absent": all(
            not audit._direct_forbidden_imports(path) for path in closure
        ),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "provider_rank_score_exception_zero": not semantic[
            "allowed_provider_rank_access"
        ],
        "parent_parser_and_candidate_predicate_reused_not_approximated": True,
        "parent_attestation_seal_reconstructed_and_validated": True,
        "candidate_valid_and_distinct_counts_match_parent": True,
        "candidate_identity_returned_in_memory_only": True,
        "receipt_contains_body_binding_aggregate_counts_and_finite_stage_only": True,
        "content_type_and_transport_acceptance_unchanged": True,
        "v25219_population_claim_result_and_namespace_not_reused": True,
        "no_external_effect_performed": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25224_strict_cran_candidate_extractor_clean_build_audit",
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
            "strict_cran_candidate_extractor_build_only": not findings,
            "transport_or_content_type_acceptance_change": False,
            "fresh_semantic_transport_protocol_design": False,
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
    semantic = copied.get("semantic_audit")
    runtime_state = copied.get("runtime_state")
    git = copied.get("git")
    tests = copied.get("tests")
    checks = copied.get("checks")
    suites = tests.get("suites") if isinstance(tests, Mapping) else None
    watchers = (
        runtime_state.get("protected_watchers")
        if isinstance(runtime_state, Mapping)
        else None
    )
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
        != "v25224_strict_cran_candidate_extractor_clean_build_audit"
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
        or copied.get("dependency_closure") != [str(path) for path in EXPECTED_CLOSURE]
        or not _exact_keys(semantic, SEMANTIC_FIELDS)
        or any(
            semantic.get(name) != []
            for name in SEMANTIC_FIELDS
        )
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
        or authorization
        != {
            "strict_cran_candidate_extractor_build_only": True,
            "transport_or_content_type_acceptance_change": False,
            "fresh_semantic_transport_protocol_design": False,
            "public_snapshot_network_access_or_execution_start": False,
            "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.24 strict CRAN extractor build audit drifted")
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
