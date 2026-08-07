from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24798_exact220_postresult as target  # noqa: E402


class V24798PostresultDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_exact220_transport_and_quality_are_bound(self) -> None:
        self.assertTrue(self.value["diagnosis_valid"])
        self.assertEqual(self.value["overall"]["current"]["whole_table_successes"], 6)
        self.assertEqual(self.value["overall"]["model_generated_tables"], 220)
        self.assertEqual(self.value["overall"]["fallback_tables"], 0)
        self.assertEqual(self.value["transport"]["provider_attempts"], 533)
        self.assertEqual(self.value["transport"]["status_2xx"], 533)
        self.assertEqual(self.value["transport"]["transport_failures"], 0)

    def test_controller_projection_exposes_zero_row_target_and_early_stop(self) -> None:
        controller = self.value["controller"]
        self.assertEqual(controller["explicit_row_target_histogram"], {"0": 220})
        self.assertEqual(controller["reason_counts"]["first_wave_sufficient"], 192)
        self.assertEqual(controller["decision_groups"]["expand"]["tasks"], 26)
        self.assertEqual(controller["decision_groups"]["stop"]["tasks"], 194)

    def test_row_f1_drops_while_other_quality_axes_improve(self) -> None:
        delta = self.value["overall"]["paired_delta_from_v24635"]
        self.assertGreater(delta["entity_acc"], 0)
        self.assertLess(delta["f1_by_row"], 0)
        self.assertGreater(delta["f1_by_item"], 0)
        self.assertGreater(delta["column_f1"], 0)
        self.assertGreater(delta["quality_composite"], 0)

    def test_evaluator_failures_are_conservative_and_complete(self) -> None:
        evaluator = self.value["evaluator"]
        self.assertEqual(evaluator["valid"], 209)
        self.assertEqual(evaluator["invalid_failure_as_zero"], 11)
        self.assertEqual(evaluator["error_taxonomy"], {"internal_error": 9, "out_of_range_metric": 2})
        self.assertFalse(evaluator["selective_retry_or_revaluation"])

    def test_diagnosis_is_noncausal_and_authorizes_only_synthetic_design(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertFalse(diagnosis["current_dominant_quality_failure_is_proven_causal"])
        self.assertFalse(diagnosis["controller_decision_group_comparison_is_randomized_or_causal"])
        self.assertTrue(diagnosis["full_budget_no_entropy_comparator_is_required_before_claiming_entropy_value"])
        self.assertEqual(
            self.value["authorization"],
            {
                "synthetic_full_budget_control_design": True,
                "new_exact220_launch": False,
                "evaluator": False,
                "retry_resume_or_selective_rerun": False,
                "leaderboard_or_sota": False,
            },
        )

    def test_tamper_fails_closed(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["authorization"]["new_exact220_launch"] = True
        unsigned = dict(altered)
        unsigned.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = target.contract.payload_sha256(unsigned)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(altered)


if __name__ == "__main__":
    unittest.main()
