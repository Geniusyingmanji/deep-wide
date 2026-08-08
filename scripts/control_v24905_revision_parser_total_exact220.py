#!/usr/bin/env python3
"""Freeze and authorize the V2.49.05 parser-total exact-220 run."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24905_revision_parser_total_exact220_contract as contract  # noqa: E402
from scripts import control_v24895_control_binding_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.configure()
    base.base.PREAUDIT_ROLE = "v24905_revision_parser_total_exact220_preactivation_audit"
    base.base.START_ROLE = "v24905_revision_parser_total_exact220_execution_start"
    base.base.base.RUNTIME_SOURCES = tuple(
        dict.fromkeys(
            (
                *base.base.base.RUNTIME_SOURCES,
                *contract.CORRECTED_SOURCES,
                contract.SOURCE,
                contract.RUNNER,
                contract.CHILD,
            )
        )
    )
    base.base.base.TEST_SUITES = (
        (contract.TEST, 15, 240),
        (Path("tests/test_v24897_revision_parser_totality.py"), 4, 240),
        (Path("tests/test_v24898_revision_parser_total_integration.py"), 2, 240),
        (Path("tests/test_v24903_revision_parser_total_production_seam.py"), 5, 240),
        *base.base.base.TEST_SUITES[1:],
    )
    base.base.base.EXPECTED_TESTS = sum(
        expected for _path, expected, _timeout in base.base.base.TEST_SUITES
    )


def main() -> None:
    configure()
    base.base.base.main()


if __name__ == "__main__":
    main()
