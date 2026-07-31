"""Pure verifier-sign-preserving OWIC credit modulation.

This build-only module closes one narrow gap in the earlier OWIC prototype.
The old additive prototype could let entropy, provenance, or cost terms reverse
the direction of an outcome-verified contribution.  Here the direction comes
only from a valid same-state terminal intervention.  Epistemic and accounting
features can change its magnitude, but never create or reverse its sign.

The terminal contribution is necessarily a post-terminal training/audit
signal.  It is represented only by bounded numbers and content-free SHA-256
references.  No question, answer, evidence, benchmark label, mapping, gold,
evaluator artifact, or score payload is accepted.  This module is outside the
active forward import graph and grants no runtime, benchmark, training, or
leaderboard authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v24223_verifier_sign_preserving_owic_credit_v1"
VERIFIED_CONTRIBUTION_ROLE = "v24223_verified_terminal_contribution"
AMPLITUDE_FEATURE_ROLE = "v24223_credit_amplitude_features"
MODULATION_RECEIPT_ROLE = "v24223_sign_preserving_credit_receipt"

MIN_REPLICATES = 3
MAX_REPLICATES = 64
PROVENANCE_ROLES = (
    "none",
    "discovery",
    "independent_verification",
    "contradiction_resolution",
    "synthesis",
)
PRODUCTION_PACKAGE_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False

MODULATION_POLICY = {
    "entropy_absolute_weight": 0.5,
    "provenance_strength_weight": 0.5,
    "cost_attenuation_weight": 0.5,
    "minimum_multiplier": 0.5,
    "maximum_multiplier": 2.0,
    "credit_clip": 1.0,
}

VERIFIED_CONTRIBUTION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "phase",
        "label_blind_runtime",
        "opaque_step_ref_sha256",
        "source_checkpoint_sha256",
        "continuation_policy_sha256",
        "evaluator_protocol_sha256",
        "intervention_protocol_sha256",
        "replicate_count",
        "replicate_signed_terminal_contributions",
        "mean_signed_terminal_contribution",
        "terminal_outcome_verified",
        "same_state_matched_continuation",
        "intervention_valid",
        "state_overlap_valid",
        "ood_detected",
        "prediction_closed_before_evaluator_join",
        "evaluator_joined_post_terminal_only",
        "runtime_forward_mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "record_sha256",
    }
)
AMPLITUDE_FEATURE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_step_ref_sha256",
        "source_checkpoint_sha256",
        "feature_source_sha256",
        "entropy_reduction",
        "provenance_role",
        "provenance_strength",
        "cost_fraction",
        "terminal_outcome_or_evaluator_signal_embedded",
        "feature_sha256",
    }
)
MODULATION_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "phase",
        "label_blind_runtime",
        "opaque_step_ref_sha256",
        "source_checkpoint_sha256",
        "verified_contribution_sha256",
        "amplitude_feature_sha256",
        "modulation_policy_sha256",
        "base_verified_advantage",
        "verifier_sign",
        "entropy_direction",
        "entropy_absolute_magnitude",
        "provenance_role",
        "provenance_strength",
        "cost_fraction",
        "pre_cost_multiplier",
        "cost_attenuation_factor",
        "magnitude_multiplier",
        "unclipped_modulated_magnitude",
        "modulated_advantage_candidate",
        "credit_clip_applied",
        "verifier_sign_preserved",
        "zero_verifier_remains_zero",
        "entropy_provenance_or_cost_determined_sign",
        "same_state_terminal_intervention_required",
        "gold_mapping_category_question_type_evaluator_score_or_reward_available_to_forward",
        "post_terminal_training_or_audit_only",
        "production_package_authorized",
        "credit_training_authorized",
        "receipt_sha256",
    }
)


def object_sha256(value: object) -> str:
    """Hash a JSON-compatible object with the frozen canonical encoding."""

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


MODULATION_POLICY_SHA256 = object_sha256(MODULATION_POLICY)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value).issubset(set("0123456789abcdef"))
    )


def _sha256(value: object, *, label: str) -> str:
    if not _is_sha256(value):
        raise ValueError(f"V2.42.23 {label} is not a SHA-256")
    return str(value)


def _bounded(
    value: object, *, label: str, minimum: float, maximum: float
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.23 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"V2.42.23 {label} is outside [{minimum},{maximum}]")
    return number


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.23 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(seal_key, None)
    return _is_sha256(seal) and seal == object_sha256(unsigned)


def _sign(value: float) -> str:
    if value > 0.0:
        return "positive"
    if value < 0.0:
        return "negative"
    return "neutral"


def _entropy_direction(value: float) -> str:
    if value > 0.0:
        return "decrease"
    if value < 0.0:
        return "increase"
    return "unchanged"


def build_verified_terminal_contribution(
    *,
    opaque_step_ref_sha256: str,
    source_checkpoint_sha256: str,
    continuation_policy_sha256: str,
    evaluator_protocol_sha256: str,
    intervention_protocol_sha256: str,
    replicate_signed_terminal_contributions: Sequence[float],
    terminal_outcome_verified: bool,
    same_state_matched_continuation: bool,
    intervention_valid: bool,
    state_overlap_valid: bool,
    ood_detected: bool,
    prediction_closed_before_evaluator_join: bool,
    evaluator_joined_post_terminal_only: bool,
) -> dict[str, Any]:
    """Seal a valid post-terminal contribution or fail closed.

    Positive values mean the action reduced terminal task loss relative to its
    matched no-op continuation.  Caller attestations cannot prove experimental
    semantics by themselves; the receipt keeps the hashes needed for a later
    source-bundle audit and refuses any invalid/OOD or unmatched intervention.
    """

    hashes = {
        "opaque_step_ref_sha256": _sha256(
            opaque_step_ref_sha256, label="opaque step reference"
        ),
        "source_checkpoint_sha256": _sha256(
            source_checkpoint_sha256, label="source checkpoint"
        ),
        "continuation_policy_sha256": _sha256(
            continuation_policy_sha256, label="continuation policy"
        ),
        "evaluator_protocol_sha256": _sha256(
            evaluator_protocol_sha256, label="evaluator protocol"
        ),
        "intervention_protocol_sha256": _sha256(
            intervention_protocol_sha256, label="intervention protocol"
        ),
    }
    flags = {
        "terminal_outcome_verified": terminal_outcome_verified,
        "same_state_matched_continuation": same_state_matched_continuation,
        "intervention_valid": intervention_valid,
        "state_overlap_valid": state_overlap_valid,
        "ood_detected": ood_detected,
        "prediction_closed_before_evaluator_join": (
            prediction_closed_before_evaluator_join
        ),
        "evaluator_joined_post_terminal_only": evaluator_joined_post_terminal_only,
    }
    if any(not isinstance(value, bool) for value in flags.values()):
        raise ValueError("V2.42.23 intervention validity flags are not boolean")
    if (
        not flags["terminal_outcome_verified"]
        or not flags["same_state_matched_continuation"]
        or not flags["intervention_valid"]
        or not flags["state_overlap_valid"]
        or flags["ood_detected"]
        or not flags["prediction_closed_before_evaluator_join"]
        or not flags["evaluator_joined_post_terminal_only"]
    ):
        raise ValueError(
            "V2.42.23 requires a valid in-overlap same-state post-terminal intervention"
        )
    if isinstance(replicate_signed_terminal_contributions, (str, bytes)):
        raise ValueError("V2.42.23 replicate contributions are not an array")
    contributions = [
        _bounded(value, label="terminal contribution", minimum=-1.0, maximum=1.0)
        for value in replicate_signed_terminal_contributions
    ]
    if not MIN_REPLICATES <= len(contributions) <= MAX_REPLICATES:
        raise ValueError(
            "V2.42.23 requires three to sixty-four fixed-continuation replicates"
        )
    mean = round(sum(contributions) / len(contributions), 12)
    record: dict[str, Any] = {
        "artifact_version": 1,
        "role": VERIFIED_CONTRIBUTION_ROLE,
        "policy_id": POLICY_ID,
        "phase": "post_terminal_outcome_verified_training_or_audit_only",
        "label_blind_runtime": True,
        **hashes,
        "replicate_count": len(contributions),
        "replicate_signed_terminal_contributions": contributions,
        "mean_signed_terminal_contribution": mean,
        **flags,
        "runtime_forward_mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "record_sha256": "",
    }
    record["record_sha256"] = object_sha256(
        {key: value for key, value in record.items() if key != "record_sha256"}
    )
    validate_verified_terminal_contribution(record)
    return record


def validate_verified_terminal_contribution(value: object) -> None:
    record = _exact_mapping(
        value, keys=VERIFIED_CONTRIBUTION_KEYS, label="verified contribution"
    )
    if (
        record.get("artifact_version") != 1
        or record.get("role") != VERIFIED_CONTRIBUTION_ROLE
        or record.get("policy_id") != POLICY_ID
        or record.get("phase")
        != "post_terminal_outcome_verified_training_or_audit_only"
        or record.get("label_blind_runtime") is not True
        or record.get("runtime_forward_mapping_gold_category_question_type_evaluator_score_or_reward_read")
        is not False
        or any(
            not _is_sha256(record.get(key))
            for key in (
                "opaque_step_ref_sha256",
                "source_checkpoint_sha256",
                "continuation_policy_sha256",
                "evaluator_protocol_sha256",
                "intervention_protocol_sha256",
            )
        )
        or not _sealed(record, seal_key="record_sha256")
    ):
        raise ValueError("V2.42.23 verified contribution header or seal is invalid")
    flags = (
        "terminal_outcome_verified",
        "same_state_matched_continuation",
        "intervention_valid",
        "state_overlap_valid",
        "ood_detected",
        "prediction_closed_before_evaluator_join",
        "evaluator_joined_post_terminal_only",
    )
    if any(not isinstance(record.get(key), bool) for key in flags):
        raise ValueError("V2.42.23 verified contribution flags are invalid")
    if (
        record["terminal_outcome_verified"] is not True
        or record["same_state_matched_continuation"] is not True
        or record["intervention_valid"] is not True
        or record["state_overlap_valid"] is not True
        or record["ood_detected"] is not False
        or record["prediction_closed_before_evaluator_join"] is not True
        or record["evaluator_joined_post_terminal_only"] is not True
    ):
        raise ValueError("V2.42.23 invalid intervention cannot supply credit sign")
    count = record.get("replicate_count")
    rows = record.get("replicate_signed_terminal_contributions")
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or not MIN_REPLICATES <= count <= MAX_REPLICATES
        or not isinstance(rows, list)
        or len(rows) != count
    ):
        raise ValueError("V2.42.23 replicate contribution schema is invalid")
    contributions = [
        _bounded(value, label="terminal contribution", minimum=-1.0, maximum=1.0)
        for value in rows
    ]
    mean = _bounded(
        record.get("mean_signed_terminal_contribution"),
        label="mean terminal contribution",
        minimum=-1.0,
        maximum=1.0,
    )
    if mean != round(sum(contributions) / len(contributions), 12):
        raise ValueError("V2.42.23 mean terminal contribution drifted")


def build_amplitude_features(
    *,
    opaque_step_ref_sha256: str,
    source_checkpoint_sha256: str,
    feature_source_sha256: str,
    entropy_reduction: float,
    provenance_role: str,
    provenance_strength: float,
    cost_fraction: float,
) -> dict[str, Any]:
    """Seal bounded non-directional features for credit magnitude only."""

    role = str(provenance_role)
    if role not in PROVENANCE_ROLES:
        raise ValueError("V2.42.23 provenance role is invalid")
    entropy = _bounded(
        entropy_reduction, label="entropy reduction", minimum=-1.0, maximum=1.0
    )
    provenance = _bounded(
        provenance_strength, label="provenance strength", minimum=0.0, maximum=1.0
    )
    cost = _bounded(cost_fraction, label="cost fraction", minimum=0.0, maximum=1.0)
    if role == "none" and provenance != 0.0:
        raise ValueError("V2.42.23 none provenance must have zero strength")
    features: dict[str, Any] = {
        "artifact_version": 1,
        "role": AMPLITUDE_FEATURE_ROLE,
        "policy_id": POLICY_ID,
        "opaque_step_ref_sha256": _sha256(
            opaque_step_ref_sha256, label="opaque step reference"
        ),
        "source_checkpoint_sha256": _sha256(
            source_checkpoint_sha256, label="source checkpoint"
        ),
        "feature_source_sha256": _sha256(
            feature_source_sha256, label="feature source"
        ),
        "entropy_reduction": entropy,
        "provenance_role": role,
        "provenance_strength": provenance,
        "cost_fraction": cost,
        "terminal_outcome_or_evaluator_signal_embedded": False,
        "feature_sha256": "",
    }
    features["feature_sha256"] = object_sha256(
        {key: value for key, value in features.items() if key != "feature_sha256"}
    )
    validate_amplitude_features(features)
    return features


def validate_amplitude_features(value: object) -> None:
    features = _exact_mapping(
        value, keys=AMPLITUDE_FEATURE_KEYS, label="amplitude features"
    )
    if (
        features.get("artifact_version") != 1
        or features.get("role") != AMPLITUDE_FEATURE_ROLE
        or features.get("policy_id") != POLICY_ID
        or features.get("terminal_outcome_or_evaluator_signal_embedded") is not False
        or features.get("provenance_role") not in PROVENANCE_ROLES
        or any(
            not _is_sha256(features.get(key))
            for key in (
                "opaque_step_ref_sha256",
                "source_checkpoint_sha256",
                "feature_source_sha256",
            )
        )
        or not _sealed(features, seal_key="feature_sha256")
    ):
        raise ValueError("V2.42.23 amplitude feature header or seal is invalid")
    _bounded(
        features.get("entropy_reduction"),
        label="entropy reduction",
        minimum=-1.0,
        maximum=1.0,
    )
    provenance = _bounded(
        features.get("provenance_strength"),
        label="provenance strength",
        minimum=0.0,
        maximum=1.0,
    )
    _bounded(
        features.get("cost_fraction"),
        label="cost fraction",
        minimum=0.0,
        maximum=1.0,
    )
    if features["provenance_role"] == "none" and provenance != 0.0:
        raise ValueError("V2.42.23 none provenance must have zero strength")


def modulate_verified_credit(
    *,
    verified_contribution: Mapping[str, Any],
    amplitude_features: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an offline advantage candidate whose sign only the verifier sets."""

    validate_verified_terminal_contribution(verified_contribution)
    validate_amplitude_features(amplitude_features)
    for key in ("opaque_step_ref_sha256", "source_checkpoint_sha256"):
        if verified_contribution[key] != amplitude_features[key]:
            raise ValueError("V2.42.23 contribution and amplitude features are unmatched")

    base = float(verified_contribution["mean_signed_terminal_contribution"])
    entropy = float(amplitude_features["entropy_reduction"])
    provenance = float(amplitude_features["provenance_strength"])
    cost = float(amplitude_features["cost_fraction"])
    entropy_magnitude = abs(entropy)
    pre_cost = round(
        1.0
        + MODULATION_POLICY["entropy_absolute_weight"] * entropy_magnitude
        + MODULATION_POLICY["provenance_strength_weight"] * provenance,
        12,
    )
    cost_factor = round(
        1.0 - MODULATION_POLICY["cost_attenuation_weight"] * cost, 12
    )
    multiplier = round(
        min(
            MODULATION_POLICY["maximum_multiplier"],
            max(
                MODULATION_POLICY["minimum_multiplier"],
                pre_cost * cost_factor,
            ),
        ),
        12,
    )
    unclipped_magnitude = round(abs(base) * multiplier, 12)
    clipped_magnitude = min(
        MODULATION_POLICY["credit_clip"], unclipped_magnitude
    )
    if base > 0.0:
        modulated = clipped_magnitude
    elif base < 0.0:
        modulated = -clipped_magnitude
    else:
        modulated = 0.0
    modulated = round(modulated, 12)
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": MODULATION_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "phase": "post_terminal_offline_advantage_candidate",
        "label_blind_runtime": True,
        "opaque_step_ref_sha256": verified_contribution["opaque_step_ref_sha256"],
        "source_checkpoint_sha256": verified_contribution[
            "source_checkpoint_sha256"
        ],
        "verified_contribution_sha256": verified_contribution["record_sha256"],
        "amplitude_feature_sha256": amplitude_features["feature_sha256"],
        "modulation_policy_sha256": MODULATION_POLICY_SHA256,
        "base_verified_advantage": base,
        "verifier_sign": _sign(base),
        "entropy_direction": _entropy_direction(entropy),
        "entropy_absolute_magnitude": entropy_magnitude,
        "provenance_role": amplitude_features["provenance_role"],
        "provenance_strength": provenance,
        "cost_fraction": cost,
        "pre_cost_multiplier": pre_cost,
        "cost_attenuation_factor": cost_factor,
        "magnitude_multiplier": multiplier,
        "unclipped_modulated_magnitude": unclipped_magnitude,
        "modulated_advantage_candidate": modulated,
        "credit_clip_applied": unclipped_magnitude > MODULATION_POLICY["credit_clip"],
        "verifier_sign_preserved": _sign(modulated) == _sign(base),
        "zero_verifier_remains_zero": base != 0.0 or modulated == 0.0,
        "entropy_provenance_or_cost_determined_sign": False,
        "same_state_terminal_intervention_required": True,
        "gold_mapping_category_question_type_evaluator_score_or_reward_available_to_forward": False,
        "post_terminal_training_or_audit_only": True,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "receipt_sha256": "",
    }
    receipt["receipt_sha256"] = object_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )
    validate_modulation_receipt(
        receipt,
        verified_contribution=verified_contribution,
        amplitude_features=amplitude_features,
    )
    return receipt


