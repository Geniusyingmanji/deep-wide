#!/usr/bin/env python3
"""Run the fresh V2.49.41 capacity-safe external gate once."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24941_open_world_ledger_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    engine.contract = contract
    engine.parse_target = parent.parse_target
    engine.build_snapshot = parent.build_snapshot
    engine.build_forward_audit = parent.build_forward_audit


def main() -> None:
    configure()
    engine.main()


if __name__ == "__main__":
    main()
