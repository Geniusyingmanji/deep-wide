from __future__ import annotations

import unittest

from src.deepwide_agent.v24123_release import object_sha256
from src.deepwide_agent.v24192_abstain_aware_gate2a import (
    DEFAULT_ABSTAIN_SETTINGS,
    branch_decision,
    evaluate_abstain_aware_gate2a,
    required_signal_available,
)
from tests.test_v24161_strict_gate2a import fixture, settings
from tests.test_v24191_policy_value_gate2a import no_entropy_costs, policy_settings


def abstain_settings(**updates: object) -> dict:
    value = dict(DEFAULT_ABSTAIN_SETTINGS)
    value.update(
        {
            "minimum_comparable_checkpoints": 3,
            "minimum_independent_task_clusters": 3,
            "minimum_full_signal_available_checkpoints": 3,
            "minimum_full_signal_available_task_clusters": 3,
            "bootstrap_resamples": 200,
        }
    )
    value.update(updates)
    return value


def set_feature_availability(
    manifest: dict,
    aggregates: list[dict],
    prediction_seal: dict,
    **values: float,
) -> None:
    for bundle in manifest["bundles"]:
        features = bundle["pre_action_features"]
        features.update(values)
        bundle["pre_action_features_sha256"] = object_sha256(features)
    manifest.pop("manifest_sha256")
    manifest["manifest_sha256"] = object_sha256(manifest)
    for row in aggregates:
        row["job_manifest_sha256"] = manifest["manifest_sha256"]
        row.pop("aggregate_sha256")
        row["aggregate_sha256"] = object_sha256(row)
    prediction_seal["job_manifest_sha256"] = manifest["manifest_sha256"]
    prediction_seal.pop("seal_sha256")
    prediction_seal["seal_sha256"] = object_sha256(prediction_seal)


