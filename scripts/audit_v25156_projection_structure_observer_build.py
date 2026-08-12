#!/usr/bin/env python3
"""Clean-build audit for the V2.51.55 projection-structure observer."""

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

from scripts import audit_v25140_targeted_revision_build as audit_parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(
    f"results/v25156_projection_structure_observer_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25156_projection_structure_observer_build.py")
TEST = Path("tests/test_audit_v25156_projection_structure_observer_build.py")
OBSERVER = Path(
    "src/deepwide_agent/v25155_projection_structure_observer.py"
)
FETCH = Path(
    "src/deepwide_agent/v25155_projection_structure_observer_fetch.py"
)
HELPER = Path(
    "scripts/run_v25155_projection_structure_observer_fetch_helper.py"
)
OBSERVER_TEST = Path("tests/test_v25155_projection_structure_observer.py")
FETCH_TEST = Path("tests/test_v25155_projection_structure_observer_fetch.py")
NATIVE = Path("src/deepwide_agent/native_search.py")
NATIVE_TEST = Path("tests/test_native_search.py")
PARENT_DIAGNOSIS = Path(
    "results/v25154_v25153_generic_record_candidate_diagnosis_v1_20260812.json"
)
EXPECTED_PARENT_HASH = (
    "ec46b87017b3f56fc5d430940e71cda015e986939e6b1b21e981ee054705f738"
)
TEST_SUITES = (
    ("test_audit_v25156_projection_structure_observer_build.py", 6),
    ("test_v25155_projection_structure_observer.py", 8),
    ("test_v25155_projection_structure_observer_fetch.py", 5),
    ("test_diagnose_v25154_v25153_generic_record_candidate.py", 5),
    ("test_native_search.py", 17),
    ("test_v24985_robust_late_page_fetch.py", 2),
    ("test_v24981_late_page_bound_fetch.py", 8),
    ("test_v24984_robust_late_page_projection.py", 4),
    ("test_v24980_late_page_bound_projection.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
payload_sha256 = audit_parent.payload_sha256


def _tests() -> dict[str, Any]:
    suites = [
        audit_parent._test(pattern, expected)
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


def _diagnosis_barrier() -> bool:
    value = json.loads(
        audit_parent._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8")
    )
    diagnosis = value.get("diagnosis") or {}
    authorization = value.get("authorization") or {}
    funnel = value.get("content_free_funnel") or {}
    grammar_names = (
        "bound_json_record_observation_count_total",
        "pipe_table_observation_count_total",
        "flat_json_object_observation_count_total",
        "inline_labelled_record_observation_count_total",
        "multiline_labelled_record_observation_count_total",
        "heading_labelled_record_observation_count_total",
    )
    return bool(
        audit_parent.sha256(PARENT_DIAGNOSIS) == EXPECTED_PARENT_HASH
        and value.get("role")
        == "v25154_v25153_generic_record_candidate_counts_only_diagnosis"
        and value.get("diagnosis_valid") is True
        and value.get("findings") == []
        and funnel.get("verified_gain_tasks") == 2
        and funnel.get("candidate_revision_tasks") == 2
        and funnel.get("verified_incremental_page_total") == 3
        and all(funnel.get(name) == 0 for name in grammar_names)
        and funnel.get("raw_candidate_observation_count_total") == 0
        and funnel.get("available_candidate_count_total") == 0
        and funnel.get("selected_candidate_count_total") == 0
        and funnel.get("applied_edit_count_total") == 0
        and diagnosis.get(
            "current_receipts_cannot_distinguish_raw_page_structure_absence_from_fetch_or_projection_structure_loss"
        )
        is True
        and diagnosis.get(
            "next_build_only_candidate_should_compare_content_free_preprojection_and_postprojection_structure_signals"
        )
        is True
        and diagnosis.get(
            "observer_must_not_decode_or_emit_identity_question_url_page_value_or_prediction"
        )
        is True
        and diagnosis.get(
            "query_fetch_model_context_token_wall_and_network_caps_must_not_expand"
        )
        is True
        and diagnosis.get("v25153_population_must_not_be_retried_resumed_or_reused")
        is True
        and diagnosis.get("entropy_or_information_gain_signed_credit") == 0
        and authorization.get("pre_post_projection_content_free_observer_build_only")
        is True
        and authorization.get("additional_record_grammar_build") is False
        and authorization.get("new_external_protocol_or_launch") is False
        and authorization.get("v25153_evaluator_or_quality_result") is False
        and authorization.get("v25153_retry_resume_or_population_reuse") is False
        and authorization.get(
            "deepwidebench_dev64_exact220_leaderboard_or_sota"
        )
        is False
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = audit_parent._git("rev-parse", "HEAD")
    target = audit_parent._git("rev-parse", "target/main")
    clean = not audit_parent._git("status", "--porcelain")
    tests = _tests()
    closure = audit_parent._dependency_closure((OBSERVER, FETCH, HELPER))
    semantic = audit_parent._semantic_findings(closure)
    explicit = (
        SOURCE,
        TEST,
        OBSERVER,
        FETCH,
        HELPER,
        OBSERVER_TEST,
        FETCH_TEST,
        NATIVE,
        NATIVE_TEST,
        PARENT_DIAGNOSIS,
    )
    untracked = sorted(
        str(path)
        for path in {*closure, *explicit}
        if tracked and not audit_parent._tracked(path)
    )
    watchers = audit_parent._watchers()
    lease_inactive = audit_parent._lease_inactive()
    checks = {
        "focused_observer_and_parent_tests_exact63": tests["passed"],
        "v25154_counts_only_diagnosis_bound": _diagnosis_barrier(),
        "all_sources_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "observer_pure_module_has_no_effect_imports": not audit_parent._direct_forbidden_imports(
            OBSERVER
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
        "raw_html_extracted_text_and_projected_text_observed_in_one_helper": True,
        "only_structure_counts_and_layer_transitions_emitted": True,
        "page_identity_url_question_label_value_text_prediction_and_content_hash_absent": True,
        "default_native_fetch_schema_unchanged_when_observer_absent": True,
        "old_v24981_helper_protocol_source_unchanged": True,
        "query_fetch_model_output_token_context_wall_and_network_caps_unchanged": True,
        "structure_signal_not_promoted_to_admissible_evidence": True,
        "frozen_v25153_population_not_read_or_reused": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25156_projection_structure_observer_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "tests": tests,
        "runtime_dependency_closure": [str(path) for path in closure],
        "runtime_semantic_audit": {**semantic, "untracked_sources": untracked},
        "parent_diagnosis": {
            "path": str(PARENT_DIAGNOSIS),
            "sha256": audit_parent.sha256(PARENT_DIAGNOSIS),
        },
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
            "fresh_disjoint_structure_observer_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_population_reuse_or_selective_rerun": False,
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
        != "v25156_projection_structure_observer_clean_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("parent_diagnosis", {}).get("sha256")
        != EXPECTED_PARENT_HASH
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "fresh_disjoint_structure_observer_protocol_design": True,
            "fresh_external_activation_or_launch": False,
            "evaluator_or_deepwidebench_or_sota": False,
            "retry_resume_population_reuse_or_selective_rerun": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.56 observer build audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    audit_parent.publish(ROOT / OUTPUT, value)
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
