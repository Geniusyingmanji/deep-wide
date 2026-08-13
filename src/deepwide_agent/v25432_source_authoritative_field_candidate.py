"""Pure source-coordinate field candidates for one shared production table.

V2.54.31 showed that a guard can remove harmful generated edits but cannot
create a beneficial edit.  This build-only primitive reverses the proposal
order: values are first extracted mechanically from structured text already
present in same-forward fetched pages.  A later model, if any, may return only
candidate IDs or abstain; it cannot author an identity, field, or value.

Every admitted candidate binds all of the following in one replayable source
coordinate: canonical HTTPS source, page ordinal, exact contiguous quote,
source identity, exact visible field, exact source value, unique production
row, and unique non-key table coordinate.  Horizontal tables, vertical
key/value records, exact labelled records, and flat JSON objects are accepted.
Unknown values, nonunique quotes, missing or duplicate rows, multiple source
coordinates for one table coordinate, value conflicts, list collapse, and
schema/key/shape changes fail closed.  No admission or invalid selection
returns the parent prediction byte-for-byte.

"Source-authoritative" here means authority over the exact published source
coordinate and value.  It does not infer first-party reputation from a host;
official/first-party page selection remains a separate visible-only routing
obligation.  This module has no file, environment, process, network, model,
search, fetch, evaluator, benchmark-label, mapping, gold, score, reward,
credential, or historical-result capability.  Entropy/information gain is
shadow-only and assigns no signed credit.  This build grants no launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from . import v24743_generic_record_binding as table_parent


POLICY_ID = "v25432_source_authoritative_field_candidate_v1"
REGISTRY_ROLE = "v25432_source_authoritative_field_candidate_registry"
REGISTRY_RECEIPT_ROLE = "v25432_content_free_candidate_registry_receipt"
APPLICATION_ROLE = "v25432_source_authoritative_candidate_application"
APPLICATION_RECEIPT_ROLE = "v25432_content_free_candidate_application_receipt"

PAGE_KEYS = frozenset({"url", "title", "content"})
MAXIMUM_PAGE_COUNT = 14
MAXIMUM_PAGE_CHARACTERS = 120_000
MAXIMUM_TOTAL_PAGE_CHARACTERS = 600_000
MAXIMUM_QUOTE_CHARACTERS = 2_000
MAXIMUM_STRUCTURED_SURFACES = 512
MAXIMUM_CANDIDATES = 80
MAXIMUM_CELL_CHARACTERS = 500
MAXIMUM_SELECTOR_IDS = 80

LIST_COLUMN_KEYS = frozenset(
    {
        "author",
        "authors",
        "contributor",
        "contributors",
        "member",
        "members",
        "participant",
        "participants",
        "owner",
        "owners",
        "creator",
        "creators",
    }
)
LIST_SEPARATOR = re.compile(r"\s*(?:;|,|\band\b|&)\s*", re.I)
_SELECTOR_ID = re.compile(r"C[0-9]{3}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SOURCE_KINDS = frozenset(
    {
        "exact_horizontal_markdown_table",
        "exact_vertical_key_value_record",
        "exact_contiguous_labelled_record",
        "exact_flat_json_record",
    }
)
CONTENT_FREE_FLAG = (
    "contains_question_prediction_query_url_quote_identity_field_value_"
    "answer_hash_opaque_id_or_credential"
)
PRIVILEGED_READ_FLAG = (
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_"
    "historical_result_read"
)
_CANDIDATE_KEYS = frozenset(
    {
        "candidate_id",
        "page_ordinal",
        "source_url",
        "source_host",
        "quote_start",
        "quote_end",
        "exact_quote",
        "source_identity",
        "row_identity",
        "source_field",
        "field",
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

_REGISTRY_COUNT_FIELDS = (
    "input_page_count",
    "accepted_page_count",
    "rejected_page_count",
    "accepted_page_character_count",
    "horizontal_table_surface_count",
    "vertical_record_surface_count",
    "labelled_record_surface_count",
    "json_record_surface_count",
    "raw_observation_attempt_count",
    "evidence_closed_observation_count",
    "nonunique_or_oversized_quote_rejected_count",
    "unknown_or_unsafe_value_rejected_count",
    "missing_row_rejected_count",
    "missing_or_key_field_rejected_count",
    "coordinate_group_count",
    "exact_duplicate_observation_count",
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


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _surface(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _key(value: object) -> str:
    return _surface(value).casefold()


def _column_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", _key(value))


def _safe_cell(value: object) -> str | None:
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    raw = str(value).strip()
    text = _surface(raw)
    if (
        not text
        or text != raw
        or len(text) > MAXIMUM_CELL_CHARACTERS
        or any(ord(character) < 32 for character in text)
        or "|" in text
        or "```" in text
        or table_parent._is_unknown(text)
    ):
        return None
    return text


def _list_cardinality(value: object) -> int:
    text = _surface(value)
    if not text:
        return 0
    return len([part for part in LIST_SEPARATOR.split(text) if part])


def _canonical_table(
    prediction: str, columns: Sequence[str]
) -> tuple[tuple[str, ...], list[list[str]]]:
    if isinstance(columns, (str, bytes)) or not isinstance(columns, Sequence):
        raise ValueError("V2.54.32 visible columns are not a sequence")
    required = tuple(str(value).strip() for value in columns)
    if (
        not 2 <= len(required) <= 32
        or any(not value or any(char in value for char in "|\r\n\x00") for value in required)
        or len({_key(value) for value in required}) != len(required)
    ):
        raise ValueError("V2.54.32 visible column vector drifted")
    parsed_columns, rows = table_parent._baseline_matrix(str(prediction))
    if (
        tuple(parsed_columns) != required
        or table_parent._render_table(parsed_columns, rows) != str(prediction)
    ):
        raise ValueError("V2.54.32 parent table is not exact canonical form")
    return required, [list(row) for row in rows]


def _canonical_url(raw: object) -> tuple[str, str] | None:
    try:
        parsed = urlsplit(str(raw or ""))
        port = parsed.port
    except ValueError:
        return None
    host = (parsed.hostname or "").casefold().strip(".")
    if (
        parsed.scheme.casefold() != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port is not None
        or ":" in host
    ):
        return None
    try:
        table_parent._source_key(host)
    except ValueError:
        return None
    return parsed._replace(scheme="https", netloc=host).geturl(), host


def _pages(
    pages: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("V2.54.32 page vector is not a sequence")
    if len(pages) > MAXIMUM_PAGE_COUNT:
        raise ValueError("V2.54.32 page count exceeds the frozen fetch cap")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    used = 0
    rejected = 0
    for ordinal, raw in enumerate(pages, 1):
        if not isinstance(raw, Mapping) or set(raw) != PAGE_KEYS:
            raise ValueError("V2.54.32 page schema drifted")
        canonical = _canonical_url(raw.get("url"))
        title = raw.get("title")
        content = raw.get("content")
        if (
            canonical is None
            or not isinstance(title, str)
            or len(title) > 500
            or not isinstance(content, str)
            or not content
            or "\x00" in content
            or len(content) > MAXIMUM_PAGE_CHARACTERS
            or used + len(content) > MAXIMUM_TOTAL_PAGE_CHARACTERS
            or canonical[0] in seen
        ):
            rejected += 1
            continue
        seen.add(canonical[0])
        used += len(content)
        output.append(
            {
                "page_ordinal": ordinal,
                "source_url": canonical[0],
                "source_host": canonical[1],
                "content": content,
            }
        )
    return output, {
        "input_page_count": len(pages),
        "accepted_page_count": len(output),
        "rejected_page_count": rejected,
        "accepted_page_character_count": used,
    }


def _line_spans(content: str) -> list[tuple[int, int, str]]:
    output: list[tuple[int, int, str]] = []
    offset = 0
    for raw in content.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        output.append((offset, offset + len(line), line))
        offset += len(raw)
    if not output and content:
        output.append((0, len(content), content))
    return output


def _pipe_cells(line: str) -> list[str] | None:
    raw = unicodedata.normalize("NFKC", str(line)).strip()
    if "|" not in raw or "\\|" in raw:
        return None
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    values = [value.strip() for value in raw.split("|")]
    return values if 2 <= len(values) <= 64 and all(values) else None


def _separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", value.replace(" ", "")) is not None
        for value in cells
    )


def _strict_json_object(raw: str) -> dict[str, Any] | None:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for name, value in pairs:
            if name in output:
                raise ValueError("duplicate JSON key")
            output[name] = value
        return output

    try:
        value = json.loads(raw, object_pairs_hook=hook)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _observation_key(value: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(value["page_ordinal"]),
        int(value["quote_start"]),
        int(value["quote_end"]),
        int(value["row_index"]),
        int(value["column_index"]),
        str(value["exact_value"]),
    )


def _check_surface_cap(counts: Mapping[str, int]) -> None:
    total = sum(
        int(counts.get(name, 0))
        for name in (
            "horizontal_table_surface_count",
            "vertical_record_surface_count",
            "labelled_record_surface_count",
            "json_record_surface_count",
        )
    )
    if total > MAXIMUM_STRUCTURED_SURFACES:
        raise ValueError("V2.54.32 structured surface cap exceeded")


def _offer(
    observations: list[dict[str, Any]],
    counts: Counter[str],
    *,
    page: Mapping[str, Any],
    quote_start: int,
    quote_end: int,
    source_identity: object,
    source_field: object,
    source_value: object,
    source_kind: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    row_map: Mapping[str, list[int]],
    column_map: Mapping[str, list[int]],
) -> None:
    counts["raw_observation_attempt_count"] += 1
    content = str(page["content"])
    quote = content[quote_start:quote_end]
    if (
        not 1 <= len(quote) <= MAXIMUM_QUOTE_CHARACTERS
        or content.count(quote) != 1
    ):
        counts["nonunique_or_oversized_quote_rejected_count"] += 1
        return
    raw_identity = str(source_identity).strip()
    raw_field = str(source_field).strip()
    value = _safe_cell(source_value)
    if value is None:
        counts["unknown_or_unsafe_value_rejected_count"] += 1
        return
    row_matches = row_map.get(_key(raw_identity), [])
    if len(row_matches) != 1:
        counts["missing_row_rejected_count"] += 1
        return
    column_matches = column_map.get(_key(raw_field), [])
    if len(column_matches) != 1 or column_matches[0] == 0:
        counts["missing_or_key_field_rejected_count"] += 1
        return
    if not raw_identity or not raw_field or any(
        needle not in quote for needle in (raw_identity, raw_field, value)
    ):
        counts["nonunique_or_oversized_quote_rejected_count"] += 1
        return
    row_index = row_matches[0]
    column_index = column_matches[0]
    observations.append(
        {
            "page_ordinal": int(page["page_ordinal"]),
            "source_url": str(page["source_url"]),
            "source_host": str(page["source_host"]),
            "quote_start": int(quote_start),
            "quote_end": int(quote_end),
            "exact_quote": quote,
            "source_identity": raw_identity,
            "row_identity": str(rows[row_index][0]),
            "source_field": raw_field,
            "field": str(columns[column_index]),
            "old_value": str(rows[row_index][column_index]),
            "exact_value": value,
            "source_kind": str(source_kind),
            "row_index": row_index,
            "column_index": column_index,
        }
    )
    counts["evidence_closed_observation_count"] += 1


def _horizontal_tables(
    page: Mapping[str, Any],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    row_map: Mapping[str, list[int]],
    column_map: Mapping[str, list[int]],
    observations: list[dict[str, Any]],
    counts: Counter[str],
) -> None:
    content = str(page["content"])
    lines = _line_spans(content)
    expected = [_key(value) for value in columns]
    index = 0
    while index + 1 < len(lines):
        header = _pipe_cells(lines[index][2])
        rule = _pipe_cells(lines[index + 1][2])
        if (
            header is None
            or rule is None
            or len(header) != len(columns)
            or [_key(value) for value in header] != expected
            or len(rule) != len(header)
            or not _separator(rule)
        ):
            index += 1
            continue
        counts["horizontal_table_surface_count"] += 1
        _check_surface_cap(counts)
        cursor = index + 2
        while cursor < len(lines):
            cells = _pipe_cells(lines[cursor][2])
            if cells is None or len(cells) != len(header) or _separator(cells):
                break
            for column_index in range(1, len(columns)):
                _offer(
                    observations,
                    counts,
                    page=page,
                    quote_start=lines[index][0],
                    quote_end=lines[cursor][1],
                    source_identity=cells[0],
                    source_field=header[column_index],
                    source_value=cells[column_index],
                    source_kind="exact_horizontal_markdown_table",
                    columns=columns,
                    rows=rows,
                    row_map=row_map,
                    column_map=column_map,
                )
            cursor += 1
        index = max(index + 1, cursor)


def _pipe_blocks(content: str) -> list[list[tuple[int, int, list[str]]]]:
    blocks: list[list[tuple[int, int, list[str]]]] = []
    current: list[tuple[int, int, list[str]]] = []
    for start, end, line in _line_spans(content):
        cells = _pipe_cells(line)
        if cells is not None and len(cells) == 2:
            current.append((start, end, cells))
            continue
        if current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _vertical_records(
    page: Mapping[str, Any],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    row_map: Mapping[str, list[int]],
    column_map: Mapping[str, list[int]],
    observations: list[dict[str, Any]],
    counts: Counter[str],
) -> None:
    content = str(page["content"])
    for block in _pipe_blocks(content):
        data = [entry for entry in block if not _separator(entry[2])]
        recognized: list[tuple[int, int, int, str, str]] = []
        seen: set[int] = set()
        invalid = False
        for start, end, cells in data:
            matches = column_map.get(_key(cells[0]), [])
            if not matches:
                continue
            if len(matches) != 1 or matches[0] in seen:
                invalid = True
                break
            seen.add(matches[0])
            recognized.append((start, end, matches[0], cells[0], cells[1]))
        identities = [entry for entry in recognized if entry[2] == 0]
        targets = [entry for entry in recognized if entry[2] > 0]
        if invalid or len(identities) != 1 or not targets:
            continue
        counts["vertical_record_surface_count"] += 1
        _check_surface_cap(counts)
        quote_start = block[0][0]
        quote_end = block[-1][1]
        for _start, _end, _field_index, source_field, source_value in targets:
            _offer(
                observations,
                counts,
                page=page,
                quote_start=quote_start,
                quote_end=quote_end,
                source_identity=identities[0][4],
                source_field=source_field,
                source_value=source_value,
                source_kind="exact_vertical_key_value_record",
                columns=columns,
                rows=rows,
                row_map=row_map,
                column_map=column_map,
            )


def _label_pair(
    line: str, columns: Sequence[str], column_map: Mapping[str, list[int]]
) -> tuple[int, str, str] | None:
    raw = str(line).strip()
    raw = re.sub(r"^(?:[-*]\s+)", "", raw)
    match = re.fullmatch(r"([^:=：\t]{1,120})\s*[:=：\t]\s*(.+?)\s*", raw)
    if match is None:
        return None
    source_field = match.group(1).strip()
    matches = column_map.get(_key(source_field), [])
    if len(matches) != 1:
        return None
    return matches[0], source_field, match.group(2).strip()


def _labelled_records(
    page: Mapping[str, Any],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    row_map: Mapping[str, list[int]],
    column_map: Mapping[str, list[int]],
    observations: list[dict[str, Any]],
    counts: Counter[str],
) -> None:
    content = str(page["content"])
    lines = _line_spans(content)
    index = 0
    while index < len(lines):
        start, _end, line = lines[index]
        first = _label_pair(line, columns, column_map)
        pairs: list[tuple[int, int, int, str, str]] = []
        source_identity: str | None = None
        cursor = index
        if first is not None:
            while cursor < len(lines):
                pair = _label_pair(lines[cursor][2], columns, column_map)
                if pair is None:
                    break
                pairs.append(
                    (lines[cursor][0], lines[cursor][1], pair[0], pair[1], pair[2])
                )
                cursor += 1
            identity_pairs = [entry for entry in pairs if entry[2] == 0]
            if len(identity_pairs) == 1:
                source_identity = identity_pairs[0][4]
        else:
            heading = str(line).strip()
            heading = re.sub(r"^#{1,6}\s+", "", heading)
            heading = re.sub(r"^\*\*(.*?)\*\*$", r"\1", heading).strip(" :：")
            if len(row_map.get(_key(heading), [])) == 1:
                source_identity = heading
                cursor = index + 1
                while cursor < len(lines):
                    pair = _label_pair(lines[cursor][2], columns, column_map)
                    if pair is None or pair[0] == 0:
                        break
                    pairs.append(
                        (
                            lines[cursor][0],
                            lines[cursor][1],
                            pair[0],
                            pair[1],
                            pair[2],
                        )
                    )
                    cursor += 1
        targets = [entry for entry in pairs if entry[2] > 0]
        target_fields = [entry[2] for entry in targets]
        if source_identity is not None and targets and len(set(target_fields)) == len(
            target_fields
        ):
            counts["labelled_record_surface_count"] += 1
            _check_surface_cap(counts)
            quote_end = lines[max(index, cursor - 1)][1]
            for _pair_start, _pair_end, _field_index, source_field, value in targets:
                _offer(
                    observations,
                    counts,
                    page=page,
                    quote_start=start,
                    quote_end=quote_end,
                    source_identity=source_identity,
                    source_field=source_field,
                    source_value=value,
                    source_kind="exact_contiguous_labelled_record",
                    columns=columns,
                    rows=rows,
                    row_map=row_map,
                    column_map=column_map,
                )
            index = max(index + 1, cursor)
            continue
        index += 1


def _json_records(
    page: Mapping[str, Any],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    row_map: Mapping[str, list[int]],
    column_map: Mapping[str, list[int]],
    observations: list[dict[str, Any]],
    counts: Counter[str],
) -> None:
    content = str(page["content"])
    decoder = json.JSONDecoder()
    cursor = 0
    surfaces = 0
    while cursor < len(content) and surfaces < MAXIMUM_STRUCTURED_SURFACES:
        start = content.find("{", cursor)
        if start < 0:
            break
        try:
            _ignored, relative_end = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            cursor = start + 1
            continue
        end = start + relative_end
        raw = content[start:end]
        payload = _strict_json_object(raw)
        cursor = max(start + 1, end)
        if payload is None or len(raw) > MAXIMUM_QUOTE_CHARACTERS:
            continue
        pairs: list[tuple[int, str, object]] = []
        seen: set[int] = set()
        invalid = False
        for source_field, value in payload.items():
            matches = column_map.get(_key(source_field), [])
            if not matches:
                continue
            if (
                len(matches) != 1
                or matches[0] in seen
                or isinstance(value, (Mapping, list, bool))
            ):
                invalid = True
                break
            seen.add(matches[0])
            pairs.append((matches[0], str(source_field), value))
        identities = [entry for entry in pairs if entry[0] == 0]
        targets = [entry for entry in pairs if entry[0] > 0]
        if invalid or len(identities) != 1 or not targets:
            continue
        surfaces += 1
        counts["json_record_surface_count"] += 1
        _check_surface_cap(counts)
        for _field_index, source_field, value in targets:
            _offer(
                observations,
                counts,
                page=page,
                quote_start=start,
                quote_end=end,
                source_identity=identities[0][2],
                source_field=source_field,
                source_value=value,
                source_kind="exact_flat_json_record",
                columns=columns,
                rows=rows,
                row_map=row_map,
                column_map=column_map,
            )


def _candidate(observation: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    value = {
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
                "source_identity",
                "row_identity",
                "source_field",
                "field",
                "old_value",
                "exact_value",
                "source_kind",
            )
        },
        "source_coordinate_is_unique": True,
        "target_table_coordinate_is_unique": True,
        "value_is_source_extracted_not_model_generated": True,
        "nonunknown_and_materially_differs_from_base": True,
        "list_cardinality_noncollapse": True,
    }
    value["candidate_payload_sha256"] = payload_sha256(value)
    return value


def _validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("candidate_payload_sha256", None)
    canonical = _canonical_url(copied.get("source_url"))
    quote = copied.get("exact_quote")
    identity = copied.get("source_identity")
    row_identity = copied.get("row_identity")
    source_field = copied.get("source_field")
    field = copied.get("field")
    old_value = copied.get("old_value")
    exact_value = copied.get("exact_value")
    true_flags = (
        "source_coordinate_is_unique",
        "target_table_coordinate_is_unique",
        "value_is_source_extracted_not_model_generated",
        "nonunknown_and_materially_differs_from_base",
        "list_cardinality_noncollapse",
    )
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
        or not 1 <= len(quote) <= MAXIMUM_QUOTE_CHARACTERS
        or any(
            not isinstance(item, str)
            or not item
            or "\x00" in item
            or "\r" in item
            or "\n" in item
            for item in (
                identity,
                row_identity,
                source_field,
                field,
                old_value,
                exact_value,
            )
        )
        or any(item not in quote for item in (identity, source_field, exact_value))
        or _safe_cell(exact_value) != exact_value
        or _key(old_value) == _key(exact_value)
        or copied.get("source_kind") not in _SOURCE_KINDS
        or any(copied.get(name) is not True for name in true_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.32 candidate schema drifted")
    if (
        _column_key(field) in LIST_COLUMN_KEYS
        and _list_cardinality(old_value) >= 2
        and _list_cardinality(exact_value) < _list_cardinality(old_value)
    ):
        raise ValueError("V2.54.32 candidate list cardinality drifted")
    return copied


def _registry_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value.get(name, 0)) for name in _REGISTRY_COUNT_FIELDS},
        "only_same_forward_injected_pages_consumed": True,
        "canonical_https_source_and_exact_quote_coordinate_required": True,
        "exact_visible_identity_and_field_binding_required": True,
        "one_unique_source_coordinate_per_target_coordinate_required": True,
        "value_is_mechanically_extracted_before_any_selection": True,
        "model_may_only_select_candidate_ids_or_abstain": True,
        "unknown_conflict_missing_row_list_collapse_or_shape_key_change_fails_closed": True,
        "source_authority_is_coordinate_provenance_not_host_reputation": True,
        "first_party_or_official_reputation_inferred": False,
        CONTENT_FREE_FLAG: False,
        PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_registry_receipt(output)


def _build_registry(
    base_prediction: str,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    required, rows = _canonical_table(str(base_prediction), columns)
    bounded, page_counts = _pages(pages)
    row_map: defaultdict[str, list[int]] = defaultdict(list)
    column_map: defaultdict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        row_map[_key(row[0])].append(index)
    for index, field in enumerate(required):
        column_map[_key(field)].append(index)
    observations: list[dict[str, Any]] = []
    counts: Counter[str] = Counter(page_counts)
    for page in bounded:
        kwargs = {
            "columns": required,
            "rows": rows,
            "row_map": row_map,
            "column_map": column_map,
            "observations": observations,
            "counts": counts,
        }
        _horizontal_tables(page, **kwargs)
        _vertical_records(page, **kwargs)
        _labelled_records(page, **kwargs)
        _json_records(page, **kwargs)

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
        exact_values = {_key(item["exact_value"]) for item in values}
        if len(values) != 1:
            name = (
                "conflicting_value_coordinate_count"
                if len(exact_values) > 1
                else "ambiguous_same_value_coordinate_count"
            )
            counts[name] += 1
            continue
        item = values[0]
        if _key(item["old_value"]) == _key(item["exact_value"]):
            counts["unchanged_coordinate_count"] += 1
            continue
        if (
            _column_key(item["field"]) in LIST_COLUMN_KEYS
            and _list_cardinality(item["old_value"]) >= 2
            and _list_cardinality(item["exact_value"])
            < _list_cardinality(item["old_value"])
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
    for name in (
        "positive_signed_credit_count",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_calls",
        "additional_fetch_calls",
        "additional_provider_tokens",
    ):
        counts[name] = 0
    receipt = _registry_receipt(counts)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_ROLE,
        "policy_id": POLICY_ID,
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode("utf-8")
        ).hexdigest(),
        "page_vector_sha256": payload_sha256(
            [
                {
                    "page_ordinal": page["page_ordinal"],
                    "source_url": page["source_url"],
                    "content": page["content"],
                }
                for page in bounded
            ]
        ),
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
    """Build and replay-validate the deterministic candidate registry."""

    value = _build_registry(base_prediction, columns, pages)
    return validate_registry(
        value, base_prediction=base_prediction, columns=columns, pages=pages
    )


def validate_registry_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "only_same_forward_injected_pages_consumed",
        "canonical_https_source_and_exact_quote_coordinate_required",
        "exact_visible_identity_and_field_binding_required",
        "one_unique_source_coordinate_per_target_coordinate_required",
        "value_is_mechanically_extracted_before_any_selection",
        "model_may_only_select_candidate_ids_or_abstain",
        "unknown_conflict_missing_row_list_collapse_or_shape_key_change_fails_closed",
        "source_authority_is_coordinate_provenance_not_host_reputation",
    )
    false_flags = (
        "first_party_or_official_reputation_inferred",
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
        *_REGISTRY_COUNT_FIELDS,
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
            for name in _REGISTRY_COUNT_FIELDS
        )
        or copied["accepted_page_count"] + copied["rejected_page_count"]
        != copied["input_page_count"]
        or copied["accepted_page_count"] > MAXIMUM_PAGE_COUNT
        or copied["accepted_page_character_count"] > MAXIMUM_TOTAL_PAGE_CHARACTERS
        or copied["available_candidate_count"] > MAXIMUM_CANDIDATES
        or copied["evidence_closed_observation_count"]
        > copied["raw_observation_attempt_count"]
        or copied["coordinate_group_count"]
        > copied["evidence_closed_observation_count"]
        or copied["positive_signed_credit_count"] != 0
        or any(copied[name] != 0 for name in _REGISTRY_COUNT_FIELDS[-5:])
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.32 candidate registry receipt drifted")
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
        or not isinstance(copied.get("base_prediction_sha256"), str)
        or not isinstance(copied.get("page_vector_sha256"), str)
        or _SHA256.fullmatch(copied["base_prediction_sha256"]) is None
        or _SHA256.fullmatch(copied["page_vector_sha256"]) is None
        or not isinstance(candidates, list)
        or len(candidates) > MAXIMUM_CANDIDATES
        or not isinstance(receipt, Mapping)
        or validate_registry_receipt(receipt) != dict(receipt)
        or receipt["available_candidate_count"] != len(candidates)
        or any(
            not isinstance(candidate, Mapping)
            or _validate_candidate(candidate) != dict(candidate)
            or candidate.get("candidate_id") != f"C{index:03d}"
            or candidate.get("candidate_payload_sha256")
            != payload_sha256(
                {
                    key: candidate[key]
                    for key in candidate
                    if key != "candidate_payload_sha256"
                }
            )
            for index, candidate in enumerate(candidates, 1)
        )
        or len(
            {
                (_key(candidate["row_identity"]), _key(candidate["field"]))
                for candidate in candidates
            }
        )
        != len(candidates)
        or len(
            {
                (
                    candidate["page_ordinal"],
                    candidate["quote_start"],
                    candidate["quote_end"],
                    _key(candidate["row_identity"]),
                    _key(candidate["field"]),
                )
                for candidate in candidates
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
        raise ValueError("V2.54.32 candidate registry drifted")
    supplied = (base_prediction is not None, columns is not None, pages is not None)
    if any(supplied) and not all(supplied):
        raise ValueError("V2.54.32 replay inputs must be supplied together")
    if all(supplied):
        assert base_prediction is not None and columns is not None and pages is not None
        if _build_registry(base_prediction, columns, pages) != copied:
            raise ValueError("V2.54.32 candidate registry replay drifted")
    return copied


def _selector(value: object) -> tuple[bool, list[str]]:
    if not isinstance(value, str):
        return False, []
    parsed = _strict_json_object(value)
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
        "parent_prediction_byte_exact_on_zero_admission_or_invalid_selection": True,
        "selected_values_replayed_from_registry_not_selector": True,
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
    """Apply only replayed candidate IDs; invalid/free-form output is a no-op."""

    required, rows = _canonical_table(str(base_prediction), columns)
    registry = build_candidate_registry(
        base_prediction, columns=required, pages=pages
    )
    valid, requested = _selector(selector_output)
    by_id = {item["candidate_id"]: item for item in registry["candidates"]}
    known = bool(valid and all(name in by_id for name in requested))
    selected = [by_id[name] for name in requested] if known else []
    coordinate_set = {
        (_key(item["row_identity"]), _key(item["field"])) for item in selected
    }
    if len(coordinate_set) != len(selected):
        selected = []
        known = False
    selected_ids = [item["candidate_id"] for item in selected]
    candidate = str(base_prediction)
    if selected:
        row_index = {_key(row[0]): index for index, row in enumerate(rows)}
        field_index = {_key(field): index for index, field in enumerate(required)}
        edited = copy.deepcopy(rows)
        for item in selected:
            target_row = row_index.get(_key(item["row_identity"]))
            target_field = field_index.get(_key(item["field"]))
            if target_row is None or target_field in {None, 0}:
                raise RuntimeError("V2.54.32 replayed candidate target drifted")
            if edited[target_row][target_field] != item["old_value"]:
                raise RuntimeError("V2.54.32 replayed candidate base cell drifted")
            edited[target_row][target_field] = str(item["exact_value"])
        candidate = table_parent._render_table(required, edited)
        reparsed_columns, reparsed_rows = _canonical_table(candidate, required)
        if (
            reparsed_columns != required
            or len(reparsed_rows) != len(rows)
            or [row[0] for row in reparsed_rows] != [row[0] for row in rows]
        ):
            raise RuntimeError("V2.54.32 post-selection preservation drifted")
        selected_coordinates = {
            (row_index[_key(item["row_identity"])], field_index[_key(item["field"])])
            for item in selected
        }
        for row_position, (before, after) in enumerate(
            zip(rows, reparsed_rows, strict=True)
        ):
            for field_position, (old, new) in enumerate(
                zip(before, after, strict=True)
            ):
                if (
                    (row_position, field_position) not in selected_coordinates
                    and old != new
                ):
                    raise RuntimeError("V2.54.32 unselected cell drifted")
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
        "parent_prediction_byte_exact_on_zero_admission_or_invalid_selection",
        "selected_values_replayed_from_registry_not_selector",
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
        raise ValueError("V2.54.32 candidate application receipt drifted")
    return copied


def validate_application(
    value: Mapping[str, Any],
    *,
    base_prediction: str | None = None,
    columns: Sequence[str] | None = None,
    pages: Sequence[Mapping[str, Any]] | None = None,
    selector_output: object | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    control = copied.get("control_prediction")
    candidate = copied.get("candidate_prediction")
    registry = copied.get("private_candidate_registry")
    selected_ids = copied.get("selected_candidate_ids")
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
        or not isinstance(selected_ids, list)
        or len(selected_ids) != len(set(selected_ids))
        or any(
            not isinstance(item, str) or _SELECTOR_ID.fullmatch(item) is None
            for item in selected_ids
        )
        or not isinstance(receipt, Mapping)
        or validate_application_receipt(receipt) != dict(receipt)
        or copied.get("control_prediction_sha256")
        != hashlib.sha256(control.encode("utf-8")).hexdigest()
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        or receipt["available_candidate_count"]
        != registry["content_free_receipt"]["available_candidate_count"]
        or receipt["selected_candidate_count"] != len(selected_ids)
        or any(
            item
            not in {
                registry_candidate["candidate_id"]
                for registry_candidate in registry["candidates"]
            }
            for item in selected_ids
        )
        or receipt["candidate_prediction_changed"] is not (control != candidate)
        or (
            selected_ids
            and not _prediction_matches_selection(
                control,
                candidate,
                registry,
                selected_ids,
            )
        )
        or (not selected_ids and candidate != control)
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
        raise ValueError("V2.54.32 candidate application drifted")
    replay_inputs = (
        base_prediction is not None,
        columns is not None,
        pages is not None,
        selector_output is not None,
    )
    if any(replay_inputs) and not all(replay_inputs):
        raise ValueError("V2.54.32 application replay inputs must be supplied together")
    if all(replay_inputs):
        assert base_prediction is not None and columns is not None and pages is not None
        expected_value = _apply_candidate_selection(
            base_prediction,
            columns=columns,
            pages=pages,
            selector_output=selector_output,
        )
        if expected_value != copied:
            raise ValueError("V2.54.32 candidate application replay drifted")
    return copied


def _prediction_matches_selection(
    control: str,
    candidate: str,
    registry: Mapping[str, Any],
    selected_ids: Sequence[str],
) -> bool:
    """Recompute a selected projection from sealed registry coordinates."""

    try:
        columns, rows = table_parent._baseline_matrix(control)
        required = tuple(columns)
        if table_parent._render_table(columns, rows) != control:
            return False
        by_id = {item["candidate_id"]: item for item in registry["candidates"]}
        chosen = [by_id[name] for name in selected_ids]
        row_index: defaultdict[str, list[int]] = defaultdict(list)
        field_index: defaultdict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(rows):
            row_index[_key(row[0])].append(index)
        for index, field in enumerate(required):
            field_index[_key(field)].append(index)
        edited = copy.deepcopy(rows)
        coordinates: set[tuple[int, int]] = set()
        for item in chosen:
            row_matches = row_index.get(_key(item["row_identity"]), [])
            field_matches = field_index.get(_key(item["field"]), [])
            if len(row_matches) != 1 or len(field_matches) != 1 or field_matches[0] == 0:
                return False
            coordinate = (row_matches[0], field_matches[0])
            if (
                coordinate in coordinates
                or edited[coordinate[0]][coordinate[1]] != item["old_value"]
            ):
                return False
            coordinates.add(coordinate)
            edited[coordinate[0]][coordinate[1]] = item["exact_value"]
        return candidate == table_parent._render_table(required, edited)
    except (KeyError, TypeError, ValueError):
        return False


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
    "validate_registry",
    "validate_registry_receipt",
]
