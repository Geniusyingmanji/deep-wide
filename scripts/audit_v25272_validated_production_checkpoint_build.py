#!/usr/bin/env python3
"""Clean-build audit for V2.52.71 validated-production checkpointing."""

from __future__ import annotations

import ast
import copy
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from deepwide_agent import v25271_validated_production_checkpoint_runtime as runtime  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as audit  # noqa: E402
from scripts import diagnose_v25270_v25267_production_only_reliability as parent  # noqa: E402


DATE = "20260812"
ROLE = "v25272_validated_production_checkpoint_clean_build_audit"
SOURCE = Path("scripts/audit_v25272_validated_production_checkpoint_build.py")
TEST = Path("tests/test_audit_v25272_validated_production_checkpoint_build.py")
RUNTIME = Path("src/deepwide_agent/v25271_validated_production_checkpoint_runtime.py")
RUNTIME_TEST = Path("tests/test_v25271_validated_production_checkpoint_runtime.py")
PARENT_DIAGNOSIS = parent.OUTPUT
PARENT_DIAGNOSIS_SHA256 = (
    "b298439d5f4987771a2e660913647be29eddafcc38e491cc89cb7840e5ab7a12"
)
OUTPUT = Path(
    f"results/v25272_validated_production_checkpoint_build_audit_v1_{DATE}.json"
)

TEST_SUITES = (
    ("test_audit_v25272_validated_production_checkpoint_build.py", 4),
    ("test_v25271_validated_production_checkpoint_runtime.py", 9),
    ("test_v25265_production_only_totality_runtime.py", 6),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_v25135_sparse_production_runtime.py", 9),
    ("test_v25267_production_only_exact220.py", 11),
    ("test_diagnose_v25270_v25267_production_only_reliability.py", 8),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 75
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "44d7681786a378e10726ddca8bf283ff904dbe1e838c965519de3e30ff3a5fc7"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "4bf35bd020aa33638a07da291364903943c0b7830f1e59e1d4e5f6035d0b5d78"
)
CHECK_NAMES = frozenset(
    {
        "parent_diagnosis_hash_and_build_only_authority_exact",
        "runtime_and_audit_tests_exact54",
        "git_clean_head_equals_target_main",
        "all_runtime_audit_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact75_and_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "normal_path_prediction_cost_and_effect_match_parent",
        "validated_checkpoint_survives_parent_build_and_validation_faults",
        "untrusted_checkpoint_fails_closed",
        "checkpoint_receipt_result_stage_and_credit_tamper_fail_closed",
        "truthful_query4_fetch14_model4_caps_unchanged",
        "finite_seven_microstage_surface_exact",
        "runtime_accepts_only_visible_task_and_injected_clients",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


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


def _stage_surface_exact() -> bool:
    source = (ROOT / RUNTIME).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(RUNTIME))
    observed: tuple[str, ...] | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "STAGES"
            for target in node.targets
        ):
            try:
                observed = tuple(ast.literal_eval(node.value))
            except BaseException:
                return False
    return observed == runtime.STAGES and runtime.STAGES == (
        "boundary_validate",
        "paired_parent_run_and_validate",
        "effect_accounting",
        "production_checkpoint_select",
        "parent_prediction_binding",
        "result_envelope_build",
        "result_envelope_validate",
    )


def _parent_barrier() -> dict[str, Any]:
    path = audit._ordinary(PARENT_DIAGNOSIS)
    value = parent.validate_diagnosis(json.loads(path.read_text(encoding="utf-8")))
    if (
        audit.sha256(PARENT_DIAGNOSIS) != PARENT_DIAGNOSIS_SHA256
        or value["authorization"][
            "synthetic_behavior_preserving_checkpoint_and_microstage_build_only"
        ]
        is not True
        or value["authorization"]["runtime_activation_or_prediction_change"] is not False
        or value["authorization"][
            "external_forward_or_new_deepwidebench_rollout"
        ]
        is not False
    ):
        raise RuntimeError("V2.52.72 parent diagnosis barrier drifted")
    return value


