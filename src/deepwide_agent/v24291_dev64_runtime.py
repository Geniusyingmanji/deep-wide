"""Total label-blind V2.42.90 runtime for the V2.42.91 dev64 gate."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, _counter_delta, _counter_snapshot, validate_visible_task
from .v24259_deterministic_table_normalizer import validate_v24259_result
from .v24267_total_fallback import build_total_fallback_result
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24289_low_coverage_rescue import RescuePolicy
from .v24290_low_coverage_task_runtime import run_v24290_task, validate_v24290_result


POLICY_ID = "v24291_total_low_coverage_rescue_dev64_v1"
MODEL_COUNTERS = ("requests", "attempts", "input_tokens", "output_tokens", "total_tokens")
SEARCH_COUNTERS = (
    "calls", "failures", "tool_calls", "fetch_calls", "fetch_failures",
    "input_tokens", "output_tokens", "total_tokens",
)


def _snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


def validate_v24291_result(value: Mapping[str, Any]) -> str:
    try:
        validate_v24290_result(value)
        return "candidate"
    except (KeyError, TypeError, ValueError):
        try:
            validate_v24259_result(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("V2.42.91 result is neither candidate nor fallback") from exc
        if value.get("completion_kind") not in {"worker_failure_fallback", "hard_deadline_fallback"}:
            raise ValueError("V2.42.91 non-candidate result is not a total fallback")
        return "fallback"


def run_v24291_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    rescue_policy: RescuePolicy,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    limits.validate()
    two_wave_policy.validate()
    rescue_policy.validate()
    try:
        started = float(monotonic())
    except BaseException:
        started = 0.0
    model_start = _snapshot(model, MODEL_COUNTERS)
    search_start = _snapshot(search, SEARCH_COUNTERS)
    last_progress: dict[str, Any] = {}

    def capture(value: Mapping[str, Any]) -> None:
        nonlocal last_progress
        last_progress = dict(value)
        if progress is not None:
            progress(value)

    try:
        result = run_v24290_task(
            visible,
            model=model,
            search=search,
            limits=limits,
            two_wave_policy=two_wave_policy,
            rescue_policy=rescue_policy,
            monotonic=monotonic,
            progress=capture,
        )
        validate_v24290_result(result)
        return result
    except BaseException as exc:
        current = dict(last_progress)
        current["model_cost"] = _counter_delta(_snapshot(model, MODEL_COUNTERS), model_start)
        current["search_cost"] = _counter_delta(_snapshot(search, SEARCH_COUNTERS), search_start)
        try:
            elapsed = max(0.0, float(monotonic()) - started)
        except BaseException:
            elapsed = 0.0
        result = build_total_fallback_result(
            visible,
            limits=limits,
            completion_kind="worker_failure_fallback",
            failure_stage="v24291_runtime_totality",
            failure_type=type(exc).__name__,
            elapsed_seconds=elapsed,
            last_progress=current,
        )
        validate_v24291_result(result)
        return result


__all__ = ["POLICY_ID", "run_v24291_task", "validate_v24291_result"]
