#!/usr/bin/env python3
"""Run the single authorized V2.53.58 repaired fresh-PEP forward."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25354_pre_effect_query_compatible_grounded_fact_runtime as runtime  # noqa: E402
from deepwide_agent import v25358_repaired_second_fresh_pep_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
    validate_search_class,
)
from scripts import run_v25353_fresh_pep_grounded_fact_external as base_runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.58 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.53.58 expected JSONL objects")
    return rows


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
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


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.53.58 requires clean pushed HEAD")


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


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    expected = {
        "one_external_forward": True,
        "evaluator": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    if (
        start.get("role")
        != "v25358_repaired_second_fresh_pep_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("arm_order_vector_sha256")
        != protocol["population"]["arm_order_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization") != expected
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.53.58 execution start drifted")
    return protocol, start


def _prepare_output() -> None:
    root = ROOT / contract.OUTPUT_ROOT
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    slots = ROOT / contract.MODEL_SLOT_DIRECTORY
    slots.mkdir(mode=0o700)
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        _publish_json(
            slots / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v25358_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _search(question: str, deadline: float) -> RobustLatePageBoundSearchClient:
    return RobustLatePageBoundSearchClient(
        contract.SEARCH["proxy_url"],
        contract.SEARCH["model"],
        visible_question=question,
        reasoning_effort=contract.SEARCH["reasoning_effort"],
        service_tier=contract.SEARCH["service_tier"],
        timeout=contract.SEARCH["timeout_seconds"],
        max_retries=contract.SEARCH["max_retries"],
        absolute_deadline=deadline,
        cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        max_workers=contract.SEARCH["workers"],
        batch_size=contract.SEARCH["batch_size"],
        search_context_size=contract.SEARCH["context_size"],
        max_output_tokens=contract.SEARCH["max_output_tokens"],
        fetch_pages=False,
        fetch_workers=contract.SEARCH["fetch_workers"],
        fetch_timeout=contract.SEARCH["fetch_timeout_seconds"],
        max_page_chars=contract.LIMITS["page_chars"],
        hard_fetch_deadline_seconds=contract.SEARCH[
            "hard_fetch_deadline_seconds"
        ],
        stage_callback=lambda _event: None,
    )


_empty_effect_snapshot = base_runner._empty_effect_snapshot
_effect_snapshot = base_runner._effect_snapshot
_health = base_runner._health
_health_snapshot = base_runner._health_snapshot


def _base_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop("pre_effect_query_contract_receipt", None)
    copied["role"] = "v25353_fresh_pep_grounded_fact_external_task_result"
    copied["protocol_id"] = base_runner.contract.PROTOCOL_ID
    copied.pop("result_payload_sha256", None)
    return base_runner.contract.seal(copied, "result_payload_sha256")


def _runtime_result_from_row(
    row: Mapping[str, Any], stage: Mapping[str, Any]
) -> dict[str, Any]:
    parent: dict[str, Any] = {
        "artifact_version": 1,
        "role": runtime.parent.ROLE,
        "policy_id": runtime.parent.POLICY_ID,
        "opaque_id": row["opaque_id"],
        "status": "terminal",
        "predictions": copy.deepcopy(row["predictions"]),
        "prediction_sha256": copy.deepcopy(row["prediction_sha256"]),
        "model_success": copy.deepcopy(row["model_success"]),
        "normalizer_status": copy.deepcopy(row["normalizer_status"]),
        "failure_types": copy.deepcopy(row["failure_types"]),
        "prediction_changed": row["prediction_changed"],
        "candidate_production_prompt_changed": row[
            "candidate_production_prompt_changed"
        ],
        "attributable_prediction_change": row[
            "attributable_prediction_change"
        ],
        "unattributable_prediction_change": row[
            "unattributable_prediction_change"
        ],
        "elapsed_seconds": row["elapsed_seconds"],
        "cost": copy.deepcopy(row["cost"]),
        "content_free_receipt": copy.deepcopy(row["content_free_receipt"]),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    parent["result_payload_sha256"] = contract.payload_sha256(parent)
    if stage.get("parent_result_payload_sha256") != parent["result_payload_sha256"]:
        raise ValueError("V2.53.58 repair receipt parent binding drifted")
    value = copy.deepcopy(parent)
    value["role"] = runtime.ROLE
    value["policy_id"] = runtime.POLICY_ID
    value["pre_effect_query_contract_receipt"] = copy.deepcopy(dict(stage))
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = contract.payload_sha256(value)
    return runtime.validate_result(value)


def _terminal_outer_failure(
    task: Mapping[str, str],
    arm_order: Sequence[str],
    exc: BaseException,
    elapsed: float,
    *,
    budget: cap.PhysicalEffectBudget | None,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    row = base_runner._terminal_outer_failure(
        task,
        arm_order,
        exc,
        elapsed,
        budget=budget,
        health=health,
    )
    row["role"] = "v25358_repaired_second_fresh_pep_task_result"
    row["protocol_id"] = contract.PROTOCOL_ID
    row["pre_effect_query_contract_receipt"] = None
    row.pop("result_payload_sha256", None)
    row = contract.seal(row, "result_payload_sha256")
    return validate_task_row(row)


def _from_runtime(
    task: Mapping[str, str],
    arm_order: Sequence[str],
    value: Mapping[str, Any],
    *,
    budget: cap.PhysicalEffectBudget,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    checked = runtime.validate_result(value)
    if checked["opaque_id"] != task["opaque_id"]:
        raise RuntimeError("V2.53.58 runtime task identity drifted")
    stage = runtime.validate_stage_receipt(
        checked["pre_effect_query_contract_receipt"]
    )
    parent = copy.deepcopy(checked)
    parent.pop("pre_effect_query_contract_receipt")
    parent["role"] = runtime.parent.ROLE
    parent["policy_id"] = runtime.parent.POLICY_ID
    parent["result_payload_sha256"] = stage["parent_result_payload_sha256"]
    parent = runtime.validate_parent_result(parent)
    row = base_runner._from_runtime(
        task,
        arm_order,
        parent,
        budget=budget,
        health=health,
    )
    row["role"] = "v25358_repaired_second_fresh_pep_task_result"
    row["protocol_id"] = contract.PROTOCOL_ID
    row["pre_effect_query_contract_receipt"] = copy.deepcopy(stage)
    row.pop("result_payload_sha256", None)
    row = contract.seal(row, "result_payload_sha256")
    return validate_task_row(row)


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25358_repaired_second_fresh_pep_task_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.53.58 task row envelope drifted")
    base = base_runner.validate_task_row(_base_row(copied))
    stage = copied.get("pre_effect_query_contract_receipt")
    if copied.get("runtime_completed") is True:
        if not isinstance(stage, Mapping):
            raise ValueError("V2.53.58 completed row omitted repair receipt")
        checked_stage = runtime.validate_stage_receipt(stage)
        _runtime_result_from_row(copied, checked_stage)
    elif stage is not None:
        raise ValueError("V2.53.58 outer failure retained repair receipt")
    if set(copied) != {*set(base), "pre_effect_query_contract_receipt"}:
        raise ValueError("V2.53.58 task row surface drifted")
    return copied


def run_one_task(
    task: Mapping[str, str], arm_order: Sequence[str]
) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.53.58 runtime input must be opaque_id and question")
    started = time.monotonic()
    outer_model: Any = None
    searches: dict[str, Any] = {}
    budget: cap.PhysicalEffectBudget | None = None
    try:
        limits = ScoreFirstLimits(**contract.LIMITS)
        deadline = started + float(contract.LIMITS["wall_seconds"])
        inner = HardTotalWallResponsesClient(
            contract.MODEL["proxy_url"],
            contract.MODEL["name"],
            reasoning_effort=contract.MODEL["reasoning_effort"],
            service_tier=contract.MODEL["service_tier"],
            timeout=contract.MODEL["timeout_seconds"],
            max_retries=contract.MODEL["max_retries"],
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
            stage_callback=lambda _event: None,
        )
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
            output_root=ROOT / contract.OUTPUT_ROOT,
            slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        budget = cap.PhysicalEffectBudget()
        outer_model = runtime.PreEffectQueryCompatibleHardCappedModel(
            bounded,
            budget,
            question=str(task["question"]),
            limits=limits,
        )
        searches = {
            phase: cap.HardCappedSearchClient(
                _search(str(task["question"]), deadline), budget, phase=phase
            )
            for phase in runtime.PHASES
        }
        result = runtime.run_paired_task(
            task,
            model=outer_model,
            searches=searches,
            limits=limits,
            budget=budget,
            arm_order=arm_order,
            monotonic=time.monotonic,
        )
        row = _from_runtime(
            task,
            arm_order,
            result,
            budget=budget,
            health=_health_snapshot(outer_model, searches),
        )
    except BaseException as exc:
        row = _terminal_outer_failure(
            task,
            arm_order,
            exc,
            time.monotonic() - started,
            budget=budget,
            health=_health_snapshot(outer_model, searches),
        )
    return validate_task_row(row)


def _hard_failure_count(row: Mapping[str, Any]) -> int:
    return sum(int(value) for value in row["hard_failure_health"].values())


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in contract.task_vector()]
        or [row["arm_order"] for row in checked] != contract.arm_order_vector()
    ):
        raise RuntimeError("V2.53.58 fixed population order drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    repairs = [row["pre_effect_query_contract_receipt"] for row in completed]
    facts = [receipt["grounded_fact_receipt"] for receipt in receipts]
    health_names = set(_health())
    unrecoverable_names = health_names - {"search_request_failures"}
    return {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "first_wave_completed_tasks": sum(
            receipt["first_wave_completed"] for receipt in receipts
        ),
        "grounded_plan_provider_success_tasks": sum(
            receipt["grounded_plan_model_call_success"] for receipt in receipts
        ),
        "both_arms_model_success_tasks": sum(
            receipt["both_arms_model_success"] for receipt in receipts
        ),
        "candidate_prompt_changed_tasks": sum(
            receipt["candidate_production_prompt_changed"] for receipt in receipts
        ),
        "verified_record_tasks": sum(
            fact["verified_record_count"] > 0 for fact in facts
        ),
        "verified_record_count_total": sum(
            fact["verified_record_count"] for fact in facts
        ),
        "verified_field_count_total": sum(
            fact["verified_field_count"] for fact in facts
        ),
        "attributable_prediction_changed_tasks": sum(
            receipt["attributable_prediction_change"] for receipt in receipts
        ),
        "unattributable_prediction_changed_tasks": sum(
            receipt["unattributable_prediction_change"] for receipt in receipts
        ),
        "pre_effect_projection_completed_tasks": len(repairs),
        "visible_fallback_query_seed_tasks": sum(
            repair["visible_fallback_query_seed_used"] for repair in repairs
        ),
        "plan_output_validation_failed_tasks": sum(
            repair["plan_output_validation_failed"] for repair in repairs
        ),
        "plan_model_effect_failed_tasks": sum(
            repair["plan_model_effect_failed"] for repair in repairs
        ),
        "outer_failure_tasks": sum(not row["runtime_completed"] for row in checked),
        "budget_rejection_tasks": sum(
            any(
                row["actual_effect_snapshot"][name] > 0
                for name in (
                    "query_rejected_count",
                    "fetch_rejected_count",
                    "model_rejected_count",
                )
            )
            for row in checked
        ),
        "search_request_failure_count": sum(
            row["hard_failure_health"]["search_request_failures"]
            for row in checked
        ),
        "unrecoverable_hard_failure_tasks": sum(
            any(row["hard_failure_health"][name] > 0 for name in unrecoverable_names)
            for row in checked
        ),
        "hard_failure_count": sum(_hard_failure_count(row) for row in checked),
        "completed_physical_queries": sum(
            row["actual_effect_snapshot"]["query_admitted_count"]
            for row in completed
        ),
        "completed_physical_fetches": sum(
            row["actual_effect_snapshot"]["fetch_admitted_count"]
            for row in completed
        ),
        "completed_physical_model_forwards": sum(
            row["actual_effect_snapshot"]["model_admitted_count"]
            for row in completed
        ),
        "all_physical_queries": sum(
            row["actual_effect_snapshot"]["query_admitted_count"]
            for row in checked
        ),
        "all_physical_fetches": sum(
            row["actual_effect_snapshot"]["fetch_admitted_count"]
            for row in checked
        ),
        "all_physical_model_forwards": sum(
            row["actual_effect_snapshot"]["model_admitted_count"]
            for row in checked
        ),
        "per_task_hard_cap_preserved_tasks": sum(
            row["actual_effect_snapshot"]["query_admitted_count"] <= 4
            and row["actual_effect_snapshot"]["fetch_admitted_count"] <= 14
            and row["actual_effect_snapshot"]["model_admitted_count"] <= 4
            for row in checked
        ),
        "equal_prompt_character_tasks": sum(
            receipt["control_production_prompt_characters"]
            == receipt["candidate_production_prompt_characters"]
            for receipt in receipts
        ),
        "candidate_first_tasks": sum(
            row["arm_order"][0] == contract.CANDIDATE_ARM for row in checked
        ),
        "positive_signed_credit_count": sum(
            receipt["positive_signed_credit_count"] for receipt in receipts
        ),
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"]) for row in completed
        ),
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_query_url_title_page_quote_record_identity_field_value_answer_or_credential": False,
    }


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    gate = contract.mechanism_gate()
    completed = int(aggregate["completed_runtime_tasks"])
    checks = {
        "fixed_terminal_denominator": aggregate["task_count"]
        == gate["fixed_task_denominator"]
        and aggregate["terminal_tasks"] == gate["terminal_tasks"],
        "minimum_completed_and_failure_as_zero": completed
        >= gate["minimum_completed_runtime_tasks"]
        and aggregate["failure_as_zero_tasks"]
        <= gate["maximum_failure_as_zero_tasks"],
        "minimum_first_wave_completed": aggregate["first_wave_completed_tasks"]
        >= gate["minimum_first_wave_completed_tasks"],
        "minimum_grounded_plan_provider_success": aggregate[
            "grounded_plan_provider_success_tasks"
        ]
        >= gate["minimum_grounded_plan_provider_success_tasks"],
        "minimum_both_arms_model_success": aggregate[
            "both_arms_model_success_tasks"
        ]
        >= gate["minimum_both_arms_model_success_tasks"],
        "minimum_candidate_prompt_changed": aggregate[
            "candidate_prompt_changed_tasks"
        ]
        >= gate["minimum_candidate_prompt_changed_tasks"],
        "minimum_verified_record_tasks": aggregate["verified_record_tasks"]
        >= gate["minimum_verified_record_tasks"],
        "minimum_verified_field_total": aggregate["verified_field_count_total"]
        >= gate["minimum_verified_field_count_total"],
        "minimum_attributable_prediction_change": aggregate[
            "attributable_prediction_changed_tasks"
        ]
        >= gate["minimum_attributable_prediction_changed_tasks"],
        "zero_unattributable_prediction_change": aggregate[
            "unattributable_prediction_changed_tasks"
        ]
        <= gate["maximum_unattributable_prediction_changed_tasks"],
        "outer_failure_cap": aggregate["outer_failure_tasks"]
        <= gate["maximum_outer_failure_tasks"],
        "zero_budget_rejection": aggregate["budget_rejection_tasks"]
        <= gate["maximum_budget_rejection_tasks"],
        "unrecoverable_hard_failure_cap": aggregate[
            "unrecoverable_hard_failure_tasks"
        ]
        <= gate["maximum_unrecoverable_hard_failure_tasks"],
        "exact_completed_query_budget": aggregate["completed_physical_queries"]
        == gate["exact_physical_queries_per_completed_task"] * completed,
        "completed_fetch_cap_preserved": aggregate["completed_physical_fetches"]
        <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "exact_completed_model_budget": aggregate[
            "completed_physical_model_forwards"
        ]
        == gate["exact_physical_model_forwards_per_completed_task"] * completed,
        "all_rows_per_task_hard_caps": aggregate[
            "per_task_hard_cap_preserved_tasks"
        ]
        == contract.TASK_COUNT,
        "pre_effect_projection_present_for_every_completed_task": aggregate[
            "pre_effect_projection_completed_tasks"
        ]
        == completed,
        "equal_prompt_characters": aggregate["equal_prompt_character_tasks"]
        == completed,
        "balanced_frozen_arm_order": aggregate["candidate_first_tasks"]
        == contract.TASK_COUNT // 2,
        "positive_signed_credit_zero": aggregate["positive_signed_credit_count"]
        == gate["positive_signed_credit_count"],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": not failed,
        "deepwidebench_successor_build_authorized": not failed,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    decision = copied.get("mechanism_decision")
    if (
        copied.get("role") != "v25358_repaired_second_fresh_pep_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(aggregate, Mapping)
        or decision != mechanism_decision(aggregate)
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "deepwidebench_successor_build": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.53.58 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.53.58 shared runtime is not ready")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    future = (contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT)
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.53.58 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.53.58 protected watcher identity drifted")
    validate_search_class()
    tasks = contract.task_vector()
    orders = contract.arm_order_vector()
    _prepare_output()
    started = time.monotonic()
    values: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {
                pool.submit(run_one_task, task, orders[index]): index
                for index, task in enumerate(tasks)
            }
            for future in as_completed(futures):
                values[futures[future]] = future.result()
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.53.58 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25358_repaired_second_fresh_pep_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_hash_vector_sha256": contract.payload_sha256(
                [row["prediction_sha256"] for row in rows]
            ),
            "all_predictions_terminal_before_evaluator_or_quality_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    aggregate = aggregate_rows(rows, wall_seconds=time.monotonic() - started)
    decision = mechanism_decision(aggregate)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25358_repaired_second_fresh_pep_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start[
                "execution_start_payload_sha256"
            ],
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "aggregate": aggregate,
            "mechanism_decision": decision,
            "authorization": {
                "forward_audit": True,
                "deepwidebench_successor_build": False,
                "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
                "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
            },
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, forward)
    return validate_forward_result(forward)


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_RESULT),
                "aggregate": value["aggregate"],
                "mechanism_decision": value["mechanism_decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
