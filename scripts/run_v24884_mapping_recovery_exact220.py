#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.84 exact-220 forward."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24879_mapping_recovery_effect_bundle as bundle  # noqa: E402
from deepwide_agent import v24881_mapping_recovery_subprocess_gate as gate  # noqa: E402
from deepwide_agent import v24884_mapping_recovery_exact220_contract as contract  # noqa: E402
from scripts import run_v24877_keyless_coverage_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.PREAUDIT_ROLE = "v24884_mapping_recovery_exact220_preactivation_audit"
    base.START_ROLE = "v24884_mapping_recovery_exact220_execution_start"
    base.PROGRESS_ROLE = "v24884_mapping_recovery_exact220_safe_forward_progress"
    base.SUMMARY_ROLE = "v24884_mapping_recovery_exact220_run_summary"
    base.FREEZE_ROLE = "v24884_mapping_recovery_exact220_prediction_freeze"
    base.FORWARD_ROLE = "v24884_mapping_recovery_exact220_forward_result"
    base.validate_bundle = bundle.validate_bundle
    base.validate_effect_receipt = bundle.validate_effect_receipt
    base.run_observed_bundle_subprocess = gate.run_observed_bundle_subprocess
    if (
        base.validate_bundle is not bundle.validate_bundle
        or base.validate_effect_receipt is not bundle.validate_effect_receipt
        or base.run_observed_bundle_subprocess
        is not gate.run_observed_bundle_subprocess
    ):
        raise RuntimeError("V2.48.84 static parent bindings drifted")


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
