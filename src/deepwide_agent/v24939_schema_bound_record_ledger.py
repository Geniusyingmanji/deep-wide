"""Schema-bound open-world record ledger for fixed-budget projection.

V2.49.33 can prioritize a row--target pair only when the visible question
already enumerates the row.  Open-world wide-table questions usually expose
the output schema but require search to discover the rows.  This pure
successor discovers row keys only from replayable structures in pages fetched
during the same forward pass:

* a pipe-delimited table whose identity and value headers exactly match the
  visible output schema; or
* a contiguous labelled record with an exact visible identity label followed
  by exact visible value labels.

Each admitted cell is atomically bound to its canonical source URL/host, one
record identity, one discovered row key, one visible target column, and one
value.  A conflicting value for the same row/target coordinate is omitted.
The compact ledger is prepended to its source page before the inherited
stable-order, source-diverse, 30k-total/5k-page projection.  It never joins a
header or record across pages or structural groups.

Inputs are limited to the visible question and same-forward fetched pages.
There is no file, environment, process, network, model, benchmark metadata,
answer, evaluator, score, reward, or historical-result capability.  Entropy
and information gain remain shadow-only; they never assign signed credit, and
an unbound observation is forced to zero credit.
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
from . import v24933_contextual_record_value_projector as parent


POLICY_ID = "v24939_schema_bound_open_world_record_ledger_v1"
ROLE = "v24939_schema_bound_record_ledger_projection"
RECEIPT_ROLE = "v24939_content_free_schema_bound_record_ledger_receipt"
TOTAL_CHARACTER_CAP = parent.TOTAL_CHARACTER_CAP
MAXIMUM_PAGE_CHARS = parent.MAXIMUM_PAGE_CHARS
BLOCK_CHARACTER_CAP = parent.BLOCK_CHARACTER_CAP
MAXIMUM_VISIBLE_GROUPS = parent.MAXIMUM_VISIBLE_GROUPS
MAXIMUM_QUERY_TERMS = parent.MAXIMUM_QUERY_TERMS
MAXIMUM_SCHEMA_COLUMNS = 32
MAXIMUM_RECORDS = 2_048
MAXIMUM_OBSERVATIONS = 8_192
MAXIMUM_ROW_KEY_CHARACTERS = 200
MAXIMUM_VALUE_CHARACTERS = 400
payload_sha256 = parent.payload_sha256

_UNKNOWN = frozenset(
    {
        "",
        "-",
        "--",
        "—",
        "?",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "未知",
        "不详",
        "无法确认",
    }
)
_FIELD = re.compile(r"^\s*([^:：\t|]{1,240})\s*[:：\t]\s*(.*?)\s*$")


def _canonical(value: object) -> str:
    return structure._canonical_phrase(value)


def _display(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).strip(
        " |,，、.;；"
    )


def _safe_surface(value: object, *, maximum: int) -> str | None:
    text = _display(value)
    if (
        not text
        or len(text) > maximum
        or "\x00" in text
        or any(ord(character) < 32 and character not in "\t" for character in text)
        or _canonical(text) in _UNKNOWN
        or re.fullmatch(r":?-{3,}:?", text.replace(" ", "")) is not None
    ):
        return None
    return text


def _visible_schema(question: str) -> list[dict[str, Any]]:
    """Return exact visible schema columns with unambiguous aliases."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.39 visible question is absent")
    visible = structure._clean(question)
    raw_columns: list[str] = []
    for pattern in structure._COLUMN_PATTERNS:
        match = pattern.search(visible)
        if match is None:
            continue
        clause = re.split(
            r"(?:不要问|don't ask|do not ask|输出格式|output format)",
            match.group(1),
            maxsplit=1,
            flags=re.I,
        )[0]
        raw_columns = [
            value
            for value in re.split(r"\s*[|,，、]\s*", clause)
            if _display(value)
        ]
        if len(raw_columns) >= 2:
            break
    if not 2 <= len(raw_columns) <= MAXIMUM_SCHEMA_COLUMNS:
        return []

    schema: list[dict[str, Any]] = []
    alias_owners: dict[str, set[int]] = defaultdict(set)
    for index, raw in enumerate(raw_columns):
        display = _display(raw)
        aliases: list[str] = []
        for candidate in (display, *structure._group_parts(display)):
            canonical = _canonical(candidate)
            if canonical and canonical not in aliases:
                aliases.append(canonical)
        if not aliases:
            return []
        schema.append({"index": index, "display": display, "aliases": aliases})
        for alias in aliases:
            alias_owners[alias].add(index)

    # An alias shared by two visible columns cannot safely bind a page header.
    for column in schema:
        column["aliases"] = [
            alias
            for alias in column["aliases"]
            if alias_owners[alias] == {int(column["index"])}
        ]
        if not column["aliases"]:
            return []
    return schema


