"""Forty-second hard-fetch transport for the V2.46.94 World Bank gate.

The frozen V2.42.87 base constructor pins its historical 25-second fetch
wall.  This append-only specialization keeps that implementation but raises
the instance wall to the preregistered 40 seconds after validating the new
fixed contract.  It has no task, benchmark, evaluator, or scoring capability.
"""

from __future__ import annotations

from typing import Any

from .v24287_forward_contract import SEARCH as LEGACY_SEARCH
from .v24468_total_wall_transport import HardTotalWallNativeSearchClient


POLICY_ID = "v24696_worldbank_40s_hard_fetch_transport_v1"
HARD_FETCH_DEADLINE_SECONDS = 40.0


class WorldBankHardTotalWallSearchClient(HardTotalWallNativeSearchClient):
    """Use the existing hard helper with the fixed World Bank fetch wall."""

    def __init__(self, *args: Any, hard_fetch_deadline_seconds: float, **kwargs: Any) -> None:
        requested = float(hard_fetch_deadline_seconds)
        if requested != HARD_FETCH_DEADLINE_SECONDS:
            raise ValueError("V2.46.96 World Bank hard fetch deadline drifted")
        super().__init__(
            *args,
            hard_fetch_deadline_seconds=float(
                LEGACY_SEARCH["hard_fetch_deadline_seconds"]
            ),
            **kwargs,
        )
        self.hard_fetch_deadline_seconds = requested


def validate_transport(client: object) -> None:
    if (
        not isinstance(client, WorldBankHardTotalWallSearchClient)
        or client.hard_fetch_deadline_seconds != HARD_FETCH_DEADLINE_SECONDS
        or client.fetch_timeout < 35.0
    ):
        raise ValueError("V2.46.96 World Bank search transport drifted")


__all__ = [
    "HARD_FETCH_DEADLINE_SECONDS",
    "POLICY_ID",
    "WorldBankHardTotalWallSearchClient",
    "validate_transport",
]
