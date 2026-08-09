#!/usr/bin/env python3
"""Run the fresh V2.49.43 representation-only gate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24943_compact_ledger_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as population  # noqa: E402


def configure() -> None:
    population.contract = contract
    engine.contract = contract
    engine.parse_target = population.parse_target
    engine.build_snapshot = population.build_snapshot
    engine.build_forward_audit = population.build_forward_audit


def main() -> None:
    configure()
    engine.main()


if __name__ == "__main__":
    main()
