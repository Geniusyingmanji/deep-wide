"""Deadline/accounting integration for the V2.48.19 quality-first runtime.

This append-only adapter keeps V2.48.12's effect-accounting semantics while
validating V2.48.19 result and receipt roles.  It has no filesystem, process,
environment, benchmark, evaluator, or network capability.
"""

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
from .v24804_shared_prefix_budget_ladder import payload_sha256
from .v24819_quality_first_controller import (
    QualityFirstPolicy,
    run_v24819_task,
    validate_result,
)


POLICY_ID = "v24823_quality_first_batched_effect_accounting_v1"
ACCOUNTING_ROLE = "v24823_quality_first_effect_accounting"
ENVELOPE_ROLE = "v24823_quality_first_task_envelope"


@dataclass(frozen=True)
class IntegratedOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    effect_accounting: dict[str, Any]


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


def _nonnegative_integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("V2.48.23 effect counter is not a nonnegative integer")
    return value


def validate_cross_artifacts(
    result: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    expected_cap: int,
) -> dict[str, Any]:
    value = validate_result(result)
    slot = validate_slot_receipt(dict(model_slot_receipt), expected_cap=expected_cap)
    health = validate_transport_health(transport_health)
    receipt = value["receipt"]
    model_cost = receipt.get("model_cost")
    search_cost = receipt.get("search_cost")
    if not isinstance(model_cost, Mapping) or not isinstance(search_cost, Mapping):
        raise ValueError("V2.48.23 cost receipt is absent")
    logical_model_calls = _nonnegative_integer(receipt["physical_model_calls"])
    model_requests = _nonnegative_integer(model_cost.get("requests"))
    model_attempts = _nonnegative_integer(model_cost.get("attempts"))
    logical_search_queries = _nonnegative_integer(
        receipt["physical_search_queries"]
    )
    provider_response_calls = _nonnegative_integer(search_cost.get("calls"))
    provider_attempts = _nonnegative_integer(health["hosted_search_attempts"])
    logical_fetch_targets = _nonnegative_integer(receipt["physical_fetch_targets"])
    fetch_calls = _nonnegative_integer(search_cost.get("fetch_calls"))
    helper_calls = _nonnegative_integer(health["hard_fetch_helper_calls"])
    deadline_rejections = _nonnegative_integer(health["fetch_deadline_rejections"])
    if (
        logical_model_calls != 2
        or logical_model_calls != slot["acquisitions"]
        or model_requests != slot["acquisitions"]
        or model_attempts < model_requests
        or slot["slot_timeouts"] != 0
        or logical_search_queries != 4
        or provider_response_calls < 1
        or provider_attempts < provider_response_calls
        or logical_fetch_targets != 10
        or fetch_calls != logical_fetch_targets
        or helper_calls + deadline_rejections != logical_fetch_targets
    ):
        raise ValueError("V2.48.23 cross-artifact effect conservation drifted")
    accounting = {
        "artifact_version": 1,
        "role": ACCOUNTING_ROLE,
        "policy_id": POLICY_ID,
        "logical_model_calls": logical_model_calls,
        "model_slot_acquisitions": int(slot["acquisitions"]),
        "model_provider_requests": model_requests,
        "model_provider_attempts": model_attempts,
        "logical_search_queries": logical_search_queries,
        "search_many_invocations": 1,
        "terminal_successful_provider_batches": 1,
        "provider_response_calls": provider_response_calls,
        "provider_attempts": provider_attempts,
        "logical_fetch_targets": logical_fetch_targets,
        "fetch_calls": fetch_calls,
        "hard_fetch_helper_calls": helper_calls,
        "fetch_deadline_rejections": deadline_rejections,
        "logical_queries_equal_provider_calls_required": False,
        "provider_attempts_may_exceed_provider_response_calls": True,
        "mandatory_required_coverage_precedes_cost_stopping": receipt[
            "mandatory_required_coverage_precedes_cost_stopping"
        ],
        "missing_or_drifted_calibration_safe_expands": receipt[
            "missing_or_drifted_calibration_safe_expands"
        ],
        "entropy_shadow_only_not_signed_credit": receipt[
            "entropy_shadow_only_not_signed_credit"
        ],
        "question_query_url_page_prediction_answer_value_or_opaque_id_emitted": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    accounting["accounting_payload_sha256"] = payload_sha256(accounting)
    return validate_effect_accounting(accounting)


def validate_effect_accounting(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("accounting_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "logical_model_calls",
        "model_slot_acquisitions",
        "model_provider_requests",
        "model_provider_attempts",
        "logical_search_queries",
        "search_many_invocations",
        "terminal_successful_provider_batches",
        "provider_response_calls",
        "provider_attempts",
        "logical_fetch_targets",
        "fetch_calls",
        "hard_fetch_helper_calls",
        "fetch_deadline_rejections",
        "logical_queries_equal_provider_calls_required",
        "provider_attempts_may_exceed_provider_response_calls",
        "mandatory_required_coverage_precedes_cost_stopping",
        "missing_or_drifted_calibration_safe_expands",
        "entropy_shadow_only_not_signed_credit",
        "question_query_url_page_prediction_answer_value_or_opaque_id_emitted",
        "benchmark_launch_or_evaluator_authorized",
        "accounting_payload_sha256",
    }
    integers = {
        "artifact_version",
        "logical_model_calls",
        "model_slot_acquisitions",
        "model_provider_requests",
        "model_provider_attempts",
        "logical_search_queries",
        "search_many_invocations",
        "terminal_successful_provider_batches",
        "provider_response_calls",
        "provider_attempts",
        "logical_fetch_targets",
        "fetch_calls",
        "hard_fetch_helper_calls",
        "fetch_deadline_rejections",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ACCOUNTING_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integers
        )
        or copied.get("logical_model_calls") != 2
        or copied.get("model_slot_acquisitions") != 2
        or copied.get("model_provider_requests") != 2
        or copied.get("model_provider_attempts", 0) < 2
        or copied.get("logical_search_queries") != 4
        or copied.get("search_many_invocations") != 1
        or copied.get("terminal_successful_provider_batches") != 1
        or copied.get("provider_response_calls", 0) < 1
        or copied.get("provider_attempts", 0)
        < copied.get("provider_response_calls", 0)
        or copied.get("logical_fetch_targets") != 10
        or copied.get("fetch_calls") != 10
        or copied.get("hard_fetch_helper_calls", 0)
        + copied.get("fetch_deadline_rejections", 0)
        != 10
        or copied.get("logical_queries_equal_provider_calls_required") is not False
        or copied.get("provider_attempts_may_exceed_provider_response_calls")
        is not True
        or copied.get("mandatory_required_coverage_precedes_cost_stopping")
        is not True
        or copied.get("missing_or_drifted_calibration_safe_expands") is not True
        or copied.get("entropy_shadow_only_not_signed_credit") is not True
        or copied.get(
            "question_query_url_page_prediction_answer_value_or_opaque_id_emitted"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.23 effect accounting drifted")
    return copied


def run_v24823_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: DeadlineAwareNativeSearchClient,
    limits: ScoreFirstLimits,
    quality_first_policy: QualityFirstPolicy,
    monotonic: Any,
) -> IntegratedOutcome:
    visible = validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.48.23 requires deadline-aware model limiter")
    if not isinstance(search, DeadlineAwareNativeSearchClient):
        raise ValueError("V2.48.23 requires deadline-aware search")
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.48.23 deadline identity drifted")
    result = run_v24819_task(
        visible,
        model=model,
        search=search,
        limits=limits,
        quality_first_policy=quality_first_policy,
        monotonic=monotonic,
    )
    slot = model.receipt()
    health = search.transport_health()
    accounting = validate_cross_artifacts(
        result,
        model_slot_receipt=slot,
        transport_health=health,
        expected_cap=int(slot["slot_cap"]),
    )
    return IntegratedOutcome(result, slot, health, accounting)


def build_envelope(outcome: IntegratedOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "effect_accounting": copy.deepcopy(outcome.effect_accounting),
        "private_visible_provider_and_prediction_content_present": True,
        "private_population_gold_or_evaluator_content_present": False,
        "private_content_emitted_to_public_aggregate": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    return validate_envelope(value)


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("envelope_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "result",
        "model_slot_receipt",
        "transport_health",
        "effect_accounting",
        "private_visible_provider_and_prediction_content_present",
        "private_population_gold_or_evaluator_content_present",
        "private_content_emitted_to_public_aggregate",
        "benchmark_launch_or_evaluator_authorized",
        "envelope_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ENVELOPE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("private_visible_provider_and_prediction_content_present")
        is not True
        or copied.get("private_population_gold_or_evaluator_content_present")
        is not False
        or copied.get("private_content_emitted_to_public_aggregate") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.23 task envelope drifted")
    slot = copied.get("model_slot_receipt")
    if not isinstance(slot, Mapping):
        raise ValueError("V2.48.23 model receipt is absent")
    observed = validate_cross_artifacts(
        copied.get("result", {}),
        model_slot_receipt=slot,
        transport_health=copied.get("transport_health", {}),
        expected_cap=int(slot.get("slot_cap", -1)),
    )
    if copied.get("effect_accounting") != observed:
        raise ValueError("V2.48.23 envelope accounting drifted")
    return copied


__all__ = [
    "ACCOUNTING_ROLE",
    "ENVELOPE_ROLE",
    "IntegratedOutcome",
    "POLICY_ID",
    "build_envelope",
    "run_v24823_task",
    "validate_cross_artifacts",
    "validate_effect_accounting",
    "validate_envelope",
]
