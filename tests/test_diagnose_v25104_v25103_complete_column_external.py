from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25103_complete_column_external_contract as contract  # noqa: E402
from scripts import diagnose_v25104_v25103_complete_column_external as target  # noqa: E402


class V25104DiagnosisTests(unittest.TestCase):
    def test_frozen_complete_column_and_attribution_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        diagnosis = value["diagnosis"]
        self.assertEqual(value["aggregate"]["terminal_tasks"], 20)
        self.assertEqual(value["aggregate"]["failure_as_zero_tasks"], 1)
        self.assertEqual(funnel["selected_page_tasks"], 15)
        self.assertEqual(funnel["complete_proposal_tasks"], 19)
        self.assertEqual(funnel["submitted_column_dispositions"], 45)
        self.assertEqual(funnel["found_column_dispositions"], 12)
        self.assertEqual(funnel["unavailable_column_dispositions"], 33)
        self.assertEqual(funnel["parent_accepted_fields"], 11)
        self.assertEqual(funnel["verifier_exposure_tasks"], 10)
        self.assertEqual(funnel["exposed_and_prediction_changed_tasks"], 2)
        self.assertEqual(funnel["exposed_and_prediction_unchanged_tasks"], 8)
        self.assertTrue(
            diagnosis["complete_column_contract_raised_exposure_from_seven_to_ten"]
        )
        self.assertFalse(value["authorization"]["v25103_evaluator_or_quality_result"])

    def test_synthetic_whitespace_reproduction_is_content_free(self) -> None:
        value = target.build_diagnosis(now=1)
        reproduction = value["synthetic_reproduction"]
        self.assertTrue(
            reproduction[
                "single_whitespace_fetch_result_reproduces_terminal_accounting_failure"
            ]
        )
        self.assertEqual(reproduction["reproduced_failure_stage"], "receipt_construction")
        self.assertTrue(reproduction["root_cause_is_whitespace_only_page_count_mismatch"])
        self.assertFalse(reproduction["network_model_search_fetch_or_evaluator_called"])

    def test_resealed_evaluator_credit_root_cause_or_funnel_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("evaluator", "credit", "root", "exposure"):
            changed = copy.deepcopy(value)
            if kind == "evaluator":
                changed["authorization"]["v25103_evaluator_or_quality_result"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            elif kind == "root":
                changed["synthetic_reproduction"][
                    "root_cause_is_whitespace_only_page_count_mismatch"
                ] = False
            else:
                changed["content_free_funnel"]["verifier_exposure_tasks"] = 11
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
