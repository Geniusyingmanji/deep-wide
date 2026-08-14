from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25470_v25469_row_key_source_no_observation as target  # noqa: E402


class V25470DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_result_is_valid_content_free_no_go(self) -> None:
        value = target.validate_diagnosis(self.value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["diagnosis"]["mechanism_gate_passed"])
        self.assertEqual(value["diagnosis"]["prediction_changed_tasks"], 0)

    def test_page_binding_is_nonzero_but_all_structured_surfaces_are_zero(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["accepted_unique_identity_page_tasks"], 16)
        self.assertEqual(diagnosis["accepted_unique_identity_page_count_total"], 30)
        self.assertTrue(all(amount == 0 for amount in diagnosis["structured_surface_counts"].values()))
        self.assertGreater(diagnosis["surface_shape_counts"]["requested_field_token_lines"], 0)

    def test_resealed_authorization_or_credit_tamper_fails(self) -> None:
        for kind in ("authorization", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "authorization":
                changed["authorization"]["external_protocol_or_forward"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_diagnosis_authorizes_build_design_only(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["generic_source_label_alignment_build_design"])
        self.assertFalse(authorization["external_protocol_or_forward"])
        self.assertFalse(authorization["postfreeze_quality_or_truth"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])


if __name__ == "__main__":
    unittest.main()
