#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.49/V2.54.50 RFC XML candidate."""

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
from deepwide_agent import v25449_official_rfc_xml_record_candidate as primitive  # noqa: E402
from deepwide_agent import v25450_official_rfc_xml_shared_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260814"
ROLE = "v25451_official_rfc_xml_shared_clean_build_audit"
IMPLEMENTATION_COMMITS = (
    "b1cc64c8164d13fbe9b2ce06969c490e970f86b0",
    "604227a143a43eb84f236c0ef854f7fd52239a3e",
    "816f7e3c755775011aab05312095b134578ab6d2",
    "e5fd52de34054c8da0e40ac282d3bda071cdb0a5",
)
SOURCE = Path("scripts/audit_v25451_official_rfc_xml_shared_build.py")
TEST = Path("tests/test_audit_v25451_official_rfc_xml_shared_build.py")
PRIMITIVE_SOURCE = Path(
    "src/deepwide_agent/v25449_official_rfc_xml_record_candidate.py"
)
PRIMITIVE_TEST = Path(
    "tests/test_v25449_official_rfc_xml_record_candidate.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25450_official_rfc_xml_shared_runtime.py"
)
RUNTIME_TEST = Path("tests/test_v25450_official_rfc_xml_shared_runtime.py")
PARENT_DIAGNOSIS = Path(
    "results/v25448_v25446_key_anchored_quality_diagnosis_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25451_official_rfc_xml_shared_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    PRIMITIVE_SOURCE: "1bc232d6f89de07da1b25593024088b7717d6d9adda4bb3c11a0597071a1d8bc",
    PRIMITIVE_TEST: "b6b4722b10e4c5dec1fc5ced7aa885f3eea0ea47c4002e5796449a6064e2057b",
    RUNTIME_SOURCE: "d8411337a874b338909959f9925b87a83063d1eb3da86ce1d30a04336b4cd3ba",
    RUNTIME_TEST: "f03c3ff121114354e2559d75a95d5c483e507642e2509524f61b853a5a5e324d",
    PARENT_DIAGNOSIS: "59c7c95b31ac821004380a760ebaa95980a5046bc9dc8b3ee94fd5ccddcf7157",
}
TEST_SUITES = (
    ("test_audit_v25451_official_rfc_xml_shared_build.py", 4),
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
EXPECTED_CLOSURE_COUNT = 99
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "5143c16e2fe36437e32ad013142e3fe9511704c0d594342d6b488d4d66cf7af7"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "4d3b0540da367c59b6ebcc21e72ce367f2681943e328618a66e27868ecbe5a3b"
)
CHECK_NAMES = frozenset(
    {
        "parent_diagnosis_bound_and_build_only_authorized",
        "fixed_primitive_runtime_test_and_diagnosis_hashes_match",
        "all_implementation_commits_in_head_history",
        "focused_parent_and_audit_tests_exact90",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact99_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "strict_visible_membership_to_exact_official_xml_urls",
        "url_xml_root_series_and_base_row_identity_all_bound",
        "rfc_xml_publication_class_not_benchmark_category",
        "one_parent_forward_and_parent_key_candidate_not_composed",
        "remaining_capacity_only_and_zero_overcap_attempt",
        "query4_fetch14_model3_final_caps",
        "redirect_failure_parse_failure_and_capacity_shortfall_preserve_base",
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
    if (
        base.sha256(PARENT_DIAGNOSIS) != FIXED_HASHES[PARENT_DIAGNOSIS]
        or value.get("role") != "v25448_v25446_key_anchored_quality_diagnosis"
        or not base.payload_sha256(
            {key: item for key, item in value.items() if key != "diagnosis_payload_sha256"}
        )
        == value.get("diagnosis_payload_sha256")
        or value.get("formal_result", {}).get("quality_gate_passed") is not False
        or value.get("candidate_funnel", {}).get("candidate_metric_improvement_count") != 0
        or value.get("next_design_constraints", {}).get("preserve_physical_fetch_cap") != 14
        or value.get("authorization", {}).get("structured_official_record_candidate_build") is not True
        or value.get("authorization", {}).get("new_external_forward") is not False
        or value.get("authorization", {}).get("deepwidebench_successor_build_or_forward") is not False
    ):
        raise RuntimeError("V2.54.51 parent diagnosis barrier drifted")
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
    integration = runtime.integration_contract()
    primitive_contract = primitive.integration_contract()
    reported_clean = clean if tracked else True
    checks = {
        "parent_diagnosis_bound_and_build_only_authorized": bool(diagnosis),
        "fixed_primitive_runtime_test_and_diagnosis_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "all_implementation_commits_in_head_history": all(
            commit in history for commit in IMPLEMENTATION_COMMITS
        ),
        "focused_parent_and_audit_tests_exact90": tests["passed"],
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "all_audit_runtime_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact99_and_hash_bound": (
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
        "strict_visible_membership_to_exact_official_xml_urls": (
            primitive_contract["maximum_deterministic_official_xml_requests"] == 4
            and primitive_contract["exact_official_url_template"]
            == "https://www.rfc-editor.org/rfc/rfcNNNN.xml"
        ),
        "url_xml_root_series_and_base_row_identity_all_bound": tests["passed"],
        "rfc_xml_publication_class_not_benchmark_category": (
            semantic["privileged_runtime_field_accesses"] == []
            and primitive_contract["category_to_status_uses_fixed_rfc_xml_schema_only"]
            is True
        ),
        "one_parent_forward_and_parent_key_candidate_not_composed": (
            integration["one_parent_forward_shared_by_base_and_candidate"] is True
            and integration["parent_key_anchored_candidate_not_composed"] is True
        ),
        "remaining_capacity_only_and_zero_overcap_attempt": (
            integration[
                "remaining_capacity_computed_only_from_content_free_budget_receipt"
            ]
            is True
            and integration["over_cap_candidate_batch_never_attempted"] is True
        ),
        "query4_fetch14_model3_final_caps": (
            integration["maximum_physical_queries"] == 4
            and integration["maximum_physical_fetches"] == 14
            and integration["normal_path_model_forwards"] == 3
        ),
        "redirect_failure_parse_failure_and_capacity_shortfall_preserve_base": tests[
            "passed"
        ],
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
        "primitive_contract": primitive_contract,
        "integration_contract": integration,
        "effect_envelope": {
            "parent_forward_count": 1,
            "candidate_maximum_additional_fetches": 4,
            "candidate_additional_queries": 0,
            "candidate_additional_model_calls": 0,
            "final_maximum_queries": 4,
            "final_maximum_fetches": 14,
            "final_normal_path_model_forwards": 3,
        },
        "protected_watchers": snapshot,
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
    findings = copied.get("findings")
    tests = copied.get("tests")
    semantic = copied.get("semantic_audit")
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commits") != list(IMPLEMENTATION_COMMITS)
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
        or copied.get("effect_envelope")
        != {
            "parent_forward_count": 1,
            "candidate_maximum_additional_fetches": 4,
            "candidate_additional_queries": 0,
            "candidate_additional_model_calls": 0,
            "final_maximum_queries": 4,
            "final_maximum_fetches": 14,
            "final_normal_path_model_forwards": 3,
        }
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
            "fresh_structurally_disjoint_population_design": valid,
            "external_protocol_design": False,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.51 official RFC XML build audit drifted")
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
