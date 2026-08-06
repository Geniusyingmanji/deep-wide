#!/usr/bin/env python3
"""Run the append-only V2.46.82 recovery of the effect-free V2.46.79 start."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24679_schema_dev64_contract as contract  # noqa: E402
from scripts import run_v24679_schema_dev64 as frozen  # noqa: E402
from scripts import v24682_v24679_schema_dev64_recovery_control as recovery  # noqa: E402


def main() -> None:
    recovery.validate_execution_start()
    frozen.FORWARD_AUDIT = contract.FORWARD_AUDIT
    frozen.EXECUTION_START = recovery.EXECUTION_START
    frozen.main()


if __name__ == "__main__":
    main()
