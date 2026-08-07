"""Effect accounting for the dedicated V2.48.26 exact transport.

V2.48.23 correctly conserved a ten-fetch controller budget, but assumed all
ten targets used the historical generic helper.  The World Bank path actually
contains two generic discovery-page targets and eight visible-bound exact API
targets.  This append-only successor binds both transport receipts and proves
``2 + 8 == 10`` without changing model, query, fetch, token, or wall budgets.

The module has no filesystem, environment, benchmark, evaluator, or direct
network capability.  Entropy remains a zero-weight shadow feature and receives
no signed task credit.
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
from .v24316_deadline_search import validate_transport_health
from .v24804_shared_prefix_budget_ladder import payload_sha256
from .v24819_quality_first_controller import (
    QualityFirstPolicy,
    run_v24819_task,
    validate_result,
)
from .v24826_worldbank_exact_api_transport import (
    EXPECTED_TARGET_COUNT,
    WorldBankExactAPITransportSearchClient,
    validate_exact_transport_receipt,
)


POLICY_ID = "v24828_quality_first_dedicated_exact_effect_accounting_v1"
ACCOUNTING_ROLE = "v24828_dedicated_exact_effect_accounting"
ENVELOPE_ROLE = "v24828_dedicated_exact_task_envelope"
TOTAL_FETCH_TARGETS = 10
GENERIC_FETCH_TARGETS = 2
DEDICATED_EXACT_FETCH_TARGETS = EXPECTED_TARGET_COUNT


@dataclass(frozen=True)
class IntegratedOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    generic_transport_health: dict[str, Any]
    exact_transport_receipt: dict[str, Any]
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


def _counter(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("V2.48.28 effect counter is not a nonnegative integer")
    return value


def validate_cross_artifacts(
    result: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    generic_transport_health: Mapping[str, Any],
    exact_transport_receipt: Mapping[str, Any],
    expected_cap: int,
) -> dict[str, Any]:
    value = validate_result(result)
    slot = validate_slot_receipt(dict(model_slot_receipt), expected_cap=expected_cap)
    generic = validate_transport_health(generic_transport_health)
    exact = validate_exact_transport_receipt(exact_transport_receipt)
    receipt = value["receipt"]
    model_cost = receipt.get("model_cost")
    search_cost = receipt.get("search_cost")
    if not isinstance(model_cost, Mapping) or not isinstance(search_cost, Mapping):
        raise ValueError("V2.48.28 cost receipt is absent")

    logical_model_calls = _counter(receipt["physical_model_calls"])
    model_requests = _counter(model_cost.get("requests"))
    model_attempts = _counter(model_cost.get("attempts"))
    logical_search_queries = _counter(receipt["physical_search_queries"])
    provider_response_calls = _counter(search_cost.get("calls"))
    provider_attempts = _counter(generic["hosted_search_attempts"])
    logical_fetch_targets = _counter(receipt["physical_fetch_targets"])
    total_fetch_calls = _counter(search_cost.get("fetch_calls"))
    generic_helper_calls = _counter(generic["hard_fetch_helper_calls"])
    generic_deadline_rejections = _counter(generic["fetch_deadline_rejections"])
    generic_fetch_targets = generic_helper_calls + generic_deadline_rejections
    exact_fetch_targets = _counter(exact["logical_requests"])

    if (
        TOTAL_FETCH_TARGETS != GENERIC_FETCH_TARGETS + DEDICATED_EXACT_FETCH_TARGETS
        or logical_model_calls != 2
        or logical_model_calls != slot["acquisitions"]
        or model_requests != slot["acquisitions"]
        or model_attempts < model_requests
        or slot["slot_timeouts"] != 0
        or logical_search_queries != 4
        or provider_response_calls < 1
        or provider_attempts < provider_response_calls
        or logical_fetch_targets != TOTAL_FETCH_TARGETS
        or total_fetch_calls != logical_fetch_targets
        or generic_fetch_targets != GENERIC_FETCH_TARGETS
        or exact_fetch_targets != DEDICATED_EXACT_FETCH_TARGETS
        or generic_fetch_targets + exact_fetch_targets != logical_fetch_targets
    ):
        raise ValueError("V2.48.28 cross-transport effect conservation drifted")

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
        "total_fetch_calls": total_fetch_calls,
        "generic_fetch_targets": generic_fetch_targets,
        "generic_hard_fetch_helper_calls": generic_helper_calls,
        "generic_fetch_deadline_rejections": generic_deadline_rejections,
        "dedicated_exact_fetch_targets": exact_fetch_targets,
        "exact_direct_helper_calls": int(exact["direct_helper_calls"]),
        "exact_direct_deadline_rejections": int(exact["direct_deadline_rejections"]),
        "exact_helper_total_wall_timeouts": int(exact["helper_total_wall_timeouts"]),
        "exact_helper_nonzero_exits": int(exact["helper_nonzero_exits"]),
        "exact_helper_invalid_results": int(exact["helper_invalid_results"]),
        "exact_terminal_successes": int(exact["terminal_successes"]),
        "exact_terminal_exhausted": int(exact["terminal_exhausted"]),
        "exact_provider_attempts": int(exact["provider_attempts"]),
        "exact_provider_retries": int(exact["provider_retries"]),
        "model_slot_receipt_sha256": payload_sha256(slot),
        "generic_transport_health_sha256": payload_sha256(generic),
        "exact_transport_receipt_sha256": payload_sha256(exact),
        "generic_and_exact_transport_effects_disjoint": True,
        "combined_fetch_budget_conserved": True,
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
    integer_fields = {
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
        "total_fetch_calls",
        "generic_fetch_targets",
        "generic_hard_fetch_helper_calls",
        "generic_fetch_deadline_rejections",
        "dedicated_exact_fetch_targets",
        "exact_direct_helper_calls",
        "exact_direct_deadline_rejections",
        "exact_helper_total_wall_timeouts",
        "exact_helper_nonzero_exits",
        "exact_helper_invalid_results",
        "exact_terminal_successes",
        "exact_terminal_exhausted",
        "exact_provider_attempts",
        "exact_provider_retries",
    }
    boolean_fields = {
        "generic_and_exact_transport_effects_disjoint",
        "combined_fetch_budget_conserved",
        "logical_queries_equal_provider_calls_required",
        "provider_attempts_may_exceed_provider_response_calls",
        "mandatory_required_coverage_precedes_cost_stopping",
        "missing_or_drifted_calibration_safe_expands",
        "entropy_shadow_only_not_signed_credit",
        "question_query_url_page_prediction_answer_value_or_opaque_id_emitted",
        "benchmark_launch_or_evaluator_authorized",
    }
    hash_fields = {
        "model_slot_receipt_sha256",
        "generic_transport_health_sha256",
        "exact_transport_receipt_sha256",
    }
    expected = {
        "role",
        "policy_id",
        "accounting_payload_sha256",
        *integer_fields,
        *boolean_fields,
        *hash_fields,
    }
    terminal_exact_failures = (
        copied.get("exact_helper_total_wall_timeouts", 0)
        + copied.get("exact_helper_nonzero_exits", 0)
        + copied.get("exact_helper_invalid_results", 0)
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ACCOUNTING_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or any(
            not isinstance(copied.get(name), str)
            or re_full_sha256(copied[name]) is False
            for name in hash_fields
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
        or copied.get("logical_fetch_targets") != TOTAL_FETCH_TARGETS
        or copied.get("total_fetch_calls") != TOTAL_FETCH_TARGETS
        or copied.get("generic_fetch_targets") != GENERIC_FETCH_TARGETS
        or copied.get("generic_hard_fetch_helper_calls", 0)
        + copied.get("generic_fetch_deadline_rejections", 0)
        != GENERIC_FETCH_TARGETS
        or copied.get("dedicated_exact_fetch_targets")
        != DEDICATED_EXACT_FETCH_TARGETS
        or copied.get("exact_direct_helper_calls", 0)
        + copied.get("exact_direct_deadline_rejections", 0)
        != DEDICATED_EXACT_FETCH_TARGETS
        or copied.get("exact_terminal_successes", 0)
        + copied.get("exact_terminal_exhausted", 0)
        + terminal_exact_failures
        + copied.get("exact_direct_deadline_rejections", 0)
        != DEDICATED_EXACT_FETCH_TARGETS
        or copied.get("exact_provider_retries", 0)
        != copied.get("exact_provider_attempts", 0)
        - copied.get("exact_terminal_successes", 0)
        - copied.get("exact_terminal_exhausted", 0)
        or copied.get("generic_and_exact_transport_effects_disjoint") is not True
        or copied.get("combined_fetch_budget_conserved") is not True
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
        raise ValueError("V2.48.28 dedicated exact effect accounting drifted")
    return copied


def re_full_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def run_v24828_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: WorldBankExactAPITransportSearchClient,
    limits: ScoreFirstLimits,
    quality_first_policy: QualityFirstPolicy,
    monotonic: Any,
) -> IntegratedOutcome:
    visible = validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.48.28 requires deadline-aware model limiter")
    if not isinstance(search, WorldBankExactAPITransportSearchClient):
        raise ValueError("V2.48.28 requires dedicated exact API transport")
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.48.28 deadline identity drifted")
    result = run_v24819_task(
        visible,
        model=model,
        search=search,
        limits=limits,
        quality_first_policy=quality_first_policy,
        monotonic=monotonic,
    )
    slot = model.receipt()
    generic = search.transport_health()
    exact = search.exact_api_transport_receipt()
    accounting = validate_cross_artifacts(
        result,
        model_slot_receipt=slot,
        generic_transport_health=generic,
        exact_transport_receipt=exact,
        expected_cap=int(slot["slot_cap"]),
    )
    return IntegratedOutcome(result, slot, generic, exact, accounting)


def build_envelope(outcome: IntegratedOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "generic_transport_health": copy.deepcopy(outcome.generic_transport_health),
        "exact_transport_receipt": copy.deepcopy(outcome.exact_transport_receipt),
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
        "generic_transport_health",
        "exact_transport_receipt",
        "effect_accounting",
        "private_visible_provider_and_prediction_content_present",
        "private_population_gold_or_evaluator_content_present",
        "private_content_emitted_to_public_aggregate",
        "benchmark_launch_or_evaluator_authorized",
        "envelope_payload_sha256",
    }
    slot = copied.get("model_slot_receipt")
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
        or not isinstance(slot, Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.28 dedicated exact task envelope drifted")
    observed = validate_cross_artifacts(
        copied.get("result", {}),
        model_slot_receipt=slot,
        generic_transport_health=copied.get("generic_transport_health", {}),
        exact_transport_receipt=copied.get("exact_transport_receipt", {}),
        expected_cap=int(slot.get("slot_cap", -1)),
    )
    if copied.get("effect_accounting") != observed:
        raise ValueError("V2.48.28 envelope accounting drifted")
    return copied


__all__ = [
    "ACCOUNTING_ROLE",
    "DEDICATED_EXACT_FETCH_TARGETS",
    "ENVELOPE_ROLE",
    "GENERIC_FETCH_TARGETS",
    "IntegratedOutcome",
    "POLICY_ID",
    "TOTAL_FETCH_TARGETS",
    "build_envelope",
    "run_v24828_task",
    "validate_cross_artifacts",
    "validate_effect_accounting",
    "validate_envelope",
]
