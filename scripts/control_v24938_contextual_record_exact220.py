#!/usr/bin/env python3
"""Freeze and authorize one exploratory V2.49.38 exact-220 run."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24938_contextual_record_exact220_contract as contract  # noqa: E402
from scripts import control_v24831_keyless_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.RUNNER,
        contract.CHILD,
        contract.PROJECTOR_SOURCE,
        Path("src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py"),
        Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"),
        Path("src/deepwide_agent/v24842_atomic_table_header_closure.py"),
        Path("src/deepwide_agent/v24839_structure_preserving_projector.py"),
        Path("scripts/run_v24831_keyless_exact220.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24635_exact220_task.py"),
    )
    base.TEST_SUITES = (
        (contract.TEST, 11, 240),
        (Path("tests/test_v24933_contextual_record_value_projector.py"), 10, 240),
        (Path("tests/test_v24935_unicode_total_replication.py"), 9, 240),
        (Path("tests/test_v24932_unicode_total_exact220.py"), 11, 240),
        (Path("tests/test_v24928_unicode_total_visible_row_compactor.py"), 12, 240),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
        (Path("tests/test_v24319_runner_integration.py"), 7, 180),
        (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
    )
    base.EXPECTED_TESTS = 78


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
