from __future__ import annotations

import copy
import hashlib
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24230_mica_credit_baseline import (  # noqa: E402
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NORMALIZATION_EPSILON,
    PRODUCTION_PACKAGE_AUTHORIZED,
    build_mica_mixed_advantage_batch,
    build_mica_policy,
    build_potential_transition,
    object_sha256,
    reject_privileged_runtime_metadata,
    validate_mica_mixed_advantage_batch,
    validate_mica_policy,
    validate_potential_transition,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def policy(*, gamma: float = 0.5, alpha: float = 0.25) -> dict[str, object]:
    return build_mica_policy(
        selection_protocol_sha256=digest("selection-protocol"),
        potential_definition_sha256=digest("potential-definition"),
        dense_feedback_protocol_sha256=digest("dense-feedback-protocol"),
        discount_factor=gamma,
        turn_return_weight=alpha,
    )


def trajectory(
    frozen: dict[str, object],
    *,
    name: str,
    potentials: list[float],
    prompt: str = "prompt-group",
    scope: str = "preregistered_training",
    initial_state: str = "common-initial-state",
    calls: int = 1,
    input_tokens: int = 10,
    output_tokens: int = 2,
) -> list[dict[str, object]]:
    if len(potentials) < 2:
        raise ValueError("fixture trajectory needs at least one transition")
    values: list[dict[str, object]] = []
    before_state = digest(initial_state)
    for turn_index, (before, after) in enumerate(
        zip(potentials, potentials[1:]), start=1
    ):
        after_state = digest(f"{name}-state-{turn_index}")
        values.append(
            build_potential_transition(
                policy=frozen,
                prompt_group_ref_sha256=digest(prompt),
                trajectory_ref_sha256=digest(f"trajectory-{name}"),
                segment_ref_sha256=digest(f"segment-{name}-{turn_index}"),
                turn_index=turn_index,
                state_before_projection_sha256=before_state,
                state_after_projection_sha256=after_state,
                dense_feedback_receipt_sha256=digest(
                    f"dense-feedback-{name}-{turn_index}"
                ),
                previous_potential=before,
                current_potential=after,
                dense_feedback_calls=calls,
                dense_feedback_input_tokens=input_tokens,
                dense_feedback_output_tokens=output_tokens,
                data_scope=scope,
            )
        )
        before_state = after_state
    return values


def two_by_two(
    frozen: dict[str, object],
) -> list[dict[str, object]]:
    return trajectory(frozen, name="a", potentials=[10.0, 8.0, 7.0]) + trajectory(
        frozen,
        name="b",
        potentials=[10.0, 9.0, 5.0],
    )


def zscore(value: float, mean: float, population_std: float) -> float:
    return (value - mean) / (population_std + NORMALIZATION_EPSILON)


class V24230MicaCreditBaselineTests(unittest.TestCase):
    def test_paper_equations_returns_population_statistics_and_mixture(self) -> None:
        frozen = policy(gamma=0.5, alpha=0.25)
        transitions = two_by_two(frozen)
        batch = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("formula-batch"),
            transitions=transitions,
        )
        validate_mica_mixed_advantage_batch(
            batch,
            policy=frozen,
            batch_ref_sha256=digest("formula-batch"),
            transitions=transitions,
        )

        by_segment = {
            row["segment_ref_sha256"]: row for row in batch["normalized_records"]
        }
        expected_returns = {
            digest("segment-a-1"): 2.5,
            digest("segment-a-2"): 1.0,
            digest("segment-b-1"): 3.0,
            digest("segment-b-2"): 4.0,
        }
        for segment, expected in expected_returns.items():
            self.assertAlmostEqual(by_segment[segment]["monte_carlo_return"], expected)

        self.assertEqual(
            batch["turn_statistics"],
            [
                {
                    "turn_index": 1,
                    "eligible_trajectory_count": 2,
                    "return_mean": 2.75,
                    "return_population_std": 0.25,
                },
                {
                    "turn_index": 2,
                    "eligible_trajectory_count": 2,
                    "return_mean": 2.5,
                    "return_population_std": 1.5,
                },
            ],
        )
        group_std = math.sqrt(1.5)
        self.assertEqual(batch["group_statistics"]["immediate_reward_count"], 4)
        self.assertAlmostEqual(batch["group_statistics"]["immediate_reward_mean"], 2.0)
        self.assertAlmostEqual(
            batch["group_statistics"]["immediate_reward_population_std"],
            group_std,
        )
        record = by_segment[digest("segment-a-2")]
        expected_turn = zscore(1.0, 2.5, 1.5)
        expected_group = zscore(1.0, 2.0, group_std)
        self.assertAlmostEqual(record["turn_normalized_return_advantage"], expected_turn)
        self.assertAlmostEqual(
            record["group_normalized_immediate_advantage"], expected_group
        )
        self.assertAlmostEqual(
            record["mixed_advantage"], 0.25 * expected_turn + 0.75 * expected_group
        )

    def test_discount_and_convex_weight_boundaries(self) -> None:
        with self.assertRaisesRegex(ValueError, "discount factor must be positive"):
            policy(gamma=0.0)
        for bad in (-0.1, 1.1, float("inf"), float("nan"), True):
            with self.subTest(gamma=bad):
                with self.assertRaises(ValueError):
                    policy(gamma=bad)  # type: ignore[arg-type]

        gamma_one = policy(gamma=1.0, alpha=0.5)
        gamma_batch = build_mica_mixed_advantage_batch(
            policy=gamma_one,
            batch_ref_sha256=digest("gamma-one"),
            transitions=two_by_two(gamma_one),
        )
        returns = {
            row["segment_ref_sha256"]: row["monte_carlo_return"]
            for row in gamma_batch["normalized_records"]
        }
        self.assertEqual(returns[digest("segment-a-1")], 3.0)
        self.assertEqual(returns[digest("segment-b-1")], 5.0)

        for alpha in (0.0, 1.0):
            with self.subTest(alpha=alpha):
                frozen = policy(alpha=alpha)
                batch = build_mica_mixed_advantage_batch(
                    policy=frozen,
                    batch_ref_sha256=digest(f"alpha-{alpha}"),
                    transitions=two_by_two(frozen),
                )
                for row in batch["normalized_records"]:
                    expected = (
                        row["group_normalized_immediate_advantage"]
                        if alpha == 0.0
                        else row["turn_normalized_return_advantage"]
                    )
                    self.assertAlmostEqual(row["mixed_advantage"], expected)
        for bad in (-0.1, 1.1, float("inf"), float("nan"), True):
            with self.subTest(alpha=bad):
                with self.assertRaises(ValueError):
                    policy(alpha=bad)  # type: ignore[arg-type]

    def test_variable_horizon_uses_only_eligible_trajectories_per_turn(self) -> None:
        frozen = policy()
        transitions = trajectory(
            frozen, name="long", potentials=[10.0, 9.0, 8.0, 7.0]
        ) + trajectory(frozen, name="short", potentials=[10.0, 5.0])
        batch = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("variable-horizon"),
            transitions=transitions,
        )
        self.assertTrue(batch["variable_horizon_supported"])
        self.assertEqual(
            [row["eligible_trajectory_count"] for row in batch["turn_statistics"]],
            [2, 1, 1],
        )
        long_late = [
            row
            for row in batch["normalized_records"]
            if row["trajectory_ref_sha256"] == digest("trajectory-long")
            and row["turn_index"] > 1
        ]
        self.assertEqual(
            [row["turn_normalized_return_advantage"] for row in long_late],
            [0.0, 0.0],
        )

    def test_population_zero_variance_is_finite_and_uses_frozen_epsilon(self) -> None:
        frozen = policy()
        transitions = trajectory(
            frozen, name="same-a", potentials=[10.0, 9.0, 8.0]
        ) + trajectory(frozen, name="same-b", potentials=[10.0, 9.0, 8.0])
        batch = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("zero-variance"),
            transitions=transitions,
        )
        self.assertEqual(frozen["normalization_epsilon"], NORMALIZATION_EPSILON)
        self.assertEqual(batch["normalization_epsilon"], NORMALIZATION_EPSILON)
        self.assertEqual(
            batch["group_statistics"]["immediate_reward_population_std"], 0.0
        )
        for statistic in batch["turn_statistics"]:
            self.assertEqual(statistic["return_population_std"], 0.0)
        for row in batch["normalized_records"]:
            self.assertEqual(row["turn_normalized_return_advantage"], 0.0)
            self.assertEqual(row["group_normalized_immediate_advantage"], 0.0)
            self.assertEqual(row["mixed_advantage"], 0.0)
            self.assertTrue(math.isfinite(row["mixed_advantage"]))

    def test_input_order_does_not_change_the_canonical_batch(self) -> None:
        frozen = policy()
        transitions = two_by_two(frozen)
        forward = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("order-invariant"),
            transitions=transitions,
        )
        reverse = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("order-invariant"),
            transitions=list(reversed(transitions)),
        )
        self.assertEqual(forward, reverse)

    def test_consecutive_turn_state_potential_and_shared_start_are_enforced(self) -> None:
        frozen = policy()
        valid_a = trajectory(frozen, name="a", potentials=[10.0, 8.0, 7.0])
        valid_b = trajectory(frozen, name="b", potentials=[10.0, 9.0, 5.0])

        gap = [
            valid_a[0],
            build_potential_transition(
                policy=frozen,
                prompt_group_ref_sha256=digest("prompt-group"),
                trajectory_ref_sha256=digest("trajectory-a"),
                segment_ref_sha256=digest("segment-a-gap"),
                turn_index=3,
                state_before_projection_sha256=valid_a[0][
                    "state_after_projection_sha256"
                ],
                state_after_projection_sha256=digest("gap-after"),
                dense_feedback_receipt_sha256=digest("gap-feedback"),
                previous_potential=8.0,
                current_potential=7.0,
                dense_feedback_calls=1,
                dense_feedback_input_tokens=1,
                dense_feedback_output_tokens=1,
                data_scope="preregistered_training",
            ),
        ] + valid_b
        with self.assertRaisesRegex(ValueError, "turn indices are not consecutive"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("turn-gap"),
                transitions=gap,
            )

        wrong_state = trajectory(frozen, name="wrong-state", potentials=[10.0, 8.0])
        wrong_state += trajectory(
            frozen,
            name="wrong-state",
            potentials=[8.0, 7.0],
            initial_state="not-the-prior-state",
        )
        wrong_state[1]["turn_index"] = 2
        wrong_state[1]["segment_ref_sha256"] = digest("segment-wrong-state-2")
        wrong_state[1].pop("transition_sha256")
        wrong_state[1]["transition_sha256"] = object_sha256(wrong_state[1])
        with self.assertRaisesRegex(ValueError, "continuity failed"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("wrong-state"),
                transitions=wrong_state + valid_b,
            )

        wrong_potential = trajectory(
            frozen, name="wrong-potential", potentials=[10.0, 8.0]
        )
        second = trajectory(
            frozen,
            name="wrong-potential",
            potentials=[7.5, 7.0],
            initial_state="wrong-potential-state-1",
        )[0]
        second["turn_index"] = 2
        second["segment_ref_sha256"] = digest("segment-wrong-potential-2")
        second.pop("transition_sha256")
        second["transition_sha256"] = object_sha256(second)
        wrong_potential.append(second)
        with self.assertRaisesRegex(ValueError, "continuity failed"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("wrong-potential"),
                transitions=wrong_potential + valid_b,
            )

        different_start = trajectory(
            frozen,
            name="different-start",
            potentials=[11.0, 9.0],
            initial_state="different-initial-state",
        )
        with self.assertRaisesRegex(ValueError, "different starts"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("different-start"),
                transitions=valid_a + different_start,
            )

    def test_duplicate_mixed_prompt_protocol_and_scope_are_rejected(self) -> None:
        frozen = policy()
        transitions = two_by_two(frozen)
        with self.assertRaisesRegex(ValueError, "duplicate segment/transition"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("duplicate"),
                transitions=transitions + [transitions[0]],
            )

        other_prompt = trajectory(
            frozen, name="other-prompt", potentials=[10.0, 8.0], prompt="other"
        )
        with self.assertRaisesRegex(ValueError, "mixes prompt, protocol, or data scope"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("mixed-prompt"),
                transitions=trajectory(
                    frozen, name="one-prompt", potentials=[10.0, 9.0]
                )
                + other_prompt,
            )

        mixed_scope = trajectory(
            frozen, name="train", potentials=[10.0, 9.0]
        ) + trajectory(
            frozen,
            name="calibration",
            potentials=[10.0, 8.0],
            scope="preregistered_calibration",
        )
        with self.assertRaisesRegex(ValueError, "mixes prompt, protocol, or data scope"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("mixed-scope"),
                transitions=mixed_scope,
            )

        alternate = build_mica_policy(
            selection_protocol_sha256=digest("selection-protocol"),
            potential_definition_sha256=digest("potential-definition"),
            dense_feedback_protocol_sha256=digest("alternate-feedback-protocol"),
            discount_factor=0.5,
            turn_return_weight=0.25,
        )
        alternate_transition = trajectory(
            alternate, name="alternate", potentials=[10.0, 9.0]
        )
        with self.assertRaisesRegex(ValueError, "contract drifted"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("mixed-protocol"),
                transitions=trajectory(
                    frozen, name="primary", potentials=[10.0, 9.0]
                )
                + alternate_transition,
            )

    def test_privileged_nested_metadata_is_rejected_after_key_normalization(self) -> None:
        reject_privileged_runtime_metadata(
            {"visible": [{"objective_type": "enumeration"}]}
        )
        for forbidden in (
            {"safe": [{"question_type": "hidden"}]},
            {"safe": {"Ground-Truth": "hidden"}},
            {"safe": {"benchmark category": "hidden"}},
            {"safe": {"evaluator_score": 1.0}},
            {"safe": [{"reward": 1.0}]},
            {"safe": {"split": "test"}},
        ):
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(ValueError, "privileged runtime metadata"):
                    reject_privileged_runtime_metadata(forbidden)

    def test_tamper_and_reseal_cannot_change_policy_transition_or_batch(self) -> None:
        frozen = policy()
        transitions = two_by_two(frozen)
        batch = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("tamper"),
            transitions=transitions,
        )

        bad_policy = copy.deepcopy(frozen)
        bad_policy["source_paper_version"] = 99
        bad_policy.pop("policy_sha256")
        bad_policy["policy_sha256"] = object_sha256(bad_policy)
        with self.assertRaisesRegex(ValueError, "policy contract drifted"):
            validate_mica_policy(bad_policy)

        bad_transition = copy.deepcopy(transitions[0])
        bad_transition[
            "dense_feedback_semantic_correctness_independently_verified"
        ] = True
        bad_transition.pop("transition_sha256")
        bad_transition["transition_sha256"] = object_sha256(bad_transition)
        with self.assertRaisesRegex(ValueError, "transition contract drifted"):
            validate_potential_transition(bad_transition, policy=frozen)

        bad_batch = copy.deepcopy(batch)
        bad_batch["normalized_records"][0]["mixed_advantage"] = 99.0
        bad_batch.pop("batch_sha256")
        bad_batch["batch_sha256"] = object_sha256(bad_batch)
        with self.assertRaisesRegex(ValueError, "batch contract drifted"):
            validate_mica_mixed_advantage_batch(
                bad_batch,
                policy=frozen,
                batch_ref_sha256=digest("tamper"),
                transitions=transitions,
            )

    def test_costs_are_aggregated_over_every_valid_turn(self) -> None:
        frozen = policy()
        transitions = trajectory(
            frozen,
            name="cost-a",
            potentials=[10.0, 9.0, 8.0],
            calls=2,
            input_tokens=11,
            output_tokens=3,
        ) + trajectory(
            frozen,
            name="cost-b",
            potentials=[10.0, 7.0],
            calls=4,
            input_tokens=13,
            output_tokens=5,
        )
        batch = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("costs"),
            transitions=transitions,
        )
        self.assertEqual(
            batch["dense_feedback_cost"],
            {"calls": 8, "input_tokens": 35, "output_tokens": 11},
        )

    def test_exact_top_level_and_nested_schemas_reject_extra_fields(self) -> None:
        frozen = policy()
        transitions = two_by_two(frozen)
        batch = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("schemas"),
            transitions=transitions,
        )
        with self.assertRaisesRegex(ValueError, "policy schema is not exact"):
            validate_mica_policy({**frozen, "extra": False})
        with self.assertRaisesRegex(ValueError, "transition schema is not exact"):
            validate_potential_transition(
                {**transitions[0], "extra": False}, policy=frozen
            )
        with self.assertRaisesRegex(ValueError, "batch schema is not exact"):
            validate_mica_mixed_advantage_batch(
                {**batch, "extra": False},
                policy=frozen,
                batch_ref_sha256=digest("schemas"),
                transitions=transitions,
            )

        nested = copy.deepcopy(batch)
        nested["turn_statistics"][0]["extra"] = False
        nested.pop("batch_sha256")
        nested["batch_sha256"] = object_sha256(nested)
        with self.assertRaisesRegex(ValueError, "turn-statistic schema is not exact"):
            validate_mica_mixed_advantage_batch(
                nested,
                policy=frozen,
                batch_ref_sha256=digest("schemas"),
                transitions=transitions,
            )

    def test_non_mapping_transition_is_rejected_without_coercion(self) -> None:
        frozen = policy()
        valid = trajectory(frozen, name="valid", potentials=[10, 9])[0]
        with self.assertRaisesRegex(ValueError, "every transition must be a mapping"):
            build_mica_mixed_advantage_batch(
                policy=frozen,
                batch_ref_sha256=digest("non-mapping"),
                transitions=[valid, 1],  # type: ignore[list-item]
            )

    def test_build_only_authority_and_scientific_limits_are_all_explicit(self) -> None:
        frozen = policy()
        transitions = two_by_two(frozen)
        batch = build_mica_mixed_advantage_batch(
            policy=frozen,
            batch_ref_sha256=digest("authority"),
            transitions=transitions,
        )
        self.assertFalse(PRODUCTION_PACKAGE_AUTHORIZED)
        self.assertFalse(CREDIT_TRAINING_AUTHORIZED)
        self.assertFalse(BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED)
        self.assertFalse(LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED)
        self.assertFalse(frozen["production_package_authorized"])
        self.assertFalse(frozen["credit_training_authorized"])
        self.assertFalse(frozen["runtime_label_routing_used"])
        for transition_value in transitions:
            self.assertFalse(
                transition_value[
                    "benchmark_evaluator_gold_mapping_category_question_type_or_score_used"
                ]
            )
            self.assertFalse(
                transition_value[
                    "raw_prompt_state_observation_or_evaluator_payload_embedded"
                ]
            )
        for field in (
            "matched_state_rollout_used",
            "learned_critic_used",
            "dense_feedback_semantic_correctness_independently_verified",
            "potential_is_causal_state_value",
            "same_state_causal_identification",
            "independent_outer_target_used",
            "benchmark_metadata_available_to_forward",
            "runtime_forward_evaluator_or_credit_training_authorized",
        ):
            self.assertFalse(batch[field], field)


if __name__ == "__main__":
    unittest.main()
