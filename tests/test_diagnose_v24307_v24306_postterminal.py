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

from scripts import diagnose_v24307_v24306_postterminal as target  # noqa: E402


class V24307DiagnosisTests(unittest.TestCase):
    def test_recomputes_forward_failure_taxonomy(self) -> None:
        value = target.build_report(ROOT, now=1)
        target.validate_report(ROOT, value)
        failure = value["forward_failure_taxonomy"]
        self.assertEqual(
            failure["baseline_zero_effect_unobservable_positions"], [18, 51]
        )
        self.assertEqual(
            failure["baseline_synthesis_provider_failure_positions"], [26, 55]
        )
        self.assertEqual(failure["candidate"], [])

    def test_deadlines_do_not_explain_fallbacks(self) -> None:
        value = target.build_report(ROOT, now=1)
        self.assertEqual(
            value["transport"]["hard_fetch_deadline_counts"],
            {"baseline": 5, "candidate": 2},
        )
        self.assertEqual(
            value["transport"]["deadline_events_overlap_fallback_positions"],
            {"baseline": [], "candidate": []},
        )
        self.assertFalse(
            value["conclusions"]["hard_fetch_deadline_is_primary_fallback_cause"]
        )

    def test_positive_point_estimate_is_not_attributed_to_recovery(self) -> None:
        value = target.build_report(ROOT, now=1)
        self.assertTrue(value["conclusions"]["candidate_point_estimate_positive"])
        self.assertTrue(
            value["conclusions"]["candidate_bootstrap_lower_bound_passed"]
        )
        self.assertFalse(
            value["conclusions"]["candidate_bootstrap_interval_width_passed"]
        )
        self.assertFalse(value["conclusions"]["quality_gain_attributable_to_recovery"])

    def test_content_free_and_no_benchmark_authority(self) -> None:
        value = target.build_report(ROOT, now=1)
        encoded = json.dumps(value)
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertFalse(value["authorization"]["additional_dev64"])
        self.assertFalse(value["authorization"]["exact220"])
        self.assertFalse(value["authorization"]["evaluator_call"])

    def test_resealed_tamper_is_recomputed_and_rejected(self) -> None:
        value = target.build_report(ROOT, now=1)
        altered = copy.deepcopy(value)
        altered["conclusions"]["exact220_authorized"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "diagnosis drifted"):
            target.validate_report(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
