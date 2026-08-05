#!/usr/bin/env python3
"""Instance-local immutable collector for the V2.46.00 total projector.

The V2.45.94 collector freezes V2.45.91 and therefore cannot carry the
stronger V2.45.99 title-funnel capability through V2.46.00.  This append-only
sibling freezes the V2.46.00 unbound projector at module load and stores it on
no shared runtime global.  It changes no task, model, search, fetch, ranking,
validator, evidence, credit, budget, or evaluator behavior.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from deepwide_agent import v24599_proof_carrying_title_funnel as proof
from deepwide_agent import v24600_total_title_funnel_projection as total


POLICY_ID = "v24602_instance_local_immutable_title_funnel_collector_v1"
FROZEN_TASK_PROJECTION = total.task_projection
_COLLECTOR_GUARD = threading.Lock()
_ACTIVE_COLLECTOR: _CapabilityCollector | None = None


def binding_valid() -> bool:
    return (
        callable(FROZEN_TASK_PROJECTION)
        and getattr(FROZEN_TASK_PROJECTION, "__self__", None) is None
        and FROZEN_TASK_PROJECTION is total.task_projection
    )


class _CapabilityCollector:
    """One-shot bridge using an immutable V2.46.00 projector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._capabilities: dict[
            int, proof.ValidatedProofCarryingContentFreeTitleFunnel
        ] = {}
        self._rows: dict[int, dict[str, Any]] = {}
        self._consumed = False

    def project(
        self,
        ordinal: int,
        capability: proof.ValidatedProofCarryingContentFreeTitleFunnel,
    ) -> dict[str, Any]:
        row = FROZEN_TASK_PROJECTION(ordinal, capability)
        with self._lock:
            if self._consumed or ordinal in self._capabilities:
                raise RuntimeError("V2.46.02 duplicate or late capability")
            self._capabilities[ordinal] = capability
            self._rows[ordinal] = copy.deepcopy(row)
        return row

    def aggregate(
        self, values: Sequence[Mapping[str, Any]], *, selected: int
    ) -> dict[str, Any]:
        if len(values) != selected:
            raise ValueError("V2.46.02 aggregate selection drifted")
        with self._lock:
            if self._consumed:
                raise RuntimeError("V2.46.02 capabilities already consumed")
            capabilities = dict(self._capabilities)
            rows = copy.deepcopy(self._rows)
            self._consumed = True
            self._capabilities.clear()
            self._rows.clear()
        proof_inputs: list[Any] = []
        for ordinal, raw in enumerate(values, start=1):
            row = total.validate_total_row(raw)
            capability = capabilities.pop(ordinal, None)
            captured = rows.pop(ordinal, None)
            if row["status"] == "validated_capability":
                if capability is None or captured != row:
                    raise RuntimeError("V2.46.02 success lacks captured capability")
                if FROZEN_TASK_PROJECTION(ordinal, capability) != row:
                    raise RuntimeError("V2.46.02 capability/public row mismatch")
                proof_inputs.append(capability)
            else:
                if capability is not None or captured is not None:
                    raise RuntimeError("V2.46.02 failure unexpectedly has capability")
                proof_inputs.append(row)
        if capabilities or rows:
            raise RuntimeError("V2.46.02 unconsumed capability vector")
        installed = total.task_projection
        if (
            getattr(installed, "__self__", None) is not self
            or getattr(installed, "__func__", None) is not type(self).project
        ):
            raise RuntimeError("V2.46.02 capability projector binding drifted")
        total.task_projection = FROZEN_TASK_PROJECTION
        try:
            return total.aggregate_projections(proof_inputs, selected=selected)
        finally:
            drifted = total.task_projection is not FROZEN_TASK_PROJECTION
            total.task_projection = installed
            if drifted:
                raise RuntimeError("V2.46.02 aggregate projector drifted")

    def destroy(self) -> None:
        with self._lock:
            self._capabilities.clear()
            self._rows.clear()
            self._consumed = True


@contextmanager
def capability_collection() -> Iterator[_CapabilityCollector]:
    global _ACTIVE_COLLECTOR
    if not _COLLECTOR_GUARD.acquire(blocking=False):
        raise RuntimeError("V2.46.02 capability collector is already active")
    collector = _CapabilityCollector()
    original = total.task_projection
    if _ACTIVE_COLLECTOR is not None or original is not FROZEN_TASK_PROJECTION:
        _COLLECTOR_GUARD.release()
        raise RuntimeError("V2.46.02 collector binding surface drifted")
    _ACTIVE_COLLECTOR = collector
    total.task_projection = collector.project
    try:
        yield collector
    finally:
        total.task_projection = original
        collector.destroy()
        _ACTIVE_COLLECTOR = None
        _COLLECTOR_GUARD.release()


def aggregate_projections(
    values: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    collector = _ACTIVE_COLLECTOR
    if collector is None:
        raise RuntimeError("V2.46.02 opaque capability collector is absent")
    return collector.aggregate(values, selected=selected)


__all__ = [
    "FROZEN_TASK_PROJECTION",
    "POLICY_ID",
    "aggregate_projections",
    "binding_valid",
    "capability_collection",
]
