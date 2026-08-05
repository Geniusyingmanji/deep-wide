"""Bind V2.45.29 acquisition around the frozen V2.45.27 worker.

The proof/capability, total projection, process supervisor, and deadline
budgets are unchanged.  The V2.45.29 receipt is validated before this wrapper
returns; the pinned validator/source manifest binds the acquisition code.  No
new public task artifact is added, preserving the exact V2.45.25 proof surface.
"""

from __future__ import annotations

from typing import Any

from . import v24527_bounded_alias_title_parent as parent
from .v24529_alias_seeded_target_acquisition import (
    AliasSeededTargetAcquisition,
    validate_receipt,
)


POLICY_ID = "v24530_alias_seeded_bounded_worker_v1"


def run_alias_seeded_worker(*args: Any, **kwargs: Any) -> dict[str, Any]:
    acquisition = AliasSeededTargetAcquisition()
    with acquisition:
        result = parent.run_alias_title_worker(*args, **kwargs)
    receipt = validate_receipt(acquisition.content_free_receipt())
    if (
        receipt["targeted_query_vector_calls"]
        + receipt["discovery_query_vector_calls"]
        < 1
        or receipt["lead_selection_calls"] < 1
    ):
        raise RuntimeError("V2.45.30 alias acquisition did not execute")
    return result


supervise_alias_seeded_worker_with_separated_budget = (
    parent.supervise_alias_title_worker_with_separated_budget
)
run_alias_seeded_parent_with_separated_budget = (
    parent.run_alias_title_parent_with_separated_budget
)
run_alias_seeded_timed_subprocess = parent.run_alias_title_timed_subprocess
budget_vector_seconds = parent.budget_vector_seconds


__all__ = [
    "POLICY_ID",
    "budget_vector_seconds",
    "run_alias_seeded_parent_with_separated_budget",
    "run_alias_seeded_timed_subprocess",
    "run_alias_seeded_worker",
    "supervise_alias_seeded_worker_with_separated_budget",
]
