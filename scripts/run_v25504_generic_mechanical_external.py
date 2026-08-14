#!/usr/bin/env python3
"""Run the single authorized V2.55.04 generic mechanical-field gate."""

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
from deepwide_agent import v25370_shared_synthesis_changed_safe_runtime as base_runtime  # noqa: E402
from deepwide_agent import v25375_schema_total_changed_safe_runtime as schema_runtime  # noqa: E402
from deepwide_agent import v25472_qualified_source_label_runtime as qualified_runtime  # noqa: E402
from deepwide_agent import v25492_visible_row_key_detail_runtime as detail_runtime  # noqa: E402
from deepwide_agent import v25500_generic_mechanical_field_runtime as runtime  # noqa: E402
from deepwide_agent import v25504_generic_mechanical_external_contract as contract  # noqa: E402
from scripts import run_v25496_visible_row_key_detail_external as harness  # noqa: E402
from scripts import v25478_clone_safe_runner_namespace as clone_safe  # noqa: E402


TASK_ROLE = "v25504_generic_mechanical_frozen_task_result"
FORWARD_ROLE = "v25504_generic_mechanical_external_forward_result"
FREEZE_ROLE = "v25504_generic_mechanical_prediction_freeze"
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
        "base_runtime": base_runtime,
        "parent_runtime": schema_runtime,
        "qualified_runtime": qualified_runtime,
        "detail_runtime": detail_runtime,
        "TASK_ROLE": TASK_ROLE,
        "FORWARD_ROLE": FORWARD_ROLE,
        "FREEZE_ROLE": FREEZE_ROLE,
        "ARMS": ARMS,
    },
    rename_from="v25496",
    rename_to="v25504",
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
    raise RuntimeError("V2.55.04 clone namespace is incomplete")

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
        start.get("role") != "v25504_generic_mechanical_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("clue_vector_sha256")
        != protocol["population"]["clue_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization") != expected
        or not contract.sealed(start, "execution_start_payload_sha256")
        or current != target
        or len(parents) != 2
        or parents[1] != start.get("git_head")
        or changed != [str(contract.EXECUTION_START)]
    ):
        raise RuntimeError("V2.55.04 execution start drifted")
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
                "role": "v25504_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _fallback_prediction(_question: str) -> str:
    return (
        "```markdown\n| "
        + " | ".join(contract.COLUMNS)
        + " |\n| "
        + " | ".join("---" for _ in contract.COLUMNS)
        + " |\n| "
        + " | ".join("Unknown" for _ in contract.COLUMNS)
        + " |\n```"
    )


def _task_metadata() -> dict[str, int]:
    output = {
        task["opaque_id"]: index for index, task in enumerate(contract.task_vector())
    }
    if len(output) != contract.TASK_COUNT:
        raise RuntimeError("V2.55.04 task metadata drifted")
    return output


def _metadata(task: Mapping[str, str]) -> int:
    index = _task_metadata().get(str(task.get("opaque_id")))
    if index is None or dict(task) != contract.task_vector()[index]:
        raise ValueError("V2.55.04 task is outside frozen population")
    return index


