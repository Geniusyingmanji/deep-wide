"""Production-only sparse runtime under the verified truthful physical caps.

The first validated production table is the only prediction.  The inherited
paired entrypoint is retained for frozen retrieval/accounting compatibility,
but its second synthesis entry deterministically replays the first response
and can never reach the provider.  Header, quote, vertical-candidate, score,
benchmark-label, and entropy routing are absent.

All query/fetch/model effects pass through the injected V2.52.53 pre-effect
budget.  This module itself has no filesystem, environment, process, network,
evaluator, credential, or benchmark-launch capability.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v25135_sparse_production_runtime as sparse
from . import v25253_outer_physical_cap_observed_runtime as cap
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25265_production_only_totality_runtime_v1"
ROLE = "v25265_production_only_totality_runtime_result"
RECEIPT_ROLE = "v25265_content_free_production_only_receipt"
STAGE_RECEIPT_ROLE = "v25265_content_free_production_only_stage_receipt"
STAGES = ("sparse_production", "production_projection")
PHASES = sparse.PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


class ProductionOnlyStageError(RuntimeError):
    """Content-free outer signal with a sealed stage/budget receipt."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.stage_receipt = validate_stage_receipt(receipt)
        super().__init__("V2.52.65 production-only runtime stage failed")


class ProductionOnlySparseModel(sparse.SparseProductionModel):
    """Suppress the unused revision provider effect unconditionally."""

    def _revision(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool,
    ) -> Any:
        del system, user, max_output_tokens, json_mode
        self.revision_synthesis_entry_count = 1
        if self._production_response is None or self.production_prediction is None:
            raise RuntimeError("V2.52.65 revision entry preceded production")
        self.identity_replay_used = True
        return self._production_response


