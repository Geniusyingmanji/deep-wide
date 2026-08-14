"""Pure row-key-derived IANA detail-page candidate.

V2.54.82 showed that loosening the existing field parser cannot create a new
candidate, while the outer physical envelope has spare fetch capacity.  This
primitive derives at most one official IANA Root Zone Database detail URL
from the completed parent table's visible ``.xx`` row key.  It then parses
only the caller-supplied page at that exact URL.

Admission requires an exact HTTPS IANA URL, exact row-key path binding,
title-or-leading page binding, and one replayable source coordinate per
field.  Supported source labels are mechanically related to visible columns:
an exact label, one separate qualifier plus the complete field suffix (for
example ``TLD Type``), or a short fused prefix on the first complete field
token (for example ``ccTLD Manager``).  Values must be on the same two-cell
pipe line, the same labelled line, or the first non-empty line within two
lines after a standalone label.  No synonym, ontology, country/TLD mapping,
host ranking, model inference, evaluator, score, reward, or historical
outcome is available.  This module performs no I/O and authorizes no launch.
"""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from . import v25004_identity_bound_detail_fields as detail
from . import v25432_source_authoritative_field_candidate as source
from . import v25464_row_key_bound_structured_source_candidate as row_bound


POLICY_ID = "v25483_row_key_iana_detail_candidate_v1"
ROLE = "v25483_row_key_iana_detail_candidate"
RECEIPT_ROLE = "v25483_content_free_row_key_iana_detail_receipt"
IANA_HOST = "www.iana.org"
IANA_PATH_PREFIX = "/domains/root/db/"
MAXIMUM_DIRECT_REQUESTS = 1
MAXIMUM_PAGE_CHARACTERS = source.MAXIMUM_PAGE_CHARACTERS
PAGE_KEYS = frozenset({"url", "title", "content"})
_ROW_KEY = re.compile(r"\.[a-z]{2}", re.ASCII)
_PATH = re.compile(r"/domains/root/db/(?P<label>[a-z]{2})\.html", re.ASCII)
_LABELLED = re.compile(r"([^:=：\t]{1,120})\s*[:=：\t]\s*(.+?)\s*")
_COUNT_FIELDS = (
    "base_row_count",
    "visible_column_count",
    "logical_request_count",
    "provided_page_count",
    "exact_url_page_count",
    "identity_surface_bound_page_count",
    "raw_field_surface_count",
    "evidence_closed_observation_count",
    "coordinate_group_count",
    "ambiguous_same_value_coordinate_count",
    "conflicting_value_coordinate_count",
    "unchanged_coordinate_count",
    "surface_equivalent_rejected_coordinate_count",
    "available_candidate_count",
    "applied_coordinate_count",
    "positive_signed_credit_count",
)


payload_sha256 = source.payload_sha256


def _authority_visible(question: str) -> bool:
    normalized = " ".join(unicodedata.normalize("NFKC", str(question)).split())
    return "iana root zone database" in normalized.casefold()


def _row_identity(base_prediction: str, columns: Sequence[str]) -> tuple[str, tuple[str, ...], list[list[str]]] | None:
    try:
        required, rows = source._canonical_table(str(base_prediction), columns)
    except (TypeError, ValueError, RuntimeError):
        return None
    if len(rows) != 1 or not _ROW_KEY.fullmatch(str(rows[0][0])):
        return None
    return str(rows[0][0]), required, rows


def request_vector(
    base_prediction: str,
    *,
    columns: Sequence[str],
    question: str,
) -> list[dict[str, str]]:
    """Derive one official detail URL from a completed visible row key."""

    bound = _row_identity(str(base_prediction), columns)
    if bound is None or not _authority_visible(str(question)):
        return []
    identity, required, _rows = bound
    if len(required) < 2:
        return []
    url = f"https://{IANA_HOST}{IANA_PATH_PREFIX}{identity.removeprefix('.')}.html"
    return [
        {
            "url": url,
            "query": "official IANA detail page for completed parent row key",
            "title": identity,
            "member_label": identity,
        }
    ]


