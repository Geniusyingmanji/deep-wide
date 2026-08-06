#!/usr/bin/env python3
"""Append-only repair of the invalid V2.46.91 generated surface bundle."""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import build_v24691_worldbank_surfaces as predecessor  # noqa: E402


DATE = "20260806"
QUARANTINE = Path(
    f"results/v24693_v24691_surface_codegen_quarantine_audit_v1_{DATE}.json"
)
AUTHORIZATION = Path(f"results/v24695_worldbank_surface_repair_build_audit_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24694_worldbank_external_contract.py")
EVALUATOR = Path("src/deepwide_agent/v24694_worldbank_external_evaluator.py")
GOLD = Path("evaluation/v24694_worldbank_gold_v1.csv")
PROVENANCE = Path("evaluation/v24694_worldbank_gold_provenance_v1.json")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.94 expected object")
    return value


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _quarantine_valid() -> bool:
    value = _read(ROOT / QUARANTINE)
    return (
        value.get("role") == "v24693_v24691_surface_codegen_quarantine_audit"
        and value.get("status") == "invalid_quarantined_do_not_use"
        and value.get("incident", {}).get("root_cause")
        == "plain_triple_quoted_evaluator_template_retained_double_brace_expressions"
        and value.get("incident", {}).get("predictions_created") is False
        and value.get("authorization", {}).get(
            "reuse_v24692_surface_publication_authority"
        )
        is False
        and value.get("authorization", {}).get(
            "fresh_append_only_surface_repair_implementation"
        )
        is True
    )


def _new_id(ordinal: int) -> str:
    return f"task_{0x246940 + ordinal:024x}"


def _old_id(ordinal: int) -> str:
    return f"task_{0x246910 + ordinal:024x}"


def _repair_evaluator(source: str) -> str:
    if "{{" not in source or "}}" not in source:
        raise RuntimeError("V2.46.94 expected predecessor brace defect")
    repaired = source.replace("{{", "{").replace("}}", "}")
    repaired = repaired.replace("v24691", "v24694").replace("V2.46.91", "V2.46.94")
    if "{{" in repaired or "}}" in repaired or "v24691" in repaired:
        raise RuntimeError("V2.46.94 evaluator repair incomplete")
    compile(repaired, str(EVALUATOR), "exec")
    return repaired


def build_surfaces() -> dict[Path, str]:
    if not _quarantine_valid():
        raise RuntimeError("V2.46.94 quarantine audit drifted")
    old = predecessor.build_surfaces()
    contract = old[predecessor.CONTRACT]
    contract = contract.replace("v24691", "v24694").replace(
        "V2.46.91", "V2.46.94"
    )
    contract = contract.replace("0x246910", "0x246940")
    compile(contract, str(CONTRACT), "exec")
    evaluator = _repair_evaluator(old[predecessor.EVALUATOR])

    reader = csv.DictReader(io.StringIO(old[predecessor.GOLD]))
    if reader.fieldnames is None:
        raise RuntimeError("V2.46.94 predecessor gold schema absent")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    id_map = {_old_id(index): _new_id(index) for index in range(1, 13)}
    gold_rows = 0
    for row in reader:
        opaque_id = str(row.get("opaque_id", ""))
        if opaque_id not in id_map:
            raise RuntimeError("V2.46.94 predecessor opaque ID drifted")
        copied = dict(row)
        copied["opaque_id"] = id_map[opaque_id]
        writer.writerow(copied)
        gold_rows += 1
    if gold_rows != 48:
        raise RuntimeError("V2.46.94 gold denominator drifted")

    provenance = json.loads(old[predecessor.PROVENANCE])
    if not isinstance(provenance, dict):
        raise RuntimeError("V2.46.94 predecessor provenance drifted")
    provenance.pop("provenance_payload_sha256", None)
    provenance["role"] = "v24694_worldbank_gold_provenance"
    provenance["quarantine_audit_sha256"] = _sha256(ROOT / QUARANTINE)
    provenance["append_only_repair"] = {
        "invalid_predecessor": "v24691",
        "only_semantic_repair": "generated_evaluator_double_braces_to_single_braces",
        "population_gold_values_and_provenance_unchanged": True,
        "new_opaque_id_namespace": True,
    }
    for record in provenance.get("records", []):
        old_id = str(record.get("opaque_id", ""))
        if old_id not in id_map:
            raise RuntimeError("V2.46.94 provenance opaque ID drifted")
        record["opaque_id"] = id_map[old_id]
    provenance["provenance_payload_sha256"] = payload_sha256(provenance)
    return {
        CONTRACT: contract,
        EVALUATOR: evaluator,
        GOLD: output.getvalue(),
        PROVENANCE: json.dumps(
            provenance, ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n",
    }


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _authorization_valid() -> bool:
    if not (ROOT / AUTHORIZATION).is_file() or (ROOT / AUTHORIZATION).is_symlink():
        return False
    value = _read(ROOT / AUTHORIZATION)
    return (
        value.get("role") == "v24695_worldbank_surface_repair_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization")
        == {
            "one_repaired_surface_publication": True,
            "external_protocol_design": False,
            "preactivation_or_launch": False,
            "evaluator_execution_on_predictions": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        and _sealed(value, "audit_payload_sha256")
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _publish(relative: Path, data: str) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.94 surface repair requires clean pushed HEAD")
    if not _authorization_valid():
        raise RuntimeError("V2.46.94 repaired publication is not authorized")
    surfaces = build_surfaces()
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in surfaces):
        raise FileExistsError("V2.46.94 repaired surface already exists")
    for path, data in surfaces.items():
        _publish(path, data)
    print(
        json.dumps(
            {"contract": str(CONTRACT), "gold_rows": 48,
             "surface_sha256": {str(path): _sha256(ROOT / path) for path in surfaces}},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
