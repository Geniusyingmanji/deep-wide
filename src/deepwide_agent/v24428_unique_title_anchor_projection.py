"""Strict page-title anchoring for structured label/value projection.

V2.44.27 measured 24 active page/selected-target pairs: nineteen lacked the
exact in-body entity anchor required by V2.44.05, while five had an anchor but
no accepted label.  The fetch layer already retains a page title, but the
legacy ``_plain_page`` boundary intentionally drops it before projection.

This pure successor preserves V2.44.05 verbatim and adds one conservative
route.  A page title must contain the complete visible row surface as a
contiguous token sequence and match exactly one visible row.  Only the
selected cell for that row is eligible.  The page must then contain an exact
column-derived label followed by a year inside a bounded title-scoped record;
multiple distinct labelled years reject the whole page/target pair.  A title
never supplies a value, and an unlabelled nearby year remains inadmissible.

The component performs no file, environment, network, model, search, fetch,
process, benchmark, evaluator, reward, or score access.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24405_structured_label_projection as base
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget, _normalize, _source_key
from .v24390_uncertainty_active_evidence_runtime import (
    _baseline_cells,
    _target_identity,
)


POLICY_ID = "v24428_unique_visible_row_title_anchor_projection_v1"
ROLE = "v24428_unique_title_anchor_projection"
MAXIMUM_TITLE_CHARACTERS = 500
MAXIMUM_TITLE_TOKENS = 64
MAXIMUM_TITLE_MATCH_START = 16
MAXIMUM_TITLE_RECORD_LINES = 96
PROJECTION_MODE = "unique_title_anchor_label_value"
PAGE_KEYS = frozenset({"host", "title", "content", "fetch_integrity"})
PROJECTION_KEYS = frozenset(
    {
        "target_binding_sha256",
        "row_key",
        "column",
        "value",
        "source_host",
        "fetch_integrity",
        "projection_mode",
        "line_ordinal",
        "normalized_label",
        "title_anchor_token_count",
    }
)
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_projection",
        "pages",
        "selected_target_binding_sha256s",
        "title_anchor_projections",
        "observations",
        "parent_observation_count",
        "unique_title_anchor_page_count",
        "ambiguous_or_absent_title_anchor_page_count",
        "title_anchor_projection_count",
        "novel_title_anchor_observation_count",
        "combined_observation_count",
        "title_anchor_projection_mode_counts",
        "complete_visible_row_surface_required",
        "unique_visible_row_title_match_required",
        "exact_column_derived_label_required",
        "single_distinct_labelled_year_required",
        "title_record_line_cap",
        "arbitrary_nearby_year_used_as_observation",
        "parent_projection_preserved",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "catalog_payload_sha256",
    }
)


def _plain_titled_page(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.44.28 page is not a mapping")
    page = {
        "host": str(value.get("host", "")),
        "title": str(value.get("title", ""))[:MAXIMUM_TITLE_CHARACTERS],
        "content": str(value.get("content", "")),
        "fetch_integrity": value.get("fetch_integrity", True) is True,
    }
    if (
        set(page) != PAGE_KEYS
        or not page["host"]
        or not page["content"]
        or page["fetch_integrity"] is not True
    ):
        raise ValueError("V2.44.28 titled page identity drifted")
    return page


def _tokens(value: object) -> tuple[str, ...]:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(character for character in text if not unicodedata.combining(character))
    raw = re.findall(r"[^\W_]+", text, flags=re.UNICODE)
    output: list[str] = []
    index = 0
    while index < len(raw):
        if len(raw[index]) == 1 and raw[index].isascii() and raw[index].isalpha():
            stop = index
            while (
                stop < len(raw)
                and len(raw[stop]) == 1
                and raw[stop].isascii()
                and raw[stop].isalpha()
            ):
                stop += 1
            if stop - index >= 2:
                output.append("".join(raw[index:stop]))
                index = stop
                continue
        output.append(raw[index])
        index += 1
    return tuple(output)


def _subsequence_start(haystack: Sequence[str], needle: Sequence[str]) -> int | None:
    if not needle or len(needle) > len(haystack):
        return None
    for index in range(0, len(haystack) - len(needle) + 1):
        if tuple(haystack[index : index + len(needle)]) == tuple(needle):
            return index
    return None


def _visible_rows(cells: Sequence[CellTarget]) -> list[tuple[str, tuple[str, ...]]]:
    rows: dict[str, tuple[str, tuple[str, ...]]] = {}
    for cell in cells:
        identity = _target_identity(cell.row_key, cell.column)[0]
        tokens = _tokens(cell.row_key)
        if not identity or not tokens:
            raise ValueError("V2.44.28 visible row cannot be title-bound")
        prior = rows.get(identity)
        current = (cell.row_key, tokens)
        if prior is not None and prior != current:
            raise ValueError("V2.44.28 visible row surface is ambiguous")
        rows[identity] = current
    return [rows[key] for key in sorted(rows)]


def _unique_title_row(
    title: str, cells: Sequence[CellTarget]
) -> tuple[str, tuple[str, ...]] | None:
    title_tokens = _tokens(title)
    if not title_tokens or len(title_tokens) > MAXIMUM_TITLE_TOKENS:
        return None
    matches: list[tuple[str, tuple[str, ...]]] = []
    for row_key, row_tokens in _visible_rows(cells):
        start = _subsequence_start(title_tokens, row_tokens)
        if start is not None and start <= MAXIMUM_TITLE_MATCH_START:
            matches.append((row_key, row_tokens))
    return matches[0] if len(matches) == 1 else None


def _labelled_years(
    lines: Sequence[str], labels: frozenset[str]
) -> list[tuple[str, str, int]]:
    output: dict[tuple[str, str, int], tuple[str, str, int]] = {}
    for index, line in enumerate(lines[:MAXIMUM_TITLE_RECORD_LINES]):
        bound = base._label_value(line, labels)
        if bound is not None:
            label, year = bound
            output[(label, year, index + 1)] = (label, year, index + 1)
        cells = base._cells(line)
        if cells is None or len(cells) < 2:
            continue
        for label_index in range(0, len(cells) - 1):
            if not base._label_equal(cells[label_index], labels):
                continue
            year = base._year(cells[label_index + 1])
            if year is None:
                continue
            label = _normalize(cells[label_index])
            output[(label, year, index + 1)] = (label, year, index + 1)
    return [output[key] for key in sorted(output, key=lambda item: (item[2], item))]


def _title_projections(
    page: Mapping[str, Any],
    cells: Sequence[CellTarget],
    permitted: Sequence[CellTarget],
) -> list[dict[str, Any]]:
    anchor = _unique_title_row(str(page["title"]), cells)
    if anchor is None:
        return []
    anchored_row, anchor_tokens = anchor
    anchored_identity = _target_identity(anchored_row, "")[0]
    lines = unicodedata.normalize("NFKC", str(page["content"])).splitlines()
    output: list[dict[str, Any]] = []
    for target in permitted:
        if _target_identity(target.row_key, "")[0] != anchored_identity:
            continue
        labels = base._accepted_labels(target)
        if not labels:
            continue
        labelled = _labelled_years(lines, labels)
        distinct_years = {year for _, year, _ in labelled}
        if len(distinct_years) != 1:
            continue
        label, year, ordinal = labelled[0]
        output.append(
            {
                "target_binding_sha256": target.binding_sha256,
                "row_key": target.row_key,
                "column": target.column,
                "value": year,
                "source_host": _source_key(str(page["host"])),
                "fetch_integrity": True,
                "projection_mode": PROJECTION_MODE,
                "line_ordinal": ordinal,
                "normalized_label": label,
                "title_anchor_token_count": len(anchor_tokens),
            }
        )
    return output


def _observation_key(value: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return base._observation_key(value)


def _compute(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None,
) -> dict[str, Any]:
    if isinstance(pages, (str, bytes)):
        raise ValueError("V2.44.28 page vector drifted")
    titled_pages = [_plain_titled_page(item) for item in pages]
    parent_projection = base.build_structured_label_projection(
        baseline_prediction,
        titled_pages,
        selected_identities=selected_identities,
    )
    base.validate_structured_label_projection(parent_projection)
    cells = _baseline_cells(baseline_prediction)
    selected = list(parent_projection["selected_target_binding_sha256s"])
    selected_set = set(selected)
    permitted = [cell for cell in cells if cell.binding_sha256 in selected_set]
    title_projections: list[dict[str, Any]] = []
    anchor_pages = 0
    for page in titled_pages:
        if _unique_title_row(page["title"], cells) is not None:
            anchor_pages += 1
        title_projections.extend(_title_projections(page, cells, permitted))
    unique: dict[tuple[str, str, str, str, int], dict[str, Any]] = {}
    for item in title_projections:
        key = (
            str(item["target_binding_sha256"]),
            str(item["source_host"]),
            _normalize(item["value"]),
            str(item["normalized_label"]),
            int(item["line_ordinal"]),
        )
        unique.setdefault(key, item)
    title_projections = [unique[key] for key in sorted(unique)]
    title_observations = base._canonical_observations(title_projections)
    parent_observations = base._canonical_observations(parent_projection["observations"])
    observations = base._canonical_observations(
        [*parent_observations, *title_observations]
    )
    parent_keys = {_observation_key(item) for item in parent_observations}
    novel = sum(
        _observation_key(item) not in parent_keys for item in title_observations
    )
    mode_counts = Counter(item["projection_mode"] for item in title_projections)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_projection": copy.deepcopy(parent_projection),
        "pages": copy.deepcopy(titled_pages),
        "selected_target_binding_sha256s": selected,
        "title_anchor_projections": title_projections,
        "observations": observations,
        "parent_observation_count": len(parent_observations),
        "unique_title_anchor_page_count": anchor_pages,
        "ambiguous_or_absent_title_anchor_page_count": len(titled_pages) - anchor_pages,
        "title_anchor_projection_count": len(title_projections),
        "novel_title_anchor_observation_count": novel,
        "combined_observation_count": len(observations),
        "title_anchor_projection_mode_counts": dict(sorted(mode_counts.items())),
        "complete_visible_row_surface_required": True,
        "unique_visible_row_title_match_required": True,
        "exact_column_derived_label_required": True,
        "single_distinct_labelled_year_required": True,
        "title_record_line_cap": MAXIMUM_TITLE_RECORD_LINES,
        "arbitrary_nearby_year_used_as_observation": False,
        "parent_projection_preserved": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_unique_title_anchor_projection(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    value = _compute(
        baseline_prediction,
        pages,
        selected_identities=selected_identities,
    )
    validate_unique_title_anchor_projection(value)
    return value


def validate_unique_title_anchor_projection(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    pages = value.get("pages")
    projections = value.get("title_anchor_projections")
    parent_projection = value.get("parent_projection")
    count_fields = (
        "parent_observation_count",
        "unique_title_anchor_page_count",
        "ambiguous_or_absent_title_anchor_page_count",
        "title_anchor_projection_count",
        "novel_title_anchor_observation_count",
        "combined_observation_count",
        "title_record_line_cap",
    )
    true_fields = (
        "complete_visible_row_surface_required",
        "unique_visible_row_title_match_required",
        "exact_column_derived_label_required",
        "single_distinct_labelled_year_required",
        "parent_projection_preserved",
    )
    false_fields = (
        "arbitrary_nearby_year_used_as_observation",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(value) != CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(parent_projection, Mapping)
        or not isinstance(pages, list)
        or not isinstance(projections, list)
        or not isinstance(value.get("observations"), list)
        or not isinstance(value.get("selected_target_binding_sha256s"), list)
        or any(set(page) != PAGE_KEYS for page in pages if isinstance(page, Mapping))
        or any(not isinstance(page, Mapping) for page in pages)
        or any(
            not isinstance(item, Mapping)
            or set(item) != PROJECTION_KEYS
            or item.get("projection_mode") != PROJECTION_MODE
            or item.get("fetch_integrity") is not True
            or isinstance(item.get("line_ordinal"), bool)
            or not isinstance(item.get("line_ordinal"), int)
            or not 1 <= item["line_ordinal"] <= MAXIMUM_TITLE_RECORD_LINES
            or isinstance(item.get("title_anchor_token_count"), bool)
            or not isinstance(item.get("title_anchor_token_count"), int)
            or item["title_anchor_token_count"] < 1
            for item in projections
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(value.get(name) is not True for name in true_fields)
        or any(value.get(name) is not False for name in false_fields)
        or value.get("title_record_line_cap") != MAXIMUM_TITLE_RECORD_LINES
        or value.get("unique_title_anchor_page_count", -1)
        + value.get("ambiguous_or_absent_title_anchor_page_count", -1)
        != len(pages)
        or value.get("title_anchor_projection_count") != len(projections)
        or value.get("combined_observation_count")
        != len(value.get("observations", []))
        or value.get("title_anchor_projection_mode_counts")
        != dict(sorted(Counter(item["projection_mode"] for item in projections).items()))
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.28 title-anchor projection identity drifted")
    base.validate_structured_label_projection(parent_projection)
    selected_identities = {
        _target_identity(cell.row_key, cell.column)
        for cell in _baseline_cells(str(parent_projection["baseline_prediction"]))
        if cell.binding_sha256 in set(value["selected_target_binding_sha256s"])
    }
    expected = _compute(
        str(parent_projection["baseline_prediction"]),
        pages,
        selected_identities=selected_identities,
    )
    if dict(value) != expected:
        raise ValueError("V2.44.28 title-anchor projection replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_unique_title_anchor_projection",
    "validate_unique_title_anchor_projection",
]
