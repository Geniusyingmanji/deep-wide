#!/usr/bin/env python3
"""Append-only region-cap repair for the V2.46.88 population publication."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import design_v24688_worldbank_population as base  # noqa: E402


DATE = "20260806"
PREDECESSOR_AUTHORIZATION = base.AUTHORIZATION
AUTHORIZATION = Path(
    f"results/v24690_worldbank_population_capacity_repair_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(f"evaluation/v24690_worldbank_population_private_v1_{DATE}.json")
OUTPUT = Path(f"results/v24690_worldbank_population_design_v1_{DATE}.json")
REGION_CAP = 9


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.90 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _authorization_valid() -> bool:
    if not (ROOT / AUTHORIZATION).is_file() or (ROOT / AUTHORIZATION).is_symlink():
        return False
    value = _read(ROOT / AUTHORIZATION)
    return (
        value.get("role")
        == "v24690_worldbank_population_capacity_repair_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization")
        == {
            "one_repaired_population_design_publication": True,
            "forward_or_evaluator_surface_publication": False,
            "preactivation_or_launch": False,
            "dev64_or_exact220": False,
            "evaluator_access": False,
            "leaderboard_or_sota": False,
        }
        and _sealed(value, "audit_payload_sha256")
    )


def select_records(
    countries: Mapping[str, Mapping[str, str]],
    snapshots: list[Mapping[str, Mapping[str, str]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return base.select_records(
        countries,
        snapshots,
        selected_count=base.SELECTED_COUNT,
        region_cap=REGION_CAP,
    )


def build_artifacts(
    selected: list[Mapping[str, Any]],
    *,
    catalog_metadata: Mapping[str, Any],
    snapshot_metadata: list[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    created_at: int,
    git_head: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    with _temporary_base_authorization():
        private, public = base.build_artifacts(
            selected,
            catalog_metadata=catalog_metadata,
            snapshot_metadata=snapshot_metadata,
            metrics=metrics,
            created_at=created_at,
            git_head=git_head,
        )
    private["role"] = "v24690_worldbank_evaluator_only_population"
    private["selection_rule"] = private["selection_rule"].replace(
        "region_cap8", "region_cap9"
    )
    private["predecessor_population_artifact_created"] = False
    private.pop("private_payload_sha256")
    private["private_payload_sha256"] = payload_sha256(private)
    public["role"] = "v24690_worldbank_population_design"
    public["authorization_audit_sha256"] = base._sha256(ROOT / AUTHORIZATION)
    public["predecessor_authorization_audit_sha256"] = base._sha256(
        ROOT / PREDECESSOR_AUTHORIZATION
    )
    public["region_cap_repair"] = {
        "old_region_cap": base.REGION_CAP,
        "new_region_cap": REGION_CAP,
        "only_selection_policy_change": "region_cap_8_to_9",
    }
    return private, public


class _temporary_base_authorization:
    """Bind only public hash fields to the repaired authorization paths."""

    def __enter__(self) -> None:
        self.original = base.AUTHORIZATION
        base.AUTHORIZATION = AUTHORIZATION

    def __exit__(self, *_args: object) -> None:
        base.AUTHORIZATION = self.original


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


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
        raise RuntimeError("V2.46.90 population repair requires clean pushed HEAD")
    if not base._parent_valid():
        raise RuntimeError("V2.46.90 V2.46.87 parent build audit drifted")
    if not _authorization_valid():
        raise RuntimeError("V2.46.90 repaired publication is not authorized")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (base.PRIVATE, base.OUTPUT, PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.46.90 population surface exists")

    catalog_raw = base._fetch_bytes(base.COUNTRY_CATALOG_URL)
    countries, catalog_metadata = base.parse_country_catalog(catalog_raw)
    snapshots: list[dict[str, dict[str, str]]] = []
    snapshot_metadata: list[dict[str, Any]] = []
    for target in base.TARGETS:
        url = base.indicator_url(target["indicator"], target["year"])
        raw = base._fetch_bytes(url)
        values, metadata = base.parse_indicator_snapshot(
            raw,
            indicator=target["indicator"],
            year=target["year"],
            source_url=url,
        )
        snapshots.append(values)
        snapshot_metadata.append(metadata)
    selected, metrics = select_records(countries, snapshots)
    private, public = build_artifacts(
        selected,
        catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        metrics=metrics,
        created_at=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
    )
    _publish(ROOT / PRIVATE, private)
    public["private_population_file_sha256"] = base._sha256(ROOT / PRIVATE)
    public["design_sha256"] = payload_sha256(public)
    _publish(ROOT / OUTPUT, public)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "private": str(PRIVATE),
                "selected_count": len(selected),
                "task_count": len(selected) // base.TASK_SIZE,
                "design_sha256": public["design_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
