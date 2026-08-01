from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24255_finite_depth_dynamic_voc import (  # noqa: E402
    build_transition_model,
    evaluate_voc_policies,
    object_sha256,
    reject_privileged_runtime_metadata,
    validate_planning_receipt,
    validate_transition_model,
)


def ref(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def outcome(
    target: str,
    probability: float = 1.0,
    *,
    calibrated: bool = True,
    calibration_label: str | None = None,
) -> dict[str, object]:
    return {
        "next_state_ref_sha256": target,
        "probability": probability,
        "calibration_ready": calibrated,
        "calibration_ref_sha256": (
            ref(calibration_label or f"calibration:{target}")
            if calibrated
            else None
        ),
    }


def action(
    label: str,
    cost: int,
    outcomes: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "action_ref_sha256": ref(f"action:{label}"),
        "cost": cost,
        "outcomes": outcomes,
    }


def state(
    label: str,
    loss: float,
    entropy: float,
    actions: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "state_ref_sha256": ref(f"state:{label}"),
        "stop_terminal_loss": loss,
        "belief_entropy": entropy,
        "actions": actions,
    }


class V24255FiniteDepthDynamicVocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root_ref = ref("state:root")
        self.high_ig_ref = ref("state:high-ig")
        self.high_value_ref = ref("state:high-value")
        self.bridge_ref = ref("state:bridge")
        self.bridge_terminal_ref = ref("state:bridge-terminal")
        self.high_ig_action = ref("action:high-ig")
        self.high_value_action = ref("action:high-value")
        self.bridge_action = ref("action:bridge")
        self.unlock_action = ref("action:unlock")
        self.states = [
            state(
                "root",
                0.60,
                0.90,
                [
                    action(
                        "high-ig",
                        1,
                        [outcome(self.high_ig_ref)],
                    ),
                    action(
                        "high-value",
                        1,
                        [outcome(self.high_value_ref)],
                    ),
                    action(
                        "bridge",
                        1,
                        [outcome(self.bridge_ref)],
                    ),
                ],
            ),
            state("high-ig", 0.58, 0.10, []),
            state("high-value", 0.30, 0.80, []),
            state(
                "bridge",
                0.60,
                0.90,
                [
                    action(
                        "unlock",
                        1,
                        [outcome(self.bridge_terminal_ref)],
                    )
                ],
            ),
            state("bridge-terminal", 0.10, 0.90, []),
        ]
        self.model = self.build_model(self.states)

    def build_model(
        self,
        states: list[dict[str, object]],
        *,
        max_depth: int = 3,
        max_budget: int = 3,
    ) -> dict[str, object]:
        return build_transition_model(
            model_fit_manifest_sha256=ref("fit"),
            calibration_protocol_sha256=ref("calibration-protocol"),
            root_state_ref_sha256=self.root_ref,
            max_depth=max_depth,
            max_budget=max_budget,
            states=states,
        )

    def evaluate(
        self, *, depth: int = 2, budget: int = 2
    ) -> dict[str, object]:
        return evaluate_voc_policies(
            model=self.model,
            expected_transition_model_sha256=self.model[
                "transition_model_sha256"
            ],
            requested_depth=depth,
            available_budget=budget,
        )

    def test_high_information_gain_and_terminal_value_rankings_diverge(self) -> None:
        receipt = self.evaluate()
        policies = receipt["policies"]
        self.assertEqual(
            policies["pure_information_gain"][
                "selected_action_ref_sha256"
            ],
            self.high_ig_action,
        )
        self.assertEqual(
            policies["myopic_terminal_loss_voc"][
                "selected_action_ref_sha256"
            ],
            self.high_value_action,
        )
        high_ig = receipt["action_values"][self.high_ig_action]
        high_value = receipt["action_values"][self.high_value_action]
        self.assertEqual(high_ig["pure_information_gain"], 0.8)
        self.assertEqual(high_ig["myopic_terminal_loss_voc"], 0.02)
        self.assertEqual(high_value["pure_information_gain"], 0.1)
        self.assertEqual(high_value["myopic_terminal_loss_voc"], 0.3)

    def test_myopic_zero_bridge_has_positive_descendant_option_value(self) -> None:
        receipt = self.evaluate(depth=2, budget=2)
        bridge = receipt["action_values"][self.bridge_action]
        self.assertEqual(bridge["myopic_terminal_loss_voc"], 0.0)
        self.assertEqual(bridge["finite_depth_dynamic_voc"], 0.5)
        self.assertEqual(bridge["descendant_option_value"], 0.5)
        self.assertEqual(
            receipt["policies"]["finite_depth_dynamic_voc"][
                "selected_action_ref_sha256"
            ],
            self.bridge_action,
        )

    def test_depth_one_is_exactly_myopic(self) -> None:
        receipt = self.evaluate(depth=1, budget=2)
        self.assertTrue(receipt["requested_depth_one_myopic_equivalence"])
        for row in receipt["action_values"].values():
            if row["affordable"]:
                self.assertEqual(
                    row["finite_depth_dynamic_voc"],
                    row["myopic_terminal_loss_voc"],
                )
                self.assertEqual(row["descendant_option_value"], 0.0)
        self.assertEqual(
            receipt["policies"]["finite_depth_dynamic_voc"],
            {
                **receipt["policies"]["myopic_terminal_loss_voc"],
                "objective": (
                    "bellman_expected_terminal_loss_reduction_per_cost"
                ),
            },
        )

    def test_budget_blocks_descendant_and_zero_budget_stops(self) -> None:
        one = self.evaluate(depth=3, budget=1)
        bridge = one["action_values"][self.bridge_action]
        self.assertEqual(bridge["finite_depth_dynamic_voc"], 0.0)
        self.assertEqual(bridge["descendant_option_value"], 0.0)
        self.assertEqual(
            one["policies"]["finite_depth_dynamic_voc"][
                "selected_action_ref_sha256"
            ],
            self.high_value_action,
        )
        zero = self.evaluate(depth=3, budget=0)
        for policy in zero["policies"].values():
            self.assertEqual(policy["decision_kind"], "stop")
            self.assertEqual(
                policy["decision_reason"],
                "no_affordable_action_within_budget",
            )

    def test_missing_calibration_abstains_all_policies(self) -> None:
        changed = copy.deepcopy(self.states)
        changed[0]["actions"][0]["outcomes"][0] = outcome(
            self.high_ig_ref, calibrated=False
        )
        model = self.build_model(changed)
        self.assertFalse(model["transition_calibration_complete"])
        self.assertEqual(model["missing_calibration_count"], 1)
        receipt = evaluate_voc_policies(
            model=model,
            expected_transition_model_sha256=model[
                "transition_model_sha256"
            ],
            requested_depth=2,
            available_budget=2,
        )
        for policy in receipt["policies"].values():
            self.assertEqual(policy["decision_kind"], "abstain")
            self.assertEqual(
                policy["decision_reason"],
                "transition_probability_calibration_incomplete",
            )
        self.assertTrue(
            all(
                row["finite_depth_dynamic_voc"] is None
                for row in receipt["action_values"].values()
            )
        )

    def test_deterministic_preregistered_order_breaks_exact_ties(self) -> None:
        first_target = ref("state:first-target")
        second_target = ref("state:second-target")
        states = [
            state(
                "root",
                0.8,
                0.8,
                [
                    action("first", 1, [outcome(first_target)]),
                    action("second", 1, [outcome(second_target)]),
                ],
            ),
            {
                **state("first-target", 0.3, 0.3, []),
                "state_ref_sha256": first_target,
            },
            {
                **state("second-target", 0.3, 0.3, []),
                "state_ref_sha256": second_target,
            },
        ]
        model = self.build_model(states, max_depth=1, max_budget=1)
        receipt = evaluate_voc_policies(
            model=model,
            expected_transition_model_sha256=model[
                "transition_model_sha256"
            ],
            requested_depth=1,
            available_budget=1,
        )
        for policy in receipt["policies"].values():
            self.assertEqual(
                policy["selected_action_ref_sha256"],
                ref("action:first"),
            )

    def test_probability_cycle_unreachable_and_budget_overflow_fail_closed(self) -> None:
        nonnormalized = copy.deepcopy(self.states)
        nonnormalized[0]["actions"][0]["outcomes"] = [
            outcome(self.high_ig_ref, 0.4, calibration_label="a"),
            outcome(self.high_value_ref, 0.5, calibration_label="b"),
        ]
        with self.assertRaisesRegex(ValueError, "not normalized"):
            self.build_model(nonnormalized)

        cyclic = copy.deepcopy(self.states)
        cyclic[4]["actions"] = [
            action("cycle", 1, [outcome(self.root_ref)])
        ]
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.build_model(cyclic)

        unreachable = copy.deepcopy(self.states)
        unreachable.append(state("unreachable", 0.2, 0.2, []))
        with self.assertRaisesRegex(ValueError, "unreachable"):
            self.build_model(unreachable)

        overflow = copy.deepcopy(self.states)
        overflow[0]["actions"][0]["cost"] = 4
        with self.assertRaisesRegex(ValueError, "action cost"):
            self.build_model(overflow, max_budget=3)
        with self.assertRaisesRegex(ValueError, "available budget"):
            self.evaluate(depth=2, budget=4)

    def test_privileged_metadata_is_rejected_recursively(self) -> None:
        for payload in (
            {"category": "hidden"},
            {"outer": [{"question_type": "hidden"}]},
            {"outer": {"ground-truth": "hidden"}},
            {"outer": {"results.csv": "hidden"}},
        ):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "privileged"):
                    reject_privileged_runtime_metadata(payload)

        changed = copy.deepcopy(self.states)
        changed[0]["category"] = "hidden"
        with self.assertRaisesRegex(ValueError, "privileged"):
            self.build_model(changed)

    def test_model_and_receipt_seals_replay_and_detect_tampering(self) -> None:
        model = validate_transition_model(
            self.model,
            expected_transition_model_sha256=self.model[
                "transition_model_sha256"
            ],
        )
        receipt = self.evaluate()
        self.assertEqual(
            receipt["receipt_sha256"],
            object_sha256(
                {
                    key: value
                    for key, value in receipt.items()
                    if key != "receipt_sha256"
                }
            ),
        )
        self.assertEqual(
            validate_planning_receipt(
                receipt,
                model=model,
                expected_transition_model_sha256=model[
                    "transition_model_sha256"
                ],
            ),
            receipt,
        )

        tampered_model = copy.deepcopy(model)
        tampered_model["states"][0]["stop_terminal_loss"] = 0.61
        with self.assertRaisesRegex(ValueError, "seal"):
            validate_transition_model(
                tampered_model,
                expected_transition_model_sha256=model[
                    "transition_model_sha256"
                ],
            )

        type_drifted_model = copy.deepcopy(model)
        type_drifted_model["missing_calibration_count"] = False
        type_drifted_model["transition_model_sha256"] = object_sha256(
            {
                key: value
                for key, value in type_drifted_model.items()
                if key != "transition_model_sha256"
            }
        )
        with self.assertRaisesRegex(ValueError, "missing calibration count"):
            validate_transition_model(
                type_drifted_model,
                expected_transition_model_sha256=type_drifted_model[
                    "transition_model_sha256"
                ],
            )

        version_drifted_model = copy.deepcopy(model)
        version_drifted_model["artifact_version"] = True
        version_drifted_model["transition_model_sha256"] = object_sha256(
            {
                key: value
                for key, value in version_drifted_model.items()
                if key != "transition_model_sha256"
            }
        )
        with self.assertRaisesRegex(ValueError, "artifact version"):
            validate_transition_model(
                version_drifted_model,
                expected_transition_model_sha256=version_drifted_model[
                    "transition_model_sha256"
                ],
            )

        tampered_receipt = copy.deepcopy(receipt)
        tampered_receipt["action_values"][self.bridge_action][
            "finite_depth_dynamic_voc"
        ] = 0.51
        with self.assertRaisesRegex(ValueError, "seal"):
            validate_planning_receipt(
                tampered_receipt,
                model=model,
                expected_transition_model_sha256=model[
                    "transition_model_sha256"
                ],
            )

        type_drifted_receipt = self.evaluate(depth=1, budget=1)
        type_drifted_receipt["requested_depth"] = True
        type_drifted_receipt["receipt_sha256"] = object_sha256(
            {
                key: value
                for key, value in type_drifted_receipt.items()
                if key != "receipt_sha256"
            }
        )
        with self.assertRaisesRegex(ValueError, "receipt depth"):
            validate_planning_receipt(
                type_drifted_receipt,
                model=model,
                expected_transition_model_sha256=model[
                    "transition_model_sha256"
                ],
            )

    def test_content_free_safety_and_authority_attestations_are_negative(self) -> None:
        receipt = self.evaluate()
        self.assertTrue(receipt["label_blind"])
        self.assertTrue(receipt["build_only"])
        self.assertFalse(receipt["entropy_is_terminal_utility"])
        self.assertFalse(
            receipt["raw_state_action_observation_question_or_id_embedded"]
        )
        self.assertFalse(
            receipt[
                "benchmark_evaluator_gold_mapping_category_question_type_split_score_or_reward_used"
            ]
        )
        self.assertFalse(
            receipt[
                "file_environment_network_model_search_fetch_or_process_accessed"
            ]
        )
        self.assertFalse(
            receipt[
                "runtime_forward_training_evaluator_or_leaderboard_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
