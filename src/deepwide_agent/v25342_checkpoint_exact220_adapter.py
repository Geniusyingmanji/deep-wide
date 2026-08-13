"""Exact-220 adapter for the validated-production checkpoint runtime.

The frozen V2.52.67 runner expects one outer ``failure_present`` bit, while
V2.52.71 deliberately exposes seven finite microstages and may return a valid
checkpoint prediction after a post-checkpoint microstage failure.  This pure
adapter preserves the complete V2.52.71 result and stage receipt, but maps the
three terminal cases onto the runner boundary:

* a returned normal result is a completed task;
* a returned recovery result is also a completed task and records a recovery
  event without calling it an outer failure;
* an exception before a trustworthy terminal result remains an outer failure.

No model, search, fetch, filesystem, process, evaluator, benchmark label, or
credential capability is added here.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v25271_validated_production_checkpoint_runtime as checkpoint
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient
from . import v25253_outer_physical_cap_observed_runtime as cap


POLICY_ID = "v25342_checkpoint_production_exact220_adapter_v1"
RESULT_ROLE = "v25342_checkpoint_production_exact220_runtime_result"
STAGE_RECEIPT_ROLE = "v25342_checkpoint_production_exact220_stage_receipt"
PHASES = checkpoint.PHASES


class ProductionOnlyStageError(RuntimeError):
    """Outer runner signal containing only a validated finite stage receipt."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.stage_receipt = validate_stage_receipt(receipt)
        super().__init__("V2.53.42 checkpoint exact-220 runtime stage failed")


def _first_failure(stage: Mapping[str, Any]) -> tuple[str | None, str | None]:
    failures = stage["stage_failure_types"]
    for name in checkpoint.STAGES:
        failure = failures[name]
        if failure is not None:
            return name, str(failure)
    return None, None


def _wrap_stage(
    value: Mapping[str, Any], *, runtime_returned: bool
) -> dict[str, Any]:
    checked = checkpoint.validate_stage_receipt(value)
    first_stage, first_type = _first_failure(checked)
    outer_failure = not bool(runtime_returned)
    recovery = bool(
        runtime_returned
        and checked["checkpoint_kind"] is not None
        and checked["recovery_disposition"].endswith(
            "preserved_after_post_checkpoint_failure"
        )
    )
    wrapped: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "checkpoint_stage_receipt": copy.deepcopy(checked),
        "checkpoint_stage_receipt_sha256": checked["receipt_payload_sha256"],
        "runtime_returned": bool(runtime_returned),
        "checkpoint_recovery_event_present": recovery,
        "failure_present": outer_failure,
        "failure_stage": first_stage if outer_failure else None,
        "failure_type": first_type if outer_failure else None,
        "outer_physical_budget_receipt": copy.deepcopy(
            checked["outer_physical_budget_receipt"]
        ),
        "returned_recovery_is_not_misreported_as_outer_failure": True,
        "normal_path_provider_search_fetch_prompt_prediction_unchanged": True,
        "checkpoint_recovery_adds_query_fetch_model_or_token_effect": False,
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "external_forward_evaluator_or_benchmark_authorized": False,
    }
    wrapped["receipt_payload_sha256"] = payload_sha256(wrapped)
    return validate_stage_receipt(wrapped)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    raw = copied.get("checkpoint_stage_receipt")
    if not isinstance(raw, Mapping):
        raise ValueError("V2.53.42 checkpoint stage receipt is absent")
    checked = checkpoint.validate_stage_receipt(raw)
    first_stage, first_type = _first_failure(checked)
    returned = copied.get("runtime_returned") is True
    outer_failure = copied.get("failure_present") is True
    recovery = bool(
        returned
        and checked["checkpoint_kind"] is not None
        and checked["recovery_disposition"].endswith(
            "preserved_after_post_checkpoint_failure"
        )
    )
    true_flags = (
        "returned_recovery_is_not_misreported_as_outer_failure",
        "normal_path_provider_search_fetch_prompt_prediction_unchanged",
    )
    false_flags = (
        "checkpoint_recovery_adds_query_fetch_model_or_token_effect",
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "external_forward_evaluator_or_benchmark_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "checkpoint_stage_receipt",
        "checkpoint_stage_receipt_sha256",
        "runtime_returned",
        "checkpoint_recovery_event_present",
        "failure_present",
        "failure_stage",
        "failure_type",
        "outer_physical_budget_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("checkpoint_stage_receipt_sha256")
        != checked["receipt_payload_sha256"]
        or not isinstance(copied.get("runtime_returned"), bool)
        or not isinstance(copied.get("checkpoint_recovery_event_present"), bool)
        or not isinstance(copied.get("failure_present"), bool)
        or outer_failure is returned
        or copied.get("checkpoint_recovery_event_present")
        is not recovery
        or copied.get("failure_stage")
        != (first_stage if outer_failure else None)
        or copied.get("failure_type") != (first_type if outer_failure else None)
        or outer_failure and first_stage is None
        or copied.get("outer_physical_budget_receipt")
        != checked["outer_physical_budget_receipt"]
        or cap.validate_budget_receipt(copied["outer_physical_budget_receipt"])
        != copied["outer_physical_budget_receipt"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.42 checkpoint stage adapter drifted")
    return copied


def _wrap_result(value: Mapping[str, Any]) -> dict[str, Any]:
    checked = checkpoint.validate_result(value)
    raw_kind = str(checked["prediction_kind"])
    prediction_kind = "model_generated" if raw_kind == "model_generated" else "fallback"
    receipt = checked["content_free_receipt"]
    recovery = bool(
        checked["role"] == checkpoint.RECOVERY_ROLE
        or receipt["post_checkpoint_recoverable_failure_present"]
    )
    wrapped: dict[str, Any] = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": checked["prediction"],
        "prediction_sha256": checked["prediction_sha256"],
        "prediction_kind": prediction_kind,
        "cost": copy.deepcopy(checked["cost"]),
        "checkpoint_runtime_result": copy.deepcopy(checked),
        "checkpoint_runtime_result_payload_sha256": checked[
            "result_payload_sha256"
        ],
        "checkpoint_present": bool(receipt["checkpoint_present"]),
        "checkpoint_recovery_event_present": recovery,
        "normal_path_prediction_cost_and_effect_unchanged": True,
        "recovery_prediction_is_sealed_checkpoint_prediction": bool(
            not recovery
            or checked["prediction"]
            == checked["production_checkpoint"]["prediction"]
        ),
        "additional_query_fetch_model_or_token_effect_for_recovery": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    wrapped["result_payload_sha256"] = payload_sha256(wrapped)
    return wrapped


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw = copied.get("checkpoint_runtime_result")
    if not isinstance(raw, Mapping):
        raise ValueError("V2.53.42 checkpoint runtime result is absent")
    expected = _wrap_result(raw)
    if copied != expected:
        raise ValueError("V2.53.42 checkpoint result adapter drifted")
    if copied["prediction_sha256"] != hashlib.sha256(
        copied["prediction"].encode()
    ).hexdigest():
        raise ValueError("V2.53.42 checkpoint prediction hash drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        result, stage = checkpoint.run_task(
            task,
            model=model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=monotonic,
        )
    except checkpoint.ProductionCheckpointStageError as exc:
        raise ProductionOnlyStageError(
            _wrap_stage(exc.stage_receipt, runtime_returned=False)
        ) from None
    return _wrap_result(result), _wrap_stage(stage, runtime_returned=True)


__all__ = [
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RESULT_ROLE",
    "STAGE_RECEIPT_ROLE",
    "run_task",
    "validate_result",
    "validate_stage_receipt",
]
