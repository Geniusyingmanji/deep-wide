"""Separate remote-effect and local-validation budgets for V2.44.80.

V2.44.78 used a 150-second remote-effect deadline inside a 175-second worker
deadline.  Its public stage chain showed every recorded network effect ending,
but all workers then reached the worker cutoff.  The local synthetic full-chain
control takes about 26.6 seconds without profiling, so the inherited 25-second
local reserve was not evidence-backed.

This append-only policy keeps the remote-effect deadline exactly 150 seconds
and gives local validation, artifact persistence, and certificate publication
an independent 70-second reserve.  A final 25-second parent reserve remains
outside the worker process group.  The policy only constructs and validates
monotonic deadlines; it performs no model, search, fetch, benchmark, evaluator,
filesystem, environment, or process action.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


POLICY_ID = "v24480_separated_remote_effect_local_validation_budget_v1"
REMOTE_EFFECT_SECONDS = 150.0
LOCAL_VALIDATION_RESERVE_SECONDS = 70.0
WORKER_TOTAL_SECONDS = REMOTE_EFFECT_SECONDS + LOCAL_VALIDATION_RESERVE_SECONDS
PARENT_CLOSURE_RESERVE_SECONDS = 25.0
PARENT_TOTAL_SECONDS = WORKER_TOTAL_SECONDS + PARENT_CLOSURE_RESERVE_SECONDS
BATCH_FINALIZATION_RESERVE_SECONDS = 10.0
BATCH_WALL_CEILING_SECONDS = PARENT_TOTAL_SECONDS + BATCH_FINALIZATION_RESERVE_SECONDS
MINIMUM_LOCAL_VALIDATION_RESERVE_SECONDS = 60.0
MINIMUM_PARENT_CLOSURE_RESERVE_SECONDS = 20.0
UNPROFILED_SYNTHETIC_FULL_CHAIN_SECONDS = 26.628652


def _finite(value: object, *, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"V2.44.80 {label} is not finite")
    return float(value)


@dataclass(frozen=True)
class PhaseDeadlines:
    """Absolute monotonic deadlines derived from one trusted origin."""

    origin: float
    remote_effect: float
    worker: float
    parent: float


def build_phase_deadlines(
    *,
    origin: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> PhaseDeadlines:
    start = monotonic() if origin is None else _finite(origin, label="origin")
    value = PhaseDeadlines(
        origin=start,
        remote_effect=start + REMOTE_EFFECT_SECONDS,
        worker=start + WORKER_TOTAL_SECONDS,
        parent=start + PARENT_TOTAL_SECONDS,
    )
    return validate_phase_deadlines(value)


def validate_phase_deadlines(value: PhaseDeadlines) -> PhaseDeadlines:
    if not isinstance(value, PhaseDeadlines):
        raise TypeError("V2.44.80 requires phase deadlines")
    origin = _finite(value.origin, label="origin")
    effect = _finite(value.remote_effect, label="remote effect deadline")
    worker = _finite(value.worker, label="worker deadline")
    parent = _finite(value.parent, label="parent deadline")
    if (
        effect != origin + REMOTE_EFFECT_SECONDS
        or worker != origin + WORKER_TOTAL_SECONDS
        or parent != origin + PARENT_TOTAL_SECONDS
        or not origin < effect < worker < parent
        or worker - effect != LOCAL_VALIDATION_RESERVE_SECONDS
        or parent - worker != PARENT_CLOSURE_RESERVE_SECONDS
        or LOCAL_VALIDATION_RESERVE_SECONDS
        < MINIMUM_LOCAL_VALIDATION_RESERVE_SECONDS
        or PARENT_CLOSURE_RESERVE_SECONDS
        < MINIMUM_PARENT_CLOSURE_RESERVE_SECONDS
    ):
        raise ValueError("V2.44.80 phase deadline contract drifted")
    return value


def remaining_remote_effect_seconds(
    deadlines: PhaseDeadlines,
    *,
    monotonic: Callable[[], float] = time.monotonic,
) -> float:
    """Return the remote-effect window and fail closed after it expires."""

    current = _finite(monotonic(), label="current monotonic time")
    value = validate_phase_deadlines(deadlines).remote_effect - current
    if not 0 < value <= REMOTE_EFFECT_SECONDS:
        raise RuntimeError("V2.44.80 remote-effect deadline is unavailable")
    return value


def remaining_worker_seconds(
    deadlines: PhaseDeadlines,
    *,
    monotonic: Callable[[], float] = time.monotonic,
) -> float:
    """Return the bounded worker window, including local validation reserve."""

    current = _finite(monotonic(), label="current monotonic time")
    value = validate_phase_deadlines(deadlines).worker - current
    if value > WORKER_TOTAL_SECONDS:
        raise RuntimeError("V2.44.80 inherited worker deadline is invalid")
    return max(1e-6, value)


def remaining_parent_seconds(
    deadlines: PhaseDeadlines,
    *,
    monotonic: Callable[[], float] = time.monotonic,
) -> float:
    current = _finite(monotonic(), label="current monotonic time")
    value = validate_phase_deadlines(deadlines).parent - current
    if value > PARENT_TOTAL_SECONDS:
        raise RuntimeError("V2.44.80 inherited parent deadline is invalid")
    return max(1e-6, value)


def budget_contract() -> dict[str, Any]:
    value = {
        "policy_id": POLICY_ID,
        "remote_effect_seconds": REMOTE_EFFECT_SECONDS,
        "local_validation_reserve_seconds": LOCAL_VALIDATION_RESERVE_SECONDS,
        "worker_total_seconds": WORKER_TOTAL_SECONDS,
        "parent_closure_reserve_seconds": PARENT_CLOSURE_RESERVE_SECONDS,
        "parent_total_seconds": PARENT_TOTAL_SECONDS,
        "batch_finalization_reserve_seconds": BATCH_FINALIZATION_RESERVE_SECONDS,
        "batch_wall_ceiling_seconds": BATCH_WALL_CEILING_SECONDS,
        "unprofiled_synthetic_full_chain_seconds": (
            UNPROFILED_SYNTHETIC_FULL_CHAIN_SECONDS
        ),
        "remote_effect_budget_unchanged_from_v24478": True,
        "local_validation_budget_is_not_available_to_remote_effect_clients": True,
        "all_deadlines_derive_from_one_monotonic_origin": True,
        "profiled_timing_used_as_external_latency_estimate": False,
        "same_v24478_population_rerun_allowed": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    validate_budget_contract(value)
    return value


def validate_budget_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    expected = {
        "policy_id": POLICY_ID,
        "remote_effect_seconds": REMOTE_EFFECT_SECONDS,
        "local_validation_reserve_seconds": LOCAL_VALIDATION_RESERVE_SECONDS,
        "worker_total_seconds": WORKER_TOTAL_SECONDS,
        "parent_closure_reserve_seconds": PARENT_CLOSURE_RESERVE_SECONDS,
        "parent_total_seconds": PARENT_TOTAL_SECONDS,
        "batch_finalization_reserve_seconds": BATCH_FINALIZATION_RESERVE_SECONDS,
        "batch_wall_ceiling_seconds": BATCH_WALL_CEILING_SECONDS,
        "unprofiled_synthetic_full_chain_seconds": (
            UNPROFILED_SYNTHETIC_FULL_CHAIN_SECONDS
        ),
        "remote_effect_budget_unchanged_from_v24478": True,
        "local_validation_budget_is_not_available_to_remote_effect_clients": True,
        "all_deadlines_derive_from_one_monotonic_origin": True,
        "profiled_timing_used_as_external_latency_estimate": False,
        "same_v24478_population_rerun_allowed": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    if copied != expected:
        raise ValueError("V2.44.80 budget contract drifted")
    return copied


__all__ = [
    "BATCH_WALL_CEILING_SECONDS",
    "LOCAL_VALIDATION_RESERVE_SECONDS",
    "PARENT_CLOSURE_RESERVE_SECONDS",
    "PARENT_TOTAL_SECONDS",
    "POLICY_ID",
    "PhaseDeadlines",
    "REMOTE_EFFECT_SECONDS",
    "WORKER_TOTAL_SECONDS",
    "budget_contract",
    "build_phase_deadlines",
    "remaining_parent_seconds",
    "remaining_remote_effect_seconds",
    "remaining_worker_seconds",
    "validate_budget_contract",
    "validate_phase_deadlines",
]
