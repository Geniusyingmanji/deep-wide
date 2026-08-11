from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25053_cran_unconditional_denominator_contract as contract  # noqa: E402
from scripts import audit_v25053_forward_erratum as audit  # noqa: E402
from scripts import audit_v25053_persisted_snapshot as persisted  # noqa: E402


class V25053ForwardErratumTests(unittest.TestCase):
    def test_actual_sorted_snapshot_is_order_independent_and_exact(self) -> None:
        rows = [
            json.loads(line)
            for line in (ROOT / contract.PUBLIC_SNAPSHOT).read_text(
                encoding="utf-8"
            ).splitlines()
        ]
        checked = persisted.validate_rows(rows)
        self.assertEqual(len(checked), 20)
        self.assertEqual(sum(row["preparation_ready"] for row in checked), 18)
        changed = copy.deepcopy(rows)
        changed[0]["record"]["extra"] = "forbidden"
        with self.assertRaises(RuntimeError):
            persisted.validate_rows(changed)

    def test_erratum_audit_is_read_only_and_keeps_mechanism_no_go(self) -> None:
        value = audit.build_forward_audit()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["mechanism_decision"]["mechanism_gate_passed"])
        self.assertEqual(
            value["mechanism_decision"]["failed_checks"],
            ["minimum_prediction_change"],
        )
        self.assertFalse(
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
