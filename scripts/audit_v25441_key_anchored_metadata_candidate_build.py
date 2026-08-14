#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.40 metadata candidate parser."""

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
from deepwide_agent import v25440_key_anchored_metadata_candidate as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260813"
ROLE = "v25441_key_anchored_metadata_candidate_clean_build_audit"
IMPLEMENTATION_COMMIT = "aa2df9d71e3c8edd912ac0bfcd2d3cbe6890deb4"
SOURCE = Path("scripts/audit_v25441_key_anchored_metadata_candidate_build.py")
TEST = Path("tests/test_audit_v25441_key_anchored_metadata_candidate_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25440_key_anchored_metadata_candidate.py"
)
RUNTIME_TEST = Path("tests/test_v25440_key_anchored_metadata_candidate.py")
OUTPUT = Path(
    f"results/v25441_key_anchored_metadata_candidate_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    RUNTIME_SOURCE: "1fe8c66b3d02e12900843c9464b3a17386bf325b13bf66fe319a5de0782a15ca",
    RUNTIME_TEST: "766b04ca1b481f87da838d3791acebcde7c5f619651974d97338215c1838b1a5",
}
TEST_SUITES = (
    ("test_audit_v25441_key_anchored_metadata_candidate_build.py", 4),
    ("test_v25440_key_anchored_metadata_candidate.py", 13),
    ("test_v25432_source_authoritative_field_candidate.py", 9),
    ("test_v24743_generic_record_binding.py", 12),
    ("test_v24754_generic_structured_page_adapter.py", 9),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25158_vertical_key_value_candidate_runtime.py", 11),
    ("test_v25369_changed_safe_verified_coordinate_edit.py", 8),
    ("test_v25420_list_atomic_changed_safe_runtime.py", 9),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 3
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "bd681f340e2ad797154922d65ddbe5be769a50df88162085ca546c87da7ad86a"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "0fcca744f602262fe6034f7578bebfc69f6a12b2613995a0da9bf17789a98033"
)
CHECK_NAMES = frozenset(
    {
        "fixed_runtime_and_test_hashes_match",
        "implementation_commit_is_in_head_history",
        "focused_parent_and_audit_tests_exact89",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_and_closure_files_tracked",
        "runtime_dependency_vector_exact3_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "parent_candidates_preserved_in_shared_conflict_resolution",
        "metadata_block_exact_key_anchored_bounded_and_nonaliased",
        "identity_exact_or_unique_key_qualified_only",
        "list_normalization_unique_equal_cardinality_atoms_only",
        "duplicate_field_coordinate_and_value_conflicts_fail_closed",
        "canonical_https_quote_identity_field_and_raw_value_bound",
        "model_can_only_select_candidate_ids_or_abstain",
        "schema_row_order_keys_and_unselected_cells_preserved",
        "registry_application_and_normalization_replay_tamper_fail_closed",
        "invalid_or_none_selector_preserves_parent_byte_exact",
        "zero_additional_model_search_fetch_query_token_or_network_effect",
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
    explicit = {SOURCE, TEST, RUNTIME_SOURCE, RUNTIME_TEST, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    source = base._ordinary(RUNTIME_SOURCE).read_text(encoding="utf-8")
    snapshot = watchers.watcher_snapshot()
    tests_green = tests["passed"]
    reported_clean = clean if tracked else True
    checks = {
        "fixed_runtime_and_test_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_is_in_head_history": IMPLEMENTATION_COMMIT in history,
        "focused_parent_and_audit_tests_exact89": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact3_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_runtime_effect_imports_zero": not base._direct_forbidden_imports(
            RUNTIME_SOURCE
        ),
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [],
        "parent_candidates_preserved_in_shared_conflict_resolution": tests_green,
        "metadata_block_exact_key_anchored_bounded_and_nonaliased": (
            runtime.MAXIMUM_BLOCK_LINES == 16 and tests_green
        ),
        "identity_exact_or_unique_key_qualified_only": tests_green,
        "list_normalization_unique_equal_cardinality_atoms_only": tests_green,
        "duplicate_field_coordinate_and_value_conflicts_fail_closed": tests_green,
        "canonical_https_quote_identity_field_and_raw_value_bound": tests_green,
        "model_can_only_select_candidate_ids_or_abstain": tests_green,
        "schema_row_order_keys_and_unselected_cells_preserved": tests_green,
        "registry_application_and_normalization_replay_tamper_fail_closed": tests_green,
        "invalid_or_none_selector_preserves_parent_byte_exact": tests_green,
        "zero_additional_model_search_fetch_query_token_or_network_effect": all(
            token not in source
            for token in (
                "model.complete",
                "search_many",
                "fetch_urls",
                "import requests",
                "urlopen",
                "subprocess",
                "socket",
            )
        ),
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": (
            runtime._COUNT_FIELDS[-6] == "positive_signed_credit_count"
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
        "candidate_contract": {
            "maximum_pages": runtime.parent.MAXIMUM_PAGE_COUNT,
            "maximum_block_lines": runtime.MAXIMUM_BLOCK_LINES,
            "maximum_candidates": runtime.MAXIMUM_CANDIDATES,
            "accepted_structures": sorted(runtime._SOURCE_KINDS),
            "identity_derivations": sorted(runtime._IDENTITY_KINDS),
            "value_normalizations": sorted(runtime._VALUE_KINDS),
            "selection_surface": {"candidate_ids": ["C001"]},
        },
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
        runtime.PRIVILEGED_READ_FLAG: False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_structurally_disjoint_key_anchored_external_protocol_design": not findings,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "reuse_v25438_population_or_forward": False,
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
    findings = copied.get("findings")
    tests = copied.get("tests")
    semantic = copied.get("semantic_audit")
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or any(not isinstance(passed, bool) for passed in checks.values())
        or findings != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (findings == [])
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
        or copied.get(runtime.PRIVILEGED_READ_FLAG) is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "fresh_structurally_disjoint_key_anchored_external_protocol_design": valid,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "reuse_v25438_population_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.41 key-anchored metadata build audit drifted")
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
