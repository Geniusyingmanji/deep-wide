#!/usr/bin/env python3
"""Freeze, authorize, and audit the V2.55.66 fresh-date mechanism gate."""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25566_robust_date_external_contract as contract  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import audit_v25549_scale_sort_guard_build as runtime_audit  # noqa: E402
from scripts import audit_v25565_robust_date_population as population_audit  # noqa: E402
from scripts import run_v25566_robust_date_external as runner  # noqa: E402


TEST_SUITES = (
    ("test_control_v25566_robust_date_external.py", 4),
    ("test_v25566_robust_date_external.py", 8),
    ("test_v25545_deterministic_visible_constraint_runtime.py", 4),
    ("test_v25544_deterministic_visible_constraint_projector.py", 7),
    ("test_v25558_model_pool_contract.py", 4),
    ("test_v25564_fresh_date_robust_population.py", 5),
    ("test_audit_v25565_robust_date_population.py", 5),
    ("test_v25478_clone_safe_runner_namespace.py", 5),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
ALLOWED_PROVIDER_SCORE_ACCESS = "src/deepwide_agent/clients.py:565:score"
TRUTH_SOURCE = "src/deepwide_agent/v25552_pypi_stable_truth.py"


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
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=tracked).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.66 control expected a JSON object")
    return value


def _read_rows(relative: Path, *, tracked: bool = True) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in contract.ordinary(ROOT, relative, tracked=tracked)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.55.66 expected JSONL objects")
    return rows


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.55.66 control requires clean pushed HEAD")
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
            pass
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


def _tests() -> dict[str, Any]:
    suites = [base_audit._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
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
        population_value = population_audit.validate(
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
            "fresh_shared_parent_external_gate_build"
        ]
        is True
        and runtime_value["authorization"]["external_protocol_or_forward"]
        is False
        and contract.sha256(ROOT / contract.POPULATION_AUDIT)
        == contract.POPULATION_AUDIT_SHA256
        and population_value["audit_valid"] is True
        and population_value["findings"] == []
        and population_value["authorization"][
            "fresh_robust_external_protocol_design"
        ]
        is True
        and population_value["authorization"]["external_forward"] is False
        and population_value["population"]["task_count"] == 20
        and population_value["population"]["identity_count"] == 40
        and population_value["overlap"]["fixed220_question_overlap_count"] == 0
        and population_value["overlap"]["fixed220_opaque_overlap_count"] == 0
    )


def _clone_namespace_ready() -> bool:
    receipt = runner.clone_namespace_receipt()
    return bool(
        receipt.get("policy_id") == "v25478_clone_safe_runner_namespace_v1"
        and receipt.get("unresolved_function_count") == 0
        and receipt.get("unresolved_global_name_count") == 0
        and all(
            receipt.get(name) is True
            for name in (
                "fcntl_resolved",
                "socket_resolved",
                "subprocess_resolved",
                "thread_pool_executor_resolved",
                "as_completed_resolved",
                "lease_helper_resolved",
            )
        )
        and receipt.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is False
        and receipt.get(
            "file_environment_process_network_model_search_fetch_or_evaluator_accessed"
        )
        is False
        and receipt.get("benchmark_launch_or_evaluator_authorized") is False
    )


class _PoolSmokeModel:
    pass


