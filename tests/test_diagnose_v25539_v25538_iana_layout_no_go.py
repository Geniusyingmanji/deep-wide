from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25539_v25538_iana_layout_no_go as target  # noqa: E402


class V25539IanaLayoutNoGoDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_aggregate_and_transfer_diagnosis_is_valid(self) -> None:
        value = target.validate_diagnosis(self.value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["diagnosis"]["mechanism_gate_passed"])
        self.assertTrue(value["content_free_aggregate_and_prior_transfer_only"])

    def test_layout_parser_repair_is_proven(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["exact_iana_url_page_tasks"], 8)
        self.assertEqual(diagnosis["iana_layout_complete_page_tasks"], 8)
        self.assertEqual(diagnosis["observation_count_total"], 16)
        self.assertTrue(diagnosis["iana_layout_parser_shape_repair_is_proven"])

    def test_materiality_not_parser_is_the_bottleneck(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["unchanged_coordinate_count_total"], 14)
        self.assertEqual(diagnosis["applied_coordinate_count_total"], 2)
        self.assertEqual(diagnosis["treatment_changed_tasks"], 2)
        self.assertTrue(
            diagnosis["observation_to_materiality_is_the_primary_bottleneck"]
        )

    def test_zero_exact220_transfer_stops_iana_population_line(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(
            diagnosis["exact220_intervention_reachable_upper_bound_tasks"], 0
        )
        self.assertTrue(diagnosis["exact220_transfer_is_provably_unreachable"])
        authorization = self.value["authorization"]
        self.assertFalse(authorization["another_iana_only_population_or_protocol"])
        self.assertFalse(authorization["v25538_quality_or_truth"])
        self.assertTrue(authorization["production_visible_generic_successor_design"])

    def test_resealed_materiality_transfer_launch_or_credit_tamper_fails(self) -> None:
        for kind in ("materiality", "transfer", "launch", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "materiality":
                changed["diagnosis"]["unchanged_coordinate_count_total"] = 13
            elif kind == "transfer":
                changed["diagnosis"][
                    "exact220_intervention_reachable_upper_bound_tasks"
                ] = 1
            elif kind == "launch":
                changed["authorization"]["deepwidebench_forward_or_evaluator"] = True
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
