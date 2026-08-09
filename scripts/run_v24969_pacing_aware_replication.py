#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.57 exact-220 replication."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24969_pacing_aware_replication_contract as contract  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
