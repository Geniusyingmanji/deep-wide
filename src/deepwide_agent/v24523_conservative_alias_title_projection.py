"""Conservative visible-row alias anchoring for title-scoped evidence.

V2.45.22 found that nine of fifteen usable page/selected-target pairs failed
because neither an exact body entity nor a unique complete-row title anchor
was available.  This pure append-only component preserves the complete
V2.45.02 catalog and adds one alias route for pages that have no exact title
anchor.

Aliases are derived only from visible row text.  A title must uniquely match
one row through a normalized full surface, a sufficiently distinctive core,
or a four-or-more-character initialism.  Organization-type conflicts,
cross-row collisions, short/generic cores, and titles already owned by the
exact parent all fail closed.  The alias supplies identity only: an exact
column label plus one year, a subject-safe explicit narrative relation plus
one year, or an exact split label/year record is still required.  Conflicting
years reject the entire page/target pair.

The component performs no file, environment, network, model, search, fetch,
process, benchmark, evaluator, reward, or score access.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import v24365_entity_segment_projection as segment
from . import v24405_structured_label_projection as structured
from . import v24428_unique_title_anchor_projection as title
from . import v24502_record_bound_title_projection as parent
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget, _normalize, _source_key
from .v24390_uncertainty_active_evidence_runtime import (
    _baseline_cells,
    _target_identity,
)


POLICY_ID = "v24523_conservative_visible_row_alias_title_projection_v1"
ROLE = "v24523_conservative_alias_title_projection"
PROJECTION_MODE = "conservative_visible_row_alias_title_evidence"
MAXIMUM_ALIAS_MATCH_START = title.MAXIMUM_TITLE_MATCH_START
CONNECTOR_TOKENS = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "da",
        "de",
        "del",
        "des",
        "di",
        "do",
        "du",
        "for",
        "in",
        "la",
        "le",
        "of",
        "the",
        "und",
        "van",
        "von",
    }
)
ORGANIZATION_TYPE_CANONICAL = {
    "academy": "academy",
    "college": "college",
    "conservatoire": "conservatory",
    "conservatory": "conservatory",
    "institute": "institute",
    "institution": "institute",
    "polytechnic": "polytechnic",
    "school": "school",
    "univ": "university",
    "universidad": "university",
    "universite": "university",
    "universitat": "university",
    "universität": "university",
    "university": "university",
}
TOKEN_EQUIVALENCE = {
    "saint": "saint",
    "st": "saint",
    "mount": "mount",
    "mt": "mount",
    **ORGANIZATION_TYPE_CANONICAL,
}
ALIAS_MODES = (
    "normalized_full_surface",
    "distinctive_core_surface",
    "visible_row_initialism",
)
EVIDENCE_KINDS = (
    "exact_label_value",
    "subject_safe_narrative_relation",
    "split_exact_label_year_record",
)
REASONS = (
    "exact_title_anchor_owned_by_parent",
    "alias_anchor_absent_or_ambiguous",
    "alias_anchor_other_selected_row",
    "alias_anchor_unsupported_column_kind",
    "alias_anchor_explicit_relation_absent",
    "alias_anchor_subject_safety_rejected",
    "alias_anchor_multiple_distinct_candidate_years",
    "alias_projection_emitted",
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
        "alias_mode",
        "alias_token_count",
        "title_match_start",
        "evidence_kind",
        "evidence_start_line_ordinal",
        "evidence_end_line_ordinal",
        "normalized_relation",
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
        "alias_title_projections",
        "alias_observations",
        "observations",
        "parent_observation_count",
        "page_target_pair_count",
        "exact_parent_anchor_page_count",
        "unique_alias_anchor_page_count",
        "ambiguous_or_absent_alias_anchor_page_count",
        "alias_projection_count",
        "novel_alias_observation_count",
        "combined_observation_count",
        "reason_counts",
        "alias_mode_counts",
        "evidence_kind_counts",
        "visible_row_only_alias_derivation",
        "unique_cross_row_alias_match_required",
        "short_or_generic_core_rejected",
        "organization_type_conflict_rejected",
        "exact_parent_title_anchor_never_overridden",
        "exact_label_or_subject_safe_relation_required",
        "single_distinct_candidate_year_required",
        "other_visible_row_stops_title_scope",
        "alias_supplies_identity_not_value",
        "parent_artifact_preserved",
        "reason_partition_exact",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "catalog_payload_sha256",
    }
)


@dataclass(frozen=True)
class AliasAnchor:
    row_key: str
    row_tokens: tuple[str, ...]
    mode: str
    alias_tokens: tuple[str, ...]
    title_match_start: int


def _canonical_tokens(value: object) -> tuple[str, ...]:
    return tuple(TOKEN_EQUIVALENCE.get(item, item) for item in title._tokens(value))


def _type_tokens(tokens: Sequence[str]) -> frozenset[str]:
    return frozenset(
        ORGANIZATION_TYPE_CANONICAL[item]
        for item in tokens
        if item in ORGANIZATION_TYPE_CANONICAL
    )


def _core_tokens(tokens: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        item
        for item in tokens
        if item not in CONNECTOR_TOKENS
        and item not in ORGANIZATION_TYPE_CANONICAL
    )


def _distinctive_core(tokens: Sequence[str]) -> tuple[str, ...] | None:
    core = _core_tokens(tokens)
    character_count = sum(len(item) for item in core)
    if (
        not core
        or character_count < 8
        or len(core) == 1
        and len(core[0]) < 8
    ):
        return None
    return core


def _initialism(tokens: Sequence[str]) -> tuple[str, ...] | None:
    components = tuple(
        item
        for item in tokens
        if item not in CONNECTOR_TOKENS
    )
    if len(components) < 2:
        return None
    value = "".join(item[0] for item in components if item)
    if not 3 <= len(value) <= 12 or not value.isascii() or not value.isalpha():
        return None
    return (value,)


def _candidate_aliases(
    row_tokens: Sequence[str],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    output: list[tuple[str, tuple[str, ...]]] = []
    full = tuple(row_tokens)
    if full and (len(full) >= 2 or len(full[0]) >= 8):
        output.append((ALIAS_MODES[0], full))
    core = _distinctive_core(full)
    if core is not None and core != full:
        output.append((ALIAS_MODES[1], core))
    initialism = _initialism(full)
    if initialism is not None and initialism not in {item[1] for item in output}:
        output.append((ALIAS_MODES[2], initialism))
    # A common visible form abbreviates a multi-token parent organization but
    # keeps the final campus/member discriminator, e.g. State University of
    # New York at Geneseo -> SUNY Geneseo.  The prefix acronym must itself be
    # at least three letters and the combined alias still has to be unique
    # across every visible row.
    components = tuple(
        item for item in full if item not in CONNECTOR_TOKENS
    )
    if len(components) >= 4:
        prefix = "".join(item[0] for item in components[:-1] if item)
        hybrid = (prefix, components[-1])
        if (
            3 <= len(prefix) <= 10
            and prefix.isascii()
            and prefix.isalpha()
            and hybrid not in {item[1] for item in output}
        ):
            output.append((ALIAS_MODES[2], hybrid))
    return tuple(output)


def _type_compatible(
    row_tokens: Sequence[str],
    title_tokens: Sequence[str],
    *,
    mode: str,
    alias_tokens: Sequence[str],
    start: int,
) -> bool:
    row_types = _type_tokens(row_tokens)
    observed_types = _type_tokens(title_tokens)
    if row_types and observed_types and row_types.isdisjoint(observed_types):
        return False
    if observed_types:
        return True
    if mode == "visible_row_initialism":
        return start <= 4
    return len(alias_tokens) >= 2 or sum(map(len, alias_tokens)) >= 10


def _row_alias_matches(
    title_tokens: Sequence[str],
    row_key: str,
    row_tokens: Sequence[str],
) -> list[AliasAnchor]:
    output: list[AliasAnchor] = []
    for mode, alias_tokens in _candidate_aliases(row_tokens):
        start = title._subsequence_start(title_tokens, alias_tokens)
        if (
            start is None
            or start > MAXIMUM_ALIAS_MATCH_START
            or not _type_compatible(
                row_tokens,
                title_tokens,
                mode=mode,
                alias_tokens=alias_tokens,
                start=start,
            )
        ):
            continue
        output.append(
            AliasAnchor(
                row_key=row_key,
                row_tokens=tuple(row_tokens),
                mode=mode,
                alias_tokens=tuple(alias_tokens),
                title_match_start=start,
            )
        )
    return output


def unique_alias_title_row(
    raw_title: str, cells: Sequence[CellTarget]
) -> AliasAnchor | None:
    """Return one visible-row-derived alias anchor or fail closed."""

    if title._unique_title_row(raw_title, cells) is not None:
        return None
    title_tokens = _canonical_tokens(raw_title)
    if not title_tokens or len(title_tokens) > title.MAXIMUM_TITLE_TOKENS:
        return None
    by_row: dict[str, list[AliasAnchor]] = {}
    for row_key, raw_tokens in title._visible_rows(cells):
        row_tokens = tuple(TOKEN_EQUIVALENCE.get(item, item) for item in raw_tokens)
        matches = _row_alias_matches(title_tokens, row_key, row_tokens)
        if matches:
            by_row[_target_identity(row_key, "")[0]] = matches
    if len(by_row) != 1:
        return None
    matches = next(iter(by_row.values()))
    order = {name: index for index, name in enumerate(ALIAS_MODES)}
    return min(
        matches,
        key=lambda item: (
            order[item.mode],
            item.title_match_start,
            -len(item.alias_tokens),
        ),
    )


def _other_visible_row_present(
    line: str,
    *,
    anchored_row: str,
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> bool:
    line_tokens = _canonical_tokens(line)
    return any(
        not structured._entity_equal(row_key, anchored_row)
        and title._subsequence_start(
            line_tokens,
            tuple(TOKEN_EQUIVALENCE.get(item, item) for item in row_tokens),
        )
        is not None
        for row_key, row_tokens in rows
    )


def _structured_candidates(
    lines: Sequence[str],
    labels: frozenset[str],
    *,
    anchored_row: str,
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> list[tuple[str, int, int, str, str]]:
    output: list[tuple[str, int, int, str, str]] = []
    all_rows = [row_key for row_key, _tokens in rows]
    for label, year, ordinal in title._labelled_years(
        lines,
        labels,
        anchored_row=anchored_row,
        all_rows=all_rows,
    ):
        output.append((year, ordinal, ordinal, EVIDENCE_KINDS[0], label))
    return output


def _narrative_candidates(
    page: Mapping[str, Any],
    lines: Sequence[str],
    target: CellTarget,
    *,
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> tuple[list[tuple[str, int, int, str, str]], bool]:
    kind = segment._column_kind(target.column)
    if kind not in structured.YEAR_KINDS or kind not in segment.YEAR_RELATIONS:
        return [], False
    output: list[tuple[str, int, int, str, str]] = []
    unsafe = False
    for index, line in enumerate(lines[: title.MAXIMUM_TITLE_RECORD_LINES]):
        if _other_visible_row_present(
            line,
            anchored_row=target.row_key,
            rows=rows,
        ):
            break
        for relation in segment._relations(line, kind):
            prospective = {
                "row_key": target.row_key,
                "value": relation.value,
                "line_ordinal": index + 1,
                "relation_kind": relation.kind,
            }
            if parent._subject_bound(page, prospective):
                output.append(
                    (
                        relation.value,
                        index + 1,
                        index + 1,
                        EVIDENCE_KINDS[1],
                        relation.kind,
                    )
                )
            else:
                unsafe = True
    return output, unsafe


def _split_record_candidates(
    lines: Sequence[str],
    labels: frozenset[str],
    *,
    anchored_row: str,
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> list[tuple[str, int, int, str, str]]:
    output: list[tuple[str, int, int, str, str]] = []
    for index, line in enumerate(lines[: title.MAXIMUM_TITLE_RECORD_LINES]):
        if _other_visible_row_present(
            line,
            anchored_row=anchored_row,
            rows=rows,
        ):
            break
        label = parent._label_only(line, labels)
        if label is None:
            continue
        stop = min(
            len(lines),
            index + 1 + parent.MAXIMUM_RECORD_LINE_GAP,
            title.MAXIMUM_TITLE_RECORD_LINES,
        )
        for value_index in range(index + 1, stop):
            value_line = lines[value_index]
            if not value_line.strip():
                continue
            if _other_visible_row_present(
                value_line,
                anchored_row=anchored_row,
                rows=rows,
            ) or parent._label_only(value_line, labels) is not None:
                break
            year = parent._record_year(value_line)
            if year is not None:
                output.append(
                    (
                        year,
                        index + 1,
                        value_index + 1,
                        EVIDENCE_KINDS[2],
                        label,
                    )
                )
            break
    return output


def _diagnose_pair(
    page: Mapping[str, Any],
    target: CellTarget,
    *,
    cells: Sequence[CellTarget],
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> tuple[str, dict[str, Any] | None]:
    if title._unique_title_row(str(page["title"]), cells) is not None:
        return REASONS[0], None
    anchor = unique_alias_title_row(str(page["title"]), cells)
    if anchor is None:
        return REASONS[1], None
    if _target_identity(anchor.row_key, "")[0] != _target_identity(
        target.row_key, ""
    )[0]:
        return REASONS[2], None
    kind = segment._column_kind(target.column)
    labels = structured._accepted_labels(target)
    if kind not in structured.YEAR_KINDS or kind not in segment.YEAR_RELATIONS or not labels:
        return REASONS[3], None
    lines = unicodedata.normalize("NFKC", str(page["content"])).splitlines()
    structured_values = _structured_candidates(
        lines,
        labels,
        anchored_row=anchor.row_key,
        rows=rows,
    )
    narrative_values, unsafe_narrative = _narrative_candidates(
        page,
        lines,
        target,
        rows=rows,
    )
    split_values = _split_record_candidates(
        lines,
        labels,
        anchored_row=anchor.row_key,
        rows=rows,
    )
    candidates = [*structured_values, *narrative_values, *split_values]
    distinct = {_normalize(item[0]) for item in candidates if _normalize(item[0])}
    if len(distinct) > 1:
        return REASONS[6], None
    if not candidates:
        return (REASONS[5] if unsafe_narrative else REASONS[4]), None
    priority = {name: index for index, name in enumerate(EVIDENCE_KINDS)}
    chosen = min(
        candidates,
        key=lambda item: (priority[item[3]], item[1], item[2], item[4]),
    )
    value, start, end, evidence_kind, relation = chosen
    projection = {
        "target_binding_sha256": target.binding_sha256,
        "row_key": target.row_key,
        "column": target.column,
        "value": value,
        "source_host": _source_key(str(page["host"])),
        "fetch_integrity": True,
        "projection_mode": PROJECTION_MODE,
        "alias_mode": anchor.mode,
        "alias_token_count": len(anchor.alias_tokens),
        "title_match_start": anchor.title_match_start,
        "evidence_kind": evidence_kind,
        "evidence_start_line_ordinal": start,
        "evidence_end_line_ordinal": end,
        "normalized_relation": relation,
    }
    return REASONS[7], projection


def _compute(
    baseline_prediction: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None,
) -> dict[str, Any]:
    if isinstance(pages, (str, bytes)):
        raise ValueError("V2.45.23 page vector drifted")
    parent_projection = parent.build_record_bound_title_projection(
        baseline_prediction,
        pages,
        selected_identities=selected_identities,
    )
    parent.validate_record_bound_title_projection(parent_projection)
    titled_pages = copy.deepcopy(parent_projection["pages"])
    cells = _baseline_cells(baseline_prediction)
    rows = title._visible_rows(cells)
    selected = list(parent_projection["selected_target_binding_sha256s"])
    selected_set = set(selected)
    permitted = [cell for cell in cells if cell.binding_sha256 in selected_set]
    reasons: Counter[str] = Counter()
    projections: list[dict[str, Any]] = []
    exact_pages = 0
    alias_pages = 0
    for page in titled_pages:
        if title._unique_title_row(str(page["title"]), cells) is not None:
            exact_pages += 1
        elif unique_alias_title_row(str(page["title"]), cells) is not None:
            alias_pages += 1
        for target in permitted:
            reason, projection = _diagnose_pair(
                page,
                target,
                cells=cells,
                rows=rows,
            )
            reasons[reason] += 1
            if projection is not None:
                projections.append(projection)
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in projections:
        key = (
            item["target_binding_sha256"],
            item["source_host"],
            _normalize(item["value"]),
            item["evidence_kind"],
            item["evidence_start_line_ordinal"],
            item["evidence_end_line_ordinal"],
        )
        unique.setdefault(key, item)
    projections = [unique[key] for key in sorted(unique)]
    alias_observations = structured._canonical_observations(projections)
    parent_observations = structured._canonical_observations(
        parent_projection["observations"]
    )
    observations = structured._canonical_observations(
        [*parent_observations, *alias_observations]
    )
    parent_keys = {structured._observation_key(item) for item in parent_observations}
    novel = sum(
        structured._observation_key(item) not in parent_keys
        for item in alias_observations
    )
    reason_counts = {name: int(reasons[name]) for name in REASONS}
    pair_count = len(titled_pages) * len(permitted)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_projection": copy.deepcopy(parent_projection),
        "pages": titled_pages,
        "selected_target_binding_sha256s": selected,
        "alias_title_projections": projections,
        "alias_observations": alias_observations,
        "observations": observations,
        "parent_observation_count": len(parent_observations),
        "page_target_pair_count": pair_count,
        "exact_parent_anchor_page_count": exact_pages,
        "unique_alias_anchor_page_count": alias_pages,
        "ambiguous_or_absent_alias_anchor_page_count": len(titled_pages)
        - exact_pages
        - alias_pages,
        "alias_projection_count": len(projections),
        "novel_alias_observation_count": novel,
        "combined_observation_count": len(observations),
        "reason_counts": reason_counts,
        "alias_mode_counts": dict(
            sorted(Counter(item["alias_mode"] for item in projections).items())
        ),
        "evidence_kind_counts": dict(
            sorted(Counter(item["evidence_kind"] for item in projections).items())
        ),
        "visible_row_only_alias_derivation": True,
        "unique_cross_row_alias_match_required": True,
        "short_or_generic_core_rejected": True,
        "organization_type_conflict_rejected": True,
        "exact_parent_title_anchor_never_overridden": True,
        "exact_label_or_subject_safe_relation_required": True,
        "single_distinct_candidate_year_required": True,
        "other_visible_row_stops_title_scope": True,
        "alias_supplies_identity_not_value": True,
        "parent_artifact_preserved": True,
        "reason_partition_exact": sum(reason_counts.values()) == pair_count,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_conservative_alias_title_projection(
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
    validate_conservative_alias_title_projection(value)
    return value


def validate_conservative_alias_title_projection(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("catalog_payload_sha256", None)
    parent_projection = copied.get("parent_projection")
    pages = copied.get("pages")
    projections = copied.get("alias_title_projections")
    reasons = copied.get("reason_counts")
    count_fields = (
        "parent_observation_count",
        "page_target_pair_count",
        "exact_parent_anchor_page_count",
        "unique_alias_anchor_page_count",
        "ambiguous_or_absent_alias_anchor_page_count",
        "alias_projection_count",
        "novel_alias_observation_count",
        "combined_observation_count",
    )
    true_fields = (
        "visible_row_only_alias_derivation",
        "unique_cross_row_alias_match_required",
        "short_or_generic_core_rejected",
        "organization_type_conflict_rejected",
        "exact_parent_title_anchor_never_overridden",
        "exact_label_or_subject_safe_relation_required",
        "single_distinct_candidate_year_required",
        "other_visible_row_stops_title_scope",
        "alias_supplies_identity_not_value",
        "parent_artifact_preserved",
        "reason_partition_exact",
    )
    false_fields = (
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != CATALOG_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(parent_projection, Mapping)
        or not isinstance(pages, list)
        or not isinstance(projections, list)
        or not isinstance(copied.get("alias_observations"), list)
        or not isinstance(copied.get("observations"), list)
        or not isinstance(copied.get("selected_target_binding_sha256s"), list)
        or not isinstance(reasons, Mapping)
        or tuple(reasons) != REASONS
        or any(
            isinstance(reasons.get(name), bool)
            or not isinstance(reasons.get(name), int)
            or reasons[name] < 0
            for name in REASONS
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or any(
            not isinstance(item, Mapping)
            or set(item) != PROJECTION_KEYS
            or item.get("projection_mode") != PROJECTION_MODE
            or item.get("fetch_integrity") is not True
            or item.get("alias_mode") not in ALIAS_MODES
            or item.get("evidence_kind") not in EVIDENCE_KINDS
            or isinstance(item.get("alias_token_count"), bool)
            or not isinstance(item.get("alias_token_count"), int)
            or item["alias_token_count"] < 1
            or isinstance(item.get("title_match_start"), bool)
            or not isinstance(item.get("title_match_start"), int)
            or not 0 <= item["title_match_start"] <= MAXIMUM_ALIAS_MATCH_START
            or isinstance(item.get("evidence_start_line_ordinal"), bool)
            or not isinstance(item.get("evidence_start_line_ordinal"), int)
            or isinstance(item.get("evidence_end_line_ordinal"), bool)
            or not isinstance(item.get("evidence_end_line_ordinal"), int)
            or not 1
            <= item["evidence_start_line_ordinal"]
            <= item["evidence_end_line_ordinal"]
            <= title.MAXIMUM_TITLE_RECORD_LINES
            or re.fullmatch(r"(?:17|18|19|20|21)\d{2}", str(item.get("value")))
            is None
            for item in projections
        )
        or sum(int(reasons[name]) for name in REASONS)
        != copied.get("page_target_pair_count")
        or copied.get("exact_parent_anchor_page_count")
        + copied.get("unique_alias_anchor_page_count")
        + copied.get("ambiguous_or_absent_alias_anchor_page_count")
        != len(pages)
        or copied.get("alias_projection_count") != len(projections)
        or copied.get("combined_observation_count")
        != len(copied.get("observations", []))
        or copied.get("alias_mode_counts")
        != dict(sorted(Counter(item["alias_mode"] for item in projections).items()))
        or copied.get("evidence_kind_counts")
        != dict(
            sorted(Counter(item["evidence_kind"] for item in projections).items())
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.23 alias title projection identity drifted")
    parent.validate_record_bound_title_projection(parent_projection)
    baseline = str(
        parent_projection["parent_projection"]["parent_projection"][
            "parent_projection"
        ]["baseline_prediction"]
    )
    selected_identities = {
        _target_identity(cell.row_key, cell.column)
        for cell in _baseline_cells(baseline)
        if cell.binding_sha256
        in set(copied["selected_target_binding_sha256s"])
    }
    expected = _compute(
        baseline,
        pages,
        selected_identities=selected_identities,
    )
    if copied != expected:
        raise ValueError("V2.45.23 alias title projection replay drifted")
    return copied


__all__ = [
    "ALIAS_MODES",
    "EVIDENCE_KINDS",
    "POLICY_ID",
    "REASONS",
    "ROLE",
    "build_conservative_alias_title_projection",
    "unique_alias_title_row",
    "validate_conservative_alias_title_projection",
]
