"""Content-free observability wrapper for V2.49.11 evidence packing."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24911_long_page_evidence_packer as parent


POLICY_ID = "v24913_observable_long_page_packer_v1"
ROLE = "v24913_content_free_long_page_packing_receipt"
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "input_page_character_cap",
        "output_page_character_cap",
        "input_page_count",
        "short_page_identity_count",
        "long_page_packed_count",
        "input_effective_content_characters",
        "input_characters_beyond_output_page_cap",
        "output_active_content_characters",
        "projected_rendered_characters",
        "projection_differs_from_prefix_baseline",
        "long_page_mechanism_engaged",
        "prefix_safe_fallback_applied",
        "candidate_visible_requirement_gain_count",
        "candidate_requirement_coverage_not_less_than_prefix_baseline",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
        "short_page_content_byte_identity_preserved",
        "same_forward_page_bytes_only",
        "entropy_information_gain_shadow_only",
        "entropy_or_information_gain_assigns_credit",
        "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential",
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read",
        "receipt_payload_sha256",
    }
)


def build_observable_packing(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
    policy: parent.PackingPolicy | None = None,
) -> dict[str, Any]:
    chosen = policy or parent.PackingPolicy()
    chosen.validate()
    packing = parent.build_packing(
        question,
        pages,
        explicit_groups=explicit_groups,
        policy=chosen,
    )
    stable = parent._stable_pages(pages, chosen)
    prefix_excerpts = [
        str(page["effective_content"])[: chosen.output_page_character_cap]
        for page in stable
    ]
    prefix_projection = parent._render(stable, prefix_excerpts)
    differs = str(packing["projection"]) != prefix_projection
    long_pages = int(packing["long_page_packed_count"])
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "input_page_character_cap": chosen.input_page_character_cap,
        "output_page_character_cap": chosen.output_page_character_cap,
        "input_page_count": int(packing["input_page_count"]),
        "short_page_identity_count": int(packing["short_page_identity_count"]),
        "long_page_packed_count": long_pages,
        "input_effective_content_characters": int(
            packing["input_effective_content_characters"]
        ),
        "input_characters_beyond_output_page_cap": sum(
            max(0, int(value) - chosen.output_page_character_cap)
            for value in packing["per_page_effective_content_characters"]
        ),
        "output_active_content_characters": int(
            packing["output_active_content_characters"]
        ),
        "projected_rendered_characters": int(
            packing["projected_rendered_characters"]
        ),
        "projection_differs_from_prefix_baseline": differs,
        "long_page_mechanism_engaged": long_pages > 0 and differs,
        "prefix_safe_fallback_applied": bool(
            packing["prefix_safe_fallback_applied"]
        ),
        "candidate_visible_requirement_gain_count": int(
            packing["candidate_visible_requirement_gain_count"]
        ),
        "candidate_requirement_coverage_not_less_than_prefix_baseline": bool(
            packing[
                "candidate_requirement_coverage_not_less_than_prefix_baseline"
            ]
        ),
        "selected_table_continuation_block_count": int(
            packing["selected_table_continuation_block_count"]
        ),
        "table_header_dependency_addition_count": int(
            packing["table_header_dependency_addition_count"]
        ),
        "orphan_selected_table_continuation_block_count": int(
            packing["orphan_selected_table_continuation_block_count"]
        ),
        "short_page_content_byte_identity_preserved": bool(
            packing["short_page_content_byte_identity_preserved"]
        ),
        "same_forward_page_bytes_only": bool(packing["same_forward_page_bytes_only"]),
        "entropy_information_gain_shadow_only": bool(
            packing["entropy_information_gain_shadow_only"]
        ),
        "entropy_or_information_gain_assigns_credit": bool(
            packing["entropy_or_information_gain_assigns_credit"]
        ),
        "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
    }
    receipt["receipt_payload_sha256"] = parent.payload_sha256(receipt)
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
        "short_page_identity_count",
        "long_page_packed_count",
        "input_effective_content_characters",
        "input_characters_beyond_output_page_cap",
        "output_active_content_characters",
        "projected_rendered_characters",
        "candidate_visible_requirement_gain_count",
        "selected_table_continuation_block_count",
        "table_header_dependency_addition_count",
        "orphan_selected_table_continuation_block_count",
    )
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
        or copied["short_page_identity_count"] + copied["long_page_packed_count"]
        != copied["input_page_count"]
        or copied["orphan_selected_table_continuation_block_count"] != 0
        or copied["candidate_requirement_coverage_not_less_than_prefix_baseline"]
        is not True
        or copied["short_page_content_byte_identity_preserved"] is not True
        or copied["same_forward_page_bytes_only"] is not True
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
        or copied["long_page_mechanism_engaged"]
        is not (
            copied["long_page_packed_count"] > 0
            and copied["projection_differs_from_prefix_baseline"] is True
        )
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.13 content-free packing receipt drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_KEYS",
    "ROLE",
    "build_observable_packing",
    "validate_receipt",
]
