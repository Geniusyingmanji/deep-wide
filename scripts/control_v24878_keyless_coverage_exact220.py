#!/usr/bin/env python3
"""Freeze and authorize corrected V2.48.78 exact-220 artifacts."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24878_keyless_coverage_exact220_contract as contract  # noqa: E402
from scripts import control_v24877_keyless_coverage_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.PREAUDIT_ROLE = "v24878_keyless_coverage_exact220_preactivation_audit"
    parent.START_ROLE = "v24878_keyless_coverage_exact220_execution_start"
    parent.configure()
    parent.base.RUNTIME_SOURCES = tuple(
        dict.fromkeys(
            (
                *parent.base.RUNTIME_SOURCES,
                Path("src/deepwide_agent/v24877_keyless_coverage_exact220_contract.py"),
                Path("scripts/run_v24877_keyless_coverage_exact220.py"),
                Path("scripts/run_v24877_keyless_coverage_exact220_task.py"),
            )
        )
    )
    parent.base.TEST_SUITES = (
        (contract.TEST, 10, 240),
        (Path("tests/test_v24878_keyless_coverage_runner_fix.py"), 3, 240),
        (Path("tests/test_v24877_keyless_coverage_exact220.py"), 12, 240),
        *parent.base.TEST_SUITES[1:],
    )
    parent.base.EXPECTED_TESTS = 109


def main() -> None:
    configure()
    parent.base.main()


if __name__ == "__main__":
    main()
