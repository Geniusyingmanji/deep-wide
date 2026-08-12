"""Build-only outer physical hard cap and content-free stage observer.

The frozen V2.51.35 parent permits a verified-gain path with four provider
forwards and fourteen physical fetches even though the public V2.52.48
protocol declared three and ten.  Synthetic verified-gain fixtures prove that
the fourth provider forward can change a prediction, so silently imposing the
smaller declaration would be quality-destructive.  This append-only seam
instead enforces the parent's true 4/14 physical ceiling in front of actual
clients; a successor protocol must declare that ceiling honestly.  A rejected
batch is never partially executed, so frozen nested accounting is not forged.
The stage observer mirrors V2.52.32 without changing a successful runtime
result and exposes only finite stage and exception-type counters.

This module is build-only.  It grants no external forward, evaluator,
benchmark, activation, retry, or signed-credit authority.
"""

from __future__ import annotations

import copy
import hashlib
import threading
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v25180_quote_aware_production_runtime as effect_parent
from . import v25188_export_failure_tolerant_same_response_runtime as frozen_parent
from . import v25232_header_totality_shadow_runtime as parent
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25253_outer_physical_cap_observed_runtime_v1"
BUDGET_RECEIPT_ROLE = "v25253_content_free_outer_physical_cap_receipt"
STAGE_RECEIPT_ROLE = "v25253_content_free_runtime_stage_receipt"
QUERY_CAP = 4
FETCH_CAP = 14
MODEL_CAP = 4
STAGES = (
    "boundary",
    "sparse_parent_run_and_validate",
    "effect_rebuild",
    "parent_freeze",
    "shadow_receipt",
    "result_envelope_validate",
)
EFFECT_STAGES = (
    "shared_first_wave_search",
    "shared_first_wave_fetch",
    "shared_second_wave_union_search",
    "shared_second_wave_union_fetch",
    "model_plan",
    "model_grounded_plan",
    "model_production",
    "model_revision",
    "model_other",
)


class PhysicalEffectBudgetExceeded(RuntimeError):
    """Content-free signal raised before an over-cap physical effect."""

    def __init__(self, effect_kind: str) -> None:
        super().__init__(f"V2.52.53 {effect_kind} physical effect cap reached")
        self.effect_kind = effect_kind


