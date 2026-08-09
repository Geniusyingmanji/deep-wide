"""Robust-visible-schema successor for late-page bound projection.

V2.49.83 exposed a parser mismatch before any quality evaluation: the legacy
score-first parser truncated an English sentence-style column declaration,
while the legacy ledger parser consumed the following instruction sentence as
part of the last column.  This pure append-only successor reuses the already
tested V2.42.86 sentence/bracket-aware visible-schema parser, then runs the
unchanged V2.49.80 source/record/target binding and 5k conservation logic.

Inputs are only the visible question and one page decoded during the same
forward pass.  There is no file, environment, process, network, model,
benchmark-label, evaluator, score, reward, historical-result, or credential
capability.  Entropy and information gain remain shadow-only and assign no
signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as structure
from . import v24939_schema_bound_record_ledger as ledger
from . import v24949_mutual_partial_signature_ledger as discovery
from . import v24980_late_page_bound_projection as parent
from .v24286_visible_schema_runtime import extract_robust_visible_columns


POLICY_ID = "v24984_robust_visible_schema_late_page_projection_v1"
ROLE = "v24984_robust_visible_schema_late_page_projection"
RECEIPT_ROLE = "v24984_content_free_robust_schema_receipt"
PAGE_CHARACTER_CAP = parent.PAGE_CHARACTER_CAP
MAXIMUM_INPUT_PAGE_CHARACTERS = parent.MAXIMUM_INPUT_PAGE_CHARACTERS


def _robust_schema(question: str) -> list[dict[str, Any]]:
    """Build the ledger schema from the frozen robust visible parser."""

    columns = extract_robust_visible_columns(question)
    if not columns:
        return []
    schema: list[dict[str, Any]] = []
    alias_owners: dict[str, set[int]] = defaultdict(set)
    for index, raw in enumerate(columns):
        display = ledger._display(raw)
        aliases: list[str] = []
        for candidate in (display, *structure._group_parts(display)):
            canonical = ledger._canonical(candidate)
            if canonical and canonical not in aliases:
                aliases.append(canonical)
        if not aliases:
            return []
        schema.append({"index": index, "display": display, "aliases": aliases})
        for alias in aliases:
            alias_owners[alias].add(index)
    for column in schema:
        column["aliases"] = [
            alias
            for alias in column["aliases"]
            if alias_owners[alias] == {int(column["index"])}
        ]
        if not column["aliases"]:
            return []
    return schema


def _full_page_table_records(
    page: Mapping[str, Any], schema: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    """Parse one complete decoded table without crossing its page boundary.

    The inherited atomic ledger intentionally keeps 1,200-character groups and
    therefore cannot bind a late row to a header in an earlier group.  Here an
    exact visible header starts a page-local table scope.  Only contiguous,
    equal-width pipe rows are admitted; prose, malformed width, a new header,
    or the page boundary closes the scope.
    """

    lines = str(page["content"]).splitlines()
    records: list[dict[str, Any]] = []
    table_count = 0
    index = 0
    while index < len(lines) and len(records) < ledger.MAXIMUM_RECORDS:
        header_cells = _pipe_cells_preserving_surface(lines[index])
        header = (
            ledger._header_mapping(header_cells, schema)
            if header_cells is not None
            else None
        )
        if header is None:
            index += 1
            continue
        table_count += 1
        row_index = index + 1
        if row_index < len(lines):
            possible_separator = _pipe_cells_preserving_surface(lines[row_index])
            if possible_separator is not None and ledger._separator(possible_separator):
                row_index += 1
        record_ordinal = 0
        while row_index < len(lines) and len(records) < ledger.MAXIMUM_RECORDS:
            cells = _pipe_cells_preserving_surface(lines[row_index])
            if cells is None or ledger._header_mapping(cells, schema) is not None:
                break
            if len(cells) != int(header["width"]) or ledger._separator(cells):
                break
            row_key = _safe_identity_surface(
                cells[int(header["identity_position"])],
            )
            fields: dict[int, str] = {}
            if row_key is not None:
                for target_index, position in header["target_positions"].items():
                    field = ledger._safe_surface(
                        cells[int(position)], maximum=ledger.MAXIMUM_VALUE_CHARACTERS
                    )
                    if field is not None:
                        fields[int(target_index)] = field
            if row_key is not None and fields:
                record_ordinal += 1
                records.append(
                    ledger._record(
                        page=page,
                        binding="robust_full_page_header_bound_table",
                        group_ordinal=table_count,
                        record_ordinal=record_ordinal,
                        identity_block_ordinal=index + 1,
                        value_block_ordinal=row_index + 1,
                        row_key=row_key,
                        fields=fields,
                        schema=schema,
                    )
                )
            row_index += 1
        index = max(index + 1, row_index)
    return records, table_count


def _pipe_cells_preserving_surface(line: str) -> list[str] | None:
    raw = unicodedata.normalize("NFKC", str(line)).strip()
    if "|" not in raw:
        return None
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    cells = [re.sub(r"\s+", " ", value).strip() for value in raw.split("|")]
    return cells if 2 <= len(cells) <= 64 else None


def _safe_identity_surface(value: object) -> str | None:
    """Preserve visible identity punctuation while rejecting unsafe surfaces."""

    text = " ".join(unicodedata.normalize("NFKC", str(value or "")).split())
    text = text.strip(" |\t\r\n")
    if (
        not text
        or len(text) > ledger.MAXIMUM_ROW_KEY_CHARACTERS
        or "\x00" in text
        or any(ord(character) < 32 for character in text)
        or ledger._canonical(text) in ledger._UNKNOWN
    ):
        return None
    return text


def _dedupe_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for raw in records:
        key = (
            str(raw["source_url"]),
            ledger._canonical(raw["row_key"]),
            tuple(
                (
                    int(field["target_index"]),
                    ledger._canonical(field["value"]),
                )
                for field in raw["fields"]
            ),
        )
        if key in seen:
            continue
        output.append(copy.deepcopy(dict(raw)))
        seen.add(key)
    return output[: ledger.MAXIMUM_RECORDS]


def _schema_receipt(
    schema: list[dict[str, Any]], *, table_count: int, table_record_count: int
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "robust_visible_schema_column_count": len(schema),
        "full_page_header_bound_table_count": int(table_count),
        "full_page_table_record_count": int(table_record_count),
        "robust_visible_schema_applied": bool(schema),
        "sentence_bracket_quote_aware_parser_used": True,
        "legacy_greedy_column_parser_used": False,
        "question_column_name_or_alias_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = parent.payload_sha256(value)
    return validate_schema_receipt(value)


def validate_schema_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    count = copied.get("robust_visible_schema_column_count")
    table_count = copied.get("full_page_header_bound_table_count")
    record_count = copied.get("full_page_table_record_count")
    false_flags = (
        "legacy_greedy_column_parser_used",
        "question_column_name_or_alias_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(count, bool)
        or not isinstance(count, int)
        or not 0 <= count <= ledger.MAXIMUM_SCHEMA_COLUMNS
        or isinstance(table_count, bool)
        or not isinstance(table_count, int)
        or table_count < 0
        or isinstance(record_count, bool)
        or not isinstance(record_count, int)
        or not 0 <= record_count <= ledger.MAXIMUM_RECORDS
        or (count == 0 and (table_count != 0 or record_count != 0))
        or copied.get("robust_visible_schema_applied") is not (count > 0)
        or copied.get("sentence_bracket_quote_aware_parser_used") is not True
        or any(copied.get(name) is not False for name in false_flags)
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.84 robust-schema receipt drifted")
    return copied


def build_projection(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.84 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.49.84 parent page cap drifted")
    normalized_page, raw_text = parent._page(page)
    raw_prefix = raw_text[:PAGE_CHARACTER_CAP]
    schema: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    conflicts: set[tuple[str, int]] = set()
    eligible: list[dict[str, Any]] = []
    observations = 0
    oversized = 0
    full_table_count = 0
    full_table_record_count = 0
    failure = 0
    try:
        stable = structure._stable_pages([normalized_page])
        if len(stable) != 1 or stable[0]["url"] != normalized_page["url"]:
            raise ValueError("V2.49.84 stable page identity drifted")
        schema = _robust_schema(question)
        if schema:
            inherited_records, _counts = discovery._discover(stable, schema)
            full_records, full_table_count = _full_page_table_records(
                stable[0], schema
            )
            full_table_record_count = len(full_records)
            records = _dedupe_records([*full_records, *inherited_records])
            conflicts, _hosts, _urls = ledger._coordinate_summary(records)
            eligible, observations, oversized = parent._eligible_records(
                records, conflicts
            )
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        schema = []
        records = []
        conflicts = set()
        eligible = []
        observations = 0
        oversized = 0
        full_table_count = 0
        full_table_record_count = 0

    ranked = parent._ranked(eligible, question=question) if eligible and schema else []
    retained: list[dict[str, Any]] = []
    projection = raw_prefix
    compact_chars = 0
    raw_retained = len(raw_prefix)
    if ranked and schema and failure == 0:
        header = parent._compact_header(normalized_page, schema)
        footer = "[/IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]"
        raw_marker = "\n[INHERITED RAW PAGE PREFIX]\n"
        output_budget = len(raw_prefix)
        fixed = len(header) + 1 + len(footer) + len(raw_marker)
        for record in ranked:
            line = str(record["line"])
            line_cost = len(line) + 1
            used = fixed + sum(len(str(item["line"])) + 1 for item in retained)
            if (
                used + line_cost + parent.MINIMUM_RAW_PREFIX_CHARACTERS
                <= output_budget
            ):
                retained.append(record)
        if retained:
            compact = (
                header
                + "\n"
                + "\n".join(str(record["line"]) for record in retained)
                + "\n"
                + footer
            )
            raw_budget = len(raw_prefix) - len(compact) - len(raw_marker)
            if raw_budget >= parent.MINIMUM_RAW_PREFIX_CHARACTERS:
                projection = compact + raw_marker + raw_text[:raw_budget]
                compact_chars = len(compact)
                raw_retained = min(len(raw_text), raw_budget)
            else:
                retained = []

    changed = projection != raw_prefix
    if not changed:
        retained = []
        compact_chars = 0
        raw_retained = len(raw_prefix)
        projection = raw_prefix
    retained_observations = sum(len(record["fields"]) for record in retained)
    parent_receipt = parent._receipt(
        {
            "input_page_count": 1,
            "input_content_characters": len(raw_text),
            "input_characters_beyond_parent_prefix": max(
                0, len(raw_text) - PAGE_CHARACTER_CAP
            ),
            "visible_schema_column_count": len(schema),
            "discovered_record_count": len(records),
            "discovered_row_key_count": len(
                {ledger._canonical(record["row_key"]) for record in records}
            ),
            "conflicting_coordinate_count": len(conflicts),
            "admissible_record_count": len(eligible),
            "admissible_bound_observation_count": observations,
            "retained_record_count": len(retained),
            "retained_bound_observation_count": retained_observations,
            "oversized_record_count": oversized,
            "compact_prefix_characters": compact_chars,
            "raw_prefix_characters_retained": raw_retained,
            "output_characters": len(projection),
            "projection_failure_count": failure,
            "positive_signed_credit_count": 0,
            "candidate_evidence_changed": changed,
            "mechanism_engaged": bool(retained) and changed and failure == 0,
            "exact_parent_prefix_handoff": not changed,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode("utf-8")).hexdigest(),
        # Kept byte-compatible with V2.49.81's frozen helper boundary.
        "content_free_receipt": parent_receipt,
        "robust_schema_receipt": _schema_receipt(
            schema,
            table_count=full_table_count,
            table_record_count=full_table_record_count,
        ),
        "same_forward_decoded_page_only": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["artifact_payload_sha256"] = parent.payload_sha256(value)
    return validate_projection(
        value,
        question=question,
        page=page,
        page_character_cap=page_character_cap,
        replay=False,
    )


def validate_projection(
    value: Mapping[str, Any],
    *,
    question: str,
    page: Mapping[str, Any],
    page_character_cap: int = PAGE_CHARACTER_CAP,
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    projection = copied.get("projection")
    parent_receipt = copied.get("content_free_receipt")
    schema_receipt = copied.get("robust_schema_receipt")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(projection, str)
        or len(projection) > page_character_cap
        or copied.get("projection_sha256")
        != hashlib.sha256(projection.encode("utf-8")).hexdigest()
        or not isinstance(parent_receipt, Mapping)
        or parent.validate_receipt(parent_receipt) != dict(parent_receipt)
        or parent_receipt.get("output_characters") != len(projection)
        or not isinstance(schema_receipt, Mapping)
        or validate_schema_receipt(schema_receipt) != dict(schema_receipt)
        or schema_receipt.get("robust_visible_schema_column_count")
        != parent_receipt.get("visible_schema_column_count")
        or copied.get("same_forward_decoded_page_only") is not True
        or copied.get(
            "additional_search_fetch_model_token_context_wall_or_network_byte_cap"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.84 robust late-page projection drifted")
    if replay and copied != build_projection(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError("V2.49.84 robust late-page projection is not reproducible")
    return copied


__all__ = [
    "MAXIMUM_INPUT_PAGE_CHARACTERS",
    "PAGE_CHARACTER_CAP",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_projection",
    "validate_projection",
    "validate_schema_receipt",
]
