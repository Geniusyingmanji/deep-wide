#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.10 exact-220 forward."""

from __future__ import annotations

import sys
import copy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24810_exact220_contract as contract  # noqa: E402
from scripts import run_v24807_exact220 as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    parent_validate = base.validate_execution_start

    def validate_execution_start(root: Path, protocol: dict) -> dict:
        audit = base._read(root / contract.PREAUDIT)
        start = base._read(root / contract.EXECUTION_START)
        if (
            audit.get("role") != "v24810_exact220_preactivation_audit"
            or start.get("role") != "v24810_exact220_execution_start"
        ):
            raise RuntimeError("V2.48.10 execution authorization drifted")
        projected_audit = copy.deepcopy(audit)
        projected_audit["role"] = "v24807_exact220_preactivation_audit"
        projected_audit.pop("audit_payload_sha256", None)
        projected_audit["audit_payload_sha256"] = contract.payload_sha256(
            projected_audit
        )
        projected_start = copy.deepcopy(start)
        projected_start["role"] = "v24807_exact220_execution_start"
        projected_start.pop("execution_start_payload_sha256", None)
        projected_start["execution_start_payload_sha256"] = contract.payload_sha256(
            projected_start
        )
        original_read = base._read

        def projected_read(path: Path) -> dict:
            if path == root / contract.PREAUDIT:
                return projected_audit
            if path == root / contract.EXECUTION_START:
                return projected_start
            return original_read(path)

        base._read = projected_read
        try:
            parent_validate(root, protocol)
        finally:
            base._read = original_read
        return start

    base.validate_execution_start = validate_execution_start


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
