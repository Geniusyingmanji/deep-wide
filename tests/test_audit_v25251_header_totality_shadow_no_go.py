from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25251_header_totality_shadow_no_go as target  # noqa: E402


class V25251HeaderTotalityShadowNoGoAuditTests(unittest.TestCase):
    def test_frozen_hashes_commit_and_parent_auditor_are_exact(self) -> None:
        self.assertTrue(target._hashes_exact())
        self.assertTrue(target._frozen_commit_boundary())
        self.assertEqual(len(target.parent.EXPECTED_FORWARD_COMMIT_PATHS), 21)

    def test_build_validates_integrity_and_preserves_mechanism_no_go(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["mechanism_gate_passed"])
        self.assertEqual(value["mechanism_failed_checks"], ["physical_effect_within_preregistered_caps"])
        self.assertFalse(value["authorization"]["independent_activation_and_quality_design"])
        self.assertTrue(value["authorization"]["content_free_successor_diagnosis_only"])

    def test_resealed_go_credit_or_integrity_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("go", "credit", "integrity"):
            changed = copy.deepcopy(value)
            if kind == "go":
                changed["mechanism_gate_passed"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                key = next(iter(changed["integrity_checks"]))
                changed["integrity_checks"][key] = False
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_source_does_not_import_or_call_evaluator(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("official_eval", source)
        self.assertNotIn("evaluate_", source)
        self.assertNotIn("import evaluation", source)


if __name__ == "__main__":
    unittest.main()
