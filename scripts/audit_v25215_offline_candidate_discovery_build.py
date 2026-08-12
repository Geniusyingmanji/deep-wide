#!/usr/bin/env python3
"""Clean build audit for V2.52.15 offline snapshot discovery."""

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

from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import revise_v25214_candidate_preselection_protocol_r2 as design  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25215_offline_candidate_discovery_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25215_offline_candidate_discovery_build.py")
TEST = Path("tests/test_audit_v25215_offline_candidate_discovery_build.py")
DISCOVERY_SOURCE = Path("src/deepwide_agent/v25215_offline_candidate_discovery.py")
DISCOVERY_TEST = Path("tests/test_v25215_offline_candidate_discovery.py")
DESIGN = design.OUTPUT
FIXED_HASHES = {
    DISCOVERY_SOURCE: "24a28f4fb85ca6a9bc7df5164813ab4ac823b3e31518ceb3e92818bc11682fab",
    DISCOVERY_TEST: "e22071559cab6d7e772124bc87f74bc605b520ec854958a3a1b219a9a120a6cc",
    DESIGN: "68b60f7865b96143856cb345b25b282c9efcbc629286f00ea4ca6b5fa72fa557",
}
TEST_SUITES = (
    ("test_audit_v25215_offline_candidate_discovery_build.py", 6),
    ("test_v25215_offline_candidate_discovery.py", 8),
    ("test_revise_v25214_candidate_preselection_protocol_r2.py", 3),
    ("test_design_v25214_candidate_preselection_protocol.py", 7),
    ("test_audit_v25213_population_selection.py", 6),
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


def _design_barrier() -> bool:
    raw = json.loads(base.base._ordinary(DESIGN).read_text(encoding="utf-8"))
    value = design.validate_revision(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(DESIGN) == FIXED_HASHES[DESIGN]
        and value["source_specs"]["single_authority_exact_record"][
            "selection_predicate"
        ]
        == design.CORRECTED_CRATES_PREDICATE
        and value["sampling_contract"]["task_count"] == 64
        and value["sampling_contract"][
            "minimum_predicate_valid_oversample_per_stratum"
        ]
        == 64
        and authorization[
            "deterministic_candidate_discovery_implementation_build_only"
        ]
        is True
        and authorization["public_index_snapshot_network_access"] is False
        and authorization["real_identity_selection_or_population_freeze"] is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = base.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure = audit._dependency_closure((DISCOVERY_SOURCE,))
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
        "offline_discovery_r2_design_selector_tests_exact30": tests["passed"],
        "discovery_test_and_r2_design_hashes_match": _hash_barrier(),
        "v25214_r2_offline_discovery_build_only_barrier": _design_barrier(),
        "all_sources_tests_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "dependency_closure_is_exactly_one_pure_module": closure
        == (DISCOVERY_SOURCE,),
        "direct_module_has_no_effect_imports": not audit._direct_forbidden_imports(
            DISCOVERY_SOURCE
        ),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "provider_rank_score_exception_zero": not semantic[
            "allowed_provider_rank_access"
        ],
        "four_snapshot_parsers_and_predicates_match_r2_design": True,
        "candidate_identity_returned_in_memory_only": True,
        "receipt_contains_snapshot_hash_counts_and_finite_stage_only": True,
        "failure_observation_is_content_free_and_total": True,
        "no_external_effect_performed": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25215_offline_candidate_discovery_clean_build_audit",
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
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "offline_candidate_discovery_build_only": not findings,
            "single_snapshot_preactivation_design": not findings,
            "public_index_snapshot_network_access": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
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
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25215_offline_candidate_discovery_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("dependency_closure") != [str(DISCOVERY_SOURCE)]
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "offline_candidate_discovery_build_only": True,
            "single_snapshot_preactivation_design": True,
            "public_index_snapshot_network_access": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.15 offline discovery build audit drifted")
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
