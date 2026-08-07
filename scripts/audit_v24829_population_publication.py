#!/usr/bin/env python3
"""Post-publication audit for the frozen V2.48.29 population."""

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

from scripts import design_v24829_target_cell_disjoint_population as design  # noqa: E402


DATE = design.DATE
OUTPUT = Path(f"results/v24829_population_publication_audit_v1_{DATE}.json")
PROTECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)


def _read(path: Path) -> dict[str, Any]:
    return design._read(ROOT, path)


def _sha256(path: Path) -> str:
    return design._sha256(ROOT, path)


def _watchers() -> list[dict[str, Any]]:
    output = []
    for pid, ticks, marker in PROTECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        cmdline = Path("/proc") / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.29 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or int(suffix[19]) != ticks or marker not in command:
            raise RuntimeError("V2.48.29 protected watcher drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    if (
        copied.get("role") != "v24829_population_publication_audit"
        or not isinstance(checks, Mapping)
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or copied.get("audit_valid") is not (copied.get("findings") == [])
        or copied.get("authorization")
        != {
            "fresh_external_protocol_design": bool(copied.get("audit_valid")),
            "external_launch": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
            "sota_claim": False,
        }
        or seal != design.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.29 publication audit drifted")
    return copied


def build(*, now: int | None = None) -> dict[str, Any]:
    private = _read(design.PRIVATE)
    public = _read(design.OUTPUT)
    historical_entities, historical_cells, historical_targets, manifest = (
        design.historical_boundary(ROOT)
    )
    groups = private.get("groups")
    targets = private.get("targets")
    private_valid = isinstance(groups, list) and isinstance(targets, list)
    selected_entities: set[str] = set()
    selected_cells: set[tuple[str, str, str]] = set()
    target_pairs: set[tuple[str, str]] = set()
    if private_valid:
        for target in targets:
            if not isinstance(target, Mapping):
                private_valid = False
                break
            target_pairs.add((str(target.get("indicator", "")), str(target.get("year", ""))))
        for group in groups:
            if not isinstance(group, list):
                private_valid = False
                break
            for item in group:
                if not isinstance(item, Mapping):
                    private_valid = False
                    break
                iso3 = str(item.get("iso3", ""))
                records = item.get("records")
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
    selection = design.target_selection_contract(ROOT)
    transport = public.get("transport")
    receipts = transport.get("receipts") if isinstance(transport, Mapping) else None
    receipt_valid = isinstance(receipts, list) and len(receipts) == 3
    if receipt_valid:
        for receipt in receipts:
            if (
                not isinstance(receipt, Mapping)
                or not design._sealed(receipt, "receipt_sha256")
                or receipt.get("terminal_outcome") != "success"
                or receipt.get("url_or_response_content_emitted") is not False
            ):
                receipt_valid = False
                break
    overlap_entities = selected_entities & historical_entities
    checks = {
        "clean_pushed_head": not design._git("status", "--porcelain")
        and design._git("rev-parse", "HEAD") == design._git("rev-parse", "target/main"),
        "private_seal_valid": design._sealed(private, "private_payload_sha256"),
        "public_seal_valid": design._sealed(public, "design_payload_sha256"),
        "private_public_binding_valid": public.get("private_population_file_sha256")
        == _sha256(design.PRIVATE),
        "fixed_denominator_32x4": private_valid
        and len(groups) == 32
        and all(len(group) == 4 for group in groups)
        and len(selected_entities) == 128,
        "target_pair_count_two": len(target_pairs) == 2,
        "target_pairs_historically_disjoint": target_pairs.isdisjoint(historical_targets),
        "selected_gold_cells_256": len(selected_cells) == 256,
        "selected_gold_cells_historically_disjoint": selected_cells.isdisjoint(historical_cells),
        "entity_overlap_disclosed_exactly": public.get("selected_entity_overlap_count")
        == len(overlap_entities)
        and public.get("selected_entity_novel_count")
        == len(selected_entities - historical_entities)
        and public.get("scope", {}).get("entity_disjoint_claim") is False,
        "never_requested_target_selection_binding_valid": selection[
            "selected_unrequested_target_key_vector"
        ]
        == ["SH.STA.BASS.ZS@2022", "SL.UEM.TOTL.ZS@2023"]
        and private.get("target_selection_contract") == selection
        and public.get("target_selection_contract") == selection,
        "historical_manifest_binding_valid": public.get(
            "historical_boundary_manifest_sha256"
        )
        == design.payload_sha256(manifest),
        "transport_receipts_valid": receipt_valid,
        "private_forward_access_denied": private.get(
            "forward_import_or_runtime_read_authorized"
        )
        is False
        and private.get(
            "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized"
        )
        is False,
    }
    watchers = _watchers()
    checks["protected_watchers_unchanged"] = watchers == _watchers()
    value = {
        "artifact_version": 1,
        "role": "v24829_population_publication_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "private_population_sha256": _sha256(design.PRIVATE),
        "public_design_sha256": _sha256(design.OUTPUT),
        "counts": {
            "tasks": len(groups) if isinstance(groups, list) else 0,
            "selected_entities": len(selected_entities),
            "selected_gold_cells": len(selected_cells),
            "historical_populations": len(manifest),
            "historical_entities": len(historical_entities),
            "historical_gold_cells": len(historical_cells),
            "historical_target_pairs": len(historical_targets),
            "selected_entity_overlap": len(overlap_entities),
            "selected_entity_novel": len(selected_entities - historical_entities),
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
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = design.payload_sha256(value)
    return validate(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    if artifact["findings"]:
        raise RuntimeError(f"V2.48.29 publication audit rejected: {artifact['findings']}")
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
