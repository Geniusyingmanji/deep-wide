from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25512_v25511_literal_unknown_no_go as target  # noqa: E402


class V25512LiteralUnknownDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_aggregate_diagnosis_is_valid_no_go(self) -> None:
        value = target.validate_diagnosis(self.value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["diagnosis"]["mechanism_gate_passed"])
        self.assertTrue(value["content_free_aggregate_only"])

    def test_links_exist_but_literal_unknown_suppresses_all_actions(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["multirow_eligible_link_tasks"], 6)
        self.assertEqual(diagnosis["eligible_unique_link_count_total"], 19)
        self.assertEqual(diagnosis["positive_uncertainty_candidate_tasks"], 0)
        self.assertEqual(diagnosis["logical_detail_request_tasks"], 0)
        self.assertEqual(diagnosis["treatment_changed_tasks"], 0)
        self.assertTrue(
            diagnosis[
                "literal_unknown_is_not_a_reliable_epistemic_uncertainty_proxy"
            ]
        )

    def test_runtime_and_parser_are_not_observed_bottleneck(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertTrue(
            diagnosis[
                "runtime_failure_budget_capacity_or_parser_is_not_the_observed_cause"
            ]
        )
        self.assertEqual(diagnosis["completed_runtime_tasks"], 20)
        self.assertEqual(diagnosis["combined_generic_observation_tasks"], 5)

    def test_only_build_only_coverage_deficit_successor_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["evidence_coverage_deficit_successor_build"])
        self.assertFalse(authorization["external_protocol_or_forward"])
        self.assertFalse(authorization["postfreeze_quality_or_truth"])
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_resealed_link_launch_or_credit_tamper_fails(self) -> None:
        for kind in ("link", "launch", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "link":
                changed["diagnosis"]["multirow_eligible_link_tasks"] = 7
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
