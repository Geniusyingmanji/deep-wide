"""Pre-effect query-contract repair for the V2.53.49 paired mechanism.

V2.53.53 exposed a deterministic boundary mismatch.  The visible-only
planner accepted a long markup-bearing fallback query, executed the first
search/fetch wave, and only then V2.51.17 rejected the same four-query vector
under its stricter legacy-query grammar.  This append-only successor reuses
V2.51.23's frozen visible-only projector on the first plan envelope before any
search or fetch effect.  The grounded-plan output, fact treatment, paired
synthesis, physical caps, and attribution rule are unchanged.

The runtime accepts only the current visible question and injected bounded
clients.  It has no benchmark label, mapping, gold, evaluator, score, reward,
historical-result, credential, filesystem, environment, process, or network
capability of its own.  Entropy/information gain remains shadow-only and
assigns no signed credit.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25110_exact_visible_schema as schema
from . import v25117_grounded_target_record_plan as target_plan
from . import v25123_visible_legacy_query_compatible_runtime as compatibility
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25349_shared_prefix_grounded_fact_paired_runtime as parent
from .clients import ModelRequestError, parse_json_object
from .v24259_deterministic_table_normalizer import _replace_text
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter


POLICY_ID = "v25354_pre_effect_query_compatible_grounded_fact_runtime_v1"
ROLE = "v25354_pre_effect_query_compatible_grounded_fact_runtime_result"
STAGE_RECEIPT_ROLE = "v25354_content_free_pre_effect_query_contract_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def projected_plan(
    plan: Mapping[str, Any], question: str, limits: score.ScoreFirstLimits
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the exact parent plan after a pre-effect compatible projection."""

    seeds, observation = compatibility._query_seeds(plan, question)
    value = dict(plan)
    value["queries"] = seeds
    columns = schema.extract_exact_visible_columns(question)
    if not columns:
        raise ValueError("V2.53.54 visible exact schema is absent or ambiguous")
    value["columns"] = columns
    completed = schema.validated_exact_plan(value, question, limits)
    queries = list(completed["queries"])
    if (
        len(queries) != limits.search_queries
        or any(target_plan._safe_query(query) != query for query in queries)
    ):
        raise ValueError("V2.53.54 completed query vector violates downstream grammar")
    return completed, observation