def validate_modulation_receipt(
    value: object,
    *,
    verified_contribution: Mapping[str, Any] | None = None,
    amplitude_features: Mapping[str, Any] | None = None,
) -> None:
    receipt = _exact_mapping(
        value, keys=MODULATION_RECEIPT_KEYS, label="modulation receipt"
    )
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != MODULATION_RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("phase") != "post_terminal_offline_advantage_candidate"
        or receipt.get("label_blind_runtime") is not True
        or receipt.get("modulation_policy_sha256") != MODULATION_POLICY_SHA256
        or receipt.get("verifier_sign") not in {"negative", "neutral", "positive"}
        or receipt.get("entropy_direction")
        not in {"decrease", "increase", "unchanged"}
        or receipt.get("verifier_sign_preserved") is not True
        or receipt.get("zero_verifier_remains_zero") is not True
        or receipt.get("entropy_provenance_or_cost_determined_sign") is not False
        or receipt.get("same_state_terminal_intervention_required") is not True
        or receipt.get("gold_mapping_category_question_type_evaluator_score_or_reward_available_to_forward")
        is not False
        or receipt.get("post_terminal_training_or_audit_only") is not True
        or receipt.get("production_package_authorized") is not False
        or receipt.get("credit_training_authorized") is not False
        or any(
            not _is_sha256(receipt.get(key))
            for key in (
                "opaque_step_ref_sha256",
                "source_checkpoint_sha256",
                "verified_contribution_sha256",
                "amplitude_feature_sha256",
                "modulation_policy_sha256",
            )
        )
        or not isinstance(receipt.get("credit_clip_applied"), bool)
        or not _sealed(receipt, seal_key="receipt_sha256")
    ):
        raise ValueError("V2.42.23 modulation receipt header or seal is invalid")
    base = _bounded(
        receipt.get("base_verified_advantage"),
        label="base verified advantage",
        minimum=-1.0,
        maximum=1.0,
    )
    entropy_magnitude = _bounded(
        receipt.get("entropy_absolute_magnitude"),
        label="entropy magnitude",
        minimum=0.0,
        maximum=1.0,
    )
    provenance = _bounded(
        receipt.get("provenance_strength"),
        label="provenance strength",
        minimum=0.0,
        maximum=1.0,
    )
    cost = _bounded(
        receipt.get("cost_fraction"),
        label="cost fraction",
        minimum=0.0,
        maximum=1.0,
    )
    pre_cost = _bounded(
        receipt.get("pre_cost_multiplier"),
        label="pre-cost multiplier",
        minimum=1.0,
        maximum=2.0,
    )
    cost_factor = _bounded(
        receipt.get("cost_attenuation_factor"),
        label="cost attenuation",
        minimum=0.5,
        maximum=1.0,
    )
    multiplier = _bounded(
        receipt.get("magnitude_multiplier"),
        label="magnitude multiplier",
        minimum=MODULATION_POLICY["minimum_multiplier"],
        maximum=MODULATION_POLICY["maximum_multiplier"],
    )
    unclipped = _bounded(
        receipt.get("unclipped_modulated_magnitude"),
        label="unclipped magnitude",
        minimum=0.0,
        maximum=2.0,
    )
    modulated = _bounded(
        receipt.get("modulated_advantage_candidate"),
        label="modulated advantage",
        minimum=-1.0,
        maximum=1.0,
    )
    expected_pre_cost = round(
        1.0
        + MODULATION_POLICY["entropy_absolute_weight"] * entropy_magnitude
        + MODULATION_POLICY["provenance_strength_weight"] * provenance,
        12,
    )
    expected_cost_factor = round(
        1.0 - MODULATION_POLICY["cost_attenuation_weight"] * cost, 12
    )
    expected_multiplier = round(
        min(
            MODULATION_POLICY["maximum_multiplier"],
            max(
                MODULATION_POLICY["minimum_multiplier"],
                expected_pre_cost * expected_cost_factor,
            ),
        ),
        12,
    )
    expected_unclipped = round(abs(base) * expected_multiplier, 12)
    expected_magnitude = min(
        MODULATION_POLICY["credit_clip"], expected_unclipped
    )
    expected_modulated = round(
        expected_magnitude if base > 0.0 else -expected_magnitude if base < 0.0 else 0.0,
        12,
    )
    if (
        receipt["verifier_sign"] != _sign(base)
        or pre_cost != expected_pre_cost
        or cost_factor != expected_cost_factor
        or multiplier != expected_multiplier
        or unclipped != expected_unclipped
        or modulated != expected_modulated
        or receipt["credit_clip_applied"]
        is not (expected_unclipped > MODULATION_POLICY["credit_clip"])
        or _sign(modulated) != _sign(base)
    ):
        raise ValueError("V2.42.23 sign-preserving modulation formula drifted")
    if verified_contribution is not None:
        validate_verified_terminal_contribution(verified_contribution)
        if (
            receipt["verified_contribution_sha256"]
            != verified_contribution["record_sha256"]
            or receipt["base_verified_advantage"]
            != verified_contribution["mean_signed_terminal_contribution"]
            or receipt["opaque_step_ref_sha256"]
            != verified_contribution["opaque_step_ref_sha256"]
            or receipt["source_checkpoint_sha256"]
            != verified_contribution["source_checkpoint_sha256"]
        ):
            raise ValueError("V2.42.23 verified contribution binding drifted")
    if amplitude_features is not None:
        validate_amplitude_features(amplitude_features)
        if (
            receipt["amplitude_feature_sha256"]
            != amplitude_features["feature_sha256"]
            or receipt["entropy_absolute_magnitude"]
            != abs(float(amplitude_features["entropy_reduction"]))
            or receipt["entropy_direction"]
            != _entropy_direction(float(amplitude_features["entropy_reduction"]))
            or receipt["provenance_role"]
            != amplitude_features["provenance_role"]
            or receipt["provenance_strength"]
            != amplitude_features["provenance_strength"]
            or receipt["cost_fraction"] != amplitude_features["cost_fraction"]
        ):
            raise ValueError("V2.42.23 amplitude feature binding drifted")
