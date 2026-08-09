#!/usr/bin/env python3
"""Freeze and authorize the V2.49.79 atomic PyPI quality gate."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24979_atomic_pypi_quality_contract as contract  # noqa: E402
from scripts import control_v24973_identity_bound_field_quality as base  # noqa: E402


def configure() -> None:
    contract._configure_schema()
    base.contract = contract
    base.FORWARD_SOURCES = (
        contract.SOURCE, contract.EXTRACTOR, contract.RUNTIME,
        contract.ATOMIC_CONTRACT, contract.SCHEMA_CONTRACT,
        contract.SCHEMA_RUNTIME, contract.FIELD_EXTRACTOR,
    )
    base.TEST_SUITES = (
        (contract.TEST, 13),
        (contract.EXTRACTOR_TEST, 8),
        (contract.ATOMIC_TEST, 12),
        (Path("tests/test_v24973_identity_bound_field_quality.py"), 14),
        (Path("tests/test_v24972_identity_bound_compact_fields.py"), 15),
    )
    base.EXPECTED_TESTS = sum(expected for _path, expected in base.TEST_SUITES)


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
