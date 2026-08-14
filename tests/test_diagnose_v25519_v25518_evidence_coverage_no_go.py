from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25519_v25518_evidence_coverage_no_go as target  # noqa: E402


class V25519EvidenceCoverageDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_aggregate_diagnosis_is_valid_no_go(self) -> None:
        value = target.validate_diagnosis(self.value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["diagnosis"]["mechanism_gate_passed"])
        self.assertTrue(value["content_free_aggregate_only"])

    def test_deficit_scheduler_reaches_fifteen_exact_pages(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["positive_evidence_deficit_candidate_tasks"], 15)
        self.assertEqual(diagnosis["logical_detail_request_tasks"], 15)
        self.assertEqual(diagnosis["admitted_detail_fetch_tasks"], 15)
        self.assertEqual(diagnosis["exact_nonredirected_detail_page_tasks"], 15)
        self.assertTrue(diagnosis["evidence_deficit_action_reach_is_established"])

    def test_zero_edit_bottleneck_preserves_epistemic_boundary(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["treatment_changed_tasks"], 0)
        self.assertTrue(diagnosis["material_edit_is_absent_after_exact_detail_fetch"])
        self.assertFalse(
            diagnosis[
                "current_aggregate_can_distinguish_parser_miss_from_materiality_rejection"
            ]
        )
        self.assertFalse(diagnosis["parser_miss_is_proven"])
        self.assertFalse(
            diagnosis[
                "unchanged_surface_equivalent_conflict_or_list_rejection_is_proven"
            ]
        )

    def test_only_build_only_instrumentation_and_parser_design_are_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["content_free_stage_instrumentation_successor_build"]
        )
        self.assertTrue(
            authorization["source_bound_multirow_iana_parser_successor_build"]
        )
        self.assertFalse(authorization["external_protocol_or_forward"])
        self.assertFalse(authorization["postfreeze_quality_or_truth"])
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_resealed_epistemic_launch_or_credit_tamper_fails(self) -> None:
        for kind in ("epistemic", "launch", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "epistemic":
                changed["diagnosis"]["parser_miss_is_proven"] = True
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
