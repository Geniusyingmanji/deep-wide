"""Visible-only 30k profile for the V2.48.42 atomic table projector.

The only selection-policy change from the audited V2.48.42 profile is the
total rendered-character cap: 16,000 -> 30,000.  The per-page cap remains
5,000 and all relevance, structure, ordering, and atomic table-header closure
logic is inherited unchanged.  A content-free receipt exposes whether the
closure mechanism actually triggered without exposing question, URL, page,
projection, or content hashes.

This pure component has no file, environment, process, network, model,
benchmark-label, gold, evaluator, score, reward, or historical-result access.
Entropy and information gain remain shadow-only and assign zero credit.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24842_atomic_table_header_closure as parent


PROFILE_ID = "v24846_visible_atomic_table_header_closure_30k_v1"
ROLE = "v24846_atomic_table_header_30k_projection"
RECEIPT_ROLE = "v24846_content_free_projection_receipt"
TOTAL_CHARACTER_CAP = 30_000
MAXIMUM_PAGE_CHARS = parent.DEFAULT_MAXIMUM_PAGE_CHARS
BLOCK_CHARACTER_CAP = parent.DEFAULT_BLOCK_CHARACTER_CAP
MAXIMUM_VISIBLE_GROUPS = parent.DEFAULT_MAXIMUM_VISIBLE_GROUPS
MAXIMUM_QUERY_TERMS = parent.DEFAULT_MAXIMUM_QUERY_TERMS
ProjectionPolicy = parent.ProjectionPolicy
payload_sha256 = parent.payload_sha256
visible_requirement_groups = parent.visible_requirement_groups


def profile_policy() -> ProjectionPolicy:
    return ProjectionPolicy(
        total_character_cap=TOTAL_CHARACTER_CAP,
        maximum_page_chars=MAXIMUM_PAGE_CHARS,
        block_character_cap=BLOCK_CHARACTER_CAP,
        maximum_visible_groups=MAXIMUM_VISIBLE_GROUPS,
        maximum_query_terms=MAXIMUM_QUERY_TERMS,
    )


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "profile_id": PROFILE_ID,
        "parent_projector_policy_id": parent.POLICY_ID,
        "policy": copy.deepcopy(dict(value["policy"])),
        "input_page_count": int(value["input_page_count"]),
        "projected_page_count": int(value["projected_page_count"]),
        "input_block_count": int(value["input_block_count"]),
        "projected_block_count": int(value["projected_block_count"]),
        "input_unique_host_count": int(value["input_unique_host_count"]),
        "projected_unique_host_count": int(value["projected_unique_host_count"]),
        "input_content_characters": int(value["input_content_characters"]),
        "allocated_content_characters": int(value["allocated_content_characters"]),
        "projected_rendered_characters": int(value["projected_rendered_characters"]),
        "truncated_content_characters": int(value["truncated_content_characters"]),
        "visible_requirement_group_count": int(value["visible_requirement_group_count"]),
        "supported_visible_requirement_group_count": int(
            value["supported_visible_requirement_group_count"]
        ),
        "retained_supported_visible_requirement_group_count": int(
            value["retained_supported_visible_requirement_group_count"]
        ),
        "missed_supported_visible_requirement_group_count": int(
            value["missed_supported_visible_requirement_group_count"]
        ),
        "selected_table_continuation_block_count": int(
            value["selected_table_continuation_block_count"]
        ),
        "table_header_dependency_addition_count": int(
            value["table_header_dependency_addition_count"]
        ),
        "orphan_selected_table_continuation_block_count": int(
            value["orphan_selected_table_continuation_block_count"]
        ),
        "atomic_table_header_closure_enforced": bool(
            value["atomic_table_header_closure_enforced"]
        ),
        "entropy_or_information_gain_assigns_credit": bool(
            value["entropy_or_information_gain_assigns_credit"]
        ),
        "contains_question_query_url_host_page_projection_content_or_hash": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return validate_receipt(receipt)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    policy = copied.get("policy")
    count_fields = (
        "input_page_count",
        "projected_page_count",
        "input_block_count",
        "projected_block_count",
        "input_unique_host_count",
        "projected_unique_host_count",
        "input_content_characters",
        "allocated_content_characters",
        "projected_rendered_characters",
        "truncated_content_characters",
        "visible_requirement_group_count",
        "supported_visible_requirement_group_count",
        "retained_supported_visible_requirement_group_count",
        "missed_supported_visible_requirement_group_count",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("profile_id") != PROFILE_ID
        or copied.get("parent_projector_policy_id") != parent.POLICY_ID
        or policy
        != {
            "total_character_cap": TOTAL_CHARACTER_CAP,
            "maximum_page_chars": MAXIMUM_PAGE_CHARS,
            "block_character_cap": BLOCK_CHARACTER_CAP,
            "maximum_visible_groups": MAXIMUM_VISIBLE_GROUPS,
            "maximum_query_terms": MAXIMUM_QUERY_TERMS,
        }
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or copied.get("projected_rendered_characters") > TOTAL_CHARACTER_CAP
        or copied.get("orphan_selected_table_continuation_block_count") != 0
        or copied.get("atomic_table_header_closure_enforced") is not True
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "contains_question_query_url_host_page_projection_content_or_hash"
        )
        is not False
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.46 content-free projection receipt drifted")
    return copied


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    projection = parent.build_projection(
        question,
        pages,
        explicit_groups=explicit_groups,
        policy=profile_policy(),
    )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "profile_id": PROFILE_ID,
        "parent_projector_policy_id": parent.POLICY_ID,
        "single_change": {
            "total_character_cap_from_to": [
                parent.DEFAULT_TOTAL_CHARACTER_CAP,
                TOTAL_CHARACTER_CAP,
            ],
            "maximum_page_chars_unchanged": True,
            "block_character_cap_unchanged": True,
            "relevance_structure_order_and_closure_logic_unchanged": True,
        },
        "projection": str(projection["projection"]),
        "content_free_receipt": _receipt(projection),
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_projection(
        value,
        question=question,
        pages=pages,
        explicit_groups=explicit_groups,
        replay=False,
    )


def validate_projection(
    value: Mapping[str, Any],
    *,
    question: str,
    pages: Sequence[Mapping[str, Any]],
    explicit_groups: Sequence[str] | None = None,
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    receipt = copied.get("content_free_receipt")
    projection = copied.get("projection")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("profile_id") != PROFILE_ID
        or copied.get("parent_projector_policy_id") != parent.POLICY_ID
        or copied.get("single_change")
        != {
            "total_character_cap_from_to": [
                parent.DEFAULT_TOTAL_CHARACTER_CAP,
                TOTAL_CHARACTER_CAP,
            ],
            "maximum_page_chars_unchanged": True,
            "block_character_cap_unchanged": True,
            "relevance_structure_order_and_closure_logic_unchanged": True,
        }
        or not isinstance(projection, str)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != receipt
        or receipt.get("projected_rendered_characters") != len(projection)
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.46 30k projection artifact drifted")
    if replay and copied != build_projection(
        question, pages, explicit_groups=explicit_groups
    ):
        raise ValueError("V2.48.46 30k projection is not reproducible")
    return copied


__all__ = [
    "BLOCK_CHARACTER_CAP",
    "MAXIMUM_PAGE_CHARS",
    "MAXIMUM_QUERY_TERMS",
    "MAXIMUM_VISIBLE_GROUPS",
    "PROFILE_ID",
    "ProjectionPolicy",
    "TOTAL_CHARACTER_CAP",
    "build_projection",
    "payload_sha256",
    "profile_policy",
    "validate_projection",
    "validate_receipt",
    "visible_requirement_groups",
]
