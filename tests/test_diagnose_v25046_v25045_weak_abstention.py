from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25046_v25045_weak_abstention as target  # noqa: E402


class V25046WeakAbstentionDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_fixed_denominator_and_no_go_are_bound(self) -> None:
        self.assertEqual(self.value["aggregate"]["tasks"], 20)
        self.assertEqual(self.value["aggregate"]["completed_tasks"], 20)
        self.assertEqual(self.value["aggregate"]["failure_as_zero_tasks"], 0)
        self.assertEqual(self.value["aggregate"]["prediction_changed_tasks"], 2)
        self.assertTrue(self.value["diagnosis"]["prompt_only_treatment_natural_exposure_below_preregistered_gate"])

    def test_changes_are_only_single_cell_abstentions(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(aggregate["row_delta_histogram"], {"0": 2})
        self.assertEqual(aggregate["column_delta_histogram"], {"0": 2})
        self.assertEqual(aggregate["changed_overlapping_cells"], 2)
        self.assertEqual(aggregate["nonunknown_to_unknown_cells"], 2)
        self.assertEqual(aggregate["unknown_to_nonunknown_cells"], 0)
        self.assertEqual(aggregate["nonunknown_to_different_nonunknown_cells"], 0)
        self.assertTrue(self.value["diagnosis"]["all_observed_changes_are_single_cell_abstentions"])

    def test_evaluator_and_benchmark_remain_unauthorized(self) -> None:
        self.assertEqual(
            self.value["authorization"],
            {
                "fresh_identity_bound_representation_gate_design": True,
                "same_population_evaluator_or_rerun": False,
                "new_deepwidebench_exact220": False,
                "leaderboard_or_sota": False,
            },
        )
        self.assertFalse(self.value["diagnosis"]["fact_correction_or_quality_gain_established"])
        self.assertFalse(self.value["diagnosis"]["entropy_or_information_gain_credit_validated"])

    def test_nested_tamper_fails_closed(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["authorization"]["new_deepwidebench_exact220"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
