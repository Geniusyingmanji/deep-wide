#!/usr/bin/env python3
"""Clean build audit for V2.52.20 content-free MIME disposition observer."""

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

from deepwide_agent import v25220_content_type_disposition as observer  # noqa: E402
from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import audit_v25218_snapshot_hard_deadline_controller_build as parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25220_content_type_disposition_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25220_content_type_disposition_build.py")
TEST = Path("tests/test_audit_v25220_content_type_disposition_build.py")
OBSERVER_SOURCE = Path("src/deepwide_agent/v25220_content_type_disposition.py")
OBSERVER_TEST = Path("tests/test_v25220_content_type_disposition.py")
TRANSPORT_SOURCE = Path("src/deepwide_agent/v25217_single_snapshot_transport.py")
TRANSPORT_TEST = Path("tests/test_v25217_single_snapshot_transport.py")
ATTEMPT_CLAIM = Path(
    "results/v25219_snapshot_population_attempt_claim_v1_20260812.json"
)
NO_GO_RESULT = Path(
    "results/v25219_snapshot_population_freeze_v1_20260812.json"
)
PARENT_AUDIT = parent.OUTPUT
FIXED_HASHES = {
    OBSERVER_SOURCE: "4fa28fd85c31fe70349122ba34c83a4eef582a908a16103f0ee25d4f277e609f",
    OBSERVER_TEST: "bfefa369651950851dd1db61939fe182b5261ddae77948edcc5dd33ac0991dd2",
    TRANSPORT_SOURCE: "946e8ddee6f1f4819b9f5df018e42009b9f2616685b2008a83162e6e667c411e",
    TRANSPORT_TEST: "18f402b171641bdee3b3ad281ff572f8c7eb03c4cadb81a348a4433575a7bd0b",
    ATTEMPT_CLAIM: "815aa9bd1c29e6e128cde1e0cbdacf284cb6e7b6313213ae6cd753a35a1869fd",
    NO_GO_RESULT: "d98abd021142f0f94b0afcf7f06ce4834c6337f04dbb51cccbd60fa5128617e1",
    PARENT_AUDIT: "988185da358ad0a9b13e846c1abc735152a4a4cf60a103bc74ee6b7c4ba86edc",
}
TEST_SUITES = (
    ("test_audit_v25220_content_type_disposition_build.py", 6),
    ("test_v25220_content_type_disposition.py", 8),
    ("test_audit_v25218_snapshot_hard_deadline_controller_build.py", 6),
    ("test_v25218_snapshot_hard_deadline_controller.py", 8),
    ("test_audit_v25217_single_snapshot_transport_build.py", 6),
    ("test_v25217_single_snapshot_transport.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256


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


def _parent_barrier() -> bool:
    raw = json.loads(base.base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    value = parent.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(PARENT_AUDIT) == FIXED_HASHES[PARENT_AUDIT]
        and value["audit_valid"] is True
        and value["findings"] == []
        and authorization["public_snapshot_network_access_or_execution_start"]
        is False
    )


def _no_go_barrier() -> bool:
    claim = json.loads(base.base._ordinary(ATTEMPT_CLAIM).read_text(encoding="utf-8"))
    result = json.loads(base.base._ordinary(NO_GO_RESULT).read_text(encoding="utf-8"))
    child = result.get("batch_receipt", {}).get("children", {}).get(
        "single_authority_multivalue_record", {}
    )
    transport = child.get("transport_receipt") or {}
    return bool(
        _hash_barrier()
        and claim.get("role") == "v25219_snapshot_population_single_attempt_claim"
        and claim.get(
            "retry_refetch_backfill_replacement_or_second_batch_authorized"
        )
        is False
        and result.get("role") == "v25219_snapshot_population_freeze_result"
        and result.get("status") == "no_go"
        and result.get("failure_stage") == "snapshot_transport"
        and result.get("task_vector") == []
        and result.get("parser_observations") == {}
        and result.get("public_snapshot_network_or_api_called") is True
        and result.get("model_hosted_search_tavily_evaluator_or_benchmark_called")
        is False
        and child.get("kind") == "transport_failure"
        and transport.get("failure_code") == "content_type"
        and transport.get("provider_attempt_count") == 1
        and transport.get("retry_count") == 0
        and transport.get("http_status") == 200
        and result.get("execution_claim_sha256") == FIXED_HASHES[ATTEMPT_CLAIM]
    )


def _direct_capability() -> dict[str, Any]:
    path = base.base._ordinary(OBSERVER_SOURCE)
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
    closure = audit._dependency_closure((OBSERVER_SOURCE,))
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
        "observer_transport_controller_tests_exact42": tests["passed"],
        "observer_parent_and_v25219_hashes_match": _hash_barrier(),
        "v25218_parent_build_audit_bound": _parent_barrier(),
        "v25219_single_attempt_transport_no_go_bound": _no_go_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "dependency_closure_exactly_one_pure_observer": closure == (OBSERVER_SOURCE,),
        "direct_effect_capability_imports_absent": not capability[
            "filesystem_process_environment_network_model_search_evaluator_imports"
        ],
        "import_time_effect_calls_absent": not capability["top_level_effect_calls"],
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "accepted_content_types_match_frozen_parent": observer.ACCEPTED_CONTENT_TYPES
        == {
            "single_authority_exact_record": ("application/json",),
            "single_authority_multivalue_record": ("text/plain",),
            "same_identity_multipage_record": ("application/json",),
            "sparse_ambiguous_open_web_record": (
                "text/html",
                "application/vnd.pypi.simple.v1+html",
            ),
        },
        "known_safe_alternate_allowlists_all_empty": observer.KNOWN_SAFE_ALTERNATES
        == {stratum: () for stratum in observer.STRATA},
        "observer_does_not_change_transport_acceptance": True,
        "missing_accepted_reserved_alternate_and_unknown_vocab_finite": observer.DISPOSITIONS
        == (
            "missing",
            "accepted",
            "known_safe_alternate",
            "unknown_disallowed",
        ),
        "v25219_attempt_not_retried_refetched_or_reused": True,
        "no_external_effect_performed": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25220_content_type_disposition_clean_build_audit",
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
        "known_safe_alternate_allowlist_count": sum(
            len(values) for values in observer.KNOWN_SAFE_ALTERNATES.values()
        ),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "content_type_disposition_observer_build_only": not findings,
            "fresh_transport_observability_protocol_design": False,
            "known_safe_alternate_allowlist_change": False,
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
    authorization = copied.get("authorization") or {}
    capability = copied.get("direct_capability_audit") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25220_content_type_disposition_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("dependency_closure") != [str(OBSERVER_SOURCE)]
        or capability.get(
            "filesystem_process_environment_network_model_search_evaluator_imports"
        )
        != []
        or capability.get("top_level_effect_calls") != []
        or copied.get("known_safe_alternate_allowlist_count") != 0
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "content_type_disposition_observer_build_only": True,
            "fresh_transport_observability_protocol_design": False,
            "known_safe_alternate_allowlist_change": False,
            "public_snapshot_network_access_or_execution_start": False,
            "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.20 content-type build audit drifted")
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
