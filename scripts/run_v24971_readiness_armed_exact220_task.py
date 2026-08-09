#!/usr/bin/env python3
"""Run one frozen V2.48.57 task in the V2.49.71 namespace."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24971_readiness_armed_exact220_contract as contract  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220_task as base  # noqa: E402


def configure() -> None:
    base.contract = contract


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
