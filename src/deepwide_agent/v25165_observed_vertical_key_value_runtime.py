"""Behavior-preserving V2.51.58 runtime with V2.51.63 observation.

The disposition observer reads only the same in-memory verified incremental
pages already consumed by V2.51.58.  Its receipt cannot enter admission,
candidate ordering, selection, projection, routing, or prediction.  Observer
failure is isolated and the frozen parent runtime continues unchanged.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v25158_vertical_key_value_candidate_runtime as parent
from . import v25163_vertical_admission_disposition_observer as observer
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25165_observed_vertical_key_value_runtime_v1"
ROLE = "v25165_observed_vertical_key_value_runtime_result"
RECEIPT_ROLE = "v25165_content_free_observed_vertical_key_value_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


class ObservedVerticalKeyValueCandidateProvider(
    parent.VerticalKeyValueCandidateProvider
):
    """Observe frozen admission without changing the parent provider path."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.disposition_observer_entry_count = 0
        self.disposition_observation: dict[str, Any] | None = None
        self.disposition_observer_failure_type: str | None = None
        self._verified_delta_cache_key: tuple[str, str, tuple[str, ...]] | None = None
        self._verified_delta_cache: list[dict[str, str]] | None = None
        self._verified_delta_cache_error: BaseException | None = None
        self.verified_delta_computation_count = 0
        self.verified_delta_cache_reuse_count = 0

    def _verified_delta_pages(
        self,
        control_user: str,
        candidate_user: str,
        columns: Sequence[str],
    ) -> list[dict[str, str]]:
        key = (str(control_user), str(candidate_user), tuple(map(str, columns)))
        if key == self._verified_delta_cache_key and (
            self._verified_delta_cache is not None
            or self._verified_delta_cache_error is not None
        ):
            self.verified_delta_cache_reuse_count += 1
            if self._verified_delta_cache_error is not None:
                raise self._verified_delta_cache_error
            return copy.deepcopy(self._verified_delta_cache)
        self.verified_delta_computation_count += 1
        self._verified_delta_cache_key = key
        try:
            values = super()._verified_delta_pages(
                control_user, candidate_user, columns
            )
        except BaseException as exc:
            self._verified_delta_cache_error = exc
            raise
        self._verified_delta_cache = copy.deepcopy(values)
        return copy.deepcopy(values)

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        eligible = bool(
            system == parent.score.SYNTHESIS_SYSTEM
            and self.synthesis_provider_entry_count == 1
        )
        if eligible:
            self.disposition_observer_entry_count = 1
            try:
                columns = parent.sparse_parent._prompt_columns(
                    user, self._columns()
                )
                verified = self._verified_delta_pages(
                    self._production_user, user, columns
                )
                self.disposition_observation = (
                    observer.observe_vertical_admission(
                        self.production_prediction or "",
                        columns=columns,
                        pages=verified,
                    )
                )
            except BaseException as exc:
                self.disposition_observer_failure_type = _safe_failure(exc)
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