class StageObserver:
    def __init__(self, budget: cap.PhysicalEffectBudget) -> None:
        if not isinstance(budget, cap.PhysicalEffectBudget):
            raise TypeError("V2.52.65 stage budget drifted")
        self._budget = budget
        self._entered = {stage: 0 for stage in STAGES}
        self._completed = {stage: 0 for stage in STAGES}
        self._failure_stage: str | None = None
        self._failure_type: str | None = None

    def run(self, stage: str, function: Callable[[], Any]) -> Any:
        if stage not in STAGES or self._failure_stage is not None or self._entered[stage]:
            raise ValueError("V2.52.65 stage transition drifted")
        self._entered[stage] = 1
        try:
            output = function()
        except BaseException as exc:
            self._failure_stage = stage
            self._failure_type = _safe_failure(exc)
            raise ProductionOnlyStageError(self.receipt()) from None
        self._completed[stage] = 1
        return output

    def receipt(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": STAGE_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "stage_entered_counts": dict(self._entered),
            "stage_completed_counts": dict(self._completed),
            "failure_present": self._failure_stage is not None,
            "failure_stage": self._failure_stage,
            "failure_type": self._failure_type,
            "outer_physical_budget_receipt": self._budget.receipt(),
            "successful_result_bytes_are_not_changed_by_observer": True,
            "failure_observer_emits_only_finite_stage_and_exception_type": True,
            "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "external_forward_evaluator_or_benchmark_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_stage_receipt(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    entered = copied.get("stage_entered_counts")
    completed = copied.get("stage_completed_counts")
    budget = copied.get("outer_physical_budget_receipt")
    failure = copied.get("failure_present") is True
    true_flags = (
        "successful_result_bytes_are_not_changed_by_observer",
        "failure_observer_emits_only_finite_stage_and_exception_type",
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
            "artifact_version", "role", "policy_id", "stage_entered_counts",
            "stage_completed_counts", "failure_present", "failure_stage",
            "failure_type", "outer_physical_budget_receipt", *true_flags,
            *false_flags, "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(entered, Mapping)
        or not isinstance(completed, Mapping)
        or set(entered) != set(STAGES)
        or set(completed) != set(STAGES)
        or any(count not in {0, 1} for count in entered.values())
        or any(count not in {0, 1} for count in completed.values())
        or any(completed[stage] > entered[stage] for stage in STAGES)
        or not isinstance(copied.get("failure_present"), bool)
        or (copied.get("failure_stage") in STAGES) is not failure
        or (
            isinstance(copied.get("failure_type"), str)
            and 0 < len(copied["failure_type"]) <= 128
        )
        is not failure
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or failure and completed[copied["failure_stage"]] != 0
        or not failure
        and (any(entered[stage] != 1 for stage in STAGES) or any(completed[stage] != 1 for stage in STAGES))
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.65 stage receipt drifted")
    return copied


def _content_free_receipt(
    *,
    provider: ProductionOnlySparseModel,
    parent_result: Mapping[str, Any] | None,
    production: str,
    post_effect_failure: str | None,
    model_cost: Mapping[str, int],
    search_cost: Mapping[str, Mapping[str, int]],
    budget: cap.PhysicalEffectBudget,
) -> dict[str, Any]:
    budget_receipt = cap.validate_budget_receipt(budget.receipt())
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "plan_provider_forward_count": provider.plan_provider_forward_count,
        "grounded_plan_provider_forward_count": provider.grounded_plan_provider_forward_count,
        "production_synthesis_entry_count": provider.production_synthesis_entry_count,
        "production_synthesis_provider_forward_count": provider.production_synthesis_provider_forward_count,
        "suppressed_revision_entry_count": provider.revision_synthesis_entry_count,
        "revision_provider_forward_count": provider.revision_synthesis_provider_forward_count,
        "provider_forward_count": (
            provider.plan_provider_forward_count
            + provider.grounded_plan_provider_forward_count
            + provider.production_synthesis_provider_forward_count
            + provider.revision_synthesis_provider_forward_count
        ),
        "model_provider_request_count": int(model_cost["requests"]),
        "model_provider_attempt_count": int(model_cost["attempts"]),
        "physical_query_count": budget_receipt["query_admitted_count"],
        "physical_fetch_count": budget_receipt["fetch_admitted_count"],
        "physical_model_forward_count": budget_receipt["model_admitted_count"],
        "system_total_tokens": int(model_cost["total_tokens"])
        + sum(int(search_cost[phase]["total_tokens"]) for phase in PHASES),
        "production_provider_output_valid": provider.production_provider_valid_output,
        "production_fallback_used": not provider.production_provider_valid_output,
        "parent_result_valid": parent_result is not None,
        "post_effect_failure_present": post_effect_failure is not None,
        "post_effect_failure_type": post_effect_failure,
        "first_validated_production_is_only_prediction": True,
        "second_synthesis_entry_is_local_identity_replay": True,
        "header_quote_vertical_candidate_or_revision_prediction_used": False,
        "prediction_preserved_after_parent_failure": bool(
            parent_result is not None or provider.production_prediction == production
        ),
        "query_fetch_model_context_token_or_wall_cap_expanded": False,
        "contains_question_column_query_url_title_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "plan_provider_forward_count", "grounded_plan_provider_forward_count",
        "production_synthesis_entry_count", "production_synthesis_provider_forward_count",
        "suppressed_revision_entry_count", "revision_provider_forward_count",
        "provider_forward_count", "model_provider_request_count",
        "model_provider_attempt_count", "physical_query_count",
        "physical_fetch_count", "physical_model_forward_count", "system_total_tokens",
        "positive_signed_credit_count",
    )
    dynamic_bools = (
        "production_provider_output_valid", "production_fallback_used",
        "parent_result_valid", "post_effect_failure_present",
        "prediction_preserved_after_parent_failure",
    )
    true_flags = (
        "first_validated_production_is_only_prediction",
        "second_synthesis_entry_is_local_identity_replay",
    )
    false_flags = (
        "header_quote_vertical_candidate_or_revision_prediction_used",
        "query_fetch_model_context_token_or_wall_cap_expanded",
        "contains_question_column_query_url_title_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    failure = copied.get("post_effect_failure_present") is True
    if (
        set(copied)
        != {
            "artifact_version", "role", "policy_id", *counts, *dynamic_bools,
            "post_effect_failure_type", *true_flags, *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic_bools)
        or copied["plan_provider_forward_count"] != 1
        or copied["grounded_plan_provider_forward_count"] not in {0, 1}
        or copied["production_synthesis_entry_count"] not in {0, 1}
        or copied["production_synthesis_provider_forward_count"]
        != copied["production_synthesis_entry_count"]
        or copied["suppressed_revision_entry_count"] not in {0, 1}
        or copied["revision_provider_forward_count"] != 0
        or copied["provider_forward_count"]
        != copied["plan_provider_forward_count"]
        + copied["grounded_plan_provider_forward_count"]
        + copied["production_synthesis_provider_forward_count"]
        or copied["provider_forward_count"] > 3
        or copied["model_provider_request_count"] > copied["provider_forward_count"]
        or copied["model_provider_attempt_count"] < copied["model_provider_request_count"]
        or copied["physical_query_count"] > cap.QUERY_CAP
        or copied["physical_fetch_count"] > cap.FETCH_CAP
        or copied["physical_model_forward_count"] > cap.MODEL_CAP
        or copied["physical_model_forward_count"] != copied["provider_forward_count"]
        or copied["production_fallback_used"] is copied["production_provider_output_valid"]
        or copied["positive_signed_credit_count"] != 0
        or failure
        is not (
            isinstance(copied.get("post_effect_failure_type"), str)
            and 0 < len(copied["post_effect_failure_type"]) <= 128
        )
        or not failure and copied.get("post_effect_failure_type") is not None
        or not copied["prediction_preserved_after_parent_failure"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.65 production-only receipt drifted")
    return copied


def _run_core(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    visible = sparse._validate_boundary(task, model=model, searches=searches, limits=limits)
    model_before = sparse.counters._counter(model, sparse._MODEL_COUNTERS)
    search_before = {
        phase: sparse.counters._counter(searches[phase], sparse._SEARCH_COUNTERS)
        for phase in PHASES
    }
    provider = ProductionOnlySparseModel(
        model,
        question=visible["question"],
        first_wave_search=searches[sparse.FIRST_PHASE],
        limits=limits,
    )
    parent_result: dict[str, Any] | None = None
    post_effect_failure: str | None = None
    try:
        parent_result = sparse.parent.validate_result(
            sparse.parent.run_paired_task(
                visible,
                model=provider,
                searches=searches,
                limits=limits,
                arm_order=sparse.ARMS,
                monotonic=monotonic,
            )
        )
    except BaseException as exc:
        post_effect_failure = _safe_failure(exc)

    model_cost = sparse.counters._delta(
        sparse.counters._counter(model, sparse._MODEL_COUNTERS), model_before
    )
    search_cost = {
        phase: sparse.counters._delta(
            sparse.counters._counter(searches[phase], sparse._SEARCH_COUNTERS),
            search_before[phase],
        )
        for phase in PHASES
    }
    columns, _schema_source = sparse.parent._total_columns(
        provider._raw_plan, visible["question"]
    )
    production = provider.production_prediction or sparse.counters._fallback(columns)
    if parent_result is not None:
        control = parent_result["predictions"][sparse.CONTROL_ARM]
        candidate = parent_result["predictions"][sparse.CANDIDATE_ARM]
        if control != candidate or control != production:
            raise ValueError("V2.52.65 parent replay changed production prediction")

    receipt = _content_free_receipt(
        provider=provider,
        parent_result=parent_result,
        production=production,
        post_effect_failure=post_effect_failure,
        model_cost=model_cost,
        search_cost=search_cost,
        budget=budget,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "prediction": production,
        "prediction_sha256": hashlib.sha256(production.encode()).hexdigest(),
        "prediction_kind": "model_generated" if provider.production_provider_valid_output else "fallback",
        "failure_types": {
            "plan": provider.plan_failure_type,
            "grounded_plan": provider.grounded_plan_failure_type,
            "production": provider.production_failure_type,
            "post_effect": post_effect_failure,
        },
        "parent_result": copy.deepcopy(parent_result),
        "parent_result_payload_sha256": None if parent_result is None else parent_result["result_payload_sha256"],
        "cost": {
            "model": model_cost,
            "search": search_cost,
            "system_total_tokens": receipt["system_total_tokens"],
        },
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
    prediction = copied.get("prediction")
    failures = copied.get("failure_types")
    parent_result = copied.get("parent_result")
    receipt = copied.get("content_free_receipt")
    cost = copied.get("cost")
    if (
        set(copied)
        != {
            "artifact_version", "role", "policy_id", "opaque_id", "status",
            "prediction", "prediction_sha256", "prediction_kind", "failure_types",
            "parent_result", "parent_result_payload_sha256", "cost",
            "content_free_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized", "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(copied.get("opaque_id"), str)
        or sparse.score.OPAQUE_ID.fullmatch(copied["opaque_id"]) is None
        or not isinstance(prediction, str)
        or not prediction
        or copied.get("prediction_sha256") != hashlib.sha256(prediction.encode()).hexdigest()
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or not isinstance(failures, Mapping)
        or set(failures) != {"plan", "grounded_plan", "production", "post_effect"}
        or any(
            failure is not None
            and (not isinstance(failure, str) or not failure or len(failure) > 128)
            for failure in failures.values()
        )
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(cost, Mapping)
        or set(cost) != {"model", "search", "system_total_tokens"}
        or cost.get("system_total_tokens") != receipt["system_total_tokens"]
        or copied["prediction_kind"]
        != ("model_generated" if receipt["production_provider_output_valid"] else "fallback")
        or receipt["post_effect_failure_present"] is not (failures["post_effect"] is not None)
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
        raise ValueError("V2.52.65 production-only result drifted")
    if parent_result is None:
        if copied.get("parent_result_payload_sha256") is not None or failures["post_effect"] is None:
            raise ValueError("V2.52.65 absent parent result drifted")
    else:
        checked_parent = sparse.parent.validate_result(parent_result)
        if (
            copied.get("parent_result_payload_sha256") != checked_parent["result_payload_sha256"]
            or checked_parent["predictions"][sparse.CONTROL_ARM] != prediction
            or checked_parent["predictions"][sparse.CANDIDATE_ARM] != prediction
        ):
            raise ValueError("V2.52.65 parent prediction binding drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    observer = StageObserver(budget)
    result = observer.run(
        "sparse_production",
        lambda: _run_core(
            task,
            model=model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=monotonic,
        ),
    )
    projected = observer.run("production_projection", lambda: validate_result(result))
    return projected, observer.receipt()


__all__ = [
    "PHASES", "POLICY_ID", "ProductionOnlySparseModel",
    "ProductionOnlyStageError", "RECEIPT_ROLE", "ROLE", "STAGES",
    "STAGE_RECEIPT_ROLE", "StageObserver", "run_task", "validate_receipt",
    "validate_result", "validate_stage_receipt",
]
