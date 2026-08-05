"""Capability-only total projection for V2.45.57 planner evidence."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24550_total_alias_joint_projection as parent
from . import v24555_decision_reachability_planner as planner
from .v24557_proof_carrying_decision_reachability import (
    ValidatedProofCarryingDecisionReachability,
)


POLICY_ID = "v24558_capability_only_total_decision_reachability_projection_v1"
PREFIX = "decision_reachability_"
PLANNER_COUNT_NAMES = (
    "selection_calls",
    "no_reachable_plan_calls",
    "one_observation_plan_calls",
    "two_observation_plan_calls",
    "three_observation_plan_calls",
    "legacy_entropy_choice_changed_calls",
    "reachable_candidate_count_total",
)
PLANNER_COUNT_FIELDS = tuple(f"{PREFIX}{name}" for name in PLANNER_COUNT_NAMES)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *PLANNER_COUNT_FIELDS,
        "decision_reachability_receipt_consumed_validated_capability",
        "decision_reachability_additional_private_effects_known_zero",
        "decision_reachability_private_task_content_emitted",
        "decision_reachability_privileged_evaluator_content_read",
        "decision_reachability_projection_claims_expected_utility_or_causality",
    }
)


def _name(name: str) -> str:
    return f"{PREFIX}{name}"


def _receipt_from_row(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": planner.POLICY_ID,
        "binding_count": planner.EXPECTED_BINDING_COUNT,
        **{name: int(value[_name(name)]) for name in PLANNER_COUNT_NAMES},
        "minimum_independent_observations_is_primary_priority": True,
        "optimistic_information_gain_per_observation_is_secondary_priority": True,
        "current_entropy_is_tertiary_priority": True,
        "projection_is_reachability_not_expected_utility_or_causality": True,
        "legacy_plan_schema_preserved": True,
        "neutral_discovery_fallback_preserved": True,
        "source_count_active_support_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged": True,
        "cache_or_cross_task_state_used": False,
        "bindings_restored": True,
        "task_question_opaque_id_query_url_page_source_value_prediction_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingDecisionReachability
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingDecisionReachability)
    ):
        raise TypeError("V2.45.58 requires ordinal and reachability capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = planner.validate_receipt(
        capability.decision_reachability_receipt()
    )
    value = {
        **base,
        **{_name(name): int(receipt[name]) for name in PLANNER_COUNT_NAMES},
        "decision_reachability_receipt_consumed_validated_capability": True,
        "decision_reachability_additional_private_effects_known_zero": True,
        "decision_reachability_private_task_content_emitted": False,
        "decision_reachability_privileged_evaluator_content_read": False,
        "decision_reachability_projection_claims_expected_utility_or_causality": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in PLANNER_COUNT_FIELDS},
        "decision_reachability_receipt_consumed_validated_capability": False,
        "decision_reachability_additional_private_effects_known_zero": False,
        "decision_reachability_private_task_content_emitted": False,
        "decision_reachability_privileged_evaluator_content_read": False,
        "decision_reachability_projection_claims_expected_utility_or_causality": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.58 failure ordinal is invalid")
    return validate_total_row(_failure_unchecked(ordinal))


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
            for name in PLANNER_COUNT_FIELDS
        )
        or planner.validate_receipt(_receipt_from_row(copied))
        != _receipt_from_row(copied)
        or copied.get(
            "decision_reachability_receipt_consumed_validated_capability"
        )
        is not success
        or copied.get("decision_reachability_additional_private_effects_known_zero")
        is not success
        or copied.get("decision_reachability_private_task_content_emitted")
        is not False
        or copied.get("decision_reachability_privileged_evaluator_content_read")
        is not False
        or copied.get(
            "decision_reachability_projection_claims_expected_utility_or_causality"
        )
        is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.58 total reachability row drifted")
    return copied


TASK_FIELDS = (
    "decision_reachability_any_plan_tasks",
    "decision_reachability_no_reachable_plan_tasks",
    "decision_reachability_one_observation_plan_tasks",
    "decision_reachability_two_observation_plan_tasks",
    "decision_reachability_three_observation_plan_tasks",
    "decision_reachability_changed_legacy_choice_tasks",
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_decision_reachability_count_fields",
        "all_decision_reachability_success_rows_consumed_validated_capabilities",
        "all_decision_reachability_failure_rows_are_content_free_zero_projections",
        "decision_reachability_failure_rows_claim_zero_private_effects",
        "decision_reachability_private_task_content_emitted",
        "decision_reachability_privileged_evaluator_content_read",
        "decision_reachability_projection_claims_expected_utility_or_causality",
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
        raise ValueError("V2.45.58 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingDecisionReachability):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item.parent_capability())
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.58 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.58 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    counts = {
        name: sum(row[_name(name)] for row in successes)
        for name in PLANNER_COUNT_NAMES
    }
    task_values = {
        "decision_reachability_any_plan_tasks": sum(
            row[_name("one_observation_plan_calls")]
            + row[_name("two_observation_plan_calls")]
            + row[_name("three_observation_plan_calls")]
            > 0
            for row in successes
        ),
        "decision_reachability_no_reachable_plan_tasks": sum(
            row[_name("no_reachable_plan_calls")] > 0 for row in successes
        ),
        "decision_reachability_one_observation_plan_tasks": sum(
            row[_name("one_observation_plan_calls")] > 0 for row in successes
        ),
        "decision_reachability_two_observation_plan_tasks": sum(
            row[_name("two_observation_plan_calls")] > 0 for row in successes
        ),
        "decision_reachability_three_observation_plan_tasks": sum(
            row[_name("three_observation_plan_calls")] > 0 for row in successes
        ),
        "decision_reachability_changed_legacy_choice_tasks": sum(
            row[_name("legacy_entropy_choice_changed_calls")] > 0
            for row in successes
        ),
    }
    value = {
        **base,
        **task_values,
        "total_decision_reachability_count_fields": counts,
        "all_decision_reachability_success_rows_consumed_validated_capabilities": all(
            row["decision_reachability_receipt_consumed_validated_capability"]
            for row in successes
        ),
        "all_decision_reachability_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "decision_reachability_failure_rows_claim_zero_private_effects": False,
        "decision_reachability_private_task_content_emitted": False,
        "decision_reachability_privileged_evaluator_content_read": False,
        "decision_reachability_projection_claims_expected_utility_or_causality": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    counts = copied.get("total_decision_reachability_count_fields")
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
        or set(counts) != set(PLANNER_COUNT_NAMES)
        or any(
            isinstance(counts.get(name), bool)
            or not isinstance(counts.get(name), int)
            or counts[name] < 0
            for name in PLANNER_COUNT_NAMES
        )
        or counts["selection_calls"]
        != counts["no_reachable_plan_calls"]
        + counts["one_observation_plan_calls"]
        + counts["two_observation_plan_calls"]
        + counts["three_observation_plan_calls"]
        or counts["legacy_entropy_choice_changed_calls"]
        > counts["one_observation_plan_calls"]
        + counts["two_observation_plan_calls"]
        + counts["three_observation_plan_calls"]
        or (counts["no_reachable_plan_calls"] > 0)
        is not (copied["decision_reachability_no_reachable_plan_tasks"] > 0)
        or (counts["one_observation_plan_calls"] > 0)
        is not (copied["decision_reachability_one_observation_plan_tasks"] > 0)
        or (counts["two_observation_plan_calls"] > 0)
        is not (copied["decision_reachability_two_observation_plan_tasks"] > 0)
        or (counts["three_observation_plan_calls"] > 0)
        is not (copied["decision_reachability_three_observation_plan_tasks"] > 0)
        or (counts["legacy_entropy_choice_changed_calls"] > 0)
        is not (copied["decision_reachability_changed_legacy_choice_tasks"] > 0)
        or (
            counts["one_observation_plan_calls"]
            + counts["two_observation_plan_calls"]
            + counts["three_observation_plan_calls"]
            > 0
        )
        is not (copied["decision_reachability_any_plan_tasks"] > 0)
        or copied.get(
            "all_decision_reachability_success_rows_consumed_validated_capabilities"
        )
        is not True
        or copied.get(
            "all_decision_reachability_failure_rows_are_content_free_zero_projections"
        )
        is not True
        or copied.get(
            "decision_reachability_failure_rows_claim_zero_private_effects"
        )
        is not False
        or copied.get("decision_reachability_private_task_content_emitted")
        is not False
        or copied.get("decision_reachability_privileged_evaluator_content_read")
        is not False
        or copied.get(
            "decision_reachability_projection_claims_expected_utility_or_causality"
        )
        is not False
    ):
        raise ValueError("V2.45.58 total reachability aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "PLANNER_COUNT_FIELDS",
    "PLANNER_COUNT_NAMES",
    "POLICY_ID",
    "ROW_KEYS",
    "TASK_FIELDS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
