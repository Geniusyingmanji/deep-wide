"""Bounded construction for the V2.46.27 citation-title backfill client.

The factory is the sole construction surface used by the V2.46.29 worker.  It
keeps V2.44.68's process-enforced total-wall request path, V2.43.16's shared
task deadline, V2.42.80's one-request task-union parsing, and V2.46.27's
same-response-only title backfill in one fail-closed type boundary.

No benchmark metadata, evaluator resource, credential, or historical outcome
is available to this module.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .v24316_deadline_search import DeadlineAwareNativeSearchClient
from .v24468_total_wall_transport import HardTotalWallNativeSearchClient
from .v24470_bounded_adaptive_integration import (
    HardTotalWallUncertaintyNativeSearchClient,
)
from .v24627_same_response_citation_title_backfill import (
    SameResponseCitationTitleBackfillMixin,
    SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient,
    validate_compatibility_successor,
)


POLICY_ID = "v24628_bounded_same_response_title_backfill_search_v1"


def build_bounded_same_response_title_backfill_search(
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
    stage_callback: Callable[[str], None] | None = None,
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
) -> SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient:
    """Construct and validate the exact bounded search successor."""

    validate_compatibility_successor()
    optional: dict[str, Any] = {}
    if popen is not None:
        optional["popen"] = popen
    if helper is not None:
        optional["helper"] = helper
    client = SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient(
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
        stage_callback=stage_callback or (lambda _stage: None),
        **optional,
    )
    cls = SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient
    request_owner = next(base for base in cls.__mro__ if "_request" in base.__dict__)
    chunk_owner = next(base for base in cls.__mro__ if "_run_chunk" in base.__dict__)
    if (
        type(client) is not cls
        or not isinstance(client, DeadlineAwareNativeSearchClient)
        or not isinstance(client, HardTotalWallUncertaintyNativeSearchClient)
        or request_owner is not HardTotalWallNativeSearchClient
        or chunk_owner is not SameResponseCitationTitleBackfillMixin
        or client.absolute_deadline != float(absolute_deadline)
        or client.multi_query_chunks != 0
        or client.recursive_split_requests != 0
        or client.hosted_search_attempts != 0
        or client.hard_fetch_helper_calls != 0
        or client.citation_title_backfill_receipt()["multi_query_payload_count"] != 0
    ):
        raise RuntimeError("V2.46.28 bounded backfill-search construction drifted")
    return client


__all__ = [
    "POLICY_ID",
    "build_bounded_same_response_title_backfill_search",
]
