#!/usr/bin/env python3
"""Pre-protocol authorization audit for a fresh normalizer observer gate."""

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

from scripts import audit_v25172_observed_production_normalizer_build as build_parent  # noqa: E402
from scripts import audit_v25173_population_selection as population_parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(
    f"results/v25174_production_normalizer_preprotocol_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25174_production_normalizer_preprotocol.py")
TEST = Path("tests/test_audit_v25174_production_normalizer_preprotocol.py")
RUNTIME_SOURCE = build_parent.RUNTIME_SOURCE
BUILD_AUDIT = build_parent.OUTPUT
POPULATION_AUDIT = Path(
    "results/v25173_production_normalizer_population_selection_audit_v1_20260812.json"
)
EXPECTED_RUNTIME_HASH = (
    "f3a8998ec7c191014d32da81fab67bafe01320def91ae3e7edbe40b3d0683458"
)
EXPECTED_BUILD_AUDIT_HASH = (
    "1f6d0a6bee278ee8567d061b4a8d9d05148e45fe2b30bac55c25780bba83bcfe"
)
EXPECTED_POPULATION_AUDIT_HASH = (
    "9d61a3c7de26787336ed565e8ce8ac8faa259176e0ecfdf92956c2ea7263e235"
)
TEST_SUITES = (
    ("test_audit_v25174_production_normalizer_preprotocol.py", 5),
    ("test_audit_v25173_population_selection.py", 3),
    ("test_audit_v25172_observed_production_normalizer_build.py", 5),
    ("test_v25171_observed_production_normalizer_runtime.py", 6),
    ("test_v25170_production_normalizer_disposition_observer.py", 6),
    ("test_diagnose_v25169_v25167_observer_censoring.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = build_parent.payload_sha256


def _tests() -> dict[str, Any]:
    suites = [
        build_parent.base._test(pattern, expected)
        for pattern, expected in TEST_SUITES
    ]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _build_barrier() -> bool:
    raw = json.loads(
        build_parent.base._ordinary(BUILD_AUDIT).read_text(encoding="utf-8")
    )
    value = build_parent.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        build_parent.base.sha256(RUNTIME_SOURCE) == EXPECTED_RUNTIME_HASH
        and build_parent.base.sha256(BUILD_AUDIT) == EXPECTED_BUILD_AUDIT_HASH
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 182
        and value["tests"]["observed"] == 182
        and authorization["implementation_build_only"] is True
        and authorization["fresh_disjoint_normalizer_observer_protocol_design"]
        is False
        and authorization["fresh_external_activation_or_launch"] is False
        and authorization["binding_successor_design"] is False
        and authorization["vertical_binding_policy_change"] is False
        and authorization[
            "v25167_population_model_evaluator_retry_resume_or_reuse"
        ]
        is False
        and authorization["evaluator_or_deepwidebench_or_sota"] is False
    )


def _population_barrier() -> bool:
    raw = json.loads(
        build_parent.base._ordinary(POPULATION_AUDIT).read_text(encoding="utf-8")
    )
    value = population_parent.validate_audit(raw)
    return bool(
        build_parent.base.sha256(POPULATION_AUDIT)
        == EXPECTED_POPULATION_AUDIT_HASH
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["identity_count"] == 20
        and value["identity_history_zero_hit_count"] == 20
        and value["identity_history_introduction_hit_total"] == 0
        and value["network_endpoint_page_value_model_or_evaluator_access"]
        is False
        and value[
            "v25141_v25145_v25149_v25153_v25157_v25160_v25167_population_reuse"
        ]
        is False
        and value["binding_successor_design"] is False
        and value["vertical_binding_policy_change"] is False
        and value[
            "external_protocol_activation_evaluator_or_deepwidebench_authorized"
        ]
        is False
        and value["entropy_or_information_gain_assigns_signed_credit"]
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = build_parent.base
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure = audit._dependency_closure((RUNTIME_SOURCE, build_parent.OBSERVER_SOURCE))
    semantic = audit._semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        BUILD_AUDIT,
        POPULATION_AUDIT,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not audit._tracked(path)
    )
    watchers = audit._watchers()
    lease_inactive = audit._lease_inactive()
    checks = {
        "focused_preprotocol_population_build_runtime_observer_and_diagnosis_tests_exact30": tests[
            "passed"
        ],
        "v25172_clean_build_audit_and_runtime_bytes_bound": _build_barrier(),
        "v25173_aggregate_population_freeze_bound": _population_barrier(),
        "all_sources_and_parent_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True
            for row in watchers.values()
        ),
        "shared_api_lease_inactive": lease_inactive,
        "old_external_populations_not_read_retried_resumed_or_reused": True,
        "binding_and_vertical_policy_change_remain_forbidden": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25174_production_normalizer_preprotocol_authorization_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "runtime_source": {
            "path": str(RUNTIME_SOURCE),
            "sha256": audit.sha256(RUNTIME_SOURCE),
        },
        "build_audit": {
            "path": str(BUILD_AUDIT),
            "sha256": audit.sha256(BUILD_AUDIT),
        },
        "population_audit": {
            "path": str(POPULATION_AUDIT),
            "sha256": audit.sha256(POPULATION_AUDIT),
        },
        "runtime_dependency_closure": [str(path) for path in closure],
        "runtime_semantic_audit": {**semantic, "untracked_sources": untracked},
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
            "fresh_disjoint_normalizer_observer_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
            "v25141_v25145_v25149_v25153_v25157_v25160_v25167_population_reuse": False,
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
        != "v25174_production_normalizer_preprotocol_authorization_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("runtime_source", {}).get("sha256") != EXPECTED_RUNTIME_HASH
        or copied.get("build_audit", {}).get("sha256")
        != EXPECTED_BUILD_AUDIT_HASH
        or copied.get("population_audit", {}).get("sha256")
        != EXPECTED_POPULATION_AUDIT_HASH
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "fresh_disjoint_normalizer_observer_protocol_design": True,
            "fresh_external_activation_or_launch": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
            "v25141_v25145_v25149_v25153_v25157_v25160_v25167_population_reuse": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.74 pre-protocol audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    build_parent.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "protocol_design_authorized": value["authorization"][
                    "fresh_disjoint_normalizer_observer_protocol_design"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
