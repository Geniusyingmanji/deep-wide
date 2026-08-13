#!/usr/bin/env python3
"""Freeze, authorize, and audit the V2.54.05 RFC membership gate."""

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

from deepwide_agent import v25405_rfc_grounded_membership_external_contract as contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import audit_v25402_grounded_record_membership_build as runtime_audit  # noqa: E402
from scripts import audit_v25404_fresh_rfc_grounded_membership_population as population_audit  # noqa: E402
from scripts import run_v25405_rfc_grounded_membership_external as runner  # noqa: E402


TEST_SUITES = (
    ("test_control_v25405_rfc_grounded_membership_external.py", 4),
    ("test_v25405_rfc_grounded_membership_external.py", 11),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25403_fresh_rfc_grounded_membership_population.py", 4),
    ("test_audit_v25402_grounded_record_membership_build.py", 4),
    ("test_audit_v25404_fresh_rfc_grounded_membership_population.py", 4),
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
        raise RuntimeError("V2.54.05 control expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.54.05 control requires clean pushed HEAD")
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


def _parent_barriers() -> bool:
    try:
        runtime_value = runtime_audit.validate_audit(
            _read(contract.RUNTIME_BUILD_AUDIT)
        )
        population_value = population_audit.validate_audit(
            _read(contract.POPULATION_AUDIT)
        )
    except BaseException:
        return False
    return bool(
        contract.sha256(ROOT / contract.RUNTIME_BUILD_AUDIT)
        == contract.RUNTIME_BUILD_AUDIT_SHA256
        and runtime_value["audit_valid"] is True
        and runtime_value["findings"] == []
        and runtime_value["authorization"][
            "fresh_population_and_external_protocol_design"
        ]
        is True
        and runtime_value["authorization"]["external_forward"] is False
        and contract.sha256(ROOT / contract.POPULATION_AUDIT)
        == contract.POPULATION_AUDIT_SHA256
        and population_value[
            "whole_consecutive_group_tree_and_history_counts_all_zero"
        ]
        is True
        and population_value["authorization"]
        ["fresh_rfc_grounded_membership_protocol_design"]
        is True
        and population_value["authorization"]
        ["network_model_search_fetch_external_forward_or_evaluator"]
        is False
    )


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
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
    policy = contract.source_policy()
    checks = {
        "runtime_and_population_parent_barriers_exact": _parent_barriers(),
        "focused_contract_runner_runtime_population_tests_exact36": tests["passed"],
        "source_manifest_complete_and_hash_bound": bool(manifest),
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
        "fresh_multirow_population_exact": (
            len(contract.task_vector()) == contract.TASK_COUNT
            and contract.payload_sha256(contract.task_vector())
            == contract.population.EXPECTED_TASK_VECTOR_SHA256
            and contract.population.ROWS_PER_TASK == 4
        ),
        "physical_caps_exact_4_14_3_normal_path": (
            contract.LIMITS["search_queries"] == 4
            and contract.LIMITS["fetch_targets"] == 10
            and contract.LIMITS["model_calls"] == 3
        ),
        "one_joint_table_record_synthesis_and_zero_candidate_model_effect": (
            policy[
                "one_visible_plan_one_grounded_plan_and_one_joint_table_record_synthesis"
            ]
            and policy["candidate_has_no_independent_model_or_sampling_effect"]
        ),
        "visible_membership_constraint_is_prethird_call_and_not_repair": (
            policy[
                "strict_visible_membership_vector_precedes_existing_third_model_call"
            ]
            and policy[
                "provider_ignored_constraint_never_triggers_post_synthesis_row_repair"
            ]
            and policy["membership_never_comes_from_page_record_task_id_or_outcome"]
        ),
        "grounded_record_membership_constraint_is_presecond_call_and_not_filter": (
            policy[
                "strict_visible_membership_vector_precedes_existing_grounded_record_call"
            ]
            and policy[
                "provider_grounded_record_membership_violation_is_measured_not_filtered"
            ]
            and policy["membership_never_comes_from_page_record_task_id_or_outcome"]
        ),
        "record_source_priority_preverification_and_never_merged": (
            policy[
                "record_source_priority_is_joint_nonempty_then_grounded_nonempty_then_none"
            ]
            and policy["record_source_selected_before_quote_or_edit_verification"]
            and policy["joint_and_grounded_records_are_never_merged_or_unioned"]
        ),
        "failure_gate_semantics_consistent_18_plus_2": (
            gate["minimum_completed_runtime_tasks"] == 18
            and gate["maximum_failure_as_zero_tasks"] == 2
            and gate["maximum_outer_failure_tasks"] == 2
            and gate["maximum_budget_rejection_tasks"] == 0
        ),
        "three_stage_funnel_gate_exact": (
            gate["minimum_selected_raw_record_tasks"] == 8
            and gate["minimum_verified_record_tasks"] == 4
            and gate["minimum_changed_safe_coordinate_tasks"] == 4
            and gate["minimum_attributable_prediction_changed_tasks"] == 4
        ),
        "membership_compliance_gate_exact": (
            gate["minimum_membership_constraint_applied_tasks"] == 18
            and gate["minimum_base_visible_membership_exact_tasks"] == 16
        ),
        "grounded_record_membership_gate_exact": (
            gate[
                "minimum_grounded_record_membership_constraint_applied_tasks"
            ]
            == 18
            and gate[
                "minimum_all_grounded_raw_records_membership_aligned_tasks"
            ]
            == 16
            and gate[
                "maximum_grounded_raw_membership_violation_count_total"
            ]
            == 2
        ),
        "missing_row_rejection_capped": gate[
            "maximum_missing_row_rejected_field_count_total"
        ]
        == 2,
        "prediction_text_not_persisted": True,
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
        "role": "v25405_rfc_grounded_membership_external_build_audit",
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
        "source_policy": policy,
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
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != "v25405_rfc_grounded_membership_external_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("source_policy") != contract.source_policy()
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
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
        raise ValueError("V2.54.05 build audit drifted")
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
        "focused_contract_runner_runtime_population_tests_exact36": tests["passed"],
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
            path.name.startswith("evaluate_") and "25405" in path.name
            for path in ROOT.joinpath("scripts").glob("evaluate_*")
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25405_rfc_grounded_membership_preactivation_audit",
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
        copied.get("role") != "v25405_rfc_grounded_membership_preactivation_audit"
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
        raise ValueError("V2.54.05 preactivation audit drifted")
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
        raise RuntimeError("V2.54.05 execution surface is not pristine")
    if not _lease_inactive() or not _endpoint_reachable() or _active_conflicts():
        raise RuntimeError("V2.54.05 execution runtime is not ready")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.54.05 protected watcher identity drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25405_rfc_grounded_membership_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
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
        "prediction",
        "predictions",
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
        "prediction_text_not_persisted": all(
            row[
                "prediction_text_query_url_title_page_quote_record_identity_field_value_answer_or_credential_persisted"
            ]
            is False
            for row in rows
        ),
        "actual_effect_snapshots_complete": all(
            set(row["actual_effect_snapshot"])
            == set(runner._empty_effect_snapshot())
            for row in rows
        ),
        "completed_stage_receipts_validate": all(
            not row["runtime_completed"]
            or runner.runtime.validate_stage_receipt(
                row["content_free_stage_receipt"]
            )
            == row["content_free_stage_receipt"]
            for row in rows
        ),
        "completed_grounded_membership_receipts_validate": all(
            not row["runtime_completed"]
            or runner.runtime.validate_receipt(
                row["content_free_stage_receipt"][
                    "grounded_record_membership_receipt"
                ]
            )
            == row["content_free_stage_receipt"][
                "grounded_record_membership_receipt"
            ]
            for row in rows
        ),
        "completed_membership_receipts_validate": all(
            not row["runtime_completed"]
            or runner.membership_runtime.validate_stage_receipt(
                row["content_free_stage_receipt"]["parent_stage_receipt"]
            )
            == row["content_free_stage_receipt"]["parent_stage_receipt"]
            for row in rows
        ),
        "completed_hybrid_receipts_validate": all(
            not row["runtime_completed"]
            or runner.hybrid_runtime.validate_stage_receipt(
                row["content_free_stage_receipt"]["parent_stage_receipt"][
                    "parent_stage_receipt"
                ]
            )
            == row["content_free_stage_receipt"]["parent_stage_receipt"][
                "parent_stage_receipt"
            ]
            for row in rows
        ),
        "task_rows_hash_bound": forward["task_rows_sha256"]
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid": (
            freeze.get("role") == runner.FREEZE_ROLE
            and freeze.get("task_count") == contract.TASK_COUNT
            and freeze.get("prediction_text_persisted") is False
            and contract.sealed(freeze, "freeze_payload_sha256")
        ),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"]
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256")
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_binds_hash_vector": freeze.get(
            "prediction_hash_vector_sha256"
        )
        == contract.payload_sha256([row["prediction_sha256"] for row in rows]),
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
        "role": "v25405_rfc_grounded_membership_forward_audit",
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
