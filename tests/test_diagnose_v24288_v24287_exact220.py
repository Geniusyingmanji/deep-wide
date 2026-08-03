from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diagnose_v24288_v24287_exact220 as target  # noqa: E402


class V24288Exact220DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_report_is_aggregate_content_free_and_no_go(self) -> None:
        target.validate_report(self.value)
        encoded = json.dumps(self.value, ensure_ascii=False)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        self.assertNotIn("opaque_id", encoded)
        self.assertEqual(self.value["controller"]["stop"]["selected"], 175)
        self.assertEqual(self.value["controller"]["expand"]["selected"], 43)
        self.assertEqual(self.value["controller"]["expand_low_coverage"]["selected"], 23)
        self.assertTrue(self.value["mechanism_conclusions"]["quality_regressed"])
        self.assertFalse(self.value["mechanism_conclusions"]["sota_supported"])

    def test_report_separates_stop_and_expand_mechanisms(self) -> None:
        stop = self.value["controller"]["stop"]["quality_composite"]["candidate_minus_control"]["mean"]
        expand = self.value["controller"]["expand"]["quality_composite"]["candidate_minus_control"]["mean"]
        self.assertGreater(stop, 0)
        self.assertLess(expand, -0.08)
        self.assertEqual(self.value["failure_taxonomy"]["forward_fallbacks"], {"best_effort_fallback": 4, "hard_deadline_fallback": 2})
        self.assertEqual(self.value["failure_taxonomy"]["evaluator_errors"], {"internal_error": 9, "out_of_range": 2})

    def test_resealed_authorization_or_partition_tamper_is_rejected(self) -> None:
        for mutation in ("launch", "partition"):
            altered = copy.deepcopy(self.value)
            if mutation == "launch":
                altered["authorization"]["exact220_launch"] = True
            else:
                altered["controller"]["expand"]["selected"] = 42
            altered["diagnosis_payload_sha256"] = target.payload_sha256(
                {key: value for key, value in altered.items() if key != "diagnosis_payload_sha256"}
            )
            with self.assertRaisesRegex(RuntimeError, "diagnosis drifted"):
                target.validate_report(altered)


if __name__ == "__main__":
    unittest.main()
