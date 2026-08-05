"""Strict same-task reachability-to-conversion joint.

This append-only successor keeps V2.45.61 unchanged and adds the missing
intersection: the same task must contain a one-observation reachable plan, a
changed legacy entropy-first choice, and the complete alias/observation/IG/
safe-change/decision-credit conversion chain.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24561_decision_reachability_conversion_joint as parent
from .v24557_proof_carrying_decision_reachability import (
    ValidatedProofCarryingDecisionReachability,
)


POLICY_ID = "v24564_strict_reachability_conversion_joint_v1"
FIELD = "decision_reachability_one_observation_changed_legacy_full_conversion_joint"
TASK_FIELD = f"{FIELD}_tasks"
ROW_KEYS = frozenset({*parent.ROW_KEYS, FIELD})


def _strict_value(row: Mapping[str, Any]) -> int:
    return int(
        int(row["decision_reachability_one_observation_full_conversion_joint"])
        == 1
        and int(row["decision_reachability_legacy_entropy_choice_changed_calls"])
        > 0
    )


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingDecisionReachability
) -> dict[str, Any]:
    if not isinstance(capability, ValidatedProofCarryingDecisionReachability):
        raise TypeError("V2.45.64 requires a decision-reachability capability")
    base = parent.task_projection(ordinal, capability)
    return validate_total_row({**base, FIELD: _strict_value(base)})


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {**parent._failure_unchecked(ordinal), FIELD: 0}


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.64 failure ordinal is invalid")
    return validate_total_row(_failure_unchecked(ordinal))


def validate_total_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {name: copied[name] for name in parent.ROW_KEYS if name in copied}
    success = copied.get("status") == "validated_capability"
    expected = _strict_value(base) if success else 0
    if (
        set(copied) != ROW_KEYS
        or set(base) != parent.ROW_KEYS
        or parent.validate_total_row(base) != base
        or isinstance(copied.get(FIELD), bool)
        or not isinstance(copied.get(FIELD), int)
        or copied[FIELD] not in (0, 1)
        or copied[FIELD] != expected
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.64 strict conversion-joint row drifted")
    return copied


AGGREGATE_KEYS = frozenset({*parent.AGGREGATE_KEYS, TASK_FIELD})


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
        raise ValueError("V2.45.64 aggregate selection drifted")
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
                    "V2.45.64 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.64 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    value = {**base, TASK_FIELD: sum(row[FIELD] for row in rows)}
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    count = copied.get(TASK_FIELD)
    if (
        set(copied) != AGGREGATE_KEYS
        or set(base) != parent.AGGREGATE_KEYS
        or parent.validate_aggregate(base) != base
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count < 0
        or count > copied["success_tasks"]
        or count
        > copied[
            "decision_reachability_one_observation_full_conversion_joint_tasks"
        ]
        or count > copied["decision_reachability_changed_legacy_choice_tasks"]
        or count
        > copied[
            "decision_reachability_changed_legacy_full_conversion_joint_tasks"
        ]
    ):
        raise ValueError("V2.45.64 strict conversion-joint aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "FIELD",
    "POLICY_ID",
    "ROW_KEYS",
    "TASK_FIELD",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
