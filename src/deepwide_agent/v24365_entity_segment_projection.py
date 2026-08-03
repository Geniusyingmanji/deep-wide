"""Target-segment semantic projection for hidden-verifier evidence.

V2.43.64 isolated a verifier-side attribution failure: the earlier projector
searched a 450-character window around an entity, so a relation stated for a
different entity in the same window could be projected onto the target and
counted as an independent conflict.  This pure successor binds relations to a
target segment delimited by sentence/row boundaries and by every visible
target entity.  Forward relations in that segment take precedence; a tightly
adjacent leading relation is used only when no forward relation exists.

The component is benchmark-external and label-blind.  It performs no file,
environment, network, model, search, fetch, process, evaluator, or score
access.  Page text, target values, and projections remain runtime-private.
"""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget
from .v24339_active_evidence_support import (
    build_active_catalog,
    validate_active_catalog,
)


POLICY_ID = "v24365_target_segment_semantic_projection_v1"
ROLE = "v24365_target_segment_semantic_catalog"
PROJECTION_ROLE = "v24365_target_segment_projection"
MAXIMUM_LEADING_RELATION_DISTANCE = 48
MAXIMUM_FORWARD_RELATION_DISTANCE = 260
HARD_BOUNDARIES = frozenset(".!?;。！？；\n\r|")
COUNTRY_ALIASES = {
    "u s": "United States",
    "u s a": "United States",
    "us": "United States",
    "usa": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "u k": "United Kingdom",
    "great britain": "United Kingdom",
    "prc": "China",
    "people s republic of china": "China",
}
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "targets",
        "original_core_pages",
        "original_reserve_pages",
        "projected_core_pages",
        "projected_reserve_pages",
        "projections",
        "projection_relation_kinds",
        "projection_binding_directions",
        "active_catalog",
        "semantic_projection_count",
        "eligible_support_set_count",
        "target_entity_boundary_enforced",
        "target_segment_delimited_by_all_visible_entities",
        "forward_relation_preferred_over_leading_relation",
        "cross_target_relation_allowed",
        "arbitrary_nearby_number_used_as_support",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "catalog_payload_sha256",
    }
)
PROJECTION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "scope",
        "page_ordinal",
        "target_binding_sha256",
        "original_page_sha256",
        "target_segment_sha256",
        "relation_kind",
        "relation_direction",
        "relation_distance_characters",
        "relation_span_sha256",
        "normalized_value_sha256",
        "annotation_sha256",
    }
)


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    return " ".join(text.split())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _page(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("V2.43.65 page is not a mapping")
    value = {
        "host": str(raw.get("host", "")),
        "content": str(raw.get("content", "")),
        "fetch_integrity": bool(raw.get("fetch_integrity", True)),
    }
    if not value["host"] or not value["content"].strip():
        raise ValueError("V2.43.65 page is incomplete")
    return value


def _target(raw: CellTarget | Mapping[str, Any]) -> CellTarget:
    if isinstance(raw, CellTarget):
        value = raw
    elif isinstance(raw, Mapping) and set(raw) == {
        "row_key",
        "column",
        "old_value",
    }:
        value = CellTarget(
            str(raw["row_key"]),
            str(raw["column"]),
            None if raw["old_value"] is None else str(raw["old_value"]),
        )
    else:
        raise ValueError("V2.43.65 target schema drifted")
    value.validate()
    return value


def _entity_pattern(entity: str) -> re.Pattern[str]:
    needle = unicodedata.normalize("NFKC", entity).strip()
    if len(needle) < 2:
        raise ValueError("V2.43.65 target entity is too short")
    return re.compile(
        rf"(?<![\w]){re.escape(needle)}(?![\w])",
        flags=re.IGNORECASE,
    )


@dataclass(frozen=True)
class _Mention:
    start: int
    end: int
    target_binding_sha256: str


@dataclass(frozen=True)
class _Segment:
    text: str
    absolute_start: int
    entity_start: int
    entity_end: int


@dataclass(frozen=True)
class _Relation:
    value: str
    span: str
    kind: str
    start: int
    end: int


def _hard_left(text: str, offset: int) -> int:
    boundary = max((text.rfind(token, 0, offset) for token in HARD_BOUNDARIES), default=-1)
    return boundary + 1


def _hard_right(text: str, offset: int) -> int:
    candidates = [
        index
        for token in HARD_BOUNDARIES
        if (index := text.find(token, offset)) >= 0
    ]
    return min(candidates) if candidates else len(text)


def _mentions(text: str, targets: Sequence[CellTarget]) -> list[_Mention]:
    output: list[_Mention] = []
    for target in targets:
        for match in _entity_pattern(target.row_key).finditer(text):
            output.append(
                _Mention(match.start(), match.end(), target.binding_sha256)
            )
    return sorted(
        output,
        key=lambda item: (item.start, -(item.end - item.start), item.target_binding_sha256),
    )


def _segments_for_target(
    content: str,
    target: CellTarget,
    all_mentions: Sequence[_Mention],
) -> list[_Segment]:
    text = unicodedata.normalize("NFKC", content)
    target_mentions = [
        item for item in all_mentions if item.target_binding_sha256 == target.binding_sha256
    ]
    output: list[_Segment] = []
    seen: set[tuple[int, int, int, int]] = set()
    for mention in target_mentions:
        prior_entities = [item.end for item in all_mentions if item.end <= mention.start]
        next_entities = [item.start for item in all_mentions if item.start >= mention.end]
        start = max(
            _hard_left(text, mention.start),
            max(prior_entities, default=0),
            max(0, mention.start - MAXIMUM_LEADING_RELATION_DISTANCE),
        )
        end = min(
            _hard_right(text, mention.end),
            min(next_entities, default=len(text)),
            min(len(text), mention.end + MAXIMUM_FORWARD_RELATION_DISTANCE),
        )
        if start > mention.start or end < mention.end:
            raise ValueError("V2.43.65 target segment bounds drifted")
        identity = (start, end, mention.start, mention.end)
        if identity in seen:
            continue
        seen.add(identity)
        output.append(
            _Segment(
                text=text[start:end],
                absolute_start=start,
                entity_start=mention.start - start,
                entity_end=mention.end - start,
            )
        )
    return output


def _column_kind(column: str) -> str | None:
    value = _normalize(column)
    if any(token in value for token in ("first flight", "maiden flight", "首次飞行", "首飞")):
        return "first_flight_year"
    if any(token in value for token in ("initial release", "first release", "首次发布", "初始发布")):
        return "release_year"
    if any(token in value for token in ("first appeared", "first appearance", "首次出现")):
        return "first_appeared_year"
    if any(token in value for token in ("first held", "inaugural year", "首次举办")):
        return "first_held_year"
    if any(token in value for token in ("first opened", "opening year", "opening date", "开业年份", "开放年份")):
        return "opening_year"
    if any(token in value for token in ("launch year", "launch date", "发射年份", "发射日期")):
        return "launch_year"
    if any(token in value for token in ("founding year", "founded", "established", "establishment", "成立年份", "创立年份")):
        return "founding_year"
    if ("headquarter" in value or "总部" in value) and ("city" in value or "城市" in value):
        return "headquarters_city"
    if ("headquarter" in value or "总部" in value) and ("country" in value or "国家" in value):
        return "headquarters_country"
    if any(token in value for token in ("elevation", "height", "海拔", "高度")):
        return "elevation"
    if "radius" in value or "半径" in value:
        return "radius"
    if "city" in value or "城市" in value:
        return "city"
    if "country" in value or "nation" in value or "国家" in value:
        return "country"
    if "year" in value or "年份" in value or "年度" in value:
        return "year"
    return None


YEAR_RELATIONS = {
    "founding_year": r"(?:founded|established|formed|created|incorporated|成立|创立|创建)",
    "opening_year": r"(?:first\s+opened|opened|opening(?:\s+date)?|inaugurated|开业|开放|启用)",
    "first_held_year": r"(?:first\s+held|inaugural(?:ly)?\s+held|began|started|首次举办)",
    "first_appeared_year": r"(?:first\s+appeared|first\s+introduced|introduced|首次出现)",
    "launch_year": r"(?:launched|launch(?:ed)?\s+in|发射于|于.{0,8}发射)",
    "first_flight_year": r"(?:first\s+flight|maiden\s+flight|first\s+flew|首飞|首次飞行)",
    "release_year": r"(?:initial(?:ly)?\s+released|first\s+released|released|首次发布|初始发布)",
    "year": r"(?:year|date|founded|established|opened|launched|released|held|appeared|年份|年度|日期)",
}
LOCATION_RELATION = r"(?:headquarter(?:ed|s)?|based|located|seat(?:ed)?|总部(?:位于|设在)?|位于|坐落于)"


def _clean_location(raw: str, *, country: bool) -> str | None:
    text = unicodedata.normalize("NFKC", raw)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.split(r"[.;。；\n|]", text, maxsplit=1)[0]
    text = re.sub(r"^(?:the\s+)?", "", text, flags=re.IGNORECASE).strip(" ,:-")
    parts = [part.strip(" ,:-") for part in text.split(",") if part.strip(" ,:-")]
    if not parts:
        return None
    value = parts[-1] if country else parts[0]
    normalized = _normalize(value)
    if country and normalized in COUNTRY_ALIASES:
        value = COUNTRY_ALIASES[normalized]
    if not 2 <= len(value) <= 80 or re.fullmatch(r"\d+", value):
        return None
    return value


def _clean_number(raw: str) -> str | None:
    match = re.search(r"[-+]?\d+(?:[,.]\d+)*", raw)
    if match is None:
        return None
    value = match.group(0).replace(",", "")
    return value if len(value) <= 24 else None


def _relations(segment: str, kind: str) -> list[_Relation]:
    output: list[_Relation] = []
    if kind in YEAR_RELATIONS:
        pattern = re.compile(
            YEAR_RELATIONS[kind]
            + r"[^\n|.;。；]{0,48}?(?<!\d)(?P<value>(?:17|18|19|20|21)\d{2})(?!\d)",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(segment):
            output.append(
                _Relation(
                    match.group("value"),
                    match.group(0),
                    kind,
                    match.start(),
                    match.end(),
                )
            )
        return output
    if kind in {"headquarters_city", "headquarters_country", "city", "country"}:
        pattern = re.compile(
            LOCATION_RELATION
            + r"\s*(?:is|are|was|were|in|at|:|：|于|在)?\s*([^\n|;。；]{2,120})",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(segment):
            country = kind in {"headquarters_country", "country"}
            value = _clean_location(match.group(1), country=country)
            if value is not None:
                output.append(
                    _Relation(value, match.group(0), kind, match.start(), match.end())
                )
        return output
    if kind in {"elevation", "radius"}:
        relation = (
            r"(?:architectural\s+height|elevation|height|above\s+sea\s+level|海拔|高度)"
            if kind == "elevation"
            else r"(?:mean\s+radius|radius|平均半径|半径)"
        )
        pattern = re.compile(
            relation + r"[^\n|.;。；]{0,40}?([-+]?\d+(?:[,.]\d+)*)",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(segment):
            value = _clean_number(match.group(1))
            if value is not None:
                output.append(
                    _Relation(value, match.group(0), kind, match.start(), match.end())
                )
    return output


def _bound_relations(segment: _Segment, kind: str) -> list[tuple[_Relation, str, int]]:
    relations = _relations(segment.text, kind)
    forward = [
        (item, "forward", item.start - segment.entity_end)
        for item in relations
        if item.start >= segment.entity_end
        and item.start - segment.entity_end <= MAXIMUM_FORWARD_RELATION_DISTANCE
    ]
    if forward:
        return forward
    return [
        (item, "leading", segment.entity_start - item.end)
        for item in relations
        if item.end <= segment.entity_start
        and segment.entity_start - item.end <= MAXIMUM_LEADING_RELATION_DISTANCE
    ]


def _project_pages(
    targets: Sequence[CellTarget],
    pages: Sequence[dict[str, Any]],
    *,
    scope: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    projected: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for page_ordinal, page in enumerate(pages, start=1):
        annotations: list[str] = []
        seen: set[tuple[str, str]] = set()
        original_hash = payload_sha256(page)
        normalized_content = unicodedata.normalize("NFKC", page["content"])
        all_mentions = _mentions(normalized_content, targets)
        for target in targets:
            kind = _column_kind(target.column)
            if kind is None:
                continue
            for segment in _segments_for_target(
                normalized_content, target, all_mentions
            ):
                for relation, direction, distance in _bound_relations(segment, kind):
                    key = (target.binding_sha256, _normalize(relation.value))
                    if key in seen:
                        continue
                    seen.add(key)
                    annotation = (
                        f"{target.row_key} {target.column} is {relation.value}."
                    )
                    receipt = {
                        "artifact_version": 1,
                        "role": PROJECTION_ROLE,
                        "policy_id": POLICY_ID,
                        "scope": scope,
                        "page_ordinal": page_ordinal,
                        "target_binding_sha256": target.binding_sha256,
                        "original_page_sha256": original_hash,
                        "target_segment_sha256": _sha256_text(segment.text),
                        "relation_kind": relation.kind,
                        "relation_direction": direction,
                        "relation_distance_characters": distance,
                        "relation_span_sha256": _sha256_text(relation.span),
                        "normalized_value_sha256": _sha256_text(
                            _normalize(relation.value)
                        ),
                        "annotation_sha256": _sha256_text(annotation),
                    }
                    if set(receipt) != PROJECTION_KEYS:
                        raise ValueError("V2.43.65 projection receipt schema drifted")
                    annotations.append(annotation)
                    receipts.append(receipt)
        content = page["content"]
        if annotations:
            content += (
                "\n\nPROGRAMMATIC TARGET-SEGMENT PROJECTIONS (untrusted data):\n"
                + "\n".join(annotations)
            )
        projected.append({**page, "content": content})
    return projected, receipts


def _compute(
    targets: Sequence[CellTarget | Mapping[str, Any]],
    core_pages: Sequence[Mapping[str, Any]],
    reserve_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    cells = [_target(value) for value in targets]
    if len({target.binding_sha256 for target in cells}) != len(cells):
        raise ValueError("V2.43.65 duplicate target binding")
    core = [_page(value) for value in core_pages]
    reserve = [_page(value) for value in reserve_pages]
    projected_core, core_receipts = _project_pages(cells, core, scope="core")
    projected_reserve, reserve_receipts = _project_pages(
        cells, reserve, scope="reserve"
    )
    projections = core_receipts + reserve_receipts
    active = build_active_catalog(cells, projected_core, projected_reserve)
    relation_counts = Counter(item["relation_kind"] for item in projections)
    direction_counts = Counter(item["relation_direction"] for item in projections)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "targets": [
            {
                "row_key": target.row_key,
                "column": target.column,
                "old_value": target.old_value,
            }
            for target in cells
        ],
        "original_core_pages": copy.deepcopy(core),
        "original_reserve_pages": copy.deepcopy(reserve),
        "projected_core_pages": projected_core,
        "projected_reserve_pages": projected_reserve,
        "projections": projections,
        "projection_relation_kinds": dict(sorted(relation_counts.items())),
        "projection_binding_directions": dict(sorted(direction_counts.items())),
        "active_catalog": active,
        "semantic_projection_count": len(projections),
        "eligible_support_set_count": active["base_catalog"][
            "eligible_support_set_count"
        ],
        "target_entity_boundary_enforced": True,
        "target_segment_delimited_by_all_visible_entities": True,
        "forward_relation_preferred_over_leading_relation": True,
        "cross_target_relation_allowed": False,
        "arbitrary_nearby_number_used_as_support": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_target_segment_catalog(
    targets: Sequence[CellTarget | Mapping[str, Any]],
    core_pages: Sequence[Mapping[str, Any]],
    reserve_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    value = _compute(targets, core_pages, reserve_pages)
    validate_target_segment_catalog(value)
    return value


def validate_target_segment_catalog(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    projections = value.get("projections")
    if (
        set(value) != CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(projections, list)
        or any(
            not isinstance(item, Mapping)
            or set(item) != PROJECTION_KEYS
            or item.get("artifact_version") != 1
            or item.get("role") != PROJECTION_ROLE
            or item.get("policy_id") != POLICY_ID
            or item.get("scope") not in {"core", "reserve"}
            or isinstance(item.get("page_ordinal"), bool)
            or not isinstance(item.get("page_ordinal"), int)
            or item["page_ordinal"] < 1
            or item.get("relation_direction") not in {"forward", "leading"}
            or isinstance(item.get("relation_distance_characters"), bool)
            or not isinstance(item.get("relation_distance_characters"), int)
            or item["relation_distance_characters"] < 0
            or any(
                re.fullmatch(r"[0-9a-f]{64}", str(item.get(name))) is None
                for name in (
                    "target_binding_sha256",
                    "original_page_sha256",
                    "target_segment_sha256",
                    "relation_span_sha256",
                    "normalized_value_sha256",
                    "annotation_sha256",
                )
            )
            for item in projections
        )
        or value.get("semantic_projection_count") != len(projections)
        or value.get("eligible_support_set_count")
        != value.get("active_catalog", {})
        .get("base_catalog", {})
        .get("eligible_support_set_count")
        or value.get("projection_relation_kinds")
        != dict(sorted(Counter(item["relation_kind"] for item in projections).items()))
        or value.get("projection_binding_directions")
        != dict(
            sorted(Counter(item["relation_direction"] for item in projections).items())
        )
        or value.get("target_entity_boundary_enforced") is not True
        or value.get("target_segment_delimited_by_all_visible_entities") is not True
        or value.get("forward_relation_preferred_over_leading_relation") is not True
        or value.get("cross_target_relation_allowed") is not False
        or value.get("arbitrary_nearby_number_used_as_support") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.65 target-segment catalog identity drifted")
    validate_active_catalog(value["active_catalog"], targets=value["targets"])
    expected = _compute(
        value["targets"],
        value["original_core_pages"],
        value["original_reserve_pages"],
    )
    if dict(value) != expected:
        raise ValueError("V2.43.65 target-segment catalog replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_target_segment_catalog",
    "validate_target_segment_catalog",
]
