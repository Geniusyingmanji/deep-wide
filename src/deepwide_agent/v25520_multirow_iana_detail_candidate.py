"""Pure source-bound IANA detail candidate for a selected multirow table.

V2.54.83 validated an exact IANA detail-page parser for one two-letter row
key.  This successor keeps its field grammar and safety rules but separates
URL selection from extraction: the caller supplies at most one already
fetched exact page.  The page URL binds one arbitrary-length visible TLD row
in a canonical multirow table, and the title or leading page surface must bind
the same row before any field is considered.

Exact, one-qualifier, and short fused visible field labels are supported in a
two-cell pipe row, labelled line, or bounded adjacent line.  Duplicate or
conflicting coordinates, unsafe values, unchanged/surface-equivalent edits,
list collapse, unbound pages, and table-shape changes fail closed.  Content-
free counters separate page binding, field surfaces, observations, rejection
classes, and material candidates.  This pure module performs no I/O, reads no
benchmark label/truth/evaluator/outcome, assigns zero entropy/IG signed
credit, and authorizes no launch.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from . import v25004_identity_bound_detail_fields as identity
from . import v25432_source_authoritative_field_candidate as source
from . import v25464_row_key_bound_structured_source_candidate as row_bound
from . import v25483_row_key_iana_detail_candidate as parent


POLICY_ID = "v25520_multirow_iana_detail_candidate_v1"
ROLE = "v25520_multirow_iana_detail_candidate"
RECEIPT_ROLE = "v25520_content_free_multirow_iana_detail_receipt"
IANA_HOST = parent.IANA_HOST
IANA_PATH_PREFIX = parent.IANA_PATH_PREFIX
MAXIMUM_DIRECT_PAGES = 1
MAXIMUM_PAGE_CHARACTERS = source.MAXIMUM_PAGE_CHARACTERS
PAGE_KEYS = frozenset({"url", "title", "content"})
_PATH = re.compile(
    r"/domains/root/db/(?P<label>[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.html",
    re.ASCII,
)
_ROW_KEY = re.compile(
    r"\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",
    re.ASCII,
)
_COUNT_FIELDS = (
    "base_row_count",
    "visible_column_count",
    "provided_page_count",
    "exact_iana_url_page_count",
    "url_row_key_bound_page_count",
    "identity_surface_bound_page_count",
    "raw_field_surface_count",
    "evidence_closed_observation_count",
    "unsafe_value_rejected_surface_count",
    "nonunique_or_unbound_quote_rejected_surface_count",
    "missing_or_next_field_rejected_surface_count",
    "coordinate_group_count",
    "ambiguous_same_value_coordinate_count",
    "conflicting_value_coordinate_count",
    "unchanged_coordinate_count",
    "surface_equivalent_rejected_coordinate_count",
    "list_collapse_rejected_coordinate_count",
    "available_candidate_count",
    "applied_coordinate_count",
    "positive_signed_credit_count",
)


payload_sha256 = source.payload_sha256


def _table(
    base_prediction: str, columns: Sequence[str]
) -> tuple[tuple[str, ...], list[list[str]], dict[str, int]]:
    required, rows = source._canonical_table(str(base_prediction), columns)
    if not rows or len(rows) > 64:
        raise ValueError("V2.55.20 canonical row count drifted")
    row_map: dict[str, int] = {}
    for index, row in enumerate(rows):
        raw = str(row[0])
        if _ROW_KEY.fullmatch(raw) is None or len(raw.removeprefix(".")) > 63:
            raise ValueError("V2.55.20 visible row key is not a bounded TLD")
        key = source._key(raw)
        if key in row_map:
            raise ValueError("V2.55.20 visible row keys are not unique")
        row_map[key] = index
    return required, rows, row_map


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


def _bound_page(
    raw: Mapping[str, Any],
    *,
    rows: Sequence[Sequence[str]],
    row_map: Mapping[str, int],
    counts: Counter[str],
) -> tuple[dict[str, str], int] | None:
    if not isinstance(raw, Mapping) or set(raw) != PAGE_KEYS:
        raise ValueError("V2.55.20 page schema drifted")
    url = raw.get("url")
    title = raw.get("title")
    content = raw.get("content")
    bound_identity = _url_identity(url)
    counts["exact_iana_url_page_count"] += int(bound_identity is not None)
    row_index = (
        row_map.get(source._key(bound_identity))
        if bound_identity is not None
        else None
    )
    counts["url_row_key_bound_page_count"] += int(row_index is not None)
    if (
        row_index is None
        or not isinstance(title, str)
        or len(title) > 500
        or not isinstance(content, str)
        or not content
        or len(content) > MAXIMUM_PAGE_CHARACTERS
        or "\x00" in content
    ):
        return None
    page = {"url": str(url), "title": title, "content": content}
    identity_value = str(rows[row_index][0])
    if not identity._page_identity_bound(page, identity_value):
        return None
    counts["identity_surface_bound_page_count"] += 1
    return page, int(row_index)


def _offer(
    output: list[dict[str, Any]],
    counts: Counter[str],
    *,
    page: Mapping[str, str],
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
    counts["raw_field_surface_count"] += 1
    value = source._safe_cell(source_value)
    content = str(page["content"])
    quote = content[quote_start:quote_end]
    if value is None:
        counts["unsafe_value_rejected_surface_count"] += 1
        return
    if (
        not source_field
        or not 1 <= len(quote) <= source.MAXIMUM_QUOTE_CHARACTERS
        or content.count(quote) != 1
        or source_field not in quote
        or value not in quote
    ):
        counts["nonunique_or_unbound_quote_rejected_surface_count"] += 1
        return
    output.append(
        {
            "source_url": str(page["url"]),
            "quote_start": int(quote_start),
            "quote_end": int(quote_end),
            "exact_quote": quote,
            "row_identity": str(rows[row_index][0]),
            "source_field": str(source_field),
            "field": str(field),
            "old_value": str(rows[row_index][column_index]),
            "exact_value": value,
            "row_index": int(row_index),
            "column_index": int(column_index),
            "label_grammar": str(grammar),
            "source_kind": str(source_kind),
        }
    )
    counts["evidence_closed_observation_count"] += 1


def _observations(
    page: Mapping[str, str],
    *,
    rows: Sequence[Sequence[str]],
    row_index: int,
    columns: Sequence[str],
    counts: Counter[str],
) -> list[dict[str, Any]]:
    lines = source._line_spans(str(page["content"]))
    output: list[dict[str, Any]] = []
    for index, (start, end, line) in enumerate(lines):
        cells = source._pipe_cells(line)
        if cells is not None and len(cells) == 2 and not source._separator(cells):
            matched = parent._field(cells[0], columns)
            if matched is not None:
                column_index, field, grammar = matched
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
                    source_kind="two_cell_pipe",
                )
            continue

        labelled = parent._LABELLED.fullmatch(str(line).strip())
        if labelled is not None:
            source_field = labelled.group(1).strip()
            matched = parent._field(source_field, columns)
            if matched is not None:
                column_index, field, grammar = matched
                _offer(
                    output,
                    counts,
                    page=page,
                    rows=rows,
                    row_index=row_index,
                    column_index=column_index,
                    field=field,
                    grammar=grammar,
                    source_field=source_field,
                    source_value=labelled.group(2).strip(),
                    quote_start=start,
                    quote_end=end,
                    source_kind="same_line_labelled",
                )
            continue

        clean = parent._clean_label(line)
        matched = parent._field(clean, columns)
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
            counts["missing_or_next_field_rejected_surface_count"] += 1
            continue
        cursor, (_next_start, next_end, next_line) = following
        if any(lines[position][2].strip() for position in range(index + 1, cursor)):
            counts["raw_field_surface_count"] += 1
            counts["missing_or_next_field_rejected_surface_count"] += 1
            continue
        if parent._field(parent._clean_label(next_line), columns) is not None:
            counts["raw_field_surface_count"] += 1
            counts["missing_or_next_field_rejected_surface_count"] += 1
            continue
        column_index, field, grammar = matched
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
            source_kind="standalone_label_next_value",
        )
    return output


def _receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "selected_page_url_not_synthesized_or_discovered_here": True,
        "exact_https_iana_host_and_arbitrary_length_tld_path_required": True,
        "url_path_binds_exactly_one_completed_visible_row_key": True,
        "same_row_key_must_bind_title_or_leading_page_surface": True,
        "source_label_is_exact_or_mechanically_qualified_complete_field_token": True,
        "value_is_exact_same_line_or_bounded_adjacent_source_text": True,
        "duplicate_conflict_unknown_surface_equivalent_list_collapse_or_shape_change_fails_closed": True,
        "content_free_stage_counters_separate_parser_observation_rejection_and_materiality": True,
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
        "selected_page_url_not_synthesized_or_discovered_here",
        "exact_https_iana_host_and_arbitrary_length_tld_path_required",
        "url_path_binds_exactly_one_completed_visible_row_key",
        "same_row_key_must_bind_title_or_leading_page_surface",
        "source_label_is_exact_or_mechanically_qualified_complete_field_token",
        "value_is_exact_same_line_or_bounded_adjacent_source_text",
        "duplicate_conflict_unknown_surface_equivalent_list_collapse_or_shape_change_fails_closed",
        "content_free_stage_counters_separate_parser_observation_rejection_and_materiality",
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
    rejected = sum(
        copied.get(name, 0)
        for name in (
            "ambiguous_same_value_coordinate_count",
            "conflicting_value_coordinate_count",
            "unchanged_coordinate_count",
            "surface_equivalent_rejected_coordinate_count",
            "list_collapse_rejected_coordinate_count",
        )
    )
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
        or not 1 <= copied["base_row_count"] <= 64
        or not 2 <= copied["visible_column_count"] <= 32
        or copied["provided_page_count"] not in {0, 1}
        or copied["exact_iana_url_page_count"] > copied["provided_page_count"]
        or copied["url_row_key_bound_page_count"]
        > copied["exact_iana_url_page_count"]
        or copied["identity_surface_bound_page_count"]
        > copied["url_row_key_bound_page_count"]
        or copied["evidence_closed_observation_count"]
        > copied["raw_field_surface_count"]
        or copied["raw_field_surface_count"]
        != copied["evidence_closed_observation_count"]
        + copied["unsafe_value_rejected_surface_count"]
        + copied["nonunique_or_unbound_quote_rejected_surface_count"]
        + copied["missing_or_next_field_rejected_surface_count"]
        or copied["coordinate_group_count"]
        > copied["evidence_closed_observation_count"]
        or copied["coordinate_group_count"]
        != rejected + copied["available_candidate_count"]
        or copied["available_candidate_count"]
        != copied["applied_coordinate_count"]
        or copied["available_candidate_count"]
        > copied["visible_column_count"] - 1
        or copied["positive_signed_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.20 receipt drifted")
    return copied


def _construct(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("V2.55.20 page vector is not a sequence")
    if len(pages) > MAXIMUM_DIRECT_PAGES:
        raise ValueError("V2.55.20 accepts at most one selected detail page")
    required, rows, row_map = _table(str(base_prediction), columns)
    counts: Counter[str] = Counter(
        base_row_count=len(rows),
        visible_column_count=len(required),
        provided_page_count=len(pages),
    )
    bound: tuple[dict[str, str], int] | None = None
    if pages:
        bound = _bound_page(
            pages[0], rows=rows, row_map=row_map, counts=counts
        )
    observations = (
        _observations(
            bound[0],
            rows=rows,
            row_index=bound[1],
            columns=required,
            counts=counts,
        )
        if bound is not None
        else []
    )

    grouped: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        grouped[
            (int(observation["row_index"]), int(observation["column_index"]))
        ].append(observation)
    counts["coordinate_group_count"] = len(grouped)
    retained: list[dict[str, Any]] = []
    for coordinate in sorted(grouped):
        values = grouped[coordinate]
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
        if (
            source._column_key(observation["field"]) in source.LIST_COLUMN_KEYS
            and source._list_cardinality(observation["old_value"]) >= 2
            and source._list_cardinality(observation["exact_value"])
            < source._list_cardinality(observation["old_value"])
        ):
            counts["list_collapse_rejected_coordinate_count"] += 1
            continue
        retained.append(observation)

    edited = copy.deepcopy(rows)
    for observation in retained:
        edited[int(observation["row_index"])][
            int(observation["column_index"])
        ] = str(observation["exact_value"])
    candidate = source.table_parent._render_table(required, edited)
    counts["available_candidate_count"] = len(retained)
    counts["applied_coordinate_count"] = len(retained)
    counts["positive_signed_credit_count"] = 0
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
        "candidate_prediction_changed": bool(retained),
        "columns": list(required),
        "private_bound_row_identity": (
            str(rows[bound[1]][0]) if bound is not None else None
        ),
        "private_pages": copy.deepcopy(list(pages)),
        "private_observations": copy.deepcopy(retained),
        "content_free_receipt": _receipt(counts),
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return value


def build_candidate(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return validate_candidate(
        _construct(str(base_prediction), columns=columns, pages=pages)
    )


def validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected_keys = {
        "artifact_version",
        "role",
        "policy_id",
        "base_prediction",
        "base_prediction_sha256",
        "candidate_prediction",
        "candidate_prediction_sha256",
        "candidate_prediction_changed",
        "columns",
        "private_bound_row_identity",
        "private_pages",
        "private_observations",
        "content_free_receipt",
        "artifact_payload_sha256",
    }
    columns = copied.get("columns")
    pages = copied.get("private_pages")
    base = copied.get("base_prediction")
    if (
        set(copied) != expected_keys
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(base, str)
        or not isinstance(columns, list)
        or not isinstance(pages, list)
        or not isinstance(copied.get("private_observations"), list)
        or not isinstance(copied.get("content_free_receipt"), Mapping)
        or validate_receipt(copied["content_free_receipt"])
        != copied["content_free_receipt"]
        or copied.get("base_prediction_sha256")
        != hashlib.sha256(base.encode()).hexdigest()
        or not isinstance(copied.get("candidate_prediction"), str)
        or copied.get("candidate_prediction_sha256")
        != hashlib.sha256(copied["candidate_prediction"].encode()).hexdigest()
        or copied.get("candidate_prediction_changed")
        is not (
            copied["candidate_prediction"] != copied["base_prediction"]
        )
        or copied.get("candidate_prediction_changed")
        is not (copied["content_free_receipt"]["applied_coordinate_count"] > 0)
        or copied.get("artifact_payload_sha256")
        != payload_sha256(
            {
                name: copy.deepcopy(item)
                for name, item in copied.items()
                if name != "artifact_payload_sha256"
            }
        )
    ):
        raise ValueError("V2.55.20 candidate drifted")
    replay = _construct(base, columns=columns, pages=pages)
    if replay != copied:
        raise ValueError("V2.55.20 candidate replay drifted")
    return copied


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "validated_parent_policy_id": parent.POLICY_ID,
        "input_is_one_already_selected_exact_detail_page": True,
        "multirow_arbitrary_length_tld_binding": True,
        "supported_label_grammars": [
            "exact",
            "separate_qualifier",
            "fused_qualifier",
        ],
        "supported_source_shapes": [
            "two_cell_pipe",
            "same_line_labelled",
            "standalone_label_bounded_adjacent_value",
        ],
        "additional_provider_effects": 0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "PAGE_KEYS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_candidate",
    "integration_contract",
    "validate_candidate",
    "validate_receipt",
]
