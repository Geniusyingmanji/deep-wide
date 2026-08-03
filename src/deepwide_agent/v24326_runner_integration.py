"""Deadline-safe runner integration for V2.43.25 paired task results."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import (
    DeadlineAwareGlobalModelSlotLimiter,
    validate_receipt as validate_slot_receipt,
)
from .v24316_deadline_search import (
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from .v24325_shared_prefix_revision_runtime import (
    run_v24325_total_task,
    validate_result,
)


POLICY_ID = "v24326_deadline_shared_prefix_revision_runner_v1"
ENVELOPE_ROLE = "v24326_shared_prefix_revision_task_envelope"


@dataclass(frozen=True)
class IntegratedPairOutcome:
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
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    expected_cap: int,
) -> None:
    validate_result(result)
    slot = validate_slot_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    validate_transport_health(transport_health)
    receipt = result["shared_prefix_revision_receipt"]
    if receipt["effect_accounting_complete"]:
        if (
            receipt["provider_model_requests"] != slot["acquisitions"]
            or receipt["pre_provider_model_rejections"] != slot["slot_timeouts"]
            or receipt["logical_model_admissions"]
            != slot["acquisitions"] + slot["slot_timeouts"]
            or receipt["provider_model_attempts"]
            != int(result["cost"]["model"]["attempts"])
        ):
            raise ValueError("V2.43.26 complete model effect conservation drifted")
    elif (
        receipt["unattributed_model_effects_lower_bound"]
        < slot["acquisitions"]
        or receipt["unattributed_model_attempts_lower_bound"]
        != int(result["cost"]["model"]["attempts"])
    ):
        raise ValueError("V2.43.26 incomplete model lower bound drifted")
    if int(result["cost"]["search"]["fetch_calls"]) != int(
        transport_health["hard_fetch_helper_calls"]
    ) + int(transport_health["fetch_deadline_rejections"]):
        raise ValueError("V2.43.26 fetch effect/health conservation drifted")


def run_v24326_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: DeadlineAwareNativeSearchClient,
    limits: ScoreFirstLimits,
    monotonic: Any,
) -> IntegratedPairOutcome:
    visible = validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.43.26 requires the deadline-aware model limiter")
    if not isinstance(search, DeadlineAwareNativeSearchClient):
        raise ValueError("V2.43.26 requires the deadline-aware search transport")
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.43.26 model/search deadline identity drifted")
    result = run_v24325_total_task(
        visible,
        model=model,
        search=search,
        limits=limits,
        monotonic=monotonic,
    )
    slot = model.receipt()
    health = search.transport_health()
    validate_cross_artifacts(
        result,
        model_slot_receipt=slot,
        transport_health=health,
        expected_cap=int(slot["slot_cap"]),
    )
    return IntegratedPairOutcome(result, slot, health)


def build_envelope(outcome: IntegratedPairOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "contains_question_prompt_response_query_url_page_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    validate_envelope(value)
    return value


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "result",
        "model_slot_receipt",
        "transport_health",
        "contains_question_prompt_response_query_url_page_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "envelope_payload_sha256",
    }
    unsigned = dict(value)
    seal = unsigned.pop("envelope_payload_sha256", None)
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != ENVELOPE_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(value.get("result"), Mapping)
        or not isinstance(value.get("model_slot_receipt"), Mapping)
        or not isinstance(value.get("transport_health"), Mapping)
        or value.get("contains_question_prompt_response_query_url_page_or_credential")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.26 envelope identity drifted")
    validate_result(value["result"])
    slot = value["model_slot_receipt"]
    validate_slot_receipt(
        dict(slot), expected_cap=int(slot.get("slot_cap", -1))
    )
    validate_transport_health(value["transport_health"])
    validate_cross_artifacts(
        value["result"],
        model_slot_receipt=slot,
        transport_health=value["transport_health"],
        expected_cap=int(slot["slot_cap"]),
    )
    return dict(value)


def validate_observed_bundle(
    value: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    expected_cap: int,
) -> dict[str, Any]:
    envelope = validate_envelope(value)
    slot = validate_slot_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    health = validate_transport_health(transport_health)
    if (
        envelope["model_slot_receipt"] != slot
        or envelope["transport_health"] != health
    ):
        raise ValueError("V2.43.26 independent receipt file drifted from envelope")
    validate_cross_artifacts(
        envelope["result"],
        model_slot_receipt=slot,
        transport_health=health,
        expected_cap=expected_cap,
    )
    return envelope


__all__ = [
    "ENVELOPE_ROLE",
    "IntegratedPairOutcome",
    "POLICY_ID",
    "build_envelope",
    "run_v24326_task",
    "validate_cross_artifacts",
    "validate_envelope",
    "validate_observed_bundle",
]
