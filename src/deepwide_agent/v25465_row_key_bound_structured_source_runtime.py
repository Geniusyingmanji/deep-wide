"""One-parent production runtime for V2.54.64 row-key-bound source edits.

This runtime reproduces the frozen V2.53.75 production path with one task-local
model facade.  The facade mirrors, without modifying, the already-paid third
synthesis prompt's exact columns and same-forward page records.  After the
parent result is terminal, its completed scored table supplies row identities
to the pure V2.54.64 candidate primitive.  The candidate is therefore a local
deterministic edit over one shared parent, not an independent rollout.

The parent still performs at most four queries, fourteen fetches, and three
model calls.  No candidate query, fetch, model call, token, context, or network
effect is added.  Runtime inputs remain exactly visible ``opaque_id`` and
``question`` plus injected capped clients.  No benchmark label, mapping, gold,
evaluator, score, reward, credential, or historical result is available.
Entropy/information gain assigns no signed credit.  This build grants no
external or DeepWideBench launch.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25135_sparse_production_runtime as prompt_parent
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25370_shared_synthesis_changed_safe_runtime as shared_parent
from . import v25375_schema_total_changed_safe_runtime as parent
from . import v25464_row_key_bound_structured_source_candidate as candidates
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter


POLICY_ID = "v25465_row_key_bound_structured_source_runtime_v1"
ROLE = "v25465_row_key_bound_structured_source_runtime_result"
RECEIPT_ROLE = "v25465_content_free_row_key_bound_structured_source_receipt"
STAGE_RECEIPT_ROLE = "v25465_content_free_row_key_bound_structured_source_stage_receipt"
ARMS = ("shared_parent_table", "row_key_bound_structured_source_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
ProductionOnlyStageError = parent.ProductionOnlyStageError

_COUNT_FIELDS = (
    "captured_column_count",
    "captured_same_forward_page_count",
    "accepted_unique_identity_page_count",
    "available_candidate_count",
    "applied_coordinate_count",
    "positive_signed_credit_count",
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_calls",
    "additional_fetch_calls",
    "additional_provider_tokens",
)


class _CaptureModel(DeadlineAwareGlobalModelSlotLimiter):
    """Transparent task-local mirror of the third production call."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
    ) -> None:
        if not isinstance(bounded, DeadlineAwareGlobalModelSlotLimiter):
            raise TypeError("V2.54.65 bounded model drifted")
        self._bounded = bounded
        self._question = str(question)
        self.logical_calls = 0
        self.capture_attempted = False
        self.capture_valid = False
        self.capture_failure_type: str | None = None
        self.captured_columns: tuple[str, ...] = ()
        self.captured_pages: list[dict[str, str]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bounded, name)

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        self.logical_calls += 1
        if str(system) == score.SYNTHESIS_SYSTEM:
            self.capture_attempted = True
            try:
                self.captured_columns = tuple(
                    prompt_parent._prompt_columns(str(user), ("Result", "Value"))
                )
                self.captured_pages = prompt_parent._prompt_pages(str(user))
                self.capture_valid = bool(self.captured_columns)
                if not self.capture_valid:
                    self.capture_failure_type = "InsufficientVisibleColumns"
            except BaseException as exc:
                self.capture_valid = False
                name = type(exc).__name__ or "Exception"
                self.capture_failure_type = name[:128]
                self.captured_columns = ()
                self.captured_pages = []
        return self._bounded.complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )

    def remaining_effect_seconds(self) -> float:
        return float(self._bounded.remaining_effect_seconds())

    def receipt(self) -> dict[str, Any]:
        return self._bounded.receipt()


def _base(parent_result: Mapping[str, Any]) -> str:
    checked = parent.validate_result(parent_result)
    base = str(checked["prediction"])
    if not base:
        raise ValueError("V2.54.65 parent prediction is absent")
    return base


