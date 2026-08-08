#!/usr/bin/env python3
"""Freeze and authorize one V2.48.66 coverage-revision exact-220."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24866_coverage_revision_exact220_contract as contract  # noqa: E402
from scripts import control_v24800_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.RUNNER,
        contract.CHILD,
        *contract.COVERAGE_SOURCES,
        Path("src/deepwide_agent/v24852_rate_aware_tavily_search.py"),
        Path("src/deepwide_agent/v24856_pacing_aware_admission.py"),
        Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
        Path("src/deepwide_agent/v24273_two_wave_task_runtime.py"),
        Path("src/deepwide_agent/v24318_deadline_conservation_runtime.py"),
        Path("src/deepwide_agent/v24319_runner_integration.py"),
        Path("src/deepwide_agent/v24630_exact220_task_integration.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24800_exact220.py"),
    )
    base.TEST_SUITES = (
        (contract.TEST, 10, 300),
        (Path("tests/test_v24859_full_evidence_coverage_revision.py"), 20, 240),
        (Path("tests/test_v24860_coverage_revision_integration.py"), 11, 240),
        (Path("tests/test_v24861_coverage_revision_exact_task.py"), 4, 240),
        (Path("tests/test_v24862_same_task_coverage_runtime.py"), 5, 240),
        (Path("tests/test_v24863_coverage_revision_child_bundle.py"), 4, 240),
        (Path("tests/test_v24864_coverage_revision_child_runtime.py"), 3, 240),
        (Path("tests/test_v24865_coverage_revision_subprocess_gate.py"), 4, 240),
        (Path("tests/test_v24857_pacing_aware_exact220.py"), 13, 240),
        (Path("tests/test_v24856_pacing_aware_admission.py"), 7, 240),
        (Path("tests/test_v24854_rate_aware_exact220.py"), 11, 240),
        (Path("tests/test_v24852_rate_aware_tavily_search.py"), 11, 240),
        (Path("tests/test_v24800_exact220.py"), 12, 240),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
    )
    base.EXPECTED_TESTS = sum(item[1] for item in base.TEST_SUITES)


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
