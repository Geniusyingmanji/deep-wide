#!/usr/bin/env python3
"""Post-freeze audit/evaluation facade for the V2.49.75 gate."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24975_raw_authority_quality_contract as contract  # noqa: E402
from scripts import finalize_v24973_identity_bound_field_quality as base  # noqa: E402
from scripts import run_v24975_raw_authority_quality as runner  # noqa: E402


def configure() -> None:
    contract.configure_parent()
    runner.configure()
    base.contract = contract
    base.runner = runner


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
