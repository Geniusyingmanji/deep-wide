#!/usr/bin/env python3
"""Audit and evaluate the fresh V2.50.57 r2 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25057_page_self_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25056_page_self_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.parent.contract = contract
    parent.EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"


def main() -> None:
    configure()
    parent.main()


if __name__ == "__main__":
    main()
