"""Export-failure-tolerant same-response quote quality runtime.

V2.51.80 already treats a later candidate/final public-export failure as a
safe terminal condition: it publishes the independently validated quote-aware
production table for both parent arms.  V2.51.86 incorrectly rejected that
state after all effects completed.  This append-only successor accepts exactly
the two parent-valid outcomes for an active repair: final export completed, or
final export failed and the parent preserved safe production.

The quality candidate remains the first quote-aware production, never the
later revision.  The control remains the deterministic frozen-parent Unknown
fallback.  No model, search, fetch, network, evaluator, or credit effect is
added.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v24982_paired_production_runtime as paired
from . import v25180_quote_aware_production_runtime as effect_parent
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25188_export_failure_tolerant_same_response_runtime_v1"
ROLE = "v25188_export_failure_tolerant_same_response_runtime_result"
RECEIPT_ROLE = "v25188_content_free_export_failure_tolerant_same_response_receipt"
CONTROL_ARM = "same_raw_frozen_parent_fallback"
CANDIDATE_ARM = "same_raw_quote_aware_production"
ARMS = (CONTROL_ARM, CANDIDATE_ARM)
PHASES = effect_parent.PHASES


def _predictions(
    checked_parent: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    parent_receipt = effect_parent.validate_receipt(
        checked_parent["content_free_receipt"],
        parent_result=checked_parent["parent_result"],
    )
    repaired = parent_receipt["quote_aware_repair_applied_count"] == 1
    candidate = str(checked_parent["production_prediction"])
    if repaired:
        internal = str(checked_parent["parent_result"]["production_prediction"])
        columns = effect_parent._canonical_internal_columns(internal)
        control = paired._fallback(columns)
    else:
        control = candidate
    predictions = {CONTROL_ARM: control, CANDIDATE_ARM: candidate}
    content_free: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": effect_parent.ROLE,
        "parent_policy_id": effect_parent.POLICY_ID,
        "parent_result_payload_sha256": str(
            checked_parent["result_payload_sha256"]
        ),
        "quote_aware_repair_applied_count": int(repaired),
        "parent_public_export_completed_count": int(
            parent_receipt["public_export_completed_count"]
        ),
        "parent_public_export_failure_present": bool(
            parent_receipt["public_export_failure_present"]
        ),
        "parent_public_export_fallback_to_safe_production": bool(
            parent_receipt["public_export_fallback_to_completed_production"]
        ),
        "same_raw_counterfactual_active": repaired,
        "prediction_changed": control != candidate,
        "control_is_exact_frozen_parent_fallback_when_active": True,
        "candidate_is_parent_production_not_later_revision": True,
        "inactive_treatment_is_byte_identical": True,
        "active_parent_export_outcomes_are_completed_or_safe_production_fallback": True,
        "additional_model_search_fetch_or_network_effect": False,
        "contains_raw_response_cell_column_question_identity_url_page_value_prediction_or_semantic_hash": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    content_free["receipt_payload_sha256"] = payload_sha256(content_free)
    return predictions, validate_receipt(content_free)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    active = copied.get("same_raw_counterfactual_active")
    changed = copied.get("prediction_changed")
    completed = copied.get("parent_public_export_completed_count") == 1
    failed = copied.get("parent_public_export_failure_present") is True
    safe_fallback = (
        copied.get("parent_public_export_fallback_to_safe_production") is True
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "parent_role",
            "parent_policy_id",
            "parent_result_payload_sha256",
            "quote_aware_repair_applied_count",
            "parent_public_export_completed_count",
            "parent_public_export_failure_present",
            "parent_public_export_fallback_to_safe_production",
            "same_raw_counterfactual_active",
            "prediction_changed",
            "control_is_exact_frozen_parent_fallback_when_active",
            "candidate_is_parent_production_not_later_revision",
            "inactive_treatment_is_byte_identical",
            "active_parent_export_outcomes_are_completed_or_safe_production_fallback",
            "additional_model_search_fetch_or_network_effect",
            "contains_raw_response_cell_column_question_identity_url_page_value_prediction_or_semantic_hash",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != effect_parent.ROLE
        or copied.get("parent_policy_id") != effect_parent.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or copied.get("quote_aware_repair_applied_count") not in {0, 1}
        or copied.get("parent_public_export_completed_count") not in {0, 1}
        or not isinstance(
            copied.get("parent_public_export_failure_present"), bool
        )
        or not isinstance(
            copied.get("parent_public_export_fallback_to_safe_production"), bool
        )
        or not isinstance(active, bool)
        or not isinstance(changed, bool)
        or active is not (copied["quote_aware_repair_applied_count"] == 1)
        or changed is not active
        or active and completed is failed
        or active and failed is not safe_fallback
        or not active and (completed or failed or safe_fallback)
        or any(
            copied.get(name) is not True
            for name in (
                "control_is_exact_frozen_parent_fallback_when_active",
                "candidate_is_parent_production_not_later_revision",
                "inactive_treatment_is_byte_identical",
                "active_parent_export_outcomes_are_completed_or_safe_production_fallback",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "additional_model_search_fetch_or_network_effect",
                "contains_raw_response_cell_column_question_identity_url_page_value_prediction_or_semantic_hash",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.88 same-response receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    parent_result = effect_parent.validate_result(
        effect_parent.run_task(
            task,
            model=model,
            searches=searches,
            limits=limits,
            monotonic=monotonic,
        )
    )
    predictions, receipt = _predictions(parent_result)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": parent_result["opaque_id"],
        "status": "terminal",
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "prediction_kind": parent_result["prediction_kind"],
        "cost": copy.deepcopy(parent_result["cost"]),
        "parent_result": copy.deepcopy(parent_result),
        "parent_result_payload_sha256": parent_result["result_payload_sha256"],
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    parent_raw = copied.get("parent_result")
    receipt_raw = copied.get("content_free_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "status",
            "predictions",
            "prediction_sha256",
            "prediction_kind",
            "cost",
            "parent_result",
            "parent_result_payload_sha256",
            "content_free_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(ARMS)
        or any(
            not isinstance(predictions.get(arm), str) or not predictions[arm]
            for arm in ARMS
        )
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(ARMS)
        or any(
            hashes.get(arm)
            != hashlib.sha256(str(predictions[arm]).encode()).hexdigest()
            for arm in ARMS
        )
        or not isinstance(parent_raw, Mapping)
        or not isinstance(receipt_raw, Mapping)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.88 same-response result drifted")
    checked_parent = effect_parent.validate_result(parent_raw)
    expected_predictions, expected_receipt = _predictions(checked_parent)
    if (
        dict(predictions) != expected_predictions
        or dict(receipt_raw) != expected_receipt
        or copied["opaque_id"] != checked_parent["opaque_id"]
        or copied["prediction_kind"] != checked_parent["prediction_kind"]
        or copied["cost"] != checked_parent["cost"]
        or copied["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt_raw["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
    ):
        raise ValueError("V2.51.88 parent/counterfactual binding drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "run_task",
    "validate_receipt",
    "validate_result",
]
