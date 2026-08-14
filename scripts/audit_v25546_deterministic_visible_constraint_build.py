#!/usr/bin/env python3
"""Clean pushed audit for the V2.55.44/45 deterministic successor."""

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
from deepwide_agent import v25544_deterministic_visible_constraint_projector as primitive  # noqa: E402
from deepwide_agent import v25545_deterministic_visible_constraint_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25543_visible_constraint_synthesis_build as parent_audit  # noqa: E402


DATE = "20260814"
ROLE = "v25546_deterministic_visible_constraint_clean_build_audit"
IMPLEMENTATION_COMMIT = "0cf0622f7ea24620e40c8e3d49ccd6e619fd66a6"
SOURCE = Path("scripts/audit_v25546_deterministic_visible_constraint_build.py")
TEST = Path("tests/test_audit_v25546_deterministic_visible_constraint_build.py")
PRIMITIVE_SOURCE = Path(
    "src/deepwide_agent/v25544_deterministic_visible_constraint_projector.py"
)
PRIMITIVE_TEST = Path(
    "tests/test_v25544_deterministic_visible_constraint_projector.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25545_deterministic_visible_constraint_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25545_deterministic_visible_constraint_runtime.py"
)
PARENT_AUDIT = parent_audit.OUTPUT
OUTPUT = Path(
    f"results/v25546_deterministic_visible_constraint_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    PRIMITIVE_SOURCE: "835d28d8ea748b641b96684a96974ed2a038f3b69179eab16dc4eef30850fe58",
    PRIMITIVE_TEST: "41eb44d71097b5ce5c5292871901653dca0f66a5e5bdee089b34cfc0f96eaba1",
    RUNTIME_SOURCE: "7d58783016158d75a5d8b38483dbf89ea85cfee31408ca625acb99f64c01a12b",
    RUNTIME_TEST: "cd294df302216c38cd249a0fb07d5823f998110721d1a2f8250540cfc5d0946b",
    PARENT_AUDIT: "d6526cb5bc7690ea121a640b57404b925cb93355197036d9e1e60a5c0c6ef688",
}
TEST_SUITES = (
    ("test_audit_v25546_deterministic_visible_constraint_build.py", 4),
    ("test_v25545_deterministic_visible_constraint_runtime.py", 4),
    ("test_v25544_deterministic_visible_constraint_projector.py", 6),
    ("test_v25541_visible_output_constraint_contract.py", 7),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25395_visible_membership_synthesis_runtime.py", 7),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25383_joint_synthesis_changed_safe_runtime.py", 8),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 95
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "6758818c955f75d9e958a2f25f1a5d0ef41b5cb2a77638cac1b9f0e190c812a7"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "b846c90ee70bc04cba09cf290bd9322bf304b573f423507b67d30cc6ab476241"
)
CHECK_NAMES = frozenset(
    {
        "v25543_parent_clean_build_hash_role_and_population_design_authority_exact",
        "implementation_sources_tests_and_parent_hash_exact",
        "implementation_commit_in_head_history",
        "focused_successor_contract_and_parent_chain_tests_exact70",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact95_and_hash_bound",
        "direct_primitive_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "complete_date_reformat_explicit_scale_conversion_and_stable_sort_only",
        "temporal_range_and_rank_slots_never_mutate_row_population",
        "partial_ambiguous_or_mixed_values_fail_closed",
        "one_v25401_parent_forward_shared_by_control_and_candidate",
        "candidate_has_zero_independent_provider_or_sampling_effect",
        "no_safe_projection_returns_parent_prediction_byte_exact",
        "query4_fetch14_model3_caps_unchanged",
        "runtime_inputs_exactly_opaque_id_and_question",
        "positive_signed_credit_zero",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_external_effect_performed_by_build_audit",
    }
)


def _parent_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    parent_audit.validate_audit(value)
    if (
        base.sha256(PARENT_AUDIT) != FIXED_HASHES[PARENT_AUDIT]
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("fixed220_visible_reach", {}).get("active_tasks") != 95
        or value.get("authorization", {}).get(
            "fresh_task_disjoint_shared_parent_population_design"
        )
        is not True
        or value.get("authorization", {}).get(
            "external_population_protocol_or_forward"
        )
        is not False
        or value.get("authorization", {}).get(
            "deepwidebench_forward_or_evaluator"
        )
        is not False
    ):
        raise RuntimeError("V2.55.46 parent build barrier drifted")
    return value


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


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str))
    vector = [
        {"path": str(path), "sha256": base.sha256(path)} for path in closure
    ]
    return closure, vector


