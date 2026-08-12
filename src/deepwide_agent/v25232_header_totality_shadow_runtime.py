"""Behavior-preserving shadow observation over frozen V2.51.88.

The V2.52.30 helper is invoked only after the frozen V2.51.70 observation has
classified the first raw production response as ``no_bindable_header_reject``
and the frozen quote-aware repair has not activated.  The shadow candidate is
discarded immediately; only its content-free receipt is retained.  The exact
V2.51.88 result is then sealed as the parent and predictions, hashes, kind,
cost, effects, and all parent receipts are copied byte-for-byte.

This module is build-only.  It does not authorize an external forward,
prediction change, evaluator, benchmark run, retry, or credit assignment.
"""

from __future__ import annotations

import copy
import hashlib
import re
import time
from collections.abc import Callable, Mapping
from typing import Any

from . import v25180_quote_aware_production_runtime as effect_parent
from . import v25188_export_failure_tolerant_same_response_runtime as parent
from . import v25230_index_positional_header_normalizer as shadow
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25232_header_totality_shadow_runtime_v1"
ROLE = "v25232_header_totality_shadow_runtime_result"
RECEIPT_ROLE = "v25232_content_free_header_totality_shadow_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _active_disposition(observation: Mapping[str, Any]) -> str:
    values = observation.get("disposition_counts")
    if not isinstance(values, Mapping):
        raise ValueError("V2.52.32 parent disposition is absent")
    active = [name for name, count in values.items() if count == 1]
    if len(active) != 1:
        raise ValueError("V2.52.32 parent disposition is ambiguous")
    return str(active[0])


