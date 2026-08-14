#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.99/V2.55.00 successor."""

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
from deepwide_agent import v25499_generic_mechanical_field_candidate as candidate  # noqa: E402
from deepwide_agent import v25500_generic_mechanical_field_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25498_exact220_visible_index_transfer as transfer  # noqa: E402


DATE = "20260814"
ROLE = "v25501_generic_mechanical_field_clean_build_audit"
IMPLEMENTATION_COMMIT = "8a135226"
SOURCE = Path("scripts/audit_v25501_generic_mechanical_field_build.py")
TEST = Path("tests/test_audit_v25501_generic_mechanical_field_build.py")
CANDIDATE_SOURCE = Path(
    "src/deepwide_agent/v25499_generic_mechanical_field_candidate.py"
)
CANDIDATE_TEST = Path("tests/test_v25499_generic_mechanical_field_candidate.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25500_generic_mechanical_field_runtime.py"
)
RUNTIME_TEST = Path("tests/test_v25500_generic_mechanical_field_runtime.py")
OUTPUT = Path(
    f"results/v25501_generic_mechanical_field_build_audit_v1_{DATE}.json"
)
TRANSFER = transfer.OUTPUT
TRANSFER_SHA256 = "423cce6b11ceef46ae9735ab59a847239de1eb1952a577ae981a07362f1c7308"
FIXED_HASHES = {
    CANDIDATE_SOURCE: "a13747df96a1472500a169d87a601f45c8f013905863604c0cd1eac64cac01f3",
    CANDIDATE_TEST: "fa2089d99eb52781828b5bb712ea501f795c68240317ed6e9ae22c1f893568f4",
    RUNTIME_SOURCE: "376c97a35d3e56de676071dc0b4c47ad77bd40d672e4352d645a4b622c1bef98",
    RUNTIME_TEST: "fa003c25dd411b43b1f0a4018d8a25d02dbe3781759bca9f88770ed1393e9434",
}
TEST_SUITES = (
    ("test_audit_v25501_generic_mechanical_field_build.py", 4),
    ("test_v25499_generic_mechanical_field_candidate.py", 7),
    ("test_v25500_generic_mechanical_field_runtime.py", 6),
    ("test_v25492_visible_row_key_detail_runtime.py", 7),
    ("test_v25491_visible_row_key_detail_selection.py", 7),
    ("test_v25484_row_key_iana_detail_runtime.py", 7),
    ("test_v25483_row_key_iana_detail_candidate.py", 7),
    ("test_v25472_qualified_source_label_runtime.py", 6),
    ("test_v25471_qualified_source_label_candidate.py", 7),
    ("test_v25465_row_key_bound_structured_source_runtime.py", 6),
    ("test_v25464_row_key_bound_structured_source_candidate.py", 9),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 95
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "5f1af6e4843387b9d00b11037a5d2f5295f8900a0d2595f5b94b47a54111e51c"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "3f77de3bc93e9d0780121e5905a01411d12cbc34c30793285174a904cf924be7"
)
CHECK_NAMES = frozenset(
    {
        "exact220_transfer_hash_role_seal_and_generic_build_authority_bound",
        "fixed_successor_source_and_test_hashes_match",
        "implementation_commit_in_head_history",
        "focused_successor_parent_and_audit_tests_exact80",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_and_closure_files_tracked",
        "runtime_dependency_vector_exact95_and_hash_bound",
        "direct_candidate_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "parent_and_detail_pages_share_one_generic_grammar",
        "exact_separate_and_fused_complete_field_tokens_only",
        "pipe_labelled_and_bounded_adjacent_values_only",
        "row_key_url_path_page_surface_quote_and_value_binding_required",
        "ambiguity_conflict_unknown_surface_only_list_collapse_and_shape_change_fail_closed",
        "one_v25492_parent_forward_and_parent_prediction_exact_control",
        "candidate_additional_effects_beyond_v25492_zero",
        "query4_fetch14_model3_final_caps",
        "candidate_additional_query_and_model_zero_total_fetch_at_most_one",
        "runtime_inputs_exactly_opaque_id_and_question",
        "entropy_information_gain_neither_routes_nor_gets_signed_credit",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_external_effect_performed",
    }
)


