"""Pure, label-blind V2.42.11 entropy-controller decision kernel.

The kernel consumes one sealed action-response model and five numeric signals
derived from the current forward pass.  It has no file, environment, network,
model-client, search-client, evaluator, or process surface.  It selects at
most one preregistered action for a decision context, or emits an explicit
``stop``/``abstain`` receipt.

This module does not implement the state-transition adapters that execute an
action.  In particular, it never calls the historical projection-only OWIC
arm.  A separately frozen publisher must bind this kernel and real,
provenance-preserving adapters to one selected candidate parent before any
benchmark execution can be authorized.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


POLICY_ID = "v24211_label_blind_entropy_voc_controller_v1"
MODEL_ROLE = "v24123_entropy_action_response_model"
RECEIPT_ROLE = "v24211_entropy_controller_decision_receipt"
FEATURE_SCHEMA_VERSION = 1
MAX_PREDICTED_SYSTEM_TOKENS = 10**12

RISK_LAYERS = ("anchor", "coverage", "row_eligibility", "cell_value")
SIGNAL_KEYS = (
    "anchor_risk_proxy",
    "coverage_risk_proxy",
    "row_eligibility_risk_proxy",
    "cell_value_risk_proxy",
    "anchor_normalized_entropy",
)
FEATURE_KEYS = tuple(
    [
        key
        for layer in RISK_LAYERS
        for key in (f"{layer}_risk_proxy", f"{layer}_risk_available")
    ]
    + ["anchor_normalized_entropy", "anchor_entropy_available"]
)
NO_ENTROPY_FEATURE_KEYS = tuple(
    key
    for key in FEATURE_KEYS
    if key not in {"anchor_normalized_entropy", "anchor_entropy_available"}
)
CONTEXT_ACTIONS = {
    "anchor": ("resolve_anchor", "regenerate_hypotheses", "falsify_anchor"),
    "late_0": ("discover_entities", "audit_scope", "test_row_constraint"),
    "late_1": ("audit_scope", "test_row_constraint", "fill_cell"),
}
POLICY_BRANCHES = {
    "full_entropy": "full_model",
    "no_entropy": "no_entropy_baseline",
}
MODEL_OUTPUTS = ("task_contribution", "log_action_system_tokens")

MODEL_KEYS = {
    "artifact_version",
    "role",
    "job_manifest_sha256",
    "model_ready",
    "blockers",
    "full_model",
    "no_entropy_baseline",
    "fit_record_count",
    "calibration_record_count",
    "fit_task_clusters",
    "calibration_task_clusters",
    "ridge_lambda",
    "minimum_fit_records_per_context_action",
    "minimum_calibration_records_per_context_action",
    "fit_calibration_aggregate_sha256",
    "audit_outcomes_read",
    "controller_or_training_authorized",
    "model_sha256",
}
BRANCH_KEYS = {"feature_keys", "models"}
ACTION_MODEL_KEYS = {
    "fit_records",
    "calibration_records",
    "raw_coefficients",
    "affine_calibrators",
}
RECEIPT_KEYS = {
    "artifact_version",
    "role",
    "policy_id",
    "label_blind",
    "opaque_task_ref_sha256",
    "decision_index",
    "policy_branch",
    "context",
    "pre_action_state_sha256",
    "selected_parent_manifest_sha256",
    "action_model_sha256",
    "action_model_job_manifest_sha256",
    "feature_schema_version",
    "four_layer_feature_projection",
    "feature_projection_sha256",
    "action_order",
    "predictions",
    "required_signal_available",
    "decision_kind",
    "selected_action",
    "decision_reason",
    "maximum_one_action_for_context",
    "strictly_positive_contribution_required",
    "tuned_net_value_epsilon",
    "question_text_read_by_controller",
    "mapping_gold_category_question_type_evaluator_score_or_reward_read",
    "file_environment_network_model_search_fetch_or_process_accessed",
    "receipt_sha256",
}


def object_sha256(value: object) -> str:
    """Hash a JSON-compatible object using the frozen canonical encoding."""

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value).issubset(set("0123456789abcdef"))
    )


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.11 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"V2.42.11 {label} is not finite")
    return number


def _positive_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"V2.42.11 {label} is not a positive integer")
    return value


def _validate_coefficients(
    value: object, *, width: int, label: str
) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != width:
        raise ValueError(f"V2.42.11 {label} width drifted")
    return tuple(_finite(item, label=label) for item in value)


def _validate_branch(
    value: object,
    *,
    expected_feature_keys: tuple[str, ...],
    minimum_fit: int,
    minimum_calibration: int,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != BRANCH_KEYS:
        raise ValueError("V2.42.11 model branch schema drifted")
    if value.get("feature_keys") != list(expected_feature_keys):
        raise ValueError("V2.42.11 model feature order drifted")
    models = value.get("models")
    if not isinstance(models, dict) or tuple(models) != tuple(CONTEXT_ACTIONS):
        raise ValueError("V2.42.11 model context order drifted")

    width = len(expected_feature_keys) + 1
    for context, actions in CONTEXT_ACTIONS.items():
        context_models = models.get(context)
        if not isinstance(context_models, dict) or tuple(context_models) != actions:
            raise ValueError("V2.42.11 model action order drifted")
        for action in actions:
            action_model = context_models[action]
            if not isinstance(action_model, dict) or set(action_model) != ACTION_MODEL_KEYS:
                raise ValueError("V2.42.11 action-model schema drifted")
            fit_records = _positive_integer(
                action_model.get("fit_records"), label="fit record count"
            )
            calibration_records = _positive_integer(
                action_model.get("calibration_records"),
                label="calibration record count",
            )
            if fit_records < minimum_fit or calibration_records < minimum_calibration:
                raise ValueError("V2.42.11 action-model support is below its seal")
            raw = action_model.get("raw_coefficients")
            calibrators = action_model.get("affine_calibrators")
            if (
                not isinstance(raw, dict)
                or tuple(raw) != MODEL_OUTPUTS
                or not isinstance(calibrators, dict)
                or tuple(calibrators) != MODEL_OUTPUTS
            ):
                raise ValueError("V2.42.11 action-model output schema drifted")
            for output in MODEL_OUTPUTS:
                _validate_coefficients(
                    raw[output], width=width, label=f"{context}/{action}/{output}"
                )
                _validate_coefficients(
                    calibrators[output],
                    width=2,
                    label=f"{context}/{action}/{output} calibrator",
                )
    return value


def validate_action_model(
    model: object,
    *,
    expected_model_sha256: str,
    expected_job_manifest_sha256: str,
) -> dict[str, Any]:
    """Validate the exact sealed V2.41.23 model without opening its sources."""

    if not _is_sha256(expected_model_sha256) or not _is_sha256(
        expected_job_manifest_sha256
    ):
        raise ValueError("V2.42.11 expected model binding is invalid")
    if not isinstance(model, dict) or set(model) != MODEL_KEYS:
        raise ValueError("V2.42.11 action-model schema is not exact")
    unsigned = copy.deepcopy(model)
    seal = unsigned.pop("model_sha256", None)
    if (
        model.get("artifact_version") != 1
        or model.get("role") != MODEL_ROLE
        or seal != expected_model_sha256
        or seal != object_sha256(unsigned)
        or model.get("job_manifest_sha256") != expected_job_manifest_sha256
        or model.get("model_ready") is not True
        or model.get("blockers") != []
        or model.get("audit_outcomes_read") is not False
        or model.get("controller_or_training_authorized") is not False
        or not _is_sha256(model.get("fit_calibration_aggregate_sha256"))
    ):
        raise ValueError("V2.42.11 action-model seal or provenance drifted")
    minimum_fit = _positive_integer(
        model.get("minimum_fit_records_per_context_action"),
        label="minimum fit support",
    )
    minimum_calibration = _positive_integer(
        model.get("minimum_calibration_records_per_context_action"),
        label="minimum calibration support",
    )
    for key in (
        "fit_record_count",
        "calibration_record_count",
        "fit_task_clusters",
        "calibration_task_clusters",
    ):
        _positive_integer(model.get(key), label=key)
    if _finite(model.get("ridge_lambda"), label="ridge lambda") <= 0.0:
        raise ValueError("V2.42.11 ridge lambda is not positive")
    _validate_branch(
        model.get("full_model"),
        expected_feature_keys=FEATURE_KEYS,
        minimum_fit=minimum_fit,
        minimum_calibration=minimum_calibration,
    )
    _validate_branch(
        model.get("no_entropy_baseline"),
        expected_feature_keys=NO_ENTROPY_FEATURE_KEYS,
        minimum_fit=minimum_fit,
        minimum_calibration=minimum_calibration,
    )
    return copy.deepcopy(model)


def project_four_layer_features(signals: object) -> dict[str, float]:
    """Project five same-pass signals into the frozen ten-coordinate schema."""

    if not isinstance(signals, Mapping) or tuple(signals) != SIGNAL_KEYS:
        raise ValueError("V2.42.11 signal schema or order drifted")

    clean: dict[str, float | None] = {}
    for key in SIGNAL_KEYS:
        value = signals[key]
        if value is None:
            clean[key] = None
            continue
        number = _finite(value, label=key)
        if not 0.0 <= number <= 1.0:
            raise ValueError(f"V2.42.11 {key} is outside [0,1]")
        clean[key] = number

    output: dict[str, float] = {}
    for layer in RISK_LAYERS:
        key = f"{layer}_risk_proxy"
        value = clean[key]
        output[key] = 0.0 if value is None else value
        output[f"{layer}_risk_available"] = 0.0 if value is None else 1.0
    entropy = clean["anchor_normalized_entropy"]
    output["anchor_normalized_entropy"] = 0.0 if entropy is None else entropy
    output["anchor_entropy_available"] = 0.0 if entropy is None else 1.0
    if tuple(output) != FEATURE_KEYS:
        raise RuntimeError("V2.42.11 projected feature order drifted")
    return output


def required_signal_available(
    features: Mapping[str, float], *, context: str, policy_branch: str
) -> bool:
    """Apply the frozen V2.41.92 branch-specific abstention rule."""

    if tuple(features) != FEATURE_KEYS or policy_branch not in POLICY_BRANCHES:
        raise ValueError("V2.42.11 availability input is invalid")
    if context == "anchor":
        risk = features["anchor_risk_available"] == 1.0
        return risk and (
            policy_branch == "no_entropy"
            or features["anchor_entropy_available"] == 1.0
        )
    if context == "late_0":
        return features["coverage_risk_available"] == 1.0
    if context == "late_1":
        return bool(
            features["row_eligibility_risk_available"] == 1.0
            or features["cell_value_risk_available"] == 1.0
        )
    raise ValueError("V2.42.11 context is not registered")


def _predict(
    branch: Mapping[str, Any],
    *,
    context: str,
    action: str,
    features: Mapping[str, float],
) -> dict[str, float | int | None]:
    keys = tuple(branch["feature_keys"])
    vector = (1.0, *(features[key] for key in keys))
    model = branch["models"][context][action]
    calibrated: dict[str, float] = {}
    for output in MODEL_OUTPUTS:
        raw = sum(
            coefficient * value
            for coefficient, value in zip(
                model["raw_coefficients"][output], vector, strict=True
            )
        )
        intercept, slope = model["affine_calibrators"][output]
        calibrated[output] = intercept + slope * raw
        if not math.isfinite(calibrated[output]):
            raise ValueError("V2.42.11 calibrated prediction is not finite")

    contribution = round(
        min(1.0, max(-1.0, calibrated["task_contribution"])), 12
    )
    log_tokens = max(0.0, calibrated["log_action_system_tokens"])
    if log_tokens > math.log1p(MAX_PREDICTED_SYSTEM_TOKENS):
        tokens: int | None = None
    else:
        tokens = max(0, int(round(math.expm1(log_tokens))))
    return {
        "predicted_task_contribution": contribution,
        "predicted_action_system_tokens": tokens,
        "predicted_contribution_per_system_token": (
            round(contribution / tokens, 18)
            if tokens is not None and tokens > 0
            else None
        ),
    }


def validate_decision_receipt(receipt: object) -> dict[str, Any]:
    """Validate a content-free decision receipt and its canonical seal."""

    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
        raise ValueError("V2.42.11 receipt schema is not exact")
    unsigned = copy.deepcopy(receipt)
    seal = unsigned.pop("receipt_sha256", None)
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("label_blind") is not True
        or seal != object_sha256(unsigned)
        or any(
            not _is_sha256(receipt.get(key))
            for key in (
                "opaque_task_ref_sha256",
                "pre_action_state_sha256",
                "selected_parent_manifest_sha256",
                "action_model_sha256",
                "action_model_job_manifest_sha256",
                "feature_projection_sha256",
            )
        )
        or receipt.get("feature_schema_version") != FEATURE_SCHEMA_VERSION
        or isinstance(receipt.get("decision_index"), bool)
        or not isinstance(receipt.get("decision_index"), int)
        or receipt.get("decision_index") < 0
        or receipt.get("policy_branch") not in POLICY_BRANCHES
        or receipt.get("context") not in CONTEXT_ACTIONS
        or receipt.get("action_order")
        != list(CONTEXT_ACTIONS[receipt.get("context")])
        or receipt.get("decision_kind") not in {"action", "stop", "abstain"}
        or receipt.get("maximum_one_action_for_context") is not True
        or receipt.get("strictly_positive_contribution_required") is not True
        or receipt.get("tuned_net_value_epsilon") is not None
        or receipt.get("question_text_read_by_controller") is not False
        or receipt.get(
            "mapping_gold_category_question_type_evaluator_score_or_reward_read"
        )
        is not False
        or receipt.get(
            "file_environment_network_model_search_fetch_or_process_accessed"
        )
        is not False
    ):
        raise ValueError("V2.42.11 receipt seal or safety contract drifted")
    projection = receipt.get("four_layer_feature_projection")
    if (
        not isinstance(projection, dict)
        or tuple(projection) != FEATURE_KEYS
        or object_sha256(projection) != receipt["feature_projection_sha256"]
        or any(
            not 0.0 <= _finite(projection[key], label=key) <= 1.0
            for key in FEATURE_KEYS
        )
        or any(
            projection[f"{layer}_risk_available"] not in {0.0, 1.0}
            or projection[f"{layer}_risk_available"] == 0.0
            and projection[f"{layer}_risk_proxy"] != 0.0
            for layer in RISK_LAYERS
        )
        or projection["anchor_entropy_available"] not in {0.0, 1.0}
        or projection["anchor_entropy_available"] == 0.0
        and projection["anchor_normalized_entropy"] != 0.0
    ):
        raise ValueError("V2.42.11 receipt feature projection drifted")

    context = receipt["context"]
    actions = CONTEXT_ACTIONS[context]
    predictions = receipt.get("predictions")
    prediction_keys = {
        "predicted_task_contribution",
        "predicted_action_system_tokens",
        "predicted_contribution_per_system_token",
    }
    if not isinstance(predictions, dict) or tuple(predictions) != actions:
        raise ValueError("V2.42.11 receipt prediction slate drifted")
    for action in actions:
        prediction = predictions[action]
        if not isinstance(prediction, dict) or set(prediction) != prediction_keys:
            raise ValueError("V2.42.11 receipt prediction schema drifted")
        contribution = _finite(
            prediction["predicted_task_contribution"],
            label="predicted task contribution",
        )
        tokens = prediction["predicted_action_system_tokens"]
        ratio = prediction["predicted_contribution_per_system_token"]
        if not -1.0 <= contribution <= 1.0:
            raise ValueError("V2.42.11 receipt contribution is outside [-1,1]")
        if tokens is not None and (
            isinstance(tokens, bool)
            or not isinstance(tokens, int)
            or not 0 <= tokens <= MAX_PREDICTED_SYSTEM_TOKENS
        ):
            raise ValueError("V2.42.11 receipt predicted cost is invalid")
        expected_ratio = (
            round(contribution / tokens, 18)
            if tokens is not None and tokens > 0
            else None
        )
        if ratio != expected_ratio:
            raise ValueError("V2.42.11 receipt value-per-token ratio drifted")

    expected_signal = required_signal_available(
        projection,
        context=context,
        policy_branch=receipt["policy_branch"],
    )
    if receipt.get("required_signal_available") is not expected_signal:
        raise ValueError("V2.42.11 receipt availability decision drifted")
    if not expected_signal:
        expected_kind = "abstain"
        expected_action = None
        expected_reason = "required_same_pass_signal_unavailable"
    elif any(
        predictions[action]["predicted_action_system_tokens"] is None
        or predictions[action]["predicted_action_system_tokens"] <= 0
        for action in actions
    ):
        expected_kind = "abstain"
        expected_action = None
        expected_reason = "positive_finite_predicted_action_cost_unavailable"
    else:
        beneficial = [
            action
            for action in actions
            if predictions[action]["predicted_task_contribution"] > 0.0
        ]
        if not beneficial:
            expected_kind = "stop"
            expected_action = None
            expected_reason = "no_strictly_positive_predicted_contribution"
        else:
            rank = {action: index for index, action in enumerate(actions)}
            expected_action = min(
                beneficial,
                key=lambda action: (
                    -float(
                        predictions[action][
                            "predicted_contribution_per_system_token"
                        ]
                    ),
                    -float(predictions[action]["predicted_task_contribution"]),
                    int(predictions[action]["predicted_action_system_tokens"]),
                    rank[action],
                ),
            )
            expected_kind = "action"
            expected_reason = (
                "maximum_strictly_positive_predicted_contribution_per_token"
            )
    if (
        receipt.get("decision_kind") != expected_kind
        or receipt.get("selected_action") != expected_action
        or receipt.get("decision_reason") != expected_reason
    ):
        raise ValueError("V2.42.11 receipt action disposition drifted")
    return copy.deepcopy(receipt)


def decide_entropy_action(
    *,
    model: object,
    expected_model_sha256: str,
    expected_job_manifest_sha256: str,
    signals: object,
    context: str,
    policy_branch: str,
    opaque_task_ref_sha256: str,
    decision_index: int,
    pre_action_state_sha256: str,
    selected_parent_manifest_sha256: str,
) -> dict[str, Any]:
    """Select one action, stop, or abstain and return a sealed receipt."""

    if context not in CONTEXT_ACTIONS or policy_branch not in POLICY_BRANCHES:
        raise ValueError("V2.42.11 context or policy branch is not registered")
    if (
        not _is_sha256(opaque_task_ref_sha256)
        or not _is_sha256(pre_action_state_sha256)
        or not _is_sha256(selected_parent_manifest_sha256)
        or isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        raise ValueError("V2.42.11 decision identity is invalid")
    clean_model = validate_action_model(
        model,
        expected_model_sha256=expected_model_sha256,
        expected_job_manifest_sha256=expected_job_manifest_sha256,
    )
    features = project_four_layer_features(signals)
    branch = clean_model[POLICY_BRANCHES[policy_branch]]
    action_order = CONTEXT_ACTIONS[context]
    predictions = {
        action: _predict(
            branch,
            context=context,
            action=action,
            features=features,
        )
        for action in action_order
    }
    signal_available = required_signal_available(
        features, context=context, policy_branch=policy_branch
    )

    if not signal_available:
        decision_kind = "abstain"
        selected_action = None
        reason = "required_same_pass_signal_unavailable"
    elif any(
        prediction["predicted_action_system_tokens"] is None
        or prediction["predicted_action_system_tokens"] <= 0
        for prediction in predictions.values()
    ):
        decision_kind = "abstain"
        selected_action = None
        reason = "positive_finite_predicted_action_cost_unavailable"
    else:
        available = [
            action
            for action in action_order
            if predictions[action]["predicted_task_contribution"] > 0.0
        ]
        if not available:
            decision_kind = "stop"
            selected_action = None
            reason = "no_strictly_positive_predicted_contribution"
        else:
            rank = {action: index for index, action in enumerate(action_order)}
            selected_action = min(
                available,
                key=lambda action: (
                    -float(
                        predictions[action][
                            "predicted_contribution_per_system_token"
                        ]
                    ),
                    -float(predictions[action]["predicted_task_contribution"]),
                    int(predictions[action]["predicted_action_system_tokens"]),
                    rank[action],
                ),
            )
            decision_kind = "action"
            reason = "maximum_strictly_positive_predicted_contribution_per_token"

    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "label_blind": True,
        "opaque_task_ref_sha256": opaque_task_ref_sha256,
        "decision_index": decision_index,
        "policy_branch": policy_branch,
        "context": context,
        "pre_action_state_sha256": pre_action_state_sha256,
        "selected_parent_manifest_sha256": selected_parent_manifest_sha256,
        "action_model_sha256": clean_model["model_sha256"],
        "action_model_job_manifest_sha256": clean_model["job_manifest_sha256"],
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "four_layer_feature_projection": features,
        "feature_projection_sha256": object_sha256(features),
        "action_order": list(action_order),
        "predictions": predictions,
        "required_signal_available": signal_available,
        "decision_kind": decision_kind,
        "selected_action": selected_action,
        "decision_reason": reason,
        "maximum_one_action_for_context": True,
        "strictly_positive_contribution_required": True,
        "tuned_net_value_epsilon": None,
        "question_text_read_by_controller": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    receipt["receipt_sha256"] = object_sha256(receipt)
    return validate_decision_receipt(receipt)


__all__ = [
    "CONTEXT_ACTIONS",
    "FEATURE_KEYS",
    "MAX_PREDICTED_SYSTEM_TOKENS",
    "MODEL_ROLE",
    "NO_ENTROPY_FEATURE_KEYS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "RISK_LAYERS",
    "SIGNAL_KEYS",
    "decide_entropy_action",
    "object_sha256",
    "project_four_layer_features",
    "required_signal_available",
    "validate_action_model",
    "validate_decision_receipt",
]
