"""Capability-only conversion observability for future targeted gates.

The V2.44.91 proof capability already contains a fully validated targeted
support receipt.  Earlier public projections discarded several content-free
conversion counts, making post-terminal diagnosis unable to distinguish page,
observation, support-count, posterior, and margin bottlenecks.  This append-
only projection exposes only integer/numeric aggregates and the fixed
threshold partition.  It accepts only the opaque V2.44.91 capability and
emits no task, query, URL, page, source, value, prediction, or hash.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .v24447_third_source_entropy_to_decision import THRESHOLD_PARTITION_FIELDS
from .v24490_entropy_targeted_support_search import (
    MAXIMUM_TARGETED_SOURCES,
    validate_recovery_receipt,
)
from .v24491_proof_carrying_targeted_support import (
    ValidatedProofCarryingTargetedEnvelope,
    _normalized_targeted_support_receipt,
)


POLICY_ID = "v24495_targeted_conversion_capability_projection_v1"
COUNT_FIELDS = (
    "targeted_cell_count",
    "selected_target_count",
    "targeted_discovered_source_count",
    "targeted_selected_source_count",
    "targeted_usable_page_count",
    "targeted_new_observation_count",
    "support_deficit_before_targeted_search",
    "safe_change_count_before_targeted_search",
    "safe_change_count_after_targeted_search",
    "candidate_changed_cell_count_after_targeted_search",
)
NUMERIC_FIELDS = (
    "positive_information_gain_total_nats_after_targeted_search",
    "epistemic_credit_total_nats_after_targeted_search",
    "decision_credit_total_nats_after_targeted_search",
)
TASK_KEYS = frozenset(
    {
        "ordinal",
        *COUNT_FIELDS,
        *NUMERIC_FIELDS,
        "threshold_failure_partition_after_targeted_search",
        "support_selection_yield",
        "usable_page_yield",
        "new_observation_yield",
        "safe_change_improvement",
        "positive_decision_credit",
        "projection_consumed_only_validated_capability",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)
AGGREGATE_KEYS = frozenset(
    {
        "selected",
        "exact_ordinal_vector",
        *(f"total_{name}" for name in COUNT_FIELDS),
        *(f"total_{name}" for name in NUMERIC_FIELDS),
        "threshold_failure_partition_totals",
        "target_plan_tasks",
        "support_selection_yield_tasks",
        "usable_page_yield_tasks",
        "new_observation_yield_tasks",
        "safe_change_improvement_tasks",
        "positive_decision_credit_tasks",
        "all_projections_consumed_validated_capabilities",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)


def _count(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"V2.44.95 invalid count: {name}")
    return item


def _number(value: Mapping[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        or float(item) < 0
    ):
        raise ValueError(f"V2.44.95 invalid number: {name}")
    return float(item)


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingTargetedEnvelope
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingTargetedEnvelope)
    ):
        raise TypeError("V2.44.95 requires ordinal and targeted capability")
    receipts = capability.counts_only_receipts()
    support = _normalized_targeted_support_receipt(
        receipts["targeted_support_receipt"]
    )
    validate_recovery_receipt(support)
    value = {
        "ordinal": ordinal,
        **{name: int(support[name]) for name in COUNT_FIELDS},
        **{name: float(support[name]) for name in NUMERIC_FIELDS},
        "threshold_failure_partition_after_targeted_search": {
            name: int(
                support["threshold_failure_partition_after_targeted_search"][name]
            )
            for name in THRESHOLD_PARTITION_FIELDS
        },
        "support_selection_yield": support["targeted_selected_source_count"] > 0,
        "usable_page_yield": support["targeted_usable_page_count"] > 0,
        "new_observation_yield": support["targeted_new_observation_count"] > 0,
        "safe_change_improvement": support["safe_change_count_after_targeted_search"]
        > support["safe_change_count_before_targeted_search"],
        "positive_decision_credit": support[
            "decision_credit_total_nats_after_targeted_search"
        ]
        > 0,
        "projection_consumed_only_validated_capability": True,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    return validate_task_projection(value)


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    partition = copied.get("threshold_failure_partition_after_targeted_search")
    if (
        set(copied) != TASK_KEYS
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or any(_count(copied, name) < 0 for name in COUNT_FIELDS)
        or any(_number(copied, name) < 0 for name in NUMERIC_FIELDS)
        or not isinstance(partition, Mapping)
        or tuple(partition) != THRESHOLD_PARTITION_FIELDS
        or any(
            isinstance(partition[name], bool)
            or not isinstance(partition[name], int)
            or partition[name] < 0
            for name in THRESHOLD_PARTITION_FIELDS
        )
        or sum(partition.values()) != copied["selected_target_count"]
        or partition["safe_change_count"]
        != copied["safe_change_count_after_targeted_search"]
        or copied["targeted_cell_count"] not in {0, 1}
        or copied["targeted_selected_source_count"]
        > copied["targeted_discovered_source_count"]
        or copied["targeted_usable_page_count"]
        > copied["targeted_selected_source_count"]
        or copied["support_deficit_before_targeted_search"]
        > MAXIMUM_TARGETED_SOURCES
        or copied["safe_change_count_before_targeted_search"]
        > copied["selected_target_count"]
        or copied["safe_change_count_after_targeted_search"]
        > copied["selected_target_count"]
        or copied["targeted_cell_count"] == 0
        and any(
            copied[name] != 0
            for name in (
                "targeted_discovered_source_count",
                "targeted_selected_source_count",
                "targeted_usable_page_count",
                "targeted_new_observation_count",
                "support_deficit_before_targeted_search",
            )
        )
        or copied["targeted_cell_count"] == 1
        and not 1
        <= copied["support_deficit_before_targeted_search"]
        <= MAXIMUM_TARGETED_SOURCES
        or copied["targeted_new_observation_count"] > 0
        and copied["targeted_usable_page_count"] == 0
        or copied["safe_change_count_after_targeted_search"]
        > copied["safe_change_count_before_targeted_search"]
        and copied["targeted_new_observation_count"] == 0
        or copied["decision_credit_total_nats_after_targeted_search"] > 0
        and (
            copied["safe_change_count_after_targeted_search"]
            <= copied["safe_change_count_before_targeted_search"]
            or copied["candidate_changed_cell_count_after_targeted_search"] == 0
        )
        or copied.get("support_selection_yield")
        is not (copied["targeted_selected_source_count"] > 0)
        or copied.get("usable_page_yield")
        is not (copied["targeted_usable_page_count"] > 0)
        or copied.get("new_observation_yield")
        is not (copied["targeted_new_observation_count"] > 0)
        or copied.get("safe_change_improvement")
        is not (
            copied["safe_change_count_after_targeted_search"]
            > copied["safe_change_count_before_targeted_search"]
        )
        or copied.get("positive_decision_credit")
        is not (
            copied["decision_credit_total_nats_after_targeted_search"] > 0
        )
        or copied["decision_credit_total_nats_after_targeted_search"]
        > copied["epistemic_credit_total_nats_after_targeted_search"] + 1e-12
        or copied["epistemic_credit_total_nats_after_targeted_search"]
        > copied["positive_information_gain_total_nats_after_targeted_search"]
        + 1e-12
        or copied.get("projection_consumed_only_validated_capability") is not True
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.95 conversion projection drifted")
    return copied


def aggregate_projections(
    values: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    rows = sorted(
        (validate_task_projection(value) for value in values),
        key=lambda value: value["ordinal"],
    )
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(rows) != selected
        or [row["ordinal"] for row in rows] != list(range(1, selected + 1))
    ):
        raise ValueError("V2.44.95 aggregate selection drifted")
    value = {
        "selected": selected,
        "exact_ordinal_vector": True,
        **{
            f"total_{name}": sum(row[name] for row in rows)
            for name in COUNT_FIELDS
        },
        **{
            f"total_{name}": sum(row[name] for row in rows)
            for name in NUMERIC_FIELDS
        },
        "threshold_failure_partition_totals": {
            name: sum(
                row["threshold_failure_partition_after_targeted_search"][name]
                for row in rows
            )
            for name in THRESHOLD_PARTITION_FIELDS
        },
        "target_plan_tasks": sum(row["targeted_cell_count"] > 0 for row in rows),
        "support_selection_yield_tasks": sum(
            row["support_selection_yield"] for row in rows
        ),
        "usable_page_yield_tasks": sum(row["usable_page_yield"] for row in rows),
        "new_observation_yield_tasks": sum(
            row["new_observation_yield"] for row in rows
        ),
        "safe_change_improvement_tasks": sum(
            row["safe_change_improvement"] for row in rows
        ),
        "positive_decision_credit_tasks": sum(
            row["positive_decision_credit"] for row in rows
        ),
        "all_projections_consumed_validated_capabilities": True,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    partition = copied.get("threshold_failure_partition_totals")
    count_names = (
        "selected",
        *(f"total_{name}" for name in COUNT_FIELDS),
        "target_plan_tasks",
        "support_selection_yield_tasks",
        "usable_page_yield_tasks",
        "new_observation_yield_tasks",
        "safe_change_improvement_tasks",
        "positive_decision_credit_tasks",
    )
    numeric_names = tuple(f"total_{name}" for name in NUMERIC_FIELDS)
    if (
        set(copied) != AGGREGATE_KEYS
        or any(_count(copied, name) < 0 for name in count_names)
        or copied["selected"] < 1
        or any(
            copied[name] > copied["selected"]
            for name in (
                "target_plan_tasks",
                "support_selection_yield_tasks",
                "usable_page_yield_tasks",
                "new_observation_yield_tasks",
                "safe_change_improvement_tasks",
                "positive_decision_credit_tasks",
            )
        )
        or any(_number(copied, name) < 0 for name in numeric_names)
        or not isinstance(partition, Mapping)
        or tuple(partition) != THRESHOLD_PARTITION_FIELDS
        or any(
            isinstance(partition[name], bool)
            or not isinstance(partition[name], int)
            or partition[name] < 0
            for name in THRESHOLD_PARTITION_FIELDS
        )
        or sum(partition.values()) != copied["total_selected_target_count"]
        or partition["safe_change_count"]
        != copied["total_safe_change_count_after_targeted_search"]
        or copied["total_targeted_cell_count"] != copied["target_plan_tasks"]
        or copied["total_targeted_cell_count"] > copied["selected"]
        or copied["total_targeted_selected_source_count"]
        > copied["total_targeted_discovered_source_count"]
        or copied["total_targeted_usable_page_count"]
        > copied["total_targeted_selected_source_count"]
        or copied["total_safe_change_count_before_targeted_search"]
        > copied["total_selected_target_count"]
        or copied["total_safe_change_count_after_targeted_search"]
        > copied["total_selected_target_count"]
        or not copied["target_plan_tasks"]
        <= copied["total_support_deficit_before_targeted_search"]
        <= copied["target_plan_tasks"] * MAXIMUM_TARGETED_SOURCES
        or copied["support_selection_yield_tasks"]
        > copied["target_plan_tasks"]
        or copied["usable_page_yield_tasks"]
        > copied["support_selection_yield_tasks"]
        or copied["new_observation_yield_tasks"]
        > copied["usable_page_yield_tasks"]
        or copied["safe_change_improvement_tasks"]
        > copied["new_observation_yield_tasks"]
        or copied["positive_decision_credit_tasks"]
        > copied["safe_change_improvement_tasks"]
        or (
            copied[
                "total_decision_credit_total_nats_after_targeted_search"
            ]
            > 0
        )
        is not (copied["positive_decision_credit_tasks"] > 0)
        or copied["total_decision_credit_total_nats_after_targeted_search"]
        > copied["total_epistemic_credit_total_nats_after_targeted_search"]
        + 1e-12
        or copied["total_epistemic_credit_total_nats_after_targeted_search"]
        > copied[
            "total_positive_information_gain_total_nats_after_targeted_search"
        ]
        + 1e-12
        or copied.get("exact_ordinal_vector") is not True
        or copied.get("all_projections_consumed_validated_capabilities") is not True
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.95 conversion aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "COUNT_FIELDS",
    "NUMERIC_FIELDS",
    "POLICY_ID",
    "TASK_KEYS",
    "aggregate_projections",
    "task_projection",
    "validate_aggregate",
    "validate_task_projection",
]
