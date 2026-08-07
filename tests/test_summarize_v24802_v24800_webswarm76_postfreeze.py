from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import summarize_v24802_v24800_webswarm76_postfreeze as target  # noqa: E402


class V24802WebSwarm76PostfreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = json.loads((ROOT / target.OUTPUT).read_text(encoding="utf-8"))
        target.validate_report(cls.value)

    def test_exact_manifest_metrics_are_fixed_denominator(self) -> None:
        current = self.value["v24800_same_manifest"]
        self.assertEqual(current["selected"], 76)
        self.assertEqual(current["evaluator_valid"], 72)
        self.assertEqual(current["evaluator_invalid_failure_as_zero"], 4)
        self.assertEqual(current["whole_table_successes"], 5)
        self.assertAlmostEqual(current["metrics"]["score"], 5 / 76)
        self.assertAlmostEqual(current["metrics"]["f1_by_row"], 0.3307177706865253)
        self.assertAlmostEqual(current["metrics"]["f1_by_item"], 0.5489454267761117)

    def test_paper_comparison_is_descriptive_and_not_cost_matched(self) -> None:
        delta = self.value["descriptive_delta_from_paper_report"]
        self.assertTrue(delta["success_rate_equal_at_two_decimal_percentage_precision"])
        self.assertGreater(delta["row_f1"], 0)
        self.assertLess(delta["item_f1"], 0)
        comparability = self.value["comparability"]
        self.assertTrue(comparability["same_exact_public_task_manifest"])
        self.assertFalse(comparability["same_model_backbone"])
        self.assertFalse(comparability["same_budget_or_action_cap"])
        self.assertFalse(comparability["fair_system_ranking_established"])

    def test_repository_subset_language_mislabel_is_retained(self) -> None:
        source = self.value["external_source"]
        self.assertEqual(source["subset_rows"], 76)
        self.assertEqual(source["subset_language_field_counts"], {"en": 75, "zh": 1})
        self.assertEqual(source["subset_label_in_repository"], "en_subset")

    def test_output_is_aggregate_only_and_grants_no_benchmark_authority(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        self.assertNotIn("deep2wide_result_", encoded)
        self.assertNotIn("wide2deep_ws_", encoded)
        self.assertFalse(
            self.value["boundary"][
                "instance_id_question_prediction_answer_query_url_page_or_credential_emitted"
            ]
        )
        self.assertEqual(
            self.value["authorization"],
            {
                "documentation_update": True,
                "new_public_dev64": False,
                "new_public_exact220": False,
                "leaderboard_submission": False,
                "sota_claim": False,
            },
        )

    def test_entropy_credit_and_sota_claims_remain_false(self) -> None:
        claims = self.value["claims"]
        self.assertFalse(claims["entropy_or_credit_assignment_validated"])
        self.assertFalse(claims["external_sota"])
        self.assertFalse(claims["v24800_outperformed_under_matched_conditions"])
        self.assertFalse(claims["webswarm_outperformed_under_matched_conditions"])

    def test_seal_and_tamper_rejection(self) -> None:
        target.validate_report(self.value)
        altered = copy.deepcopy(self.value)
        altered["authorization"]["new_public_exact220"] = True
        unsigned = dict(altered)
        unsigned.pop("report_payload_sha256")
        altered["report_payload_sha256"] = target.contract.payload_sha256(unsigned)
        with self.assertRaises(RuntimeError):
            target.validate_report(altered)

    def test_rebuild_when_external_manifest_is_available(self) -> None:
        subset = ROOT / target.DEFAULT_SUBSET
        if not subset.is_file():
            self.skipTest("external WebSwarm manifest is not present in clean checkout")
        rebuilt = target.build_report(
            now=int(self.value["created_at_unix"]),
        )
        self.assertEqual(rebuilt, self.value)


if __name__ == "__main__":
    unittest.main()
