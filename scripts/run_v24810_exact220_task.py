#!/usr/bin/env python3
"""Run one V2.48.10 task with the audited V2.48.07 implementation."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24810_exact220_contract as contract  # noqa: E402
from scripts import run_v24807_exact220_task as base  # noqa: E402


def configure(argv: list[str] | None = None) -> Path:
    base.contract = contract
    return base.configure(argv)


def main() -> None:
    configure()
    base.algorithm.main()


if __name__ == "__main__":
    main()
