from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25505_v25504_generic_materiality_no_go as target  # noqa: E402


class V25505GenericMaterialityDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_aggregate_diagnosis_is_valid_no_go(self) -> None:
        value = target.validate_diagnosis(self.value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["diagnosis"]["mechanism_gate_passed"])
        self.assertTrue(value["content_free_aggregate_only"])

    def test_parser_engages_but_material_edits_are_sparse(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["generic_mechanical_field_surface_tasks"], 10)
        self.assertEqual(diagnosis["generic_mechanical_observation_tasks"], 10)
        self.assertEqual(diagnosis["available_candidate_tasks"], 1)
        self.assertEqual(diagnosis["prediction_changed_tasks"], 1)
        self.assertTrue(
            diagnosis["parser_engagement_is_no_longer_the_primary_bottleneck"]
        )

    def test_runtime_failure_budget_and_capacity_are_not_observed_cause(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertTrue(
            diagnosis["runtime_failure_budget_or_capacity_is_not_the_observed_cause"]
        )
        self.assertEqual(diagnosis["completed_runtime_tasks"], 20)
        self.assertEqual(diagnosis["combined_candidate_page_tasks"], 20)

    def test_only_upstream_successor_design_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization[
                "upstream_evidence_selection_or_synthesis_coverage_successor_design"
            ]
        )
        self.assertFalse(
            authorization["relax_materiality_or_unique_coordinate_rules"]
        )
        self.assertFalse(authorization["external_protocol_or_forward"])
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_resealed_materiality_launch_or_credit_tamper_fails(self) -> None:
        for kind in ("materiality", "launch", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "materiality":
                changed["diagnosis"]["available_candidate_tasks"] = 2
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
