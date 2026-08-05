"""Capability-only total projection for the alias-title terminal stage.

Successful rows can be minted only from the opaque V2.45.25 capability.
Failure rows are exact content-free zeros and explicitly do not claim that
private effects were zero.  Public success dictionaries are valid display
objects, but aggregation cannot re-ingest them as proof.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24504_proof_carrying_record_bound_reserve as base_proof
from . import v24513_terminal_record_bound_projection as parent
from . import v24524_alias_title_integration as alias
from .v24525_proof_carrying_alias_title import (
    ValidatedProofCarryingAliasTitle,
)


POLICY_ID = "v24526_capability_only_total_alias_title_projection_v1"
COUNT_PREFIX = "alias_stage_"
NUMBER_PREFIX = "alias_stage_"
COUNT_FIELDS = tuple(f"{COUNT_PREFIX}{name}" for name in alias.COUNT_FIELDS)
NUMBER_FIELDS = tuple(f"{NUMBER_PREFIX}{name}" for name in alias.NUMERIC_FIELDS)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *COUNT_FIELDS,
        *NUMBER_FIELDS,
        "alias_stage_receipt_consumed_validated_capability",
        "alias_stage_private_effects_known_zero",
        "alias_stage_private_task_content_emitted",
        "alias_stage_privileged_evaluator_content_read",
    }
)


def _count_name(name: str) -> str:
    return f"{COUNT_PREFIX}{name}"


def _number_name(name: str) -> str:
    return f"{NUMBER_PREFIX}{name}"


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingAliasTitle
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingAliasTitle)
    ):
        raise TypeError("V2.45.26 requires ordinal and alias capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = alias.validate_alias_title_receipt(
        capability.counts_only_receipt()
    )
    if (
        base["record_bound_active_observation_count"]
        != receipt["parent_active_observation_count"]
        or base["terminal_safe_change_count"]
        != receipt["parent_safe_change_count"]
        or base["terminal_candidate_changed_cell_count"]
        != receipt["parent_candidate_changed_cell_count"]
        or not math.isclose(
            float(base["terminal_decision_credit_total_nats"]),
            float(receipt["parent_decision_credit_total_nats"]),
            abs_tol=1e-12,
        )
    ):
        raise ValueError("V2.45.26 parent capability/alias receipt drifted")
    value = {
        **base,
        **{
            _count_name(name): int(receipt[name])
            for name in alias.COUNT_FIELDS
        },
        **{
            _number_name(name): float(receipt[name])
            for name in alias.NUMERIC_FIELDS
        },
        "alias_stage_receipt_consumed_validated_capability": True,
        "alias_stage_private_effects_known_zero": True,
        "alias_stage_private_task_content_emitted": False,
        "alias_stage_privileged_evaluator_content_read": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent.failure_projection_unchecked(ordinal),
        **{name: 0 for name in COUNT_FIELDS},
        **{name: 0.0 for name in NUMBER_FIELDS},
        "alias_stage_receipt_consumed_validated_capability": False,
        "alias_stage_private_effects_known_zero": False,
        "alias_stage_private_task_content_emitted": False,
        "alias_stage_privileged_evaluator_content_read": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.26 failure ordinal is invalid")
    return validate_total_row(_failure_unchecked(ordinal))


def validate_total_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {name: copied[name] for name in parent.ROW_KEYS if name in copied}
    success = copied.get("status") == "validated_capability"
    count = lambda name: copied.get(_count_name(name))
    number = lambda name: copied.get(_number_name(name))
    external_effect_names = (
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_provider_search_calls",
        "additional_fetch_calls",
    )
    if (
        set(copied) != ROW_KEYS
        or set(base) != parent.ROW_KEYS
        or parent.validate_total_row(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in COUNT_FIELDS
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in NUMBER_FIELDS
        )
        or count("alias_active_observation_count")
        != count("parent_active_observation_count")
        + count("added_observation_count")
        - count("removed_observation_count")
        or count("ambiguous_source_observation_rejection_count")
        != count("alias_ambiguous_source_observation_rejection_count")
        + count("exact_parent_ambiguous_source_observation_removal_count")
        or count("exact_parent_ambiguous_source_observation_removal_count")
        > count("removed_observation_count")
        or count("alias_projection_count") < count("alias_observation_count")
        or count("safe_change_improvement_count")
        != max(
            0,
            count("alias_safe_change_count")
            - count("parent_safe_change_count"),
        )
        or count("safe_change_regression_count")
        != max(
            0,
            count("parent_safe_change_count")
            - count("alias_safe_change_count"),
        )
        or count("candidate_change_improvement_count")
        != max(
            0,
            count("alias_candidate_changed_cell_count")
            - count("parent_candidate_changed_cell_count"),
        )
        or count("candidate_change_regression_count")
        != max(
            0,
            count("parent_candidate_changed_cell_count")
            - count("alias_candidate_changed_cell_count"),
        )
        or not math.isclose(
            number("positive_information_gain_gain_nats"),
            max(
                0.0,
                number("alias_positive_information_gain_total_nats")
                - number("parent_positive_information_gain_total_nats"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("positive_information_gain_regression_nats"),
            max(
                0.0,
                number("parent_positive_information_gain_total_nats")
                - number("alias_positive_information_gain_total_nats"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("epistemic_credit_gain_nats"),
            max(
                0.0,
                number("alias_epistemic_credit_total_nats")
                - number("parent_epistemic_credit_total_nats"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("epistemic_credit_regression_nats"),
            max(
                0.0,
                number("parent_epistemic_credit_total_nats")
                - number("alias_epistemic_credit_total_nats"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("decision_credit_gain_nats"),
            max(
                0.0,
                number("alias_decision_credit_total_nats")
                - number("parent_decision_credit_total_nats"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("decision_credit_regression_nats"),
            max(
                0.0,
                number("parent_decision_credit_total_nats")
                - number("alias_decision_credit_total_nats"),
            ),
            abs_tol=1e-12,
        )
        or number("alias_decision_credit_total_nats")
        > number("alias_epistemic_credit_total_nats") + 1e-12
        or number("decision_credit_gain_nats") > 0
        and (
            count("alias_safe_change_count") == 0
            or count("alias_candidate_changed_cell_count") == 0
        )
        or any(count(name) != 0 for name in external_effect_names)
        or base["record_bound_active_observation_count"]
        != count("parent_active_observation_count")
        or base["terminal_safe_change_count"]
        != count("parent_safe_change_count")
        or base["terminal_candidate_changed_cell_count"]
        != count("parent_candidate_changed_cell_count")
        or not math.isclose(
            float(base["terminal_decision_credit_total_nats"]),
            number("parent_decision_credit_total_nats"),
            abs_tol=1e-12,
        )
        or copied.get("alias_stage_receipt_consumed_validated_capability")
        is not success
        or copied.get("alias_stage_private_effects_known_zero") is not success
        or copied.get("alias_stage_private_task_content_emitted") is not False
        or copied.get("alias_stage_privileged_evaluator_content_read") is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.26 total alias row drifted")
    return copied


TASK_FIELDS = (
    "alias_anchor_tasks",
    "alias_projection_tasks",
    "alias_observation_tasks",
    "alias_added_observation_tasks",
    "alias_safe_change_improvement_tasks",
    "alias_safe_change_regression_tasks",
    "alias_positive_information_gain_tasks",
    "alias_epistemic_credit_gain_tasks",
    "alias_decision_credit_gain_tasks",
    "alias_decision_credit_regression_tasks",
    "alias_terminal_safe_change_tasks",
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_alias_stage_count_fields",
        "total_alias_stage_number_fields",
        "all_alias_success_rows_consumed_validated_capabilities",
        "all_alias_failure_rows_are_content_free_zero_projections",
        "alias_failure_rows_claim_zero_private_effects",
        "alias_private_task_content_emitted",
        "alias_privileged_evaluator_content_read",
    }
)


def aggregate_projections(
    values: Sequence[ValidatedProofCarryingAliasTitle | Mapping[str, Any]],
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
        raise ValueError("V2.45.26 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Mapping[str, Any]] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingAliasTitle):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(
                base_proof.task_projection(ordinal, item.parent_capability())
            )
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.26 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.26 aggregate input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    count_totals = {
        name: sum(row[_count_name(name)] for row in successes)
        for name in alias.COUNT_FIELDS
    }
    number_totals = {
        name: sum(row[_number_name(name)] for row in successes)
        for name in alias.NUMERIC_FIELDS
    }
    value = {
        **base,
        "alias_anchor_tasks": sum(
            row[_count_name("unique_alias_anchor_page_count")] > 0
            for row in successes
        ),
        "alias_projection_tasks": sum(
            row[_count_name("alias_projection_count")] > 0 for row in successes
        ),
        "alias_observation_tasks": sum(
            row[_count_name("alias_observation_count")] > 0 for row in successes
        ),
        "alias_added_observation_tasks": sum(
            row[_count_name("added_observation_count")] > 0 for row in successes
        ),
        "alias_safe_change_improvement_tasks": sum(
            row[_count_name("safe_change_improvement_count")] > 0
            for row in successes
        ),
        "alias_safe_change_regression_tasks": sum(
            row[_count_name("safe_change_regression_count")] > 0
            for row in successes
        ),
        "alias_positive_information_gain_tasks": sum(
            row[_number_name("positive_information_gain_gain_nats")] > 0
            for row in successes
        ),
        "alias_epistemic_credit_gain_tasks": sum(
            row[_number_name("epistemic_credit_gain_nats")] > 0
            for row in successes
        ),
        "alias_decision_credit_gain_tasks": sum(
            row[_number_name("decision_credit_gain_nats")] > 0
            for row in successes
        ),
        "alias_decision_credit_regression_tasks": sum(
            row[_number_name("decision_credit_regression_nats")] > 0
            for row in successes
        ),
        "alias_terminal_safe_change_tasks": sum(
            row[_count_name("alias_safe_change_count")] > 0
            for row in successes
        ),
        "total_alias_stage_count_fields": count_totals,
        "total_alias_stage_number_fields": number_totals,
        "all_alias_success_rows_consumed_validated_capabilities": all(
            row["alias_stage_receipt_consumed_validated_capability"]
            for row in successes
        ),
        "all_alias_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "alias_failure_rows_claim_zero_private_effects": False,
        "alias_private_task_content_emitted": False,
        "alias_privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    counts = copied.get("total_alias_stage_count_fields")
    numbers = copied.get("total_alias_stage_number_fields")
    if (
        set(copied) != AGGREGATE_KEYS
        or set(base) != parent.AGGREGATE_KEYS
        or parent.validate_aggregate(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            or copied[name] > copied["success_tasks"]
            for name in TASK_FIELDS
        )
        or not isinstance(counts, Mapping)
        or set(counts) != set(alias.COUNT_FIELDS)
        or any(
            isinstance(counts.get(name), bool)
            or not isinstance(counts.get(name), int)
            or counts[name] < 0
            for name in alias.COUNT_FIELDS
        )
        or not isinstance(numbers, Mapping)
        or set(numbers) != set(alias.NUMERIC_FIELDS)
        or any(
            isinstance(numbers.get(name), bool)
            or not isinstance(numbers.get(name), (int, float))
            or not math.isfinite(float(numbers[name]))
            or float(numbers[name]) < 0
            for name in alias.NUMERIC_FIELDS
        )
        or counts["alias_active_observation_count"]
        != counts["parent_active_observation_count"]
        + counts["added_observation_count"]
        - counts["removed_observation_count"]
        or counts["ambiguous_source_observation_rejection_count"]
        != counts["alias_ambiguous_source_observation_rejection_count"]
        + counts["exact_parent_ambiguous_source_observation_removal_count"]
        or counts["safe_change_improvement_count"]
        != max(
            0,
            counts["alias_safe_change_count"]
            - counts["parent_safe_change_count"],
        )
        or counts["safe_change_regression_count"]
        != max(
            0,
            counts["parent_safe_change_count"]
            - counts["alias_safe_change_count"],
        )
        or counts["candidate_change_improvement_count"]
        != max(
            0,
            counts["alias_candidate_changed_cell_count"]
            - counts["parent_candidate_changed_cell_count"],
        )
        or counts["candidate_change_regression_count"]
        != max(
            0,
            counts["parent_candidate_changed_cell_count"]
            - counts["alias_candidate_changed_cell_count"],
        )
        or not math.isclose(
            numbers["positive_information_gain_gain_nats"],
            max(
                0.0,
                numbers["alias_positive_information_gain_total_nats"]
                - numbers["parent_positive_information_gain_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            numbers["positive_information_gain_regression_nats"],
            max(
                0.0,
                numbers["parent_positive_information_gain_total_nats"]
                - numbers["alias_positive_information_gain_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            numbers["epistemic_credit_gain_nats"],
            max(
                0.0,
                numbers["alias_epistemic_credit_total_nats"]
                - numbers["parent_epistemic_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            numbers["epistemic_credit_regression_nats"],
            max(
                0.0,
                numbers["parent_epistemic_credit_total_nats"]
                - numbers["alias_epistemic_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            numbers["decision_credit_gain_nats"],
            max(
                0.0,
                numbers["alias_decision_credit_total_nats"]
                - numbers["parent_decision_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            numbers["decision_credit_regression_nats"],
            max(
                0.0,
                numbers["parent_decision_credit_total_nats"]
                - numbers["alias_decision_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or any(
            counts[name] != 0
            for name in (
                "additional_model_requests",
                "additional_logical_queries",
                "additional_search_batches",
                "additional_provider_search_calls",
                "additional_fetch_calls",
            )
        )
        or counts["parent_safe_change_count"]
        != copied["total_terminal_safe_change_count"]
        or counts["parent_candidate_changed_cell_count"]
        != copied["total_terminal_candidate_changed_cell_count"]
        or not math.isclose(
            numbers["parent_decision_credit_total_nats"],
            copied["total_terminal_decision_credit_nats"],
            abs_tol=1e-12,
        )
        or (counts["unique_alias_anchor_page_count"] > 0)
        is not (copied["alias_anchor_tasks"] > 0)
        or (counts["alias_projection_count"] > 0)
        is not (copied["alias_projection_tasks"] > 0)
        or (counts["alias_observation_count"] > 0)
        is not (copied["alias_observation_tasks"] > 0)
        or (counts["added_observation_count"] > 0)
        is not (copied["alias_added_observation_tasks"] > 0)
        or (counts["safe_change_improvement_count"] > 0)
        is not (copied["alias_safe_change_improvement_tasks"] > 0)
        or (counts["safe_change_regression_count"] > 0)
        is not (copied["alias_safe_change_regression_tasks"] > 0)
        or (numbers["positive_information_gain_gain_nats"] > 0)
        is not (copied["alias_positive_information_gain_tasks"] > 0)
        or (numbers["epistemic_credit_gain_nats"] > 0)
        is not (copied["alias_epistemic_credit_gain_tasks"] > 0)
        or (numbers["decision_credit_gain_nats"] > 0)
        is not (copied["alias_decision_credit_gain_tasks"] > 0)
        or (numbers["decision_credit_regression_nats"] > 0)
        is not (copied["alias_decision_credit_regression_tasks"] > 0)
        or (counts["alias_safe_change_count"] > 0)
        is not (copied["alias_terminal_safe_change_tasks"] > 0)
        or copied.get("all_alias_success_rows_consumed_validated_capabilities")
        is not True
        or copied.get("all_alias_failure_rows_are_content_free_zero_projections")
        is not True
        or copied.get("alias_failure_rows_claim_zero_private_effects") is not False
        or copied.get("alias_private_task_content_emitted") is not False
        or copied.get("alias_privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.45.26 total alias aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "COUNT_FIELDS",
    "NUMBER_FIELDS",
    "POLICY_ID",
    "ROW_KEYS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
