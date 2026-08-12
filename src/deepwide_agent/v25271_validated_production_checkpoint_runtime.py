"""Build-only validated-production checkpoint and finite microstage runtime.

V2.52.67 showed that a broad ``sparse_production`` stage can turn a table that
was already normalized into an outer fallback when later parent binding or
result-envelope validation raises.  This append-only successor captures the
production table immediately after the frozen production normalizer returns.
Later parent/envelope failures may discard only the invalid auxiliary parent
envelope; they cannot discard the sealed production checkpoint.  A failure
before any checkpoint exists remains fail-closed as a visible-schema Unknown
table.

The provider, retrieval, prompts, evidence, and physical caps are unchanged.
The normal path invokes the same parent exactly once and performs no extra
network/model/search/fetch effect.  This module has no filesystem, process,
environment, credential, evaluator, benchmark-launch, or signed-credit
capability.  It is synthetic-build-only until a separate protocol authorizes
a fresh external reliability population.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v25135_sparse_production_runtime as sparse
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25265_production_only_totality_runtime as parent
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25271_validated_production_checkpoint_runtime_v1"
ROLE = "v25271_validated_production_checkpoint_runtime_result"
RECOVERY_ROLE = "v25271_validated_production_checkpoint_recovery_result"
CHECKPOINT_ROLE = "v25271_validated_production_checkpoint"
RECEIPT_ROLE = "v25271_content_free_checkpoint_recovery_receipt"
STAGE_RECEIPT_ROLE = "v25271_content_free_checkpoint_microstage_receipt"
CHECKPOINT_KINDS = ("validated_model_output", "deterministic_fallback")
STAGES = (
    "boundary_validate",
    "paired_parent_run_and_validate",
    "effect_accounting",
    "production_checkpoint_select",
    "parent_prediction_binding",
    "result_envelope_build",
    "result_envelope_validate",
)
RECOVERY_DISPOSITIONS = (
    "clean_validated_production",
    "clean_deterministic_fallback",
    "validated_production_preserved_after_post_checkpoint_failure",
    "deterministic_fallback_preserved_after_post_checkpoint_failure",
    "visible_fallback_before_checkpoint",
    "untrusted_checkpoint_rejected",
    "checkpoint_unrecoverable_accounting_failure",
)
RECOVERABLE_POST_CHECKPOINT_STAGES = (
    "paired_parent_run_and_validate",
    "parent_prediction_binding",
    "result_envelope_build",
    "result_envelope_validate",
)
PHASES = sparse.PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


class ProductionCheckpointStageError(RuntimeError):
    """Finite content-free signal for an unrecoverable microstage failure."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.stage_receipt = validate_stage_receipt(receipt)
        super().__init__("V2.52.71 production checkpoint runtime stage failed")


