#!/usr/bin/env python3
"""Publish the V2.50.53 forward audit with persistence-order erratum."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25053_cran_unconditional_denominator_contract as contract  # noqa: E402
from scripts import audit_v25053_persisted_snapshot as persisted  # noqa: E402
from scripts import control_v25053_cran_unconditional as base  # noqa: E402


def build_forward_audit() -> dict:
    original = base.runner.validate_snapshot_rows
    try:
        base.runner.validate_snapshot_rows = persisted.validate_rows
        value = base.build_forward_audit()
    finally:
        base.runner.validate_snapshot_rows = original
    value["persistence_order_erratum"] = {
        "json_object_key_order_is_not_schema_order": True,
        "persisted_snapshot_validated_by_exact_key_sets": True,
        "prediction_snapshot_or_forward_artifact_modified": False,
        "network_model_fetch_or_evaluator_called": False,
        "failed_standard_audit_output_created": False,
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    value = build_forward_audit()
    if value.get("findings") or value.get("audit_valid") is not True:
        raise RuntimeError(value.get("findings") or "V2.50.53 erratum audit invalid")
    base._publish(contract.FORWARD_AUDIT, value)
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_AUDIT),
                "role": value["role"],
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "mechanism_gate_passed": value["mechanism_decision"][
                    "mechanism_gate_passed"
                ],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
