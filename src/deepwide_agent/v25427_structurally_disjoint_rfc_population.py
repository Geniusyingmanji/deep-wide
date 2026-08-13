"""Structurally disjoint RFC population for the V2.54.26 combined runtime.

V2.54.25 showed that literal identity scans miss populations encoded through
``tuple(range(...))``.  The selection rule here is instead structural: replay
the candidate order frozen by V2.54.14, derive every consumed RFC interval
from a tracked population source only when its paired external forward result
is also frozen, and take the first complete 80-identity block with zero range
intersection.  RFC 9320--9399 is consumed, so RFC 9240--9319 is selected.

The ordered block is indivisible.  No identity or task is removed, replaced,
or ranked.  Before this artifact was frozen, aggregate identity presence for
the block was observed as 80/80 in an already-frozen RFC index snapshot; that
observation is disclosed but is not an input to the deterministic selection
rule.  No field value, page quality, prediction, evaluator, or per-task outcome
is used.  This pure data module grants no model/network/evaluator authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25427_structurally_disjoint_rfc_population_v1"
SELECTION_PARENT_COMMIT = "e00bc631549a7f16b6f6a1c2cee65a1313813d9f"
PRIORITY_AUDIT_SHA256 = (
    "26bfb47371252fa2fa7dbb37b5bc568ea98c85ff2a62ae984882fae8c5eb3651"
)
OVERLAP_ERRATUM_SHA256 = (
    "7915a3502423fb8ae78174c5818f1db7f4d256d05df34fd7fb4b1e07c770fa5d"
)
TASK_COUNT = 20
ROWS_PER_TASK = 4
RFC_NUMBERS = tuple(range(9240, 9320))
COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
CANDIDATE_INTERVAL_ORDER = (
    (9320, 9399),
    (9240, 9319),
    (9160, 9239),
)
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "bba413a5fd450a0a81b17fc1f565fa5e5463782a5389efeacbef1d550deb2e8b"
)
EXPECTED_GROUP_VECTOR_SHA256 = (
    "02d5a67124dfb405e16e46bab47170240517a157f2ed3491c8db963f20c31e2c"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "8d66814ad9fb10d6cb0aa2507cb94aedd6f5f04cf63734947c3eb56bb48e8f7e"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def identity_vector() -> list[str]:
    values = [f"RFC {number}" for number in RFC_NUMBERS]
    observed = payload_sha256(values)
    if (
        RFC_NUMBERS != tuple(range(9240, 9320))
        or len(values) != TASK_COUNT * ROWS_PER_TASK
        or len(set(values)) != len(values)
        or any(re.fullmatch(r"RFC 9[0-9]{3}", value) is None for value in values)
        or (
            EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
            and observed != EXPECTED_IDENTITY_VECTOR_SHA256
        )
    ):
        raise RuntimeError("V2.54.27 RFC identity vector drifted")
    return values


def _group(task_index: int) -> tuple[str, ...]:
    identities = identity_vector()
    start = task_index * ROWS_PER_TASK
    return tuple(identities[start : start + ROWS_PER_TASK])


def _question(group: Sequence[str]) -> str:
    visible = "; ".join(group)
    return (
        "Use public web sources and the official RFC Editor index/detail "
        "pages to return exactly one Markdown table and no prose for the "
        f"four visible document identities <RFCS>{visible}</RFCS>. "
        "Columns exactly: "
        + " | ".join(COLUMNS)
        + ". Return exactly four rows in the same RFC order shown above. "
        "The RFC cell must use the visible `RFC NNNN` form. Title, Authors, "
        "Status, Stream, and Published must all belong to that same RFC "
        "Editor metadata record. Preserve official spelling, list separators, "
        "and ordering; render Published as shown by the official source. Use "
        "Unknown only when same-forward fetched public pages do not establish "
        "a value."
    )


def group_vector() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for task_index in range(TASK_COUNT):
        group = _group(task_index)
        question = _question(group)
        opaque = "task_" + hashlib.sha256(
            f"v25427:{task_index}:{question}".encode()
        ).hexdigest()[:24]
        values.append(
            {
                "task_index": task_index,
                "identity_count": len(group),
                "task": {"opaque_id": opaque, "question": question},
            }
        )
    checked = validate_group_vector(values)
    observed = payload_sha256(checked)
    if (
        EXPECTED_GROUP_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_GROUP_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.27 group vector drifted")
    return checked


def task_vector() -> list[dict[str, str]]:
    values = [dict(group["task"]) for group in group_vector()]
    observed = payload_sha256(values)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.27 task vector drifted")
    return values


def validate_group_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.54.27 task denominator drifted")
    output: list[dict[str, Any]] = []
    opaque_ids: list[str] = []
    identities = identity_vector()
    for task_index, raw in enumerate(values):
        if (
            not isinstance(raw, Mapping)
            or set(raw) != {"task_index", "identity_count", "task"}
            or raw.get("task_index") != task_index
            or raw.get("identity_count") != ROWS_PER_TASK
            or not isinstance(raw.get("task"), Mapping)
        ):
            raise ValueError("V2.54.27 group shape drifted")
        task = raw["task"]
        group = _group(task_index)
        expected_question = _question(group)
        if (
            set(task) != {"opaque_id", "question"}
            or not isinstance(task.get("opaque_id"), str)
            or re.fullmatch(r"task_[0-9a-f]{24}", task["opaque_id"]) is None
            or task.get("question") != expected_question
            or any(
                identity in expected_question
                for identity in identities
                if identity not in group
            )
            or "https://" in expected_question
        ):
            raise ValueError("V2.54.27 task binding drifted")
        opaque_ids.append(task["opaque_id"])
        output.append(
            {
                "task_index": task_index,
                "identity_count": ROWS_PER_TASK,
                "task": dict(task),
            }
        )
    if len(set(opaque_ids)) != TASK_COUNT:
        raise ValueError("V2.54.27 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "four_rfc_identities_directly_visible_per_question": True,
        "population_is_one_consecutive_indivisible_eighty_identity_vector": True,
        "candidate_order_precedes_current_endpoint_model_or_quality_observation": True,
        "consumed_intervals_require_structural_range_and_frozen_forward_evidence": True,
        "selected_first_candidate_with_zero_consumed_range_intersection": True,
        "individual_identity_or_task_retention_replacement_or_ranking": False,
        "aggregate_candidate_identity_presence_previously_observed": True,
        "aggregate_candidate_identity_presence_count": 80,
        "aggregate_presence_used_for_selection_replacement_or_ranking": False,
        "candidate_field_value_page_quality_prediction_or_evaluator_used_for_selection": False,
        "membership_comes_only_from_visible_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "network_model_search_fetch_evaluator_or_benchmark_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_tasks": TASK_COUNT,
        "required_completed_runtime_tasks": TASK_COUNT,
        "maximum_failure_as_zero_tasks": 0,
        "maximum_outer_failure_tasks": 0,
        "maximum_budget_rejection_tasks": 0,
        "required_membership_constraint_applied_tasks": TASK_COUNT,
        "required_base_visible_membership_exact_tasks": TASK_COUNT,
        "required_grounded_record_membership_constraint_applied_tasks": TASK_COUNT,
        "maximum_grounded_raw_membership_violation_count_total": 0,
        "minimum_selected_raw_record_tasks": 8,
        "minimum_verified_record_tasks": 4,
        "minimum_raw_candidate_changed_tasks": 4,
        "maximum_missing_row_rejected_field_count_total": 2,
        "maximum_editor_validation_failure_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "exact_normal_path_model_forwards_per_completed_task": 3,
        "one_parent_forward_per_task": True,
        "zero_additional_list_guard_provider_effects": True,
        "base_raw_and_guarded_predictions_frozen_per_task": True,
        "all_content_free_receipts_valid": True,
        "positive_signed_credit_count": 0,
        "postfreeze_shared_effect_quality_required": True,
    }


__all__ = [
    "CANDIDATE_INTERVAL_ORDER",
    "COLUMNS",
    "EXPECTED_GROUP_VECTOR_SHA256",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "OVERLAP_ERRATUM_SHA256",
    "POLICY_ID",
    "PRIORITY_AUDIT_SHA256",
    "RFC_NUMBERS",
    "ROWS_PER_TASK",
    "SELECTION_PARENT_COMMIT",
    "TASK_COUNT",
    "group_vector",
    "identity_vector",
    "mechanism_gate",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_group_vector",
]
