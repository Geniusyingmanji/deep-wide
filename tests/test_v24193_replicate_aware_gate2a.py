from __future__ import annotations

import unittest

from src.deepwide_agent.v24123_release import object_sha256
from src.deepwide_agent.v24193_replicate_aware_gate2a import (
    DEFAULT_REPLICATE_SETTINGS,
    evaluate_replicate_aware_gate2a,
)
from tests.test_v24161_strict_gate2a import fixture, settings
from tests.test_v24191_policy_value_gate2a import no_entropy_costs, policy_settings
from tests.test_v24192_abstain_aware_gate2a import abstain_settings


def replicate_settings(**updates: object) -> dict:
    value = dict(DEFAULT_REPLICATE_SETTINGS)
    value.update(
        {
            "minimum_independent_task_clusters": 12,
            "minimum_full_signal_available_task_clusters": 12,
            "bootstrap_resamples": 1000,
        }
    )
    value.update(updates)
    return value


def parent_settings() -> dict:
    return settings(
        minimum_comparable_checkpoints=12,
        minimum_rank_evaluable_checkpoints=12,
        minimum_independent_task_clusters=12,
        minimum_valid_records_per_active_action=12,
        minimum_entropy_increase_risk_decrease_bundles=12,
        minimum_entropy_increase_risk_decrease_task_clusters=12,
        bootstrap_resamples=500,
    )


def parent_policy_settings() -> dict:
    return policy_settings(
        minimum_comparable_checkpoints=12,
        minimum_independent_task_clusters=12,
        bootstrap_resamples=500,
    )


def parent_abstain_settings() -> dict:
    return abstain_settings(
        minimum_comparable_checkpoints=12,
        minimum_independent_task_clusters=12,
        minimum_full_signal_available_checkpoints=12,
        minimum_full_signal_available_task_clusters=12,
        bootstrap_resamples=500,
    )


def set_replicates(
    manifest: dict,
    aggregates: list[dict],
    *,
    selected: list[float],
) -> None:
    action_by_bundle = {
        bundle["bundle_sha256"]: bundle["action"]
        for bundle in manifest["bundles"]
    }
    for row in aggregates:
        values = (
            selected
            if action_by_bundle[row["bundle_sha256"]] == "falsify_anchor"
            else [0.0, 0.0, 0.0]
        )
        row["replicate_signed_task_contribution"] = list(values)
        row["mean_signed_task_contribution"] = round(sum(values) / 3.0, 12)
        row.pop("aggregate_sha256")
        row["aggregate_sha256"] = object_sha256(row)


class V24193ReplicateAwareGate2ATests(unittest.TestCase):
    def evaluate(self, selected: list[float]) -> dict:
        mean = round(sum(selected) / 3.0, 12)
        states = [
            ([0.0, 0.0, mean], [0.0, 0.0, mean], [0.9, 0.8, -0.1])
            for _ in range(12)
        ]
        manifest, aggregates, predictions = fixture(states)
        set_replicates(manifest, aggregates, selected=selected)
        return evaluate_replicate_aware_gate2a(
            manifest,
            aggregates,
            predictions,
            no_entropy_costs(predictions),
            parent_settings=parent_settings(),
            policy_settings=parent_policy_settings(),
            abstain_settings=parent_abstain_settings(),
            replicate_settings=replicate_settings(),
        )

    def test_noisy_replicates_reject_parent_mean_only_false_pass(self) -> None:
        report = self.evaluate([-1.0, 0.4, 1.0])
        self.assertTrue(report["parent_v24192_gate_replay"]["passed"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["status"], "fail")
        parent_lower = report["parent_v24192_gate_replay"][
            "simultaneous_policy_value_advantage"
        ]["shared_cluster_bootstrap_minimum_95ci"]["lower"]
        hierarchical_lower = report[
            "hierarchical_simultaneous_policy_value_advantage"
        ]["hierarchical_shared_minimum_95ci"]["lower"]
        self.assertGreater(parent_lower, 0.0)
        self.assertLess(hierarchical_lower, 0.0)

    def test_stable_positive_replicates_pass_both_hierarchical_gates(self) -> None:
        report = self.evaluate([0.8, 0.9, 1.0])
        self.assertTrue(report["parent_v24192_gate_replay"]["passed"])
        self.assertTrue(report["passed"])
        self.assertEqual(report["status"], "pass")
        self.assertGreater(
            report["hierarchical_simultaneous_policy_value_advantage"]
            ["hierarchical_shared_minimum_95ci"]["lower"],
            0.0,
        )
        self.assertGreater(
            report[
                "full_signal_available_hierarchical_simultaneous_action_value_advantage"
            ]["hierarchical_shared_minimum_95ci"]["lower"],
            0.0,
        )

    def test_observed_estimands_exactly_replay_parent_means(self) -> None:
        report = self.evaluate([0.7, 0.8, 0.9])
        parent = report["parent_v24192_gate_replay"]
        for child_key, parent_key in (
            (
                "hierarchical_simultaneous_policy_value_advantage",
                "simultaneous_policy_value_advantage",
            ),
            (
                "full_signal_available_hierarchical_simultaneous_action_value_advantage",
                "full_signal_available_simultaneous_action_value_advantage",
            ),
        ):
            self.assertEqual(
                report[child_key]["individual_estimates"],
                parent[parent_key]["individual_estimates"],
            )

    def test_replicate_settings_fail_closed(self) -> None:
        states = [
            ([0.0, 0.0, 0.9], [0.0, 0.0, 0.9], [0.9, 0.8, -0.1])
            for _ in range(12)
        ]
        manifest, aggregates, predictions = fixture(states)
        with self.assertRaisesRegex(ValueError, "replicate settings"):
            evaluate_replicate_aware_gate2a(
                manifest,
                aggregates,
                predictions,
                no_entropy_costs(predictions),
                parent_settings=parent_settings(),
                policy_settings=parent_policy_settings(),
                abstain_settings=parent_abstain_settings(),
                replicate_settings=replicate_settings(
                    required_replicates_per_action=2
                ),
            )


if __name__ == "__main__":
    unittest.main()
