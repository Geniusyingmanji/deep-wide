"""Task-level joint observability for alias acquisition and entropy gain.

The V2.45.45 public aggregate retained marginal task counts but not their joint
distribution.  This append-only receipt binds one validated V2.45.47 surface
receipt to the already validated targeted-stage transition and publishes exact
same-task co-occurrence indicators.  Co-occurrence is explicitly not a claim
that a particular lead caused an observation or information gain.

Credit semantics are unchanged from V2.45.33: the action must have a plan,
query/selection activity, a selected source, and a new observation before it
can receive the frozen targeted-stage information delta.  Decision credit
still additionally requires a safe output improvement and changed cell.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from . import v24457_adaptive_entropy_support as adaptive
from . import v24490_entropy_targeted_support_search as targeted
from . import v24524_alias_title_integration as alias_integration
from . import v24527_bounded_alias_title_parent as bounded_parent
from . import v24533_alias_acquisition_entropy_credit as predecessor_action
from . import v24547_alias_surface_observability as surface
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24548_alias_action_same_task_joint_observability_v1"
ROLE = "v24548_alias_action_joint_observability_receipt"
TARGET_COUNT_FIELDS = (
    "target_plan_count",
    "targeted_logical_query_count",
    "targeted_search_batch_count",
    "targeted_selected_source_count",
    "targeted_usable_page_count",
    "targeted_new_observation_count",
    "safe_change_count_before_targeted_search",
    "safe_change_count_after_targeted_search",
    "safe_change_improvement_count",
    "safe_change_regression_count",
    "candidate_changed_cell_count_after_targeted_search",
)
ACTION_COUNT_FIELDS = (
    "action_positive_information_gain_count",
    "action_positive_epistemic_credit_count",
    "action_positive_decision_credit_count",
    "action_decision_credit_regression_count",
)
JOINT_COUNT_FIELDS = (
    "acquisition_active_and_positive_information_gain_count",
    "acquisition_active_and_positive_epistemic_gain_count",
    "new_observation_and_alias_surface_hit_count",
    "new_observation_and_selected_alias_surface_hit_count",
    "selected_alias_surface_hit_and_positive_information_gain_count",
    "selected_alias_surface_hit_new_observation_and_positive_information_gain_count",
)
COUNT_FIELDS = (*TARGET_COUNT_FIELDS, *ACTION_COUNT_FIELDS, *JOINT_COUNT_FIELDS)
NUMBER_FIELDS = predecessor_action.NUMBER_FIELDS
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "surface_policy_id",
        "targeted_policy_id",
        "adaptive_parent_policy_id",
        "alias_surface_receipt",
        *COUNT_FIELDS,
        *NUMBER_FIELDS,
        "same_task_joint_counts_do_not_claim_lead_level_causality",
        "acquisition_action_eligibility_requires_plan_query_selection_and_new_observation",
        "action_credit_uses_frozen_targeted_stage_posterior_delta",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
        "query_text_used_to_establish_alias_hit",
        "alias_hint_itself_receives_vote_or_source_credit",
        "allocated_credit_used_for_same_run_routing_training_or_policy_update",
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.45.48 {label} is invalid")
    return value


def _number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.45.48 {label} is invalid")
    return float(value)


def _targeted_and_adaptive_receipts(
    alias_result: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    validated = copy.deepcopy(dict(alias_result))
    alias_integration.validate_alias_title_receipt(
        validated.get("alias_title_receipt", {})
    )
    record = validated["parent_result"]
    reserve = record["parent_result"]
    targeted_result = reserve["parent_result"]
    adaptive_result = targeted_result["parent_result"]
    target = targeted.validate_recovery_receipt(
        targeted_result["targeted_support_receipt"]
    )
    before = adaptive.validate_recovery_receipt(
        adaptive_result["adaptive_support_receipt"]
    )
    return validated, target, before


def validate_surface_activity(
    alias_result: Mapping[str, Any], surface_receipt: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    validated, target, before = _targeted_and_adaptive_receipts(alias_result)
    activity = surface.validate_receipt(surface_receipt)
    target_count = int(target["targeted_cell_count"])
    query_calls = int(activity["targeted_query_vector_calls"]) + int(
        activity["discovery_query_vector_calls"]
    )
    selections = int(activity["lead_selection_calls"])
    if (
        target_count not in {0, 1}
        or target_count == 1
        and (query_calls < 1 or selections < 1)
        or target_count == 0
        and (query_calls != 0 or selections != 0)
    ):
        raise RuntimeError("V2.45.48 alias surface activity/plan drifted")
    return validated, target, before, activity


def build_joint_receipt(
    alias_result: Mapping[str, Any], surface_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    _validated, target, before, activity = validate_surface_activity(
        alias_result, surface_receipt
    )
    pre_information = float(before["final_positive_information_gain_total_nats"])
    post_information = float(
        target["positive_information_gain_total_nats_after_targeted_search"]
    )
    pre_epistemic = float(before["final_epistemic_credit_total_nats"])
    post_epistemic = float(
        target["epistemic_credit_total_nats_after_targeted_search"]
    )
    pre_decision = float(before["final_decision_credit_total_nats"])
    post_decision = float(
        target["decision_credit_total_nats_after_targeted_search"]
    )
    information_gain = max(0.0, post_information - pre_information)
    information_regression = max(0.0, pre_information - post_information)
    epistemic_gain = max(0.0, post_epistemic - pre_epistemic)
    epistemic_regression = max(0.0, pre_epistemic - post_epistemic)
    decision_gain = max(0.0, post_decision - pre_decision)
    decision_regression = max(0.0, pre_decision - post_decision)
    target_count = int(target["targeted_cell_count"])
    safe_before = int(target["safe_change_count_before_targeted_search"])
    safe_after = int(target["safe_change_count_after_targeted_search"])
    safe_improvement = max(0, safe_after - safe_before)
    safe_regression = max(0, safe_before - safe_after)
    new_observations = int(target["targeted_new_observation_count"])
    candidate_changes = int(
        target["candidate_changed_cell_count_after_targeted_search"]
    )
    acquisition_active = (
        target_count == 1
        and int(activity["alias_seeded_query_vector_calls"]) > 0
        and int(activity["lead_selection_calls"]) > 0
        and int(activity["selected_lead_count"]) > 0
        and int(target["targeted_selected_source_count"]) > 0
    )
    credit_active = acquisition_active and new_observations > 0
    alias_hit = int(activity["alias_surface_hit_lead_count"]) > 0
    selected_alias_hit = (
        int(activity["selected_alias_surface_hit_lead_count"]) > 0
    )
    action_information = information_gain if credit_active else 0.0
    action_epistemic = epistemic_gain if credit_active else 0.0
    action_decision = (
        decision_gain
        if credit_active and safe_improvement > 0 and candidate_changes > 0
        else 0.0
    )
    action_decision_regression = decision_regression if credit_active else 0.0
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "surface_policy_id": surface.POLICY_ID,
        "targeted_policy_id": targeted.POLICY_ID,
        "adaptive_parent_policy_id": adaptive.POLICY_ID,
        "alias_surface_receipt": copy.deepcopy(activity),
        "target_plan_count": target_count,
        "targeted_logical_query_count": int(
            target["targeted_logical_query_count"]
        ),
        "targeted_search_batch_count": int(
            target["targeted_search_batch_count"]
        ),
        "targeted_selected_source_count": int(
            target["targeted_selected_source_count"]
        ),
        "targeted_usable_page_count": int(target["targeted_usable_page_count"]),
        "targeted_new_observation_count": new_observations,
        "safe_change_count_before_targeted_search": safe_before,
        "safe_change_count_after_targeted_search": safe_after,
        "safe_change_improvement_count": safe_improvement,
        "safe_change_regression_count": safe_regression,
        "candidate_changed_cell_count_after_targeted_search": candidate_changes,
        "action_positive_information_gain_count": int(action_information > 0),
        "action_positive_epistemic_credit_count": int(action_epistemic > 0),
        "action_positive_decision_credit_count": int(action_decision > 0),
        "action_decision_credit_regression_count": int(
            action_decision_regression > 0
        ),
        "acquisition_active_and_positive_information_gain_count": int(
            acquisition_active and information_gain > 0
        ),
        "acquisition_active_and_positive_epistemic_gain_count": int(
            acquisition_active and epistemic_gain > 0
        ),
        "new_observation_and_alias_surface_hit_count": int(
            new_observations > 0 and alias_hit
        ),
        "new_observation_and_selected_alias_surface_hit_count": int(
            new_observations > 0 and selected_alias_hit
        ),
        "selected_alias_surface_hit_and_positive_information_gain_count": int(
            selected_alias_hit and information_gain > 0
        ),
        "selected_alias_surface_hit_new_observation_and_positive_information_gain_count": int(
            selected_alias_hit and new_observations > 0 and information_gain > 0
        ),
        "information_gain_total_nats_before_targeted_search": pre_information,
        "information_gain_total_nats_after_targeted_search": post_information,
        "information_gain_gain_nats": information_gain,
        "information_gain_regression_nats": information_regression,
        "epistemic_credit_total_nats_before_targeted_search": pre_epistemic,
        "epistemic_credit_total_nats_after_targeted_search": post_epistemic,
        "epistemic_credit_gain_nats": epistemic_gain,
        "epistemic_credit_regression_nats": epistemic_regression,
        "decision_credit_total_nats_before_targeted_search": pre_decision,
        "decision_credit_total_nats_after_targeted_search": post_decision,
        "decision_credit_gain_nats": decision_gain,
        "decision_credit_regression_nats": decision_regression,
        "action_information_credit_nats": action_information,
        "action_epistemic_credit_nats": action_epistemic,
        "action_decision_credit_nats": action_decision,
        "action_decision_credit_regression_nats": action_decision_regression,
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
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_joint_receipt(value)


def validate_joint_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    activity = surface.validate_receipt(copied.get("alias_surface_receipt", {}))
    acquisition_active = (
        copied.get("target_plan_count") == 1
        and activity["alias_seeded_query_vector_calls"] > 0
        and activity["lead_selection_calls"] > 0
        and activity["selected_lead_count"] > 0
        and copied.get("targeted_selected_source_count", 0) > 0
    )
    credit_active = (
        acquisition_active and copied.get("targeted_new_observation_count", 0) > 0
    )
    alias_hit = activity["alias_surface_hit_lead_count"] > 0
    selected_alias_hit = activity["selected_alias_surface_hit_lead_count"] > 0
    info_gain = float(copied.get("information_gain_gain_nats", -1))
    epistemic_gain = float(copied.get("epistemic_credit_gain_nats", -1))
    true_fields = (
        "same_task_joint_counts_do_not_claim_lead_level_causality",
        "acquisition_action_eligibility_requires_plan_query_selection_and_new_observation",
        "action_credit_uses_frozen_targeted_stage_posterior_delta",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
    )
    false_fields = (
        "query_text_used_to_establish_alias_hit",
        "alias_hint_itself_receives_vote_or_source_credit",
        "allocated_credit_used_for_same_run_routing_training_or_policy_update",
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("surface_policy_id") != surface.POLICY_ID
        or copied.get("targeted_policy_id") != targeted.POLICY_ID
        or copied.get("adaptive_parent_policy_id") != adaptive.POLICY_ID
        or any(_count(copied.get(name), name) < 0 for name in COUNT_FIELDS)
        or any(copied[name] not in {0, 1} for name in ACTION_COUNT_FIELDS + JOINT_COUNT_FIELDS)
        or any(_number(copied.get(name), name) < 0 for name in NUMBER_FIELDS)
        or copied["target_plan_count"] not in {0, 1}
        or copied["targeted_logical_query_count"]
        != copied["target_plan_count"] * targeted.MAXIMUM_TARGETED_LOGICAL_QUERIES
        or copied["targeted_search_batch_count"] != copied["target_plan_count"]
        or copied["targeted_usable_page_count"]
        > copied["targeted_selected_source_count"]
        or copied["target_plan_count"] == 0
        and (
            activity["targeted_query_vector_calls"]
            + activity["discovery_query_vector_calls"]
            + activity["lead_selection_calls"]
            != 0
        )
        or copied["target_plan_count"] == 1
        and (
            activity["targeted_query_vector_calls"]
            + activity["discovery_query_vector_calls"]
            < 1
            or activity["lead_selection_calls"] < 1
        )
        or copied["safe_change_improvement_count"]
        != max(
            0,
            copied["safe_change_count_after_targeted_search"]
            - copied["safe_change_count_before_targeted_search"],
        )
        or copied["safe_change_regression_count"]
        != max(
            0,
            copied["safe_change_count_before_targeted_search"]
            - copied["safe_change_count_after_targeted_search"],
        )
        or not math.isclose(
            copied["information_gain_gain_nats"],
            max(
                0.0,
                copied["information_gain_total_nats_after_targeted_search"]
                - copied["information_gain_total_nats_before_targeted_search"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["information_gain_regression_nats"],
            max(
                0.0,
                copied["information_gain_total_nats_before_targeted_search"]
                - copied["information_gain_total_nats_after_targeted_search"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["epistemic_credit_gain_nats"],
            max(
                0.0,
                copied["epistemic_credit_total_nats_after_targeted_search"]
                - copied["epistemic_credit_total_nats_before_targeted_search"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["epistemic_credit_regression_nats"],
            max(
                0.0,
                copied["epistemic_credit_total_nats_before_targeted_search"]
                - copied["epistemic_credit_total_nats_after_targeted_search"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["decision_credit_gain_nats"],
            max(
                0.0,
                copied["decision_credit_total_nats_after_targeted_search"]
                - copied["decision_credit_total_nats_before_targeted_search"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["decision_credit_regression_nats"],
            max(
                0.0,
                copied["decision_credit_total_nats_before_targeted_search"]
                - copied["decision_credit_total_nats_after_targeted_search"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["action_information_credit_nats"],
            info_gain if credit_active else 0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["action_epistemic_credit_nats"],
            epistemic_gain if credit_active else 0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["action_decision_credit_nats"],
            (
                copied["decision_credit_gain_nats"]
                if credit_active
                and copied["safe_change_improvement_count"] > 0
                and copied["candidate_changed_cell_count_after_targeted_search"] > 0
                else 0.0
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["action_decision_credit_regression_nats"],
            copied["decision_credit_regression_nats"] if credit_active else 0.0,
            abs_tol=1e-12,
        )
        or copied["action_positive_information_gain_count"]
        != int(copied["action_information_credit_nats"] > 0)
        or copied["action_positive_epistemic_credit_count"]
        != int(copied["action_epistemic_credit_nats"] > 0)
        or copied["action_positive_decision_credit_count"]
        != int(copied["action_decision_credit_nats"] > 0)
        or copied["action_decision_credit_regression_count"]
        != int(copied["action_decision_credit_regression_nats"] > 0)
        or copied["action_decision_credit_nats"]
        > copied["action_epistemic_credit_nats"] + 1e-12
        or copied["acquisition_active_and_positive_information_gain_count"]
        != int(acquisition_active and info_gain > 0)
        or copied["acquisition_active_and_positive_epistemic_gain_count"]
        != int(acquisition_active and epistemic_gain > 0)
        or copied["new_observation_and_alias_surface_hit_count"]
        != int(copied["targeted_new_observation_count"] > 0 and alias_hit)
        or copied["new_observation_and_selected_alias_surface_hit_count"]
        != int(
            copied["targeted_new_observation_count"] > 0 and selected_alias_hit
        )
        or copied["selected_alias_surface_hit_and_positive_information_gain_count"]
        != int(selected_alias_hit and info_gain > 0)
        or copied[
            "selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
        ]
        != int(
            selected_alias_hit
            and copied["targeted_new_observation_count"] > 0
            and info_gain > 0
        )
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.48 joint observability receipt drifted")
    return copied


def run_alias_surface_worker_with_receipt(
    *args: Any, **kwargs: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    acquisition = surface.AliasSurfaceObservability()
    with acquisition:
        result = bounded_parent.run_alias_title_worker(*args, **kwargs)
    receipt = build_joint_receipt(result, acquisition.content_free_receipt())
    return result, receipt


def run_alias_surface_worker(*args: Any, **kwargs: Any) -> dict[str, Any]:
    result, _receipt = run_alias_surface_worker_with_receipt(*args, **kwargs)
    return result


__all__ = [
    "ACTION_COUNT_FIELDS",
    "COUNT_FIELDS",
    "JOINT_COUNT_FIELDS",
    "NUMBER_FIELDS",
    "POLICY_ID",
    "ROLE",
    "TARGET_COUNT_FIELDS",
    "build_joint_receipt",
    "run_alias_surface_worker",
    "run_alias_surface_worker_with_receipt",
    "validate_joint_receipt",
    "validate_surface_activity",
]