def _pipe_cells(line: str) -> list[str] | None:
    raw = unicodedata.normalize("NFKC", str(line)).strip()
    if "|" not in raw:
        return None
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    cells = [_display(value) for value in raw.split("|")]
    return cells if 2 <= len(cells) <= 64 else None


def _separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", value.replace(" ", "")) is not None
        for value in cells
    )


def _schema_index(label: object, schema: Sequence[Mapping[str, Any]]) -> int | None:
    canonical = _canonical(label)
    matches = [
        int(column["index"])
        for column in schema
        if canonical in column["aliases"]
    ]
    return matches[0] if len(matches) == 1 else None


def _header_mapping(
    cells: Sequence[str], schema: Sequence[Mapping[str, Any]]
) -> dict[str, Any] | None:
    if not cells or any(not _canonical(cell) for cell in cells):
        return None
    normalized = [_canonical(cell) for cell in cells]
    if len(set(normalized)) != len(normalized):
        return None
    matches = [_schema_index(cell, schema) for cell in cells]
    identity_positions = [index for index, value in enumerate(matches) if value == 0]
    target_positions: dict[int, int] = {}
    for position, value in enumerate(matches):
        if value is None or value == 0:
            continue
        if value in target_positions:
            return None
        target_positions[value] = position
    if len(identity_positions) != 1 or not target_positions:
        return None
    return {
        "width": len(cells),
        "identity_position": identity_positions[0],
        "target_positions": dict(sorted(target_positions.items())),
    }


def _field_pair(
    line: str, schema: Sequence[Mapping[str, Any]]
) -> tuple[int, str] | None:
    cells = _pipe_cells(line)
    if cells is not None and len(cells) == 2:
        label, raw_value = cells
    else:
        match = _FIELD.fullmatch(str(line))
        if match is None:
            return None
        label, raw_value = match.group(1), match.group(2)
    index = _schema_index(label, schema)
    if index is None:
        return None
    maximum = MAXIMUM_ROW_KEY_CHARACTERS if index == 0 else MAXIMUM_VALUE_CHARACTERS
    value = _safe_surface(raw_value, maximum=maximum)
    return (index, value) if value is not None else None


def _page_groups(
    blocks: Sequence[Mapping[str, Any]], page_ordinal: int
) -> list[list[tuple[int, str]]]:
    grouped: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for block in blocks:
        if int(block["page_ordinal"]) != page_ordinal:
            continue
        group = int(block.get("structure_group_ordinal", block["block_ordinal"]))
        for line in str(block["content"]).splitlines():
            if line.strip():
                grouped[group].append((int(block["block_ordinal"]), line))
    return [grouped[index] for index in sorted(grouped)]


