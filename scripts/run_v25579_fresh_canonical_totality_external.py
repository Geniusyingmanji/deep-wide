#!/usr/bin/env python3
"""Run the single authorized V2.55.79 canonical-column totality gate."""

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

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25558_model_pool_contract as model_pool  # noqa: E402
from deepwide_agent import v25575_canonical_column_totality_runtime as runtime  # noqa: E402
from deepwide_agent import v25579_fresh_canonical_totality_external_contract as contract  # noqa: E402
from scripts import run_v25550_visible_constraint_external as harness  # noqa: E402
from scripts import v25478_clone_safe_runner_namespace as clone_safe  # noqa: E402


TASK_ROLE = "v25579_fresh_canonical_totality_frozen_task_result"
FORWARD_ROLE = "v25579_fresh_canonical_totality_forward_result"
FREEZE_ROLE = "v25579_fresh_canonical_totality_prediction_freeze"
ARMS = contract.ARMS
CONTROL_ARM = contract.CONTROL_ARM
CANDIDATE_ARM = contract.CANDIDATE_ARM
EXPECTED_PREDECESSOR_FAILURE = (
    "ValueError: V2.53.95 selected verifier state drifted"
)


_SOURCE_NAMES = (
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
_SOURCE_FUNCTIONS = {name: getattr(harness, name) for name in _SOURCE_NAMES}
_NAMESPACE, _CLONES = clone_safe.clone_group(
    _SOURCE_FUNCTIONS,
    visible_globals=harness.__dict__,
    overrides={
        "contract": contract,
        "runtime": runtime,
        "cap": cap,
        "TASK_ROLE": TASK_ROLE,
        "FORWARD_ROLE": FORWARD_ROLE,
        "FREEZE_ROLE": FREEZE_ROLE,
        "ARMS": ARMS,
        "POOL_ID": model_pool.MODEL_POOL_ID,
    },
    rename_from="v25550",
    rename_to="v25579",
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
    raise RuntimeError("V2.55.79 clone namespace is incomplete")

for _name in (
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
):
    globals()[_name] = _CLONES[_name]


def clone_namespace_receipt() -> dict[str, Any]:
    return copy.deepcopy(_CLONE_NAMESPACE_RECEIPT)


def model_pool_contract() -> dict[str, Any]:
    value = model_pool.contract()
    if _NAMESPACE.get("POOL_ID") != value["model_pool_id"]:
        raise RuntimeError("V2.55.79 runner model pool wiring drifted")
    return value


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
        start.get("role")
        != "v25579_fresh_canonical_totality_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("identity_vector_sha256")
        != protocol["population"]["identity_vector_sha256"]
        or start.get("failure_fallback_vector_sha256")
        != protocol["population"]["failure_fallback_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization") != expected
        or not contract.sealed(start, "execution_start_payload_sha256")
        or current != target
        or len(parents) != 2
        or parents[1] != start.get("git_head")
        or changed != [str(contract.EXECUTION_START)]
    ):
        raise RuntimeError("V2.55.79 execution start drifted")
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
                "role": "v25579_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _task_metadata() -> dict[str, int]:
    output = {
        task["opaque_id"]: index
        for index, task in enumerate(contract.task_vector())
    }
    if len(output) != contract.TASK_COUNT:
        raise RuntimeError("V2.55.79 task metadata drifted")
    return output


def _metadata(task: Mapping[str, str]) -> int:
    index = _task_metadata().get(str(task.get("opaque_id")))
    if index is None or dict(task) != contract.task_vector()[index]:
        raise ValueError("V2.55.79 task is outside frozen population")
    return index


def _fallback_prediction(question: str) -> str:
    for index, task in enumerate(contract.task_vector()):
        if task["question"] == question:
            return contract.failure_fallback(index)
    raise ValueError("V2.55.79 fallback question is outside population")


class _CounterfactualHybrid:
    """Minimal state needed by the frozen V2.53.95 local verifier."""

    prepared_records = None
    grounded_prepared_records = None

    @staticmethod
    def choose_record_source() -> str:
        return "none"


def _predecessor_counterfactual(
    task: Mapping[str, str], columns: Sequence[str] | None
) -> dict[str, Any]:
    if columns is None:
        return {
            "evaluated": False,
            "failed": False,
            "failure_type": None,
            "raw_column_count": 0,
            "uses_parent_prediction_columns": False,
            "uses_empty_page_vector": False,
            "additional_effect_count": 0,
        }
    failure: str | None = None
    try:
        runtime.visible_parent._TaskLocalVerifier(
            _CounterfactualHybrid()
        ).prepare_record_proposal(str(task["question"]), tuple(columns), ())
    except Exception as exc:  # Pure local verifier; preserve exact taxonomy.
        failure = f"{type(exc).__name__}: {exc}"
    return {
        "evaluated": True,
        "failed": failure is not None,
        "failure_type": failure,
        "raw_column_count": len(tuple(columns)),
        "uses_parent_prediction_columns": True,
        "uses_empty_page_vector": True,
        "additional_effect_count": 0,
    }


def _decode_completed(
    task: Mapping[str, str],
    result: Mapping[str, Any],
    stage: Mapping[str, Any],
) -> dict[str, Any]:
    index = _metadata(task)
    checked, checked_stage = runtime.validate_runtime_pair(result, stage)
    canonical_handoff = checked["role"] == runtime.HANDOFF_ROLE
    if canonical_handoff:
        parent_result = runtime.membership_parent.validate_result(
            checked["private_parent_result"]
        )
        parent_stage = runtime.membership_parent.validate_stage_receipt(
            checked_stage["parent_stage_receipt"]
        )
        runtime.validate_handoff_receipt(
            checked["canonical_column_handoff_receipt"],
            parent_result=parent_result,
        )
        successor_mode = "canonical_column_handoff"
        active_family_count = 0
    else:
        parent_result = runtime.totality.parent.validate_result(
            checked["private_parent_result"]
        )
        parent_stage = runtime.totality.parent.validate_stage_receipt(
            checked_stage["parent_stage_receipt"]
        )
        constrained = checked.get("private_constrained_result")
        constrained_result = (
            runtime.totality.constrained.validate_result(constrained)
            if isinstance(constrained, Mapping)
            else None
        )
        receipt = runtime.totality.validate_receipt(
            checked["constraint_totality_receipt"],
            parent_result=parent_result,
            constrained_result=constrained_result,
        )
        successor_mode = str(checked["mode"])
        active_family_count = int(receipt["active_family_count"])
    budget = cap.validate_budget_receipt(
        checked_stage["outer_physical_budget_receipt"]
    )
    internal_predictions = checked.get("predictions") or {}
    if (
        checked["opaque_id"] != task["opaque_id"]
        or checked["private_parent_result_payload_sha256"]
        != parent_result["result_payload_sha256"]
        or checked_stage["parent_runtime_result_payload_sha256"]
        != parent_result["result_payload_sha256"]
        or checked_stage["runtime_result_payload_sha256"]
        != checked["result_payload_sha256"]
        or parent_stage["outer_physical_budget_receipt"] != budget
        or set(internal_predictions) != set(runtime.ARMS)
        or internal_predictions[runtime.CANDIDATE_ARM] != checked["prediction"]
        or internal_predictions[runtime.CONTROL_ARM]
        != parent_result["prediction"]
    ):
        raise ValueError("V2.55.79 successor result/stage chain drifted")
    raw_columns, _reason = runtime.totality._projection_columns(
        parent_result["prediction"]
    )
    expected_columns = contract.population.columns_for_index(index)
    counterfactual = _predecessor_counterfactual(task, raw_columns)
    exposure = contract.population.exposure_for_index(index)
    candidate = str(checked["prediction"])
    control = (
        contract.failure_fallback(index)
        if exposure == "canonical_drift"
        else candidate
    )
    predictions = {CONTROL_ARM: control, CANDIDATE_ARM: candidate}
    parent_preserved = candidate == parent_result["prediction"]
    handoff = successor_mode in {
        "canonical_column_handoff",
        runtime.BYTE_EXACT_PARENT_HANDOFF,
    }
    return {
        "result": checked,
        "stage": checked_stage,
        "parent_result": parent_result,
        "parent_stage": parent_stage,
        "budget": budget,
        "preassigned_exposure": exposure,
        "visible_columns_match_preassigned_exposure": (
            raw_columns == expected_columns
        ),
        "predecessor_counterfactual": counterfactual,
        "successor_mode": successor_mode,
        "successor_canonical_column_handoff": canonical_handoff,
        "successor_ordinary_canonical_projection": (
            exposure == "ordinary_ascii"
            and successor_mode == runtime.CANONICAL_PROJECTION
        ),
        "successor_parent_prediction_byte_preserved": parent_preserved,
        "unsafe_handoff_present": handoff and not parent_preserved,
        "active_visible_constraint_family_count": active_family_count,
        "predictions": predictions,
        "ordinary_control_candidate_byte_equal": (
            exposure == "ordinary_ascii" and control == candidate
        ),
        "drift_fallback_to_candidate_changed": (
            exposure == "canonical_drift" and control != candidate
        ),
        "outer_candidate_equals_successor_prediction": (
            candidate == checked["prediction"]
        ),
        "outer_candidate_equals_successor_parent_prediction": parent_preserved,
    }


_FACT_FIELDS = (
    "preassigned_exposure",
    "visible_columns_match_preassigned_exposure",
    "predecessor_counterfactual_evaluated",
    "predecessor_counterfactual_failed",
    "predecessor_counterfactual_failure_type",
    "predecessor_counterfactual_raw_column_count",
    "predecessor_counterfactual_uses_parent_prediction_columns",
    "predecessor_counterfactual_uses_empty_page_vector",
    "predecessor_counterfactual_additional_effect_count",
    "successor_mode",
    "successor_canonical_column_handoff",
    "successor_ordinary_canonical_projection",
    "successor_parent_prediction_byte_preserved",
    "ordinary_control_candidate_byte_equal",
    "drift_fallback_to_candidate_changed",
    "unsafe_handoff_present",
    "result_stage_binding_failure_present",
    "active_visible_constraint_family_count",
    "outer_candidate_equals_successor_prediction",
    "outer_candidate_equals_successor_parent_prediction",
)


def _fact_fields(decoded: Mapping[str, Any]) -> dict[str, Any]:
    counterfactual = decoded["predecessor_counterfactual"]
    return {
        "preassigned_exposure": decoded["preassigned_exposure"],
        "visible_columns_match_preassigned_exposure": decoded[
            "visible_columns_match_preassigned_exposure"
        ],
        "predecessor_counterfactual_evaluated": counterfactual["evaluated"],
        "predecessor_counterfactual_failed": counterfactual["failed"],
        "predecessor_counterfactual_failure_type": counterfactual[
            "failure_type"
        ],
        "predecessor_counterfactual_raw_column_count": counterfactual[
            "raw_column_count"
        ],
        "predecessor_counterfactual_uses_parent_prediction_columns": counterfactual[
            "uses_parent_prediction_columns"
        ],
        "predecessor_counterfactual_uses_empty_page_vector": counterfactual[
            "uses_empty_page_vector"
        ],
        "predecessor_counterfactual_additional_effect_count": counterfactual[
            "additional_effect_count"
        ],
        "successor_mode": decoded["successor_mode"],
        "successor_canonical_column_handoff": decoded[
            "successor_canonical_column_handoff"
        ],
        "successor_ordinary_canonical_projection": decoded[
            "successor_ordinary_canonical_projection"
        ],
        "successor_parent_prediction_byte_preserved": decoded[
            "successor_parent_prediction_byte_preserved"
        ],
        "ordinary_control_candidate_byte_equal": decoded[
            "ordinary_control_candidate_byte_equal"
        ],
        "drift_fallback_to_candidate_changed": decoded[
            "drift_fallback_to_candidate_changed"
        ],
        "unsafe_handoff_present": decoded["unsafe_handoff_present"],
        "result_stage_binding_failure_present": False,
        "active_visible_constraint_family_count": decoded[
            "active_visible_constraint_family_count"
        ],
        "outer_candidate_equals_successor_prediction": decoded[
            "outer_candidate_equals_successor_prediction"
        ],
        "outer_candidate_equals_successor_parent_prediction": decoded[
            "outer_candidate_equals_successor_parent_prediction"
        ],
    }


def _terminal_outer_failure(
    task: Mapping[str, str],
    exc: BaseException,
    elapsed: float,
    *,
    budget: cap.PhysicalEffectBudget | None,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    index = _metadata(task)
    prediction = contract.failure_fallback(index)
    predictions = {arm: prediction for arm in ARMS}
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": str(task["opaque_id"]),
        "task_index": index,
        "runtime_input_keys": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "terminal": True,
        "successor_runtime_completed": False,
        "failure_as_zero": True,
        "outer_failure_type": (type(exc).__name__ or "Exception")[:128],
        "runtime_result": None,
        "runtime_result_payload_sha256": None,
        "content_free_stage_receipt": None,
        "runtime_stage_payload_sha256": None,
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(prediction.encode()).hexdigest() for arm in ARMS
        },
        "prediction_kind": "fallback",
        "candidate_prediction_changed": False,
        "preassigned_exposure": contract.population.exposure_for_index(index),
        "visible_columns_match_preassigned_exposure": False,
        "predecessor_counterfactual_evaluated": False,
        "predecessor_counterfactual_failed": False,
        "predecessor_counterfactual_failure_type": None,
        "predecessor_counterfactual_raw_column_count": 0,
        "predecessor_counterfactual_uses_parent_prediction_columns": False,
        "predecessor_counterfactual_uses_empty_page_vector": False,
        "predecessor_counterfactual_additional_effect_count": 0,
        "successor_mode": None,
        "successor_canonical_column_handoff": False,
        "successor_ordinary_canonical_projection": False,
        "successor_parent_prediction_byte_preserved": False,
        "ordinary_control_candidate_byte_equal": False,
        "drift_fallback_to_candidate_changed": False,
        "unsafe_handoff_present": False,
        "result_stage_binding_failure_present": False,
        "active_visible_constraint_family_count": 0,
        "outer_candidate_equals_successor_prediction": False,
        "outer_candidate_equals_successor_parent_prediction": False,
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
    before = cap.validate_budget_receipt(budget.receipt())
    decoded = _decode_completed(task, value, stage)
    after = cap.validate_budget_receipt(budget.receipt())
    if before != after or decoded["budget"] != after:
        raise RuntimeError("V2.55.79 counterfactual changed physical effects")
    checked = decoded["result"]
    predictions = copy.deepcopy(decoded["predictions"])
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": checked["opaque_id"],
        "task_index": _metadata(task),
        "runtime_input_keys": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "terminal": True,
        "successor_runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "runtime_result": copy.deepcopy(checked),
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "content_free_stage_receipt": copy.deepcopy(decoded["stage"]),
        "runtime_stage_payload_sha256": contract.payload_sha256(decoded["stage"]),
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "prediction_kind": checked["prediction_kind"],
        "candidate_prediction_changed": (
            predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM]
        ),
        **_fact_fields(decoded),
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