class PreEffectQueryCompatibleHardCappedModel(cap.HardCappedModelLimiter):
    """Hard-capped model whose first response is safe before search begins."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        budget: cap.PhysicalEffectBudget,
        *,
        question: str,
        limits: score.ScoreFirstLimits,
    ) -> None:
        super().__init__(bounded, budget)
        self._v25354_question = str(question)
        self._v25354_limits = limits
        self.logical_call_count = 0
        self.plan_model_effect_failure_type: str | None = None
        self.plan_transport_failed = False
        self.plan_output_validation_failure_type: str | None = None
        self.query_observation: dict[str, Any] = {
            "input_provider_query_string_count": 0,
            "compatible_provider_query_seed_count": 0,
            "transformed_or_rejected_provider_query_count": 0,
            "emitted_query_seed_count": 0,
            "visible_fallback_query_seed_used": False,
        }
        # Fail before any effect if the visible schema or fixed limits cannot
        # produce a vector accepted by the downstream grounded-plan grammar.
        projected_plan({}, self._v25354_question, self._v25354_limits)

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        self.logical_call_count += 1
        if self.logical_call_count != 1:
            return super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        if str(system) != score.PLAN_SYSTEM:
            raise ValueError("V2.53.54 first model call is not the visible plan")
        try:
            value = super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
            try:
                raw_plan = parse_json_object(score._model_text(value))
            except (TypeError, ValueError) as exc:
                raw_plan = {}
                self.plan_output_validation_failure_type = _safe_failure(exc)
        except BaseException as exc:
            raw_plan = {}
            value = ""
            self.plan_model_effect_failure_type = _safe_failure(exc)
            self.plan_transport_failed = isinstance(exc, ModelRequestError)
        plan, observation = projected_plan(
            raw_plan, self._v25354_question, self._v25354_limits
        )
        self.query_observation = observation
        return _replace_text(
            value,
            json.dumps(plan, ensure_ascii=False, separators=(",", ":")),
        )


def _stage_receipt(
    model: PreEffectQueryCompatibleHardCappedModel,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    observation = model.query_observation
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "logical_model_call_count": model.logical_call_count,
        "input_provider_query_string_count": int(
            observation["input_provider_query_string_count"]
        ),
        "compatible_provider_query_seed_count": int(
            observation["compatible_provider_query_seed_count"]
        ),
        "transformed_or_rejected_provider_query_count": int(
            observation["transformed_or_rejected_provider_query_count"]
        ),
        "emitted_query_seed_count": int(observation["emitted_query_seed_count"]),
        "plan_model_effect_failed": model.plan_model_effect_failure_type is not None,
        "plan_model_effect_failure_type": model.plan_model_effect_failure_type,
        "plan_transport_failed": model.plan_transport_failed,
        "plan_output_validation_failed": model.plan_output_validation_failure_type
        is not None,
        "plan_output_validation_failure_type": model.plan_output_validation_failure_type,
        "visible_fallback_query_seed_used": bool(
            observation["visible_fallback_query_seed_used"]
        ),
        "query_projection_completed_before_first_search_or_fetch_effect": True,
        "frozen_v25123_visible_query_projector_reused": True,
        "markup_urls_controls_and_forbidden_syntax_removed": True,
        "completed_four_query_vector_valid_under_downstream_grammar": True,
        "grounded_plan_fact_treatment_and_attribution_rule_unchanged": True,
        "physical_query_fetch_model_caps_unchanged": True,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "contains_question_query_column_url_title_page_prediction_answer_hash_opaque_id_or_credential": False,
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
    counts = (
        "logical_model_call_count",
        "input_provider_query_string_count",
        "compatible_provider_query_seed_count",
        "transformed_or_rejected_provider_query_count",
        "emitted_query_seed_count",
    )
    nullable = (
        "plan_model_effect_failure_type",
        "plan_output_validation_failure_type",
    )
    bool_fields = (
        "plan_model_effect_failed",
        "plan_transport_failed",
        "plan_output_validation_failed",
        "visible_fallback_query_seed_used",
    )
    true_flags = (
        "query_projection_completed_before_first_search_or_fetch_effect",
        "frozen_v25123_visible_query_projector_reused",
        "markup_urls_controls_and_forbidden_syntax_removed",
        "completed_four_query_vector_valid_under_downstream_grammar",
        "grounded_plan_fact_treatment_and_attribution_rule_unchanged",
        "physical_query_fetch_model_caps_unchanged",
    )
    false_flags = (
        "additional_model_search_fetch_token_context_wall_or_network_budget",
        "contains_question_query_column_url_title_page_prediction_answer_hash_opaque_id_or_credential",
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
        *counts,
        *nullable,
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
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or not 1 <= copied["logical_model_call_count"] <= cap.MODEL_CAP
        or copied["input_provider_query_string_count"] > 4
        or copied["compatible_provider_query_seed_count"]
        > copied["input_provider_query_string_count"]
        or copied["transformed_or_rejected_provider_query_count"]
        > copied["input_provider_query_string_count"]
        or not 1 <= copied["emitted_query_seed_count"] <= 4
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or any(
            copied.get(name) is not None
            and (
                not isinstance(copied[name], str)
                or not copied[name]
                or len(copied[name]) > 128
            )
            for name in nullable
        )
        or copied["plan_model_effect_failed"]
        is not (copied["plan_model_effect_failure_type"] is not None)
        or copied["plan_transport_failed"]
        is not (copied["plan_model_effect_failure_type"] == "ModelRequestError")
        or copied["plan_output_validation_failed"]
        is not (copied["plan_output_validation_failure_type"] is not None)
        or copied["visible_fallback_query_seed_used"]
        is not (
            copied["compatible_provider_query_seed_count"] == 0
            and copied["emitted_query_seed_count"] == 1
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.54 pre-effect query-contract receipt drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: PreEffectQueryCompatibleHardCappedModel,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    visible = score.validate_visible_task(task)
    if (
        not isinstance(model, PreEffectQueryCompatibleHardCappedModel)
        or model._budget is not budget
        or model._v25354_question != visible["question"]
    ):
        raise TypeError("V2.53.54 pre-effect model boundary drifted")
    kwargs: dict[str, Any] = {
        "model": model,
        "searches": searches,
        "limits": limits,
        "budget": budget,
        "arm_order": arm_order,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent_result = parent.validate_result(parent.run_paired_task(visible, **kwargs))
    value = copy.deepcopy(parent_result)
    value["role"] = ROLE
    value["policy_id"] = POLICY_ID
    value["pre_effect_query_contract_receipt"] = _stage_receipt(
        model, parent_result
    )
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    stage = copied.get("pre_effect_query_contract_receipt")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(stage, Mapping)
        or validate_stage_receipt(stage) != dict(stage)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.54 result envelope drifted")
    parent_value = copy.deepcopy(copied)
    parent_value.pop("pre_effect_query_contract_receipt")
    parent_value["role"] = parent.ROLE
    parent_value["policy_id"] = parent.POLICY_ID
    parent_value["result_payload_sha256"] = stage[
        "parent_result_payload_sha256"
    ]
    parent_checked = parent.validate_result(parent_value)
    if (
        stage["logical_model_call_count"]
        != parent_checked["content_free_receipt"]["physical_model_forward_count"]
        or parent_checked["content_free_receipt"]["outer_physical_budget_receipt"]
        ["query_rejected_count"]
        != 0
    ):
        raise ValueError("V2.53.54 stage-to-parent binding drifted")
    return copied


validate_parent_receipt = parent.validate_receipt
validate_parent_result = parent.validate_result
validate_receipt = parent.validate_receipt


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "PHASES",
    "POLICY_ID",
    "PreEffectQueryCompatibleHardCappedModel",
    "ROLE",
    "SECOND_PHASE",
    "STAGE_RECEIPT_ROLE",
    "projected_plan",
    "run_paired_task",
    "validate_parent_receipt",
    "validate_parent_result",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
