"""Append-only V2.43.13 child integration for deadline-aware paired runs.

This module deliberately contains no benchmark selection, evaluator, mapping,
gold, label, or score capability.  It creates a model transport whose slot
queue and provider attempts share the task's absolute deadline, then delegates
the visible-only task to the V2.43.12 outer-total runtime.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .clients import ResponsesClient
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24294_staged_reserve import StagedReservePolicy
from .v24310_paired_dev_runtime import ARMS, validate_v24310_result
from .v24312_deadline_reliability import (
    DEFAULT_CLEANUP_RESERVE_SECONDS,
    DEFAULT_MINIMUM_ATTEMPT_SECONDS,
    DeadlineAwareGlobalModelSlotLimiter,
    DeadlineAwareResponsesClient,
    run_v24312_total_task,
    validate_receipt,
)


POLICY_ID = "v24313_deadline_aware_common_recovery_runner_integration_v1"


def build_deadline_model(
    *,
    url: str,
    model_name: str,
    reasoning_effort: str,
    service_tier: str,
    static_timeout_seconds: float,
    max_retries: int,
    slot_directory: Path,
    output_root: Path,
    slot_cap: int,
    pool_id: str,
    absolute_deadline: float,
    cleanup_reserve_seconds: float = DEFAULT_CLEANUP_RESERVE_SECONDS,
    minimum_attempt_seconds: float = DEFAULT_MINIMUM_ATTEMPT_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    inner: Any | None = None,
) -> DeadlineAwareGlobalModelSlotLimiter:
    """Construct the one allowed model path for a future V2.43.13 child."""

    provider = inner
    if provider is None:
        provider = DeadlineAwareResponsesClient(
            url,
            model_name,
            reasoning_effort=reasoning_effort,
            service_tier=service_tier,
            timeout=static_timeout_seconds,
            max_retries=max_retries,
            absolute_deadline=absolute_deadline,
            cleanup_reserve_seconds=cleanup_reserve_seconds,
            minimum_attempt_seconds=minimum_attempt_seconds,
            monotonic=monotonic,
            sleeper=sleeper,
        )
    if isinstance(provider, ResponsesClient) and not isinstance(
        provider, DeadlineAwareResponsesClient
    ):
        raise ValueError("V2.43.13 rejects static-timeout ResponsesClient")
    value = DeadlineAwareGlobalModelSlotLimiter(
        provider,
        slot_directory=slot_directory,
        output_root=output_root,
        absolute_deadline=absolute_deadline,
        slot_cap=slot_cap,
        pool_id=pool_id,
        cleanup_reserve_seconds=cleanup_reserve_seconds,
        minimum_attempt_seconds=minimum_attempt_seconds,
        monotonic=monotonic,
        sleeper=sleeper,
    )
    return value


def run_v24313_task(
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
    visible = validate_visible_task(task)
    if arm not in ARMS:
        raise ValueError("V2.43.13 arm is invalid")
    result = run_v24312_total_task(
        visible,
        arm=arm,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
        reserve_policy=reserve_policy,
        monotonic=monotonic,
        progress=progress,
    )
    validate_v24310_result(result, arm)
    return result


def validate_deadline_model_receipt(
    value: Mapping[str, Any],
    *,
    expected_cap: int,
    expected_acquisitions: int | None = None,
) -> dict[str, Any]:
    return validate_receipt(
        value,
        expected_cap=expected_cap,
        expected_acquisitions=expected_acquisitions,
    )


__all__ = [
    "POLICY_ID",
    "build_deadline_model",
    "run_v24313_task",
    "validate_deadline_model_receipt",
]