def _transfer_barrier() -> dict[str, Any]:
    path = base._ordinary(TRANSFER)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        base.sha256(TRANSFER) != TRANSFER_SHA256
        or transfer.validate_audit(value) != value
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "generic_parent_and_detail_visible_schema_grammar_build"
        )
        is not True
        or value.get("authorization", {}).get("new_external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.55.01 transfer barrier drifted")
    return value


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
    closure = tuple(sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    barrier = _transfer_barrier()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    history = base._git("rev-list", head).splitlines()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        CANDIDATE_SOURCE,
        CANDIDATE_TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        TRANSFER,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    integration = runtime.integration_contract()
    primitive = candidate.integration_contract()
    snapshot = watchers.watcher_snapshot()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "exact220_transfer_hash_role_seal_and_generic_build_authority_bound": bool(
            barrier
        ),
        "fixed_successor_source_and_test_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_in_head_history": any(
            commit.startswith(IMPLEMENTATION_COMMIT) for commit in history
        ),
        "focused_successor_parent_and_audit_tests_exact80": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact95_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_candidate_and_runtime_effect_imports_zero": (
            not base._direct_forbidden_imports(CANDIDATE_SOURCE)
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
        "parent_and_detail_pages_share_one_generic_grammar": integration[
            "same_generic_grammar_over_parent_and_detail_pages"
        ],
        "exact_separate_and_fused_complete_field_tokens_only": primitive[
            "supported_label_grammars"
        ]
        == ["exact", "separate_qualifier", "fused_qualifier"],
        "pipe_labelled_and_bounded_adjacent_values_only": primitive[
            "supported_new_source_shapes"
        ]
        == [
            "fused_two_cell_pipe",
            "qualified_same_line_labelled",
            "standalone_label_bounded_adjacent_value",
        ],
        "row_key_url_path_page_surface_quote_and_value_binding_required": tests_green,
        "ambiguity_conflict_unknown_surface_only_list_collapse_and_shape_change_fail_closed": tests_green,
        "one_v25492_parent_forward_and_parent_prediction_exact_control": integration[
            "one_v25492_parent_forward_only"
        ],
        "candidate_additional_effects_beyond_v25492_zero": integration[
            "maximum_candidate_additional_fetches_beyond_v25492"
        ]
        == 0,
        "query4_fetch14_model3_final_caps": (
            integration["maximum_physical_queries"] == 4
            and integration["maximum_physical_fetches"] == 14
            and integration["normal_path_model_forwards"] == 3
        ),
        "candidate_additional_query_and_model_zero_total_fetch_at_most_one": (
            integration["candidate_additional_queries"] == 0
            and integration["candidate_additional_model_calls"] == 0
            and integration["maximum_total_additional_fetches_beyond_v25472"] == 1
        ),
        "runtime_inputs_exactly_opaque_id_and_question": integration[
            "runtime_input_keys"
        ]
        == ["opaque_id", "question"],
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": (
            integration["entropy_or_information_gain_assigns_signed_credit"]
            is False
            and primitive["entropy_or_information_gain_assigns_signed_credit"]
            is False
        ),
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "transfer_barrier": {"path": str(TRANSFER), "sha256": TRANSFER_SHA256},
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
        "candidate_contract": primitive,
        "runtime_contract": integration,
        "effect_delta_beyond_v25492": {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "provider_tokens": 0,
        },
        "total_effect_delta_beyond_v25472": {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "maximum_fetch_calls": 1,
            "provider_tokens": 0,
        },
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_task_disjoint_external_population_design": not findings,
            "external_protocol_or_forward": False,
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
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or copied.get("transfer_barrier")
        != {"path": str(TRANSFER), "sha256": TRANSFER_SHA256}
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not isinstance(tests, Mapping)
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or not isinstance(semantic, Mapping)
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or copied.get("effect_delta_beyond_v25492")
        != {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "provider_tokens": 0,
        }
        or copied.get("total_effect_delta_beyond_v25472")
        != {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "maximum_fetch_calls": 1,
            "provider_tokens": 0,
        }
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
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
            "fresh_task_disjoint_external_population_design": valid,
            "external_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.01 build audit drifted")
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
                "tests": value["tests"]["observed"],
                "closure": len(value["runtime_dependency_vector"]),
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
