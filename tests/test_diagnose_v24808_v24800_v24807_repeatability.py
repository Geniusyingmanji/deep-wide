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

from scripts import diagnose_v24808_v24800_v24807_repeatability as target  # noqa: E402


class V24808RepeatabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_same_algorithm_full220_is_not_byte_stable(self) -> None:
        overall = self.value["overall"]
        self.assertEqual(overall["v24800"]["n"], 220)
        self.assertEqual(overall["v24807"]["n"], 220)
        self.assertEqual(overall["prediction_sha256_identical_tasks"], 10)
        self.assertEqual(overall["prediction_sha256_changed_tasks"], 210)

    def test_whole_table_does_not_replicate_a_gain(self) -> None:
        overall = self.value["overall"]
        self.assertEqual(overall["v24800"]["whole_table_successes"], 8)
        self.assertEqual(overall["v24807"]["whole_table_successes"], 8)
        self.assertEqual(overall["delta_v24807_minus_v24800"]["whole_table_successes"], 0)
        self.assertEqual(
            overall["whole_table_transitions"],
            {
                "old_failure_new_failure": 210,
                "old_failure_new_success": 2,
                "old_success_new_failure": 2,
                "old_success_new_success": 6,
            },
        )

    def test_composite_difference_is_unresolved(self) -> None:
        bootstrap = self.value["overall"]["paired_composite_bootstrap"]
        lower, upper = bootstrap["percentile_95_interval"]
        self.assertLess(lower, 0)
        self.assertGreater(upper, 0)
        self.assertFalse(bootstrap["interval_excludes_zero"])
        self.assertAlmostEqual(bootstrap["mean_delta"], -0.018585371211356696)

    def test_evaluator_failure_modes_and_overlap_are_retained(self) -> None:
        evaluator = self.value["evaluator"]
        self.assertEqual(evaluator["v24800_invalid_failure_as_zero"], 13)
        self.assertEqual(evaluator["v24807_invalid_failure_as_zero"], 11)
        self.assertEqual(evaluator["invalid_intersection"], 7)
        self.assertEqual(evaluator["invalid_union"], 17)
        self.assertEqual(evaluator["error_taxonomy"]["v24807"], {
            "empty_inner_join_assignment": 10,
            "out_of_range_metric": 1,
        })
        self.assertFalse(evaluator["selective_retry_or_revaluation"])

    def test_output_is_aggregate_only_and_forbids_public_rerun(self) -> None:
        encoded = json.dumps(self.value, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertFalse(self.value["boundary"]["prediction_field_read"])
        self.assertFalse(self.value["authorization"]["new_public_dev64"])
        self.assertFalse(self.value["authorization"]["new_public_exact220"])
        self.assertFalse(self.value["authorization"]["selective_revaluation"])

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
