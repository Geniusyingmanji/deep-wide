"""Total public projection for record-bound success and failure rows."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .v24504_proof_carrying_record_bound_reserve import (
    validate_task_projection as validate_success_projection,
)
from .v24505_record_bound_timed_parent import validate_failure_projection


POLICY_ID = "v24505_total_record_bound_projection_v1"
ROW_COUNT_FIELDS = (
    "targeted_plan_present",
    "reserve_selected_source_count",
    "reserve_usable_page_count",
    "reserve_new_observation_count",
    "parent_active_observation_count",
    "record_bound_active_observation_count",
    "added_observation_count",
    "removed_observation_count",
    "ambiguous_source_observation_removal_count",
    "record_bound_projection_count",
    "safe_change_improvement_count",
    "safe_change_regression_count",
    "additional_external_effects",
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
        "private_effects_known_zero",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)


def _from_success(value: Mapping[str, Any]) -> dict[str, Any]:
    item = validate_success_projection(value)
    effects = sum(
        item[name]
        for name in (
            "additional_model_requests",
            "additional_logical_queries",
            "additional_search_batches",
            "additional_provider_search_calls",
            "additional_fetch_calls",
        )
    )
    return {
        "ordinal": item["ordinal"],
        "status": "validated_capability",
        "passed": item["passed"],
        **{
            name: item[name]
            for name in ROW_COUNT_FIELDS
            if name != "additional_external_effects"
        },
        "additional_external_effects": effects,
        **{name: item[name] for name in ROW_NUMBER_FIELDS},
        "projection_consumed_validated_capability": True,
        "private_effects_known_zero": True,
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
        or copied["record_bound_active_observation_count"]
        != copied["parent_active_observation_count"]
        + copied["added_observation_count"]
        - copied["removed_observation_count"]
        or copied["ambiguous_source_observation_removal_count"]
        > copied["removed_observation_count"]
        or copied["additional_external_effects"] != 0
        or (copied["decision_credit_gain_nats"] > 0)
        is not (copied["safe_change_improvement_count"] > 0)
        or copied.get("projection_consumed_validated_capability") is not success
        or copied.get("private_effects_known_zero") is not success
        or not success
        and copied != validate_failure_projection(copied)
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.45.05 total record-bound row drifted")
    return copied


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
        "parent_observation_tasks",
        "record_bound_added_observation_tasks",
        "record_bound_removed_observation_tasks",
        "record_bound_projection_tasks",
        "safe_change_improvement_tasks",
        "safe_change_regression_tasks",
        "positive_decision_credit_gain_tasks",
        "decision_credit_regression_tasks",
        "total_added_observation_count",
        "total_removed_observation_count",
        "total_record_bound_projection_count",
        "total_decision_credit_gain_nats",
        "total_decision_credit_regression_nats",
        "total_additional_external_effects_success_rows",
        "total_validation_memo_misses",
        "total_validation_memo_hits",
        "total_validation_memo_mismatches",
        "all_success_rows_consumed_validated_capabilities",
        "all_failure_rows_are_content_free_zero_projections",
        "failure_rows_claim_zero_private_effects",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)


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
        raise ValueError("V2.45.05 total selection drifted")
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    value = {
        "selected": selected,
        "exact_ordinal_vector": True,
        "success_tasks": len(successes),
        "failure_as_zero_tasks": len(failures),
        "passed_success_tasks": sum(row["passed"] for row in successes),
        "target_plan_tasks": sum(row["targeted_plan_present"] > 0 for row in successes),
        "reserve_engaged_tasks": sum(
            row["reserve_selected_source_count"] > 0 for row in successes
        ),
        "reserve_usable_page_tasks": sum(
            row["reserve_usable_page_count"] > 0 for row in successes
        ),
        "parent_observation_tasks": sum(
            row["reserve_new_observation_count"] > 0 for row in successes
        ),
        "record_bound_added_observation_tasks": sum(
            row["added_observation_count"] > 0 for row in successes
        ),
        "record_bound_removed_observation_tasks": sum(
            row["removed_observation_count"] > 0 for row in successes
        ),
        "record_bound_projection_tasks": sum(
            row["record_bound_projection_count"] > 0 for row in successes
        ),
        "safe_change_improvement_tasks": sum(
            row["safe_change_improvement_count"] > 0 for row in successes
        ),
        "safe_change_regression_tasks": sum(
            row["safe_change_regression_count"] > 0 for row in successes
        ),
        "positive_decision_credit_gain_tasks": sum(
            row["decision_credit_gain_nats"] > 0 for row in successes
        ),
        "decision_credit_regression_tasks": sum(
            row["decision_credit_regression_nats"] > 0 for row in successes
        ),
        "total_added_observation_count": sum(
            row["added_observation_count"] for row in successes
        ),
        "total_removed_observation_count": sum(
            row["removed_observation_count"] for row in successes
        ),
        "total_record_bound_projection_count": sum(
            row["record_bound_projection_count"] for row in successes
        ),
        "total_decision_credit_gain_nats": sum(
            row["decision_credit_gain_nats"] for row in successes
        ),
        "total_decision_credit_regression_nats": sum(
            row["decision_credit_regression_nats"] for row in successes
        ),
        "total_additional_external_effects_success_rows": sum(
            row["additional_external_effects"] for row in successes
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
    numeric = (
        "total_decision_credit_gain_nats",
        "total_decision_credit_regression_nats",
    )
    true_fields = (
        "exact_ordinal_vector",
        "all_success_rows_consumed_validated_capabilities",
        "all_failure_rows_are_content_free_zero_projections",
    )
    false_fields = (
        "failure_rows_claim_zero_private_effects",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    )
    counts = tuple(
        name
        for name in AGGREGATE_KEYS
        if name not in {*numeric, *true_fields, *false_fields}
    )
    task_counts = (
        "passed_success_tasks",
        "target_plan_tasks",
        "reserve_engaged_tasks",
        "reserve_usable_page_tasks",
        "parent_observation_tasks",
        "record_bound_added_observation_tasks",
        "record_bound_removed_observation_tasks",
        "record_bound_projection_tasks",
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
        or copied["total_additional_external_effects_success_rows"] != 0
        or copied["total_validation_memo_mismatches"] != 0
        or copied["total_added_observation_count"]
        < copied["record_bound_added_observation_tasks"]
        or (copied["total_added_observation_count"] > 0)
        is not (copied["record_bound_added_observation_tasks"] > 0)
        or copied["total_removed_observation_count"]
        < copied["record_bound_removed_observation_tasks"]
        or (copied["total_removed_observation_count"] > 0)
        is not (copied["record_bound_removed_observation_tasks"] > 0)
        or copied["total_record_bound_projection_count"]
        < copied["record_bound_projection_tasks"]
        or (copied["total_record_bound_projection_count"] > 0)
        is not (copied["record_bound_projection_tasks"] > 0)
        or copied["positive_decision_credit_gain_tasks"]
        > copied["safe_change_improvement_tasks"]
        or copied["decision_credit_regression_tasks"]
        > copied["safe_change_regression_tasks"]
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
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.05 total record-bound aggregate drifted")
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
