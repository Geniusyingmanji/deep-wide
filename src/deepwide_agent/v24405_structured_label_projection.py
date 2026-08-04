"""Replayable structured label/value projection for visible table targets.

V2.44.03 completed all sixteen external tasks but converted only one of
twenty-eight active pages into an observation.  The inherited V2.43.65
projector deliberately stops at line and table-cell boundaries and recognizes
prose such as ``Alpha was released in 2007``.  Public software pages commonly
encode the same fact as either an entity-scoped infobox::

    Alpha
    Release | 5 April 2007

or a comparison table::

    Software | Initial release year
    Alpha    | 2007

This pure successor adds those two *structured* bindings while retaining the
legacy target-segment observations.  A value is never admitted merely because
it is close to an entity: an exact visible entity and an exact, column-derived
field label must participate in the same bounded record.  In particular,
``Stable release`` and ``Latest release`` are not aliases of ``Initial
release``.  The component performs no file, environment, network, model,
search, process, benchmark, evaluator, reward, or score access.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as table
from . import v24365_entity_segment_projection as segment
from . import v24390_uncertainty_active_evidence_runtime as legacy
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget, _normalize, _source_key


POLICY_ID = "v24405_entity_scoped_structured_label_projection_v1"
ROLE = "v24405_structured_label_projection"
MAXIMUM_ENTITY_RECORD_LINES = 16
MAXIMUM_TABLE_ROWS = 128
YEAR_KINDS = frozenset(
    {
        "first_flight_year",
        "release_year",
        "first_appeared_year",
        "first_held_year",
        "opening_year",
        "launch_year",
        "founding_year",
        "year",
    }
)
PROJECTION_MODES = frozenset(
    {
        "entity_block_label_value",
        "inline_label_value",
        "table_header_value",
    }
)
YEAR = re.compile(r"(?<!\d)((?:17|18|19|20|21)\d{2})(?!\d)")
BRACKET_CITATION = re.compile(r"\[[^\]\n]{1,24}\]")
MARKDOWN_RULE = re.compile(r"^:?-{3,}:?$")
LABELS: dict[str, frozenset[str]] = {
    "release_year": frozenset(
        {
            "release",
            "released",
            "release date",
            "initial release",
            "initial release date",
            "initial release year",
            "first release",
            "first release date",
            "first release year",
            "original release",
        }
    ),
    "founding_year": frozenset(
        {
            "founded",
            "founded date",
            "founding year",
            "established",
            "established date",
            "establishment",
            "establishment year",
            "formation",
            "formation year",
        }
    ),
    "opening_year": frozenset(
        {
            "opened",
            "opening date",
            "opening year",
            "first opened",
            "inaugurated",
        }
    ),
    "first_held_year": frozenset(
        {"first held", "first held year", "inaugural", "inaugural year"}
    ),
    "first_appeared_year": frozenset(
        {
            "first appeared",
            "first appeared year",
            "first appearance",
            "first appearance year",
        }
    ),
    "launch_year": frozenset(
        {"launch", "launched", "launch date", "launch year"}
    ),
    "first_flight_year": frozenset(
        {
            "first flight",
            "first flight date",
            "first flight year",
            "maiden flight",
        }
    ),
    "year": frozenset({"year"}),
}
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
    }
)
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_prediction",
        "pages",
        "selected_target_binding_sha256s",
        "legacy_observations",
        "structured_projections",
        "observations",
        "legacy_observation_count",
        "structured_projection_count",
        "novel_structured_observation_count",
        "combined_observation_count",
        "structured_projection_mode_counts",
        "exact_visible_entity_binding_required",
        "exact_column_derived_label_required",
        "entity_record_line_cap",
        "table_row_cap",
        "stable_latest_preview_release_labels_rejected",
        "cross_target_binding_allowed",
        "arbitrary_nearby_year_used_as_observation",
        "legacy_target_segment_observations_preserved",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "catalog_payload_sha256",
    }
)


def _canonical_line(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = BRACKET_CITATION.sub("", text)
    return " ".join(text.strip().strip("| ").split())


def _cells(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    raw = unicodedata.normalize("NFKC", line).strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    values = [_canonical_line(item) for item in raw.split("|")]
    return values if len(values) >= 2 and any(values) else None


def _is_rule_row(cells: Sequence[str]) -> bool:
    return bool(cells) and all(
        not item or MARKDOWN_RULE.fullmatch(item.replace(" ", "")) is not None
        for item in cells
    )


def _entity_equal(value: object, entity: object) -> bool:
    return table._support_normalize(_canonical_line(value)) == table._support_normalize(
        _canonical_line(entity)
    )


def _accepted_labels(target: CellTarget) -> frozenset[str]:
    kind = segment._column_kind(target.column)
    if kind not in YEAR_KINDS:
        return frozenset()
    column = _normalize(target.column)
    values = set(LABELS.get(str(kind), frozenset()))
    if column:
        values.add(column)
        for suffix in (" year", " date"):
            if column.endswith(suffix) and len(column) > len(suffix):
                values.add(column[: -len(suffix)].strip())
    return frozenset(values)


def _label_equal(value: object, labels: frozenset[str]) -> bool:
    return _normalize(BRACKET_CITATION.sub("", str(value or ""))) in labels


def _year(value: object) -> str | None:
    match = YEAR.search(unicodedata.normalize("NFKC", str(value or "")))
    return None if match is None else match.group(1)


def _label_value(line: str, labels: frozenset[str]) -> tuple[str, str] | None:
    cells = _cells(line)
    if cells is not None and len(cells) == 2 and _label_equal(cells[0], labels):
        value = _year(cells[1])
        return (_normalize(cells[0]), value) if value is not None else None
    match = re.fullmatch(r"\s*([^:：\t]{1,120})\s*[:：\t]\s*(.+?)\s*", line)
    if match is None or not _label_equal(match.group(1), labels):
        return None
    value = _year(match.group(2))
    return (_normalize(match.group(1)), value) if value is not None else None


def _projection(
    target: CellTarget,
    *,
    value: str,
    source: str,
    mode: str,
    line_ordinal: int,
    normalized_label: str,
) -> dict[str, Any]:
    output = {
        "target_binding_sha256": target.binding_sha256,
        "row_key": target.row_key,
        "column": target.column,
        "value": value,
        "source_host": source,
        "fetch_integrity": True,
        "projection_mode": mode,
        "line_ordinal": line_ordinal,
        "normalized_label": normalized_label,
    }
    if set(output) != PROJECTION_KEYS or mode not in PROJECTION_MODES:
        raise ValueError("V2.44.05 structured projection schema drifted")
    return output


def _entity_block_projections(
    lines: Sequence[str],
    target: CellTarget,
    *,
    all_targets: Sequence[CellTarget],
    source: str,
) -> list[dict[str, Any]]:
    labels = _accepted_labels(target)
    if not labels:
        return []
    output: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        cells = _cells(line)
        if cells is not None and len(cells) >= 3 and _entity_equal(
            cells[0], target.row_key
        ):
            for label_index in range(1, len(cells) - 1):
                if not _label_equal(cells[label_index], labels):
                    continue
                value = _year(cells[label_index + 1])
                if value is not None:
                    output.append(
                        _projection(
                            target,
                            value=value,
                            source=source,
                            mode="inline_label_value",
                            line_ordinal=index + 1,
                            normalized_label=_normalize(cells[label_index]),
                        )
                    )
        if not _entity_equal(line, target.row_key):
            continue
        for next_index in range(
            index + 1,
            min(len(lines), index + 1 + MAXIMUM_ENTITY_RECORD_LINES),
        ):
            current = lines[next_index]
            if not current.strip():
                break
            if any(
                _entity_equal(current, other.row_key)
                for other in all_targets
                if other.binding_sha256 != target.binding_sha256
            ):
                break
            bound = _label_value(current, labels)
            if bound is None:
                continue
            label, value = bound
            output.append(
                _projection(
                    target,
                    value=value,
                    source=source,
                    mode="entity_block_label_value",
                    line_ordinal=next_index + 1,
                    normalized_label=label,
                )
            )
    return output


def _table_projections(
    lines: Sequence[str], target: CellTarget, *, source: str
) -> list[dict[str, Any]]:
    labels = _accepted_labels(target)
    if not labels:
        return []
    output: list[dict[str, Any]] = []
    for header_index, header_line in enumerate(lines):
        header = _cells(header_line)
        if header is None or _is_rule_row(header):
            continue
        label_indexes = [
            index
            for index, value in enumerate(header)
            if index > 0 and _label_equal(value, labels)
        ]
        if not label_indexes:
            continue
        for row_index in range(
            header_index + 1,
            min(len(lines), header_index + 1 + MAXIMUM_TABLE_ROWS),
        ):
            if not lines[row_index].strip():
                break
            row = _cells(lines[row_index])
            if row is None:
                break
            if _is_rule_row(row):
                continue
            if len(row) != len(header) or not _entity_equal(row[0], target.row_key):
                continue
            for label_index in label_indexes:
                value = _year(row[label_index])
                if value is None:
                    continue
                output.append(
                    _projection(
                        target,
                        value=value,
                        source=source,
                        mode="table_header_value",
                        line_ordinal=row_index + 1,
                        normalized_label=_normalize(header[label_index]),
                    )
                )
    return output


def _observation_key(value: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        table._support_normalize(value["row_key"]),
        table._normalize_column(value["column"]),
        _source_key(str(value["source_host"])),
        _normalize(value["value"]),
    )


def _canonical_observations(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for raw in values:
        observation = {
            "row_key": str(raw["row_key"]),
            "column": str(raw["column"]),
            "value": str(raw["value"]),
            "source_host": _source_key(str(raw["source_host"])),
            "fetch_integrity": raw["fetch_integrity"] is True,
        }
        if not observation["fetch_integrity"]:
            raise ValueError("V2.44.05 observation lacks fetch integrity")
        output.setdefault(_observation_key(observation), observation)
    return [output[key] for key in sorted(output)]


def _selected_bindings(
    cells: Sequence[CellTarget],
    selected_identities: set[tuple[str, str]] | None,
) -> list[str]:
    visible = {
        legacy._target_identity(item.row_key, item.column): item.binding_sha256
        for item in cells
    }
    identities = set(visible) if selected_identities is None else set(selected_identities)
    if not identities.issubset(visible):
        raise ValueError("V2.44.05 selected projection target is not visible")
    return sorted(visible[identity] for identity in identities)


def _compute(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_target_binding_sha256s: Sequence[str],
) -> dict[str, Any]:
    cells = legacy._baseline_cells(baseline_prediction)
    selected = list(selected_target_binding_sha256s)
    if selected != sorted(set(selected)) or not set(selected).issubset(
        {item.binding_sha256 for item in cells}
    ):
        raise ValueError("V2.44.05 selected binding vector drifted")
    permitted_cells = [item for item in cells if item.binding_sha256 in set(selected)]
    permitted_identities = {
        legacy._target_identity(item.row_key, item.column) for item in permitted_cells
    }
    plain_pages = [legacy._plain_page(item) for item in pages]
    legacy_observations = legacy._project_observations(
        baseline_prediction,
        plain_pages,
        selected_identities=permitted_identities,
    )
    projections: list[dict[str, Any]] = []
    for page in plain_pages:
        if page["fetch_integrity"] is not True:
            continue
        source = _source_key(str(page["host"]))
        lines = unicodedata.normalize("NFKC", str(page["content"])).splitlines()
        for target in permitted_cells:
            projections.extend(
                _entity_block_projections(
                    lines,
                    target,
                    all_targets=cells,
                    source=source,
                )
            )
            projections.extend(_table_projections(lines, target, source=source))
    unique_projections: dict[
        tuple[str, str, str, str, str, int], dict[str, Any]
    ] = {}
    for item in projections:
        key = (
            str(item["target_binding_sha256"]),
            str(item["source_host"]),
            _normalize(item["value"]),
            str(item["projection_mode"]),
            str(item["normalized_label"]),
            int(item["line_ordinal"]),
        )
        unique_projections.setdefault(key, item)
    structured = [unique_projections[key] for key in sorted(unique_projections)]
    structured_observations = _canonical_observations(structured)
    legacy_canonical = _canonical_observations(legacy_observations)
    combined = _canonical_observations([*legacy_canonical, *structured_observations])
    legacy_keys = {_observation_key(item) for item in legacy_canonical}
    novel = sum(
        _observation_key(item) not in legacy_keys for item in structured_observations
    )
    mode_counts = Counter(str(item["projection_mode"]) for item in structured)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "baseline_prediction": baseline_prediction,
        "pages": copy.deepcopy(plain_pages),
        "selected_target_binding_sha256s": selected,
        "legacy_observations": legacy_canonical,
        "structured_projections": structured,
        "observations": combined,
        "legacy_observation_count": len(legacy_canonical),
        "structured_projection_count": len(structured),
        "novel_structured_observation_count": novel,
        "combined_observation_count": len(combined),
        "structured_projection_mode_counts": dict(sorted(mode_counts.items())),
        "exact_visible_entity_binding_required": True,
        "exact_column_derived_label_required": True,
        "entity_record_line_cap": MAXIMUM_ENTITY_RECORD_LINES,
        "table_row_cap": MAXIMUM_TABLE_ROWS,
        "stable_latest_preview_release_labels_rejected": True,
        "cross_target_binding_allowed": False,
        "arbitrary_nearby_year_used_as_observation": False,
        "legacy_target_segment_observations_preserved": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_structured_label_projection(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    cells = legacy._baseline_cells(baseline_prediction)
    selected = _selected_bindings(cells, selected_identities)
    value = _compute(
        baseline_prediction,
        pages,
        selected_target_binding_sha256s=selected,
    )
    validate_structured_label_projection(value)
    return value


def validate_structured_label_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    projections = value.get("structured_projections")
    if (
        set(value) != CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(value.get("baseline_prediction"), str)
        or not isinstance(value.get("pages"), list)
        or not isinstance(value.get("selected_target_binding_sha256s"), list)
        or not isinstance(projections, list)
        or any(
            not isinstance(item, Mapping)
            or set(item) != PROJECTION_KEYS
            or item.get("projection_mode") not in PROJECTION_MODES
            or item.get("fetch_integrity") is not True
            or isinstance(item.get("line_ordinal"), bool)
            or not isinstance(item.get("line_ordinal"), int)
            or item["line_ordinal"] < 1
            for item in projections
        )
        or value.get("legacy_observation_count")
        != len(value.get("legacy_observations", []))
        or value.get("structured_projection_count") != len(projections)
        or value.get("combined_observation_count")
        != len(value.get("observations", []))
        or value.get("structured_projection_mode_counts")
        != dict(
            sorted(Counter(item["projection_mode"] for item in projections).items())
        )
        or value.get("exact_visible_entity_binding_required") is not True
        or value.get("exact_column_derived_label_required") is not True
        or value.get("entity_record_line_cap") != MAXIMUM_ENTITY_RECORD_LINES
        or value.get("table_row_cap") != MAXIMUM_TABLE_ROWS
        or value.get("stable_latest_preview_release_labels_rejected") is not True
        or value.get("cross_target_binding_allowed") is not False
        or value.get("arbitrary_nearby_year_used_as_observation") is not False
        or value.get("legacy_target_segment_observations_preserved") is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get(
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.05 structured projection identity drifted")
    expected = _compute(
        str(value["baseline_prediction"]),
        value["pages"],
        selected_target_binding_sha256s=value["selected_target_binding_sha256s"],
    )
    if dict(value) != expected:
        raise ValueError("V2.44.05 structured projection replay drifted")
    return copy.deepcopy(dict(value))


def project_observations(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    return build_structured_label_projection(
        baseline_prediction,
        pages,
        selected_identities=selected_identities,
    )["observations"]


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_structured_label_projection",
    "project_observations",
    "validate_structured_label_projection",
]