_TASK_INTEGER_FIELDS = (
    "predecessor_counterfactual_raw_column_count",
    "predecessor_counterfactual_additional_effect_count",
    "active_visible_constraint_family_count",
    "positive_signed_credit_count",
)
_TASK_BOOLEAN_FIELDS = (
    "visible_columns_match_preassigned_exposure",
    "predecessor_counterfactual_evaluated",
    "predecessor_counterfactual_failed",
    "predecessor_counterfactual_uses_parent_prediction_columns",
    "predecessor_counterfactual_uses_empty_page_vector",
    "successor_canonical_column_handoff",
    "successor_ordinary_canonical_projection",
    "successor_parent_prediction_byte_preserved",
    "ordinary_control_candidate_byte_equal",
    "drift_fallback_to_candidate_changed",
    "unsafe_handoff_present",
    "result_stage_binding_failure_present",
    "outer_candidate_equals_successor_prediction",
    "outer_candidate_equals_successor_parent_prediction",
)


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "opaque_id",
        "task_index",
        "runtime_input_keys",
        "terminal",
        "successor_runtime_completed",
        "failure_as_zero",
        "outer_failure_type",
        "runtime_result",
        "runtime_result_payload_sha256",
        "content_free_stage_receipt",
        "runtime_stage_payload_sha256",
        "predictions",
        "prediction_sha256",
        "prediction_kind",
        "candidate_prediction_changed",
        *_FACT_FIELDS,
        "actual_effect_snapshot",
        "cost",
        "hard_failure_health",
        "elapsed_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "positive_signed_credit_count",
        "retry_resume_replay_backfill_replacement_or_selective_rerun",
        "question_query_url_title_page_quote_record_field_value_answer_or_credential_persisted_outside_sealed_runtime_and_predictions",
        "result_payload_sha256",
    }
    metadata = _task_metadata().get(str(copied.get("opaque_id")))
    effects = copied.get("actual_effect_snapshot") or {}
    health = copied.get("hard_failure_health") or {}
    predictions = copied.get("predictions") or {}
    hashes = copied.get("prediction_sha256") or {}
    completed = copied.get("successor_runtime_completed") is True
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or metadata is None
        or copied.get("task_index") != metadata
        or copied.get("preassigned_exposure")
        != contract.population.exposure_for_index(metadata)
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("successor_runtime_completed"), bool)
        or copied.get("failure_as_zero") is completed
        or set(predictions) != set(ARMS)
        or any(
            not isinstance(predictions[arm], str) or not predictions[arm]
            for arm in ARMS
        )
        or set(hashes) != set(ARMS)
        or any(
            hashes[arm]
            != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or not isinstance(copied.get("candidate_prediction_changed"), bool)
        or copied["candidate_prediction_changed"]
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or any(
            not isinstance(copied.get(name), bool)
            for name in _TASK_BOOLEAN_FIELDS
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _TASK_INTEGER_FIELDS
        )
        or copied.get("predecessor_counterfactual_failure_type") is not None
        and (
            not isinstance(copied["predecessor_counterfactual_failure_type"], str)
            or not copied["predecessor_counterfactual_failure_type"]
            or len(copied["predecessor_counterfactual_failure_type"]) > 256
        )
        or set(effects) != set(_empty_effect_snapshot())
        or any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for amount in effects.values()
        )
        or set(health) != set(_health())
        or any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for amount in health.values()
        )
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
        raise ValueError("V2.55.79 task row drifted")
    task = contract.task_vector()[metadata]
    if completed:
        runtime_result = copied.get("runtime_result")
        stage = copied.get("content_free_stage_receipt")
        if not isinstance(runtime_result, Mapping) or not isinstance(stage, Mapping):
            raise ValueError("V2.55.79 completed runtime surface is absent")
        decoded = _decode_completed(task, runtime_result, stage)
        expected_facts = _fact_fields(decoded)
        budget = decoded["budget"]
        if (
            copied.get("runtime_result_payload_sha256")
            != decoded["result"]["result_payload_sha256"]
            or copied.get("runtime_stage_payload_sha256")
            != contract.payload_sha256(decoded["stage"])
            or copied["predictions"] != decoded["predictions"]
            or copied["prediction_kind"] != decoded["result"]["prediction_kind"]
            or any(copied[name] != expected_facts[name] for name in _FACT_FIELDS)
            or copied.get("outer_failure_type") is not None
            or copied["cost"] != decoded["result"]["cost"]
            or _validate_cost(copied.get("cost")) != copied["cost"]
            or any(
                effects[f"{kind}_{suffix}_count"]
                != budget[f"{kind}_{suffix}_count"]
                for kind in ("query", "fetch", "model")
                for suffix in ("admitted", "rejected")
            )
        ):
            raise ValueError("V2.55.79 completed task row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or copied.get("runtime_result") is not None
        or copied.get("runtime_result_payload_sha256") is not None
        or copied.get("content_free_stage_receipt") is not None
        or copied.get("runtime_stage_payload_sha256") is not None
        or copied.get("cost") is not None
        or copied.get("prediction_kind") != "fallback"
        or len(set(predictions.values())) != 1
        or copied.get("successor_mode") is not None
        or copied.get("predecessor_counterfactual_failure_type") is not None
        or any(copied[name] is not False for name in _TASK_BOOLEAN_FIELDS)
        or any(copied[name] != 0 for name in _TASK_INTEGER_FIELDS)
    ):
        raise ValueError("V2.55.79 failure task row drifted")
    return copied


