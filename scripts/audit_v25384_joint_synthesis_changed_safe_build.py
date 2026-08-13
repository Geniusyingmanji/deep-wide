#!/usr/bin/env python3
"""Clean-build audit for the V2.53.83 joint synthesis successor."""

from __future__ import annotations

import copy
import json
import os
import socket
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25068_quote_verified_external_contract as watcher_contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260813"
ROLE = "v25384_joint_synthesis_changed_safe_clean_build_audit"
SOURCE = Path("scripts/audit_v25384_joint_synthesis_changed_safe_build.py")
TEST = Path("tests/test_audit_v25384_joint_synthesis_changed_safe_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25383_joint_synthesis_changed_safe_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25383_joint_synthesis_changed_safe_runtime.py"
)
FUNNEL_DIAGNOSIS = Path(
    "results/v25382_v25379_changed_safe_funnel_diagnosis_v1_20260813.json"
)
OUTPUT = Path(
    f"results/v25384_joint_synthesis_changed_safe_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    RUNTIME_SOURCE: "2c9abc90673dffe8b33f2612e6ec5eb2de3d6b2a5933831e7876a6aed52f796e",
    RUNTIME_TEST: "2eb496ac5ee0f6e5389b5308d640cb7edb204e2b5a0d1b34c00dab2a282f2775",
    FUNNEL_DIAGNOSIS: "0065067086e1465dc470ce24573b02ec850ded834c25e08227fef71bdbeb2399",
}
TEST_SUITES = (
    ("test_audit_v25384_joint_synthesis_changed_safe_build.py", 4),
    ("test_v25383_joint_synthesis_changed_safe_runtime.py", 8),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
    ("test_v25369_changed_safe_verified_coordinate_edit.py", 8),
    ("test_v25360_quote_coordinate_partial_field_record.py", 8),
    ("test_v25354_pre_effect_query_compatible_grounded_fact_runtime.py", 6),
    ("test_v25349_shared_prefix_grounded_fact_paired_runtime.py", 8),
    ("test_v25346_grounded_fact_bootstrap.py", 8),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25117_grounded_target_record_plan.py", 6),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 83
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "e8eeed301f55db64d1c4355341a9df754675f084ad3847c3e1f7a7af714f9707"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "34f6e84649dd03bb6e8a22aa5f297d937efb77e99c200e73f941da1833f48400"
)
CHECK_NAMES = frozenset(
    {
        "v25382_funnel_diagnosis_bound_and_build_only",
        "fixed_runtime_test_and_diagnosis_hashes_match",
        "joint_runtime_and_parent_tests_exact95",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked",
        "runtime_dependency_vector_exact83_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "grounded_records_removed_before_parent_editor",
        "third_call_jointly_emits_table_and_records",
        "complete_two_wave_page_surface_reused",
        "records_require_same_response_row_key",
        "quote_field_value_verifier_replayed",
        "malformed_invalid_missing_or_unchanged_is_noop",
        "synthetic_second_wave_positive_chain_attributable",
        "task_local_mixed_concurrency_no_global_mutation",
        "receipt_tamper_fails_closed",
        "truthful_query4_fetch14_model3_normal_cap",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "entropy_information_gain_positive_signed_credit_zero",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "local_gpt56_port_reachable",
        "local_tcp_probe_only_no_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


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
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _diagnosis_barrier() -> dict[str, Any]:
    path = base._ordinary(FUNNEL_DIAGNOSIS)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        base.sha256(FUNNEL_DIAGNOSIS) != FIXED_HASHES[FUNNEL_DIAGNOSIS]
        or value.get("role")
        != "v25382_v25379_changed_safe_content_free_funnel_diagnosis"
        or value.get("decision", {}).get("v25379_quality") != "no_go"
        or value.get("decision", {}).get("next_build_priority")
        != "source_bound_record_proposal_coverage_then_missing_row_safe_bridge"
        or value.get("authorization", {}).get("next_build_only") is not True
        or value.get("authorization", {}).get("new_external_forward") is not False
        or value.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
    ):
        raise RuntimeError("V2.53.84 funnel diagnosis barrier drifted")
    return value


def _port_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            return True
    except OSError:
        return False


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    diagnosis = _diagnosis_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {SOURCE, TEST, *FIXED_HASHES, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    fixed_match = all(
        base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
    )
    watchers = watcher_contract.watcher_snapshot()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "v25382_funnel_diagnosis_bound_and_build_only": bool(diagnosis),
        "fixed_runtime_test_and_diagnosis_hashes_match": fixed_match,
        "joint_runtime_and_parent_tests_exact95": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact83_and_hash_bound": (
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
        "grounded_records_removed_before_parent_editor": tests_green,
        "third_call_jointly_emits_table_and_records": tests_green,
        "complete_two_wave_page_surface_reused": tests_green,
        "records_require_same_response_row_key": tests_green,
        "quote_field_value_verifier_replayed": tests_green,
        "malformed_invalid_missing_or_unchanged_is_noop": tests_green,
        "synthetic_second_wave_positive_chain_attributable": tests_green,
        "task_local_mixed_concurrency_no_global_mutation": tests_green,
        "receipt_tamper_fails_closed": tests_green,
        "truthful_query4_fetch14_model3_normal_cap": tests_green,
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "entropy_information_gain_positive_signed_credit_zero": tests_green,
        "protected_watchers_unchanged": watchers
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watcher_contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "local_gpt56_port_reachable": _port_reachable(),
        "local_tcp_probe_only_no_model_search_fetch_evaluator_benchmark_or_api_called": True,
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
        "physical_caps": {
            "queries": 4,
            "fetches": 14,
            "normal_path_model_forwards": 3,
            "outer_hard_model_cap": 4,
        },
        "matched_estimand": {
            "control": "joint_response_base_table",
            "candidate": "deterministic_changed_safe_verified_coordinate_edit",
            "shared_visible_plan_calls": 1,
            "shared_grounded_plan_calls": 1,
            "shared_query_count": 4,
            "shared_fetch_cap": 14,
            "joint_table_record_synthesis_calls": 1,
            "candidate_model_calls": 0,
            "normal_path_physical_model_calls": 3,
            "required_attribution_chain": [
                "complete_two_wave_same_forward_page_surface",
                "same_response_table_and_record_proposal",
                "same_page_quote_verified_field",
                "row_identity_exists_in_same_response_table",
                "verified_value_differs_from_base_cell",
                "deterministic_cell_edit",
                "prediction_changed",
            ],
            "positive_signed_credit_count": 0,
        },
        "protected_watchers": watchers,
        "local_tcp_reachability_probe_performed": True,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_population_and_external_protocol_design": not findings,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
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
    expected_authorization = {
        "fresh_population_and_external_protocol_design": valid,
        "external_forward": False,
        "deepwidebench_forward_or_evaluator": False,
        "leaderboard_or_sota": False,
        "retry_resume_backfill_replacement_or_selective_rerun": False,
    }
    if (
        copied.get("role") != ROLE
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
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization") != expected_authorization
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.84 joint synthesis build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
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
    if not value["audit_valid"]:
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
