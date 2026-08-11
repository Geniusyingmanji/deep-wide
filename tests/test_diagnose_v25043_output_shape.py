from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25043_output_shape as target  # noqa: E402


class V25043OutputShapeDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_exact220_shape_barrier_and_privacy(self) -> None:
        self.assertEqual(self.value["paired"]["tasks"], 220)
        self.assertEqual(self.value["output_shape"]["v25030"]["canonical_table_tasks"], 220)
        self.assertEqual(self.value["output_shape"]["v24857"]["canonical_table_tasks"], 220)
        self.assertTrue(
            self.value["checks"][
                "no_question_prediction_cell_instance_id_gold_or_per_task_metric_emitted"
            ]
        )

    def test_grouped_counts_cover_fixed_denominator(self) -> None:
        grouped = self.value["paired"]["grouped_quality"]
        for dimension in grouped.values():
            self.assertEqual(sum(group["tasks"] for group in dimension.values()), 220)

    def test_whole_table_transition_matches_frozen_results(self) -> None:
        transitions = self.value["paired"]["grouped_quality"]["whole_table_transition"]
        self.assertEqual(
            transitions["gain"]["tasks"]
            + transitions["both_exact"]["tasks"],
            7,
        )
        self.assertEqual(
            transitions["loss"]["tasks"]
            + transitions["both_exact"]["tasks"],
            9,
        )
        self.assertTrue(self.value["diagnosis"]["whole_table_losses_exceed_gains"])

    def test_unknown_reduction_is_not_authorized_as_utility(self) -> None:
        self.assertTrue(
            self.value["diagnosis"][
                "simple_unknown_reduction_is_not_a_safe_task_utility_proxy"
            ]
        )
        self.assertTrue(
            self.value["diagnosis"]["forced_coverage_ledger_reuse_is_not_authorized"]
        )
        self.assertFalse(
            self.value["diagnosis"]["entropy_or_information_gain_credit_validated"]
        )

    def test_authority_stops_before_benchmark(self) -> None:
        self.assertEqual(
            self.value["authorization"],
            {
                "fresh_label_blind_external_matched_gate_design": True,
                "new_exact220_launch": False,
                "evaluator_or_selective_revaluation": False,
                "retry_resume_or_selective_rerun": False,
                "leaderboard_or_sota": False,
            },
        )

    def test_nested_tamper_fails_closed(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["authorization"]["new_exact220_launch"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
