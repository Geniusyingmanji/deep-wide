#!/usr/bin/env python3
"""Run one neutral V2.49.04 parser-total reliability task."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24904_revision_parser_total_reliability_contract as contract  # noqa: E402
from deepwide_agent.v24902_revision_parser_total_child_runtime import run_child_bundle  # noqa: E402
from scripts import run_v24883_mapping_recovery_reliability_task as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.run_child_bundle = run_child_bundle


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
