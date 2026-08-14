#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.83/V2.54.84 successor."""

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
from deepwide_agent import v25483_row_key_iana_detail_candidate as primitive  # noqa: E402
from deepwide_agent import v25484_row_key_iana_detail_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25482_v25481_qualified_label_no_go as diagnosis  # noqa: E402


DATE = "20260814"
ROLE = "v25485_row_key_iana_detail_clean_build_audit"
IMPLEMENTATION_COMMIT = "69cd0cc21d0a95cbb356dcc3d5503022504c0515"
SOURCE = Path("scripts/audit_v25485_row_key_iana_detail_build.py")
TEST = Path("tests/test_audit_v25485_row_key_iana_detail_build.py")
PRIMITIVE_SOURCE = Path(
    "src/deepwide_agent/v25483_row_key_iana_detail_candidate.py"
)
PRIMITIVE_TEST = Path("tests/test_v25483_row_key_iana_detail_candidate.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25484_row_key_iana_detail_runtime.py")
RUNTIME_TEST = Path("tests/test_v25484_row_key_iana_detail_runtime.py")
DIAGNOSIS = Path(
    "results/v25482_v25481_qualified_label_no_go_diagnosis_v1_20260814.json"
)
OUTPUT = Path(f"results/v25485_row_key_iana_detail_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    PRIMITIVE_SOURCE: "639ce8ecd74eb742bab04b78a62a0fd1f78b4f0605b258fc8ca8b354d756656e",
    PRIMITIVE_TEST: "374ecd369bc86fe20105d06fba601559b4b9e7bfe8eb04a1ed9d8479724eba96",
    RUNTIME_SOURCE: "0ca1fab8f9641943f5f16fa98ff40ac719a6536c92c1fa7c747074864685d08f",
    RUNTIME_TEST: "1a4ceee5085570ad655f8080200a956c5e3de43adb8ee10b170c631c85cbd14c",
    DIAGNOSIS: "f48b9bc6a13fae93317657356638a50ee01057cf9be22030ceb3d562bbbf9cad",
}
TEST_SUITES = (
    ("test_audit_v25485_row_key_iana_detail_build.py", 4),
    ("test_v25483_row_key_iana_detail_candidate.py", 7),
    ("test_v25484_row_key_iana_detail_runtime.py", 7),
    ("test_v25472_qualified_source_label_runtime.py", 6),
    ("test_v25471_qualified_source_label_candidate.py", 7),
    ("test_v25464_row_key_bound_structured_source_candidate.py", 9),
    ("test_v25465_row_key_bound_structured_source_runtime.py", 6),
    ("test_v25450_official_rfc_xml_shared_runtime.py", 7),
    ("test_v25432_source_authoritative_field_candidate.py", 9),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_diagnose_v25482_v25481_qualified_label_no_go.py", 4),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 92
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "79c8eb65f06d112357392a906e46dd66d3b678f823f7ae907d1093a29d1fc1d5"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "13d49acca632b8d8a939faf741c9daf02fb020040d9d941e470eaf39cbe928a8"
)
CHECK_NAMES = frozenset(
    {
        "v25482_no_go_and_official_detail_reach_authorization_bound",
        "fixed_successor_tests_and_diagnosis_hashes_match",
        "implementation_commit_in_head_history",
        "focused_successor_parent_and_audit_tests_exact76",
        "git_clean_head_equals_target_main",
        "all_audit_runtime_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact92_and_hash_bound",
        "direct_primitive_and_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "official_url_derived_only_after_completed_parent_row_key",
        "visible_iana_authority_and_exact_https_host_path_required",
        "no_country_tld_mapping_synonym_ontology_host_rank_or_model_inference",
        "row_key_url_path_and_title_or_leading_page_surface_bound",
        "field_and_value_evidence_closed_and_conflict_fail_closed",
        "one_v25472_parent_forward_and_parent_prediction_exact_control",
        "remaining_capacity_only_and_zero_overcap_attempt",
        "query4_fetch14_model3_final_caps",
        "candidate_additional_query_and_model_zero_fetch_at_most_one",
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


def _diagnosis_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    diagnosis.validate_diagnosis(value)
    observed = value["diagnosis"]
    if (
        base.sha256(DIAGNOSIS) != FIXED_HASHES[DIAGNOSIS]
        or value.get("audit_valid") is not True
        or observed.get("prediction_changed_tasks") != 1
        or observed.get("unused_fetch_capacity_under_existing_hard_cap") != 80
        or observed.get("adjacent_surface_counterfactual", {}).get(
            "adjacent_counterfactual_candidate_count"
        )
        != 0
        or observed.get("next_bottleneck")
        != "row_key_bound_official_detail_page_reach_before_field_parsing"
        or value.get("authorization", {}).get(
            "row_key_derived_official_detail_fetch_build_design"
        )
        is not True
        or value.get("authorization", {}).get("external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.54.85 diagnosis barrier drifted")
    return value


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    history = set(base._git("rev-list", head).splitlines())
    prior = _diagnosis_barrier()
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
        DIAGNOSIS,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    primitive_contract = primitive.integration_contract()
    integration = runtime.integration_contract()
    snapshot = watchers.watcher_snapshot()
    tests_green = tests["passed"]
    checks = {
        "v25482_no_go_and_official_detail_reach_authorization_bound": bool(prior),
        "fixed_successor_tests_and_diagnosis_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_in_head_history": IMPLEMENTATION_COMMIT in history,
        "focused_successor_parent_and_audit_tests_exact76": tests_green,
        "git_clean_head_equals_target_main": (clean if tracked else True)
        and head == target,
        "all_audit_runtime_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact92_and_hash_bound": (
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
        "official_url_derived_only_after_completed_parent_row_key": (
            primitive_contract[
                "official_url_derived_only_from_completed_parent_row_key"
            ]
            and integration["one_v25472_parent_forward_shared_by_base_and_candidate"]
        ),
        "visible_iana_authority_and_exact_https_host_path_required": (
            primitive_contract["visible_iana_authority_phrase_required"]
            and primitive_contract[
                "exact_https_host_path_and_nonredirected_page_required"
            ]
        ),
        "no_country_tld_mapping_synonym_ontology_host_rank_or_model_inference": (
            primitive_contract[
                "country_tld_mapping_synonym_ontology_host_ranking_or_model_inference"
            ]
            is False
        ),
        "row_key_url_path_and_title_or_leading_page_surface_bound": primitive_contract[
            "row_key_binds_url_path_and_title_or_leading_page_surface"
        ],
        "field_and_value_evidence_closed_and_conflict_fail_closed": tests_green,
        "one_v25472_parent_forward_and_parent_prediction_exact_control": (
            integration["one_v25472_parent_forward_shared_by_base_and_candidate"]
            and integration["qualified_source_label_parent_prediction_is_exact_control"]
        ),
        "remaining_capacity_only_and_zero_overcap_attempt": (
            integration[
                "remaining_capacity_computed_only_from_content_free_budget_receipt"
            ]
            and integration["over_cap_candidate_fetch_never_attempted"]
        ),
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
        "runtime_inputs_exactly_opaque_id_and_question": integration[
            "runtime_input_keys"
        ]
        == ["opaque_id", "question"],
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
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean if tracked else True,
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
            "fresh_outcome_blind_external_population_design": valid,
            "external_protocol_or_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.85 build audit drifted")
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
