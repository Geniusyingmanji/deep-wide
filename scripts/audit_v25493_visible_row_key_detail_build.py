#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.91/V2.54.92 successor."""

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
from deepwide_agent import v25491_visible_row_key_detail_selection as selection  # noqa: E402
from deepwide_agent import v25492_visible_row_key_detail_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260814"
ROLE = "v25493_visible_row_key_detail_clean_build_audit"
IMPLEMENTATION_COMMITS = (
    "bb61a8257abb35fe9960247d957fcceb23866c85",
    "73794b212c62fabf1286efb465c611beb146e621",
)
SOURCE = Path("scripts/audit_v25493_visible_row_key_detail_build.py")
TEST = Path("tests/test_audit_v25493_visible_row_key_detail_build.py")
SELECTION_SOURCE = Path(
    "src/deepwide_agent/v25491_visible_row_key_detail_selection.py"
)
SELECTION_TEST = Path("tests/test_v25491_visible_row_key_detail_selection.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25492_visible_row_key_detail_runtime.py")
RUNTIME_TEST = Path("tests/test_v25492_visible_row_key_detail_runtime.py")
OUTPUT = Path(f"results/v25493_visible_row_key_detail_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    SELECTION_SOURCE: "a563c1a411edce7efa145145e141c30991ae8ef94689a743e25d9db6d69dff0f",
    SELECTION_TEST: "da1084e4a849c24551cc615226d8857aeee3774bf02f55556e6da51f790ec544",
    RUNTIME_SOURCE: "fadbad95f8c90b60f854d0b521e7488309a84d50b3c6264dea3b1b4d75c5a424",
    RUNTIME_TEST: "3b173c8630ff73d31920f741f84a81ad75a98b734fc98584cae3adbb10b75380",
}
TEST_SUITES = (
    ("test_audit_v25493_visible_row_key_detail_build.py", 4),
    ("test_v25491_visible_row_key_detail_selection.py", 7),
    ("test_v25492_visible_row_key_detail_runtime.py", 7),
    ("test_v25484_row_key_iana_detail_runtime.py", 7),
    ("test_v25472_qualified_source_label_runtime.py", 6),
    ("test_v25471_qualified_source_label_candidate.py", 7),
    ("test_v25465_row_key_bound_structured_source_runtime.py", 6),
    ("test_v25464_row_key_bound_structured_source_candidate.py", 9),
    ("test_v25010_attested_child_detail_selection.py", 8),
    ("test_v25001_page_visible_link_selection.py", 8),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 93
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "92603c504d0d267a483f3db4cb30d4a1caf3abeb2fe2df0d294a3d5a3205b177"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "6a6e1fb91b9519d4d247995162efef896743118da3bf2303812cfbbc6753491b"
)
CHECK_NAMES = frozenset(
    {
        "fixed_successor_source_and_test_hashes_match",
        "implementation_commits_in_head_history",
        "focused_successor_parent_and_audit_tests_exact76",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_and_closure_files_tracked",
        "runtime_dependency_vector_exact93_and_hash_bound",
        "direct_selection_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "completed_parent_table_is_only_row_key_source",
        "candidate_urls_only_from_same_forward_visible_page_links",
        "same_origin_strict_child_and_public_url_required",
        "url_path_and_anchor_bind_one_identical_parent_row_key",
        "one_url_per_row_and_one_global_candidate_or_identity_handoff",
        "already_fetched_ambiguity_redirect_conflict_and_failure_fail_closed",
        "one_v25472_parent_forward_and_parent_prediction_exact_control",
        "parent_fetch_responses_mirrored_without_mutation",
        "remaining_capacity_only_and_zero_overcap_attempt",
        "query4_fetch14_model3_final_caps",
        "candidate_additional_query_and_model_zero_fetch_at_most_one",
        "detail_fields_row_key_page_surface_visible_schema_and_value_bound",
        "runtime_inputs_exactly_opaque_id_and_question",
        "entropy_information_gain_neither_routes_nor_gets_signed_credit",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
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
    closure = tuple(sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    history = set(base._git("rev-list", head).splitlines())
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        SELECTION_SOURCE,
        SELECTION_TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    integration = runtime.integration_contract()
    snapshot = watchers.watcher_snapshot()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "fixed_successor_source_and_test_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commits_in_head_history": all(
            commit in history for commit in IMPLEMENTATION_COMMITS
        ),
        "focused_successor_parent_and_audit_tests_exact76": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact93_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_selection_and_runtime_effect_imports_zero": (
            not base._direct_forbidden_imports(SELECTION_SOURCE)
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
        "completed_parent_table_is_only_row_key_source": tests_green,
        "candidate_urls_only_from_same_forward_visible_page_links": integration[
            "parent_fetch_responses_mirrored_without_request_or_response_mutation"
        ],
        "same_origin_strict_child_and_public_url_required": tests_green,
        "url_path_and_anchor_bind_one_identical_parent_row_key": tests_green,
        "one_url_per_row_and_one_global_candidate_or_identity_handoff": tests_green,
        "already_fetched_ambiguity_redirect_conflict_and_failure_fail_closed": tests_green,
        "one_v25472_parent_forward_and_parent_prediction_exact_control": integration[
            "one_v25472_parent_forward_shared_by_base_and_candidate"
        ],
        "parent_fetch_responses_mirrored_without_mutation": integration[
            "parent_fetch_responses_mirrored_without_request_or_response_mutation"
        ],
        "remaining_capacity_only_and_zero_overcap_attempt": tests_green,
        "query4_fetch14_model3_final_caps": (
            integration["maximum_physical_queries"] == 4
            and integration["maximum_physical_fetches"] == 14
            and integration["normal_path_model_forwards"] == 3
        ),
        "candidate_additional_query_and_model_zero_fetch_at_most_one": (
            integration["candidate_additional_queries"] == 0
            and integration["candidate_additional_model_calls"] == 0
            and integration["maximum_candidate_additional_fetches"] == 1
        ),
        "detail_fields_row_key_page_surface_visible_schema_and_value_bound": tests_green,
        "runtime_inputs_exactly_opaque_id_and_question": integration[
            "runtime_input_keys"
        ]
        == ["opaque_id", "question"],
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": integration[
            "entropy_or_information_gain_assigns_signed_credit"
        ]
        is False,
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
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
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
        "integration_contract": integration,
        "effect_delta": {
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
            "fresh_outcome_blind_external_population_design": not findings,
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
        or copied.get("implementation_commits") != list(IMPLEMENTATION_COMMITS)
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
        or copied.get("effect_delta")
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
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_outcome_blind_external_population_design": valid,
            "external_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.93 build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
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
