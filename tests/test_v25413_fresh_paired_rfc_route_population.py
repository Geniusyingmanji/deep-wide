from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership  # noqa: E402
from deepwide_agent import v25411_visible_membership_route_runtime as route  # noqa: E402
from deepwide_agent import v25413_fresh_paired_rfc_route_population as target  # noqa: E402


class V25413FreshPairedRfcRoutePopulationTests(unittest.TestCase):
    def test_identity_pair_and_task_vectors_are_fixed(self) -> None:
        identities = target.identity_vector()
        pairs = target.pair_vector()
        tasks = target.task_vector()
        self.assertEqual(identities[0], "RFC 9320")
        self.assertEqual(identities[-1], "RFC 9399")
        self.assertEqual(len(identities), 80)
        self.assertEqual(len(set(identities)), 80)
        self.assertEqual(len(pairs), target.PAIR_COUNT)
        self.assertEqual(len(tasks), target.TASK_COUNT)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 40)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.payload_sha256(pairs), target.EXPECTED_PAIR_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_each_pair_differs_only_by_membership_wrapper_and_routes_exactly(self) -> None:
        for pair in target.pair_vector():
            tasks = pair["tasks"]
            absent = tasks[route.STABLE_BRANCH]["question"]
            present = tasks[route.MEMBERSHIP_BRANCH]["question"]
            absent_members, absent_source = membership.visible_membership(absent)
            present_members, present_source = membership.visible_membership(present)
            self.assertEqual(absent_members, ())
            self.assertEqual(absent_source, "none")
            self.assertEqual(len(present_members), 4)
            self.assertEqual(present_source, "plural_inline_tag_vector")
            self.assertEqual(
                route.route_for_visible_question(absent), route.STABLE_BRANCH
            )
            self.assertEqual(
                route.route_for_visible_question(present), route.MEMBERSHIP_BRANCH
            )
            vector = "; ".join(present_members)
            self.assertEqual(
                present.replace(f"<RFCS>{vector}</RFCS>", vector), absent
            )

    def test_pair_validation_rejects_reorder_cross_pair_and_route_tamper(self) -> None:
        base = target.pair_vector()
        for kind in ("reorder", "cross_pair", "route"):
            changed = copy.deepcopy(base)
            if kind == "reorder":
                changed[0], changed[1] = changed[1], changed[0]
            elif kind == "cross_pair":
                changed[0]["tasks"][route.STABLE_BRANCH] = copy.deepcopy(
                    changed[1]["tasks"][route.STABLE_BRANCH]
                )
            else:
                task = changed[0]["tasks"][route.STABLE_BRANCH]
                task["question"] = task["question"].replace(
                    "RFC 9320; RFC 9321; RFC 9322; RFC 9323",
                    "<RFCS>RFC 9320; RFC 9321; RFC 9322; RFC 9323</RFCS>",
                )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_pair_vector(changed)

    def test_policy_and_gate_are_outcome_blind_and_do_not_authorize_launch(self) -> None:
        policy = target.source_policy()
        gate = target.route_gate()
        self.assertTrue(policy["only_pair_difference_is_strict_plural_membership_wrapper"])
        self.assertTrue(policy["membership_absent_route_is_v25375"])
        self.assertTrue(policy["membership_present_route_is_v25401"])
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])
        self.assertFalse(
            policy["deepwidebench_forward_evaluator_leaderboard_or_sota_authorized"]
        )
        self.assertEqual(gate["fixed_pair_denominator"], 20)
        self.assertEqual(gate["fixed_task_denominator"], 40)
        self.assertEqual(gate["maximum_membership_absent_outer_failure_tasks"], 0)
        self.assertEqual(gate["maximum_naked_outer_failure_tasks"], 0)
        self.assertEqual(gate["positive_signed_credit_count"], 0)


if __name__ == "__main__":
    unittest.main()
