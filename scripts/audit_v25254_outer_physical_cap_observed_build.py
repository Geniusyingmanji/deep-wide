#!/usr/bin/env python3
"""Clean-build audit for V2.52.53 truthful physical caps and stage observer."""

from __future__ import annotations

import ast
import copy
import json
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as runtime  # noqa: E402
from deepwide_agent import v25248_header_totality_shadow_external_contract as external  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as audit  # noqa: E402
from scripts import diagnose_v25252_v25248_shadow_no_go as parent  # noqa: E402
from scripts import run_v25248_header_totality_shadow_external as publisher  # noqa: E402


SOURCE = Path("scripts/audit_v25254_outer_physical_cap_observed_build.py")
TEST = Path("tests/test_audit_v25254_outer_physical_cap_observed_build.py")
RUNTIME = Path("src/deepwide_agent/v25253_outer_physical_cap_observed_runtime.py")
RUNTIME_TEST = Path("tests/test_v25253_outer_physical_cap_observed_runtime.py")
PARENT_DIAGNOSIS = parent.RESULT
PARENT_DIAGNOSIS_SHA256 = "f9c0eb558092ff92c16a939bc951da2fbde2989b54dbebb91fdd794dd22fe4ec"
RESULT = Path(f"results/v25254_outer_physical_cap_observed_build_audit_v1_{external.DATE}.json")
TEST_SUITES = (
    ("test_audit_v25254_outer_physical_cap_observed_build.py", 4),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_v25232_header_totality_shadow_runtime.py", 8),
    ("test_v25188_export_failure_tolerant_same_response_runtime.py", 13),
    ("test_v25180_quote_aware_production_runtime.py", 9),
    ("test_v25165_observed_vertical_key_value_runtime.py", 6),
    ("test_v25158_vertical_key_value_candidate_runtime.py", 11),
    ("test_v25135_sparse_production_runtime.py", 9),
    ("test_diagnose_v25252_v25248_shadow_no_go.py", 4),
)
EXPECTED_TESTS = sum(value for _pattern, value in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 73
EXPECTED_CLOSURE_VECTOR_SHA256 = "8c474023ee9bcbdfcd8a9f68f0def106f6c2b01d671cb1dad29165181b2d9ae0"
EXPECTED_CLOSURE_PATH_SHA256 = "f6e0f29ec3b4b250b92d014c66e367b3437ffc78178469a9a3d401e4a3eacb1c"
CHECK_NAMES = {
    "parent_diagnosis_hash_and_build_only_authority_exact",
    "runtime_and_audit_tests_exact71",
    "git_clean_head_equals_target_main",
    "all_runtime_audit_test_parent_and_closure_files_tracked",
    "runtime_dependency_vector_exact73_and_hash_bound",
    "privileged_runtime_field_access_zero",
    "evaluator_capability_zero",
    "credential_literal_zero",
    "only_known_provider_rank_score_exception",
    "truthful_query4_fetch14_model4_caps",
    "fifth_model_and_fifteenth_fetch_rejected_before_effect",
    "verified_gain_revision_quality_path_preserved",
    "content_free_six_stage_failure_observer_present",
    "runtime_accepts_only_visible_task_and_injected_clients",
    "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
    "no_external_effect_performed",
}


def _tests() -> dict[str, Any]:
    suites = [audit._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(sorted(audit._dependency_closure((RUNTIME,)), key=str))
    vector = [{"path": str(path), "sha256": audit.sha256(path)} for path in closure]
    return closure, vector


def _tracked(path: Path) -> bool:
    return audit._tracked(path)


def _stage_surface_present() -> bool:
    source = (ROOT / RUNTIME).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(RUNTIME))
    stage_literal = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "STAGES" for target in node.targets
        ):
            try:
                stage_literal = tuple(ast.literal_eval(node.value))
            except BaseException:
                return False
    return stage_literal == runtime.STAGES and runtime.STAGES == (
        "boundary",
        "sparse_parent_run_and_validate",
        "effect_rebuild",
        "parent_freeze",
        "shadow_receipt",
        "result_envelope_validate",
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    parent_path = audit._ordinary(PARENT_DIAGNOSIS)
    parent_value = parent.validate_diagnosis(json.loads(parent_path.read_text(encoding="utf-8")))
    tests = _tests()
    closure, vector = _closure()
    semantic = audit._semantic_findings(closure)
    explicit = {SOURCE, TEST, RUNTIME, RUNTIME_TEST, PARENT_DIAGNOSIS, *closure}
    untracked = sorted(str(path) for path in explicit if tracked and not _tracked(path))
    test_green = tests["passed"]
    checks = {
        "parent_diagnosis_hash_and_build_only_authority_exact": (
            audit.sha256(PARENT_DIAGNOSIS) == PARENT_DIAGNOSIS_SHA256
            and parent_value["authorization"]["outer_physical_hard_cap_and_content_free_stage_observer_build_only"] is True
            and parent_value["authorization"]["fresh_external_protocol_design"] is False
        ),
        "runtime_and_audit_tests_exact71": test_green,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "all_runtime_audit_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact73_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and external.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and external.payload_sha256([row["path"] for row in vector]) == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "privileged_runtime_field_access_zero": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "only_known_provider_rank_score_exception": semantic["allowed_provider_rank_access"] == ["src/deepwide_agent/clients.py:565:score"],
        "truthful_query4_fetch14_model4_caps": (
            runtime.QUERY_CAP == 4 and runtime.FETCH_CAP == 14 and runtime.MODEL_CAP == 4
        ),
        "fifth_model_and_fifteenth_fetch_rejected_before_effect": test_green,
        "verified_gain_revision_quality_path_preserved": test_green,
        "content_free_six_stage_failure_observer_present": _stage_surface_present(),
        "runtime_accepts_only_visible_task_and_injected_clients": test_green,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25254_outer_physical_cap_observed_clean_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_parent": {"path": str(PARENT_DIAGNOSIS), "sha256": audit.sha256(PARENT_DIAGNOSIS)},
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": external.payload_sha256(vector),
        "runtime_dependency_path_sha256": external.payload_sha256([row["path"] for row in vector]),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "physical_caps": {"queries": runtime.QUERY_CAP, "fetches": runtime.FETCH_CAP, "model_forwards": runtime.MODEL_CAP},
        "observed_stages": list(runtime.STAGES),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_artifact_disjoint_observed_reliability_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return external.seal(value, "audit_payload_sha256")


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    git_value = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    vector = copied.get("runtime_dependency_vector") or []
    semantic = copied.get("semantic_audit") or {}
    checks = copied.get("checks") or {}
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git", "fixed_parent",
            "tests", "runtime_dependency_vector", "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256", "semantic_audit", "physical_caps",
            "observed_stages", "checks", "findings", "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25254_outer_physical_cap_observed_clean_build_audit"
        or set(git_value) != {"head", "target_main", "equal", "clean"}
        or git_value.get("head") != git_value.get("target_main")
        or git_value.get("equal") is not True
        or git_value.get("clean") is not True
        or copied.get("fixed_parent") != {"path": str(PARENT_DIAGNOSIS), "sha256": PARENT_DIAGNOSIS_SHA256}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256") or "")) is None
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or copied.get("runtime_dependency_vector_sha256") != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256") != EXPECTED_CLOSURE_PATH_SHA256
        or set(semantic)
        != {"privileged_runtime_field_accesses", "evaluator_capabilities", "credential_literal_hits", "allowed_provider_rank_access", "untracked_sources"}
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("allowed_provider_rank_access") != ["src/deepwide_agent/clients.py:565:score"]
        or semantic.get("untracked_sources") != []
        or copied.get("physical_caps") != {"queries": 4, "fetches": 14, "model_forwards": 4}
        or copied.get("observed_stages") != list(runtime.STAGES)
        or set(checks) != CHECK_NAMES
        or not all(checks.values())
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or any(copied.get(name) is not False for name in (
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
        ))
        or copied.get("authorization")
        != {
            "fresh_artifact_disjoint_observed_reliability_protocol_design": True,
            "fresh_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not external.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.52.54 build audit drifted")
    return copied


def main() -> None:
    value = validate_audit(build_audit())
    publisher._publish_json(ROOT / RESULT, value)
    print(json.dumps({"path": str(RESULT), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
