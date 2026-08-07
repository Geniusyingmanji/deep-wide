"""Trusted-child integration of the corrected V2.47.90 observer."""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from . import v24778_staged_fetch_fallback_runtime as base
from . import v24790_full_catalog_selected_target as selected


POLICY_ID = "v24790_full_catalog_selected_target_trusted_child_v1"
ROLE = "v24790_cross_tab_task_projection"
STATUSES = (
    "validated",
    "no_baseline_unknown_target",
    "private_catalog_absent",
    "base_runtime_failure",
    "selected_catalog_or_observer_failure",
)
PUBLIC_RESULT_KEYS = frozenset(
    {
        "artifact_version", "role", "policy_id", "opaque_id", "status",
        "base_result_valid", "selected_receipt_valid", "predictions",
        "prediction_sha256", "scheduler_receipt", "semantic_receipt",
        "selected_cross_tab_receipt", "private_catalog_present",
        "baseline_unknown_target_present", "base_runtime_executed_once",
        "base_result_validated_once_before_observer",
        "full_catalog_observed_without_single_target_rebuild",
        "predictions_equal_validated_base_result",
        "catalog_or_private_content_serialized_to_public_projection",
        "question_query_identity_field_value_url_host_page_or_private_content_hash_emitted",
        "additional_model_search_fetch_or_evaluator_effect",
        "positive_entropy_or_task_credit_assigned",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized", "result_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return base.payload_sha256(value)


def _projection(
    *, visible: Mapping[str, str], status: str,
    validated: Mapping[str, Any] | None,
    receipt: Mapping[str, Any] | None,
    base_executed: bool, private_catalog_present: bool,
    unknown_present: bool,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError("V2.47.90 terminal status drifted")
    base_valid = validated is not None
    receipt_valid = receipt is not None
    predictions = copy.deepcopy(dict(validated["predictions"])) if base_valid else {}
    hashes = copy.deepcopy(dict(validated["prediction_sha256"])) if base_valid else {}
    scheduler = copy.deepcopy(dict(validated["scheduler_receipt"])) if base_valid else None
    semantic = copy.deepcopy(dict(validated["semantic_receipt"])) if base_valid else None
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": status,
        "base_result_valid": base_valid,
        "selected_receipt_valid": receipt_valid,
        "predictions": predictions,
        "prediction_sha256": hashes,
        "scheduler_receipt": scheduler,
        "semantic_receipt": semantic,
        "selected_cross_tab_receipt": copy.deepcopy(dict(receipt)) if receipt_valid else None,
        "private_catalog_present": private_catalog_present,
        "baseline_unknown_target_present": unknown_present,
        "base_runtime_executed_once": base_executed,
        "base_result_validated_once_before_observer": base_valid,
        "full_catalog_observed_without_single_target_rebuild": receipt_valid,
        "predictions_equal_validated_base_result": base_valid,
        "catalog_or_private_content_serialized_to_public_projection": False,
        "question_query_identity_field_value_url_host_page_or_private_content_hash_emitted": False,
        "additional_model_search_fetch_or_evaluator_effect": 0,
        "positive_entropy_or_task_credit_assigned": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_sha256"] = payload_sha256(value)
    return validate_projection(value)


def run_v24790_task(
    task: Mapping[str, Any], *, model: Any, search: Any,
    limits: ScoreFirstLimits, monotonic: Callable[[], float],
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    try:
        validated = base.run_v24778_task(
            visible, model=model, search=search, limits=limits, monotonic=monotonic
        )
    except Exception:
        return _projection(
            visible=visible, status="base_runtime_failure", validated=None,
            receipt=None, base_executed=True, private_catalog_present=False,
            unknown_present=False,
        )
    catalog = validated.get("private_semantic_catalog")
    if catalog is None:
        return _projection(
            visible=visible, status="private_catalog_absent", validated=validated,
            receipt=None, base_executed=True, private_catalog_present=False,
            unknown_present=selected.select_first_unknown_target(
                str(validated["predictions"]["baseline"])
            ) is not None,
        )
    baseline = str(validated["predictions"]["baseline"])
    candidate = str(validated["predictions"]["staged_fallback_semantic"])
    unknown_present = selected.select_first_unknown_target(baseline) is not None
    if not unknown_present:
        return _projection(
            visible=visible, status="no_baseline_unknown_target", validated=validated,
            receipt=None, base_executed=True, private_catalog_present=True,
            unknown_present=False,
        )
    try:
        receipt = selected.build_selected_target_cross_tab(
            catalog, baseline, candidate
        )
        if receipt is None:
            raise ValueError("V2.47.90 selected receipt unexpectedly absent")
    except Exception:
        return _projection(
            visible=visible, status="selected_catalog_or_observer_failure",
            validated=validated, receipt=None, base_executed=True,
            private_catalog_present=True, unknown_present=True,
        )
    return _projection(
        visible=visible, status="validated", validated=validated,
        receipt=receipt, base_executed=True, private_catalog_present=True,
        unknown_present=True,
    )


def validate_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    status = copied.get("status")
    base_valid = copied.get("base_result_valid")
    receipt_valid = copied.get("selected_receipt_valid")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    receipt = copied.get("selected_cross_tab_receipt")
    if (
        set(copied) != PUBLIC_RESULT_KEYS
        or copied.get("artifact_version") != 1 or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID or status not in STATUSES
        or not isinstance(base_valid, bool) or not isinstance(receipt_valid, bool)
        or not isinstance(predictions, Mapping) or not isinstance(hashes, Mapping)
        or copied.get("base_runtime_executed_once") is not True
        or copied.get("catalog_or_private_content_serialized_to_public_projection") is not False
        or copied.get("question_query_identity_field_value_url_host_page_or_private_content_hash_emitted") is not False
        or copied.get("additional_model_search_fetch_or_evaluator_effect") != 0
        or copied.get("positive_entropy_or_task_credit_assigned") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.90 task projection drifted")
    if base_valid:
        if (
            set(predictions) != set(base.ARMS) or set(hashes) != set(base.ARMS)
            or any(hashes[arm] != hashlib.sha256(str(predictions[arm]).encode()).hexdigest() for arm in base.ARMS)
            or not isinstance(copied.get("scheduler_receipt"), Mapping)
            or not isinstance(copied.get("semantic_receipt"), Mapping)
            or copied.get("base_result_validated_once_before_observer") is not True
            or copied.get("predictions_equal_validated_base_result") is not True
        ):
            raise ValueError("V2.47.90 validated base projection drifted")
        base.validate_scheduler_receipt(copied["scheduler_receipt"])
        base.semantic.validate_semantic_receipt(copied["semantic_receipt"])
    elif (
        predictions or hashes or copied.get("scheduler_receipt") is not None
        or copied.get("semantic_receipt") is not None
        or copied.get("private_catalog_present") is not False
        or copied.get("baseline_unknown_target_present") is not False
        or copied.get("base_result_validated_once_before_observer") is not False
        or copied.get("predictions_equal_validated_base_result") is not False
    ):
        raise ValueError("V2.47.90 base failure projection drifted")
    if receipt_valid:
        if status != "validated" or not isinstance(receipt, Mapping):
            raise ValueError("V2.47.90 valid selected receipt status drifted")
        selected.validate_receipt(receipt)
    elif receipt is not None or status == "validated":
        raise ValueError("V2.47.90 absent selected receipt drifted")
    if (
        (status == "validated" and (not base_valid or not receipt_valid or not copied["private_catalog_present"] or not copied["baseline_unknown_target_present"] or not copied["full_catalog_observed_without_single_target_rebuild"]))
        or (status == "no_baseline_unknown_target" and (not base_valid or receipt_valid or not copied["private_catalog_present"] or copied["baseline_unknown_target_present"] or copied["full_catalog_observed_without_single_target_rebuild"]))
        or (status == "private_catalog_absent" and (not base_valid or receipt_valid or copied["private_catalog_present"] or copied["full_catalog_observed_without_single_target_rebuild"]))
        or (status == "base_runtime_failure" and (base_valid or receipt_valid))
        or (status == "selected_catalog_or_observer_failure" and (not base_valid or receipt_valid or not copied["private_catalog_present"] or not copied["baseline_unknown_target_present"] or copied["full_catalog_observed_without_single_target_rebuild"]))
    ):
        raise ValueError("V2.47.90 terminal status semantics drifted")
    return copied


__all__ = ["POLICY_ID", "PUBLIC_RESULT_KEYS", "ROLE", "STATUSES", "run_v24790_task", "validate_projection"]
