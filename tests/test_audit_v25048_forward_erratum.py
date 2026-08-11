from __future__ import annotations

import sys
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25048_atomic_pypi_representation_contract as contract  # noqa: E402
from scripts import audit_v25048_forward_erratum as target  # noqa: E402


class V25048ForwardErratumAuditTests(unittest.TestCase):
    def test_actual_frozen_forward_validates_without_effects(self) -> None:
        value = json.loads(
            (ROOT / contract.FORWARD_AUDIT).read_text(encoding="utf-8")
        )
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["mechanism_decision"]["mechanism_gate_passed"])
        self.assertTrue(
            value["authorization"][
                "postfreeze_external_evaluator_implementation_and_protocol"
            ]
        )
        self.assertFalse(
            value["persistence_order_erratum"][
                "prediction_snapshot_or_forward_artifact_modified"
            ]
        )
        self.assertTrue(contract.sealed(value, "audit_payload_sha256"))


if __name__ == "__main__":
    unittest.main()