def _url_identity(value: object) -> str | None:
    try:
        parsed = urlsplit(str(value or ""))
        port = parsed.port
    except ValueError:
        return None
    match = _PATH.fullmatch(parsed.path)
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold().strip(".") != IANA_HOST
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
        or match is None
    ):
        return None
    return "." + match.group("label")


def _clean_label(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = re.sub(r"^[#*_`~+\-\s:]+", "", text)
    text = re.sub(r"[#*_`~+\-\s:]+$", "", text)
    return text.strip()


def _field(label: str, columns: Sequence[str]) -> tuple[int, str, str] | None:
    clean = _clean_label(label)
    label_tokens = detail._tokens(clean)
    if not label_tokens:
        return None
    matches: list[tuple[int, str, str]] = []
    for index, visible in enumerate(columns):
        if index == 0:
            continue
        field_tokens = detail._tokens(visible)
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
            grammar = "exact" if exact else "separate_qualifier" if separate else "fused_qualifier"
            matches.append((index, str(visible), grammar))
    return matches[0] if len(matches) == 1 else None


def _page(raw: Mapping[str, Any], identity: str) -> dict[str, str] | None:
    if not isinstance(raw, Mapping) or set(raw) != PAGE_KEYS:
        return None
    url = str(raw.get("url") or "")
    title = str(raw.get("title") or "")
    content = raw.get("content")
    if (
        _url_identity(url) != identity
        or not isinstance(content, str)
        or not content
        or len(content) > MAXIMUM_PAGE_CHARACTERS
        or "\x00" in content
    ):
        return None
    page = {"url": url, "title": title[:500], "content": content}
    return page if detail._page_identity_bound(page, identity) else None


def _offer(
    output: list[dict[str, Any]],
    counts: Counter[str],
    *,
    page: Mapping[str, str],
    row_identity: str,
    column_index: int,
    field: str,
    grammar: str,
    source_field: str,
    source_value: object,
    quote_start: int,
    quote_end: int,
    old_value: str,
    source_kind: str,
) -> None:
    counts["raw_field_surface_count"] += 1
    value = source._safe_cell(source_value)
    content = str(page["content"])
    quote = content[quote_start:quote_end]
    if (
        value is None
        or not 1 <= len(quote) <= source.MAXIMUM_QUOTE_CHARACTERS
        or content.count(quote) != 1
        or source_field not in quote
        or value not in quote
    ):
        return
    output.append(
        {
            "source_url": str(page["url"]),
            "quote_start": int(quote_start),
            "quote_end": int(quote_end),
            "exact_quote": quote,
            "row_identity": row_identity,
            "source_field": source_field,
            "field": field,
            "old_value": old_value,
            "exact_value": value,
            "column_index": int(column_index),
            "label_grammar": grammar,
            "source_kind": source_kind,
        }
    )
    counts["evidence_closed_observation_count"] += 1


def _observations(
    page: Mapping[str, str],
    *,
    identity: str,
    columns: Sequence[str],
    row: Sequence[str],
    counts: Counter[str],
) -> list[dict[str, Any]]:
    lines = source._line_spans(str(page["content"]))
    output: list[dict[str, Any]] = []
    for index, (start, end, line) in enumerate(lines):
        cells = source._pipe_cells(line)
        if cells is not None and len(cells) == 2 and not source._separator(cells):
            matched = _field(cells[0], columns)
            if matched is not None:
                column_index, field, grammar = matched
                _offer(
                    output,
                    counts,
                    page=page,
                    row_identity=identity,
                    column_index=column_index,
                    field=field,
                    grammar=grammar,
                    source_field=cells[0],
                    source_value=cells[1],
                    quote_start=start,
                    quote_end=end,
                    old_value=str(row[column_index]),
                    source_kind="two_cell_pipe",
                )
            continue

        labelled = _LABELLED.fullmatch(str(line).strip())
        if labelled is not None:
            matched = _field(labelled.group(1), columns)
            if matched is not None:
                column_index, field, grammar = matched
                _offer(
                    output,
                    counts,
                    page=page,
                    row_identity=identity,
                    column_index=column_index,
                    field=field,
                    grammar=grammar,
                    source_field=labelled.group(1).strip(),
                    source_value=labelled.group(2).strip(),
                    quote_start=start,
                    quote_end=end,
                    old_value=str(row[column_index]),
                    source_kind="same_line_labelled",
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
            counts["raw_field_surface_count"] += 1
            continue
        cursor, (_next_start, next_end, next_line) = following
        if any(lines[position][2].strip() for position in range(index + 1, cursor)):
            counts["raw_field_surface_count"] += 1
            continue
        if _field(_clean_label(next_line), columns) is not None:
            counts["raw_field_surface_count"] += 1
            continue
        column_index, field, grammar = matched
        _offer(
            output,
            counts,
            page=page,
            row_identity=identity,
            column_index=column_index,
            field=field,
            grammar=grammar,
            source_field=clean,
            source_value=next_line.strip(),
            quote_start=start,
            quote_end=next_end,
            old_value=str(row[column_index]),
            source_kind="standalone_label_next_value",
        )
    return output


def _receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "official_url_derived_only_from_completed_parent_row_key": True,
        "visible_authority_phrase_required": True,
        "exact_https_iana_host_and_detail_path_required": True,
        "exact_nonredirected_page_admission_is_runtime_obligation": True,
        "row_key_binds_url_path_and_title_or_leading_page_surface": True,
        "source_label_is_exact_or_mechanically_qualified_complete_field_token": True,
        "value_is_exact_same_line_or_bounded_adjacent_source_text": True,
        "ambiguity_conflict_unknown_surface_only_or_shape_change_fails_closed": True,
        "country_tld_mapping_synonym_ontology_host_ranking_or_model_inference_absent": True,
        "contains_question_url_title_page_quote_identity_field_value_prediction_answer_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "official_url_derived_only_from_completed_parent_row_key",
        "visible_authority_phrase_required",
        "exact_https_iana_host_and_detail_path_required",
        "exact_nonredirected_page_admission_is_runtime_obligation",
        "row_key_binds_url_path_and_title_or_leading_page_surface",
        "source_label_is_exact_or_mechanically_qualified_complete_field_token",
        "value_is_exact_same_line_or_bounded_adjacent_source_text",
        "ambiguity_conflict_unknown_surface_only_or_shape_change_fails_closed",
        "country_tld_mapping_synonym_ontology_host_ranking_or_model_inference_absent",
    )
    false_flags = (
        "contains_question_url_title_page_quote_identity_field_value_prediction_answer_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
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
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _COUNT_FIELDS
        )
        or copied["base_row_count"] not in {0, 1}
        or copied["logical_request_count"] not in {0, 1}
        or copied["provided_page_count"] > 1
        or copied["exact_url_page_count"] > copied["provided_page_count"]
        or copied["identity_surface_bound_page_count"] > copied["exact_url_page_count"]
        or copied["available_candidate_count"] != copied["applied_coordinate_count"]
        or copied["available_candidate_count"] > max(0, copied["visible_column_count"] - 1)
        or copied["positive_signed_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.83 receipt drifted")
    return copied


def build_candidate(
    base_prediction: str,
    *,
    columns: Sequence[str],
    question: str,
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence) or len(pages) > 1:
        raise ValueError("V2.54.83 page vector drifted")
    bound = _row_identity(str(base_prediction), columns)
    counts: Counter[str] = Counter()
    requests = request_vector(
        str(base_prediction), columns=columns, question=str(question)
    )
    counts["logical_request_count"] = len(requests)
    counts["provided_page_count"] = len(pages)
    observations: list[dict[str, Any]] = []
    required: tuple[str, ...] = tuple(str(value) for value in columns)
    rows: list[list[str]] = []
    identity = ""
    if bound is not None:
        identity, required, rows = bound
        counts["base_row_count"] = 1
        counts["visible_column_count"] = len(required)
    if bound is not None and requests and len(pages) == 1:
        raw = pages[0]
        counts["exact_url_page_count"] = int(
            isinstance(raw, Mapping) and _url_identity(raw.get("url")) == identity
        )
        admitted = _page(raw, identity) if isinstance(raw, Mapping) else None
        if admitted is not None:
            counts["identity_surface_bound_page_count"] = 1
            observations = _observations(
                admitted,
                identity=identity,
                columns=required,
                row=rows[0],
                counts=counts,
            )

    grouped: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        grouped[int(observation["column_index"])].append(observation)
    counts["coordinate_group_count"] = len(grouped)
    retained: list[dict[str, Any]] = []
    for column_index in sorted(grouped):
        values = grouped[column_index]
        normalized = {source._key(value["exact_value"]) for value in values}
        if len(values) != 1:
            counts[
                "conflicting_value_coordinate_count"
                if len(normalized) > 1
                else "ambiguous_same_value_coordinate_count"
            ] += 1
            continue
        observation = values[0]
        if source._key(observation["old_value"]) == source._key(
            observation["exact_value"]
        ):
            counts["unchanged_coordinate_count"] += 1
            continue
        if row_bound._surface_equivalent(
            observation["field"],
            observation["old_value"],
            observation["exact_value"],
        ):
            counts["surface_equivalent_rejected_coordinate_count"] += 1
            continue
        retained.append(observation)

    edited = copy.deepcopy(rows)
    for observation in retained:
        edited[0][int(observation["column_index"])] = str(
            observation["exact_value"]
        )
    candidate = (
        source.table_parent._render_table(required, edited)
        if rows
        else str(base_prediction)
    )
    counts["available_candidate_count"] = len(retained)
    counts["applied_coordinate_count"] = len(retained)
    counts["positive_signed_credit_count"] = 0
    receipt = _receipt(counts)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "base_prediction": str(base_prediction),
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode()
        ).hexdigest(),
        "candidate_prediction": candidate,
        "candidate_prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "candidate_prediction_changed": candidate != str(base_prediction),
        "private_row_identity": identity or None,
        "private_columns": list(required),
        "private_pages": copy.deepcopy(list(pages)),
        "private_observations": copy.deepcopy(retained),
        "content_free_receipt": receipt,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_candidate(value)


