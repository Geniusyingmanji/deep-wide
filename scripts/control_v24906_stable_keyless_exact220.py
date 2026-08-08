#!/usr/bin/env python3
"""Freeze and authorize one fresh stable-keyless exact-220 replication."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24906_stable_keyless_exact220_contract as contract  # noqa: E402
from scripts import control_v24831_keyless_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.RUNNER,
        contract.CHILD,
        Path("scripts/run_v24831_keyless_exact220.py"),
        Path("scripts/run_v24831_keyless_exact220_task.py"),
        Path("scripts/run_v24791_exact220.py"),
        Path("scripts/run_v24791_exact220_task.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24635_exact220_task.py"),
    )
    base.TEST_SUITES = (
        (contract.TEST, 8, 180),
        (Path("tests/test_v24831_keyless_exact220.py"), 8, 180),
        (Path("tests/test_v24791_exact220.py"), 9, 180),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
        (Path("tests/test_v24630_thin_backfill_search.py"), 2, 180),
        (Path("tests/test_v24319_runner_integration.py"), 7, 180),
        (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
    )
    base.EXPECTED_TESTS = 52


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
