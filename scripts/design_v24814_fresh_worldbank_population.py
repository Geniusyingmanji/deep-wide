#!/usr/bin/env python3
"""Append-only V2.48.13 successor removing its unreachable region cap."""

from __future__ import annotations

import copy
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24813_fresh_worldbank_population as base  # noqa: E402


DATE = base.DATE
FAILURE_AUDIT = Path(
    f"results/v24813_population_zero_publication_failure_audit_v1_{DATE}.json"
)
AUTHORIZATION = Path(
    f"results/v24814_fresh_worldbank_population_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(f"evaluation/v24814_fresh_worldbank_population_private_v1_{DATE}.json")
OUTPUT = Path(f"results/v24814_fresh_worldbank_population_design_v1_{DATE}.json")
REGION_CAP = base.SELECTED_COUNT


def select_population(
    countries: Mapping[str, Mapping[str, str]],
    snapshots: Sequence[Mapping[str, Mapping[str, Any]]],
    excluded: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(snapshots) != len(base.TARGETS):
        raise ValueError("V2.48.14 snapshot vector drifted")
    candidates = []
    for iso3, country in countries.items():
        if iso3 in excluded or any(iso3 not in snapshot for snapshot in snapshots):
            continue
        records = [dict(snapshot[iso3]) for snapshot in snapshots]
        if all(record.get("value") is not None for record in records):
            candidates.append({**dict(country), "records": records})
    ordered = sorted(
        candidates,
        key=lambda item: (base._rank(str(item["iso3"])), str(item["iso3"])),
    )
    selected = ordered[: base.SELECTED_COUNT]
    if (
        len(selected) != base.SELECTED_COUNT
        or len({item["iso3"] for item in selected}) != base.SELECTED_COUNT
        or not excluded.isdisjoint({item["iso3"] for item in selected})
    ):
        raise RuntimeError("V2.48.14 fresh complete capacity is insufficient")
    return selected, {
        "complete_candidate_count": len(candidates),
        "selected_country_count": base.SELECTED_COUNT,
        "task_count": base.TASK_COUNT,
        "task_size": base.TASK_SIZE,
        "task_stratum_counts": {"complete": base.TASK_COUNT},
        "region_count": len({item["region_id"] for item in selected}),
    }


def build_artifacts(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    original = base.AUTHORIZATION
    try:
        base.AUTHORIZATION = AUTHORIZATION
        private, public = base.build_artifacts(*args, **kwargs)
    finally:
        base.AUTHORIZATION = original
    private = copy.deepcopy(private)
    public = copy.deepcopy(public)
    private["role"] = "v24814_fresh_worldbank_evaluator_only_population"
    private["selection_rule"] = (
        "exclude_96_historical_and_64_consumed_v24809_countries_then_"
        "v24813_hash_rank_select_48_complete_without_unreachable_region_cap"
    )
    private["append_only_successor"] = {
        "predecessor": "v24813",
        "only_change": "remove_unreachable_region_cap12",
        "predecessor_private_or_public_population_written": False,
        "population_targets_rank_task_count_and_historical_exclusion_unchanged": True,
    }
    private.pop("private_payload_sha256")
    private["private_payload_sha256"] = base.payload_sha256(private)
    public["role"] = "v24814_fresh_worldbank_population_design"
    public["authorization_audit_sha256"] = base._sha256(ROOT / AUTHORIZATION)
    public["v24813_zero_publication_failure_audit_sha256"] = base._sha256(
        ROOT / FAILURE_AUDIT
    )
    public["append_only_successor"] = private["append_only_successor"]
    return private, public


def _authorized() -> bool:
    value = base._read(ROOT / AUTHORIZATION)
    return (
        value.get("role") == "v24814_fresh_worldbank_population_build_audit"
        and value.get("audit_valid") is True and value.get("findings") == []
        and value.get("authorization", {}).get("one_population_publication") is True
        and value.get("authorization", {}).get("external_launch") is False
        and base._sealed(value, "audit_payload_sha256")
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
    if base._git("status", "--porcelain") or base._git(
        "rev-parse", "HEAD"
    ) != base._git("rev-parse", "target/main"):
        raise RuntimeError("V2.48.14 publication requires clean pushed HEAD")
    if not _authorized():
        raise RuntimeError("V2.48.14 publication is not authorized")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (base.PRIVATE, base.OUTPUT, PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.48.14 population surface exists")
    excluded, historical_manifest = base.historical_iso3()
    catalog_raw = base.base._fetch_bytes(base.base.COUNTRY_CATALOG_URL)
    countries, catalog_metadata = base.base.parse_country_catalog(catalog_raw)
    snapshots = []
    snapshot_metadata = []
    for target in base.TARGETS:
        url = base.base.indicator_url(target["indicator"], target["year"])
        raw = base.base._fetch_bytes(url)
        records, metadata = base.base.parse_indicator_snapshot(
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
        created_at=__import__("time").time_ns() // 1_000_000_000,
        git_head=base._git("rev-parse", "HEAD"),
    )
    _publish(ROOT / PRIVATE, private)
    public["private_population_file_sha256"] = base._sha256(ROOT / PRIVATE)
    public["design_payload_sha256"] = base.payload_sha256(public)
    _publish(ROOT / OUTPUT, public)
    print(json.dumps({"private": str(PRIVATE), "output": str(OUTPUT), **metrics}, sort_keys=True))


if __name__ == "__main__":
    main()