def _application(
    base: str,
    capture: _CaptureModel,
) -> tuple[dict[str, Any] | None, str, str | None]:
    if not capture.capture_valid:
        return (
            None,
            base,
            capture.capture_failure_type or "SynthesisCaptureNotAttempted",
        )
    try:
        application = candidates.build_application(
            base,
            columns=capture.captured_columns,
            pages=capture.captured_pages,
        )
        checked = candidates.validate_application(
            application,
            base_prediction=base,
            columns=capture.captured_columns,
            pages=capture.captured_pages,
        )
        return checked, str(checked["candidate_prediction"]), None
    except BaseException as exc:
        name = type(exc).__name__ or "Exception"
        return None, base, name[:128]


def _receipt(
    *,
    parent_result: Mapping[str, Any],
    capture: _CaptureModel,
    application: Mapping[str, Any] | None,
    application_failure_type: str | None,
    base: str,
    candidate: str,
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    if application is None:
        accepted_pages = available = applied = 0
        application_hash = None
    else:
        checked = candidates.validate_application(application)
        registry_receipt = candidates.validate_registry_receipt(
            checked["private_candidate_registry"]["content_free_receipt"]
        )
        accepted_pages = registry_receipt["accepted_unique_identity_page_count"]
        available = registry_receipt["available_candidate_count"]
        applied = checked["content_free_receipt"]["applied_coordinate_count"]
        application_hash = checked["artifact_payload_sha256"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "captured_column_count": len(capture.captured_columns),
        "captured_same_forward_page_count": len(capture.captured_pages),
        "accepted_unique_identity_page_count": int(accepted_pages),
        "available_candidate_count": int(available),
        "applied_coordinate_count": int(applied),
        "positive_signed_credit_count": 0,
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_calls": 0,
        "additional_fetch_calls": 0,
        "additional_provider_tokens": 0,
        "synthesis_capture_attempted": bool(capture.capture_attempted),
        "synthesis_capture_valid": bool(capture.capture_valid),
        "candidate_application_valid": application is not None,
        "candidate_prediction_changed": base != candidate,
        "candidate_identity_handoff": base == candidate,
        "capture_failure_type": (
            capture.capture_failure_type
            if capture.capture_valid or capture.capture_failure_type
            else "SynthesisCaptureNotAttempted"
        ),
        "application_failure_type": application_failure_type,
        "parent_result_payload_sha256": checked_parent["result_payload_sha256"],
        "application_payload_sha256": application_hash,
        "one_v25375_parent_forward_only": True,
        "third_synthesis_prompt_and_provider_request_byte_exact": True,
        "parent_completed_table_row_keys_supply_candidate_identity": True,
        "candidate_consumes_only_same_forward_captured_pages": True,
        "candidate_is_pure_local_deterministic_source_edit": True,
        "zero_candidate_or_capture_failure_preserves_parent_byte_exact": True,
        "query4_fetch14_model3_token_context_and_wall_caps_unchanged": True,
        "runtime_inputs_exactly_opaque_id_question_and_injected_clients": True,
        "contains_question_query_url_title_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    dynamic = (
        "synthesis_capture_attempted",
        "synthesis_capture_valid",
        "candidate_application_valid",
        "candidate_prediction_changed",
        "candidate_identity_handoff",
    )
    true_flags = (
        "one_v25375_parent_forward_only",
        "third_synthesis_prompt_and_provider_request_byte_exact",
        "parent_completed_table_row_keys_supply_candidate_identity",
        "candidate_consumes_only_same_forward_captured_pages",
        "candidate_is_pure_local_deterministic_source_edit",
        "zero_candidate_or_capture_failure_preserves_parent_byte_exact",
        "query4_fetch14_model3_token_context_and_wall_caps_unchanged",
        "runtime_inputs_exactly_opaque_id_question_and_injected_clients",
    )
    false_flags = (
        "contains_question_query_url_title_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *dynamic,
        "capture_failure_type",
        "application_failure_type",
        "parent_result_payload_sha256",
        "application_payload_sha256",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _COUNT_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic)
        or copied["applied_coordinate_count"] != copied["available_candidate_count"]
        or copied["positive_signed_credit_count"] != 0
        or any(copied[name] != 0 for name in _COUNT_FIELDS[-5:])
        or copied["candidate_prediction_changed"]
        is not (copied["applied_coordinate_count"] > 0)
        or copied["candidate_identity_handoff"]
        is not (not copied["candidate_prediction_changed"])
        or copied["synthesis_capture_valid"] and not copied["synthesis_capture_attempted"]
        or copied["candidate_application_valid"] and not copied["synthesis_capture_valid"]
        or copied["candidate_application_valid"]
        is not (copied.get("application_payload_sha256") is not None)
        or copied["candidate_application_valid"]
        and copied.get("application_failure_type") is not None
        or not copied["synthesis_capture_valid"]
        and copied.get("capture_failure_type") is None
        or any(
            item is not None
            and (not isinstance(item, str) or not item or len(item) > 128)
            for item in (
                copied.get("capture_failure_type"),
                copied.get("application_failure_type"),
            )
        )
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or copied.get("application_payload_sha256") is not None
        and (
            not isinstance(copied["application_payload_sha256"], str)
            or len(copied["application_payload_sha256"]) != 64
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.65 runtime receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    capture: _CaptureModel,
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    base = _base(checked_parent)
    application, candidate, failure = _application(base, capture)
    receipt = _receipt(
        parent_result=checked_parent,
        capture=capture,
        application=application,
        application_failure_type=failure,
        base=base,
        candidate=candidate,
    )
    predictions = {BASE_ARM: base, CANDIDATE_ARM: candidate}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked_parent["opaque_id"],
        "status": "terminal",
        "prediction": candidate,
        "prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "prediction_kind": checked_parent["prediction_kind"],
        "predictions": predictions,
        "prediction_sha256_by_arm": {
            arm: hashlib.sha256(prediction.encode()).hexdigest()
            for arm, prediction in predictions.items()
        },
        "prediction_changed": base != candidate,
        "row_key_bound_source_receipt": copy.deepcopy(receipt),
        "private_source_application": copy.deepcopy(application),
        "private_source_columns": list(capture.captured_columns),
        "private_same_forward_pages": copy.deepcopy(capture.captured_pages),
        "private_parent_result": copy.deepcopy(checked_parent),
        "private_parent_result_payload_sha256": checked_parent[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked_parent["cost"]),
        "scored_prediction_is_row_key_bound_source_candidate": True,
        "shared_parent_prediction_is_exact_control": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    raw = copied.get("private_parent_result")
    application = copied.get("private_source_application")
    columns = copied.get("private_source_columns")
    pages = copied.get("private_same_forward_pages")
    receipt = copied.get("row_key_bound_source_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256_by_arm")
    if not isinstance(raw, Mapping):
        raise ValueError("V2.54.65 private parent result is absent")
    parent_result = parent.validate_result(raw)
    base = _base(parent_result)
    checked_application: dict[str, Any] | None = None
    if application is not None:
        if not isinstance(application, Mapping):
            raise ValueError("V2.54.65 private application drifted")
        checked_application = candidates.validate_application(application)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "prediction",
        "prediction_sha256",
        "prediction_kind",
        "predictions",
        "prediction_sha256_by_arm",
        "prediction_changed",
        "row_key_bound_source_receipt",
        "private_source_application",
        "private_source_columns",
        "private_same_forward_pages",
        "private_parent_result",
        "private_parent_result_payload_sha256",
        "cost",
        "scored_prediction_is_row_key_bound_source_candidate",
        "shared_parent_prediction_is_exact_control",
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
        or copied.get("opaque_id") != parent_result["opaque_id"]
        or copied.get("prediction_kind") != parent_result["prediction_kind"]
        or not isinstance(columns, list)
        or any(not isinstance(item, str) for item in columns)
        or not isinstance(pages, list)
        or any(not isinstance(page, Mapping) or set(page) != candidates.PAGE_KEYS for page in pages)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["parent_result_payload_sha256"] != parent_result["result_payload_sha256"]
        or receipt["captured_column_count"] != len(columns)
        or receipt["captured_same_forward_page_count"] != len(pages)
        or copied.get("private_parent_result_payload_sha256")
        != parent_result["result_payload_sha256"]
        or copied.get("cost") != parent_result["cost"]
        or set(predictions or {}) != set(ARMS)
        or predictions[BASE_ARM] != base
        or set(hashes or {}) != set(ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or copied.get("prediction") != predictions[CANDIDATE_ARM]
        or copied.get("prediction_sha256") != hashes[CANDIDATE_ARM]
        or copied.get("prediction_changed")
        is not (predictions[BASE_ARM] != predictions[CANDIDATE_ARM])
        or receipt["candidate_prediction_changed"] is not copied["prediction_changed"]
        or checked_application is None
        and predictions[CANDIDATE_ARM] != predictions[BASE_ARM]
        or checked_application is not None
        and (
            checked_application["control_prediction"] != base
            or checked_application["candidate_prediction"] != predictions[CANDIDATE_ARM]
            or receipt["application_payload_sha256"]
            != checked_application["artifact_payload_sha256"]
            or candidates.validate_application(
                checked_application,
                base_prediction=base,
                columns=columns,
                pages=pages,
            )
            != checked_application
        )
        or copied.get("scored_prediction_is_row_key_bound_source_candidate") is not True
        or copied.get("shared_parent_prediction_is_exact_control") is not True
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
        raise ValueError("V2.54.65 runtime result drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any],
    parent_stage: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["row_key_bound_source_receipt"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "row_key_bound_source_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "one_parent_forward_and_pure_local_candidate_application": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_query_url_page_quote_prediction_answer_opaque_id_or_credential": False,
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
    receipt = copied.get("row_key_bound_source_receipt")
    stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "row_key_bound_source_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        "one_parent_forward_and_pure_local_candidate_application",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
        "contains_question_query_url_page_quote_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not False
        or copied.get("failure_stage") is not None
        or copied.get("failure_type") is not None
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(stage, Mapping)
        or parent.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or stage["outer_physical_budget_receipt"] != budget
        or copied.get("parent_runtime_result_payload_sha256")
        != receipt["parent_result_payload_sha256"]
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or copied.get("one_parent_forward_and_pure_local_candidate_application") is not True
        or copied.get("query_fetch_model_token_context_and_wall_caps_unchanged") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "contains_question_query_url_page_quote_prediction_answer_opaque_id_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.65 runtime stage receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    visible = score.validate_visible_task(task)
    if (
        not isinstance(model, cap.HardCappedModelLimiter)
        or model._budget is not budget
        or not isinstance(model._inner_limiter, DeadlineAwareGlobalModelSlotLimiter)
        or model._synthesis_entry_count != 0
    ):
        raise ValueError("V2.54.65 hard-capped model wiring drifted")
    capture = _CaptureModel(model._inner_limiter, question=visible["question"])
    captured_model = cap.HardCappedModelLimiter(capture, budget)
    parent_result, parent_stage = parent.run_task(
        visible,
        model=captured_model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    if capture.logical_calls != budget.receipt()["model_admitted_count"]:
        raise RuntimeError("V2.54.65 captured model effect count drifted")
    result = validate_result(_wrap_result(parent_result, capture))
    return result, _stage_receipt(result, parent_stage)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "one_parent_forward_only": True,
        "parent_completed_table_supplies_row_keys": True,
        "same_forward_pages_captured_without_prompt_or_request_mutation": True,
        "maximum_physical_queries": 4,
        "maximum_physical_fetches": 14,
        "normal_path_model_forwards": 3,
        "additional_candidate_provider_effects": 0,
        "runtime_input_keys": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "ARMS",
    "BASE_ARM",
    "CANDIDATE_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "STAGE_RECEIPT_ROLE",
    "integration_contract",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
