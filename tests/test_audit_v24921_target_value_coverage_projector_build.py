from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24921_target_value_coverage_projector_build as audit  # noqa: E402


class V24921TargetValueCoverageProjectorBuildAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = audit.validate(audit.build(now=1))

    def test_audit_is_valid(self) -> None:
        self.assertTrue(self.value["audit_valid"])
        self.assertEqual(self.value["findings"], [])

    def test_exact42_tests_pass(self) -> None:
        self.assertEqual(sum(row["observed"] for row in self.value["tests"]), 42)
        self.assertTrue(all(row["passed"] for row in self.value["tests"]))

    def test_label_blind_no_effect_and_no_credit(self) -> None:
        self.assertFalse(
            self.value["mechanism"][
                "additional_network_search_fetch_model_token_context_or_wall_cap"
            ]
        )
        policy = self.value["source_policy"]
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_historical_result_read"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])


if __name__ == "__main__":
    unittest.main()
