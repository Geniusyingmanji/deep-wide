from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24293_v24291_dev64 as target  # noqa: E402


class V24293DiagnosisTests(unittest.TestCase):
    def test_report_recomputes_no_go_and_budget_block(self) -> None:
        value = target.build_report(ROOT, now=1)
        target.validate_report(ROOT, value)
        self.assertEqual(value["result_summary"]["decision"], "no_go")
        self.assertEqual(value["mechanism_activation"]["controller_expand"], 6)
        self.assertEqual(value["mechanism_activation"]["rescue_triggered"], 0)
        self.assertEqual(value["mechanism_activation"]["budget_blocked_low_coverage_tasks"], 2)
        self.assertEqual(value["mechanism_activation"]["budget_blocked_aggregate"]["remaining_fetch_capacity"], [0, 0])

    def test_report_does_not_claim_rescue_or_exact220(self) -> None:
        value = target.build_report(ROOT, now=1)
        self.assertFalse(value["conclusions"]["quality_gain_attributable_to_rescue"])
        self.assertFalse(value["conclusions"]["quality_gain_statistically_resolved"])
        self.assertFalse(value["conclusions"]["exact220_authorized"])
        self.assertFalse(value["authorization"]["additional_dev64"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_resealed_tamper_is_recomputed_and_rejected(self) -> None:
        value = target.build_report(ROOT, now=1)
        altered = copy.deepcopy(value)
        altered["conclusions"]["quality_gain_attributable_to_rescue"] = True
        unsigned = dict(altered)
        unsigned.pop("diagnosis_payload_sha256", None)
        altered["diagnosis_payload_sha256"] = target.payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "diagnosis drifted"):
            target.validate_report(ROOT, altered)

    def test_output_contains_no_per_task_identity_or_content(self) -> None:
        value = target.build_report(ROOT, now=1)
        encoded = str(value)
        self.assertNotIn("task_b69d", encoded)
        self.assertNotIn("deep2wide_result", encoded)
        self.assertNotIn("wide2deep_ws_", encoded)


if __name__ == "__main__":
    unittest.main()
