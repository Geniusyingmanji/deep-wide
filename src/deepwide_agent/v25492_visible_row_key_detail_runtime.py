"""Capacity-safe generic row-key detail successor over one frozen parent.

The V2.54.72 parent runs exactly once.  Transparent task-local search facades
mirror, without modifying, the page batches returned by that same forward.
After the parent table is terminal, V2.54.91 may select one globally
unambiguous visible child link whose URL path and anchor both bind the same
completed row key.  Only remaining capacity under the existing four-query,
fourteen-fetch, three-model envelope may be used for that direct fetch.

The exact non-redirected detail page is passed to V2.54.71, which applies only
evidence-closed structured fields bound by row key, URL path, page surface,
visible column label, and verbatim source value.  Missing capacity, ambiguity,
redirects, fetch failures, parse failures, and conflicts preserve the parent
prediction byte-for-byte.  Runtime inputs remain exactly visible ``opaque_id``
and ``question`` plus injected bounded clients.  No benchmark label, mapping,
truth, evaluator, score, reward, credential, or historical outcome is read.
Entropy/information gain assigns no signed credit.  This build authorizes no
external forward, benchmark launch, or evaluator.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25471_qualified_source_label_candidate as candidates
from . import v25472_qualified_source_label_runtime as parent
from . import v25491_visible_row_key_detail_selection as selection


POLICY_ID = "v25492_visible_row_key_detail_runtime_v1"
ROLE = "v25492_visible_row_key_detail_runtime_result"
RECEIPT_ROLE = "v25492_content_free_visible_row_key_detail_receipt"
STAGE_RECEIPT_ROLE = "v25492_content_free_visible_row_key_detail_stage_receipt"
ARMS = ("qualified_source_label_parent", "visible_row_key_detail_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
SECOND_PHASE = PHASES[1]
ProductionOnlyStageError = parent.ProductionOnlyStageError
payload_sha256 = parent.payload_sha256


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__ or "Exception"
    return name[:128]


class _CaptureSearch(cap.HardCappedSearchClient):
    """Transparent mirror around one already hard-capped search client."""

    def __init__(self, wrapped: cap.HardCappedSearchClient) -> None:
        if not isinstance(wrapped, cap.HardCappedSearchClient):
            raise TypeError("V2.54.92 capture search boundary drifted")
        self._wrapped = wrapped
        self._budget = wrapped._budget
        self._phase = wrapped._phase
        self.fetch_batches: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> Any:
        return self._wrapped.search_many(queries, **kwargs)

    def fetch_urls(self, requests: Sequence[Mapping[str, str]]) -> Any:
        output = self._wrapped.fetch_urls(requests)
        if isinstance(output, Sequence) and not isinstance(output, (str, bytes)):
            self.fetch_batches.extend(
                copy.deepcopy(item) for item in output if isinstance(item, Mapping)
            )
        return output

    def late_page_projection_receipt(self) -> dict[str, Any]:
        return self._wrapped.late_page_projection_receipt()

    def parent_prefix_for(self, url: str) -> str:
        return str(self._wrapped.parent_prefix_for(url))

    def remaining_effect_seconds(self) -> float:
        return float(self._wrapped.remaining_effect_seconds())


def _exact_pages(
    requests: Sequence[Mapping[str, str]],
    fetched: object,
    search: _CaptureSearch,
) -> list[dict[str, str]]:
    requested = {str(item["url"]) for item in requests}
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    if not isinstance(fetched, Sequence) or isinstance(fetched, (str, bytes)):
        return output
    for batch in fetched:
        if not isinstance(batch, Mapping):
            continue
        results = batch.get("results")
        if not isinstance(results, Sequence) or isinstance(results, (str, bytes)):
            continue
        for item in results:
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


def _candidate(
    base: str,
    columns: Sequence[str],
    pre_detail_fetch_batches: Sequence[Mapping[str, Any]],
    *,
    searches: Mapping[str, _CaptureSearch],
    budget: cap.PhysicalEffectBudget,
) -> tuple[
    dict[str, Any],
    dict[str, Any] | None,
    list[dict[str, str]],
    dict[str, Any],
]:
    parent_budget = cap.validate_budget_receipt(budget.receipt())
    selected = selection.build_selection(
        base,
        columns=columns,
        fetch_batches=pre_detail_fetch_batches,
    )
    checked_selection = selection.validate_selection(
        selected,
        base_prediction=base,
        columns=columns,
        fetch_batches=pre_detail_fetch_batches,
    )
    requests = list(checked_selection["requests"])
    remaining = max(0, cap.FETCH_CAP - parent_budget["fetch_admitted_count"])
    admitted = requests[: min(len(requests), remaining)]
    fetched: object = []
    fetch_failure: str | None = None
    if admitted:
        try:
            fetched = searches[SECOND_PHASE].fetch_urls(admitted)
        except BaseException as exc:
            fetch_failure = _safe_failure(exc)
    pages = _exact_pages(admitted, fetched, searches[SECOND_PHASE])
    application: dict[str, Any] | None = None
    application_failure: str | None = None
    try:
        built = candidates.build_application(base, columns=columns, pages=pages)
        application = candidates.validate_application(
            built, base_prediction=base, columns=columns, pages=pages
        )
    except BaseException as exc:
        application_failure = _safe_failure(exc)
    details = {
        "parent_budget": parent_budget,
        "logical_request_count": len(requests),
        "admitted_request_count": len(admitted),
        "capacity_shortfall_count": len(requests) - len(admitted),
        "exact_nonredirected_page_count": len(pages),
        "candidate_fetch_failure_type": fetch_failure,
        "candidate_application_failure_type": application_failure,
    }
    return checked_selection, application, pages, details


def _application_counts(
    application: Mapping[str, Any] | None,
) -> tuple[int, int, int, str | None]:
    if application is None:
        return 0, 0, 0, None
    checked = candidates.validate_application(application)
    registry = candidates.validate_registry_receipt(
        checked["private_candidate_registry"]["content_free_receipt"]
    )
    return (
        int(registry["accepted_unique_identity_page_count"]),
        int(registry["available_candidate_count"]),
        int(checked["content_free_receipt"]["applied_coordinate_count"]),
        str(checked["artifact_payload_sha256"]),
    )


def _receipt(
    *,
    parent_result: Mapping[str, Any],
    selected: Mapping[str, Any],
    application: Mapping[str, Any] | None,
    details: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    checked_selection = selection.validate_selection(selected)
    selector_receipt = selection.validate_receipt(
        checked_selection["content_free_receipt"]
    )
    parent_budget = cap.validate_budget_receipt(details["parent_budget"])
    final = cap.validate_budget_receipt(final_budget)
    accepted_pages, available, applied, application_hash = _application_counts(
        application
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_query_count": parent_budget["query_admitted_count"],
        "parent_fetch_count": parent_budget["fetch_admitted_count"],
        "parent_model_count": parent_budget["model_admitted_count"],
        "raw_fetched_page_count": selector_receipt["raw_fetched_page_count"],
        "raw_page_visible_link_count": selector_receipt[
            "raw_page_visible_link_count"
        ],
        "joint_bound_link_count": selector_receipt["joint_bound_link_count"],
        "eligible_unique_link_count": selector_receipt[
            "eligible_unique_link_count"
        ],
        "detail_logical_request_count": int(details["logical_request_count"]),
        "detail_admitted_fetch_count": int(details["admitted_request_count"]),
        "detail_capacity_shortfall_count": int(details["capacity_shortfall_count"]),
        "detail_exact_nonredirected_page_count": int(
            details["exact_nonredirected_page_count"]
        ),
        "detail_accepted_unique_identity_page_count": accepted_pages,
        "available_candidate_count": available,
        "applied_coordinate_count": applied,
        "final_query_count": final["query_admitted_count"],
        "final_fetch_count": final["fetch_admitted_count"],
        "final_model_count": final["model_admitted_count"],
        "positive_signed_credit_count": 0,
        "candidate_prediction_changed": applied > 0,
        "candidate_identity_handoff": applied == 0,
        "candidate_fetch_failure_type": details["candidate_fetch_failure_type"],
        "candidate_application_failure_type": details[
            "candidate_application_failure_type"
        ],
        "parent_result_payload_sha256": checked_parent["result_payload_sha256"],
        "selection_payload_sha256": checked_selection["artifact_payload_sha256"],
        "application_payload_sha256": application_hash,
        "one_v25472_parent_forward_shared_by_base_and_candidate": True,
        "qualified_source_label_parent_prediction_is_exact_control": True,
        "candidate_url_selected_only_from_same_forward_visible_links": True,
        "candidate_url_path_and_anchor_bind_one_completed_parent_row_key": True,
        "only_exact_nonredirected_detail_page_admitted": True,
        "detail_fields_require_row_key_page_surface_and_visible_schema_binding": True,
        "candidate_fetch_never_exceeds_remaining_outer_capacity": True,
        "outer_query4_fetch14_model3_caps_preserved": True,
        "candidate_additional_query_count_zero": True,
        "candidate_additional_model_count_zero": True,
        "capacity_selection_fetch_parse_or_application_failure_preserves_parent": True,
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
        "raw_fetched_page_count",
        "raw_page_visible_link_count",
        "joint_bound_link_count",
        "eligible_unique_link_count",
        "detail_logical_request_count",
        "detail_admitted_fetch_count",
        "detail_capacity_shortfall_count",
        "detail_exact_nonredirected_page_count",
        "detail_accepted_unique_identity_page_count",
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
        "candidate_url_selected_only_from_same_forward_visible_links",
        "candidate_url_path_and_anchor_bind_one_completed_parent_row_key",
        "only_exact_nonredirected_detail_page_admitted",
        "detail_fields_require_row_key_page_surface_and_visible_schema_binding",
        "candidate_fetch_never_exceeds_remaining_outer_capacity",
        "outer_query4_fetch14_model3_caps_preserved",
        "candidate_additional_query_count_zero",
        "candidate_additional_model_count_zero",
        "capacity_selection_fetch_parse_or_application_failure_preserves_parent",
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
        "candidate_application_failure_type",
        "parent_result_payload_sha256",
        "selection_payload_sha256",
        "application_payload_sha256",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    failure_fields = (
        copied.get("candidate_fetch_failure_type"),
        copied.get("candidate_application_failure_type"),
    )
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
        or copied["detail_accepted_unique_identity_page_count"]
        > copied["detail_exact_nonredirected_page_count"]
        or copied["available_candidate_count"] != copied["applied_coordinate_count"]
        or copied["final_query_count"] > cap.QUERY_CAP
        or copied["final_fetch_count"] > cap.FETCH_CAP
        or copied["final_model_count"] > 3
        or copied["positive_signed_credit_count"] != 0
        or copied.get("candidate_prediction_changed")
        is not (copied["applied_coordinate_count"] > 0)
        or copied.get("candidate_identity_handoff")
        is copied["candidate_prediction_changed"]
        or any(
            item is not None
            and (not isinstance(item, str) or not item or len(item) > 128)
            for item in failure_fields
        )
        or any(
            not isinstance(copied.get(name), str) or len(copied[name]) != 64
            for name in (
                "parent_result_payload_sha256",
                "selection_payload_sha256",
            )
        )
        or copied.get("application_payload_sha256") is not None
        and (
            not isinstance(copied["application_payload_sha256"], str)
            or len(copied["application_payload_sha256"]) != 64
        )
        or (copied["application_payload_sha256"] is None)
        is not (copied["candidate_application_failure_type"] is not None)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.92 runtime receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    selected: Mapping[str, Any],
    application: Mapping[str, Any] | None,
    pre_detail_fetch_batches: Sequence[Mapping[str, Any]],
    pages: Sequence[Mapping[str, str]],
    details: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    checked_selection = selection.validate_selection(selected)
    base = str(checked_parent["prediction"])
    candidate = base
    checked_application: dict[str, Any] | None = None
    if application is not None:
        checked_application = candidates.validate_application(application)
        if checked_application["control_prediction"] != base:
            raise ValueError("V2.54.92 application control drifted")
        candidate = str(checked_application["candidate_prediction"])
    receipt = _receipt(
        parent_result=checked_parent,
        selected=checked_selection,
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
        "visible_row_key_detail_receipt": copy.deepcopy(receipt),
        "private_visible_link_selection": copy.deepcopy(checked_selection),
        "private_detail_application": copy.deepcopy(checked_application),
        "private_pre_detail_fetch_batches": copy.deepcopy(
            list(pre_detail_fetch_batches)
        ),
        "private_detail_pages": copy.deepcopy(list(pages)),
        "private_source_columns": copy.deepcopy(
            checked_parent["private_source_columns"]
        ),
        "private_parent_result": copy.deepcopy(checked_parent),
        "private_parent_result_payload_sha256": checked_parent[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked_parent["cost"]),
        "scored_prediction_is_visible_row_key_detail_candidate": True,
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
    raw_parent = copied.get("private_parent_result")
    selected = copied.get("private_visible_link_selection")
    application = copied.get("private_detail_application")
    batches = copied.get("private_pre_detail_fetch_batches")
    pages = copied.get("private_detail_pages")
    columns = copied.get("private_source_columns")
    receipt = copied.get("visible_row_key_detail_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256_by_arm")
    if not isinstance(raw_parent, Mapping):
        raise ValueError("V2.54.92 private parent is absent")
    checked_parent = parent.validate_result(raw_parent)
    base = str(checked_parent["prediction"])
    if (
        not isinstance(columns, list)
        or any(not isinstance(item, str) for item in columns)
        or not isinstance(batches, list)
        or any(not isinstance(item, Mapping) for item in batches)
        or not isinstance(pages, list)
        or any(
            not isinstance(item, Mapping) or set(item) != candidates.PAGE_KEYS
            for item in pages
        )
        or not isinstance(selected, Mapping)
    ):
        raise ValueError("V2.54.92 private replay inputs drifted")
    checked_selection = selection.validate_selection(
        selected,
        base_prediction=base,
        columns=columns,
        fetch_batches=batches,
    )
    checked_application: dict[str, Any] | None = None
    candidate = base
    if application is not None:
        if not isinstance(application, Mapping):
            raise ValueError("V2.54.92 application drifted")
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
        "visible_row_key_detail_receipt",
        "private_visible_link_selection",
        "private_detail_application",
        "private_pre_detail_fetch_batches",
        "private_detail_pages",
        "private_source_columns",
        "private_parent_result",
        "private_parent_result_payload_sha256",
        "cost",
        "scored_prediction_is_visible_row_key_detail_candidate",
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
        or columns != checked_parent["private_source_columns"]
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt["selection_payload_sha256"]
        != checked_selection["artifact_payload_sha256"]
        or receipt["detail_exact_nonredirected_page_count"] != len(pages)
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
        or copied.get("scored_prediction_is_visible_row_key_detail_candidate")
        is not True
        or copied.get("qualified_source_label_parent_prediction_is_exact_control")
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
        raise ValueError("V2.54.92 runtime result drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any],
    parent_stage: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["visible_row_key_detail_receipt"])
    final = cap.validate_budget_receipt(final_budget)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "visible_row_key_detail_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(final),
        "one_parent_forward_then_capacity_safe_visible_detail_fetch": True,
        "candidate_fetch_accounted_in_same_outer_budget": True,
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
    receipt = copied.get("visible_row_key_detail_receipt")
    stage = copied.get("parent_stage_receipt")
    final = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "one_parent_forward_then_capacity_safe_visible_detail_fetch",
        "candidate_fetch_accounted_in_same_outer_budget",
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
        "visible_row_key_detail_receipt",
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
        or any(final[f"{kind}_rejected_count"] != 0 for kind in ("query", "fetch", "model"))
        or copied.get("parent_runtime_result_payload_sha256")
        != receipt["parent_result_payload_sha256"]
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.92 runtime stage receipt drifted")
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
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], cap.HardCappedSearchClient)
            or searches[phase]._budget is not budget
            or searches[phase]._phase != phase
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.54.92 hard-capped search wiring drifted")
    captured = {phase: _CaptureSearch(searches[phase]) for phase in PHASES}
    parent_result, parent_stage = parent.run_task(
        visible,
        model=model,
        searches=captured,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    checked_parent = parent.validate_result(parent_result)
    base = str(checked_parent["prediction"])
    columns = tuple(str(value) for value in checked_parent["private_source_columns"])
    pre_detail = [
        copy.deepcopy(batch)
        for phase in PHASES
        for batch in captured[phase].fetch_batches
    ]
    selected, application, pages, details = _candidate(
        base,
        columns,
        pre_detail,
        searches=captured,
        budget=budget,
    )
    final_budget = cap.validate_budget_receipt(budget.receipt())
    result = _wrap_result(
        checked_parent,
        selected,
        application,
        pre_detail,
        pages,
        details,
        final_budget,
    )
    return result, _stage_receipt(result, parent_stage, final_budget)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "selection_policy_id": selection.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "arms": list(ARMS),
        "one_v25472_parent_forward_shared_by_base_and_candidate": True,
        "parent_fetch_responses_mirrored_without_request_or_response_mutation": True,
        "maximum_candidate_additional_fetches": 1,
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
