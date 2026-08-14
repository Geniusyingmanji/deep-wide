"""Pure generic mechanical-field successor over V2.54.71.

The completed table supplies exact visible columns and row identities.  Pages
must already be jointly bound to exactly one row by URL-path and visible page
surface under V2.54.64.  This successor preserves every V2.54.71 candidate
and adds only source shapes demonstrated by V2.54.83 but expressed for any
visible schema:

* a fused qualifier on a two-cell pipe label (``pkgVersion | 2.0``),
* one separate or fused qualifier on a same-line labelled field, and
* an exact, one-qualifier, or fused standalone label followed by the first
  non-empty value no more than two source lines later.

The complete visible field token sequence must be present mechanically; no
synonym, ontology, host vocabulary, task rule, or model inference is used.
Duplicate or conflicting coordinates, unsafe/Unknown values, surface-only
changes, list collapse, and table-shape changes fail closed.  This module is
pure, performs no I/O, assigns zero entropy/IG credit, and authorizes no run.
"""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25004_identity_bound_detail_fields as identity
from . import v25432_source_authoritative_field_candidate as source
from . import v25464_row_key_bound_structured_source_candidate as row_bound
from . import v25471_qualified_source_label_candidate as parent


POLICY_ID = "v25499_generic_mechanical_field_candidate_v1"
REGISTRY_ROLE = "v25499_generic_mechanical_field_candidate_registry"
REGISTRY_RECEIPT_ROLE = "v25499_content_free_candidate_registry_receipt"
APPLICATION_ROLE = "v25499_generic_mechanical_field_application"
APPLICATION_RECEIPT_ROLE = "v25499_content_free_candidate_application_receipt"

PAGE_KEYS = parent.PAGE_KEYS
MAXIMUM_CANDIDATES = parent.MAXIMUM_CANDIDATES
_CANDIDATE_ID = re.compile(r"C[0-9]{3}")
_LABELLED = re.compile(r"([^:=：\t]{1,120})\s*[:=：\t]\s*(.+?)\s*")
_NEW_SOURCE_KINDS = frozenset(
    {
        "generic_fused_two_cell_pipe_record",
        "generic_qualified_same_line_labelled_record",
        "generic_standalone_label_adjacent_value_record",
    }
)
_SOURCE_KINDS = frozenset({*parent._SOURCE_KINDS, *_NEW_SOURCE_KINDS})
_IDENTITY_BINDING_KINDS = parent._IDENTITY_BINDING_KINDS
_COUNT_FIELDS = (
    *parent._COUNT_FIELDS,
    "generic_mechanical_field_surface_count",
    "generic_mechanical_observation_count",
    "exact_label_surface_count",
    "separate_qualifier_surface_count",
    "fused_qualifier_surface_count",
    "fused_pipe_surface_count",
    "qualified_labelled_surface_count",
    "standalone_adjacent_surface_count",
    "standalone_missing_value_count",
    "standalone_next_field_rejection_count",
)


payload_sha256 = parent.payload_sha256
_GRAMMAR_COUNT = {
    "exact": "exact_label_surface_count",
    "separate_qualifier": "separate_qualifier_surface_count",
    "fused_qualifier": "fused_qualifier_surface_count",
}


