"""Pure row-key-bound structured-source candidate application.

The earlier V2.54.32 parser required a source record to repeat the table row
identity inside the same structured span.  That is unnecessarily restrictive
for one-record detail pages: the completed parent table already supplies the
row keys, while the page URL path and title/leading surface can bind exactly
one of those keys before any field is read.

This primitive therefore starts from one exact canonical parent table.  It
binds each row key to at most one same-forward HTTPS page using both an exact
URL-path token match and an exact title/leading-surface token match.  A page is
accepted only when the page binds exactly one parent row; several pages may
bind that row, but the downstream unique source-coordinate rule then rejects
duplicate or conflicting evidence for the same table cell.  It preserves the
V2.54.32 explicit-identity parser and adds page-bound variants of its four
structured surfaces: horizontal Markdown tables, vertical key/value tables,
contiguous labelled records, and flat JSON objects.  Page binding supplies
only the row identity; field names and values must still be exact contiguous
source text.

Every retained edit has one unique source coordinate and one unique existing
non-key target coordinate.  Conflicts, repeated source coordinates, duplicate
row keys, Unknown/unsafe values, list collapse, shape/key changes, and
case/spacing/list-separator-only changes fail closed.  All candidates are
applied deterministically; zero candidates preserve the parent prediction
byte-for-byte.

The module has no filesystem, process, environment, network, model, search,
fetch, evaluator, benchmark-label, mapping, gold, score, reward, credential,
or historical-result capability.  Entropy/information gain is shadow-only and
assigns no signed credit.  This build grants no launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import unquote, urlsplit

from . import v25004_identity_bound_detail_fields as identity_parent
from . import v25432_source_authoritative_field_candidate as parent


POLICY_ID = "v25464_row_key_bound_structured_source_candidate_v1"
REGISTRY_ROLE = "v25464_row_key_bound_structured_source_candidate_registry"
REGISTRY_RECEIPT_ROLE = "v25464_content_free_candidate_registry_receipt"
APPLICATION_ROLE = "v25464_row_key_bound_structured_source_application"
APPLICATION_RECEIPT_ROLE = "v25464_content_free_candidate_application_receipt"

PAGE_KEYS = parent.PAGE_KEYS
MAXIMUM_BLOCK_LINES = 24
MAXIMUM_CANDIDATES = parent.MAXIMUM_CANDIDATES
_CANDIDATE_ID = re.compile(r"C[0-9]{3}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SOURCE_KINDS = frozenset(
    {
        *parent._SOURCE_KINDS,
        "page_bound_horizontal_markdown_record",
        "page_bound_vertical_key_value_record",
        "page_bound_contiguous_labelled_record",
        "page_bound_flat_json_record",
    }
)
_IDENTITY_BINDING_KINDS = frozenset(
    {
        "explicit_record_identity_and_unique_page_binding",
        "unique_url_path_and_surface_page_binding",
    }
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
        "row_identity",
        "source_field",
        "field",
        "old_value",
        "exact_value",
        "source_kind",
        "identity_binding_kind",
        "source_coordinate_is_unique",
        "target_table_coordinate_is_unique",
        "value_is_source_extracted_not_model_generated",
        "material_semantic_change_not_surface_only",
        "list_cardinality_noncollapse",
        "candidate_payload_sha256",
    }
)

_COUNT_FIELDS = (
    "input_page_count",
    "canonical_page_count",
    "rejected_page_count",
    "accepted_page_character_count",
    "parent_row_count",
    "url_path_bound_page_count",
    "identity_surface_bound_page_count",
    "joint_bound_page_count",
    "ambiguous_joint_page_count",
    "multi_page_row_binding_count",
    "accepted_unique_identity_page_count",
    "explicit_parent_candidate_count",
    "page_bound_horizontal_surface_count",
    "page_bound_vertical_surface_count",
    "page_bound_labelled_surface_count",
    "page_bound_json_surface_count",
    "raw_observation_count",
    "evidence_closed_observation_count",
    "exact_duplicate_observation_count",
    "coordinate_group_count",
    "ambiguous_same_value_coordinate_count",
    "conflicting_value_coordinate_count",
    "unchanged_coordinate_count",
    "surface_equivalent_rejected_coordinate_count",
    "list_collapse_rejected_coordinate_count",
    "truncated_unique_candidate_count",
    "available_candidate_count",
    "applied_coordinate_count",
    "positive_signed_credit_count",
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_calls",
    "additional_fetch_calls",
    "additional_provider_tokens",
)


payload_sha256 = parent.payload_sha256


def _identity_path_bound(url: str, identity: str) -> bool:
    """Require complete identity tokens in the URL path, never a substring."""

    canonical = parent._canonical_url(url)
    if canonical is None:
        return False
    try:
        path_tokens = frozenset(
            identity_parent._tokens(unquote(urlsplit(canonical[0]).path or ""))
        )
    except ValueError:
        return False
    identity_tokens = tuple(identity_parent._tokens(identity))
    joined = "".join(identity_tokens)
    specificity = sum(len(token) for token in identity_tokens)
    return bool(
        identity_tokens
        and specificity >= 2
        and (
            set(identity_tokens).issubset(path_tokens)
            or (len(identity_tokens) >= 2 and joined in path_tokens)
        )
    )


def _canonical_pages(
    pages: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("V2.54.64 page vector is not a sequence")
    if len(pages) > parent.MAXIMUM_PAGE_COUNT:
        raise ValueError("V2.54.64 page count exceeds the frozen fetch cap")
    counts: Counter[str] = Counter(input_page_count=len(pages))
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    used = 0
    for ordinal, raw in enumerate(pages, 1):
        if not isinstance(raw, Mapping) or set(raw) != PAGE_KEYS:
            raise ValueError("V2.54.64 page schema drifted")
        canonical = parent._canonical_url(raw.get("url"))
        title = raw.get("title")
        content = raw.get("content")
        if (
            canonical is None
            or not isinstance(title, str)
            or len(title) > 500
            or not isinstance(content, str)
            or not content
            or "\x00" in content
            or len(content) > parent.MAXIMUM_PAGE_CHARACTERS
            or used + len(content) > parent.MAXIMUM_TOTAL_PAGE_CHARACTERS
            or canonical[0] in seen
        ):
            counts["rejected_page_count"] += 1
            continue
        seen.add(canonical[0])
        used += len(content)
        output.append(
            {
                "page_ordinal": ordinal,
                "url": canonical[0],
                "source_host": canonical[1],
                "title": title,
                "content": content,
            }
        )
    counts["canonical_page_count"] = len(output)
    counts["accepted_page_character_count"] = used
    return output, counts


def _bound_pages(
    rows: Sequence[Sequence[str]],
    pages: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    canonical, counts = _canonical_pages(pages)
    identities = [str(row[0]) for row in rows]
    if len({parent._key(value) for value in identities}) != len(identities):
        raise ValueError("V2.54.64 parent row keys are not unique")
    counts["parent_row_count"] = len(identities)
    provisional: list[tuple[dict[str, Any], str]] = []
    row_frequency: Counter[str] = Counter()
    for page in canonical:
        path_matches = [
            identity
            for identity in identities
            if _identity_path_bound(str(page["url"]), identity)
        ]
        surface_matches = [
            identity
            for identity in identities
            if identity_parent._page_identity_bound(
                {
                    "url": str(page["url"]),
                    "title": str(page["title"]),
                    "content": str(page["content"]),
                },
                identity,
            )
        ]
        joint = [
            identity
            for identity in identities
            if identity in path_matches and identity in surface_matches
        ]
        counts["url_path_bound_page_count"] += int(bool(path_matches))
        counts["identity_surface_bound_page_count"] += int(bool(surface_matches))
        counts["joint_bound_page_count"] += int(bool(joint))
        counts["ambiguous_joint_page_count"] += int(len(joint) > 1)
        if len(joint) == 1:
            key = parent._key(joint[0])
            row_frequency[key] += 1
            provisional.append((page, joint[0]))
    accepted: list[dict[str, Any]] = []
    counts["multi_page_row_binding_count"] = sum(
        count for count in row_frequency.values() if count > 1
    )
    for page, identity in provisional:
        accepted.append({**page, "row_identity": identity})
    counts["accepted_unique_identity_page_count"] = len(accepted)
    return accepted, counts


def _list_atoms(value: object) -> tuple[str, ...]:
    text = parent._surface(value)
    if not text:
        return ()
    atoms = tuple(
        parent._key(part)
        for part in parent.LIST_SEPARATOR.split(text)
        if parent._surface(part)
    )
    return atoms if len(atoms) >= 2 else ()


def _surface_equivalent(field: str, old: str, new: str) -> bool:
    if parent._key(old) == parent._key(new):
        return True
    return bool(
        parent._column_key(field) in parent.LIST_COLUMN_KEYS
        and _list_atoms(old)
        and _list_atoms(old) == _list_atoms(new)
    )


def _offer(
    observations: list[dict[str, Any]],
    counts: Counter[str],
    *,
    page: Mapping[str, Any],
    quote_start: int,
    quote_end: int,
    source_field: object,
    source_value: object,
    source_kind: str,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    column_map: Mapping[str, list[int]],
) -> None:
    counts["raw_observation_count"] += 1
    content = str(page["content"])
    quote = content[quote_start:quote_end]
    field_text = str(source_field).strip()
    value = parent._safe_cell(source_value)
    matches = column_map.get(parent._key(field_text), [])
    row_index = int(page["row_index"])
    if (
        value is None
        or len(matches) != 1
        or matches[0] == 0
        or not 1 <= len(quote) <= parent.MAXIMUM_QUOTE_CHARACTERS
        or content.count(quote) != 1
        or not field_text
        or field_text not in quote
        or value not in quote
    ):
        return
    column_index = matches[0]
    observations.append(
        {
            "page_ordinal": int(page["page_ordinal"]),
            "source_url": str(page["url"]),
            "source_host": str(page["source_host"]),
            "quote_start": int(quote_start),
            "quote_end": int(quote_end),
            "exact_quote": quote,
            "row_identity": str(rows[row_index][0]),
            "source_field": field_text,
            "field": str(columns[column_index]),
            "old_value": str(rows[row_index][column_index]),
            "exact_value": value,
            "source_kind": source_kind,
            "identity_binding_kind": "unique_url_path_and_surface_page_binding",
            "row_index": row_index,
            "column_index": column_index,
            "origin": "page_bound",
        }
    )
    counts["evidence_closed_observation_count"] += 1


def _horizontal(
    page: Mapping[str, Any],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    column_map: Mapping[str, list[int]],
    observations: list[dict[str, Any]],
    counts: Counter[str],
) -> None:
    lines = parent._line_spans(str(page["content"]))
    index = 0
    while index + 2 < len(lines):
        header = parent._pipe_cells(lines[index][2])
        rule = parent._pipe_cells(lines[index + 1][2])
        if header is None or rule is None or len(header) != len(rule) or not parent._separator(rule):
            index += 1
            continue
        mapped = [column_map.get(parent._key(value), []) for value in header]
        if (
            any(len(matches) != 1 or matches[0] == 0 for matches in mapped)
            or len({matches[0] for matches in mapped}) != len(mapped)
        ):
            index += 1
            continue
        cursor = index + 2
        data: list[tuple[int, int, list[str]]] = []
        while cursor < len(lines):
            cells = parent._pipe_cells(lines[cursor][2])
            if cells is None or len(cells) != len(header) or parent._separator(cells):
                break
            data.append((lines[cursor][0], lines[cursor][1], cells))
            cursor += 1
        if len(data) == 1:
            counts["page_bound_horizontal_surface_count"] += 1
            quote_start = lines[index][0]
            quote_end = data[0][1]
            for source_field, value in zip(header, data[0][2], strict=True):
                _offer(
                    observations,
                    counts,
                    page=page,
                    quote_start=quote_start,
                    quote_end=quote_end,
                    source_field=source_field,
                    source_value=value,
                    source_kind="page_bound_horizontal_markdown_record",
                    columns=columns,
                    rows=rows,
                    column_map=column_map,
                )
        index = max(index + 1, cursor)


def _vertical(
    page: Mapping[str, Any],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    column_map: Mapping[str, list[int]],
    observations: list[dict[str, Any]],
    counts: Counter[str],
) -> None:
    for block in parent._pipe_blocks(str(page["content"])):
        # A two-column Markdown horizontal table is also a run of two-cell
        # pipe lines.  Its separator makes the grammars mutually exclusive,
        # so a header cannot be reinterpreted as a vertical field/value row.
        if any(parent._separator(entry[2]) for entry in block):
            continue
        recognized: list[tuple[int, str, str]] = []
        invalid = False
        for _start, _end, cells in block:
            matches = column_map.get(parent._key(cells[0]), [])
            if not matches:
                continue
            if len(matches) != 1 or any(item[0] == matches[0] for item in recognized):
                invalid = True
                break
            recognized.append((matches[0], cells[0], cells[1]))
        if invalid or any(index == 0 for index, _field, _value in recognized):
            continue
        targets = [item for item in recognized if item[0] > 0]
        if not targets:
            continue
        counts["page_bound_vertical_surface_count"] += 1
        for _field_index, source_field, source_value in targets:
            _offer(
                observations,
                counts,
                page=page,
                quote_start=block[0][0],
                quote_end=block[-1][1],
                source_field=source_field,
                source_value=source_value,
                source_kind="page_bound_vertical_key_value_record",
                columns=columns,
                rows=rows,
                column_map=column_map,
            )


def _strict_label(line: str) -> tuple[str, str] | None:
    raw = re.sub(r"^(?:[-*]\s+)", "", str(line).strip())
    match = re.fullmatch(r"([^:=：\t]{1,120})\s*[:=：\t]\s*(.+?)\s*", raw)
    return None if match is None else (match.group(1).strip(), match.group(2).strip())


def _labelled(
    page: Mapping[str, Any],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    column_map: Mapping[str, list[int]],
    observations: list[dict[str, Any]],
    counts: Counter[str],
) -> None:
    lines = parent._line_spans(str(page["content"]))
    index = 0
    while index < len(lines):
        if _strict_label(lines[index][2]) is None:
            index += 1
            continue
        cursor = index
        block: list[tuple[int, int, str, str]] = []
        while cursor < len(lines) and cursor - index < MAXIMUM_BLOCK_LINES:
            pair = _strict_label(lines[cursor][2])
            if pair is None:
                break
            block.append((lines[cursor][0], lines[cursor][1], pair[0], pair[1]))
            cursor += 1
        recognized: list[tuple[int, str, str]] = []
        invalid = False
        for _start, _end, source_field, value in block:
            matches = column_map.get(parent._key(source_field), [])
            if not matches:
                continue
            if len(matches) != 1 or any(item[0] == matches[0] for item in recognized):
                invalid = True
                break
            recognized.append((matches[0], source_field, value))
        if not invalid and not any(item[0] == 0 for item in recognized):
            targets = [item for item in recognized if item[0] > 0]
            if targets:
                counts["page_bound_labelled_surface_count"] += 1
                for _field_index, source_field, value in targets:
                    _offer(
                        observations,
                        counts,
                        page=page,
                        quote_start=block[0][0],
                        quote_end=block[-1][1],
                        source_field=source_field,
                        source_value=value,
                        source_kind="page_bound_contiguous_labelled_record",
                        columns=columns,
                        rows=rows,
                        column_map=column_map,
                    )
        index = max(index + 1, cursor)


def _json_records(
    page: Mapping[str, Any],
    *,
    columns: Sequence[str],
    rows: Sequence[Sequence[str]],
    column_map: Mapping[str, list[int]],
    observations: list[dict[str, Any]],
    counts: Counter[str],
) -> None:
    content = str(page["content"])
    decoder = json.JSONDecoder()
    cursor = 0
    while cursor < len(content):
        start = content.find("{", cursor)
        if start < 0:
            break
        try:
            _ignored, size = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            cursor = start + 1
            continue
        end = start + size
        cursor = max(start + 1, end)
        raw = content[start:end]
        payload = parent._strict_json_object(raw)
        if payload is None or len(raw) > parent.MAXIMUM_QUOTE_CHARACTERS:
            continue
        recognized: list[tuple[int, str, object]] = []
        invalid = False
        for source_field, value in payload.items():
            matches = column_map.get(parent._key(source_field), [])
            if not matches:
                continue
            if (
                len(matches) != 1
                or any(item[0] == matches[0] for item in recognized)
                or isinstance(value, (Mapping, list, bool))
            ):
                invalid = True
                break
            recognized.append((matches[0], str(source_field), value))
        if invalid or any(item[0] == 0 for item in recognized):
            continue
        targets = [item for item in recognized if item[0] > 0]
        if not targets:
            continue
        counts["page_bound_json_surface_count"] += 1
        for _field_index, source_field, value in targets:
            _offer(
                observations,
                counts,
                page=page,
                quote_start=start,
                quote_end=end,
                source_field=source_field,
                source_value=value,
                source_kind="page_bound_flat_json_record",
                columns=columns,
                rows=rows,
                column_map=column_map,
            )


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


def validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("candidate_payload_sha256", None)
    canonical = parent._canonical_url(copied.get("source_url"))
    strings = (
        copied.get("exact_quote"),
        copied.get("row_identity"),
        copied.get("source_field"),
        copied.get("field"),
        copied.get("old_value"),
        copied.get("exact_value"),
    )
    if (
        set(copied) != _CANDIDATE_KEYS
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
        or any(
            "\r" in item
            or "\n" in item
            or any(ord(character) < 32 for character in item)
            for item in strings[1:]
        )
        or len(copied["exact_quote"])
        != copied["quote_end"] - copied["quote_start"]
        or copied["source_field"] not in copied["exact_quote"]
        or copied["exact_value"] not in copied["exact_quote"]
        or parent._safe_cell(copied["exact_value"]) != copied["exact_value"]
        or _surface_equivalent(
            str(copied["field"]),
            str(copied["old_value"]),
            str(copied["exact_value"]),
        )
        or copied.get("source_kind") not in _SOURCE_KINDS
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
        raise ValueError("V2.54.64 candidate drifted")
    if (
        parent._column_key(copied["field"]) in parent.LIST_COLUMN_KEYS
        and parent._list_cardinality(copied["old_value"]) >= 2
        and parent._list_cardinality(copied["exact_value"])
        < parent._list_cardinality(copied["old_value"])
    ):
        raise ValueError("V2.54.64 candidate list cardinality drifted")
    return copied


def _registry_receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "parent_row_keys_supply_identity_only_after_parent_completion": True,
        "accepted_page_requires_unique_url_path_and_title_or_leading_surface_binding": True,
        "each_accepted_page_binds_exactly_one_parent_row": True,
        "field_and_value_are_exact_contiguous_source_text": True,
        "v25432_explicit_identity_candidates_are_preserved": True,
        "horizontal_vertical_labelled_and_flat_json_surfaces_supported": True,
        "case_spacing_or_list_separator_only_change_rejected": True,
        "conflict_ambiguity_unknown_list_collapse_or_shape_key_change_fails_closed": True,
        "source_provenance_does_not_infer_host_reputation": True,
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
    bound, counts = _bound_pages(rows, pages)
    row_map = {parent._key(row[0]): index for index, row in enumerate(rows)}
    column_map: defaultdict[str, list[int]] = defaultdict(list)
    for index, field in enumerate(required):
        column_map[parent._key(field)].append(index)
    parent_pages = [
        {"url": page["url"], "title": page["title"], "content": page["content"]}
        for page in bound
    ]
    explicit = parent.build_candidate_registry(
        str(base_prediction), columns=required, pages=parent_pages
    )
    observations: list[dict[str, Any]] = []
    bound_identity_by_url = {
        str(page["url"]): str(page["row_identity"]) for page in bound
    }
    bound_ordinal_by_url = {
        str(page["url"]): int(page["page_ordinal"]) for page in bound
    }
    for candidate in explicit["candidates"]:
        if parent._key(candidate["row_identity"]) != parent._key(
            bound_identity_by_url.get(str(candidate["source_url"]), "")
        ):
            continue
        observations.append(
            {
                **{
                    name: copy.deepcopy(candidate[name])
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
                    )
                },
                "page_ordinal": bound_ordinal_by_url[str(candidate["source_url"])],
                "identity_binding_kind": "explicit_record_identity_and_unique_page_binding",
                "row_index": row_map[parent._key(candidate["row_identity"])],
                "column_index": tuple(parent._key(value) for value in required).index(
                    parent._key(candidate["field"])
                ),
                "origin": "explicit",
            }
        )
    counts["explicit_parent_candidate_count"] = len(observations)
    for page in bound:
        enriched = {
            **page,
            "row_index": row_map[parent._key(page["row_identity"])],
        }
        kwargs = {
            "columns": required,
            "rows": rows,
            "column_map": column_map,
            "observations": observations,
            "counts": counts,
        }
        _horizontal(enriched, **kwargs)
        _vertical(enriched, **kwargs)
        _labelled(enriched, **kwargs)
        _json_records(enriched, **kwargs)

    deduplicated: dict[tuple[Any, ...], dict[str, Any]] = {}
    for observation in observations:
        key = (
            int(observation["page_ordinal"]),
            int(observation["quote_start"]),
            int(observation["quote_end"]),
            int(observation["row_index"]),
            int(observation["column_index"]),
            parent._key(observation["exact_value"]),
        )
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
        normalized = {parent._key(item["exact_value"]) for item in values}
        if len(values) != 1:
            counts[
                "conflicting_value_coordinate_count"
                if len(normalized) > 1
                else "ambiguous_same_value_coordinate_count"
            ] += 1
            continue
        item = values[0]
        if parent._key(item["old_value"]) == parent._key(item["exact_value"]):
            counts["unchanged_coordinate_count"] += 1
            continue
        if _surface_equivalent(item["field"], item["old_value"], item["exact_value"]):
            counts["surface_equivalent_rejected_coordinate_count"] += 1
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
    counts["applied_coordinate_count"] = len(candidates)
    for name in _COUNT_FIELDS[-6:]:
        counts[name] = 0
    counts["available_candidate_count"] = len(candidates)
    counts["applied_coordinate_count"] = len(candidates)
    receipt = _registry_receipt(counts)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_ROLE,
        "policy_id": POLICY_ID,
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode("utf-8")
        ).hexdigest(),
        "input_page_vector_sha256": payload_sha256(list(pages)),
        "bound_page_vector_sha256": payload_sha256(
            [
                {
                    "page_ordinal": page["page_ordinal"],
                    "url": page["url"],
                    "row_identity": page["row_identity"],
                    "content": page["content"],
                }
                for page in bound
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
    return validate_registry(_build_registry(base_prediction, columns, pages))


def validate_registry_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "parent_row_keys_supply_identity_only_after_parent_completion",
        "accepted_page_requires_unique_url_path_and_title_or_leading_surface_binding",
        "each_accepted_page_binds_exactly_one_parent_row",
        "field_and_value_are_exact_contiguous_source_text",
        "v25432_explicit_identity_candidates_are_preserved",
        "horizontal_vertical_labelled_and_flat_json_surfaces_supported",
        "case_spacing_or_list_separator_only_change_rejected",
        "conflict_ambiguity_unknown_list_collapse_or_shape_key_change_fails_closed",
        "source_provenance_does_not_infer_host_reputation",
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
        or copied["canonical_page_count"] + copied["rejected_page_count"]
        != copied["input_page_count"]
        or copied["accepted_unique_identity_page_count"] > copied["joint_bound_page_count"]
        or copied["available_candidate_count"] > MAXIMUM_CANDIDATES
        or copied["applied_coordinate_count"] != copied["available_candidate_count"]
        or copied["positive_signed_credit_count"] != 0
        or any(copied[name] != 0 for name in _COUNT_FIELDS[-5:])
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.64 registry receipt drifted")
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
        "input_page_vector_sha256",
        "bound_page_vector_sha256",
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
        or any(
            _SHA256.fullmatch(str(copied.get(name, ""))) is None
            for name in (
                "base_prediction_sha256",
                "input_page_vector_sha256",
                "bound_page_vector_sha256",
            )
        )
        or not isinstance(candidates, list)
        or len(candidates) > MAXIMUM_CANDIDATES
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
        or not isinstance(receipt, Mapping)
        or validate_registry_receipt(receipt) != dict(receipt)
        or receipt["available_candidate_count"] != len(candidates)
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
        raise ValueError("V2.54.64 registry drifted")
    supplied = (base_prediction is not None, columns is not None, pages is not None)
    if any(supplied) and not all(supplied):
        raise ValueError("V2.54.64 registry replay inputs are incomplete")
    if all(supplied):
        assert base_prediction is not None and columns is not None and pages is not None
        if _build_registry(base_prediction, columns, pages) != copied:
            raise ValueError("V2.54.64 registry replay drifted")
    return copied


def _application_receipt(registry: Mapping[str, Any], changed: bool) -> dict[str, Any]:
    count = len(registry["candidates"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": APPLICATION_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "available_candidate_count": count,
        "selected_candidate_count": count,
        "applied_coordinate_count": count,
        "positive_signed_credit_count": 0,
        "candidate_prediction_changed": bool(changed),
        "candidate_identity_handoff": not bool(changed),
        "deterministic_policy_selects_all_and_only_unique_registry_candidates": True,
        "selected_values_replayed_from_source_registry": True,
        "schema_row_count_order_keys_and_unselected_cells_preserved": True,
        "zero_candidate_preserves_parent_prediction_byte_exact": True,
        "zero_additional_model_search_fetch_query_token_context_wall_or_network_effect": True,
        CONTENT_FREE_FLAG: False,
        PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_application_receipt(value)


def _project(
    base_prediction: str,
    columns: Sequence[str],
    registry: Mapping[str, Any],
) -> str:
    required, rows = parent._canonical_table(str(base_prediction), columns)
    row_index = {parent._key(row[0]): index for index, row in enumerate(rows)}
    field_index = {parent._key(field): index for index, field in enumerate(required)}
    edited = copy.deepcopy(rows)
    coordinates: set[tuple[int, int]] = set()
    for candidate in registry["candidates"]:
        coordinate = (
            row_index[parent._key(candidate["row_identity"])],
            field_index[parent._key(candidate["field"])],
        )
        if (
            coordinate[1] == 0
            or coordinate in coordinates
            or edited[coordinate[0]][coordinate[1]] != candidate["old_value"]
        ):
            raise RuntimeError("V2.54.64 projection coordinate drifted")
        coordinates.add(coordinate)
        edited[coordinate[0]][coordinate[1]] = candidate["exact_value"]
    candidate = parent.table_parent._render_table(required, edited)
    checked_columns, checked_rows = parent._canonical_table(candidate, required)
    if (
        checked_columns != required
        or len(checked_rows) != len(rows)
        or [row[0] for row in checked_rows] != [row[0] for row in rows]
    ):
        raise RuntimeError("V2.54.64 projected table shape drifted")
    for row_position, (before, after) in enumerate(zip(rows, checked_rows, strict=True)):
        for field_position, (old, new) in enumerate(zip(before, after, strict=True)):
            if (row_position, field_position) not in coordinates and old != new:
                raise RuntimeError("V2.54.64 unselected coordinate drifted")
    return candidate


def _build_application(
    base_prediction: str,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    registry = _build_registry(base_prediction, columns, pages)
    candidate = _project(base_prediction, columns, registry)
    changed = candidate != str(base_prediction)
    receipt = _application_receipt(registry, changed)
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
        "selected_candidate_ids": [item["candidate_id"] for item in registry["candidates"]],
        "content_free_receipt": receipt,
        PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return value


def build_application(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return validate_application(_build_application(base_prediction, columns, pages))


def validate_application_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "available_candidate_count",
        "selected_candidate_count",
        "applied_coordinate_count",
        "positive_signed_credit_count",
    )
    dynamic = ("candidate_prediction_changed", "candidate_identity_handoff")
    true_flags = (
        "deterministic_policy_selects_all_and_only_unique_registry_candidates",
        "selected_values_replayed_from_source_registry",
        "schema_row_count_order_keys_and_unselected_cells_preserved",
        "zero_candidate_preserves_parent_prediction_byte_exact",
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
        or copied["selected_candidate_count"] != copied["available_candidate_count"]
        or copied["applied_coordinate_count"] != copied["selected_candidate_count"]
        or copied["positive_signed_credit_count"] != 0
        or copied["candidate_prediction_changed"]
        is not (copied["applied_coordinate_count"] > 0)
        or copied["candidate_identity_handoff"]
        is not (not copied["candidate_prediction_changed"])
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.64 application receipt drifted")
    return copied


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
        or selected != [item["candidate_id"] for item in registry["candidates"]]
        or not isinstance(receipt, Mapping)
        or validate_application_receipt(receipt) != dict(receipt)
        or receipt["available_candidate_count"] != len(registry["candidates"])
        or registry.get("base_prediction_sha256")
        != hashlib.sha256(control.encode("utf-8")).hexdigest()
        or copied.get("control_prediction_sha256")
        != hashlib.sha256(control.encode("utf-8")).hexdigest()
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        or candidate != _project(control, tuple(parent.table_parent._baseline_matrix(control)[0]), registry)
        or receipt["candidate_prediction_changed"] is not (control != candidate)
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
        raise ValueError("V2.54.64 application drifted")
    supplied = (base_prediction is not None, columns is not None, pages is not None)
    if any(supplied) and not all(supplied):
        raise ValueError("V2.54.64 application replay inputs are incomplete")
    if all(supplied):
        assert base_prediction is not None and columns is not None and pages is not None
        if _build_application(base_prediction, columns, pages) != copied:
            raise ValueError("V2.54.64 application replay drifted")
    return copied


__all__ = [
    "APPLICATION_RECEIPT_ROLE",
    "APPLICATION_ROLE",
    "PAGE_KEYS",
    "POLICY_ID",
    "REGISTRY_RECEIPT_ROLE",
    "REGISTRY_ROLE",
    "build_application",
    "build_candidate_registry",
    "validate_application",
    "validate_application_receipt",
    "validate_candidate",
    "validate_registry",
    "validate_registry_receipt",
]
