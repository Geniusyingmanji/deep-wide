"""Visible-membership proposal followed by a pure list-atomic guard.

V2.54.25 localized two independent facts: the visible-membership constraint
removes out-of-table record proposals before the already-paid grounded call,
while the list-cardinality guard rejects observed harmful Authors edits.  This
wrapper composes both mechanisms without composing two forwards.  It invokes
V2.54.01 exactly once, recovers the shared base and deterministic changed-safe
candidate from that one private parent chain, and applies the V2.54.20 guard
locally.  Base, raw candidate, and guarded candidate therefore share all model,
search, fetch, page-byte, and sampling effects.

The module has no file, environment, process, network, model-construction,
evaluator, benchmark-label, mapping, gold, score, reward, credential, or
historical-result capability.  Runtime inputs remain visible ``opaque_id`` and
``question`` plus injected same-forward clients.  Entropy/information gain is
shadow-only and assigns no signed credit.  This build grants no launch.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25370_shared_synthesis_changed_safe_runtime as shared_parent
from . import v25389_hybrid_record_fallback_runtime as hybrid_parent
from . import v25395_visible_membership_synthesis_runtime as membership_parent
from . import v25401_grounded_record_membership_runtime as parent
from . import v25420_list_atomic_changed_safe_runtime as guard
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25426_membership_list_atomic_shared_runtime_v1"
ROLE = "v25426_membership_list_atomic_shared_runtime_result"
RECEIPT_ROLE = "v25426_content_free_membership_list_atomic_shared_receipt"
STAGE_RECEIPT_ROLE = "v25426_content_free_membership_list_atomic_shared_stage_receipt"
ARMS = (
    "shared_base_table",
    "membership_changed_safe_candidate",
    "membership_list_atomic_candidate",
)
BASE_ARM, RAW_ARM, GUARDED_ARM = ARMS
PHASES = parent.PHASES
ProductionOnlyStageError = parent.ProductionOnlyStageError


def _shared_predictions(
    parent_result: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    checked = parent.validate_result(parent_result)
    membership = membership_parent.validate_result(checked["private_parent_result"])
    hybrid = hybrid_parent.validate_result(membership["private_parent_result"])
    shared = shared_parent.validate_result(hybrid["private_parent_result"])
    base = str(shared["predictions"][shared_parent.CONTROL_ARM])
    raw = str(shared["predictions"][shared_parent.CANDIDATE_ARM])
    if (
        checked["prediction"] != raw
        or membership["prediction"] != raw
        or hybrid["prediction"] != raw
        or checked["prediction_sha256"] != hashlib.sha256(raw.encode()).hexdigest()
    ):
        raise ValueError("V2.54.26 shared parent prediction chain drifted")
    return checked, membership, hybrid, shared, base, raw


def _receipt(
    parent_result: Mapping[str, Any], observed: Mapping[str, Any]
) -> dict[str, Any]:
    checked, membership, _hybrid, _shared, base, raw = _shared_predictions(
        parent_result
    )
    membership_receipt = parent.validate_receipt(
        checked["grounded_record_membership_receipt"], parent_result=membership
    )
    guard_receipt = guard.validate_receipt(guard._receipt(observed))
    guarded = str(observed["prediction"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "visible_member_count": membership_receipt["visible_member_count"],
        "grounded_raw_record_count": membership_receipt[
            "grounded_raw_record_count"
        ],
        "grounded_raw_membership_match_count": membership_receipt[
            "grounded_raw_membership_match_count"
        ],
        "grounded_raw_membership_mismatch_count": membership_receipt[
            "grounded_raw_membership_mismatch_count"
        ],
        "grounded_raw_membership_unclassified_count": membership_receipt[
            "grounded_raw_membership_unclassified_count"
        ],
        "grounded_raw_membership_violation_count": membership_receipt[
            "grounded_raw_membership_violation_count"
        ],
        "changed_coordinate_count": guard_receipt["changed_coordinate_count"],
        "list_semantic_changed_coordinate_count": guard_receipt[
            "list_semantic_changed_coordinate_count"
        ],
        "retained_candidate_coordinate_count": guard_receipt[
            "retained_candidate_coordinate_count"
        ],
        "rejected_list_cardinality_decrease_count": guard_receipt[
            "rejected_list_cardinality_decrease_count"
        ],
        "positive_signed_credit_count": 0,
        "grounded_record_membership_constraint_applied": membership_receipt[
            "grounded_record_membership_constraint_applied"
        ],
        "all_grounded_raw_records_membership_aligned": membership_receipt[
            "all_grounded_raw_records_membership_aligned"
        ],
        "raw_candidate_changed": base != raw,
        "guard_changed_raw_candidate": raw != guarded,
        "guarded_candidate_changed_from_base": base != guarded,
        "grounded_record_membership_receipt": copy.deepcopy(membership_receipt),
        "list_atomic_guard_receipt": copy.deepcopy(guard_receipt),
        "one_v25401_parent_forward_only": True,
        "visible_membership_precedes_existing_grounded_record_call": True,
        "provider_record_violation_is_observed_not_postfiltered": True,
        "base_raw_and_guarded_share_all_provider_and_retrieval_effects": True,
        "list_guard_is_pure_local_and_zero_provider_effect": True,
        "query4_fetch14_model3_caps_unchanged": True,
        "contains_question_membership_identity_query_url_page_quote_field_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_wrapper": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value, parent_result=checked)


def validate_receipt(
    value: Mapping[str, Any], *, parent_result: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    membership = copied.get("grounded_record_membership_receipt")
    guarded = copied.get("list_atomic_guard_receipt")
    integer_fields = (
        "visible_member_count",
        "grounded_raw_record_count",
        "grounded_raw_membership_match_count",
        "grounded_raw_membership_mismatch_count",
        "grounded_raw_membership_unclassified_count",
        "grounded_raw_membership_violation_count",
        "changed_coordinate_count",
        "list_semantic_changed_coordinate_count",
        "retained_candidate_coordinate_count",
        "rejected_list_cardinality_decrease_count",
        "positive_signed_credit_count",
    )
    dynamic_flags = (
        "grounded_record_membership_constraint_applied",
        "all_grounded_raw_records_membership_aligned",
        "raw_candidate_changed",
        "guard_changed_raw_candidate",
        "guarded_candidate_changed_from_base",
    )
    true_flags = (
        "one_v25401_parent_forward_only",
        "visible_membership_precedes_existing_grounded_record_call",
        "provider_record_violation_is_observed_not_postfiltered",
        "base_raw_and_guarded_share_all_provider_and_retrieval_effects",
        "list_guard_is_pure_local_and_zero_provider_effect",
        "query4_fetch14_model3_caps_unchanged",
    )
    false_flags = (
        "contains_question_membership_identity_query_url_page_quote_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_wrapper",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *integer_fields,
        *dynamic_flags,
        "grounded_record_membership_receipt",
        "list_atomic_guard_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic_flags)
        or copied["positive_signed_credit_count"] != 0
        or not isinstance(membership, Mapping)
        or parent.validate_receipt(membership) != dict(membership)
        or not isinstance(guarded, Mapping)
        or guard.validate_receipt(guarded) != dict(guarded)
        or copied["visible_member_count"] != membership["visible_member_count"]
        or copied["grounded_raw_record_count"]
        != membership["grounded_raw_record_count"]
        or copied["grounded_raw_membership_match_count"]
        != membership["grounded_raw_membership_match_count"]
        or copied["grounded_raw_membership_mismatch_count"]
        != membership["grounded_raw_membership_mismatch_count"]
        or copied["grounded_raw_membership_unclassified_count"]
        != membership["grounded_raw_membership_unclassified_count"]
        or copied["grounded_raw_membership_violation_count"]
        != membership["grounded_raw_membership_violation_count"]
        or copied["grounded_record_membership_constraint_applied"]
        is not membership["grounded_record_membership_constraint_applied"]
        or copied["all_grounded_raw_records_membership_aligned"]
        is not membership["all_grounded_raw_records_membership_aligned"]
        or copied["changed_coordinate_count"] != guarded["changed_coordinate_count"]
        or copied["list_semantic_changed_coordinate_count"]
        != guarded["list_semantic_changed_coordinate_count"]
        or copied["retained_candidate_coordinate_count"]
        != guarded["retained_candidate_coordinate_count"]
        or copied["rejected_list_cardinality_decrease_count"]
        != guarded["rejected_list_cardinality_decrease_count"]
        or copied["guard_changed_raw_candidate"]
        is not guarded["guard_changed_candidate"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.26 combined membership/list receipt drifted")
    if parent_result is not None:
        checked, membership_result, _hybrid, _shared, base, raw = _shared_predictions(
            parent_result
        )
        expected_membership = parent.validate_receipt(
            checked["grounded_record_membership_receipt"],
            parent_result=membership_result,
        )
        observed = guard.apply_list_atomic_guard(
            base, raw, guard._visible_columns(base)
        )
        expected_guard = guard.validate_receipt(guard._receipt(observed))
        if (
            dict(membership) != expected_membership
            or dict(guarded) != expected_guard
            or copied["raw_candidate_changed"] is not (base != raw)
            or copied["guarded_candidate_changed_from_base"]
            is not (base != observed["prediction"])
        ):
            raise ValueError("V2.54.26 receipt/parent binding drifted")
    return copied


def _wrap_result(parent_result: Mapping[str, Any]) -> dict[str, Any]:
    checked, _membership, _hybrid, _shared, base, raw = _shared_predictions(
        parent_result
    )
    observed = guard.apply_list_atomic_guard(
        base, raw, guard._visible_columns(base)
    )
    guarded = str(observed["prediction"])
    receipt = _receipt(checked, observed)
    predictions = {
        BASE_ARM: base,
        RAW_ARM: raw,
        GUARDED_ARM: guarded,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": guarded,
        "prediction_sha256": hashlib.sha256(guarded.encode()).hexdigest(),
        "prediction_kind": checked["prediction_kind"],
        "predictions": predictions,
        "prediction_sha256_by_arm": {
            arm: hashlib.sha256(prediction.encode()).hexdigest()
            for arm, prediction in predictions.items()
        },
        "raw_candidate_changed": base != raw,
        "guarded_candidate_changed_from_base": base != guarded,
        "guard_changed_raw_candidate": raw != guarded,
        "combined_membership_list_atomic_receipt": copy.deepcopy(receipt),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked["result_payload_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_membership_list_atomic_candidate": True,
        "all_three_arms_share_one_v25401_parent_forward": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    parent_result = copied.get("private_parent_result")
    receipt = copied.get("combined_membership_list_atomic_receipt")
    if not isinstance(parent_result, Mapping) or not isinstance(receipt, Mapping):
        raise ValueError("V2.54.26 private parent or receipt is absent")
    expected = _wrap_result(parent_result)
    if copied != expected:
        raise ValueError("V2.54.26 result adapter drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(
        checked["combined_membership_list_atomic_receipt"],
        parent_result=checked["private_parent_result"],
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "combined_membership_list_atomic_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "one_parent_forward_and_pure_local_guard": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_stage_receipt(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    receipt = copied.get("combined_membership_list_atomic_receipt")
    stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "combined_membership_list_atomic_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        "one_parent_forward_and_pure_local_guard",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not False
        or copied.get("failure_stage") is not None
        or copied.get("failure_type") is not None
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(stage, Mapping)
        or parent.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or stage["outer_physical_budget_receipt"] != budget
        or not isinstance(copied.get("parent_runtime_result_payload_sha256"), str)
        or len(copied["parent_runtime_result_payload_sha256"]) != 64
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or copied.get("one_parent_forward_and_pure_local_guard") is not True
        or copied.get("query_fetch_model_token_context_and_wall_caps_unchanged")
        is not True
        or any(
            copied.get(name) is not False
            for name in (
                "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.26 combined stage receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    visible = score.validate_visible_task(task)
    parent_result, parent_stage = parent.run_task(
        visible,
        model=model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    checked = parent.validate_result(parent_result)
    result = validate_result(_wrap_result(checked))
    return result, _stage_receipt(result, parent_stage)


__all__ = [
    "ARMS",
    "BASE_ARM",
    "GUARDED_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RAW_ARM",
    "RECEIPT_ROLE",
    "ROLE",
    "STAGE_RECEIPT_ROLE",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
