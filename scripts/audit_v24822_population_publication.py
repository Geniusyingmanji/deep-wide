#!/usr/bin/env python3
"""Post-publication audit for the frozen V2.48.22 external population."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v24809_worldbank_budget_ladder_smoke_contract as watcher_contract,
)
from scripts import (  # noqa: E402
    design_v24822_bounded_snapshot_transport_population as design,
)


DATE = design.DATE
OUTPUT = Path(f"results/v24822_population_publication_audit_v1_{DATE}.json")


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


def _read(path: Path) -> dict[str, Any]:
    target = ROOT / path
    if (
        target.is_symlink()
        or not target.is_file()
        or not target.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.22 publication audit expected object: {path}")
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.22 publication audit expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == design.payload_sha256(unsigned)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(*, now: int | None = None) -> dict[str, Any]:
    private = _read(design.PRIVATE)
    public = _read(design.OUTPUT)
    entities, historical_cells, historical_targets, historical_manifest = (
        design.parent.historical_boundary()
    )
    groups = private.get("groups")
    targets = private.get("targets")
    selected_entities: set[str] = set()
    selected_cells: set[tuple[str, str, str]] = set()
    private_valid = isinstance(groups, list) and isinstance(targets, list)
    target_pairs: set[tuple[str, str]] = set()
    if private_valid:
        for target in targets:
            if not isinstance(target, Mapping):
                private_valid = False
                break
            target_pairs.add(
                (str(target.get("indicator", "")), str(target.get("year", "")))
            )
        for group in groups:
            if not isinstance(group, list):
                private_valid = False
                break
            for item in group:
                records = item.get("records") if isinstance(item, Mapping) else None
                iso3 = str(item.get("iso3", "")) if isinstance(item, Mapping) else ""
                if len(iso3) != 3 or not isinstance(records, list):
                    private_valid = False
                    break
                selected_entities.add(iso3)
                for record in records:
                    if not isinstance(record, Mapping):
                        private_valid = False
                        break
                    selected_cells.add(
                        (
                            iso3,
                            str(record.get("indicator", "")),
                            str(record.get("year", "")),
                        )
                    )
    transport = public.get("transport")
    receipts = transport.get("receipts") if isinstance(transport, Mapping) else None
    receipt_valid = isinstance(receipts, list) and len(receipts) == 3
    if receipt_valid:
        for receipt in receipts:
            if not isinstance(receipt, Mapping):
                receipt_valid = False
                break
            unsigned = dict(receipt)
            seal = unsigned.pop("receipt_sha256", None)
            if (
                seal != design.payload_sha256(unsigned)
                or receipt.get("terminal_outcome") != "success"
                or receipt.get("url_or_response_content_emitted") is not False
            ):
                receipt_valid = False
                break
    overlap_entities = selected_entities & entities
    checks = {
        "clean_pushed_head": not _git("status", "--porcelain")
        and _git("rev-parse", "HEAD") == _git("rev-parse", "target/main"),
        "private_seal_valid": _sealed(private, "private_payload_sha256"),
        "public_seal_valid": _sealed(public, "design_payload_sha256"),
        "private_public_binding_valid": public.get(
            "private_population_file_sha256"
        )
        == _sha256(design.PRIVATE),
        "fixed_denominator_32x4": private_valid
        and len(groups) == 32
        and all(len(group) == 4 for group in groups)
        and len(selected_entities) == 128,
        "target_pair_count_two": len(target_pairs) == 2,
        "target_pairs_historically_disjoint": target_pairs.isdisjoint(
            historical_targets
        ),
        "selected_gold_cells_256": len(selected_cells) == 256,
        "selected_gold_cells_historically_disjoint": selected_cells.isdisjoint(
            historical_cells
        ),
        "entity_overlap_disclosed_exactly": public.get(
            "selected_entity_overlap_count"
        )
        == len(overlap_entities)
        and public.get("selected_entity_novel_count")
        == len(selected_entities - entities)
        and public.get("scope", {}).get("entity_disjoint_claim") is False,
        "transport_receipts_valid": receipt_valid,
        "historical_manifest_binding_valid": public.get(
            "historical_boundary_manifest_sha256"
        )
        == design.payload_sha256(historical_manifest),
        "private_forward_access_denied": private.get(
            "forward_import_or_runtime_read_authorized"
        )
        is False
        and private.get(
            "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized"
        )
        is False,
    }
    watchers = watcher_contract.protected_watcher_snapshot()
    value = {
        "artifact_version": 1,
        "role": "v24822_population_publication_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "private_population_sha256": _sha256(design.PRIVATE),
        "public_design_sha256": _sha256(design.OUTPUT),
        "counts": {
            "tasks": len(groups) if isinstance(groups, list) else 0,
            "selected_entities": len(selected_entities),
            "selected_gold_cells": len(selected_cells),
            "historical_entities": len(entities),
            "historical_gold_cells": len(historical_cells),
            "historical_target_pairs": len(historical_targets),
            "selected_entity_overlap": len(overlap_entities),
            "selected_entity_novel": len(selected_entities - entities),
            "selected_gold_cell_overlap": len(selected_cells & historical_cells),
            "selected_target_pair_overlap": len(target_pairs & historical_targets),
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "protected_watchers": watchers,
        "effect_boundary": {
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "private_values_used_for_forward_routing": False,
            "population_prediction_or_evaluation_performed": False,
        },
        "authorization": {
            "fresh_external_protocol_design": all(checks.values()),
            "external_launch": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_payload_sha256"] = design.payload_sha256(value)
    if value["findings"]:
        raise RuntimeError(
            f"V2.48.22 publication audit rejected: {value['findings']}"
        )
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
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


if __name__ == "__main__":
    artifact = build()
    publish(OUTPUT, artifact)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "counts": artifact["counts"],
                "findings": artifact["findings"],
                "authorization": artifact["authorization"],
            },
            sort_keys=True,
        )
    )
