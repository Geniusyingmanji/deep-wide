from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25083_visible_identity_external_contract as contract  # noqa: E402
from scripts import diagnose_v25084_v25083_visible_identity_external as target  # noqa: E402


class V25084DiagnosisTests(unittest.TestCase):
    def test_frozen_content_free_identity_proposal_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_identity_proposal_funnel"]
        diagnosis = value["diagnosis"]
        self.assertEqual(value["aggregate"]["terminal_tasks"], 20)
        self.assertEqual(value["aggregate"]["verifier_exposure_tasks"], 0)
        self.assertEqual(value["aggregate"]["prediction_changed_tasks"], 1)
        self.assertEqual(funnel["visible_identity_tasks"], 20)
        self.assertEqual(funnel["unique_identity_bound_page_tasks"], 9)
        self.assertEqual(funnel["ambiguous_multi_joint_page_tasks"], 3)
        self.assertEqual(funnel["zero_joint_page_tasks"], 8)
        self.assertEqual(funnel["proposal_nonempty_tasks"], 8)
        self.assertEqual(funnel["parsed_records"], 8)
        self.assertEqual(funnel["parsed_fields"], 11)
        self.assertEqual(funnel["field_label_or_value_binding_rejections"], 8)
        self.assertEqual(funnel["verified_records"], 0)
        self.assertTrue(diagnosis["observed_bottleneck_moved_to_atomic_field_disposition"])
        self.assertTrue(diagnosis["aggregate_rejection_does_not_prove_any_individual_field_was_valid"])
        self.assertFalse(value["authorization"]["v25083_evaluator_or_quality_result"])

    def test_parent_hashes_are_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(
            set(value["parents"]),
            {"forward_result_sha256", "forward_audit_sha256", "task_rows_sha256"},
        )
        self.assertTrue(all(len(value["parents"][name]) == 64 for name in value["parents"]))

    def test_resealed_evaluator_credit_or_funnel_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("evaluator", "credit", "unique", "nonempty"):
            changed = copy.deepcopy(value)
            if kind == "evaluator":
                changed["authorization"]["v25083_evaluator_or_quality_result"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            elif kind == "unique":
                changed["content_free_identity_proposal_funnel"]["unique_identity_bound_page_tasks"] = 8
            else:
                changed["content_free_identity_proposal_funnel"]["proposal_nonempty_tasks"] = 7
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
