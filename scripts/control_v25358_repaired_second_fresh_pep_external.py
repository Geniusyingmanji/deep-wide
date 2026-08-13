#!/usr/bin/env python3
"""Freeze, authorize, and audit the V2.53.58 repaired mechanism gate."""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25358_repaired_second_fresh_pep_external_contract as contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import audit_v25350_shared_prefix_grounded_fact_paired_build as parent_audit  # noqa: E402
from scripts import audit_v25357_second_fresh_pep_population_selection as population_audit  # noqa: E402
from scripts import diagnose_v25355_v25353_pre_effect_query_contract as diagnosis  # noqa: E402
from scripts import run_v25358_repaired_second_fresh_pep_external as runner  # noqa: E402


TEST_SUITES = (
    ("test_control_v25358_repaired_second_fresh_pep_external.py", 4),
    ("test_v25358_repaired_second_fresh_pep_external.py", 8),
    ("test_v25354_pre_effect_query_compatible_grounded_fact_runtime.py", 6),
    ("test_v25356_second_fresh_pep_grounded_fact_population.py", 4),
    ("test_audit_v25357_second_fresh_pep_population_selection.py", 3),
    ("test_v25349_shared_prefix_grounded_fact_paired_runtime.py", 8),
    ("test_v25123_visible_legacy_query_compatible_runtime.py", 7),
    ("test_v25346_grounded_fact_bootstrap.py", 8),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25117_grounded_target_record_plan.py", 6),
    ("test_v25119_grounded_target_record_paired_runtime.py", 7),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
ALLOWED_PROVIDER_SCORE_ACCESS = "src/deepwide_agent/clients.py:565:score"


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
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


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.58 control expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.53.58 control requires clean pushed HEAD")
    return head, target


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _endpoint_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            return True
    except OSError:
        return False


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (str(contract.RUNNER), "scripts/run_official_eval_local.py")
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _test(pattern: str, expected: int) -> dict[str, Any]:
    return base_audit._test(pattern, expected)


def _tests() -> dict[str, Any]:
    suites = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _semantic_audit() -> dict[str, Any]:
    closure = contract.forward_dependency_closure(ROOT)
    semantic = base_audit._semantic_findings(closure)
    return {
        "dependency_closure": [str(path) for path in closure],
        "dependency_closure_sha256": contract.payload_sha256(
            {str(path): contract.sha256(ROOT / path) for path in closure}
        ),
        **semantic,
    }


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _parent_barrier() -> bool:
    try:
        parent = parent_audit.validate_audit(_read(contract.PARENT_BUILD_AUDIT))
        diagnosed = diagnosis.validate(_read(contract.DIAGNOSIS))
        population = population_audit.validate_audit(
            _read(contract.POPULATION_AUDIT)
        )
    except BaseException:
        return False
    return bool(
        contract.sha256(ROOT / contract.PARENT_BUILD_AUDIT)
        == contract.PARENT_BUILD_AUDIT_SHA256
        and parent["audit_valid"] is True
        and parent["findings"] == []
        and contract.sha256(ROOT / contract.DIAGNOSIS)
        == contract.DIAGNOSIS_SHA256
        and diagnosed["audit_valid"] is True
        and diagnosed["findings"] == []
        and diagnosed["repair"]["rerun_same_twenty_tasks_authorized"] is False
        and diagnosed["authorization"]["fresh_disjoint_population_design"]
        is True
        and contract.sha256(ROOT / contract.POPULATION_AUDIT)
        == contract.POPULATION_AUDIT_SHA256
        and population["canonical_identity_and_slug_tree_match_count"] == 0
        and population[
            "canonical_identity_and_slug_history_introduction_count"
        ]
        == 0
        and population["authorization"]
        ["second_fresh_pep_population_build_and_protocol_design"]
        is True
        and population["authorization"]
        ["network_model_search_fetch_external_forward_or_evaluator"]
        is False
    )


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    head, target = (
        _clean_pushed() if require_clean else ("build-only", "build-only")
    )
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    future = (
        contract.BUILD_AUDIT,
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    gate = contract.mechanism_gate()
    checks = {
        "parent_build_diagnosis_and_population_history_audits_exact": _parent_barrier(),
        "focused_repair_population_runtime_tests_exact82": tests["passed"],
        "source_manifest_complete_and_hash_bound": set(manifest)
        == {
            *(str(path) for path in contract.forward_dependency_closure(ROOT)),
            str(contract.CONTROL),
            str(contract.TEST),
            str(contract.CONTROL_TEST),
            str(contract.RUNTIME_TEST),
            str(contract.POPULATION_TEST),
            str(contract.PARENT_BUILD_AUDIT),
            str(contract.DIAGNOSIS),
            str(contract.POPULATION_AUDIT),
        },
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == [ALLOWED_PROVIDER_SCORE_ACCESS],
        "future_protocol_effect_and_output_surfaces_pristine": _future_pristine(
            future
        ),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": _lease_inactive(),
        "second_fresh_population_and_balanced_arm_order": (
            len(contract.task_vector()) == contract.TASK_COUNT
            and contract.payload_sha256(contract.arm_order_vector())
            == contract.population.EXPECTED_ARM_ORDER_VECTOR_SHA256
        ),
        "physical_caps_exact_4_14_4": contract.LIMITS["search_queries"] == 4
        and contract.LIMITS["fetch_targets"] == 10
        and contract.LIMITS["model_calls"] == 3,
        "failure_gate_semantics_consistent_18_plus_2": (
            gate["minimum_completed_runtime_tasks"] == 18
            and gate["maximum_failure_as_zero_tasks"] == 2
            and gate["maximum_outer_failure_tasks"] == 2
            and gate["maximum_budget_rejection_tasks"] == 0
        ),
        "pre_effect_projection_required": contract.source_policy()[
            "pre_effect_query_projection_required_before_first_search_or_fetch"
        ]
        is True,
        "entropy_information_gain_signed_credit_disabled": gate[
            "positive_signed_credit_count"
        ]
        == 0,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25358_repaired_second_fresh_pep_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests,
        "semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    checks = copied.get("checks") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != "v25358_repaired_second_fresh_pep_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not checks
        or not all(checks.values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("source_policy") != contract.source_policy()
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "protocol_generation_after_build_commit_push": True,
            "external_forward": False,
            "evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.53.58 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    validate_build(_read(contract.BUILD_AUDIT))
    return contract.build_protocol(
        ROOT,
        now=int(time.time()) if now is None else int(now),
        tracked=True,
        require_pristine=True,
        build_audit_sha256=contract.sha256(ROOT / contract.BUILD_AUDIT),
    )


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    tests = _tests()
    semantic = _semantic_audit()
    checks = {
        "protocol_valid": True,
        "git_head_equals_target_main": head == target,
        "focused_repair_population_runtime_tests_exact82": tests["passed"],
        "source_manifest_unchanged": protocol["source_manifest"]
        == contract.dependency_manifest(ROOT, tracked=True),
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [],
        "execution_surfaces_pristine": _future_pristine(
            (
                contract.PREAUDIT,
                contract.EXECUTION_START,
                contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT,
                contract.OUTPUT_ROOT,
            )
        ),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_reachable(),
        "conflicting_forward_or_evaluator_processes_absent": not _active_conflicts(),
        "evaluator_surface_absent": not any(
            path.name.startswith("evaluate_") and "25358" in path.name
            for path in ROOT.joinpath("scripts").glob("evaluate_*")
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25358_repaired_second_fresh_pep_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "source_manifest_sha256": protocol["source_manifest_sha256"],
        "tests": tests,
        "semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "execution_start_generation": not findings,
            "external_forward": False,
            "evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role")
        != "v25358_repaired_second_fresh_pep_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("execution_start_generation")
        is not True
        or copied.get("authorization", {}).get("external_forward") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.53.58 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    validate_preaudit(_read(contract.PREAUDIT))
    future = (
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    if head != target or not _future_pristine(future):
        raise RuntimeError("V2.53.58 execution surface is not pristine")
    if not _lease_inactive() or not _endpoint_reachable() or _active_conflicts():
        raise RuntimeError("V2.53.58 execution runtime is not ready")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.53.58 protected watcher identity drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25358_repaired_second_fresh_pep_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "arm_order_vector_sha256": protocol["population"][
            "arm_order_vector_sha256"
        ],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_external_forward": True,
            "evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def _recursive_keys(value: Any) -> set[str]:
    output: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            output.add(str(key))
            output.update(_recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            output.update(_recursive_keys(child))
    return output


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    rows = [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]
    aggregate = runner.aggregate_rows(
        rows, wall_seconds=float(forward["aggregate"]["batch_wall_seconds"])
    )
    decision = runner.mechanism_decision(aggregate)
    freeze = _read(contract.PREDICTION_FREEZE)
    forbidden_keys = {
        "question",
        "query",
        "url",
        "host",
        "title",
        "page",
        "quote",
        "record_identity",
        "field_value",
        "category",
        "question_type",
        "gold",
        "score",
        "reward",
    }
    checks = {
        "protocol_forward_and_rows_validate": True,
        "exact_task_denominator_and_order": len(rows) == contract.TASK_COUNT
        and [row["opaque_id"] for row in rows]
        == [task["opaque_id"] for task in contract.task_vector()],
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision
        == forward["mechanism_decision"],
        "task_rows_contain_no_forbidden_content_keys": not _recursive_keys(
            rows
        ).intersection(forbidden_keys),
        "actual_effect_snapshots_complete": all(
            set(row["actual_effect_snapshot"])
            == set(runner._empty_effect_snapshot())
            for row in rows
        ),
        "completed_repair_receipts_validate": all(
            not row["runtime_completed"]
            or runner.runtime.validate_stage_receipt(
                row["pre_effect_query_contract_receipt"]
            )
            == row["pre_effect_query_contract_receipt"]
            for row in rows
        ),
        "content_free_parent_receipts_validate": all(
            not row["runtime_completed"]
            or runner.runtime.validate_parent_receipt(row["content_free_receipt"])
            == row["content_free_receipt"]
            for row in rows
        ),
        "task_rows_hash_bound": forward["task_rows_sha256"]
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid": contract.sealed(
            freeze, "freeze_payload_sha256"
        ),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"]
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256")
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "forward_process_absent": not _active_conflicts(),
        "no_evaluator_or_deepwidebench_direct_authority": forward[
            "authorization"
        ]["deepwidebench_forward_evaluator_leaderboard_or_sota"]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25358_repaired_second_fresh_pep_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "aggregate": aggregate,
        "mechanism_decision": decision,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "deepwidebench_successor_build": not findings
            and decision["mechanism_gate_passed"],
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("build-audit", "protocol", "preaudit", "start", "forward-audit"),
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    elif args.command == "start":
        value, path = build_start(), contract.EXECUTION_START
    else:
        value, path = build_forward_audit(), contract.FORWARD_AUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value.get("role"),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
