from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25125_visible_query_recovery_external_contract as contract  # noqa: E402
from scripts import diagnose_v25126_v25125_recovery_mechanism as target  # noqa: E402


class V25126RecoveryMechanismDiagnosisTests(unittest.TestCase):
    def test_frozen_content_free_causal_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        diagnosis = value["diagnosis"]
        self.assertEqual(funnel["completed_runtime_tasks"], 20)
        self.assertEqual(funnel["grounded_plan_strict_valid_tasks"], 10)
        self.assertEqual(funnel["grounded_plan_strategy_applied_tasks"], 8)
        self.assertEqual(funnel["positive_target_field_page_gain_tasks"], 6)
        self.assertEqual(funnel["prediction_changed_tasks"], 5)
        self.assertEqual(funnel["unattributable_prediction_changed_tasks"], 4)
        self.assertEqual(funnel["attributable_prediction_changed_tasks"], 1)
        self.assertEqual(
            funnel["prediction_unchanged_despite_positive_field_page_gain_tasks"], 5
        )
        self.assertTrue(
            diagnosis[
                "independent_synthesis_sampling_creates_unattributable_differences"
            ]
        )
        self.assertTrue(
            diagnosis["most_positive_retrieval_gains_do_not_change_prediction"]
        )
        self.assertFalse(value["authorization"]["v25125_evaluator_or_quality_result"])

    def test_parent_hashes_are_exactly_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(value["parents"], target.EXPECTED_HASHES)

    def test_resealed_evaluator_credit_or_funnel_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("evaluator", "credit", "funnel"):
            changed = copy.deepcopy(value)
            if kind == "evaluator":
                changed["authorization"]["v25125_evaluator_or_quality_result"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            else:
                changed["content_free_funnel"]["unattributable_prediction_changed_tasks"] = 3
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
