#!/usr/bin/env python3
"""Build the evaluator-only V2.46.37 gold from one immutable public snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24637_external_contract import (  # noqa: E402
    ENTITY_GROUPS,
    visible_task,
)
from deepwide_agent.v24637_external_evaluator import (  # noqa: E402
    GOLD, OURAIRPORTS_SNAPSHOT_SHA256, OURAIRPORTS_URL,
)


def build(source: bytes) -> str:
    if hashlib.sha256(source).hexdigest() != OURAIRPORTS_SNAPSHOT_SHA256:
        raise RuntimeError("V2.46.37 immutable OurAirports snapshot hash drifted")
    text = source.decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    by_name = {str(row.get("name", "")).strip(): row for row in rows}
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=["opaque_id", "Airport", "ICAO code", "IATA code"],
        lineterminator="\n",
    )
    writer.writeheader()
    for ordinal, group in enumerate(ENTITY_GROUPS, 1):
        opaque_id = visible_task(ordinal)["opaque_id"]
        for entity in group:
            row = by_name.get(entity)
            if row is None:
                raise RuntimeError("V2.46.37 frozen airport entity is absent from snapshot")
            icao = str(row.get("icao_code", "")).strip()
            iata = str(row.get("iata_code", "")).strip()
            if len(icao) != 4 or len(iata) != 3:
                raise RuntimeError("V2.46.37 frozen airport code is incomplete")
            writer.writerow(
                {"opaque_id": opaque_id, "Airport": entity, "ICAO code": icao, "IATA code": iata}
            )
    return output.getvalue()


def publish(path: Path, value: str) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source")
    parser.add_argument("--output", default=str(GOLD))
    args = parser.parse_args()
    if args.source:
        path = Path(args.source)
        source = path.read_bytes()
    else:
        with urllib.request.urlopen(OURAIRPORTS_URL, timeout=30) as response:
            source = response.read()
    output = ROOT / args.output
    publish(output, build(source))
    print(hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
