"""Runner integration for V2.43.18 conservation and V2.43.16 search deadlines.

The module is benchmark-agnostic.  It binds one visible task to a shared model
and search absolute deadline, validates the cross-artifact effect equations,
and provides a fail-closed parent projection when a child cannot publish an
exact result.  An incomplete parent projection remains a fixed-denominator
prediction but cannot satisfy a promotion gate.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24263_global_model_limiter import payload_sha256
from .v24259_deterministic_table_normalizer import validate_v24259_result
from .v24267_total_fallback import build_total_fallback_result
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24294_staged_reserve import StagedReservePolicy
from .v24312_deadline_reliability import (
    DeadlineAwareGlobalModelSlotLimiter,
    validate_receipt as validate_slot_receipt,
)
from .v24316_deadline_search import (
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from .v24318_deadline_conservation_runtime import (
    MODEL_FIELD,
    run_v24318_task,
    validate_model_receipt,
    validate_v24318_result,
)


POLICY_ID = "v24319_deadline_conservation_runner_integration_v1"
ENVELOPE_ROLE = "v24319_deadline_conservation_task_envelope"
PARENT_BOUNDS_ROLE = "v24319_parent_effect_bounds"
PARENT_BOUNDS_FIELD = "v24319_parent_effect_bounds"
ARMS = ("baseline", "candidate")
STAGES = ("plan", "synthesis_initial", "synthesis_recovery", "repair")


@dataclass(frozen=True)
class IntegratedTaskOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]


def _aligned_deadlines(model: Any, search: Any) -> bool:
    try:
        return (
            abs(float(model.absolute_deadline) - float(search.absolute_deadline))
            <= 1e-6
            and abs(
                float(model.cleanup_reserve_seconds)
                - float(search.cleanup_reserve_seconds)
            )
            <= 1e-6
            and abs(
                float(model.minimum_attempt_seconds)
                - float(search.minimum_attempt_seconds)
            )
            <= 1e-9
        )
    except (AttributeError, TypeError, ValueError):
        return False


def validate_cross_artifacts(
    result: Mapping[str, Any],
    *,
    arm: str,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    expected_cap: int,
) -> None:
    validate_v24318_result(result, arm)
    conservation = validate_model_receipt(result[MODEL_FIELD])
    slot = validate_slot_receipt(
        dict(model_slot_receipt),
        expected_cap=expected_cap,
        expected_acquisitions=int(conservation["provider_requests_total"]),
    )
    validate_transport_health(transport_health)
    if (
        conservation["pre_provider_rejections_total"] != slot["slot_timeouts"]
        or conservation["logical_admissions_total"]
        != slot["acquisitions"] + slot["slot_timeouts"]
        or conservation["provider_requests_total"] != slot["acquisitions"]
        or conservation["provider_attempts_total"]
        != int(result["cost"]["model"]["attempts"])
    ):
        raise ValueError("V2.43.19 cross-artifact effect conservation drifted")


def run_v24319_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: DeadlineAwareNativeSearchClient,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Any,
    progress: Any = None,
) -> IntegratedTaskOutcome:
    visible = validate_visible_task(task)
    if arm not in ARMS:
        raise ValueError("V2.43.19 arm is invalid")
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.43.19 requires the deadline-aware model limiter")
    if not isinstance(search, DeadlineAwareNativeSearchClient):
        raise ValueError("V2.43.19 requires the deadline-aware search transport")
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.43.19 model/search deadline identity drifted")
    result = run_v24318_task(
        visible,
        arm=arm,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
        reserve_policy=reserve_policy,
        monotonic=monotonic,
        progress=progress,
    )
    slot = model.receipt()
    health = search.transport_health()
    validate_cross_artifacts(
        result,
        arm=arm,
        model_slot_receipt=slot,
        transport_health=health,
        expected_cap=int(slot["slot_cap"]),
    )
    return IntegratedTaskOutcome(result, slot, health)


def build_envelope(outcome: IntegratedTaskOutcome, *, arm: str) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "result": copy.deepcopy(outcome.result),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    validate_envelope(value)
    return value


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "result",
        "transport_health",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "envelope_payload_sha256",
    }
    unsigned = dict(value)
    seal = unsigned.pop("envelope_payload_sha256", None)
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != ENVELOPE_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") not in ARMS
        or not isinstance(value.get("result"), Mapping)
        or not isinstance(value.get("transport_health"), Mapping)
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.19 task envelope drifted")
    validate_v24318_result(value["result"], str(value["arm"]))
    validate_transport_health(value["transport_health"])
    return dict(value)


def _empty_stage_counts() -> dict[str, int]:
    return {stage: 0 for stage in STAGES}


def _safe_progress_model(progress: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(progress, Mapping):
        return None
    value = progress.get(MODEL_FIELD)
    if not isinstance(value, Mapping):
        return None
    try:
        return validate_model_receipt(value)
    except (KeyError, TypeError, ValueError):
        return None


def build_parent_effect_bounds(
    *,
    model_call_cap: int,
    progress: Mapping[str, Any] | None,
    model_slot_receipt: Mapping[str, Any] | None,
    expected_cap: int,
) -> dict[str, Any]:
    if model_call_cap != 3:
        raise ValueError("V2.43.19 parent projection requires exact three-call cap")
    safe = _safe_progress_model(progress)
    safe_logical = int(safe["logical_admissions_total"]) if safe else 0
    safe_requests = int(safe["provider_requests_total"]) if safe else 0
    safe_attempts = int(safe["provider_attempts_total"]) if safe else 0
    safe_rejected = int(safe["pre_provider_rejections_total"]) if safe else 0
    logical_by_stage = (
        dict(safe["logical_admissions_by_stage"]) if safe else _empty_stage_counts()
    )
    slot: dict[str, Any] | None = None
    if isinstance(model_slot_receipt, Mapping):
        try:
            slot = validate_slot_receipt(
                dict(model_slot_receipt), expected_cap=expected_cap
            )
        except (KeyError, TypeError, ValueError):
            slot = None
    if slot is not None:
        requests_lower = max(safe_requests, int(slot["acquisitions"]))
        rejected_lower = max(safe_rejected, int(slot["slot_timeouts"]))
        logical_lower = max(safe_logical, requests_lower + rejected_lower)
    else:
        requests_lower = safe_requests
        rejected_lower = safe_rejected
        logical_lower = safe_logical
    logical_lower = min(model_call_cap, logical_lower)
    requests_lower = min(logical_lower, requests_lower)
    rejected_lower = min(logical_lower - requests_lower, rejected_lower)
    value = {
        "artifact_version": 1,
        "role": PARENT_BOUNDS_ROLE,
        "policy_id": POLICY_ID,
        "model_call_cap": model_call_cap,
        "known_logical_admissions_by_stage": logical_by_stage,
        "logical_admissions_lower_bound": logical_lower,
        "logical_admissions_upper_bound": model_call_cap,
        "provider_requests_lower_bound": requests_lower,
        "provider_requests_upper_bound": model_call_cap,
        "provider_attempts_lower_bound": max(requests_lower, safe_attempts),
        "pre_provider_rejections_lower_bound": rejected_lower,
        "pre_provider_rejections_upper_bound": model_call_cap,
        "effect_count_complete": False,
        "effect_attribution_complete": False,
        "provider_attempt_count_complete": False,
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    validate_parent_effect_bounds(value)
    return value


def validate_parent_effect_bounds(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "model_call_cap",
        "known_logical_admissions_by_stage",
        "logical_admissions_lower_bound",
        "logical_admissions_upper_bound",
        "provider_requests_lower_bound",
        "provider_requests_upper_bound",
        "provider_attempts_lower_bound",
        "pre_provider_rejections_lower_bound",
        "pre_provider_rejections_upper_bound",
        "effect_count_complete",
        "effect_attribution_complete",
        "provider_attempt_count_complete",
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    counts = value.get("known_logical_admissions_by_stage")
    numeric = (
        "logical_admissions_lower_bound",
        "logical_admissions_upper_bound",
        "provider_requests_lower_bound",
        "provider_requests_upper_bound",
        "provider_attempts_lower_bound",
        "pre_provider_rejections_lower_bound",
        "pre_provider_rejections_upper_bound",
    )
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != PARENT_BOUNDS_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("model_call_cap") != 3
        or not isinstance(counts, Mapping)
        or set(counts) != set(STAGES)
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number not in {0, 1}
            for number in counts.values()
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in numeric
        )
        or value.get("effect_count_complete") is not False
        or value.get("effect_attribution_complete") is not False
        or value.get("provider_attempt_count_complete") is not False
        or value.get("question_prompt_response_prediction_answer_opaque_id_or_credential_emitted")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.43.19 parent effect bounds drifted")
    logical_lower = value["logical_admissions_lower_bound"]
    logical_upper = value["logical_admissions_upper_bound"]
    requests_lower = value["provider_requests_lower_bound"]
    requests_upper = value["provider_requests_upper_bound"]
    rejected_lower = value["pre_provider_rejections_lower_bound"]
    rejected_upper = value["pre_provider_rejections_upper_bound"]
    if (
        not sum(counts.values()) <= logical_lower <= logical_upper == 3
        or not requests_lower <= requests_upper <= logical_upper
        or not rejected_lower <= rejected_upper <= logical_upper
        or requests_lower + rejected_lower > logical_lower
        or value["provider_attempts_lower_bound"] < requests_lower
    ):
        raise ValueError("V2.43.19 parent effect bounds are inconsistent")
    return dict(value)


def project_parent_failure(
    task: Mapping[str, Any],
    *,
    limits: ScoreFirstLimits,
    completion_kind: str,
    failure_type: str,
    elapsed_seconds: float,
    progress: Mapping[str, Any] | None,
    model_slot_receipt: Mapping[str, Any] | None,
    expected_cap: int,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    bounds = build_parent_effect_bounds(
        model_call_cap=limits.model_calls,
        progress=progress,
        model_slot_receipt=model_slot_receipt,
        expected_cap=expected_cap,
    )
    current = dict(progress) if isinstance(progress, Mapping) else {}
    model_cost = current.get("model_cost")
    model_cost = dict(model_cost) if isinstance(model_cost, Mapping) else {}
    model_cost["requests"] = bounds["provider_requests_lower_bound"]
    model_cost["attempts"] = bounds["provider_attempts_lower_bound"]
    current["model_cost"] = model_cost
    current["admitted_model_calls"] = bounds["logical_admissions_lower_bound"]
    value = build_total_fallback_result(
        visible,
        limits=limits,
        completion_kind=completion_kind,
        failure_stage="v24319_parent_executor",
        failure_type=failure_type,
        elapsed_seconds=elapsed_seconds,
        last_progress=current,
    )
    value["budget"]["events"] = [
        {"stage": "v24319_unattributed_model_effect", "effect": "model", "admitted": True}
        for _ in range(bounds["logical_admissions_lower_bound"])
    ]
    value["budget"]["admitted_model_calls"] = bounds[
        "logical_admissions_lower_bound"
    ]
    value[PARENT_BOUNDS_FIELD] = bounds
    validate_projected_parent_result(value)
    return value


def validate_projected_parent_result(value: Mapping[str, Any]) -> None:
    bounds = value.get(PARENT_BOUNDS_FIELD)
    if not isinstance(bounds, Mapping):
        raise ValueError("V2.43.19 parent bounds are absent")
    validate_parent_effect_bounds(bounds)
    parent = copy.deepcopy(dict(value))
    parent.pop(PARENT_BOUNDS_FIELD, None)
    validate_v24259_result(parent)
    admitted = [
        event
        for event in parent["budget"]["events"]
        if event.get("effect") == "model" and event.get("admitted") is True
    ]
    if (
        parent.get("completion_kind")
        not in {"worker_failure_fallback", "hard_deadline_fallback"}
        or parent["budget"]["admitted_model_calls"]
        != bounds["logical_admissions_lower_bound"]
        or len(admitted) != bounds["logical_admissions_lower_bound"]
        or parent["cost"]["model"]["requests"]
        != bounds["provider_requests_lower_bound"]
        or parent["cost"]["model"]["attempts"]
        != bounds["provider_attempts_lower_bound"]
    ):
        raise ValueError("V2.43.19 projected parent result drifted")


__all__ = [
    "ARMS",
    "ENVELOPE_ROLE",
    "IntegratedTaskOutcome",
    "PARENT_BOUNDS_FIELD",
    "POLICY_ID",
    "build_envelope",
    "build_parent_effect_bounds",
    "project_parent_failure",
    "run_v24319_task",
    "validate_cross_artifacts",
    "validate_envelope",
    "validate_parent_effect_bounds",
    "validate_projected_parent_result",
]
