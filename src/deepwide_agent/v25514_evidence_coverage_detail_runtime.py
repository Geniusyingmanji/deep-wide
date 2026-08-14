"""One-parent evidence-coverage detail runtime with a matched control.

This runtime is the V2.55.07 matched-treatment design with one change: the
optional detail action is scheduled by V2.55.13 row-local evidence-coverage
deficit instead of literal ``Unknown`` output cells.  The V2.54.72 parent runs
exactly once.  V2.54.99 over parent pages creates the control.  V2.55.13 uses
only the control table, the same parent pages, and same-forward visible links
to select at most one already-admissible detail URL.  V2.54.99 over control +
parent pages + the exact nonredirected detail page creates the candidate.

Candidate failure preserves control byte-for-byte; control failure suppresses
the optional fetch.  The runtime remains inside four queries, fourteen
fetches, and three model calls.  It reads no label, truth, evaluator, score,
reward, credential, or historical outcome, assigns zero entropy/IG signed
credit, and authorizes no external forward or evaluator.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25472_qualified_source_label_runtime as parent
from . import v25492_visible_row_key_detail_runtime as detail_parent
from . import v25499_generic_mechanical_field_candidate as candidates
from . import v25513_evidence_coverage_deficit_selection as selection


POLICY_ID = "v25514_evidence_coverage_detail_runtime_v1"
ROLE = "v25514_evidence_coverage_detail_runtime_result"
RECEIPT_ROLE = "v25514_content_free_evidence_coverage_detail_receipt"
STAGE_RECEIPT_ROLE = "v25514_content_free_evidence_coverage_detail_stage_receipt"
ARMS = ("generic_parent_control", "evidence_coverage_detail_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
SECOND_PHASE = PHASES[1]
ProductionOnlyStageError = parent.ProductionOnlyStageError
payload_sha256 = parent.payload_sha256


_CaptureSearch = detail_parent._CaptureSearch


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__ or "Exception"
    return name[:128]


def _application(
    base: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, str, str | None]:
    try:
        built = candidates.build_application(base, columns=columns, pages=pages)
        checked = candidates.validate_application(
            built, base_prediction=base, columns=columns, pages=pages
        )
        return checked, str(checked["candidate_prediction"]), None
    except BaseException as exc:
        return None, base, _safe_failure(exc)


def _application_counts(
    application: Mapping[str, Any] | None,
) -> tuple[int, int, int, int, str | None]:
    if application is None:
        return 0, 0, 0, 0, None
    checked = candidates.validate_application(application)
    registry = candidates.validate_registry_receipt(
        checked["private_candidate_registry"]["content_free_receipt"]
    )
    return (
        int(registry["generic_mechanical_field_surface_count"]),
        int(registry["generic_mechanical_observation_count"]),
        int(registry["available_candidate_count"]),
        int(checked["content_free_receipt"]["applied_coordinate_count"]),
        str(checked["artifact_payload_sha256"]),
    )


def _table_difference_count(
    control: str,
    candidate: str,
    columns: Sequence[str],
) -> int:
    required, control_rows = candidates.source._canonical_table(control, columns)
    other_required, candidate_rows = candidates.source._canonical_table(
        candidate, columns
    )
    if required != other_required or len(control_rows) != len(candidate_rows):
        raise ValueError("V2.55.14 treatment table shape drifted")
    count = 0
    for left, right in zip(control_rows, candidate_rows, strict=True):
        if left[0] != right[0] or len(left) != len(right):
            raise ValueError("V2.55.14 treatment row identity drifted")
        count += sum(a != b for a, b in zip(left[1:], right[1:], strict=True))
    return count


def _post_parent(
    parent_result: Mapping[str, Any],
    pre_detail_fetch_batches: Sequence[Mapping[str, Any]],
    *,
    searches: Mapping[str, _CaptureSearch],
    budget: cap.PhysicalEffectBudget,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any],
    dict[str, Any] | None,
    list[dict[str, str]],
    list[dict[str, str]],
    str,
    str,
    dict[str, Any],
]:
    checked_parent = parent.validate_result(parent_result)
    base = str(checked_parent["prediction"])
    columns = tuple(str(item) for item in checked_parent["private_source_columns"])
    parent_pages = [
        copy.deepcopy(dict(page))
        for page in checked_parent["private_same_forward_pages"]
    ]
    control_application, control, control_failure = _application(
        base, columns=columns, pages=parent_pages
    )
    raw_selection = selection.build_selection(
        control,
        columns=columns,
        fetch_batches=pre_detail_fetch_batches,
        pages=parent_pages,
    )
    checked_selection = selection.validate_selection(
        raw_selection,
        base_prediction=control,
        columns=columns,
        fetch_batches=pre_detail_fetch_batches,
        pages=parent_pages,
    )
    parent_budget = cap.validate_budget_receipt(budget.receipt())
    requests = list(checked_selection["requests"])
    remaining = max(0, cap.FETCH_CAP - parent_budget["fetch_admitted_count"])
    suppressed = len(requests) if control_application is None else 0
    admitted = [] if suppressed else requests[: min(len(requests), remaining)]
    capacity_shortfall = len(requests) - len(admitted) - suppressed
    fetched: object = []
    fetch_failure: str | None = None
    if admitted:
        try:
            fetched = searches[SECOND_PHASE].fetch_urls(admitted)
        except BaseException as exc:
            fetch_failure = _safe_failure(exc)
    detail_pages = detail_parent._exact_pages(
        admitted, fetched, searches[SECOND_PHASE]
    )
    combined_pages = [*parent_pages, *copy.deepcopy(detail_pages)]
    candidate_application: dict[str, Any] | None = None
    candidate = control
    candidate_failure: str | None = None
    if control_application is not None:
        candidate_application, candidate, candidate_failure = _application(
            control, columns=columns, pages=combined_pages
        )
    details = {
        "parent_budget": parent_budget,
        "control_application_failure_type": control_failure,
        "logical_request_count": len(requests),
        "control_failure_suppressed_request_count": suppressed,
        "admitted_request_count": len(admitted),
        "capacity_shortfall_count": capacity_shortfall,
        "exact_nonredirected_page_count": len(detail_pages),
        "candidate_fetch_failure_type": fetch_failure,
        "candidate_application_failure_type": candidate_failure,
    }
    return (
        control_application,
        checked_selection,
        candidate_application,
        detail_pages,
        combined_pages,
        control,
        candidate,
        details,
    )


def _receipt(
    *,
    parent_result: Mapping[str, Any],
    control_application: Mapping[str, Any] | None,
    selected: Mapping[str, Any],
    candidate_application: Mapping[str, Any] | None,
    detail_pages: Sequence[Mapping[str, Any]],
    combined_pages: Sequence[Mapping[str, Any]],
    control: str,
    candidate: str,
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
    control_surface, control_observation, control_available, control_applied, control_hash = (
        _application_counts(control_application)
    )
    candidate_surface, candidate_observation, candidate_available, candidate_applied, candidate_hash = (
        _application_counts(candidate_application)
    )
    changed_coordinates = _table_difference_count(
        control, candidate, checked_parent["private_source_columns"]
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
        "coverage_probe_unique_coordinate_count": selector_receipt[
            "coverage_probe_unique_coordinate_count"
        ],
        "coverage_probe_covered_row_count": selector_receipt[
            "coverage_probe_covered_row_count"
        ],
        "evidence_deficit_candidate_row_count": selector_receipt[
            "candidate_row_count"
        ],
        "candidate_covered_nonkey_cell_count_total": selector_receipt[
            "candidate_covered_nonkey_cell_count_total"
        ],
        "candidate_evidence_deficit_count_total": selector_receipt[
            "candidate_evidence_deficit_count_total"
        ],
        "positive_evidence_deficit_candidate_count": selector_receipt[
            "positive_evidence_deficit_candidate_count"
        ],
        "maximum_evidence_deficit_count": selector_receipt[
            "maximum_evidence_deficit_count"
        ],
        "maximum_evidence_deficit_tie_count": selector_receipt[
            "maximum_evidence_deficit_tie_count"
        ],
        "detail_logical_request_count": int(details["logical_request_count"]),
        "control_failure_suppressed_request_count": int(
            details["control_failure_suppressed_request_count"]
        ),
        "detail_admitted_fetch_count": int(details["admitted_request_count"]),
        "detail_capacity_shortfall_count": int(details["capacity_shortfall_count"]),
        "detail_exact_nonredirected_page_count": len(detail_pages),
        "parent_candidate_page_count": len(
            checked_parent["private_same_forward_pages"]
        ),
        "combined_candidate_page_count": len(combined_pages),
        "control_generic_field_surface_count": control_surface,
        "control_generic_observation_count": control_observation,
        "control_available_candidate_count": control_available,
        "control_applied_coordinate_count": control_applied,
        "combined_generic_field_surface_count": candidate_surface,
        "combined_generic_observation_count": candidate_observation,
        "combined_available_candidate_count": candidate_available,
        "combined_applied_coordinate_count": candidate_applied,
        "treatment_changed_coordinate_count": changed_coordinates,
        "final_query_count": final["query_admitted_count"],
        "final_fetch_count": final["fetch_admitted_count"],
        "final_model_count": final["model_admitted_count"],
        "positive_signed_credit_count": 0,
        "control_application_valid": control_application is not None,
        "candidate_application_valid": candidate_application is not None,
        "candidate_prediction_changed": control != candidate,
        "candidate_identity_handoff": control == candidate,
        "control_application_failure_type": details[
            "control_application_failure_type"
        ],
        "candidate_fetch_failure_type": details[
            "candidate_fetch_failure_type"
        ],
        "candidate_application_failure_type": details[
            "candidate_application_failure_type"
        ],
        "parent_result_payload_sha256": checked_parent["result_payload_sha256"],
        "control_application_payload_sha256": control_hash,
        "selection_payload_sha256": checked_selection["artifact_payload_sha256"],
        "candidate_application_payload_sha256": candidate_hash,
        "one_v25472_parent_forward_shared_by_control_and_candidate": True,
        "control_is_generic_application_over_parent_pages_only": True,
        "selection_reads_only_control_schema_parent_page_coverage_and_same_forward_visible_links": True,
        "candidate_is_generic_application_over_control_and_parent_plus_detail_pages": True,
        "candidate_url_path_and_anchor_bind_one_completed_control_row_key": True,
        "only_exact_nonredirected_detail_page_admitted": True,
        "different_rows_are_scheduling_alternatives_not_merged_evidence": True,
        "control_or_candidate_failure_preserves_preceding_prediction_byte_exact": True,
        "candidate_fetch_never_exceeds_remaining_outer_capacity": True,
        "outer_query4_fetch14_model3_caps_preserved": True,
        "candidate_additional_query_count_zero": True,
        "candidate_additional_model_count_zero": True,
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


_COUNT_FIELDS = (
    "parent_query_count",
    "parent_fetch_count",
    "parent_model_count",
    "raw_fetched_page_count",
    "raw_page_visible_link_count",
    "joint_bound_link_count",
    "eligible_unique_link_count",
    "coverage_probe_unique_coordinate_count",
    "coverage_probe_covered_row_count",
    "evidence_deficit_candidate_row_count",
    "candidate_covered_nonkey_cell_count_total",
    "candidate_evidence_deficit_count_total",
    "positive_evidence_deficit_candidate_count",
    "maximum_evidence_deficit_count",
    "maximum_evidence_deficit_tie_count",
    "detail_logical_request_count",
    "control_failure_suppressed_request_count",
    "detail_admitted_fetch_count",
    "detail_capacity_shortfall_count",
    "detail_exact_nonredirected_page_count",
    "parent_candidate_page_count",
    "combined_candidate_page_count",
    "control_generic_field_surface_count",
    "control_generic_observation_count",
    "control_available_candidate_count",
    "control_applied_coordinate_count",
    "combined_generic_field_surface_count",
    "combined_generic_observation_count",
    "combined_available_candidate_count",
    "combined_applied_coordinate_count",
    "treatment_changed_coordinate_count",
    "final_query_count",
    "final_fetch_count",
    "final_model_count",
    "positive_signed_credit_count",
)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    dynamic_flags = (
        "control_application_valid",
        "candidate_application_valid",
        "candidate_prediction_changed",
        "candidate_identity_handoff",
    )
    true_flags = (
        "one_v25472_parent_forward_shared_by_control_and_candidate",
        "control_is_generic_application_over_parent_pages_only",
        "selection_reads_only_control_schema_parent_page_coverage_and_same_forward_visible_links",
        "candidate_is_generic_application_over_control_and_parent_plus_detail_pages",
        "candidate_url_path_and_anchor_bind_one_completed_control_row_key",
        "only_exact_nonredirected_detail_page_admitted",
        "different_rows_are_scheduling_alternatives_not_merged_evidence",
        "control_or_candidate_failure_preserves_preceding_prediction_byte_exact",
        "candidate_fetch_never_exceeds_remaining_outer_capacity",
        "outer_query4_fetch14_model3_caps_preserved",
        "candidate_additional_query_count_zero",
        "candidate_additional_model_count_zero",
    )
    false_flags = (
        "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    hashes = (
        "parent_result_payload_sha256",
        "control_application_payload_sha256",
        "selection_payload_sha256",
        "candidate_application_payload_sha256",
    )
    failures = (
        "control_application_failure_type",
        "candidate_fetch_failure_type",
        "candidate_application_failure_type",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *dynamic_flags,
        *failures,
        *hashes,
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
        or any(not isinstance(copied.get(name), bool) for name in dynamic_flags)
        or copied["parent_query_count"] != copied["final_query_count"]
        or copied["parent_model_count"] != copied["final_model_count"]
        or copied["final_fetch_count"]
        != copied["parent_fetch_count"] + copied["detail_admitted_fetch_count"]
        or copied["detail_logical_request_count"]
        != copied["detail_admitted_fetch_count"]
        + copied["detail_capacity_shortfall_count"]
        + copied["control_failure_suppressed_request_count"]
        or copied["detail_logical_request_count"] not in {0, 1}
        or copied["detail_admitted_fetch_count"] > 1
        or copied["detail_exact_nonredirected_page_count"]
        > copied["detail_admitted_fetch_count"]
        or copied["combined_candidate_page_count"]
        != copied["parent_candidate_page_count"]
        + copied["detail_exact_nonredirected_page_count"]
        or copied["control_applied_coordinate_count"]
        != copied["control_available_candidate_count"]
        or copied["combined_applied_coordinate_count"]
        != copied["combined_available_candidate_count"]
        or copied["control_generic_observation_count"]
        > copied["control_generic_field_surface_count"]
        or copied["combined_generic_observation_count"]
        > copied["combined_generic_field_surface_count"]
        or copied["positive_evidence_deficit_candidate_count"]
        > copied["evidence_deficit_candidate_row_count"]
        or copied["final_query_count"] > cap.QUERY_CAP
        or copied["final_fetch_count"] > cap.FETCH_CAP
        or copied["final_model_count"] > 3
        or copied["positive_signed_credit_count"] != 0
        or copied["candidate_prediction_changed"]
        is not (copied["treatment_changed_coordinate_count"] > 0)
        or copied["candidate_identity_handoff"]
        is copied["candidate_prediction_changed"]
        or copied["control_application_valid"]
        is not (copied["control_application_payload_sha256"] is not None)
        or copied["candidate_application_valid"]
        is not (copied["candidate_application_payload_sha256"] is not None)
        or copied["candidate_application_valid"]
        and not copied["control_application_valid"]
        or copied["control_failure_suppressed_request_count"]
        and copied["control_application_valid"]
        or copied["control_application_valid"]
        and copied["control_application_failure_type"] is not None
        or copied["candidate_application_valid"]
        and copied["candidate_application_failure_type"] is not None
        or any(
            item is not None
            and (not isinstance(item, str) or not item or len(item) > 128)
            for item in (copied.get(name) for name in failures)
        )
        or any(
            copied.get(name) is not None
            and (not isinstance(copied[name], str) or len(copied[name]) != 64)
            for name in hashes
        )
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or not isinstance(copied.get("selection_payload_sha256"), str)
        or len(copied["selection_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.14 runtime receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    control_application: Mapping[str, Any] | None,
    selected: Mapping[str, Any],
    candidate_application: Mapping[str, Any] | None,
    pre_detail_fetch_batches: Sequence[Mapping[str, Any]],
    detail_pages: Sequence[Mapping[str, str]],
    combined_pages: Sequence[Mapping[str, str]],
    control: str,
    candidate: str,
    details: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    checked_selection = selection.validate_selection(selected)
    checked_control = (
        candidates.validate_application(control_application)
        if control_application is not None
        else None
    )
    checked_candidate = (
        candidates.validate_application(candidate_application)
        if candidate_application is not None
        else None
    )
    receipt = _receipt(
        parent_result=checked_parent,
        control_application=checked_control,
        selected=checked_selection,
        candidate_application=checked_candidate,
        detail_pages=detail_pages,
        combined_pages=combined_pages,
        control=control,
        candidate=candidate,
        details=details,
        final_budget=final_budget,
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
        "evidence_coverage_detail_receipt": copy.deepcopy(receipt),
        "private_control_application": copy.deepcopy(checked_control),
        "private_evidence_coverage_selection": copy.deepcopy(checked_selection),
        "private_candidate_application": copy.deepcopy(checked_candidate),
        "private_pre_detail_fetch_batches": copy.deepcopy(
            list(pre_detail_fetch_batches)
        ),
        "private_detail_pages": copy.deepcopy(list(detail_pages)),
        "private_combined_candidate_pages": copy.deepcopy(list(combined_pages)),
        "private_source_columns": copy.deepcopy(
            checked_parent["private_source_columns"]
        ),
        "private_parent_result": copy.deepcopy(checked_parent),
        "private_parent_result_payload_sha256": checked_parent[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked_parent["cost"]),
        "scored_prediction_is_evidence_coverage_detail_candidate": True,
        "generic_parent_application_is_exact_control": True,
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
    control_application = copied.get("private_control_application")
    selected = copied.get("private_evidence_coverage_selection")
    candidate_application = copied.get("private_candidate_application")
    batches = copied.get("private_pre_detail_fetch_batches")
    detail_pages = copied.get("private_detail_pages")
    combined_pages = copied.get("private_combined_candidate_pages")
    columns = copied.get("private_source_columns")
    receipt = copied.get("evidence_coverage_detail_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256_by_arm")
    if not isinstance(raw_parent, Mapping):
        raise ValueError("V2.55.14 private parent absent")
    checked_parent = parent.validate_result(raw_parent)
    base = str(checked_parent["prediction"])
    parent_pages = checked_parent["private_same_forward_pages"]
    if (
        not isinstance(columns, list)
        or columns != checked_parent["private_source_columns"]
        or not isinstance(batches, list)
        or any(not isinstance(item, Mapping) for item in batches)
        or not isinstance(detail_pages, list)
        or any(
            not isinstance(item, Mapping) or set(item) != candidates.PAGE_KEYS
            for item in detail_pages
        )
        or not isinstance(combined_pages, list)
        or combined_pages != [*parent_pages, *detail_pages]
        or not isinstance(selected, Mapping)
    ):
        raise ValueError("V2.55.14 private replay surface drifted")
    checked_control: dict[str, Any] | None = None
    control = base
    if control_application is not None:
        if not isinstance(control_application, Mapping):
            raise ValueError("V2.55.14 control application drifted")
        checked_control = candidates.validate_application(
            control_application,
            base_prediction=base,
            columns=columns,
            pages=parent_pages,
        )
        control = str(checked_control["candidate_prediction"])
    checked_selection = selection.validate_selection(
        selected,
        base_prediction=control,
        columns=columns,
        fetch_batches=batches,
        pages=parent_pages,
    )
    checked_candidate: dict[str, Any] | None = None
    candidate = control
    if candidate_application is not None:
        if not isinstance(candidate_application, Mapping):
            raise ValueError("V2.55.14 candidate application drifted")
        checked_candidate = candidates.validate_application(
            candidate_application,
            base_prediction=control,
            columns=columns,
            pages=combined_pages,
        )
        candidate = str(checked_candidate["candidate_prediction"])
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
        "evidence_coverage_detail_receipt",
        "private_control_application",
        "private_evidence_coverage_selection",
        "private_candidate_application",
        "private_pre_detail_fetch_batches",
        "private_detail_pages",
        "private_combined_candidate_pages",
        "private_source_columns",
        "private_parent_result",
        "private_parent_result_payload_sha256",
        "cost",
        "scored_prediction_is_evidence_coverage_detail_candidate",
        "generic_parent_application_is_exact_control",
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
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt["control_application_payload_sha256"]
        != (
            checked_control["artifact_payload_sha256"]
            if checked_control is not None
            else None
        )
        or receipt["selection_payload_sha256"]
        != checked_selection["artifact_payload_sha256"]
        or receipt["candidate_application_payload_sha256"]
        != (
            checked_candidate["artifact_payload_sha256"]
            if checked_candidate is not None
            else None
        )
        or receipt["detail_exact_nonredirected_page_count"] != len(detail_pages)
        or receipt["combined_candidate_page_count"] != len(combined_pages)
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
        != _table_difference_count(control, candidate, columns)
        or copied.get("scored_prediction_is_evidence_coverage_detail_candidate")
        is not True
        or copied.get("generic_parent_application_is_exact_control") is not True
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
        raise ValueError("V2.55.14 runtime result drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any],
    parent_stage: Mapping[str, Any],
    final_budget: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["evidence_coverage_detail_receipt"])
    final = cap.validate_budget_receipt(final_budget)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "evidence_coverage_detail_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(final),
        "one_parent_forward_then_pure_control_and_bounded_detail_treatment": True,
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
    receipt = copied.get("evidence_coverage_detail_receipt")
    stage = copied.get("parent_stage_receipt")
    final = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "one_parent_forward_then_pure_control_and_bounded_detail_treatment",
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
        "evidence_coverage_detail_receipt",
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
        raise ValueError("V2.55.14 runtime stage receipt drifted")
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
        raise ValueError("V2.55.14 hard-capped search wiring drifted")
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
    pre_detail = [
        copy.deepcopy(batch)
        for phase in PHASES
        for batch in captured[phase].fetch_batches
    ]
    (
        control_application,
        selected,
        candidate_application,
        detail_pages,
        combined_pages,
        control,
        candidate,
        details,
    ) = _post_parent(
        checked_parent,
        pre_detail,
        searches=captured,
        budget=budget,
    )
    final_budget = cap.validate_budget_receipt(budget.receipt())
    result = _wrap_result(
        checked_parent,
        control_application,
        selected,
        candidate_application,
        pre_detail,
        detail_pages,
        combined_pages,
        control,
        candidate,
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
        "one_v25472_parent_forward_shared_by_control_and_candidate": True,
        "control_pages": "same_forward_parent_pages",
        "candidate_pages": "same_forward_parent_pages_plus_one_exact_detail",
        "scheduling_signal": "row_local_missing_unique_source_bound_coordinate_count",
        "maximum_candidate_additional_fetches": 1,
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "maximum_total_fetches": cap.FETCH_CAP,
        "maximum_total_queries": cap.QUERY_CAP,
        "maximum_normal_path_model_calls": 3,
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
    "candidates",
    "integration_contract",
    "parent",
    "payload_sha256",
    "run_task",
    "selection",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
