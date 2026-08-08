#!/usr/bin/env python3
"""Run the corrected append-only V2.48.78 exact-220 forward."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24878_keyless_coverage_exact220_contract as contract  # noqa: E402
from scripts import run_v24877_keyless_coverage_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.PREAUDIT_ROLE = "v24878_keyless_coverage_exact220_preactivation_audit"
    base.START_ROLE = "v24878_keyless_coverage_exact220_execution_start"
    base.PROGRESS_ROLE = "v24878_keyless_coverage_exact220_safe_forward_progress"
    base.SUMMARY_ROLE = "v24878_keyless_coverage_exact220_run_summary"
    base.FREEZE_ROLE = "v24878_keyless_coverage_exact220_prediction_freeze"
    base.FORWARD_ROLE = "v24878_keyless_coverage_exact220_forward_result"


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
