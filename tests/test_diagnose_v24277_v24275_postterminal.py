from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

from scripts import diagnose_v24277_v24275_postterminal as target


ROOT = Path(__file__).resolve().parents[1]


class V24277PostterminalDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_real_report_is_aggregate_no_go_and_content_free(self) -> None:
        target.validate_report(self.value)
        encoded = json.dumps(self.value, ensure_ascii=False)
        self.assertNotIn("opaque_id", encoded)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        self.assertEqual(self.value["candidate_controller"]["stop_tasks"], 57)
        self.assertEqual(self.value["candidate_controller"]["expand_tasks"], 7)
        self.assertEqual(
            self.value["gate"]["failed_checks"],
            [
                "candidate_hard_fetch_deadline_failures",
                "search_token_ratio",
                "task_wall_sum_ratio",
            ],
        )

    def test_report_quantifies_fetch_but_not_search_token_reduction(self) -> None:
        mechanism = self.value["mechanism_conclusions"]
        self.assertGreater(mechanism["fetch_call_reduction_fraction"], 0.60)
        self.assertLess(mechanism["search_total_token_reduction_fraction"], 0.01)
        self.assertTrue(mechanism["search_input_tokens_increased"])
        self.assertFalse(
            mechanism["fetch_reduction_translated_to_search_token_reduction"]
        )

    def test_resealed_launch_or_wrong_gate_tamper_is_rejected(self) -> None:
        for mutation in ("launch", "gate"):
            altered = copy.deepcopy(self.value)
            if mutation == "launch":
                altered["authorization"]["exact220_launch"] = True
            else:
                altered["gate"]["failed_checks"] = []
            altered["diagnosis_payload_sha256"] = target.payload_sha256(
                {
                    key: value
                    for key, value in altered.items()
                    if key != "diagnosis_payload_sha256"
                }
            )
            with self.assertRaisesRegex(RuntimeError, "diagnosis drifted"):
                target.validate_report(altered)


if __name__ == "__main__":
    unittest.main()