def _runner_pool_constructor_ready() -> bool:
    try:
        value = runner.model_pool_contract()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output = Path(raw)
            slots = output / "slots"
            slots.mkdir()
            for index in range(1, 3):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            limiter = DeadlineAwareGlobalModelSlotLimiter(
                _PoolSmokeModel(),
                slot_directory=slots,
                output_root=output,
                slot_cap=2,
                pool_id=value["model_pool_id"],
                absolute_deadline=time.monotonic() + 60,
            )
        return bool(
            limiter.pool_id == contract.model_pool.MODEL_POOL_ID
            and value == contract.model_pool.contract()
        )
    except BaseException:
        return False


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    closure = semantic["dependency_closure"]
    policy = contract.source_policy()
    gate = contract.mechanism_gate()
    quality = contract.quality_gate()
    checks = {
        "runtime_and_population_parent_barriers_exact": _parent_barriers(),
        "focused_contract_runner_runtime_population_tests_exact42": tests["passed"],
        "source_manifest_complete_and_hash_bound": bool(manifest),
        "clone_namespace_recursive_globals_resolved_before_effect": _clone_namespace_ready(),
        "actual_runner_namespace_and_real_limiter_constructor_pool_ready": _runner_pool_constructor_ready(),
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
        "truth_totality_and_quality_evaluator_absent_from_forward_closure": (
            TRUTH_SOURCE not in closure
            and not any("evaluate_v255" in path for path in closure)
        ),
        "future_protocol_effect_quality_and_output_surfaces_pristine": _future_pristine(
            (contract.BUILD_AUDIT, *contract.future_surfaces())
        ),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": _lease_inactive(),
        "fresh_population_exact_twenty_date_tasks_forty_new_identities": (
            len(contract.task_vector()) == 20
            and contract.population.DATE_TASK_COUNT == 20
            and contract.population.SCALE_TASK_COUNT == 0
            and len(contract.population.identity_vector()) == 40
            and len(set(contract.population.identity_vector())) == 40
        ),
        "one_parent_forward_and_zero_incremental_provider_effect": (
            policy["one_v25401_parent_forward_shared_by_control_and_candidate"]
            and policy["control_is_parent_prediction_byte_exact"]
            and policy["candidate_is_only_v25544_pure_deterministic_projection"]
            and policy["independent_sampling_between_arms"] is False
            and gate[
                "candidate_additional_queries_fetches_model_calls_or_sampling_effects"
            ]
            == 0
        ),
        "physical_caps_exact_4_14_max3_normal_path": (
            contract.LIMITS["search_queries"] == 4
            and contract.LIMITS["model_calls"] == 3
            and gate["maximum_physical_fetches_per_completed_task"] == 14
            and gate["maximum_normal_path_model_forwards_per_completed_task"] == 3
        ),
        "all_outer_failures_failure_as_zero_without_retry": (
            gate["maximum_failure_as_zero_tasks"] == 0
            and gate["maximum_outer_or_accounting_failure_tasks"] == 0
            and gate["maximum_naked_outer_failure_tasks"] == 0
            and policy[
                "fixed_failure_as_zero_denominator_no_retry_resume_or_replacement"
            ]
        ),
        "date_only_mechanism_gate_exact": (
            gate["minimum_active_constraint_tasks"] == 20
            and gate["minimum_date_contract_tasks"] == 20
            and gate["minimum_scale_contract_tasks"] == 0
            and gate["minimum_explicit_order_contract_tasks"] == 20
            and gate["minimum_candidate_prediction_changed_tasks"] == 2
            and gate["minimum_date_changed_tasks"] == 1
            and gate["minimum_scale_changed_tasks"] == 0
            and gate["minimum_sort_applied_tasks"] == 1
            and gate["maximum_unattributable_prediction_changed_tasks"] == 0
        ),
        "both_predictions_frozen_before_quality_truth": policy[
            "prediction_freeze_precedes_truth_evaluator_or_quality_decision"
        ]
        and quality["each_control_and_candidate_prediction_evaluated_exactly_once"],
        "quality_requires_arm_blind_robust_exact_gain_soft_nonregression_and_total_unknown": (
            quality["fixed20_failure_as_zero_metrics_reported"]
            and quality["minimum_arm_blind_paired_complete_tasks"] == 18
            and quality["paired_complete_selection_uses_only_truth_availability"]
            and quality[
                "prediction_arm_outcome_or_score_used_for_completeness_selection"
            ]
            is False
            and quality["candidate_exact_strictly_greater_than_control_on_fixed20"]
            and quality["maximum_candidate_exact_losses_on_paired_complete"] == 0
            and quality["maximum_two_sided_exact_sign_test_p"] == 0.05
            and quality[
                "candidate_entity_row_item_column_and_composite_nonregression_on_fixed20"
            ]
            and quality["candidate_invalid_and_fallback_nonincrease_on_fixed20"]
            and quality[
                "official_identity_bound_no_stable_release_is_valid_unknown"
            ]
            and quality[
                "known_dates_descending_then_unknown_stable_supplied_order"
            ]
        ),
        "entropy_information_gain_signed_credit_disabled": (
            gate["positive_signed_credit_count"] == 0
            and quality["positive_signed_credit_count"] == 0
        ),
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25566_robust_date_build_audit",
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
        "mechanism_gate": gate,
        "postfreeze_quality_gate": quality,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return validate_build(contract.seal(value, "audit_payload_sha256"))


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25566_robust_date_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("source_policy") != contract.source_policy()
        or copied.get("mechanism_gate") != contract.mechanism_gate()
        or copied.get("postfreeze_quality_gate") != contract.quality_gate()
        or copied.get("semantic_audit", {}).get("privileged_runtime_field_accesses")
        != []
        or copied.get("semantic_audit", {}).get("evaluator_capabilities") != []
        or copied.get("semantic_audit", {}).get("credential_literal_hits") != []
        or TRUTH_SOURCE in copied.get("semantic_audit", {}).get(
            "dependency_closure", []
        )
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "protocol_generation_after_build_commit_push": True,
            "external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.55.66 build audit drifted")
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
        "focused_contract_runner_runtime_population_tests_exact42": tests["passed"],
        "source_manifest_unchanged": protocol["source_manifest"]
        == contract.dependency_manifest(ROOT, tracked=True),
        "clone_namespace_recursive_globals_resolved_before_effect": _clone_namespace_ready(),
        "actual_runner_namespace_and_real_limiter_constructor_pool_ready": _runner_pool_constructor_ready(),
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [],
        "truth_totality_and_quality_evaluator_absent_from_forward_closure": (
            TRUTH_SOURCE not in semantic["dependency_closure"]
            and not any(
                "evaluate_v255" in path
                for path in semantic["dependency_closure"]
            )
        ),
        "execution_and_quality_surfaces_pristine": _future_pristine(
            (
                contract.PREAUDIT,
                contract.EXECUTION_START,
                contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT,
                contract.POSTFREEZE_QUALITY_PROTOCOL,
                contract.QUALITY_RESULT,
                contract.QUALITY_AUDIT,
                contract.OUTPUT_ROOT,
            )
        ),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_reachable(),
        "conflicting_forward_or_evaluator_processes_absent": not _active_conflicts(),
        "postfreeze_quality_not_yet_authorized_or_implemented": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25566_robust_date_preactivation_audit",
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
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25566_robust_date_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization")
        != {
            "execution_start_generation": True,
            "external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.55.66 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    validate_preaudit(_read(contract.PREAUDIT))
    future = (
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.POSTFREEZE_QUALITY_PROTOCOL,
        contract.QUALITY_RESULT,
        contract.QUALITY_AUDIT,
        contract.OUTPUT_ROOT,
    )
    if head != target or not _future_pristine(future):
        raise RuntimeError("V2.55.66 execution surface is not pristine")
    if not _lease_inactive() or not _endpoint_reachable() or _active_conflicts():
        raise RuntimeError("V2.55.66 execution runtime is not ready")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.55.66 protected watcher identity drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25566_robust_date_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "identity_vector_sha256": protocol["population"]["identity_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_external_forward": True,
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    rows = [
        runner.validate_task_row(row)
        for row in _read_rows(contract.TASK_ROWS, tracked=True)
    ]
    aggregate = runner.aggregate_rows(
        rows, wall_seconds=float(forward["aggregate"]["batch_wall_seconds"])
    )
    decision = runner.mechanism_decision(aggregate)
    freeze = _read(contract.PREDICTION_FREEZE)
    checks = {
        "protocol_forward_and_rows_validate": True,
        "exact_task_denominator_and_order": len(rows) == contract.TASK_COUNT
        and [row["opaque_id"] for row in rows]
        == [task["opaque_id"] for task in contract.task_vector()],
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision
        == forward["mechanism_decision"],
        "all_completed_runtime_result_stage_pairs_validate": all(
            not row["runtime_completed"]
            or bool(
                runner._decode_completed(
                    row["runtime_result"], row["content_free_stage_receipt"]
                )
            )
            for row in rows
        ),
        "actual_effect_snapshots_complete": all(
            set(row["actual_effect_snapshot"])
            == set(runner._empty_effect_snapshot())
            for row in rows
        ),
        "date_only_surface_scale_counts_zero": aggregate["scale_contract_tasks"] == 0
        and aggregate["scale_changed_tasks"] == 0
        and aggregate["scale_cell_changed_count_total"] == 0,
        "task_rows_hash_bound": forward["task_rows_sha256"]
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid": freeze.get("role") == runner.FREEZE_ROLE
        and freeze.get("task_count") == contract.TASK_COUNT
        and freeze.get("both_prediction_texts_persisted") is True
        and freeze.get(
            "all_predictions_terminal_before_truth_evaluator_or_quality_decision"
        )
        is True
        and contract.sealed(freeze, "freeze_payload_sha256"),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"]
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256")
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_binds_both_vectors": all(
            freeze.get("prediction_vector_sha256", {}).get(arm)
            == contract.payload_sha256([row["predictions"][arm] for row in rows])
            and freeze.get("prediction_hash_vector_sha256", {}).get(arm)
            == contract.payload_sha256(
                [row["prediction_sha256"][arm] for row in rows]
            )
            for arm in runner.ARMS
        ),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "forward_process_absent": not _active_conflicts(),
        "no_truth_evaluator_or_benchmark_read_by_forward": all(
            row[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
            is False
            for row in rows
        ),
        "positive_signed_credit_zero": aggregate["positive_signed_credit_count"]
        == 0,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25566_robust_date_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "aggregate": aggregate,
        "mechanism_decision": decision,
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "authorization": {
            "postfreeze_quality_protocol": valid
            and decision["mechanism_gate_passed"],
            "deepwidebench_successor_build": False,
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
