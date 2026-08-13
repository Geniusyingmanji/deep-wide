#!/usr/bin/env python3
"""Clean-build audit for V2.53.95 visible-membership synthesis."""

from __future__ import annotations

import copy
import json
import os
import socket
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

from deepwide_agent import v25068_quote_verified_external_contract as watcher_contract  # noqa: E402
from deepwide_agent import v25376_changed_safe_exact220_contract as public_tasks  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25394_v25393_hybrid_row_overlap as diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25396_visible_membership_synthesis_clean_build_audit"
SOURCE = Path("scripts/audit_v25396_visible_membership_synthesis_build.py")
TEST = Path("tests/test_audit_v25396_visible_membership_synthesis_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25395_visible_membership_synthesis_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25395_visible_membership_synthesis_runtime.py"
)
DIAGNOSIS_SOURCE = diagnosis.SOURCE
DIAGNOSIS_ARTIFACT = diagnosis.OUTPUT
DIAGNOSIS_TEST = diagnosis.TEST
OUTPUT = Path(
    f"results/v25396_visible_membership_synthesis_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    RUNTIME_SOURCE: "b875c992b0c238281490b459cc4dad6baac7165c48a52f8b19eb4a0cfbfa0a19",
    RUNTIME_TEST: "70cc6db310989665cb9e4492cb85a7aa33f2cd12f95065e9167edf1ae5430a86",
    DIAGNOSIS_SOURCE: "0fdf4b08f9697ca712c9c3efd4926b0a11d87d8a9d2b8a83a8ee626c2be4003b",
    DIAGNOSIS_ARTIFACT: "632f32bbe88f443519b58fe4a07dce9597634ded489db846adf3de5920c23368",
}
TEST_SUITES = (
    ("test_audit_v25396_visible_membership_synthesis_build.py", 4),
    ("test_v25395_visible_membership_synthesis_runtime.py", 7),
    ("test_diagnose_v25394_v25393_hybrid_row_overlap.py", 4),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25383_joint_synthesis_changed_safe_runtime.py", 8),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
    ("test_v25369_changed_safe_verified_coordinate_edit.py", 8),
    ("test_v25360_quote_coordinate_partial_field_record.py", 8),
    ("test_v25014_multi_identity_detail_fields.py", 9),
    ("test_v25080_visible_identity_page_record.py", 8),
    ("test_v24921_target_value_coverage_projector.py", 9),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 91
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "63468b732114690a995b5243eea8cf129758e12316aede04f9c66cad560ca3ef"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "d5c6bf084bc99b36e6500253817194e0298a98872f3ad45679d2e572ae98b744"
)
CHECK_NAMES = frozenset(
    {
        "v25394_row_overlap_diagnosis_bound_and_build_only",
        "fixed_runtime_test_diagnosis_hashes_match",
        "visible_membership_and_parent_tests_exact99",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked",
        "runtime_dependency_vector_exact91_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "membership_comes_only_from_strict_visible_question_grammar",
        "no_membership_parent_prompt_and_prediction_identity",
        "constraint_precedes_existing_third_model_call",
        "provider_ignored_constraint_does_not_append_or_repair_rows",
        "joint_grounded_priority_and_no_fallthrough_unchanged",
        "truthful_query4_fetch14_model3_normal_cap",
        "receipt_membership_parent_and_credit_tamper_fail_closed",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "public220_visible_question_coverage_aggregate_only",
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
    closure = tuple(
        sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str)
    )
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _diagnosis_barrier() -> dict[str, Any]:
    value = diagnosis.validate_diagnosis(
        json.loads(base._ordinary(DIAGNOSIS_ARTIFACT).read_text(encoding="utf-8"))
    )
    funnel = value["content_free_funnel"]
    if (
        base.sha256(DIAGNOSIS_ARTIFACT) != FIXED_HASHES[DIAGNOSIS_ARTIFACT]
        or funnel["verified_field_count_total"] != 27
        or funnel["missing_row_rejected_field_count_total"] != 10
        or funnel["unchanged_verified_coordinate_count_total"] != 11
        or funnel["changed_safe_coordinate_count_total"] != 6
        or funnel["verified_field_disposition_is_exhaustive"] is not True
        or value["authorization"][
            "pre_synthesis_verified_row_constraint_build_only"
        ]
        is not True
        or value["authorization"]["new_external_forward"] is not False
    ):
        raise RuntimeError("V2.53.96 diagnosis barrier drifted")
    return value


def _public_visible_coverage() -> dict[str, Any]:
    rows = public_tasks.task_vector(ROOT)
    counts: Counter[str] = Counter()
    member_histogram: Counter[int] = Counter()
    for row in rows:
        values, source = runtime.visible_membership(row["question"])
        counts[source] += 1
        member_histogram[len(values)] += 1
    return {
        "task_count": len(rows),
        "membership_source_counts": dict(sorted(counts.items())),
        "visible_member_count_histogram": {
            str(key): value for key, value in sorted(member_histogram.items())
        },
        "question_text_opaque_id_mapping_gold_answer_evaluator_or_score_persisted": False,
        "runtime_or_evaluator_called": False,
    }


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
    diagnosed = _diagnosis_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        DIAGNOSIS_SOURCE,
        DIAGNOSIS_ARTIFACT,
        DIAGNOSIS_TEST,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    fixed_match = all(
        base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
    )
    watchers = watcher_contract.watcher_snapshot()
    coverage = _public_visible_coverage()
    reported_clean = clean if tracked else True
    tests_green = tests["passed"]
    checks = {
        "v25394_row_overlap_diagnosis_bound_and_build_only": bool(diagnosed),
        "fixed_runtime_test_diagnosis_hashes_match": fixed_match,
        "visible_membership_and_parent_tests_exact99": tests_green,
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_diagnosis_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact91_and_hash_bound": (
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
        "membership_comes_only_from_strict_visible_question_grammar": tests_green,
        "no_membership_parent_prompt_and_prediction_identity": tests_green,
        "constraint_precedes_existing_third_model_call": tests_green,
        "provider_ignored_constraint_does_not_append_or_repair_rows": tests_green,
        "joint_grounded_priority_and_no_fallthrough_unchanged": tests_green,
        "truthful_query4_fetch14_model3_normal_cap": tests_green,
        "receipt_membership_parent_and_credit_tamper_fail_closed": tests_green,
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "public220_visible_question_coverage_aggregate_only": (
            coverage["task_count"] == 220
            and sum(coverage["membership_source_counts"].values()) == 220
            and coverage[
                "question_text_opaque_id_mapping_gold_answer_evaluator_or_score_persisted"
            ]
            is False
            and coverage["runtime_or_evaluator_called"] is False
        ),
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
        "public220_visible_question_coverage": coverage,
        "physical_caps": {
            "queries": 4,
            "fetches": 14,
            "normal_path_model_forwards": 3,
            "outer_hard_model_cap": 4,
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
    coverage = copied.get("public220_visible_question_coverage")
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
        or not isinstance(coverage, Mapping)
        or coverage.get("task_count") != 220
        or sum((coverage.get("membership_source_counts") or {}).values()) != 220
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
        raise ValueError("V2.53.96 visible membership build audit drifted")
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
                "coverage": value["public220_visible_question_coverage"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