def _record(
    *,
    page: Mapping[str, Any],
    binding: str,
    group_ordinal: int,
    record_ordinal: int,
    identity_block_ordinal: int,
    value_block_ordinal: int,
    row_key: str,
    fields: Mapping[int, str],
    schema: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    field_vector = [
        {
            "target_index": int(index),
            "target_label": str(schema[index]["display"]),
            "value": str(fields[index]),
        }
        for index in sorted(fields)
    ]
    identity_material = {
        "source_url": str(page["url"]),
        "binding": binding,
        "group_ordinal": group_ordinal,
        "record_ordinal": record_ordinal,
        "row_key": row_key,
        "fields": field_vector,
    }
    record_id = "R" + payload_sha256(identity_material)[:20]
    value: dict[str, Any] = {
        "record_id": record_id,
        "source_page_ordinal": int(page["ordinal"]),
        "source_url": str(page["url"]),
        "source_host": str(page["host"]),
        "binding_kind": binding,
        "structure_group_ordinal": int(group_ordinal),
        "identity_block_ordinal": int(identity_block_ordinal),
        "value_block_ordinal": int(value_block_ordinal),
        "row_key_label": str(schema[0]["display"]),
        "row_key": row_key,
        "fields": field_vector,
    }
    value["record_payload_sha256"] = payload_sha256(value)
    return value


def _table_records(
    *,
    page: Mapping[str, Any],
    groups: Sequence[Sequence[tuple[int, str]]],
    schema: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    counts = {
        "header_bound_table_count": 0,
        "candidate_table_row_count": 0,
        "malformed_table_row_count": 0,
    }
    for group_ordinal, lines in enumerate(groups, 1):
        index = 0
        while index < len(lines):
            header_cells = _pipe_cells(lines[index][1])
            header = (
                _header_mapping(header_cells, schema)
                if header_cells is not None
                else None
            )
            if header is None:
                index += 1
                continue
            counts["header_bound_table_count"] += 1
            header_block = lines[index][0]
            row_index = index + 1
            if row_index < len(lines):
                possible_separator = _pipe_cells(lines[row_index][1])
                if possible_separator is not None and _separator(possible_separator):
                    row_index += 1
            record_ordinal = 0
            while row_index < len(lines):
                cells = _pipe_cells(lines[row_index][1])
                if cells is None:
                    break
                if _header_mapping(cells, schema) is not None:
                    break
                counts["candidate_table_row_count"] += 1
                if len(cells) != int(header["width"]) or _separator(cells):
                    counts["malformed_table_row_count"] += 1
                    break
                row_key = _safe_surface(
                    cells[int(header["identity_position"])],
                    maximum=MAXIMUM_ROW_KEY_CHARACTERS,
                )
                fields: dict[int, str] = {}
                if row_key is not None:
                    for target_index, position in header["target_positions"].items():
                        field_value = _safe_surface(
                            cells[int(position)], maximum=MAXIMUM_VALUE_CHARACTERS
                        )
                        if field_value is not None:
                            fields[int(target_index)] = field_value
                if row_key is not None and fields and len(records) < MAXIMUM_RECORDS:
                    record_ordinal += 1
                    records.append(
                        _record(
                            page=page,
                            binding="header_bound_table",
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
    counts = {"identity_label_bound_record_count": 0, "duplicate_field_conflict_count": 0}
    for group_ordinal, lines in enumerate(groups, 1):
        current_identity: str | None = None
        identity_block = 0
        fields: dict[int, str] = {}
        conflicted: set[int] = set()
        record_ordinal = 0
        last_block = 0

        def flush() -> None:
            nonlocal current_identity, identity_block, fields, conflicted
            nonlocal record_ordinal, last_block
            clean_fields = {
                index: value for index, value in fields.items() if index not in conflicted
            }
            if (
                current_identity is not None
                and clean_fields
                and len(records) < MAXIMUM_RECORDS
            ):
                record_ordinal += 1
                records.append(
                    _record(
                        page=page,
                        binding="identity_label_bound_record",
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
            current_identity = None
            identity_block = 0
            fields = {}
            conflicted = set()
            last_block = 0

        for block_ordinal, line in lines:
            pair = _field_pair(line, schema)
            if pair is None:
                flush()
                continue
            index, value = pair
            if index == 0:
                flush()
                current_identity = value
                identity_block = block_ordinal
                last_block = block_ordinal
                continue
            if current_identity is None:
                continue
            last_block = block_ordinal
            if index in fields and _canonical(fields[index]) != _canonical(value):
                conflicted.add(index)
                counts["duplicate_field_conflict_count"] += 1
            else:
                fields.setdefault(index, value)
        flush()
    return records, counts


def _discover(
    pages: Sequence[Mapping[str, Any]], schema: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    blocks = [
        block
        for page in pages
        for block in atomic._blocks(page, BLOCK_CHARACTER_CAP)
    ]
    records: list[dict[str, Any]] = []
    counts = {
        "header_bound_table_count": 0,
        "candidate_table_row_count": 0,
        "malformed_table_row_count": 0,
        "identity_label_bound_record_count": 0,
        "duplicate_field_conflict_count": 0,
    }
    seen_ids: set[str] = set()
    for page in pages:
        groups = _page_groups(blocks, int(page["ordinal"]))
        table_records, table_counts = _table_records(
            page=page, groups=groups, schema=schema
        )
        labelled_records, labelled_counts = _labelled_records(
            page=page, groups=groups, schema=schema
        )
        for name, number in {**table_counts, **labelled_counts}.items():
            counts[name] += number
        for record in (*table_records, *labelled_records):
            if len(records) >= MAXIMUM_RECORDS:
                break
            record_id = str(record["record_id"])
            if record_id in seen_ids:
                continue
            records.append(record)
            seen_ids.add(record_id)
    return records, counts


def _coordinate_summary(
    records: Sequence[Mapping[str, Any]],
) -> tuple[set[tuple[str, int]], dict[tuple[str, int], set[str]], dict[tuple[str, int], set[str]]]:
    values: dict[tuple[str, int], set[str]] = defaultdict(set)
    hosts: dict[tuple[str, int], set[str]] = defaultdict(set)
    urls: dict[tuple[str, int], set[str]] = defaultdict(set)
    for record in records:
        row = _canonical(record["row_key"])
        for field in record["fields"]:
            coordinate = (row, int(field["target_index"]))
            values[coordinate].add(_canonical(field["value"]))
            hosts[coordinate].add(str(record["source_host"]))
            urls[coordinate].add(str(record["source_url"]))
    conflicts = {coordinate for coordinate, candidates in values.items() if len(candidates) > 1}
    return conflicts, hosts, urls


def _ledger_line(
    record: Mapping[str, Any],
    fields: Sequence[Mapping[str, Any]],
) -> tuple[list[str], str]:
    token = f"[SBCL:{record['record_id']}]"
    tokens = [token for _field in fields]
    payload = {
        "binding": record["binding_kind"],
        "row_key_label": record["row_key_label"],
        "row_key": record["row_key"],
        "fields": [
            [field["target_label"], field["value"]] for field in fields
        ],
        "source_host": record["source_host"],
    }
    return tokens, token + " " + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )


def _augment_pages(
    pages: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    conflicts: set[tuple[str, int]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines_by_page: dict[int, list[str]] = defaultdict(list)
    observations: list[dict[str, Any]] = []
    seen_observations: set[tuple[str, str, int, str]] = set()
    for record in records:
        row = _canonical(record["row_key"])
        eligible: list[Mapping[str, Any]] = []
        for field in record["fields"]:
            target = int(field["target_index"])
            if (row, target) in conflicts:
                continue
            identity = (
                str(record["source_url"]),
                row,
                target,
                _canonical(field["value"]),
            )
            if identity in seen_observations:
                continue
            eligible.append(field)
            seen_observations.add(identity)

        # Pack several fields from the same source-bound record into one
        # structural line, but never let the line exceed the inherited atomic
        # block cap.  This preserves more wide rows than one JSON line/cell.
        chunks: list[list[Mapping[str, Any]]] = []
        current: list[Mapping[str, Any]] = []
        for field in eligible:
            if len(observations) + sum(len(chunk) for chunk in chunks) + len(current) >= MAXIMUM_OBSERVATIONS:
                break
            proposed = [*current, field]
            _tokens, proposed_line = _ledger_line(record, proposed)
            if len(proposed_line) <= BLOCK_CHARACTER_CAP:
                current = proposed
                continue
            if current:
                chunks.append(current)
            single_tokens, single_line = _ledger_line(record, [field])
            current = [field] if single_tokens and len(single_line) <= BLOCK_CHARACTER_CAP else []
        if current:
            chunks.append(current)

        for chunk in chunks:
            tokens, line = _ledger_line(record, chunk)
            lines_by_page[int(record["source_page_ordinal"])].append(line)
            for token, field in zip(tokens, chunk, strict=True):
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
            preamble = (
                "[SCHEMA-BOUND RECORD LEDGER: exact header/label binding; "
                "conflicting coordinates omitted]\n"
            )
            copied["content"] = preamble + "\n".join(lines) + "\n\n" + copied["content"]
        output.append(copied)
    return output, observations


def _content_free_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    count_names = (
        "input_page_count",
        "visible_schema_column_count",
        "visible_value_target_count",
        "header_bound_table_count",
        "candidate_table_row_count",
        "malformed_table_row_count",
        "identity_label_bound_record_count",
        "duplicate_field_conflict_count",
        "discovered_record_count",
        "discovered_row_key_count",
        "raw_bound_observation_count",
        "conflicting_coordinate_count",
        "admissible_bound_observation_count",
        "retained_admissible_bound_observation_count",
        "missed_admissible_bound_observation_count",
        "admissible_record_count",
        "retained_admissible_record_count",
        "independently_corroborated_coordinate_count",
        "single_host_coordinate_count",
        "source_url_count",
        "source_host_count",
        "shadow_information_gain_eligible_observation_count",
        "positive_signed_credit_count",
        "unbound_observation_positive_credit_count",
        "projected_rendered_characters",
    )
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        **{name: int(value[name]) for name in count_names},
        "row_keys_discovered_from_exact_schema_bound_pages_not_question_enumeration": True,
        "table_header_and_row_never_joined_across_page_or_structure_group": True,
        "source_url_host_record_row_target_and_value_atomically_bound": True,
        "conflicting_coordinates_fail_closed_before_projection": True,
        "stable_source_and_record_order_preserved": True,
        "inherited_total_and_per_page_caps_preserved": True,
        "same_forward_page_bytes_only": True,
        "source_title_required_for_record_admission": False,
        "entropy_information_gain_shadow_only": True,
        "unbound_observation_credit_forced_zero": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_query_url_host_row_value_projection_hash_opaque_id_or_credential": False,
        "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read": False,
        "additional_search_fetch_model_call_token_context_or_wall_cap": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return validate_receipt(receipt)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    count_names = (
        "input_page_count",
        "visible_schema_column_count",
        "visible_value_target_count",
        "header_bound_table_count",
        "candidate_table_row_count",
        "malformed_table_row_count",
        "identity_label_bound_record_count",
        "duplicate_field_conflict_count",
        "discovered_record_count",
        "discovered_row_key_count",
        "raw_bound_observation_count",
        "conflicting_coordinate_count",
        "admissible_bound_observation_count",
        "retained_admissible_bound_observation_count",
        "missed_admissible_bound_observation_count",
        "admissible_record_count",
        "retained_admissible_record_count",
        "independently_corroborated_coordinate_count",
        "single_host_coordinate_count",
        "source_url_count",
        "source_host_count",
        "shadow_information_gain_eligible_observation_count",
        "positive_signed_credit_count",
        "unbound_observation_positive_credit_count",
        "projected_rendered_characters",
    )
    true_flags = (
        "row_keys_discovered_from_exact_schema_bound_pages_not_question_enumeration",
        "table_header_and_row_never_joined_across_page_or_structure_group",
        "source_url_host_record_row_target_and_value_atomically_bound",
        "conflicting_coordinates_fail_closed_before_projection",
        "stable_source_and_record_order_preserved",
        "inherited_total_and_per_page_caps_preserved",
        "same_forward_page_bytes_only",
        "entropy_information_gain_shadow_only",
        "unbound_observation_credit_forced_zero",
    )
    false_flags = (
        "source_title_required_for_record_admission",
        "entropy_or_information_gain_assigns_signed_credit",
        "contains_question_query_url_host_row_value_projection_hash_opaque_id_or_credential",
        "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_call_token_context_or_wall_cap",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_names
        )
        or copied["visible_value_target_count"]
        != max(0, copied["visible_schema_column_count"] - 1)
        or copied["retained_admissible_bound_observation_count"]
        > copied["admissible_bound_observation_count"]
        or copied["missed_admissible_bound_observation_count"]
        != copied["admissible_bound_observation_count"]
        - copied["retained_admissible_bound_observation_count"]
        or copied["retained_admissible_record_count"]
        > copied["admissible_record_count"]
        or copied["shadow_information_gain_eligible_observation_count"]
        != copied["admissible_bound_observation_count"]
        or copied["positive_signed_credit_count"] != 0
        or copied["unbound_observation_positive_credit_count"] != 0
        or copied["projected_rendered_characters"] > TOTAL_CHARACTER_CAP
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.39 schema-bound ledger receipt drifted")
    return copied


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    # Discover open-world rows before the inherited visible-row compactor.
    # If a prompt names only a subset of rows, compaction may intentionally
    # drop other table rows; the bound ledger must already have captured them.
    discovery_pages = structure._stable_pages(pages)
    compacted_pages, original_compaction = unicode_total.compact_pages(question, pages)
    stable = structure._stable_pages(compacted_pages)
    if [page["url"] for page in discovery_pages] != [page["url"] for page in stable]:
        raise ValueError("V2.49.39 normalized/compacted page identity drifted")
    schema = _visible_schema(question)
    records, discovery_counts = _discover(discovery_pages, schema) if schema else ([], {
        "header_bound_table_count": 0,
        "candidate_table_row_count": 0,
        "malformed_table_row_count": 0,
        "identity_label_bound_record_count": 0,
        "duplicate_field_conflict_count": 0,
    })
    conflicts, coordinate_hosts, coordinate_urls = _coordinate_summary(records)
    augmented_pages, observations = _augment_pages(stable, records, conflicts)
    inherited = parent.build_projection(
        question, augmented_pages, explicit_groups=explicit_groups
    )
    projection = str(inherited["projection"])
    retained_tokens = {
        observation["token"]
        for observation in observations
        if observation["token"] in projection
    }
    retained_observations = [
        observation
        for observation in observations
        if observation["token"] in retained_tokens
    ]
    admissible_record_ids = {str(value["record_id"]) for value in observations}
    retained_record_ids = {
        str(value["record_id"]) for value in retained_observations
    }
    raw_observations = sum(len(record["fields"]) for record in records)
    nonconflicting_coordinates = set(coordinate_hosts) - conflicts
    independent = sum(
        len(coordinate_hosts[coordinate]) >= 2
        for coordinate in nonconflicting_coordinates
    )
    receipt_input = {
        "input_page_count": len(discovery_pages),
        "visible_schema_column_count": len(schema),
        "visible_value_target_count": max(0, len(schema) - 1),
        **discovery_counts,
        "discovered_record_count": len(records),
        "discovered_row_key_count": len({_canonical(record["row_key"]) for record in records}),
        "raw_bound_observation_count": raw_observations,
        "conflicting_coordinate_count": len(conflicts),
        "admissible_bound_observation_count": len(observations),
        "retained_admissible_bound_observation_count": len(retained_observations),
        "missed_admissible_bound_observation_count": len(observations) - len(retained_observations),
        "admissible_record_count": len(admissible_record_ids),
        "retained_admissible_record_count": len(retained_record_ids),
        "independently_corroborated_coordinate_count": independent,
        "single_host_coordinate_count": sum(
            len(coordinate_hosts[coordinate]) == 1
            for coordinate in nonconflicting_coordinates
        ),
        "source_url_count": len({url for values in coordinate_urls.values() for url in values}),
        "source_host_count": len({host for values in coordinate_hosts.values() for host in values}),
        "shadow_information_gain_eligible_observation_count": len(observations),
        "positive_signed_credit_count": 0,
        "unbound_observation_positive_credit_count": 0,
        "projected_rendered_characters": len(projection),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
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
        "original_unicode_total_compaction_receipt": original_compaction,
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
    value["content_free_receipt"] = _content_free_receipt(value)
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
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(projection, str)
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode("utf-8")).hexdigest()
        or copied.get("projected_rendered_characters") != len(projection)
        or len(projection) > TOTAL_CHARACTER_CAP
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or any(
            receipt.get(name) != copied.get(name)
            for name in (
                "input_page_count",
                "visible_schema_column_count",
                "visible_value_target_count",
                "header_bound_table_count",
                "candidate_table_row_count",
                "malformed_table_row_count",
                "identity_label_bound_record_count",
                "duplicate_field_conflict_count",
                "discovered_record_count",
                "discovered_row_key_count",
                "raw_bound_observation_count",
                "conflicting_coordinate_count",
                "admissible_bound_observation_count",
                "retained_admissible_bound_observation_count",
                "missed_admissible_bound_observation_count",
                "admissible_record_count",
                "retained_admissible_record_count",
                "independently_corroborated_coordinate_count",
                "single_host_coordinate_count",
                "source_url_count",
                "source_host_count",
                "shadow_information_gain_eligible_observation_count",
                "positive_signed_credit_count",
                "unbound_observation_positive_credit_count",
                "projected_rendered_characters",
            )
        )
        or unicode_total.validate_receipt(
            copied.get("original_unicode_total_compaction_receipt", {})
        )
        != copied.get("original_unicode_total_compaction_receipt")
        or parent.validate_receipt(copied.get("parent_projection_receipt", {}))
        != copied.get("parent_projection_receipt")
        or unicode_total.validate_receipt(
            copied.get("parent_augmented_unicode_total_compaction_receipt", {})
        )
        != copied.get("parent_augmented_unicode_total_compaction_receipt")
        or not isinstance(records, list)
        or len(records) != copied.get("discovered_record_count")
        or not isinstance(observations, list)
        or len(observations) != copied.get("admissible_bound_observation_count")
        or any(
            not isinstance(record, Mapping)
            or record.get("record_payload_sha256")
            != payload_sha256(
                {key: item for key, item in record.items() if key != "record_payload_sha256"}
            )
            for record in records
        )
        or any(
            not isinstance(observation, Mapping)
            or observation.get("observation_payload_sha256")
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
        or copied.get(
            "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.39 schema-bound ledger projection drifted")
    compacted, _ = unicode_total.compact_pages(question, pages)
    stable = structure._stable_pages(compacted)
    if (
        copied.get("visible_question_sha256")
        != hashlib.sha256(question.encode("utf-8")).hexdigest()
        or copied.get("visible_schema_sha256") != payload_sha256(_visible_schema(question))
        or copied.get("input_page_count") != len(stable)
    ):
        raise ValueError("V2.49.39 visible input binding drifted")
    if replay and copied != build_projection(
        question, pages, explicit_groups=explicit_groups
    ):
        raise ValueError("V2.49.39 schema-bound ledger is not reproducible")
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