def build_checkpoint(
    prediction: str,
    *,
    provider_output_valid: bool,
    production_failure_type: str | None,
) -> dict[str, Any]:
    if not isinstance(prediction, str) or not prediction:
        raise ValueError("V2.52.71 checkpoint prediction is empty")
    kind = (
        "validated_model_output" if provider_output_valid else "deterministic_fallback"
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CHECKPOINT_ROLE,
        "policy_id": POLICY_ID,
        "checkpoint_kind": kind,
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "production_provider_output_valid": bool(provider_output_valid),
        "production_failure_type": production_failure_type,
        "created_immediately_after_frozen_production_normalizer_or_deterministic_fallback": True,
        "checkpoint_precedes_parent_binding_receipt_and_result_envelope": True,
        "contains_only_same_forward_visible_input_and_public_page_derived_output": True,
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
    valid = copied.get("production_provider_output_valid") is True
    true_flags = (
        "created_immediately_after_frozen_production_normalizer_or_deterministic_fallback",
        "checkpoint_precedes_parent_binding_receipt_and_result_envelope",
        "contains_only_same_forward_visible_input_and_public_page_derived_output",
    )
    false_flags = (
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
            "checkpoint_kind",
            "prediction",
            "prediction_sha256",
            "production_provider_output_valid",
            "production_failure_type",
            *true_flags,
            *false_flags,
            "checkpoint_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CHECKPOINT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("checkpoint_kind") not in CHECKPOINT_KINDS
        or not isinstance(prediction, str)
        or not prediction
        or copied.get("prediction_sha256")
        != hashlib.sha256(prediction.encode()).hexdigest()
        or not isinstance(copied.get("production_provider_output_valid"), bool)
        or copied["checkpoint_kind"]
        != ("validated_model_output" if valid else "deterministic_fallback")
        or valid
        and copied.get("production_failure_type") is not None
        or not valid
        and (
            not isinstance(copied.get("production_failure_type"), str)
            or not copied["production_failure_type"]
            or len(copied["production_failure_type"]) > 128
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.71 production checkpoint drifted")
    return copied


class CheckpointingProductionModel(parent.ProductionOnlySparseModel):
    """The frozen production-only provider plus an in-memory post-normalizer seal."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.production_checkpoint: dict[str, Any] | None = None

    def _production(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool,
    ) -> Any:
        response = super()._production(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if not isinstance(self.production_prediction, str) or not self.production_prediction:
            raise ValueError("V2.52.71 production returned without a table")
        self.production_checkpoint = build_checkpoint(
            self.production_prediction,
            provider_output_valid=self.production_provider_valid_output,
            production_failure_type=self.production_failure_type,
        )
        return response


class MicrostageObserver:
    """Ordered finite-stage observer that allows explicit recovery after failure."""

    def __init__(self, budget: cap.PhysicalEffectBudget) -> None:
        if not isinstance(budget, cap.PhysicalEffectBudget):
            raise TypeError("V2.52.71 stage budget drifted")
        self._budget = budget
        self._next = 0
        self._entered = {stage: 0 for stage in STAGES}
        self._completed = {stage: 0 for stage in STAGES}
        self._failures: dict[str, str | None] = {stage: None for stage in STAGES}

    def attempt(self, stage: str, function: Callable[[], Any]) -> tuple[bool, Any]:
        if self._next >= len(STAGES) or stage != STAGES[self._next]:
            raise ValueError("V2.52.71 microstage transition drifted")
        self._next += 1
        self._entered[stage] = 1
        try:
            output = function()
        except BaseException as exc:
            self._failures[stage] = _safe_failure(exc)
            return False, None
        self._completed[stage] = 1
        return True, output

    @property
    def failures(self) -> dict[str, str | None]:
        return dict(self._failures)

    def receipt(
        self,
        *,
        checkpoint_kind: str | None,
        parent_result_retained: bool,
        disposition: str,
    ) -> dict[str, Any]:
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": STAGE_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "stage_entered_counts": dict(self._entered),
            "stage_completed_counts": dict(self._completed),
            "stage_failure_types": dict(self._failures),
            "failure_count": sum(value is not None for value in self._failures.values()),
            "checkpoint_kind": checkpoint_kind,
            "parent_result_retained": bool(parent_result_retained),
            "recovery_disposition": disposition,
            "outer_physical_budget_receipt": self._budget.receipt(),
            "observer_does_not_change_successful_prediction_cost_or_effect": True,
            "post_checkpoint_failure_discards_only_auxiliary_parent_envelope": True,
            "pre_checkpoint_failure_uses_only_visible_schema_fallback": True,
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
    failures = copied.get("stage_failure_types")
    budget = copied.get("outer_physical_budget_receipt")
    checkpoint_kind = copied.get("checkpoint_kind")
    disposition = copied.get("recovery_disposition")
    true_flags = (
        "observer_does_not_change_successful_prediction_cost_or_effect",
        "post_checkpoint_failure_discards_only_auxiliary_parent_envelope",
        "pre_checkpoint_failure_uses_only_visible_schema_fallback",
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
            "stage_entered_counts",
            "stage_completed_counts",
            "stage_failure_types",
            "failure_count",
            "checkpoint_kind",
            "parent_result_retained",
            "recovery_disposition",
            "outer_physical_budget_receipt",
            *true_flags,
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(entered, Mapping)
        or not isinstance(completed, Mapping)
        or not isinstance(failures, Mapping)
        or set(entered) != set(STAGES)
        or set(completed) != set(STAGES)
        or set(failures) != set(STAGES)
        or any(entered[stage] not in {0, 1} for stage in STAGES)
        or any(completed[stage] not in {0, 1} for stage in STAGES)
        or any(completed[stage] > entered[stage] for stage in STAGES)
        or any(
            failures[stage] is not None
            and (
                not isinstance(failures[stage], str)
                or not failures[stage]
                or len(failures[stage]) > 128
                or completed[stage] != 0
            )
            for stage in STAGES
        )
        or copied.get("failure_count")
        != sum(failures[stage] is not None for stage in STAGES)
        or checkpoint_kind is not None and checkpoint_kind not in CHECKPOINT_KINDS
        or not isinstance(copied.get("parent_result_retained"), bool)
        or disposition not in RECOVERY_DISPOSITIONS
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or disposition == "clean_validated_production"
        and (
            checkpoint_kind != "validated_model_output"
            or not copied["parent_result_retained"]
            or copied["failure_count"] != 0
            or any(entered[stage] != 1 or completed[stage] != 1 for stage in STAGES)
        )
        or disposition == "clean_deterministic_fallback"
        and (
            checkpoint_kind != "deterministic_fallback"
            or not copied["parent_result_retained"]
            or copied["failure_count"] != 0
            or any(entered[stage] != 1 or completed[stage] != 1 for stage in STAGES)
        )
        or disposition
        in {
            "validated_production_preserved_after_post_checkpoint_failure",
            "deterministic_fallback_preserved_after_post_checkpoint_failure",
        }
        and (
            checkpoint_kind
            != (
                "validated_model_output"
                if disposition.startswith("validated")
                else "deterministic_fallback"
            )
            or copied["parent_result_retained"]
            or copied["failure_count"] < 1
            or not any(failures[stage] is not None for stage in RECOVERABLE_POST_CHECKPOINT_STAGES)
        )
        or disposition == "visible_fallback_before_checkpoint"
        and (
            checkpoint_kind is not None
            or copied["parent_result_retained"]
            or not any(
                failures[stage] is not None
                for stage in (
                    "boundary_validate",
                    "paired_parent_run_and_validate",
                    "production_checkpoint_select",
                )
            )
        )
        or disposition == "checkpoint_unrecoverable_accounting_failure"
        and (
            checkpoint_kind not in CHECKPOINT_KINDS
            or copied["parent_result_retained"]
            or failures["effect_accounting"] is None
        )
        or disposition == "untrusted_checkpoint_rejected"
        and (
            checkpoint_kind is not None
            or copied["parent_result_retained"]
            or failures["production_checkpoint_select"] is None
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.71 microstage receipt drifted")
    return copied


def _visible_fallback(question: str) -> str:
    columns, _source = sparse.parent._total_columns({}, question)
    return sparse.counters._fallback(columns)


def _cost_snapshot(
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    model_before: Mapping[str, int],
    search_before: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
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
    return {
        "model": model_cost,
        "search": search_cost,
        "system_total_tokens": model_cost["total_tokens"]
        + sum(search_cost[phase]["total_tokens"] for phase in PHASES),
    }


def _retain_parent_if_bound(
    parent_result: Mapping[str, Any] | None, prediction: str
) -> dict[str, Any] | None:
    if parent_result is None:
        return None
    checked = sparse.parent.validate_result(parent_result)
    if (
        checked["predictions"][sparse.CONTROL_ARM] != prediction
        or checked["predictions"][sparse.CANDIDATE_ARM] != prediction
    ):
        raise ValueError("V2.52.71 parent prediction does not bind checkpoint")
    return checked


def _disposition(
    checkpoint: Mapping[str, Any] | None,
    parent_result: Mapping[str, Any] | None,
    failures: Mapping[str, str | None],
) -> str:
    if checkpoint is None:
        return "visible_fallback_before_checkpoint"
    prefix = (
        "validated_production"
        if checkpoint["checkpoint_kind"] == "validated_model_output"
        else "deterministic_fallback"
    )
    if parent_result is not None and not any(failures.values()):
        return f"clean_{prefix}"
    return f"{prefix}_preserved_after_post_checkpoint_failure"


def _precheckpoint_result(
    *,
    observer: MicrostageObserver,
    visible: Mapping[str, str],
    provider: CheckpointingProductionModel,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    model_before: Mapping[str, int],
    search_before: Mapping[str, Mapping[str, int]],
    budget: cap.PhysicalEffectBudget,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if provider.production_checkpoint is not None:
        raise RuntimeError("V2.52.71 pre-checkpoint recovery saw a checkpoint")
    if observer._next == STAGES.index("effect_accounting"):
        cost_ok, cost = observer.attempt(
            "effect_accounting",
            lambda: _cost_snapshot(model, searches, model_before, search_before),
        )
        if not cost_ok:
            raise ProductionCheckpointStageError(
                observer.receipt(
                    checkpoint_kind=None,
                    parent_result_retained=False,
                    disposition="visible_fallback_before_checkpoint",
                )
            )
    else:
        cost = _cost_snapshot(model, searches, model_before, search_before)
    if observer._next == STAGES.index("production_checkpoint_select"):
        observer.attempt("production_checkpoint_select", lambda: None)
    if observer._next == STAGES.index("parent_prediction_binding"):
        observer.attempt("parent_prediction_binding", lambda: None)

    prediction = _visible_fallback(visible["question"])
    disposition = "visible_fallback_before_checkpoint"
    receipt = _content_free_receipt(
        provider=provider,
        checkpoint=None,
        retained_parent=None,
        disposition=disposition,
        cost=cost,
        budget=budget,
        failures=observer.failures,
    )
    build_ok, result = observer.attempt(
        "result_envelope_build",
        lambda: _build_result(
            visible=visible,
            prediction=prediction,
            prediction_kind="visible_fallback",
            checkpoint=None,
            retained_parent=None,
            cost=cost,
            receipt=receipt,
        ),
    )
    if not build_ok:
        raise ProductionCheckpointStageError(
            observer.receipt(
                checkpoint_kind=None,
                parent_result_retained=False,
                disposition=disposition,
            )
        )
    validate_ok, checked = observer.attempt(
        "result_envelope_validate", lambda: validate_result(result)
    )
    if not validate_ok:
        raise ProductionCheckpointStageError(
            observer.receipt(
                checkpoint_kind=None,
                parent_result_retained=False,
                disposition=disposition,
            )
        )
    return checked, observer.receipt(
        checkpoint_kind=None,
        parent_result_retained=False,
        disposition=disposition,
    )


def _content_free_receipt(
    *,
    provider: CheckpointingProductionModel,
    checkpoint: Mapping[str, Any] | None,
    retained_parent: Mapping[str, Any] | None,
    disposition: str,
    cost: Mapping[str, Any],
    budget: cap.PhysicalEffectBudget,
    failures: Mapping[str, str | None],
) -> dict[str, Any]:
    budget_receipt = cap.validate_budget_receipt(budget.receipt())
    checkpoint_kind = None if checkpoint is None else checkpoint["checkpoint_kind"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "checkpoint_kind": checkpoint_kind,
        "checkpoint_present": checkpoint is not None,
        "checkpoint_provider_output_valid": bool(
            checkpoint is not None and checkpoint["production_provider_output_valid"]
        ),
        "parent_result_retained": retained_parent is not None,
        "recovery_disposition": disposition,
        "plan_provider_forward_count": provider.plan_provider_forward_count,
        "grounded_plan_provider_forward_count": provider.grounded_plan_provider_forward_count,
        "production_synthesis_provider_forward_count": provider.production_synthesis_provider_forward_count,
        "revision_provider_forward_count": provider.revision_synthesis_provider_forward_count,
        "provider_forward_count": (
            provider.plan_provider_forward_count
            + provider.grounded_plan_provider_forward_count
            + provider.production_synthesis_provider_forward_count
            + provider.revision_synthesis_provider_forward_count
        ),
        "model_provider_request_count": int(cost["model"]["requests"]),
        "model_provider_attempt_count": int(cost["model"]["attempts"]),
        "physical_query_count": budget_receipt["query_admitted_count"],
        "physical_fetch_count": budget_receipt["fetch_admitted_count"],
        "physical_model_forward_count": budget_receipt["model_admitted_count"],
        "system_total_tokens": int(cost["system_total_tokens"]),
        "microstage_failure_count": sum(value is not None for value in failures.values()),
        "post_checkpoint_recoverable_failure_present": bool(
            checkpoint is not None
            and any(failures[stage] is not None for stage in RECOVERABLE_POST_CHECKPOINT_STAGES)
        ),
        "validated_checkpoint_never_replaced_by_visible_fallback": True,
        "normal_path_provider_search_fetch_prompt_and_prediction_unchanged": True,
        "second_synthesis_entry_is_local_identity_replay": True,
        "checkpoint_recovery_does_not_add_model_search_or_fetch_effect": True,
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential": False,
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
    counts = (
        "plan_provider_forward_count",
        "grounded_plan_provider_forward_count",
        "production_synthesis_provider_forward_count",
        "revision_provider_forward_count",
        "provider_forward_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "physical_query_count",
        "physical_fetch_count",
        "physical_model_forward_count",
        "system_total_tokens",
        "microstage_failure_count",
        "positive_signed_credit_count",
    )
    dynamic_bools = (
        "checkpoint_present",
        "checkpoint_provider_output_valid",
        "parent_result_retained",
        "post_checkpoint_recoverable_failure_present",
    )
    true_flags = (
        "validated_checkpoint_never_replaced_by_visible_fallback",
        "normal_path_provider_search_fetch_prompt_and_prediction_unchanged",
        "second_synthesis_entry_is_local_identity_replay",
        "checkpoint_recovery_does_not_add_model_search_or_fetch_effect",
    )
    false_flags = (
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "external_forward_evaluator_or_benchmark_authorized",
    )
    checkpoint_kind = copied.get("checkpoint_kind")
    disposition = copied.get("recovery_disposition")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "checkpoint_kind",
            "recovery_disposition",
            *counts,
            *dynamic_bools,
            *true_flags,
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or checkpoint_kind is not None and checkpoint_kind not in CHECKPOINT_KINDS
        or disposition not in RECOVERY_DISPOSITIONS
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic_bools)
        or copied["checkpoint_present"] is not (checkpoint_kind is not None)
        or copied["checkpoint_provider_output_valid"]
        is not (checkpoint_kind == "validated_model_output")
        or copied["plan_provider_forward_count"] not in {0, 1}
        or copied["grounded_plan_provider_forward_count"] not in {0, 1}
        or copied["production_synthesis_provider_forward_count"] not in {0, 1}
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
        or copied["checkpoint_present"]
        and copied["production_synthesis_provider_forward_count"] != 1
        or not copied["checkpoint_present"]
        and copied["production_synthesis_provider_forward_count"] != 0
        or copied["positive_signed_credit_count"] != 0
        or disposition.startswith("clean_")
        is not bool(copied["parent_result_retained"] and copied["microstage_failure_count"] == 0)
        or copied["post_checkpoint_recoverable_failure_present"]
        is not bool(
            copied["checkpoint_present"]
            and disposition.endswith("preserved_after_post_checkpoint_failure")
        )
        or disposition == "visible_fallback_before_checkpoint"
        and (copied["checkpoint_present"] or copied["parent_result_retained"])
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.71 checkpoint recovery receipt drifted")
    return copied


def _build_result(
    *,
    visible: Mapping[str, str],
    prediction: str,
    prediction_kind: str,
    checkpoint: Mapping[str, Any] | None,
    retained_parent: Mapping[str, Any] | None,
    cost: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "prediction_kind": prediction_kind,
        "production_checkpoint": None if checkpoint is None else copy.deepcopy(checkpoint),
        "production_checkpoint_payload_sha256": (
            None if checkpoint is None else checkpoint["checkpoint_payload_sha256"]
        ),
        "parent_result": None if retained_parent is None else copy.deepcopy(retained_parent),
        "parent_result_payload_sha256": (
            None if retained_parent is None else retained_parent["result_payload_sha256"]
        ),
        "cost": copy.deepcopy(cost),
        "content_free_receipt": copy.deepcopy(receipt),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def _build_recovery_result(
    *,
    visible: Mapping[str, str],
    checkpoint: Mapping[str, Any],
    cost: Mapping[str, Any],
    receipt: Mapping[str, Any],
    observer: MicrostageObserver,
) -> dict[str, Any]:
    checked_checkpoint = validate_checkpoint(checkpoint)
    checked_receipt = validate_receipt(receipt)
    failures = observer.failures
    active = [
        stage
        for stage in RECOVERABLE_POST_CHECKPOINT_STAGES
        if failures[stage] is not None
    ]
    if not active:
        raise ValueError("V2.52.71 recovery requires a post-checkpoint failure")
    prediction = checked_checkpoint["prediction"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECOVERY_ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "prediction_kind": (
            "model_generated"
            if checked_checkpoint["checkpoint_kind"] == "validated_model_output"
            else "fallback"
        ),
        "production_checkpoint": copy.deepcopy(checked_checkpoint),
        "production_checkpoint_payload_sha256": checked_checkpoint[
            "checkpoint_payload_sha256"
        ],
        "parent_result": None,
        "parent_result_payload_sha256": None,
        "cost": copy.deepcopy(dict(cost)),
        "content_free_receipt": copy.deepcopy(checked_receipt),
        "recovered_failure_stages": active,
        "recovered_failure_types": {stage: failures[stage] for stage in active},
        "recovery_envelope_is_independent_of_failed_parent_or_primary_envelope": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_recovery_result(value)


def validate_recovery_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    prediction = copied.get("prediction")
    checkpoint_raw = copied.get("production_checkpoint")
    receipt_raw = copied.get("content_free_receipt")
    cost = copied.get("cost")
    stages = copied.get("recovered_failure_stages")
    types = copied.get("recovered_failure_types")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "status",
            "prediction",
            "prediction_sha256",
            "prediction_kind",
            "production_checkpoint",
            "production_checkpoint_payload_sha256",
            "parent_result",
            "parent_result_payload_sha256",
            "cost",
            "content_free_receipt",
            "recovered_failure_stages",
            "recovered_failure_types",
            "recovery_envelope_is_independent_of_failed_parent_or_primary_envelope",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECOVERY_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(copied.get("opaque_id"), str)
        or sparse.score.OPAQUE_ID.fullmatch(copied["opaque_id"]) is None
        or not isinstance(prediction, str)
        or not prediction
        or copied.get("prediction_sha256")
        != hashlib.sha256(prediction.encode()).hexdigest()
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or not isinstance(checkpoint_raw, Mapping)
        or not isinstance(receipt_raw, Mapping)
        or not isinstance(cost, Mapping)
        or copied.get("parent_result") is not None
        or copied.get("parent_result_payload_sha256") is not None
        or not isinstance(stages, list)
        or not stages
        or any(stage not in RECOVERABLE_POST_CHECKPOINT_STAGES for stage in stages)
        or len(stages) != len(set(stages))
        or not isinstance(types, Mapping)
        or list(types) != stages
        or any(
            not isinstance(types[stage], str)
            or not types[stage]
            or len(types[stage]) > 128
            for stage in stages
        )
        or copied.get(
            "recovery_envelope_is_independent_of_failed_parent_or_primary_envelope"
        )
        is not True
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
        raise ValueError("V2.52.71 recovery result envelope drifted")
    checkpoint = validate_checkpoint(checkpoint_raw)
    receipt = validate_receipt(receipt_raw)
    if (
        copied.get("production_checkpoint_payload_sha256")
        != checkpoint["checkpoint_payload_sha256"]
        or prediction != checkpoint["prediction"]
        or copied["prediction_kind"]
        != (
            "model_generated"
            if checkpoint["checkpoint_kind"] == "validated_model_output"
            else "fallback"
        )
        or receipt["checkpoint_kind"] != checkpoint["checkpoint_kind"]
        or receipt["parent_result_retained"] is not False
        or receipt["recovery_disposition"]
        != (
            "validated_production_preserved_after_post_checkpoint_failure"
            if checkpoint["checkpoint_kind"] == "validated_model_output"
            else "deterministic_fallback_preserved_after_post_checkpoint_failure"
        )
        or receipt["post_checkpoint_recoverable_failure_present"] is not True
        or receipt["microstage_failure_count"] < len(stages)
        or set(cost) != {"model", "search", "system_total_tokens"}
        or not isinstance(cost.get("model"), Mapping)
        or set(cost["model"]) != set(sparse._MODEL_COUNTERS)
        or set(cost.get("search") or {}) != set(PHASES)
        or any(
            not isinstance(cost["search"].get(phase), Mapping)
            or set(cost["search"][phase]) != set(sparse._SEARCH_COUNTERS)
            for phase in PHASES
        )
        or cost.get("system_total_tokens")
        != cost["model"]["total_tokens"]
        + sum(cost["search"][phase]["total_tokens"] for phase in PHASES)
        or receipt["model_provider_request_count"] != cost["model"]["requests"]
        or receipt["model_provider_attempt_count"] != cost["model"]["attempts"]
        or receipt["system_total_tokens"] != cost["system_total_tokens"]
    ):
        raise ValueError("V2.52.71 recovery checkpoint binding drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if copied.get("role") == RECOVERY_ROLE:
        return validate_recovery_result(copied)
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    prediction = copied.get("prediction")
    checkpoint_raw = copied.get("production_checkpoint")
    parent_raw = copied.get("parent_result")
    receipt_raw = copied.get("content_free_receipt")
    cost = copied.get("cost")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "status",
            "prediction",
            "prediction_sha256",
            "prediction_kind",
            "production_checkpoint",
            "production_checkpoint_payload_sha256",
            "parent_result",
            "parent_result_payload_sha256",
            "cost",
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
        or not isinstance(copied.get("opaque_id"), str)
        or sparse.score.OPAQUE_ID.fullmatch(copied["opaque_id"]) is None
        or not isinstance(prediction, str)
        or not prediction
        or copied.get("prediction_sha256")
        != hashlib.sha256(prediction.encode()).hexdigest()
        or copied.get("prediction_kind")
        not in {"model_generated", "fallback", "visible_fallback"}
        or not isinstance(receipt_raw, Mapping)
        or validate_receipt(receipt_raw) != dict(receipt_raw)
        or not isinstance(cost, Mapping)
        or set(cost) != {"model", "search", "system_total_tokens"}
        or not isinstance(cost.get("model"), Mapping)
        or set(cost["model"]) != set(sparse._MODEL_COUNTERS)
        or set(cost.get("search") or {}) != set(PHASES)
        or any(
            not isinstance(cost["search"].get(phase), Mapping)
            or set(cost["search"][phase]) != set(sparse._SEARCH_COUNTERS)
            for phase in PHASES
        )
        or cost.get("system_total_tokens")
        != cost["model"]["total_tokens"]
        + sum(cost["search"][phase]["total_tokens"] for phase in PHASES)
        or receipt_raw["model_provider_request_count"] != cost["model"]["requests"]
        or receipt_raw["model_provider_attempt_count"] != cost["model"]["attempts"]
        or receipt_raw["system_total_tokens"] != cost["system_total_tokens"]
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
        raise ValueError("V2.52.71 result envelope drifted")

    checkpoint: dict[str, Any] | None = None
    if checkpoint_raw is not None:
        if not isinstance(checkpoint_raw, Mapping):
            raise ValueError("V2.52.71 checkpoint envelope drifted")
        checkpoint = validate_checkpoint(checkpoint_raw)
        expected_kind = (
            "model_generated"
            if checkpoint["checkpoint_kind"] == "validated_model_output"
            else "fallback"
        )
        if (
            copied.get("production_checkpoint_payload_sha256")
            != checkpoint["checkpoint_payload_sha256"]
            or prediction != checkpoint["prediction"]
            or copied["prediction_kind"] != expected_kind
            or receipt_raw["checkpoint_kind"] != checkpoint["checkpoint_kind"]
        ):
            raise ValueError("V2.52.71 checkpoint binding drifted")
    elif (
        copied.get("production_checkpoint_payload_sha256") is not None
        or copied["prediction_kind"] != "visible_fallback"
        or receipt_raw["checkpoint_present"] is not False
    ):
        raise ValueError("V2.52.71 pre-checkpoint fallback drifted")

    if parent_raw is not None:
        if not isinstance(parent_raw, Mapping):
            raise ValueError("V2.52.71 parent envelope drifted")
        checked_parent = sparse.parent.validate_result(parent_raw)
        if (
            copied.get("parent_result_payload_sha256")
            != checked_parent["result_payload_sha256"]
            or checked_parent["predictions"][sparse.CONTROL_ARM] != prediction
            or checked_parent["predictions"][sparse.CANDIDATE_ARM] != prediction
            or receipt_raw["parent_result_retained"] is not True
        ):
            raise ValueError("V2.52.71 parent binding drifted")
    elif (
        copied.get("parent_result_payload_sha256") is not None
        or receipt_raw["parent_result_retained"] is not False
    ):
        raise ValueError("V2.52.71 absent parent drifted")
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
    observer = MicrostageObserver(budget)
    ok, visible = observer.attempt(
        "boundary_validate",
        lambda: sparse._validate_boundary(
            task, model=model, searches=searches, limits=limits
        ),
    )
    if not ok:
        raise ProductionCheckpointStageError(
            observer.receipt(
                checkpoint_kind=None,
                parent_result_retained=False,
                disposition="visible_fallback_before_checkpoint",
            )
        )
    model_before = sparse.counters._counter(model, sparse._MODEL_COUNTERS)
    search_before = {
        phase: sparse.counters._counter(searches[phase], sparse._SEARCH_COUNTERS)
        for phase in PHASES
    }
    provider = CheckpointingProductionModel(
        model,
        question=visible["question"],
        first_wave_search=searches[sparse.FIRST_PHASE],
        limits=limits,
    )
    _parent_ok, parent_result = observer.attempt(
        "paired_parent_run_and_validate",
        lambda: sparse.parent.validate_result(
            sparse.parent.run_paired_task(
                visible,
                model=provider,
                searches=searches,
                limits=limits,
                arm_order=sparse.ARMS,
                monotonic=monotonic,
            )
        ),
    )
    cost_ok, cost = observer.attempt(
        "effect_accounting",
        lambda: _cost_snapshot(model, searches, model_before, search_before),
    )
    if not cost_ok:
        checkpoint = provider.production_checkpoint
        raise ProductionCheckpointStageError(
            observer.receipt(
                checkpoint_kind=(
                    None if checkpoint is None else checkpoint["checkpoint_kind"]
                ),
                parent_result_retained=False,
                disposition=(
                    "visible_fallback_before_checkpoint"
                    if checkpoint is None
                    else (
                        "checkpoint_unrecoverable_accounting_failure"
                    )
                ),
            )
        )

    _checkpoint_ok, selected = observer.attempt(
        "production_checkpoint_select",
        lambda: (
            validate_checkpoint(provider.production_checkpoint)
            if provider.production_checkpoint is not None
            else (
                None
                if provider.production_synthesis_entry_count == 0
                else (_ for _ in ()).throw(
                    ValueError("V2.52.71 production checkpoint is unavailable")
                )
            )
        ),
    )
    if not _checkpoint_ok:
        raise ProductionCheckpointStageError(
            observer.receipt(
                checkpoint_kind=None,
                parent_result_retained=False,
                disposition="untrusted_checkpoint_rejected",
            )
        )
    checkpoint = selected
    if checkpoint is None:
        return _precheckpoint_result(
            observer=observer,
            visible=visible,
            provider=provider,
            model=model,
            searches=searches,
            model_before=model_before,
            search_before=search_before,
            budget=budget,
        )
    prediction = (
        checkpoint["prediction"]
        if checkpoint is not None
        else _visible_fallback(visible["question"])
    )
    prediction_kind = (
        "model_generated"
        if checkpoint is not None
        and checkpoint["checkpoint_kind"] == "validated_model_output"
        else "fallback"
        if checkpoint is not None
        else "visible_fallback"
    )
    _binding_ok, retained_parent = observer.attempt(
        "parent_prediction_binding",
        lambda: _retain_parent_if_bound(parent_result, prediction),
    )
    disposition = _disposition(checkpoint, retained_parent, observer.failures)
    receipt = _content_free_receipt(
        provider=provider,
        checkpoint=checkpoint,
        retained_parent=retained_parent,
        disposition=disposition,
        cost=cost,
        budget=budget,
        failures=observer.failures,
    )
    build_ok, result = observer.attempt(
        "result_envelope_build",
        lambda: _build_result(
            visible=visible,
            prediction=prediction,
            prediction_kind=prediction_kind,
            checkpoint=checkpoint,
            retained_parent=retained_parent,
            cost=cost,
            receipt=receipt,
        ),
    )
    if not build_ok:
        retained_parent = None
        disposition = (
            "validated_production_preserved_after_post_checkpoint_failure"
            if checkpoint["checkpoint_kind"] == "validated_model_output"
            else "deterministic_fallback_preserved_after_post_checkpoint_failure"
        )
        receipt = _content_free_receipt(
            provider=provider,
            checkpoint=checkpoint,
            retained_parent=None,
            disposition=disposition,
            cost=cost,
            budget=budget,
            failures=observer.failures,
        )
        return _build_recovery_result(
            visible=visible,
            checkpoint=checkpoint,
            cost=cost,
            receipt=receipt,
            observer=observer,
        ), observer.receipt(
            checkpoint_kind=checkpoint["checkpoint_kind"],
            parent_result_retained=False,
            disposition=disposition,
        )
    validate_ok, checked = observer.attempt(
        "result_envelope_validate", lambda: validate_result(result)
    )
    if not validate_ok:
        retained_parent = None
        disposition = (
            "validated_production_preserved_after_post_checkpoint_failure"
            if checkpoint["checkpoint_kind"] == "validated_model_output"
            else "deterministic_fallback_preserved_after_post_checkpoint_failure"
        )
        receipt = _content_free_receipt(
            provider=provider,
            checkpoint=checkpoint,
            retained_parent=None,
            disposition=disposition,
            cost=cost,
            budget=budget,
            failures=observer.failures,
        )
        return _build_recovery_result(
            visible=visible,
            checkpoint=checkpoint,
            cost=cost,
            receipt=receipt,
            observer=observer,
        ), observer.receipt(
            checkpoint_kind=checkpoint["checkpoint_kind"],
            parent_result_retained=False,
            disposition=disposition,
        )
    stage = observer.receipt(
        checkpoint_kind=None if checkpoint is None else checkpoint["checkpoint_kind"],
        parent_result_retained=retained_parent is not None,
        disposition=disposition,
    )
    return checked, stage


__all__ = [
    "CHECKPOINT_KINDS",
    "CHECKPOINT_ROLE",
    "CheckpointingProductionModel",
    "MicrostageObserver",
    "PHASES",
    "POLICY_ID",
    "ProductionCheckpointStageError",
    "RECEIPT_ROLE",
    "RECOVERY_DISPOSITIONS",
    "ROLE",
    "STAGES",
    "STAGE_RECEIPT_ROLE",
    "build_checkpoint",
    "run_task",
    "validate_checkpoint",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
