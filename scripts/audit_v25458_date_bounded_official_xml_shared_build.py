#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.56/V2.54.57 successor."""

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
from deepwide_agent import v25456_date_bounded_official_rfc_xml_record_candidate as primitive  # noqa: E402
from deepwide_agent import v25457_date_bounded_official_rfc_xml_shared_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25455_v25454_official_xml_prefix as diagnosis_module  # noqa: E402


DATE = "20260814"
ROLE = "v25458_date_bounded_official_xml_shared_clean_build_audit"
IMPLEMENTATION_COMMIT = "328efa0aaa26f64bca2485ac1d650cff561956d0"
SOURCE = Path("scripts/audit_v25458_date_bounded_official_xml_shared_build.py")
TEST = Path("tests/test_audit_v25458_date_bounded_official_xml_shared_build.py")
PRIMITIVE_SOURCE = Path(
    "src/deepwide_agent/v25456_date_bounded_official_rfc_xml_record_candidate.py"
)
PRIMITIVE_TEST = Path(
    "tests/test_v25456_date_bounded_official_rfc_xml_record_candidate.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25457_date_bounded_official_rfc_xml_shared_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25457_date_bounded_official_rfc_xml_shared_runtime.py"
)
PARENT_DIAGNOSIS = Path(
    "results/v25455_v25454_official_xml_prefix_diagnosis_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25458_date_bounded_official_xml_shared_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    PRIMITIVE_SOURCE: "a267a2f64d76bbc64d2edb14104c5f27f1f8f27dbec12740f93e617bf67765b2",
    PRIMITIVE_TEST: "475a9a961c15d4a511463cf6b12b7162d1586dfb65c6e6f30ffd1d3d2a0686f8",
    RUNTIME_SOURCE: "7d5505eb359c6dae7da5a74d86f3e5b20a1d5281a570ea2b82c50ce380ecdeb8",
    RUNTIME_TEST: "2faf90e000a755231c675134541b03fe09fa6c1d4bf2cb930305efdd32a4e467",
    PARENT_DIAGNOSIS: "4f83aae963664fee762e32e9ea5cfa6e57e5899906e37c492b29a051c1dc71f0",
}
TEST_SUITES = (
    ("test_audit_v25458_date_bounded_official_xml_shared_build.py", 4),
    ("test_v25457_date_bounded_official_rfc_xml_shared_runtime.py", 7),
    ("test_v25456_date_bounded_official_rfc_xml_record_candidate.py", 8),
    ("test_v25450_official_rfc_xml_shared_runtime.py", 7),
    ("test_v25449_official_rfc_xml_record_candidate.py", 8),
    ("test_v25444_key_anchored_metadata_shared_runtime.py", 8),
    ("test_v25440_key_anchored_metadata_candidate.py", 13),
    ("test_v25434_source_authoritative_shared_runtime.py", 9),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25395_visible_membership_synthesis_runtime.py", 7),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 101
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "3add4fe71e5838347796aa637cf3e92edf196d92e87eced9f87119277cd327f2"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "b65c0a5b6c1e9f77f58c31a24f848d095abe99879acca15ed7503d3ed57341ac"
)
CHECK_NAMES = frozenset(
    {
        "parent_no_go_diagnosis_bound_and_build_only_authorized",
        "fixed_successor_tests_and_diagnosis_hashes_match",
        "implementation_commit_in_head_history",
        "focused_successor_parent_and_audit_tests_exact105",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact101_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "frozen_v25454_exact_pages_replay_78_of_78_without_truth",
        "complete_front_and_date_bounded_front_both_supported",
        "doctype_entity_incomplete_date_and_incomplete_author_fail_closed",
        "explicit_xml_typography_and_author_attribute_compatibility_only",
        "url_xml_root_series_and_base_row_identity_all_bound",
        "one_parent_forward_and_parent_key_candidate_not_composed",
        "remaining_capacity_only_and_zero_overcap_attempt",
        "query4_fetch14_model3_final_caps",
        "candidate_additional_query_and_model_zero",
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


def _diagnosis_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
    diagnosis_module.validate_diagnosis(value)
    stats = value["aggregate_prefix_statistics"]
    if (
        base.sha256(PARENT_DIAGNOSIS) != FIXED_HASHES[PARENT_DIAGNOSIS]
        or value.get("diagnosis_valid") is not True
        or stats.get("exact_nonredirected_page_count") != 78
        or stats.get("current_parser_valid_record_count") != 0
        or stats.get("date_bounded_parseable_record_count") != 78
        or value.get("authorization", {}).get(
            "date_bounded_official_xml_parser_successor_build"
        )
        is not True
        or value.get("authorization", {}).get("new_external_forward") is not False
        or value.get("authorization", {}).get("postfreeze_truth_or_quality")
        is not False
    ):
        raise RuntimeError("V2.54.58 parent diagnosis barrier drifted")
    return value


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    history = set(base._git("rev-list", head).splitlines())
    diagnosis = _diagnosis_barrier()
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
        PARENT_DIAGNOSIS,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    snapshot = watchers.watcher_snapshot()
    primitive_contract = primitive.integration_contract()
    integration = runtime.integration_contract()
    checks = {
        "parent_no_go_diagnosis_bound_and_build_only_authorized": bool(diagnosis),
        "fixed_successor_tests_and_diagnosis_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_in_head_history": IMPLEMENTATION_COMMIT in history,
        "focused_successor_parent_and_audit_tests_exact105": tests["passed"],
        "git_clean_head_equals_target_main": (clean if tracked else True)
        and head == target,
        "all_audit_runtime_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact101_and_hash_bound": (
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
        "frozen_v25454_exact_pages_replay_78_of_78_without_truth": tests["passed"],
        "complete_front_and_date_bounded_front_both_supported": (
            primitive_contract["complete_front_supported"]
            and primitive_contract[
                "date_bounded_temporary_front_closure_supported"
            ]
        ),
        "doctype_entity_incomplete_date_and_incomplete_author_fail_closed": tests[
            "passed"
        ],
        "explicit_xml_typography_and_author_attribute_compatibility_only": (
            primitive_contract[
                "date_must_be_complete_before_temporary_closure"
            ]
            and primitive_contract[
                "temporary_closure_must_parse_as_rfc_front_with_date"
            ]
            and primitive_contract[
                "workgroup_source_or_draft_prefix_to_stream_inference"
            ]
            is False
        ),
        "url_xml_root_series_and_base_row_identity_all_bound": primitive_contract[
            "url_xml_root_series_and_base_row_identity_all_bound"
        ],
        "one_parent_forward_and_parent_key_candidate_not_composed": (
            integration["one_parent_forward_shared_by_base_and_candidate"]
            and integration["parent_key_anchored_candidate_not_composed"]
        ),
        "remaining_capacity_only_and_zero_overcap_attempt": (
            integration[
                "remaining_capacity_computed_only_from_content_free_budget_receipt"
            ]
            and integration["over_cap_candidate_batch_never_attempted"]
        ),
        "query4_fetch14_model3_final_caps": (
            integration["maximum_physical_queries"] == 4
            and integration["maximum_physical_fetches"] == 14
            and integration["normal_path_model_forwards"] == 3
        ),
        "candidate_additional_query_and_model_zero": (
            integration["candidate_additional_queries"] == 0
            and integration["candidate_additional_model_calls"] == 0
        ),
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": (
            integration["entropy_or_information_gain_assigns_signed_credit"]
            is False
            and primitive_contract[
                "entropy_or_information_gain_assigns_signed_credit"
            ]
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
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean if tracked else True},
        "fixed_artifact_hashes": {str(path): base.sha256(path) for path in FIXED_HASHES},
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": base.payload_sha256(vector),
        "runtime_dependency_path_sha256": base.payload_sha256([row["path"] for row in vector]),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "primitive_contract": primitive_contract,
        "integration_contract": integration,
        "frozen_prefix_replay": {
            "source_forward_terminal_tasks": 20,
            "exact_nonredirected_pages": 78,
            "old_parser_valid_records": 0,
            "successor_parser_valid_records": 78,
            "truth_evaluator_or_quality_opened": False,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_structurally_disjoint_population_design": not findings,
            "external_protocol_design": False,
            "external_forward": False,
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
        or copied.get("frozen_prefix_replay")
        != {
            "source_forward_terminal_tasks": 20,
            "exact_nonredirected_pages": 78,
            "old_parser_valid_records": 0,
            "successor_parser_valid_records": 78,
            "truth_evaluator_or_quality_opened": False,
        }
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "fresh_structurally_disjoint_population_design": valid,
            "external_protocol_design": False,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.58 date-bounded build audit drifted")
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
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"], "tests": value["tests"]["observed"], "closure": len(value["runtime_dependency_vector"]), "findings": value["findings"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
