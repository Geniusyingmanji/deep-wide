#!/usr/bin/env python3
"""Freeze and authorize one V2.48.57 pacing-aware exact-220 forward."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as contract  # noqa: E402
from scripts import control_v24800_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE, contract.RUNNER, contract.CHILD,
        contract.TRANSPORT_SOURCE, contract.ADMISSION_SOURCE,
        Path("scripts/run_v24800_exact220.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24635_exact220_task.py"),
        Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
        Path("src/deepwide_agent/v24799_fixed_full_budget_control.py"),
        Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
        Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
        Path("src/deepwide_agent/v24273_two_wave_task_runtime.py"),
    )
    base.TEST_SUITES = (
        (Path("tests/test_v24857_pacing_aware_exact220.py"), 13, 240),
        (Path("tests/test_v24856_pacing_aware_admission.py"), 7, 240),
        (Path("tests/test_v24854_rate_aware_exact220.py"), 11, 240),
        (Path("tests/test_v24852_rate_aware_tavily_search.py"), 11, 240),
        (Path("tests/test_v24800_exact220.py"), 12, 240),
        (Path("tests/test_v24799_fixed_full_budget_control.py"), 5, 240),
        (Path("tests/test_v24796_deadline_tavily_search.py"), 6, 240),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
        (Path("tests/test_v24630_thin_backfill_search.py"), 2, 180),
        (Path("tests/test_v24319_runner_integration.py"), 7, 180),
        (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
    )
    base.EXPECTED_TESTS = 92


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
