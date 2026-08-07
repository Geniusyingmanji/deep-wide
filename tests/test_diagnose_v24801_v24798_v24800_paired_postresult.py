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
    diagnose_v24801_v24798_v24800_paired_postresult as target,
)


class V24801PairedPostresultDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_full_budget_observed_frontier_and_cost_delta(self) -> None:
        overall = self.value["overall"]
        self.assertEqual(overall["old"]["n"], 220)
        self.assertEqual(overall["new"]["n"], 220)
        self.assertEqual(overall["old"]["whole_table_successes"], 6)
        self.assertEqual(overall["new"]["whole_table_successes"], 8)
        self.assertEqual(overall["delta"]["whole_table_success_delta"], 2)
        self.assertGreater(
            overall["delta"]["metrics"]["quality_composite"], 0
        )
        self.assertGreater(overall["system_total_tokens_delta"], 1_000_000)
        self.assertEqual(overall["prediction_sha256_identical_tasks"], 5)

    def test_old_early_stop_stratum_contains_observed_gain(self) -> None:
        groups = self.value["old_reason_groups"]
        sufficient = groups["first_wave_sufficient"]
        self.assertEqual(sufficient["old"]["n"], 192)
        self.assertEqual(
            sufficient["new_reason_counts"], {"positive_entropy_voc": 192}
        )
        self.assertEqual(
            sufficient["delta"]["whole_table_success_delta"], 2
        )
        self.assertGreater(
            sufficient["delta"]["metrics"]["quality_composite"], 0
        )
        self.assertLessEqual(
            groups["positive_entropy_voc"]["delta"]["metrics"][
                "quality_composite"
            ],
            0,
        )

    def test_task_level_uncertainty_and_evaluator_health_are_retained(self) -> None:
        bootstrap = self.value["paired_composite_bootstrap"]
        lower, upper = bootstrap["percentile_95_interval"]
        self.assertLess(lower, 0)
        self.assertGreater(upper, 0)
        self.assertFalse(bootstrap["interval_excludes_zero"])
        self.assertEqual(sum(bootstrap["direction_counts"].values()), 220)
        self.assertEqual(
            sum(self.value["evaluator"]["validity_transitions"].values()), 220
        )
        self.assertEqual(self.value["evaluator"]["old_invalid_failure_as_zero"], 11)
        self.assertEqual(self.value["evaluator"]["new_invalid_failure_as_zero"], 13)

    def test_output_is_aggregate_only_and_forbids_public_rerun(self) -> None:
        encoded = json.dumps(self.value, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))
        boundary = self.value["boundary"]
        self.assertFalse(boundary["prediction_field_used"])
        self.assertFalse(
            boundary[
                "mapping_answer_category_question_type_split_resource_opened"
            ]
        )
        self.assertFalse(self.value["authorization"]["new_public_dev64"])
        self.assertFalse(self.value["authorization"]["new_public_exact220"])

    def test_interpretation_is_noncausal_and_entropy_credit_unvalidated(self) -> None:
        conclusions = self.value["conclusions"]
        self.assertTrue(conclusions["observed_internal_whole_table_frontier_improved"])
        self.assertTrue(
            conclusions["observed_internal_quality_composite_frontier_improved"]
        )
        self.assertFalse(
            conclusions["randomized_or_shared_prefix_causal_effect_established"]
        )
        self.assertFalse(conclusions["full_budget_dominates_entropy_controller_at_matched_cost"])
        self.assertFalse(
            conclusions["entropy_or_information_gain_is_validated_as_credit"]
        )
        self.assertFalse(conclusions["leaderboard_or_external_sota_established"])

    def test_reproducible_seal_and_tamper_rejection(self) -> None:
        target.validate_report(ROOT, self.value)
        altered = copy.deepcopy(self.value)
        altered["authorization"]["new_public_exact220"] = True
        unsigned = dict(altered)
        unsigned.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = target.contract.payload_sha256(unsigned)
        with self.assertRaises(RuntimeError):
            target.validate_report(ROOT, altered, rebuild=False)


if __name__ == "__main__":
    unittest.main()
