"""Behavior-preserving checkpoint for the V2.48.57 legacy task outcome.

The caller first obtains an ``IntegratedExact220TaskOutcome`` from the frozen
V2.48.57 production chain.  This module validates all parent cross-artifacts
and seals that in-memory outcome before the legacy task envelope is built.
The clean path returns the ordinary legacy envelope byte-for-byte.  If and
only if envelope build or validation then fails, an independent recovery
envelope preserves the already validated prediction, cost, and receipts.

There is no provider, search, fetch, network, filesystem, process, evaluator,
benchmark-launch, or signed-credit capability in this module.  It is
build-only until a separate fresh/disjoint external protocol is authorized.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from typing import Any

from . import v24630_exact220_task_integration as parent
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25286_legacy_outcome_checkpoint_v1"
CHECKPOINT_ROLE = "v25286_validated_legacy_outcome_checkpoint"
RECOVERY_ROLE = "v25286_legacy_outcome_checkpoint_recovery_envelope"
RECEIPT_ROLE = "v25286_content_free_legacy_outcome_checkpoint_receipt"
ARM = "baseline"
RECOVERABLE_STAGES = (
    "legacy_envelope_build",
    "legacy_envelope_validate",
)


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _outcome_mapping(
    outcome: parent.IntegratedExact220TaskOutcome,
) -> dict[str, Any]:
    if not isinstance(outcome, parent.IntegratedExact220TaskOutcome):
        raise TypeError("V2.52.86 expected an integrated legacy outcome")
    parent.validate_cross_artifacts(
        outcome.result,
        arm=ARM,
        model_slot_receipt=outcome.model_slot_receipt,
        transport_health=outcome.transport_health,
        search_single_shot_receipt=outcome.search_single_shot_receipt,
        citation_title_backfill_receipt=outcome.citation_title_backfill_receipt,
        expected_cap=int(outcome.model_slot_receipt.get("slot_cap", -1)),
    )
    return {
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
        "citation_title_backfill_receipt": copy.deepcopy(
            outcome.citation_title_backfill_receipt
        ),
    }


def _outcome_from_mapping(
    value: Mapping[str, Any],
) -> parent.IntegratedExact220TaskOutcome:
    if not isinstance(value, Mapping) or set(value) != {
        "result",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "citation_title_backfill_receipt",
    }:
        raise ValueError("V2.52.86 checkpoint outcome schema drifted")
    outcome = parent.IntegratedExact220TaskOutcome(
        copy.deepcopy(value["result"]),
        copy.deepcopy(value["model_slot_receipt"]),
        copy.deepcopy(value["transport_health"]),
        copy.deepcopy(value["search_single_shot_receipt"]),
        copy.deepcopy(value["citation_title_backfill_receipt"]),
    )
    _outcome_mapping(outcome)
    return outcome


def build_checkpoint(
    outcome: parent.IntegratedExact220TaskOutcome,
) -> dict[str, Any]:
    mapped = _outcome_mapping(outcome)
    result = mapped["result"]
    prediction = result.get("prediction")
    cost = result.get("cost")
    if (
        not isinstance(prediction, str)
        or not prediction
        or not isinstance(cost, Mapping)
    ):
        raise ValueError("V2.52.86 parent prediction/cost is unavailable")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CHECKPOINT_ROLE,
        "policy_id": POLICY_ID,
        "arm": ARM,
        "opaque_id": result["opaque_id"],
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "cost": copy.deepcopy(cost),
        "validated_outcome": mapped,
        "validated_outcome_payload_sha256": payload_sha256(mapped),
        "created_after_parent_cross_artifact_validation": True,
        "created_before_legacy_envelope_build": True,
        "normal_path_prediction_cost_effect_and_receipts_unchanged": True,
        "contains_same_forward_private_task_content": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "external_forward_evaluator_or_benchmark_authorized": False,
    }
    value["checkpoint_payload_sha256"] = payload_sha256(value)
    return validate_checkpoint(value)


def validate_checkpoint(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("checkpoint_payload_sha256", None)
    prediction = copied.get("prediction")
    mapped = copied.get("validated_outcome")
    cost = copied.get("cost")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "arm",
            "opaque_id",
            "prediction",
            "prediction_sha256",
            "cost",
            "validated_outcome",
            "validated_outcome_payload_sha256",
            "created_after_parent_cross_artifact_validation",
            "created_before_legacy_envelope_build",
            "normal_path_prediction_cost_effect_and_receipts_unchanged",
            "contains_same_forward_private_task_content",
            "private_task_content_emitted_to_public_aggregate",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "external_forward_evaluator_or_benchmark_authorized",
            "checkpoint_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CHECKPOINT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("arm") != ARM
        or not isinstance(prediction, str)
        or not prediction
        or copied.get("prediction_sha256")
        != hashlib.sha256(prediction.encode()).hexdigest()
        or not isinstance(cost, Mapping)
        or not isinstance(mapped, Mapping)
        or copied.get("validated_outcome_payload_sha256")
        != payload_sha256(mapped)
        or any(
            copied.get(name) is not True
            for name in (
                "created_after_parent_cross_artifact_validation",
                "created_before_legacy_envelope_build",
                "normal_path_prediction_cost_effect_and_receipts_unchanged",
                "contains_same_forward_private_task_content",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "private_task_content_emitted_to_public_aggregate",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "external_forward_evaluator_or_benchmark_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.86 legacy outcome checkpoint drifted")
    outcome = _outcome_from_mapping(mapped)
    if (
        copied.get("opaque_id") != outcome.result["opaque_id"]
        or prediction != outcome.result["prediction"]
        or dict(cost) != outcome.result["cost"]
    ):
        raise ValueError("V2.52.86 checkpoint outcome binding drifted")
    return copied


def _receipt(
    checkpoint: Mapping[str, Any],
    *,
    disposition: str,
    failure_stage: str | None,
    failure_type: str | None,
) -> dict[str, Any]:
    checked = validate_checkpoint(checkpoint)
    clean = disposition == "clean_legacy_envelope"
    recovered = disposition == "checkpoint_preserved_after_envelope_failure"
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "checkpoint_payload_sha256": checked["checkpoint_payload_sha256"],
        "recovery_disposition": disposition,
        "legacy_envelope_clean": clean,
        "recovery_envelope_created": recovered,
        "failure_stage": failure_stage,
        "failure_type": failure_type,
        "prediction_equal_checkpoint": True,
        "cost_equal_checkpoint": True,
        "parent_result_and_all_effect_receipts_equal_checkpoint": True,
        "additional_query_count": 0,
        "additional_fetch_count": 0,
        "additional_model_forward_count": 0,
        "additional_system_total_tokens": 0,
        "normal_path_returns_byte_identical_legacy_envelope": True,
        "recovery_discards_only_failed_auxiliary_envelope": True,
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "external_forward_evaluator_or_benchmark_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    disposition = copied.get("recovery_disposition")
    clean = disposition == "clean_legacy_envelope"
    recovered = disposition == "checkpoint_preserved_after_envelope_failure"
    zero_fields = (
        "additional_query_count",
        "additional_fetch_count",
        "additional_model_forward_count",
        "additional_system_total_tokens",
        "positive_signed_credit_count",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "checkpoint_payload_sha256",
            "recovery_disposition",
            "legacy_envelope_clean",
            "recovery_envelope_created",
            "failure_stage",
            "failure_type",
            "prediction_equal_checkpoint",
            "cost_equal_checkpoint",
            "parent_result_and_all_effect_receipts_equal_checkpoint",
            *zero_fields,
            "normal_path_returns_byte_identical_legacy_envelope",
            "recovery_discards_only_failed_auxiliary_envelope",
            "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "external_forward_evaluator_or_benchmark_authorized",
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("checkpoint_payload_sha256"), str)
        or len(copied["checkpoint_payload_sha256"]) != 64
        or disposition
        not in {
            "clean_legacy_envelope",
            "checkpoint_preserved_after_envelope_failure",
        }
        or copied.get("legacy_envelope_clean") is not clean
        or copied.get("recovery_envelope_created") is not recovered
        or clean
        and (
            copied.get("failure_stage") is not None
            or copied.get("failure_type") is not None
        )
        or recovered
        and (
            copied.get("failure_stage") not in RECOVERABLE_STAGES
            or not isinstance(copied.get("failure_type"), str)
            or not copied["failure_type"]
            or len(copied["failure_type"]) > 128
        )
        or any(
            copied.get(name) is not True
            for name in (
                "prediction_equal_checkpoint",
                "cost_equal_checkpoint",
                "parent_result_and_all_effect_receipts_equal_checkpoint",
                "normal_path_returns_byte_identical_legacy_envelope",
                "recovery_discards_only_failed_auxiliary_envelope",
            )
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] != 0
            for name in zero_fields
        )
        or any(
            copied.get(name) is not False
            for name in (
                "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "external_forward_evaluator_or_benchmark_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.86 content-free checkpoint receipt drifted")
    return copied


def _recovery_envelope(
    checkpoint: Mapping[str, Any],
    *,
    failure_stage: str,
    failure_type: str,
) -> dict[str, Any]:
    checked = validate_checkpoint(checkpoint)
    receipt = _receipt(
        checked,
        disposition="checkpoint_preserved_after_envelope_failure",
        failure_stage=failure_stage,
        failure_type=failure_type,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECOVERY_ROLE,
        "policy_id": POLICY_ID,
        "arm": ARM,
        "status": "terminal",
        "opaque_id": checked["opaque_id"],
        "prediction": checked["prediction"],
        "prediction_sha256": checked["prediction_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "outcome_checkpoint": copy.deepcopy(checked),
        "outcome_checkpoint_payload_sha256": checked[
            "checkpoint_payload_sha256"
        ],
        "content_free_checkpoint_receipt": receipt,
        "recovered_failure_stage": failure_stage,
        "recovered_failure_type": failure_type,
        "recovery_envelope_independent_of_failed_legacy_envelope": True,
        "private_task_content_present": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["recovery_payload_sha256"] = payload_sha256(value)
    return validate_recovery_envelope(value)


def validate_recovery_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("recovery_payload_sha256", None)
    checkpoint_raw = copied.get("outcome_checkpoint")
    receipt_raw = copied.get("content_free_checkpoint_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "arm",
            "status",
            "opaque_id",
            "prediction",
            "prediction_sha256",
            "cost",
            "outcome_checkpoint",
            "outcome_checkpoint_payload_sha256",
            "content_free_checkpoint_receipt",
            "recovered_failure_stage",
            "recovered_failure_type",
            "recovery_envelope_independent_of_failed_legacy_envelope",
            "private_task_content_present",
            "private_task_content_emitted_to_public_aggregate",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "recovery_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECOVERY_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("arm") != ARM
        or copied.get("status") != "terminal"
        or not isinstance(checkpoint_raw, Mapping)
        or not isinstance(receipt_raw, Mapping)
        or copied.get("recovered_failure_stage") not in RECOVERABLE_STAGES
        or not isinstance(copied.get("recovered_failure_type"), str)
        or not copied["recovered_failure_type"]
        or copied.get("recovery_envelope_independent_of_failed_legacy_envelope")
        is not True
        or copied.get("private_task_content_present") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "private_task_content_emitted_to_public_aggregate",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.86 recovery envelope drifted")
    checkpoint = validate_checkpoint(checkpoint_raw)
    receipt = validate_receipt(receipt_raw)
    if (
        copied.get("outcome_checkpoint_payload_sha256")
        != checkpoint["checkpoint_payload_sha256"]
        or receipt["checkpoint_payload_sha256"]
        != checkpoint["checkpoint_payload_sha256"]
        or copied.get("opaque_id") != checkpoint["opaque_id"]
        or copied.get("prediction") != checkpoint["prediction"]
        or copied.get("prediction_sha256") != checkpoint["prediction_sha256"]
        or copied.get("cost") != checkpoint["cost"]
        or copied.get("recovered_failure_stage") != receipt["failure_stage"]
        or copied.get("recovered_failure_type") != receipt["failure_type"]
        or receipt["recovery_envelope_created"] is not True
    ):
        raise ValueError("V2.52.86 recovery checkpoint binding drifted")
    return copied


def run_from_validated_outcome(
    outcome: parent.IntegratedExact220TaskOutcome,
) -> tuple[dict[str, Any], dict[str, Any]]:
    checkpoint = build_checkpoint(outcome)
    try:
        envelope = parent.build_envelope(outcome, arm=ARM)
    except BaseException as exc:
        failure_type = _safe_failure(exc)
        return _recovery_envelope(
            checkpoint,
            failure_stage="legacy_envelope_build",
            failure_type=failure_type,
        ), _receipt(
            checkpoint,
            disposition="checkpoint_preserved_after_envelope_failure",
            failure_stage="legacy_envelope_build",
            failure_type=failure_type,
        )
    try:
        checked = parent.validate_envelope(envelope)
    except BaseException as exc:
        failure_type = _safe_failure(exc)
        return _recovery_envelope(
            checkpoint,
            failure_stage="legacy_envelope_validate",
            failure_type=failure_type,
        ), _receipt(
            checkpoint,
            disposition="checkpoint_preserved_after_envelope_failure",
            failure_stage="legacy_envelope_validate",
            failure_type=failure_type,
        )
    receipt = _receipt(
        checkpoint,
        disposition="clean_legacy_envelope",
        failure_stage=None,
        failure_type=None,
    )
    if checked != envelope:
        raise ValueError("V2.52.86 legacy validator changed the clean envelope")
    return checked, receipt


__all__ = [
    "ARM",
    "CHECKPOINT_ROLE",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "RECOVERABLE_STAGES",
    "RECOVERY_ROLE",
    "build_checkpoint",
    "run_from_validated_outcome",
    "validate_checkpoint",
    "validate_receipt",
    "validate_recovery_envelope",
]
