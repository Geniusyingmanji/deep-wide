"""Third fresh visible-identity population for partial-field mechanism testing.

The consecutive PEP 750--769 vector was fixed as one indivisible group before
opening any candidate page, endpoint value, model output, evaluator, or
quality signal.  An aggregate repository-only scan against parent commit
``c2af2c5e`` found zero canonical identity or slug matches in its tree and
ancestor history.  No identity was individually retained, replaced, or
selected using an endpoint or outcome.

Every identity is directly visible in its question.  This pure data module
grants no network, model, search, fetch, evaluator, benchmark, retry,
replacement, or signed-credit authority.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25364_third_fresh_visible_pep_partial_field_population_v1"
FRESHNESS_PARENT_COMMIT = "c2af2c5e518ee9a7480a0f91a7f6c165c390e8c8"
TASK_COUNT = 20
COLUMNS = ("PEP", "Title", "Status", "Type", "Created")
PEP_NUMBERS = tuple(range(750, 770))
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "71c820701bfd26a1a366fd7c201f2b1e418db1b0469798a51e2778cf047c2ecf"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "c1bdf59df347d6525740762e679d287f78c1eb3df6f53f7d6ffded63fe7b5213"
)
EXPECTED_ARM_ORDER_VECTOR_SHA256 = (
    "2d49ca3dda188ba8df5eb9f60fb7224e360ca35be99b6a696f3e972b0f4cfb4d"
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
        PEP_NUMBERS != tuple(range(750, 770))
        or len(values) != TASK_COUNT
        or len(set(values)) != TASK_COUNT
        or any(re.fullmatch(r"PEP [1-9][0-9]{2}", value) is None for value in values)
        or payload_sha256(values) != EXPECTED_IDENTITY_VECTOR_SHA256
    ):
        raise RuntimeError("V2.53.64 PEP identity vector drifted")
    return values


def task_vector() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for identity in identity_vector():
        opaque = "task_" + hashlib.sha256(
            f"v25364:{identity}".encode()
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
        raise RuntimeError("V2.53.64 task vector hash drifted")
    return output


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    identities = identity_vector()
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.53.64 task denominator drifted")
    output: list[dict[str, str]] = []
    for raw, identity in zip(values, identities, strict=True):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.53.64 visible task boundary drifted")
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
            raise ValueError("V2.53.64 task identity binding drifted")
        output.append({"opaque_id": opaque, "question": question})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.53.64 opaque identity collision")
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25364-arm-order:{tasks[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    output = [
        [CANDIDATE_ARM, CONTROL_ARM]
        if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]
    if payload_sha256(output) != EXPECTED_ARM_ORDER_VECTOR_SHA256:
        raise RuntimeError("V2.53.64 arm-order vector drifted")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "proposal_identity_directly_visible_in_question": True,
        "hidden_clue_identity_mapping_absent": True,
        "population_is_one_consecutive_indivisible_vector": True,
        "population_fixed_before_candidate_page_endpoint_model_or_evaluator_access": True,
        "freshness_bound_to_parent_tree_and_ancestor_history_zero_match": True,
        "official_pep_metadata_surface_not_used_to_select_or_replace_tasks": True,
        "pre_effect_query_projection_required_before_first_search_or_fetch": True,
        "one_visible_plan_one_joint_grounded_plan_and_two_production_calls": True,
        "both_arms_share_queries_search_responses_fetched_pages_and_page_bytes": True,
        "candidate_only_treatment_is_equal_length_partial_field_quote_verified_prefix": True,
        "query_fetch_model_context_token_wall_and_network_caps_not_expanded": True,
        "fixed_twenty_failure_as_zero_denominator_no_retry_resume_or_replacement": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    """Keep the V2.53.58 mechanism thresholds fixed before the new forward."""

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
        "maximum_outer_failure_tasks": 2,
        "maximum_budget_rejection_tasks": 0,
        "maximum_unrecoverable_hard_failure_tasks": 2,
        "recoverable_search_request_failures_reported_but_not_signed_credit": True,
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
    "EXPECTED_ARM_ORDER_VECTOR_SHA256",
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