def validate_candidate(
    value: Mapping[str, Any],
    *,
    base_prediction: str | None = None,
    columns: Sequence[str] | None = None,
    question: str | None = None,
    pages: Sequence[Mapping[str, Any]] | None = None,
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    receipt = copied.get("content_free_receipt")
    base = copied.get("base_prediction")
    candidate = copied.get("candidate_prediction")
    private_pages = copied.get("private_pages")
    observations = copied.get("private_observations")
    private_columns = copied.get("private_columns")
    private_identity = copied.get("private_row_identity")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "base_prediction",
        "base_prediction_sha256",
        "candidate_prediction",
        "candidate_prediction_sha256",
        "candidate_prediction_changed",
        "private_row_identity",
        "private_columns",
        "private_pages",
        "private_observations",
        "content_free_receipt",
        "artifact_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(base, str)
        or not isinstance(candidate, str)
        or copied.get("base_prediction_sha256")
        != hashlib.sha256(base.encode()).hexdigest()
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(candidate.encode()).hexdigest()
        or copied.get("candidate_prediction_changed") is not (base != candidate)
        or not isinstance(private_columns, list)
        or not isinstance(private_pages, list)
        or len(private_pages) > 1
        or any(not isinstance(page, Mapping) or set(page) != PAGE_KEYS for page in private_pages)
        or not isinstance(observations, list)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["provided_page_count"] != len(private_pages)
        or receipt["available_candidate_count"] != len(observations)
        or receipt["applied_coordinate_count"] != len(observations)
        or copied["candidate_prediction_changed"] is not (len(observations) > 0)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.83 candidate drifted")
    bound = _row_identity(base, private_columns)
    if bound is None:
        if (
            private_identity is not None
            or private_pages
            or observations
            or candidate != base
            or receipt["base_row_count"] != 0
        ):
            raise ValueError("V2.54.83 invalid-base handoff drifted")
    else:
        identity, required, rows = bound
        request_issued = receipt["logical_request_count"] == 1
        admitted_pages = (
            [
                page
                for page in private_pages
                if _page(page, identity) is not None
            ]
            if request_issued
            else []
        )
        observation_keys = {
            "source_url",
            "quote_start",
            "quote_end",
            "exact_quote",
            "row_identity",
            "source_field",
            "field",
            "old_value",
            "exact_value",
            "column_index",
            "label_grammar",
            "source_kind",
        }
        seen_columns: set[int] = set()
        edited = copy.deepcopy(rows)
        if (
            private_identity != identity
            or private_columns != list(required)
            or receipt["base_row_count"] != 1
            or receipt["visible_column_count"] != len(required)
            or receipt["exact_url_page_count"]
            != (
                sum(
                    _url_identity(page.get("url")) == identity
                    for page in private_pages
                )
                if request_issued
                else 0
            )
            or receipt["identity_surface_bound_page_count"] != len(admitted_pages)
            or observations and len(admitted_pages) != 1
            or not request_issued and (observations or candidate != base)
        ):
            raise ValueError("V2.54.83 private binding drifted")
        page = admitted_pages[0] if admitted_pages else None
        for observation in observations:
            if not isinstance(observation, Mapping) or set(observation) != observation_keys:
                raise ValueError("V2.54.83 observation schema drifted")
            column_index = observation.get("column_index")
            matched = _field(str(observation.get("source_field") or ""), required)
            if (
                page is None
                or isinstance(column_index, bool)
                or not isinstance(column_index, int)
                or not 1 <= column_index < len(required)
                or column_index in seen_columns
                or observation.get("source_url") != page["url"]
                or observation.get("row_identity") != identity
                or observation.get("field") != required[column_index]
                or observation.get("old_value") != rows[0][column_index]
                or source._safe_cell(observation.get("exact_value"))
                != observation.get("exact_value")
                or matched is None
                or matched
                != (
                    column_index,
                    required[column_index],
                    observation.get("label_grammar"),
                )
                or observation.get("source_kind")
                not in {
                    "two_cell_pipe",
                    "same_line_labelled",
                    "standalone_label_next_value",
                }
            ):
                raise ValueError("V2.54.83 observation binding drifted")
            quote_start = observation.get("quote_start")
            quote_end = observation.get("quote_end")
            content = page["content"]
            quote = observation.get("exact_quote")
            if (
                isinstance(quote_start, bool)
                or not isinstance(quote_start, int)
                or isinstance(quote_end, bool)
                or not isinstance(quote_end, int)
                or not 0 <= quote_start < quote_end <= len(content)
                or quote != content[quote_start:quote_end]
                or content.count(str(quote)) != 1
                or str(observation["source_field"]) not in str(quote)
                or str(observation["exact_value"]) not in str(quote)
                or row_bound._surface_equivalent(
                    required[column_index],
                    rows[0][column_index],
                    str(observation["exact_value"]),
                )
            ):
                raise ValueError("V2.54.83 observation evidence drifted")
            seen_columns.add(column_index)
            edited[0][column_index] = str(observation["exact_value"])
        reconstructed = source.table_parent._render_table(required, edited)
        if reconstructed != candidate:
            raise ValueError("V2.54.83 candidate reconstruction drifted")
    if base_prediction is not None and replay:
        if columns is None or question is None or pages is None:
            raise ValueError("V2.54.83 replay inputs are incomplete")
        rebuilt = build_candidate(
            str(base_prediction),
            columns=columns,
            question=str(question),
            pages=pages,
        )
        if rebuilt != copied:
            raise ValueError("V2.54.83 candidate replay drifted")
    return copied


__all__ = [
    "IANA_HOST",
    "IANA_PATH_PREFIX",
    "MAXIMUM_DIRECT_REQUESTS",
    "PAGE_KEYS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_candidate",
    "request_vector",
    "validate_candidate",
    "validate_receipt",
]
