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
from .v24524_alias_title_integration import validate_alias_title_receipt
from . import v24490_entropy_targeted_support_search as targeted


POLICY_ID = "v24530_alias_seeded_bounded_worker_v1"


def validate_acquisition_activity(
    result: dict[str, Any], receipt_value: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = validate_receipt(receipt_value)
    validated = validate_alias_title_receipt(result["alias_title_receipt"])
    if validated != result["alias_title_receipt"]:
        raise RuntimeError("V2.45.30 alias result receipt drifted")
    record = result["parent_result"]
    reserve = record["parent_result"]
    targeted_result = reserve["parent_result"]
    if not isinstance(targeted_result, dict):
        raise RuntimeError("V2.45.30 targeted result shell is absent")
    target_receipt = targeted.validate_recovery_receipt(
        targeted_result["targeted_support_receipt"]
    )
    target_count = target_receipt["targeted_cell_count"]
    query_calls = (
        receipt["targeted_query_vector_calls"]
        + receipt["discovery_query_vector_calls"]
    )
    selection_calls = receipt["lead_selection_calls"]
    if (
        target_count not in {0, 1}
        or target_count == 1
        and (query_calls < 1 or selection_calls < 1)
        or target_count == 0
        and (query_calls != 0 or selection_calls != 0)
    ):
        raise RuntimeError("V2.45.30 alias acquisition activity/plan drifted")
    return result, receipt


def run_alias_seeded_worker_with_receipt(
    *args: Any, **kwargs: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    acquisition = AliasSeededTargetAcquisition()
    with acquisition:
        result = parent.run_alias_title_worker(*args, **kwargs)
    return validate_acquisition_activity(
        result, acquisition.content_free_receipt()
    )


def run_alias_seeded_worker(*args: Any, **kwargs: Any) -> dict[str, Any]:
    result, _receipt = run_alias_seeded_worker_with_receipt(*args, **kwargs)
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
    "run_alias_seeded_worker_with_receipt",
    "supervise_alias_seeded_worker_with_separated_budget",
    "validate_acquisition_activity",
]