def _clean_label(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = re.sub(r"^[#*_`~+\-\s:]+", "", text)
    text = re.sub(r"[#*_`~+\-\s:]+$", "", text)
    return text.strip()


def _field(label: str, columns: Sequence[str]) -> tuple[int, str, str] | None:
    """Bind one exact/separate/fused complete visible field token vector."""

    label_tokens = identity._tokens(_clean_label(label))
    if not label_tokens:
        return None
    matches: list[tuple[int, str, str]] = []
    for index, visible in enumerate(columns):
        if index == 0:
            continue
        field_tokens = identity._tokens(visible)
        exact = tuple(label_tokens) == tuple(field_tokens)
        separate = bool(
            field_tokens
            and len(label_tokens) == len(field_tokens) + 1
            and tuple(label_tokens[-len(field_tokens) :]) == tuple(field_tokens)
            and len(label_tokens[0]) >= 2
        )
        fused = bool(
            field_tokens
            and len(label_tokens) == len(field_tokens)
            and tuple(label_tokens[1:]) == tuple(field_tokens[1:])
            and label_tokens[0].endswith(field_tokens[0])
            and 2 <= len(label_tokens[0]) - len(field_tokens[0]) <= 8
        )
        if exact or separate or fused:
            grammar = (
                "exact"
                if exact
                else "separate_qualifier"
                if separate
                else "fused_qualifier"
            )
            matches.append((index, str(visible), grammar))
    return matches[0] if len(matches) == 1 else None


def _offer(
    observations: list[dict[str, Any]],
    counts: Counter[str],
    *,
    page: Mapping[str, Any],
    rows: Sequence[Sequence[str]],
    row_index: int,
    column_index: int,
    field: str,
    grammar: str,
    source_field: str,
    source_value: object,
    quote_start: int,
    quote_end: int,
    source_kind: str,
) -> None:
    counts["generic_mechanical_field_surface_count"] += 1
    counts[_GRAMMAR_COUNT[grammar]] += 1
    counts["raw_observation_count"] += 1
    content = str(page["content"])
    value = source._safe_cell(source_value)
    quote = content[quote_start:quote_end]
    clean_field = _clean_label(source_field)
    if (
        value is None
        or not clean_field
        or not 1 <= len(quote) <= source.MAXIMUM_QUOTE_CHARACTERS
        or content.count(quote) != 1
        or clean_field not in quote
        or value not in quote
    ):
        return
    observations.append(
        {
            "page_ordinal": int(page["page_ordinal"]),
            "source_url": str(page["url"]),
            "source_host": str(page["source_host"]),
            "quote_start": int(quote_start),
            "quote_end": int(quote_end),
            "exact_quote": quote,
            "row_identity": str(rows[row_index][0]),
            "source_field": clean_field,
            "field": str(field),
            "old_value": str(rows[row_index][column_index]),
            "exact_value": value,
            "source_kind": source_kind,
            "identity_binding_kind": "unique_url_path_and_surface_page_binding",
            "row_index": int(row_index),
            "column_index": int(column_index),
            "origin": "generic_mechanical_field",
        }
    )
    counts["evidence_closed_observation_count"] += 1
    counts["generic_mechanical_observation_count"] += 1


def _generic_observations(
    rows: Sequence[Sequence[str]],
    pages: Sequence[Mapping[str, Any]],
    *,
    columns: Sequence[str],
    counts: Counter[str],
) -> list[dict[str, Any]]:
    bound, _bound_counts = row_bound._bound_pages(rows, pages)
    row_map = {source._key(row[0]): index for index, row in enumerate(rows)}
    output: list[dict[str, Any]] = []
    for page in bound:
        row_index = row_map[source._key(page["row_identity"])]
        lines = source._line_spans(str(page["content"]))
        for index, (start, end, line) in enumerate(lines):
            cells = source._pipe_cells(line)
            if cells is not None and len(cells) == 2 and not source._separator(cells):
                matched = _field(cells[0], columns)
                if matched is not None and matched[2] == "fused_qualifier":
                    column_index, field, grammar = matched
                    counts["fused_pipe_surface_count"] += 1
                    _offer(
                        output,
                        counts,
                        page=page,
                        rows=rows,
                        row_index=row_index,
                        column_index=column_index,
                        field=field,
                        grammar=grammar,
                        source_field=cells[0],
                        source_value=cells[1],
                        quote_start=start,
                        quote_end=end,
                        source_kind="generic_fused_two_cell_pipe_record",
                    )
                continue

            labelled = _LABELLED.fullmatch(str(line).strip())
            if labelled is not None:
                matched = _field(labelled.group(1), columns)
                if matched is not None and matched[2] in {
                    "separate_qualifier",
                    "fused_qualifier",
                }:
                    column_index, field, grammar = matched
                    counts["qualified_labelled_surface_count"] += 1
                    _offer(
                        output,
                        counts,
                        page=page,
                        rows=rows,
                        row_index=row_index,
                        column_index=column_index,
                        field=field,
                        grammar=grammar,
                        source_field=labelled.group(1),
                        source_value=labelled.group(2),
                        quote_start=start,
                        quote_end=end,
                        source_kind="generic_qualified_same_line_labelled_record",
                    )
                continue

            clean = _clean_label(line)
            matched = _field(clean, columns)
            if matched is None:
                continue
            following = next(
                (
                    (cursor, lines[cursor])
                    for cursor in range(index + 1, min(len(lines), index + 3))
                    if lines[cursor][2].strip()
                ),
                None,
            )
            if following is None:
                counts["generic_mechanical_field_surface_count"] += 1
                counts[_GRAMMAR_COUNT[matched[2]]] += 1
                counts["standalone_missing_value_count"] += 1
                continue
            cursor, (_next_start, next_end, next_line) = following
            if _field(_clean_label(next_line), columns) is not None:
                counts["generic_mechanical_field_surface_count"] += 1
                counts[_GRAMMAR_COUNT[matched[2]]] += 1
                counts["standalone_next_field_rejection_count"] += 1
                continue
            column_index, field, grammar = matched
            counts["standalone_adjacent_surface_count"] += 1
            _offer(
                output,
                counts,
                page=page,
                rows=rows,
                row_index=row_index,
                column_index=column_index,
                field=field,
                grammar=grammar,
                source_field=clean,
                source_value=next_line.strip(),
                quote_start=start,
                quote_end=next_end,
                source_kind="generic_standalone_label_adjacent_value_record",
            )
    return output


def _parent_observations(
    registry: Mapping[str, Any],
    rows: Sequence[Sequence[str]],
    columns: Sequence[str],
) -> list[dict[str, Any]]:
    checked = parent.validate_registry(registry)
    row_map = {source._key(row[0]): index for index, row in enumerate(rows)}
    column_map = {source._key(field): index for index, field in enumerate(columns)}
    return [
        {
            **{
                name: copy.deepcopy(item[name])
                for name in (
                    "page_ordinal",
                    "source_url",
                    "source_host",
                    "quote_start",
                    "quote_end",
                    "exact_quote",
                    "row_identity",
                    "source_field",
                    "field",
                    "old_value",
                    "exact_value",
                    "source_kind",
                    "identity_binding_kind",
                )
            },
            "row_index": row_map[source._key(item["row_identity"])],
            "column_index": column_map[source._key(item["field"])],
            "origin": "parent",
        }
        for item in checked["candidates"]
    ]


def _candidate(observation: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    value: dict[str, Any] = {
        "candidate_id": candidate_id,
        **{
            name: copy.deepcopy(observation[name])
            for name in (
                "page_ordinal",
                "source_url",
                "source_host",
                "quote_start",
                "quote_end",
                "exact_quote",
                "row_identity",
                "source_field",
                "field",
                "old_value",
                "exact_value",
                "source_kind",
                "identity_binding_kind",
            )
        },
        "source_coordinate_is_unique": True,
        "target_table_coordinate_is_unique": True,
        "value_is_source_extracted_not_model_generated": True,
        "material_semantic_change_not_surface_only": True,
        "list_cardinality_noncollapse": True,
    }
    value["candidate_payload_sha256"] = payload_sha256(value)
    return validate_candidate(value)


def _new_source_shape_valid(value: Mapping[str, Any]) -> bool:
    kind = str(value.get("source_kind") or "")
    quote = str(value.get("exact_quote") or "")
    source_field = str(value.get("source_field") or "")
    exact_value = str(value.get("exact_value") or "")
    if kind == "generic_fused_two_cell_pipe_record":
        cells = source._pipe_cells(quote.strip())
        return bool(
            cells is not None
            and len(cells) == 2
            and not source._separator(cells)
            and _clean_label(cells[0]) == source_field
            and source._safe_cell(cells[1]) == exact_value
        )
    if kind == "generic_qualified_same_line_labelled_record":
        matched = _LABELLED.fullmatch(quote.strip())
        return bool(
            matched is not None
            and _clean_label(matched.group(1)) == source_field
            and source._safe_cell(matched.group(2)) == exact_value
        )
    if kind == "generic_standalone_label_adjacent_value_record":
        lines = source._line_spans(quote)
        if not lines or _clean_label(lines[0][2]) != source_field:
            return False
        following = next(
            (
                (index, line)
                for index, (_start, _end, line) in enumerate(lines[1:3], 1)
                if line.strip()
            ),
            None,
        )
        return bool(
            following is not None
            and source._safe_cell(following[1].strip()) == exact_value
        )
    return True


def validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("candidate_payload_sha256", None)
    canonical = source._canonical_url(copied.get("source_url"))
    strings = tuple(
        copied.get(name)
        for name in (
            "exact_quote",
            "row_identity",
            "source_field",
            "field",
            "old_value",
            "exact_value",
        )
    )
    if (
        set(copied) != row_bound._CANDIDATE_KEYS
        or _CANDIDATE_ID.fullmatch(str(copied.get("candidate_id", ""))) is None
        or isinstance(copied.get("page_ordinal"), bool)
        or not isinstance(copied.get("page_ordinal"), int)
        or copied["page_ordinal"] < 1
        or canonical is None
        or copied.get("source_url") != canonical[0]
        or copied.get("source_host") != canonical[1]
        or isinstance(copied.get("quote_start"), bool)
        or not isinstance(copied.get("quote_start"), int)
        or isinstance(copied.get("quote_end"), bool)
        or not isinstance(copied.get("quote_end"), int)
        or copied["quote_start"] < 0
        or copied["quote_end"] <= copied["quote_start"]
        or any(not isinstance(item, str) or not item or "\x00" in item for item in strings)
        or len(copied["exact_quote"])
        != copied["quote_end"] - copied["quote_start"]
        or copied["source_field"] not in copied["exact_quote"]
        or copied["exact_value"] not in copied["exact_quote"]
        or source._safe_cell(copied["exact_value"]) != copied["exact_value"]
        or row_bound._surface_equivalent(
            copied["field"], copied["old_value"], copied["exact_value"]
        )
        or copied.get("source_kind") not in _SOURCE_KINDS
        or not _new_source_shape_valid(copied)
        or copied.get("identity_binding_kind") not in _IDENTITY_BINDING_KINDS
        or any(
            copied.get(name) is not True
            for name in (
                "source_coordinate_is_unique",
                "target_table_coordinate_is_unique",
                "value_is_source_extracted_not_model_generated",
                "material_semantic_change_not_surface_only",
                "list_cardinality_noncollapse",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.99 candidate drifted")
    if copied["source_kind"] in _NEW_SOURCE_KINDS:
        matched = _field(copied["source_field"], ("__key__", copied["field"]))
        if matched is None:
            raise ValueError("V2.54.99 mechanical field binding drifted")
        grammar = matched[2]
        allowed = {
            "generic_fused_two_cell_pipe_record": {"fused_qualifier"},
            "generic_qualified_same_line_labelled_record": {
                "separate_qualifier",
                "fused_qualifier",
            },
            "generic_standalone_label_adjacent_value_record": {
                "exact",
                "separate_qualifier",
                "fused_qualifier",
            },
        }[copied["source_kind"]]
        if grammar not in allowed:
            raise ValueError("V2.54.99 source-shape grammar drifted")
    else:
        parent.validate_candidate(copied)
    return copied


def _registry_receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "all_v25471_candidates_preserved": True,
        "complete_visible_field_tokens_required": True,
        "exact_one_token_or_short_fused_qualifier_only": True,
        "two_cell_pipe_same_line_labelled_or_bounded_adjacent_value_only": True,
        "parent_row_key_url_path_and_page_surface_binding_required": True,
        "source_field_quote_and_verbatim_value_sealed": True,
        "same_grammar_applies_independently_to_any_caller_supplied_bound_pages": True,
        "synonym_ontology_host_task_or_model_alias_absent": True,
        "conflict_ambiguity_unknown_surface_only_list_collapse_or_shape_change_fails_closed": True,
        row_bound.CONTENT_FREE_FLAG: False,
        row_bound.PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_registry_receipt(value)


def validate_registry_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "all_v25471_candidates_preserved",
        "complete_visible_field_tokens_required",
        "exact_one_token_or_short_fused_qualifier_only",
        "two_cell_pipe_same_line_labelled_or_bounded_adjacent_value_only",
        "parent_row_key_url_path_and_page_surface_binding_required",
        "source_field_quote_and_verbatim_value_sealed",
        "same_grammar_applies_independently_to_any_caller_supplied_bound_pages",
        "synonym_ontology_host_task_or_model_alias_absent",
        "conflict_ambiguity_unknown_surface_only_list_collapse_or_shape_change_fails_closed",
    )
    false_flags = (
        row_bound.CONTENT_FREE_FLAG,
        row_bound.PRIVILEGED_READ_FLAG,
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != REGISTRY_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _COUNT_FIELDS
        )
        or copied["available_candidate_count"] > MAXIMUM_CANDIDATES
        or copied["applied_coordinate_count"] != copied["available_candidate_count"]
        or copied["generic_mechanical_observation_count"]
        > copied["generic_mechanical_field_surface_count"]
        or copied["positive_signed_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.99 registry receipt drifted")
    return copied


def build_candidate_registry(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    required, rows = source._canonical_table(str(base_prediction), columns)
    parent_registry = parent.build_candidate_registry(
        str(base_prediction), columns=required, pages=pages
    )
    parent_receipt = parent.validate_registry_receipt(
        parent_registry["content_free_receipt"]
    )
    counts = Counter(
        {name: int(parent_receipt.get(name, 0)) for name in parent._COUNT_FIELDS}
    )
    observations = _parent_observations(parent_registry, rows, required)
    observations.extend(
        _generic_observations(
            rows, pages, columns=required, counts=counts
        )
    )
    dedup: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in observations:
        key = (
            item["page_ordinal"],
            item["quote_start"],
            item["quote_end"],
            item["row_index"],
            item["column_index"],
            source._key(item["exact_value"]),
        )
        if key in dedup:
            counts["exact_duplicate_observation_count"] += 1
        else:
            dedup[key] = item
    grouped: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for item in dedup.values():
        grouped[(item["row_index"], item["column_index"])].append(item)
    counts["coordinate_group_count"] = len(grouped)
    retained: list[dict[str, Any]] = []
    for coordinate in sorted(grouped):
        items = grouped[coordinate]
        normalized = {source._key(item["exact_value"]) for item in items}
        if len(items) != 1:
            counts[
                "conflicting_value_coordinate_count"
                if len(normalized) > 1
                else "ambiguous_same_value_coordinate_count"
            ] += 1
            continue
        item = items[0]
        if source._key(item["old_value"]) == source._key(item["exact_value"]):
            counts["unchanged_coordinate_count"] += 1
            continue
        if row_bound._surface_equivalent(
            item["field"], item["old_value"], item["exact_value"]
        ):
            counts["surface_equivalent_rejected_coordinate_count"] += 1
            continue
        if (
            source._column_key(item["field"]) in source.LIST_COLUMN_KEYS
            and source._list_cardinality(item["old_value"]) >= 2
            and source._list_cardinality(item["exact_value"])
            < source._list_cardinality(item["old_value"])
        ):
            counts["list_collapse_rejected_coordinate_count"] += 1
            continue
        retained.append(item)
    retained.sort(
        key=lambda item: (
            item["row_index"],
            item["column_index"],
            item["page_ordinal"],
            item["quote_start"],
        )
    )
    if len(retained) > MAXIMUM_CANDIDATES:
        counts["truncated_unique_candidate_count"] = (
            len(retained) - MAXIMUM_CANDIDATES
        )
        retained = retained[:MAXIMUM_CANDIDATES]
    candidates = [
        _candidate(item, f"C{index:03d}")
        for index, item in enumerate(retained, 1)
    ]
    counts["available_candidate_count"] = len(candidates)
    counts["applied_coordinate_count"] = len(candidates)
    counts["positive_signed_credit_count"] = 0
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_ROLE,
        "policy_id": POLICY_ID,
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode()
        ).hexdigest(),
        "columns": list(required),
        "candidates": candidates,
        "content_free_receipt": _registry_receipt(counts),
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_registry(value)


def validate_registry(
    value: Mapping[str, Any],
    *,
    base_prediction: str | None = None,
    columns: Sequence[str] | None = None,
    pages: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    candidates = copied.get("candidates")
    receipt = copied.get("content_free_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "base_prediction_sha256",
            "columns",
            "candidates",
            "content_free_receipt",
            "artifact_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != REGISTRY_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("columns"), list)
        or not copied["columns"]
        or not isinstance(candidates, list)
        or len(candidates) > MAXIMUM_CANDIDATES
        or [validate_candidate(item) for item in candidates] != candidates
        or [item["candidate_id"] for item in candidates]
        != [f"C{index:03d}" for index in range(1, len(candidates) + 1)]
        or not isinstance(receipt, Mapping)
        or validate_registry_receipt(receipt) != dict(receipt)
        or receipt["available_candidate_count"] != len(candidates)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.99 registry drifted")
    if base_prediction is not None:
        if columns is None or pages is None:
            raise ValueError("V2.54.99 registry replay inputs incomplete")
        replay = build_candidate_registry(
            str(base_prediction), columns=columns, pages=pages
        )
        if replay != copied:
            raise ValueError("V2.54.99 registry replay drifted")
    return copied


def build_application(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    registry = build_candidate_registry(
        base_prediction, columns=columns, pages=pages
    )
    required, rows = source._canonical_table(str(base_prediction), columns)
    row_map = {source._key(row[0]): index for index, row in enumerate(rows)}
    column_map = {source._key(field): index for index, field in enumerate(required)}
    edited = [list(row) for row in rows]
    for item in registry["candidates"]:
        row_index = row_map[source._key(item["row_identity"])]
        column_index = column_map[source._key(item["field"])]
        edited[row_index][column_index] = item["exact_value"]
    candidate_prediction = source.table_parent._render_table(required, edited)
    count = len(registry["candidates"])
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": APPLICATION_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "available_candidate_count": count,
        "selected_candidate_count": count,
        "applied_coordinate_count": count,
        "positive_signed_credit_count": 0,
        "candidate_prediction_changed": bool(count),
        "candidate_identity_handoff": not count,
        "all_candidates_applied_deterministically": True,
        "zero_candidate_preserves_parent_byte_exact": True,
        "schema_row_count_order_keys_and_other_cells_preserved": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": APPLICATION_ROLE,
        "policy_id": POLICY_ID,
        "control_prediction": str(base_prediction),
        "candidate_prediction": candidate_prediction,
        "control_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode()
        ).hexdigest(),
        "candidate_prediction_sha256": hashlib.sha256(
            candidate_prediction.encode()
        ).hexdigest(),
        "private_candidate_registry": registry,
        "content_free_receipt": receipt,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_application(value)


def validate_application(
    value: Mapping[str, Any],
    *,
    base_prediction: str | None = None,
    columns: Sequence[str] | None = None,
    pages: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    registry = copied.get("private_candidate_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("V2.54.99 application registry absent")
    checked = validate_registry(registry)
    count = len(checked["candidates"])
    control = copied.get("control_prediction")
    candidate = copied.get("candidate_prediction")
    expected_receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": APPLICATION_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "available_candidate_count": count,
        "selected_candidate_count": count,
        "applied_coordinate_count": count,
        "positive_signed_credit_count": 0,
        "candidate_prediction_changed": bool(count),
        "candidate_identity_handoff": not count,
        "all_candidates_applied_deterministically": True,
        "zero_candidate_preserves_parent_byte_exact": True,
        "schema_row_count_order_keys_and_other_cells_preserved": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    expected_receipt["receipt_payload_sha256"] = payload_sha256(expected_receipt)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "control_prediction",
            "candidate_prediction",
            "control_prediction_sha256",
            "candidate_prediction_sha256",
            "private_candidate_registry",
            "content_free_receipt",
            "artifact_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != APPLICATION_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(control, str)
        or not isinstance(candidate, str)
        or copied.get("control_prediction_sha256")
        != hashlib.sha256(control.encode()).hexdigest()
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(candidate.encode()).hexdigest()
        or copied.get("content_free_receipt") != expected_receipt
        or (count == 0 and candidate != control)
        or (count > 0 and candidate == control)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.99 application drifted")
    if base_prediction is not None:
        if columns is None or pages is None:
            raise ValueError("V2.54.99 application replay inputs incomplete")
        replay = build_application(
            str(base_prediction), columns=columns, pages=pages
        )
        if replay != copied:
            raise ValueError("V2.54.99 application replay drifted")
    return copied


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "complete_visible_field_tokens_required": True,
        "supported_label_grammars": [
            "exact",
            "separate_qualifier",
            "fused_qualifier",
        ],
        "supported_new_source_shapes": [
            "fused_two_cell_pipe",
            "qualified_same_line_labelled",
            "standalone_label_bounded_adjacent_value",
        ],
        "same_candidate_applies_to_parent_or_detail_pages": True,
        "additional_provider_effects": 0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "APPLICATION_RECEIPT_ROLE",
    "APPLICATION_ROLE",
    "PAGE_KEYS",
    "POLICY_ID",
    "REGISTRY_RECEIPT_ROLE",
    "REGISTRY_ROLE",
    "build_application",
    "build_candidate_registry",
    "integration_contract",
    "validate_application",
    "validate_candidate",
    "validate_registry",
    "validate_registry_receipt",
]
