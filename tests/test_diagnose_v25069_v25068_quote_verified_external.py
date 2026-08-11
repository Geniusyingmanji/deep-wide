from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25069_v25068_quote_verified_external as target  # noqa: E402


class V25069DiagnosisTests(unittest.TestCase):
    def test_frozen_content_free_diagnosis(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(value["aggregate"]["terminal_tasks"], 20)
        self.assertEqual(value["aggregate"]["verifier_exposure_tasks"], 0)
        self.assertEqual(value["aggregate"]["prediction_changed_tasks"], 2)
        self.assertTrue(value["diagnosis"]["current_single_quote_all_fields_contract_has_no_natural_reach"])
        self.assertFalse(value["authorization"]["v25068_evaluator_or_quality_result"])

    def test_diagnosis_binds_all_parent_artifacts(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(
            set(value["parents"]),
            {"forward_result_sha256", "forward_audit_sha256", "task_rows_sha256"},
        )
        self.assertTrue(all(len(value["parents"][name]) == 64 for name in value["parents"]))

    def test_resealed_evaluator_or_entropy_credit_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("evaluator", "credit", "reach"):
            changed = copy.deepcopy(value)
            if kind == "evaluator":
                changed["authorization"]["v25068_evaluator_or_quality_result"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            else:
                changed["diagnosis"]["current_single_quote_all_fields_contract_has_no_natural_reach"] = False
            changed.pop("diagnosis_payload_sha256")
            from deepwide_agent import v25068_quote_verified_external_contract as contract

            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
