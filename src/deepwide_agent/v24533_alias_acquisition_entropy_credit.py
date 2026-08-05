"""Content-free entropy credit for an alias-seeded acquisition action.

The acquisition policy changes retrieval queries and visible-title ranking,
but it must not receive credit merely for running.  This layer binds its
validated activity receipt to the already validated V2.44.90 targeted-stage
transition.  Action information/epistemic credit is positive only when that
stage adds an observation and the frozen posterior reports a positive gain.
Action decision credit additionally requires a new safe output change and a
changed candidate cell.

The receipt contains only fixed-vocabulary counts and nats.  It emits no task,
entity, query, URL, page, source, value, or prediction content and performs no
external effect.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from . import v24457_adaptive_entropy_support as adaptive
from . import v24490_entropy_targeted_support_search as targeted
from . import v24524_alias_title_integration as alias_integration
from . import v24529_alias_seeded_target_acquisition as acquisition
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24530_alias_seeded_bounded_worker import validate_acquisition_activity


POLICY_ID = "v24533_alias_seeded_acquisition_entropy_credit_v1"
ROLE = "v24533_alias_acquisition_entropy_credit_receipt"
COUNT_FIELDS = (
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
    "targeted_query_vector_calls",
    "discovery_query_vector_calls",
    "lead_selection_calls",
    "alias_seeded_query_vector_calls",
    "row_without_safe_alias_query_vector_calls",
    "visible_lead_count",
    "alias_title_hit_lead_count",
    "selected_lead_count",
    "selected_alias_title_hit_lead_count",
    "action_positive_information_gain_count",
    "action_positive_epistemic_credit_count",
    "action_positive_decision_credit_count",
    "action_decision_credit_regression_count",
)
NUMBER_FIELDS = (
    "information_gain_total_nats_before_targeted_search",
    "information_gain_total_nats_after_targeted_search",
    "information_gain_gain_nats",
    "information_gain_regression_nats",
    "epistemic_credit_total_nats_before_targeted_search",
    "epistemic_credit_total_nats_after_targeted_search",
    "epistemic_credit_gain_nats",
    "epistemic_credit_regression_nats",
    "decision_credit_total_nats_before_targeted_search",
    "decision_credit_total_nats_after_targeted_search",
    "decision_credit_gain_nats",
    "decision_credit_regression_nats",
    "action_information_credit_nats",
    "action_epistemic_credit_nats",
    "action_decision_credit_nats",
    "action_decision_credit_regression_nats",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "acquisition_policy_id",
        "targeted_policy_id",
        "adaptive_parent_policy_id",
        *COUNT_FIELDS,
        *NUMBER_FIELDS,
        "acquisition_action_eligibility_requires_plan_query_selection_and_new_observation",
        "action_credit_uses_frozen_targeted_stage_posterior_delta",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
        "query_replay_call_counts_are_diagnostic_not_effect_counts",
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
        raise ValueError(f"V2.45.33 {label} is invalid")
    return value


def _number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.45.33 {label} is invalid")
    return float(value)


def _targeted_and_adaptive_receipts(
    alias_result: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    validated_alias = copy.deepcopy(dict(alias_result))
    alias_integration.validate_alias_title_receipt(
        validated_alias.get("alias_title_receipt", {})
    )
    record = validated_alias["parent_result"]
    reserve = record["parent_result"]
    targeted_result = reserve["parent_result"]
    adaptive_result = targeted_result["parent_result"]
    targeted_receipt = targeted.validate_recovery_receipt(
        targeted_result["targeted_support_receipt"]
    )
    adaptive_receipt = adaptive.validate_recovery_receipt(
        adaptive_result["adaptive_support_receipt"]
    )
    return validated_alias, targeted_receipt, adaptive_receipt


def build_action_credit_receipt(
    alias_result: Mapping[str, Any], acquisition_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    validated_alias, target, before = _targeted_and_adaptive_receipts(
        alias_result
    )
    _, activity = validate_acquisition_activity(
        validated_alias, dict(acquisition_receipt)
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
    active = (
        target_count == 1
        and int(activity["alias_seeded_query_vector_calls"]) > 0
        and int(activity["lead_selection_calls"]) > 0
        and int(activity["selected_lead_count"]) > 0
        and int(target["targeted_selected_source_count"]) > 0
        and new_observations > 0
    )
    action_information = information_gain if active else 0.0
    action_epistemic = epistemic_gain if active else 0.0
    action_decision = (
        decision_gain
        if active and safe_improvement > 0 and candidate_changes > 0
        else 0.0
    )
    action_decision_regression = decision_regression if active else 0.0
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "acquisition_policy_id": acquisition.POLICY_ID,
        "targeted_policy_id": targeted.POLICY_ID,
        "adaptive_parent_policy_id": adaptive.POLICY_ID,
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
        **{name: int(activity[name]) for name in acquisition.RECEIPT_KEYS if name in COUNT_FIELDS},
        "action_positive_information_gain_count": int(action_information > 0),
        "action_positive_epistemic_credit_count": int(action_epistemic > 0),
        "action_positive_decision_credit_count": int(action_decision > 0),
        "action_decision_credit_regression_count": int(
            action_decision_regression > 0
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
        "acquisition_action_eligibility_requires_plan_query_selection_and_new_observation": True,
        "action_credit_uses_frozen_targeted_stage_posterior_delta": True,
        "source_credit_uses_normalized_leave_one_out_information_gain": True,
        "decision_credit_requires_safe_output_change": True,
        "query_replay_call_counts_are_diagnostic_not_effect_counts": True,
        "alias_hint_itself_receives_vote_or_source_credit": False,
        "allocated_credit_used_for_same_run_routing_training_or_policy_update": False,
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_action_credit_receipt(value)


def validate_action_credit_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_fields = (
        "acquisition_action_eligibility_requires_plan_query_selection_and_new_observation",
        "action_credit_uses_frozen_targeted_stage_posterior_delta",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
        "query_replay_call_counts_are_diagnostic_not_effect_counts",
    )
    false_fields = (
        "alias_hint_itself_receives_vote_or_source_credit",
        "allocated_credit_used_for_same_run_routing_training_or_policy_update",
        "task_question_opaque_id_entity_query_url_page_source_value_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    active = (
        copied.get("target_plan_count") == 1
        and copied.get("alias_seeded_query_vector_calls", 0) > 0
        and copied.get("lead_selection_calls", 0) > 0
        and copied.get("selected_lead_count", 0) > 0
        and copied.get("targeted_selected_source_count", 0) > 0
        and copied.get("targeted_new_observation_count", 0) > 0
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("acquisition_policy_id") != acquisition.POLICY_ID
        or copied.get("targeted_policy_id") != targeted.POLICY_ID
        or copied.get("adaptive_parent_policy_id") != adaptive.POLICY_ID
        or any(_count(copied.get(name), name) < 0 for name in COUNT_FIELDS)
        or any(_number(copied.get(name), name) < 0 for name in NUMBER_FIELDS)
        or copied["target_plan_count"] not in {0, 1}
        or copied["targeted_logical_query_count"]
        != copied["target_plan_count"] * targeted.MAXIMUM_TARGETED_LOGICAL_QUERIES
        or copied["targeted_search_batch_count"] != copied["target_plan_count"]
        or copied["targeted_usable_page_count"]
        > copied["targeted_selected_source_count"]
        or copied["alias_seeded_query_vector_calls"]
        + copied["row_without_safe_alias_query_vector_calls"]
        != copied["targeted_query_vector_calls"]
        + copied["discovery_query_vector_calls"]
        or copied["alias_title_hit_lead_count"] > copied["visible_lead_count"]
        or copied["selected_lead_count"] > copied["visible_lead_count"]
        or copied["selected_alias_title_hit_lead_count"]
        > copied["selected_lead_count"]
        or copied["target_plan_count"] == 0
        and (
            copied["targeted_query_vector_calls"]
            + copied["discovery_query_vector_calls"]
            + copied["lead_selection_calls"]
            != 0
        )
        or copied["target_plan_count"] == 1
        and (
            copied["targeted_query_vector_calls"]
            + copied["discovery_query_vector_calls"]
            < 1
            or copied["lead_selection_calls"] < 1
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
            copied["information_gain_gain_nats"] if active else 0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["action_epistemic_credit_nats"],
            copied["epistemic_credit_gain_nats"] if active else 0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["action_decision_credit_nats"],
            (
                copied["decision_credit_gain_nats"]
                if active
                and copied["safe_change_improvement_count"] > 0
                and copied["candidate_changed_cell_count_after_targeted_search"] > 0
                else 0.0
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["action_decision_credit_regression_nats"],
            copied["decision_credit_regression_nats"] if active else 0.0,
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
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.33 action-credit receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS",
    "NUMBER_FIELDS",
    "POLICY_ID",
    "ROLE",
    "build_action_credit_receipt",
    "validate_action_credit_receipt",
]
