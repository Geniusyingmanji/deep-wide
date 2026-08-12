"""Content-free observer for V2.51.58 vertical admission dispositions.

The observer mirrors the frozen V2.51.58 block-admission predicates and emits
only mutually-exclusive reason counts.  It never changes extraction output,
candidate ordering, routing, prediction, or any query/model/fetch budget.

No page text, key, value, identity, field, quote, URL, question, prediction,
semantic hash, benchmark label, mapping, gold, evaluator output, score, reward,
history, credential, filesystem, process, environment, model, or network
surface is emitted or accessed.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25158_vertical_key_value_candidate_runtime as frozen
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25163_vertical_admission_disposition_observer_v1"
ROLE = "v25163_content_free_vertical_admission_disposition_observation"

DISPOSITION_NAMES = (
    "empty_or_duplicate_normalized_key_reject",
    "mapped_field_unsafe_or_unknown_value_reject",
    "no_visible_schema_key_reject",
    "missing_primary_key_row_reject",
    "multiple_primary_key_rows_reject",
    "primary_identity_not_unique_production_row_reject",
    "identity_bound_without_nonkey_visible_field",
    "identity_bound_quote_span_reject",
    "identity_bound_without_changed_safe_candidate",
    "identity_bound_candidate_ready",
)
IDENTITY_BOUND_DISPOSITIONS = (
    "identity_bound_without_nonkey_visible_field",
    "identity_bound_quote_span_reject",
    "identity_bound_without_changed_safe_candidate",
    "identity_bound_candidate_ready",
)


def _block_disposition(
    content: str,
    block: Sequence[tuple[int, int, str, str]],
    *,
    page_ordinal: int,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> tuple[str, int]:
    """Return one mutually-exclusive reason and frozen candidate count."""

    seen_keys: set[str] = set()
    visible: list[tuple[int, int, int, str]] = []
    for start, end, raw_key, raw_value in block:
        key = frozen._vertical_key(raw_key)
        canonical_key = frozen._surface(key)
        if not key or not canonical_key or canonical_key in seen_keys:
            return "empty_or_duplicate_normalized_key_reject", 0
        seen_keys.add(canonical_key)
        field_index = frozen.parent._column_index(header, key)
        if field_index is None:
            continue
        value = frozen.deterministic_parent._safe_cell(raw_value)
        if value is None:
            return "mapped_field_unsafe_or_unknown_value_reject", 0
        visible.append((start, end, field_index, value))

    if not visible:
        return "no_visible_schema_key_reject", 0
    identity_rows = [entry for entry in visible if entry[2] == 0]
    if not identity_rows:
        return "missing_primary_key_row_reject", 0
    if len(identity_rows) > 1:
        return "multiple_primary_key_rows_reject", 0
    identity_start, identity_end, _identity_field, raw_identity = identity_rows[0]
    row_index = frozen.deterministic_parent._row_index(rows, raw_identity)
    if row_index is None:
        return "primary_identity_not_unique_production_row_reject", 0

    nonkey = [entry for entry in visible if entry[2] > 0]
    if not nonkey:
        return "identity_bound_without_nonkey_visible_field", 0

    quote_eligible = 0
    candidate_count = 0
    for field_start, field_end, field_index, raw_value in nonkey:
        quote_start = min(identity_start, field_start)
        quote_end = max(identity_end, field_end)
        exact_quote = content[quote_start:quote_end]
        if (
            not 1 <= len(exact_quote) <= frozen.MAXIMUM_QUOTE_CHARACTERS
            or not frozen.quote_parent._occurs_exactly_once(content, exact_quote)
        ):
            continue
        quote_eligible += 1
        candidate = frozen.deterministic_parent._proposal(
            page_ordinal=page_ordinal,
            quote=exact_quote,
            row_index=row_index,
            field_index=field_index,
            new_value=raw_value,
            header=header,
            rows=rows,
            source_kind="vertical_key_value_identity_field_span",
        )
        if candidate is not None:
            candidate_count += 1

    if candidate_count:
        return "identity_bound_candidate_ready", candidate_count
    if not quote_eligible:
        return "identity_bound_quote_span_reject", 0
    return "identity_bound_without_changed_safe_candidate", 0


def observe_vertical_admission(
    production: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Mirror frozen vertical admission and emit content-free dispositions."""

    header, rows = frozen.deterministic_parent.targeted_parent._table_matrix(
        production, columns
    )
    normalized_pages = [
        {
            "title": str(page.get("title") or ""),
            "content": str(page.get("content") or ""),
        }
        for page in pages
    ]
    dispositions = {name: 0 for name in DISPOSITION_NAMES}
    page_with_blocks = 0
    page_with_identity_bound = 0
    ambiguous_pages = 0
    frozen_candidate_observations = 0

    for page_ordinal, page in enumerate(normalized_pages, 1):
        content = page["content"]
        blocks = frozen._vertical_pipe_blocks(content)
        page_with_blocks += int(bool(blocks))
        bound_count = 0
        block_candidate_count = 0
        for block in blocks:
            disposition, candidate_count = _block_disposition(
                content,
                block,
                page_ordinal=page_ordinal,
                header=header,
                rows=rows,
            )
            dispositions[disposition] += 1
            bound_count += int(disposition in IDENTITY_BOUND_DISPOSITIONS)
            block_candidate_count += candidate_count

            frozen_bound, frozen_candidates = frozen._vertical_block_candidates(
                content,
                block,
                page_ordinal=page_ordinal,
                header=header,
                rows=rows,
            )
            if (
                frozen_bound is not (disposition in IDENTITY_BOUND_DISPOSITIONS)
                or len(frozen_candidates) != candidate_count
            ):
                raise ValueError("V2.51.63 frozen block parity drifted")

        frozen_candidates, structure = frozen._vertical_key_value_observations(
            content,
            page_ordinal=page_ordinal,
            header=header,
            rows=rows,
        )
        if (
            structure["vertical_pipe_block_count"] != len(blocks)
            or structure["vertical_identity_bound_block_count"] != bound_count
            or structure["vertical_ambiguous_page_count"] != int(bound_count > 1)
            or len(frozen_candidates)
            != (block_candidate_count if bound_count == 1 else 0)
        ):
            raise ValueError("V2.51.63 frozen page parity drifted")
        page_with_identity_bound += int(bound_count > 0)
        ambiguous_pages += int(bound_count > 1)
        frozen_candidate_observations += len(frozen_candidates)

    block_count = sum(dispositions.values())
    identity_bound = sum(dispositions[name] for name in IDENTITY_BOUND_DISPOSITIONS)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "page_count": len(normalized_pages),
        "page_with_vertical_block_count": page_with_blocks,
        "vertical_block_count": block_count,
        "disposition_counts": dispositions,
        "identity_bound_block_count": identity_bound,
        "page_with_identity_bound_block_count": page_with_identity_bound,
        "ambiguous_page_count": ambiguous_pages,
        "frozen_vertical_candidate_observation_count": frozen_candidate_observations,
        "dispositions_are_mutually_exclusive_and_exhaustive": True,
        "frozen_v25158_block_and_page_admission_parity_verified": True,
        "observer_reason_buckets_change_admission_routing_prediction_or_budget": False,
        "page_text_key_value_identity_field_quote_url_question_prediction_or_semantic_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    dispositions = copied.get("disposition_counts")
    true_flags = (
        "dispositions_are_mutually_exclusive_and_exhaustive",
        "frozen_v25158_block_and_page_admission_parity_verified",
    )
    false_flags = (
        "observer_reason_buckets_change_admission_routing_prediction_or_budget",
        "page_text_key_value_identity_field_quote_url_question_prediction_or_semantic_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    count_names = (
        "page_count",
        "page_with_vertical_block_count",
        "vertical_block_count",
        "identity_bound_block_count",
        "page_with_identity_bound_block_count",
        "ambiguous_page_count",
        "frozen_vertical_candidate_observation_count",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            *count_names,
            "disposition_counts",
            *true_flags,
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(dispositions, Mapping)
        or set(dispositions) != set(DISPOSITION_NAMES)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_names
        )
        or any(
            isinstance(dispositions.get(name), bool)
            or not isinstance(dispositions.get(name), int)
            or dispositions[name] < 0
            for name in DISPOSITION_NAMES
        )
        or copied["vertical_block_count"] != sum(dispositions.values())
        or copied["identity_bound_block_count"]
        != sum(dispositions[name] for name in IDENTITY_BOUND_DISPOSITIONS)
        or copied["page_with_vertical_block_count"] > copied["page_count"]
        or copied["page_with_identity_bound_block_count"] > copied["page_count"]
        or copied["ambiguous_page_count"]
        > copied["page_with_identity_bound_block_count"]
        or dispositions["identity_bound_candidate_ready"]
        > copied["identity_bound_block_count"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.63 vertical disposition observation drifted")
    return copied


__all__ = [
    "DISPOSITION_NAMES",
    "IDENTITY_BOUND_DISPOSITIONS",
    "POLICY_ID",
    "ROLE",
    "observe_vertical_admission",
    "validate_observation",
]
