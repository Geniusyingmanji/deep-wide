from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25088_partial_field_external_contract as contract  # noqa: E402
from scripts import diagnose_v25089_v25088_partial_field_external as target  # noqa: E402


class V25089DiagnosisTests(unittest.TestCase):
    def test_frozen_content_free_attribution_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        diagnosis = value["diagnosis"]
        self.assertEqual(value["aggregate"]["terminal_tasks"], 20)
        self.assertEqual(value["aggregate"]["verifier_exposure_tasks"], 4)
        self.assertEqual(value["aggregate"]["prediction_changed_tasks"], 4)
        self.assertEqual(funnel["unique_identity_bound_page_tasks"], 8)
        self.assertEqual(funnel["ambiguous_multi_joint_page_tasks"], 9)
        self.assertEqual(funnel["zero_joint_page_tasks"], 3)
        self.assertEqual(funnel["parsed_fields"], 14)
        self.assertEqual(funnel["field_accepted_count"], 4)
        self.assertEqual(funnel["field_label_or_value_binding_rejections"], 10)
        self.assertEqual(funnel["mixed_accepted_and_rejected_field_tasks"], 4)
        self.assertEqual(funnel["exposed_and_prediction_changed_tasks"], 0)
        self.assertEqual(funnel["unexposed_and_prediction_changed_tasks"], 4)
        self.assertTrue(diagnosis["future_gate_must_require_exposure_prediction_change_intersection"])
        self.assertTrue(diagnosis["future_runtime_must_identity_handoff_when_candidate_evidence_is_unchanged"])
        self.assertFalse(value["authorization"]["v25088_evaluator_or_quality_result"])

    def test_parent_hashes_are_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(
            set(value["parents"]),
            {"forward_result_sha256", "forward_audit_sha256", "task_rows_sha256"},
        )
        self.assertTrue(all(len(value["parents"][name]) == 64 for name in value["parents"]))

    def test_resealed_evaluator_credit_attribution_or_funnel_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("evaluator", "credit", "attribution", "accepted"):
            changed = copy.deepcopy(value)
            if kind == "evaluator":
                changed["authorization"]["v25088_evaluator_or_quality_result"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            elif kind == "attribution":
                changed["content_free_funnel"]["exposed_and_prediction_changed_tasks"] = 1
            else:
                changed["content_free_funnel"]["field_accepted_count"] = 5
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
