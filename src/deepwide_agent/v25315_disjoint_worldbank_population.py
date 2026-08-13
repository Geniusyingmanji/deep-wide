"""Pure selector for a genuinely disjoint World Bank successor population.

V2.53.05 consumed all 24 probed target indicators (not only its selected
quartet) and its 144 selected entity codes.  This append-only selector binds
those frozen facts and accepts only caller-supplied catalog/target bytes.  It
performs no filesystem, network, model, benchmark, or evaluator effect.

The public World Bank surface has at most roughly 265 entity codes, so another
144-code population cannot be disjoint.  The successor therefore keeps twelve
tasks while preregistering a deterministic capacity ladder: prefer 9 rows per
task (108 unique new entities), otherwise accept exactly 8 rows per task (96),
and fail closed below 96.  The ladder is based only on same-response non-null
coverage; it does not use predictions, labels, answers, or evaluator output.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25295_worldbank_monotone_fill_gate as parent
from .clients import canonicalize_url


POLICY_ID = "v25315_disjoint_worldbank_population_v1"
SELECTION_SEED = "v25315-fresh-disjoint-worldbank-successor-v1"
TASK_COUNT = 12
PREFERRED_ROWS_PER_TASK = 9
MINIMUM_ROWS_PER_TASK = 8
PREFERRED_ENTITY_COUNT = TASK_COUNT * PREFERRED_ROWS_PER_TASK
MINIMUM_ENTITY_COUNT = TASK_COUNT * MINIMUM_ROWS_PER_TASK
TARGET_COUNT = parent.TARGET_COUNT
MINIMUM_TARGET_OVERSAMPLE = parent.MINIMUM_TARGET_OVERSAMPLE
PAGE_COUNT = parent.PAGE_COUNT
TARGET_YEAR = parent.TARGET_YEAR
MAXIMUM_PAGE_CHARS = parent.MAXIMUM_PAGE_CHARS
MAXIMUM_EVIDENCE_CHARS = parent.MAXIMUM_EVIDENCE_CHARS


def _normalized(value: object) -> str:
    return " ".join(str(value).casefold().split())


def _rank(namespace: str, value: object) -> str:
    normalized = _normalized(value)
    if namespace not in {"target", "entity"} or not normalized or len(normalized) > 160:
        raise ValueError("V2.53.15 deterministic rank input drifted")
    return hashlib.sha256(
        f"{SELECTION_SEED}\0{namespace}\0{normalized}".encode()
    ).hexdigest()


def _consumed_targets(value: Sequence[str]) -> frozenset[str]:
    if isinstance(value, (str, bytes)) or len(value) != MINIMUM_TARGET_OVERSAMPLE:
        raise ValueError("V2.53.15 requires the exact 24 consumed target keys")
    normalized = frozenset(_normalized(item) for item in value)
    if len(normalized) != MINIMUM_TARGET_OVERSAMPLE or any(
        not item.endswith(f"@{TARGET_YEAR}") for item in normalized
    ):
        raise ValueError("V2.53.15 consumed target vector drifted")
    return normalized


def _consumed_entities(value: Sequence[str]) -> frozenset[str]:
    if isinstance(value, (str, bytes)) or len(value) != parent.ENTITY_ROW_COUNT:
        raise ValueError("V2.53.15 requires the exact 144 consumed entity codes")
    normalized = frozenset(str(item).strip().upper() for item in value)
    if len(normalized) != parent.ENTITY_ROW_COUNT or any(
        len(item) != 3 or not item.isalnum() for item in normalized
    ):
        raise ValueError("V2.53.15 consumed entity vector drifted")
    return normalized


def _consumed_response_hashes(value: Sequence[str]) -> frozenset[str]:
    if isinstance(value, (str, bytes)) or len(value) != MINIMUM_TARGET_OVERSAMPLE * 2:
        raise ValueError("V2.53.15 requires the exact 48 consumed response hashes")
    normalized = frozenset(str(item).strip().casefold() for item in value)
    if len(normalized) != MINIMUM_TARGET_OVERSAMPLE * 2 or any(
        re.fullmatch(r"[0-9a-f]{64}", item) is None for item in normalized
    ):
        raise ValueError("V2.53.15 consumed response hash vector drifted")
    return normalized


def target_urls(indicator: str) -> tuple[str, str]:
    if parent.INDICATOR.fullmatch(indicator) is None:
        raise ValueError("V2.53.15 indicator drifted")
    prefix = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    return tuple(
        f"{prefix}?date={TARGET_YEAR}&format=json&page={page}"
        f"&per_page={parent.WORLD_BANK_PER_PAGE}"
        for page in (1, 2)
    )  # type: ignore[return-value]


def parse_catalog(
    blob: bytes,
    *,
    historical_target_keys: Sequence[str],
    consumed_target_keys: Sequence[str],
) -> tuple[list[parent.TargetSpec], dict[str, int]]:
    """Select exactly 24 pre-ranked, never-before-probed target indicators."""

    if not isinstance(blob, bytes) or not blob or len(blob) > 32 * 1024 * 1024:
        raise ValueError("V2.53.15 catalog bytes drifted")
    try:
        value = json.loads(blob)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("V2.53.15 catalog JSON invalid") from exc
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("V2.53.15 catalog envelope drifted")
    metadata, records = value
    if not isinstance(metadata, Mapping) or not isinstance(records, list):
        raise ValueError("V2.53.15 catalog schema drifted")
    try:
        page = int(metadata["page"])
        pages = int(metadata["pages"])
        per_page = int(metadata["per_page"])
        total = int(metadata["total"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("V2.53.15 catalog metadata drifted") from exc
    if (
        page != 1
        or pages != 1
        or per_page != 50_000
        or total != len(records)
        or not MINIMUM_TARGET_OVERSAMPLE <= total <= per_page
    ):
        raise ValueError("V2.53.15 catalog does not self-prove complete coverage")
    historical = {_normalized(item) for item in historical_target_keys}
    consumed = _consumed_targets(consumed_target_keys)
    excluded = historical | consumed
    observed: set[str] = set()
    compatible: list[parent.TargetSpec] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("V2.53.15 catalog record drifted")
        indicator = str(record.get("id") or "").strip().upper()
        source = record.get("source") or {}
        source_id = str(
            source.get("id") if isinstance(source, Mapping) else ""
        ).strip()
        if not indicator or indicator in observed or source_id != "2":
            raise ValueError("V2.53.15 catalog identity/source drifted")
        observed.add(indicator)
        label = " ".join(str(record.get("name") or "").split())
        key = f"{indicator}@{TARGET_YEAR}".casefold()
        if (
            parent.INDICATOR.fullmatch(indicator) is None
            or key in excluded
            or not label
            or len(label) > 80
            or any(character in label for character in "|`\r\n")
        ):
            continue
        spec = parent.TargetSpec(
            label=label,
            indicator=indicator,
            year=TARGET_YEAR,
            urls=target_urls(indicator),
        )
        spec.validate()
        compatible.append(spec)
    ranked = sorted(
        compatible, key=lambda item: (_rank("target", item.key), item.key)
    )
    selected = ranked[:MINIMUM_TARGET_OVERSAMPLE]
    if len(selected) != MINIMUM_TARGET_OVERSAMPLE:
        raise RuntimeError("V2.53.15 fresh catalog capacity is insufficient")
    if any(_normalized(item.key) in consumed for item in selected):
        raise RuntimeError("V2.53.15 consumed target reached selected vector")
    return selected, {
        "catalog_total": total,
        "historical_target_count": len(historical),
        "consumed_target_count": len(consumed),
        "runtime_compatible_fresh_count": len(compatible),
        "selected_candidate_count": len(selected),
    }


def _render_page(
    parsed: parent.ParsedWorldBankPage,
    *,
    target: parent.TargetSpec,
    selected_entities: set[str],
    url: str,
) -> dict[str, Any]:
    rows = [
        (code, parsed.values[code])
        for code in sorted(parsed.values)
        if code in selected_entities
    ]
    lines = [
        f"| Entity code | {target.column} |",
        "| --- | --- |",
        *(f"| {code} | {value} |" for code, value in rows),
    ]
    content = "\n".join(lines)
    if not rows or len(content) > MAXIMUM_PAGE_CHARS:
        raise ValueError("V2.53.15 rendered page capacity drifted")
    return {
        "url": canonicalize_url(url),
        "title": "Official World Bank indicator page",
        "content": content,
        "fetch_integrity": True,
    }


def _target_values(
    pages: Sequence[parent.ParsedWorldBankPage],
) -> dict[str, str]:
    output: dict[str, str] = {}
    for page in pages:
        if set(output).intersection(page.values):
            raise ValueError("V2.53.15 target entity duplication drifted")
        output.update(page.values)
    return output


def select_and_render_population(
    candidates: Mapping[parent.TargetSpec, Sequence[bytes]],
    *,
    consumed_target_keys: Sequence[str],
    consumed_entity_codes: Sequence[str],
    consumed_response_sha256: Sequence[str],
) -> dict[str, Any]:
    """Choose a disjoint quartet and 96 or 108 unique successor entities."""

    if len(candidates) != MINIMUM_TARGET_OVERSAMPLE:
        raise ValueError("V2.53.15 requires exactly 24 consumed new candidates")
    consumed_targets = _consumed_targets(consumed_target_keys)
    consumed_entities = _consumed_entities(consumed_entity_codes)
    consumed_responses = _consumed_response_hashes(consumed_response_sha256)
    parsed: dict[
        str,
        tuple[
            parent.TargetSpec,
            tuple[parent.ParsedWorldBankPage, parent.ParsedWorldBankPage],
        ],
    ] = {}
    response_hashes: set[str] = set()
    for target, blobs in candidates.items():
        target.validate()
        normalized = _normalized(target.key)
        if normalized in consumed_targets:
            raise ValueError("V2.53.15 consumed target reused")
        if normalized in parsed:
            raise ValueError("V2.53.15 duplicate target key")
        if isinstance(blobs, (str, bytes)) or len(blobs) != 2:
            raise ValueError("V2.53.15 target response vector drifted")
        for blob in blobs:
            digest = hashlib.sha256(blob).hexdigest()
            if digest in consumed_responses:
                raise ValueError("V2.53.15 consumed target response bytes reused")
            if digest in response_hashes:
                raise ValueError("V2.53.15 target response bytes reused")
            response_hashes.add(digest)
        parsed[normalized] = (
            target,
            parent.parse_target_pages(blobs, target=target),
        )
    ranked = sorted(parsed, key=lambda key: (_rank("target", key), key))
    chosen: tuple[str, ...] | None = None
    entities: list[str] | None = None
    rows_per_task: int | None = None
    pages: list[dict[str, Any]] | None = None
    for required, row_count in (
        (PREFERRED_ENTITY_COUNT, PREFERRED_ROWS_PER_TASK),
        (MINIMUM_ENTITY_COUNT, MINIMUM_ROWS_PER_TASK),
    ):
        for combination in itertools.combinations(ranked, TARGET_COUNT):
            common = set.intersection(
                *(set(_target_values(parsed[key][1])) for key in combination)
            ) - set(consumed_entities)
            if len(common) < required:
                continue
            selected_entities = sorted(
                common, key=lambda code: (_rank("entity", code), code)
            )[:required]
            rendered: list[dict[str, Any]] = []
            try:
                for key in combination:
                    target, target_pages = parsed[key]
                    for index, target_page in enumerate(target_pages):
                        rendered.append(
                            _render_page(
                                target_page,
                                target=target,
                                selected_entities=set(selected_entities),
                                url=target.urls[index],
                            )
                        )
            except ValueError:
                continue
            if (
                len(rendered) == PAGE_COUNT
                and sum(len(page["content"]) for page in rendered)
                <= MAXIMUM_EVIDENCE_CHARS
            ):
                chosen = combination
                entities = selected_entities
                rows_per_task = row_count
                pages = rendered
                break
        if chosen is not None:
            break
    if chosen is None or entities is None or rows_per_task is None or pages is None:
        raise RuntimeError("V2.53.15 no viable disjoint four-target combination")
    if set(entities).intersection(consumed_entities):
        raise RuntimeError("V2.53.15 consumed entity reached selected vector")
    columns = ["Entity code", *(parsed[key][0].column for key in chosen)]
    tasks: list[dict[str, str]] = []
    for index in range(TASK_COUNT):
        codes = entities[index * rows_per_task : (index + 1) * rows_per_task]
        question = (
            "Return exactly one Markdown table and no prose. Column names: "
            + " | ".join(columns)
            + ". Include exactly these entity-code rows in this order: "
            + ", ".join(codes)
            + ". Use Unknown only when the supplied official pages do not show a value."
        )
        opaque = "task_" + hashlib.sha256(
            f"{POLICY_ID}:{','.join(chosen)}:{','.join(codes)}".encode()
        ).hexdigest()[:24]
        tasks.append({"opaque_id": opaque, "question": question})
    if any(len(task["question"]) > 4_000 for task in tasks):
        raise RuntimeError("V2.53.15 visible task capacity drifted")
    return {
        "target_keys": list(chosen),
        "target_columns": columns[1:],
        "entities": entities,
        "rows_per_task": rows_per_task,
        "pages": pages,
        "tasks": tasks,
        "disjointness_receipt": {
            "consumed_target_count": len(consumed_targets),
            "consumed_entity_count": len(consumed_entities),
            "consumed_response_hash_count": len(consumed_responses),
            "selected_target_overlap_count": 0,
            "selected_entity_overlap_count": 0,
            "selected_response_overlap_count": 0,
            "candidate_response_hash_count": len(response_hashes),
            "candidate_response_hashes_unique": len(response_hashes)
            == MINIMUM_TARGET_OVERSAMPLE * 2,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
    }


TargetSpec = parent.TargetSpec
ParsedWorldBankPage = parent.ParsedWorldBankPage
parse_worldbank_page = parent.parse_worldbank_page
parse_target_pages = parent.parse_target_pages


__all__ = [
    "MAXIMUM_EVIDENCE_CHARS",
    "MAXIMUM_PAGE_CHARS",
    "MINIMUM_ENTITY_COUNT",
    "MINIMUM_ROWS_PER_TASK",
    "MINIMUM_TARGET_OVERSAMPLE",
    "PAGE_COUNT",
    "POLICY_ID",
    "PREFERRED_ENTITY_COUNT",
    "PREFERRED_ROWS_PER_TASK",
    "ParsedWorldBankPage",
    "SELECTION_SEED",
    "TARGET_COUNT",
    "TARGET_YEAR",
    "TASK_COUNT",
    "TargetSpec",
    "parse_catalog",
    "parse_target_pages",
    "parse_worldbank_page",
    "select_and_render_population",
    "target_urls",
]
