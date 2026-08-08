#!/usr/bin/env python3
"""Freeze and authorize one fresh V2.48.00-policy exact-220 replication."""

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
from scripts import control_v24800_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.RUNNER,
        contract.CHILD,
        Path("scripts/run_v24800_exact220.py"),
        Path("scripts/run_v24800_exact220_task.py"),
        Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
        Path("src/deepwide_agent/v24799_fixed_full_budget_control.py"),
        Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
        Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24635_exact220_task.py"),
    )
    base.TEST_SUITES = (
        (Path("tests/test_v24850_v24800_replication_exact220.py"), 10, 240),
        (Path("tests/test_v24800_exact220.py"), 12, 240),
        (Path("tests/test_v24799_fixed_full_budget_control.py"), 5, 240),
        (Path("tests/test_v24796_deadline_tavily_search.py"), 6, 240),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
        (Path("tests/test_v24630_thin_backfill_search.py"), 2, 180),
        (Path("tests/test_v24319_runner_integration.py"), 7, 180),
        (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
    )
    base.EXPECTED_TESTS = 60


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
