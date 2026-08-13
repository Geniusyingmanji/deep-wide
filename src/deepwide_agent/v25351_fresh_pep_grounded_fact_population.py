"""Fresh visible-identity population for grounded-fact mechanism testing.

The twenty proposal identities were fixed by domain knowledge before opening
any candidate page, endpoint value, model output, evaluator, or quality
signal.  Every identity is directly visible in its question; there is no
hidden clue-to-identity mapping.  A separate aggregate history audit binds the
vector to a parent commit in which none of the identities occurred.

This module is pure population data and grants no network, model, evaluator,
benchmark, retry, or signed-credit authority.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25351_fresh_visible_pep_grounded_fact_population_v1"
FRESHNESS_PARENT_COMMIT = "9a4501d4bd219be184dccbf28457d6255a6ccd2e"
TASK_COUNT = 20
COLUMNS = ("PEP", "Title", "Status", "Type", "Created")
PEP_NUMBERS = (
    621,
    634,
    635,
    636,
    639,
    646,
    647,
    649,
    654,
    655,
    657,
    660,
    668,
    673,
    675,
    681,
    682,
    685,
    688,
    691,
)
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "f08760a5063cd891975b1a99c88ad2de460ce57952a02dc77938e197da052f11"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "ff641d7d3d6f4665a8e4851bbb01ca129aa4df398ae01882bd7ed62c9f4e7c9d"
)
ARMS = ("raw_shared_page_evidence", "grounded_fact_prefix")
CONTROL_ARM, CANDIDATE_ARM = ARMS


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
    values = [f"PEP {number}" for number in PEP_NUMBERS]
    if (
        len(values) != TASK_COUNT
        or len(set(values)) != TASK_COUNT
        or any(re.fullmatch(r"PEP [1-9][0-9]{2}", value) is None for value in values)
        or payload_sha256(values) != EXPECTED_IDENTITY_VECTOR_SHA256
    ):
        raise RuntimeError("V2.53.51 PEP identity vector drifted")
    return values


def task_vector() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for identity in identity_vector():
        opaque = "task_" + hashlib.sha256(
            f"v25351:{identity}".encode()
        ).hexdigest()[:24]
        question = (
            "Use public web sources and the official Python Enhancement Proposals "
            "collection to return exactly one Markdown table and no prose for the "
            f"visible proposal identity <PEP>{identity}</PEP>. Columns exactly: "
            + " | ".join(COLUMNS)
            + ". Preserve official spelling and metadata wording. The PEP cell must "
            f"be {identity}. Title, Status, Type, and Created must all belong to the "
            "same official proposal metadata record. Render Created as shown by the "
            "official source; use Unknown only when same-forward fetched public pages "
            "do not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    output = validate_task_vector(rows)
    if payload_sha256(output) != EXPECTED_TASK_VECTOR_SHA256:
        raise RuntimeError("V2.53.51 task vector hash drifted")
    return output


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    identities = identity_vector()
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.53.51 task denominator drifted")
    output: list[dict[str, str]] = []
    for raw, identity in zip(values, identities, strict=True):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.53.51 visible task boundary drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or not isinstance(question, str)
            or f"<PEP>{identity}</PEP>" not in question
            or "Columns exactly: " + " | ".join(COLUMNS) not in question
            or any(
                f"<PEP>{other}</PEP>" in question
                for other in identities
                if other != identity
            )
            or "https://" in question
        ):
            raise ValueError("V2.53.51 task identity binding drifted")
        output.append({"opaque_id": opaque, "question": question})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.53.51 opaque identity collision")
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25351-arm-order:{tasks[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM]
        if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "proposal_identity_directly_visible_in_question": True,
        "hidden_clue_identity_mapping_absent": True,
        "population_fixed_before_candidate_page_endpoint_model_or_evaluator_access": True,
        "freshness_bound_to_parent_tree_and_ancestor_history_zero_match": True,
        "official_pep_metadata_surface_not_used_to_select_or_replace_tasks": True,
        "one_visible_plan_one_joint_grounded_plan_and_two_production_calls": True,
        "both_arms_share_queries_search_responses_fetched_pages_and_page_bytes": True,
        "candidate_only_treatment_is_equal_length_quote_verified_fact_prefix": True,
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
        "minimum_grounded_plan_provider_success_tasks": 18,
        "minimum_both_arms_model_success_tasks": 18,
        "minimum_candidate_prompt_changed_tasks": 6,
        "minimum_verified_record_tasks": 6,
        "minimum_verified_field_count_total": 12,
        "minimum_attributable_prediction_changed_tasks": 3,
        "maximum_unattributable_prediction_changed_tasks": 0,
        "maximum_outer_accounting_or_budget_rejection_tasks": 0,
        "maximum_transport_search_fetch_or_model_hard_failures": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "exact_physical_model_forwards_per_completed_task": 4,
        "equal_control_candidate_prompt_characters_per_completed_task": True,
        "balanced_frozen_arm_order_exact": True,
        "all_content_free_receipts_valid": True,
        "positive_signed_credit_count": 0,
    }


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "COLUMNS",
    "CONTROL_ARM",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "FRESHNESS_PARENT_COMMIT",
    "PEP_NUMBERS",
    "POLICY_ID",
    "TASK_COUNT",
    "arm_order_vector",
    "identity_vector",
    "mechanism_gate",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
