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

from scripts import audit_v24804_shared_prefix_budget_ladder as target  # noqa: E402


class V24804BuildAuditTests(unittest.TestCase):
    def test_runtime_ast_is_label_blind(self) -> None:
        accesses, imports = target.ast_findings(target.RUNTIME)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

    def test_synthetic_decision_gate_has_expand_stop_and_fail_closed(self) -> None:
        value = target._synthetic_decision_gate()
        self.assertEqual(value["expand_decision"], "expand")
        self.assertEqual(value["stop_decision"], "stop")
        self.assertEqual(value["calibration_incomplete_decision"], "stop")
        self.assertTrue(value["entropy_feature_value_zero"])
        self.assertTrue(value["entropy_assigns_signed_credit_false"])
        self.assertTrue(value["wave_two_response_read_false"])

    def test_published_audit_is_valid_and_grants_no_launch(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.04 build audit has not been published")
        value = json.loads(path.read_text(encoding="utf-8"))
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["external_launch"])
        self.assertFalse(value["authorization"]["public_exact220"])

    def test_resealed_authority_tamper_fails(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.04 build audit has not been published")
        value = json.loads(path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(value)
        changed["authorization"]["public_exact220"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
