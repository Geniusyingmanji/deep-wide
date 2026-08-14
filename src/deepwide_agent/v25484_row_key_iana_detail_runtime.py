"""Capacity-safe official IANA detail fetch over one V2.54.72 parent.

The V2.54.72 parent executes once and supplies its qualified-label prediction,
completed row key, exact visible columns, and a content-free outer budget
receipt.  This successor derives at most one official IANA detail URL from
that completed row key, then uses only remaining capacity under the existing
four-query / fourteen-fetch / three-model envelope.  The inherited hard cap
reserves the fetch before any underlying effect.

Only an exact non-redirected page is admitted.  V2.54.83 mechanically binds
the row key, page surface, source label, exact value, and target coordinate.
No capacity, fetch, parse, or application success preserves the V2.54.72
prediction byte-for-byte.  Runtime input remains exactly visible
``opaque_id`` and ``question`` plus injected bounded clients.  No benchmark
label, mapping, gold, evaluator, score, reward, credential, or historical
outcome is available.  Entropy/information gain assigns no signed credit.
This build grants no external or benchmark launch.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25472_qualified_source_label_runtime as parent
from . import v25483_row_key_iana_detail_candidate as candidates


POLICY_ID = "v25484_row_key_iana_detail_runtime_v1"
ROLE = "v25484_row_key_iana_detail_runtime_result"
RECEIPT_ROLE = "v25484_content_free_row_key_iana_detail_receipt"
STAGE_RECEIPT_ROLE = "v25484_content_free_row_key_iana_detail_stage_receipt"
ARMS = ("qualified_source_label_parent", "row_key_iana_detail_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
SECOND_PHASE = PHASES[1]
ProductionOnlyStageError = parent.ProductionOnlyStageError
payload_sha256 = parent.payload_sha256


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _exact_pages(
    requests: Sequence[Mapping[str, str]],
    fetched: object,
    search: cap.HardCappedSearchClient,
) -> list[dict[str, str]]:
    requested = {str(item["url"]) for item in requests}
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    if not isinstance(fetched, Sequence) or isinstance(fetched, (str, bytes)):
        return output
    for batch in fetched:
        if not isinstance(batch, Mapping):
            continue
        for item in batch.get("results") or []:
            if not isinstance(item, Mapping):
                continue
            original = str(item.get("requested_url") or item.get("fetch_url") or "")
            final = str(item.get("url") or "")
            if original not in requested or final != original or original in seen:
                continue
            prefix = str(search.parent_prefix_for(original))
            if not prefix:
                continue
            output.append(
                {
                    "url": original,
                    "title": str(item.get("title") or "")[:500],
                    "content": prefix,
                }
            )
            seen.add(original)
    return output


def _fetch_candidate(
    base: str,
    columns: Sequence[str],
    visible_question: str,
    *,
    searches: Mapping[str, cap.HardCappedSearchClient],
    budget: cap.PhysicalEffectBudget,
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    parent_budget = cap.validate_budget_receipt(budget.receipt())
    requests = candidates.request_vector(
        base, columns=columns, question=visible_question
    )
    remaining = max(0, cap.FETCH_CAP - parent_budget["fetch_admitted_count"])
    admitted = requests[: min(len(requests), remaining)]
    fetched: object = []
    failure: str | None = None
    if admitted:
        try:
            fetched = searches[SECOND_PHASE].fetch_urls(admitted)
        except BaseException as exc:
            failure = _safe_failure(exc)
    pages = _exact_pages(admitted, fetched, searches[SECOND_PHASE])
    application = candidates.build_candidate(
        base,
        columns=columns,
        question=visible_question,
        pages=pages,
    )
    details = {
        "parent_budget": parent_budget,
        "logical_request_count": len(requests),
        "admitted_request_count": len(admitted),
        "capacity_shortfall_count": len(requests) - len(admitted),
        "exact_nonredirected_page_count": len(pages),
        "candidate_fetch_failure_type": failure,
    }
    return application, pages, details


def _receipt(
    *,
    parent_result: Mapping[str, Any],
    application: Mapping[str, Any],
    details: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    checked_application = candidates.validate_candidate(application)
    candidate_receipt = candidates.validate_receipt(
        checked_application["content_free_receipt"]
    )
    parent_budget = cap.validate_budget_receipt(details["parent_budget"])
    final = cap.validate_budget_receipt(final_budget)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_query_count": parent_budget["query_admitted_count"],
        "parent_fetch_count": parent_budget["fetch_admitted_count"],
        "parent_model_count": parent_budget["model_admitted_count"],
        "detail_logical_request_count": int(details["logical_request_count"]),
        "detail_admitted_fetch_count": int(details["admitted_request_count"]),
        "detail_capacity_shortfall_count": int(details["capacity_shortfall_count"]),
        "detail_exact_nonredirected_page_count": int(
            details["exact_nonredirected_page_count"]
        ),
        "detail_identity_surface_bound_page_count": candidate_receipt[
            "identity_surface_bound_page_count"
        ],
        "detail_raw_field_surface_count": candidate_receipt[
            "raw_field_surface_count"
        ],
        "detail_evidence_closed_observation_count": candidate_receipt[
            "evidence_closed_observation_count"
        ],
        "available_candidate_count": candidate_receipt["available_candidate_count"],
        "applied_coordinate_count": candidate_receipt["applied_coordinate_count"],
        "final_query_count": final["query_admitted_count"],
        "final_fetch_count": final["fetch_admitted_count"],
        "final_model_count": final["model_admitted_count"],
        "positive_signed_credit_count": 0,
        "candidate_prediction_changed": bool(
            checked_application["candidate_prediction_changed"]
        ),
        "candidate_identity_handoff": not bool(
            checked_application["candidate_prediction_changed"]
        ),
        "candidate_fetch_failure_type": details["candidate_fetch_failure_type"],
        "parent_result_payload_sha256": checked_parent["result_payload_sha256"],
        "application_payload_sha256": checked_application[
            "artifact_payload_sha256"
        ],
        "one_v25472_parent_forward_shared_by_base_and_candidate": True,
        "qualified_source_label_parent_prediction_is_exact_control": True,
        "official_url_derived_only_after_completed_parent_row_key": True,
        "only_exact_nonredirected_official_detail_page_admitted": True,
        "candidate_fetch_never_exceeds_remaining_outer_capacity": True,
        "outer_query4_fetch14_model3_caps_preserved": True,
        "candidate_additional_query_count_zero": True,
        "candidate_additional_model_count_zero": True,
        "capacity_fetch_parse_or_application_failure_preserves_parent": True,
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
    counts = (
        "parent_query_count",
        "parent_fetch_count",
        "parent_model_count",
        "detail_logical_request_count",
        "detail_admitted_fetch_count",
        "detail_capacity_shortfall_count",
        "detail_exact_nonredirected_page_count",
        "detail_identity_surface_bound_page_count",
        "detail_raw_field_surface_count",
        "detail_evidence_closed_observation_count",
        "available_candidate_count",
        "applied_coordinate_count",
        "final_query_count",
        "final_fetch_count",
        "final_model_count",
        "positive_signed_credit_count",
    )
    true_flags = (
        "one_v25472_parent_forward_shared_by_base_and_candidate",
        "qualified_source_label_parent_prediction_is_exact_control",
        "official_url_derived_only_after_completed_parent_row_key",
        "only_exact_nonredirected_official_detail_page_admitted",
        "candidate_fetch_never_exceeds_remaining_outer_capacity",
        "outer_query4_fetch14_model3_caps_preserved",
        "candidate_additional_query_count_zero",
        "candidate_additional_model_count_zero",
        "capacity_fetch_parse_or_application_failure_preserves_parent",
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
        *counts,
        "candidate_prediction_changed",
        "candidate_identity_handoff",
        "candidate_fetch_failure_type",
        "parent_result_payload_sha256",
        "application_payload_sha256",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    failure = copied.get("candidate_fetch_failure_type")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["parent_query_count"] != copied["final_query_count"]
        or copied["parent_model_count"] != copied["final_model_count"]
        or copied["final_fetch_count"]
        != copied["parent_fetch_count"] + copied["detail_admitted_fetch_count"]
        or copied["detail_logical_request_count"]
        != copied["detail_admitted_fetch_count"]
        + copied["detail_capacity_shortfall_count"]
        or copied["detail_logical_request_count"] not in {0, 1}
        or copied["detail_admitted_fetch_count"] > 1
        or copied["detail_exact_nonredirected_page_count"]
        > copied["detail_admitted_fetch_count"]
        or copied["detail_identity_surface_bound_page_count"]
        > copied["detail_exact_nonredirected_page_count"]
        or copied["detail_evidence_closed_observation_count"]
        > copied["detail_raw_field_surface_count"]
        or copied["available_candidate_count"] != copied["applied_coordinate_count"]
        or copied["final_query_count"] > cap.QUERY_CAP
        or copied["final_fetch_count"] > cap.FETCH_CAP
        or copied["final_model_count"] > 3
        or copied["positive_signed_credit_count"] != 0
        or copied.get("candidate_prediction_changed")
        is not (copied["applied_coordinate_count"] > 0)
        or copied.get("candidate_identity_handoff")
        is copied["candidate_prediction_changed"]
        or failure is not None
        and (not isinstance(failure, str) or not failure or len(failure) > 128)
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or not isinstance(copied.get("application_payload_sha256"), str)
        or len(copied["application_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.84 receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    application: Mapping[str, Any],
    details: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    checked_application = candidates.validate_candidate(application)
    base = str(checked_parent["prediction"])
    candidate = str(checked_application["candidate_prediction"])
    if checked_application["base_prediction"] != base:
        raise ValueError("V2.54.84 parent base drifted")
    receipt = _receipt(
        parent_result=checked_parent,
        application=checked_application,
        details=details,
        final_budget=final_budget,
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
        "row_key_iana_detail_receipt": copy.deepcopy(receipt),
        "private_row_key_iana_detail_application": copy.deepcopy(
            checked_application
        ),
        "private_parent_result": copy.deepcopy(checked_parent),
        "private_parent_result_payload_sha256": checked_parent[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked_parent["cost"]),
        "scored_prediction_is_row_key_iana_detail_candidate": True,
        "qualified_source_label_parent_prediction_is_exact_control": True,
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
    raw = copied.get("private_parent_result")
    application = copied.get("private_row_key_iana_detail_application")
    receipt = copied.get("row_key_iana_detail_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256_by_arm")
    if not isinstance(raw, Mapping):
        raise ValueError("V2.54.84 parent result is absent")
    checked_parent = parent.validate_result(raw)
    if not isinstance(application, Mapping):
        raise ValueError("V2.54.84 application is absent")
    checked_application = candidates.validate_candidate(application)
    base = str(checked_parent["prediction"])
    candidate = str(checked_application["candidate_prediction"])
    candidate_receipt = candidates.validate_receipt(
        checked_application["content_free_receipt"]
    )
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
        "row_key_iana_detail_receipt",
        "private_row_key_iana_detail_application",
        "private_parent_result",
        "private_parent_result_payload_sha256",
        "cost",
        "scored_prediction_is_row_key_iana_detail_candidate",
        "qualified_source_label_parent_prediction_is_exact_control",
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
        or checked_application["base_prediction"] != base
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt["application_payload_sha256"]
        != checked_application["artifact_payload_sha256"]
        or receipt["detail_exact_nonredirected_page_count"]
        != candidate_receipt["provided_page_count"]
        or receipt["detail_identity_surface_bound_page_count"]
        != candidate_receipt["identity_surface_bound_page_count"]
        or receipt["detail_raw_field_surface_count"]
        != candidate_receipt["raw_field_surface_count"]
        or receipt["detail_evidence_closed_observation_count"]
        != candidate_receipt["evidence_closed_observation_count"]
        or receipt["available_candidate_count"]
        != candidate_receipt["available_candidate_count"]
        or receipt["applied_coordinate_count"]
        != candidate_receipt["applied_coordinate_count"]
        or receipt["candidate_prediction_changed"]
        is not checked_application["candidate_prediction_changed"]
        or copied.get("private_parent_result_payload_sha256")
        != checked_parent["result_payload_sha256"]
        or copied.get("cost") != checked_parent["cost"]
        or set(predictions or {}) != set(ARMS)
        or predictions[BASE_ARM] != base
        or predictions[CANDIDATE_ARM] != candidate
        or set(hashes or {}) != set(ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or copied.get("prediction") != candidate
        or copied.get("prediction_sha256") != hashes[CANDIDATE_ARM]
        or copied.get("prediction_changed") is not (base != candidate)
        or copied.get("scored_prediction_is_row_key_iana_detail_candidate")
        is not True
        or copied.get("qualified_source_label_parent_prediction_is_exact_control")
        is not True
        or copied.get(
            "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.84 result drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any],
    parent_stage: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["row_key_iana_detail_receipt"])
    final = cap.validate_budget_receipt(final_budget)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "row_key_iana_detail_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(final),
        "one_parent_forward_then_capacity_safe_detail_fetch": True,
        "candidate_fetch_accounted_in_same_outer_budget": True,
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
    receipt = copied.get("row_key_iana_detail_receipt")
    stage = copied.get("parent_stage_receipt")
    final = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "one_parent_forward_then_capacity_safe_detail_fetch",
        "candidate_fetch_accounted_in_same_outer_budget",
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
        "row_key_iana_detail_receipt",
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
        or not isinstance(stage, Mapping)
        or parent.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(final, Mapping)
        or cap.validate_budget_receipt(final) != dict(final)
        or stage["outer_physical_budget_receipt"]["query_admitted_count"]
        != receipt["parent_query_count"]
        or stage["outer_physical_budget_receipt"]["fetch_admitted_count"]
        != receipt["parent_fetch_count"]
        or stage["outer_physical_budget_receipt"]["model_admitted_count"]
        != receipt["parent_model_count"]
        or final["query_admitted_count"] != receipt["final_query_count"]
        or final["fetch_admitted_count"] != receipt["final_fetch_count"]
        or final["model_admitted_count"] != receipt["final_model_count"]
        or any(
            final[f"{kind}_rejected_count"] != 0
            for kind in ("query", "fetch", "model")
        )
        or copied.get("parent_runtime_result_payload_sha256")
        != receipt["parent_result_payload_sha256"]
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.84 stage receipt drifted")
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
    parent_result, parent_stage = parent.run_task(
        visible,
        model=model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    checked_parent = parent.validate_result(parent_result)
    base = str(checked_parent["prediction"])
    columns = tuple(str(value) for value in checked_parent["private_source_columns"])
    application, _pages, details = _fetch_candidate(
        base,
        columns,
        visible["question"],
        searches=searches,
        budget=budget,
    )
    final_budget = cap.validate_budget_receipt(budget.receipt())
    result = _wrap_result(checked_parent, application, details, final_budget)
    return result, _stage_receipt(result, parent_stage, final_budget)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "arms": list(ARMS),
        "one_v25472_parent_forward_shared_by_base_and_candidate": True,
        "qualified_source_label_parent_prediction_is_exact_control": True,
        "maximum_candidate_additional_fetches": 1,
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "maximum_physical_queries": cap.QUERY_CAP,
        "maximum_physical_fetches": cap.FETCH_CAP,
        "normal_path_model_forwards": 3,
        "remaining_capacity_computed_only_from_content_free_budget_receipt": True,
        "over_cap_candidate_fetch_never_attempted": True,
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
