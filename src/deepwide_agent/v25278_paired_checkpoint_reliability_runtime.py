"""Same-forward paired reliability projection for validated checkpoints.

One real V2.52.71 forward produces the control result and its sealed
production checkpoint.  If and only if that control is a clean terminal
checkpoint result, the candidate arm locally projects a fixed
``result_envelope_validate`` failure from the *same* checkpoint, cost, and
physical-budget receipt.  The projection performs no additional provider,
search, fetch, network, filesystem, process, evaluator, or benchmark effect.

This module is build-only.  A separate frozen protocol must authorize any
external population.  It assigns no entropy/information-gain credit.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25271_validated_production_checkpoint_runtime as parent
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25278_same_forward_paired_checkpoint_reliability_v1"
ROLE = "v25278_same_forward_paired_checkpoint_reliability_result"
RECEIPT_ROLE = "v25278_content_free_paired_checkpoint_reliability_receipt"
INJECTED_STAGE = "result_envelope_validate"
INJECTED_FAILURE_TYPE = "InjectedCheckpointReliabilityFault"
ELIGIBILITY_REASONS = (
    "clean_trusted_checkpoint",
    "control_has_no_trusted_checkpoint",
    "control_not_clean_checkpoint_result",
)


class InjectedCheckpointReliabilityFault(RuntimeError):
    """Fixed local post-checkpoint fault; never includes task content."""


def _eligibility(
    control: Mapping[str, Any], stage: Mapping[str, Any]
) -> tuple[bool, str]:
    checked = parent.validate_result(control)
    checked_stage = parent.validate_stage_receipt(stage)
    checkpoint = checked.get("production_checkpoint")
    if checkpoint is None:
        return False, "control_has_no_trusted_checkpoint"
    clean_disposition = (
        "clean_validated_production"
        if checkpoint["checkpoint_kind"] == "validated_model_output"
        else "clean_deterministic_fallback"
    )
    if (
        checked.get("role") != parent.ROLE
        or checked.get("parent_result") is None
        or checked["content_free_receipt"]["recovery_disposition"]
        != clean_disposition
        or checked_stage["failure_count"] != 0
        or any(
            checked_stage["stage_entered_counts"][name] != 1
            or checked_stage["stage_completed_counts"][name] != 1
            for name in parent.STAGES
        )
    ):
        return False, "control_not_clean_checkpoint_result"
    return True, "clean_trusted_checkpoint"


def _project_receipt(control: Mapping[str, Any]) -> dict[str, Any]:
    checked = parent.validate_result(control)
    checkpoint = parent.validate_checkpoint(checked["production_checkpoint"])
    receipt = copy.deepcopy(checked["content_free_receipt"])
    receipt["parent_result_retained"] = False
    receipt["recovery_disposition"] = (
        "validated_production_preserved_after_post_checkpoint_failure"
        if checkpoint["checkpoint_kind"] == "validated_model_output"
        else "deterministic_fallback_preserved_after_post_checkpoint_failure"
    )
    receipt["microstage_failure_count"] = 1
    receipt["post_checkpoint_recoverable_failure_present"] = True
    receipt.pop("receipt_payload_sha256")
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return parent.validate_receipt(receipt)


def _project_candidate(
    control: Mapping[str, Any],
    *,
    budget: cap.PhysicalEffectBudget,
) -> tuple[dict[str, Any], dict[str, Any]]:
    checked = parent.validate_result(control)
    checkpoint = parent.validate_checkpoint(checked["production_checkpoint"])
    observer = parent.MicrostageObserver(budget)
    for stage in parent.STAGES[:-1]:
        ok, _value = observer.attempt(stage, lambda: None)
        if not ok:
            raise RuntimeError("V2.52.78 local pre-injection projection failed")
    ok, _value = observer.attempt(
        INJECTED_STAGE,
        lambda: (_ for _ in ()).throw(InjectedCheckpointReliabilityFault()),
    )
    if ok or observer.failures[INJECTED_STAGE] != INJECTED_FAILURE_TYPE:
        raise RuntimeError("V2.52.78 fixed fault injection did not fire")
    receipt = _project_receipt(checked)
    disposition = receipt["recovery_disposition"]
    candidate = parent._build_recovery_result(
        visible={"opaque_id": checked["opaque_id"]},
        checkpoint=checkpoint,
        cost=checked["cost"],
        receipt=receipt,
        observer=observer,
    )
    candidate_stage = observer.receipt(
        checkpoint_kind=checkpoint["checkpoint_kind"],
        parent_result_retained=False,
        disposition=disposition,
    )
    return parent.validate_recovery_result(candidate), parent.validate_stage_receipt(
        candidate_stage
    )


def _paired_receipt(
    control: Mapping[str, Any],
    control_stage: Mapping[str, Any],
    candidate: Mapping[str, Any] | None,
    candidate_stage: Mapping[str, Any] | None,
    *,
    eligible: bool,
    reason: str,
) -> dict[str, Any]:
    checked = parent.validate_result(control)
    checked_stage = parent.validate_stage_receipt(control_stage)
    checkpoint = checked.get("production_checkpoint")
    candidate_checked = (
        None if candidate is None else parent.validate_recovery_result(candidate)
    )
    candidate_stage_checked = (
        None
        if candidate_stage is None
        else parent.validate_stage_receipt(candidate_stage)
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "shared_real_forward_count": 1,
        "paired_projection_eligible": bool(eligible),
        "eligibility_reason": reason,
        "checkpoint_present": checkpoint is not None,
        "checkpoint_kind": (
            None if checkpoint is None else checkpoint["checkpoint_kind"]
        ),
        "candidate_recovery_created": candidate_checked is not None,
        "candidate_injected_failure_stage": (
            INJECTED_STAGE if candidate_checked is not None else None
        ),
        "candidate_injected_failure_type": (
            INJECTED_FAILURE_TYPE if candidate_checked is not None else None
        ),
        "control_and_candidate_prediction_equal": bool(
            candidate_checked is not None
            and checked["prediction"] == candidate_checked["prediction"]
        ),
        "control_and_candidate_checkpoint_equal": bool(
            candidate_checked is not None
            and checked["production_checkpoint"]
            == candidate_checked["production_checkpoint"]
        ),
        "control_and_candidate_cost_equal": bool(
            candidate_checked is not None
            and checked["cost"] == candidate_checked["cost"]
        ),
        "control_and_candidate_physical_budget_receipt_equal": bool(
            candidate_stage_checked is not None
            and checked_stage["outer_physical_budget_receipt"]
            == candidate_stage_checked["outer_physical_budget_receipt"]
        ),
        "candidate_additional_query_count": 0,
        "candidate_additional_fetch_count": 0,
        "candidate_additional_model_forward_count": 0,
        "candidate_additional_system_total_tokens": 0,
        "same_forward_checkpoint_is_only_treatment_input": True,
        "candidate_projection_is_local_and_does_not_call_provider_search_fetch_or_network": True,
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
    eligible = copied.get("paired_projection_eligible") is True
    reason = copied.get("eligibility_reason")
    candidate_created = copied.get("candidate_recovery_created") is True
    equality_fields = (
        "control_and_candidate_prediction_equal",
        "control_and_candidate_checkpoint_equal",
        "control_and_candidate_cost_equal",
        "control_and_candidate_physical_budget_receipt_equal",
    )
    zero_fields = (
        "candidate_additional_query_count",
        "candidate_additional_fetch_count",
        "candidate_additional_model_forward_count",
        "candidate_additional_system_total_tokens",
        "positive_signed_credit_count",
    )
    true_flags = (
        "same_forward_checkpoint_is_only_treatment_input",
        "candidate_projection_is_local_and_does_not_call_provider_search_fetch_or_network",
    )
    false_flags = (
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "external_forward_evaluator_or_benchmark_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "shared_real_forward_count",
            "paired_projection_eligible",
            "eligibility_reason",
            "checkpoint_present",
            "checkpoint_kind",
            "candidate_recovery_created",
            "candidate_injected_failure_stage",
            "candidate_injected_failure_type",
            *equality_fields,
            *zero_fields,
            *true_flags,
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("shared_real_forward_count") != 1
        or not isinstance(copied.get("paired_projection_eligible"), bool)
        or reason not in ELIGIBILITY_REASONS
        or not isinstance(copied.get("checkpoint_present"), bool)
        or copied.get("checkpoint_kind") is not None
        and copied["checkpoint_kind"] not in parent.CHECKPOINT_KINDS
        or not isinstance(copied.get("candidate_recovery_created"), bool)
        or any(not isinstance(copied.get(name), bool) for name in equality_fields)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] != 0
            for name in zero_fields
        )
        or eligible is not (reason == "clean_trusted_checkpoint")
        or candidate_created is not eligible
        or eligible
        and (
            copied.get("checkpoint_present") is not True
            or copied.get("checkpoint_kind") not in parent.CHECKPOINT_KINDS
            or copied.get("candidate_injected_failure_stage") != INJECTED_STAGE
            or copied.get("candidate_injected_failure_type") != INJECTED_FAILURE_TYPE
            or any(copied[name] is not True for name in equality_fields)
        )
        or not eligible
        and (
            copied.get("candidate_injected_failure_stage") is not None
            or copied.get("candidate_injected_failure_type") is not None
            or any(copied[name] is not False for name in equality_fields)
        )
        or reason == "control_has_no_trusted_checkpoint"
        and (
            copied.get("checkpoint_present") is not False
            or copied.get("checkpoint_kind") is not None
        )
        or reason == "control_not_clean_checkpoint_result"
        and copied.get("checkpoint_present") is not True
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.78 paired checkpoint receipt drifted")
    return copied


def _build_result(
    *,
    control: Mapping[str, Any],
    control_stage: Mapping[str, Any],
    candidate: Mapping[str, Any] | None,
    candidate_stage: Mapping[str, Any] | None,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    checked_control = parent.validate_result(control)
    checked_control_stage = parent.validate_stage_receipt(control_stage)
    checked_candidate = (
        None if candidate is None else parent.validate_recovery_result(candidate)
    )
    checked_candidate_stage = (
        None
        if candidate_stage is None
        else parent.validate_stage_receipt(candidate_stage)
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked_control["opaque_id"],
        "status": "terminal",
        "control_result": copy.deepcopy(checked_control),
        "control_result_payload_sha256": checked_control["result_payload_sha256"],
        "control_stage_receipt": copy.deepcopy(checked_control_stage),
        "candidate_recovery_result": copy.deepcopy(checked_candidate),
        "candidate_recovery_result_payload_sha256": (
            None
            if checked_candidate is None
            else checked_candidate["result_payload_sha256"]
        ),
        "candidate_stage_receipt": copy.deepcopy(checked_candidate_stage),
        "content_free_paired_receipt": copy.deepcopy(validate_receipt(receipt)),
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
    control_raw = copied.get("control_result")
    control_stage_raw = copied.get("control_stage_receipt")
    candidate_raw = copied.get("candidate_recovery_result")
    candidate_stage_raw = copied.get("candidate_stage_receipt")
    receipt_raw = copied.get("content_free_paired_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "status",
            "control_result",
            "control_result_payload_sha256",
            "control_stage_receipt",
            "candidate_recovery_result",
            "candidate_recovery_result_payload_sha256",
            "candidate_stage_receipt",
            "content_free_paired_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(control_raw, Mapping)
        or not isinstance(control_stage_raw, Mapping)
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
        raise ValueError("V2.52.78 paired checkpoint result envelope drifted")
    control = parent.validate_result(control_raw)
    control_stage = parent.validate_stage_receipt(control_stage_raw)
    receipt = validate_receipt(receipt_raw)
    eligible, reason = _eligibility(control, control_stage)
    if (
        copied.get("opaque_id") != control["opaque_id"]
        or copied.get("control_result_payload_sha256")
        != control["result_payload_sha256"]
        or receipt["paired_projection_eligible"] is not eligible
        or receipt["eligibility_reason"] != reason
    ):
        raise ValueError("V2.52.78 control binding drifted")
    if eligible:
        if not isinstance(candidate_raw, Mapping) or not isinstance(
            candidate_stage_raw, Mapping
        ):
            raise ValueError("V2.52.78 eligible candidate is absent")
        candidate = parent.validate_recovery_result(candidate_raw)
        candidate_stage = parent.validate_stage_receipt(candidate_stage_raw)
        if (
            copied.get("candidate_recovery_result_payload_sha256")
            != candidate["result_payload_sha256"]
            or candidate["opaque_id"] != control["opaque_id"]
            or candidate["prediction"] != control["prediction"]
            or candidate["prediction_kind"] != control["prediction_kind"]
            or candidate["production_checkpoint"]
            != control["production_checkpoint"]
            or candidate["cost"] != control["cost"]
            or candidate["recovered_failure_stages"] != [INJECTED_STAGE]
            or candidate["recovered_failure_types"]
            != {INJECTED_STAGE: INJECTED_FAILURE_TYPE}
            or candidate_stage["stage_failure_types"][INJECTED_STAGE]
            != INJECTED_FAILURE_TYPE
            or candidate_stage["outer_physical_budget_receipt"]
            != control_stage["outer_physical_budget_receipt"]
        ):
            raise ValueError("V2.52.78 candidate binding drifted")
    elif (
        candidate_raw is not None
        or candidate_stage_raw is not None
        or copied.get("candidate_recovery_result_payload_sha256") is not None
    ):
        raise ValueError("V2.52.78 ineligible candidate must be absent")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    control, control_stage = parent.run_task(
        task,
        model=model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    checked_control = parent.validate_result(control)
    checked_control_stage = parent.validate_stage_receipt(control_stage)
    eligible, reason = _eligibility(checked_control, checked_control_stage)
    candidate: dict[str, Any] | None = None
    candidate_stage: dict[str, Any] | None = None
    if eligible:
        candidate, candidate_stage = _project_candidate(
            checked_control,
            budget=budget,
        )
    receipt = _paired_receipt(
        checked_control,
        checked_control_stage,
        candidate,
        candidate_stage,
        eligible=eligible,
        reason=reason,
    )
    return _build_result(
        control=checked_control,
        control_stage=checked_control_stage,
        candidate=candidate,
        candidate_stage=candidate_stage,
        receipt=receipt,
    )


__all__ = [
    "ELIGIBILITY_REASONS",
    "INJECTED_FAILURE_TYPE",
    "INJECTED_STAGE",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "InjectedCheckpointReliabilityFault",
    "run_paired_task",
    "validate_receipt",
    "validate_result",
]