class ObservedRuntimeStageError(RuntimeError):
    """Safe outer failure with a sealed content-free stage receipt."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        checked = validate_stage_receipt(receipt)
        super().__init__("V2.52.53 observed runtime stage failed")
        self.stage_receipt = checked


class PhysicalEffectBudget:
    """One shared per-task budget across model and both search phases."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requested = {"query": 0, "fetch": 0, "model": 0}
        self._admitted = {"query": 0, "fetch": 0, "model": 0}
        self._rejected = {"query": 0, "fetch": 0, "model": 0}
        self._attempt_batches = {"query": 0, "fetch": 0, "model": 0}
        self._rejected_batches = {"query": 0, "fetch": 0, "model": 0}
        self._rejection_stages = {stage: 0 for stage in EFFECT_STAGES}

    @staticmethod
    def _cap(kind: str) -> int:
        return {"query": QUERY_CAP, "fetch": FETCH_CAP, "model": MODEL_CAP}[kind]

    def reserve(self, kind: str, count: int, *, stage: str) -> None:
        if (
            kind not in {"query", "fetch", "model"}
            or stage not in EFFECT_STAGES
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
        ):
            raise ValueError("V2.52.53 physical budget reservation drifted")
        if count == 0:
            return
        with self._lock:
            self._attempt_batches[kind] += 1
            self._requested[kind] += count
            if self._admitted[kind] + count > self._cap(kind):
                self._rejected[kind] += count
                self._rejected_batches[kind] += 1
                self._rejection_stages[stage] += 1
                raise PhysicalEffectBudgetExceeded(kind)
            self._admitted[kind] += count

    def receipt(self) -> dict[str, Any]:
        with self._lock:
            requested = dict(self._requested)
            admitted = dict(self._admitted)
            rejected = dict(self._rejected)
            batches = dict(self._attempt_batches)
            rejected_batches = dict(self._rejected_batches)
            stages = dict(self._rejection_stages)
        value = {
            "artifact_version": 1,
            "role": BUDGET_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "query_cap": QUERY_CAP,
            "fetch_cap": FETCH_CAP,
            "model_cap": MODEL_CAP,
            "query_requested_count": requested["query"],
            "query_admitted_count": admitted["query"],
            "query_rejected_count": rejected["query"],
            "fetch_requested_count": requested["fetch"],
            "fetch_admitted_count": admitted["fetch"],
            "fetch_rejected_count": rejected["fetch"],
            "model_requested_count": requested["model"],
            "model_admitted_count": admitted["model"],
            "model_rejected_count": rejected["model"],
            "query_batch_attempt_count": batches["query"],
            "fetch_batch_attempt_count": batches["fetch"],
            "model_call_attempt_count": batches["model"],
            "query_rejected_batch_count": rejected_batches["query"],
            "fetch_rejected_batch_count": rejected_batches["fetch"],
            "model_rejected_call_count": rejected_batches["model"],
            "rejection_stage_counts": stages,
            "reservation_precedes_slot_provider_search_fetch_or_network_effect": True,
            "over_cap_batch_is_rejected_atomically_before_underlying_effect": True,
            "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "external_forward_evaluator_or_benchmark_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_budget_receipt(value)


def validate_budget_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integer_fields = (
        "query_cap", "fetch_cap", "model_cap",
        "query_requested_count", "query_admitted_count", "query_rejected_count",
        "fetch_requested_count", "fetch_admitted_count", "fetch_rejected_count",
        "model_requested_count", "model_admitted_count", "model_rejected_count",
        "query_batch_attempt_count", "fetch_batch_attempt_count", "model_call_attempt_count",
        "query_rejected_batch_count", "fetch_rejected_batch_count", "model_rejected_call_count",
    )
    true_flags = (
        "reservation_precedes_slot_provider_search_fetch_or_network_effect",
        "over_cap_batch_is_rejected_atomically_before_underlying_effect",
    )
    false_flags = (
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "external_forward_evaluator_or_benchmark_authorized",
    )
    stages = copied.get("rejection_stage_counts")
    expected = {
        "artifact_version", "role", "policy_id", *integer_fields,
        "rejection_stage_counts", *true_flags, *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != BUDGET_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or (copied["query_cap"], copied["fetch_cap"], copied["model_cap"])
        != (QUERY_CAP, FETCH_CAP, MODEL_CAP)
        or copied["query_admitted_count"] > QUERY_CAP
        or copied["fetch_admitted_count"] > FETCH_CAP
        or copied["model_admitted_count"] > MODEL_CAP
        or copied["query_requested_count"]
        != copied["query_admitted_count"] + copied["query_rejected_count"]
        or copied["fetch_requested_count"]
        != copied["fetch_admitted_count"] + copied["fetch_rejected_count"]
        or copied["model_requested_count"]
        != copied["model_admitted_count"] + copied["model_rejected_count"]
        or not isinstance(stages, Mapping)
        or set(stages) != set(EFFECT_STAGES)
        or any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in stages.values())
        or sum(stages.values())
        != copied["query_rejected_batch_count"]
        + copied["fetch_rejected_batch_count"]
        + copied["model_rejected_call_count"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.53 physical budget receipt drifted")
    return copied


class HardCappedModelLimiter(DeadlineAwareGlobalModelSlotLimiter):
    """Type-compatible proxy that rejects a fifth call before slot acquire."""

    def __init__(self, inner: DeadlineAwareGlobalModelSlotLimiter, budget: PhysicalEffectBudget) -> None:
        if not isinstance(inner, DeadlineAwareGlobalModelSlotLimiter) or not isinstance(budget, PhysicalEffectBudget):
            raise TypeError("V2.52.53 hard-capped model boundary drifted")
        self._inner_limiter = inner
        self._budget = budget
        self._synthesis_entry_count = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner_limiter, name)

    def _stage(self, system: str) -> str:
        if system == effect_parent.score.PLAN_SYSTEM:
            return "model_plan"
        if system.startswith(
            effect_parent.parent.parent.sparse_parent.target_plan.SYSTEM_PROMPT
        ):
            return "model_grounded_plan"
        if system == effect_parent.score.SYNTHESIS_SYSTEM:
            stage = "model_production" if self._synthesis_entry_count == 0 else "model_revision"
            self._synthesis_entry_count += 1
            return stage
        return "model_other"

    def complete(
        self, system: str, user: str, *, max_output_tokens: int, json_mode: bool = False
    ) -> Any:
        stage = self._stage(str(system))
        self._budget.reserve("model", 1, stage=stage)
        return self._inner_limiter.complete(
            system, user, max_output_tokens=max_output_tokens, json_mode=json_mode
        )

    def remaining_effect_seconds(self) -> float:
        return float(self._inner_limiter.remaining_effect_seconds())

    def receipt(self) -> dict[str, Any]:
        return self._inner_limiter.receipt()


class HardCappedSearchClient(RobustLatePageBoundSearchClient):
    """Type-compatible proxy sharing query/fetch caps across both phases."""

    def __init__(
        self,
        inner: RobustLatePageBoundSearchClient,
        budget: PhysicalEffectBudget,
        *,
        phase: str,
    ) -> None:
        if (
            not isinstance(inner, RobustLatePageBoundSearchClient)
            or not isinstance(budget, PhysicalEffectBudget)
            or phase not in parent.PHASES
        ):
            raise TypeError("V2.52.53 hard-capped search boundary drifted")
        self._inner_search = inner
        self._budget = budget
        self._phase = phase

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner_search, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> Any:
        values = list(queries)
        self._budget.reserve("query", len(values), stage=f"{self._phase}_search")
        return self._inner_search.search_many(values, **kwargs)

    def fetch_urls(self, requests: Sequence[Mapping[str, str]]) -> Any:
        values = list(requests)
        self._budget.reserve("fetch", len(values), stage=f"{self._phase}_fetch")
        return self._inner_search.fetch_urls(values)

    def late_page_projection_receipt(self) -> dict[str, Any]:
        return self._inner_search.late_page_projection_receipt()

    def parent_prefix_for(self, url: str) -> str:
        return str(self._inner_search.parent_prefix_for(url))

    def remaining_effect_seconds(self) -> float:
        return float(self._inner_search.remaining_effect_seconds())


class RuntimeStageObserver:
    def __init__(self, budget: PhysicalEffectBudget) -> None:
        if not isinstance(budget, PhysicalEffectBudget):
            raise TypeError("V2.52.53 stage observer budget drifted")
        self._budget = budget
        self._entered = {stage: 0 for stage in STAGES}
        self._completed = {stage: 0 for stage in STAGES}
        self._failure_stage: str | None = None
        self._failure_type: str | None = None

    def run(self, stage: str, function: Callable[[], Any]) -> Any:
        if stage not in STAGES or self._failure_stage is not None or self._entered[stage] != 0:
            raise ValueError("V2.52.53 stage transition drifted")
        self._entered[stage] = 1
        try:
            output = function()
        except BaseException as exc:
            self._failure_stage = stage
            name = type(exc).__name__
            self._failure_type = name if name and len(name) <= 128 else "Exception"
            raise ObservedRuntimeStageError(self.receipt()) from None
        self._completed[stage] = 1
        return output

    def receipt(self) -> dict[str, Any]:
        value = {
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
    expected = {
        "artifact_version", "role", "policy_id", "stage_entered_counts",
        "stage_completed_counts", "failure_present", "failure_stage", "failure_type",
        "outer_physical_budget_receipt", *true_flags, *false_flags,
        "receipt_payload_sha256",
    }
    failure = copied.get("failure_present") is True
    if (
        set(copied) != expected
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
        or validate_budget_receipt(budget) != dict(budget)
        or failure
        and completed[copied["failure_stage"]] != 0
        or not failure
        and (any(entered[stage] != 1 for stage in STAGES) or any(completed[stage] != 1 for stage in STAGES))
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.53 runtime stage receipt drifted")
    return copied


def run_observed_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    budget: PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Mirror V2.52.32 and return its exact result plus a side receipt."""

    observer = RuntimeStageObserver(budget)
    visible = observer.run(
        "boundary",
        lambda: effect_parent.parent.parent.sparse_parent._validate_boundary(
            task, model=model, searches=searches, limits=limits
        ),
    )
    provider = parent.HeaderTotalityShadowProvider(
        model,
        question=visible["question"],
        first_wave_search=searches[parent.FIRST_PHASE],
        limits=limits,
    )
    sparse_result = observer.run(
        "sparse_parent_run_and_validate",
        lambda: effect_parent.parent.parent.sparse_parent.validate_result(
            effect_parent.parent.parent.sparse_parent.run_task(
                visible,
                model=provider,
                searches=searches,
                limits=limits,
                monotonic=monotonic,
            )
        ),
    )
    effect_result = observer.run(
        "effect_rebuild", lambda: parent._effect_result(provider, sparse_result)
    )
    parent_result = observer.run(
        "parent_freeze", lambda: parent._frozen_parent_result(effect_result)
    )
    receipt = observer.run(
        "shadow_receipt", lambda: parent._receipt(provider, parent_result)
    )

    def envelope() -> dict[str, Any]:
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": parent.ROLE,
            "policy_id": parent.POLICY_ID,
            "opaque_id": parent_result["opaque_id"],
            "status": "terminal",
            "predictions": copy.deepcopy(parent_result["predictions"]),
            "prediction_sha256": copy.deepcopy(parent_result["prediction_sha256"]),
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
        return parent.validate_result(value)

    result = observer.run("result_envelope_validate", envelope)
    return result, observer.receipt()


__all__ = [
    "BUDGET_RECEIPT_ROLE", "EFFECT_STAGES", "FETCH_CAP", "HardCappedModelLimiter",
    "HardCappedSearchClient", "MODEL_CAP", "ObservedRuntimeStageError", "POLICY_ID",
    "PhysicalEffectBudget", "PhysicalEffectBudgetExceeded", "QUERY_CAP", "STAGES",
    "STAGE_RECEIPT_ROLE", "RuntimeStageObserver", "run_observed_task",
    "validate_budget_receipt", "validate_stage_receipt",
]
