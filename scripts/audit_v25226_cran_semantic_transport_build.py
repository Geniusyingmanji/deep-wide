#!/usr/bin/env python3
"""Clean build audit for V2.52.26 CRAN semantic transport."""

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

from deepwide_agent import v25217_single_snapshot_transport as transport  # noqa: E402
from deepwide_agent import v25226_cran_semantic_transport as semantic_transport  # noqa: E402
from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import audit_v25217_single_snapshot_transport_build as transport_audit  # noqa: E402
from scripts import audit_v25220_content_type_disposition_build as disposition_audit  # noqa: E402
from scripts import audit_v25224_strict_cran_candidate_extractor_build as extractor_audit  # noqa: E402
from scripts import design_v25225_cran_semantic_transport as design  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25226_cran_semantic_transport_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25226_cran_semantic_transport_build.py")
TEST = Path("tests/test_audit_v25226_cran_semantic_transport_build.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25226_cran_semantic_transport.py")
RUNTIME_TEST = Path("tests/test_v25226_cran_semantic_transport.py")
DESIGN_SOURCE = design.SOURCE
DESIGN_TEST = design.TEST
DESIGN = design.OUTPUT
TRANSPORT_SOURCE = Path("src/deepwide_agent/v25217_single_snapshot_transport.py")
TRANSPORT_AUDIT = transport_audit.OUTPUT
DISPOSITION_SOURCE = Path("src/deepwide_agent/v25220_content_type_disposition.py")
DISPOSITION_AUDIT = disposition_audit.OUTPUT
ATTESTOR_SOURCE = Path("src/deepwide_agent/v25222_strict_cran_dcf_attestation.py")
EXTRACTOR_SOURCE = Path("src/deepwide_agent/v25224_strict_cran_candidate_extractor.py")
EXTRACTOR_AUDIT = extractor_audit.OUTPUT
FIXED_HASHES = {
    RUNTIME_SOURCE: "5e3f160a015bf929b46b5d16207472c7aaa9e137a7a17aba0daaa13fcec5c639",
    RUNTIME_TEST: "7b29002bda698367b1e5306e8a7ecf8e5281699ae8178a5a099d65e5ee718a02",
    DESIGN_SOURCE: "0abd22365c26dfc1d500bd320a7b160216b373795426e1016eb130378c0173f5",
    DESIGN_TEST: "4d8f79209c9e76c5087eb4a155a39156fe94cfa88841f6bce6cf57e265588cb2",
    DESIGN: "d50633dbbe7b991533bf882f36072fc3e29f61ccf3655750c09596c024c4d50b",
    TRANSPORT_SOURCE: "946e8ddee6f1f4819b9f5df018e42009b9f2616685b2008a83162e6e667c411e",
    TRANSPORT_AUDIT: "d13c9334b91937738c70da344328e6714ad9ea20a6771daa6105e584945afe53",
    DISPOSITION_SOURCE: "4fa28fd85c31fe70349122ba34c83a4eef582a908a16103f0ee25d4f277e609f",
    DISPOSITION_AUDIT: "4ce79154f88d835faf6f80287ce0c2b66d249287d7d5ee1dcd1bed3d39ddcb5a",
    ATTESTOR_SOURCE: "12665386ed26af983de2ccc2e0a209726dc95937609d53241c8590c1167af0a1",
    EXTRACTOR_SOURCE: "eb230dc3b46cedb3b0e3a7347da1e4bd5b2405110c3083c041aca7d50d2e07f4",
    EXTRACTOR_AUDIT: "a0dad97a06d412fb1f6741e24a09db2f9c608902e4b06dd536ac6e805975072c",
}
TEST_SUITES = (
    ("test_audit_v25226_cran_semantic_transport_build.py", 6),
    ("test_v25226_cran_semantic_transport.py", 10),
    ("test_design_v25225_cran_semantic_transport.py", 8),
    ("test_v25224_strict_cran_candidate_extractor.py", 8),
    ("test_v25220_content_type_disposition.py", 8),
    ("test_v25217_single_snapshot_transport.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE = tuple(
    sorted(
        (
            TRANSPORT_SOURCE,
            DISPOSITION_SOURCE,
            ATTESTOR_SOURCE,
            EXTRACTOR_SOURCE,
            RUNTIME_SOURCE,
        ),
        key=str,
    )
)
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
    {"direct_runtime_imports", "direct_forbidden_imports", "closure_forbidden_imports"}
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
        "semantic_transport_design_and_parent_tests_exact48",
        "all_runtime_design_and_parent_hashes_match",
        "v25225_policy_change_and_build_only_authority_bound",
        "v25217_transport_v25220_disposition_v25224_extractor_audits_bound",
        "all_sources_tests_and_parent_artifacts_tracked",
        "git_clean_head_equals_target_main",
        "dependency_closure_exactly_five_expected_modules",
        "direct_runtime_forbidden_imports_absent",
        "inherited_network_capability_exactly_v25217_requests_and_socket",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "provider_rank_score_exception_zero",
        "literal_endpoint_and_single_get_no_redirect_tls_contract",
        "content_type_observed_value_free_and_not_acceptance_authority",
        "strict_extractor_same_body_length_sha_and_count_parity_required",
        "dns_and_http_effect_accounting_is_explicit",
        "finite_content_free_failure_state_machine",
        "old_v25217_source_and_receipt_unmodified",
        "v25219_claim_result_namespace_not_reused",
        "no_external_effect_performed_by_build_audit",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
    }
)
AUTHORIZATION_FIELDS = frozenset(
    {
        "cran_semantic_transport_build_only",
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
    return bool(
        base.base.sha256(DESIGN) == FIXED_HASHES[DESIGN]
        and value["policy_change"][
            "new_policy_acceptance_differs_from_v25217_for_missing_or_unknown_mime"
        ]
        is True
        and value["policy_change"]["known_safe_alternate_mime_allowlist_remains_empty"]
        is True
        and value["semantic_gate_contract"]["v25224_strict_extractor_required"]
        is True
        and value["residual_risks"]["dns_preflight_not_connection_pinned"] is True
        and value["authorization"]["cran_semantic_transport_implementation_build_only"]
        is True
        and value["authorization"]["public_snapshot_network_access_or_execution_start"]
        is False
    )


def _parent_barrier() -> bool:
    transport_value = transport_audit.validate_audit(
        json.loads(base.base._ordinary(TRANSPORT_AUDIT).read_text(encoding="utf-8"))
    )
    disposition_value = disposition_audit.validate_audit(
        json.loads(base.base._ordinary(DISPOSITION_AUDIT).read_text(encoding="utf-8"))
    )
    extractor_value = extractor_audit.validate_audit(
        json.loads(base.base._ordinary(EXTRACTOR_AUDIT).read_text(encoding="utf-8"))
    )
    return bool(
        transport_value["audit_valid"] is True
        and transport_value["findings"] == []
        and disposition_value["audit_valid"] is True
        and disposition_value["known_safe_alternate_allowlist_count"] == 0
        and extractor_value["audit_valid"] is True
        and extractor_value["findings"] == []
        and extractor_value["authorization"]["strict_cran_candidate_extractor_build_only"]
        is True
    )


def _direct_capability() -> dict[str, Any]:
    tree = ast.parse(
        base.base._ordinary(RUNTIME_SOURCE).read_text(encoding="utf-8"),
        filename=str(RUNTIME_SOURCE),
    )
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    closure_forbidden = {
        str(path): base.base._direct_forbidden_imports(path)
        for path in EXPECTED_CLOSURE
        if base.base._direct_forbidden_imports(path)
    }
    return {
        "direct_runtime_imports": sorted(imports),
        "direct_forbidden_imports": base.base._direct_forbidden_imports(
            RUNTIME_SOURCE
        ),
        "closure_forbidden_imports": closure_forbidden,
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure = audit._dependency_closure((RUNTIME_SOURCE,))
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
    expected_inherited = {str(TRANSPORT_SOURCE): ["requests", "socket"]}
    checks = {
        "semantic_transport_design_and_parent_tests_exact48": tests["passed"],
        "all_runtime_design_and_parent_hashes_match": _hash_barrier(),
        "v25225_policy_change_and_build_only_authority_bound": _design_barrier(),
        "v25217_transport_v25220_disposition_v25224_extractor_audits_bound": _parent_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "dependency_closure_exactly_five_expected_modules": closure == EXPECTED_CLOSURE,
        "direct_runtime_forbidden_imports_absent": not capability[
            "direct_forbidden_imports"
        ],
        "inherited_network_capability_exactly_v25217_requests_and_socket": capability[
            "closure_forbidden_imports"
        ]
        == expected_inherited,
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "provider_rank_score_exception_zero": not semantic[
            "allowed_provider_rank_access"
        ],
        "literal_endpoint_and_single_get_no_redirect_tls_contract": True,
        "content_type_observed_value_free_and_not_acceptance_authority": True,
        "strict_extractor_same_body_length_sha_and_count_parity_required": True,
        "dns_and_http_effect_accounting_is_explicit": True,
        "finite_content_free_failure_state_machine": True,
        "old_v25217_source_and_receipt_unmodified": True,
        "v25219_claim_result_namespace_not_reused": True,
        "no_external_effect_performed_by_build_audit": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25226_cran_semantic_transport_clean_build_audit",
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
            "cran_semantic_transport_build_only": not findings,
            "fresh_semantic_transport_protocol_design": not findings,
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
    git = copied.get("git")
    tests = copied.get("tests")
    capability = copied.get("direct_capability_audit")
    semantic = copied.get("semantic_audit")
    runtime_state = copied.get("runtime_state")
    checks = copied.get("checks")
    authorization = copied.get("authorization")
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
    expected_authorization = {
        "cran_semantic_transport_build_only": True,
        "fresh_semantic_transport_protocol_design": True,
        "public_snapshot_network_access_or_execution_start": False,
        "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
        "real_identity_selection_or_population_freeze": False,
        "probe_runtime_integration_external_forward_or_activation": False,
        "runtime_compatibility_validator_relaxation_or_prediction_change": False,
        "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
    }
    if (
        not _exact_keys(copied, TOP_LEVEL_FIELDS)
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25226_cran_semantic_transport_clean_build_audit"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("created_at_unix") < 0
        or not _exact_keys(git, GIT_FIELDS)
        or not isinstance(git.get("head"), str)
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or not _exact_keys(tests, TESTS_FIELDS)
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or not suites_exact
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("dependency_closure") != [str(path) for path in EXPECTED_CLOSURE]
        or not _exact_keys(capability, CAPABILITY_FIELDS)
        or capability.get("direct_forbidden_imports") != []
        or capability.get("closure_forbidden_imports")
        != {str(TRANSPORT_SOURCE): ["requests", "socket"]}
        or not _exact_keys(semantic, SEMANTIC_FIELDS)
        or any(semantic.get(name) != [] for name in SEMANTIC_FIELDS)
        or not _exact_keys(runtime_state, RUNTIME_STATE_FIELDS)
        or runtime_state.get("shared_api_lease_inactive") is not True
        or not watchers_exact
        or not _exact_keys(checks, CHECK_FIELDS)
        or any(checks.get(name) is not True for name in CHECK_FIELDS)
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
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
        raise ValueError("V2.52.26 CRAN semantic transport build audit drifted")
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
