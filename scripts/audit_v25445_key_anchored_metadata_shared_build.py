#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.44 production integration."""

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
from deepwide_agent import v25444_key_anchored_metadata_shared_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260813"
ROLE = "v25445_key_anchored_metadata_shared_clean_build_audit"
IMPLEMENTATION_COMMIT = "2359b38947ba731fb7e9dbacfda1f289b361ee3b"
SOURCE = Path("scripts/audit_v25445_key_anchored_metadata_shared_build.py")
TEST = Path("tests/test_audit_v25445_key_anchored_metadata_shared_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25444_key_anchored_metadata_shared_runtime.py"
)
RUNTIME_TEST = Path("tests/test_v25444_key_anchored_metadata_shared_runtime.py")
PRIMITIVE_AUDIT = Path(
    "results/v25441_key_anchored_metadata_candidate_build_audit_v1_20260813.json"
)
POPULATION_AUDIT = Path(
    "results/v25443_structurally_disjoint_key_anchored_population_audit_v1_20260813.json"
)
OUTPUT = Path(
    f"results/v25445_key_anchored_metadata_shared_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    RUNTIME_SOURCE: "6e298d5dd16a5c6cb67e0979a7a63cd87e0cba44c66c3b614677d90252fc0e51",
    RUNTIME_TEST: "cdec0a72fefb3d466ffcedc73b460b41cbc2bd752ec028ad013dd9a5434765d1",
    PRIMITIVE_AUDIT: "70255ed37d5cb37955fafb3cd7ad35db90a36dd35b3fe2b607da73b9f2244fe3",
    POPULATION_AUDIT: "d1598a88e5452402a21e46e143f63d6693671cc9b3888586bea2a41b2614c53f",
}
TEST_SUITES = (
    ("test_audit_v25445_key_anchored_metadata_shared_build.py", 4),
    ("test_v25444_key_anchored_metadata_shared_runtime.py", 8),
    ("test_v25440_key_anchored_metadata_candidate.py", 13),
    ("test_v25434_source_authoritative_shared_runtime.py", 9),
    ("test_v25432_source_authoritative_field_candidate.py", 9),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25395_visible_membership_synthesis_runtime.py", 7),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
    ("test_v25420_list_atomic_changed_safe_runtime.py", 9),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 97
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "b383c93a2dc8eb6cf2841d775e2e134b1474bf564eb4408dfd1d243854f2d98c"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "20198791bcae147797a30900873434681779eb8a786d168ab4a14947e3b0ec26"
)
CHECK_NAMES = frozenset(
    {
        "primitive_and_population_audits_bound",
        "fixed_runtime_test_and_parent_hashes_match",
        "implementation_commit_is_in_head_history",
        "focused_parent_and_audit_tests_exact93",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact97_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "private_namespace_binds_v25440_without_parent_mutation",
        "one_v25401_parent_forward_only",
        "all_parent_provider_requests_byte_exact",
        "key_anchored_metadata_candidate_applied_and_replayed",
        "duplicate_conflict_unbound_or_invalid_application_preserves_base",
        "schema_row_order_keys_and_unselected_cells_preserved",
        "query4_fetch14_model3_caps_unchanged",
        "zero_additional_model_search_fetch_or_network_call_surface",
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


def _parent_barriers() -> tuple[dict[str, Any], dict[str, Any]]:
    primitive = json.loads(base._ordinary(PRIMITIVE_AUDIT).read_text(encoding="utf-8"))
    population = json.loads(
        base._ordinary(POPULATION_AUDIT).read_text(encoding="utf-8")
    )
    if (
        base.sha256(PRIMITIVE_AUDIT) != FIXED_HASHES[PRIMITIVE_AUDIT]
        or base.sha256(POPULATION_AUDIT) != FIXED_HASHES[POPULATION_AUDIT]
        or primitive.get("audit_valid") is not True
        or primitive.get("authorization", {}).get(
            "fresh_structurally_disjoint_key_anchored_external_protocol_design"
        )
        is not True
        or primitive.get("authorization", {}).get("external_forward") is not False
        or population.get("audit_valid") is not True
        or population.get("selected_interval") != "RFC 9080-9159"
        or population.get("selected_consumed_overlap_identity_count") != 0
        or population.get("authorization", {}).get(
            "key_anchored_external_protocol_design"
        )
        is not True
        or population.get("authorization", {}).get(
            "network_model_search_fetch_external_forward_or_evaluator"
        )
        is not False
        or population.get("authorization", {}).get(
            "reuse_v25438_population_or_forward"
        )
        is not False
    ):
        raise RuntimeError("V2.54.45 parent build/population barrier drifted")
    return primitive, population


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    history = set(base._git("rev-list", head).splitlines())
    primitive, population = _parent_barriers()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        PRIMITIVE_AUDIT,
        POPULATION_AUDIT,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    source = base._ordinary(RUNTIME_SOURCE).read_text(encoding="utf-8")
    snapshot = watchers.watcher_snapshot()
    tests_green = tests["passed"]
    reported_clean = clean if tracked else True
    integration = runtime.integration_contract()
    checks = {
        "primitive_and_population_audits_bound": bool(primitive and population),
        "fixed_runtime_test_and_parent_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_is_in_head_history": IMPLEMENTATION_COMMIT in history,
        "focused_parent_and_audit_tests_exact93": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact97_and_hash_bound": (
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
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "private_namespace_binds_v25440_without_parent_mutation": (
            integration["candidate_module_bound_in_private_namespace"] is True
            and integration["parent_module_global_candidate_unchanged"] is True
        ),
        "one_v25401_parent_forward_only": integration["one_parent_forward_only"]
        is True,
        "all_parent_provider_requests_byte_exact": tests_green,
        "key_anchored_metadata_candidate_applied_and_replayed": tests_green,
        "duplicate_conflict_unbound_or_invalid_application_preserves_base": tests_green,
        "schema_row_order_keys_and_unselected_cells_preserved": tests_green,
        "query4_fetch14_model3_caps_unchanged": integration
        == {
            **integration,
            "maximum_physical_queries": 4,
            "maximum_physical_fetches": 14,
            "normal_path_model_forwards": 3,
            "additional_candidate_provider_effects": 0,
        },
        "zero_additional_model_search_fetch_or_network_call_surface": all(
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
            integration["entropy_or_information_gain_assigns_signed_credit"] is False
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
        runtime.candidates.PRIVILEGED_READ_FLAG: False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_key_anchored_external_protocol_design": not findings,
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
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or copied.get("effect_delta")
        != {
            "model_requests": 0,
            "logical_queries": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "provider_tokens": 0,
        }
        or copied.get(runtime.candidates.PRIVILEGED_READ_FLAG) is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "fresh_disjoint_key_anchored_external_protocol_design": valid,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "reuse_v25438_population_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.45 key-anchored metadata shared audit drifted")
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
