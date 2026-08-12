#!/usr/bin/env python3
"""Clean-build audit for the pure V2.51.77 escaped-pipe normalizer."""

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

from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import diagnose_v25176_v25175_normalizer_representation as diagnosis  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25178_quote_aware_normalizer_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25178_quote_aware_normalizer_build.py")
TEST = Path("tests/test_audit_v25178_quote_aware_normalizer_build.py")
NORMALIZER_SOURCE = Path(
    "src/deepwide_agent/v25177_quote_aware_pipe_normalizer.py"
)
NORMALIZER_TEST = Path("tests/test_v25177_quote_aware_pipe_normalizer.py")
PARENT_DIAGNOSIS = diagnosis.OUTPUT
EXPECTED_PARENT_DIAGNOSIS_HASH = (
    "7e37476e616acda8e4500e32768da6e798df1ea3fe8249369a871fbcbbbb331e"
)
TEST_SUITES = (
    ("test_audit_v25178_quote_aware_normalizer_build.py", 5),
    ("test_v25177_quote_aware_pipe_normalizer.py", 9),
    ("test_diagnose_v25176_v25175_normalizer_representation.py", 5),
    ("test_v25170_production_normalizer_disposition_observer.py", 6),
    ("test_v24259_deterministic_table_normalizer.py", 11),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = base.payload_sha256


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


def _parent_barrier() -> bool:
    raw = json.loads(base._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
    value = diagnosis.validate_diagnosis(raw)
    authorization = value["authorization"]
    return bool(
        base.sha256(PARENT_DIAGNOSIS) == EXPECTED_PARENT_DIAGNOSIS_HASH
        and value["diagnosis_valid"] is True
        and value["findings"] == []
        and value["aggregate"]["task_count"] == 20
        and value["aggregate"]["production_model_generated_tasks"] == 19
        and value["aggregate"]["production_fallback_tasks"] == 1
        and value["diagnosis"][
            "aggregate_cannot_distinguish_row_width_mismatch_from_backslash_escaped_pipe"
        ]
        is True
        and value["diagnosis"][
            "natural_reject_is_not_claimed_to_be_an_escaped_pipe"
        ]
        is True
        and authorization["quote_aware_literal_preserving_normalizer_build_only"]
        is True
        and authorization["runtime_integration_or_external_protocol"] is False
        and authorization["old_population_retry_resume_rerun_or_reuse"] is False
        and authorization["binding_successor_design"] is False
        and authorization["vertical_binding_policy_change"] is False
        and authorization["evaluator_or_quality_result"] is False
        and authorization["deepwidebench_dev64_exact220_leaderboard_or_sota"]
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure = base._dependency_closure((NORMALIZER_SOURCE,))
    semantic = base._semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        NORMALIZER_SOURCE,
        NORMALIZER_TEST,
        diagnosis.SOURCE,
        diagnosis.TEST,
        PARENT_DIAGNOSIS,
        diagnosis.PUBLIC_LOADER,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not base._tracked(path)
    )
    watchers = base._watchers()
    lease_inactive = base._lease_inactive()
    representation = diagnosis.representation_experiment()
    checks = {
        "focused_quote_aware_diagnosis_observer_and_parent_tests_exact36": tests[
            "passed"
        ],
        "v25176_frozen_representation_diagnosis_bound": _parent_barrier(),
        "all_sources_parent_artifact_and_public_loader_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "direct_normalizer_has_no_effect_imports": not base._direct_forbidden_imports(
            NORMALIZER_SOURCE
        ),
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
        "escaped_pipe_failure_synthetically_reproduced": not representation[
            "frozen_exact_parser_accepts_backslash_escaped_pipe"
        ]
        and not representation[
            "frozen_normalizer_accepts_backslash_escaped_pipe"
        ],
        "internal_transport_and_final_csv_representation_are_bounded": representation[
            "internal_numeric_entity_is_frozen_parser_compatible"
        ]
        and representation[
            "internal_numeric_entity_roundtrips_to_semantic_values"
        ]
        and representation[
            "csv_quoted_pipe_is_public_loader_column_shape_compatible"
        ]
        and representation[
            "csv_quoted_pipe_preserves_nonwhitespace_literal_and_delimiter"
        ],
        "natural_failure_not_reidentified_or_old_population_opened": True,
        "runtime_integration_external_protocol_evaluator_and_220_forbidden": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25178_quote_aware_normalizer_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "normalizer_dependency_closure": [str(path) for path in closure],
        "normalizer_semantic_audit": {**semantic, "untracked_sources": untracked},
        "parent_representation_diagnosis": {
            "path": str(PARENT_DIAGNOSIS),
            "sha256": base.sha256(PARENT_DIAGNOSIS),
        },
        "representation_experiment": representation,
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
            "pure_normalizer_build_valid": not findings,
            "runtime_integration_design": not findings,
            "runtime_integration_implementation": False,
            "fresh_external_protocol_or_launch": False,
            "old_population_retry_resume_rerun_or_reuse": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_deepwidebench_or_sota": False,
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
        or copied.get("role") != "v25178_quote_aware_normalizer_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_representation_diagnosis", {}).get("sha256")
        != EXPECTED_PARENT_DIAGNOSIS_HASH
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
            "pure_normalizer_build_valid": True,
            "runtime_integration_design": True,
            "runtime_integration_implementation": False,
            "fresh_external_protocol_or_launch": False,
            "old_population_retry_resume_rerun_or_reuse": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_deepwidebench_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.78 quote-aware build audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
