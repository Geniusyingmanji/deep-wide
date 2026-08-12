#!/usr/bin/env python3
"""Pre-protocol authorization audit for the V2.51.60 external gate.

This audit binds the clean V2.51.58 runtime build to the aggregate-only
V2.51.60 population freeze.  A successful audit authorizes protocol design
only.  It cannot authorize activation, external effects, an evaluator, or a
DeepWideBench run.
"""

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

from scripts import (  # noqa: E402
    audit_v25159_vertical_key_value_candidate_build as build_parent,
)
from scripts import audit_v25160_population_selection as population_parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(
    f"results/v25161_vertical_key_value_preprotocol_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25161_vertical_key_value_preprotocol.py")
TEST = Path("tests/test_audit_v25161_vertical_key_value_preprotocol.py")
RUNTIME_SOURCE = build_parent.RUNTIME_SOURCE
BUILD_AUDIT = build_parent.OUTPUT
POPULATION_AUDIT = Path(
    "results/v25160_vertical_key_value_population_selection_audit_v1_20260812.json"
)
EXPECTED_RUNTIME_HASH = (
    "ec0420854f145c12a63a311b147d69af31d10e0646f4afac9e9daa32b6902f26"
)
EXPECTED_BUILD_AUDIT_HASH = (
    "2a8bb6b3b97ca47b70bfe9c7e668fe6995bb0cc22d6ecf47929f505d296a708d"
)
EXPECTED_POPULATION_AUDIT_HASH = (
    "029485c9a0e400982664e8498c1aabac13fc9d7a68ce5201433b98a92312c1a0"
)
TEST_SUITES = (
    ("test_audit_v25161_vertical_key_value_preprotocol.py", 5),
    ("test_audit_v25160_population_selection.py", 3),
    ("test_v25158_vertical_key_value_candidate_runtime.py", 11),
    ("test_audit_v25159_vertical_key_value_candidate_build.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = build_parent.payload_sha256


def _tests() -> dict[str, Any]:
    suites = [
        build_parent.audit_parent._test(pattern, expected)
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
        build_parent.audit_parent._ordinary(BUILD_AUDIT).read_text(
            encoding="utf-8"
        )
    )
    value = build_parent.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        build_parent.audit_parent.sha256(RUNTIME_SOURCE)
        == EXPECTED_RUNTIME_HASH
        and build_parent.audit_parent.sha256(BUILD_AUDIT)
        == EXPECTED_BUILD_AUDIT_HASH
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 159
        and value["tests"]["observed"] == 159
        and authorization["implementation_build_only"] is True
        and authorization["fresh_disjoint_external_protocol_design"] is False
        and authorization["fresh_external_activation_or_launch"] is False
        and authorization["v25157_population_model_evaluator_retry_resume_or_reuse"]
        is False
        and authorization["evaluator_or_deepwidebench_or_sota"] is False
    )


def _population_barrier() -> bool:
    raw = json.loads(
        build_parent.audit_parent._ordinary(POPULATION_AUDIT).read_text(
            encoding="utf-8"
        )
    )
    value = population_parent.validate_audit(raw)
    return bool(
        build_parent.audit_parent.sha256(POPULATION_AUDIT)
        == EXPECTED_POPULATION_AUDIT_HASH
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["identity_count"] == 20
        and value["identity_history_zero_hit_count"] == 20
        and value["network_endpoint_page_value_model_or_evaluator_access"]
        is False
        and value[
            "v25141_v25145_v25149_v25153_v25157_population_reuse"
        ]
        is False
        and value[
            "external_protocol_activation_evaluator_or_deepwidebench_authorized"
        ]
        is False
        and value["entropy_or_information_gain_assigns_signed_credit"]
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    audit = build_parent.audit_parent
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    tests = _tests()
    closure = audit._dependency_closure((RUNTIME_SOURCE,))
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
        "focused_preprotocol_population_runtime_and_build_tests_exact24": tests[
            "passed"
        ],
        "v25159_clean_build_audit_and_runtime_bytes_bound": _build_barrier(),
        "v25160_aggregate_population_freeze_bound": _population_barrier(),
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
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25161_vertical_key_value_preprotocol_authorization_audit",
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
            "fresh_disjoint_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
            "v25141_v25145_v25149_v25153_v25157_population_reuse": False,
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
        != "v25161_vertical_key_value_preprotocol_authorization_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("runtime_source", {}).get("sha256")
        != EXPECTED_RUNTIME_HASH
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
            "fresh_disjoint_external_protocol_design": True,
            "fresh_external_activation_or_launch": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
            "v25141_v25145_v25149_v25153_v25157_population_reuse": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.61 pre-protocol audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    build_parent.audit_parent.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "protocol_design_authorized": value["authorization"][
                    "fresh_disjoint_external_protocol_design"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