def _decode_completed(
    result: Mapping[str, Any], stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = runtime.validate_result(result)
    checked_stage = runtime.validate_stage_receipt(stage)
    detail = detail_runtime.validate_result(checked["private_parent_result"])
    detail_stage = detail_runtime.validate_stage_receipt(
        checked_stage["parent_stage_receipt"]
    )
    qualified = qualified_runtime.validate_result(detail["private_parent_result"])
    qualified_stage = qualified_runtime.validate_stage_receipt(
        detail_stage["parent_stage_receipt"]
    )
    schema = schema_runtime.validate_result(qualified["private_parent_result"])
    schema_stage = schema_runtime.validate_stage_receipt(
        qualified_stage["parent_stage_receipt"]
    )
    base = base_runtime.validate_result(schema["private_parent_result"])
    parent_receipt = base_runtime.validate_receipt(base["content_free_receipt"])
    source_receipt = qualified_runtime.validate_receipt(
        qualified["row_key_bound_source_receipt"]
    )
    detail_receipt = detail_runtime.validate_receipt(
        detail["visible_row_key_detail_receipt"]
    )
    generic_receipt = runtime.validate_receipt(
        checked["generic_mechanical_field_receipt"]
    )
    budget = cap.validate_budget_receipt(
        checked_stage["outer_physical_budget_receipt"]
    )
    predictions = copy.deepcopy(checked["predictions"])
    if (
        detail["result_payload_sha256"]
        != checked["private_parent_result_payload_sha256"]
        or qualified["result_payload_sha256"]
        != detail["private_parent_result_payload_sha256"]
        or schema["result_payload_sha256"]
        != qualified["private_parent_result_payload_sha256"]
        or base["result_payload_sha256"]
        != schema["private_parent_result_payload_sha256"]
        or predictions[runtime.BASE_ARM] != detail["predictions"][detail_runtime.BASE_ARM]
        or predictions[runtime.CANDIDATE_ARM] != checked["prediction"]
        or checked["prediction_changed"]
        is not (predictions[runtime.BASE_ARM] != predictions[runtime.CANDIDATE_ARM])
        or generic_receipt["candidate_prediction_changed"]
        is not checked["prediction_changed"]
        or checked_stage["parent_runtime_result_payload_sha256"]
        != detail["result_payload_sha256"]
        or detail_stage["parent_runtime_result_payload_sha256"]
        != qualified["result_payload_sha256"]
        or qualified_stage["parent_runtime_result_payload_sha256"]
        != schema["result_payload_sha256"]
        or schema_stage["outer_physical_budget_receipt"]
        != qualified_stage["outer_physical_budget_receipt"]
        or detail_receipt["final_query_count"] != budget["query_admitted_count"]
        or detail_receipt["final_fetch_count"] != budget["fetch_admitted_count"]
        or detail_receipt["final_model_count"] != budget["model_admitted_count"]
        or generic_receipt["final_query_count"] != budget["query_admitted_count"]
        or generic_receipt["final_fetch_count"] != budget["fetch_admitted_count"]
        or generic_receipt["final_model_count"] != budget["model_admitted_count"]
    ):
        raise ValueError("V2.55.04 shared parent chain drifted")
    return {
        "result": checked,
        "stage": checked_stage,
        "detail_result": detail,
        "detail_stage": detail_stage,
        "qualified_result": qualified,
        "qualified_stage": qualified_stage,
        "schema_result": schema,
        "schema_stage": schema_stage,
        "base_result": base,
        "parent_receipt": parent_receipt,
        "source_receipt": source_receipt,
        "detail_receipt": detail_receipt,
        "generic_receipt": generic_receipt,
        "budget": budget,
        "predictions": predictions,
    }


_MECHANISM_FIELDS = (
    "parent_same_forward_page_count",
    "exact_detail_page_count",
    "combined_candidate_page_count",
    "generic_mechanical_field_surface_count",
    "generic_mechanical_observation_count",
    "available_candidate_count",
    "applied_coordinate_count",
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
        "candidate_prediction_changed": False,
        "synthesis_capture_valid": False,
        **{name: 0 for name in _MECHANISM_FIELDS},
        "application_failure_present": False,
        "content_free_stage_receipt": None,
        "actual_effect_snapshot": _effect_snapshot(budget),
        "cost": None,
        "hard_failure_health": _health(health),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
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
    source = decoded["source_receipt"]
    generic = decoded["generic_receipt"]
    observed_budget = cap.validate_budget_receipt(budget.receipt())
    if checked["opaque_id"] != task["opaque_id"] or decoded["budget"] != observed_budget:
        raise RuntimeError("V2.55.04 runtime task binding drifted")
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
        "candidate_prediction_changed": bool(checked["prediction_changed"]),
        "synthesis_capture_valid": bool(source["synthesis_capture_valid"]),
        **{name: int(generic[name]) for name in _MECHANISM_FIELDS},
        "application_failure_present": generic[
            "candidate_application_failure_type"
        ]
        is not None,
        "content_free_stage_receipt": copy.deepcopy(decoded["stage"]),
        "actual_effect_snapshot": _effect_snapshot(budget),
        "cost": copy.deepcopy(checked["cost"]),
        "hard_failure_health": _health(health),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        "question_query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions": False,
    }
    return validate_task_row(contract.seal(row, "result_payload_sha256"))


_TASK_INTEGER_FIELDS = (*_MECHANISM_FIELDS, "positive_signed_credit_count")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version", "role", "protocol_id", "opaque_id", "task_index",
        "runtime_input_keys", "terminal", "runtime_completed", "failure_as_zero",
        "outer_failure_type", "runtime_result", "runtime_result_payload_sha256",
        "predictions", "prediction_sha256", "prediction_kind",
        "candidate_prediction_changed", "synthesis_capture_valid", *_MECHANISM_FIELDS,
        "application_failure_present", "content_free_stage_receipt",
        "actual_effect_snapshot", "cost", "hard_failure_health", "elapsed_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit", "positive_signed_credit_count",
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
        or copied.get("candidate_prediction_changed")
        is not (predictions[runtime.BASE_ARM] != predictions[runtime.CANDIDATE_ARM])
        or not isinstance(copied.get("synthesis_capture_valid"), bool)
        or not isinstance(copied.get("application_failure_present"), bool)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _TASK_INTEGER_FIELDS
        )
        or copied["combined_candidate_page_count"]
        != copied["parent_same_forward_page_count"] + copied["exact_detail_page_count"]
        or copied["generic_mechanical_observation_count"]
        > copied["generic_mechanical_field_surface_count"]
        or copied["available_candidate_count"] != copied["applied_coordinate_count"]
        or copied["candidate_prediction_changed"]
        is not (copied["applied_coordinate_count"] > 0)
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
        raise ValueError("V2.55.04 task row drifted")
    if completed:
        runtime_result = copied.get("runtime_result")
        stage = copied.get("content_free_stage_receipt")
        if not isinstance(runtime_result, Mapping) or not isinstance(stage, Mapping):
            raise ValueError("V2.55.04 completed runtime surface absent")
        decoded = _decode_completed(runtime_result, stage)
        checked = decoded["result"]
        generic = decoded["generic_receipt"]
        budget = decoded["budget"]
        cost = _validate_cost(copied.get("cost"))
        if (
            copied.get("runtime_result_payload_sha256") != checked["result_payload_sha256"]
            or copied["predictions"] != decoded["predictions"]
            or copied["prediction_kind"] != checked["prediction_kind"]
            or copied["candidate_prediction_changed"] != checked["prediction_changed"]
            or copied["synthesis_capture_valid"]
            != decoded["source_receipt"]["synthesis_capture_valid"]
            or any(copied[name] != generic[name] for name in _MECHANISM_FIELDS)
            or copied["application_failure_present"]
            is not (generic["candidate_application_failure_type"] is not None)
            or copied["cost"] != checked["cost"]
            or checked["opaque_id"] != copied["opaque_id"]
            or copied.get("outer_failure_type") is not None
            or any(
                effects[f"{kind}_{suffix}_count"] != budget[f"{kind}_{suffix}_count"]
                for kind in ("query", "fetch", "model")
                for suffix in ("admitted", "rejected")
            )
            or cost["system_total_tokens"]
            != decoded["parent_receipt"]["system_total_tokens"]
        ):
            raise ValueError("V2.55.04 completed task row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or copied.get("runtime_result") is not None
        or copied.get("runtime_result_payload_sha256") is not None
        or copied.get("content_free_stage_receipt") is not None
        or copied.get("cost") is not None
        or copied.get("prediction_kind") != "fallback"
        or len(set(predictions.values())) != 1
        or any(copied[name] != 0 for name in _TASK_INTEGER_FIELDS)
        or copied["synthesis_capture_valid"] is not False
        or copied["application_failure_present"] is not False
    ):
        raise ValueError("V2.55.04 failure task row drifted")
    return copied


