from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25427_structurally_disjoint_rfc_population as target  # noqa: E402


class V25427StructurallyDisjointRfcPopulationTests(unittest.TestCase):
    def test_vectors_are_fixed_to_9240_9319(self) -> None:
        identities = target.identity_vector()
        groups = target.group_vector()
        tasks = target.task_vector()
        self.assertEqual(identities[0], "RFC 9240")
        self.assertEqual(identities[-1], "RFC 9319")
        self.assertEqual(len(identities), 80)
        self.assertEqual(len(groups), 20)
        self.assertEqual(len(tasks), 20)
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

    def test_each_task_has_exact_visible_membership_order_and_schema(self) -> None:
        identities = target.identity_vector()
        for index, group in enumerate(target.group_vector()):
            question = group["task"]["question"]
            expected = identities[index * 4 : (index + 1) * 4]
            self.assertIn(f"<RFCS>{'; '.join(expected)}</RFCS>", question)
            self.assertIn(
                "RFC | Title | Authors | Status | Stream | Published", question
            )
            self.assertIn(
                "Preserve official spelling, list separators, and ordering",
                question,
            )
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
                ].replace("RFC 9240", "RFC 9241", 1)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_group_vector(changed)

    def test_policy_discloses_presence_and_authorizes_no_effect(self) -> None:
        policy = target.source_policy()
        gate = target.mechanism_gate()
        self.assertTrue(policy["aggregate_candidate_identity_presence_previously_observed"])
        self.assertEqual(policy["aggregate_candidate_identity_presence_count"], 80)
        self.assertFalse(
            policy["aggregate_presence_used_for_selection_replacement_or_ranking"]
        )
        self.assertFalse(
            policy[
                "candidate_field_value_page_quality_prediction_or_evaluator_used_for_selection"
            ]
        )
        self.assertFalse(
            policy["network_model_search_fetch_evaluator_or_benchmark_authorized"]
        )
        self.assertEqual(gate["fixed_task_denominator"], 20)
        self.assertTrue(gate["one_parent_forward_per_task"])
        self.assertTrue(gate["zero_additional_list_guard_provider_effects"])
        self.assertEqual(gate["positive_signed_credit_count"], 0)


if __name__ == "__main__":
    unittest.main()
