from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25526_v25525_parser_shape_no_go as target  # noqa: E402


class V25526ParserShapeDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_aggregate_diagnosis_is_valid_no_go(self) -> None:
        value = target.validate_diagnosis(self.value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["diagnosis"]["mechanism_gate_passed"])
        self.assertTrue(value["content_free_aggregate_only"])

    def test_exact_iana_url_row_and_surface_binding_reaches_eight(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["exact_nonredirected_detail_page_tasks"], 16)
        self.assertEqual(diagnosis["exact_iana_url_page_tasks"], 8)
        self.assertEqual(diagnosis["url_row_key_bound_page_tasks"], 8)
        self.assertEqual(diagnosis["identity_surface_bound_page_tasks"], 8)
        self.assertTrue(
            diagnosis["exact_iana_url_row_and_surface_binding_is_established"]
        )

    def test_zero_raw_surface_proves_parser_shape_miss_before_materiality(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["raw_field_surface_tasks"], 0)
        self.assertEqual(diagnosis["evidence_closed_observation_tasks"], 0)
        self.assertEqual(diagnosis["material_candidate_tasks"], 0)
        self.assertEqual(diagnosis["treatment_changed_tasks"], 0)
        self.assertTrue(diagnosis["field_parser_shape_miss_is_proven"])
        self.assertTrue(diagnosis["materiality_filter_is_not_reached"])

    def test_only_independent_shape_study_and_pure_parser_build_are_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["independent_public_iana_page_shape_study"])
        self.assertTrue(authorization["pure_mechanical_field_parser_successor_build"])
        self.assertFalse(
            authorization["open_v25525_task_rows_pages_predictions_or_truth_for_tuning"]
        )
        self.assertFalse(authorization["external_protocol_or_forward"])
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_resealed_parser_launch_or_credit_tamper_fails(self) -> None:
        for kind in ("parser", "launch", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "parser":
                changed["diagnosis"]["raw_field_surface_tasks"] = 1
            elif kind == "launch":
                changed["authorization"]["external_protocol_or_forward"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
