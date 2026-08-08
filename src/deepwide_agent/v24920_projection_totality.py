"""Total projection boundary for the V2.49.16 long-page mechanism.

V2.49.16 totalized the diagnosed per-page structural-selection overflow but
left the rendered-total overflow outside its narrow exception boundary.  This
append-only wrapper catches only those two documented projection-cap failures
and returns the exact stable 5k prefix over the same already-fetched pages.
It does not search, fetch, call a model, alter a budget, or assign credit.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24911_long_page_evidence_packer as parent
from .v24911_long_page_evidence_packer import PackingPolicy
from . import v24916_prefix_total_long_page_packer as previous


POLICY_ID = "v24920_projection_totality_v1"
ROLE = "v24920_content_free_projection_totality_receipt"
TOTAL_OVERFLOW_MESSAGE = "V2.49.11 rendered projection exceeded total cap"
ALLOWED_MESSAGES = frozenset({previous.OVERFLOW_MESSAGE, TOTAL_OVERFLOW_MESSAGE})
FALLBACK_REASONS = frozenset({"none", "per_page_cap", "rendered_total_cap"})
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "input_page_character_cap",
        "output_page_character_cap",
        "total_rendered_character_cap",
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
        "projection_totality_fallback_applied",
        "projection_totality_fallback_reason",
        "fallback_trigger_was_exact_allowed_projection_cap_error",
        "fallback_projection_is_exact_stable_5k_prefix",
        "candidate_visible_requirement_gain_count",
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


def _policy(policy: PackingPolicy | None) -> PackingPolicy:
    chosen = policy or PackingPolicy(
        input_page_character_cap=12_000,
        output_page_character_cap=5_000,
        block_character_cap=1_200,
        total_rendered_character_cap=60_000,
        maximum_pages=10,
        maximum_visible_groups=64,
        maximum_query_terms=96,
    )
    chosen.validate()
    if (
        chosen.input_page_character_cap != 12_000
        or chosen.output_page_character_cap != 5_000
        or chosen.total_rendered_character_cap != 60_000
        or chosen.maximum_pages != 10
    ):
        raise ValueError("V2.49.20 production projection caps drifted")
    return chosen


def _stable_prefix(
    pages: Sequence[Mapping[str, Any]], policy: PackingPolicy
) -> tuple[str, list[dict[str, Any]], int]:
    stable = parent._stable_pages(pages, policy)
    excerpts = [
        str(page["effective_content"])[: policy.output_page_character_cap]
        for page in stable
    ]
    # The legacy evidence budget counts active page content, not provenance
    # headers.  Preserve that exact baseline even when long URLs make the
    # rendered string longer than evidence_chars.
    projection = parent._render(stable, excerpts)
    return projection, stable, sum(len(value) for value in excerpts)


def _reason(error: RuntimeError) -> str:
    message = str(error)
    if message == previous.OVERFLOW_MESSAGE:
        return "per_page_cap"
    if message == TOTAL_OVERFLOW_MESSAGE:
        return "rendered_total_cap"
    raise error


def build_projection_totality(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
    policy: PackingPolicy | None = None,
) -> dict[str, Any]:
    chosen = _policy(policy)
    prefix_projection, stable, prefix_active = _stable_prefix(pages, chosen)
    reason = "none"
    try:
        packing = previous.build_prefix_total_packing(
            question,
            pages,
            explicit_groups=explicit_groups,
            policy=chosen,
        )
        base = previous.validate_receipt(packing["content_free_receipt"])
        if base["structural_cap_totality_fallback_applied"]:
            reason = "per_page_cap"
    except RuntimeError as error:
        reason = _reason(error)
        packing = {
            "projection": prefix_projection,
            "search_provider_narrative_or_snippet_forwarded": False,
        }
        base = None

    fallback = reason != "none"
    if fallback:
        projection = prefix_projection
        output_active = prefix_active
        query_aware = 0
        differs = False
        engaged = False
        gain = continuation = additions = orphan = 0
    else:
        projection = str(packing["projection"])
        if base is None:
            raise RuntimeError("V2.49.20 successful projection lost its receipt")
        output_active = int(base["output_active_content_characters"])
        query_aware = int(base["final_query_aware_long_page_count"])
        differs = bool(base["projection_differs_from_prefix_baseline"])
        engaged = bool(base["long_page_mechanism_engaged"])
        gain = int(base["candidate_visible_requirement_gain_count"])
        continuation = int(base["selected_table_continuation_block_count"])
        additions = int(base["table_header_dependency_addition_count"])
        orphan = int(base["orphan_selected_table_continuation_block_count"])

    lengths = [int(page["effective_content_characters"]) for page in stable]
    long_count = sum(value > chosen.output_page_character_cap for value in lengths)
    short_count = len(stable) - long_count
    exact_prefix = projection == prefix_projection
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "input_page_character_cap": chosen.input_page_character_cap,
        "output_page_character_cap": chosen.output_page_character_cap,
        "total_rendered_character_cap": chosen.total_rendered_character_cap,
        "input_page_count": len(stable),
        "original_short_page_count": short_count,
        "original_long_page_count": long_count,
        "input_effective_content_characters": sum(lengths),
        "input_characters_beyond_output_page_cap": sum(
            max(0, value - chosen.output_page_character_cap) for value in lengths
        ),
        "output_active_content_characters": output_active,
        "projected_rendered_characters": len(projection),
        "final_query_aware_long_page_count": query_aware,
        "projection_differs_from_prefix_baseline": differs,
        "long_page_mechanism_engaged": engaged,
        "projection_totality_fallback_applied": fallback,
        "projection_totality_fallback_reason": reason,
        "fallback_trigger_was_exact_allowed_projection_cap_error": fallback,
        "fallback_projection_is_exact_stable_5k_prefix": fallback and exact_prefix,
        "candidate_visible_requirement_gain_count": gain,
        "selected_table_continuation_block_count": continuation,
        "table_header_dependency_addition_count": additions,
        "orphan_selected_table_continuation_block_count": orphan,
        "original_short_page_content_byte_identity_preserved": all(
            str(page["effective_content"])
            == str(page["effective_content"])[: chosen.output_page_character_cap]
            for page in stable
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
    receipt["receipt_payload_sha256"] = parent.payload_sha256(receipt)
    packing["projection"] = projection
    packing["content_free_receipt"] = validate_receipt(receipt)
    return packing


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integers = (
        "input_page_character_cap",
        "output_page_character_cap",
        "total_rendered_character_cap",
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
    fallback = copied.get("projection_totality_fallback_applied")
    reason = copied.get("projection_totality_fallback_reason")
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
        or copied["total_rendered_character_cap"] != 60_000
        or copied["input_page_count"] > 10
        or copied["original_short_page_count"] + copied["original_long_page_count"]
        != copied["input_page_count"]
        or copied["final_query_aware_long_page_count"]
        > copied["original_long_page_count"]
        or copied["output_active_content_characters"]
        > 5_000 * copied["input_page_count"]
        or copied["orphan_selected_table_continuation_block_count"] != 0
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
        or reason not in FALLBACK_REASONS
        or fallback is not (reason != "none")
        or copied["fallback_trigger_was_exact_allowed_projection_cap_error"]
        is not fallback
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
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.20 projection totality receipt drifted")
    return copied


__all__ = [
    "ALLOWED_MESSAGES",
    "FALLBACK_REASONS",
    "POLICY_ID",
    "RECEIPT_KEYS",
    "ROLE",
    "TOTAL_OVERFLOW_MESSAGE",
    "build_projection_totality",
    "validate_receipt",
]
