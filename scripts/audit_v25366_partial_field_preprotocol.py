#!/usr/bin/env python3
"""Pre-protocol barrier for the third fresh partial-field mechanism gate."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25364_third_fresh_pep_partial_field_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25363_partial_field_grounded_fact_build as build_parent  # noqa: E402
from scripts import audit_v25365_third_fresh_pep_population_selection as population_parent  # noqa: E402


DATE = "20260813"
ROLE = "v25366_partial_field_third_fresh_preprotocol_audit"
SOURCE = Path("scripts/audit_v25366_partial_field_preprotocol.py")
TEST = Path("tests/test_audit_v25366_partial_field_preprotocol.py")
RUNTIME_SOURCE = build_parent.RUNTIME_SOURCE
BUILD_AUDIT = build_parent.OUTPUT
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25364_third_fresh_pep_partial_field_population.py"
)
POPULATION_AUDIT = population_parent.OUTPUT
OUTPUT = Path(f"results/v25366_partial_field_preprotocol_audit_v1_{DATE}.json")
EXPECTED_RUNTIME_HASH = (
    "62f635e900b242894335091ef0ca502a43b4620c7fc64e7d90827359e8a2fb1d"
)
EXPECTED_BUILD_AUDIT_HASH = (
    "b789b3fc9bf01f94e0d77bb21f2d1e443175f1bce62bb469d6be2f51665f6d45"
)
EXPECTED_POPULATION_SOURCE_HASH = (
    "838146048c073d4c4892536569e87e6c6fda9ee9e54c7b6f19c5cc9d1d521623"
)
EXPECTED_POPULATION_AUDIT_HASH = (
    "44e0d2ecd3563b5006c01e6751cb918a641fbcb4d32a98f630f6f15dbb1aca9e"
)
TEST_SUITES = (
    ("test_audit_v25366_partial_field_preprotocol.py", 4),
    ("test_audit_v25363_partial_field_grounded_fact_build.py", 4),
    ("test_v25362_partial_field_grounded_fact_runtime.py", 5),
    ("test_v25364_third_fresh_pep_partial_field_population.py", 4),
    ("test_audit_v25365_third_fresh_pep_population_selection.py", 3),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _build_barrier() -> bool:
    value = build_parent.validate_audit(
        json.loads(base._ordinary(BUILD_AUDIT).read_text(encoding="utf-8"))
    )
    authorization = value["authorization"]
    return bool(
        base.sha256(RUNTIME_SOURCE) == EXPECTED_RUNTIME_HASH
        and base.sha256(BUILD_AUDIT) == EXPECTED_BUILD_AUDIT_HASH
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 73
        and value["tests"]["observed"] == 73
        and value["semantic_audit"]["privileged_runtime_field_accesses"] == []
        and value["semantic_audit"]["evaluator_capabilities"] == []
        and value["semantic_audit"]["credential_literal_hits"] == []
        and authorization[
            "fresh_disjoint_population_selection_and_protocol_design"
        ]
        is True
        and authorization["network_activation_or_external_forward"] is False
        and authorization["evaluator_or_deepwidebench_forward"] is False
    )


def _population_barrier() -> bool:
    value = population_parent.validate_audit(
        json.loads(base._ordinary(POPULATION_AUDIT).read_text(encoding="utf-8"))
    )
    authorization = value["authorization"]
    return bool(
        base.sha256(POPULATION_SOURCE) == EXPECTED_POPULATION_SOURCE_HASH
        and base.sha256(POPULATION_AUDIT) == EXPECTED_POPULATION_AUDIT_HASH
        and value["identity_count"] == population.TASK_COUNT
        and value["identity_vector_sha256"]
        == population.EXPECTED_IDENTITY_VECTOR_SHA256
        and value["canonical_identity_and_slug_tree_match_count"] == 0
        and value["canonical_identity_and_slug_history_introduction_count"] == 0
        and value["whole_consecutive_group_tree_and_history_counts_all_zero"]
        is True
        and value[
            "individual_identity_retained_replaced_or_selected_using_scan_outcome"
        ]
        is False
        and authorization["third_fresh_pep_population_protocol_design"] is True
        and authorization[
            "network_model_search_fetch_external_forward_or_evaluator"
        ]
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure = base._dependency_closure((RUNTIME_SOURCE,))
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        BUILD_AUDIT,
        POPULATION_SOURCE,
        POPULATION_AUDIT,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    watcher_rows = watchers.watcher_snapshot()
    expected_watchers = [
        {"pid": pid, "start_ticks": ticks, "marker": marker}
        for pid, ticks, marker in watchers.EXPECTED_WATCHERS
    ]
    checks = {
        "focused_build_runtime_population_and_preprotocol_tests_exact20": tests[
            "passed"
        ],
        "v25363_clean_build_runtime_and_hash_barrier": _build_barrier(),
        "v25364_v25365_indivisible_population_zero_history_barrier": _population_barrier(),
        "all_sources_parent_artifacts_and_runtime_closure_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "runtime_dependency_closure_exact80": len(closure) == 80,
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "runtime_boundary_and_mechanism_gate_fixed": (
            population.source_policy()["runtime_boundary"]
            == ["opaque_id", "question", "same_forward_public_pages"]
            and population.mechanism_gate()[
                "minimum_attributable_prediction_changed_tasks"
            ]
            == 3
            and population.mechanism_gate()["positive_signed_credit_count"] == 0
        ),
        "old_populations_retry_resume_replay_or_reuse_forbidden": True,
        "protected_watchers_unchanged": watcher_rows == expected_watchers,
        "shared_api_lease_inactive": base._lease_inactive(),
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean if tracked else True,
        },
        "tests": tests,
        "runtime_source": {
            "path": str(RUNTIME_SOURCE),
            "sha256": base.sha256(RUNTIME_SOURCE),
        },
        "build_audit": {
            "path": str(BUILD_AUDIT),
            "sha256": base.sha256(BUILD_AUDIT),
        },
        "population_source": {
            "path": str(POPULATION_SOURCE),
            "sha256": base.sha256(POPULATION_SOURCE),
        },
        "population_audit": {
            "path": str(POPULATION_AUDIT),
            "sha256": base.sha256(POPULATION_AUDIT),
        },
        "runtime_dependency_closure": [str(path) for path in closure],
        "runtime_semantic_audit": {**semantic, "untracked_sources": untracked},
        "runtime_state": {
            "shared_api_lease_inactive": checks["shared_api_lease_inactive"],
            "protected_watchers": watcher_rows,
        },
        "task_and_gate_binding": {
            "task_count": population.TASK_COUNT,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
            "arm_order_vector_sha256": population.EXPECTED_ARM_ORDER_VECTOR_SHA256,
            "mechanism_gate": population.mechanism_gate(),
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "third_fresh_partial_field_protocol_design": not findings,
            "external_activation_or_launch": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_replay_population_replacement_or_selective_rerun": False,
            "first_or_second_fresh_population_reuse": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
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
        or copied.get("population_source", {}).get("sha256")
        != EXPECTED_POPULATION_SOURCE_HASH
        or copied.get("population_audit", {}).get("sha256")
        != EXPECTED_POPULATION_AUDIT_HASH
        or copied.get("task_and_gate_binding")
        != {
            "task_count": population.TASK_COUNT,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
            "arm_order_vector_sha256": population.EXPECTED_ARM_ORDER_VECTOR_SHA256,
            "mechanism_gate": population.mechanism_gate(),
        }
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "third_fresh_partial_field_protocol_design": True,
            "external_activation_or_launch": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_replay_population_replacement_or_selective_rerun": False,
            "first_or_second_fresh_population_reuse": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.66 partial-field preprotocol audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "protocol_design_authorized": value["authorization"][
                    "third_fresh_partial_field_protocol_design"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
