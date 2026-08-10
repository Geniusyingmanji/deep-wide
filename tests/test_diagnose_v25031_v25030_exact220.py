from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25031_v25030_exact220 as target  # noqa: E402


class V25031V25030DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_complete_result_and_comparisons_are_bound(self) -> None:
        current = self.value["overall"]["v25030"]
        self.assertEqual(current["whole_table_successes"], 7)
        self.assertAlmostEqual(current["quality_composite"], 0.45029083584190965)
        self.assertEqual(self.value["overall"]["v25030_minus_v24857"]["whole_table_successes"], -2)
        self.assertEqual(self.value["overall"]["v25030_minus_v24969"]["whole_table_successes"], 2)

    def test_refinement_groups_cover_exact220_and_are_noncausal(self) -> None:
        groups = self.value["refinement_association"]
        self.assertEqual(groups["applied"]["tasks"], 129)
        self.assertEqual(groups["legacy_handoff"]["tasks"], 91)
        self.assertGreater(groups["applied"]["quality_composite"], groups["legacy_handoff"]["quality_composite"])
        self.assertTrue(self.value["diagnosis"]["refinement_group_difference_is_descriptive_not_randomized_or_causal"])

    def test_evaluator_only_family_audit_cannot_route_runtime(self) -> None:
        audit = self.value["evaluator_only_family_audit"]
        self.assertFalse(audit["runtime_routing_or_policy_selection_authorized"])
        self.assertEqual(audit["groups"]["deep2wide"]["tasks"], 85)
        self.assertEqual(audit["groups"]["wide2deep_en"]["tasks"], 70)
        self.assertEqual(audit["groups"]["wide2deep_zh"]["tasks"], 65)

    def test_cost_and_quality_bottleneck_are_explicit(self) -> None:
        delta = self.value["overall"]["v25030_minus_v24857"]
        self.assertGreater(delta["column_f1"], 0)
        self.assertLess(delta["entity_acc"], 0)
        self.assertLess(delta["f1_by_row"], 0)
        self.assertGreater(delta["token_ratio"], 3.6)

    def test_failures_and_evaluator_invalids_are_accounted(self) -> None:
        self.assertEqual(self.value["failure_taxonomy"]["runtime"], {"refinement:ModelRequestError": 1, "synthesis:ValueError": 5})
        self.assertEqual(self.value["failure_taxonomy"]["evaluator"], {"internal_error": 10, "out_of_range_metric": 2})

    def test_authority_is_only_matched_label_blind_gate_design(self) -> None:
        self.assertEqual(
            self.value["authorization"],
            {
                "matched_label_blind_external_or_synthetic_gate_design": True,
                "new_exact220_launch": False,
                "evaluator": False,
                "retry_resume_or_selective_rerun": False,
                "leaderboard_or_sota": False,
            },
        )
        self.assertFalse(self.value["diagnosis"]["entropy_or_information_gain_credit_validated_by_this_run"])

    def test_tamper_fails_closed(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["authorization"]["new_exact220_launch"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
