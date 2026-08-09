#!/usr/bin/env python3
"""Audit V2.50.23 exposure and fail closed before any exact-220 effect."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25023_distinct_coverage_exact220_contract as contract  # noqa: E402
from scripts import control_v24800_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.RUNNER,
        contract.CHILD,
        contract.SELECTION_SOURCE,
        contract.RETRIEVAL_SOURCE,
        contract.SEARCH_SOURCE,
        contract.TASK_INTEGRATION_SOURCE,
        contract.PROJECTOR_SOURCE,
        contract.SELECTOR_PARENT_SOURCE,
        contract.FETCH_SOURCE,
        contract.FETCH_PARENT_SOURCE,
        contract.FETCH_HELPER,
        Path("scripts/run_v24857_pacing_aware_exact220.py"),
        contract.TRANSPORT_SOURCE,
        contract.ADMISSION_SOURCE,
        Path("scripts/run_v24800_exact220.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24635_exact220_task.py"),
        Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
        Path("src/deepwide_agent/v24799_fixed_full_budget_control.py"),
        Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
        Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
        Path("src/deepwide_agent/v24273_two_wave_task_runtime.py"),
    )
    base.TEST_SUITES = (
        (contract.TEST, 13, 240),
        (Path("tests/test_v25019_production_distinct_coverage_selection.py"), 6, 240),
        (Path("tests/test_v25020_pacing_distinct_coverage_retrieval.py"), 5, 240),
        (Path("tests/test_v25021_rate_aware_multi_identity_search.py"), 3, 240),
        (Path("tests/test_v25022_production_distinct_coverage_task.py"), 4, 240),
        (Path("tests/test_v25014_multi_identity_detail_fields.py"), 9, 240),
        (Path("tests/test_v25015_distinct_identity_child_selection.py"), 11, 240),
        (Path("tests/test_v25016_multi_identity_detail_fetch.py"), 5, 240),
        (Path("tests/test_v24857_pacing_aware_exact220.py"), 13, 240),
        (Path("tests/test_v24856_pacing_aware_admission.py"), 7, 240),
        (Path("tests/test_v24854_rate_aware_exact220.py"), 11, 240),
        (Path("tests/test_v24852_rate_aware_tavily_search.py"), 11, 240),
        (Path("tests/test_v24800_exact220.py"), 12, 240),
        (Path("tests/test_v24799_fixed_full_budget_control.py"), 5, 240),
        (Path("tests/test_v24796_deadline_tavily_search.py"), 6, 240),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
        (Path("tests/test_v24630_thin_backfill_search.py"), 2, 180),
        (Path("tests/test_v24319_runner_integration.py"), 7, 180),
        (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
    )
    base.EXPECTED_TESTS = 148


def _require_exposure_go() -> None:
    path = ROOT / contract.EXPOSURE_AUDIT
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.50.23 exposure audit is absent")
    value = contract.validate_exposure_audit(ROOT, base._read(path))
    if value["passed"] is not True:
        raise RuntimeError("V2.50.23 protocol blocked by zero natural mechanism exposure")


def main() -> None:
    configure()
    if len(sys.argv) == 2 and sys.argv[1] == "exposure":
        value = contract.build_exposure_audit(ROOT, now=int(time.time()))
        base.publish_new(ROOT / contract.EXPOSURE_AUDIT, value)
        print(
            json.dumps(
                {
                    "path": str(contract.EXPOSURE_AUDIT),
                    "status": value["status"],
                    "passed": value["passed"],
                    "strict_multi_identity_task_count": value["exposure"][
                        "strict_multi_identity_task_count"
                    ],
                },
                sort_keys=True,
            )
        )
        return
    _require_exposure_go()
    base.main()


if __name__ == "__main__":
    main()
