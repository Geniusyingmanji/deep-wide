from __future__ import annotations

import copy
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24225_triage_role_baseline import (  # noqa: E402
    CREDIT_TRAINING_AUTHORIZED,
    MAX_CONTEXT_PAIRS_PER_SIDE,
    PRODUCTION_PACKAGE_AUTHORIZED,
    ROLE_CONSTANTS,
    build_credit_policy,
    build_outcome_advantage_receipt,
    build_role_judgment,
    build_role_typed_credit,
    build_whitened_credit_batch,
    object_sha256,
    reject_role_judge_privileged_metadata,
    validate_credit_policy,
    validate_outcome_advantage_receipt,
    validate_role_judgment,
    validate_role_typed_credit,
    validate_whitened_credit_batch,
)


def digest(character: str) -> str:
    return character * 64


def policy(*, weight: float = 0.4) -> dict[str, object]:
    return build_credit_policy(
        selection_protocol_sha256=digest("a"),
        mixing_weight=weight,
    )


def judgment(
    *,
    segment: str = "1",
    trajectory: str = "2",
    role: str = "useful_exploration",
    previous: int = 5,
    following: int = 5,
) -> dict[str, object]:
    return build_role_judgment(
        segment_ref_sha256=digest(segment),
        trajectory_ref_sha256=digest(trajectory),
        visible_task_prompt_projection_sha256=digest("3"),
        judge_context_projection_sha256=digest("4"),
        judge_model_sha256=digest("5"),
        rubric_sha256=digest("6"),
        previous_action_observation_pair_count=previous,
        future_action_observation_pair_count=following,
        assigned_role=role,
        judge_input_tokens=120,
        judge_output_tokens=8,
    )


def outcome(
    *,
    segment: str = "1",
    trajectory: str = "2",
    advantage: float = 0.25,
) -> dict[str, object]:
    return build_outcome_advantage_receipt(
        segment_ref_sha256=digest(segment),
        trajectory_ref_sha256=digest(trajectory),
        group_ref_sha256=digest("7"),
        verifier_protocol_sha256=digest("8"),
        verifier_outcome_ref_sha256=digest("9"),
        outcome_advantage=advantage,
    )


