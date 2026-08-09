"""Compose the frozen rate-aware search and multi-identity fetch seams.

Python's C3 linearization places V2.50.16's hard-deadline fetch mixin before
V2.48.52's direct-search client, while the direct-search implementation remains
owned by V2.48.52.  Consequently the composed client preserves the provider
rate gate, key-local failure policy, logical attempt cap, task deadline, fetch
process/byte/deadline cap, page-character cap, and content-free receipts.

Only the already-audited V2.50.16 helper identity differs from V2.48.57.  The
helper consumes the current visible question in memory and returns the exact
parent 5k prefix unless the strict multi-identity detail projection admits an
atomic record.  No benchmark label, gold, evaluator, score, or historical
outcome is accepted.
"""

from __future__ import annotations

from .v24852_rate_aware_tavily_search import (
    RateAwareDeadlineTavilyThinCompatibilityClient,
    validate_search_class as validate_rate_search_class,
)
from .v24981_late_page_bound_fetch import LatePageBoundFetchMixin
from .v25016_multi_identity_detail_fetch import (
    MultiIdentityDetailSearchClient,
    validate_search_class as validate_multi_identity_search_class,
)


POLICY_ID = "v25021_rate_aware_multi_identity_detail_search_v1"


class RateAwareMultiIdentityDetailSearchClient(
    MultiIdentityDetailSearchClient,
    RateAwareDeadlineTavilyThinCompatibilityClient,
):
    """One client with the frozen rate/search and detail/fetch boundaries."""


def validate_search_class() -> None:
    validate_rate_search_class()
    validate_multi_identity_search_class()
    cls = RateAwareMultiIdentityDetailSearchClient
    fetch_owner = next(base for base in cls.__mro__ if "_fetch_url" in base.__dict__)
    search_owner = next(
        base for base in cls.__mro__ if "_direct_search" in base.__dict__
    )
    if (
        fetch_owner is not LatePageBoundFetchMixin
        or search_owner is not RateAwareDeadlineTavilyThinCompatibilityClient
        or not issubclass(cls, MultiIdentityDetailSearchClient)
        or not issubclass(cls, RateAwareDeadlineTavilyThinCompatibilityClient)
    ):
        raise RuntimeError("V2.50.21 composed search MRO drifted")


__all__ = [
    "POLICY_ID",
    "RateAwareMultiIdentityDetailSearchClient",
    "validate_search_class",
]