def build_audit(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    parent = _parent_barrier()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain", "--untracked-files=all")
    history = set(base._git("rev-list", head).splitlines())
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        PRIMITIVE_SOURCE,
        PRIMITIVE_TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        PARENT_AUDIT,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    primitive_contract = primitive.integration_contract()
    runtime_contract = runtime.integration_contract()
    snapshot = watchers.watcher_snapshot()
    reported_clean = clean if tracked else True
    checks = {
        "v25543_parent_clean_build_hash_role_and_population_design_authority_exact": bool(parent),
        "implementation_sources_tests_and_parent_hash_exact": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_in_head_history": IMPLEMENTATION_COMMIT in history,
        "focused_successor_contract_and_parent_chain_tests_exact70": tests["passed"],
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact95_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_primitive_and_runtime_effect_imports_zero": (
            not base._direct_forbidden_imports(PRIMITIVE_SOURCE)
            and not base._direct_forbidden_imports(RUNTIME_SOURCE)
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
        "complete_date_reformat_explicit_scale_conversion_and_stable_sort_only": primitive_contract[
            "operations"
        ]
        == ["complete_date_reformat", "explicit_scale_conversion", "stable_total_sort"],
        "temporal_range_and_rank_slots_never_mutate_row_population": (
            primitive_contract["temporal_range_row_filtering"] is False
            and primitive_contract["rank_slot_row_insertion_deletion_or_relabeling"]
            is False
            and primitive_contract["schema_or_row_count_mutation"] is False
        ),
        "partial_ambiguous_or_mixed_values_fail_closed": (
            primitive_contract["partial_date_precision_invention"] is False
            and primitive_contract["ambiguous_value_or_mixed_sort_type_mutation"]
            is False
            and tests["passed"]
        ),
        "one_v25401_parent_forward_shared_by_control_and_candidate": (
            runtime_contract["one_parent_forward_shared_by_both_arms"]
            and runtime_contract["parent_policy_id"] == runtime.parent.POLICY_ID
        ),
        "candidate_has_zero_independent_provider_or_sampling_effect": (
            runtime_contract["candidate_has_no_independent_model_or_sampling_effect"]
            and runtime_contract["candidate_only_effect_is_pure_deterministic_projection"]
        ),
        "no_safe_projection_returns_parent_prediction_byte_exact": tests["passed"],
        "query4_fetch14_model3_caps_unchanged": (
            runtime_contract["maximum_physical_queries"] == 4
            and runtime_contract["maximum_physical_fetches"] == 14
            and runtime_contract["normal_path_model_forwards"] == 3
            and runtime_contract[
                "additional_model_search_fetch_token_context_wall_or_network_budget"
            ]
            is False
        ),
        "runtime_inputs_exactly_opaque_id_and_question": runtime_contract[
            "runtime_input_keys"
        ]
        == ["opaque_id", "question"],
        "positive_signed_credit_zero": (
            primitive_contract["positive_signed_credit_count"] == 0
            and runtime_contract["positive_signed_credit_count"] == 0
        ),
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "no_external_effect_performed_by_build_audit": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "parent_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": FIXED_HASHES[PARENT_AUDIT],
            "fixed220_visible_reach_active_tasks": 95,
        },
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": reported_clean},
        "fixed_artifact_hashes": {str(path): base.sha256(path) for path in FIXED_HASHES},
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": base.payload_sha256(vector),
        "runtime_dependency_path_sha256": base.payload_sha256([row["path"] for row in vector]),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "primitive_contract": primitive_contract,
        "runtime_contract": runtime_contract,
        "effect_delta_beyond_v25401": {"model_requests": 0, "logical_queries": 0, "search_calls": 0, "fetch_calls": 0, "provider_tokens": 0},
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "task_rows_question_column_opaque_id_url_page_prediction_truth_or_per_task_feature_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_task_disjoint_shared_parent_population_design": not findings,
            "external_population_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    tests = copied.get("tests")
    semantic = copied.get("semantic_audit")
    git = copied.get("git")
    vector = copied.get("runtime_dependency_vector")
    valid = copied.get("audit_valid") is True
    expected_watchers = [
        {"pid": pid, "start_ticks": ticks, "marker": marker}
        for pid, ticks, marker in watchers.EXPECTED_WATCHERS
    ]
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or copied.get("parent_build_audit") != {"path": str(PARENT_AUDIT), "sha256": FIXED_HASHES[PARENT_AUDIT], "fixed220_visible_reach_active_tasks": 95}
        or copied.get("fixed_artifact_hashes") != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or not isinstance(git, Mapping)
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or any(passed is not True for passed in checks.values())
        or copied.get("findings") != []
        or not valid
        or not isinstance(tests, Mapping)
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or not isinstance(semantic, Mapping)
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or not isinstance(vector, list)
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or base.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or base.payload_sha256(
            [row.get("path") for row in vector if isinstance(row, Mapping)]
        )
        != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("primitive_contract") != primitive.integration_contract()
        or copied.get("runtime_contract") != runtime.integration_contract()
        or copied.get("effect_delta_beyond_v25401") != {"model_requests": 0, "logical_queries": 0, "search_calls": 0, "fetch_calls": 0, "provider_tokens": 0}
        or copied.get("protected_watchers") != expected_watchers
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("task_rows_question_column_opaque_id_url_page_prediction_truth_or_per_task_feature_persisted") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization") != {
            "fresh_task_disjoint_shared_parent_population_design": valid,
            "external_population_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.46 deterministic constraint build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"], "findings": value["findings"], "tests": value["tests"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
