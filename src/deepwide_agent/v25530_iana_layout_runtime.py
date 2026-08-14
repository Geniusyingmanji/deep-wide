"""Matched IANA-layout treatment over one V2.55.14 parent forward.

The parent runs once and supplies the exact generic control plus at most one
same-forward selected detail page.  This wrapper adds no provider effect.  It
applies the pure V2.55.29 IANA delegation-layout parser only to that page and
the shared control table.  Runtime inputs and the outer four-query,
fourteen-fetch, three-model-call envelope remain unchanged.

Failure preserves the control byte-for-byte.  No benchmark label, truth,
evaluator, score, reward, credential, or historical outcome is available;
entropy/information gain assigns no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25514_evidence_coverage_detail_runtime as parent
from . import v25529_iana_layout_candidate as candidates


POLICY_ID = "v25530_iana_delegation_layout_runtime_v1"
ROLE = "v25530_iana_delegation_layout_runtime_result"
RECEIPT_ROLE = "v25530_content_free_iana_delegation_layout_runtime_receipt"
STAGE_RECEIPT_ROLE = "v25530_content_free_iana_delegation_layout_stage_receipt"
ARMS = ("generic_parent_control", "iana_delegation_layout_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
SECOND_PHASE = parent.SECOND_PHASE
ProductionOnlyStageError = parent.ProductionOnlyStageError
payload_sha256 = parent.payload_sha256


def _safe_failure(exc: BaseException) -> str:
    return (type(exc).__name__ or "Exception")[:128]


def _application(
    base: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, str, str | None]:
    try:
        built = candidates.build_candidate(
            base, columns=columns, pages=pages
        )
        checked = candidates.validate_candidate(built)
        if (
            checked["base_prediction"] != base
            or checked["columns"] != list(columns)
            or checked["private_pages"] != list(pages)
        ):
            raise ValueError("V2.55.30 candidate input binding drifted")
        return checked, str(checked["candidate_prediction"]), None
    except BaseException as exc:
        return None, base, _safe_failure(exc)


def _table_difference_count(
    control: str, candidate: str, columns: Sequence[str]
) -> int:
    required, control_rows = candidates.source._canonical_table(control, columns)
    other_required, candidate_rows = candidates.source._canonical_table(
        candidate, columns
    )
    if required != other_required or len(control_rows) != len(candidate_rows):
        raise ValueError("V2.55.30 treatment table shape drifted")
    changed = 0
    for left, right in zip(control_rows, candidate_rows, strict=True):
        if left[0] != right[0] or len(left) != len(right):
            raise ValueError("V2.55.30 treatment row identity drifted")
        changed += sum(
            first != second
            for first, second in zip(left[1:], right[1:], strict=True)
        )
    return changed


def _receipt(
    *,
    parent_result: Mapping[str, Any],
    application: Mapping[str, Any] | None,
    candidate: str,
    application_failure: str | None,
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    parent_receipt = parent.validate_receipt(
        checked_parent["evidence_coverage_detail_receipt"]
    )
    control = str(checked_parent["predictions"][parent.BASE_ARM])
    checked_application = (
        candidates.validate_candidate(application)
        if application is not None
        else None
    )
    parser_receipt = (
        candidates.validate_receipt(
            checked_application["content_free_receipt"]
        )
        if checked_application is not None
        else None
    )
    changed = _table_difference_count(
        control, candidate, checked_parent["private_source_columns"]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_query_count": parent_receipt["final_query_count"],
        "parent_fetch_count": parent_receipt["final_fetch_count"],
        "parent_model_count": parent_receipt["final_model_count"],
        "eligible_unique_link_count": parent_receipt[
            "eligible_unique_link_count"
        ],
        "positive_evidence_deficit_candidate_count": parent_receipt[
            "positive_evidence_deficit_candidate_count"
        ],
        "detail_logical_request_count": parent_receipt[
            "detail_logical_request_count"
        ],
        "detail_admitted_fetch_count": parent_receipt[
            "detail_admitted_fetch_count"
        ],
        "detail_capacity_shortfall_count": parent_receipt[
            "detail_capacity_shortfall_count"
        ],
        "detail_exact_nonredirected_page_count": parent_receipt[
            "detail_exact_nonredirected_page_count"
        ],
        "iana_layout_parser_receipt": copy.deepcopy(parser_receipt),
        "treatment_changed_coordinate_count": changed,
        "final_query_count": parent_receipt["final_query_count"],
        "final_fetch_count": parent_receipt["final_fetch_count"],
        "final_model_count": parent_receipt["final_model_count"],
        "positive_signed_credit_count": 0,
        "candidate_application_valid": checked_application is not None,
        "candidate_prediction_changed": control != candidate,
        "candidate_identity_handoff": control == candidate,
        "candidate_application_failure_type": application_failure,
        "parent_result_payload_sha256": checked_parent["result_payload_sha256"],
        "candidate_application_payload_sha256": (
            checked_application["artifact_payload_sha256"]
            if checked_application is not None
            else None
        ),
        "one_v25514_parent_forward_shared_by_control_and_candidate": True,
        "generic_parent_control_is_exact_parent_base_arm": True,
        "evidence_deficit_selection_and_exact_detail_fetch_inherited_unchanged": True,
        "candidate_uses_only_shared_control_and_selected_detail_page": True,
        "iana_layout_parser_adds_zero_query_fetch_or_model_effect": True,
        "outer_query4_fetch14_model3_caps_preserved": True,
        "application_failure_preserves_control_byte_exact": True,
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    parser_receipt = copied.get("iana_layout_parser_receipt")
    count_fields = (
        "parent_query_count",
        "parent_fetch_count",
        "parent_model_count",
        "eligible_unique_link_count",
        "positive_evidence_deficit_candidate_count",
        "detail_logical_request_count",
        "detail_admitted_fetch_count",
        "detail_capacity_shortfall_count",
        "detail_exact_nonredirected_page_count",
        "treatment_changed_coordinate_count",
        "final_query_count",
        "final_fetch_count",
        "final_model_count",
        "positive_signed_credit_count",
    )
    dynamic_flags = (
        "candidate_application_valid",
        "candidate_prediction_changed",
        "candidate_identity_handoff",
    )
    true_flags = (
        "one_v25514_parent_forward_shared_by_control_and_candidate",
        "generic_parent_control_is_exact_parent_base_arm",
        "evidence_deficit_selection_and_exact_detail_fetch_inherited_unchanged",
        "candidate_uses_only_shared_control_and_selected_detail_page",
        "iana_layout_parser_adds_zero_query_fetch_or_model_effect",
        "outer_query4_fetch14_model3_caps_preserved",
        "application_failure_preserves_control_byte_exact",
    )
    false_flags = (
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *count_fields,
        "iana_layout_parser_receipt",
        *dynamic_flags,
        "candidate_application_failure_type",
        "parent_result_payload_sha256",
        "candidate_application_payload_sha256",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    failure = copied.get("candidate_application_failure_type")
    app_hash = copied.get("candidate_application_payload_sha256")
    parser_valid = parser_receipt is not None
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic_flags)
        or parser_valid
        and (
            not isinstance(parser_receipt, Mapping)
            or candidates.validate_receipt(parser_receipt)
            != dict(parser_receipt)
        )
        or copied["parent_query_count"] != copied["final_query_count"]
        or copied["parent_fetch_count"] != copied["final_fetch_count"]
        or copied["parent_model_count"] != copied["final_model_count"]
        or copied["detail_logical_request_count"]
        != copied["detail_admitted_fetch_count"]
        + copied["detail_capacity_shortfall_count"]
        or copied["detail_logical_request_count"] not in {0, 1}
        or copied["detail_admitted_fetch_count"] > 1
        or copied["detail_exact_nonredirected_page_count"]
        > copied["detail_admitted_fetch_count"]
        or parser_valid
        and parser_receipt["provided_page_count"]
        != copied["detail_exact_nonredirected_page_count"]
        or parser_valid
        and parser_receipt["applied_coordinate_count"]
        != copied["treatment_changed_coordinate_count"]
        or parser_valid
        and parser_receipt["iana_layout_complete_page_count"]
        > parser_receipt["identity_surface_bound_page_count"]
        or copied["candidate_prediction_changed"]
        is not (copied["treatment_changed_coordinate_count"] > 0)
        or copied["candidate_identity_handoff"]
        is copied["candidate_prediction_changed"]
        or copied["candidate_application_valid"] is not parser_valid
        or copied["candidate_application_valid"] is not (app_hash is not None)
        or copied["candidate_application_valid"] is not (failure is None)
        or failure is not None
        and (not isinstance(failure, str) or not failure or len(failure) > 128)
        or app_hash is not None
        and (not isinstance(app_hash, str) or len(app_hash) != 64)
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or copied["final_query_count"] > cap.QUERY_CAP
        or copied["final_fetch_count"] > cap.FETCH_CAP
        or copied["final_model_count"] > 3
        or copied["positive_signed_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.30 receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    application: Mapping[str, Any] | None,
    candidate: str,
    application_failure: str | None,
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    control = str(checked_parent["predictions"][parent.BASE_ARM])
    checked_application = (
        candidates.validate_candidate(application)
        if application is not None
        else None
    )
    if checked_application is not None and (
        checked_application["base_prediction"] != control
        or checked_application["columns"]
        != checked_parent["private_source_columns"]
        or checked_application["private_pages"]
        != checked_parent["private_detail_pages"]
        or checked_application["candidate_prediction"] != candidate
    ):
        raise ValueError("V2.55.30 application binding drifted")
    receipt = _receipt(
        parent_result=checked_parent,
        application=checked_application,
        candidate=candidate,
        application_failure=application_failure,
    )
    predictions = {BASE_ARM: control, CANDIDATE_ARM: candidate}
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
            arm: hashlib.sha256(text.encode()).hexdigest()
            for arm, text in predictions.items()
        },
        "prediction_changed": control != candidate,
        "iana_layout_receipt": copy.deepcopy(receipt),
        "private_iana_layout_application": copy.deepcopy(checked_application),
        "private_parent_result": copy.deepcopy(checked_parent),
        "private_parent_result_payload_sha256": checked_parent[
            "result_payload_sha256"
        ],
        "private_source_columns": copy.deepcopy(
            checked_parent["private_source_columns"]
        ),
        "cost": copy.deepcopy(checked_parent["cost"]),
        "scored_prediction_is_iana_delegation_layout_candidate": True,
        "generic_parent_control_is_exact_parent_base_arm": True,
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    raw_parent = copied.get("private_parent_result")
    raw_application = copied.get("private_iana_layout_application")
    receipt = copied.get("iana_layout_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256_by_arm")
    if not isinstance(raw_parent, Mapping):
        raise ValueError("V2.55.30 parent result absent")
    checked_parent = parent.validate_result(raw_parent)
    control = str(checked_parent["predictions"][parent.BASE_ARM])
    checked_application = None
    candidate = control
    if raw_application is not None:
        if not isinstance(raw_application, Mapping):
            raise ValueError("V2.55.30 application drifted")
        checked_application = candidates.validate_candidate(raw_application)
        if (
            checked_application["base_prediction"] != control
            or checked_application["columns"]
            != checked_parent["private_source_columns"]
            or checked_application["private_pages"]
            != checked_parent["private_detail_pages"]
        ):
            raise ValueError("V2.55.30 application replay input drifted")
        candidate = str(checked_application["candidate_prediction"])
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
        "iana_layout_receipt",
        "private_iana_layout_application",
        "private_parent_result",
        "private_parent_result_payload_sha256",
        "private_source_columns",
        "cost",
        "scored_prediction_is_iana_delegation_layout_candidate",
        "generic_parent_control_is_exact_parent_base_arm",
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
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
        or copied.get("opaque_id") != checked_parent["opaque_id"]
        or copied.get("prediction_kind") != checked_parent["prediction_kind"]
        or copied.get("private_source_columns")
        != checked_parent["private_source_columns"]
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt["candidate_application_payload_sha256"]
        != (
            checked_application["artifact_payload_sha256"]
            if checked_application is not None
            else None
        )
        or copied.get("private_parent_result_payload_sha256")
        != checked_parent["result_payload_sha256"]
        or copied.get("cost") != checked_parent["cost"]
        or set(predictions or {}) != set(ARMS)
        or predictions[BASE_ARM] != control
        or predictions[CANDIDATE_ARM] != candidate
        or set(hashes or {}) != set(ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or copied.get("prediction") != candidate
        or copied.get("prediction_sha256") != hashes[CANDIDATE_ARM]
        or copied.get("prediction_changed") is not (control != candidate)
        or receipt["candidate_prediction_changed"]
        is not copied["prediction_changed"]
        or receipt["treatment_changed_coordinate_count"]
        != _table_difference_count(
            control, candidate, checked_parent["private_source_columns"]
        )
        or copied.get("scored_prediction_is_iana_delegation_layout_candidate")
        is not True
        or copied.get("generic_parent_control_is_exact_parent_base_arm")
        is not True
        or any(
            copied.get(name) is not False
            for name in (
                "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.30 result drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_result(result)
    checked_parent_stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["iana_layout_receipt"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "iana_layout_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(checked_parent_stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            checked_parent_stage["outer_physical_budget_receipt"]
        ),
        "one_parent_forward_then_pure_iana_layout_application": True,
        "iana_layout_parser_adds_zero_provider_effect": True,
        "outer_query4_fetch14_model3_caps_preserved": True,
        "contains_question_query_url_page_record_value_prediction_answer_opaque_id_or_credential": False,
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_stage_receipt(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    receipt = copied.get("iana_layout_receipt")
    parent_stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "one_parent_forward_then_pure_iana_layout_application",
        "iana_layout_parser_adds_zero_provider_effect",
        "outer_query4_fetch14_model3_caps_preserved",
    )
    false_flags = (
        "contains_question_query_url_page_record_value_prediction_answer_opaque_id_or_credential",
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "iana_layout_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        *true_flags,
        *false_flags,
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
        or not isinstance(parent_stage, Mapping)
        or parent.validate_stage_receipt(parent_stage) != dict(parent_stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or copied.get("parent_runtime_result_payload_sha256")
        != parent_stage["runtime_result_payload_sha256"]
        or receipt["parent_query_count"] != budget["query_admitted_count"]
        or receipt["parent_fetch_count"] != budget["fetch_admitted_count"]
        or receipt["parent_model_count"] != budget["model_admitted_count"]
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.30 stage receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.Limits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    parent_result, parent_stage = parent.run_task(
        task,
        model=model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    checked_parent = parent.validate_result(parent_result)
    checked_parent_stage = parent.validate_stage_receipt(parent_stage)
    control = str(checked_parent["predictions"][parent.BASE_ARM])
    application, candidate, failure = _application(
        control,
        columns=checked_parent["private_source_columns"],
        pages=checked_parent["private_detail_pages"],
    )
    result = _wrap_result(
        checked_parent, application, candidate, failure
    )
    stage = _stage_receipt(result, checked_parent_stage)
    return validate_result(result), validate_stage_receipt(stage)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "one_parent_forward": True,
        "base_arm": BASE_ARM,
        "candidate_arm": CANDIDATE_ARM,
        "candidate_pages": "same_forward_selected_exact_detail_page_only",
        "maximum_candidate_additional_fetches_beyond_parent": 0,
        "candidate_additional_queries_beyond_parent": 0,
        "candidate_additional_model_calls_beyond_parent": 0,
        "outer_query_cap": cap.QUERY_CAP,
        "outer_fetch_cap": cap.FETCH_CAP,
        "outer_normal_path_model_cap": 3,
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
    "ROLE",
    "integration_contract",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
