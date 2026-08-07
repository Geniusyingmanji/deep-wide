#!/usr/bin/env python3
"""Append-only V2.48.05 clean-gate successor for smoke publication.

V2.48.05 stopped before network because its generic clean-tree check included
the pre-existing local ``.research/tmp/`` paper cache. This successor changes
only that pre-network check and publishes to new V2.48.06 surfaces. Population
selection, targets, ranks, strata, privacy, and all downstream authority remain
unchanged.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
from collections.abc import Mapping
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
AUTHORIZATION = Path(
    f"results/v24806_worldbank_budget_ladder_smoke_population_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(
    f"evaluation/v24806_worldbank_budget_ladder_smoke_population_private_v1_{DATE}.json"
)
OUTPUT = Path(
    f"results/v24806_worldbank_budget_ladder_smoke_population_design_v1_{DATE}.json"
)
FAILURE_AUDIT = Path(
    f"results/v24806_v24805_population_zero_effect_failure_audit_v1_{DATE}.json"
)


def _clean_except_local_research_tmp() -> bool:
    lines = [
        line
        for line in base._git("status", "--porcelain=v1").splitlines()
        if line.strip()
    ]
    return all(line == "?? .research/tmp/" for line in lines)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.06 expected object")
    return value


def _authorized() -> bool:
    path = ROOT / AUTHORIZATION
    if path.is_symlink() or not path.is_file():
        return False
    value = _read(path)
    return (
        value.get("role")
        == "v24806_worldbank_budget_ladder_smoke_population_build_audit"
        and value.get("audit_valid") is True and value.get("findings") == []
        and value.get("authorization", {}).get("one_smoke_population_publication")
        is True
        and value.get("authorization", {}).get("smoke_launch") is False
        and base._sealed(value, "audit_payload_sha256")
    )


def build_artifacts(
    selected: list[Mapping[str, Any]], *,
    catalog_metadata: Mapping[str, Any],
    snapshot_metadata: list[Mapping[str, Any]],
    historical_manifest: Mapping[str, str],
    metrics: Mapping[str, Any], created_at: int, git_head: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    original = base.AUTHORIZATION
    try:
        base.AUTHORIZATION = AUTHORIZATION
        private, public = base.build_artifacts(
            selected,
            catalog_metadata=catalog_metadata,
            snapshot_metadata=snapshot_metadata,
            historical_manifest=historical_manifest,
            metrics=metrics,
            created_at=created_at,
            git_head=git_head,
        )
    finally:
        base.AUTHORIZATION = original
    private["role"] = (
        "v24806_worldbank_budget_ladder_smoke_evaluator_only_population"
    )
    private["append_only_clean_gate_successor"] = {
        "predecessor": "v24805",
        "only_change": "permit_exact_untracked_research_tmp_directory",
        "predecessor_population_consumed": False,
        "population_selection_targets_ranks_strata_and_policy_unchanged": True,
    }
    private.pop("private_payload_sha256")
    private["private_payload_sha256"] = base.payload_sha256(private)
    public["role"] = "v24806_worldbank_budget_ladder_smoke_population_design"
    public["authorization_audit_sha256"] = base._sha256(ROOT / AUTHORIZATION)
    public["predecessor_zero_effect_failure_audit_sha256"] = base._sha256(
        ROOT / FAILURE_AUDIT
    )
    public["append_only_clean_gate_successor"] = {
        "predecessor": "v24805",
        "only_change": "permit_exact_untracked_research_tmp_directory",
        "predecessor_population_consumed": False,
        "population_selection_targets_ranks_strata_and_policy_unchanged": True,
    }
    return private, public


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
    if not _clean_except_local_research_tmp() or base._git(
        "rev-parse", "HEAD"
    ) != base._git("rev-parse", "target/main"):
        raise RuntimeError("V2.48.06 population publication requires clean pushed HEAD")
    if not _authorized():
        raise RuntimeError("V2.48.06 population publication is not authorized")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (base.PRIVATE, base.OUTPUT, PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.48.06 population surface exists")
    excluded, historical_manifest = base.historical_iso3()
    catalog_raw = base._fetch_bytes(base.COUNTRY_CATALOG_URL)
    countries, catalog_metadata = base.parse_country_catalog(catalog_raw)
    snapshots: list[dict[str, dict[str, Any]]] = []
    snapshot_metadata: list[dict[str, Any]] = []
    for target in base.TARGETS:
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
    selected, metrics = base.select_population(countries, snapshots, excluded)
    private, public = build_artifacts(
        selected,
        catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        historical_manifest=historical_manifest,
        metrics=metrics,
        created_at=__import__("time").time_ns() // 1_000_000_000,
        git_head=base._git("rev-parse", "HEAD"),
    )
    _publish(ROOT / PRIVATE, private)
    public["private_population_file_sha256"] = base._sha256(ROOT / PRIVATE)
    public["design_payload_sha256"] = base.payload_sha256(public)
    _publish(ROOT / OUTPUT, public)
    print(json.dumps({
        "private": str(PRIVATE), "output": str(OUTPUT),
        "selected_count": metrics["selected_country_count"],
        "task_count": metrics["task_count"],
        "task_stratum_counts": metrics["task_stratum_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
