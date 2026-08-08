#!/usr/bin/env python3
"""Post-freeze evaluator namespace for V2.49.05 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24905_revision_parser_total_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24877_keyless_coverage_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.FORWARD_ROLE = "v24905_revision_parser_total_exact220_forward_result"
    parent.SUMMARY_ROLE = "v24905_revision_parser_total_exact220_run_summary"
    parent.FREEZE_ROLE = "v24905_revision_parser_total_exact220_prediction_freeze"
    parent.configure()
    parent.base.CONTROL_FILES = tuple(
        dict.fromkeys(
            (
                "scripts/finalize_v24905_revision_parser_total_exact220.py",
                *parent.base.CONTROL_FILES,
            )
        )
    )
    parent.base.EVALUATOR_PROTOCOL = Path(
        f"results/v24905_revision_parser_total_exact220_evaluator_preregistration_v1_{contract.DATE}.json"
    )
    parent.base.FINAL_RESULT = Path(
        f"results/v24905_revision_parser_total_exact220_result_v1_{contract.DATE}.json"
    )
    parent.base.POSTAUDIT = Path(
        f"results/v24905_revision_parser_total_exact220_postresult_audit_v1_{contract.DATE}.json"
    )


def main() -> None:
    configure()
    parent.base.main()


if __name__ == "__main__":
    main()
