#!/usr/bin/env python3
"""Freeze and authorize one V2.49.54 cold exact-220 replication."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24964_partial_signature_replication_contract as contract  # noqa: E402
from scripts import control_v24831_keyless_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.RUNNER,
        contract.CHILD,
        Path("scripts/run_v24954_partial_signature_exact220.py"),
        Path("scripts/run_v24954_partial_signature_exact220_task.py"),
        Path("src/deepwide_agent/v24949_mutual_partial_signature_ledger.py"),
        Path("src/deepwide_agent/v24945_injective_schema_signature_ledger.py"),
        Path("src/deepwide_agent/v24942_compact_schema_bound_record_ledger.py"),
        Path("src/deepwide_agent/v24939_schema_bound_record_ledger.py"),
        Path("src/deepwide_agent/v24933_contextual_record_value_projector.py"),
        Path("src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py"),
        Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"),
        Path("scripts/run_v24831_keyless_exact220.py"),
        Path("scripts/run_v24831_keyless_exact220_task.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24635_exact220_task.py"),
    )
    base.TEST_SUITES = (
        (contract.TEST, 9, 240),
        (Path("tests/test_v24954_partial_signature_exact220.py"), 13, 240),
        (Path("tests/test_v24949_mutual_partial_signature_ledger.py"), 12, 240),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
        (Path("tests/test_v24319_runner_integration.py"), 7, 180),
        (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
    )
    base.EXPECTED_TESTS = 59


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
