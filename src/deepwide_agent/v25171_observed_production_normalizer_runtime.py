"""Behavior-preserving production-normalizer observation over V2.51.65.

The observer sees the first successful production provider response after the
frozen V2.51.65 provider has processed it but before V2.51.35 may replace it
with a fallback.  Observation cannot change the response object, parent
prediction, candidate path, costs, or any query/model/fetch budget.  Observer
failure is isolated and the frozen parent runtime continues unchanged.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Mapping
from typing import Any

from . import v25165_observed_vertical_key_value_runtime as parent
from . import v25170_production_normalizer_disposition_observer as observer
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25171_observed_production_normalizer_runtime_v1"
ROLE = "v25171_observed_production_normalizer_runtime_result"
RECEIPT_ROLE = "v25171_content_free_observed_production_normalizer_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


class ObservedProductionNormalizerProvider(
    parent.ObservedVerticalKeyValueCandidateProvider
):
    """Observe the first raw production response without changing it."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.production_normalizer_observer_entry_count = 0
        self.production_normalizer_observation: dict[str, Any] | None = None
        self.production_normalizer_observer_failure_type: str | None = None

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        first_production = bool(
            system == parent.parent.score.SYNTHESIS_SYSTEM
            and self.synthesis_provider_entry_count == 0
        )
        response = super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if first_production:
            self.production_normalizer_observer_entry_count = 1
            try:
                truncated = getattr(response, "output_truncated", False)
                if not isinstance(truncated, bool):
                    raise TypeError("provider truncation flag drifted")
                columns = parent.parent.sparse_parent._prompt_columns(
                    user, self._columns()
                )
                self.production_normalizer_observation = (
                    observer.observe_production_normalization(
                        parent.parent.score._model_text(response),
                        columns=columns,
                        provider_output_truncated=truncated,
                    )
                )
            except BaseException as exc:
                self.production_normalizer_observer_failure_type = _safe_failure(exc)
        return response


def _frozen_parent_result(
    provider: ObservedProductionNormalizerProvider,
    sparse_result: Mapping[str, Any],
) -> dict[str, Any]:
    vertical_result = parent._frozen_parent_result(provider, sparse_result)
    receipt = parent._receipt(provider, vertical_result)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": parent.ROLE,
        "policy_id": parent.POLICY_ID,
        "opaque_id": vertical_result["opaque_id"],
        "status": "terminal",
        "production_prediction": vertical_result["production_prediction"],
        "production_prediction_sha256": vertical_result[
            "production_prediction_sha256"
        ],
        "prediction": vertical_result["prediction"],
        "prediction_sha256": vertical_result["prediction_sha256"],
        "prediction_kind": vertical_result["prediction_kind"],
        "cost": copy.deepcopy(vertical_result["cost"]),
        "parent_result": copy.deepcopy(vertical_result),
        "parent_result_payload_sha256": vertical_result["result_payload_sha256"],
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return parent.validate_result(value)


