#!/usr/bin/env python3
"""Design a fresh 12-task population after consuming V2.48.09's countries."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24805_worldbank_budget_ladder_smoke_population as base  # noqa: E402
from deepwide_agent.v24809_worldbank_budget_ladder_smoke_contract import payload_sha256  # noqa: E402


DATE = "20260807"
PARENT_AUDIT = Path(f"results/v24812_batched_search_accounting_build_audit_v1_{DATE}.json")
CONSUMED_POPULATION = Path(
    f"evaluation/v24806_worldbank_budget_ladder_smoke_population_private_v1_{DATE}.json"
)
AUTHORIZATION = Path(
    f"results/v24813_fresh_worldbank_population_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(f"evaluation/v24813_fresh_worldbank_population_private_v1_{DATE}.json")
OUTPUT = Path(f"results/v24813_fresh_worldbank_population_design_v1_{DATE}.json")
TARGETS = base.TARGETS
TASK_SIZE = 4
TASK_COUNT = 12
SELECTED_COUNT = TASK_SIZE * TASK_COUNT
REGION_CAP = 12
POLICY = base.POLICY


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(
        ROOT.resolve()
    ):
        raise RuntimeError(f"V2.48.13 expected repository object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.13 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def historical_iso3(root: Path = ROOT) -> tuple[set[str], dict[str, str]]:
    old, manifest = base.historical_iso3(root)
    consumed_path = root / CONSUMED_POPULATION
    consumed = json.loads(consumed_path.read_text(encoding="utf-8"))
    consumed_iso3 = base._iso3_values(consumed)
    if len(old) != 96 or len(consumed_iso3) != 64 or not old.isdisjoint(consumed_iso3):
        raise RuntimeError("V2.48.13 historical population boundary drifted")
    output = old | consumed_iso3
    manifest[str(CONSUMED_POPULATION)] = hashlib.sha256(
        consumed_path.read_bytes()
    ).hexdigest()
    if len(output) != 160:
        raise RuntimeError("V2.48.13 historical exclusion count drifted")
    return output, dict(sorted(manifest.items()))


def _rank(iso3: str) -> str:
    return hashlib.sha256(f"v24813:fresh-complete:{iso3}".encode()).hexdigest()


def select_population(
    countries: Mapping[str, Mapping[str, str]],
    snapshots: Sequence[Mapping[str, Mapping[str, Any]]],
    excluded: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(snapshots) != len(TARGETS):
        raise ValueError("V2.48.13 snapshot vector drifted")
    candidates = []
    for iso3, country in countries.items():
        if iso3 in excluded or any(iso3 not in snapshot for snapshot in snapshots):
            continue
        records = [dict(snapshot[iso3]) for snapshot in snapshots]
        if all(record.get("value") is not None for record in records):
            candidates.append({**dict(country), "records": records})
    ordered = sorted(
        candidates, key=lambda item: (_rank(str(item["iso3"])), str(item["iso3"]))
    )
    selected: list[dict[str, Any]] = []
    regions: Counter[str] = Counter()
    for item in ordered:
        region = str(item["region_id"])
        if regions[region] >= REGION_CAP:
            continue
        selected.append(item)
        regions[region] += 1
        if len(selected) == SELECTED_COUNT:
            break
    if (
        len(selected) != SELECTED_COUNT
        or len({item["iso3"] for item in selected}) != SELECTED_COUNT
        or not excluded.isdisjoint({item["iso3"] for item in selected})
    ):
        raise RuntimeError("V2.48.13 fresh complete capacity is insufficient")
    return selected, {
        "complete_candidate_count": len(candidates),
        "selected_country_count": SELECTED_COUNT,
        "task_count": TASK_COUNT,
        "task_size": TASK_SIZE,
        "task_stratum_counts": {"complete": TASK_COUNT},
        "region_count": len({item["region_id"] for item in selected}),
    }


def build_artifacts(
    selected: Sequence[Mapping[str, Any]], *,
    catalog_metadata: Mapping[str, Any],
    snapshot_metadata: Sequence[Mapping[str, Any]],
    historical_manifest: Mapping[str, str], metrics: Mapping[str, Any],
    created_at: int, git_head: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    groups = [
        [dict(item) for item in selected[index : index + TASK_SIZE]]
        for index in range(0, len(selected), TASK_SIZE)
    ]
    if len(groups) != TASK_COUNT or any(len(group) != TASK_SIZE for group in groups):
        raise RuntimeError("V2.48.13 task grouping drifted")
    private = {
        "artifact_version": 1,
        "role": "v24813_fresh_worldbank_evaluator_only_population",
        "created_at_unix": int(created_at),
        "targets": [dict(target) for target in TARGETS],
        "adaptive_policy": dataclasses.asdict(POLICY),
        "task_stratum_vector": ["complete"] * TASK_COUNT,
        "groups": groups,
        "catalog": dict(catalog_metadata),
        "indicator_snapshots": [dict(item) for item in snapshot_metadata],
        "historical_exclusion_manifest": dict(historical_manifest),
        "historical_excluded_iso3_count": 160,
        "selection_rule": (
            "exclude_96_historical_and_64_consumed_v24809_countries_then_"
            "v24813_hash_rank_region_cap12_select_48_complete"
        ),
        "forward_import_or_runtime_read_authorized": False,
        "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized": False,
        "smoke_only_not_main_calibration_lock_validation_or_confirmatory": True,
    }
    private["private_payload_sha256"] = payload_sha256(private)
    visible = [{"name": item["name"], "iso3": item["iso3"]} for item in selected]
    values = [
        {
            "iso3": item["iso3"],
            "records": [
                {
                    "indicator": record["indicator"], "year": record["year"],
                    "value": record["value"],
                    "response_sha256": record["response_sha256"],
                }
                for record in item["records"]
            ],
        }
        for item in selected
    ]
    public = {
        "artifact_version": 1,
        "role": "v24813_fresh_worldbank_population_design",
        "created_at_unix": int(created_at),
        "git_head": git_head,
        "parent_audit_sha256": _sha256(ROOT / PARENT_AUDIT),
        "authorization_audit_sha256": _sha256(ROOT / AUTHORIZATION),
        "catalog_response_sha256": catalog_metadata["response_sha256"],
        "indicator_snapshot_metadata": [dict(item) for item in snapshot_metadata],
        "historical_exclusion_manifest_sha256": payload_sha256(historical_manifest),
        "historical_excluded_iso3_count": 160,
        **dict(metrics),
        "selected_visible_vector_sha256": payload_sha256(visible),
        "selected_value_and_provenance_vector_sha256": payload_sha256(values),
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
            "smoke_task_count": TASK_COUNT,
            "main_calibration_task_count": 128,
            "this_population_satisfies_main_sample_size": False,
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
    value = _read(ROOT / AUTHORIZATION)
    return (
        value.get("role") == "v24813_fresh_worldbank_population_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("one_population_publication") is True
        and value.get("authorization", {}).get("external_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
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
        raise RuntimeError("V2.48.13 publication requires clean pushed HEAD")
    if not _authorized():
        raise RuntimeError("V2.48.13 publication is not authorized")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PRIVATE, OUTPUT)):
        raise FileExistsError("V2.48.13 population surface exists")
    excluded, historical_manifest = historical_iso3()
    catalog_raw = base._fetch_bytes(base.COUNTRY_CATALOG_URL)
    countries, catalog_metadata = base.parse_country_catalog(catalog_raw)
    snapshots = []
    snapshot_metadata = []
    for target in TARGETS:
        url = base.indicator_url(target["indicator"], target["year"])
        raw = base._fetch_bytes(url)
        records, metadata = base.parse_indicator_snapshot(
            raw, indicator=target["indicator"], year=target["year"],
            source_url=url,
        )
        snapshots.append(records)
        snapshot_metadata.append(metadata)
    selected, metrics = select_population(countries, snapshots, excluded)
    private, public = build_artifacts(
        selected, catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        historical_manifest=historical_manifest, metrics=metrics,
        created_at=int(time.time()), git_head=_git("rev-parse", "HEAD"),
    )
    _publish(ROOT / PRIVATE, private)
    public["private_population_file_sha256"] = _sha256(ROOT / PRIVATE)
    public["design_payload_sha256"] = payload_sha256(public)
    _publish(ROOT / OUTPUT, public)
    print(json.dumps({"private": str(PRIVATE), "output": str(OUTPUT), **metrics}, sort_keys=True))


if __name__ == "__main__":
    main()
