from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    diagnose_v24636_v24630_v24635_paired_postresult as target,
)


class V24636PairedPostresultDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_completion_transitions_and_primary_result(self) -> None:
        self.assertEqual(self.value["overall"]["old_fallback_tables"], 34)
        self.assertEqual(self.value["overall"]["new_fallback_tables"], 1)
        rescued = self.value["completion_transition_groups"][
            "old_fallback_to_new_model"
        ]
        self.assertEqual(rescued["old"]["n"], 34)
        self.assertEqual(rescued["delta"]["whole_table_success_delta"], 0)
        self.assertGreater(rescued["delta"]["quality_composite_delta"], 0)
        self.assertEqual(
            self.value["overall"]["delta"]["whole_table_success_delta"], -1
        )
        self.assertGreater(
            self.value["overall"]["delta"]["quality_composite_delta"], 0
        )

    def test_transition_partition_and_delta_reconcile(self) -> None:
        groups = self.value["completion_transition_groups"]
        self.assertEqual(sum(group["old"]["n"] for group in groups.values()), 220)
        self.assertTrue(self.value["delta_reconciliation"]["matches_overall"])
        self.assertAlmostEqual(
            self.value["delta_reconciliation"]["weighted_quality_composite_delta"],
            self.value["overall"]["delta"]["quality_composite_delta"],
        )
        self.assertEqual(
            self.value["delta_reconciliation"]["whole_table_success_delta"], -1
        )

    def test_direction_and_evaluator_transition_denominators(self) -> None:
        for value in self.value["paired_metric_direction_counts"].values():
            self.assertEqual(sum(value.values()), 220)
        self.assertEqual(
            sum(self.value["evaluator_validity_transitions"].values()), 220
        )

    def test_output_is_aggregate_only_and_forbids_public_rerun(self) -> None:
        encoded = json.dumps(self.value, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))
        boundary = self.value["boundary"]
        self.assertFalse(boundary["prediction_field_used"])
        self.assertFalse(
            boundary[
                "mapping_answer_category_question_type_or_split_resource_opened"
            ]
        )
        self.assertFalse(
            self.value["authorization"]["new_exact220"]
        )
        self.assertFalse(
            self.value["next_work"]["public_exact220_allowed_from_this_diagnosis"]
        )

    def test_interpretation_is_noncausal_and_metric_specific(self) -> None:
        conclusions = self.value["conclusions"]
        self.assertTrue(conclusions["capacity_reliability_improved_in_observed_run"])
        self.assertFalse(conclusions["randomized_causal_effect_of_schedule_established"])
        self.assertFalse(conclusions["strict_whole_table_primary_metric_improved"])
        self.assertTrue(conclusions["quality_composite_improved"])
        self.assertTrue(conclusions["fallback_reduction_is_not_sufficient_for_exact_table_success"])

    def test_seal_and_tamper_rejection(self) -> None:
        target.validate_report(ROOT, self.value)
        altered = copy.deepcopy(self.value)
        altered["authorization"]["new_exact220"] = True
        with self.assertRaises(RuntimeError):
            target.validate_report(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
