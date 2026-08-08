"""Prefix-total query-aware packing for the V2.49.14 cap failure.

The V2.49.13 mechanism remains active whenever its structural selection is
within the frozen 5,000-character output cap.  Only the single diagnosed
overflow exception falls back to the exact stable 5k prefix of the same
already-fetched pages.  No additional search, fetch, model call, or credit is
introduced.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24911_long_page_evidence_packer as long_parent
from .v24911_long_page_evidence_packer import PackingPolicy
from . import v24913_observable_long_page_packer as parent


POLICY_ID = "v24916_prefix_total_long_page_packer_v1"
ROLE = "v24916_content_free_prefix_total_packing_receipt"
OVERFLOW_MESSAGE = "V2.49.11 structural selection exceeded per-page cap"
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "input_page_character_cap",
        "output_page_character_cap",
        "input_page_count",
        "original_short_page_count",
        "original_long_page_count",
        "input_effective_content_characters",
        "input_characters_beyond_output_page_cap",
        "output_active_content_characters",
        "projected_rendered_characters",
        "final_query_aware_long_page_count",
        "projection_differs_from_prefix_baseline",
        "long_page_mechanism_engaged",
        "structural_cap_totality_fallback_applied",
        "fallback_trigger_was_exact_diagnosed_overflow",
        "fallback_projection_is_exact_stable_5k_prefix",
        "prefix_safe_fallback_applied",
        "candidate_visible_requirement_gain_count",
        "candidate_requirement_coverage_not_less_than_prefix_baseline",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
        "original_short_page_content_byte_identity_preserved",
        "same_forward_page_bytes_only",
        "additional_search_fetch_model_call_or_wall_cap",
        "entropy_information_gain_shadow_only",
        "entropy_or_information_gain_assigns_credit",
        "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential",
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read",
        "receipt_payload_sha256",
    }
)


def _stable_prefix_pages(
    pages: Sequence[Mapping[str, Any]], policy: PackingPolicy
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    stable = long_parent._stable_pages(pages, policy)
    prefix = [
        {
            "title": str(page["title"]),
            "url": str(page["url"]),
            "content": str(page["effective_content"])[
                : policy.output_page_character_cap
            ],
        }
        for page in stable
    ]
    return prefix, stable


def build_prefix_total_packing(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
    policy: PackingPolicy | None = None,
) -> dict[str, Any]:
    chosen = policy or PackingPolicy()
    chosen.validate()
    if (
        chosen.input_page_character_cap != 12_000
        or chosen.output_page_character_cap != 5_000
    ):
        raise ValueError("V2.49.16 production caps drifted")
    prefix_pages, stable = _stable_prefix_pages(pages, chosen)
    prefix_projection = long_parent._render(
        stable,
        [
            str(page["effective_content"])[
                : chosen.output_page_character_cap
            ]
            for page in stable
        ],
    )
    fallback = False
    try:
        packing = parent.build_observable_packing(
            question,
            pages,
            explicit_groups=explicit_groups,
            policy=chosen,
        )
    except RuntimeError as error:
        if str(error) != OVERFLOW_MESSAGE:
            raise
        fallback = True
        packing = parent.build_observable_packing(
            question,
            prefix_pages,
            explicit_groups=explicit_groups,
            policy=chosen,
        )
    base = parent.validate_receipt(packing["content_free_receipt"])
    original_lengths = [
        int(page["effective_content_characters"]) for page in stable
    ]
    original_long = sum(
        value > chosen.output_page_character_cap for value in original_lengths
    )
    original_short = len(stable) - original_long
    exact_prefix = str(packing["projection"]) == prefix_projection
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "input_page_character_cap": chosen.input_page_character_cap,
        "output_page_character_cap": chosen.output_page_character_cap,
        "input_page_count": len(stable),
        "original_short_page_count": original_short,
        "original_long_page_count": original_long,
        "input_effective_content_characters": sum(original_lengths),
        "input_characters_beyond_output_page_cap": sum(
            max(0, value - chosen.output_page_character_cap)
            for value in original_lengths
        ),
        "output_active_content_characters": int(
            base["output_active_content_characters"]
        ),
        "projected_rendered_characters": int(
            base["projected_rendered_characters"]
        ),
        "final_query_aware_long_page_count": (
            0 if fallback else int(base["long_page_packed_count"])
        ),
        "projection_differs_from_prefix_baseline": (
            False
            if fallback
            else bool(base["projection_differs_from_prefix_baseline"])
        ),
        "long_page_mechanism_engaged": (
            False if fallback else bool(base["long_page_mechanism_engaged"])
        ),
        "structural_cap_totality_fallback_applied": fallback,
        "fallback_trigger_was_exact_diagnosed_overflow": fallback,
        "fallback_projection_is_exact_stable_5k_prefix": fallback and exact_prefix,
        "prefix_safe_fallback_applied": fallback
        or bool(base["prefix_safe_fallback_applied"]),
        "candidate_visible_requirement_gain_count": (
            0
            if fallback
            else int(base["candidate_visible_requirement_gain_count"])
        ),
        "candidate_requirement_coverage_not_less_than_prefix_baseline": True,
        "selected_table_continuation_block_count": (
            0
            if fallback
            else int(base["selected_table_continuation_block_count"])
        ),
        "table_header_dependency_addition_count": (
            0
            if fallback
            else int(base["table_header_dependency_addition_count"])
        ),
        "orphan_selected_table_continuation_block_count": 0,
        "original_short_page_content_byte_identity_preserved": all(
            prefix_pages[index]["content"] == str(page["effective_content"])
            for index, page in enumerate(stable)
            if int(page["effective_content_characters"])
            <= chosen.output_page_character_cap
        ),
        "same_forward_page_bytes_only": True,
        "additional_search_fetch_model_call_or_wall_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
    }
    receipt["receipt_payload_sha256"] = long_parent.payload_sha256(receipt)
    packing["content_free_receipt"] = validate_receipt(receipt)
    return packing


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integers = (
        "input_page_character_cap",
        "output_page_character_cap",
        "input_page_count",
        "original_short_page_count",
        "original_long_page_count",
        "input_effective_content_characters",
        "input_characters_beyond_output_page_cap",
        "output_active_content_characters",
        "projected_rendered_characters",
        "final_query_aware_long_page_count",
        "candidate_visible_requirement_gain_count",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
    )
    fallback = copied.get("structural_cap_totality_fallback_applied")
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integers
        )
        or copied["input_page_character_cap"] != 12_000
        or copied["output_page_character_cap"] != 5_000
        or copied["original_short_page_count"]
        + copied["original_long_page_count"]
        != copied["input_page_count"]
        or copied["final_query_aware_long_page_count"]
        > copied["original_long_page_count"]
        or copied["output_active_content_characters"]
        > 5_000 * copied["input_page_count"]
        or copied["orphan_selected_table_continuation_block_count"] != 0
        or copied["candidate_requirement_coverage_not_less_than_prefix_baseline"]
        is not True
        or copied["original_short_page_content_byte_identity_preserved"] is not True
        or copied["same_forward_page_bytes_only"] is not True
        or copied["additional_search_fetch_model_call_or_wall_cap"] is not False
        or copied["entropy_information_gain_shadow_only"] is not True
        or copied["entropy_or_information_gain_assigns_credit"] is not False
        or copied[
            "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential"
        ]
        is not False
        or copied[
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
        or not isinstance(fallback, bool)
        or copied["fallback_trigger_was_exact_diagnosed_overflow"] is not fallback
        or fallback
        and (
            copied["fallback_projection_is_exact_stable_5k_prefix"] is not True
            or copied["final_query_aware_long_page_count"] != 0
            or copied["projection_differs_from_prefix_baseline"] is not False
            or copied["long_page_mechanism_engaged"] is not False
            or copied["candidate_visible_requirement_gain_count"] != 0
            or copied["selected_table_continuation_block_count"] != 0
            or copied["table_header_dependency_addition_count"] != 0
        )
        or not fallback
        and copied["fallback_projection_is_exact_stable_5k_prefix"] is not False
        or copied["long_page_mechanism_engaged"]
        is not (
            copied["final_query_aware_long_page_count"] > 0
            and copied["projection_differs_from_prefix_baseline"] is True
        )
        or seal != long_parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.16 prefix-total receipt drifted")
    return copied


__all__ = [
    "OVERFLOW_MESSAGE",
    "POLICY_ID",
    "RECEIPT_KEYS",
    "ROLE",
    "build_prefix_total_packing",
    "validate_receipt",
]
