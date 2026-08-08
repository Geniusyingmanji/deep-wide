#!/usr/bin/env python3
"""Freeze and authorize V2.48.84 mapping-recovery exact-220 artifacts."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24884_mapping_recovery_exact220_contract as contract  # noqa: E402
from scripts import control_v24877_keyless_coverage_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.PREAUDIT_ROLE = "v24884_mapping_recovery_exact220_preactivation_audit"
    parent.START_ROLE = "v24884_mapping_recovery_exact220_execution_start"
    parent.configure()
    parent.base.RUNTIME_SOURCES = tuple(
        dict.fromkeys(
            (
                *parent.base.RUNTIME_SOURCES,
                Path("src/deepwide_agent/v24878_keyless_coverage_exact220_contract.py"),
                Path("scripts/run_v24877_keyless_coverage_exact220.py"),
                Path("scripts/run_v24877_keyless_coverage_exact220_task.py"),
                *contract.CORRECTED_SOURCES,
            )
        )
    )
    parent.base.TEST_SUITES = (
        (contract.TEST, 15, 240),
        (Path("tests/test_v24879_mapping_recovery_effect_bundle.py"), 15, 240),
        (Path("tests/test_v24880_mapping_recovery_child_runtime.py"), 2, 240),
        (Path("tests/test_v24881_mapping_recovery_subprocess_gate.py"), 2, 240),
        (Path("tests/test_v24882_mapping_recovery_stage_runtime.py"), 10, 240),
        (Path("tests/test_v24878_keyless_coverage_exact220.py"), 10, 240),
        (Path("tests/test_v24878_keyless_coverage_runner_fix.py"), 3, 240),
        *parent.base.TEST_SUITES[1:],
    )
    parent.base.EXPECTED_TESTS = 141


def main() -> None:
    configure()
    parent.base.main()


if __name__ == "__main__":
    main()
