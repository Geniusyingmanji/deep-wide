"""Bind V2.50.05 detail projection into the frozen V2.50.02 paired runtime.

V2.50.02 deliberately requires instances of its audited robust search-client
class.  V2.50.05 is an append-only subclass that changes only the isolated
helper identity, so it already satisfies that boundary.  This wrapper adds an
exact V2.50.05 entry check and delegates without mutating any parent global,
preserving cross-task concurrency and every parent algorithm, receipt, budget,
arm, and validator.

The wrapper accepts exactly ``opaque_id`` and ``question`` through the parent
runtime.  It has no file, environment, network, model, evaluator, benchmark,
score, reward, or credential capability of its own.  Entropy/information gain
remain shadow-only and assign no signed credit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25002_page_visible_link_paired_runtime as parent
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v25005_detail_field_fetch import DetailFieldLatePageBoundSearchClient


POLICY_ID = "v25006_detail_field_page_visible_link_runtime_binding_v1"
ARMS = parent.ARMS
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM
FIRST_PHASE = parent.FIRST_PHASE
SECOND_PHASE = parent.SECOND_PHASE
PHASES = parent.PHASES
ROLE = parent.ROLE
RECEIPT_ROLE = parent.RECEIPT_ROLE


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, DetailFieldLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], DetailFieldLatePageBoundSearchClient)
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.50.06 requires two distinct detail-field clients")
    kwargs: dict[str, Any] = {
        "model": model,
        "searches": searches,
        "limits": limits,
        "arm_order": arm_order,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    value = parent.run_paired_task(task, **kwargs)
    return parent.validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    return parent.validate_result(value)


def validate_binding() -> None:
    if (
        parent.RobustLatePageBoundSearchClient.__name__
        != "RobustLatePageBoundSearchClient"
        or not issubclass(
            DetailFieldLatePageBoundSearchClient,
            parent.RobustLatePageBoundSearchClient,
        )
    ):
        raise RuntimeError("V2.50.06 detail-field runtime binding drifted")


__all__ = [
    "ARMS", "CANDIDATE_ARM", "CONTROL_ARM", "FIRST_PHASE", "PHASES",
    "POLICY_ID", "RECEIPT_ROLE", "ROLE", "SECOND_PHASE", "run_paired_task",
    "validate_binding", "validate_result",
]
