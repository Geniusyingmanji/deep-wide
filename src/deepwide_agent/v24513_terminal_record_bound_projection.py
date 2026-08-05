"""Total public projection with proof-derived terminal decision state.

V2.45.12 exposed only record-stage deltas.  A zero safe-change/credit gain is
ambiguous: every layer may have failed, or an earlier targeted/reserve layer
may already have produced a safe terminal decision that record recovery
preserved.  This module extends the V2.45.05 total row with absolute parent and
terminal safe-change counts, candidate-change counts, and decision-credit
totals already bound into the V2.45.04 capability certificate.

Failure rows remain conservative zeros and do not claim that private effects
were zero.  No task content, value, source, page, prediction, label, evaluator,
or score is exposed.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24505_total_record_bound_projection as parent
from .v24504_proof_carrying_record_bound_reserve import (
    ValidatedProofCarryingRecordBoundEnvelope,
    task_projection as base_task_projection,
    validate_task_projection as validate_base_task_projection,
)
from .v24505_record_bound_timed_parent import (
    failure_projection as base_failure_projection,
)


POLICY_ID = "v24513_terminal_record_bound_projection_v1"
TERMINAL_COUNT_FIELDS = (
    "parent_safe_change_count",
    "terminal_safe_change_count",
    "parent_candidate_changed_cell_count",
    "terminal_candidate_changed_cell_count",
)
TERMINAL_NUMBER_FIELDS = (
    "parent_decision_credit_total_nats",
    "terminal_decision_credit_total_nats",
)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *TERMINAL_COUNT_FIELDS,
        *TERMINAL_NUMBER_FIELDS,
        "terminal_state_consumed_validated_capability",
    }
)


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingRecordBoundEnvelope
) -> dict[str, Any]:
    raw = base_task_projection(ordinal, capability)
    receipts = capability.counts_only_receipts()
    record = receipts["record_bound_receipt"]
    if any(
        raw[name] != record[name]
        for name in (
            *TERMINAL_COUNT_FIELDS[:1],
            "record_bound_safe_change_count",
            "parent_candidate_changed_cell_count",
            "record_bound_candidate_changed_cell_count",
            *TERMINAL_NUMBER_FIELDS[:1],
            "record_bound_decision_credit_total_nats",
        )
    ):
        raise ValueError("V2.45.13 capability receipt projection drifted")
    return _from_success_projection(raw)


def _from_success_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    raw = validate_base_task_projection(value)
    base = parent.normalize_projection(raw)
    value = {
        **base,
        "parent_safe_change_count": int(raw["parent_safe_change_count"]),
        "terminal_safe_change_count": int(
            raw["record_bound_safe_change_count"]
        ),
        "parent_candidate_changed_cell_count": int(
            raw["parent_candidate_changed_cell_count"]
        ),
        "terminal_candidate_changed_cell_count": int(
            raw["record_bound_candidate_changed_cell_count"]
        ),
        "parent_decision_credit_total_nats": float(
            raw["parent_decision_credit_total_nats"]
        ),
        "terminal_decision_credit_total_nats": float(
            raw["record_bound_decision_credit_total_nats"]
        ),
        "terminal_state_consumed_validated_capability": True,
    }
    return validate_total_row(value)


def failure_projection(ordinal: int) -> dict[str, Any]:
    value = {
        **base_failure_projection(ordinal),
        **{name: 0 for name in TERMINAL_COUNT_FIELDS},
        **{name: 0.0 for name in TERMINAL_NUMBER_FIELDS},
        "terminal_state_consumed_validated_capability": False,
    }
    return validate_total_row(value)


def normalize_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("status") == "failure_as_zero":
        return failure_projection(int(value.get("ordinal", 0)))
    # Aggregate only the complete V2.45.04 capability projection.  Re-ingesting
    # an already expanded terminal row would let a structurally self-consistent
    # public dictionary stand in for the proof-derived predecessor surface.
    if set(value) == ROW_KEYS:
        raise ValueError("V2.45.13 expanded terminal row cannot be re-ingested")
    return _from_success_projection(value)


def validate_total_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {name: copied[name] for name in parent.ROW_KEYS if name in copied}
    success = copied.get("status") == "validated_capability"
    if (
        set(copied) != ROW_KEYS
        or set(base) != parent.ROW_KEYS
        or parent.validate_total_row(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in TERMINAL_COUNT_FIELDS
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in TERMINAL_NUMBER_FIELDS
        )
        or copied["safe_change_improvement_count"]
        != max(
            0,
            copied["terminal_safe_change_count"]
            - copied["parent_safe_change_count"],
        )
        or copied["safe_change_regression_count"]
        != max(
            0,
            copied["parent_safe_change_count"]
            - copied["terminal_safe_change_count"],
        )
        or not math.isclose(
            float(copied["decision_credit_gain_nats"]),
            max(
                0.0,
                float(copied["terminal_decision_credit_total_nats"])
                - float(copied["parent_decision_credit_total_nats"]),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            float(copied["decision_credit_regression_nats"]),
            max(
                0.0,
                float(copied["parent_decision_credit_total_nats"])
                - float(copied["terminal_decision_credit_total_nats"]),
            ),
            abs_tol=1e-12,
        )
        or copied["terminal_safe_change_count"]
        > copied["terminal_candidate_changed_cell_count"]
        or (copied["terminal_decision_credit_total_nats"] > 0)
        and (
            copied["terminal_safe_change_count"] == 0
            or copied["terminal_candidate_changed_cell_count"] == 0
        )
        or copied.get("terminal_state_consumed_validated_capability")
        is not success
        or not success
        and copied != failure_projection_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.13 terminal row drifted")
    return copied


def failure_projection_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **base_failure_projection(ordinal),
        **{name: 0 for name in TERMINAL_COUNT_FIELDS},
        **{name: 0.0 for name in TERMINAL_NUMBER_FIELDS},
        "terminal_state_consumed_validated_capability": False,
    }


AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        "parent_safe_change_tasks",
        "terminal_safe_change_tasks",
        "parent_positive_decision_credit_tasks",
        "terminal_positive_decision_credit_tasks",
        "total_parent_safe_change_count",
        "total_terminal_safe_change_count",
        "total_safe_change_improvement_count",
        "total_safe_change_regression_count",
        "total_parent_candidate_changed_cell_count",
        "total_terminal_candidate_changed_cell_count",
        "total_parent_decision_credit_nats",
        "total_terminal_decision_credit_nats",
        "all_terminal_states_consumed_validated_capabilities",
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
        raise ValueError("V2.45.13 terminal selection drifted")
    successes = [
        row for row in rows if row["status"] == "validated_capability"
    ]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    base = {
        "selected": selected,
        "exact_ordinal_vector": True,
        "success_tasks": len(successes),
        "failure_as_zero_tasks": len(failures),
        "passed_success_tasks": sum(row["passed"] for row in successes),
        "target_plan_tasks": sum(
            row["targeted_plan_present"] > 0 for row in successes
        ),
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
            row["projection_consumed_validated_capability"]
            for row in successes
        ),
        "all_failure_rows_are_content_free_zero_projections": all(
            row == failure_projection_unchecked(row["ordinal"])
            for row in failures
        ),
        "failure_rows_claim_zero_private_effects": False,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    parent.validate_aggregate(base)
    value = {
        **base,
        "parent_safe_change_tasks": sum(
            row["parent_safe_change_count"] > 0 for row in successes
        ),
        "terminal_safe_change_tasks": sum(
            row["terminal_safe_change_count"] > 0 for row in successes
        ),
        "parent_positive_decision_credit_tasks": sum(
            row["parent_decision_credit_total_nats"] > 0 for row in successes
        ),
        "terminal_positive_decision_credit_tasks": sum(
            row["terminal_decision_credit_total_nats"] > 0 for row in successes
        ),
        "total_parent_safe_change_count": sum(
            row["parent_safe_change_count"] for row in successes
        ),
        "total_terminal_safe_change_count": sum(
            row["terminal_safe_change_count"] for row in successes
        ),
        "total_safe_change_improvement_count": sum(
            row["safe_change_improvement_count"] for row in successes
        ),
        "total_safe_change_regression_count": sum(
            row["safe_change_regression_count"] for row in successes
        ),
        "total_parent_candidate_changed_cell_count": sum(
            row["parent_candidate_changed_cell_count"] for row in successes
        ),
        "total_terminal_candidate_changed_cell_count": sum(
            row["terminal_candidate_changed_cell_count"] for row in successes
        ),
        "total_parent_decision_credit_nats": sum(
            row["parent_decision_credit_total_nats"] for row in successes
        ),
        "total_terminal_decision_credit_nats": sum(
            row["terminal_decision_credit_total_nats"] for row in successes
        ),
        "all_terminal_states_consumed_validated_capabilities": all(
            row["terminal_state_consumed_validated_capability"]
            for row in successes
        ),
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    count_fields = (
        "parent_safe_change_tasks",
        "terminal_safe_change_tasks",
        "parent_positive_decision_credit_tasks",
        "terminal_positive_decision_credit_tasks",
        "total_parent_safe_change_count",
        "total_terminal_safe_change_count",
        "total_safe_change_improvement_count",
        "total_safe_change_regression_count",
        "total_parent_candidate_changed_cell_count",
        "total_terminal_candidate_changed_cell_count",
    )
    number_fields = (
        "total_parent_decision_credit_nats",
        "total_terminal_decision_credit_nats",
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or set(base) != parent.AGGREGATE_KEYS
        or parent.validate_aggregate(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in number_fields
        )
        or any(
            copied[name] > copied["success_tasks"]
            for name in (
                "parent_safe_change_tasks",
                "terminal_safe_change_tasks",
                "parent_positive_decision_credit_tasks",
                "terminal_positive_decision_credit_tasks",
            )
        )
        or (copied["total_parent_decision_credit_nats"] > 0)
        is not (copied["parent_positive_decision_credit_tasks"] > 0)
        or (copied["total_terminal_decision_credit_nats"] > 0)
        is not (copied["terminal_positive_decision_credit_tasks"] > 0)
        or copied["parent_positive_decision_credit_tasks"]
        > copied["parent_safe_change_tasks"]
        or copied["terminal_positive_decision_credit_tasks"]
        > copied["terminal_safe_change_tasks"]
        or copied["total_parent_safe_change_count"]
        > copied["total_parent_candidate_changed_cell_count"]
        or copied["total_terminal_safe_change_count"]
        > copied["total_terminal_candidate_changed_cell_count"]
        or copied["total_terminal_safe_change_count"]
        != copied["total_parent_safe_change_count"]
        + copied["total_safe_change_improvement_count"]
        - copied["total_safe_change_regression_count"]
        or not math.isclose(
            float(copied["total_terminal_decision_credit_nats"]),
            float(copied["total_parent_decision_credit_nats"])
            + float(copied["total_decision_credit_gain_nats"])
            - float(copied["total_decision_credit_regression_nats"]),
            abs_tol=1e-12,
        )
        or (copied["total_parent_safe_change_count"] > 0)
        is not (copied["parent_safe_change_tasks"] > 0)
        or (copied["total_terminal_safe_change_count"] > 0)
        is not (copied["terminal_safe_change_tasks"] > 0)
        or (copied["total_safe_change_improvement_count"] > 0)
        is not (copied["safe_change_improvement_tasks"] > 0)
        or (copied["total_safe_change_regression_count"] > 0)
        is not (copied["safe_change_regression_tasks"] > 0)
        or copied.get("all_terminal_states_consumed_validated_capabilities")
        is not True
    ):
        raise ValueError("V2.45.13 terminal aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "POLICY_ID",
    "ROW_KEYS",
    "aggregate_projections",
    "failure_projection",
    "normalize_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
