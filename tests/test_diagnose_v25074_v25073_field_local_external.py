from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25073_field_local_external_contract as contract  # noqa: E402
from scripts import diagnose_v25074_v25073_field_local_external as target  # noqa: E402


class V25074DiagnosisTests(unittest.TestCase):
    def test_frozen_content_free_diagnosis(self) -> None:
        value = target.build_diagnosis(now=1)
        aggregate = value["aggregate"]
        runtime = value["content_free_runtime_diagnosis"]
        diagnosis = value["diagnosis"]
        self.assertEqual(aggregate["terminal_tasks"], 20)
        self.assertEqual(aggregate["verifier_exposure_tasks"], 1)
        self.assertEqual(aggregate["prediction_changed_tasks"], 3)
        self.assertEqual(runtime["query_local_mapping_failure_rows"], 28)
        self.assertEqual(runtime["terminal_hard_failure_total"], 0)
        self.assertEqual(runtime["proposal_empty_tasks"], 18)
        self.assertEqual(runtime["proposal_nonempty_tasks"], 2)
        self.assertEqual(runtime["verified_record_tasks"], 1)
        self.assertEqual(runtime["field_label_or_value_binding_rejection_tasks"], 1)
        self.assertTrue(diagnosis["proposal_reach_is_primary_observed_bottleneck"])
        self.assertFalse(value["authorization"]["v25073_evaluator_or_quality_result"])

    def test_diagnosis_binds_all_parent_artifacts(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(
            set(value["parents"]),
            {"forward_result_sha256", "forward_audit_sha256", "task_rows_sha256"},
        )
        self.assertTrue(all(len(value["parents"][name]) == 64 for name in value["parents"]))

    def test_resealed_evaluator_credit_or_counts_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("evaluator", "credit", "count", "bottleneck"):
            changed = copy.deepcopy(value)
            if kind == "evaluator":
                changed["authorization"]["v25073_evaluator_or_quality_result"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            elif kind == "count":
                changed["content_free_runtime_diagnosis"]["proposal_empty_tasks"] = 17
            else:
                changed["diagnosis"]["proposal_reach_is_primary_observed_bottleneck"] = False
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
