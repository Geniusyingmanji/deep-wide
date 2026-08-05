"""Total public projection for reserve success and failure rows."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .v24497_proof_carrying_targeted_reserve import (
    validate_task_projection as validate_success_projection,
)
from .v24498_reserve_timed_parent import validate_failure_projection


POLICY_ID = "v24498_total_reserve_projection_v1"
ROW_COUNT_FIELDS = (
    "targeted_plan_present",
    "reserve_selected_source_count",
    "reserve_usable_page_count",
    "reserve_new_observation_count",
    "reserve_supporting_target_observation_count",
    "reserve_conflicting_target_observation_count",
    "safe_change_improvement_count",
    "safe_change_regression_count",
    "additional_fetch_effects",
    "additional_model_acquisitions",
    "validation_memo_misses",
    "validation_memo_hits",
    "validation_memo_mismatches",
)
ROW_NUMBER_FIELDS = (
    "decision_credit_gain_nats",
    "decision_credit_regression_nats",
)
ROW_KEYS = frozenset(
    {
        "ordinal",
        "status",
        "passed",
        *ROW_COUNT_FIELDS,
        *ROW_NUMBER_FIELDS,
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
        "reserve_engaged_tasks",
        "reserve_usable_page_tasks",
        "reserve_new_observation_tasks",
        "reserve_supporting_observation_tasks",
        "reserve_conflicting_observation_tasks",
        "safe_change_improvement_tasks",
        "safe_change_regression_tasks",
        "positive_decision_credit_gain_tasks",
        "decision_credit_regression_tasks",
        "total_reserve_selected_source_count",
        "total_reserve_usable_page_count",
        "total_reserve_new_observation_count",
        "total_reserve_supporting_target_observation_count",
        "total_reserve_conflicting_target_observation_count",
        "total_additional_fetch_effects_success_rows",
        "total_additional_model_acquisitions_success_rows",
        "total_validation_memo_misses",
        "total_validation_memo_hits",
        "total_validation_memo_mismatches",
        "total_decision_credit_gain_nats",
        "total_decision_credit_regression_nats",
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
        **{name: item[name] for name in ROW_COUNT_FIELDS},
        **{name: item[name] for name in ROW_NUMBER_FIELDS},
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
    success = copied.get("status") == "validated_capability"
    if (
        set(copied) != ROW_KEYS
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or copied.get("status") not in {"validated_capability", "failure_as_zero"}
        or not isinstance(copied.get("passed"), bool)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in ROW_COUNT_FIELDS
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in ROW_NUMBER_FIELDS
        )
        or copied["reserve_usable_page_count"]
        > copied["reserve_selected_source_count"]
        or copied["reserve_supporting_target_observation_count"]
        + copied["reserve_conflicting_target_observation_count"]
        > copied["reserve_new_observation_count"]
        or copied["additional_fetch_effects"]
        != copied["reserve_selected_source_count"]
        or copied["additional_model_acquisitions"] != 0
        or (copied["decision_credit_gain_nats"] > 0)
        is not (copied["safe_change_improvement_count"] > 0)
        or copied.get("projection_consumed_validated_capability") is not success
        or not success
        and copied != validate_failure_projection(copied)
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.98 total reserve row drifted")
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
        raise ValueError("V2.44.98 total reserve selection drifted")
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    value = {
        "selected": selected,
        "exact_ordinal_vector": True,
        "success_tasks": len(successes),
        "failure_as_zero_tasks": len(failures),
        "passed_success_tasks": sum(row["passed"] for row in successes),
        "target_plan_tasks": sum(row["targeted_plan_present"] > 0 for row in successes),
        "reserve_engaged_tasks": sum(row["reserve_selected_source_count"] > 0 for row in successes),
        "reserve_usable_page_tasks": sum(row["reserve_usable_page_count"] > 0 for row in successes),
        "reserve_new_observation_tasks": sum(row["reserve_new_observation_count"] > 0 for row in successes),
        "reserve_supporting_observation_tasks": sum(row["reserve_supporting_target_observation_count"] > 0 for row in successes),
        "reserve_conflicting_observation_tasks": sum(row["reserve_conflicting_target_observation_count"] > 0 for row in successes),
        "safe_change_improvement_tasks": sum(row["safe_change_improvement_count"] > 0 for row in successes),
        "safe_change_regression_tasks": sum(row["safe_change_regression_count"] > 0 for row in successes),
        "positive_decision_credit_gain_tasks": sum(row["decision_credit_gain_nats"] > 0 for row in successes),
        "decision_credit_regression_tasks": sum(row["decision_credit_regression_nats"] > 0 for row in successes),
        "total_reserve_selected_source_count": sum(row["reserve_selected_source_count"] for row in successes),
        "total_reserve_usable_page_count": sum(row["reserve_usable_page_count"] for row in successes),
        "total_reserve_new_observation_count": sum(row["reserve_new_observation_count"] for row in successes),
        "total_reserve_supporting_target_observation_count": sum(row["reserve_supporting_target_observation_count"] for row in successes),
        "total_reserve_conflicting_target_observation_count": sum(row["reserve_conflicting_target_observation_count"] for row in successes),
        "total_additional_fetch_effects_success_rows": sum(row["additional_fetch_effects"] for row in successes),
        "total_additional_model_acquisitions_success_rows": sum(row["additional_model_acquisitions"] for row in successes),
        "total_validation_memo_misses": sum(row["validation_memo_misses"] for row in successes),
        "total_validation_memo_hits": sum(row["validation_memo_hits"] for row in successes),
        "total_validation_memo_mismatches": sum(row["validation_memo_mismatches"] for row in successes),
        "total_decision_credit_gain_nats": sum(row["decision_credit_gain_nats"] for row in successes),
        "total_decision_credit_regression_nats": sum(row["decision_credit_regression_nats"] for row in successes),
        "all_success_rows_consumed_validated_capabilities": all(row["projection_consumed_validated_capability"] for row in successes),
        "all_failure_rows_are_content_free_zero_projections": all(row == validate_failure_projection(row) for row in failures),
        "failure_rows_claim_zero_private_effects": False,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    numeric = (
        "total_decision_credit_gain_nats",
        "total_decision_credit_regression_nats",
    )
    noncounts = {
        "exact_ordinal_vector",
        *numeric,
        "all_success_rows_consumed_validated_capabilities",
        "all_failure_rows_are_content_free_zero_projections",
        "failure_rows_claim_zero_private_effects",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
    counts = tuple(name for name in AGGREGATE_KEYS if name not in noncounts)
    task_counts = (
        "passed_success_tasks",
        "target_plan_tasks",
        "reserve_engaged_tasks",
        "reserve_usable_page_tasks",
        "reserve_new_observation_tasks",
        "reserve_supporting_observation_tasks",
        "reserve_conflicting_observation_tasks",
        "safe_change_improvement_tasks",
        "safe_change_regression_tasks",
        "positive_decision_credit_gain_tasks",
        "decision_credit_regression_tasks",
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["selected"] < 1
        or copied["success_tasks"] + copied["failure_as_zero_tasks"]
        != copied["selected"]
        or any(copied[name] > copied["success_tasks"] for name in task_counts)
        or copied["reserve_usable_page_tasks"] > copied["reserve_engaged_tasks"]
        or copied["reserve_new_observation_tasks"] > copied["reserve_usable_page_tasks"]
        or copied["safe_change_improvement_tasks"] > copied["reserve_new_observation_tasks"]
        or copied["positive_decision_credit_gain_tasks"] > copied["safe_change_improvement_tasks"]
        or copied["total_reserve_usable_page_count"] > copied["total_reserve_selected_source_count"]
        or copied["total_reserve_supporting_target_observation_count"]
        + copied["total_reserve_conflicting_target_observation_count"]
        > copied["total_reserve_new_observation_count"]
        or copied["total_additional_fetch_effects_success_rows"]
        != copied["total_reserve_selected_source_count"]
        or copied["total_additional_model_acquisitions_success_rows"] != 0
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in numeric
        )
        or (copied["total_decision_credit_gain_nats"] > 0)
        is not (copied["positive_decision_credit_gain_tasks"] > 0)
        or (copied["total_decision_credit_regression_nats"] > 0)
        is not (copied["decision_credit_regression_tasks"] > 0)
        or copied.get("exact_ordinal_vector") is not True
        or copied.get("all_success_rows_consumed_validated_capabilities") is not True
        or copied.get("all_failure_rows_are_content_free_zero_projections") is not True
        or copied.get("failure_rows_claim_zero_private_effects") is not False
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.98 total reserve aggregate drifted")
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
