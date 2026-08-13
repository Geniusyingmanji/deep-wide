from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25421_fresh_rfc_list_atomic_population as target  # noqa: E402


class V25421FreshRfcListAtomicPopulationTests(unittest.TestCase):
    def test_identity_group_and_task_vectors_are_fixed(self) -> None:
        identities = target.identity_vector()
        groups = target.group_vector()
        tasks = target.task_vector()
        self.assertEqual(identities[0], "RFC 9720")
        self.assertEqual(identities[-1], "RFC 9799")
        self.assertEqual(len(identities), 80)
        self.assertEqual(len(set(identities)), 80)
        self.assertEqual(len(groups), 20)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.payload_sha256(groups), target.EXPECTED_GROUP_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_each_task_has_exact_group_order_and_visible_schema(self) -> None:
        identities = target.identity_vector()
        for index, group in enumerate(target.group_vector()):
            question = group["task"]["question"]
            expected = identities[index * 4 : (index + 1) * 4]
            positions = [question.index(identity) for identity in expected]
            self.assertEqual(positions, sorted(positions))
            self.assertIn("RFC | Title | Authors | Status | Stream | Published", question)
            self.assertIn("Preserve official spelling, list separators, and ordering", question)
            for identity in identities:
                self.assertEqual(identity in question, identity in expected)

    def test_validation_rejects_reorder_cross_group_and_question_tamper(self) -> None:
        base = target.group_vector()
        for kind in ("reorder", "cross_group", "question"):
            changed = copy.deepcopy(base)
            if kind == "reorder":
                changed[0], changed[1] = changed[1], changed[0]
            elif kind == "cross_group":
                changed[0]["task"] = copy.deepcopy(changed[1]["task"])
            else:
                changed[0]["task"]["question"] = changed[0]["task"][
                    "question"
                ].replace("RFC 9720", "RFC 9721", 1)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_group_vector(changed)

    def test_policy_and_gate_are_outcome_blind_and_do_not_authorize_launch(self) -> None:
        policy = target.source_policy()
        gate = target.mechanism_gate()
        self.assertFalse(policy["independent_sampling_between_quality_arms"])
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])
        self.assertFalse(
            policy["deepwidebench_forward_evaluator_leaderboard_or_sota_authorized"]
        )
        self.assertEqual(gate["fixed_task_denominator"], 20)
        self.assertEqual(gate["maximum_outer_failure_tasks"], 0)
        self.assertTrue(gate["zero_additional_guard_provider_effects"])
        self.assertEqual(gate["positive_signed_credit_count"], 0)


if __name__ == "__main__":
    unittest.main()
