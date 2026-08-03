from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24298_v24297_paired_dev64 as target  # noqa: E402


class V24298DiagnosisTests(unittest.TestCase):
    def test_recomputes_quality_mechanism_and_reliability_no_go(self) -> None:
        value = target.build_report(ROOT, now=1)
        target.validate_report(ROOT, value)
        self.assertEqual(value["result_summary"]["decision"], "no_go")
        self.assertGreater(
            value["result_summary"]["candidate_minus_baseline"][
                "quality_composite"
            ],
            0,
        )
        self.assertEqual(
            value["mechanism_activation"]["low_coverage_diversity_tail_tasks"], 10
        )
        self.assertEqual(value["reliability"]["candidate_extra_fallbacks"], 5)
        self.assertEqual(
            value["reliability"]["failure_taxonomy"]["candidate"][
                "fallback_failed_model_events_by_stage"
            ],
            {"repair": 1, "synthesis": 5},
        )

    def test_transport_is_not_the_candidate_regression(self) -> None:
        value = target.build_report(ROOT, now=1)
        transport = value["reliability"]["transport"]
        self.assertEqual(transport["baseline"]["hard_fetch_deadline_failures"], 6)
        self.assertEqual(transport["candidate"]["hard_fetch_deadline_failures"], 3)
        self.assertFalse(value["conclusions"]["candidate_transport_worse_than_baseline"])
        self.assertTrue(
            value["conclusions"][
                "candidate_extra_fallbacks_explained_by_model_stage_failures"
            ]
        )

    def test_report_does_not_authorize_benchmark_or_sota(self) -> None:
        value = target.build_report(ROOT, now=1)
        self.assertFalse(value["conclusions"]["exact220_authorized"])
        self.assertFalse(value["authorization"]["additional_dev64"])
        self.assertFalse(value["authorization"]["exact220"])
        self.assertFalse(value["authorization"]["sota_claim"])

    def test_resealed_tamper_is_recomputed_and_rejected(self) -> None:
        value = target.build_report(ROOT, now=1)
        altered = copy.deepcopy(value)
        altered["conclusions"]["exact220_authorized"] = True
        unsigned = dict(altered)
        unsigned.pop("diagnosis_payload_sha256", None)
        altered["diagnosis_payload_sha256"] = target.payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "diagnosis drifted"):
            target.validate_report(ROOT, altered)

    def test_output_contains_no_task_identity_or_content(self) -> None:
        encoded = str(target.build_report(ROOT, now=1))
        self.assertNotIn("task_069126", encoded)
        self.assertNotIn("deep2wide_result", encoded)
        self.assertNotIn("wide2deep_ws_", encoded)


if __name__ == "__main__":
    unittest.main()
