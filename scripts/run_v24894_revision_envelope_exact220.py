#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.94 exact-220 forward."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24890_revision_envelope_mapping_bundle as bundle  # noqa: E402
from deepwide_agent import v24892_revision_envelope_subprocess_gate as gate  # noqa: E402
from deepwide_agent import v24894_revision_envelope_exact220_contract as contract  # noqa: E402
from scripts import run_v24884_mapping_recovery_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.base.contract = contract
    parent.base.PREAUDIT_ROLE = "v24894_revision_envelope_exact220_preactivation_audit"
    parent.base.START_ROLE = "v24894_revision_envelope_exact220_execution_start"
    parent.base.PROGRESS_ROLE = "v24894_revision_envelope_exact220_safe_forward_progress"
    parent.base.SUMMARY_ROLE = "v24894_revision_envelope_exact220_run_summary"
    parent.base.FREEZE_ROLE = "v24894_revision_envelope_exact220_prediction_freeze"
    parent.base.FORWARD_ROLE = "v24894_revision_envelope_exact220_forward_result"
    parent.base.validate_bundle = bundle.validate_bundle
    parent.base.validate_effect_receipt = bundle.validate_effect_receipt
    parent.base.run_observed_bundle_subprocess = gate.run_observed_bundle_subprocess


def main() -> None:
    configure()
    parent.base.main()


if __name__ == "__main__":
    main()