AGGREGATE_INTEGER_FIELDS = (
    "task_count",
    "terminal_tasks",
    "successor_runtime_completed_tasks",
    "failure_as_zero_tasks",
    "successor_outer_failure_tasks",
    "successor_model_generated_tasks",
    "successor_fallback_tasks",
    "preassigned_canonical_drift_tasks",
    "preassigned_ordinary_ascii_tasks",
    "visible_columns_match_preassigned_exposure_tasks",
    "predecessor_counterfactual_evaluated_tasks",
    "predecessor_counterfactual_failure_tasks",
    "predecessor_counterfactual_exact_expected_failure_tasks",
    "drift_predecessor_counterfactual_failure_tasks",
    "ordinary_predecessor_counterfactual_nonfailure_tasks",
    "predecessor_counterfactual_additional_effect_count_total",
    "successor_canonical_column_handoff_tasks",
    "drift_successor_canonical_column_handoff_tasks",
    "successor_ordinary_canonical_projection_tasks",
    "successor_parent_prediction_byte_preserved_tasks",
    "candidate_parent_prediction_loss_tasks",
    "ordinary_control_candidate_byte_equal_tasks",
    "drift_fallback_to_candidate_changed_tasks",
    "unsafe_handoff_tasks",
    "result_stage_binding_failure_tasks",
    "outer_candidate_equals_successor_prediction_tasks",
    "active_visible_constraint_family_count_total",
    "budget_rejection_tasks",
    "all_physical_queries",
    "all_physical_fetches",
    "all_physical_model_forwards",
    "completed_physical_queries",
    "completed_physical_fetches",
    "completed_physical_model_forwards",
    "per_task_hard_cap_preserved_tasks",
    "positive_signed_credit_count",
    "system_total_tokens",
)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        *AGGREGATE_INTEGER_FIELDS,
        "batch_wall_seconds",
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
        or copied["successor_runtime_completed_tasks"]
        + copied["failure_as_zero_tasks"]
        != contract.TASK_COUNT
        or copied["successor_outer_failure_tasks"]
        != copied["failure_as_zero_tasks"]
        or copied["preassigned_canonical_drift_tasks"]
        + copied["preassigned_ordinary_ascii_tasks"]
        != contract.TASK_COUNT
        or copied["candidate_parent_prediction_loss_tasks"]
        != copied["successor_runtime_completed_tasks"]
        - copied["successor_parent_prediction_byte_preserved_tasks"]
        or copied["predecessor_counterfactual_exact_expected_failure_tasks"]
        > copied["predecessor_counterfactual_failure_tasks"]
        or copied["drift_predecessor_counterfactual_failure_tasks"]
        > copied["predecessor_counterfactual_failure_tasks"]
        or copied["drift_successor_canonical_column_handoff_tasks"]
        > copied["successor_canonical_column_handoff_tasks"]
        or copied["positive_signed_credit_count"] != 0
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
        raise ValueError("V2.55.79 aggregate drifted")
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
        raise RuntimeError("V2.55.79 fixed population order drifted")
    completed = [row for row in checked if row["successor_runtime_completed"]]
    value: dict[str, Any] = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "successor_runtime_completed_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "successor_outer_failure_tasks": sum(
            not row["successor_runtime_completed"] for row in checked
        ),
        "successor_model_generated_tasks": sum(
            row["successor_runtime_completed"]
            and row["prediction_kind"] == "model_generated"
            for row in checked
        ),
        "successor_fallback_tasks": sum(
            row["prediction_kind"] == "fallback" for row in checked
        ),
        "preassigned_canonical_drift_tasks": sum(
            row["preassigned_exposure"] == "canonical_drift" for row in checked
        ),
        "preassigned_ordinary_ascii_tasks": sum(
            row["preassigned_exposure"] == "ordinary_ascii" for row in checked
        ),
        "visible_columns_match_preassigned_exposure_tasks": sum(
            row["visible_columns_match_preassigned_exposure"] for row in checked
        ),
        "predecessor_counterfactual_evaluated_tasks": sum(
            row["predecessor_counterfactual_evaluated"] for row in checked
        ),
        "predecessor_counterfactual_failure_tasks": sum(
            row["predecessor_counterfactual_failed"] for row in checked
        ),
        "predecessor_counterfactual_exact_expected_failure_tasks": sum(
            row["predecessor_counterfactual_failure_type"]
            == EXPECTED_PREDECESSOR_FAILURE
            for row in checked
        ),
        "drift_predecessor_counterfactual_failure_tasks": sum(
            row["preassigned_exposure"] == "canonical_drift"
            and row["predecessor_counterfactual_failed"]
            for row in checked
        ),
        "ordinary_predecessor_counterfactual_nonfailure_tasks": sum(
            row["preassigned_exposure"] == "ordinary_ascii"
            and row["predecessor_counterfactual_evaluated"]
            and not row["predecessor_counterfactual_failed"]
            for row in checked
        ),
        "predecessor_counterfactual_additional_effect_count_total": sum(
            row["predecessor_counterfactual_additional_effect_count"]
            for row in checked
        ),
        "successor_canonical_column_handoff_tasks": sum(
            row["successor_canonical_column_handoff"] for row in checked
        ),
        "drift_successor_canonical_column_handoff_tasks": sum(
            row["preassigned_exposure"] == "canonical_drift"
            and row["successor_canonical_column_handoff"]
            for row in checked
        ),
        "successor_ordinary_canonical_projection_tasks": sum(
            row["successor_ordinary_canonical_projection"] for row in checked
        ),
        "successor_parent_prediction_byte_preserved_tasks": sum(
            row["successor_parent_prediction_byte_preserved"] for row in checked
        ),
        "candidate_parent_prediction_loss_tasks": sum(
            row["successor_runtime_completed"]
            and not row["successor_parent_prediction_byte_preserved"]
            for row in checked
        ),
        "ordinary_control_candidate_byte_equal_tasks": sum(
            row["ordinary_control_candidate_byte_equal"] for row in checked
        ),
        "drift_fallback_to_candidate_changed_tasks": sum(
            row["drift_fallback_to_candidate_changed"] for row in checked
        ),
        "unsafe_handoff_tasks": sum(
            row["unsafe_handoff_present"] for row in checked
        ),
        "result_stage_binding_failure_tasks": sum(
            row["result_stage_binding_failure_present"] for row in checked
        ),
        "outer_candidate_equals_successor_prediction_tasks": sum(
            row["outer_candidate_equals_successor_prediction"] for row in checked
        ),
        "active_visible_constraint_family_count_total": sum(
            row["active_visible_constraint_family_count"] for row in checked
        ),
        "budget_rejection_tasks": sum(
            any(
                row["actual_effect_snapshot"][f"{kind}_rejected_count"] > 0
                for kind in ("query", "fetch", "model")
            )
            for row in checked
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
        "per_task_hard_cap_preserved_tasks": sum(
            row["actual_effect_snapshot"]["query_admitted_count"] <= 4
            and row["actual_effect_snapshot"]["fetch_admitted_count"] <= 14
            and row["actual_effect_snapshot"]["model_admitted_count"] <= 3
            for row in checked
        ),
        "positive_signed_credit_count": 0,
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"])
            for row in completed
            if row["cost"] is not None
        ),
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate": False,
    }
    return validate_aggregate(value)


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_aggregate(aggregate)
    gate = contract.mechanism_gate()
    completed = value["successor_runtime_completed_tasks"]
    checks = {
        "fixed_task_denominator": value["task_count"]
        == gate["fixed_task_denominator"],
        "all_tasks_terminal": value["terminal_tasks"]
        == gate["required_terminal_tasks"],
        "all_successor_runtime_tasks_completed": completed
        == gate["required_successor_runtime_completed_tasks"],
        "all_successor_model_generated": value["successor_model_generated_tasks"]
        == gate["required_successor_model_generated_tasks"],
        "zero_successor_fallback": value["successor_fallback_tasks"]
        <= gate["maximum_successor_fallback_tasks"],
        "zero_successor_outer_failure": value["successor_outer_failure_tasks"]
        <= gate["maximum_successor_outer_failure_tasks"],
        "preassigned_drift_count_exact": value[
            "preassigned_canonical_drift_tasks"
        ]
        == gate["required_preassigned_canonical_drift_tasks"],
        "preassigned_ordinary_count_exact": value[
            "preassigned_ordinary_ascii_tasks"
        ]
        == gate["required_preassigned_ordinary_ascii_tasks"],
        "all_parent_columns_match_preassigned_exposure": value[
            "visible_columns_match_preassigned_exposure_tasks"
        ]
        == completed,
        "counterfactual_evaluated_for_all_completed": value[
            "predecessor_counterfactual_evaluated_tasks"
        ]
        == completed,
        "predecessor_failure_count_exact": value[
            "predecessor_counterfactual_failure_tasks"
        ]
        == gate["required_predecessor_counterfactual_failure_tasks"],
        "predecessor_failure_taxonomy_exact": value[
            "predecessor_counterfactual_exact_expected_failure_tasks"
        ]
        == gate["required_predecessor_counterfactual_failure_tasks"],
        "all_drift_tasks_reproduce_predecessor_failure": value[
            "drift_predecessor_counterfactual_failure_tasks"
        ]
        == gate["required_preassigned_canonical_drift_tasks"],
        "all_ordinary_tasks_reproduce_predecessor_nonfailure": value[
            "ordinary_predecessor_counterfactual_nonfailure_tasks"
        ]
        == gate["required_preassigned_ordinary_ascii_tasks"],
        "zero_counterfactual_provider_effect": value[
            "predecessor_counterfactual_additional_effect_count_total"
        ]
        == 0,
        "drift_successor_handoff_count_exact": value[
            "drift_successor_canonical_column_handoff_tasks"
        ]
        == gate["required_successor_canonical_column_handoff_tasks"],
        "ordinary_successor_projection_count_exact": value[
            "successor_ordinary_canonical_projection_tasks"
        ]
        == gate["required_successor_ordinary_canonical_projection_tasks"],
        "ordinary_outer_predictions_byte_equal": value[
            "ordinary_control_candidate_byte_equal_tasks"
        ]
        == gate["required_ordinary_control_candidate_byte_equal_tasks"],
        "minimum_drift_fallback_to_candidate_change": value[
            "drift_fallback_to_candidate_changed_tasks"
        ]
        >= gate[
            "minimum_drift_candidate_prediction_changed_from_failure_fallback_tasks"
        ],
        "zero_candidate_parent_prediction_loss": value[
            "candidate_parent_prediction_loss_tasks"
        ]
        <= gate["maximum_candidate_parent_prediction_loss_tasks"],
        "zero_result_stage_binding_failure": value[
            "result_stage_binding_failure_tasks"
        ]
        <= gate["maximum_result_stage_binding_failure_tasks"],
        "zero_unsafe_handoff": value["unsafe_handoff_tasks"]
        <= gate["maximum_unsafe_handoff_tasks"],
        "outer_candidate_is_successor_prediction": value[
            "outer_candidate_equals_successor_prediction_tasks"
        ]
        == completed,
        "zero_old_visible_constraint_family": value[
            "active_visible_constraint_family_count_total"
        ]
        == 0,
        "zero_budget_rejection": value["budget_rejection_tasks"] == 0,
        "exact_completed_query_budget": value["completed_physical_queries"]
        == gate["exact_physical_queries_per_completed_task"] * completed,
        "completed_fetch_cap_preserved": value["completed_physical_fetches"]
        <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "exact_completed_model_budget": value[
            "completed_physical_model_forwards"
        ]
        == gate["exact_normal_path_model_forwards_per_completed_task"]
        * completed,
        "all_rows_per_task_hard_caps": value[
            "per_task_hard_cap_preserved_tasks"
        ]
        == contract.TASK_COUNT,
        "positive_signed_credit_zero": value["positive_signed_credit_count"]
        == gate["positive_signed_credit_count"],
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
        raise ValueError("V2.55.79 forward result drifted")
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
