"""One-parent generic mechanical-field runtime over V2.54.92.

V2.54.92 executes exactly once and remains the sole effectful parent.  Its
qualified-source-label control table, same-forward parent pages, and at most
one exact visible-link detail page are then handed together to the pure
V2.54.99 candidate.  Thus one identical mechanical grammar applies to both
page classes without changing any query, fetch, model request, prompt, token,
deadline, or outer ``4 query / 14 fetch / 3 model`` cap.

Candidate parsing or application failure preserves the V2.54.92 control
prediction byte-for-byte.  Runtime inputs remain exactly visible
``opaque_id`` and ``question`` plus injected bounded clients.  No benchmark
label, mapping, truth, evaluator, score, reward, credential, or historical
outcome is read.  Entropy/information gain assigns zero signed credit.  This
build authorizes no external forward, benchmark launch, or evaluator.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25492_visible_row_key_detail_runtime as parent
from . import v25499_generic_mechanical_field_candidate as candidates


POLICY_ID = "v25500_generic_mechanical_field_runtime_v1"
ROLE = "v25500_generic_mechanical_field_runtime_result"
RECEIPT_ROLE = "v25500_content_free_generic_mechanical_field_receipt"
STAGE_RECEIPT_ROLE = "v25500_content_free_generic_mechanical_field_stage_receipt"
ARMS = ("v25492_qualified_parent_control", "generic_mechanical_field_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
ProductionOnlyStageError = parent.ProductionOnlyStageError
payload_sha256 = parent.payload_sha256


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__ or "Exception"
    return name[:128]


def _base(parent_result: Mapping[str, Any]) -> str:
    checked = parent.validate_result(parent_result)
    predictions = checked["predictions"]
    value = str(predictions[parent.BASE_ARM])
    if not value:
        raise ValueError("V2.55.00 parent control prediction is absent")
    return value


def _combined_pages(parent_result: Mapping[str, Any]) -> list[dict[str, str]]:
    checked = parent.validate_result(parent_result)
    nested = checked["private_parent_result"]
    parent_pages = nested["private_same_forward_pages"]
    detail_pages = checked["private_detail_pages"]
    pages = [copy.deepcopy(dict(page)) for page in (*parent_pages, *detail_pages)]
    if (
        len(pages) > cap.FETCH_CAP
        or any(set(page) != candidates.PAGE_KEYS for page in pages)
    ):
        raise ValueError("V2.55.00 combined page boundary drifted")
    return pages


def _application(
    base: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, str, str | None]:
    try:
        value = candidates.build_application(
            base, columns=columns, pages=pages
        )
        checked = candidates.validate_application(
            value, base_prediction=base, columns=columns, pages=pages
        )
        return checked, str(checked["candidate_prediction"]), None
    except BaseException as exc:
        return None, base, _safe_failure(exc)


def _receipt(
    *,
    parent_result: Mapping[str, Any],
    application: Mapping[str, Any] | None,
    application_failure_type: str | None,
    combined_pages: Sequence[Mapping[str, Any]],
    base: str,
    candidate: str,
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    parent_receipt = parent.validate_receipt(
        checked_parent["visible_row_key_detail_receipt"]
    )
    final = cap.validate_budget_receipt(final_budget)
    parent_page_count = len(
        checked_parent["private_parent_result"]["private_same_forward_pages"]
    )
    detail_page_count = len(checked_parent["private_detail_pages"])
    if application is None:
        registry_receipt = None
        field_surfaces = observations = available = applied = 0
        application_hash = None
    else:
        checked_application = candidates.validate_application(application)
        registry_receipt = candidates.validate_registry_receipt(
            checked_application["private_candidate_registry"]["content_free_receipt"]
        )
        field_surfaces = registry_receipt[
            "generic_mechanical_field_surface_count"
        ]
        observations = registry_receipt[
            "generic_mechanical_observation_count"
        ]
        available = registry_receipt["available_candidate_count"]
        applied = checked_application["content_free_receipt"][
            "applied_coordinate_count"
        ]
        application_hash = checked_application["artifact_payload_sha256"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_same_forward_page_count": parent_page_count,
        "exact_detail_page_count": detail_page_count,
        "combined_candidate_page_count": len(combined_pages),
        "generic_mechanical_field_surface_count": int(field_surfaces),
        "generic_mechanical_observation_count": int(observations),
        "available_candidate_count": int(available),
        "applied_coordinate_count": int(applied),
        "final_query_count": final["query_admitted_count"],
        "final_fetch_count": final["fetch_admitted_count"],
        "final_model_count": final["model_admitted_count"],
        "positive_signed_credit_count": 0,
        "candidate_prediction_changed": base != candidate,
        "candidate_identity_handoff": base == candidate,
        "candidate_application_failure_type": application_failure_type,
        "parent_result_payload_sha256": checked_parent["result_payload_sha256"],
        "application_payload_sha256": application_hash,
        "one_v25492_parent_forward_only": True,
        "v25492_qualified_parent_prediction_is_exact_control": True,
        "parent_and_detail_pages_share_one_generic_mechanical_grammar": True,
        "parent_pages_come_only_from_same_forward_synthesis_capture": True,
        "detail_pages_are_only_exact_nonredirected_visible_link_fetches": True,
        "candidate_additional_query_fetch_and_model_counts_zero": True,
        "outer_query4_fetch14_model3_caps_preserved": True,
        "application_failure_preserves_parent_control_byte_exact": True,
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
        "parent_same_forward_page_count",
        "exact_detail_page_count",
        "combined_candidate_page_count",
        "generic_mechanical_field_surface_count",
        "generic_mechanical_observation_count",
        "available_candidate_count",
        "applied_coordinate_count",
        "final_query_count",
        "final_fetch_count",
        "final_model_count",
        "positive_signed_credit_count",
    )
    true_flags = (
        "one_v25492_parent_forward_only",
        "v25492_qualified_parent_prediction_is_exact_control",
        "parent_and_detail_pages_share_one_generic_mechanical_grammar",
        "parent_pages_come_only_from_same_forward_synthesis_capture",
        "detail_pages_are_only_exact_nonredirected_visible_link_fetches",
        "candidate_additional_query_fetch_and_model_counts_zero",
        "outer_query4_fetch14_model3_caps_preserved",
        "application_failure_preserves_parent_control_byte_exact",
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
        "candidate_application_failure_type",
        "parent_result_payload_sha256",
        "application_payload_sha256",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    failure = copied.get("candidate_application_failure_type")
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
        or copied["combined_candidate_page_count"]
        != copied["parent_same_forward_page_count"]
        + copied["exact_detail_page_count"]
        or copied["combined_candidate_page_count"] > cap.FETCH_CAP
        or copied["generic_mechanical_observation_count"]
        > copied["generic_mechanical_field_surface_count"]
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
        or copied.get("application_payload_sha256") is not None
        and (
            not isinstance(copied["application_payload_sha256"], str)
            or len(copied["application_payload_sha256"]) != 64
        )
        or (copied["application_payload_sha256"] is None)
        is not (failure is not None)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.00 runtime receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    base = _base(checked_parent)
    columns = tuple(str(value) for value in checked_parent["private_source_columns"])
    pages = _combined_pages(checked_parent)
    application, candidate, failure = _application(
        base, columns=columns, pages=pages
    )
    receipt = _receipt(
        parent_result=checked_parent,
        application=application,
        application_failure_type=failure,
        combined_pages=pages,
        base=base,
        candidate=candidate,
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
        "generic_mechanical_field_receipt": copy.deepcopy(receipt),
        "private_generic_mechanical_application": copy.deepcopy(application),
        "private_combined_candidate_pages": copy.deepcopy(pages),
        "private_source_columns": list(columns),
        "private_parent_result": copy.deepcopy(checked_parent),
        "private_parent_result_payload_sha256": checked_parent[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked_parent["cost"]),
        "scored_prediction_is_generic_mechanical_field_candidate": True,
        "v25492_qualified_parent_prediction_is_exact_control": True,
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
    application = copied.get("private_generic_mechanical_application")
    pages = copied.get("private_combined_candidate_pages")
    columns = copied.get("private_source_columns")
    receipt = copied.get("generic_mechanical_field_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256_by_arm")
    if not isinstance(raw_parent, Mapping):
        raise ValueError("V2.55.00 private parent absent")
    checked_parent = parent.validate_result(raw_parent)
    base = _base(checked_parent)
    expected_pages = _combined_pages(checked_parent)
    if (
        not isinstance(columns, list)
        or any(not isinstance(item, str) for item in columns)
        or not isinstance(pages, list)
        or any(not isinstance(page, Mapping) for page in pages)
    ):
        raise ValueError("V2.55.00 replay inputs drifted")
    checked_application: dict[str, Any] | None = None
    candidate = base
    if application is not None:
        if not isinstance(application, Mapping):
            raise ValueError("V2.55.00 application drifted")
        checked_application = candidates.validate_application(
            application,
            base_prediction=base,
            columns=columns,
            pages=pages,
        )
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
        "generic_mechanical_field_receipt",
        "private_generic_mechanical_application",
        "private_combined_candidate_pages",
        "private_source_columns",
        "private_parent_result",
        "private_parent_result_payload_sha256",
        "cost",
        "scored_prediction_is_generic_mechanical_field_candidate",
        "v25492_qualified_parent_prediction_is_exact_control",
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
        or columns != checked_parent["private_source_columns"]
        or pages != expected_pages
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt["combined_candidate_page_count"] != len(pages)
        or receipt["application_payload_sha256"]
        != (
            checked_application["artifact_payload_sha256"]
            if checked_application is not None
            else None
        )
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
        or receipt["candidate_prediction_changed"] is not copied["prediction_changed"]
        or copied.get("scored_prediction_is_generic_mechanical_field_candidate")
        is not True
        or copied.get("v25492_qualified_parent_prediction_is_exact_control")
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
        raise ValueError("V2.55.00 runtime result drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any],
    parent_stage: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["generic_mechanical_field_receipt"])
    final = cap.validate_budget_receipt(final_budget)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "generic_mechanical_field_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(final),
        "one_effectful_parent_then_pure_generic_candidate": True,
        "parent_and_candidate_share_exact_effect_snapshot": True,
        "outer_query4_fetch14_model3_caps_preserved": True,
        "contains_question_query_url_anchor_page_record_value_prediction_answer_opaque_id_or_credential": False,
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
    receipt = copied.get("generic_mechanical_field_receipt")
    stage = copied.get("parent_stage_receipt")
    final = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "one_effectful_parent_then_pure_generic_candidate",
        "parent_and_candidate_share_exact_effect_snapshot",
        "outer_query4_fetch14_model3_caps_preserved",
    )
    false_flags = (
        "contains_question_query_url_anchor_page_record_value_prediction_answer_opaque_id_or_credential",
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
        "generic_mechanical_field_receipt",
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
        or final != stage["outer_physical_budget_receipt"]
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
        raise ValueError("V2.55.00 stage receipt drifted")
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
    final = cap.validate_budget_receipt(budget.receipt())
    result = _wrap_result(parent_result, final)
    return result, _stage_receipt(result, parent_stage, final)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "arms": list(ARMS),
        "one_v25492_parent_forward_only": True,
        "same_generic_grammar_over_parent_and_detail_pages": True,
        "maximum_candidate_additional_fetches_beyond_v25492": 0,
        "maximum_total_additional_fetches_beyond_v25472": 1,
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "maximum_physical_queries": cap.QUERY_CAP,
        "maximum_physical_fetches": cap.FETCH_CAP,
        "normal_path_model_forwards": 3,
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
