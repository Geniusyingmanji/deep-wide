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

from scripts import diagnose_v24825_v24824_fetch_failure as target  # noqa: E402


class V24825FetchFailureDiagnosisTests(unittest.TestCase):
    def test_aggregate_current_conserves_all_fetch_failures(self):
        value = target.aggregate(target.CURRENT_ROOT)
        self.assertEqual(value["tasks"], 32)
        self.assertEqual(value["fetch_calls"], 320)
        self.assertEqual(value["fetch_failures"], 275)
        self.assertEqual(value["generic_nonusable"], 23)
        self.assertEqual(value["exact_nonvalid"], 252)
        self.assertEqual(value["reconstructed_fetch_failures"], 275)

    def test_exact_missing_is_preprojection_not_parser_rejection(self):
        value = target.aggregate(target.CURRENT_ROOT)
        self.assertEqual(value["full_valid_exact_record_count"], 4)
        self.assertEqual(value["full_missing_response_count"], 252)
        self.assertEqual(value["full_invalid_exact_response_count"], 0)
        self.assertEqual(value["full_null_value_record_count"], 0)
        self.assertEqual(value["full_unmatched_or_duplicate_result_count"], 0)

    def test_baseline_transport_was_materially_healthier(self):
        baseline = target.aggregate(target.BASELINE_ROOT)
        current = target.aggregate(target.CURRENT_ROOT)
        self.assertEqual(baseline["full_valid_exact_record_count"], 91)
        self.assertEqual(baseline["exact_targets"], 96)
        self.assertLess(
            current["full_valid_exact_record_count"] / current["exact_targets"],
            baseline["full_valid_exact_record_count"] / baseline["exact_targets"],
        )

    def test_build_is_valid_and_grants_no_launch(self):
        value = target.build(now=1)
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(
            value["authorization"]["append_only_exact_api_transport_design"]
        )
        self.assertFalse(value["authorization"]["new_external_population_or_launch"])
        self.assertFalse(value["authorization"]["public_exact220"])

    def test_resealed_public_authority_tamper_fails(self):
        value = target.build(now=1)
        changed = copy.deepcopy(value)
        changed["authorization"]["public_exact220"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