def credit(
    *,
    segment: str = "1",
    trajectory: str = "2",
    role: str = "useful_exploration",
    advantage: float = 0.25,
    weight: float = 0.4,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    frozen = policy(weight=weight)
    typed = judgment(segment=segment, trajectory=trajectory, role=role)
    terminal = outcome(
        segment=segment,
        trajectory=trajectory,
        advantage=advantage,
    )
    record = build_role_typed_credit(
        policy=frozen,
        judgment=typed,
        outcome_receipt=terminal,
    )
    return frozen, typed, terminal, record


class V24225TriageRoleBaselineTests(unittest.TestCase):
    def test_role_constants_and_formula_match_triage_v3(self) -> None:
        self.assertEqual(
            ROLE_CONSTANTS,
            {
                "decisive_progress": 1.0,
                "useful_exploration": 0.5,
                "no_progress_infrastructure": -0.1,
                "regression": -0.5,
            },
        )
        frozen, typed, terminal, record = credit(
            role="useful_exploration",
            advantage=0.3,
            weight=0.4,
        )
        self.assertAlmostEqual(record["role_correction"], 0.2)
        self.assertAlmostEqual(record["unwhitened_role_typed_credit"], 0.5)
        validate_role_typed_credit(
            record,
            policy=frozen,
            judgment=typed,
            outcome_receipt=terminal,
        )

    def test_each_role_maps_to_the_frozen_constant(self) -> None:
        for name, expected in ROLE_CONSTANTS.items():
            with self.subTest(role=name):
                _, _, _, record = credit(role=name, advantage=0.0)
                self.assertEqual(record["role_constant"], expected)
                self.assertAlmostEqual(record["role_correction"], 0.4 * expected)

    def test_additive_baseline_can_reverse_small_outcome_advantage(self) -> None:
        _, _, _, negative = credit(
            role="regression",
            advantage=0.05,
            weight=0.4,
        )
        self.assertAlmostEqual(negative["unwhitened_role_typed_credit"], -0.15)
        self.assertFalse(negative["verifier_direction_preserved"])

        _, _, _, positive = credit(
            role="decisive_progress",
            advantage=-0.1,
            weight=0.4,
        )
        self.assertAlmostEqual(positive["unwhitened_role_typed_credit"], 0.3)
        self.assertFalse(positive["verifier_direction_preserved"])

    def test_policy_freezes_training_only_selection_and_no_authority(self) -> None:
        value = policy()
        validate_credit_policy(value)
        self.assertEqual(
            value["mixing_weight_selection_scope"],
            "preregistered_training_split_only_before_heldout_evaluation",
        )
        self.assertFalse(value["test_or_benchmark_outcome_used_for_selection"])
        self.assertFalse(value["runtime_label_routing_used"])
        self.assertFalse(value["production_package_authorized"])
        self.assertFalse(value["credit_training_authorized"])
        self.assertFalse(PRODUCTION_PACKAGE_AUTHORIZED)
        self.assertFalse(CREDIT_TRAINING_AUTHORIZED)

    def test_policy_rejects_bad_weight_protocol_and_nonfinite_values(self) -> None:
        for bad in (-0.01, 1.01, float("inf"), float("nan"), True):
            with self.subTest(weight=bad):
                with self.assertRaises(ValueError):
                    build_credit_policy(
                        selection_protocol_sha256=digest("a"),
                        mixing_weight=bad,
                    )
        with self.assertRaisesRegex(ValueError, "selection protocol"):
            build_credit_policy(
                selection_protocol_sha256="not-a-hash",
                mixing_weight=0.4,
            )

    def test_role_judge_is_bounded_to_five_pairs_per_side(self) -> None:
        value = judgment(previous=MAX_CONTEXT_PAIRS_PER_SIDE, following=5)
        validate_role_judgment(value)
        self.assertFalse(value["final_verifier_outcome_available_to_judge"])
        self.assertFalse(
            value[
                "evaluator_gold_mapping_category_question_type_or_score_available_to_judge"
            ]
        )
        for previous, following in ((6, 0), (0, 6), (-1, 0), (0, -1)):
            with self.subTest(previous=previous, following=following):
                with self.assertRaises(ValueError):
                    judgment(previous=previous, following=following)

    def test_role_judge_rejects_unknown_role_and_privileged_nested_metadata(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown role"):
            judgment(role="outcome_success")
        for forbidden in (
            {"safe": [{"question_type": "hidden"}]},
            {"safe": {"final_outcome": 1}},
            {"safe": {"evaluator_score": 0.9}},
            {"safe": {"reward": 1}},
        ):
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(ValueError, "privileged metadata rejected"):
                    reject_role_judge_privileged_metadata(forbidden)

    def test_outcome_receipt_is_post_terminal_and_separated(self) -> None:
        value = outcome(advantage=-1.25)
        validate_outcome_advantage_receipt(value)
        self.assertTrue(value["trajectory_terminal"])
        self.assertTrue(value["verifier_joined_post_terminal"])
        self.assertFalse(value["role_judgment_or_role_label_available_to_verifier"])
        self.assertFalse(
            value["outcome_reward_or_evaluator_payload_available_to_role_judge"]
        )
        self.assertFalse(value["benchmark_metadata_available_to_forward"])
        self.assertFalse(value["raw_verifier_payload_embedded"])

    def test_outcome_receipt_rejects_nonfinite_and_unbounded_advantage(self) -> None:
        for bad in (-100.01, 100.01, float("inf"), float("nan"), True):
            with self.subTest(advantage=bad):
                with self.assertRaises(ValueError):
                    outcome(advantage=bad)

    def test_judgment_and_outcome_must_bind_same_segment_and_trajectory(self) -> None:
        frozen = policy()
        with self.assertRaisesRegex(ValueError, "identities differ"):
            build_role_typed_credit(
                policy=frozen,
                judgment=judgment(segment="1", trajectory="2"),
                outcome_receipt=outcome(segment="a", trajectory="2"),
            )
        with self.assertRaisesRegex(ValueError, "identities differ"):
            build_role_typed_credit(
                policy=frozen,
                judgment=judgment(segment="1", trajectory="2"),
                outcome_receipt=outcome(segment="1", trajectory="b"),
            )

    def test_credit_discloses_judge_cost_and_noncausal_scope(self) -> None:
        _, _, _, record = credit()
        self.assertEqual(
            record["judge_cost"],
            {"calls": 1, "input_tokens": 120, "output_tokens": 8},
        )
        self.assertTrue(record["judge_and_verifier_sources_separated"])
        self.assertFalse(record["role_typing_is_causal_identification"])
        self.assertFalse(record["runtime_forward_evaluator_or_training_authorized"])

    def test_tampered_and_resealed_policy_judgment_outcome_and_credit_fail(self) -> None:
        frozen, typed, terminal, record = credit()

        bad_policy = copy.deepcopy(frozen)
        bad_policy["role_constants"]["useful_exploration"] = 0.75
        bad_policy.pop("policy_sha256")
        bad_policy["policy_sha256"] = object_sha256(bad_policy)
        with self.assertRaisesRegex(ValueError, "policy contract drifted"):
            validate_credit_policy(bad_policy)

        bad_judgment = copy.deepcopy(typed)
        bad_judgment["final_verifier_outcome_available_to_judge"] = True
        bad_judgment.pop("judgment_sha256")
        bad_judgment["judgment_sha256"] = object_sha256(bad_judgment)
        with self.assertRaisesRegex(ValueError, "judgment contract drifted"):
            validate_role_judgment(bad_judgment)

        bad_outcome = copy.deepcopy(terminal)
        bad_outcome["outcome_reward_or_evaluator_payload_available_to_role_judge"] = True
        bad_outcome.pop("receipt_sha256")
        bad_outcome["receipt_sha256"] = object_sha256(bad_outcome)
        with self.assertRaisesRegex(ValueError, "outcome receipt contract drifted"):
            validate_outcome_advantage_receipt(bad_outcome)

        bad_record = copy.deepcopy(record)
        bad_record["unwhitened_role_typed_credit"] = 99.0
        bad_record.pop("record_sha256")
        bad_record["record_sha256"] = object_sha256(bad_record)
        with self.assertRaisesRegex(ValueError, "credit contract drifted"):
            validate_role_typed_credit(
                bad_record,
                policy=frozen,
                judgment=typed,
                outcome_receipt=terminal,
            )

    def test_exact_schemas_reject_extra_keys(self) -> None:
        frozen, typed, terminal, record = credit()
        for validator, value, kwargs in (
            (validate_credit_policy, frozen, {}),
            (validate_role_judgment, typed, {}),
            (validate_outcome_advantage_receipt, terminal, {}),
            (
                validate_role_typed_credit,
                record,
                {
                    "policy": frozen,
                    "judgment": typed,
                    "outcome_receipt": terminal,
                },
            ),
        ):
            with self.subTest(validator=validator.__name__):
                with self.assertRaisesRegex(ValueError, "schema is not exact"):
                    validator({**value, "extra": False}, **kwargs)

    def test_batch_whitening_matches_population_zscore(self) -> None:
        frozen = policy()
        records = []
        for segment, role, advantage in (
            ("1", "decisive_progress", 0.2),
            ("2", "useful_exploration", 0.1),
            ("3", "regression", -0.2),
        ):
            typed = judgment(segment=segment, role=role)
            terminal = outcome(segment=segment, advantage=advantage)
            records.append(
                build_role_typed_credit(
                    policy=frozen,
                    judgment=typed,
                    outcome_receipt=terminal,
                )
            )
        batch = build_whitened_credit_batch(
            policy=frozen,
            batch_ref_sha256=digest("b"),
            credit_records=records,
        )
        validate_whitened_credit_batch(
            batch,
            policy=frozen,
            batch_ref_sha256=digest("b"),
            credit_records=records,
        )
        whitened = [
            row["whitened_role_typed_credit"]
            for row in batch["whitened_records"]
        ]
        self.assertAlmostEqual(sum(whitened), 0.0, places=7)
        self.assertTrue(math.isfinite(batch["unwhitened_population_std"]))
        self.assertEqual(batch["record_count"], 3)
        self.assertFalse(batch["runtime_forward_evaluator_or_training_authorized"])

    def test_batch_whitening_sorts_records_and_rejects_duplicates(self) -> None:
        frozen = policy()
        record_a = build_role_typed_credit(
            policy=frozen,
            judgment=judgment(segment="a"),
            outcome_receipt=outcome(segment="a"),
        )
        record_b = build_role_typed_credit(
            policy=frozen,
            judgment=judgment(segment="b", role="regression"),
            outcome_receipt=outcome(segment="b"),
        )
        batch = build_whitened_credit_batch(
            policy=frozen,
            batch_ref_sha256=digest("c"),
            credit_records=[record_b, record_a],
        )
        self.assertEqual(
            [row["segment_ref_sha256"] for row in batch["whitened_records"]],
            [digest("a"), digest("b")],
        )
        with self.assertRaisesRegex(ValueError, "duplicated"):
            build_whitened_credit_batch(
                policy=frozen,
                batch_ref_sha256=digest("c"),
                credit_records=[record_a, record_a],
            )
        with self.assertRaisesRegex(ValueError, "at least two"):
            build_whitened_credit_batch(
                policy=frozen,
                batch_ref_sha256=digest("c"),
                credit_records=[record_a],
            )

    def test_tampered_whitened_batch_fails_even_when_resealed(self) -> None:
        frozen = policy()
        records = [
            build_role_typed_credit(
                policy=frozen,
                judgment=judgment(segment=segment),
                outcome_receipt=outcome(segment=segment),
            )
            for segment in ("a", "b")
        ]
        batch = build_whitened_credit_batch(
            policy=frozen,
            batch_ref_sha256=digest("c"),
            credit_records=records,
        )
        bad = copy.deepcopy(batch)
        bad["whitened_records"][0]["whitened_role_typed_credit"] = 100.0
        bad.pop("batch_sha256")
        bad["batch_sha256"] = object_sha256(bad)
        with self.assertRaisesRegex(ValueError, "batch contract drifted"):
            validate_whitened_credit_batch(
                bad,
                policy=frozen,
                batch_ref_sha256=digest("c"),
                credit_records=records,
            )


if __name__ == "__main__":
    unittest.main()
