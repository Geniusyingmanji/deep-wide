#!/usr/bin/env python3
"""Run the fresh V2.48.50 exact-220 replication."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v24850_v24800_replication_exact220_contract as contract,
)
from scripts import run_v24800_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
