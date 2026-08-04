"""Total public projection for V2.44.92 success and failure rows.

Successful rows remain the exact V2.44.91 capability projections.  Failed
workers use the separate V2.44.92 content-free zero schema.  This adapter
normalizes both into one aggregate-safe surface without claiming that a
failure row consumed a validated capability or had zero private effects; the
separate observation aggregate retains all known lower bounds.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .v24491_proof_carrying_targeted_support import (
    validate_task_projection as validate_success_projection,
)
from .v24492_targeted_timed_parent import validate_failure_projection


POLICY_ID = "v24493_total_targeted_projection_v1"
ROW_KEYS = frozenset(
    {
        "ordinal",
        "status",
        "passed",
        "target_plan_present",
        "safe_change_count_before_targeted_search",
        "safe_change_count_after_targeted_search",
        "decision_credit_total_nats_after_targeted_search",
        "additional_fetch_effects",
        "additional_model_acquisitions",
        "validation_memo_misses",
        "validation_memo_hits",
        "validation_memo_mismatches",
        "projection_consumed_validated_capability",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)
AGGREGATE_KEYS = frozenset(
    {
        "selected",
        "exact_ordinal_vector",
        "success_tasks",
        "failure_as_zero_tasks",
        "passed_success_tasks",
        "target_plan_tasks",
        "safe_change_improvement_tasks",
        "positive_decision_credit_tasks",
        "total_additional_fetch_effects_success_rows",
        "total_additional_model_acquisitions_success_rows",
        "total_validation_memo_misses",
        "total_validation_memo_hits",
        "total_validation_memo_mismatches",
        "total_decision_credit_nats",
        "all_success_rows_consumed_validated_capabilities",
        "all_failure_rows_are_content_free_zero_projections",
        "failure_rows_claim_zero_private_effects",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)


def _from_success(value: Mapping[str, Any]) -> dict[str, Any]:
    item = validate_success_projection(value)
    return {
        "ordinal": item["ordinal"],
        "status": "validated_capability",
        "passed": item["passed"],
        "target_plan_present": item["target_plan_present"],
        "safe_change_count_before_targeted_search": item[
            "safe_change_count_before_targeted_search"
        ],
        "safe_change_count_after_targeted_search": item[
            "safe_change_count_after_targeted_search"
        ],
        "decision_credit_total_nats_after_targeted_search": item[
            "decision_credit_total_nats_after_targeted_search"
        ],
        "additional_fetch_effects": item["additional_fetch_effects"],
        "additional_model_acquisitions": item["additional_model_acquisitions"],
        "validation_memo_misses": item["validation_memo_misses"],
        "validation_memo_hits": item["validation_memo_hits"],
        "validation_memo_mismatches": item["validation_memo_mismatches"],
        "projection_consumed_validated_capability": True,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }


def normalize_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("status") == "failure_as_zero":
        return validate_total_row(validate_failure_projection(value))
    return validate_total_row(_from_success(value))


def validate_total_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    counts = (
        "safe_change_count_before_targeted_search",
        "safe_change_count_after_targeted_search",
        "additional_fetch_effects",
        "additional_model_acquisitions",
        "validation_memo_misses",
        "validation_memo_hits",
        "validation_memo_mismatches",
    )
    number = copied.get("decision_credit_total_nats_after_targeted_search")
    success = copied.get("status") == "validated_capability"
    if (
        set(copied) != ROW_KEYS
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or copied.get("status") not in {"validated_capability", "failure_as_zero"}
        or not isinstance(copied.get("passed"), bool)
        or not isinstance(copied.get("target_plan_present"), bool)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or isinstance(number, bool)
        or not isinstance(number, (int, float))
        or not math.isfinite(float(number))
        or float(number) < 0
        or copied.get("projection_consumed_validated_capability") is not success
        or not success
        and copied != validate_failure_projection(copied)
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.93 total targeted row drifted")
    return copied


def aggregate_projections(
    values: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    rows = sorted(
        (normalize_projection(value) for value in values),
        key=lambda value: value["ordinal"],
    )
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(rows) != selected
        or [row["ordinal"] for row in rows] != list(range(1, selected + 1))
    ):
        raise ValueError("V2.44.93 aggregate selection drifted")
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    value = {
        "selected": selected,
        "exact_ordinal_vector": True,
        "success_tasks": len(successes),
        "failure_as_zero_tasks": len(failures),
        "passed_success_tasks": sum(row["passed"] for row in successes),
        "target_plan_tasks": sum(row["target_plan_present"] for row in successes),
        "safe_change_improvement_tasks": sum(
            row["safe_change_count_after_targeted_search"]
            > row["safe_change_count_before_targeted_search"]
            for row in successes
        ),
        "positive_decision_credit_tasks": sum(
            row["decision_credit_total_nats_after_targeted_search"] > 0
            for row in successes
        ),
        "total_additional_fetch_effects_success_rows": sum(
            row["additional_fetch_effects"] for row in successes
        ),
        "total_additional_model_acquisitions_success_rows": sum(
            row["additional_model_acquisitions"] for row in successes
        ),
        "total_validation_memo_misses": sum(
            row["validation_memo_misses"] for row in successes
        ),
        "total_validation_memo_hits": sum(
            row["validation_memo_hits"] for row in successes
        ),
        "total_validation_memo_mismatches": sum(
            row["validation_memo_mismatches"] for row in successes
        ),
        "total_decision_credit_nats": sum(
            row["decision_credit_total_nats_after_targeted_search"]
            for row in successes
        ),
        "all_success_rows_consumed_validated_capabilities": all(
            row["projection_consumed_validated_capability"] for row in successes
        ),
        "all_failure_rows_are_content_free_zero_projections": all(
            row == validate_failure_projection(row) for row in failures
        ),
        "failure_rows_claim_zero_private_effects": False,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    counts = tuple(
        name
        for name in AGGREGATE_KEYS
        if name
        not in {
            "exact_ordinal_vector",
            "total_decision_credit_nats",
            "all_success_rows_consumed_validated_capabilities",
            "all_failure_rows_are_content_free_zero_projections",
            "failure_rows_claim_zero_private_effects",
            "private_task_content_emitted",
            "privileged_evaluator_content_read",
        }
    )
    credit = copied.get("total_decision_credit_nats")
    if (
        set(copied) != AGGREGATE_KEYS
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied.get("selected", 0) < 1
        or copied.get("success_tasks", -1)
        + copied.get("failure_as_zero_tasks", -1)
        != copied.get("selected")
        or copied.get("passed_success_tasks", 0) > copied.get("success_tasks", -1)
        or isinstance(credit, bool)
        or not isinstance(credit, (int, float))
        or not math.isfinite(float(credit))
        or float(credit) < 0
        or copied.get("exact_ordinal_vector") is not True
        or copied.get("all_success_rows_consumed_validated_capabilities") is not True
        or copied.get("all_failure_rows_are_content_free_zero_projections") is not True
        or copied.get("failure_rows_claim_zero_private_effects") is not False
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.93 total targeted aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "POLICY_ID",
    "ROW_KEYS",
    "aggregate_projections",
    "normalize_projection",
    "validate_aggregate",
    "validate_total_row",
]
