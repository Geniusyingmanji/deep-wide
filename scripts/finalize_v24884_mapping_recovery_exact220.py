#!/usr/bin/env python3
"""Post-freeze evaluator namespace for V2.48.84 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24884_mapping_recovery_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24877_keyless_coverage_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.FORWARD_ROLE = "v24884_mapping_recovery_exact220_forward_result"
    parent.SUMMARY_ROLE = "v24884_mapping_recovery_exact220_run_summary"
    parent.FREEZE_ROLE = "v24884_mapping_recovery_exact220_prediction_freeze"
    parent.configure()
    parent.base.EVALUATOR_PROTOCOL = Path(
        f"results/v24884_mapping_recovery_exact220_evaluator_preregistration_v1_{contract.DATE}.json"
    )
    parent.base.FINAL_RESULT = Path(
        f"results/v24884_mapping_recovery_exact220_result_v1_{contract.DATE}.json"
    )
    parent.base.POSTAUDIT = Path(
        f"results/v24884_mapping_recovery_exact220_postresult_audit_v1_{contract.DATE}.json"
    )
    parent.base.CONTROL_FILES = (
        "scripts/finalize_v24884_mapping_recovery_exact220.py",
        "scripts/finalize_v24877_keyless_coverage_exact220.py",
        "scripts/finalize_v24791_exact220.py",
        "scripts/run_official_eval_local.py",
        "scripts/finalize_v24287_exact220.py",
        "scripts/finalize_fullset_rollout.py",
        "scripts/deepwide_api_lease.py",
        "tests/test_v24884_mapping_recovery_exact220.py",
    )
    parent.base.REFERENCES = {
        **parent.base.REFERENCES,
        "v24878": Path(
            "results/v24878_keyless_coverage_exact220_result_v1_20260808.json"
        ),
    }


def main() -> None:
    configure()
    parent.base.main()


if __name__ == "__main__":
    main()
