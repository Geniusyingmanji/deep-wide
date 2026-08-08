"""Same-pass pacing-aware admission for bounded two-wave retrieval.

V2.48.55 showed that the V2.48.52 provider-wide queue wait was included in
the legacy 30-second first-wave latency ceiling.  This append-only adapter
changes only that admission threshold: after the first wave, it credits the
critical-path *maximum* provider-gate wait observed by the same task, capped
at 30 seconds.  Raw first-wave elapsed time remains unchanged in the frozen
retrieval receipt, while the controller's policy records the effective
ceiling used for replay.

The adapter does not change the task absolute deadline, cleanup reserve,
query/fetch/model/token caps, search pacing/cooldown, prompts, evidence, or
synthesis.  It reads no question, benchmark label, mapping, gold, evaluator,
score, reward, prediction, URL, page, or credential.  Historical cohort
membership is never an input.
"""

from __future__ import annotations

import contextvars
import dataclasses
import json
import math
import types
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24272_two_wave_retrieval as parent_retrieval
from .v24272_two_wave_entropy_voc import (
    DECISIONS,
    REASONS,
    FirstWaveObservation,
    TwoWavePolicy,
    decide_two_wave as legacy_decide_two_wave,
    object_sha256,
)
from .v24852_rate_aware_tavily_search import (
    validate_receipt as validate_rate_receipt,
)


POLICY_ID = "v24856_same_pass_max_provider_wait_pacing_aware_admission_v1"
ROLE = "v24856_pacing_aware_admission_receipt"
MAX_PROVIDER_WAIT_CREDIT_SECONDS = 30.0
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "base_controller_policy_id",
        "provider_wait_metric",
        "provider_start_reservations_before",
        "provider_start_reservations_at_admission",
        "provider_max_wait_seconds_before",
        "provider_max_wait_seconds_at_admission",
        "observed_provider_max_wait_delta_seconds",
        "maximum_provider_wait_credit_seconds",
        "credited_provider_wait_seconds",
        "raw_wave1_elapsed_seconds",
        "base_wave1_ceiling_seconds",
        "effective_wave1_ceiling_seconds",
        "legacy_decision",
        "legacy_reason",
        "pacing_aware_decision",
        "pacing_aware_reason",
        "decision_changed",
        "absolute_task_deadline_changed",
        "cleanup_reserve_changed",
        "query_fetch_model_token_or_context_cap_changed",
        "search_pacing_cooldown_or_attempt_cap_changed",
        "raw_first_wave_elapsed_rewritten",
        "same_pass_content_free_transport_telemetry_only",
        "question_query_url_page_prediction_answer_or_credential_read_or_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "historical_correctness_429_or_latency_cohort_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


_ADMISSION_CONTEXT: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar("v24856_admission_context", default=None)
)


def _finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.48.56 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"V2.48.56 {label} is invalid")
    return number


def _rate_snapshot(search: Any) -> dict[str, Any]:
    method = getattr(search, "rate_aware_search_receipt", None)
    if not callable(method):
        raise TypeError("V2.48.56 requires a rate-aware search receipt")
    return validate_rate_receipt(method())


