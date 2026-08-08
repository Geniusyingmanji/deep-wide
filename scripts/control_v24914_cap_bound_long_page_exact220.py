#!/usr/bin/env python3
"""Freeze and authorize one V2.49.14 cap-bound exact-220 run."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24914_cap_bound_long_page_exact220_contract as contract  # noqa: E402
from scripts import control_v24831_keyless_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.FETCH_SOURCE,
        contract.FETCH_HELPER,
        contract.PACKER_SOURCE,
        contract.BINDING_SOURCE,
        contract.GENERIC_CHILD,
        contract.RUNNER,
        contract.CHILD,
        Path("scripts/run_v24831_keyless_exact220.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24635_exact220_task.py"),
        Path("src/deepwide_agent/v24257_score_first_runtime.py"),
        Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
    )
    base.TEST_SUITES = (
        (contract.TEST, 10, 240),
        (contract.RECEIPT_TEST, 5, 180),
        (Path("tests/test_v24913_cap_bound_long_page_fetch.py"), 6, 180),
        (Path("tests/test_v24913_observable_long_page_packer.py"), 5, 180),
        (Path("tests/test_v24913_long_page_runtime_binding.py"), 5, 180),
        (Path("tests/test_v24911_long_page_evidence_packer.py"), 12, 180),
        (Path("tests/test_v24909_keyless_fixed_budget_exact220.py"), 8, 180),
        (Path("tests/test_v24799_fixed_full_budget_control.py"), 5, 180),
        (Path("tests/test_v24831_keyless_exact220.py"), 8, 180),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
        (Path("tests/test_v24319_runner_integration.py"), 7, 180),
        (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
    )
    base.EXPECTED_TESTS = 89


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
