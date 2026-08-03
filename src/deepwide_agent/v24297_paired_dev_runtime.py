"""Total label-blind runtimes for the V2.42.97 fresh paired-dev64 gate.

Both arms share the same visible-schema model wrapper, total fallback boundary,
model/search budgets, and two-wave controller.  The only intended treatment is
the retrieval allocation after an ``expand`` decision:

* baseline: the frozen V2.42.86 ``6+4`` schedule;
* candidate: the V2.42.96 ``6+2+2`` staged-reserve schedule.

The public input is exactly ``{opaque_id, question}``.  No benchmark label,
mapping, gold answer, evaluator output, or prior score is accepted or read.
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
from .v24294_staged_reserve import StagedReservePolicy
from .v24296_staged_reserve_task_runtime import (
    run_v24296_task,
    validate_v24296_result,
)


POLICY_ID = "v24297_fresh_paired_dev64_total_runtime_v1"
ARMS = ("baseline", "candidate")
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


def _snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


def validate_v24297_result(value: Mapping[str, Any], arm: str) -> str:
    if arm not in ARMS:
        raise ValueError("V2.42.97 arm is invalid")
    validator = validate_v24286_result if arm == "baseline" else validate_v24296_result
    try:
        validator(value)
        return "candidate"
    except (KeyError, TypeError, ValueError):
        try:
            validate_v24259_result(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("V2.42.97 result is neither candidate nor fallback") from exc
        if value.get("completion_kind") not in {
            "worker_failure_fallback",
            "hard_deadline_fallback",
        }:
            raise ValueError("V2.42.97 non-candidate result is not a total fallback")
        return "fallback"


def run_v24297_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run one arm and convert every ordinary failure into a canonical table."""

    visible = validate_visible_task(task)
    if arm not in ARMS:
        raise ValueError("V2.42.97 arm is invalid")
    limits.validate()
    two_wave_policy.validate()
    if reserve_policy is not None:
        reserve_policy.validate()
    if arm == "candidate" and reserve_policy is None:
        raise ValueError("V2.42.97 candidate reserve policy is absent")
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
        if arm == "baseline":
            result = run_v24286_task(
                visible,
                model=model,
                search=search,
                limits=limits,
                policy=two_wave_policy,
                monotonic=monotonic,
                progress=capture,
            )
        else:
            result = run_v24296_task(
                visible,
                model=model,
                search=search,
                limits=limits,
                two_wave_policy=two_wave_policy,
                reserve_policy=reserve_policy,
                monotonic=monotonic,
                progress=capture,
            )
        validate_v24297_result(result, arm)
        return result
    except BaseException as exc:
        current = dict(last_progress)
        current["model_cost"] = _counter_delta(
            _snapshot(model, MODEL_COUNTERS), model_start
        )
        current["search_cost"] = _counter_delta(
            _snapshot(search, SEARCH_COUNTERS), search_start
        )
        try:
            elapsed = max(0.0, float(monotonic()) - started)
        except BaseException:
            elapsed = 0.0
        result = build_total_fallback_result(
            visible,
            limits=limits,
            completion_kind="worker_failure_fallback",
            failure_stage=f"v24297_{arm}_runtime_totality",
            failure_type=type(exc).__name__,
            elapsed_seconds=elapsed,
            last_progress=current,
        )
        validate_v24297_result(result, arm)
        return result


__all__ = [
    "ARMS",
    "POLICY_ID",
    "run_v24297_task",
    "validate_v24297_result",
]
