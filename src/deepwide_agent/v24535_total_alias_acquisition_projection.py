"""Capability-only total projection for alias acquisition action credit."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24526_total_alias_title_projection as parent
from . import v24533_alias_acquisition_entropy_credit as action
from .v24534_proof_carrying_alias_acquisition import (
    ValidatedProofCarryingAliasAcquisition,
)


POLICY_ID = "v24535_capability_only_total_alias_acquisition_projection_v1"
COUNT_PREFIX = "acquisition_action_"
NUMBER_PREFIX = "acquisition_action_"
COUNT_FIELDS = tuple(f"{COUNT_PREFIX}{name}" for name in action.COUNT_FIELDS)
NUMBER_FIELDS = tuple(f"{NUMBER_PREFIX}{name}" for name in action.NUMBER_FIELDS)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *COUNT_FIELDS,
        *NUMBER_FIELDS,
        "acquisition_action_receipt_consumed_validated_capability",
        "acquisition_action_private_effects_known_zero",
        "acquisition_action_private_task_content_emitted",
        "acquisition_action_privileged_evaluator_content_read",
    }
)


def _count_name(name: str) -> str:
    return f"{COUNT_PREFIX}{name}"


def _number_name(name: str) -> str:
    return f"{NUMBER_PREFIX}{name}"


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingAliasAcquisition
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingAliasAcquisition)
    ):
        raise TypeError("V2.45.35 requires ordinal and acquisition capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = action.validate_action_credit_receipt(
        capability.action_credit_receipt()
    )
    if base["targeted_plan_present"] != receipt["target_plan_count"]:
        raise ValueError("V2.45.35 parent/acquisition plan drifted")
    value = {
        **base,
        **{
            _count_name(name): int(receipt[name])
            for name in action.COUNT_FIELDS
        },
        **{
            _number_name(name): float(receipt[name])
            for name in action.NUMBER_FIELDS
        },
        "acquisition_action_receipt_consumed_validated_capability": True,
        "acquisition_action_private_effects_known_zero": True,
        "acquisition_action_private_task_content_emitted": False,
        "acquisition_action_privileged_evaluator_content_read": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in COUNT_FIELDS},
        **{name: 0.0 for name in NUMBER_FIELDS},
        "acquisition_action_receipt_consumed_validated_capability": False,
        "acquisition_action_private_effects_known_zero": False,
        "acquisition_action_private_task_content_emitted": False,
        "acquisition_action_privileged_evaluator_content_read": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.35 failure ordinal is invalid")
    return validate_total_row(_failure_unchecked(ordinal))


def validate_total_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {name: copied[name] for name in parent.ROW_KEYS if name in copied}
    success = copied.get("status") == "validated_capability"
    count = lambda name: copied.get(_count_name(name))
    number = lambda name: copied.get(_number_name(name))
    active = (
        count("target_plan_count") == 1
        and count("alias_seeded_query_vector_calls") > 0
        and count("lead_selection_calls") > 0
        and count("selected_lead_count") > 0
        and count("targeted_selected_source_count") > 0
        and count("targeted_new_observation_count") > 0
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
        or base["targeted_plan_present"] != count("target_plan_count")
        or count("target_plan_count") not in {0, 1}
        or count("targeted_logical_query_count")
        != count("target_plan_count") * 2
        or count("targeted_search_batch_count") != count("target_plan_count")
        or count("targeted_usable_page_count")
        > count("targeted_selected_source_count")
        or count("alias_seeded_query_vector_calls")
        + count("row_without_safe_alias_query_vector_calls")
        != count("targeted_query_vector_calls")
        + count("discovery_query_vector_calls")
        or count("selected_alias_title_hit_lead_count")
        > count("selected_lead_count")
        or count("selected_lead_count") > count("visible_lead_count")
        or count("alias_title_hit_lead_count") > count("visible_lead_count")
        or count("target_plan_count") == 0
        and (
            count("targeted_query_vector_calls")
            + count("discovery_query_vector_calls")
            + count("lead_selection_calls")
            != 0
        )
        or count("target_plan_count") == 1
        and (
            count("targeted_query_vector_calls")
            + count("discovery_query_vector_calls")
            < 1
            or count("lead_selection_calls") < 1
        )
        or count("safe_change_improvement_count")
        != max(
            0,
            count("safe_change_count_after_targeted_search")
            - count("safe_change_count_before_targeted_search"),
        )
        or count("safe_change_regression_count")
        != max(
            0,
            count("safe_change_count_before_targeted_search")
            - count("safe_change_count_after_targeted_search"),
        )
        or not math.isclose(
            number("information_gain_gain_nats"),
            max(
                0.0,
                number("information_gain_total_nats_after_targeted_search")
                - number("information_gain_total_nats_before_targeted_search"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("information_gain_regression_nats"),
            max(
                0.0,
                number("information_gain_total_nats_before_targeted_search")
                - number("information_gain_total_nats_after_targeted_search"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("epistemic_credit_gain_nats"),
            max(
                0.0,
                number("epistemic_credit_total_nats_after_targeted_search")
                - number("epistemic_credit_total_nats_before_targeted_search"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("epistemic_credit_regression_nats"),
            max(
                0.0,
                number("epistemic_credit_total_nats_before_targeted_search")
                - number("epistemic_credit_total_nats_after_targeted_search"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("decision_credit_gain_nats"),
            max(
                0.0,
                number("decision_credit_total_nats_after_targeted_search")
                - number("decision_credit_total_nats_before_targeted_search"),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("decision_credit_regression_nats"),
            max(
                0.0,
                number("decision_credit_total_nats_before_targeted_search")
                - number("decision_credit_total_nats_after_targeted_search"),
            ),
            abs_tol=1e-12,
        )
        or count("action_positive_information_gain_count")
        != int(number("action_information_credit_nats") > 0)
        or count("action_positive_epistemic_credit_count")
        != int(number("action_epistemic_credit_nats") > 0)
        or count("action_positive_decision_credit_count")
        != int(number("action_decision_credit_nats") > 0)
        or count("action_decision_credit_regression_count")
        != int(number("action_decision_credit_regression_nats") > 0)
        or not math.isclose(
            number("action_information_credit_nats"),
            number("information_gain_gain_nats") if active else 0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("action_epistemic_credit_nats"),
            number("epistemic_credit_gain_nats") if active else 0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("action_decision_credit_nats"),
            (
                number("decision_credit_gain_nats")
                if active
                and count("safe_change_improvement_count") > 0
                and count("candidate_changed_cell_count_after_targeted_search")
                > 0
                else 0.0
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            number("action_decision_credit_regression_nats"),
            number("decision_credit_regression_nats") if active else 0.0,
            abs_tol=1e-12,
        )
        or number("action_decision_credit_nats")
        > number("action_epistemic_credit_nats") + 1e-12
        or copied.get(
            "acquisition_action_receipt_consumed_validated_capability"
        )
        is not success
        or copied.get("acquisition_action_private_effects_known_zero")
        is not success
        or copied.get("acquisition_action_private_task_content_emitted")
        is not False
        or copied.get("acquisition_action_privileged_evaluator_content_read")
        is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.35 total acquisition row drifted")
    return copied


TASK_FIELDS = (
    "acquisition_plan_tasks",
    "acquisition_activity_tasks",
    "acquisition_new_observation_tasks",
    "acquisition_alias_title_hit_tasks",
    "acquisition_selected_alias_title_hit_tasks",
    "acquisition_positive_information_gain_tasks",
    "acquisition_positive_epistemic_credit_tasks",
    "acquisition_positive_decision_credit_tasks",
    "acquisition_decision_credit_regression_tasks",
    "acquisition_safe_change_improvement_tasks",
    "acquisition_safe_change_regression_tasks",
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_acquisition_action_count_fields",
        "total_acquisition_action_number_fields",
        "all_acquisition_success_rows_consumed_validated_capabilities",
        "all_acquisition_failure_rows_are_content_free_zero_projections",
        "acquisition_failure_rows_claim_zero_private_effects",
        "acquisition_private_task_content_emitted",
        "acquisition_privileged_evaluator_content_read",
    }
)


def aggregate_projections(
    values: Sequence[ValidatedProofCarryingAliasAcquisition | Mapping[str, Any]],
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
        raise ValueError("V2.45.35 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingAliasAcquisition):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item.parent_capability())
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.35 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.35 aggregate input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    counts = {
        name: sum(row[_count_name(name)] for row in successes)
        for name in action.COUNT_FIELDS
    }
    numbers = {
        name: sum(row[_number_name(name)] for row in successes)
        for name in action.NUMBER_FIELDS
    }
    value = {
        **base,
        "acquisition_plan_tasks": sum(
            row[_count_name("target_plan_count")] > 0 for row in successes
        ),
        "acquisition_activity_tasks": sum(
            row[_count_name("alias_seeded_query_vector_calls")] > 0
            and row[_count_name("lead_selection_calls")] > 0
            for row in successes
        ),
        "acquisition_new_observation_tasks": sum(
            row[_count_name("targeted_new_observation_count")] > 0
            for row in successes
        ),
        "acquisition_alias_title_hit_tasks": sum(
            row[_count_name("alias_title_hit_lead_count")] > 0
            for row in successes
        ),
        "acquisition_selected_alias_title_hit_tasks": sum(
            row[_count_name("selected_alias_title_hit_lead_count")] > 0
            for row in successes
        ),
        "acquisition_positive_information_gain_tasks": sum(
            row[_number_name("action_information_credit_nats")] > 0
            for row in successes
        ),
        "acquisition_positive_epistemic_credit_tasks": sum(
            row[_number_name("action_epistemic_credit_nats")] > 0
            for row in successes
        ),
        "acquisition_positive_decision_credit_tasks": sum(
            row[_number_name("action_decision_credit_nats")] > 0
            for row in successes
        ),
        "acquisition_decision_credit_regression_tasks": sum(
            row[_number_name("action_decision_credit_regression_nats")] > 0
            for row in successes
        ),
        "acquisition_safe_change_improvement_tasks": sum(
            row[_count_name("safe_change_improvement_count")] > 0
            for row in successes
        ),
        "acquisition_safe_change_regression_tasks": sum(
            row[_count_name("safe_change_regression_count")] > 0
            for row in successes
        ),
        "total_acquisition_action_count_fields": counts,
        "total_acquisition_action_number_fields": numbers,
        "all_acquisition_success_rows_consumed_validated_capabilities": all(
            row["acquisition_action_receipt_consumed_validated_capability"]
            for row in successes
        ),
        "all_acquisition_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "acquisition_failure_rows_claim_zero_private_effects": False,
        "acquisition_private_task_content_emitted": False,
        "acquisition_privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    counts = copied.get("total_acquisition_action_count_fields")
    numbers = copied.get("total_acquisition_action_number_fields")
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
        or set(counts) != set(action.COUNT_FIELDS)
        or any(
            isinstance(counts.get(name), bool)
            or not isinstance(counts.get(name), int)
            or counts[name] < 0
            for name in action.COUNT_FIELDS
        )
        or not isinstance(numbers, Mapping)
        or set(numbers) != set(action.NUMBER_FIELDS)
        or any(
            isinstance(numbers.get(name), bool)
            or not isinstance(numbers.get(name), (int, float))
            or not math.isfinite(float(numbers[name]))
            or float(numbers[name]) < 0
            for name in action.NUMBER_FIELDS
        )
        or counts["target_plan_count"] != copied["target_plan_tasks"]
        or counts["action_positive_information_gain_count"]
        != copied["acquisition_positive_information_gain_tasks"]
        or counts["action_positive_epistemic_credit_count"]
        != copied["acquisition_positive_epistemic_credit_tasks"]
        or counts["action_positive_decision_credit_count"]
        != copied["acquisition_positive_decision_credit_tasks"]
        or counts["action_decision_credit_regression_count"]
        != copied["acquisition_decision_credit_regression_tasks"]
        or numbers["action_information_credit_nats"]
        > numbers["information_gain_gain_nats"] + 1e-12
        or numbers["action_epistemic_credit_nats"]
        > numbers["epistemic_credit_gain_nats"] + 1e-12
        or numbers["action_decision_credit_nats"]
        > numbers["decision_credit_gain_nats"] + 1e-12
        or numbers["action_decision_credit_regression_nats"]
        > numbers["decision_credit_regression_nats"] + 1e-12
        or numbers["action_decision_credit_nats"]
        > numbers["action_epistemic_credit_nats"] + 1e-12
        or (counts["alias_seeded_query_vector_calls"] > 0)
        is not (copied["acquisition_activity_tasks"] > 0)
        or (counts["targeted_new_observation_count"] > 0)
        is not (copied["acquisition_new_observation_tasks"] > 0)
        or (counts["alias_title_hit_lead_count"] > 0)
        is not (copied["acquisition_alias_title_hit_tasks"] > 0)
        or (counts["selected_alias_title_hit_lead_count"] > 0)
        is not (copied["acquisition_selected_alias_title_hit_tasks"] > 0)
        or (numbers["action_information_credit_nats"] > 0)
        is not (copied["acquisition_positive_information_gain_tasks"] > 0)
        or (numbers["action_epistemic_credit_nats"] > 0)
        is not (copied["acquisition_positive_epistemic_credit_tasks"] > 0)
        or (numbers["action_decision_credit_nats"] > 0)
        is not (copied["acquisition_positive_decision_credit_tasks"] > 0)
        or (numbers["action_decision_credit_regression_nats"] > 0)
        is not (copied["acquisition_decision_credit_regression_tasks"] > 0)
        or (counts["safe_change_improvement_count"] > 0)
        is not (copied["acquisition_safe_change_improvement_tasks"] > 0)
        or (counts["safe_change_regression_count"] > 0)
        is not (copied["acquisition_safe_change_regression_tasks"] > 0)
        or copied.get(
            "all_acquisition_success_rows_consumed_validated_capabilities"
        )
        is not True
        or copied.get(
            "all_acquisition_failure_rows_are_content_free_zero_projections"
        )
        is not True
        or copied.get("acquisition_failure_rows_claim_zero_private_effects")
        is not False
        or copied.get("acquisition_private_task_content_emitted") is not False
        or copied.get("acquisition_privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.45.35 total acquisition aggregate drifted")
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
