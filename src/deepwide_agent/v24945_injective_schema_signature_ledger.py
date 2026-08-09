"""Injective token-signature schema binding for native fetched-page layouts.

The V2.49.42 compact ledger accepts only exact visible-schema aliases.  Real
HTML table extraction preserves row boundaries but commonly changes a visible
column such as ``Total population [SP.POP.TOTL] @2020`` into the semantically
equivalent header ``Population, total``.  This append-only successor retains
the compact record representation while adding one conservative binding rule:
after bracketed codes and four-digit years are removed, a page label may bind
to a visible column when their multi-token ASCII multisets are identical.

Every binding remains injective.  A repeated page header, a signature shared
by two visible columns, a wrong row width, a cross-page join, or a conflicting
coordinate fails closed.  Single-token and non-ASCII labels still require an
exact alias.  Content-free structural counters are shadow diagnostics only;
they do not alter selection.  Inputs are limited to the visible question and
same-forward fetched pages.  Entropy and information gain remain shadow-only
and never assign signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as structure
from . import v24842_atomic_table_header_closure as atomic
from . import v24928_unicode_total_visible_row_compactor as unicode_total
from . import v24933_contextual_record_value_projector as projector_parent
from . import v24939_schema_bound_record_ledger as ledger_parent
from . import v24942_compact_schema_bound_record_ledger as compact_parent


POLICY_ID = "v24945_injective_token_signature_schema_bound_ledger_v1"
ROLE = "v24945_injective_schema_signature_ledger_projection"
RECEIPT_ROLE = "v24945_content_free_injective_schema_signature_receipt"
TOTAL_CHARACTER_CAP = ledger_parent.TOTAL_CHARACTER_CAP
MAXIMUM_PAGE_CHARS = ledger_parent.MAXIMUM_PAGE_CHARS
BLOCK_CHARACTER_CAP = ledger_parent.BLOCK_CHARACTER_CAP
MAXIMUM_VISIBLE_GROUPS = ledger_parent.MAXIMUM_VISIBLE_GROUPS
MAXIMUM_QUERY_TERMS = ledger_parent.MAXIMUM_QUERY_TERMS
MAXIMUM_RECORDS = ledger_parent.MAXIMUM_RECORDS
MAXIMUM_ROW_KEY_CHARACTERS = ledger_parent.MAXIMUM_ROW_KEY_CHARACTERS
MAXIMUM_VALUE_CHARACTERS = ledger_parent.MAXIMUM_VALUE_CHARACTERS
payload_sha256 = ledger_parent.payload_sha256

_ASCII_TOKEN = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", re.I)
_FOUR_DIGIT_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


def _signature(value: object) -> tuple[str, ...] | None:
    """Return a conservative order-invariant multi-token ASCII signature."""

    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = structure._BRACKET_CODE.sub(" ", text)
    text = _FOUR_DIGIT_YEAR.sub(" ", text)
    tokens = _ASCII_TOKEN.findall(text)
    # Reordering one generic token (for example ``name``) is not evidence of
    # equivalence.  Non-ASCII labels deliberately stay on the exact path.
    if len(tokens) < 2 or re.search(r"[^\x00-\x7f]", text):
        return None
    return tuple(sorted(tokens))


def _schema_signature_owners(
    schema: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, ...], set[int]]:
    owners: dict[tuple[str, ...], set[int]] = defaultdict(set)
    for column in schema:
        signature = _signature(column["display"])
        if signature is not None:
            owners[signature].add(int(column["index"]))
    return dict(owners)


def _label_match(
    label: object, schema: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    canonical = ledger_parent._canonical(label)
    exact = {
        int(column["index"])
        for column in schema
        if canonical and canonical in column["aliases"]
    }
    signature = _signature(label)
    owners = _schema_signature_owners(schema)
    semantic = set(owners.get(signature, set())) if signature is not None else set()
    combined = exact | semantic
    if len(combined) > 1:
        return {"status": "ambiguous", "index": None, "method": None}
    if len(combined) == 0:
        return {"status": "unbound", "index": None, "method": None}
    index = next(iter(combined))
    method = "exact" if exact == {index} else "token_signature"
    return {"status": "bound", "index": index, "method": method}


def _header_analysis(
    cells: Sequence[str], schema: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if not cells or any(not ledger_parent._canonical(cell) for cell in cells):
        return {"status": "invalid", "schema_touch": False}
    matches = [_label_match(cell, schema) for cell in cells]
    schema_touch = any(match["status"] != "unbound" for match in matches)
    normalized = [ledger_parent._canonical(cell) for cell in cells]
    if len(set(normalized)) != len(normalized):
        return {"status": "ambiguous", "schema_touch": schema_touch}
    if any(match["status"] == "ambiguous" for match in matches):
        return {"status": "ambiguous", "schema_touch": schema_touch}
    indexes = [
        match["index"] if match["status"] == "bound" else None
        for match in matches
    ]
    bound_indexes = [int(index) for index in indexes if index is not None]
    if len(bound_indexes) != len(set(bound_indexes)):
        return {"status": "ambiguous", "schema_touch": schema_touch}
    identity_positions = [
        position for position, index in enumerate(indexes) if index == 0
    ]
    target_positions = {
        int(index): position
        for position, index in enumerate(indexes)
        if index is not None and index != 0
    }
    if len(identity_positions) != 1 or not target_positions:
        return {"status": "unbound", "schema_touch": schema_touch}
    signature_positions = sum(
        match.get("method") == "token_signature" for match in matches
    )
    return {
        "status": "bound",
        "schema_touch": True,
        "width": len(cells),
        "identity_position": identity_positions[0],
        "target_positions": dict(sorted(target_positions.items())),
        "exact_position_count": len(bound_indexes) - signature_positions,
        "signature_position_count": signature_positions,
        "binding_kind": (
            "injective_signature_header_bound_table"
            if signature_positions
            else "exact_header_bound_table"
        ),
    }


def _field_pair(
    line: str, schema: Sequence[Mapping[str, Any]]
) -> tuple[int, str, str] | None:
    cells = ledger_parent._pipe_cells(line)
    if cells is not None and len(cells) == 2:
        label, raw_value = cells
    else:
        match = ledger_parent._FIELD.fullmatch(str(line))
        if match is None:
            return None
        label, raw_value = match.group(1), match.group(2)
    matched = _label_match(label, schema)
    if matched["status"] != "bound":
        return None
    index = int(matched["index"])
    maximum = MAXIMUM_ROW_KEY_CHARACTERS if index == 0 else MAXIMUM_VALUE_CHARACTERS
    value = ledger_parent._safe_surface(raw_value, maximum=maximum)
    if value is None:
        return None
    return index, value, str(matched["method"])


def _diagnose_groups(
    groups: Sequence[Sequence[tuple[int, str]]],
    schema: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    counts = {
        "pipe_group_count": 0,
        "pipe_line_count": 0,
        "schema_touching_pipe_line_count": 0,
        "exact_header_mapping_count": 0,
        "signature_header_mapping_count": 0,
        "ambiguous_header_mapping_count": 0,
    }
    for lines in groups:
        group_has_pipe = False
        for _block, line in lines:
            cells = ledger_parent._pipe_cells(line)
            if cells is None:
                continue
            group_has_pipe = True
            counts["pipe_line_count"] += 1
            analysis = _header_analysis(cells, schema)
            counts["schema_touching_pipe_line_count"] += int(
                bool(analysis.get("schema_touch"))
            )
            if analysis["status"] == "ambiguous" and analysis["schema_touch"]:
                counts["ambiguous_header_mapping_count"] += 1
            elif analysis["status"] == "bound":
                name = (
                    "signature_header_mapping_count"
                    if analysis["signature_position_count"]
                    else "exact_header_mapping_count"
                )
                counts[name] += 1
        counts["pipe_group_count"] += int(group_has_pipe)
    return counts


def _table_records(
    *,
    page: Mapping[str, Any],
    groups: Sequence[Sequence[tuple[int, str]]],
    schema: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    counts = {
        "header_bound_table_count": 0,
        "exact_header_bound_table_count": 0,
        "signature_header_bound_table_count": 0,
        "candidate_table_row_count": 0,
        "valid_width_table_row_count": 0,
        "malformed_table_row_count": 0,
    }
    for group_ordinal, lines in enumerate(groups, 1):
        index = 0
        while index < len(lines):
            header_cells = ledger_parent._pipe_cells(lines[index][1])
            analysis = (
                _header_analysis(header_cells, schema)
                if header_cells is not None
                else {"status": "unbound"}
            )
            if analysis["status"] != "bound":
                index += 1
                continue
            counts["header_bound_table_count"] += 1
            counter = (
                "signature_header_bound_table_count"
                if analysis["signature_position_count"]
                else "exact_header_bound_table_count"
            )
            counts[counter] += 1
            header_block = lines[index][0]
            row_index = index + 1
            if row_index < len(lines):
                separator = ledger_parent._pipe_cells(lines[row_index][1])
                if separator is not None and ledger_parent._separator(separator):
                    row_index += 1
            record_ordinal = 0
            while row_index < len(lines):
                cells = ledger_parent._pipe_cells(lines[row_index][1])
                if cells is None:
                    break
                next_analysis = _header_analysis(cells, schema)
                if next_analysis["status"] == "bound":
                    break
                counts["candidate_table_row_count"] += 1
                if (
                    len(cells) != int(analysis["width"])
                    or ledger_parent._separator(cells)
                ):
                    counts["malformed_table_row_count"] += 1
                    break
                counts["valid_width_table_row_count"] += 1
                row_key = ledger_parent._safe_surface(
                    cells[int(analysis["identity_position"])],
                    maximum=MAXIMUM_ROW_KEY_CHARACTERS,
                )
                fields: dict[int, str] = {}
                if row_key is not None:
                    for target_index, position in analysis["target_positions"].items():
                        field_value = ledger_parent._safe_surface(
                            cells[int(position)], maximum=MAXIMUM_VALUE_CHARACTERS
                        )
                        if field_value is not None:
                            fields[int(target_index)] = field_value
                if row_key is not None and fields and len(records) < MAXIMUM_RECORDS:
                    record_ordinal += 1
                    records.append(
                        ledger_parent._record(
                            page=page,
                            binding=str(analysis["binding_kind"]),
                            group_ordinal=group_ordinal,
                            record_ordinal=record_ordinal,
                            identity_block_ordinal=header_block,
                            value_block_ordinal=lines[row_index][0],
                            row_key=row_key,
                            fields=fields,
                            schema=schema,
                        )
                    )
                row_index += 1
            index = max(index + 1, row_index)
    return records, counts


def _labelled_records(
    *,
    page: Mapping[str, Any],
    groups: Sequence[Sequence[tuple[int, str]]],
    schema: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    counts = {
        "identity_label_bound_record_count": 0,
        "exact_identity_label_bound_record_count": 0,
        "signature_identity_label_bound_record_count": 0,
        "duplicate_field_conflict_count": 0,
    }
    for group_ordinal, lines in enumerate(groups, 1):
        current_identity: str | None = None
        identity_block = 0
        fields: dict[int, str] = {}
        conflicted: set[int] = set()
        used_signature = False
        record_ordinal = 0
        last_block = 0

        def flush() -> None:
            nonlocal current_identity, identity_block, fields, conflicted
            nonlocal used_signature, record_ordinal, last_block
            clean_fields = {
                index: value for index, value in fields.items() if index not in conflicted
            }
            if (
                current_identity is not None
                and clean_fields
                and len(records) < MAXIMUM_RECORDS
            ):
                record_ordinal += 1
                binding = (
                    "injective_signature_identity_label_bound_record"
                    if used_signature
                    else "exact_identity_label_bound_record"
                )
                records.append(
                    ledger_parent._record(
                        page=page,
                        binding=binding,
                        group_ordinal=group_ordinal,
                        record_ordinal=record_ordinal,
                        identity_block_ordinal=identity_block,
                        value_block_ordinal=last_block,
                        row_key=current_identity,
                        fields=clean_fields,
                        schema=schema,
                    )
                )
                counts["identity_label_bound_record_count"] += 1
                name = (
                    "signature_identity_label_bound_record_count"
                    if used_signature
                    else "exact_identity_label_bound_record_count"
                )
                counts[name] += 1
            current_identity = None
            identity_block = 0
            fields = {}
            conflicted = set()
            used_signature = False
            last_block = 0

        for block_ordinal, line in lines:
            pair = _field_pair(line, schema)
            if pair is None:
                flush()
                continue
            index, value, method = pair
            if index == 0:
                flush()
                current_identity = value
                identity_block = block_ordinal
                last_block = block_ordinal
                used_signature = method == "token_signature"
                continue
            if current_identity is None:
                continue
            used_signature = used_signature or method == "token_signature"
            last_block = block_ordinal
            if index in fields and ledger_parent._canonical(fields[index]) != ledger_parent._canonical(value):
                conflicted.add(index)
                counts["duplicate_field_conflict_count"] += 1
            else:
                fields.setdefault(index, value)
        flush()
    return records, counts


def _zero_discovery_counts() -> dict[str, int]:
    return {
        "pipe_group_count": 0,
        "pipe_line_count": 0,
        "schema_touching_pipe_line_count": 0,
        "exact_header_mapping_count": 0,
        "signature_header_mapping_count": 0,
        "ambiguous_header_mapping_count": 0,
        "header_bound_table_count": 0,
        "exact_header_bound_table_count": 0,
        "signature_header_bound_table_count": 0,
        "candidate_table_row_count": 0,
        "valid_width_table_row_count": 0,
        "malformed_table_row_count": 0,
        "identity_label_bound_record_count": 0,
        "exact_identity_label_bound_record_count": 0,
        "signature_identity_label_bound_record_count": 0,
        "duplicate_field_conflict_count": 0,
    }


def _discover(
    pages: Sequence[Mapping[str, Any]], schema: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    blocks = [
        block
        for page in pages
        for block in atomic._blocks(page, BLOCK_CHARACTER_CAP)
    ]
    records: list[dict[str, Any]] = []
    counts = _zero_discovery_counts()
    seen_ids: set[str] = set()
    for page in pages:
        groups = ledger_parent._page_groups(blocks, int(page["ordinal"]))
        diagnostics = _diagnose_groups(groups, schema)
        table_records, table_counts = _table_records(
            page=page, groups=groups, schema=schema
        )
        labelled_records, labelled_counts = _labelled_records(
            page=page, groups=groups, schema=schema
        )
        for name, number in {
            **diagnostics,
            **table_counts,
            **labelled_counts,
        }.items():
            counts[name] += int(number)
        for record in (*table_records, *labelled_records):
            if len(records) >= MAXIMUM_RECORDS:
                break
            record_id = str(record["record_id"])
            if record_id in seen_ids:
                continue
            records.append(record)
            seen_ids.add(record_id)
    return records, counts


def _compact_header(
    page: Mapping[str, Any], schema: Sequence[Mapping[str, Any]]
) -> str:
    return "[SBCL-SCHEMA] " + json.dumps(
        {
            "source_host": page["host"],
            "row_key_label": schema[0]["display"],
            "targets": [
                [int(column["index"]), str(column["display"])]
                for column in schema[1:]
            ],
            "binding": "exact_or_injective_token_signature",
            "conflicts": "omitted",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _compact_line(
    record: Mapping[str, Any], fields: Sequence[Mapping[str, Any]]
) -> tuple[str, str]:
    token = f"[SBCL:{record['record_id']}]"
    line = token + " " + json.dumps(
        {
            "row": record["row_key"],
            "cells": [
                [int(field["target_index"]), str(field["value"])]
                for field in fields
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return token, line


def _compact_augment_pages(
    pages: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    conflicts: set[tuple[str, int]],
    schema: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    lines_by_page: dict[int, list[str]] = defaultdict(list)
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, str]] = set()
    maximum_line = 0
    compact_characters = 0
    for record in records:
        row = ledger_parent._canonical(record["row_key"])
        eligible: list[Mapping[str, Any]] = []
        for field in record["fields"]:
            target = int(field["target_index"])
            identity = (
                str(record["source_url"]),
                row,
                target,
                ledger_parent._canonical(field["value"]),
            )
            if (row, target) in conflicts or identity in seen:
                continue
            eligible.append(field)
            seen.add(identity)
        if not eligible:
            continue
        token, line = _compact_line(record, eligible)
        if len(line) > BLOCK_CHARACTER_CAP:
            raise ValueError("V2.49.45 compact record exceeds atomic block cap")
        maximum_line = max(maximum_line, len(line))
        compact_characters += len(line)
        lines_by_page[int(record["source_page_ordinal"])].append(line)
        for field in eligible:
            observation = {
                "token": token,
                "record_id": record["record_id"],
                "source_page_ordinal": record["source_page_ordinal"],
                "source_url": record["source_url"],
                "source_host": record["source_host"],
                "binding_kind": record["binding_kind"],
                "row_key": record["row_key"],
                "target_index": int(field["target_index"]),
                "target_label": field["target_label"],
                "value": field["value"],
            }
            observation["observation_payload_sha256"] = payload_sha256(observation)
            observations.append(observation)
    output: list[dict[str, Any]] = []
    for page in pages:
        copied = {
            "title": str(page["title"]),
            "url": str(page["url"]),
            "content": str(page["content"]),
        }
        lines = lines_by_page.get(int(page["ordinal"]), [])
        if lines:
            header = _compact_header(page, schema)
            compact_characters += len(header)
            copied["content"] = header + "\n" + "\n".join(lines) + "\n\n" + copied["content"]
        output.append(copied)
    return output, observations, maximum_line, compact_characters


_DISCOVERY_COUNT_NAMES = tuple(_zero_discovery_counts())
_RECEIPT_COUNT_NAMES = (
    "input_page_count",
    "visible_schema_column_count",
    *_DISCOVERY_COUNT_NAMES,
    "discovered_record_count",
    "discovered_row_key_count",
    "conflicting_coordinate_count",
    "admissible_bound_observation_count",
    "retained_admissible_bound_observation_count",
    "missed_admissible_bound_observation_count",
    "admissible_record_count",
    "retained_admissible_record_count",
    "source_url_count",
    "source_host_count",
    "compact_ledger_characters",
    "maximum_compact_record_line_characters",
    "projected_rendered_characters",
    "positive_signed_credit_count",
    "unbound_observation_positive_credit_count",
)


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": compact_parent.POLICY_ID,
        **{name: int(value[name]) for name in _RECEIPT_COUNT_NAMES},
        "multi_token_ascii_multiset_signature_only": True,
        "bracket_code_and_four_digit_year_removed_before_signature": True,
        "page_header_to_visible_schema_binding_injective": True,
        "ambiguous_duplicate_or_shared_signature_fails_closed": True,
        "table_header_and_row_never_joined_across_page_or_structure_group": True,
        "source_url_host_record_row_target_and_value_atomically_bound": True,
        "conflicting_coordinates_fail_closed_before_projection": True,
        "content_free_shadow_diagnostics_do_not_change_selection": True,
        "record_rows_atomic_and_never_split_across_blocks": True,
        "inherited_total_and_per_page_caps_preserved": True,
        "same_forward_page_bytes_only": True,
        "entropy_information_gain_shadow_only": True,
        "unbound_observation_credit_forced_zero": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read": False,
        "additional_search_fetch_model_call_token_context_or_wall_cap": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return validate_receipt(receipt)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "multi_token_ascii_multiset_signature_only",
        "bracket_code_and_four_digit_year_removed_before_signature",
        "page_header_to_visible_schema_binding_injective",
        "ambiguous_duplicate_or_shared_signature_fails_closed",
        "table_header_and_row_never_joined_across_page_or_structure_group",
        "source_url_host_record_row_target_and_value_atomically_bound",
        "conflicting_coordinates_fail_closed_before_projection",
        "content_free_shadow_diagnostics_do_not_change_selection",
        "record_rows_atomic_and_never_split_across_blocks",
        "inherited_total_and_per_page_caps_preserved",
        "same_forward_page_bytes_only",
        "entropy_information_gain_shadow_only",
        "unbound_observation_credit_forced_zero",
    )
    false_flags = (
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_call_token_context_or_wall_cap",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != compact_parent.POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _RECEIPT_COUNT_NAMES
        )
        or copied["header_bound_table_count"]
        != copied["exact_header_bound_table_count"]
        + copied["signature_header_bound_table_count"]
        or copied["identity_label_bound_record_count"]
        != copied["exact_identity_label_bound_record_count"]
        + copied["signature_identity_label_bound_record_count"]
        or copied["retained_admissible_bound_observation_count"]
        > copied["admissible_bound_observation_count"]
        or copied["missed_admissible_bound_observation_count"]
        != copied["admissible_bound_observation_count"]
        - copied["retained_admissible_bound_observation_count"]
        or copied["retained_admissible_record_count"]
        > copied["admissible_record_count"]
        or copied["maximum_compact_record_line_characters"] > BLOCK_CHARACTER_CAP
        or copied["projected_rendered_characters"] > TOTAL_CHARACTER_CAP
        or copied["positive_signed_credit_count"] != 0
        or copied["unbound_observation_positive_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.45 injective schema-signature receipt drifted")
    return copied


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    discovery_pages = structure._stable_pages(pages)
    compacted_pages, compaction = unicode_total.compact_pages(question, pages)
    stable = structure._stable_pages(compacted_pages)
    if [page["url"] for page in discovery_pages] != [page["url"] for page in stable]:
        raise ValueError("V2.49.45 normalized/compacted page identity drifted")
    schema = ledger_parent._visible_schema(question)
    records, discovery_counts = (
        _discover(discovery_pages, schema)
        if schema
        else ([], _zero_discovery_counts())
    )
    conflicts, coordinate_hosts, coordinate_urls = ledger_parent._coordinate_summary(records)
    augmented, observations, maximum_line, ledger_chars = _compact_augment_pages(
        stable, records, conflicts, schema
    )
    inherited = projector_parent.build_projection(
        question, augmented, explicit_groups=explicit_groups
    )
    projection = str(inherited["projection"])
    retained_tokens = {
        observation["token"]
        for observation in observations
        if observation["token"] in projection
    }
    retained = [
        observation
        for observation in observations
        if observation["token"] in retained_tokens
    ]
    record_ids = {str(value["record_id"]) for value in observations}
    retained_ids = {str(value["record_id"]) for value in retained}
    receipt_input = {
        "input_page_count": len(discovery_pages),
        "visible_schema_column_count": len(schema),
        **discovery_counts,
        "discovered_record_count": len(records),
        "discovered_row_key_count": len(
            {ledger_parent._canonical(record["row_key"]) for record in records}
        ),
        "conflicting_coordinate_count": len(conflicts),
        "admissible_bound_observation_count": len(observations),
        "retained_admissible_bound_observation_count": len(retained),
        "missed_admissible_bound_observation_count": len(observations) - len(retained),
        "admissible_record_count": len(record_ids),
        "retained_admissible_record_count": len(retained_ids),
        "source_url_count": len(
            {url for values in coordinate_urls.values() for url in values}
        ),
        "source_host_count": len(
            {host for values in coordinate_hosts.values() for host in values}
        ),
        "compact_ledger_characters": ledger_chars,
        "maximum_compact_record_line_characters": maximum_line,
        "projected_rendered_characters": len(projection),
        "positive_signed_credit_count": 0,
        "unbound_observation_positive_credit_count": 0,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": compact_parent.POLICY_ID,
        "visible_question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "visible_schema_sha256": payload_sha256(schema),
        "source_manifest_sha256": payload_sha256(
            [
                {
                    "ordinal": page["ordinal"],
                    "url": page["url"],
                    "host": page["host"],
                    "content_sha256": page["content_sha256"],
                }
                for page in discovery_pages
            ]
        ),
        **receipt_input,
        "record_ledger": records,
        "admissible_observations": observations,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode("utf-8")).hexdigest(),
        "content_free_receipt": {},
        "original_unicode_total_compaction_receipt": compaction,
        "parent_projection_receipt": copy.deepcopy(inherited["content_free_receipt"]),
        "parent_augmented_unicode_total_compaction_receipt": copy.deepcopy(
            inherited["unicode_total_compaction_receipt"]
        ),
        "same_forward_page_bytes_only": True,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["content_free_receipt"] = _receipt(value)
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
    receipt = copied.get("content_free_receipt")
    records = copied.get("record_ledger")
    observations = copied.get("admissible_observations")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != compact_parent.POLICY_ID
        or not isinstance(projection, str)
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode("utf-8")).hexdigest()
        or copied.get("projected_rendered_characters") != len(projection)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(records, list)
        or len(records) != copied.get("discovered_record_count")
        or not isinstance(observations, list)
        or len(observations) != copied.get("admissible_bound_observation_count")
        or any(
            record.get("record_payload_sha256")
            != payload_sha256(
                {key: item for key, item in record.items() if key != "record_payload_sha256"}
            )
            for record in records
        )
        or any(
            observation.get("observation_payload_sha256")
            != payload_sha256(
                {
                    key: item
                    for key, item in observation.items()
                    if key != "observation_payload_sha256"
                }
            )
            for observation in observations
        )
        or copied.get("same_forward_page_bytes_only") is not True
        or copied.get("entropy_information_gain_shadow_only") is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.45 injective schema-signature projection drifted")
    compacted, _ = unicode_total.compact_pages(question, pages)
    stable = structure._stable_pages(compacted)
    schema = ledger_parent._visible_schema(question)
    if (
        copied.get("visible_question_sha256")
        != hashlib.sha256(question.encode("utf-8")).hexdigest()
        or copied.get("visible_schema_sha256") != payload_sha256(schema)
        or copied.get("input_page_count") != len(stable)
    ):
        raise ValueError("V2.49.45 visible input binding drifted")
    if replay and copied != build_projection(
        question, pages, explicit_groups=explicit_groups
    ):
        raise ValueError("V2.49.45 projection is not reproducible")
    return copied


__all__ = [
    "BLOCK_CHARACTER_CAP",
    "MAXIMUM_PAGE_CHARS",
    "MAXIMUM_QUERY_TERMS",
    "MAXIMUM_VISIBLE_GROUPS",
    "POLICY_ID",
    "ROLE",
    "TOTAL_CHARACTER_CAP",
    "build_projection",
    "payload_sha256",
    "validate_projection",
    "validate_receipt",
]
