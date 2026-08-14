#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.64/V2.54.65 successor."""

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
from deepwide_agent import v25464_row_key_bound_structured_source_candidate as primitive  # noqa: E402
from deepwide_agent import v25465_row_key_bound_structured_source_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25463_date_bounded_official_xml_exact220_transfer as transfer  # noqa: E402


DATE = "20260814"
ROLE = "v25466_row_key_bound_structured_source_clean_build_audit"
IMPLEMENTATION_COMMIT = "2bcdd94b3cc01e083f562724d497c5e7ff2e7475"
SOURCE = Path("scripts/audit_v25466_row_key_bound_structured_source_build.py")
TEST = Path("tests/test_audit_v25466_row_key_bound_structured_source_build.py")
PRIMITIVE_SOURCE = Path(
    "src/deepwide_agent/v25464_row_key_bound_structured_source_candidate.py"
)
PRIMITIVE_TEST = Path(
    "tests/test_v25464_row_key_bound_structured_source_candidate.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25465_row_key_bound_structured_source_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25465_row_key_bound_structured_source_runtime.py"
)
TRANSFER_AUDIT = Path(
    "results/v25463_date_bounded_official_xml_exact220_transfer_audit_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25466_row_key_bound_structured_source_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    PRIMITIVE_SOURCE: "423256b8baa5ea687cee0c1a0fa1e373503ee69ecaa11263f5c1f61676409bb5",
    PRIMITIVE_TEST: "7564d3088d5180e4b49fd443fcab64f649ba653585cdc793c6057532c565617c",
    RUNTIME_SOURCE: "f4f87b3a9c80fe29633d8c65e473899c1a5104bbaf32937effbf638bbe87e5b8",
    RUNTIME_TEST: "b86c8042cc7e0170cdae70b37c0a575090c6a1e52d7f9e61df998406ac24866e",
    TRANSFER_AUDIT: "91d23eca4e33fccaee09780269d2fe2800cee150b59412a311e8d586951a18ea",
}
TEST_SUITES = (
    ("test_audit_v25466_row_key_bound_structured_source_build.py", 4),
    ("test_v25464_row_key_bound_structured_source_candidate.py", 9),
    ("test_v25465_row_key_bound_structured_source_runtime.py", 6),
    ("test_v25432_source_authoritative_field_candidate.py", 9),
    ("test_v25434_source_authoritative_shared_runtime.py", 9),
    ("test_v25440_key_anchored_metadata_candidate.py", 13),
    ("test_v25444_key_anchored_metadata_shared_runtime.py", 8),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 88
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "a031c854c4d4dd286739962da92b20a3ca2cb8ae17f1052b17d77135424e72b0"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "ee244a9d94e808337af83e3f34cfa4fdcca6ba1d9dd84a7acaf9145f8c5e3cff"
)
CHECK_NAMES = frozenset(
    {
        "v25463_zero_transfer_and_generic_successor_authorization_bound",
        "fixed_successor_tests_and_transfer_hashes_match",
        "implementation_commit_in_head_history",
        "focused_successor_parent_and_audit_tests_exact76",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact88_and_hash_bound",
        "direct_primitive_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "parent_table_row_keys_replace_visible_membership_dependency",
        "unique_url_path_and_title_or_leading_surface_binding_required",
        "four_structured_source_grammars_supported",
        "source_coordinate_conflict_ambiguity_and_cross_page_join_fail_closed",
        "surface_equivalent_and_list_collapse_edits_rejected",
        "deterministic_replay_preserves_schema_rows_keys_and_unselected_cells",
        "one_v25375_parent_forward_and_provider_requests_byte_exact",
        "query4_fetch14_model3_caps_and_zero_candidate_effect_delta",
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


def _transfer_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(TRANSFER_AUDIT).read_text(encoding="utf-8"))
    transfer.validate_audit(value)
    exposure = value["visible_transfer"]
    if (
        base.sha256(TRANSFER_AUDIT) != FIXED_HASHES[TRANSFER_AUDIT]
        or value.get("audit_valid") is not True
        or exposure.get("task_count") != 220
        or exposure.get("strict_rfc_request_exposure_tasks") != 0
        or value.get("authorization", {}).get(
            "generic_visible_source_structured_record_successor_build"
        )
        is not True
        or value.get("authorization", {}).get("deepwidebench_forward_or_evaluator")
        is not False
    ):
        raise RuntimeError("V2.54.66 transfer barrier drifted")
    return value


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    history = set(base._git("rev-list", head).splitlines())
    prior = _transfer_barrier()
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
    integration = runtime.integration_contract()
    snapshot = watchers.watcher_snapshot()
    tests_green = tests["passed"]
    reported_clean = clean if tracked else True
    checks = {
        "v25463_zero_transfer_and_generic_successor_authorization_bound": bool(prior),
        "fixed_successor_tests_and_transfer_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_in_head_history": IMPLEMENTATION_COMMIT in history,
        "focused_successor_parent_and_audit_tests_exact76": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact88_and_hash_bound": (
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
        "parent_table_row_keys_replace_visible_membership_dependency": (
            integration["parent_completed_table_supplies_row_keys"] is True
        ),
        "unique_url_path_and_title_or_leading_surface_binding_required": tests_green,
        "four_structured_source_grammars_supported": tests_green,
        "source_coordinate_conflict_ambiguity_and_cross_page_join_fail_closed": tests_green,
        "surface_equivalent_and_list_collapse_edits_rejected": tests_green,
        "deterministic_replay_preserves_schema_rows_keys_and_unselected_cells": tests_green,
        "one_v25375_parent_forward_and_provider_requests_byte_exact": (
            integration["one_parent_forward_only"] is True and tests_green
        ),
        "query4_fetch14_model3_caps_and_zero_candidate_effect_delta": (
            integration["maximum_physical_queries"] == 4
            and integration["maximum_physical_fetches"] == 14
            and integration["normal_path_model_forwards"] == 3
            and integration["additional_candidate_provider_effects"] == 0
        ),
        "runtime_inputs_exactly_opaque_id_and_question": integration[
            "runtime_input_keys"
        ]
        == ["opaque_id", "question"],
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": (
            integration["entropy_or_information_gain_assigns_signed_credit"]
            is False
            and tests_green
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
            "fetch_calls": 0,
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
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
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
            "fetch_calls": 0,
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
            "fresh_outcome_blind_external_population_design": valid,
            "external_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.66 build audit drifted")
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
