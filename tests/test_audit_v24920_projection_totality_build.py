from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24920_projection_totality_build as audit  # noqa: E402


class V24920ProjectionTotalityBuildAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = audit.validate(audit.build(now=1))

    def test_audit_is_valid(self) -> None:
        self.assertTrue(self.value["audit_valid"])
        self.assertEqual(self.value["findings"], [])

    def test_exact71_tests_pass(self) -> None:
        self.assertEqual(sum(row["observed"] for row in self.value["tests"]), 71)
        self.assertTrue(all(row["passed"] for row in self.value["tests"]))

    def test_totality_is_narrow_and_no_effect(self) -> None:
        mechanism = self.value["mechanism"]
        self.assertTrue(mechanism["fallback_is_exact_stable_prefix"])
        self.assertFalse(
            mechanism["type_value_baseexception_or_unrelated_runtime_error_swallowed"]
        )
        self.assertFalse(
            mechanism["additional_network_fetch_search_model_or_wall_cap"]
        )

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
