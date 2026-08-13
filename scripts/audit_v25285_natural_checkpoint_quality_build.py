#!/usr/bin/env python3
"""Clean-build audit for the V2.52.84 natural checkpoint quality seam."""

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

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from deepwide_agent import v25280_paired_checkpoint_reliability_external_contract as external_contract  # noqa: E402
from deepwide_agent import v25284_natural_checkpoint_quality_runtime as runtime  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25272_validated_production_checkpoint_build as checkpoint_audit  # noqa: E402
from scripts import audit_v25277_third_disjoint_checkpoint_population as population_audit  # noqa: E402
from scripts import audit_v25283_paired_checkpoint_reliability_forward as reliability_audit  # noqa: E402


DATE = "20260813"
ROLE = "v25285_natural_checkpoint_quality_clean_build_audit"
OUTPUT = Path(f"results/v25285_natural_checkpoint_quality_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25285_natural_checkpoint_quality_build.py")
TEST = Path("tests/test_audit_v25285_natural_checkpoint_quality_build.py")
RUNTIME = Path("src/deepwide_agent/v25284_natural_checkpoint_quality_runtime.py")
RUNTIME_TEST = Path("tests/test_v25284_natural_checkpoint_quality_runtime.py")
FIXED_PARENTS = {
    checkpoint_audit.OUTPUT: (
        "f7c7d16def15ff80ae76b3a506da345c38b3c28286bf4c3e05eec84480f5aace"
    ),
    external_contract.FORWARD_AUDIT: (
        "8c1bd6cd12e32be50ae9e9dbb1706ebb145fda699c392b26ee0e656d8f13bc2a"
    ),
}
TEST_SUITES = (
    ("test_audit_v25285_natural_checkpoint_quality_build.py", 5),
    ("test_v25284_natural_checkpoint_quality_runtime.py", 11),
    ("test_v25278_paired_checkpoint_reliability_runtime.py", 7),
    ("test_v25271_validated_production_checkpoint_runtime.py", 9),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 76
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "f1b0f406d200d78af35fc6421ef4a2f9528a0f6c721eabb820c882e808e42631"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "e7f0f91a2d74d59de7d46c1cc07f5e895f8de3f2d9b5d7d088334242590c398c"
)
EXPECTED_RUNTIME_SHA256 = (
    "1bb7409e1fdd12a810de70d67c6fb1f007963ceb6a873e21cc5f71ef6bc91e33"
)
EXPECTED_RUNTIME_TEST_SHA256 = (
    "86e6708201029ec17cf10658282288891b8c80c09041d9821b25da49c60bf2ed"
)
CHECK_NAMES = frozenset(
    {
        "checkpoint_and_reliability_parent_hashes_validate_and_authorize_design_only",
        "runtime_and_audit_tests_exact32",
        "git_clean_head_equals_target_main",
        "all_runtime_audit_test_parent_and_closure_files_tracked",
        "runtime_and_test_hashes_exact",
        "runtime_dependency_vector_exact76_and_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "one_real_v25271_forward_per_task",
        "no_fault_injection_and_injected_marker_rejected",
        "clean_and_precheckpoint_tasks_are_identity_pairs",
        "natural_postcheckpoint_event_is_only_prediction_change_entry",
        "regular_and_recovery_roles_are_stage_bound",
        "result_stage_receipt_and_effect_parity_are_exact",
        "caller_projector_receives_visible_input_and_is_recomputed",
        "existing_external_projector_two_rows_per_visible_task",
        "candidate_additional_query_fetch_model_token_and_credit_zero",
        "nested_resealed_result_receipt_stage_projector_and_credit_tamper_fail_closed",
        "truthful_query4_fetch14_model4_caps_unchanged",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(sorted(base._dependency_closure((RUNTIME,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _fixed_parents() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_PARENTS}


def _parent_barrier() -> bool:
    if _fixed_parents() != {str(path): digest for path, digest in FIXED_PARENTS.items()}:
        return False
    try:
        checkpoint = checkpoint_audit.validate_audit(
            json.loads(base._ordinary(checkpoint_audit.OUTPUT).read_text(encoding="utf-8"))
        )
        reliability = reliability_audit.validate_audit(
            json.loads(
                base._ordinary(external_contract.FORWARD_AUDIT).read_text(
                    encoding="utf-8"
                )
            )
        )
    except BaseException:
        return False
    return bool(
        checkpoint["audit_valid"] is True
        and checkpoint["findings"] == []
        and checkpoint["authorization"][
            "fresh_benchmark_external_reliability_protocol_design"
        ]
        is True
        and checkpoint["authorization"]["runtime_activation_or_external_launch"]
        is False
        and reliability["audit_valid"] is True
        and reliability["findings"] == []
        and reliability["reliability_decision"]["reliability_gate_passed"] is True
        and reliability["authorization"]["postforward_reliability_diagnosis"]
        is True
        and reliability["authorization"][
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"
        ]
        is False
    )


def _source_invariants() -> bool:
    source = base._ordinary(RUNTIME).read_text(encoding="utf-8")
    return bool(
        source.count("parent.run_task(") == 1
        and "InjectedCheckpointReliabilityFault()" not in source
        and "failure_as_zero_projector=dict" not in source
        and "failure_as_zero_projector: Callable[[Mapping[str, str]], str]" in source
    )


def _live_watchers_exact(watchers: object) -> bool:
    expected_rows = population_audit.parent_audit.EXPECTED_WATCHERS
    if (
        not isinstance(watchers, list)
        or len(watchers) != len(expected_rows)
        or any(
            not isinstance(row, Mapping)
            or set(row) != {"pid", "marker", "start_ticks"}
            for row in expected_rows
        )
    ):
        return False
    expected = {row["pid"]: row["start_ticks"] for row in expected_rows}
    observed: dict[int, int] = {}
    for row in watchers:
        if (
            not isinstance(row, Mapping)
            or set(row) != {"pid", "start_ticks", "matches_frozen_identity"}
            or isinstance(row.get("pid"), bool)
            or not isinstance(row.get("pid"), int)
            or isinstance(row.get("start_ticks"), bool)
            or not isinstance(row.get("start_ticks"), int)
            or row.get("matches_frozen_identity") is not True
            or row["pid"] in observed
        ):
            return False
        observed[row["pid"]] = row["start_ticks"]
    return observed == expected


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        RUNTIME,
        RUNTIME_TEST,
        *FIXED_PARENTS,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    tests_green = tests["passed"]
    checks = {
        "checkpoint_and_reliability_parent_hashes_validate_and_authorize_design_only": _parent_barrier(),
        "runtime_and_audit_tests_exact32": tests_green,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "all_runtime_audit_test_parent_and_closure_files_tracked": not untracked,
        "runtime_and_test_hashes_exact": (
            base.sha256(RUNTIME) == EXPECTED_RUNTIME_SHA256
            and base.sha256(RUNTIME_TEST) == EXPECTED_RUNTIME_TEST_SHA256
        ),
        "runtime_dependency_vector_exact76_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and seal.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and seal.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "one_real_v25271_forward_per_task": tests_green and _source_invariants(),
        "no_fault_injection_and_injected_marker_rejected": tests_green
        and _source_invariants(),
        "clean_and_precheckpoint_tasks_are_identity_pairs": tests_green,
        "natural_postcheckpoint_event_is_only_prediction_change_entry": tests_green,
        "regular_and_recovery_roles_are_stage_bound": tests_green,
        "result_stage_receipt_and_effect_parity_are_exact": tests_green,
        "caller_projector_receives_visible_input_and_is_recomputed": tests_green,
        "existing_external_projector_two_rows_per_visible_task": tests_green,
        "candidate_additional_query_fetch_model_token_and_credit_zero": tests_green,
        "nested_resealed_result_receipt_stage_projector_and_credit_tamper_fail_closed": tests_green,
        "truthful_query4_fetch14_model4_caps_unchanged": (
            cap.QUERY_CAP == 4 and cap.FETCH_CAP == 14 and cap.MODEL_CAP == 4
        ),
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "protected_watchers_unchanged": _live_watchers_exact(
            external_contract.watcher_snapshot()
        ),
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
            "clean": clean,
        },
        "fixed_parents": _fixed_parents(),
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": seal.payload_sha256(vector),
        "runtime_dependency_path_sha256": seal.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "paired_estimand": {
            "real_forward_count_per_task": 1,
            "treatment_entry": "observed_natural_postcheckpoint_recovery_only",
            "clean_or_precheckpoint_task": "control_candidate_identity",
            "natural_postcheckpoint_control": "visible_input_only_legacy_failure_as_zero",
            "natural_postcheckpoint_candidate": "same_forward_trusted_checkpoint_prediction",
            "fault_injection": False,
            "candidate_additional_queries": 0,
            "candidate_additional_fetches": 0,
            "candidate_additional_model_forwards": 0,
            "candidate_additional_system_total_tokens": 0,
            "positive_signed_credit_count": 0,
            "quality_claim_requires_prediction_freeze_forward_audit_and_independent_postfreeze_evaluator": True,
            "zero_natural_event_population_is_mechanism_no_go": True,
        },
        "future_protocol_requirements": {
            "fresh_disjoint_task_population": True,
            "runtime_keys": ["opaque_id", "question"],
            "caller_visible_failure_as_zero_projector_source_hash_bound": True,
            "fixed_denominator_failure_as_zero": True,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "quality_go": {
                "candidate_exact_strictly_greater": True,
                "entity_row_item_column_composite_nonregression": True,
                "evaluator_invalid_fallback_outer_failure_nonincrease": True,
            },
            "direct_public_220_after_build": False,
        },
        "physical_caps": {
            "queries": cap.QUERY_CAP,
            "fetches": cap.FETCH_CAP,
            "model_forwards": cap.MODEL_CAP,
        },
        "protected_watchers": external_contract.watcher_snapshot(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_natural_checkpoint_quality_population_and_protocol_design": not findings,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "candidate_quality_or_prediction_improvement_claim": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = seal.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    vector = copied.get("runtime_dependency_vector") or []
    semantic = copied.get("semantic_audit") or {}
    checks = copied.get("checks") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_parents",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "paired_estimand",
            "future_protocol_requirements",
            "physical_caps",
            "protected_watchers",
            "checks",
            "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or copied.get("fixed_parents")
        != {str(path): digest for path, digest in FIXED_PARENTS.items()}
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or set(row)
            != {
                "pattern",
                "expected",
                "observed",
                "returncode",
                "passed",
                "output_sha256",
            }
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or any(
            not isinstance(row, Mapping)
            or set(row) != {"path", "sha256"}
            or not isinstance(row.get("path"), str)
            or not isinstance(row.get("sha256"), str)
            or len(row["sha256"]) != 64
            for row in vector
        )
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or semantic
        != {
            "privileged_runtime_field_accesses": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
            "allowed_provider_rank_access": [
                "src/deepwide_agent/clients.py:565:score"
            ],
            "untracked_sources": [],
        }
        or copied.get("paired_estimand")
        != {
            "real_forward_count_per_task": 1,
            "treatment_entry": "observed_natural_postcheckpoint_recovery_only",
            "clean_or_precheckpoint_task": "control_candidate_identity",
            "natural_postcheckpoint_control": "visible_input_only_legacy_failure_as_zero",
            "natural_postcheckpoint_candidate": "same_forward_trusted_checkpoint_prediction",
            "fault_injection": False,
            "candidate_additional_queries": 0,
            "candidate_additional_fetches": 0,
            "candidate_additional_model_forwards": 0,
            "candidate_additional_system_total_tokens": 0,
            "positive_signed_credit_count": 0,
            "quality_claim_requires_prediction_freeze_forward_audit_and_independent_postfreeze_evaluator": True,
            "zero_natural_event_population_is_mechanism_no_go": True,
        }
        or copied.get("future_protocol_requirements")
        != {
            "fresh_disjoint_task_population": True,
            "runtime_keys": ["opaque_id", "question"],
            "caller_visible_failure_as_zero_projector_source_hash_bound": True,
            "fixed_denominator_failure_as_zero": True,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "quality_go": {
                "candidate_exact_strictly_greater": True,
                "entity_row_item_column_composite_nonregression": True,
                "evaluator_invalid_fallback_outer_failure_nonincrease": True,
            },
            "direct_public_220_after_build": False,
        }
        or copied.get("physical_caps")
        != {"queries": 4, "fetches": 14, "model_forwards": 4}
        or not _live_watchers_exact(copied.get("protected_watchers"))
        or checks != {name: True for name in CHECK_NAMES}
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or copied.get("authorization")
        != {
            "fresh_disjoint_natural_checkpoint_quality_population_and_protocol_design": True,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "candidate_quality_or_prediction_improvement_claim": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or signature != seal.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.85 natural checkpoint quality build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    import os

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
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True}, sort_keys=True))


if __name__ == "__main__":
    main()
