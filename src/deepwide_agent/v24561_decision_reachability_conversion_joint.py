"""Capability-only task joint for reachability-to-decision conversion.

The projection joins counts already proven by a V2.45.57 capability.  It says
only that planner reachability and the acquisition/evidence/decision chain
co-occurred in one task; it does not claim that a particular planner call,
query, lead, source, or page caused the safe change.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24558_total_decision_reachability_projection as parent
from .v24557_proof_carrying_decision_reachability import (
    ValidatedProofCarryingDecisionReachability,
)


POLICY_ID = "v24561_decision_reachability_conversion_joint_v1"
JOINT_NAMES = (
    "one_observation_full_conversion_joint",
    "changed_legacy_full_conversion_joint",
)
JOINT_FIELDS = tuple(f"decision_reachability_{name}" for name in JOINT_NAMES)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *JOINT_FIELDS,
        "decision_reachability_conversion_joint_claims_call_or_lead_level_causality",
    }
)


def _full_conversion(row: Mapping[str, Any]) -> bool:
    return (
        int(
            row[
                "alias_joint_selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
            ]
        )
        > 0
        and int(row["alias_joint_action_positive_information_gain_count"]) > 0
        and int(row["alias_joint_action_positive_epistemic_credit_count"]) > 0
        and int(row["alias_joint_safe_change_improvement_count"]) > 0
        and int(row["alias_joint_action_positive_decision_credit_count"]) > 0
        and float(row["alias_joint_action_information_credit_nats"]) > 0.0
        and float(row["alias_joint_action_epistemic_credit_nats"]) > 0.0
        and float(row["alias_joint_action_decision_credit_nats"]) > 0.0
    )


def _joint_values(row: Mapping[str, Any]) -> dict[str, int]:
    full = _full_conversion(row)
    return {
        JOINT_FIELDS[0]: int(
            full and int(row["decision_reachability_one_observation_plan_calls"]) > 0
        ),
        JOINT_FIELDS[1]: int(
            full
            and int(row["decision_reachability_legacy_entropy_choice_changed_calls"])
            > 0
        ),
    }


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingDecisionReachability
) -> dict[str, Any]:
    if not isinstance(capability, ValidatedProofCarryingDecisionReachability):
        raise TypeError("V2.45.61 requires a decision-reachability capability")
    base = parent.task_projection(ordinal, capability)
    value = {
        **base,
        **_joint_values(base),
        "decision_reachability_conversion_joint_claims_call_or_lead_level_causality": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in JOINT_FIELDS},
        "decision_reachability_conversion_joint_claims_call_or_lead_level_causality": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.61 failure ordinal is invalid")
    return validate_total_row(_failure_unchecked(ordinal))


def validate_total_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {name: copied[name] for name in parent.ROW_KEYS if name in copied}
    success = copied.get("status") == "validated_capability"
    expected = _joint_values(base) if success else {name: 0 for name in JOINT_FIELDS}
    if (
        set(copied) != ROW_KEYS
        or set(base) != parent.ROW_KEYS
        or parent.validate_total_row(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] not in (0, 1)
            for name in JOINT_FIELDS
        )
        or {name: copied[name] for name in JOINT_FIELDS} != expected
        or copied.get(
            "decision_reachability_conversion_joint_claims_call_or_lead_level_causality"
        )
        is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.61 conversion-joint row drifted")
    return copied


TASK_FIELDS = tuple(f"{name}_tasks" for name in JOINT_FIELDS)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_decision_reachability_conversion_joint_count_fields",
        "decision_reachability_conversion_joint_claims_call_or_lead_level_causality",
    }
)


def aggregate_projections(
    values: Sequence[
        ValidatedProofCarryingDecisionReachability | Mapping[str, Any]
    ],
    *,
    selected: int,
) -> dict[str, Any]:
    if (
        isinstance(values, (str, bytes))
        or isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(values) != selected
    ):
        raise ValueError("V2.45.61 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingDecisionReachability):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item)
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.61 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.61 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    counts = {
        name: sum(row[f"decision_reachability_{name}"] for row in rows)
        for name in JOINT_NAMES
    }
    value = {
        **base,
        **{
            f"decision_reachability_{name}_tasks": counts[name]
            for name in JOINT_NAMES
        },
        "total_decision_reachability_conversion_joint_count_fields": counts,
        "decision_reachability_conversion_joint_claims_call_or_lead_level_causality": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    counts = copied.get("total_decision_reachability_conversion_joint_count_fields")
    one = copied.get(TASK_FIELDS[0])
    changed = copied.get(TASK_FIELDS[1])
    if (
        set(copied) != AGGREGATE_KEYS
        or set(base) != parent.AGGREGATE_KEYS
        or parent.validate_aggregate(base) != base
        or not isinstance(counts, Mapping)
        or set(counts) != set(JOINT_NAMES)
        or any(
            isinstance(counts.get(name), bool)
            or not isinstance(counts.get(name), int)
            or counts[name] < 0
            or counts[name] > copied["success_tasks"]
            for name in JOINT_NAMES
        )
        or isinstance(one, bool)
        or not isinstance(one, int)
        or isinstance(changed, bool)
        or not isinstance(changed, int)
        or one != counts[JOINT_NAMES[0]]
        or changed != counts[JOINT_NAMES[1]]
        or changed > one
        or one > copied["decision_reachability_one_observation_plan_tasks"]
        or changed > copied["decision_reachability_changed_legacy_choice_tasks"]
        or one > copied["selected_alias_surface_hit_tasks"]
        or one > copied["alias_joint_new_observation_tasks"]
        or one > copied["alias_joint_raw_positive_information_gain_tasks"]
        or one > copied["alias_joint_safe_change_improvement_tasks"]
        or one > copied["alias_joint_action_positive_decision_credit_tasks"]
        or copied.get(
            "decision_reachability_conversion_joint_claims_call_or_lead_level_causality"
        )
        is not False
    ):
        raise ValueError("V2.45.61 conversion-joint aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "JOINT_FIELDS",
    "JOINT_NAMES",
    "POLICY_ID",
    "ROW_KEYS",
    "TASK_FIELDS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
