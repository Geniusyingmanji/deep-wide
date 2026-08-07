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

from scripts import audit_v24819_quality_first_controller as target  # noqa: E402


class V24819BuildAuditTests(unittest.TestCase):
    def test_parent_authority_is_valid(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertTrue(target._parent_build_valid())

    def test_runtime_and_parent_are_label_blind(self) -> None:
        for runtime in (target.RUNTIME, target.PARENT_RUNTIME):
            accesses, imports = target.ast_findings(runtime)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])

    def test_decision_gate_enforces_quality_first_precedence(self) -> None:
        value = target._decision_gate()
        self.assertEqual(value["mandatory_high_cost_decision"], "expand")
        self.assertEqual(value["missing_calibration_decision"], "expand")
        self.assertEqual(value["drifted_calibration_decision"], "expand")
        self.assertEqual(
            value["calibrated_complete_coverage_decision"], "stop"
        )
        self.assertEqual(value["budget_blocked_decision"], "stop")
        self.assertEqual(value["unactionable_gap_decision"], "stop")
        self.assertEqual(
            value["unactionable_gap_reason"],
            "required_coverage_not_actionable",
        )
        self.assertTrue(value["all_suffix_blind"])
        self.assertTrue(value["all_entropy_shadow_only"])
        self.assertTrue(
            value[
                "quality_cost_stop_only_after_complete_coverage_and_valid_calibration"
            ]
        )

    def test_published_audit_is_valid_and_grants_no_launch(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.19 build audit has not been published")
        value = json.loads(path.read_text(encoding="utf-8"))
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["external_launch"])
        self.assertFalse(value["authorization"]["public_exact220"])

    def test_resealed_public_authority_tamper_fails(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.19 build audit has not been published")
        value = json.loads(path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(value)
        changed["authorization"]["public_exact220"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
