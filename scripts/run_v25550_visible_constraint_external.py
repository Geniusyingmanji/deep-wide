#!/usr/bin/env python3
"""Run the single authorized V2.55.50 visible-constraint gate."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24982_paired_production_runtime as counters  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25545_deterministic_visible_constraint_runtime as runtime  # noqa: E402
from deepwide_agent import v25550_visible_constraint_external_contract as contract  # noqa: E402
from scripts import run_v25496_visible_row_key_detail_external as harness  # noqa: E402
from scripts import v25478_clone_safe_runner_namespace as clone_safe  # noqa: E402


TASK_ROLE = "v25550_visible_constraint_frozen_task_result"
FORWARD_ROLE = "v25550_visible_constraint_external_forward_result"
FREEZE_ROLE = "v25550_visible_constraint_prediction_freeze"
ARMS = runtime.ARMS

SOURCE_NAMES = (
    "_read",
    "_publish_json",
    "_publish_jsonl",
    "_clean_pushed",
    "_lease_inactive",
    "_active_conflicts",
    "_search",
    "_empty_effect_snapshot",
    "_effect_snapshot",
    "_health",
    "_health_snapshot",
    "_validate_cost",
    "run_one_task",
    "run_forward",
)
_SOURCE_FUNCTIONS = {name: getattr(harness, name) for name in SOURCE_NAMES}
_NAMESPACE, _CLONES = clone_safe.clone_group(
    _SOURCE_FUNCTIONS,
    visible_globals=harness.__dict__,
    overrides={
        "contract": contract,
        "runtime": runtime,
        "counters": counters,
        "cap": cap,
        "TASK_ROLE": TASK_ROLE,
        "FORWARD_ROLE": FORWARD_ROLE,
        "FREEZE_ROLE": FREEZE_ROLE,
        "ARMS": ARMS,
    },
    rename_from="v25496",
    rename_to="v25550",
)
_CLONE_NAMESPACE_RECEIPT = clone_safe.content_free_receipt(
    _SOURCE_FUNCTIONS, _NAMESPACE
)
if (
    _CLONE_NAMESPACE_RECEIPT["unresolved_function_count"] != 0
    or _CLONE_NAMESPACE_RECEIPT["unresolved_global_name_count"] != 0
    or not all(
        _CLONE_NAMESPACE_RECEIPT[name]
        for name in (
            "fcntl_resolved",
            "socket_resolved",
            "subprocess_resolved",
            "thread_pool_executor_resolved",
            "as_completed_resolved",
            "lease_helper_resolved",
        )
    )
):
    raise RuntimeError("V2.55.50 clone namespace is incomplete")

globals().update(
    {
        name: _CLONES[name]
        for name in (
            "_read",
            "_publish_json",
            "_publish_jsonl",
            "_clean_pushed",
            "_lease_inactive",
            "_active_conflicts",
            "_search",
            "_empty_effect_snapshot",
            "_effect_snapshot",
            "_health",
            "_health_snapshot",
            "_validate_cost",
        )
    }
)


def clone_namespace_receipt() -> dict[str, Any]:
    return copy.deepcopy(_CLONE_NAMESPACE_RECEIPT)


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    expected = {
        "one_external_forward": True,
        "postfreeze_quality": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    current = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    parents = contract.git(ROOT, "rev-list", "--parents", "-n", "1", current).split()
    changed = sorted(
        line.strip()
        for line in contract.git(
            ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", current
        ).splitlines()
        if line.strip()
    )
    if (
        start.get("role") != "v25550_visible_constraint_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("identity_vector_sha256")
        != protocol["population"]["identity_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization") != expected
        or not contract.sealed(start, "execution_start_payload_sha256")
        or current != target
        or len(parents) != 2
        or parents[1] != start.get("git_head")
        or changed != [str(contract.EXECUTION_START)]
    ):
        raise RuntimeError("V2.55.50 execution start drifted")
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
                "role": "v25550_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _columns(question: str) -> tuple[str, ...]:
    return (
        contract.population.DATE_COLUMNS
        if "<PROJECT>" in question
        else contract.population.SCALE_COLUMNS
    )


def _fallback_prediction(question: str) -> str:
    columns = _columns(question)
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n| "
        + " | ".join("Unknown" for _ in columns)
        + " |\n| "
        + " | ".join("Unknown" for _ in columns)
        + " |\n```"
    )


def _task_metadata() -> dict[str, int]:
    output = {
        task["opaque_id"]: index for index, task in enumerate(contract.task_vector())
    }
    if len(output) != contract.TASK_COUNT:
        raise RuntimeError("V2.55.50 task metadata drifted")
    return output


def _metadata(task: Mapping[str, str]) -> int:
    index = _task_metadata().get(str(task.get("opaque_id")))
    if index is None or dict(task) != contract.task_vector()[index]:
        raise ValueError("V2.55.50 task is outside frozen population")
    return index


def _decode_completed(
    result: Mapping[str, Any], stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = runtime.validate_result(result)
    checked_stage = runtime.validate_stage_receipt(stage)
    parent = runtime.parent.validate_result(checked["private_parent_result"])
    parent_stage = runtime.parent.validate_stage_receipt(
        checked_stage["parent_stage_receipt"]
    )
    visible = runtime.contracts.validate_contract(
        checked["private_visible_constraint_contract"]
    )
    receipt = runtime.validate_receipt(
        checked["deterministic_visible_constraint_receipt"],
        parent_result=parent,
        contract=visible,
        projection=runtime.projector.build_projection(
            checked["predictions"][runtime.CONTROL_ARM], visible
        ),
    )
    projection = runtime.projector.validate_receipt(receipt["projection_receipt"])
    budget = cap.validate_budget_receipt(
        checked_stage["outer_physical_budget_receipt"]
    )
    predictions = copy.deepcopy(checked["predictions"])
    if (
        parent["result_payload_sha256"]
        != checked["private_parent_result_payload_sha256"]
        or checked_stage["parent_runtime_result_payload_sha256"]
        != parent["result_payload_sha256"]
        or parent_stage["outer_physical_budget_receipt"] != budget
        or predictions[runtime.CONTROL_ARM]
        != checked["private_parent_result"]["prediction"]
        or predictions[runtime.CANDIDATE_ARM] != checked["prediction"]
        or checked["candidate_prediction_changed"]
        is not (predictions[runtime.CONTROL_ARM] != predictions[runtime.CANDIDATE_ARM])
        or receipt["candidate_prediction_changed"]
        is not checked["candidate_prediction_changed"]
    ):
        raise ValueError("V2.55.50 shared-parent chain drifted")
    return {
        "result": checked,
        "stage": checked_stage,
        "parent_result": parent,
        "parent_stage": parent_stage,
        "visible_contract": visible,
        "runtime_receipt": receipt,
        "projection_receipt": projection,
        "budget": budget,
        "predictions": predictions,
    }


_COUNT_FIELDS = (
    "active_family_count",
    "date_cell_changed_count",
    "scale_cell_changed_count",
    "sort_applied_count",
    "sort_already_satisfied_count",
    "sort_rejected_count",
    "positive_signed_credit_count",
)


def _terminal_outer_failure(
    task: Mapping[str, str],
    exc: BaseException,
    elapsed: float,
    *,
    budget: cap.PhysicalEffectBudget | None,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    prediction = _fallback_prediction(str(task["question"]))
    predictions = {arm: prediction for arm in ARMS}
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": str(task["opaque_id"]),
        "task_index": _metadata(task),
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": False,
        "failure_as_zero": True,
        "outer_failure_type": (type(exc).__name__ or "Exception")[:128],
        "runtime_result": None,
        "runtime_result_payload_sha256": None,
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(prediction.encode()).hexdigest() for arm in ARMS
        },
        "prediction_kind": "fallback",
        "constraint_active": False,
        "date_contract_active": False,
        "scale_contract_active": False,
        "order_contract_active": False,
        "candidate_prediction_changed": False,
        "parent_prediction_loss_present": False,
        "unattributable_prediction_change_present": False,
        **{name: 0 for name in _COUNT_FIELDS},
        "content_free_stage_receipt": None,
        "actual_effect_snapshot": _effect_snapshot(budget),
        "cost": None,
        "hard_failure_health": _health(health),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        "question_query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions": False,
    }
    return validate_task_row(contract.seal(row, "result_payload_sha256"))


def _from_runtime(
    task: Mapping[str, str],
    value: Mapping[str, Any],
    stage: Mapping[str, Any],
    *,
    elapsed: float,
    budget: cap.PhysicalEffectBudget,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    decoded = _decode_completed(value, stage)
    checked = decoded["result"]
    visible = decoded["visible_contract"]
    receipt = decoded["runtime_receipt"]
    projection = decoded["projection_receipt"]
    observed_budget = cap.validate_budget_receipt(budget.receipt())
    if checked["opaque_id"] != task["opaque_id"] or decoded["budget"] != observed_budget:
        raise RuntimeError("V2.55.50 runtime task binding drifted")
    predictions = copy.deepcopy(decoded["predictions"])
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": checked["opaque_id"],
        "task_index": _metadata(task),
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "runtime_result": copy.deepcopy(checked),
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in ARMS
        },
        "prediction_kind": checked["prediction_kind"],
        "constraint_active": bool(receipt["constraint_active"]),
        "date_contract_active": visible["date_format"] is not None,
        "scale_contract_active": visible["numeric_scale"] is not None,
        "order_contract_active": visible["explicit_order"] is not None,
        "candidate_prediction_changed": bool(checked["candidate_prediction_changed"]),
        "parent_prediction_loss_present": predictions[runtime.CONTROL_ARM]
        != decoded["parent_result"]["prediction"],
        "unattributable_prediction_change_present": checked[
            "candidate_prediction_changed"
        ]
        is not projection["candidate_prediction_changed"],
        "active_family_count": int(receipt["active_family_count"]),
        "date_cell_changed_count": int(projection["date_cell_changed_count"]),
        "scale_cell_changed_count": int(projection["scale_cell_changed_count"]),
        "sort_applied_count": int(projection["sort_applied_count"]),
        "sort_already_satisfied_count": int(
            projection["sort_already_satisfied_count"]
        ),
        "sort_rejected_count": int(projection["sort_rejected_count"]),
        "positive_signed_credit_count": 0,
        "content_free_stage_receipt": copy.deepcopy(decoded["stage"]),
        "actual_effect_snapshot": _effect_snapshot(budget),
        "cost": copy.deepcopy(checked["cost"]),
        "hard_failure_health": _health(health),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        "question_query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions": False,
    }
    return validate_task_row(contract.seal(row, "result_payload_sha256"))


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version", "role", "protocol_id", "opaque_id", "task_index",
        "runtime_input_keys", "terminal", "runtime_completed", "failure_as_zero",
        "outer_failure_type", "runtime_result", "runtime_result_payload_sha256",
        "predictions", "prediction_sha256", "prediction_kind", "constraint_active",
        "date_contract_active", "scale_contract_active", "order_contract_active",
        "candidate_prediction_changed", "parent_prediction_loss_present",
        "unattributable_prediction_change_present", *_COUNT_FIELDS,
        "content_free_stage_receipt", "actual_effect_snapshot", "cost",
        "hard_failure_health", "elapsed_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "retry_resume_replay_backfill_replacement_or_selective_rerun",
        "question_query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions",
        "result_payload_sha256",
    }
    metadata = _task_metadata().get(str(copied.get("opaque_id")))
    effects = copied.get("actual_effect_snapshot") or {}
    health = copied.get("hard_failure_health") or {}
    predictions = copied.get("predictions") or {}
    hashes = copied.get("prediction_sha256") or {}
    completed = copied.get("runtime_completed") is True
    boolean_fields = (
        "constraint_active", "date_contract_active", "scale_contract_active",
        "order_contract_active", "candidate_prediction_changed",
        "parent_prediction_loss_present", "unattributable_prediction_change_present",
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or metadata is None
        or copied.get("task_index") != metadata
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("runtime_completed"), bool)
        or copied.get("failure_as_zero") is completed
        or set(predictions) != set(ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in ARMS)
        or set(hashes) != set(ARMS)
        or any(hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in ARMS)
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or copied["candidate_prediction_changed"]
        is not (predictions[runtime.CONTROL_ARM] != predictions[runtime.CANDIDATE_ARM])
        or copied["constraint_active"] is not (copied["active_family_count"] > 0)
        or copied["candidate_prediction_changed"]
        is not (
            copied["date_cell_changed_count"] > 0
            or copied["scale_cell_changed_count"] > 0
            or copied["sort_applied_count"] > 0
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _COUNT_FIELDS
        )
        or set(effects) != set(_empty_effect_snapshot())
        or any(isinstance(amount, bool) or not isinstance(amount, int) or amount < 0 for amount in effects.values())
        or set(health) != set(_health())
        or any(isinstance(amount, bool) or not isinstance(amount, int) or amount < 0 for amount in health.values())
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or copied["elapsed_seconds"] < 0
        or copied.get("positive_signed_credit_count") != 0
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_replay_backfill_replacement_or_selective_rerun",
                "question_query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.55.50 task row drifted")
    if completed:
        runtime_result = copied.get("runtime_result")
        stage = copied.get("content_free_stage_receipt")
        if not isinstance(runtime_result, Mapping) or not isinstance(stage, Mapping):
            raise ValueError("V2.55.50 completed runtime surface is absent")
        decoded = _decode_completed(runtime_result, stage)
        checked = decoded["result"]
        visible = decoded["visible_contract"]
        projection = decoded["projection_receipt"]
        budget = decoded["budget"]
        if (
            copied.get("runtime_result_payload_sha256") != checked["result_payload_sha256"]
            or copied["predictions"] != decoded["predictions"]
            or copied["prediction_kind"] != checked["prediction_kind"]
            or copied["constraint_active"]
            is not (visible["active_family_count"] > 0)
            or copied["date_contract_active"] is not (visible["date_format"] is not None)
            or copied["scale_contract_active"] is not (visible["numeric_scale"] is not None)
            or copied["order_contract_active"] is not (visible["explicit_order"] is not None)
            or copied["active_family_count"] != visible["active_family_count"]
            or any(copied[name] != projection[name] for name in (
                "date_cell_changed_count", "scale_cell_changed_count",
                "sort_applied_count", "sort_already_satisfied_count", "sort_rejected_count",
            ))
            or copied["parent_prediction_loss_present"] is not False
            or copied["unattributable_prediction_change_present"] is not False
            or copied["cost"] != checked["cost"]
            or checked["opaque_id"] != copied["opaque_id"]
            or copied.get("outer_failure_type") is not None
            or any(
                effects[f"{kind}_{suffix}_count"] != budget[f"{kind}_{suffix}_count"]
                for kind in ("query", "fetch", "model")
                for suffix in ("admitted", "rejected")
            )
            or _validate_cost(copied.get("cost")) != copied["cost"]
        ):
            raise ValueError("V2.55.50 completed task row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or copied.get("runtime_result") is not None
        or copied.get("runtime_result_payload_sha256") is not None
        or copied.get("content_free_stage_receipt") is not None
        or copied.get("cost") is not None
        or copied.get("prediction_kind") != "fallback"
        or len(set(predictions.values())) != 1
        or any(copied[name] != 0 for name in _COUNT_FIELDS)
        or any(copied[name] is not False for name in boolean_fields)
    ):
        raise ValueError("V2.55.50 failure task row drifted")
    return copied


AGGREGATE_INTEGER_FIELDS = (
    "task_count", "terminal_tasks", "completed_runtime_tasks", "failure_as_zero_tasks",
    "outer_failure_tasks", "naked_outer_failure_tasks", "model_generated_tasks",
    "shared_parent_tasks", "active_constraint_tasks", "date_contract_tasks",
    "scale_contract_tasks", "explicit_order_contract_tasks", "date_changed_tasks",
    "scale_changed_tasks", "sort_applied_tasks", "sort_already_satisfied_tasks",
    "sort_rejected_tasks", "prediction_changed_tasks", "parent_prediction_loss_tasks",
    "unattributable_prediction_changed_tasks", "date_cell_changed_count_total",
    "scale_cell_changed_count_total", "sort_applied_count_total", "budget_rejection_tasks",
    "all_physical_queries", "all_physical_fetches", "all_physical_model_forwards",
    "completed_physical_queries", "completed_physical_fetches",
    "completed_physical_model_forwards", "per_task_hard_cap_preserved_tasks",
    "fallback_tasks", "positive_signed_credit_count", "system_total_tokens",
)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        *AGGREGATE_INTEGER_FIELDS, "batch_wall_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate",
    }
    if (
        set(copied) != expected
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in AGGREGATE_INTEGER_FIELDS
        )
        or copied["task_count"] != contract.TASK_COUNT
        or copied["terminal_tasks"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"] + copied["failure_as_zero_tasks"] != contract.TASK_COUNT
        or copied["outer_failure_tasks"] != copied["failure_as_zero_tasks"]
    ):
        raise ValueError("V2.55.50 aggregate shape drifted")
    if (
        copied["positive_signed_credit_count"] != 0
        or isinstance(copied.get("batch_wall_seconds"), bool)
        or not isinstance(copied.get("batch_wall_seconds"), (int, float))
        or not math.isfinite(float(copied["batch_wall_seconds"]))
        or copied["batch_wall_seconds"] < 0
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate",
            )
        )
    ):
        raise ValueError("V2.55.50 aggregate drifted")
    return copied


def aggregate_rows(rows: Sequence[Mapping[str, Any]], *, wall_seconds: float) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in contract.task_vector()]
    ):
        raise RuntimeError("V2.55.50 fixed population order drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    value: dict[str, Any] = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "outer_failure_tasks": sum(not row["runtime_completed"] for row in checked),
        "naked_outer_failure_tasks": sum(not row["runtime_completed"] and row["content_free_stage_receipt"] is None for row in checked),
        "model_generated_tasks": sum(row["prediction_kind"] == "model_generated" for row in checked),
        "shared_parent_tasks": sum(row["runtime_completed"] and not row["parent_prediction_loss_present"] for row in checked),
        "active_constraint_tasks": sum(row["constraint_active"] for row in checked),
        "date_contract_tasks": sum(row["date_contract_active"] for row in checked),
        "scale_contract_tasks": sum(row["scale_contract_active"] for row in checked),
        "explicit_order_contract_tasks": sum(row["order_contract_active"] for row in checked),
        "date_changed_tasks": sum(row["date_cell_changed_count"] > 0 for row in checked),
        "scale_changed_tasks": sum(row["scale_cell_changed_count"] > 0 for row in checked),
        "sort_applied_tasks": sum(row["sort_applied_count"] > 0 for row in checked),
        "sort_already_satisfied_tasks": sum(row["sort_already_satisfied_count"] > 0 for row in checked),
        "sort_rejected_tasks": sum(row["sort_rejected_count"] > 0 for row in checked),
        "prediction_changed_tasks": sum(row["candidate_prediction_changed"] for row in checked),
        "parent_prediction_loss_tasks": sum(row["parent_prediction_loss_present"] for row in checked),
        "unattributable_prediction_changed_tasks": sum(row["unattributable_prediction_change_present"] for row in checked),
        "date_cell_changed_count_total": sum(row["date_cell_changed_count"] for row in checked),
        "scale_cell_changed_count_total": sum(row["scale_cell_changed_count"] for row in checked),
        "sort_applied_count_total": sum(row["sort_applied_count"] for row in checked),
        "budget_rejection_tasks": sum(any(row["actual_effect_snapshot"][f"{kind}_rejected_count"] > 0 for kind in ("query", "fetch", "model")) for row in checked),
        "all_physical_queries": sum(row["actual_effect_snapshot"]["query_admitted_count"] for row in checked),
        "all_physical_fetches": sum(row["actual_effect_snapshot"]["fetch_admitted_count"] for row in checked),
        "all_physical_model_forwards": sum(row["actual_effect_snapshot"]["model_admitted_count"] for row in checked),
        "completed_physical_queries": sum(row["actual_effect_snapshot"]["query_admitted_count"] for row in completed),
        "completed_physical_fetches": sum(row["actual_effect_snapshot"]["fetch_admitted_count"] for row in completed),
        "completed_physical_model_forwards": sum(row["actual_effect_snapshot"]["model_admitted_count"] for row in completed),
        "per_task_hard_cap_preserved_tasks": sum(row["actual_effect_snapshot"]["query_admitted_count"] <= 4 and row["actual_effect_snapshot"]["fetch_admitted_count"] <= 14 and row["actual_effect_snapshot"]["model_admitted_count"] <= 3 for row in checked),
        "fallback_tasks": sum(row["prediction_kind"] == "fallback" for row in checked),
        "positive_signed_credit_count": 0,
        "system_total_tokens": sum(int(row["cost"]["system_total_tokens"]) for row in completed if row["cost"] is not None),
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate": False,
    }
    return validate_aggregate(value)


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_aggregate(aggregate)
    gate = contract.mechanism_gate()
    completed = value["completed_runtime_tasks"]
    checks = {
        "fixed_task_denominator": value["task_count"] == gate["fixed_task_denominator"],
        "all_tasks_terminal": value["terminal_tasks"] == gate["required_terminal_tasks"],
        "all_runtime_tasks_completed": completed == gate["required_completed_runtime_tasks"],
        "all_model_generated": value["model_generated_tasks"] == gate["required_model_generated_tasks"],
        "zero_outer_failure": value["outer_failure_tasks"] <= gate["maximum_outer_or_accounting_failure_tasks"],
        "zero_naked_outer_failure": value["naked_outer_failure_tasks"] <= gate["maximum_naked_outer_failure_tasks"],
        "all_shared_parent": value["shared_parent_tasks"] == gate["required_shared_parent_tasks"],
        "zero_parent_prediction_loss": value["parent_prediction_loss_tasks"] <= gate["maximum_parent_prediction_loss_tasks"],
        "minimum_active_constraint_tasks": value["active_constraint_tasks"] >= gate["minimum_active_constraint_tasks"],
        "minimum_date_contract_tasks": value["date_contract_tasks"] >= gate["minimum_date_contract_tasks"],
        "minimum_scale_contract_tasks": value["scale_contract_tasks"] >= gate["minimum_scale_contract_tasks"],
        "minimum_explicit_order_contract_tasks": value["explicit_order_contract_tasks"] >= gate["minimum_explicit_order_contract_tasks"],
        "minimum_prediction_changed_tasks": value["prediction_changed_tasks"] >= gate["minimum_candidate_prediction_changed_tasks"],
        "minimum_date_changed_tasks": value["date_changed_tasks"] >= gate["minimum_date_changed_tasks"],
        "minimum_scale_changed_tasks": value["scale_changed_tasks"] >= gate["minimum_scale_changed_tasks"],
        "minimum_sort_applied_tasks": value["sort_applied_tasks"] >= gate["minimum_sort_applied_tasks"],
        "zero_unattributable_change": value["unattributable_prediction_changed_tasks"] <= gate["maximum_unattributable_prediction_changed_tasks"],
        "zero_budget_rejection": value["budget_rejection_tasks"] == 0,
        "exact_completed_query_budget": value["completed_physical_queries"] == gate["exact_physical_queries_per_completed_task"] * completed,
        "completed_fetch_cap_preserved": value["completed_physical_fetches"] <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "completed_model_cap_preserved": value["completed_physical_model_forwards"] <= gate["maximum_normal_path_model_forwards_per_completed_task"] * completed,
        "all_rows_per_task_hard_caps": value["per_task_hard_cap_preserved_tasks"] == contract.TASK_COUNT,
        "positive_signed_credit_zero": value["positive_signed_credit_count"] == gate["positive_signed_credit_count"],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": not failed,
        "postfreeze_quality_protocol_authorized": not failed,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        copied.get("role") != FORWARD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("mechanism_decision") != mechanism_decision(aggregate)
        or copied.get("authorization") != {
            "forward_audit": True,
            "postfreeze_quality_protocol": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.55.50 forward result drifted")
    return copied


_NAMESPACE.update(
    {
        "_validate_start": _validate_start,
        "_prepare_output": _prepare_output,
        "_fallback_prediction": _fallback_prediction,
        "_task_metadata": _task_metadata,
        "_metadata": _metadata,
        "_decode_completed": _decode_completed,
        "_terminal_outer_failure": _terminal_outer_failure,
        "_from_runtime": _from_runtime,
        "validate_task_row": validate_task_row,
        "validate_aggregate": validate_aggregate,
        "aggregate_rows": aggregate_rows,
        "mechanism_decision": mechanism_decision,
        "validate_forward_result": validate_forward_result,
    }
)
run_one_task = _CLONES["run_one_task"]
run_forward = _CLONES["run_forward"]


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
