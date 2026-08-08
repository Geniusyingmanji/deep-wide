#!/usr/bin/env python3
"""Freeze and authorize one V2.48.77 keyless coverage exact-220 run."""

from __future__ import annotations

import copy
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24877_keyless_coverage_exact220_contract as contract  # noqa: E402
from scripts import control_v24831_keyless_exact220 as base  # noqa: E402


PREAUDIT_ROLE = "v24877_keyless_coverage_exact220_preactivation_audit"
START_ROLE = "v24877_keyless_coverage_exact220_execution_start"


def _reseal(value: Mapping[str, Any], *, role: str, field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied["role"] = role
    copied.pop(field, None)
    copied[field] = contract.payload_sha256(copied)
    return copied


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.RUNNER,
        contract.CHILD,
        *contract.SEAM_SOURCES,
        Path("src/deepwide_agent/v24799_fixed_full_budget_control.py"),
        Path("src/deepwide_agent/v24859_full_evidence_coverage_revision.py"),
        Path("src/deepwide_agent/v24860_coverage_revision_integration.py"),
        Path("src/deepwide_agent/v24861_coverage_revision_exact_task.py"),
        Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
        Path("scripts/run_v24831_keyless_exact220.py"),
        Path("scripts/run_v24635_exact220.py"),
    )
    base.TEST_SUITES = (
        (contract.TEST, 11, 240),
        (Path("tests/test_v24873_keyless_fixed_coverage_runtime.py"), 5, 240),
        (Path("tests/test_v24874_keyless_coverage_bundle.py"), 10, 240),
        (Path("tests/test_v24875_keyless_coverage_child_runtime.py"), 6, 240),
        (Path("tests/test_v24876_keyless_coverage_subprocess_gate.py"), 3, 240),
        (Path("tests/test_v24859_full_evidence_coverage_revision.py"), 20, 240),
        (Path("tests/test_v24860_coverage_revision_integration.py"), 11, 240),
        (Path("tests/test_v24861_coverage_revision_exact_task.py"), 4, 240),
        (Path("tests/test_v24799_fixed_full_budget_control.py"), 5, 240),
        (Path("tests/test_v24831_keyless_exact220.py"), 8, 240),
        (Path("tests/test_v24635_exact220.py"), 10, 240),
        (Path("tests/test_v24630_thin_backfill_search.py"), 2, 240),
    )
    base.EXPECTED_TESTS = 95

    inherited_build_preaudit = base.build_preaudit
    inherited_validate_preaudit = base.validate_preaudit
    inherited_build_start = base.build_start
    inherited_validate_start = base.validate_start

    def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
        return _reseal(
            inherited_build_preaudit(now=now),
            role=PREAUDIT_ROLE,
            field="audit_payload_sha256",
        )

    def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
        projected = _reseal(
            value,
            role="v24831_keyless_exact220_preactivation_audit",
            field="audit_payload_sha256",
        )
        inherited_validate_preaudit(projected)
        copied = copy.deepcopy(dict(value))
        unsigned = dict(copied)
        seal = unsigned.pop("audit_payload_sha256", None)
        if copied.get("role") != PREAUDIT_ROLE or seal != contract.payload_sha256(unsigned):
            raise RuntimeError("V2.48.77 preactivation audit drifted")
        return copied

    base.build_preaudit = build_preaudit
    base.validate_preaudit = validate_preaudit

    def build_start(*, now: int | None = None) -> dict[str, Any]:
        return _reseal(
            inherited_build_start(now=now),
            role=START_ROLE,
            field="execution_start_payload_sha256",
        )

    def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
        projected = _reseal(
            value,
            role="v24831_keyless_exact220_execution_start",
            field="execution_start_payload_sha256",
        )
        inherited_validate_start(projected)
        copied = copy.deepcopy(dict(value))
        unsigned = dict(copied)
        seal = unsigned.pop("execution_start_payload_sha256", None)
        if copied.get("role") != START_ROLE or seal != contract.payload_sha256(unsigned):
            raise RuntimeError("V2.48.77 execution start drifted")
        return copied

    base.build_start = build_start
    base.validate_start = validate_start


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