def _build_receipt(
    *,
    before: Mapping[str, Any],
    current: Mapping[str, Any],
    observation: FirstWaveObservation,
    base_policy: TwoWavePolicy,
    effective_policy: TwoWavePolicy,
    legacy: Mapping[str, Any],
    pacing: Mapping[str, Any],
) -> dict[str, Any]:
    before_max = float(before["max_provider_gate_wait_seconds"])
    current_max = float(current["max_provider_gate_wait_seconds"])
    observed = max(0.0, current_max - before_max)
    credited = min(observed, MAX_PROVIDER_WAIT_CREDIT_SECONDS)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "base_controller_policy_id": str(legacy["policy_id"]),
        "provider_wait_metric": "same_task_max_provider_gate_wait_delta",
        "provider_start_reservations_before": int(
            before["provider_start_reservations"]
        ),
        "provider_start_reservations_at_admission": int(
            current["provider_start_reservations"]
        ),
        "provider_max_wait_seconds_before": before_max,
        "provider_max_wait_seconds_at_admission": current_max,
        "observed_provider_max_wait_delta_seconds": round(observed, 6),
        "maximum_provider_wait_credit_seconds": (
            MAX_PROVIDER_WAIT_CREDIT_SECONDS
        ),
        "credited_provider_wait_seconds": round(credited, 6),
        "raw_wave1_elapsed_seconds": round(
            float(observation.search_seconds) + float(observation.fetch_seconds),
            6,
        ),
        "base_wave1_ceiling_seconds": float(
            base_policy.maximum_wave1_seconds
        ),
        "effective_wave1_ceiling_seconds": float(
            effective_policy.maximum_wave1_seconds
        ),
        "legacy_decision": str(legacy["decision"]),
        "legacy_reason": str(legacy["reason"]),
        "pacing_aware_decision": str(pacing["decision"]),
        "pacing_aware_reason": str(pacing["reason"]),
        "decision_changed": (
            legacy["decision"] != pacing["decision"]
            or legacy["reason"] != pacing["reason"]
        ),
        "absolute_task_deadline_changed": False,
        "cleanup_reserve_changed": False,
        "query_fetch_model_token_or_context_cap_changed": False,
        "search_pacing_cooldown_or_attempt_cap_changed": False,
        "raw_first_wave_elapsed_rewritten": False,
        "same_pass_content_free_transport_telemetry_only": True,
        "question_query_url_page_prediction_answer_or_credential_read_or_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "historical_correctness_429_or_latency_cohort_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = object_sha256(value)
    return validate_receipt(value)


def _pacing_decide_two_wave(
    observation: FirstWaveObservation,
    *,
    policy: TwoWavePolicy | None = None,
) -> dict[str, Any]:
    context = _ADMISSION_CONTEXT.get()
    if context is None:
        raise RuntimeError("V2.48.56 admission context is absent")
    chosen = policy or TwoWavePolicy()
    chosen.validate()
    current = _rate_snapshot(context["search"])
    before = context["before"]
    observed = max(
        0.0,
        float(current["max_provider_gate_wait_seconds"])
        - float(before["max_provider_gate_wait_seconds"]),
    )
    credited = min(observed, MAX_PROVIDER_WAIT_CREDIT_SECONDS)
    effective = dataclasses.replace(
        chosen,
        maximum_wave1_seconds=(
            float(chosen.maximum_wave1_seconds) + credited
        ),
    )
    legacy = legacy_decide_two_wave(observation, policy=chosen)
    pacing = legacy_decide_two_wave(observation, policy=effective)
    context["receipt"] = _build_receipt(
        before=before,
        current=current,
        observation=observation,
        base_policy=chosen,
        effective_policy=effective,
        legacy=legacy,
        pacing=pacing,
    )
    return pacing


def _isolated_parent_runner() -> Any:
    original = parent_retrieval.run_two_wave_retrieval
    if original.__closure__:
        raise RuntimeError("V2.48.56 parent retrieval unexpectedly has closure state")
    namespace = dict(original.__globals__)
    namespace["decide_two_wave"] = _pacing_decide_two_wave
    return types.FunctionType(
        original.__code__,
        namespace,
        name="v24856_isolated_run_two_wave_retrieval",
        argdefs=original.__defaults__,
        closure=None,
    )


_RUN_PARENT_ISOLATED = _isolated_parent_runner()


