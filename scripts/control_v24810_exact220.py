#!/usr/bin/env python3
"""Preregister, audit, and authorize one V2.48.10 exact-220 forward."""

from __future__ import annotations

import json
import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24810_exact220_contract as contract  # noqa: E402
from scripts import control_v24807_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.RUNTIME_SOURCES = (
        contract.SOURCE,
        contract.RUNNER,
        contract.CHILD,
        Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
        Path("src/deepwide_agent/v24799_fixed_full_budget_control.py"),
        Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
        Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
        Path("scripts/run_v24807_exact220.py"),
        Path("scripts/run_v24800_exact220.py"),
        Path("scripts/run_v24635_exact220.py"),
        Path("scripts/run_v24635_exact220_task.py"),
    )
    base.TEST_SUITES = (
        (Path("tests/test_v24810_exact220.py"), 7, 240),
        *base.TEST_SUITES,
    )
    base.EXPECTED_TESTS = 64

    parent_build_preaudit = base.build_preaudit
    parent_validate_preaudit = base.validate_preaudit
    parent_build_start = base.build_start
    parent_validate_start = base.validate_start

    def project_role(value, role: str, seal_field: str):
        projected = copy.deepcopy(dict(value))
        projected["role"] = role
        projected.pop(seal_field, None)
        projected[seal_field] = contract.payload_sha256(projected)
        return projected

    def build_preaudit(*, now=None):
        return project_role(
            parent_build_preaudit(now=now),
            "v24810_exact220_preactivation_audit",
            "audit_payload_sha256",
        )

    def validate_preaudit(value):
        projected = copy.deepcopy(dict(value))
        if projected.get("role") != "v24810_exact220_preactivation_audit":
            raise RuntimeError("V2.48.10 preactivation role drifted")
        projected["role"] = "v24807_exact220_preactivation_audit"
        projected.pop("audit_payload_sha256", None)
        projected["audit_payload_sha256"] = contract.payload_sha256(projected)
        parent_validate_preaudit(projected)
        return copy.deepcopy(dict(value))

    def build_start(*, now=None):
        return project_role(
            parent_build_start(now=now),
            "v24810_exact220_execution_start",
            "execution_start_payload_sha256",
        )

    def validate_start(value):
        projected = copy.deepcopy(dict(value))
        if projected.get("role") != "v24810_exact220_execution_start":
            raise RuntimeError("V2.48.10 execution-start role drifted")
        projected["role"] = "v24807_exact220_execution_start"
        projected.pop("execution_start_payload_sha256", None)
        projected["execution_start_payload_sha256"] = contract.payload_sha256(
            projected
        )
        parent_validate_start(projected)
        return copy.deepcopy(dict(value))

    base.build_preaudit = build_preaudit
    base.validate_preaudit = validate_preaudit
    base.build_start = build_start
    base.validate_start = validate_start


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
