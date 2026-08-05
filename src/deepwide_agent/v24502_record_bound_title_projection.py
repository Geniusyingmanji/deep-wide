"""Record-bound title projection with conservative narrative subject binding.

The frozen V2.44.36 projector accepts same-line narrative relations under a
unique visible-row title anchor.  This successor keeps its complete artifact
as a parent, but admits a narrative observation only when the relation has an
explicit target subject, no subject, or a small generic/anaphoric subject.
This prevents an unrelated named subject in the body from borrowing the page
title's row identity.

The successor also adds one exact structured route for extracted infoboxes in
which an accepted label and its date value occupy adjacent record lines.  A
bare year is never sufficient, another visible row terminates the record, and
multiple distinct record years reject the page/target pair.  It is pure,
label-blind, and performs no external effect.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24365_entity_segment_projection as segment
from . import v24405_structured_label_projection as structured
from . import v24428_unique_title_anchor_projection as title
from . import v24436_narrative_title_anchor_projection as parent
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget, _normalize, _source_key
from .v24390_uncertainty_active_evidence_runtime import (
    _baseline_cells,
    _target_identity,
)


POLICY_ID = "v24502_record_bound_title_projection_v1"
ROLE = "v24502_record_bound_title_projection"
PROJECTION_MODE = "unique_title_anchor_split_label_year"
MAXIMUM_RECORD_LINE_GAP = 2
GENERIC_SUBJECT_TOKENS = frozenset(
    {
        "a",
        "an",
        "the",
        "this",
        "that",
        "it",
        "its",
        "was",
        "were",
        "is",
        "has",
        "had",
        "been",
        "officially",
        "institution",
        "university",
        "school",
        "college",
        "academy",
        "institute",
        "conservatory",
        "organization",
        "organisation",
        "company",
        "foundation",
        "association",
        "society",
        "team",
        "club",
        "franchise",
        "product",
        "software",
        "project",
        "service",
        "system",
        "event",
        "venue",
        "building",
        "museum",
        "hospital",
        "park",
    }
)
DATE_VALUE_TOKENS = frozenset(
    {
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "sept",
        "oct",
        "nov",
        "dec",
        "c",
        "ca",
        "circa",
        "around",
        "approximately",
        "approx",
        "ad",
        "ce",
        "year",
        "years",
        "ago",
    }
)
PROJECTION_KEYS = frozenset(
    {
        "target_binding_sha256",
        "row_key",
        "column",
        "value",
        "source_host",
        "fetch_integrity",
        "projection_mode",
        "label_line_ordinal",
        "value_line_ordinal",
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
        "admitted_parent_narrative_projections",
        "record_bound_projections",
        "observations",
        "parent_observation_count",
        "base_non_narrative_observation_count",
        "parent_narrative_projection_count",
        "admitted_parent_narrative_projection_count",
        "rejected_parent_narrative_projection_count",
        "record_bound_projection_count",
        "novel_record_bound_observation_count",
        "combined_observation_count",
        "projection_mode_counts",
        "complete_visible_row_title_anchor_required",
        "narrative_subject_must_be_target_or_bounded_generic",
        "nonvisible_named_foreign_subject_rejected",
        "exact_column_derived_label_required",
        "split_label_year_record_gap",
        "single_distinct_record_year_required",
        "other_visible_row_stops_record_scope",
        "bare_year_used_as_observation",
        "parent_artifact_preserved",
        "parent_observations_admitted_without_safety_filter",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "catalog_payload_sha256",
    }
)


def _tokens(value: object) -> tuple[str, ...]:
    return title._tokens(value)


def _contains_tokens(haystack: Sequence[str], needle: Sequence[str]) -> bool:
    return title._subsequence_start(haystack, needle) is not None


def _subject_bound(
    page: Mapping[str, Any], projection: Mapping[str, Any]
) -> bool:
    lines = unicodedata.normalize("NFKC", str(page["content"])).splitlines()
    ordinal = int(projection["line_ordinal"])
    if not 1 <= ordinal <= len(lines):
        return False
    line = lines[ordinal - 1]
    kind = str(projection["relation_kind"])
    target_tokens = _tokens(projection["row_key"])
    for relation in segment._relations(line, kind):
        if _normalize(relation.value) != _normalize(projection["value"]):
            continue
        prefix_tokens = _tokens(line[: relation.start])
        if not prefix_tokens or _contains_tokens(prefix_tokens, target_tokens):
            return True
        if set(prefix_tokens).issubset(GENERIC_SUBJECT_TOKENS):
            return True
    return False


def _admitted_parent_narrative(
    projection: Mapping[str, Any], cells: Sequence[CellTarget]
) -> list[dict[str, Any]]:
    pages = projection["pages"]
    output: list[dict[str, Any]] = []
    for raw in projection["narrative_title_projections"]:
        item = copy.deepcopy(dict(raw))
        source = _source_key(str(item["source_host"]))
        candidates = [
            page
            for page in pages
            if _source_key(str(page["host"])) == source
            and (
                (anchor := title._unique_title_row(str(page["title"]), cells))
                is not None
            )
            and _target_identity(anchor[0], "")[0]
            == _target_identity(item["row_key"], "")[0]
        ]
        if any(_subject_bound(page, item) for page in candidates):
            output.append(item)
    return output


def _other_visible_row_present(
    line: str, *, anchored_row: str, rows: Sequence[tuple[str, tuple[str, ...]]]
) -> bool:
    tokens = _tokens(line)
    return any(
        not structured._entity_equal(row, anchored_row)
        and _contains_tokens(tokens, row_tokens)
        for row, row_tokens in rows
    )


def _label_only(line: str, labels: frozenset[str]) -> str | None:
    canonical = structured._canonical_line(line)
    cells = structured._cells(line)
    if cells is not None:
        nonempty = [item for item in cells if item]
        if len(nonempty) != 1:
            return None
        canonical = nonempty[0]
    return _normalize(canonical) if structured._label_equal(canonical, labels) else None


def _record_year(line: str) -> str | None:
    text = unicodedata.normalize("NFKC", str(line))
    text = structured.BRACKET_CITATION.sub("", text).strip().strip("| ")
    matches = list(structured.YEAR.finditer(text))
    years = {match.group(1) for match in matches}
    if len(years) != 1 or len(text) > 120:
        return None
    residual = structured.YEAR.sub(" ", text)
    residual = re.sub(r"\b\d{1,3}(?:st|nd|rd|th)?\b", " ", residual, flags=re.I)
    residual = residual.translate(str.maketrans({"年": " ", "月": " ", "日": " ", "约": " "}))
    words = {
        word.casefold()
        for word in re.findall(r"[^\W\d_]+", residual, flags=re.UNICODE)
    }
    if any(word not in DATE_VALUE_TOKENS for word in words):
        return None
    return next(iter(years))


def _record_projections(
    page: Mapping[str, Any],
    target: CellTarget,
    *,
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> list[dict[str, Any]]:
    anchor = title._unique_title_row(str(page["title"]), _row_cells(rows))
    if anchor is None:
        return []
    anchored_row, anchor_tokens = anchor
    if _target_identity(anchored_row, "")[0] != _target_identity(target.row_key, "")[0]:
        return []
    labels = structured._accepted_labels(target)
    if not labels:
        return []
    lines = unicodedata.normalize("NFKC", str(page["content"])).splitlines()
    output: list[dict[str, Any]] = []
    for index, line in enumerate(lines[: title.MAXIMUM_TITLE_RECORD_LINES]):
        if _other_visible_row_present(line, anchored_row=anchored_row, rows=rows):
            break
        label = _label_only(line, labels)
        if label is None:
            continue
        stop = min(
            len(lines),
            index + 1 + MAXIMUM_RECORD_LINE_GAP,
            title.MAXIMUM_TITLE_RECORD_LINES,
        )
        for value_index in range(index + 1, stop):
            value_line = lines[value_index]
            if not value_line.strip():
                continue
            if _other_visible_row_present(
                value_line, anchored_row=anchored_row, rows=rows
            ):
                break
            if _label_only(value_line, labels) is not None:
                break
            year = _record_year(value_line)
            if year is not None:
                output.append(
                    {
                        "target_binding_sha256": target.binding_sha256,
                        "row_key": target.row_key,
                        "column": target.column,
                        "value": year,
                        "source_host": _source_key(str(page["host"])),
                        "fetch_integrity": True,
                        "projection_mode": PROJECTION_MODE,
                        "label_line_ordinal": index + 1,
                        "value_line_ordinal": value_index + 1,
                        "normalized_label": label,
                        "title_anchor_token_count": len(anchor_tokens),
                    }
                )
            break
    if len({_normalize(item["value"]) for item in output}) != 1:
        return []
    return output


def _row_cells(
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> list[CellTarget]:
    return [CellTarget(row, "visible row", None) for row, _tokens_ in rows]


def _compute(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None,
) -> dict[str, Any]:
    if isinstance(pages, (str, bytes)):
        raise ValueError("V2.45.02 page vector drifted")
    parent_projection = parent.build_narrative_title_anchor_projection(
        baseline_prediction,
        pages,
        selected_identities=selected_identities,
    )
    parent.validate_narrative_title_anchor_projection(parent_projection)
    titled_pages = copy.deepcopy(parent_projection["pages"])
    cells = _baseline_cells(baseline_prediction)
    rows = title._visible_rows(cells)
    selected = list(parent_projection["selected_target_binding_sha256s"])
    selected_set = set(selected)
    permitted = [cell for cell in cells if cell.binding_sha256 in selected_set]
    admitted_narrative = _admitted_parent_narrative(parent_projection, cells)
    records: list[dict[str, Any]] = []
    for page in titled_pages:
        for target in permitted:
            records.extend(_record_projections(page, target, rows=rows))
    record_unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in records:
        key = (
            item["target_binding_sha256"],
            item["source_host"],
            _normalize(item["value"]),
            item["normalized_label"],
            item["label_line_ordinal"],
            item["value_line_ordinal"],
        )
        record_unique.setdefault(key, item)
    records = [record_unique[key] for key in sorted(record_unique)]
    base_observations = structured._canonical_observations(
        parent_projection["parent_projection"]["observations"]
    )
    narrative_observations = structured._canonical_observations(admitted_narrative)
    record_observations = structured._canonical_observations(records)
    observations = structured._canonical_observations(
        [*base_observations, *narrative_observations, *record_observations]
    )
    before_record_keys = {
        structured._observation_key(item)
        for item in [*base_observations, *narrative_observations]
    }
    novel_records = sum(
        structured._observation_key(item) not in before_record_keys
        for item in record_observations
    )
    mode_counts = Counter(
        [item["projection_mode"] for item in admitted_narrative]
        + [item["projection_mode"] for item in records]
    )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_projection": copy.deepcopy(parent_projection),
        "pages": titled_pages,
        "selected_target_binding_sha256s": selected,
        "admitted_parent_narrative_projections": admitted_narrative,
        "record_bound_projections": records,
        "observations": observations,
        "parent_observation_count": len(parent_projection["observations"]),
        "base_non_narrative_observation_count": len(base_observations),
        "parent_narrative_projection_count": len(
            parent_projection["narrative_title_projections"]
        ),
        "admitted_parent_narrative_projection_count": len(admitted_narrative),
        "rejected_parent_narrative_projection_count": len(
            parent_projection["narrative_title_projections"]
        )
        - len(admitted_narrative),
        "record_bound_projection_count": len(records),
        "novel_record_bound_observation_count": novel_records,
        "combined_observation_count": len(observations),
        "projection_mode_counts": dict(sorted(mode_counts.items())),
        "complete_visible_row_title_anchor_required": True,
        "narrative_subject_must_be_target_or_bounded_generic": True,
        "nonvisible_named_foreign_subject_rejected": True,
        "exact_column_derived_label_required": True,
        "split_label_year_record_gap": MAXIMUM_RECORD_LINE_GAP,
        "single_distinct_record_year_required": True,
        "other_visible_row_stops_record_scope": True,
        "bare_year_used_as_observation": False,
        "parent_artifact_preserved": True,
        "parent_observations_admitted_without_safety_filter": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_record_bound_title_projection(
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
    validate_record_bound_title_projection(value)
    return value


def validate_record_bound_title_projection(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    parent_projection = value.get("parent_projection")
    projections = value.get("record_bound_projections")
    admitted = value.get("admitted_parent_narrative_projections")
    true_fields = (
        "complete_visible_row_title_anchor_required",
        "narrative_subject_must_be_target_or_bounded_generic",
        "nonvisible_named_foreign_subject_rejected",
        "exact_column_derived_label_required",
        "single_distinct_record_year_required",
        "other_visible_row_stops_record_scope",
        "parent_artifact_preserved",
    )
    false_fields = (
        "bare_year_used_as_observation",
        "parent_observations_admitted_without_safety_filter",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    count_fields = (
        "parent_observation_count",
        "base_non_narrative_observation_count",
        "parent_narrative_projection_count",
        "admitted_parent_narrative_projection_count",
        "rejected_parent_narrative_projection_count",
        "record_bound_projection_count",
        "novel_record_bound_observation_count",
        "combined_observation_count",
    )
    if (
        set(value) != CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(parent_projection, Mapping)
        or not isinstance(value.get("pages"), list)
        or not isinstance(value.get("selected_target_binding_sha256s"), list)
        or not isinstance(admitted, list)
        or not isinstance(projections, list)
        or not isinstance(value.get("observations"), list)
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or value.get("split_label_year_record_gap") != MAXIMUM_RECORD_LINE_GAP
        or any(value.get(name) is not True for name in true_fields)
        or any(value.get(name) is not False for name in false_fields)
        or any(
            not isinstance(item, Mapping)
            or set(item) != parent.PROJECTION_KEYS
            or item.get("projection_mode") != parent.PROJECTION_MODE
            for item in admitted
        )
        or any(
            not isinstance(item, Mapping)
            or set(item) != PROJECTION_KEYS
            or item.get("projection_mode") != PROJECTION_MODE
            or item.get("fetch_integrity") is not True
            or not 1 <= item.get("label_line_ordinal", 0)
            < item.get("value_line_ordinal", 0)
            <= title.MAXIMUM_TITLE_RECORD_LINES
            or item["value_line_ordinal"] - item["label_line_ordinal"]
            > MAXIMUM_RECORD_LINE_GAP
            or re.fullmatch(r"(?:17|18|19|20|21)\d{2}", str(item.get("value")))
            is None
            for item in projections
        )
        or value.get("parent_narrative_projection_count")
        != len(parent_projection.get("narrative_title_projections", []))
        or value.get("admitted_parent_narrative_projection_count") != len(admitted)
        or value.get("rejected_parent_narrative_projection_count")
        != value.get("parent_narrative_projection_count") - len(admitted)
        or value.get("record_bound_projection_count") != len(projections)
        or value.get("combined_observation_count")
        != len(value.get("observations", []))
        or value.get("projection_mode_counts")
        != dict(
            sorted(
                Counter(
                    [item["projection_mode"] for item in admitted]
                    + [item["projection_mode"] for item in projections]
                ).items()
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.02 record-bound projection identity drifted")
    parent.validate_narrative_title_anchor_projection(parent_projection)
    baseline = str(
        parent_projection["parent_projection"]["parent_projection"][
            "baseline_prediction"
        ]
    )
    selected_identities = {
        _target_identity(cell.row_key, cell.column)
        for cell in _baseline_cells(baseline)
        if cell.binding_sha256
        in set(value["selected_target_binding_sha256s"])
    }
    expected = _compute(
        baseline,
        value["pages"],
        selected_identities=selected_identities,
    )
    if dict(value) != expected:
        raise ValueError("V2.45.02 record-bound projection replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_record_bound_title_projection",
    "validate_record_bound_title_projection",
]