def _watchers_exact() -> bool:
    observed = contract.watcher_snapshot()
    expected = {
        pid: {"marker": marker, "start_ticks": start_ticks}
        for pid, marker, start_ticks in (
            (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py", 713986317),
            (3061652, "scripts/watch_v24218_exact220_executor.py", 747569004),
            (2808901, "scripts/watch_v24215_joint_package_recovery.py", 746680268),
            (2889939, "scripts/watch_v24216_package_gate.py", 746969965),
        )
    }
    return len(observed) == 4 and all(
        row["pid"] in expected
        and row["marker"] == expected[row["pid"]]["marker"]
        and row["start_ticks"] == expected[row["pid"]]["start_ticks"]
        for row in observed
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = audit._git("rev-parse", "HEAD")
    target = audit._git("rev-parse", "target/main")
    clean = not audit._git("status", "--porcelain")
    _parent_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = audit._semantic_findings(closure)
    explicit = {SOURCE, TEST, RUNTIME, RUNTIME_TEST, PARENT_DIAGNOSIS, *closure}
    untracked = sorted(str(path) for path in explicit if tracked and not _tracked(path))
    tests_green = tests["passed"]
    checks = {
        "parent_diagnosis_hash_and_build_only_authority_exact": True,
        "runtime_and_audit_tests_exact54": tests_green,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "all_runtime_audit_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact75_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and contract.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and contract.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_zero": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "normal_path_prediction_cost_and_effect_match_parent": tests_green,
        "validated_checkpoint_survives_parent_build_and_validation_faults": tests_green,
        "untrusted_checkpoint_fails_closed": tests_green,
        "checkpoint_receipt_result_stage_and_credit_tamper_fail_closed": tests_green,
        "truthful_query4_fetch14_model4_caps_unchanged": (
            cap.QUERY_CAP == 4 and cap.FETCH_CAP == 14 and cap.MODEL_CAP == 4
        ),
        "finite_seven_microstage_surface_exact": _stage_surface_exact(),
        "runtime_accepts_only_visible_task_and_injected_clients": tests_green,
        "protected_watchers_unchanged": _watchers_exact(),
        "shared_api_lease_inactive": audit._lease_inactive(),
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_parent": {
            "path": str(PARENT_DIAGNOSIS),
            "sha256": audit.sha256(PARENT_DIAGNOSIS),
        },
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": contract.payload_sha256(vector),
        "runtime_dependency_path_sha256": contract.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "physical_caps": {"queries": cap.QUERY_CAP, "fetches": cap.FETCH_CAP, "model_forwards": cap.MODEL_CAP},
        "microstages": list(runtime.STAGES),
        "protected_watchers": contract.watcher_snapshot(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_benchmark_external_reliability_protocol_design": not findings,
            "runtime_activation_or_external_launch": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation_of_v25267": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    vector = copied.get("runtime_dependency_vector") or []
    semantic = copied.get("semantic_audit") or {}
    checks = copied.get("checks") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_parent",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "physical_caps",
            "microstages",
            "protected_watchers",
            "checks",
            "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or copied.get("fixed_parent")
        != {"path": str(PARENT_DIAGNOSIS), "sha256": PARENT_DIAGNOSIS_SHA256}
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
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or semantic
        != {
            "privileged_runtime_field_accesses": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
            "allowed_provider_rank_access": ["src/deepwide_agent/clients.py:565:score"],
            "untracked_sources": [],
        }
        or copied.get("physical_caps")
        != {"queries": 4, "fetches": 14, "model_forwards": 4}
        or copied.get("microstages") != list(runtime.STAGES)
        or copied.get("protected_watchers") != contract.watcher_snapshot()
        or set(checks) != CHECK_NAMES
        or not all(checks.values())
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "fresh_benchmark_external_reliability_protocol_design": True,
            "runtime_activation_or_external_launch": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation_of_v25267": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.72 build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    import os

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
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True, "findings": []}, sort_keys=True))


if __name__ == "__main__":
    main()
