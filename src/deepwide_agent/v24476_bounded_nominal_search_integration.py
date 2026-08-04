"""Bounded adaptive integration for the V2.44.74 compatible search type.

This append-only layer supplies the exact search factory future bounded workers
must use.  It delegates construction to the frozen V2.44.74 compatibility
class and validates the nominal V2.43.91 and hard-total-wall V2.44.70 type
surfaces before returning the client.  The frozen V2.44.38 and V2.44.68--74
modules remain unchanged.

No benchmark selection, label, mapping, gold, evaluator, reward, score, or
credential is available here.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .v24391_uncertainty_active_evidence_runner import (
    UncertaintyDeadlineAwareNativeSearchClient,
)
from .v24470_bounded_adaptive_integration import (
    HardTotalWallUncertaintyNativeSearchClient,
)
from .v24474_nominal_hard_total_wall_search import (
    NominalCompatibleHardTotalWallUncertaintyNativeSearchClient,
    build_nominal_compatible_hard_total_wall_search,
    validate_compatibility_class,
)


POLICY_ID = "v24476_bounded_nominal_hard_search_integration_v1"


def build_bounded_nominal_hard_total_wall_search(
    *,
    url: str,
    model_name: str,
    reasoning_effort: str,
    service_tier: str,
    static_timeout_seconds: float,
    max_retries: int,
    absolute_deadline: float,
    cleanup_reserve_seconds: float,
    minimum_attempt_seconds: float,
    stage_callback: Callable[[str], None],
    max_workers: int = 1,
    batch_size: int = 8,
    search_context_size: str = "medium",
    max_output_tokens: int = 4_000,
    fetch_pages: bool = False,
    fetch_workers: int = 8,
    fetch_timeout: float = 20,
    max_page_chars: int = 5_000,
    hard_fetch_deadline_seconds: float = 25,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    popen: Any = None,
    helper: Path | None = None,
) -> NominalCompatibleHardTotalWallUncertaintyNativeSearchClient:
    """Build and fail-closed validate the future worker search transport."""

    validate_compatibility_class()
    client = build_nominal_compatible_hard_total_wall_search(
        url=url,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        service_tier=service_tier,
        static_timeout_seconds=static_timeout_seconds,
        max_retries=max_retries,
        absolute_deadline=absolute_deadline,
        cleanup_reserve_seconds=cleanup_reserve_seconds,
        minimum_attempt_seconds=minimum_attempt_seconds,
        stage_callback=stage_callback,
        max_workers=max_workers,
        batch_size=batch_size,
        search_context_size=search_context_size,
        max_output_tokens=max_output_tokens,
        fetch_pages=fetch_pages,
        fetch_workers=fetch_workers,
        fetch_timeout=fetch_timeout,
        max_page_chars=max_page_chars,
        hard_fetch_deadline_seconds=hard_fetch_deadline_seconds,
        monotonic=monotonic,
        sleeper=sleeper,
        popen=popen,
        helper=helper,
    )
    if (
        type(client)
        is not NominalCompatibleHardTotalWallUncertaintyNativeSearchClient
        or not isinstance(client, UncertaintyDeadlineAwareNativeSearchClient)
        or not isinstance(client, HardTotalWallUncertaintyNativeSearchClient)
        or client.absolute_deadline != float(absolute_deadline)
        or client.static_search_timeout_seconds != float(static_timeout_seconds)
        or client.multi_query_chunks != 0
        or client.recursive_split_requests != 0
        or client.hosted_search_attempts != 0
        or client.hard_fetch_helper_calls != 0
    ):
        raise RuntimeError("V2.44.76 bounded search construction drifted")
    return client


__all__ = [
    "POLICY_ID",
    "build_bounded_nominal_hard_total_wall_search",
]
