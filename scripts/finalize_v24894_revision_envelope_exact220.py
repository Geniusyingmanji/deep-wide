#!/usr/bin/env python3
"""Post-freeze evaluator namespace for V2.48.94 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24894_revision_envelope_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24884_mapping_recovery_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.parent.contract = contract
    parent.parent.FORWARD_ROLE = "v24894_revision_envelope_exact220_forward_result"
    parent.parent.SUMMARY_ROLE = "v24894_revision_envelope_exact220_run_summary"
    parent.parent.FREEZE_ROLE = "v24894_revision_envelope_exact220_prediction_freeze"
    parent.configure()
    parent.parent.base.EVALUATOR_PROTOCOL = Path(
        f"results/v24894_revision_envelope_exact220_evaluator_preregistration_v1_{contract.DATE}.json"
    )
    parent.parent.base.FINAL_RESULT = Path(
        f"results/v24894_revision_envelope_exact220_result_v1_{contract.DATE}.json"
    )
    parent.parent.base.POSTAUDIT = Path(
        f"results/v24894_revision_envelope_exact220_postresult_audit_v1_{contract.DATE}.json"
    )


def main() -> None:
    configure()
    parent.parent.base.main()


if __name__ == "__main__":
    main()