class HeaderTotalityShadowProvider(effect_parent.QuoteAwareProductionProvider):
    """Observe one narrow rejected state without changing the response."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.header_totality_shadow_eligibility_count = 0
        self.header_totality_shadow_entry_count = 0
        self.header_totality_shadow_completed_count = 0
        self.header_totality_shadow_failure_type: str | None = None
        self.header_totality_shadow_receipt: dict[str, Any] | None = None
        self.header_totality_shadow_candidate_available_count = 0

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        first_production = bool(
            system == effect_parent.score.SYNTHESIS_SYSTEM
            and self.synthesis_provider_entry_count == 0
        )
        response = super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if not first_production:
            return response
        raw_observation = self.raw_normalizer_observation
        eligible = bool(
            raw_observation is not None
            and self.raw_normalizer_observer_failure_type is None
            and _active_disposition(raw_observation)
            == "no_bindable_header_reject"
            and self.quote_aware_repair_applied_count == 0
        )
        self.header_totality_shadow_eligibility_count = int(eligible)
        if not eligible:
            return response
        self.header_totality_shadow_entry_count = 1
        try:
            columns = effect_parent.parent.parent.sparse_parent._prompt_columns(
                user, self._columns()
            )
            marker = "未知" if re.search(r"[\u4e00-\u9fff]", self._question) else "Unknown"
            candidate, receipt = shadow.normalize_index_positional_header_table(
                effect_parent.score._model_text(response),
                columns,
                unknown_marker=marker,
            )
            checked = shadow.validate_receipt(receipt)
            available = int(candidate is not None)
            if available != int(checked["accepted"]):
                raise ValueError("V2.52.32 shadow candidate/receipt parity drifted")
            self.header_totality_shadow_receipt = checked
            self.header_totality_shadow_candidate_available_count = available
            self.header_totality_shadow_completed_count = 1
            # Candidate is intentionally not stored or returned.
            candidate = None
        except BaseException as exc:
            self.header_totality_shadow_failure_type = _safe_failure(exc)
        return response


def _effect_result(
    provider: HeaderTotalityShadowProvider,
    sparse_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the frozen V2.51.80 result with the shadow provider."""

    internal_parent = effect_parent._internal_parent_result(provider, sparse_result)
    production = internal_parent["production_prediction"]
    final = internal_parent["prediction"]
    diagnostics: dict[str, Any] | None = None
    public_export_attempt_count = 0
    public_export_completed_count = 0
    public_export_failure_type: str | None = None
    public_export_fallback_to_completed_production = False
    if provider.quote_aware_repair_applied_count:
        repair_receipt = effect_parent.repair.validate_receipt(
            provider.quote_aware_repair_receipt or {}
        )
        safe_public = provider.quote_aware_public_production
        if not isinstance(safe_public, str) or not safe_public:
            raise RuntimeError("V2.52.32 frozen repair lost safe public production")
        production = final = safe_public
        public_export_attempt_count = 1
        try:
            canonical_safe = effect_parent._safe_public_production(
                internal_parent["production_prediction"],
                expected_entity_cells=repair_receipt["internal_entity_cell_count"],
                expected_entity_occurrences=repair_receipt[
                    "escaped_pipe_occurrence_count"
                ],
            )
            if safe_public != canonical_safe:
                raise ValueError("V2.52.32 frozen safe public production drifted")
            production, final, diagnostics = effect_parent.export_public_predictions(
                internal_parent["production_prediction"],
                internal_parent["prediction"],
                columns=effect_parent._canonical_internal_columns(
                    internal_parent["production_prediction"]
                ),
                expected_production_entity_cells=repair_receipt[
                    "internal_entity_cell_count"
                ],
                expected_production_entity_occurrences=repair_receipt[
                    "escaped_pipe_occurrence_count"
                ],
            )
            public_export_completed_count = 1
        except BaseException as exc:
            public_export_failure_type = effect_parent._safe_failure(exc)
            public_export_fallback_to_completed_production = True
            diagnostics = effect_parent._publication_failure_diagnostics(
                repair_receipt
            )
            production = final = safe_public
    receipt = effect_parent._receipt(
        provider,
        internal_parent,
        diagnostics,
        public_export_attempt_count=public_export_attempt_count,
        public_export_completed_count=public_export_completed_count,
        public_export_failure_type=public_export_failure_type,
        public_export_fallback_to_completed_production=(
            public_export_fallback_to_completed_production
        ),
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": effect_parent.ROLE,
        "policy_id": effect_parent.POLICY_ID,
        "opaque_id": internal_parent["opaque_id"],
        "status": "terminal",
        "production_prediction": production,
        "production_prediction_sha256": hashlib.sha256(production.encode()).hexdigest(),
        "prediction": final,
        "prediction_sha256": hashlib.sha256(final.encode()).hexdigest(),
        "prediction_kind": internal_parent["prediction_kind"],
        "cost": copy.deepcopy(internal_parent["cost"]),
        "parent_result": copy.deepcopy(internal_parent),
        "parent_result_payload_sha256": internal_parent["result_payload_sha256"],
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return effect_parent.validate_result(value)


def _frozen_parent_result(effect_result: Mapping[str, Any]) -> dict[str, Any]:
    checked_effect = effect_parent.validate_result(effect_result)
    predictions, receipt = parent._predictions(checked_effect)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": parent.ROLE,
        "policy_id": parent.POLICY_ID,
        "opaque_id": checked_effect["opaque_id"],
        "status": "terminal",
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "prediction_kind": checked_effect["prediction_kind"],
        "cost": copy.deepcopy(checked_effect["cost"]),
        "parent_result": copy.deepcopy(checked_effect),
        "parent_result_payload_sha256": checked_effect["result_payload_sha256"],
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return parent.validate_result(value)


def _receipt(
    provider: HeaderTotalityShadowProvider,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    effect_receipt = checked_parent["parent_result"]["content_free_receipt"]
    raw_observation = effect_receipt["raw_normalizer_observation"]
    raw_disposition = (
        _active_disposition(raw_observation)
        if isinstance(raw_observation, Mapping)
        else None
    )
    expected_eligible = bool(
        raw_disposition == "no_bindable_header_reject"
        and effect_receipt["quote_aware_repair_applied_count"] == 0
    )
    shadow_receipt = (
        shadow.validate_receipt(provider.header_totality_shadow_receipt)
        if provider.header_totality_shadow_receipt is not None
        else None
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(checked_parent["result_payload_sha256"]),
        "parent_raw_no_bindable_header_reject": raw_disposition
        == "no_bindable_header_reject",
        "parent_quote_aware_repair_applied_count": int(
            effect_receipt["quote_aware_repair_applied_count"]
        ),
        "shadow_eligibility_count": int(
            provider.header_totality_shadow_eligibility_count
        ),
        "shadow_entry_count": int(provider.header_totality_shadow_entry_count),
        "shadow_completed_count": int(
            provider.header_totality_shadow_completed_count
        ),
        "shadow_failure_present": provider.header_totality_shadow_failure_type
        is not None,
        "shadow_failure_type": provider.header_totality_shadow_failure_type,
        "shadow_candidate_available_count": int(
            provider.header_totality_shadow_candidate_available_count
        ),
        "shadow_receipt": copy.deepcopy(shadow_receipt),
        "shadow_runs_only_after_frozen_no_bindable_header_reject": True,
        "shadow_candidate_discarded_before_parent_continues": True,
        "shadow_failure_isolated_and_parent_continues": True,
        "parent_predictions_hashes_kind_cost_effects_and_receipts_unchanged": True,
        "shadow_changes_response_fallback_prediction_candidate_routing_or_budget": False,
        "contains_response_header_cell_question_identity_url_page_prediction_semantic_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "external_forward_evaluator_or_benchmark_authorized": False,
    }
    if int(expected_eligible) != value["shadow_eligibility_count"]:
        raise ValueError("V2.52.32 parent/shadow eligibility parity drifted")
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value, parent_result=checked_parent)


def validate_receipt(
    value: Mapping[str, Any],
    *,
    parent_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    shadow_receipt = copied.get("shadow_receipt")
    eligible = copied.get("shadow_eligibility_count") == 1
    entered = copied.get("shadow_entry_count") == 1
    completed = copied.get("shadow_completed_count") == 1
    failed = copied.get("shadow_failure_present") is True
    available = copied.get("shadow_candidate_available_count") == 1
    count_names = (
        "parent_quote_aware_repair_applied_count",
        "shadow_eligibility_count",
        "shadow_entry_count",
        "shadow_completed_count",
        "shadow_candidate_available_count",
    )
    dynamic_bools = (
        "parent_raw_no_bindable_header_reject",
        "shadow_failure_present",
    )
    true_flags = (
        "shadow_runs_only_after_frozen_no_bindable_header_reject",
        "shadow_candidate_discarded_before_parent_continues",
        "shadow_failure_isolated_and_parent_continues",
        "parent_predictions_hashes_kind_cost_effects_and_receipts_unchanged",
    )
    false_flags = (
        "shadow_changes_response_fallback_prediction_candidate_routing_or_budget",
        "contains_response_header_cell_question_identity_url_page_prediction_semantic_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "external_forward_evaluator_or_benchmark_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "parent_role",
        "parent_policy_id",
        "parent_result_payload_sha256",
        *count_names,
        *dynamic_bools,
        "shadow_failure_type",
        "shadow_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
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
        or any(not isinstance(copied.get(name), bool) for name in dynamic_bools)
        or eligible is not entered
        or entered and completed is failed
        or completed and not entered
        or failed and not entered
        or not entered and (completed or failed or available or shadow_receipt is not None)
        or completed
        and (
            not isinstance(shadow_receipt, Mapping)
            or shadow.validate_receipt(shadow_receipt) != dict(shadow_receipt)
            or available is not bool(shadow_receipt["accepted"])
        )
        or failed
        and (
            not isinstance(copied.get("shadow_failure_type"), str)
            or not copied["shadow_failure_type"]
            or len(copied["shadow_failure_type"]) > 128
            or shadow_receipt is not None
            or available
        )
        or not failed and copied.get("shadow_failure_type") is not None
        or eligible
        and (
            copied["parent_raw_no_bindable_header_reject"] is not True
            or copied["parent_quote_aware_repair_applied_count"] != 0
        )
        or not eligible
        and copied["parent_raw_no_bindable_header_reject"]
        and copied["parent_quote_aware_repair_applied_count"] == 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.32 header-totality shadow receipt drifted")
    if parent_result is not None:
        checked_parent = parent.validate_result(parent_result)
        effect_receipt = checked_parent["parent_result"]["content_free_receipt"]
        raw = effect_receipt["raw_normalizer_observation"]
        raw_no_bindable = bool(
            isinstance(raw, Mapping)
            and _active_disposition(raw) == "no_bindable_header_reject"
        )
        quote_applied = int(effect_receipt["quote_aware_repair_applied_count"])
        if (
            copied["parent_result_payload_sha256"]
            != checked_parent["result_payload_sha256"]
            or copied["parent_raw_no_bindable_header_reject"] is not raw_no_bindable
            or copied["parent_quote_aware_repair_applied_count"] != quote_applied
            or copied["shadow_eligibility_count"]
            != int(raw_no_bindable and quote_applied == 0)
        ):
            raise ValueError("V2.52.32 shadow receipt-parent binding drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = effect_parent.parent.parent.sparse_parent._validate_boundary(
        task, model=model, searches=searches, limits=limits
    )
    provider = HeaderTotalityShadowProvider(
        model,
        question=visible["question"],
        first_wave_search=searches[FIRST_PHASE],
        limits=limits,
    )
    sparse_result = effect_parent.parent.parent.sparse_parent.validate_result(
        effect_parent.parent.parent.sparse_parent.run_task(
            visible,
            model=provider,
            searches=searches,
            limits=limits,
            monotonic=monotonic,
        )
    )
    effect_result = _effect_result(provider, sparse_result)
    parent_result = _frozen_parent_result(effect_result)
    receipt = _receipt(provider, parent_result)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
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
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    parent_raw = copied.get("parent_result")
    receipt_raw = copied.get("content_free_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "predictions",
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
        or not isinstance(receipt_raw, Mapping)
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(ARMS)
        or any(
            not isinstance(predictions.get(arm), str)
            or not predictions[arm]
            or hashes.get(arm)
            != hashlib.sha256(str(predictions[arm]).encode()).hexdigest()
            for arm in ARMS
        )
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
        raise ValueError("V2.52.32 header-totality shadow result drifted")
    checked_parent = parent.validate_result(parent_raw)
    validate_receipt(receipt_raw, parent_result=checked_parent)
    if (
        copied["opaque_id"] != checked_parent["opaque_id"]
        or dict(predictions) != checked_parent["predictions"]
        or dict(hashes) != checked_parent["prediction_sha256"]
        or copied["prediction_kind"] != checked_parent["prediction_kind"]
        or copied["cost"] != checked_parent["cost"]
        or copied["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt_raw["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
    ):
        raise ValueError("V2.52.32 behavior-preserving parent binding drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "HeaderTotalityShadowProvider",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "SECOND_PHASE",
    "run_task",
    "validate_receipt",
    "validate_result",
]
