"""Capability-only total projection for alias/action joint observability."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24526_total_alias_title_projection as parent
from . import v24529_alias_seeded_target_acquisition as predecessor
from . import v24547_alias_surface_observability as surface
from . import v24548_alias_action_joint_observability as joint
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24549_proof_carrying_alias_joint import (
    ValidatedProofCarryingAliasJoint,
)


POLICY_ID = "v24550_capability_only_total_alias_action_joint_projection_v1"
SURFACE_PREFIX = "alias_surface_"
JOINT_PREFIX = "alias_joint_"
SURFACE_COUNT_FIELDS = tuple(
    f"{SURFACE_PREFIX}{name}" for name in surface.COUNT_FIELDS
)
JOINT_COUNT_FIELDS = tuple(f"{JOINT_PREFIX}{name}" for name in joint.COUNT_FIELDS)
JOINT_NUMBER_FIELDS = tuple(f"{JOINT_PREFIX}{name}" for name in joint.NUMBER_FIELDS)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *SURFACE_COUNT_FIELDS,
        *JOINT_COUNT_FIELDS,
        *JOINT_NUMBER_FIELDS,
        "alias_joint_receipt_consumed_validated_capability",
        "alias_joint_private_effects_known_zero",
        "alias_joint_private_task_content_emitted",
        "alias_joint_privileged_evaluator_content_read",
        "alias_joint_same_task_counts_claim_lead_level_causality",
    }
)


def _surface_name(name: str) -> str:
    return f"{SURFACE_PREFIX}{name}"


def _joint_name(name: str) -> str:
    return f"{JOINT_PREFIX}{name}"


def _surface_receipt_from_row(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": surface.POLICY_ID,
        "predecessor_policy_id": predecessor.POLICY_ID,
        "binding_count": surface.EXPECTED_BINDING_COUNT,
        **{name: int(value[_surface_name(name)]) for name in surface.COUNT_FIELDS},
        "logical_queries_per_plan_unchanged": True,
        "search_batches_per_plan_unchanged": True,
        "maximum_fetches_per_plan_unchanged": True,
        "alias_derived_only_from_visible_row_text": True,
        "lead_priority_uses_visible_title_and_normalized_url_only": True,
        "normalized_url_surface_excludes_query_fragment_userinfo_and_port": True,
        "query_text_used_to_establish_alias_hit": False,
        "query_only_alias_surface_receives_ranking_priority": False,
        "alias_hint_receives_vote_or_source_entropy_or_decision_credit": False,
        "final_cross_row_identity_relation_year_source_posterior_margin_leave_one_out_and_safe_change_rules_unchanged": True,
        "cache_or_cross_task_state_used": False,
        "bindings_restored": True,
        "task_question_opaque_id_query_url_page_prediction_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


def _joint_receipt_from_row(value: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "artifact_version": 1,
        "role": joint.ROLE,
        "policy_id": joint.POLICY_ID,
        "surface_policy_id": surface.POLICY_ID,
        "targeted_policy_id": joint.targeted.POLICY_ID,
        "adaptive_parent_policy_id": joint.adaptive.POLICY_ID,
        "alias_surface_receipt": _surface_receipt_from_row(value),
        **{name: int(value[_joint_name(name)]) for name in joint.COUNT_FIELDS},
        **{
            name: float(value[_joint_name(name)])
            for name in joint.NUMBER_FIELDS
        },
        "same_task_joint_counts_do_not_claim_lead_level_causality": True,
        "acquisition_action_eligibility_requires_plan_query_selection_and_new_observation": True,
        "action_credit_uses_frozen_targeted_stage_posterior_delta": True,
        "source_credit_uses_normalized_leave_one_out_information_gain": True,
        "decision_credit_requires_safe_output_change": True,
        "query_text_used_to_establish_alias_hit": False,
        "alias_hint_itself_receives_vote_or_source_credit": False,
        "allocated_credit_used_for_same_run_routing_training_or_policy_update": False,
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return receipt


def task_projection(
    ordinal: int, capability: ValidatedProofCarryingAliasJoint
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingAliasJoint)
    ):
        raise TypeError("V2.45.50 requires ordinal and alias-joint capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = joint.validate_joint_receipt(
        capability.joint_observability_receipt()
    )
    if base["targeted_plan_present"] != receipt["target_plan_count"]:
        raise ValueError("V2.45.50 parent/joint plan drifted")
    activity = receipt["alias_surface_receipt"]
    value = {
        **base,
        **{
            _surface_name(name): int(activity[name])
            for name in surface.COUNT_FIELDS
        },
        **{
            _joint_name(name): int(receipt[name])
            for name in joint.COUNT_FIELDS
        },
        **{
            _joint_name(name): float(receipt[name])
            for name in joint.NUMBER_FIELDS
        },
        "alias_joint_receipt_consumed_validated_capability": True,
        "alias_joint_private_effects_known_zero": True,
        "alias_joint_private_task_content_emitted": False,
        "alias_joint_privileged_evaluator_content_read": False,
        "alias_joint_same_task_counts_claim_lead_level_causality": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in SURFACE_COUNT_FIELDS},
        **{name: 0 for name in JOINT_COUNT_FIELDS},
        **{name: 0.0 for name in JOINT_NUMBER_FIELDS},
        "alias_joint_receipt_consumed_validated_capability": False,
        "alias_joint_private_effects_known_zero": False,
        "alias_joint_private_task_content_emitted": False,
        "alias_joint_privileged_evaluator_content_read": False,
        "alias_joint_same_task_counts_claim_lead_level_causality": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.50 failure ordinal is invalid")
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
            for name in (*SURFACE_COUNT_FIELDS, *JOINT_COUNT_FIELDS)
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in JOINT_NUMBER_FIELDS
        )
        or base["targeted_plan_present"]
        != copied[_joint_name("target_plan_count")]
        or joint.validate_joint_receipt(_joint_receipt_from_row(copied))
        != _joint_receipt_from_row(copied)
        or copied.get("alias_joint_receipt_consumed_validated_capability")
        is not success
        or copied.get("alias_joint_private_effects_known_zero") is not success
        or copied.get("alias_joint_private_task_content_emitted") is not False
        or copied.get("alias_joint_privileged_evaluator_content_read") is not False
        or copied.get("alias_joint_same_task_counts_claim_lead_level_causality")
        is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.50 total alias-joint row drifted")
    return copied


TASK_FIELDS = (
    "alias_joint_plan_tasks",
    "alias_joint_activity_tasks",
    "alias_surface_hit_tasks",
    "selected_alias_surface_hit_tasks",
    "query_only_alias_surface_tasks",
    "alias_joint_new_observation_tasks",
    "alias_joint_raw_positive_information_gain_tasks",
    "alias_joint_action_positive_information_credit_tasks",
    "alias_joint_action_positive_epistemic_credit_tasks",
    "alias_joint_action_positive_decision_credit_tasks",
    "alias_joint_safe_change_improvement_tasks",
    "alias_joint_safe_change_regression_tasks",
    "alias_joint_decision_credit_regression_tasks",
    *tuple(f"{name}_tasks" for name in joint.JOINT_COUNT_FIELDS),
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_alias_surface_count_fields",
        "total_alias_joint_count_fields",
        "total_alias_joint_number_fields",
        "all_alias_joint_success_rows_consumed_validated_capabilities",
        "all_alias_joint_failure_rows_are_content_free_zero_projections",
        "alias_joint_failure_rows_claim_zero_private_effects",
        "alias_joint_private_task_content_emitted",
        "alias_joint_privileged_evaluator_content_read",
        "alias_joint_same_task_counts_claim_lead_level_causality",
    }
)


def aggregate_projections(
    values: Sequence[ValidatedProofCarryingAliasJoint | Mapping[str, Any]],
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
        raise ValueError("V2.45.50 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingAliasJoint):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item.parent_capability())
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.50 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.50 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    surface_counts = {
        name: sum(row[_surface_name(name)] for row in successes)
        for name in surface.COUNT_FIELDS
    }
    joint_counts = {
        name: sum(row[_joint_name(name)] for row in successes)
        for name in joint.COUNT_FIELDS
    }
    joint_numbers = {
        name: sum(row[_joint_name(name)] for row in successes)
        for name in joint.NUMBER_FIELDS
    }
    task_values = {
        "alias_joint_plan_tasks": sum(
            row[_joint_name("target_plan_count")] > 0 for row in successes
        ),
        "alias_joint_activity_tasks": sum(
            row[_surface_name("alias_seeded_query_vector_calls")] > 0
            and row[_surface_name("lead_selection_calls")] > 0
            for row in successes
        ),
        "alias_surface_hit_tasks": sum(
            row[_surface_name("alias_surface_hit_lead_count")] > 0
            for row in successes
        ),
        "selected_alias_surface_hit_tasks": sum(
            row[_surface_name("selected_alias_surface_hit_lead_count")] > 0
            for row in successes
        ),
        "query_only_alias_surface_tasks": sum(
            row[_surface_name("query_only_alias_surface_lead_count")] > 0
            for row in successes
        ),
        "alias_joint_new_observation_tasks": sum(
            row[_joint_name("targeted_new_observation_count")] > 0
            for row in successes
        ),
        "alias_joint_raw_positive_information_gain_tasks": sum(
            row[_joint_name("information_gain_gain_nats")] > 0
            for row in successes
        ),
        "alias_joint_action_positive_information_credit_tasks": sum(
            row[_joint_name("action_information_credit_nats")] > 0
            for row in successes
        ),
        "alias_joint_action_positive_epistemic_credit_tasks": sum(
            row[_joint_name("action_epistemic_credit_nats")] > 0
            for row in successes
        ),
        "alias_joint_action_positive_decision_credit_tasks": sum(
            row[_joint_name("action_decision_credit_nats")] > 0
            for row in successes
        ),
        "alias_joint_safe_change_improvement_tasks": sum(
            row[_joint_name("safe_change_improvement_count")] > 0
            for row in successes
        ),
        "alias_joint_safe_change_regression_tasks": sum(
            row[_joint_name("safe_change_regression_count")] > 0
            for row in successes
        ),
        "alias_joint_decision_credit_regression_tasks": sum(
            row[_joint_name("action_decision_credit_regression_nats")] > 0
            for row in successes
        ),
        **{
            f"{name}_tasks": sum(
                row[_joint_name(name)] > 0 for row in successes
            )
            for name in joint.JOINT_COUNT_FIELDS
        },
    }
    value = {
        **base,
        **task_values,
        "total_alias_surface_count_fields": surface_counts,
        "total_alias_joint_count_fields": joint_counts,
        "total_alias_joint_number_fields": joint_numbers,
        "all_alias_joint_success_rows_consumed_validated_capabilities": all(
            row["alias_joint_receipt_consumed_validated_capability"]
            for row in successes
        ),
        "all_alias_joint_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "alias_joint_failure_rows_claim_zero_private_effects": False,
        "alias_joint_private_task_content_emitted": False,
        "alias_joint_privileged_evaluator_content_read": False,
        "alias_joint_same_task_counts_claim_lead_level_causality": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    surface_counts = copied.get("total_alias_surface_count_fields")
    joint_counts = copied.get("total_alias_joint_count_fields")
    joint_numbers = copied.get("total_alias_joint_number_fields")
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
        or not isinstance(surface_counts, Mapping)
        or set(surface_counts) != set(surface.COUNT_FIELDS)
        or any(
            isinstance(surface_counts.get(name), bool)
            or not isinstance(surface_counts.get(name), int)
            or surface_counts[name] < 0
            for name in surface.COUNT_FIELDS
        )
        or not isinstance(joint_counts, Mapping)
        or set(joint_counts) != set(joint.COUNT_FIELDS)
        or any(
            isinstance(joint_counts.get(name), bool)
            or not isinstance(joint_counts.get(name), int)
            or joint_counts[name] < 0
            for name in joint.COUNT_FIELDS
        )
        or not isinstance(joint_numbers, Mapping)
        or set(joint_numbers) != set(joint.NUMBER_FIELDS)
        or any(
            isinstance(joint_numbers.get(name), bool)
            or not isinstance(joint_numbers.get(name), (int, float))
            or not math.isfinite(float(joint_numbers[name]))
            or float(joint_numbers[name]) < 0
            for name in joint.NUMBER_FIELDS
        )
        or joint_counts["target_plan_count"] != copied["target_plan_tasks"]
        or joint_counts["target_plan_count"] != copied["alias_joint_plan_tasks"]
        or any(
            joint_counts[name] != copied[f"{name}_tasks"]
            for name in joint.JOINT_COUNT_FIELDS
        )
        or joint_counts["action_positive_information_gain_count"]
        != copied["alias_joint_action_positive_information_credit_tasks"]
        or joint_counts["action_positive_epistemic_credit_count"]
        != copied["alias_joint_action_positive_epistemic_credit_tasks"]
        or joint_counts["action_positive_decision_credit_count"]
        != copied["alias_joint_action_positive_decision_credit_tasks"]
        or joint_counts["action_decision_credit_regression_count"]
        != copied["alias_joint_decision_credit_regression_tasks"]
        or (surface_counts["alias_seeded_query_vector_calls"] > 0)
        is not (copied["alias_joint_activity_tasks"] > 0)
        or (surface_counts["alias_surface_hit_lead_count"] > 0)
        is not (copied["alias_surface_hit_tasks"] > 0)
        or (surface_counts["selected_alias_surface_hit_lead_count"] > 0)
        is not (copied["selected_alias_surface_hit_tasks"] > 0)
        or (surface_counts["query_only_alias_surface_lead_count"] > 0)
        is not (copied["query_only_alias_surface_tasks"] > 0)
        or (joint_counts["targeted_new_observation_count"] > 0)
        is not (copied["alias_joint_new_observation_tasks"] > 0)
        or (joint_numbers["information_gain_gain_nats"] > 0)
        is not (copied["alias_joint_raw_positive_information_gain_tasks"] > 0)
        or (joint_numbers["action_information_credit_nats"] > 0)
        is not (
            copied["alias_joint_action_positive_information_credit_tasks"] > 0
        )
        or (joint_numbers["action_epistemic_credit_nats"] > 0)
        is not (
            copied["alias_joint_action_positive_epistemic_credit_tasks"] > 0
        )
        or (joint_numbers["action_decision_credit_nats"] > 0)
        is not (copied["alias_joint_action_positive_decision_credit_tasks"] > 0)
        or (joint_counts["safe_change_improvement_count"] > 0)
        is not (copied["alias_joint_safe_change_improvement_tasks"] > 0)
        or (joint_counts["safe_change_regression_count"] > 0)
        is not (copied["alias_joint_safe_change_regression_tasks"] > 0)
        or joint_numbers["action_information_credit_nats"]
        > joint_numbers["information_gain_gain_nats"] + 1e-12
        or joint_numbers["action_epistemic_credit_nats"]
        > joint_numbers["epistemic_credit_gain_nats"] + 1e-12
        or joint_numbers["action_decision_credit_nats"]
        > joint_numbers["decision_credit_gain_nats"] + 1e-12
        or joint_numbers["action_decision_credit_nats"]
        > joint_numbers["action_epistemic_credit_nats"] + 1e-12
        or copied.get(
            "all_alias_joint_success_rows_consumed_validated_capabilities"
        )
        is not True
        or copied.get(
            "all_alias_joint_failure_rows_are_content_free_zero_projections"
        )
        is not True
        or copied.get("alias_joint_failure_rows_claim_zero_private_effects")
        is not False
        or copied.get("alias_joint_private_task_content_emitted") is not False
        or copied.get("alias_joint_privileged_evaluator_content_read") is not False
        or copied.get("alias_joint_same_task_counts_claim_lead_level_causality")
        is not False
    ):
        raise ValueError("V2.45.50 total alias-joint aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "JOINT_COUNT_FIELDS",
    "JOINT_NUMBER_FIELDS",
    "POLICY_ID",
    "ROW_KEYS",
    "SURFACE_COUNT_FIELDS",
    "TASK_FIELDS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