def run_pacing_aware_two_wave_retrieval(
    queries: Sequence[str],
    *,
    search: Any,
    required_column_count: int,
    explicit_row_target: int = 0,
    search_results_per_query: int = 3,
    policy: TwoWavePolicy | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    """Run the frozen retrieval with isolated pacing-aware admission only."""

    before = _rate_snapshot(search)
    context: dict[str, Any] = {
        "search": search,
        "before": before,
        "receipt": None,
    }
    token = _ADMISSION_CONTEXT.set(context)
    try:
        kwargs: dict[str, Any] = {
            "search": search,
            "required_column_count": required_column_count,
            "explicit_row_target": explicit_row_target,
            "search_results_per_query": search_results_per_query,
            "policy": policy,
        }
        if monotonic is not None:
            kwargs["monotonic"] = monotonic
        value = _RUN_PARENT_ISOLATED(list(queries), **kwargs)
    finally:
        _ADMISSION_CONTEXT.reset(token)
    receipt = context.get("receipt")
    if not isinstance(receipt, Mapping):
        raise RuntimeError("V2.48.56 pacing receipt was not produced")
    output = dict(value)
    output["pacing_admission_receipt"] = validate_receipt(receipt)
    return output


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    numeric = (
        "provider_max_wait_seconds_before",
        "provider_max_wait_seconds_at_admission",
        "observed_provider_max_wait_delta_seconds",
        "maximum_provider_wait_credit_seconds",
        "credited_provider_wait_seconds",
        "raw_wave1_elapsed_seconds",
        "base_wave1_ceiling_seconds",
        "effective_wave1_ceiling_seconds",
    )
    integers = (
        "artifact_version",
        "provider_start_reservations_before",
        "provider_start_reservations_at_admission",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("provider_wait_metric")
        != "same_task_max_provider_gate_wait_delta"
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integers
        )
        or any(_finite_nonnegative(copied.get(name), name) < 0 for name in numeric)
        or copied.get("legacy_decision") not in DECISIONS
        or copied.get("pacing_aware_decision") not in DECISIONS
        or copied.get("legacy_reason") not in REASONS
        or copied.get("pacing_aware_reason") not in REASONS
        or not isinstance(copied.get("decision_changed"), bool)
        or copied.get("absolute_task_deadline_changed") is not False
        or copied.get("cleanup_reserve_changed") is not False
        or copied.get("query_fetch_model_token_or_context_cap_changed") is not False
        or copied.get("search_pacing_cooldown_or_attempt_cap_changed") is not False
        or copied.get("raw_first_wave_elapsed_rewritten") is not False
        or copied.get("same_pass_content_free_transport_telemetry_only") is not True
        or copied.get(
            "question_query_url_page_prediction_answer_or_credential_read_or_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("historical_correctness_429_or_latency_cohort_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != object_sha256(unsigned)
    ):
        raise ValueError("V2.48.56 pacing admission receipt drifted")
    before = float(copied["provider_max_wait_seconds_before"])
    current = float(copied["provider_max_wait_seconds_at_admission"])
    observed = float(copied["observed_provider_max_wait_delta_seconds"])
    cap = float(copied["maximum_provider_wait_credit_seconds"])
    credited = float(copied["credited_provider_wait_seconds"])
    base = float(copied["base_wave1_ceiling_seconds"])
    effective = float(copied["effective_wave1_ceiling_seconds"])
    if (
        copied["provider_start_reservations_at_admission"]
        < copied["provider_start_reservations_before"]
        or current < before
        or not math.isclose(observed, current - before, abs_tol=1e-6)
        or cap != MAX_PROVIDER_WAIT_CREDIT_SECONDS
        or not math.isclose(credited, min(observed, cap), abs_tol=1e-6)
        or not math.isclose(effective, base + credited, abs_tol=1e-6)
        or copied["decision_changed"]
        is not (
            copied["legacy_decision"] != copied["pacing_aware_decision"]
            or copied["legacy_reason"] != copied["pacing_aware_reason"]
        )
    ):
        raise ValueError("V2.48.56 pacing arithmetic drifted")
    return copied


def validate_isolation() -> None:
    if (
        parent_retrieval.run_two_wave_retrieval.__globals__["decide_two_wave"]
        is not legacy_decide_two_wave
        or _RUN_PARENT_ISOLATED.__globals__["decide_two_wave"]
        is not _pacing_decide_two_wave
        or _RUN_PARENT_ISOLATED.__code__
        is not parent_retrieval.run_two_wave_retrieval.__code__
    ):
        raise RuntimeError("V2.48.56 isolated parent binding drifted")


__all__ = [
    "MAX_PROVIDER_WAIT_CREDIT_SECONDS",
    "POLICY_ID",
    "ROLE",
    "run_pacing_aware_two_wave_retrieval",
    "validate_isolation",
    "validate_receipt",
]
