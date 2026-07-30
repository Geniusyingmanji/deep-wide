from __future__ import annotations

import unittest

from src.deepwide_agent.v24191_policy_value_gate2a import (
    DEFAULT_POLICY_SETTINGS,
    derive_no_entropy_predicted_tokens,
    evaluate_policy_value_gate2a,
    select_deployment_action,
)
from src.deepwide_agent.v24123_release import (
    ACTION_MODEL_ROLE,
    NO_ENTROPY_FEATURE_KEYS,
    object_sha256,
)
from tests.test_v24161_strict_gate2a import fixture, settings


def policy_settings(**updates: object) -> dict:
    value = dict(DEFAULT_POLICY_SETTINGS)
    value.update(
        {
            "minimum_comparable_checkpoints": 3,
            "minimum_independent_task_clusters": 3,
            "bootstrap_resamples": 200,
        }
    )
    value.update(updates)
    return value


def no_entropy_costs(predictions: dict) -> dict[str, int]:
    return {
        row["bundle_sha256"]: 100 for row in predictions["predictions"]
    }


class V24191PolicyValueGate2ATests(unittest.TestCase):
    def test_no_entropy_costs_are_replayed_from_frozen_model(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.1, 0.2, 0.9], [0.9, 0.8, -0.1])
            for _ in range(3)
        ]
        manifest, _, _ = fixture(states)
        action_models = {}
        for action_index, action in enumerate(
            ("resolve_anchor", "regenerate_hypotheses", "falsify_anchor")
        ):
            vector_size = len(NO_ENTROPY_FEATURE_KEYS) + 1
            action_models[action] = {
                "fit_records": 5,
                "calibration_records": 3,
                "raw_coefficients": {
                    "task_contribution": [0.0] * vector_size,
                    "log_action_system_tokens": [0.0] * vector_size,
                },
                "affine_calibrators": {
                    "task_contribution": [0.0, 0.0],
                    "log_action_system_tokens": [
                        __import__("math").log1p(100 + action_index),
                        0.0,
                    ],
                },
            }
        model = {
            "artifact_version": 1,
            "role": ACTION_MODEL_ROLE,
            "job_manifest_sha256": manifest["manifest_sha256"],
            "model_ready": True,
            "blockers": [],
            "full_model": {},
            "no_entropy_baseline": {
                "feature_keys": list(NO_ENTROPY_FEATURE_KEYS),
                "models": {"anchor": action_models},
            },
            "fit_record_count": 15,
            "calibration_record_count": 9,
            "fit_task_clusters": 3,
            "calibration_task_clusters": 3,
            "ridge_lambda": 0.001,
            "minimum_fit_records_per_context_action": 5,
            "minimum_calibration_records_per_context_action": 3,
            "fit_calibration_aggregate_sha256": "a" * 64,
            "audit_outcomes_read": False,
            "controller_or_training_authorized": False,
        }
        model["model_sha256"] = object_sha256(model)
        costs = derive_no_entropy_predicted_tokens(manifest, model)
        by_action = {
            bundle["action"]: costs[bundle["bundle_sha256"]]
            for bundle in manifest["bundles"]
        }
        self.assertEqual(
            by_action,
            {
                "resolve_anchor": 100,
                "regenerate_hypotheses": 101,
                "falsify_anchor": 102,
            },
        )

    def test_deployment_selection_uses_positive_gain_per_token_and_stop(self) -> None:
        order = ("first", "second", "third")
        self.assertEqual(
            select_deployment_action(
                {"first": 0.4, "second": 0.3, "third": -0.1},
                {"first": 400, "second": 100, "third": 1},
                action_order=order,
            ),
            "second",
        )
        self.assertIsNone(
            select_deployment_action(
                {"first": 0.0, "second": -0.1, "third": -0.2},
                {"first": 1, "second": 1, "third": 1},
                action_order=order,
            )
        )

    def test_full_and_no_entropy_use_branch_specific_costs(self) -> None:
        states = [
            ([0.9, 0.3, 0.1], [0.9, 0.8, 0.1], [0.9, 0.8, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        baseline_costs = no_entropy_costs(predictions)
        action_by_bundle = {
            bundle["bundle_sha256"]: bundle["action"]
            for bundle in manifest["bundles"]
        }
        for row in predictions["predictions"]:
            row["predicted_action_system_tokens"] = (
                100 if row["action"] == "resolve_anchor" else 1000
            )
            row.pop("prediction_sha256")
            row["prediction_sha256"] = object_sha256(row)
        predictions.pop("seal_sha256")
        predictions["seal_sha256"] = object_sha256(predictions)
        for bundle_sha, action in action_by_bundle.items():
            baseline_costs[bundle_sha] = (
                1000 if action == "resolve_anchor" else 100
            )
        report = evaluate_policy_value_gate2a(
            manifest,
            aggregates,
            predictions,
            baseline_costs,
            parent_settings=settings(),
            policy_settings=policy_settings(),
        )
        self.assertEqual(report["selection_counts"]["full"], {"resolve_anchor": 3})
        self.assertEqual(
            report["selection_counts"]["no_entropy"],
            {"regenerate_hypotheses": 3},
        )

    def test_v24190_can_pass_while_deployed_policy_is_worse_than_random(self) -> None:
        states = [
            ([0.0, 0.1, 1.0], [0.0, 1.0, 0.5], [1.0, 0.5, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        report = evaluate_policy_value_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=settings(),
            policy_settings=policy_settings(),
        )
        self.assertTrue(report["parent_v24190_gate_replay"]["passed"])
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["passed"])
        self.assertAlmostEqual(
            report["policy_value"]["full_selected_value"]["estimate"], 0.1
        )
        self.assertLess(
            report["policy_value"][
                "full_minus_uniform_random_action_value"
            ]["estimate"],
            0.0,
        )
        self.assertAlmostEqual(
            report["oracle_regret"]["full_oracle_regret"]["estimate"], 0.9
        )

    def test_perfect_policy_passes_parent_and_policy_value_gate(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.1, 0.2, 0.9], [0.9, 0.8, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        report = evaluate_policy_value_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=settings(),
            policy_settings=policy_settings(),
        )
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["passed"])
        self.assertTrue(report["parent_v24190_gate_replay"]["passed"])
        self.assertEqual(report["selection_counts"]["full"], {"falsify_anchor": 3})
        self.assertEqual(
            report["top1_oracle_hit"]["full_top1_oracle_hit"]["estimate"],
            1.0,
        )
        self.assertGreater(
            report["simultaneous_policy_value_advantage"][
                "shared_cluster_bootstrap_minimum_95ci"
            ]["lower"],
            0.0,
        )

    def test_correct_stop_alone_does_not_claim_action_value(self) -> None:
        states = [
            ([-0.3, -0.2, -0.1], [-0.3, -0.2, -0.1], [0.9, 0.8, 0.7])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(
            states, entropy_positive=False
        )
        report = evaluate_policy_value_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=settings(
                minimum_entropy_increase_risk_decrease_bundles=0,
                minimum_entropy_increase_risk_decrease_task_clusters=0,
            ),
            policy_settings=policy_settings(),
        )
        self.assertEqual(report["selection_counts"]["full"], {"stop": 3})
        self.assertEqual(
            report["policy_value"]["full_selected_value_over_stop"]["estimate"],
            0.0,
        )
        self.assertFalse(report["passed"])

    def test_zero_predicted_cost_fails_policy_evaluability(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.1, 0.2, 0.9], [0.9, 0.8, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        for row in predictions["predictions"]:
            row["predicted_action_system_tokens"] = 0
            row.pop("prediction_sha256")
            from src.deepwide_agent.v24123_release import object_sha256

            row["prediction_sha256"] = object_sha256(row)
        predictions.pop("seal_sha256")
        from src.deepwide_agent.v24123_release import object_sha256

        predictions["seal_sha256"] = object_sha256(predictions)
        report = evaluate_policy_value_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=settings(),
            policy_settings=policy_settings(),
        )
        self.assertEqual(report["status"], "not_evaluable")
        self.assertEqual(
            report["nonpositive_predicted_or_actual_cost_checkpoints"], 3
        )
        self.assertFalse(report["passed"])


if __name__ == "__main__":
    unittest.main()
