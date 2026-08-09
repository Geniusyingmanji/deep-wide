#!/usr/bin/env python3
"""Freeze and authorize the independent V2.49.75 external gate."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24975_raw_authority_quality_contract as contract  # noqa: E402
from scripts import control_v24973_identity_bound_field_quality as base  # noqa: E402


def configure() -> None:
    contract.configure_parent()
    base.contract = contract
    base.FORWARD_SOURCES = (
        contract.SOURCE,
        contract.EXTRACTOR,
        contract.RUNTIME,
        contract.PARENT_CONTRACT,
        contract.PARENT_RUNTIME,
        contract.FIELD_EXTRACTOR,
    )
    base.TEST_SUITES = (
        (contract.TEST, 10),
        (contract.EXTRACTOR_TEST, 7),
        (contract.PARENT_TEST, 14),
        (contract.FIELD_EXTRACTOR_TEST, 15),
    )
    base.EXPECTED_TESTS = sum(expected for _path, expected in base.TEST_SUITES)


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
