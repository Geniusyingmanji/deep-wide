#!/usr/bin/env python3
"""Clean pushed build audit for the V2.55.41/42 constraint successor."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25110_exact_visible_schema as exact_schema  # noqa: E402
from deepwide_agent import v24675_expanded_visible_schema as expanded_schema  # noqa: E402
from deepwide_agent import v25406_grounded_membership_exact220_contract as exact220  # noqa: E402
from deepwide_agent import v25541_visible_output_constraint_contract as primitive  # noqa: E402
from deepwide_agent import v25542_visible_constraint_synthesis_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260814"
ROLE = "v25543_visible_constraint_synthesis_clean_build_audit"
IMPLEMENTATION_COMMIT = "edfeb297c70b676bc093b5013cad5dc3e3595425"
SOURCE = Path("scripts/audit_v25543_visible_constraint_synthesis_build.py")
TEST = Path("tests/test_audit_v25543_visible_constraint_synthesis_build.py")
PRIMITIVE_SOURCE = Path(
    "src/deepwide_agent/v25541_visible_output_constraint_contract.py"
)
PRIMITIVE_TEST = Path(
    "tests/test_v25541_visible_output_constraint_contract.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25542_visible_constraint_synthesis_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25542_visible_constraint_synthesis_runtime.py"
)
TRANSFER_AUDIT = Path(
    "results/v25540_visible_constraint_transfer_reach_audit_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25543_visible_constraint_synthesis_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    PRIMITIVE_SOURCE: "9c9c1d785a29c26c6e40f3ee6a11204cbdc968637088aeb816a27df752029abf",
    PRIMITIVE_TEST: "bfcb9ce5ab4411aa87870c64e6386768d7489c86cb2abc6cf7879be3d0c1e1d8",
    RUNTIME_SOURCE: "7a1c74b7494dedf00057643ff4a5ab090343de3f9ce35bf4e4ae5565b263ba1f",
    RUNTIME_TEST: "35408b4237e73b8ddd4712826716069b4e38b3e4eb6074f79d2792bc0d81324b",
    TRANSFER_AUDIT: "7df97cf8aa3a5f92a67fb70ad7f5dfe85915868c5c35dc6bdc0a74aa07453159",
}
TEST_SUITES = (
    ("test_audit_v25543_visible_constraint_synthesis_build.py", 4),
    ("test_v25542_visible_constraint_synthesis_runtime.py", 6),
    ("test_v25541_visible_output_constraint_contract.py", 7),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25395_visible_membership_synthesis_runtime.py", 7),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25383_joint_synthesis_changed_safe_runtime.py", 8),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 94
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "b92a402bcfe2293799cc25580bcf02cb5f5ae5cb744910ac55cd708ca395134b"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "6cce78d10f166772732871a44b321e352d74d862df4e8aad84191d23c852a805"
)
EXPECTED_VISIBLE_REACH = {
    "task_count": 220,
    "active_tasks": 95,
    "active_with_explicit_schema_tasks": 94,
    "temporal_year_range_tasks": 43,
    "date_format_tasks": 46,
    "numeric_scale_tasks": 19,
    "rank_slots_tasks": 6,
    "explicit_order_tasks": 3,
    "active_family_count_histogram": {"0": 125, "1": 74, "2": 20, "3": 1},
}
CHECK_NAMES = frozenset(
    {
        "v25540_transfer_audit_hash_role_and_build_authority_exact",
        "implementation_sources_tests_and_transfer_hash_exact",
        "implementation_commit_in_head_history",
        "focused_successor_and_parent_chain_tests_exact66",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_transfer_and_closure_files_tracked",
        "runtime_dependency_vector_exact94_and_hash_bound",
        "direct_primitive_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "conservative_visible_constraint_reach_exact95_of_220",
        "all_five_constraint_families_have_nonzero_fixed220_reach",
        "no_active_constraint_parent_third_call_byte_exact",
        "one_existing_third_call_and_parent_pipeline_replayed",
        "content_free_nonmutating_observer_and_zero_signed_credit",
        "query4_fetch14_model3_caps_unchanged",
        "runtime_inputs_exactly_opaque_id_and_question",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_external_effect_performed_by_build_audit",
    }
)


def _transfer_barrier() -> dict[str, Any]:
    value = json.loads(
        base._ordinary(TRANSFER_AUDIT).read_text(encoding="utf-8")
    )
    if (
        base.sha256(TRANSFER_AUDIT) != FIXED_HASHES[TRANSFER_AUDIT]
        or value.get("role") != "v25540_visible_constraint_transfer_reach_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "generic_visible_constraint_successor_build"
        )
        is not True
        or value.get("authorization", {}).get(
            "new_external_population_protocol_or_forward"
        )
        is not False
        or value.get("authorization", {}).get(
            "deepwidebench_forward_or_evaluator"
        )
        is not False
        or value.get("audit_payload_sha256")
        != exact220.payload_sha256(
            {
                key: item
                for key, item in value.items()
                if key != "audit_payload_sha256"
            }
        )
    ):
        raise RuntimeError("V2.55.43 transfer barrier drifted")
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
    closure = tuple(
        sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str)
    )
    vector = [
        {"path": str(path), "sha256": base.sha256(path)} for path in closure
    ]
    return closure, vector


def _visible_reach() -> dict[str, Any]:
    vector = exact220.task_vector(ROOT)
    family_counts: Counter[str] = Counter()
    histogram: Counter[int] = Counter()
    active = active_with_schema = 0
    for task in vector:
        question = task["question"]
        exact = exact_schema.extract_exact_visible_columns(question)
        expanded = expanded_schema.extract_expanded_visible_columns(question)
        columns = exact or expanded or ["Result", "Value"]
        contract = primitive.build_contract(question, columns)
        count = int(contract["active_family_count"])
        active += int(count > 0)
        active_with_schema += int(count > 0 and bool(exact or expanded))
        histogram[count] += 1
        for family in contract["active_families"]:
            family_counts[family] += 1
    return {
        "task_count": len(vector),
        "opaque_id_vector_sha256": exact220.payload_sha256(
            [task["opaque_id"] for task in vector]
        ),
        "visible_question_vector_sha256": exact220.payload_sha256(
            [task["question"] for task in vector]
        ),
        "active_tasks": active,
        "active_with_explicit_schema_tasks": active_with_schema,
        "temporal_year_range_tasks": family_counts["temporal_year_range"],
        "date_format_tasks": family_counts["date_format"],
        "numeric_scale_tasks": family_counts["numeric_scale"],
        "rank_slots_tasks": family_counts["rank_slots"],
        "explicit_order_tasks": family_counts["explicit_order"],
        "active_family_count_histogram": {
            str(key): histogram[key] for key in sorted(histogram)
        },
        "question_column_opaque_id_or_per_task_feature_persisted": False,
    }


def build_audit(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    transfer = _transfer_barrier()
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
        TRANSFER_AUDIT,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    primitive_contract = primitive.integration_contract()
    runtime_contract = runtime.integration_contract()
    reach = _visible_reach()
    snapshot = watchers.watcher_snapshot()
    tests_green = tests["passed"]
    reported_clean = clean if tracked else True
    checks = {
        "v25540_transfer_audit_hash_role_and_build_authority_exact": bool(
            transfer
        ),
        "implementation_sources_tests_and_transfer_hash_exact": all(
            base.sha256(path) == expected
            for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_in_head_history": IMPLEMENTATION_COMMIT in history,
        "focused_successor_and_parent_chain_tests_exact66": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_transfer_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact94_and_hash_bound": (
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
        "conservative_visible_constraint_reach_exact95_of_220": all(
            reach.get(name) == expected
            for name, expected in EXPECTED_VISIBLE_REACH.items()
        ),
        "all_five_constraint_families_have_nonzero_fixed220_reach": all(
            reach[name] > 0
            for name in (
                "temporal_year_range_tasks",
                "date_format_tasks",
                "numeric_scale_tasks",
                "rank_slots_tasks",
                "explicit_order_tasks",
            )
        ),
        "no_active_constraint_parent_third_call_byte_exact": (
            primitive_contract["no_active_constraint_returns_empty_suffix"]
            and runtime_contract["no_active_constraint_parent_prompt_byte_exact"]
            and tests_green
        ),
        "one_existing_third_call_and_parent_pipeline_replayed": (
            runtime_contract["one_existing_third_model_call_receives_constraint"]
            and runtime_contract[
                "parent_normalizer_verifier_membership_and_editor_replayed"
            ]
            and runtime_contract["post_return_observer_changes_prediction"]
            is False
        ),
        "content_free_nonmutating_observer_and_zero_signed_credit": (
            primitive_contract[
                "prediction_observer_is_content_free_and_non_mutating"
            ]
            and primitive_contract["positive_signed_credit_count"] == 0
            and runtime_contract["positive_signed_credit_count"] == 0
        ),
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
        "transfer_barrier": {
            "path": str(TRANSFER_AUDIT),
            "sha256": FIXED_HASHES[TRANSFER_AUDIT],
            "generic_visible_constraint_successor_build": True,
        },
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": reported_clean,
        },
        "fixed_artifact_hashes": {
            str(path): base.sha256(path) for path in FIXED_HASHES
        },
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": base.payload_sha256(vector),
        "runtime_dependency_path_sha256": base.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "fixed220_visible_reach": reach,
        "primitive_contract": primitive_contract,
        "runtime_contract": runtime_contract,
        "effect_delta_beyond_v25401": {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "provider_tokens": 0,
        },
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
    reach = copied.get("fixed220_visible_reach")
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or copied.get("transfer_barrier")
        != {
            "path": str(TRANSFER_AUDIT),
            "sha256": FIXED_HASHES[TRANSFER_AUDIT],
            "generic_visible_constraint_successor_build": True,
        }
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
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
        or not isinstance(reach, Mapping)
        or any(
            reach.get(name) != expected
            for name, expected in EXPECTED_VISIBLE_REACH.items()
        )
        or copied.get("effect_delta_beyond_v25401")
        != {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "provider_tokens": 0,
        }
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get(
            "task_rows_question_column_opaque_id_url_page_prediction_truth_or_per_task_feature_persisted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_task_disjoint_shared_parent_population_design": valid,
            "external_population_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.43 visible constraint build audit drifted")
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
    if value["findings"]:
        raise RuntimeError(value["findings"])
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "tests": value["tests"],
                "fixed220_visible_reach": value["fixed220_visible_reach"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
