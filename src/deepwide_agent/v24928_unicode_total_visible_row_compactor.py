"""Unicode-total visible-row compaction before target--value projection.

V2.49.24 measured compacted text against the *raw* input length even though
its inherited cleaner first applies NFKC normalization.  Compatibility
characters can expand under NFKC (for example ``½`` -> ``1⁄2``), so a valid
page could fail the receipt before synthesis.  This append-only successor
keeps the transform and all projection caps unchanged, but accounts for raw
and normalized input lengths separately and enforces compaction against the
normalized budget domain.

Inputs remain limited to the visible question and pages fetched during the
same forward pass.  The component has no file, environment, process, network,
model, benchmark-label, gold, evaluator, score, reward, or historical-result
capability.  Entropy/information gain remains shadow-only.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as structure
from . import v24921_target_value_coverage_projector as target_value
from . import v24924_visible_row_table_compactor as parent


POLICY_ID = "v24928_unicode_total_visible_row_sparse_table_compactor_v1"
ROLE = "v24928_unicode_total_visible_row_sparse_projection"
RECEIPT_ROLE = "v24928_content_free_unicode_total_compaction_receipt"
payload_sha256 = target_value.payload_sha256


def compact_pages(
    question: str, pages: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compact pages while accounting in the NFKC-normalized length domain."""

    visible_rows = target_value.visible_row_targets(question)
    output: list[dict[str, Any]] = []
    totals = {
        "table_count": 0,
        "eligible_table_count": 0,
        "input_table_row_count": 0,
        "retained_table_row_count": 0,
        "dropped_table_row_count": 0,
    }
    raw_characters = 0
    normalized_characters = 0
    output_characters = 0
    expansion_characters = 0
    contraction_characters = 0
    expansion_pages = 0
    contraction_pages = 0
    for raw in pages:
        if not isinstance(raw, Mapping):
            continue
        copied = copy.deepcopy(dict(raw))
        original = str(copied.get("raw_content") or copied.get("content") or "")
        normalized = structure._clean(original)
        compacted, counts = parent.compact_page_content(original, visible_rows)
        if "raw_content" in copied:
            copied["raw_content"] = compacted
        else:
            copied["content"] = compacted
        raw_size = len(original)
        normalized_size = len(normalized)
        delta = normalized_size - raw_size
        raw_characters += raw_size
        normalized_characters += normalized_size
        output_characters += len(compacted)
        expansion_characters += max(0, delta)
        contraction_characters += max(0, -delta)
        expansion_pages += int(delta > 0)
        contraction_pages += int(delta < 0)
        for name in totals:
            totals[name] += counts[name]
        output.append(copied)
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "visible_row_target_count": len(visible_rows),
        "input_page_count": len(pages),
        "output_page_count": len(output),
        "raw_input_content_characters": raw_characters,
        "normalized_input_content_characters": normalized_characters,
        "output_content_characters": output_characters,
        "nfkc_expansion_characters": expansion_characters,
        "nfkc_contraction_characters": contraction_characters,
        "nfkc_expansion_page_count": expansion_pages,
        "nfkc_contraction_page_count": contraction_pages,
        **totals,
        "compaction_budget_domain": "nfkc_normalized_input_characters",
        "unicode_normalization_form": "NFKC",
        "unicode_normalization_is_parent_cleaner_owned": True,
        "only_visible_row_bound_table_rows_removed_or_retained": True,
        "table_header_and_separator_preserved_for_compacted_tables": True,
        "non_table_text_preserved_after_nfkc_normalization": True,
        "page_title_url_order_and_count_preserved": True,
        "additional_search_fetch_model_token_context_or_wall_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_row_page_content_url_hash_opaque_id_or_credential": False,
        "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return output, validate_receipt(receipt)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "visible_row_target_count",
        "input_page_count",
        "output_page_count",
        "raw_input_content_characters",
        "normalized_input_content_characters",
        "output_content_characters",
        "nfkc_expansion_characters",
        "nfkc_contraction_characters",
        "nfkc_expansion_page_count",
        "nfkc_contraction_page_count",
        "table_count",
        "eligible_table_count",
        "input_table_row_count",
        "retained_table_row_count",
        "dropped_table_row_count",
    )
    raw = copied.get("raw_input_content_characters")
    normalized = copied.get("normalized_input_content_characters")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["output_page_count"] != copied["input_page_count"]
        or copied["output_content_characters"] > normalized
        or normalized - raw
        != copied["nfkc_expansion_characters"]
        - copied["nfkc_contraction_characters"]
        or copied["nfkc_expansion_page_count"] > copied["input_page_count"]
        or copied["nfkc_contraction_page_count"] > copied["input_page_count"]
        or copied["nfkc_expansion_page_count"]
        + copied["nfkc_contraction_page_count"]
        > copied["input_page_count"]
        or copied["eligible_table_count"] > copied["table_count"]
        or copied["retained_table_row_count"]
        + copied["dropped_table_row_count"]
        > copied["input_table_row_count"]
        or copied.get("compaction_budget_domain")
        != "nfkc_normalized_input_characters"
        or copied.get("unicode_normalization_form") != "NFKC"
        or copied.get("unicode_normalization_is_parent_cleaner_owned") is not True
        or copied.get("only_visible_row_bound_table_rows_removed_or_retained")
        is not True
        or copied.get("table_header_and_separator_preserved_for_compacted_tables")
        is not True
        or copied.get("non_table_text_preserved_after_nfkc_normalization") is not True
        or copied.get("page_title_url_order_and_count_preserved") is not True
        or copied.get("additional_search_fetch_model_token_context_or_wall_cap")
        is not False
        or copied.get("entropy_information_gain_shadow_only") is not True
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "contains_question_row_page_content_url_hash_opaque_id_or_credential"
        )
        is not False
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.28 Unicode-total compaction receipt drifted")
    return copied


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    compacted, receipt = compact_pages(question, pages)
    projection = target_value.build_projection(
        question, compacted, explicit_groups=explicit_groups
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "projection": projection["projection"],
        "projection_sha256": hashlib.sha256(
            projection["projection"].encode("utf-8")
        ).hexdigest(),
        "projection_receipt": projection["content_free_receipt"],
        "compaction_receipt": receipt,
        "same_forward_page_bytes_only": True,
        "additional_search_fetch_model_token_context_or_wall_cap": False,
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
    projection = copied.get("projection")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(projection, str)
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode("utf-8")).hexdigest()
        or target_value.validate_receipt(copied.get("projection_receipt", {}))
        != copied.get("projection_receipt")
        or validate_receipt(copied.get("compaction_receipt", {}))
        != copied.get("compaction_receipt")
        or copied.get("same_forward_page_bytes_only") is not True
        or copied.get("additional_search_fetch_model_token_context_or_wall_cap")
        is not False
        or copied.get("entropy_information_gain_shadow_only") is not True
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.28 Unicode-total sparse projection drifted")
    if replay and copied != build_projection(
        question, pages, explicit_groups=explicit_groups
    ):
        raise ValueError("V2.49.28 projection is not reproducible")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_projection",
    "compact_pages",
    "payload_sha256",
    "validate_projection",
    "validate_receipt",
]
