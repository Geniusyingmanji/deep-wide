"""Exact-visible-schema recovery and separated failure accounting.

This append-only wrapper preserves every V2.51.06 query, fetch, model, token,
context, and wall budget.  The first logical model effect is still attempted
exactly once.  Its plan envelope is deterministically forced to the columns
explicitly declared in the visible question; if the provider effect fails,
only that already-visible schema is recovered.  Proposal model-effect failure
and representation validation failure are recorded as disjoint mechanisms.

Runtime input remains exactly ``opaque_id`` and ``question`` plus injected
bounded clients.  No benchmark label, mapping, gold, evaluator, score, reward,
credential, historical result, or launch capability is introduced.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25106_total_verified_field_enforced_paired_runtime as parent
from . import v25110_exact_visible_schema as schema
from .clients import ModelRequestError, parse_json_object
from .v24259_deterministic_table_normalizer import _replace_text
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25111_schema_recovered_failure_separated_paired_runtime_v1"
ROLE = "v25111_schema_recovered_failure_separated_paired_runtime_result"
STAGE_RECEIPT_ROLE = "v25111_content_free_stage_failure_accounting_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


class ExactVisibleSchemaStageModel(DeadlineAwareGlobalModelSlotLimiter):
    """Transparent bounded-model proxy with a visible-only plan fallback."""

    def __init__(self, bounded: DeadlineAwareGlobalModelSlotLimiter, question: str) -> None:
        if not isinstance(bounded, DeadlineAwareGlobalModelSlotLimiter):
            raise TypeError("V2.51.11 requires a bounded global model limiter")
        columns = schema.extract_exact_visible_columns(question)
        if not columns:
            raise ValueError("V2.51.11 visible exact schema is absent or ambiguous")
        self._bounded = bounded
        self._columns = tuple(columns)
        self.logical_call_count = 0
        self.plan_model_effect_failure_type: str | None = None
        self.plan_transport_failed = False
        self.plan_output_validation_failure_type: str | None = None
        self.proposal_model_effect_failure_type: str | None = None
        self.proposal_transport_failed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bounded, name)

    @property
    def visible_schema_column_count(self) -> int:
        return len(self._columns)

    def remaining_effect_seconds(self) -> float:
        return float(self._bounded.remaining_effect_seconds())

    def receipt(self) -> dict[str, Any]:
        return self._bounded.receipt()

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        self.logical_call_count += 1
        stage = self.logical_call_count
        if stage == 1:
            try:
                value = self._bounded.complete(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )
                try:
                    plan = parse_json_object(score._model_text(value))
                except (TypeError, ValueError) as exc:
                    plan = {}
                    self.plan_output_validation_failure_type = _safe_failure(exc)
            except BaseException as exc:
                plan = {}
                value = ""
                self.plan_model_effect_failure_type = _safe_failure(exc)
                self.plan_transport_failed = isinstance(exc, ModelRequestError)
            plan["columns"] = list(self._columns)
            return _replace_text(
                value,
                json.dumps(plan, ensure_ascii=False, separators=(",", ":")),
            )
        if stage == 2:
            try:
                return self._bounded.complete(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )
            except BaseException as exc:
                self.proposal_model_effect_failure_type = _safe_failure(exc)
                self.proposal_transport_failed = isinstance(exc, ModelRequestError)
                raise
        return self._bounded.complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


def _stage_receipt(
    model: ExactVisibleSchemaStageModel,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    completed = parent_result.get("status") == "terminal"
    parent_receipt = parent_result.get("content_free_receipt") if completed else None
    representation_failed = bool(
        isinstance(parent_receipt, Mapping)
        and parent_receipt.get("representation_validation_failed") is True
    )
    representation_type = (
        parent_receipt.get("representation_failure_type")
        if isinstance(parent_receipt, Mapping)
        else None
    )
    proposal_type = model.proposal_model_effect_failure_type
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "parent_runtime_completed": completed,
        "logical_model_call_count": model.logical_call_count,
        "visible_schema_column_count": model.visible_schema_column_count,
        "plan_model_effect_failed": model.plan_model_effect_failure_type is not None,
        "plan_model_effect_failure_type": model.plan_model_effect_failure_type,
        "plan_transport_failed": model.plan_transport_failed,
        "plan_output_validation_failed": model.plan_output_validation_failure_type is not None,
        "plan_output_validation_failure_type": model.plan_output_validation_failure_type,
        "proposal_model_effect_failed": proposal_type is not None,
        "proposal_model_effect_failure_type": proposal_type,
        "proposal_transport_failed": model.proposal_transport_failed,
        "representation_validation_failed": representation_failed,
        "representation_failure_type": representation_type,
        "visible_schema_forced_on_plan_envelope": True,
        "visible_schema_recovered_after_plan_model_effect_failure": (
            model.plan_model_effect_failure_type is not None
        ),
        "proposal_failure_does_not_imply_representation_failure": True,
        "transport_and_representation_failures_accounted_separately": True,
        "query_search_fetch_model_token_context_wall_and_network_caps_preserved": True,
        "contains_question_column_query_url_title_page_quote_anchor_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
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
    nullable_types = (
        "plan_model_effect_failure_type",
        "plan_output_validation_failure_type",
        "proposal_model_effect_failure_type",
        "representation_failure_type",
    )
    bool_fields = (
        "parent_runtime_completed",
        "plan_model_effect_failed",
        "plan_transport_failed",
        "plan_output_validation_failed",
        "proposal_model_effect_failed",
        "proposal_transport_failed",
        "representation_validation_failed",
    )
    true_flags = (
        "visible_schema_forced_on_plan_envelope",
        "proposal_failure_does_not_imply_representation_failure",
        "transport_and_representation_failures_accounted_separately",
        "query_search_fetch_model_token_context_wall_and_network_caps_preserved",
    )
    false_flags = (
        "contains_question_column_query_url_title_page_quote_anchor_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "parent_role",
        "parent_policy_id",
        "parent_result_payload_sha256",
        "logical_model_call_count",
        "visible_schema_column_count",
        "visible_schema_recovered_after_plan_model_effect_failure",
        *nullable_types,
        *bool_fields,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != parent.ROLE
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or not isinstance(
            copied.get("visible_schema_recovered_after_plan_model_effect_failure"), bool
        )
        or copied["visible_schema_recovered_after_plan_model_effect_failure"]
        is not copied["plan_model_effect_failed"]
        or isinstance(copied.get("logical_model_call_count"), bool)
        or not isinstance(copied.get("logical_model_call_count"), int)
        or not 0 <= copied["logical_model_call_count"] <= 4
        or isinstance(copied.get("visible_schema_column_count"), bool)
        or not isinstance(copied.get("visible_schema_column_count"), int)
        or not 1 <= copied["visible_schema_column_count"] <= 20
        or any(
            copied.get(name) is not None
            and (
                not isinstance(copied[name], str)
                or not copied[name]
                or len(copied[name]) > 128
            )
            for name in nullable_types
        )
        or copied["plan_model_effect_failed"]
        is not (copied["plan_model_effect_failure_type"] is not None)
        or copied["plan_transport_failed"]
        is not (copied["plan_model_effect_failure_type"] == "ModelRequestError")
        or copied["plan_output_validation_failed"]
        is not (copied["plan_output_validation_failure_type"] is not None)
        or copied["proposal_model_effect_failed"]
        is not (copied["proposal_model_effect_failure_type"] is not None)
        or copied["proposal_transport_failed"]
        is not (copied["proposal_model_effect_failure_type"] == "ModelRequestError")
        or copied["representation_validation_failed"]
        is not (copied["representation_failure_type"] is not None)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.11 stage receipt drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    visible = score.validate_visible_task(task)
    stage_model = ExactVisibleSchemaStageModel(model, visible["question"])
    kwargs: dict[str, Any] = {
        "model": stage_model,
        "searches": searches,
        "limits": limits,
        "arm_order": arm_order,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent_result = parent.validate_result(parent.run_paired_task(visible, **kwargs))
    value = copy.deepcopy(parent_result)
    value["role"] = ROLE
    value["policy_id"] = POLICY_ID
    value["stage_failure_accounting"] = _stage_receipt(stage_model, parent_result)
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    stage = copied.get("stage_failure_accounting")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(stage, Mapping)
        or validate_stage_receipt(stage) != dict(stage)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.11 result envelope drifted")
    parent_value = copy.deepcopy(copied)
    parent_value.pop("stage_failure_accounting")
    parent_value["role"] = parent.ROLE
    parent_value["policy_id"] = parent.POLICY_ID
    parent_value["result_payload_sha256"] = stage["parent_result_payload_sha256"]
    parent_checked = parent.validate_result(parent_value)
    parent_completed = parent_checked["status"] == "terminal"
    receipt = parent_checked["content_free_receipt"] if parent_completed else None
    if (
        stage["parent_runtime_completed"] is not parent_completed
        or parent_completed and stage["logical_model_call_count"] != 4
        or parent_completed
        and stage["representation_validation_failed"]
        is not receipt["representation_validation_failed"]
        or parent_completed
        and stage["representation_failure_type"] != receipt["representation_failure_type"]
        or parent_completed
        and stage["proposal_model_effect_failure_type"]
        != parent_checked["failure_types"]["proposal"]
    ):
        raise ValueError("V2.51.11 stage-to-parent binding drifted")
    return copied


validate_accounting_failure_receipt = parent.validate_accounting_failure_receipt
validate_accounting_failure_result = parent.validate_accounting_failure_result
validate_parent_receipt = parent.validate_receipt


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "ExactVisibleSchemaStageModel",
    "FIRST_PHASE",
    "PHASES",
    "POLICY_ID",
    "ROLE",
    "SECOND_PHASE",
    "STAGE_RECEIPT_ROLE",
    "run_paired_task",
    "validate_accounting_failure_receipt",
    "validate_accounting_failure_result",
    "validate_parent_receipt",
    "validate_result",
    "validate_stage_receipt",
]