def _frozen_parent_result(
    provider: ObservedVerticalKeyValueCandidateProvider,
    sparse_result: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = parent._receipt(provider, sparse_result)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": parent.ROLE,
        "policy_id": parent.POLICY_ID,
        "opaque_id": sparse_result["opaque_id"],
        "status": "terminal",
        "production_prediction": sparse_result["production_prediction"],
        "production_prediction_sha256": sparse_result[
            "production_prediction_sha256"
        ],
        "prediction": sparse_result["prediction"],
        "prediction_sha256": sparse_result["prediction_sha256"],
        "prediction_kind": sparse_result["prediction_kind"],
        "cost": copy.deepcopy(sparse_result["cost"]),
        "parent_result": copy.deepcopy(dict(sparse_result)),
        "parent_result_payload_sha256": sparse_result["result_payload_sha256"],
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return parent.validate_result(value)


def _receipt(
    provider: ObservedVerticalKeyValueCandidateProvider,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    parent_receipt = parent_result["content_free_receipt"]
    observation = (
        observer.validate_observation(provider.disposition_observation)
        if provider.disposition_observation is not None
        else None
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "parent_candidate_revision_entry_count": int(
            parent_receipt["candidate_revision_entry_count"]
        ),
        "disposition_observer_entry_count": int(
            provider.disposition_observer_entry_count
        ),
        "disposition_observer_completed_count": int(observation is not None),
        "verified_delta_computation_count": int(
            provider.verified_delta_computation_count
        ),
        "verified_delta_cache_reuse_count": int(
            provider.verified_delta_cache_reuse_count
        ),
        "disposition_observer_failure_present": (
            provider.disposition_observer_failure_type is not None
        ),
        "disposition_observer_failure_type": (
            provider.disposition_observer_failure_type
        ),
        "disposition_observation": copy.deepcopy(observation),
        "observer_and_parent_share_one_verified_delta_cache": True,
        "observer_failure_isolated_and_parent_continues": True,
        "parent_prediction_cost_candidate_and_effect_receipts_unchanged": True,
        "observer_reason_buckets_change_admission_routing_prediction_or_budget": False,
        "contains_question_query_url_title_page_key_value_identity_field_quote_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value, parent_receipt=parent_receipt)


def validate_receipt(
    value: Mapping[str, Any],
    *,
    parent_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    observation = copied.get("disposition_observation")
    entered = copied.get("disposition_observer_entry_count") == 1
    completed = copied.get("disposition_observer_completed_count") == 1
    failed = copied.get("disposition_observer_failure_present") is True
    true_flags = (
        "observer_and_parent_share_one_verified_delta_cache",
        "observer_failure_isolated_and_parent_continues",
        "parent_prediction_cost_candidate_and_effect_receipts_unchanged",
    )
    false_flags = (
        "observer_reason_buckets_change_admission_routing_prediction_or_budget",
        "contains_question_query_url_title_page_key_value_identity_field_quote_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    count_names = (
        "parent_candidate_revision_entry_count",
        "disposition_observer_entry_count",
        "disposition_observer_completed_count",
        "verified_delta_computation_count",
        "verified_delta_cache_reuse_count",
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
            *count_names,
            "disposition_observer_failure_present",
            "disposition_observer_failure_type",
            "disposition_observation",
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
            for name in count_names
        )
        or copied["disposition_observer_entry_count"]
        != copied["parent_candidate_revision_entry_count"]
        or completed and not entered
        or failed and not entered
        or entered and completed is failed
        or not entered and (completed or failed)
        or not entered
        and (
            copied["verified_delta_computation_count"]
            or copied["verified_delta_cache_reuse_count"]
        )
        or completed
        and (
            copied["verified_delta_computation_count"] != 1
            or copied["verified_delta_cache_reuse_count"] != 1
        )
        or copied["verified_delta_cache_reuse_count"]
        > copied["verified_delta_computation_count"]
        or completed
        and (
            not isinstance(observation, Mapping)
            or observer.validate_observation(observation) != dict(observation)
            or copied.get("disposition_observer_failure_type") is not None
        )
        or not completed
        and observation is not None
        or failed
        and (
            not isinstance(copied.get("disposition_observer_failure_type"), str)
            or not copied["disposition_observer_failure_type"]
            or len(copied["disposition_observer_failure_type"]) > 128
        )
        or not failed
        and copied.get("disposition_observer_failure_type") is not None
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.65 observed vertical receipt drifted")
    if parent_receipt is not None:
        checked_parent = parent.validate_receipt(parent_receipt)
        if (
            copied["parent_candidate_revision_entry_count"]
            != checked_parent["candidate_revision_entry_count"]
            or completed
            and (
                observation["page_count"]
                != checked_parent["verified_incremental_page_count"]
                or observation["vertical_block_count"]
                != checked_parent["vertical_pipe_block_count"]
                or observation["identity_bound_block_count"]
                != checked_parent["vertical_identity_bound_block_count"]
                or observation["ambiguous_page_count"]
                != checked_parent["vertical_ambiguous_page_count"]
                or observation["frozen_vertical_candidate_observation_count"]
                != checked_parent[
                    "vertical_key_value_record_observation_count"
                ]
            )
        ):
            raise ValueError("V2.51.65 observation-parent parity drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: parent.score.ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = parent.sparse_parent._validate_boundary(
        task, model=model, searches=searches, limits=limits
    )
    provider = ObservedVerticalKeyValueCandidateProvider(
        model,
        question=visible["question"],
        first_wave_search=searches[FIRST_PHASE],
        limits=limits,
    )
    sparse_result = parent.sparse_parent.validate_result(
        parent.sparse_parent.run_task(
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
        raise ValueError("V2.51.65 result envelope drifted")
    checked_parent = parent.validate_result(parent_raw)
    validate_receipt(
        receipt, parent_receipt=checked_parent["content_free_receipt"]
    )
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
        raise ValueError("V2.51.65 behavior-preserving parent binding drifted")
    return copied


run_observed_vertical_key_value_task = run_task


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
    "ObservedVerticalKeyValueCandidateProvider",
    "run_observed_vertical_key_value_task",
    "run_task",
    "validate_receipt",
    "validate_result",
]
