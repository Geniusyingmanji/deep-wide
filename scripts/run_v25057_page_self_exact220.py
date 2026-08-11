#!/usr/bin/env python3
"""Run the fresh V2.50.57 r2 page-self exact-220 forward."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25057_page_self_exact220_contract as contract  # noqa: E402
from scripts import run_v25056_page_self_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.parent.contract = contract
    parent.parent.runtime = parent.runtime
    parent.parent.RobustLatePageBoundSearchClient = parent.PageSelfProductionSearchClient
    parent.parent.validate_search_class = parent.validate_search_class
    parent.parent._validate_start = parent._validate_start
    parent.parent._prepare_output = parent._prepare_output
    parent.parent._aggregate = parent._aggregate


def main() -> None:
    configure()
    parent.parent.main()


if __name__ == "__main__":
    main()
