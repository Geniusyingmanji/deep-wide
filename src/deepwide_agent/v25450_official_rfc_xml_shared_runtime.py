"""Shared-parent runtime with capacity-safe official RFC XML candidates.

V2.54.44 executes once and supplies the unchanged ``shared_base_table``.
After that parent is terminal, this successor reads only the content-free
outer budget receipt.  It uses at most the remaining capacity under the
existing fourteen-fetch cap to fetch a deterministic prefix of the four
official RFC XML URLs derived from strict visible membership.  The batch is
reserved atomically by the inherited hard-capped client, so no over-cap
network effect or budget rejection is attempted.

Only exact non-redirected RFC Editor XML endpoints are admitted.  The pure
V2.54.49 primitive then binds URL, XML root, RFC series identity, and the
existing base row before applying fields.  Missing capacity, failed fetches,
redirects, malformed XML, and unavailable rows preserve the corresponding
base cells.  The parent key-anchored candidate is not composed.

Runtime inputs remain visible ``opaque_id`` and ``question`` plus injected
bounded clients.  No benchmark label, mapping, gold, evaluator, score,
reward, credential, or historical result is available.  The candidate adds
zero query and model calls, at most four fetches, and never exceeds the
existing 4-query / 14-fetch / 3-model envelope.  Entropy/information gain
assigns no signed credit.  This build grants no launch.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25444_key_anchored_metadata_shared_runtime as parent
from . import v25449_official_rfc_xml_record_candidate as candidates


POLICY_ID = "v25450_official_rfc_xml_shared_runtime_v1"
ROLE = "v25450_official_rfc_xml_shared_runtime_result"
RECEIPT_ROLE = "v25450_content_free_official_rfc_xml_shared_receipt"
STAGE_RECEIPT_ROLE = "v25450_content_free_official_rfc_xml_shared_stage_receipt"
ARMS = ("shared_base_table", "official_rfc_xml_record_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
SECOND_PHASE = PHASES[1]
ProductionOnlyStageError = parent.ProductionOnlyStageError
payload_sha256 = parent.payload_sha256


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _exact_success_urls(value: object) -> set[str]:
    output: set[str] = set()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return output
    for batch in value:
        if not isinstance(batch, Mapping):
            continue
        for item in batch.get("results") or []:
            if not isinstance(item, Mapping):
                continue
            requested = str(item.get("requested_url") or item.get("fetch_url") or "")
            final = str(item.get("url") or "")
            if requested and final == requested:
                output.add(requested)
    return output


def _official_pages(
    requests: Sequence[Mapping[str, str]],
    fetched: object,
    search: cap.HardCappedSearchClient,
) -> list[dict[str, str]]:
    successful = _exact_success_urls(fetched)
    output: list[dict[str, str]] = []
    for request in requests:
        url = str(request["url"])
        if url not in successful:
            continue
        prefix = str(search.parent_prefix_for(url))
        if prefix:
            output.append({"url": url, "content": prefix})
    return output


def _fetch_candidate(
    base: str,
    visible_question: str,
    *,
    searches: Mapping[str, cap.HardCappedSearchClient],
    budget: cap.PhysicalEffectBudget,
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    parent_budget = cap.validate_budget_receipt(budget.receipt())
    requests = candidates.request_vector(visible_question)
    remaining = max(0, cap.FETCH_CAP - parent_budget["fetch_admitted_count"])
    admitted_requests = requests[: min(len(requests), remaining)]
    fetched: object = []
    failure: str | None = None
    if admitted_requests:
        try:
            fetched = searches[SECOND_PHASE].fetch_urls(admitted_requests)
        except BaseException as exc:
            failure = _safe_failure(exc)
    pages = _official_pages(admitted_requests, fetched, searches[SECOND_PHASE])
    application = candidates.build_candidate(
        base, question=visible_question, pages=pages
    )
    details = {
        "parent_budget": parent_budget,
        "logical_request_count": len(requests),
        "admitted_request_count": len(admitted_requests),
        "capacity_shortfall_count": len(requests) - len(admitted_requests),
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
    checked_application = candidates.validate_candidate(
        application,
        pages=[],
        replay=False,
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
        "official_xml_logical_request_count": int(
            details["logical_request_count"]
        ),
        "official_xml_admitted_fetch_count": int(
            details["admitted_request_count"]
        ),
        "official_xml_capacity_shortfall_count": int(
            details["capacity_shortfall_count"]
        ),
        "official_xml_exact_nonredirected_page_count": int(
            details["exact_nonredirected_page_count"]
        ),
        "official_xml_valid_record_count": int(
            checked_application["valid_record_count"]
        ),
        "applied_coordinate_count": int(
            checked_application["applied_coordinate_count"]
        ),
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
        "candidate_fetch_failure_type": details[
            "candidate_fetch_failure_type"
        ],
        "parent_result_payload_sha256": checked_parent["result_payload_sha256"],
        "application_payload_sha256": checked_application[
            "artifact_payload_sha256"
        ],
        "one_parent_forward_shared_by_base_and_candidate": True,
        "parent_key_anchored_candidate_not_composed": True,
        "official_urls_derive_only_from_strict_visible_membership": True,
        "only_exact_nonredirected_official_xml_pages_admitted": True,
        "candidate_fetch_batch_never_exceeds_remaining_outer_capacity": True,
        "outer_query4_fetch14_model3_caps_preserved": True,
        "candidate_additional_query_count_zero": True,
        "candidate_additional_model_count_zero": True,
        "partial_capacity_fetch_or_parse_failure_preserves_base_cells": True,
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
        "official_xml_logical_request_count",
        "official_xml_admitted_fetch_count",
        "official_xml_capacity_shortfall_count",
        "official_xml_exact_nonredirected_page_count",
        "official_xml_valid_record_count",
        "applied_coordinate_count",
        "final_query_count",
        "final_fetch_count",
        "final_model_count",
        "positive_signed_credit_count",
    )
    true_flags = (
        "one_parent_forward_shared_by_base_and_candidate",
        "parent_key_anchored_candidate_not_composed",
        "official_urls_derive_only_from_strict_visible_membership",
        "only_exact_nonredirected_official_xml_pages_admitted",
        "candidate_fetch_batch_never_exceeds_remaining_outer_capacity",
        "outer_query4_fetch14_model3_caps_preserved",
        "candidate_additional_query_count_zero",
        "candidate_additional_model_count_zero",
        "partial_capacity_fetch_or_parse_failure_preserves_base_cells",
    )
    false_flags = (
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    failure = copied.get("candidate_fetch_failure_type")
    if (
        copied.get("artifact_version") != 1
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
        != copied["parent_fetch_count"]
        + copied["official_xml_admitted_fetch_count"]
        or copied["official_xml_logical_request_count"]
        != copied["official_xml_admitted_fetch_count"]
        + copied["official_xml_capacity_shortfall_count"]
        or copied["official_xml_logical_request_count"] not in {0, 4}
        or copied["official_xml_admitted_fetch_count"] > 4
        or copied["official_xml_exact_nonredirected_page_count"]
        > copied["official_xml_admitted_fetch_count"]
        or copied["official_xml_valid_record_count"]
        > copied["official_xml_exact_nonredirected_page_count"]
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
        raise ValueError("V2.54.50 content-free receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    application: Mapping[str, Any],
    pages: Sequence[Mapping[str, str]],
    details: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    checked_application = candidates.validate_candidate(
        application, pages=pages
    )
    base = str(checked_parent["predictions"][parent.BASE_ARM])
    candidate = str(checked_application["candidate_prediction"])
    if checked_application["base_prediction"] != base:
        raise ValueError("V2.54.50 shared base drifted")
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
        "official_rfc_xml_receipt": copy.deepcopy(receipt),
        "private_official_rfc_xml_application": copy.deepcopy(
            checked_application
        ),
        "private_same_forward_official_rfc_xml_pages": copy.deepcopy(
            list(pages)
        ),
        "private_parent_result": copy.deepcopy(checked_parent),
        "private_parent_result_payload_sha256": checked_parent[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked_parent["cost"]),
        "scored_prediction_is_official_rfc_xml_candidate": True,
        "shared_base_is_parent_shared_base_not_parent_key_candidate": True,
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
    application = copied.get("private_official_rfc_xml_application")
    pages = copied.get("private_same_forward_official_rfc_xml_pages")
    receipt = copied.get("official_rfc_xml_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256_by_arm")
    if not isinstance(raw, Mapping):
        raise ValueError("V2.54.50 parent result is absent")
    checked_parent = parent.validate_result(raw)
    if not isinstance(pages, list) or any(
        not isinstance(page, Mapping)
        or set(page) != {"url", "content"}
        or not isinstance(page["url"], str)
        or not isinstance(page["content"], str)
        for page in pages
    ):
        raise ValueError("V2.54.50 private page surface drifted")
    if not isinstance(application, Mapping):
        raise ValueError("V2.54.50 application is absent")
    checked_application = candidates.validate_candidate(
        application, pages=pages
    )
    base = str(checked_parent["predictions"][parent.BASE_ARM])
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
        "official_rfc_xml_receipt",
        "private_official_rfc_xml_application",
        "private_same_forward_official_rfc_xml_pages",
        "private_parent_result",
        "private_parent_result_payload_sha256",
        "cost",
        "scored_prediction_is_official_rfc_xml_candidate",
        "shared_base_is_parent_shared_base_not_parent_key_candidate",
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
        or receipt["official_xml_exact_nonredirected_page_count"] != len(pages)
        or receipt["official_xml_valid_record_count"]
        != checked_application["valid_record_count"]
        or receipt["applied_coordinate_count"]
        != checked_application["applied_coordinate_count"]
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
        or copied.get("scored_prediction_is_official_rfc_xml_candidate")
        is not True
        or copied.get(
            "shared_base_is_parent_shared_base_not_parent_key_candidate"
        )
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
        raise ValueError("V2.54.50 runtime result drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any],
    parent_stage: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["official_rfc_xml_receipt"])
    final = cap.validate_budget_receipt(final_budget)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "official_rfc_xml_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(final),
        "one_parent_forward_then_capacity_safe_candidate_fetch": True,
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
    receipt = copied.get("official_rfc_xml_receipt")
    stage = copied.get("parent_stage_receipt")
    final = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "one_parent_forward_then_capacity_safe_candidate_fetch",
        "candidate_fetch_accounted_in_same_outer_budget",
        "outer_query4_fetch14_model3_caps_preserved",
    )
    false_flags = (
        "contains_question_query_url_page_record_value_prediction_answer_opaque_id_or_credential",
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        copied.get("artifact_version") != 1
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
        or final["query_rejected_count"] != 0
        or final["fetch_rejected_count"] != 0
        or final["model_rejected_count"] != 0
        or copied.get("parent_runtime_result_payload_sha256")
        != receipt["parent_result_payload_sha256"]
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.50 stage receipt drifted")
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
    base = str(checked_parent["predictions"][parent.BASE_ARM])
    application, pages, details = _fetch_candidate(
        base,
        visible["question"],
        searches=searches,
        budget=budget,
    )
    final_budget = cap.validate_budget_receipt(budget.receipt())
    result = _wrap_result(
        checked_parent, application, pages, details, final_budget
    )
    return result, _stage_receipt(result, parent_stage, final_budget)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "arms": list(ARMS),
        "one_parent_forward_shared_by_base_and_candidate": True,
        "parent_key_anchored_candidate_not_composed": True,
        "maximum_candidate_additional_fetches": 4,
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "maximum_physical_queries": cap.QUERY_CAP,
        "maximum_physical_fetches": cap.FETCH_CAP,
        "normal_path_model_forwards": 3,
        "remaining_capacity_computed_only_from_content_free_budget_receipt": True,
        "over_cap_candidate_batch_never_attempted": True,
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
