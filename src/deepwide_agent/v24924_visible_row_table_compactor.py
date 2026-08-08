"""Visible-row sparse table compaction before target--value projection.

Long structured pages often spend the fixed 5k/page budget on unrelated table
rows.  This pure transform keeps each Markdown table header/separator and only
rows that bind a user-visible row entity.  Non-table text is preserved so the
downstream target--value projector retains its ordinary fallback surface.

Inputs are only the visible question and same-forward fetched pages.  The
component has no file, environment, network, model, benchmark label, gold,
evaluator, score, reward, or historical-result capability.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as structure
from . import v24921_target_value_coverage_projector as target_value


POLICY_ID = "v24924_visible_row_sparse_table_compactor_v1"
ROLE = "v24924_visible_row_sparse_projection"
RECEIPT_ROLE = "v24924_content_free_visible_row_compaction_receipt"
payload_sha256 = target_value.payload_sha256


def _table_cells(line: str) -> list[str]:
    value = line.strip()
    if not value.startswith("|") or not value.endswith("|"):
        return []
    return [cell.strip() for cell in value.strip("|").split("|")]


def _separator(line: str) -> bool:
    cells = _table_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _row_bound(line: str, rows: Sequence[str]) -> bool:
    cells = {
        structure._canonical_phrase(cell)
        for cell in _table_cells(line)
        if structure._canonical_phrase(cell)
    }
    return any(row in cells for row in rows)


def compact_page_content(
    content: str, visible_rows: Sequence[str]
) -> tuple[str, dict[str, int]]:
    if not isinstance(content, str):
        raise ValueError("V2.49.24 page content must be text")
    rows = [structure._canonical_phrase(row) for row in visible_rows]
    rows = [row for row in rows if row]
    lines = structure._clean(content).splitlines()
    output: list[str] = []
    table_count = 0
    eligible_table_count = 0
    input_table_rows = 0
    retained_table_rows = 0
    dropped_table_rows = 0
    index = 0
    while index < len(lines):
        if not _table_cells(lines[index]):
            output.append(lines[index])
            index += 1
            continue
        end = index
        while end < len(lines) and _table_cells(lines[end]):
            end += 1
        table = lines[index:end]
        table_count += 1
        if len(table) < 2 or not _separator(table[1]):
            output.extend(table)
            index = end
            continue
        header, separator, *body = table
        input_table_rows += len(body)
        selected = [
            line
            for line in body
            if _row_bound(line, rows)
        ]
        if selected:
            eligible_table_count += 1
            output.extend((header, separator, *selected))
            retained_table_rows += len(selected)
            dropped_table_rows += len(body) - len(selected)
        else:
            # A table that cannot bind a visible row is not silently removed;
            # keeping it preserves the parent's safe generic fallback surface.
            output.extend(table)
        index = end
    compacted = "\n".join(output).strip()
    return compacted, {
        "table_count": table_count,
        "eligible_table_count": eligible_table_count,
        "input_table_row_count": input_table_rows,
        "retained_table_row_count": retained_table_rows,
        "dropped_table_row_count": dropped_table_rows,
    }


def compact_pages(
    question: str, pages: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    visible_rows = target_value.visible_row_targets(question)
    output: list[dict[str, Any]] = []
    totals = {
        "table_count": 0,
        "eligible_table_count": 0,
        "input_table_row_count": 0,
        "retained_table_row_count": 0,
        "dropped_table_row_count": 0,
    }
    input_characters = 0
    output_characters = 0
    for raw in pages:
        if not isinstance(raw, Mapping):
            continue
        copied = copy.deepcopy(dict(raw))
        original = str(copied.get("raw_content") or copied.get("content") or "")
        compacted, counts = compact_page_content(original, visible_rows)
        if "raw_content" in copied:
            copied["raw_content"] = compacted
        else:
            copied["content"] = compacted
        input_characters += len(original)
        output_characters += len(compacted)
        for name in totals:
            totals[name] += counts[name]
        output.append(copied)
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "visible_row_target_count": len(visible_rows),
        "input_page_count": len(pages),
        "output_page_count": len(output),
        "input_content_characters": input_characters,
        "output_content_characters": output_characters,
        **totals,
        "only_visible_row_bound_table_rows_removed_or_retained": True,
        "table_header_and_separator_preserved_for_compacted_tables": True,
        "non_table_text_preserved": True,
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
        "input_content_characters",
        "output_content_characters",
        "table_count",
        "eligible_table_count",
        "input_table_row_count",
        "retained_table_row_count",
        "dropped_table_row_count",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["output_page_count"] != copied["input_page_count"]
        or copied["output_content_characters"] > copied["input_content_characters"]
        or copied["eligible_table_count"] > copied["table_count"]
        or copied["retained_table_row_count"] + copied["dropped_table_row_count"]
        > copied["input_table_row_count"]
        or copied.get("only_visible_row_bound_table_rows_removed_or_retained")
        is not True
        or copied.get("table_header_and_separator_preserved_for_compacted_tables")
        is not True
        or copied.get("non_table_text_preserved") is not True
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
        raise ValueError("V2.49.24 visible-row compaction receipt drifted")
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
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.24 visible-row sparse projection drifted")
    if replay and copied != build_projection(
        question, pages, explicit_groups=explicit_groups
    ):
        raise ValueError("V2.49.24 projection is not reproducible")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_projection",
    "compact_page_content",
    "compact_pages",
    "payload_sha256",
    "validate_projection",
    "validate_receipt",
]
