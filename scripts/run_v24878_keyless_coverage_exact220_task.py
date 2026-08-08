#!/usr/bin/env python3
"""Static V2.48.78 child namespace for the corrected keyless coverage run."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24878_keyless_coverage_exact220_contract as contract  # noqa: E402
from scripts import run_v24877_keyless_coverage_exact220_task as base  # noqa: E402


def main() -> None:
    base.contract = contract
    base.main()


if __name__ == "__main__":
    main()
