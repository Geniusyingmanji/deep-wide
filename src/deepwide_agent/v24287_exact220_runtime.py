"""Total label-blind runtime used by the V2.42.87 exact-220 rollout.

The normal path is exactly V2.42.86 (two-wave keyless retrieval, robust
visible-schema handling, and additive stage timing).  This module adds only a
total exception boundary so every valid visible task produces one prediction
for the fixed benchmark denominator.  It never reads benchmark labels, gold,
mapping, evaluator data, scores, or prior per-task outcomes.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

from .v24257_score_first_runtime import (
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import validate_v24259_result
from .v24267_total_fallback import build_total_fallback_result
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24286_visible_schema_runtime import run_v24286_task, validate_v24286_result


POLICY_ID = "v24287_exact220_total_visible_schema_two_wave_v1"
MODEL_COUNTERS = ("requests", "attempts", "input_tokens", "output_tokens", "total_tokens")
SEARCH_COUNTERS = (
    "calls",
    "failures",
    "tool_calls",
    "fetch_calls",
    "fetch_failures",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)


def _snapshot_or_zero(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


def _elapsed(monotonic: Callable[[], float], started: float) -> float:
    try:
        return max(0.0, float(monotonic()) - started)
    except BaseException:
        return 0.0


def _safe_progress(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def validate_v24287_result(value: Mapping[str, Any]) -> str:
    """Validate either the candidate result or its canonical total fallback."""

    try:
        validate_v24286_result(value)
        return "candidate"
    except (KeyError, TypeError, ValueError):
        try:
            validate_v24259_result(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("V2.42.87 result is neither candidate nor fallback") from exc
        kind = str(value.get("completion_kind", ""))
        if kind not in {"worker_failure_fallback", "hard_deadline_fallback"}:
            raise ValueError("V2.42.87 non-candidate result is not a total fallback")
        return "fallback"


def run_v24287_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    policy: TwoWavePolicy,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run V2.42.86 and totalize only failures escaping that frozen runtime."""

    visible = validate_visible_task(task)
    limits.validate()
    policy.validate()
    try:
        started = float(monotonic())
    except BaseException:
        started = 0.0
    model_start = _snapshot_or_zero(model, MODEL_COUNTERS)
    search_start = _snapshot_or_zero(search, SEARCH_COUNTERS)
    last_progress: dict[str, Any] = {}

    def capture(value: Mapping[str, Any]) -> None:
        nonlocal last_progress
        last_progress = dict(value)
        if progress is not None:
            progress(value)

    try:
        result = run_v24286_task(
            visible,
            model=model,
            search=search,
            limits=limits,
            policy=policy,
            monotonic=monotonic,
            progress=capture,
        )
        validate_v24286_result(result)
        return result
    except BaseException as exc:
        current = _safe_progress(last_progress)
        current["model_cost"] = _counter_delta(
            _snapshot_or_zero(model, MODEL_COUNTERS), model_start
        )
        current["search_cost"] = _counter_delta(
            _snapshot_or_zero(search, SEARCH_COUNTERS), search_start
        )
        result = build_total_fallback_result(
            visible,
            limits=limits,
            completion_kind="worker_failure_fallback",
            failure_stage="v24287_runtime_totality",
            failure_type=type(exc).__name__,
            elapsed_seconds=_elapsed(monotonic, started),
            last_progress=current,
        )
        validate_v24287_result(result)
        return result


__all__ = [
    "POLICY_ID",
    "run_v24287_task",
    "validate_v24287_result",
]
