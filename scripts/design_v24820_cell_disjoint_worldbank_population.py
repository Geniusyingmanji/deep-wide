#!/usr/bin/env python3
"""Publish one 32-task target-cell-disjoint World Bank population.

Country-level novelty is nearly exhausted by prior World Bank experiments, so
this population does not pretend to be entity-disjoint.  It instead freezes two
previously unused indicator/year targets and proves that every selected gold
cell key ``(ISO3, indicator, year)`` is absent from tracked historical
populations.  Selection prioritizes countries never used before and then fills
the fixed 128-country denominator by a frozen hash rank.

The evaluator-only artifact contains public World Bank values.  The public
design artifact contains only counts and hashes.  Neither artifact authorizes a
forward launch or evaluator access.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    design_v24805_worldbank_budget_ladder_smoke_population as base,
)


DATE = "20260807"
CONTROLLER_AUDIT = Path(
    f"results/v24819_quality_first_controller_build_audit_v1_{DATE}.json"
)
AUTHORIZATION = Path(
    f"results/v24820_cell_disjoint_worldbank_population_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(
    f"evaluation/v24820_cell_disjoint_worldbank_population_private_v1_{DATE}.json"
)
OUTPUT = Path(
    f"results/v24820_cell_disjoint_worldbank_population_design_v1_{DATE}.json"
)
HISTORICAL_POPULATIONS = (
    Path("evaluation/v24690_worldbank_population_private_v1_20260806.json"),
    Path("evaluation/v24729_worldbank_population_private_v1_20260806.json"),
    Path(
        "evaluation/v24806_worldbank_budget_ladder_smoke_population_private_v1_20260807.json"
    ),
    Path(
        "evaluation/v24814_fresh_worldbank_population_private_v1_20260807.json"
    ),
)
TARGETS = (
    {
        "label": "Population ages 0-14 (%)",
        "indicator": "SP.POP.0014.TO.ZS",
        "year": "2023",
    },
    {
        "label": "Population ages 15-64 (%)",
        "indicator": "SP.POP.1564.TO.ZS",
        "year": "2023",
    },
)
TASK_SIZE = 4
TASK_COUNT = 32
SELECTED_COUNT = TASK_SIZE * TASK_COUNT


def payload_sha256(value: object) -> str:
    return base.payload_sha256(value)


def _ordinary(path: Path) -> Path:
    if (
        path.is_absolute()
        or ".." in path.parts
        or (ROOT / path).is_symlink()
        or not (ROOT / path).is_file()
        or not (ROOT / path).resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.20 expected repository object: {path}")
    return ROOT / path


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.20 expected JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def historical_boundary(
    root: Path = ROOT,
) -> tuple[set[str], set[tuple[str, str, str]], set[tuple[str, str]], dict[str, str]]:
    """Extract only identity/target keys from evaluator-only predecessors."""

    entities: set[str] = set()
    cells: set[tuple[str, str, str]] = set()
    targets: set[tuple[str, str]] = set()
    manifest: dict[str, str] = {}
    for relative in HISTORICAL_POPULATIONS:
        path = root / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
        ):
            raise RuntimeError(f"V2.48.20 historical artifact absent: {relative}")
        raw = path.read_bytes()
        value = json.loads(raw)
        if not isinstance(value, Mapping):
            raise RuntimeError("V2.48.20 historical artifact is not an object")
        artifact_targets = value.get("targets")
        groups = value.get("groups")
        if not isinstance(artifact_targets, list) or not isinstance(groups, list):
            raise RuntimeError("V2.48.20 historical boundary schema drifted")
        local_targets: set[tuple[str, str]] = set()
        for target in artifact_targets:
            if not isinstance(target, Mapping):
                raise RuntimeError("V2.48.20 historical target drifted")
            indicator = str(target.get("indicator", ""))
            year = str(target.get("year", ""))
            if not indicator or not year:
                raise RuntimeError("V2.48.20 historical target key drifted")
            local_targets.add((indicator, year))
        if len(local_targets) != 2:
            raise RuntimeError("V2.48.20 historical target cardinality drifted")
        for group in groups:
            if not isinstance(group, list):
                raise RuntimeError("V2.48.20 historical group drifted")
            for item in group:
                if not isinstance(item, Mapping):
                    raise RuntimeError("V2.48.20 historical entity drifted")
                iso3 = str(item.get("iso3", ""))
                if len(iso3) != 3 or not iso3.isupper():
                    raise RuntimeError("V2.48.20 historical ISO3 drifted")
                entities.add(iso3)
                cells.update((iso3, indicator, year) for indicator, year in local_targets)
        targets.update(local_targets)
        manifest[str(relative)] = hashlib.sha256(raw).hexdigest()
    if len(targets) != 6 or len(entities) < 190:
        raise RuntimeError("V2.48.20 historical coverage boundary drifted")
    return entities, cells, targets, dict(sorted(manifest.items()))


def _rank(iso3: str) -> str:
    return hashlib.sha256(f"v24820:cell-disjoint:{iso3}".encode()).hexdigest()


def select_population(
    countries: Mapping[str, Mapping[str, str]],
    snapshots: Sequence[Mapping[str, Mapping[str, Any]]],
    historical_entities: set[str],
    historical_cells: set[tuple[str, str, str]],
    historical_targets: set[tuple[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(snapshots) != len(TARGETS):
        raise ValueError("V2.48.20 snapshot vector drifted")
    target_pairs = {(target["indicator"], target["year"]) for target in TARGETS}
    if target_pairs & historical_targets:
        raise RuntimeError("V2.48.20 target/year pair is not historical-disjoint")
    candidates: list[dict[str, Any]] = []
    for iso3, country in countries.items():
        if any(iso3 not in snapshot for snapshot in snapshots):
            continue
        records = [dict(snapshot[iso3]) for snapshot in snapshots]
        if not all(record.get("value") is not None for record in records):
            continue
        candidate_cells = {
            (iso3, str(record["indicator"]), str(record["year"]))
            for record in records
        }
        if candidate_cells & historical_cells:
            raise RuntimeError("V2.48.20 candidate cell overlaps history")
        candidates.append({**dict(country), "records": records})
    ordered = sorted(
        candidates,
        key=lambda item: (
            str(item["iso3"]) in historical_entities,
            _rank(str(item["iso3"])),
            str(item["iso3"]),
        ),
    )
    selected = ordered[:SELECTED_COUNT]
    selected_entities = {str(item["iso3"]) for item in selected}
    selected_cells = {
        (
            str(item["iso3"]),
            str(record["indicator"]),
            str(record["year"]),
        )
        for item in selected
        for record in item["records"]
    }
    overlap = selected_entities & historical_entities
    if (
        len(selected) != SELECTED_COUNT
        or len(selected_entities) != SELECTED_COUNT
        or len(selected_cells) != SELECTED_COUNT * len(TARGETS)
        or selected_cells & historical_cells
    ):
        raise RuntimeError("V2.48.20 fixed population capacity or disjointness failed")
    return selected, {
        "complete_candidate_count": len(candidates),
        "selected_country_count": SELECTED_COUNT,
        "task_count": TASK_COUNT,
        "task_size": TASK_SIZE,
        "selected_gold_cell_count": len(selected_cells),
        "historical_entity_count": len(historical_entities),
        "historical_target_pair_count": len(historical_targets),
        "historical_gold_cell_key_count": len(historical_cells),
        "selected_entity_overlap_count": len(overlap),
        "selected_entity_novel_count": len(selected_entities - historical_entities),
        "selected_entity_overlap_rate": round(len(overlap) / SELECTED_COUNT, 12),
        "selected_target_pair_overlap_count": len(target_pairs & historical_targets),
        "selected_gold_cell_overlap_count": len(selected_cells & historical_cells),
        "region_count": len({str(item["region_id"]) for item in selected}),
    }


def build_artifacts(
    selected: Sequence[Mapping[str, Any]],
    *,
    authorization_audit_sha256: str,
    catalog_metadata: Mapping[str, Any],
    snapshot_metadata: Sequence[Mapping[str, Any]],
    historical_manifest: Mapping[str, str],
    metrics: Mapping[str, Any],
    created_at: int,
    git_head: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if re.fullmatch(r"[0-9a-f]{64}", authorization_audit_sha256) is None:
        raise ValueError("V2.48.20 authorization digest drifted")
    groups = [
        [copy.deepcopy(dict(item)) for item in selected[index : index + TASK_SIZE]]
        for index in range(0, len(selected), TASK_SIZE)
    ]
    if len(groups) != TASK_COUNT or any(len(group) != TASK_SIZE for group in groups):
        raise RuntimeError("V2.48.20 group denominator drifted")
    private = {
        "artifact_version": 1,
        "role": "v24820_cell_disjoint_worldbank_evaluator_only_population",
        "created_at_unix": int(created_at),
        "targets": [dict(target) for target in TARGETS],
        "groups": groups,
        "catalog": dict(catalog_metadata),
        "indicator_snapshots": [dict(item) for item in snapshot_metadata],
        "historical_boundary_manifest": dict(historical_manifest),
        "selection_rule": (
            "new_indicator_year_pairs_then_complete_values_then_entity_novelty_"
            "first_then_v24820_hash_rank_select_128"
        ),
        "disjointness_scope": {
            "task_question_vector_disjoint": True,
            "indicator_year_target_pairs_disjoint": True,
            "country_indicator_year_gold_cells_disjoint": True,
            "country_entities_disjoint": False,
            "country_entity_overlap_reported_in_public_design": True,
        },
        "forward_import_or_runtime_read_authorized": False,
        "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized": False,
        "mechanism_validation_only_not_calibration_lock_validation_or_confirmatory": True,
    }
    private["private_payload_sha256"] = payload_sha256(private)
    visible = [
        {"name": str(item["name"]), "iso3": str(item["iso3"])}
        for item in selected
    ]
    value_vector = [
        {
            "iso3": str(item["iso3"]),
            "records": [
                {
                    "indicator": str(record["indicator"]),
                    "year": str(record["year"]),
                    "value": record["value"],
                    "response_sha256": str(record["response_sha256"]),
                }
                for record in item["records"]
            ],
        }
        for item in selected
    ]
    public = {
        "artifact_version": 1,
        "role": "v24820_cell_disjoint_worldbank_population_design",
        "created_at_unix": int(created_at),
        "git_head": git_head,
        "controller_build_audit_sha256": _sha256(CONTROLLER_AUDIT),
        "authorization_audit_sha256": authorization_audit_sha256,
        "catalog_response_sha256": str(catalog_metadata["response_sha256"]),
        "indicator_snapshot_metadata": [
            dict(item) for item in snapshot_metadata
        ],
        "historical_boundary_manifest_sha256": payload_sha256(
            historical_manifest
        ),
        **dict(metrics),
        "selected_visible_vector_sha256": payload_sha256(visible),
        "selected_value_and_provenance_vector_sha256": payload_sha256(
            value_vector
        ),
        "private_population_file_sha256": None,
        "network": {
            "worldbank_country_catalog_reads": 1,
            "worldbank_bulk_indicator_reads": 2,
            "model_search_benchmark_or_evaluator_calls": 0,
        },
        "privacy": {
            "selected_country_name_iso3_value_or_gold_emitted": False,
            "private_vector_under_evaluation_directory": True,
            "forward_import_or_runtime_read_authorized": False,
        },
        "scope": {
            "mechanism_validation_task_count": TASK_COUNT,
            "main_calibration_task_count": 128,
            "this_population_satisfies_main_calibration_size": False,
            "entity_disjoint_claim": False,
            "target_cell_disjoint_claim": True,
        },
        "authorization": {
            "fresh_external_protocol_design": True,
            "external_launch": False,
            "evaluator_access": False,
            "public_dev64_or_exact220": False,
        },
    }
    return private, public


def _authorized() -> bool:
    value = _read(AUTHORIZATION)
    return (
        value.get("role")
        == "v24820_cell_disjoint_worldbank_population_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("one_population_publication")
        is True
        and value.get("authorization", {}).get("external_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.20 publication requires clean pushed HEAD")
    if not _authorized():
        raise RuntimeError("V2.48.20 publication is not authorized")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.48.20 population surface exists")
    historical_entities, historical_cells, historical_targets, manifest = (
        historical_boundary()
    )
    catalog_raw = base._fetch_bytes(base.COUNTRY_CATALOG_URL)
    countries, catalog_metadata = base.parse_country_catalog(catalog_raw)
    snapshots: list[dict[str, dict[str, Any]]] = []
    snapshot_metadata: list[dict[str, Any]] = []
    for target in TARGETS:
        url = base.indicator_url(target["indicator"], target["year"])
        raw = base._fetch_bytes(url)
        records, metadata = base.parse_indicator_snapshot(
            raw,
            indicator=target["indicator"],
            year=target["year"],
            source_url=url,
        )
        snapshots.append(records)
        snapshot_metadata.append(metadata)
    selected, metrics = select_population(
        countries,
        snapshots,
        historical_entities,
        historical_cells,
        historical_targets,
    )
    private, public = build_artifacts(
        selected,
        authorization_audit_sha256=_sha256(AUTHORIZATION),
        catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        historical_manifest=manifest,
        metrics=metrics,
        created_at=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
    )
    _publish(PRIVATE, private)
    public["private_population_file_sha256"] = hashlib.sha256(
        (ROOT / PRIVATE).read_bytes()
    ).hexdigest()
    public["design_payload_sha256"] = payload_sha256(public)
    _publish(OUTPUT, public)
    print(
        json.dumps(
            {
                "private": str(PRIVATE),
                "output": str(OUTPUT),
                **metrics,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
