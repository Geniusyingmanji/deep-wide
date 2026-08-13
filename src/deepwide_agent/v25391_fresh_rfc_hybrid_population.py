"""Fresh outcome-blind RFC population for the V2.53.89 hybrid runtime.

The complete RFC 9680--9759 interval was fixed as one indivisible vector at
parent commit ``c88621f3`` before opening any RFC page, endpoint value, model
output, evaluator, or quality signal. Twenty tasks each expose four
consecutive identities and request a four-row table. Selection uses only the
public integer identities and an aggregate parent-tree/history collision scan;
no task is individually retained, replaced, or ranked by endpoint or outcome.

This pure data module grants no network, model, search, fetch, evaluator,
benchmark, retry, replacement, or signed-credit authority.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25391_fresh_outcome_blind_rfc_hybrid_population_v1"
FRESHNESS_PARENT_COMMIT = "c88621f3a375aedd62ee1fc1989dccfffd44cb95"
TASK_COUNT = 20
ROWS_PER_TASK = 4
RFC_NUMBERS = tuple(range(9680, 9760))
COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "32c9b74f5ad3729c2c23ff54223d9877356b9597b15404bcbb09379f98361192"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "e1b19e6036718747afc70dda93c9253b3a88fc0e6623c13136ac5f44c4e1eb9f"
)


def payload_sha256(value: object) -> str:
    import json

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
        RFC_NUMBERS != tuple(range(9680, 9760))
        or len(values) != TASK_COUNT * ROWS_PER_TASK
        or len(set(values)) != len(values)
        or any(re.fullmatch(r"RFC 9[0-9]{3}", value) is None for value in values)
        or (
            EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
            and observed != EXPECTED_IDENTITY_VECTOR_SHA256
        )
    ):
        raise RuntimeError("V2.53.91 RFC identity vector drifted")
    return values


def _task_vector_unchecked() -> list[dict[str, str]]:
    identities = identity_vector()
    rows: list[dict[str, str]] = []
    for task_index in range(TASK_COUNT):
        group = identities[
            task_index * ROWS_PER_TASK : (task_index + 1) * ROWS_PER_TASK
        ]
        visible = "; ".join(group)
        opaque = "task_" + hashlib.sha256(
            f"v25391:{visible}".encode()
        ).hexdigest()[:24]
        question = (
            "Use public web sources and the official RFC Editor index/detail "
            "pages to return exactly one Markdown table and no prose for the "
            f"four visible document identities <RFCS>{visible}</RFCS>. "
            "Columns exactly: "
            + " | ".join(COLUMNS)
            + ". Return exactly four rows in the same RFC order shown above. "
            "The RFC cell must use the visible `RFC NNNN` form. Title, Authors, "
            "Status, Stream, and Published must all belong to that same RFC "
            "Editor metadata record. Preserve official spelling and ordering; "
            "render Published as shown by the official source. Use Unknown only "
            "when same-forward fetched public pages do not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return rows


def task_vector() -> list[dict[str, str]]:
    output = validate_task_vector(_task_vector_unchecked())
    observed = payload_sha256(output)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.53.91 task vector hash drifted")
    return output


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    identities = identity_vector()
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.53.91 task denominator drifted")
    output: list[dict[str, str]] = []
    for task_index, raw in enumerate(values):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.53.91 visible task boundary drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        group = identities[
            task_index * ROWS_PER_TASK : (task_index + 1) * ROWS_PER_TASK
        ]
        visible = "; ".join(group)
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or not isinstance(question, str)
            or f"<RFCS>{visible}</RFCS>" not in question
            or "Columns exactly: " + " | ".join(COLUMNS) not in question
            or "Return exactly four rows in the same RFC order" not in question
            or any(
                identity in question
                for identity in identities
                if identity not in group
            )
            or "https://" in question
        ):
            raise ValueError("V2.53.91 task identity binding drifted")
        output.append({"opaque_id": opaque, "question": question})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.53.91 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "four_rfc_identities_directly_visible_per_question": True,
        "hidden_clue_identity_mapping_absent": True,
        "population_is_one_consecutive_indivisible_eighty_identity_vector": True,
        "population_fixed_before_candidate_page_endpoint_model_or_evaluator_access": True,
        "freshness_bound_to_parent_tree_and_ancestor_history_zero_match": True,
        "official_rfc_metadata_surface_not_used_to_select_or_replace_tasks": True,
        "multirow_structure_selected_before_any_outcome": True,
        "pre_effect_query_projection_required_before_first_search_or_fetch": True,
        "one_visible_plan_one_grounded_plan_and_one_joint_table_record_synthesis": True,
        "record_source_priority_is_joint_nonempty_then_grounded_nonempty_then_none": True,
        "record_source_selected_before_quote_or_edit_verification": True,
        "joint_and_grounded_records_are_never_merged_or_unioned": True,
        "candidate_only_effect_is_local_changed_safe_verified_coordinate_edit": True,
        "candidate_has_no_independent_model_or_sampling_effect": True,
        "query_fetch_model_context_token_wall_and_network_caps_not_expanded": True,
        "fixed_twenty_failure_as_zero_denominator_no_retry_resume_or_replacement": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "terminal_tasks": TASK_COUNT,
        "minimum_completed_runtime_tasks": 18,
        "maximum_failure_as_zero_tasks": 2,
        "minimum_first_wave_completed_tasks": 18,
        "minimum_second_wave_completed_tasks": 18,
        "minimum_grounded_plan_provider_success_tasks": 18,
        "minimum_joint_envelope_exact_tasks": 18,
        "minimum_base_synthesis_success_tasks": 18,
        "minimum_exact_canonical_base_table_tasks": 18,
        "minimum_selected_raw_record_tasks": 8,
        "minimum_verified_record_tasks": 4,
        "minimum_changed_safe_coordinate_tasks": 4,
        "minimum_attributable_prediction_changed_tasks": 4,
        "maximum_unattributable_prediction_changed_tasks": 0,
        "maximum_missing_row_rejected_field_count_total": 2,
        "maximum_editor_validation_failure_tasks": 0,
        "maximum_outer_failure_tasks": 2,
        "maximum_budget_rejection_tasks": 0,
        "maximum_unrecoverable_hard_failure_tasks": 2,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "exact_normal_path_model_forwards_per_completed_task": 3,
        "all_content_free_receipts_valid": True,
        "positive_signed_credit_count": 0,
    }


__all__ = [
    "COLUMNS",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "FRESHNESS_PARENT_COMMIT",
    "POLICY_ID",
    "RFC_NUMBERS",
    "ROWS_PER_TASK",
    "TASK_COUNT",
    "identity_vector",
    "mechanism_gate",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
