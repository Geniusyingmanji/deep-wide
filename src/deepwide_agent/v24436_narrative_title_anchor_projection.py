"""Conservative narrative relation projection under a unique page-title anchor.

V2.44.34 observed unique title alignment on seventeen of twenty active pages,
but the V2.44.28 successor emitted no title projection.  V2.44.28 accepts only
explicit key/value records such as ``Founded | 1898``.  This pure append-only
successor preserves that parent verbatim and adds a second route for bounded
narrative records such as ``the club was founded in 1898``.

The title must still match exactly one complete visible row, and that row must
be the selected target row.  The column kind determines the accepted relation
vocabulary.  A relation word and one four-digit year must occur in the same
bounded line before any other visible row is encountered.  Multiple distinct
years reject the whole page/target pair.  A nearby year without an explicit
relation is never evidence.

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

from . import v24365_entity_segment_projection as segment
from . import v24405_structured_label_projection as structured
from . import v24428_unique_title_anchor_projection as parent
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget, _normalize, _source_key
from .v24390_uncertainty_active_evidence_runtime import (
    _baseline_cells,
    _target_identity,
)


POLICY_ID = "v24436_unique_title_narrative_relation_projection_v1"
ROLE = "v24436_narrative_title_anchor_projection"
MAXIMUM_NARRATIVE_RECORD_LINES = parent.MAXIMUM_TITLE_RECORD_LINES
PROJECTION_MODE = "unique_title_anchor_narrative_relation"
REASONS = (
    "unique_title_anchor_absent",
    "title_anchor_other_selected_row",
    "unsupported_narrative_column_kind",
    "explicit_narrative_relation_absent",
    "multiple_distinct_narrative_years",
    "narrative_projection_emitted",
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
        "line_ordinal",
        "relation_kind",
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
        "narrative_title_projections",
        "observations",
        "parent_observation_count",
        "parent_title_anchor_projection_count",
        "page_target_pair_count",
        "reason_counts",
        "narrative_projection_count",
        "novel_narrative_observation_count",
        "combined_observation_count",
        "narrative_projection_mode_counts",
        "complete_visible_row_title_anchor_required",
        "title_anchor_must_match_selected_row",
        "column_kind_relation_vocabulary_required",
        "relation_and_year_must_share_bounded_line",
        "single_distinct_narrative_year_required",
        "other_visible_row_stops_title_scope",
        "arbitrary_nearby_year_used_as_observation",
        "parent_projection_preserved",
        "reason_partition_exact",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "catalog_payload_sha256",
    }
)


def _other_visible_row_present(
    line: str, *, anchored_row: str, all_rows: Sequence[tuple[str, tuple[str, ...]]]
) -> bool:
    line_tokens = parent._tokens(line)
    return any(
        not structured._entity_equal(row_key, anchored_row)
        and parent._subsequence_start(line_tokens, row_tokens) is not None
        for row_key, row_tokens in all_rows
    )


def _narrative_relations(
    page: Mapping[str, Any],
    target: CellTarget,
    *,
    all_rows: Sequence[tuple[str, tuple[str, ...]]],
) -> tuple[str, list[tuple[str, int, str]], int]:
    anchor = parent._unique_title_row(str(page["title"]), _cells_from_rows(all_rows))
    if anchor is None:
        return REASONS[0], [], 0
    anchored_row, anchor_tokens = anchor
    if _target_identity(anchored_row, "")[0] != _target_identity(target.row_key, "")[0]:
        return REASONS[1], [], len(anchor_tokens)
    kind = segment._column_kind(target.column)
    if kind not in structured.YEAR_KINDS or kind not in segment.YEAR_RELATIONS:
        return REASONS[2], [], len(anchor_tokens)
    output: dict[tuple[str, int, str], tuple[str, int, str]] = {}
    lines = unicodedata.normalize("NFKC", str(page["content"])).splitlines()
    for index, line in enumerate(lines[:MAXIMUM_NARRATIVE_RECORD_LINES]):
        if _other_visible_row_present(
            line, anchored_row=anchored_row, all_rows=all_rows
        ):
            break
        for relation in segment._relations(line, kind):
            item = (relation.value, index + 1, relation.kind)
            output[item] = item
    relations = [output[key] for key in sorted(output, key=lambda item: (item[1], item))]
    distinct = {value for value, _, _ in relations}
    if not relations:
        return REASONS[3], [], len(anchor_tokens)
    if len(distinct) != 1:
        return REASONS[4], relations, len(anchor_tokens)
    return REASONS[5], relations, len(anchor_tokens)


def _cells_from_rows(
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> list[CellTarget]:
    # ``_unique_title_row`` needs only row surfaces.  Use one inert column per
    # visible row; values never participate in title matching.
    return [CellTarget(row_key, "visible row", None) for row_key, _ in rows]


def _projection(
    page: Mapping[str, Any],
    target: CellTarget,
    relations: Sequence[tuple[str, int, str]],
    *,
    anchor_token_count: int,
) -> dict[str, Any]:
    value, line_ordinal, relation_kind = relations[0]
    return {
        "target_binding_sha256": target.binding_sha256,
        "row_key": target.row_key,
        "column": target.column,
        "value": value,
        "source_host": _source_key(str(page["host"])),
        "fetch_integrity": True,
        "projection_mode": PROJECTION_MODE,
        "line_ordinal": line_ordinal,
        "relation_kind": relation_kind,
        "title_anchor_token_count": anchor_token_count,
    }


def _compute(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None,
) -> dict[str, Any]:
    if isinstance(pages, (str, bytes)):
        raise ValueError("V2.44.36 page vector drifted")
    titled_pages = [parent._plain_titled_page(item) for item in pages]
    parent_projection = parent.build_unique_title_anchor_projection(
        baseline_prediction,
        titled_pages,
        selected_identities=selected_identities,
    )
    parent.validate_unique_title_anchor_projection(parent_projection)
    cells = _baseline_cells(baseline_prediction)
    rows = parent._visible_rows(cells)
    selected = list(parent_projection["selected_target_binding_sha256s"])
    selected_set = set(selected)
    permitted = [cell for cell in cells if cell.binding_sha256 in selected_set]
    reason_counts: Counter[str] = Counter()
    projections: list[dict[str, Any]] = []
    for page in titled_pages:
        for target in permitted:
            reason, relations, anchor_tokens = _narrative_relations(
                page, target, all_rows=rows
            )
            reason_counts[reason] += 1
            if reason == "narrative_projection_emitted":
                projections.append(
                    _projection(
                        page,
                        target,
                        relations,
                        anchor_token_count=anchor_tokens,
                    )
                )
    unique: dict[tuple[str, str, str, str, int], dict[str, Any]] = {}
    for item in projections:
        key = (
            str(item["target_binding_sha256"]),
            str(item["source_host"]),
            _normalize(item["value"]),
            str(item["relation_kind"]),
            int(item["line_ordinal"]),
        )
        unique.setdefault(key, item)
    projections = [unique[key] for key in sorted(unique)]
    narrative_observations = structured._canonical_observations(projections)
    parent_observations = structured._canonical_observations(
        parent_projection["observations"]
    )
    observations = structured._canonical_observations(
        [*parent_observations, *narrative_observations]
    )
    parent_keys = {structured._observation_key(item) for item in parent_observations}
    novel = sum(
        structured._observation_key(item) not in parent_keys
        for item in narrative_observations
    )
    mode_counts = Counter(item["projection_mode"] for item in projections)
    complete_reasons = {name: int(reason_counts.get(name, 0)) for name in REASONS}
    pair_count = len(titled_pages) * len(permitted)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_projection": copy.deepcopy(parent_projection),
        "pages": copy.deepcopy(titled_pages),
        "selected_target_binding_sha256s": selected,
        "narrative_title_projections": projections,
        "observations": observations,
        "parent_observation_count": len(parent_observations),
        "parent_title_anchor_projection_count": int(
            parent_projection["title_anchor_projection_count"]
        ),
        "page_target_pair_count": pair_count,
        "reason_counts": complete_reasons,
        "narrative_projection_count": len(projections),
        "novel_narrative_observation_count": novel,
        "combined_observation_count": len(observations),
        "narrative_projection_mode_counts": dict(sorted(mode_counts.items())),
        "complete_visible_row_title_anchor_required": True,
        "title_anchor_must_match_selected_row": True,
        "column_kind_relation_vocabulary_required": True,
        "relation_and_year_must_share_bounded_line": True,
        "single_distinct_narrative_year_required": True,
        "other_visible_row_stops_title_scope": True,
        "arbitrary_nearby_year_used_as_observation": False,
        "parent_projection_preserved": True,
        "reason_partition_exact": sum(complete_reasons.values()) == pair_count,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_narrative_title_anchor_projection(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    value = _compute(
        baseline_prediction, pages, selected_identities=selected_identities
    )
    validate_narrative_title_anchor_projection(value)
    return value


def validate_narrative_title_anchor_projection(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    parent_projection = value.get("parent_projection")
    pages = value.get("pages")
    projections = value.get("narrative_title_projections")
    reason_counts = value.get("reason_counts")
    true_fields = (
        "complete_visible_row_title_anchor_required",
        "title_anchor_must_match_selected_row",
        "column_kind_relation_vocabulary_required",
        "relation_and_year_must_share_bounded_line",
        "single_distinct_narrative_year_required",
        "other_visible_row_stops_title_scope",
        "parent_projection_preserved",
        "reason_partition_exact",
    )
    false_fields = (
        "arbitrary_nearby_year_used_as_observation",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    count_fields = (
        "parent_observation_count",
        "parent_title_anchor_projection_count",
        "page_target_pair_count",
        "narrative_projection_count",
        "novel_narrative_observation_count",
        "combined_observation_count",
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
        or not isinstance(reason_counts, Mapping)
        or tuple(reason_counts) != REASONS
        or any(
            isinstance(reason_counts.get(name), bool)
            or not isinstance(reason_counts.get(name), int)
            or reason_counts[name] < 0
            for name in REASONS
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(value.get(name) is not True for name in true_fields)
        or any(value.get(name) is not False for name in false_fields)
        or any(
            not isinstance(item, Mapping)
            or set(item) != PROJECTION_KEYS
            or item.get("projection_mode") != PROJECTION_MODE
            or item.get("fetch_integrity") is not True
            or item.get("relation_kind") not in segment.YEAR_RELATIONS
            or isinstance(item.get("line_ordinal"), bool)
            or not isinstance(item.get("line_ordinal"), int)
            or not 1 <= item["line_ordinal"] <= MAXIMUM_NARRATIVE_RECORD_LINES
            or isinstance(item.get("title_anchor_token_count"), bool)
            or not isinstance(item.get("title_anchor_token_count"), int)
            or item["title_anchor_token_count"] < 1
            or re.fullmatch(r"(?:17|18|19|20|21)\d{2}", str(item.get("value")))
            is None
            for item in projections
        )
        or sum(int(reason_counts[name]) for name in REASONS)
        != value.get("page_target_pair_count")
        or value.get("narrative_projection_count") != len(projections)
        or value.get("combined_observation_count")
        != len(value.get("observations", []))
        or value.get("narrative_projection_mode_counts")
        != dict(sorted(Counter(item["projection_mode"] for item in projections).items()))
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.36 narrative title projection identity drifted")
    parent.validate_unique_title_anchor_projection(parent_projection)
    selected_identities = {
        _target_identity(cell.row_key, cell.column)
        for cell in _baseline_cells(str(parent_projection["parent_projection"]["baseline_prediction"]))
        if cell.binding_sha256 in set(value["selected_target_binding_sha256s"])
    }
    expected = _compute(
        str(parent_projection["parent_projection"]["baseline_prediction"]),
        pages,
        selected_identities=selected_identities,
    )
    if dict(value) != expected:
        raise ValueError("V2.44.36 narrative title projection replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "REASONS",
    "ROLE",
    "build_narrative_title_anchor_projection",
    "validate_narrative_title_anchor_projection",
]
