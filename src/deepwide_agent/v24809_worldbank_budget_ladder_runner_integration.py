"""Deadline-aware envelope for the V2.48.09 shared-prefix smoke runtime."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24312_deadline_reliability import (
    DeadlineAwareGlobalModelSlotLimiter,
    validate_receipt as validate_slot_receipt,
)
from .v24316_deadline_search import (
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from .v24804_shared_prefix_budget_ladder import (
    AdaptivePolicy,
    run_v24804_task,
    validate_result,
)
from .v24809_worldbank_budget_ladder_smoke_contract import payload_sha256


POLICY_ID = "v24809_deadline_shared_prefix_budget_ladder_runner_v1"
ENVELOPE_ROLE = "v24809_worldbank_budget_ladder_smoke_task_envelope"


@dataclass(frozen=True)
class IntegratedOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]


def _aligned_deadlines(model: Any, search: Any) -> bool:
    try:
        return (
            abs(float(model.absolute_deadline) - float(search.absolute_deadline)) <= 1e-6
            and abs(float(model.cleanup_reserve_seconds) - float(search.cleanup_reserve_seconds)) <= 1e-6
            and abs(float(model.minimum_attempt_seconds) - float(search.minimum_attempt_seconds)) <= 1e-9
        )
    except (AttributeError, TypeError, ValueError):
        return False


def validate_cross_artifacts(
    result: Mapping[str, Any], *, model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any], expected_cap: int,
) -> None:
    value = validate_result(result)
    slot = validate_slot_receipt(dict(model_slot_receipt), expected_cap=expected_cap)
    health = validate_transport_health(transport_health)
    receipt = value["receipt"]
    if (
        receipt["physical_model_calls"] != slot["acquisitions"]
        or receipt["model_cost"]["requests"] != slot["acquisitions"]
        or slot["slot_timeouts"] != 0
        or receipt["physical_search_queries"] != receipt["search_cost"]["calls"]
        or receipt["physical_fetch_targets"]
        != health["hard_fetch_helper_calls"] + health["fetch_deadline_rejections"]
    ):
        raise ValueError("V2.48.09 cross-artifact effect conservation drifted")


def run_v24809_task(
    task: Mapping[str, Any], *, model: DeadlineAwareGlobalModelSlotLimiter,
    search: DeadlineAwareNativeSearchClient, limits: ScoreFirstLimits,
    adaptive_policy: AdaptivePolicy, monotonic: Any,
) -> IntegratedOutcome:
    visible = validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.48.09 requires deadline-aware model limiter")
    if not isinstance(search, DeadlineAwareNativeSearchClient):
        raise ValueError("V2.48.09 requires deadline-aware search")
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.48.09 deadline identity drifted")
    result = run_v24804_task(
        visible, model=model, search=search, limits=limits,
        adaptive_policy=adaptive_policy, monotonic=monotonic,
    )
    slot = model.receipt()
    health = search.transport_health()
    validate_cross_artifacts(
        result, model_slot_receipt=slot, transport_health=health,
        expected_cap=int(slot["slot_cap"]),
    )
    return IntegratedOutcome(result, slot, health)


def build_envelope(outcome: IntegratedOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "private_visible_provider_and_prediction_content_present": True,
        "private_population_gold_or_evaluator_content_present": False,
        "private_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    return validate_envelope(value)


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("envelope_payload_sha256", None)
    if (
        value.get("role") != ENVELOPE_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(value.get("result"), Mapping)
        or not isinstance(value.get("model_slot_receipt"), Mapping)
        or not isinstance(value.get("transport_health"), Mapping)
        or value.get("private_visible_provider_and_prediction_content_present") is not True
        or value.get("private_population_gold_or_evaluator_content_present") is not False
        or value.get("private_content_emitted_to_public_aggregate") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.09 task envelope drifted")
    slot = value["model_slot_receipt"]
    validate_cross_artifacts(
        value["result"], model_slot_receipt=slot,
        transport_health=value["transport_health"],
        expected_cap=int(slot.get("slot_cap", -1)),
    )
    return copy.deepcopy(dict(value))


__all__ = [
    "ENVELOPE_ROLE", "IntegratedOutcome", "POLICY_ID", "build_envelope",
    "run_v24809_task", "validate_cross_artifacts", "validate_envelope",
]
