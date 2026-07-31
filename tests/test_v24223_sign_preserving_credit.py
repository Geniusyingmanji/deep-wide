from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24223_sign_preserving_credit import (  # noqa: E402
    CREDIT_TRAINING_AUTHORIZED,
    MODULATION_POLICY,
    MODULATION_POLICY_SHA256,
    PRODUCTION_PACKAGE_AUTHORIZED,
    build_amplitude_features,
    build_verified_terminal_contribution,
    modulate_verified_credit,
    object_sha256,
    validate_amplitude_features,
    validate_modulation_receipt,
    validate_verified_terminal_contribution,
)


def digest(character: str) -> str:
    return character * 64


def contribution(
    *values: float,
    terminal_outcome_verified: bool = True,
    same_state_matched_continuation: bool = True,
    intervention_valid: bool = True,
    state_overlap_valid: bool = True,
    ood_detected: bool = False,
    prediction_closed_before_evaluator_join: bool = True,
    evaluator_joined_post_terminal_only: bool = True,
) -> dict[str, object]:
    return build_verified_terminal_contribution(
        opaque_step_ref_sha256=digest("a"),
        source_checkpoint_sha256=digest("b"),
        continuation_policy_sha256=digest("c"),
        evaluator_protocol_sha256=digest("d"),
        intervention_protocol_sha256=digest("e"),
        replicate_signed_terminal_contributions=list(values or (0.2, 0.2, 0.2)),
        terminal_outcome_verified=terminal_outcome_verified,
        same_state_matched_continuation=same_state_matched_continuation,
        intervention_valid=intervention_valid,
        state_overlap_valid=state_overlap_valid,
        ood_detected=ood_detected,
        prediction_closed_before_evaluator_join=(
            prediction_closed_before_evaluator_join
        ),
        evaluator_joined_post_terminal_only=evaluator_joined_post_terminal_only,
    )


def features(
    *,
    entropy_reduction: float = 0.6,
    provenance_role: str = "independent_verification",
    provenance_strength: float = 0.8,
    cost_fraction: float = 0.2,
    step: str = "a",
    checkpoint: str = "b",
) -> dict[str, object]:
    return build_amplitude_features(
        opaque_step_ref_sha256=digest(step),
        source_checkpoint_sha256=digest(checkpoint),
        feature_source_sha256=digest("f"),
        entropy_reduction=entropy_reduction,
        provenance_role=provenance_role,
        provenance_strength=provenance_strength,
        cost_fraction=cost_fraction,
    )


def reseal(value: dict[str, object], key: str) -> None:
    unsigned = copy.deepcopy(value)
    unsigned.pop(key)
    value[key] = object_sha256(unsigned)


