"""Key-anchored bounded metadata candidates over V2.54.32.

V2.54.39 found that first-party RFC metadata pages were already reachable,
but the parent parser stopped at the first non-target ``label: value`` line.
This pure successor keeps all V2.54.32 candidates and adds one conservative
surface: a block anchored by the exact visible key-column label, bounded by
the first non-labelled line and sixteen lines total.  Non-target labels may
occur inside the block but are never interpreted or aliased.

When a raw key value is not itself a row identity, the exact key label and
raw value may be joined with one space only if that result uniquely names an
existing base row.  For exact list fields, a raw source value may be split on
two or more ASCII spaces and rendered with ``; `` only when there are at least
two unique atoms and their count exactly equals the base cell's list
cardinality.  The original source span and raw value remain sealed, and the
normalized value is replay-derived rather than model-authored.

No singular/plural, status/category, title/heading, prose, host, task, or
domain alias is permitted.  Conflicts, repeated source coordinates, missing
rows, unsafe atoms, list collapse, and shape/key changes fail closed.  The
module has no file, environment, process, network, model, search, fetch,
evaluator, benchmark-label, mapping, gold, score, reward, credential, or
historical-result capability.  Entropy/information gain assigns no signed
credit and this build grants no launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25432_source_authoritative_field_candidate as parent


POLICY_ID = "v25440_key_anchored_metadata_candidate_v1"
REGISTRY_ROLE = "v25440_key_anchored_metadata_candidate_registry"
REGISTRY_RECEIPT_ROLE = "v25440_content_free_metadata_candidate_registry_receipt"
APPLICATION_ROLE = "v25440_key_anchored_metadata_candidate_application"
APPLICATION_RECEIPT_ROLE = (
    "v25440_content_free_metadata_candidate_application_receipt"
)

PAGE_KEYS = parent.PAGE_KEYS
MAXIMUM_BLOCK_LINES = 16
MAXIMUM_CANDIDATES = parent.MAXIMUM_CANDIDATES
MAXIMUM_SELECTOR_IDS = parent.MAXIMUM_SELECTOR_IDS
_SELECTOR_ID = re.compile(r"C[0-9]{3}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MULTI_ASCII_SPACE = re.compile(r" {2,}")
_MISSING = object()
_SOURCE_KINDS = frozenset(
    {*parent._SOURCE_KINDS, "key_anchored_bounded_metadata_record"}
)
_IDENTITY_KINDS = frozenset(
    {"exact_visible_identity", "exact_key_label_qualification"}
)
_VALUE_KINDS = frozenset(
    {"identity", "ascii_multi_space_list_atomic"}
)
CONTENT_FREE_FLAG = parent.CONTENT_FREE_FLAG
PRIVILEGED_READ_FLAG = parent.PRIVILEGED_READ_FLAG

_CANDIDATE_KEYS = frozenset(
    {
        "candidate_id",
        "page_ordinal",
        "source_url",
        "source_host",
        "quote_start",
        "quote_end",
        "exact_quote",
        "raw_source_identity",
        "source_identity_label",
        "identity_derivation_kind",
        "source_identity",
        "row_identity",
        "source_field",
        "field",
        "raw_source_value",
        "value_normalization_kind",
        "old_value",
        "exact_value",
        "source_kind",
        "source_coordinate_is_unique",
        "target_table_coordinate_is_unique",
        "value_is_source_extracted_not_model_generated",
        "nonunknown_and_materially_differs_from_base",
        "list_cardinality_noncollapse",
        "candidate_payload_sha256",
    }
)

_COUNT_FIELDS = (
    "input_page_count",
    "accepted_page_count",
    "rejected_page_count",
    "accepted_page_character_count",
    "parent_candidate_count",
    "metadata_block_count",
    "metadata_identity_exact_count",
    "metadata_identity_qualified_count",
    "metadata_identity_rejected_count",
    "metadata_duplicate_visible_field_rejected_count",
    "metadata_exact_field_attempt_count",
    "metadata_value_normalized_count",
    "metadata_value_rejected_count",
    "raw_observation_count",
    "evidence_closed_observation_count",
    "exact_duplicate_observation_count",
    "coordinate_group_count",
    "ambiguous_same_value_coordinate_count",
    "conflicting_value_coordinate_count",
    "unchanged_coordinate_count",
    "list_collapse_rejected_coordinate_count",
    "truncated_unique_candidate_count",
    "available_candidate_count",
    "positive_signed_credit_count",
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_calls",
    "additional_fetch_calls",
    "additional_provider_tokens",
)


payload_sha256 = parent.payload_sha256


def _strict_label(line: str) -> tuple[str, str] | None:
    raw = str(line).strip()
    raw = re.sub(r"^(?:[-*]\s+)", "", raw)
    match = re.fullmatch(r"([^:=：\t]{1,120})\s*[:=：\t]\s*(.+?)\s*", raw)
    if match is None:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _identity_binding(
    label: str,
    raw_value: str,
    *,
    rows: Sequence[Sequence[str]],
    row_map: Mapping[str, list[int]],
) -> tuple[int, str, str] | None:
    exact = row_map.get(parent._key(raw_value), [])
    qualified_surface = parent._surface(f"{label} {raw_value}")
    qualified = row_map.get(parent._key(qualified_surface), [])
    matches: list[tuple[int, str]] = []
    if len(exact) == 1:
        matches.append((exact[0], "exact_visible_identity"))
    if len(qualified) == 1 and (
        not matches or qualified[0] != matches[0][0]
    ):
        matches.append((qualified[0], "exact_key_label_qualification"))
    if len(matches) != 1:
        return None
    row_index, kind = matches[0]
    return row_index, str(rows[row_index][0]), kind


def _atomic_value(
    raw_value: str,
    *,
    field: str,
    old_value: str,
) -> tuple[str, str] | None:
    exact = parent._safe_cell(raw_value)
    if exact is not None:
        if (
            parent._column_key(field) in parent.LIST_COLUMN_KEYS
            and parent._list_cardinality(exact)
            != parent._list_cardinality(old_value)
        ):
            return None
        return exact, "identity"
    if parent._column_key(field) not in parent.LIST_COLUMN_KEYS:
        return None
    if not _MULTI_ASCII_SPACE.search(raw_value):
        return None
    if any(character.isspace() and character != " " for character in raw_value):
        return None
    atoms = [part.strip() for part in _MULTI_ASCII_SPACE.split(raw_value)]
    if (
        len(atoms) < 2
        or any(not atom or parent._safe_cell(atom) != atom for atom in atoms)
        or len({parent._key(atom) for atom in atoms}) != len(atoms)
        or len(atoms) != parent._list_cardinality(old_value)
    ):
        return None
    normalized = "; ".join(atoms)
    if parent._safe_cell(normalized) != normalized:
        return None
    return normalized, "ascii_multi_space_list_atomic"


def _parent_observations(
    registry: Mapping[str, Any],
    *,
    rows: Sequence[Sequence[str]],
    columns: Sequence[str],
) -> list[dict[str, Any]]:
    row_index = {parent._key(row[0]): index for index, row in enumerate(rows)}
    field_index = {parent._key(field): index for index, field in enumerate(columns)}
    output: list[dict[str, Any]] = []
    checked = parent.validate_registry(registry)
    for candidate in checked["candidates"]:
        row = row_index.get(parent._key(candidate["row_identity"]))
        field = field_index.get(parent._key(candidate["field"]))
        if row is None or field in {None, 0}:
            raise RuntimeError("V2.54.40 parent candidate target drifted")
        output.append(
            {
                "page_ordinal": candidate["page_ordinal"],
                "source_url": candidate["source_url"],
                "source_host": candidate["source_host"],
                "quote_start": candidate["quote_start"],
                "quote_end": candidate["quote_end"],
                "exact_quote": candidate["exact_quote"],
                "raw_source_identity": candidate["source_identity"],
                "source_identity_label": None,
                "identity_derivation_kind": "exact_visible_identity",
                "source_identity": candidate["source_identity"],
                "row_identity": candidate["row_identity"],
                "source_field": candidate["source_field"],
                "field": candidate["field"],
                "raw_source_value": candidate["exact_value"],
                "value_normalization_kind": "identity",
                "old_value": candidate["old_value"],
                "exact_value": candidate["exact_value"],
                "source_kind": candidate["source_kind"],
                "row_index": row,
                "column_index": field,
            }
        )
    return output


def _metadata_observations(
    pages: Sequence[Mapping[str, Any]],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    row_map: Mapping[str, list[int]],
    column_map: Mapping[str, list[int]],
    counts: Counter[str],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for page in pages:
        content = str(page["content"])
        lines = parent._line_spans(content)
        index = 0
        while index < len(lines):
            key = parent._label_pair(lines[index][2], columns, column_map)
            if key is None or key[0] != 0:
                index += 1
                continue
            cursor = index
            block: list[tuple[int, int, str, str]] = []
            while cursor < len(lines) and cursor - index < MAXIMUM_BLOCK_LINES:
                pair = _strict_label(lines[cursor][2])
                if pair is None:
                    break
                block.append(
                    (lines[cursor][0], lines[cursor][1], pair[0], pair[1])
                )
                cursor += 1
            if not block:
                index += 1
                continue
            counts["metadata_block_count"] += 1
            recognized_indices: list[int] = []
            for _start, _end, source_field, _raw_value in block:
                matches = column_map.get(parent._key(source_field), [])
                if len(matches) == 1:
                    recognized_indices.append(matches[0])
            if len(recognized_indices) != len(set(recognized_indices)):
                counts["metadata_identity_rejected_count"] += 1
                counts["metadata_duplicate_visible_field_rejected_count"] += 1
                index = max(index + 1, cursor)
                continue
            binding = _identity_binding(
                key[1], key[2], rows=rows, row_map=row_map
            )
            if binding is None:
                counts["metadata_identity_rejected_count"] += 1
                index = max(index + 1, cursor)
                continue
            row_index, source_identity, identity_kind = binding
            counts[
                "metadata_identity_exact_count"
                if identity_kind == "exact_visible_identity"
                else "metadata_identity_qualified_count"
            ] += 1
            quote_start = lines[index][0]
            quote_end = lines[cursor - 1][1]
            quote = content[quote_start:quote_end]
            for _start, _end, source_field, raw_value in block:
                matches = column_map.get(parent._key(source_field), [])
                if len(matches) != 1 or matches[0] == 0:
                    continue
                column_index = matches[0]
                field = str(columns[column_index])
                counts["metadata_exact_field_attempt_count"] += 1
                normalized = _atomic_value(
                    raw_value,
                    field=field,
                    old_value=str(rows[row_index][column_index]),
                )
                if normalized is None:
                    counts["metadata_value_rejected_count"] += 1
                    continue
                exact_value, normalization_kind = normalized
                counts["metadata_value_normalized_count"] += int(
                    normalization_kind != "identity"
                )
                counts["raw_observation_count"] += 1
                if (
                    not 1 <= len(quote) <= parent.MAXIMUM_QUOTE_CHARACTERS
                    or content.count(quote) != 1
                    or any(
                        needle not in quote
                        for needle in (
                            key[1],
                            key[2],
                            source_field,
                            raw_value,
                        )
                    )
                ):
                    continue
                output.append(
                    {
                        "page_ordinal": int(page["page_ordinal"]),
                        "source_url": str(page["source_url"]),
                        "source_host": str(page["source_host"]),
                        "quote_start": quote_start,
                        "quote_end": quote_end,
                        "exact_quote": quote,
                        "raw_source_identity": key[2],
                        "source_identity_label": key[1],
                        "identity_derivation_kind": identity_kind,
                        "source_identity": source_identity,
                        "row_identity": str(rows[row_index][0]),
                        "source_field": source_field,
                        "field": field,
                        "raw_source_value": raw_value,
                        "value_normalization_kind": normalization_kind,
                        "old_value": str(rows[row_index][column_index]),
                        "exact_value": exact_value,
                        "source_kind": "key_anchored_bounded_metadata_record",
                        "row_index": row_index,
                        "column_index": column_index,
                    }
                )
                counts["evidence_closed_observation_count"] += 1
            index = max(index + 1, cursor)
    return output


def _observation_key(value: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(value["page_ordinal"]),
        int(value["quote_start"]),
        int(value["quote_end"]),
        int(value["row_index"]),
        int(value["column_index"]),
        parent._key(value["exact_value"]),
    )


def _candidate(observation: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    value: dict[str, Any] = {
        "candidate_id": candidate_id,
        **{
            name: copy.deepcopy(observation[name])
            for name in _CANDIDATE_KEYS
            if name
            not in {
                "candidate_id",
                "source_coordinate_is_unique",
                "target_table_coordinate_is_unique",
                "value_is_source_extracted_not_model_generated",
                "nonunknown_and_materially_differs_from_base",
                "list_cardinality_noncollapse",
                "candidate_payload_sha256",
            }
        },
        "source_coordinate_is_unique": True,
        "target_table_coordinate_is_unique": True,
        "value_is_source_extracted_not_model_generated": True,
        "nonunknown_and_materially_differs_from_base": True,
        "list_cardinality_noncollapse": True,
    }
    value["candidate_payload_sha256"] = payload_sha256(value)
    return validate_candidate(value)


def _derived_identity(value: Mapping[str, Any]) -> str | None:
    kind = value.get("identity_derivation_kind")
    raw = value.get("raw_source_identity")
    label = value.get("source_identity_label")
    if not isinstance(raw, str) or not raw:
        return None
    if kind == "exact_visible_identity" and (
        label is None or isinstance(label, str) and label
    ):
        return raw
    if (
        kind == "exact_key_label_qualification"
        and isinstance(label, str)
        and label
    ):
        return parent._surface(f"{label} {raw}")
    return None


def _derived_value(value: Mapping[str, Any]) -> str | None:
    raw = value.get("raw_source_value")
    kind = value.get("value_normalization_kind")
    if not isinstance(raw, str) or not raw:
        return None
    if kind == "identity":
        return raw if parent._safe_cell(raw) == raw else None
    if kind == "ascii_multi_space_list_atomic":
        field = value.get("field")
        old = value.get("old_value")
        if not isinstance(field, str) or not isinstance(old, str):
            return None
        normalized = _atomic_value(raw, field=field, old_value=old)
        if normalized is None or normalized[1] != kind:
            return None
        return normalized[0]
    return None


def _metadata_quote_is_exactly_bound(value: Mapping[str, Any]) -> bool:
    quote = value.get("exact_quote")
    identity_label = value.get("source_identity_label")
    raw_identity = value.get("raw_source_identity")
    source_field = value.get("source_field")
    raw_value = value.get("raw_source_value")
    if not all(
        isinstance(item, str) and item
        for item in (
            quote,
            identity_label,
            raw_identity,
            source_field,
            raw_value,
        )
    ):
        return False
    pairs = [_strict_label(line) for line in quote.splitlines()]
    return bool(
        1 <= len(pairs) <= MAXIMUM_BLOCK_LINES
        and all(pair is not None for pair in pairs)
        and pairs[0] == (identity_label, raw_identity)
        and sum(pair == (source_field, raw_value) for pair in pairs) == 1
    )


def validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("candidate_payload_sha256", None)
    quote = copied.get("exact_quote")
    source_identity = copied.get("source_identity")
    row_identity = copied.get("row_identity")
    raw_identity = copied.get("raw_source_identity")
    source_field = copied.get("source_field")
    raw_value = copied.get("raw_source_value")
    field = copied.get("field")
    old = copied.get("old_value")
    exact = copied.get("exact_value")
    derived_identity = _derived_identity(copied)
    derived_value = _derived_value(copied)
    canonical = parent._canonical_url(copied.get("source_url"))
    identity_label = copied.get("source_identity_label")
    source_kind = copied.get("source_kind")
    identity_kind = copied.get("identity_derivation_kind")
    normalization_kind = copied.get("value_normalization_kind")
    if (
        set(copied) != _CANDIDATE_KEYS
        or _SELECTOR_ID.fullmatch(str(copied.get("candidate_id", ""))) is None
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
        or not isinstance(quote, str)
        or len(quote) != copied["quote_end"] - copied["quote_start"]
        or not 1 <= len(quote) <= parent.MAXIMUM_QUOTE_CHARACTERS
        or not all(
            isinstance(item, str)
            and item
            and "\x00" not in item
            and "\r" not in item
            and "\n" not in item
            for item in (
                raw_identity,
                source_identity,
                row_identity,
                source_field,
                field,
                raw_value,
                old,
                exact,
            )
        )
        or (
            identity_label is not None
            and (
                not isinstance(identity_label, str)
                or not identity_label
                or any(character in identity_label for character in "\x00\r\n")
            )
        )
        or identity_kind not in _IDENTITY_KINDS
        or normalization_kind not in _VALUE_KINDS
        or source_kind not in _SOURCE_KINDS
        or parent._key(source_field) != parent._key(field)
        or (
            source_kind == "key_anchored_bounded_metadata_record"
            and (
                identity_label is None
                or not _metadata_quote_is_exactly_bound(copied)
            )
        )
        or (
            source_kind != "key_anchored_bounded_metadata_record"
            and (
                identity_label is not None
                or identity_kind != "exact_visible_identity"
                or normalization_kind != "identity"
            )
        )
        or (
            identity_kind == "exact_key_label_qualification"
            and source_kind != "key_anchored_bounded_metadata_record"
        )
        or (
            normalization_kind == "ascii_multi_space_list_atomic"
            and source_kind != "key_anchored_bounded_metadata_record"
        )
        or derived_identity is None
        or parent._key(derived_identity) != parent._key(source_identity)
        or parent._key(source_identity) != parent._key(row_identity)
        or derived_value != exact
        or parent._key(old) == parent._key(exact)
        or any(item not in quote for item in (raw_identity, source_field, raw_value))
        or (
            copied.get("source_identity_label") is not None
            and copied["source_identity_label"] not in quote
        )
        or copied.get("source_coordinate_is_unique") is not True
        or copied.get("target_table_coordinate_is_unique") is not True
        or copied.get("value_is_source_extracted_not_model_generated") is not True
        or copied.get("nonunknown_and_materially_differs_from_base") is not True
        or copied.get("list_cardinality_noncollapse") is not True
        or (
            parent._column_key(field) in parent.LIST_COLUMN_KEYS
            and parent._list_cardinality(old) >= 2
            and parent._list_cardinality(exact) < parent._list_cardinality(old)
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.40 candidate drifted")
    return copied


def _registry_receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "parent_and_metadata_candidates_share_one_conflict_resolution": True,
        "key_anchor_must_be_exact_visible_key_column_label": True,
        "non_target_metadata_labels_skipped_not_interpreted": True,
        "identity_qualification_requires_unique_existing_base_row": True,
        "list_normalization_requires_exact_field_unique_atoms_and_equal_cardinality": True,
        "raw_source_span_and_value_preserved_before_normalization": True,
        "model_may_only_select_candidate_ids_or_abstain": True,
        "singular_plural_status_category_title_heading_or_prose_alias_used": False,
        CONTENT_FREE_FLAG: False,
        PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_registry_receipt(value)


def _build_registry(
    base_prediction: str,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    required, rows = parent._canonical_table(str(base_prediction), columns)
    bounded, page_counts = parent._pages(pages)
    parent_registry = parent.build_candidate_registry(
        base_prediction, columns=required, pages=pages
    )
    row_map: defaultdict[str, list[int]] = defaultdict(list)
    column_map: defaultdict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        row_map[parent._key(row[0])].append(index)
    for index, field in enumerate(required):
        column_map[parent._key(field)].append(index)
    counts: Counter[str] = Counter(page_counts)
    counts["parent_candidate_count"] = len(parent_registry["candidates"])
    observations = _parent_observations(
        parent_registry, rows=rows, columns=required
    )
    observations.extend(
        _metadata_observations(
            bounded,
            columns=required,
            rows=rows,
            row_map=row_map,
            column_map=column_map,
            counts=counts,
        )
    )
    deduplicated: dict[tuple[Any, ...], dict[str, Any]] = {}
    for observation in observations:
        key = _observation_key(observation)
        if key in deduplicated:
            counts["exact_duplicate_observation_count"] += 1
        else:
            deduplicated[key] = observation
    grouped: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for observation in deduplicated.values():
        grouped[(observation["row_index"], observation["column_index"])].append(
            observation
        )
    counts["coordinate_group_count"] = len(grouped)
    retained: list[dict[str, Any]] = []
    for coordinate in sorted(grouped):
        values = grouped[coordinate]
        exact_values = {parent._key(item["exact_value"]) for item in values}
        if len(values) != 1:
            counts[
                "conflicting_value_coordinate_count"
                if len(exact_values) > 1
                else "ambiguous_same_value_coordinate_count"
            ] += 1
            continue
        item = values[0]
        if parent._key(item["old_value"]) == parent._key(item["exact_value"]):
            counts["unchanged_coordinate_count"] += 1
            continue
        if (
            parent._column_key(item["field"]) in parent.LIST_COLUMN_KEYS
            and parent._list_cardinality(item["old_value"]) >= 2
            and parent._list_cardinality(item["exact_value"])
            < parent._list_cardinality(item["old_value"])
        ):
            counts["list_collapse_rejected_coordinate_count"] += 1
            continue
        retained.append(item)
    retained.sort(
        key=lambda item: (
            int(item["row_index"]),
            int(item["column_index"]),
            int(item["page_ordinal"]),
            int(item["quote_start"]),
        )
    )
    counts["truncated_unique_candidate_count"] = max(
        0, len(retained) - MAXIMUM_CANDIDATES
    )
    retained = retained[:MAXIMUM_CANDIDATES]
    candidates = [
        _candidate(item, f"C{index:03d}") for index, item in enumerate(retained, 1)
    ]
    counts["available_candidate_count"] = len(candidates)
    for name in _COUNT_FIELDS[-6:]:
        counts[name] = 0
    counts["available_candidate_count"] = len(candidates)
    receipt = _registry_receipt(counts)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_ROLE,
        "policy_id": POLICY_ID,
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode("utf-8")
        ).hexdigest(),
        "page_vector_sha256": parent_registry["page_vector_sha256"],
        "parent_registry_payload_sha256": parent_registry["artifact_payload_sha256"],
        "candidates": candidates,
        "content_free_receipt": receipt,
        PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return value


def build_candidate_registry(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    value = _build_registry(base_prediction, columns, pages)
    return validate_registry(
        value, base_prediction=base_prediction, columns=columns, pages=pages
    )


def validate_registry_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "parent_and_metadata_candidates_share_one_conflict_resolution",
        "key_anchor_must_be_exact_visible_key_column_label",
        "non_target_metadata_labels_skipped_not_interpreted",
        "identity_qualification_requires_unique_existing_base_row",
        "list_normalization_requires_exact_field_unique_atoms_and_equal_cardinality",
        "raw_source_span_and_value_preserved_before_normalization",
        "model_may_only_select_candidate_ids_or_abstain",
    )
    false_flags = (
        "singular_plural_status_category_title_heading_or_prose_alias_used",
        CONTENT_FREE_FLAG,
        PRIVILEGED_READ_FLAG,
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
        or copied["accepted_page_count"] + copied["rejected_page_count"]
        != copied["input_page_count"]
        or copied["metadata_identity_exact_count"]
        + copied["metadata_identity_qualified_count"]
        + copied["metadata_identity_rejected_count"]
        != copied["metadata_block_count"]
        or copied["metadata_duplicate_visible_field_rejected_count"]
        > copied["metadata_identity_rejected_count"]
        or copied["metadata_value_normalized_count"]
        + copied["metadata_value_rejected_count"]
        > copied["metadata_exact_field_attempt_count"]
        or copied["available_candidate_count"] > MAXIMUM_CANDIDATES
        or copied["positive_signed_credit_count"] != 0
        or any(copied[name] != 0 for name in _COUNT_FIELDS[-5:])
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.40 registry receipt drifted")
    return copied


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
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "base_prediction_sha256",
        "page_vector_sha256",
        "parent_registry_payload_sha256",
        "candidates",
        "content_free_receipt",
        PRIVILEGED_READ_FLAG,
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "artifact_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != REGISTRY_ROLE
        or copied.get("policy_id") != POLICY_ID
        or _SHA256.fullmatch(str(copied.get("base_prediction_sha256", "")))
        is None
        or _SHA256.fullmatch(str(copied.get("page_vector_sha256", ""))) is None
        or _SHA256.fullmatch(
            str(copied.get("parent_registry_payload_sha256", ""))
        )
        is None
        or not isinstance(candidates, list)
        or len(candidates) > MAXIMUM_CANDIDATES
        or not isinstance(receipt, Mapping)
        or validate_registry_receipt(receipt) != dict(receipt)
        or receipt["available_candidate_count"] != len(candidates)
        or any(
            not isinstance(candidate, Mapping)
            or validate_candidate(candidate) != dict(candidate)
            or candidate["candidate_id"] != f"C{index:03d}"
            for index, candidate in enumerate(candidates, 1)
        )
        or len(
            {
                (parent._key(item["row_identity"]), parent._key(item["field"]))
                for item in candidates
            }
        )
        != len(candidates)
        or any(
            copied.get(name) is not False
            for name in (
                PRIVILEGED_READ_FLAG,
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.40 registry drifted")
    supplied = (base_prediction is not None, columns is not None, pages is not None)
    if any(supplied) and not all(supplied):
        raise ValueError("V2.54.40 replay inputs must be supplied together")
    if all(supplied):
        assert base_prediction is not None and columns is not None and pages is not None
        if _build_registry(base_prediction, columns, pages) != copied:
            raise ValueError("V2.54.40 registry replay drifted")
    return copied


def _selector(value: object) -> tuple[bool, list[str]]:
    if not isinstance(value, str):
        return False, []
    parsed = parent._strict_json_object(value)
    if parsed is None or set(parsed) != {"candidate_ids"}:
        return False, []
    ids = parsed.get("candidate_ids")
    if (
        not isinstance(ids, list)
        or len(ids) > MAXIMUM_SELECTOR_IDS
        or any(not isinstance(item, str) or _SELECTOR_ID.fullmatch(item) is None for item in ids)
        or len(set(ids)) != len(ids)
    ):
        return False, []
    return True, list(ids)


def _application_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": APPLICATION_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "available_candidate_count": int(value["available_candidate_count"]),
        "requested_candidate_count": int(value["requested_candidate_count"]),
        "selected_candidate_count": int(value["selected_candidate_count"]),
        "applied_coordinate_count": int(value["applied_coordinate_count"]),
        "positive_signed_credit_count": 0,
        "selector_output_present": bool(value["selector_output_present"]),
        "selector_strictly_valid": bool(value["selector_strictly_valid"]),
        "all_selected_candidate_ids_known": bool(
            value["all_selected_candidate_ids_known"]
        ),
        "candidate_prediction_changed": bool(value["candidate_prediction_changed"]),
        "candidate_identity_handoff": bool(value["candidate_identity_handoff"]),
        "selected_values_and_normalizations_replayed_from_registry": True,
        "schema_row_count_order_keys_and_unselected_cells_preserved": True,
        "selection_interface_accepts_only_candidate_ids_or_abstain": True,
        "zero_additional_model_search_fetch_query_token_context_wall_or_network_effect": True,
        CONTENT_FREE_FLAG: False,
        PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_application_receipt(output)


def _apply_candidate_selection(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
    selector_output: object,
) -> dict[str, Any]:
    required, rows = parent._canonical_table(str(base_prediction), columns)
    registry = build_candidate_registry(
        base_prediction, columns=required, pages=pages
    )
    valid, requested = _selector(selector_output)
    by_id = {item["candidate_id"]: item for item in registry["candidates"]}
    known = bool(valid and all(name in by_id for name in requested))
    selected = [by_id[name] for name in requested] if known else []
    if len(
        {(parent._key(item["row_identity"]), parent._key(item["field"])) for item in selected}
    ) != len(selected):
        selected = []
        known = False
    selected_ids = [item["candidate_id"] for item in selected]
    candidate = str(base_prediction)
    if selected:
        row_index = {parent._key(row[0]): index for index, row in enumerate(rows)}
        field_index = {
            parent._key(field): index for index, field in enumerate(required)
        }
        edited = copy.deepcopy(rows)
        coordinates: set[tuple[int, int]] = set()
        for item in selected:
            coordinate = (
                row_index[parent._key(item["row_identity"])],
                field_index[parent._key(item["field"])],
            )
            if (
                coordinate[1] == 0
                or coordinate in coordinates
                or edited[coordinate[0]][coordinate[1]] != item["old_value"]
            ):
                raise RuntimeError("V2.54.40 selected coordinate drifted")
            coordinates.add(coordinate)
            edited[coordinate[0]][coordinate[1]] = item["exact_value"]
        candidate = parent.table_parent._render_table(required, edited)
        reparsed_columns, reparsed_rows = parent._canonical_table(candidate, required)
        if (
            reparsed_columns != required
            or len(reparsed_rows) != len(rows)
            or [row[0] for row in reparsed_rows] != [row[0] for row in rows]
        ):
            raise RuntimeError("V2.54.40 selected table preservation drifted")
        for row_position, (before, after) in enumerate(
            zip(rows, reparsed_rows, strict=True)
        ):
            for field_position, (old, new) in enumerate(
                zip(before, after, strict=True)
            ):
                if (
                    (row_position, field_position) not in coordinates
                    and old != new
                ):
                    raise RuntimeError("V2.54.40 unselected cell drifted")
    changed = candidate != str(base_prediction)
    receipt = _application_receipt(
        {
            "available_candidate_count": len(registry["candidates"]),
            "requested_candidate_count": len(requested),
            "selected_candidate_count": len(selected),
            "applied_coordinate_count": len(selected),
            "selector_output_present": isinstance(selector_output, str),
            "selector_strictly_valid": valid,
            "all_selected_candidate_ids_known": known,
            "candidate_prediction_changed": changed,
            "candidate_identity_handoff": not changed,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": APPLICATION_ROLE,
        "policy_id": POLICY_ID,
        "control_prediction": str(base_prediction),
        "candidate_prediction": candidate,
        "control_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode("utf-8")
        ).hexdigest(),
        "candidate_prediction_sha256": hashlib.sha256(
            candidate.encode("utf-8")
        ).hexdigest(),
        "private_candidate_registry": registry,
        "selected_candidate_ids": selected_ids,
        "content_free_receipt": receipt,
        PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return value


def apply_candidate_selection(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
    selector_output: object,
) -> dict[str, Any]:
    value = _apply_candidate_selection(
        base_prediction,
        columns=columns,
        pages=pages,
        selector_output=selector_output,
    )
    return validate_application(value)


def validate_application_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "available_candidate_count",
        "requested_candidate_count",
        "selected_candidate_count",
        "applied_coordinate_count",
        "positive_signed_credit_count",
    )
    dynamic = (
        "selector_output_present",
        "selector_strictly_valid",
        "all_selected_candidate_ids_known",
        "candidate_prediction_changed",
        "candidate_identity_handoff",
    )
    true_flags = (
        "selected_values_and_normalizations_replayed_from_registry",
        "schema_row_count_order_keys_and_unselected_cells_preserved",
        "selection_interface_accepts_only_candidate_ids_or_abstain",
        "zero_additional_model_search_fetch_query_token_context_wall_or_network_effect",
    )
    false_flags = (
        CONTENT_FREE_FLAG,
        PRIVILEGED_READ_FLAG,
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        *dynamic,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != APPLICATION_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic)
        or copied["requested_candidate_count"] > MAXIMUM_SELECTOR_IDS
        or copied["selected_candidate_count"] > copied["available_candidate_count"]
        or copied["applied_coordinate_count"] != copied["selected_candidate_count"]
        or copied["positive_signed_credit_count"] != 0
        or copied["candidate_prediction_changed"]
        is not (copied["applied_coordinate_count"] > 0)
        or copied["candidate_identity_handoff"]
        is not (not copied["candidate_prediction_changed"])
        or copied["all_selected_candidate_ids_known"]
        and not copied["selector_strictly_valid"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.40 application receipt drifted")
    return copied


def _prediction_matches_selection(
    control: str,
    candidate: str,
    registry: Mapping[str, Any],
    selected_ids: Sequence[str],
) -> bool:
    try:
        columns, rows = parent.table_parent._baseline_matrix(control)
        if parent.table_parent._render_table(columns, rows) != control:
            return False
        by_id = {item["candidate_id"]: item for item in registry["candidates"]}
        chosen = [by_id[name] for name in selected_ids]
        row_index = {parent._key(row[0]): index for index, row in enumerate(rows)}
        field_index = {
            parent._key(field): index for index, field in enumerate(columns)
        }
        edited = copy.deepcopy(rows)
        coordinates: set[tuple[int, int]] = set()
        for item in chosen:
            coordinate = (
                row_index[parent._key(item["row_identity"])],
                field_index[parent._key(item["field"])],
            )
            if (
                coordinate[1] == 0
                or coordinate in coordinates
                or edited[coordinate[0]][coordinate[1]] != item["old_value"]
            ):
                return False
            coordinates.add(coordinate)
            edited[coordinate[0]][coordinate[1]] = item["exact_value"]
        return candidate == parent.table_parent._render_table(columns, edited)
    except (KeyError, TypeError, ValueError):
        return False


def validate_application(
    value: Mapping[str, Any],
    *,
    base_prediction: str | None = None,
    columns: Sequence[str] | None = None,
    pages: Sequence[Mapping[str, Any]] | None = None,
    selector_output: object = _MISSING,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    control = copied.get("control_prediction")
    candidate = copied.get("candidate_prediction")
    registry = copied.get("private_candidate_registry")
    selected = copied.get("selected_candidate_ids")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "control_prediction",
        "candidate_prediction",
        "control_prediction_sha256",
        "candidate_prediction_sha256",
        "private_candidate_registry",
        "selected_candidate_ids",
        "content_free_receipt",
        PRIVILEGED_READ_FLAG,
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "artifact_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != APPLICATION_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(control, str)
        or not isinstance(candidate, str)
        or not isinstance(registry, Mapping)
        or validate_registry(registry) != dict(registry)
        or not isinstance(selected, list)
        or len(selected) != len(set(selected))
        or any(
            not isinstance(item, str) or _SELECTOR_ID.fullmatch(item) is None
            for item in selected
        )
        or not isinstance(receipt, Mapping)
        or validate_application_receipt(receipt) != dict(receipt)
        or copied.get("control_prediction_sha256")
        != hashlib.sha256(control.encode("utf-8")).hexdigest()
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        or receipt["available_candidate_count"]
        != registry["content_free_receipt"]["available_candidate_count"]
        or receipt["selected_candidate_count"] != len(selected)
        or any(
            item not in {entry["candidate_id"] for entry in registry["candidates"]}
            for item in selected
        )
        or receipt["candidate_prediction_changed"] is not (control != candidate)
        or selected
        and not _prediction_matches_selection(control, candidate, registry, selected)
        or not selected
        and candidate != control
        or any(
            copied.get(name) is not False
            for name in (
                PRIVILEGED_READ_FLAG,
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.40 application drifted")
    replay = (
        base_prediction is not None,
        columns is not None,
        pages is not None,
        selector_output is not _MISSING,
    )
    if any(replay) and not all(replay):
        raise ValueError("V2.54.40 application replay inputs are incomplete")
    if all(replay):
        assert base_prediction is not None and columns is not None and pages is not None
        if _apply_candidate_selection(
            base_prediction,
            columns=columns,
            pages=pages,
            selector_output=selector_output,
        ) != copied:
            raise ValueError("V2.54.40 application replay drifted")
    return copied


__all__ = [
    "APPLICATION_RECEIPT_ROLE",
    "APPLICATION_ROLE",
    "PAGE_KEYS",
    "POLICY_ID",
    "REGISTRY_RECEIPT_ROLE",
    "REGISTRY_ROLE",
    "apply_candidate_selection",
    "build_candidate_registry",
    "validate_application",
    "validate_application_receipt",
    "validate_candidate",
    "validate_registry",
    "validate_registry_receipt",
]
