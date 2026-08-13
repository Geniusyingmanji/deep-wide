"""Natural-event shared-prefix quality projection for checkpoint recovery.

The runtime invokes V2.52.71 exactly once.  A clean parent is projected as an
identity pair.  Only when that same real forward naturally returns a trusted
post-checkpoint recovery does the control arm receive the legacy visible
failure-as-zero table while the candidate keeps the sealed checkpoint table.
No fault is injected and no second provider, search, fetch, or network effect
is performed.

This module is build-only.  It has no evaluator, filesystem, process,
environment, credential, benchmark-launch, or signed-credit capability.  A
fresh/disjoint external protocol and a post-freeze evaluator are required
before any quality claim.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25271_validated_production_checkpoint_runtime as parent
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25284_natural_checkpoint_quality_runtime_v1"
ROLE = "v25284_natural_checkpoint_quality_runtime_result"
RECEIPT_ROLE = "v25284_content_free_natural_checkpoint_quality_receipt"
CONTROL_ARM = "legacy_failure_as_zero"
CANDIDATE_ARM = "checkpoint_recovery"
ARMS = (CONTROL_ARM, CANDIDATE_ARM)
OUTCOME_REASONS = (
    "clean_identity",
    "natural_postcheckpoint_recovery",
    "precheckpoint_visible_fallback_identity",
    "unrecoverable_failure_as_zero",
)
INJECTED_FAILURE_TYPE = "InjectedCheckpointReliabilityFault"


def _visible(task: Mapping[str, Any]) -> dict[str, str]:
    if (
        not isinstance(task, Mapping)
        or set(task) != {"opaque_id", "question"}
        or not isinstance(task.get("opaque_id"), str)
        or parent.sparse.score.OPAQUE_ID.fullmatch(task["opaque_id"]) is None
        or not isinstance(task.get("question"), str)
        or not task["question"].strip()
    ):
        raise ValueError("V2.52.84 visible task boundary drifted")
    return {"opaque_id": task["opaque_id"], "question": task["question"]}


def _prediction(value: str, kind: str) -> dict[str, str]:
    if not isinstance(value, str) or not value:
        raise ValueError("V2.52.84 empty prediction")
    if kind not in {"model_generated", "fallback", "visible_fallback"}:
        raise ValueError("V2.52.84 prediction kind drifted")
    return {
        "prediction": value,
        "prediction_sha256": hashlib.sha256(value.encode()).hexdigest(),
        "prediction_kind": kind,
    }


def _active_failures(stage: Mapping[str, Any]) -> dict[str, str]:
    checked = parent.validate_stage_receipt(stage)
    active = {
        name: failure
        for name, failure in checked["stage_failure_types"].items()
        if failure is not None
    }
    if INJECTED_FAILURE_TYPE in active.values():
        raise ValueError("V2.52.84 rejects injected checkpoint faults")
    return active


def _effect_parity(
    result: Mapping[str, Any], stage: Mapping[str, Any]
) -> bool:
    receipt = result["content_free_receipt"]
    budget = stage["outer_physical_budget_receipt"]
    return bool(
        receipt["physical_query_count"] == budget["query_admitted_count"]
        and receipt["physical_fetch_count"] == budget["fetch_admitted_count"]
        and receipt["physical_model_forward_count"]
        == budget["model_admitted_count"]
    )


def _projection(
    visible: Mapping[str, str],
    parent_result: Mapping[str, Any] | None,
    parent_stage: Mapping[str, Any],
    *,
    failure_as_zero_projector: Callable[[Mapping[str, str]], str],
) -> dict[str, Any]:
    task = _visible(visible)
    if not callable(failure_as_zero_projector):
        raise TypeError("V2.52.84 failure-as-zero projector is not callable")
    stage = parent.validate_stage_receipt(parent_stage)
    failures = _active_failures(stage)
    fallback = failure_as_zero_projector(dict(task))
    if not isinstance(fallback, str) or not fallback:
        raise ValueError("V2.52.84 failure-as-zero projector returned no table")
    fallback_arm = _prediction(fallback, "visible_fallback")

    checked: dict[str, Any] | None = None
    checkpoint: dict[str, Any] | None = None
    if parent_result is not None:
        checked = parent.validate_result(parent_result)
        if checked["opaque_id"] != task["opaque_id"] or not _effect_parity(
            checked, stage
        ):
            raise ValueError("V2.52.84 parent task/effect binding drifted")
        receipt = parent.validate_receipt(checked["content_free_receipt"])
        if (
            stage["checkpoint_kind"] != receipt["checkpoint_kind"]
            or stage["parent_result_retained"]
            is not receipt["parent_result_retained"]
            or stage["recovery_disposition"] != receipt["recovery_disposition"]
            or stage["failure_count"] != receipt["microstage_failure_count"]
        ):
            raise ValueError("V2.52.84 result/stage receipt binding drifted")
        raw_checkpoint = checked.get("production_checkpoint")
        if raw_checkpoint is not None:
            checkpoint = parent.validate_checkpoint(raw_checkpoint)

    if checked is None:
        if (
            not failures
            or stage["parent_result_retained"] is not False
            or stage["recovery_disposition"]
            not in {
                "visible_fallback_before_checkpoint",
                "untrusted_checkpoint_rejected",
                "checkpoint_unrecoverable_accounting_failure",
            }
        ):
            raise ValueError("V2.52.84 absent parent failure binding drifted")
        reason = "unrecoverable_failure_as_zero"
        control = candidate = fallback_arm
    elif checkpoint is None:
        receipt = parent.validate_receipt(checked["content_free_receipt"])
        if (
            checked["prediction_kind"] != "visible_fallback"
            or receipt["checkpoint_present"] is not False
            or receipt["recovery_disposition"] != "visible_fallback_before_checkpoint"
        ):
            raise ValueError("V2.52.84 precheckpoint fallback drifted")
        reason = "precheckpoint_visible_fallback_identity"
        control = candidate = fallback_arm
    else:
        natural = bool(
            receipt["post_checkpoint_recoverable_failure_present"]
            and receipt["recovery_disposition"].endswith(
                "preserved_after_post_checkpoint_failure"
            )
        )
        if natural:
            active = set(failures)
            early_recoverable = {
                "paired_parent_run_and_validate",
                "parent_prediction_binding",
            }
            envelope_recoverable = {
                "result_envelope_build",
                "result_envelope_validate",
            }
            if (
                not failures
                or not active.issubset(
                    set(parent.RECOVERABLE_POST_CHECKPOINT_STAGES)
                )
                or checked["role"] == parent.ROLE
                and (
                    not active.issubset(early_recoverable)
                    or checked["parent_result"] is not None
                )
                or checked["role"] == parent.RECOVERY_ROLE
                and not active.intersection(envelope_recoverable)
            ):
                raise ValueError("V2.52.84 natural recovery stage drifted")
            if checked["role"] == parent.RECOVERY_ROLE and (
                checked["recovered_failure_stages"] != list(failures)
                or checked["recovered_failure_types"] != failures
            ):
                raise ValueError("V2.52.84 recovery failure binding drifted")
            reason = "natural_postcheckpoint_recovery"
            control = fallback_arm
            candidate = _prediction(
                checked["prediction"], checked["prediction_kind"]
            )
        else:
            expected_disposition = (
                "clean_validated_production"
                if checkpoint["checkpoint_kind"] == "validated_model_output"
                else "clean_deterministic_fallback"
            )
            if (
                failures
                or receipt["recovery_disposition"] != expected_disposition
                or receipt["microstage_failure_count"] != 0
                or checked["role"] != parent.ROLE
            ):
                raise ValueError("V2.52.84 clean identity drifted")
            reason = "clean_identity"
            control = candidate = _prediction(
                checked["prediction"], checked["prediction_kind"]
            )

    return {
        "reason": reason,
        "parent_result": checked,
        "parent_stage": stage,
        "checkpoint": checkpoint,
        "failures": failures,
        "arms": {
            CONTROL_ARM: copy.deepcopy(control),
            CANDIDATE_ARM: copy.deepcopy(candidate),
        },
    }


def _build_receipt(projected: Mapping[str, Any]) -> dict[str, Any]:
    reason = projected["reason"]
    parent_result = projected["parent_result"]
    checkpoint = projected["checkpoint"]
    failures = dict(projected["failures"])
    arms = projected["arms"]
    changed = (
        arms[CONTROL_ARM]["prediction"] != arms[CANDIDATE_ARM]["prediction"]
    )
    natural = reason == "natural_postcheckpoint_recovery"
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "shared_real_forward_count": 1,
        "outcome_reason": reason,
        "parent_result_terminal": parent_result is not None,
        "trusted_checkpoint_present": checkpoint is not None,
        "checkpoint_kind": (
            None if checkpoint is None else checkpoint["checkpoint_kind"]
        ),
        "observed_failure_stages": list(failures),
        "observed_failure_types": failures,
        "natural_postcheckpoint_recovery_present": natural,
        "legacy_failure_as_zero_counterfactual_active": natural,
        "candidate_preserves_trusted_checkpoint": natural,
        "control_and_candidate_prediction_equal": not changed,
        "control_and_candidate_prediction_changed": changed,
        "candidate_additional_query_count": 0,
        "candidate_additional_fetch_count": 0,
        "candidate_additional_model_forward_count": 0,
        "candidate_additional_system_total_tokens": 0,
        "natural_event_only_and_no_fault_injection": True,
        "same_forward_visible_input_effect_checkpoint_and_cost": True,
        "failure_as_zero_projector_receives_visible_input_only": True,
        "postfreeze_evaluator_required_for_any_quality_claim": True,
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "candidate_quality_or_prediction_improvement_claim": False,
        "external_forward_evaluator_or_benchmark_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    reason = copied.get("outcome_reason")
    stages = copied.get("observed_failure_stages")
    failures = copied.get("observed_failure_types")
    natural = copied.get("natural_postcheckpoint_recovery_present") is True
    changed = copied.get("control_and_candidate_prediction_changed") is True
    zero_fields = (
        "candidate_additional_query_count",
        "candidate_additional_fetch_count",
        "candidate_additional_model_forward_count",
        "candidate_additional_system_total_tokens",
        "positive_signed_credit_count",
    )
    true_flags = (
        "natural_event_only_and_no_fault_injection",
        "same_forward_visible_input_effect_checkpoint_and_cost",
        "failure_as_zero_projector_receives_visible_input_only",
        "postfreeze_evaluator_required_for_any_quality_claim",
    )
    false_flags = (
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "candidate_quality_or_prediction_improvement_claim",
        "external_forward_evaluator_or_benchmark_authorized",
    )
    dynamic_bools = (
        "parent_result_terminal",
        "trusted_checkpoint_present",
        "natural_postcheckpoint_recovery_present",
        "legacy_failure_as_zero_counterfactual_active",
        "candidate_preserves_trusted_checkpoint",
        "control_and_candidate_prediction_equal",
        "control_and_candidate_prediction_changed",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "shared_real_forward_count",
            "outcome_reason",
            "parent_result_terminal",
            "trusted_checkpoint_present",
            "checkpoint_kind",
            "observed_failure_stages",
            "observed_failure_types",
            "natural_postcheckpoint_recovery_present",
            "legacy_failure_as_zero_counterfactual_active",
            "candidate_preserves_trusted_checkpoint",
            "control_and_candidate_prediction_equal",
            "control_and_candidate_prediction_changed",
            *zero_fields,
            *true_flags,
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("shared_real_forward_count") != 1
        or reason not in OUTCOME_REASONS
        or any(not isinstance(copied.get(name), bool) for name in dynamic_bools)
        or copied.get("checkpoint_kind") is not None
        and copied["checkpoint_kind"] not in parent.CHECKPOINT_KINDS
        or copied["trusted_checkpoint_present"]
        is not (copied.get("checkpoint_kind") is not None)
        or not isinstance(stages, list)
        or len(stages) != len(set(stages))
        or not isinstance(failures, Mapping)
        or list(failures) != stages
        or any(
            stage not in parent.STAGES
            or not isinstance(failures[stage], str)
            or not failures[stage]
            or len(failures[stage]) > 128
            for stage in stages
        )
        or INJECTED_FAILURE_TYPE in failures.values()
        or natural is not (reason == "natural_postcheckpoint_recovery")
        or copied["legacy_failure_as_zero_counterfactual_active"] is not natural
        or copied["candidate_preserves_trusted_checkpoint"] is not natural
        or copied["control_and_candidate_prediction_equal"] is changed
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] != 0
            for name in zero_fields
        )
        or reason == "clean_identity"
        and (
            copied["parent_result_terminal"] is not True
            or copied["trusted_checkpoint_present"] is not True
            or stages
            or changed
        )
        or reason == "natural_postcheckpoint_recovery"
        and (
            copied["parent_result_terminal"] is not True
            or copied["trusted_checkpoint_present"] is not True
            or not stages
            or not set(stages).issubset(
                set(parent.RECOVERABLE_POST_CHECKPOINT_STAGES)
            )
        )
        or reason == "precheckpoint_visible_fallback_identity"
        and (
            copied["parent_result_terminal"] is not True
            or copied["trusted_checkpoint_present"] is not False
            or changed
        )
        or reason == "unrecoverable_failure_as_zero"
        and (
            copied["parent_result_terminal"] is not False
            or copied["trusted_checkpoint_present"] is not False
            or changed
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.84 quality receipt drifted")
    return copied


def _build_result(
    visible: Mapping[str, str], projected: Mapping[str, Any]
) -> dict[str, Any]:
    receipt = _build_receipt(projected)
    parent_result = projected["parent_result"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "visible_input_payload_sha256": payload_sha256(dict(visible)),
        "arms": copy.deepcopy(projected["arms"]),
        "parent_result": copy.deepcopy(parent_result),
        "parent_result_payload_sha256": (
            None
            if parent_result is None
            else parent_result["result_payload_sha256"]
        ),
        "parent_stage_receipt": copy.deepcopy(projected["parent_stage"]),
        "content_free_quality_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(
    value: Mapping[str, Any],
    *,
    task: Mapping[str, Any],
    failure_as_zero_projector: Callable[[Mapping[str, str]], str],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    visible = _visible(task)
    arms = copied.get("arms")
    parent_raw = copied.get("parent_result")
    stage_raw = copied.get("parent_stage_receipt")
    receipt_raw = copied.get("content_free_quality_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "status",
            "visible_input_payload_sha256",
            "arms",
            "parent_result",
            "parent_result_payload_sha256",
            "parent_stage_receipt",
            "content_free_quality_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("opaque_id") != visible["opaque_id"]
        or copied.get("status") != "terminal"
        or copied.get("visible_input_payload_sha256")
        != payload_sha256(visible)
        or not isinstance(arms, Mapping)
        or list(arms) != list(ARMS)
        or not isinstance(stage_raw, Mapping)
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
        raise ValueError("V2.52.84 quality result envelope drifted")
    projected = _projection(
        visible,
        parent_raw,
        stage_raw,
        failure_as_zero_projector=failure_as_zero_projector,
    )
    expected_receipt = _build_receipt(projected)
    if (
        copied["arms"] != projected["arms"]
        or validate_receipt(receipt_raw) != expected_receipt
        or copied.get("parent_result_payload_sha256")
        != (
            None
            if projected["parent_result"] is None
            else projected["parent_result"]["result_payload_sha256"]
        )
    ):
        raise ValueError("V2.52.84 quality projection binding drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
    failure_as_zero_projector: Callable[[Mapping[str, str]], str],
) -> dict[str, Any]:
    visible = _visible(task)
    parent_result: dict[str, Any] | None
    try:
        parent_result, parent_stage = parent.run_task(
            visible,
            model=model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=monotonic,
        )
    except parent.ProductionCheckpointStageError as exc:
        parent_result = None
        parent_stage = exc.stage_receipt
    projected = _projection(
        visible,
        parent_result,
        parent_stage,
        failure_as_zero_projector=failure_as_zero_projector,
    )
    return validate_result(
        _build_result(visible, projected),
        task=visible,
        failure_as_zero_projector=failure_as_zero_projector,
    )


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "INJECTED_FAILURE_TYPE",
    "OUTCOME_REASONS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "run_task",
    "validate_receipt",
    "validate_result",
]