AGGREGATE_INTEGER_FIELDS = (
    "task_count", "terminal_tasks", "completed_runtime_tasks", "failure_as_zero_tasks",
    "outer_failure_tasks", "naked_outer_failure_tasks", "parent_role_tasks",
    "first_wave_completed_tasks", "second_wave_completed_tasks",
    "grounded_plan_provider_success_tasks", "base_synthesis_success_tasks",
    "exact_canonical_base_table_tasks", "synthesis_capture_valid_tasks",
    "combined_candidate_page_tasks", "combined_candidate_page_count_total",
    "generic_mechanical_field_surface_tasks", "generic_mechanical_field_surface_count_total",
    "generic_mechanical_observation_tasks", "generic_mechanical_observation_count_total",
    "available_candidate_tasks", "available_candidate_count_total", "applied_candidate_tasks",
    "applied_coordinate_count_total", "application_failure_tasks", "prediction_changed_tasks",
    "budget_rejection_tasks", "all_physical_queries", "all_physical_fetches",
    "all_physical_model_forwards", "completed_physical_queries",
    "completed_physical_fetches", "completed_physical_model_forwards",
    "per_task_hard_cap_preserved_tasks", "fallback_tasks", "positive_signed_credit_count",
    "system_total_tokens",
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
        or any(isinstance(copied.get(name), bool) or not isinstance(copied.get(name), int) or copied[name] < 0 for name in AGGREGATE_INTEGER_FIELDS)
        or copied["task_count"] != contract.TASK_COUNT
        or copied["terminal_tasks"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"] + copied["failure_as_zero_tasks"] != contract.TASK_COUNT
        or copied["outer_failure_tasks"] != copied["failure_as_zero_tasks"]
        or copied["generic_mechanical_observation_count_total"] > copied["generic_mechanical_field_surface_count_total"]
        or copied["applied_coordinate_count_total"] != copied["available_candidate_count_total"]
        or copied["prediction_changed_tasks"] > copied["available_candidate_tasks"]
        or copied["positive_signed_credit_count"] != 0
        or isinstance(copied.get("batch_wall_seconds"), bool)
        or not isinstance(copied.get("batch_wall_seconds"), (int, float))
        or not math.isfinite(float(copied["batch_wall_seconds"]))
        or copied["batch_wall_seconds"] < 0
        or any(copied.get(name) is not False for name in (
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate",
        ))
    ):
        raise ValueError("V2.55.04 aggregate drifted")
    return copied


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in contract.task_vector()]
    ):
        raise RuntimeError("V2.55.04 fixed population order drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    decoded = [
        _decode_completed(row["runtime_result"], row["content_free_stage_receipt"])
        for row in completed
    ]
    parents = [item["parent_receipt"] for item in decoded]
    generic = [item["generic_receipt"] for item in decoded]
    value: dict[str, Any] = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "outer_failure_tasks": sum(not row["runtime_completed"] for row in checked),
        "naked_outer_failure_tasks": sum(not row["runtime_completed"] and row["content_free_stage_receipt"] is None for row in checked),
        "parent_role_tasks": sum(item["result"]["role"] == runtime.ROLE for item in decoded),
        "first_wave_completed_tasks": sum(receipt["first_wave_completed"] for receipt in parents),
        "second_wave_completed_tasks": sum(receipt["second_wave_completed"] for receipt in parents),
        "grounded_plan_provider_success_tasks": sum(receipt["grounded_plan_model_call_success"] for receipt in parents),
        "base_synthesis_success_tasks": sum(receipt["base_synthesis_model_success"] for receipt in parents),
        "exact_canonical_base_table_tasks": sum(receipt["base_table_exact_canonical"] for receipt in parents),
        "synthesis_capture_valid_tasks": sum(item["source_receipt"]["synthesis_capture_valid"] for item in decoded),
        "combined_candidate_page_tasks": sum(receipt["combined_candidate_page_count"] > 0 for receipt in generic),
        "combined_candidate_page_count_total": sum(receipt["combined_candidate_page_count"] for receipt in generic),
        "generic_mechanical_field_surface_tasks": sum(receipt["generic_mechanical_field_surface_count"] > 0 for receipt in generic),
        "generic_mechanical_field_surface_count_total": sum(receipt["generic_mechanical_field_surface_count"] for receipt in generic),
        "generic_mechanical_observation_tasks": sum(receipt["generic_mechanical_observation_count"] > 0 for receipt in generic),
        "generic_mechanical_observation_count_total": sum(receipt["generic_mechanical_observation_count"] for receipt in generic),
        "available_candidate_tasks": sum(receipt["available_candidate_count"] > 0 for receipt in generic),
        "available_candidate_count_total": sum(receipt["available_candidate_count"] for receipt in generic),
        "applied_candidate_tasks": sum(receipt["applied_coordinate_count"] > 0 for receipt in generic),
        "applied_coordinate_count_total": sum(receipt["applied_coordinate_count"] for receipt in generic),
        "application_failure_tasks": sum(receipt["candidate_application_failure_type"] is not None for receipt in generic),
        "prediction_changed_tasks": sum(receipt["candidate_prediction_changed"] for receipt in generic),
        "budget_rejection_tasks": sum(any(row["actual_effect_snapshot"][f"{kind}_rejected_count"] > 0 for kind in ("query", "fetch", "model")) for row in checked),
        "all_physical_queries": sum(row["actual_effect_snapshot"]["query_admitted_count"] for row in checked),
        "all_physical_fetches": sum(row["actual_effect_snapshot"]["fetch_admitted_count"] for row in checked),
        "all_physical_model_forwards": sum(row["actual_effect_snapshot"]["model_admitted_count"] for row in checked),
        "completed_physical_queries": sum(row["actual_effect_snapshot"]["query_admitted_count"] for row in completed),
        "completed_physical_fetches": sum(row["actual_effect_snapshot"]["fetch_admitted_count"] for row in completed),
        "completed_physical_model_forwards": sum(row["actual_effect_snapshot"]["model_admitted_count"] for row in completed),
        "per_task_hard_cap_preserved_tasks": sum(
            row["actual_effect_snapshot"]["query_admitted_count"] <= 4
            and row["actual_effect_snapshot"]["fetch_admitted_count"] <= 14
            and row["actual_effect_snapshot"]["model_admitted_count"] <= 3
            for row in checked
        ),
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
        "zero_outer_failure": value["outer_failure_tasks"] <= gate["maximum_outer_failure_tasks"],
        "zero_naked_outer_failure": value["naked_outer_failure_tasks"] <= gate["maximum_naked_outer_failure_tasks"],
        "parent_role_exact": value["parent_role_tasks"] == contract.TASK_COUNT,
        "synthesis_capture_valid_exact": value["synthesis_capture_valid_tasks"] == gate["required_synthesis_capture_valid_tasks"],
        "minimum_combined_candidate_page_tasks": value["combined_candidate_page_tasks"] >= gate["minimum_combined_candidate_page_tasks"],
        "minimum_generic_mechanical_field_surface_tasks": value["generic_mechanical_field_surface_tasks"] >= gate["minimum_generic_mechanical_field_surface_tasks"],
        "minimum_generic_mechanical_observation_tasks": value["generic_mechanical_observation_tasks"] >= gate["minimum_generic_mechanical_observation_tasks"],
        "minimum_available_candidate_tasks": value["available_candidate_tasks"] >= gate["minimum_available_candidate_tasks"],
        "minimum_applied_candidate_tasks": value["applied_candidate_tasks"] >= gate["minimum_applied_candidate_tasks"],
        "minimum_prediction_changed_tasks": value["prediction_changed_tasks"] >= gate["minimum_prediction_changed_tasks"],
        "zero_application_failure": value["application_failure_tasks"] <= gate["maximum_application_failure_tasks"],
        "zero_budget_rejection": value["budget_rejection_tasks"] <= gate["maximum_budget_rejection_tasks"],
        "exact_completed_query_budget": value["completed_physical_queries"] == gate["exact_physical_queries_per_completed_task"] * completed,
        "completed_fetch_cap_preserved": value["completed_physical_fetches"] <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "completed_model_budget_preserved": value["completed_physical_model_forwards"] <= gate["maximum_normal_path_model_forwards_per_completed_task"] * completed,
        "all_rows_per_task_hard_caps": value["per_task_hard_cap_preserved_tasks"] == contract.TASK_COUNT,
        "candidate_change_implies_applied_coordinates": value["prediction_changed_tasks"] == 0 or value["applied_coordinate_count_total"] > 0,
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
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "postfreeze_quality_protocol": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.55.04 forward result drifted")
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
