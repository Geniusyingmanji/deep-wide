#!/usr/bin/env python3
"""Run one V2.49.09 task with the statically bound fixed-budget policy."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24909_keyless_fixed_budget_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24907_keyless_fixed_budget_binding import bind_child_algorithm  # noqa: E402
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


def configure() -> None:
    bind_child_algorithm(algorithm, contract)


def main() -> None:
    configure()
    algorithm.main()


if __name__ == "__main__":
    main()
