from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24916_prefix_total_long_page_build as audit  # noqa: E402


class V24916PrefixTotalLongPageBuildAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = audit.build(now=1)

    def test_audit_is_valid(self) -> None:
        self.assertTrue(self.value["audit_valid"])
        self.assertEqual(self.value["findings"], [])

    def test_exact54_tests_pass(self) -> None:
        self.assertEqual(sum(row["observed"] for row in self.value["tests"]), 54)
        self.assertTrue(all(row["passed"] for row in self.value["tests"]))

    def test_mechanism_is_total_and_no_effect(self) -> None:
        mechanism = self.value["mechanism"]
        self.assertTrue(mechanism["overflow_fallback_is_exact_prefix"])
        self.assertFalse(mechanism["unrelated_exception_swallowed"])
        self.assertFalse(mechanism["additional_network_or_model_effect"])

    def test_label_blind_and_entropy_credit_zero(self) -> None:
        policy = self.value["source_policy"]
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_historical_result_read"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_credit"])


if __name__ == "__main__":
    unittest.main()