class V24192AbstainAwareGate2ATests(unittest.TestCase):
    def test_exact_branch_specific_missing_signal_rules(self) -> None:
        features = {
            "anchor_risk_proxy": 0.2,
            "anchor_risk_available": 1.0,
            "coverage_risk_proxy": 0.0,
            "coverage_risk_available": 0.0,
            "row_eligibility_risk_proxy": 0.3,
            "row_eligibility_risk_available": 1.0,
            "cell_value_risk_proxy": 0.0,
            "cell_value_risk_available": 0.0,
            "anchor_normalized_entropy": 0.0,
            "anchor_entropy_available": 0.0,
        }
        self.assertFalse(
            required_signal_available(features, context="anchor", branch="full")
        )
        self.assertTrue(
            required_signal_available(
                features, context="anchor", branch="no_entropy"
            )
        )
        self.assertFalse(
            required_signal_available(features, context="late_0", branch="full")
        )
        self.assertTrue(
            required_signal_available(features, context="late_1", branch="full")
        )

    def test_abstain_is_distinct_from_stop(self) -> None:
        scores = {"first": 0.4, "second": 0.3, "third": 0.2}
        tokens = {"first": 100, "second": 100, "third": 100}
        missing = {
            "anchor_risk_proxy": 0.0,
            "anchor_risk_available": 0.0,
            "coverage_risk_proxy": 0.0,
            "coverage_risk_available": 0.0,
            "row_eligibility_risk_proxy": 0.0,
            "row_eligibility_risk_available": 0.0,
            "cell_value_risk_proxy": 0.0,
            "cell_value_risk_available": 0.0,
            "anchor_normalized_entropy": 0.0,
            "anchor_entropy_available": 0.0,
        }
        self.assertEqual(
            branch_decision(
                scores,
                tokens,
                missing,
                context="anchor",
                branch="full",
                action_order=("first", "second", "third"),
            ),
            ("abstain", None),
        )
        available = dict(missing)
        available.update(
            anchor_risk_proxy=0.2,
            anchor_risk_available=1.0,
            anchor_normalized_entropy=0.3,
            anchor_entropy_available=1.0,
        )
        self.assertEqual(
            branch_decision(
                {key: -value for key, value in scores.items()},
                tokens,
                available,
                context="anchor",
                branch="full",
                action_order=("first", "second", "third"),
            ),
            ("stop", None),
        )

    def test_v24191_missing_entropy_false_pass_is_rejected(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.1, 0.2, 0.9], [0.9, 0.8, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        set_feature_availability(
            manifest,
            aggregates,
            predictions,
            anchor_normalized_entropy=0.0,
            anchor_entropy_available=0.0,
        )
        report = evaluate_abstain_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=settings(),
            policy_settings=policy_settings(),
            abstain_settings=abstain_settings(),
        )
        self.assertTrue(report["parent_v24191_gate_replay"]["passed"])
        self.assertEqual(report["status"], "not_evaluable")
        self.assertFalse(report["passed"])
        self.assertEqual(report["decision_counts"]["full"], {"abstain": 3})
        self.assertEqual(report["full_signal_available_checkpoints"], 0)
        self.assertEqual(
            report["policy_value"]["full_selected_value"]["estimate"], 0.0
        )
        self.assertEqual(
            report["policy_value"][
                "full_availability_matched_uniform_random_action_value"
            ]["estimate"],
            0.0,
        )
        self.assertEqual(
            report["oracle_regret"]["full_oracle_regret"]["estimate"], 0.0
        )

    def test_missing_entropy_penalizes_full_against_no_entropy(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.1, 0.2, 0.9], [0.1, 0.2, 0.9])
            for _ in range(4)
        ]
        manifest, aggregates, predictions = fixture(states)
        missing_cluster = sorted(
            {bundle["task_cluster_ref_sha256"] for bundle in manifest["bundles"]}
        )[0]
        for bundle in manifest["bundles"]:
            if bundle["task_cluster_ref_sha256"] == missing_cluster:
                features = bundle["pre_action_features"]
                features["anchor_normalized_entropy"] = 0.0
                features["anchor_entropy_available"] = 0.0
                bundle["pre_action_features_sha256"] = object_sha256(features)
        manifest.pop("manifest_sha256")
        manifest["manifest_sha256"] = object_sha256(manifest)
        for row in aggregates:
            row["job_manifest_sha256"] = manifest["manifest_sha256"]
            row.pop("aggregate_sha256")
            row["aggregate_sha256"] = object_sha256(row)
        predictions["job_manifest_sha256"] = manifest["manifest_sha256"]
        predictions.pop("seal_sha256")
        predictions["seal_sha256"] = object_sha256(predictions)
        report = evaluate_abstain_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=settings(),
            policy_settings=policy_settings(),
            abstain_settings=abstain_settings(
                minimum_full_signal_available_checkpoints=3,
                minimum_full_signal_available_task_clusters=3,
            ),
        )
        self.assertEqual(report["decision_counts"]["full"]["abstain"], 1)
        self.assertEqual(
            report["decision_counts"]["no_entropy"]["falsify_anchor"], 4
        )
        self.assertLess(
            report["policy_value"][
                "full_minus_no_entropy_policy_value"
            ]["estimate"],
            0.0,
        )
        self.assertFalse(report["passed"])

    def test_all_available_positive_policy_passes(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.1, 0.2, 0.9], [0.9, 0.8, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        report = evaluate_abstain_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=settings(),
            policy_settings=policy_settings(),
            abstain_settings=abstain_settings(),
        )
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["passed"])
        self.assertEqual(report["decision_counts"]["full"], {"falsify_anchor": 3})
        self.assertEqual(report["full_signal_available_checkpoints"], 3)
        self.assertGreater(
            report["simultaneous_policy_value_advantage"][
                "shared_cluster_bootstrap_minimum_95ci"
            ]["lower"],
            0.0,
        )
        self.assertGreater(
            report[
                "full_signal_available_simultaneous_action_value_advantage"
            ]["shared_cluster_bootstrap_minimum_95ci"]["lower"],
            0.0,
        )

    def test_overall_abstention_gain_cannot_hide_bad_available_state_policy(self) -> None:
        available = [
            ([0.0, 0.8, 1.0], [0.0, 0.9, 0.8], [-0.1, -0.2, 1.0])
            for _ in range(4)
        ]
        missing = [
            ([-0.9, -0.8, 0.9], [-0.9, -0.8, 0.9], [0.9, 0.8, -0.1])
            for _ in range(8)
        ]
        manifest, aggregates, predictions = fixture([*available, *missing])
        missing_clusters = {
            object_sha256(["cluster", index]) for index in range(4, 12)
        }
        for bundle in manifest["bundles"]:
            if bundle["task_cluster_ref_sha256"] in missing_clusters:
                features = bundle["pre_action_features"]
                features["anchor_normalized_entropy"] = 0.0
                features["anchor_entropy_available"] = 0.0
                bundle["pre_action_features_sha256"] = object_sha256(features)
        manifest.pop("manifest_sha256")
        manifest["manifest_sha256"] = object_sha256(manifest)
        for row in aggregates:
            row["job_manifest_sha256"] = manifest["manifest_sha256"]
            row.pop("aggregate_sha256")
            row["aggregate_sha256"] = object_sha256(row)
        predictions["job_manifest_sha256"] = manifest["manifest_sha256"]
        predictions.pop("seal_sha256")
        predictions["seal_sha256"] = object_sha256(predictions)
        report = evaluate_abstain_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=settings(
                minimum_comparable_checkpoints=12,
                minimum_rank_evaluable_checkpoints=12,
                minimum_independent_task_clusters=12,
                minimum_valid_records_per_active_action=12,
                minimum_entropy_increase_risk_decrease_bundles=12,
                minimum_entropy_increase_risk_decrease_task_clusters=12,
                bootstrap_resamples=500,
            ),
            policy_settings=policy_settings(
                minimum_comparable_checkpoints=12,
                minimum_independent_task_clusters=12,
                bootstrap_resamples=500,
            ),
            abstain_settings=abstain_settings(
                minimum_comparable_checkpoints=12,
                minimum_independent_task_clusters=12,
                minimum_full_signal_available_checkpoints=4,
                minimum_full_signal_available_task_clusters=4,
                bootstrap_resamples=500,
            ),
        )
        self.assertTrue(report["parent_v24191_gate_replay"]["passed"])
        self.assertGreater(
            report["simultaneous_policy_value_advantage"][
                "shared_cluster_bootstrap_minimum_95ci"
            ]["lower"],
            0.0,
        )
        self.assertLess(
            report[
                "full_signal_available_simultaneous_action_value_advantage"
            ]["shared_cluster_bootstrap_minimum_95ci"]["lower"],
            0.0,
        )
        self.assertFalse(report["policy_value_conditions_passed"])
        self.assertFalse(report["passed"])

    def test_missing_branch_does_not_require_its_predicted_cost(self) -> None:
        states = [
            ([0.1, 0.2, 0.9], [0.1, 0.2, 0.9], [0.9, 0.8, -0.1])
            for _ in range(3)
        ]
        manifest, aggregates, predictions = fixture(states)
        set_feature_availability(
            manifest,
            aggregates,
            predictions,
            anchor_risk_proxy=0.0,
            anchor_risk_available=0.0,
            anchor_normalized_entropy=0.0,
            anchor_entropy_available=0.0,
        )
        for row in predictions["predictions"]:
            row["predicted_action_system_tokens"] = 0
            row.pop("prediction_sha256")
            row["prediction_sha256"] = object_sha256(row)
        predictions.pop("seal_sha256")
        predictions["seal_sha256"] = object_sha256(predictions)
        costs = {row["bundle_sha256"]: 0 for row in predictions["predictions"]}
        report = evaluate_abstain_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            costs,
            parent_settings=settings(),
            policy_settings=policy_settings(),
            abstain_settings=abstain_settings(),
        )
        self.assertEqual(
            report["nonpositive_required_predicted_cost_checkpoints"], 0
        )
        self.assertEqual(report["decision_counts"]["full"], {"abstain": 3})
        self.assertEqual(report["status"], "not_evaluable")


if __name__ == "__main__":
    unittest.main()
