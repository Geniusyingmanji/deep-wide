"""Nominally compatible hard-total-wall task-union search transport.

V2.44.72 exposed a type-boundary mismatch: the append-only V2.44.70 hard
transport implemented the required task-union behaviour, but the frozen
V2.44.38 timeout contract accepts only a nominal instance of V2.43.91's
``UncertaintyDeadlineAwareNativeSearchClient``.  This module leaves both
frozen parents unchanged and supplies a compatibility class whose method
resolution order keeps V2.44.68's hard-total-wall request implementation
ahead of the legacy nominal base.

The class changes no request, retry, fetch, task-union, receipt, or deadline
semantics.  It contains no benchmark selection, label, mapping, gold,
evaluator, reward, score, or credential capability.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .v24391_uncertainty_active_evidence_runner import (
    UncertaintyDeadlineAwareNativeSearchClient,
)
from .v24468_total_wall_transport import HardTotalWallNativeSearchClient
from .v24470_bounded_adaptive_integration import (
    HardTotalWallUncertaintyNativeSearchClient,
)


POLICY_ID = "v24474_nominally_compatible_hard_total_wall_search_v1"


class NominalCompatibleHardTotalWallUncertaintyNativeSearchClient(
    HardTotalWallUncertaintyNativeSearchClient,
    UncertaintyDeadlineAwareNativeSearchClient,
):
    """Hard task-union transport satisfying the frozen legacy nominal check."""


def validate_compatibility_class() -> None:
    cls = NominalCompatibleHardTotalWallUncertaintyNativeSearchClient
    mro = cls.__mro__
    request_owner = next(base for base in mro if "_request" in base.__dict__)
    run_chunk_owner = next(base for base in mro if "_run_chunk" in base.__dict__)
    if (
        not issubclass(cls, HardTotalWallUncertaintyNativeSearchClient)
        or not issubclass(cls, UncertaintyDeadlineAwareNativeSearchClient)
        or request_owner is not HardTotalWallNativeSearchClient
        or run_chunk_owner.__name__ != "TaskUnionSingleShotMixin"
        or mro.index(HardTotalWallUncertaintyNativeSearchClient)
        > mro.index(UncertaintyDeadlineAwareNativeSearchClient)
        or mro.index(UncertaintyDeadlineAwareNativeSearchClient)
        > mro.index(HardTotalWallNativeSearchClient)
    ):
        raise RuntimeError("V2.44.74 compatibility MRO drifted")


def build_nominal_compatible_hard_total_wall_search(
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
    """Build the compatibility client without changing frozen semantics."""

    validate_compatibility_class()
    optional: dict[str, Any] = {}
    if popen is not None:
        optional["popen"] = popen
    if helper is not None:
        optional["helper"] = helper
    client = NominalCompatibleHardTotalWallUncertaintyNativeSearchClient(
        url,
        model_name,
        reasoning_effort=reasoning_effort,
        service_tier=service_tier,
        timeout=static_timeout_seconds,
        max_retries=max_retries,
        max_workers=max_workers,
        batch_size=batch_size,
        search_context_size=search_context_size,
        max_output_tokens=max_output_tokens,
        fetch_pages=fetch_pages,
        fetch_workers=fetch_workers,
        fetch_timeout=fetch_timeout,
        max_page_chars=max_page_chars,
        hard_fetch_deadline_seconds=hard_fetch_deadline_seconds,
        absolute_deadline=absolute_deadline,
        cleanup_reserve_seconds=cleanup_reserve_seconds,
        minimum_attempt_seconds=minimum_attempt_seconds,
        monotonic=monotonic,
        sleeper=sleeper,
        stage_callback=stage_callback,
        **optional,
    )
    if (
        type(client)
        is not NominalCompatibleHardTotalWallUncertaintyNativeSearchClient
        or not isinstance(client, HardTotalWallUncertaintyNativeSearchClient)
        or not isinstance(client, UncertaintyDeadlineAwareNativeSearchClient)
        or client.absolute_deadline != float(absolute_deadline)
    ):
        raise RuntimeError("V2.44.74 compatibility client construction drifted")
    return client


__all__ = [
    "NominalCompatibleHardTotalWallUncertaintyNativeSearchClient",
    "POLICY_ID",
    "build_nominal_compatible_hard_total_wall_search",
    "validate_compatibility_class",
]
