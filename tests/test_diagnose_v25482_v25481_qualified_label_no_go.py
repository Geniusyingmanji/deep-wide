from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25482_v25481_qualified_label_no_go as target  # noqa: E402


class V25482DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_result_is_valid_content_free_no_go(self) -> None:
        value = target.validate_diagnosis(self.value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["diagnosis"]["mechanism_gate_passed"])
        self.assertEqual(value["diagnosis"]["prediction_changed_tasks"], 1)

    def test_parser_relaxation_has_zero_counterfactual_candidate(self) -> None:
        diagnosis = self.value["diagnosis"]
        adjacent = diagnosis["adjacent_surface_counterfactual"]
        self.assertEqual(adjacent["fused_standalone_field_surface_count"], 13)
        self.assertEqual(adjacent["adjacent_evidence_closed_observation_count"], 13)
        self.assertEqual(adjacent["adjacent_counterfactual_candidate_count"], 0)
        self.assertEqual(adjacent["counterfactual_candidate_tasks"], 0)

    def test_fetch_capacity_and_next_bottleneck_are_bound(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["unused_fetch_capacity_under_existing_hard_cap"], 80)
        self.assertEqual(
            diagnosis["next_bottleneck"],
            "row_key_bound_official_detail_page_reach_before_field_parsing",
        )
        self.assertTrue(
            diagnosis[
                "next_candidate_requires_one_row_key_derived_official_detail_fetch_within_existing_cap"
            ]
        )

    def test_resealed_authorization_credit_or_count_tamper_fails(self) -> None:
        for kind in ("authorization", "credit", "count"):
            changed = copy.deepcopy(self.value)
            if kind == "authorization":
                changed["authorization"]["external_protocol_or_forward"] = True
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["diagnosis"]["unused_fetch_capacity_under_existing_hard_cap"] = 79
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
