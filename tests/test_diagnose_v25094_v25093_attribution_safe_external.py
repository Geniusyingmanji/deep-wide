from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25093_attribution_safe_external_contract as contract  # noqa: E402
from scripts import diagnose_v25094_v25093_attribution_safe_external as target  # noqa: E402


class V25094DiagnosisTests(unittest.TestCase):
    def test_frozen_content_free_authority_attribution_and_field_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        diagnosis = value["diagnosis"]
        self.assertEqual(value["aggregate"]["terminal_tasks"], 20)
        self.assertEqual(value["aggregate"]["failure_as_zero_tasks"], 1)
        self.assertEqual(funnel["selected_page_tasks"], 16)
        self.assertEqual(funnel["authority_tiebreak_eligible_tasks"], 5)
        self.assertEqual(funnel["authority_tiebreak_selected_tasks"], 5)
        self.assertEqual(funnel["parsed_fields"], 15)
        self.assertEqual(funnel["field_accepted_count"], 1)
        self.assertEqual(funnel["field_label_or_value_binding_rejections"], 12)
        self.assertEqual(funnel["field_page_reference_rejections"], 2)
        self.assertEqual(funnel["exposed_and_prediction_changed_tasks"], 1)
        self.assertEqual(funnel["unexposed_and_prediction_changed_tasks"], 0)
        self.assertEqual(funnel["prediction_identity_handoff_tasks"], 18)
        self.assertTrue(diagnosis["field_binding_is_dominant_post_selection_bottleneck"])
        self.assertTrue(diagnosis["outer_value_error_stage_is_not_attributable_from_frozen_content_free_row"])
        self.assertFalse(value["authorization"]["v25093_evaluator_or_quality_result"])

    def test_parent_hashes_are_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(
            set(value["parents"]),
            {"forward_result_sha256", "forward_audit_sha256", "task_rows_sha256"},
        )
        self.assertTrue(all(len(value["parents"][name]) == 64 for name in value["parents"]))

    def test_resealed_evaluator_credit_failure_or_funnel_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("evaluator", "credit", "failure", "binding"):
            changed = copy.deepcopy(value)
            if kind == "evaluator":
                changed["authorization"]["v25093_evaluator_or_quality_result"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            elif kind == "failure":
                changed["diagnosis"]["outer_value_error_stage_is_not_attributable_from_frozen_content_free_row"] = False
            else:
                changed["content_free_funnel"]["field_label_or_value_binding_rejections"] = 11
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
