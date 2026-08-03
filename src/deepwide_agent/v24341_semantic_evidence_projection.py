"""Label-blind semantic projection from page relations to visible columns.

The projector recognizes task-independent column wording (year, headquarters,
city, country, launch, first flight, release, elevation, radius) and requires a
matching relation phrase inside an entity-local window.  It never treats an
arbitrary nearby number as support.  Extracted values remain bound to the
original page, relation span, target, and normalized value by replayable hashes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget
from .v24339_active_evidence_support import (
    build_active_catalog,
    validate_active_catalog,
)


POLICY_ID = "v24341_visible_column_semantic_projection_v1"
ROLE = "v24341_semantic_active_evidence_catalog"
PROJECTION_ROLE = "v24341_page_semantic_projection"
PROJECTED_CATALOG_KEYS = frozenset(
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
        "active_catalog",
        "semantic_projection_count",
        "eligible_support_set_count",
        "only_entity_local_relation_bound_values_projected",
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
        "relation_kind",
        "relation_span_sha256",
        "normalized_value_sha256",
        "annotation_sha256",
    }
)
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


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    return " ".join(text.split())


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _page(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("V2.43.41 page is not a mapping")
    value = {
        "host": str(raw.get("host", "")),
        "content": str(raw.get("content", "")),
        "fetch_integrity": bool(raw.get("fetch_integrity", True)),
    }
    if not value["host"] or not value["content"].strip():
        raise ValueError("V2.43.41 page is incomplete")
    return value


def _target(raw: CellTarget | Mapping[str, Any]) -> CellTarget:
    if isinstance(raw, CellTarget):
        value = raw
    elif isinstance(raw, Mapping) and set(raw) == {"row_key", "column", "old_value"}:
        value = CellTarget(
            str(raw["row_key"]),
            str(raw["column"]),
            None if raw["old_value"] is None else str(raw["old_value"]),
        )
    else:
        raise ValueError("V2.43.41 target schema drifted")
    value.validate()
    return value


def _entity_windows(content: str, entity: str, *, radius: int = 450) -> list[str]:
    text = unicodedata.normalize("NFKC", content)
    needle = unicodedata.normalize("NFKC", entity).strip()
    if len(needle) < 2:
        return []
    return [
        text[max(0, match.start() - radius) : min(len(text), match.end() + radius)]
        for match in re.finditer(re.escape(needle), text, flags=re.IGNORECASE)
    ]


def _column_kind(column: str) -> str | None:
    value = _normalize(column)
    if any(token in value for token in ("first flight", "maiden flight", "首次飞行", "首飞")):
        return "first_flight_year"
    if any(token in value for token in ("initial release", "first release", "首次发布", "初始发布")):
        return "release_year"
    if any(token in value for token in ("launch year", "launch date", "发射年份", "发射日期")):
        return "launch_year"
    if any(token in value for token in ("founding year", "founded", "established", "成立年份", "创立年份")):
        return "founding_year"
    if "year" in value or "年份" in value or "年度" in value:
        return "year"
    if ("headquarter" in value or "总部" in value) and ("city" in value or "城市" in value):
        return "headquarters_city"
    if ("headquarter" in value or "总部" in value) and ("country" in value or "国家" in value):
        return "headquarters_country"
    if "city" in value or "城市" in value:
        return "city"
    if "country" in value or "nation" in value or "国家" in value:
        return "country"
    if any(token in value for token in ("elevation", "height", "海拔", "高度")):
        return "elevation"
    if "radius" in value or "半径" in value:
        return "radius"
    return None


YEAR_RELATIONS = {
    "founding_year": r"(?:founded|established|formed|created|incorporated|成立|创立|创建)",
    "launch_year": r"(?:launched|launch(?:ed)?\s+in|发射于|于.{0,8}发射)",
    "first_flight_year": r"(?:first\s+flight|maiden\s+flight|first\s+flew|首飞|首次飞行)",
    "release_year": r"(?:initial(?:ly)?\s+released|first\s+released|released|首次发布|初始发布)",
    "year": r"(?:year|date|founded|established|launched|released|年份|年度|日期)",
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


def _extract(window: str, kind: str) -> list[tuple[str, str, str]]:
    output: list[tuple[str, str, str]] = []
    if kind in YEAR_RELATIONS:
        pattern = re.compile(
            YEAR_RELATIONS[kind]
            + r"[^\n|.;。；]{0,48}?(?<!\d)((?:18|19|20|21)\d{2})(?!\d)",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(window):
            output.append((match.group(1), match.group(0), kind))
        return output
    if kind in {"headquarters_city", "headquarters_country", "city", "country"}:
        pattern = re.compile(
            LOCATION_RELATION
            + r"\s*(?:is|are|was|were|in|at|:|：|于|在)?\s*([^\n|;。；]{2,120})",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(window):
            country = kind in {"headquarters_country", "country"}
            value = _clean_location(match.group(1), country=country)
            if value is not None:
                output.append((value, match.group(0), kind))
        return output
    if kind in {"elevation", "radius"}:
        relation = r"(?:elevation|height|above\s+sea\s+level|海拔|高度)" if kind == "elevation" else r"(?:mean\s+radius|radius|平均半径|半径)"
        pattern = re.compile(
            relation + r"[^\n|.;。；]{0,40}?([-+]?\d+(?:[,.]\d+)*)",
            flags=re.IGNORECASE,
        )
        for match in pattern.finditer(window):
            value = _clean_number(match.group(1))
            if value is not None:
                output.append((value, match.group(0), kind))
    return output


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
        for target in targets:
            kind = _column_kind(target.column)
            if kind is None:
                continue
            for window in _entity_windows(page["content"], target.row_key):
                for value, span, relation_kind in _extract(window, kind):
                    key = (target.binding_sha256, _normalize(value))
                    if key in seen:
                        continue
                    seen.add(key)
                    annotation = f"{target.row_key} {target.column} is {value}."
                    annotations.append(annotation)
                    receipt = {
                        "artifact_version": 1,
                        "role": PROJECTION_ROLE,
                        "policy_id": POLICY_ID,
                        "scope": scope,
                        "page_ordinal": page_ordinal,
                        "target_binding_sha256": target.binding_sha256,
                        "original_page_sha256": original_hash,
                        "relation_kind": relation_kind,
                        "relation_span_sha256": _sha256_text(span),
                        "normalized_value_sha256": _sha256_text(_normalize(value)),
                        "annotation_sha256": _sha256_text(annotation),
                    }
                    if set(receipt) != PROJECTION_KEYS:
                        raise ValueError("V2.43.41 projection receipt schema drifted")
                    receipts.append(receipt)
        content = page["content"]
        if annotations:
            content += "\n\nPROGRAMMATIC RELATION PROJECTIONS (untrusted data):\n" + "\n".join(annotations)
        projected.append({**page, "content": content})
    return projected, receipts


def _compute_semantic_active_catalog(
    targets: Sequence[CellTarget | Mapping[str, Any]],
    core_pages: Sequence[Mapping[str, Any]],
    reserve_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    cells = [_target(value) for value in targets]
    core = [_page(value) for value in core_pages]
    reserve = [_page(value) for value in reserve_pages]
    projected_core, core_receipts = _project_pages(cells, core, scope="core")
    projected_reserve, reserve_receipts = _project_pages(cells, reserve, scope="reserve")
    projections = core_receipts + reserve_receipts
    active = build_active_catalog(cells, projected_core, projected_reserve)
    target_values = [
        {"row_key": target.row_key, "column": target.column, "old_value": target.old_value}
        for target in cells
    ]
    relation_counts = Counter(item["relation_kind"] for item in projections)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "targets": target_values,
        "original_core_pages": copy.deepcopy(core),
        "original_reserve_pages": copy.deepcopy(reserve),
        "projected_core_pages": projected_core,
        "projected_reserve_pages": projected_reserve,
        "projections": projections,
        "projection_relation_kinds": dict(sorted(relation_counts.items())),
        "active_catalog": active,
        "semantic_projection_count": len(projections),
        "eligible_support_set_count": active["base_catalog"]["eligible_support_set_count"],
        "only_entity_local_relation_bound_values_projected": True,
        "arbitrary_nearby_number_used_as_support": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_semantic_active_catalog(
    targets: Sequence[CellTarget | Mapping[str, Any]],
    core_pages: Sequence[Mapping[str, Any]],
    reserve_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    value = _compute_semantic_active_catalog(targets, core_pages, reserve_pages)
    validate_semantic_active_catalog(value)
    return value


def validate_semantic_active_catalog(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    if (
        set(value) != PROJECTED_CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("only_entity_local_relation_bound_values_projected") is not True
        or value.get("arbitrary_nearby_number_used_as_support") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_or_process_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.41 semantic catalog identity drifted")
    expected = _compute_semantic_active_catalog(
        value["targets"],
        value["original_core_pages"],
        value["original_reserve_pages"],
    )
    if dict(value) != expected:
        raise ValueError("V2.43.41 semantic catalog replay drifted")
    return dict(value)


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_semantic_active_catalog",
    "validate_semantic_active_catalog",
]
