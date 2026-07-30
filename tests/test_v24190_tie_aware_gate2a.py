from __future__ import annotations

import unittest

from src.deepwide_agent.v24190_tie_aware_gate2a import (
    evaluate_tie_aware_gate2a,
    expected_topk_hit_probability,
    uniform_topk_hit_probability,
)
from tests.test_v24161_strict_gate2a import fixture, settings


class V24190TieAwareGate2ATests(unittest.TestCase):
    def test_random_top2_accounts_for_true_best_multiplicity(self) -> None:
        self.assertAlmostEqual(
            uniform_topk_hit_probability(action_count=3, best_count=1), 2 / 3
        )
        self.assertEqual(
            uniform_topk_hit_probability(action_count=3, best_count=2), 1.0
        )
        self.assertEqual(
            uniform_topk_hit_probability(action_count=3, best_count=3), 1.0
        )

    def test_prediction_boundary_tie_is_uniform_not_action_ordered(self) -> None:
        scores = {"first": 1.0, "second": 0.5, "third": 0.5}
        self.assertEqual(
            expected_topk_hit_probability(scores, {"second"}), 0.5
        )
        self.assertEqual(
            expected_topk_hit_probability(scores, {"third"}), 0.5
        )
        self.assertEqual(expected_topk_hit_probability(scores, {"first"}), 1.0)
        self.assertAlmostEqual(
            expected_topk_hit_probability(
                {"first": 0.5, "second": 0.5, "third": 0.5},
                {"third"},
            ),
            2 / 3,
        )

    def test_tied_true_best_cannot_create_random_advantage(self) -> None:
        states = [
            ([0.9, 0.9, 0.1], [0.9, 0.8, 0.1], [0.1, 0.0, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        report = evaluate_tie_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            settings=settings(
                minimum_entropy_increase_risk_decrease_bundles=0,
                minimum_entropy_increase_risk_decrease_task_clusters=0,
            ),
        )
        advantage = report["tie_aware_top2"]["full_advantage_over_random"]
        parent_advantage = report["parent_strict_gate_replay"]["paired_top2"][
            "full_advantage_over_random"
        ]
        self.assertAlmostEqual(parent_advantage["estimate"], 1 / 3)
        self.assertEqual(advantage["estimate"], 0.0)
        self.assertFalse(report["tie_aware_top2_conditions_passed"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["actual_best_multiplicity"], {"2": 3})

    def test_all_prediction_scores_tied_cannot_beat_random(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.5, 0.5, 0.5], [0.1, 0.1, 0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        report = evaluate_tie_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            settings=settings(),
        )
        top2 = report["tie_aware_top2"]
        self.assertAlmostEqual(top2["full_expected_hit_rate"]["estimate"], 2 / 3)
        self.assertEqual(top2["full_advantage_over_random"]["estimate"], 0.0)
        self.assertFalse(report["passed"])

    def test_unique_non_tied_case_preserves_positive_parent_direction(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.1, 0.2, 0.9], [0.9, 0.8, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        report = evaluate_tie_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            settings=settings(),
        )
        self.assertEqual(report["actual_best_multiplicity"], {"1": 3})
        self.assertGreater(
            report["tie_aware_top2"]["full_advantage_over_random"]["estimate"],
            0.0,
        )
        self.assertTrue(report["passed"])


if __name__ == "__main__":
    unittest.main()
