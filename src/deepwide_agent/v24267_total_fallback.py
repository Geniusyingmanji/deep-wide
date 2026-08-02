"""Total, label-blind fallback boundary for the V2.42.59 candidate.

The frozen V2.42.57 fallback can become internally unrepresentable when a
visible column declaration contains Markdown pipe separators.  This successor
does not change planning, retrieval, synthesis, normalization, repair, or any
model-generated prediction.  It only guarantees that an exception path emits
one canonical, content-free single-column table whose accounting matches the
effects already attempted by the same forward pass.
"""

from __future__ import annotations

import re
import time
import math
from collections.abc import Callable, Mapping
from typing import Any

from .v24257_score_first_runtime import (
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import (
    build_v24259_fallback_result,
    run_v24259_task,
    validate_v24259_result,
)


POLICY_ID = "v24267_total_fallback_boundary_v1"
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
    """Keep the exception boundary total even for a malformed injected client."""

    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


def _elapsed_or_zero(monotonic: Callable[[], float], started: float) -> float:
    try:
        return max(0.0, float(monotonic()) - started)
    except BaseException:
        return 0.0


def _safe_visible_task(task: Mapping[str, Any]) -> dict[str, str]:
    visible = validate_visible_task(task)
    return {
        "opaque_id": visible["opaque_id"],
        "question": "Return a Markdown table. Column names: Result.",
    }


def _bounded_nonnegative(value: Any, maximum: int | None = None) -> int:
    try:
        converted = max(0, int(value or 0))
    except (TypeError, ValueError, OverflowError):
        return 0
    return min(converted, maximum) if maximum is not None else converted


def _safe_elapsed(value: Any) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return max(0.0, converted) if math.isfinite(converted) else 0.0


def _safe_progress(
    value: Mapping[str, Any] | None, limits: ScoreFirstLimits
) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    return {
        "admitted_model_calls": _bounded_nonnegative(
            raw.get("admitted_model_calls"), limits.model_calls
        ),
        "admitted_search_queries": _bounded_nonnegative(
            raw.get("admitted_search_queries"), limits.search_queries
        ),
        "admitted_fetch_targets": _bounded_nonnegative(
            raw.get("admitted_fetch_targets"), limits.fetch_targets
        ),
        "search_batch_count": _bounded_nonnegative(raw.get("search_batch_count")),
        "projected_chars": _bounded_nonnegative(raw.get("projected_chars")),
        "events": [],
        "model_cost": {
            name: _bounded_nonnegative((raw.get("model_cost") or {}).get(name))
            if isinstance(raw.get("model_cost"), Mapping)
            else 0
            for name in MODEL_COUNTERS
        },
        "search_cost": {
            name: _bounded_nonnegative((raw.get("search_cost") or {}).get(name))
            if isinstance(raw.get("search_cost"), Mapping)
            else 0
            for name in SEARCH_COUNTERS
        },
    }


def build_total_fallback_result(
    task: Mapping[str, Any],
    *,
    limits: ScoreFirstLimits,
    completion_kind: str,
    failure_stage: str,
    failure_type: str,
    elapsed_seconds: float,
    last_progress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical V2.42.59 fallback for every valid visible task."""

    validate_visible_task(task)
    result = build_v24259_fallback_result(
        _safe_visible_task(task),
        limits=limits,
        completion_kind=completion_kind,
        failure_stage=failure_stage,
        failure_type=failure_type,
        elapsed_seconds=_safe_elapsed(elapsed_seconds),
        last_progress=_safe_progress(last_progress, limits),
    )
    validate_v24259_result(result)
    return result


def run_total_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run V2.42.59 unchanged, totalizing only its exception boundary."""

    visible = validate_visible_task(task)
    policy = limits or ScoreFirstLimits()
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
        result = run_v24259_task(
            visible,
            model=model,
            search=search,
            limits=policy,
            monotonic=monotonic,
            progress=capture,
        )
        validate_v24259_result(result)
        return result
    except BaseException as exc:
        current = _safe_progress(last_progress, policy)
        current["model_cost"] = _counter_delta(
            _snapshot_or_zero(model, MODEL_COUNTERS), model_start
        )
        current["search_cost"] = _counter_delta(
            _snapshot_or_zero(search, SEARCH_COUNTERS), search_start
        )
        result = build_total_fallback_result(
            visible,
            limits=policy,
            completion_kind="worker_failure_fallback",
            failure_stage="v24267_runtime_totality",
            failure_type=type(exc).__name__,
            elapsed_seconds=_elapsed_or_zero(monotonic, started),
            last_progress=current,
        )
        validate_v24259_result(result)
        return result