class V24223SignPreservingCreditTests(unittest.TestCase):
    def test_positive_verifier_sign_is_preserved(self) -> None:
        verified = contribution(0.2, 0.3, 0.4)
        amplitude = features()
        receipt = modulate_verified_credit(
            verified_contribution=verified,
            amplitude_features=amplitude,
        )
        self.assertEqual(receipt["base_verified_advantage"], 0.3)
        self.assertEqual(receipt["verifier_sign"], "positive")
        self.assertGreater(receipt["modulated_advantage_candidate"], 0.0)
        self.assertTrue(receipt["verifier_sign_preserved"])
        self.assertFalse(receipt["entropy_provenance_or_cost_determined_sign"])
        validate_modulation_receipt(
            receipt,
            verified_contribution=verified,
            amplitude_features=amplitude,
        )

    def test_entropy_increase_correction_can_receive_positive_credit(self) -> None:
        verified = contribution(0.25, 0.25, 0.25)
        increased_entropy = features(entropy_reduction=-0.8)
        decreased_entropy = features(entropy_reduction=0.8)
        correction = modulate_verified_credit(
            verified_contribution=verified,
            amplitude_features=increased_entropy,
        )
        contraction = modulate_verified_credit(
            verified_contribution=verified,
            amplitude_features=decreased_entropy,
        )
        self.assertEqual(correction["entropy_direction"], "increase")
        self.assertEqual(contraction["entropy_direction"], "decrease")
        self.assertEqual(
            correction["modulated_advantage_candidate"],
            contraction["modulated_advantage_candidate"],
        )
        self.assertGreater(correction["modulated_advantage_candidate"], 0.0)

    def test_entropy_gain_cannot_flip_negative_terminal_contribution(self) -> None:
        verified = contribution(-0.1, -0.2, -0.3)
        amplitude = features(
            entropy_reduction=1.0,
            provenance_role="contradiction_resolution",
            provenance_strength=1.0,
            cost_fraction=0.0,
        )
        receipt = modulate_verified_credit(
            verified_contribution=verified,
            amplitude_features=amplitude,
        )
        self.assertEqual(receipt["verifier_sign"], "negative")
        self.assertLess(receipt["modulated_advantage_candidate"], 0.0)
        self.assertEqual(receipt["magnitude_multiplier"], 2.0)

    def test_zero_verifier_contribution_cannot_become_credit(self) -> None:
        verified = contribution(-0.5, 0.0, 0.5)
        amplitude = features(
            entropy_reduction=1.0,
            provenance_role="contradiction_resolution",
            provenance_strength=1.0,
            cost_fraction=0.0,
        )
        receipt = modulate_verified_credit(
            verified_contribution=verified,
            amplitude_features=amplitude,
        )
        self.assertEqual(receipt["verifier_sign"], "neutral")
        self.assertEqual(receipt["modulated_advantage_candidate"], 0.0)
        self.assertTrue(receipt["zero_verifier_remains_zero"])

    def test_cost_only_attenuates_magnitude(self) -> None:
        verified = contribution(0.4, 0.4, 0.4)
        cheap = modulate_verified_credit(
            verified_contribution=verified,
            amplitude_features=features(cost_fraction=0.0),
        )
        expensive = modulate_verified_credit(
            verified_contribution=verified,
            amplitude_features=features(cost_fraction=1.0),
        )
        self.assertGreater(
            cheap["modulated_advantage_candidate"],
            expensive["modulated_advantage_candidate"],
        )
        self.assertGreater(expensive["modulated_advantage_candidate"], 0.0)

    def test_credit_clip_preserves_sign(self) -> None:
        positive = modulate_verified_credit(
            verified_contribution=contribution(1.0, 1.0, 1.0),
            amplitude_features=features(
                entropy_reduction=1.0,
                provenance_strength=1.0,
                cost_fraction=0.0,
            ),
        )
        negative = modulate_verified_credit(
            verified_contribution=contribution(-1.0, -1.0, -1.0),
            amplitude_features=features(
                entropy_reduction=1.0,
                provenance_strength=1.0,
                cost_fraction=0.0,
            ),
        )
        self.assertEqual(positive["modulated_advantage_candidate"], 1.0)
        self.assertEqual(negative["modulated_advantage_candidate"], -1.0)
        self.assertTrue(positive["credit_clip_applied"])
        self.assertTrue(negative["credit_clip_applied"])

    def test_three_fixed_replicates_are_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "three to sixty-four"):
            contribution(0.1, 0.2)
        with self.assertRaisesRegex(ValueError, "three to sixty-four"):
            contribution(*([0.1] * 65))

    def test_invalid_or_ood_intervention_fails_closed(self) -> None:
        invalid_cases = (
            {"terminal_outcome_verified": False},
            {"same_state_matched_continuation": False},
            {"intervention_valid": False},
            {"state_overlap_valid": False},
            {"ood_detected": True},
            {"prediction_closed_before_evaluator_join": False},
            {"evaluator_joined_post_terminal_only": False},
        )
        for kwargs in invalid_cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, "valid in-overlap"):
                    contribution(0.1, 0.1, 0.1, **kwargs)

    def test_unmatched_state_or_step_fails_closed(self) -> None:
        verified = contribution(0.2, 0.2, 0.2)
        for amplitude in (features(step="9"), features(checkpoint="8")):
            with self.subTest(amplitude=amplitude):
                with self.assertRaisesRegex(ValueError, "unmatched"):
                    modulate_verified_credit(
                        verified_contribution=verified,
                        amplitude_features=amplitude,
                    )

    def test_none_provenance_cannot_carry_strength(self) -> None:
        with self.assertRaisesRegex(ValueError, "zero strength"):
            features(provenance_role="none", provenance_strength=0.1)
        value = features(provenance_role="none", provenance_strength=0.0)
        validate_amplitude_features(value)

    def test_out_of_range_features_and_contributions_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside"):
            contribution(0.1, 0.2, 1.1)
        with self.assertRaisesRegex(ValueError, "outside"):
            features(entropy_reduction=-1.1)
        with self.assertRaisesRegex(ValueError, "outside"):
            features(provenance_strength=1.1)
        with self.assertRaisesRegex(ValueError, "outside"):
            features(cost_fraction=-0.1)

    def test_tampered_and_resealed_artifacts_are_rejected(self) -> None:
        verified = contribution(0.2, 0.2, 0.2)
        amplitude = features()
        receipt = modulate_verified_credit(
            verified_contribution=verified,
            amplitude_features=amplitude,
        )
        tampered = copy.deepcopy(receipt)
        tampered["modulated_advantage_candidate"] = -float(
            tampered["modulated_advantage_candidate"]
        )
        reseal(tampered, "receipt_sha256")
        with self.assertRaisesRegex(ValueError, "formula drifted"):
            validate_modulation_receipt(tampered)

        invalid = copy.deepcopy(verified)
        invalid["ood_detected"] = True
        reseal(invalid, "record_sha256")
        with self.assertRaisesRegex(ValueError, "cannot supply credit sign"):
            validate_verified_terminal_contribution(invalid)

        contaminated = copy.deepcopy(amplitude)
        contaminated["terminal_outcome_or_evaluator_signal_embedded"] = True
        reseal(contaminated, "feature_sha256")
        with self.assertRaisesRegex(ValueError, "header or seal"):
            validate_amplitude_features(contaminated)

    def test_extra_privileged_fields_are_rejected_by_exact_schema(self) -> None:
        verified = contribution(0.2, 0.2, 0.2)
        verified["ground_truth"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_verified_terminal_contribution(verified)
        amplitude = features()
        amplitude["evaluator_score"] = 1.0
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_amplitude_features(amplitude)

    def test_policy_hash_and_authorization_are_frozen_false(self) -> None:
        self.assertEqual(MODULATION_POLICY_SHA256, object_sha256(MODULATION_POLICY))
        self.assertFalse(PRODUCTION_PACKAGE_AUTHORIZED)
        self.assertFalse(CREDIT_TRAINING_AUTHORIZED)
        receipt = modulate_verified_credit(
            verified_contribution=contribution(0.1, 0.1, 0.1),
            amplitude_features=features(),
        )
        self.assertFalse(receipt["production_package_authorized"])
        self.assertFalse(receipt["credit_training_authorized"])
        self.assertTrue(receipt["post_terminal_training_or_audit_only"])
        self.assertFalse(
            receipt[
                "gold_mapping_category_question_type_evaluator_score_or_reward_available_to_forward"
            ]
        )


if __name__ == "__main__":
    unittest.main()
