#!/usr/bin/env python3
"""Control plane for the fresh V2.50.57 r2 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25057_page_self_exact220_contract as contract  # noqa: E402
from scripts import control_v25056_page_self_exact220 as parent  # noqa: E402


TEST_SUITES = (
    (contract.TEST, 6),
    (Path("tests/test_v25056_page_self_exact220.py"), 8),
    *parent.TEST_SUITES[1:],
)
EXPECTED_TESTS = sum(count for _path, count in TEST_SUITES)


def configure() -> None:
    parent.contract = contract
    parent.TEST_SUITES = TEST_SUITES
    parent.EXPECTED_TESTS = EXPECTED_TESTS
    parent.configure()


def main() -> None:
    configure()
    parent.parent.main()


if __name__ == "__main__":
    main()
