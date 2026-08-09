#!/usr/bin/env python3
"""Configure and run the V2.49.41 post-freeze evaluator."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24941_open_world_ledger_external_contract as contract  # noqa: E402
from scripts import evaluate_v24940_open_world_ledger_external as parent  # noqa: E402


def main() -> None:
    parent.contract = contract
    parent.main()


if __name__ == "__main__":
    main()