def _receipt(
    provider: ObservedProductionNormalizerProvider,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    observation = (
        observer.validate_observation(provider.production_normalizer_observation)
        if provider.production_normalizer_observation is not None
        else None
    )
    sparse_receipt = parent_result["parent_result"]["parent_result"][
        "content_free_receipt"
    ]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "production_normalizer_observer_entry_count": int(
            provider.production_normalizer_observer_entry_count
        ),
        "production_normalizer_observer_completed_count": int(
            observation is not None
        ),
        "production_normalizer_observer_failure_present": (
            provider.production_normalizer_observer_failure_type is not None
        ),
        "production_normalizer_observer_failure_type": (
            provider.production_normalizer_observer_failure_type
        ),
        "production_normalizer_observation": copy.deepcopy(observation),
        "parent_production_provider_output_valid": bool(
            sparse_receipt["production_provider_output_valid"]
        ),
        "parent_production_fallback_used": bool(
            sparse_receipt["production_fallback_used"]
        ),
        "observer_runs_after_parent_provider_response_and_before_sparse_fallback": True,
        "observer_failure_isolated_and_parent_continues": True,
        "parent_prediction_cost_candidate_and_effect_receipts_unchanged": True,
        "observer_disposition_changes_response_fallback_prediction_candidate_routing_or_budget": False,
        "contains_response_cell_column_question_identity_url_page_key_value_prediction_semantic_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value, parent_result=parent_result)


def validate_receipt(
    value: Mapping[str, Any],
    *,
    parent_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    observation = copied.get("production_normalizer_observation")
    entered = copied.get("production_normalizer_observer_entry_count") == 1
    completed = copied.get("production_normalizer_observer_completed_count") == 1
    failed = copied.get("production_normalizer_observer_failure_present") is True
    counts = (
        "production_normalizer_observer_entry_count",
        "production_normalizer_observer_completed_count",
    )
    dynamics = (
        "production_normalizer_observer_failure_present",
        "parent_production_provider_output_valid",
        "parent_production_fallback_used",
    )
    true_flags = (
        "observer_runs_after_parent_provider_response_and_before_sparse_fallback",
        "observer_failure_isolated_and_parent_continues",
        "parent_prediction_cost_candidate_and_effect_receipts_unchanged",
    )
    false_flags = (
        "observer_disposition_changes_response_fallback_prediction_candidate_routing_or_budget",
        "contains_response_cell_column_question_identity_url_page_key_value_prediction_semantic_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
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
            *counts,
            *dynamics,
            "production_normalizer_observer_failure_type",
            "production_normalizer_observation",
            *true_flags,
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != parent.ROLE
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] not in {0, 1}
            for name in counts
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamics)
        or completed and not entered
        or failed and not entered
        or entered and completed is failed
        or not entered and (completed or failed)
        or copied["parent_production_fallback_used"]
        is copied["parent_production_provider_output_valid"]
        or completed
        and (
            not isinstance(observation, Mapping)
            or observer.validate_observation(observation) != dict(observation)
            or copied.get("production_normalizer_observer_failure_type") is not None
            or observation["frozen_synthesis_contract_accepted"]
            is not copied["parent_production_provider_output_valid"]
        )
        or not completed and observation is not None
        or failed
        and (
            not isinstance(
                copied.get("production_normalizer_observer_failure_type"), str
            )
            or not copied["production_normalizer_observer_failure_type"]
            or len(copied["production_normalizer_observer_failure_type"]) > 128
        )
        or not failed
        and copied.get("production_normalizer_observer_failure_type") is not None
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.71 production normalizer receipt drifted")
    if parent_result is not None:
        checked_parent = parent.validate_result(parent_result)
        sparse_receipt = checked_parent["parent_result"]["parent_result"][
            "content_free_receipt"
        ]
        if (
            copied["parent_result_payload_sha256"]
            != checked_parent["result_payload_sha256"]
            or copied["parent_production_provider_output_valid"]
            is not sparse_receipt["production_provider_output_valid"]
            or copied["parent_production_fallback_used"]
            is not sparse_receipt["production_fallback_used"]
        ):
            raise ValueError("V2.51.71 observation-parent parity drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: parent.parent.score.ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = parent.parent.sparse_parent._validate_boundary(
        task, model=model, searches=searches, limits=limits
    )
    provider = ObservedProductionNormalizerProvider(
        model,
        question=visible["question"],
        first_wave_search=searches[FIRST_PHASE],
        limits=limits,
    )
    sparse_result = parent.parent.sparse_parent.validate_result(
        parent.parent.sparse_parent.run_task(
            visible,
            model=provider,
            searches=searches,
            limits=limits,
            monotonic=monotonic,
        )
    )
    parent_result = _frozen_parent_result(provider, sparse_result)
    receipt = _receipt(provider, parent_result)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": parent_result["opaque_id"],
        "status": "terminal",
        "production_prediction": parent_result["production_prediction"],
        "production_prediction_sha256": parent_result[
            "production_prediction_sha256"
        ],
        "prediction": parent_result["prediction"],
        "prediction_sha256": parent_result["prediction_sha256"],
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
    parent_raw = copied.get("parent_result")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "production_prediction",
        "production_prediction_sha256",
        "prediction",
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
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(parent_raw, Mapping)
        or not isinstance(receipt, Mapping)
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
        raise ValueError("V2.51.71 result envelope drifted")
    checked_parent = parent.validate_result(parent_raw)
    validate_receipt(receipt, parent_result=checked_parent)
    if (
        copied["opaque_id"] != checked_parent["opaque_id"]
        or copied["production_prediction"]
        != checked_parent["production_prediction"]
        or copied["production_prediction_sha256"]
        != checked_parent["production_prediction_sha256"]
        or copied["prediction"] != checked_parent["prediction"]
        or copied["prediction_sha256"] != checked_parent["prediction_sha256"]
        or copied["prediction_kind"] != checked_parent["prediction_kind"]
        or copied["cost"] != checked_parent["cost"]
        or copied["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
    ):
        raise ValueError("V2.51.71 behavior-preserving parent binding drifted")
    return copied


run_observed_production_normalizer_task = run_task


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "SECOND_PHASE",
    "ObservedProductionNormalizerProvider",
    "run_observed_production_normalizer_task",
    "run_task",
    "validate_receipt",
    "validate_result",
]
