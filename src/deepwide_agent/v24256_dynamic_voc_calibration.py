"""Build-only split calibration for finite-depth dynamic VOC.

V2.41.23 estimates a *myopic* terminal contribution from matched no-op/action
continuations.  Its aggregate intentionally retains pre-action features,
terminal contribution, cost, and provenance hashes, but not a calibrated
successor-state distribution.  It therefore cannot be silently reinterpreted
as a dynamic transition model.

This module defines the missing data boundary.  It consumes only content-free
development records:

* a preregistered depth-unrolled state/action DAG;
* post-action transition records that bind pre/post state projections; and
* stop-now terminal-loss records joined to an evaluator only after prediction
  freeze.

Fit and calibration task-cluster sets are exact and disjoint.  Transition
probabilities and stop losses are estimated from the fit clusters only.
Calibration clusters are used only for normalized multiclass Brier and stop
loss MAE gates.  Every task cluster is one statistical unit, so replicate
counts cannot manufacture support.  If any support or calibration gate fails,
the emitted V2.42.55 model marks every transition uncalibrated and all three
policies abstain.

The module has no file, environment, network, model, search, evaluator,
subprocess, or active-runtime surface.  It grants no production, benchmark,
training, or leaderboard authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import defaultdict
from typing import Any, Mapping, Sequence

from .v24255_finite_depth_dynamic_voc import (
    build_transition_model,
    evaluate_voc_policies,
    validate_transition_model,
)


POLICY_ID = "v24256_label_blind_dynamic_voc_split_calibration_v1"
TOPOLOGY_ROLE = "v24256_dynamic_voc_topology"
PROTOCOL_ROLE = "v24256_dynamic_voc_calibration_protocol"
TRANSITION_SAMPLE_ROLE = "v24256_post_action_transition_sample"
STOP_SAMPLE_ROLE = "v24256_stop_terminal_loss_sample"
REPORT_ROLE = "v24256_dynamic_voc_calibration_report"
PACKAGE_ROLE = "v24256_dynamic_voc_calibrated_source_package"

FIT_ROLE = "development_fit"
CALIBRATION_ROLE = "development_calibration"
PARTITION_ROLES = (FIT_ROLE, CALIBRATION_ROLE)
PRECISION = 12
MAX_TASK_CLUSTERS = 10_000
MAX_SAMPLES = 1_000_000
BELIEF_ENTROPY_ROLE = (
    "predeclared_diagnostic_feature_not_calibrated_terminal_utility"
)

PRODUCTION_PACKAGE_AUTHORIZED = False
RUNTIME_FORWARD_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False
BENCHMARK_EVALUATOR_LAUNCH_AUTHORIZED = False
LEADERBOARD_OR_SOTA_CLAIM_AUTHORIZED = False

FORBIDDEN_RUNTIME_METADATA_KEYS = frozenset(
    {
        "answer",
        "answerkey",
        "benchmarkcategory",
        "benchmarklabel",
        "benchmarksubset",
        "category",
        "correctness",
        "evaluatoroutput",
        "evaluatorpayload",
        "evaluatorscore",
        "finaloutcome",
        "gold",
        "groundtruth",
        "mapping",
        "officialmetrics",
        "prediction",
        "question",
        "questiontype",
        "rawobservation",
        "resultscsv",
        "reward",
        "score",
        "split",
        "taskcategory",
        "taskid",
        "verifieroutcome",
    }
)

TOPOLOGY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "abstraction_manifest_sha256",
        "root_state_ref_sha256",
        "max_depth",
        "max_budget",
        "belief_entropy_role",
        "state_order",
        "states",
        "raw_state_action_observation_question_or_id_embedded",
        "benchmark_category_question_type_split_gold_mapping_or_score_used",
        "topology_sha256",
    }
)
TOPOLOGY_STATE_KEYS = frozenset(
    {"state_ref_sha256", "belief_entropy", "actions"}
)
TOPOLOGY_ACTION_KEYS = frozenset(
    {
        "action_ref_sha256",
        "cost",
        "allowed_next_state_ref_sha256s",
    }
)
PROTOCOL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "topology_sha256",
        "fit_partition_manifest_sha256",
        "calibration_partition_manifest_sha256",
        "fit_task_cluster_ref_sha256s",
        "calibration_task_cluster_ref_sha256s",
        "fit_task_cluster_count",
        "calibration_task_cluster_count",
        "dirichlet_alpha_per_successor",
        "minimum_fit_transition_clusters_per_action",
        "minimum_calibration_transition_clusters_per_action",
        "maximum_normalized_multiclass_brier",
        "minimum_fit_stop_clusters_per_state",
        "minimum_calibration_stop_clusters_per_state",
        "maximum_stop_loss_mae",
        "transition_fit_formula",
        "transition_calibration_formula",
        "stop_loss_fit_formula",
        "stop_loss_calibration_formula",
        "task_cluster_is_statistical_unit",
        "fit_and_calibration_clusters_disjoint",
        "calibration_outcomes_used_for_gate_not_fit",
        "audit_test_or_benchmark_clusters_allowed",
        "runtime_label_or_evaluator_metadata_available",
        "controller_training_or_benchmark_authorized",
        "protocol_sha256",
    }
)
TRANSITION_SAMPLE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "topology_sha256",
        "protocol_sha256",
        "partition_role",
        "task_cluster_ref_sha256",
        "source_state_ref_sha256",
        "action_ref_sha256",
        "next_state_ref_sha256",
        "pre_state_projection_sha256",
        "post_state_projection_sha256",
        "action_observation_receipt_sha256",
        "state_transition_receipt_sha256",
        "same_pass_transition",
        "runtime_evaluator_or_score_used",
        "raw_state_action_observation_question_or_id_embedded",
        "sample_sha256",
    }
)
STOP_SAMPLE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "topology_sha256",
        "protocol_sha256",
        "partition_role",
        "task_cluster_ref_sha256",
        "state_ref_sha256",
        "state_projection_sha256",
        "prediction_freeze_sha256",
        "terminal_receipt_sha256",
        "evaluator_protocol_sha256",
        "evaluator_artifact_sha256",
        "terminal_status",
        "evaluator_valid",
        "terminal_loss",
        "prediction_frozen_before_evaluator_read",
        "evaluator_joined_post_terminal_only",
        "development_terminal_loss_used_offline",
        "official_score_used_as_terminal_loss",
        "raw_prediction_evaluator_payload_question_or_id_embedded",
        "sample_sha256",
    }
)
ACTION_REPORT_KEYS = frozenset(
    {
        "source_state_ref_sha256",
        "action_ref_sha256",
        "cost",
        "allowed_next_state_ref_sha256s",
        "fit_task_cluster_count",
        "calibration_task_cluster_count",
        "fitted_transition_probabilities",
        "normalized_multiclass_brier",
        "maximum_normalized_multiclass_brier",
        "fit_support_ready",
        "calibration_support_ready",
        "calibration_metric_ready",
        "gate_passed",
    }
)
PROBABILITY_ROW_KEYS = frozenset(
    {"next_state_ref_sha256", "probability"}
)
STATE_REPORT_KEYS = frozenset(
    {
        "state_ref_sha256",
        "fit_task_cluster_count",
        "calibration_task_cluster_count",
        "fitted_stop_terminal_loss",
        "stop_loss_mae",
        "maximum_stop_loss_mae",
        "fit_support_ready",
        "calibration_support_ready",
        "calibration_metric_ready",
        "gate_passed",
    }
)
REPORT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind",
        "build_only",
        "topology_sha256",
        "protocol_sha256",
        "fit_data_manifest_sha256",
        "calibration_data_manifest_sha256",
        "fit_task_cluster_count",
        "calibration_task_cluster_count",
        "fit_partition_cluster_coverage_complete",
        "calibration_partition_cluster_coverage_complete",
        "task_cluster_is_statistical_unit",
        "fit_and_calibration_clusters_disjoint",
        "transition_probabilities_fit_from_fit_clusters_only",
        "stop_losses_fit_from_fit_clusters_only",
        "calibration_outcomes_used_for_gate_not_fit",
        "action_calibration",
        "state_stop_loss_calibration",
        "blockers",
        "calibration_complete",
        "development_terminal_loss_used_offline",
        "runtime_evaluator_payload_available",
        "audit_test_or_benchmark_outcome_used",
        "raw_state_action_observation_prediction_question_or_id_embedded",
        "controller_training_runtime_evaluator_or_leaderboard_authorized",
        "report_sha256",
    }
)
PACKAGE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind",
        "build_only",
        "topology_sha256",
        "protocol_sha256",
        "calibration_report",
        "calibration_report_sha256",
        "v24255_transition_model",
        "v24255_transition_model_sha256",
        "calibration_complete",
        "incomplete_calibration_forces_all_policies_to_abstain",
        "development_only_fit_and_calibration",
        "runtime_evaluator_payload_available",
        "production_package_authorized",
        "runtime_forward_authorized",
        "credit_training_authorized",
        "benchmark_evaluator_launch_authorized",
        "leaderboard_or_sota_claim_authorized",
        "package_sha256",
    }
)


def object_sha256(value: object) -> str:
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
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.56 {label} schema is not exact")
    return value


def _integer(
    value: object, *, label: str, minimum: int, maximum: int
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.56 {label} is outside the frozen range")
    return value


def _number(
    value: object, *, label: str, minimum: float, maximum: float
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"V2.42.56 {label} is not finite")
    number = float(value)
    if number < minimum or number > maximum:
        raise ValueError(f"V2.42.56 {label} is outside the frozen range")
    return 0.0 if number == 0.0 else number


def _quantize(value: float) -> float:
    rounded = round(float(value), PRECISION)
    return 0.0 if rounded == 0.0 else rounded


def _normalized_metadata_key(value: object) -> str:
    return "".join(
        character for character in str(value).casefold() if character.isalnum()
    )


def reject_privileged_runtime_metadata(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalized_metadata_key(key) in FORBIDDEN_RUNTIME_METADATA_KEYS:
                raise ValueError("V2.42.56 privileged runtime metadata rejected")
            reject_privileged_runtime_metadata(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            reject_privileged_runtime_metadata(nested)


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    if not _is_sha256(value.get(seal_key)):
        return False
    unsigned = dict(value)
    seal = unsigned.pop(seal_key)
    return seal == object_sha256(unsigned)


def _normalize_topology_states(
    states: object, *, max_budget: int
) -> list[dict[str, Any]]:
    if not isinstance(states, list) or not states:
        raise ValueError("V2.42.56 topology states are absent")
    normalized: list[dict[str, Any]] = []
    state_refs: set[str] = set()
    action_refs: set[str] = set()
    action_count = 0
    for state_index, raw_state in enumerate(states):
        state = _exact(
            raw_state,
            keys=TOPOLOGY_STATE_KEYS,
            label=f"topology state {state_index}",
        )
        state_ref = state["state_ref_sha256"]
        if not _is_sha256(state_ref) or state_ref in state_refs:
            raise ValueError("V2.42.56 state reference is invalid or duplicated")
        state_refs.add(str(state_ref))
        entropy = _number(
            state["belief_entropy"],
            label="belief entropy",
            minimum=0.0,
            maximum=1.0,
        )
        raw_actions = state["actions"]
        if not isinstance(raw_actions, list):
            raise ValueError("V2.42.56 topology actions are not a list")
        actions: list[dict[str, Any]] = []
        for action_index, raw_action in enumerate(raw_actions):
            action = _exact(
                raw_action,
                keys=TOPOLOGY_ACTION_KEYS,
                label=f"topology action {state_index}/{action_index}",
            )
            action_ref = action["action_ref_sha256"]
            if not _is_sha256(action_ref) or action_ref in action_refs:
                raise ValueError(
                    "V2.42.56 action reference is invalid or duplicated"
                )
            action_refs.add(str(action_ref))
            cost = _integer(
                action["cost"],
                label="action cost",
                minimum=1,
                maximum=max_budget,
            )
            successors = action["allowed_next_state_ref_sha256s"]
            if (
                not isinstance(successors, list)
                or not successors
                or len(successors) != len(set(successors))
                or any(not _is_sha256(item) for item in successors)
            ):
                raise ValueError("V2.42.56 allowed successors are invalid")
            actions.append(
                {
                    "action_ref_sha256": str(action_ref),
                    "cost": cost,
                    "allowed_next_state_ref_sha256s": [
                        str(item) for item in successors
                    ],
                }
            )
            action_count += 1
        normalized.append(
            {
                "state_ref_sha256": str(state_ref),
                "belief_entropy": entropy,
                "actions": actions,
            }
        )
    if action_count == 0:
        raise ValueError("V2.42.56 topology has no computation action")
    if any(
        successor not in state_refs
        for state in normalized
        for action in state["actions"]
        for successor in action["allowed_next_state_ref_sha256s"]
    ):
        raise ValueError("V2.42.56 topology successor state is absent")
    return normalized


def _validate_topology_with_v24255(
    *,
    states: list[dict[str, Any]],
    root_state_ref_sha256: str,
    max_depth: int,
    max_budget: int,
) -> None:
    model_states: list[dict[str, Any]] = []
    for state in states:
        actions: list[dict[str, Any]] = []
        for action in state["actions"]:
            successors = action["allowed_next_state_ref_sha256s"]
            probability = 1.0 / len(successors)
            outcomes = [
                {
                    "next_state_ref_sha256": successor,
                    "probability": (
                        _quantize(probability)
                        if index < len(successors) - 1
                        else _quantize(
                            1.0
                            - math.fsum(
                                _quantize(probability)
                                for _ in range(len(successors) - 1)
                            )
                        )
                    ),
                    "calibration_ready": False,
                    "calibration_ref_sha256": None,
                }
                for index, successor in enumerate(successors)
            ]
            actions.append(
                {
                    "action_ref_sha256": action["action_ref_sha256"],
                    "cost": action["cost"],
                    "outcomes": outcomes,
                }
            )
        model_states.append(
            {
                "state_ref_sha256": state["state_ref_sha256"],
                "stop_terminal_loss": 1.0,
                "belief_entropy": state["belief_entropy"],
                "actions": actions,
            }
        )
    build_transition_model(
        model_fit_manifest_sha256=object_sha256(
            "v24256_topology_validation_fit"
        ),
        calibration_protocol_sha256=object_sha256(
            "v24256_topology_validation_protocol"
        ),
        root_state_ref_sha256=root_state_ref_sha256,
        max_depth=max_depth,
        max_budget=max_budget,
        states=model_states,
    )


def build_topology(
    *,
    abstraction_manifest_sha256: str,
    root_state_ref_sha256: str,
    max_depth: int,
    max_budget: int,
    states: object,
) -> dict[str, Any]:
    if (
        not _is_sha256(abstraction_manifest_sha256)
        or not _is_sha256(root_state_ref_sha256)
    ):
        raise ValueError("V2.42.56 topology identity is invalid")
    depth = _integer(
        max_depth, label="maximum depth", minimum=1, maximum=8
    )
    budget = _integer(
        max_budget, label="maximum budget", minimum=1, maximum=1_000_000
    )
    normalized = _normalize_topology_states(states, max_budget=budget)
    _validate_topology_with_v24255(
        states=normalized,
        root_state_ref_sha256=root_state_ref_sha256,
        max_depth=depth,
        max_budget=budget,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": TOPOLOGY_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "abstraction_manifest_sha256": abstraction_manifest_sha256,
        "root_state_ref_sha256": root_state_ref_sha256,
        "max_depth": depth,
        "max_budget": budget,
        "belief_entropy_role": BELIEF_ENTROPY_ROLE,
        "state_order": [
            state["state_ref_sha256"] for state in normalized
        ],
        "states": normalized,
        "raw_state_action_observation_question_or_id_embedded": False,
        "benchmark_category_question_type_split_gold_mapping_or_score_used": False,
    }
    value["topology_sha256"] = object_sha256(value)
    return validate_topology(value)


def validate_topology(value: object) -> dict[str, Any]:
    topology = _exact(value, keys=TOPOLOGY_KEYS, label="topology")
    unsigned = dict(topology)
    seal = unsigned.pop("topology_sha256", None)
    if (
        _integer(
            topology["artifact_version"],
            label="artifact version",
            minimum=1,
            maximum=1,
        )
        != 1
        or topology["role"] != TOPOLOGY_ROLE
        or topology["policy_id"] != POLICY_ID
        or topology["build_only"] is not True
        or not _is_sha256(topology["abstraction_manifest_sha256"])
        or not _is_sha256(topology["root_state_ref_sha256"])
        or topology["belief_entropy_role"] != BELIEF_ENTROPY_ROLE
        or topology[
            "raw_state_action_observation_question_or_id_embedded"
        ]
        is not False
        or topology[
            "benchmark_category_question_type_split_gold_mapping_or_score_used"
        ]
        is not False
        or seal != object_sha256(unsigned)
    ):
        raise ValueError("V2.42.56 topology seal or safety contract drifted")
    depth = _integer(
        topology["max_depth"],
        label="maximum depth",
        minimum=1,
        maximum=8,
    )
    budget = _integer(
        topology["max_budget"],
        label="maximum budget",
        minimum=1,
        maximum=1_000_000,
    )
    normalized = _normalize_topology_states(
        topology["states"], max_budget=budget
    )
    if (
        object_sha256(topology["states"]) != object_sha256(normalized)
        or topology["state_order"]
        != [state["state_ref_sha256"] for state in normalized]
    ):
        raise ValueError("V2.42.56 topology normalization drifted")
    _validate_topology_with_v24255(
        states=normalized,
        root_state_ref_sha256=str(topology["root_state_ref_sha256"]),
        max_depth=depth,
        max_budget=budget,
    )
    return copy.deepcopy(dict(topology))


def _cluster_refs(value: object, *, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > MAX_TASK_CLUSTERS
        or len(value) != len(set(value))
        or any(not _is_sha256(item) for item in value)
        or value != sorted(value)
    ):
        raise ValueError(f"V2.42.56 {label} cluster refs are invalid")
    return [str(item) for item in value]


def build_calibration_protocol(
    *,
    topology: object,
    fit_partition_manifest_sha256: str,
    calibration_partition_manifest_sha256: str,
    fit_task_cluster_ref_sha256s: list[str],
    calibration_task_cluster_ref_sha256s: list[str],
    dirichlet_alpha_per_successor: float,
    minimum_fit_transition_clusters_per_action: int,
    minimum_calibration_transition_clusters_per_action: int,
    maximum_normalized_multiclass_brier: float,
    minimum_fit_stop_clusters_per_state: int,
    minimum_calibration_stop_clusters_per_state: int,
    maximum_stop_loss_mae: float,
) -> dict[str, Any]:
    clean_topology = validate_topology(topology)
    if (
        not _is_sha256(fit_partition_manifest_sha256)
        or not _is_sha256(calibration_partition_manifest_sha256)
        or fit_partition_manifest_sha256
        == calibration_partition_manifest_sha256
    ):
        raise ValueError("V2.42.56 partition manifests are invalid")
    fit_clusters = _cluster_refs(
        fit_task_cluster_ref_sha256s, label="fit"
    )
    calibration_clusters = _cluster_refs(
        calibration_task_cluster_ref_sha256s, label="calibration"
    )
    if set(fit_clusters) & set(calibration_clusters):
        raise ValueError("V2.42.56 fit and calibration clusters overlap")
    alpha = _number(
        dirichlet_alpha_per_successor,
        label="Dirichlet alpha",
        minimum=1e-12,
        maximum=1_000.0,
    )
    min_fit_transition = _integer(
        minimum_fit_transition_clusters_per_action,
        label="minimum fit transition clusters",
        minimum=1,
        maximum=len(fit_clusters),
    )
    min_cal_transition = _integer(
        minimum_calibration_transition_clusters_per_action,
        label="minimum calibration transition clusters",
        minimum=1,
        maximum=len(calibration_clusters),
    )
    max_brier = _number(
        maximum_normalized_multiclass_brier,
        label="maximum normalized multiclass Brier",
        minimum=0.0,
        maximum=1.0,
    )
    min_fit_stop = _integer(
        minimum_fit_stop_clusters_per_state,
        label="minimum fit stop clusters",
        minimum=1,
        maximum=len(fit_clusters),
    )
    min_cal_stop = _integer(
        minimum_calibration_stop_clusters_per_state,
        label="minimum calibration stop clusters",
        minimum=1,
        maximum=len(calibration_clusters),
    )
    max_mae = _number(
        maximum_stop_loss_mae,
        label="maximum stop loss MAE",
        minimum=0.0,
        maximum=1.0,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PROTOCOL_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "topology_sha256": clean_topology["topology_sha256"],
        "fit_partition_manifest_sha256": fit_partition_manifest_sha256,
        "calibration_partition_manifest_sha256": (
            calibration_partition_manifest_sha256
        ),
        "fit_task_cluster_ref_sha256s": fit_clusters,
        "calibration_task_cluster_ref_sha256s": calibration_clusters,
        "fit_task_cluster_count": len(fit_clusters),
        "calibration_task_cluster_count": len(calibration_clusters),
        "dirichlet_alpha_per_successor": alpha,
        "minimum_fit_transition_clusters_per_action": min_fit_transition,
        "minimum_calibration_transition_clusters_per_action": (
            min_cal_transition
        ),
        "maximum_normalized_multiclass_brier": max_brier,
        "minimum_fit_stop_clusters_per_state": min_fit_stop,
        "minimum_calibration_stop_clusters_per_state": min_cal_stop,
        "maximum_stop_loss_mae": max_mae,
        "transition_fit_formula": (
            "cluster_equal_empirical_mass_plus_symmetric_dirichlet_alpha"
        ),
        "transition_calibration_formula": (
            "cluster_equal_mean_normalized_multiclass_brier"
        ),
        "stop_loss_fit_formula": (
            "mean_of_within_cluster_mean_terminal_loss"
        ),
        "stop_loss_calibration_formula": (
            "cluster_equal_mean_absolute_terminal_loss_error"
        ),
        "task_cluster_is_statistical_unit": True,
        "fit_and_calibration_clusters_disjoint": True,
        "calibration_outcomes_used_for_gate_not_fit": True,
        "audit_test_or_benchmark_clusters_allowed": False,
        "runtime_label_or_evaluator_metadata_available": False,
        "controller_training_or_benchmark_authorized": False,
    }
    value["protocol_sha256"] = object_sha256(value)
    return validate_calibration_protocol(
        value,
        topology=clean_topology,
    )


def validate_calibration_protocol(
    value: object, *, topology: object
) -> dict[str, Any]:
    clean_topology = validate_topology(topology)
    protocol = _exact(
        value, keys=PROTOCOL_KEYS, label="calibration protocol"
    )
    unsigned = dict(protocol)
    seal = unsigned.pop("protocol_sha256", None)
    fit_clusters = _cluster_refs(
        protocol["fit_task_cluster_ref_sha256s"], label="fit"
    )
    calibration_clusters = _cluster_refs(
        protocol["calibration_task_cluster_ref_sha256s"],
        label="calibration",
    )
    if (
        _integer(
            protocol["artifact_version"],
            label="artifact version",
            minimum=1,
            maximum=1,
        )
        != 1
        or protocol["role"] != PROTOCOL_ROLE
        or protocol["policy_id"] != POLICY_ID
        or protocol["build_only"] is not True
        or protocol["topology_sha256"] != clean_topology["topology_sha256"]
        or not _is_sha256(protocol["fit_partition_manifest_sha256"])
        or not _is_sha256(
            protocol["calibration_partition_manifest_sha256"]
        )
        or protocol["fit_partition_manifest_sha256"]
        == protocol["calibration_partition_manifest_sha256"]
        or set(fit_clusters) & set(calibration_clusters)
        or _integer(
            protocol["fit_task_cluster_count"],
            label="fit task cluster count",
            minimum=1,
            maximum=MAX_TASK_CLUSTERS,
        )
        != len(fit_clusters)
        or _integer(
            protocol["calibration_task_cluster_count"],
            label="calibration task cluster count",
            minimum=1,
            maximum=MAX_TASK_CLUSTERS,
        )
        != len(calibration_clusters)
        or protocol["transition_fit_formula"]
        != "cluster_equal_empirical_mass_plus_symmetric_dirichlet_alpha"
        or protocol["transition_calibration_formula"]
        != "cluster_equal_mean_normalized_multiclass_brier"
        or protocol["stop_loss_fit_formula"]
        != "mean_of_within_cluster_mean_terminal_loss"
        or protocol["stop_loss_calibration_formula"]
        != "cluster_equal_mean_absolute_terminal_loss_error"
        or protocol["task_cluster_is_statistical_unit"] is not True
        or protocol["fit_and_calibration_clusters_disjoint"] is not True
        or protocol["calibration_outcomes_used_for_gate_not_fit"] is not True
        or protocol["audit_test_or_benchmark_clusters_allowed"] is not False
        or protocol["runtime_label_or_evaluator_metadata_available"] is not False
        or protocol["controller_training_or_benchmark_authorized"] is not False
        or seal != object_sha256(unsigned)
    ):
        raise ValueError("V2.42.56 protocol seal or safety contract drifted")
    _number(
        protocol["dirichlet_alpha_per_successor"],
        label="Dirichlet alpha",
        minimum=1e-12,
        maximum=1_000.0,
    )
    _integer(
        protocol["minimum_fit_transition_clusters_per_action"],
        label="minimum fit transition clusters",
        minimum=1,
        maximum=len(fit_clusters),
    )
    _integer(
        protocol["minimum_calibration_transition_clusters_per_action"],
        label="minimum calibration transition clusters",
        minimum=1,
        maximum=len(calibration_clusters),
    )
    _number(
        protocol["maximum_normalized_multiclass_brier"],
        label="maximum normalized multiclass Brier",
        minimum=0.0,
        maximum=1.0,
    )
    _integer(
        protocol["minimum_fit_stop_clusters_per_state"],
        label="minimum fit stop clusters",
        minimum=1,
        maximum=len(fit_clusters),
    )
    _integer(
        protocol["minimum_calibration_stop_clusters_per_state"],
        label="minimum calibration stop clusters",
        minimum=1,
        maximum=len(calibration_clusters),
    )
    _number(
        protocol["maximum_stop_loss_mae"],
        label="maximum stop loss MAE",
        minimum=0.0,
        maximum=1.0,
    )
    return copy.deepcopy(dict(protocol))


def _topology_maps(
    topology: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, tuple[str, Mapping[str, Any]]]]:
    states = {
        state["state_ref_sha256"]: state for state in topology["states"]
    }
    actions = {
        action["action_ref_sha256"]: (state["state_ref_sha256"], action)
        for state in topology["states"]
        for action in state["actions"]
    }
    return states, actions


def _validate_partition_cluster(
    *,
    protocol: Mapping[str, Any],
    partition_role: object,
    task_cluster_ref_sha256: object,
) -> tuple[str, str]:
    if partition_role not in PARTITION_ROLES:
        raise ValueError("V2.42.56 audit/test/benchmark partition rejected")
    if not _is_sha256(task_cluster_ref_sha256):
        raise ValueError("V2.42.56 task cluster reference is invalid")
    expected = (
        protocol["fit_task_cluster_ref_sha256s"]
        if partition_role == FIT_ROLE
        else protocol["calibration_task_cluster_ref_sha256s"]
    )
    if task_cluster_ref_sha256 not in expected:
        raise ValueError("V2.42.56 task cluster is outside its frozen partition")
    return str(partition_role), str(task_cluster_ref_sha256)


def build_transition_sample(
    *,
    topology: object,
    protocol: object,
    partition_role: str,
    task_cluster_ref_sha256: str,
    source_state_ref_sha256: str,
    action_ref_sha256: str,
    next_state_ref_sha256: str,
    pre_state_projection_sha256: str,
    post_state_projection_sha256: str,
    action_observation_receipt_sha256: str,
    state_transition_receipt_sha256: str,
) -> dict[str, Any]:
    clean_topology = validate_topology(topology)
    clean_protocol = validate_calibration_protocol(
        protocol, topology=clean_topology
    )
    partition, cluster = _validate_partition_cluster(
        protocol=clean_protocol,
        partition_role=partition_role,
        task_cluster_ref_sha256=task_cluster_ref_sha256,
    )
    states, actions = _topology_maps(clean_topology)
    action_binding = actions.get(action_ref_sha256)
    hashes = (
        pre_state_projection_sha256,
        post_state_projection_sha256,
        action_observation_receipt_sha256,
        state_transition_receipt_sha256,
    )
    if (
        source_state_ref_sha256 not in states
        or action_binding is None
        or action_binding[0] != source_state_ref_sha256
        or next_state_ref_sha256
        not in action_binding[1]["allowed_next_state_ref_sha256s"]
        or not all(_is_sha256(item) for item in hashes)
    ):
        raise ValueError("V2.42.56 transition sample binding is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": TRANSITION_SAMPLE_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "topology_sha256": clean_topology["topology_sha256"],
        "protocol_sha256": clean_protocol["protocol_sha256"],
        "partition_role": partition,
        "task_cluster_ref_sha256": cluster,
        "source_state_ref_sha256": source_state_ref_sha256,
        "action_ref_sha256": action_ref_sha256,
        "next_state_ref_sha256": next_state_ref_sha256,
        "pre_state_projection_sha256": pre_state_projection_sha256,
        "post_state_projection_sha256": post_state_projection_sha256,
        "action_observation_receipt_sha256": (
            action_observation_receipt_sha256
        ),
        "state_transition_receipt_sha256": state_transition_receipt_sha256,
        "same_pass_transition": True,
        "runtime_evaluator_or_score_used": False,
        "raw_state_action_observation_question_or_id_embedded": False,
    }
    value["sample_sha256"] = object_sha256(value)
    return validate_transition_sample(
        value,
        topology=clean_topology,
        protocol=clean_protocol,
    )


def validate_transition_sample(
    value: object, *, topology: object, protocol: object
) -> dict[str, Any]:
    clean_topology = validate_topology(topology)
    clean_protocol = validate_calibration_protocol(
        protocol, topology=clean_topology
    )
    sample = _exact(
        value, keys=TRANSITION_SAMPLE_KEYS, label="transition sample"
    )
    unsigned = dict(sample)
    seal = unsigned.pop("sample_sha256", None)
    _, actions = _topology_maps(clean_topology)
    binding = actions.get(sample["action_ref_sha256"])
    partition, cluster = _validate_partition_cluster(
        protocol=clean_protocol,
        partition_role=sample["partition_role"],
        task_cluster_ref_sha256=sample["task_cluster_ref_sha256"],
    )
    if (
        _integer(
            sample["artifact_version"],
            label="artifact version",
            minimum=1,
            maximum=1,
        )
        != 1
        or sample["role"] != TRANSITION_SAMPLE_ROLE
        or sample["policy_id"] != POLICY_ID
        or sample["build_only"] is not True
        or sample["topology_sha256"] != clean_topology["topology_sha256"]
        or sample["protocol_sha256"] != clean_protocol["protocol_sha256"]
        or sample["partition_role"] != partition
        or sample["task_cluster_ref_sha256"] != cluster
        or binding is None
        or binding[0] != sample["source_state_ref_sha256"]
        or sample["next_state_ref_sha256"]
        not in binding[1]["allowed_next_state_ref_sha256s"]
        or any(
            not _is_sha256(sample[key])
            for key in (
                "pre_state_projection_sha256",
                "post_state_projection_sha256",
                "action_observation_receipt_sha256",
                "state_transition_receipt_sha256",
            )
        )
        or sample["same_pass_transition"] is not True
        or sample["runtime_evaluator_or_score_used"] is not False
        or sample[
            "raw_state_action_observation_question_or_id_embedded"
        ]
        is not False
        or seal != object_sha256(unsigned)
    ):
        raise ValueError("V2.42.56 transition sample seal or binding drifted")
    return copy.deepcopy(dict(sample))


def build_stop_loss_sample(
    *,
    topology: object,
    protocol: object,
    partition_role: str,
    task_cluster_ref_sha256: str,
    state_ref_sha256: str,
    state_projection_sha256: str,
    prediction_freeze_sha256: str,
    terminal_receipt_sha256: str,
    evaluator_protocol_sha256: str,
    evaluator_artifact_sha256: str | None,
    terminal_status: str,
    evaluator_valid: bool,
    terminal_loss: float,
) -> dict[str, Any]:
    clean_topology = validate_topology(topology)
    clean_protocol = validate_calibration_protocol(
        protocol, topology=clean_topology
    )
    partition, cluster = _validate_partition_cluster(
        protocol=clean_protocol,
        partition_role=partition_role,
        task_cluster_ref_sha256=task_cluster_ref_sha256,
    )
    states, _ = _topology_maps(clean_topology)
    loss = _number(
        terminal_loss,
        label="terminal loss",
        minimum=0.0,
        maximum=1.0,
    )
    if (
        state_ref_sha256 not in states
        or not all(
            _is_sha256(item)
            for item in (
                state_projection_sha256,
                prediction_freeze_sha256,
                terminal_receipt_sha256,
                evaluator_protocol_sha256,
            )
        )
        or terminal_status not in {"completed", "failed"}
        or not isinstance(evaluator_valid, bool)
        or (
            evaluator_valid
            and (
                terminal_status != "completed"
                or not _is_sha256(evaluator_artifact_sha256)
            )
        )
        or (
            not evaluator_valid
            and (evaluator_artifact_sha256 is not None or loss != 1.0)
        )
    ):
        raise ValueError("V2.42.56 stop-loss sample binding is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STOP_SAMPLE_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "topology_sha256": clean_topology["topology_sha256"],
        "protocol_sha256": clean_protocol["protocol_sha256"],
        "partition_role": partition,
        "task_cluster_ref_sha256": cluster,
        "state_ref_sha256": state_ref_sha256,
        "state_projection_sha256": state_projection_sha256,
        "prediction_freeze_sha256": prediction_freeze_sha256,
        "terminal_receipt_sha256": terminal_receipt_sha256,
        "evaluator_protocol_sha256": evaluator_protocol_sha256,
        "evaluator_artifact_sha256": evaluator_artifact_sha256,
        "terminal_status": terminal_status,
        "evaluator_valid": evaluator_valid,
        "terminal_loss": loss,
        "prediction_frozen_before_evaluator_read": True,
        "evaluator_joined_post_terminal_only": True,
        "development_terminal_loss_used_offline": True,
        "official_score_used_as_terminal_loss": False,
        "raw_prediction_evaluator_payload_question_or_id_embedded": False,
    }
    value["sample_sha256"] = object_sha256(value)
    return validate_stop_loss_sample(
        value,
        topology=clean_topology,
        protocol=clean_protocol,
    )


def validate_stop_loss_sample(
    value: object, *, topology: object, protocol: object
) -> dict[str, Any]:
    clean_topology = validate_topology(topology)
    clean_protocol = validate_calibration_protocol(
        protocol, topology=clean_topology
    )
    sample = _exact(value, keys=STOP_SAMPLE_KEYS, label="stop-loss sample")
    unsigned = dict(sample)
    seal = unsigned.pop("sample_sha256", None)
    states, _ = _topology_maps(clean_topology)
    partition, cluster = _validate_partition_cluster(
        protocol=clean_protocol,
        partition_role=sample["partition_role"],
        task_cluster_ref_sha256=sample["task_cluster_ref_sha256"],
    )
    loss = _number(
        sample["terminal_loss"],
        label="terminal loss",
        minimum=0.0,
        maximum=1.0,
    )
    if (
        _integer(
            sample["artifact_version"],
            label="artifact version",
            minimum=1,
            maximum=1,
        )
        != 1
        or sample["role"] != STOP_SAMPLE_ROLE
        or sample["policy_id"] != POLICY_ID
        or sample["build_only"] is not True
        or sample["topology_sha256"] != clean_topology["topology_sha256"]
        or sample["protocol_sha256"] != clean_protocol["protocol_sha256"]
        or sample["partition_role"] != partition
        or sample["task_cluster_ref_sha256"] != cluster
        or sample["state_ref_sha256"] not in states
        or any(
            not _is_sha256(sample[key])
            for key in (
                "state_projection_sha256",
                "prediction_freeze_sha256",
                "terminal_receipt_sha256",
                "evaluator_protocol_sha256",
            )
        )
        or sample["terminal_status"] not in {"completed", "failed"}
        or not isinstance(sample["evaluator_valid"], bool)
        or (
            sample["evaluator_valid"]
            and (
                sample["terminal_status"] != "completed"
                or not _is_sha256(sample["evaluator_artifact_sha256"])
            )
        )
        or (
            not sample["evaluator_valid"]
            and (
                sample["evaluator_artifact_sha256"] is not None
                or loss != 1.0
            )
        )
        or sample["prediction_frozen_before_evaluator_read"] is not True
        or sample["evaluator_joined_post_terminal_only"] is not True
        or sample["development_terminal_loss_used_offline"] is not True
        or sample["official_score_used_as_terminal_loss"] is not False
        or sample[
            "raw_prediction_evaluator_payload_question_or_id_embedded"
        ]
        is not False
        or seal != object_sha256(unsigned)
    ):
        raise ValueError("V2.42.56 stop-loss sample seal or binding drifted")
    return copy.deepcopy(dict(sample))


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("V2.42.56 cannot average an empty sequence")
    return math.fsum(values) / len(values)


def _probability_vector(
    *,
    successors: list[str],
    samples: list[Mapping[str, Any]],
    alpha: float,
) -> tuple[list[float], int]:
    by_cluster: dict[str, list[str]] = defaultdict(list)
    for sample in samples:
        by_cluster[str(sample["task_cluster_ref_sha256"])].append(
            str(sample["next_state_ref_sha256"])
        )
    cluster_count = len(by_cluster)
    if cluster_count == 0:
        raw = [1.0 / len(successors) for _ in successors]
    else:
        masses = [0.0 for _ in successors]
        index = {successor: position for position, successor in enumerate(successors)}
        for outcomes in by_cluster.values():
            denominator = len(outcomes)
            counts = [0 for _ in successors]
            for outcome in outcomes:
                counts[index[outcome]] += 1
            for position, count in enumerate(counts):
                masses[position] += count / denominator
        denominator = cluster_count + alpha * len(successors)
        raw = [
            (mass + alpha) / denominator
            for mass in masses
        ]
    probabilities = [
        _quantize(value) for value in raw[:-1]
    ]
    probabilities.append(_quantize(1.0 - math.fsum(probabilities)))
    if any(value <= 0.0 for value in probabilities) or abs(
        math.fsum(probabilities) - 1.0
    ) > 1e-9:
        raise RuntimeError("V2.42.56 fitted probability vector drifted")
    return probabilities, cluster_count


def _cluster_equal_brier(
    *,
    successors: list[str],
    probabilities: list[float],
    samples: list[Mapping[str, Any]],
) -> tuple[float | None, int]:
    by_cluster: dict[str, list[float]] = defaultdict(list)
    index = {successor: position for position, successor in enumerate(successors)}
    for sample in samples:
        observed = index[str(sample["next_state_ref_sha256"])]
        score = math.fsum(
            (
                probability
                - (1.0 if position == observed else 0.0)
            )
            ** 2
            for position, probability in enumerate(probabilities)
        ) / len(successors)
        by_cluster[str(sample["task_cluster_ref_sha256"])].append(score)
    if not by_cluster:
        return None, 0
    cluster_scores = [_mean(values) for values in by_cluster.values()]
    return _quantize(_mean(cluster_scores)), len(by_cluster)


def _fit_stop_loss(
    samples: list[Mapping[str, Any]],
) -> tuple[float, int]:
    by_cluster: dict[str, list[float]] = defaultdict(list)
    for sample in samples:
        by_cluster[str(sample["task_cluster_ref_sha256"])].append(
            float(sample["terminal_loss"])
        )
    if not by_cluster:
        return 1.0, 0
    cluster_means = [_mean(values) for values in by_cluster.values()]
    return _quantize(_mean(cluster_means)), len(by_cluster)


def _cluster_equal_mae(
    *, prediction: float, samples: list[Mapping[str, Any]]
) -> tuple[float | None, int]:
    by_cluster: dict[str, list[float]] = defaultdict(list)
    for sample in samples:
        by_cluster[str(sample["task_cluster_ref_sha256"])].append(
            abs(prediction - float(sample["terminal_loss"]))
        )
    if not by_cluster:
        return None, 0
    cluster_errors = [_mean(values) for values in by_cluster.values()]
    return _quantize(_mean(cluster_errors)), len(by_cluster)


def _data_manifest(
    *,
    partition_role: str,
    transition_samples: list[Mapping[str, Any]],
    stop_samples: list[Mapping[str, Any]],
) -> str:
    return object_sha256(
        {
            "partition_role": partition_role,
            "transition_sample_sha256s": sorted(
                str(sample["sample_sha256"])
                for sample in transition_samples
                if sample["partition_role"] == partition_role
            ),
            "stop_sample_sha256s": sorted(
                str(sample["sample_sha256"])
                for sample in stop_samples
                if sample["partition_role"] == partition_role
            ),
        }
    )


def _fit_clean(
    *,
    topology: Mapping[str, Any],
    protocol: Mapping[str, Any],
    transition_samples: list[Mapping[str, Any]],
    stop_samples: list[Mapping[str, Any]],
) -> dict[str, Any]:
    states, _ = _topology_maps(topology)
    observed_fit_clusters = {
        str(sample["task_cluster_ref_sha256"])
        for sample in [*transition_samples, *stop_samples]
        if sample["partition_role"] == FIT_ROLE
    }
    observed_calibration_clusters = {
        str(sample["task_cluster_ref_sha256"])
        for sample in [*transition_samples, *stop_samples]
        if sample["partition_role"] == CALIBRATION_ROLE
    }
    fit_expected = set(protocol["fit_task_cluster_ref_sha256s"])
    calibration_expected = set(
        protocol["calibration_task_cluster_ref_sha256s"]
    )
    fit_coverage = observed_fit_clusters == fit_expected
    calibration_coverage = (
        observed_calibration_clusters == calibration_expected
    )
    blockers: list[str] = []
    if not fit_coverage:
        blockers.append(
            f"fit_partition_cluster_coverage:{len(observed_fit_clusters)}/{len(fit_expected)}"
        )
    if not calibration_coverage:
        blockers.append(
            "calibration_partition_cluster_coverage:"
            f"{len(observed_calibration_clusters)}/{len(calibration_expected)}"
        )

    action_rows: list[dict[str, Any]] = []
    fitted_by_action: dict[str, list[float]] = {}
    for state in topology["states"]:
        for action in state["actions"]:
            action_ref = action["action_ref_sha256"]
            successors = action["allowed_next_state_ref_sha256s"]
            fit_samples = [
                sample
                for sample in transition_samples
                if sample["partition_role"] == FIT_ROLE
                and sample["action_ref_sha256"] == action_ref
            ]
            calibration_samples = [
                sample
                for sample in transition_samples
                if sample["partition_role"] == CALIBRATION_ROLE
                and sample["action_ref_sha256"] == action_ref
            ]
            probabilities, fit_count = _probability_vector(
                successors=successors,
                samples=fit_samples,
                alpha=float(protocol["dirichlet_alpha_per_successor"]),
            )
            brier, calibration_count = _cluster_equal_brier(
                successors=successors,
                probabilities=probabilities,
                samples=calibration_samples,
            )
            fit_ready = fit_count >= int(
                protocol[
                    "minimum_fit_transition_clusters_per_action"
                ]
            )
            calibration_ready = calibration_count >= int(
                protocol[
                    "minimum_calibration_transition_clusters_per_action"
                ]
            )
            metric_ready = bool(
                brier is not None
                and brier
                <= float(
                    protocol["maximum_normalized_multiclass_brier"]
                )
            )
            passed = fit_ready and calibration_ready and metric_ready
            if not fit_ready:
                blockers.append(f"transition_fit_support:{action_ref}")
            if not calibration_ready:
                blockers.append(
                    f"transition_calibration_support:{action_ref}"
                )
            elif not metric_ready:
                blockers.append(f"transition_brier:{action_ref}")
            fitted_by_action[action_ref] = probabilities
            action_rows.append(
                {
                    "source_state_ref_sha256": state["state_ref_sha256"],
                    "action_ref_sha256": action_ref,
                    "cost": action["cost"],
                    "allowed_next_state_ref_sha256s": list(successors),
                    "fit_task_cluster_count": fit_count,
                    "calibration_task_cluster_count": calibration_count,
                    "fitted_transition_probabilities": [
                        {
                            "next_state_ref_sha256": successor,
                            "probability": probability,
                        }
                        for successor, probability in zip(
                            successors, probabilities, strict=True
                        )
                    ],
                    "normalized_multiclass_brier": brier,
                    "maximum_normalized_multiclass_brier": protocol[
                        "maximum_normalized_multiclass_brier"
                    ],
                    "fit_support_ready": fit_ready,
                    "calibration_support_ready": calibration_ready,
                    "calibration_metric_ready": metric_ready,
                    "gate_passed": passed,
                }
            )

    stop_rows: list[dict[str, Any]] = []
    fitted_stop_by_state: dict[str, float] = {}
    for state_ref in topology["state_order"]:
        fit_samples = [
            sample
            for sample in stop_samples
            if sample["partition_role"] == FIT_ROLE
            and sample["state_ref_sha256"] == state_ref
        ]
        calibration_samples = [
            sample
            for sample in stop_samples
            if sample["partition_role"] == CALIBRATION_ROLE
            and sample["state_ref_sha256"] == state_ref
        ]
        fitted, fit_count = _fit_stop_loss(fit_samples)
        mae, calibration_count = _cluster_equal_mae(
            prediction=fitted, samples=calibration_samples
        )
        fit_ready = fit_count >= int(
            protocol["minimum_fit_stop_clusters_per_state"]
        )
        calibration_ready = calibration_count >= int(
            protocol["minimum_calibration_stop_clusters_per_state"]
        )
        metric_ready = bool(
            mae is not None
            and mae <= float(protocol["maximum_stop_loss_mae"])
        )
        passed = fit_ready and calibration_ready and metric_ready
        if not fit_ready:
            blockers.append(f"stop_fit_support:{state_ref}")
        if not calibration_ready:
            blockers.append(f"stop_calibration_support:{state_ref}")
        elif not metric_ready:
            blockers.append(f"stop_loss_mae:{state_ref}")
        fitted_stop_by_state[state_ref] = fitted
        stop_rows.append(
            {
                "state_ref_sha256": state_ref,
                "fit_task_cluster_count": fit_count,
                "calibration_task_cluster_count": calibration_count,
                "fitted_stop_terminal_loss": fitted,
                "stop_loss_mae": mae,
                "maximum_stop_loss_mae": protocol[
                    "maximum_stop_loss_mae"
                ],
                "fit_support_ready": fit_ready,
                "calibration_support_ready": calibration_ready,
                "calibration_metric_ready": metric_ready,
                "gate_passed": passed,
            }
        )

    blockers = sorted(set(blockers))
    complete = not blockers
    fit_manifest = _data_manifest(
        partition_role=FIT_ROLE,
        transition_samples=transition_samples,
        stop_samples=stop_samples,
    )
    calibration_manifest = _data_manifest(
        partition_role=CALIBRATION_ROLE,
        transition_samples=transition_samples,
        stop_samples=stop_samples,
    )
    report: dict[str, Any] = {
        "artifact_version": 1,
        "role": REPORT_ROLE,
        "policy_id": POLICY_ID,
        "label_blind": True,
        "build_only": True,
        "topology_sha256": topology["topology_sha256"],
        "protocol_sha256": protocol["protocol_sha256"],
        "fit_data_manifest_sha256": fit_manifest,
        "calibration_data_manifest_sha256": calibration_manifest,
        "fit_task_cluster_count": len(observed_fit_clusters),
        "calibration_task_cluster_count": len(observed_calibration_clusters),
        "fit_partition_cluster_coverage_complete": fit_coverage,
        "calibration_partition_cluster_coverage_complete": (
            calibration_coverage
        ),
        "task_cluster_is_statistical_unit": True,
        "fit_and_calibration_clusters_disjoint": True,
        "transition_probabilities_fit_from_fit_clusters_only": True,
        "stop_losses_fit_from_fit_clusters_only": True,
        "calibration_outcomes_used_for_gate_not_fit": True,
        "action_calibration": action_rows,
        "state_stop_loss_calibration": stop_rows,
        "blockers": blockers,
        "calibration_complete": complete,
        "development_terminal_loss_used_offline": True,
        "runtime_evaluator_payload_available": False,
        "audit_test_or_benchmark_outcome_used": False,
        "raw_state_action_observation_prediction_question_or_id_embedded": False,
        "controller_training_runtime_evaluator_or_leaderboard_authorized": False,
    }
    report["report_sha256"] = object_sha256(report)

    model_states: list[dict[str, Any]] = []
    for state in topology["states"]:
        model_actions: list[dict[str, Any]] = []
        for action in state["actions"]:
            probabilities = fitted_by_action[action["action_ref_sha256"]]
            model_actions.append(
                {
                    "action_ref_sha256": action["action_ref_sha256"],
                    "cost": action["cost"],
                    "outcomes": [
                        {
                            "next_state_ref_sha256": successor,
                            "probability": probability,
                            "calibration_ready": complete,
                            "calibration_ref_sha256": (
                                report["report_sha256"]
                                if complete
                                else None
                            ),
                        }
                        for successor, probability in zip(
                            action["allowed_next_state_ref_sha256s"],
                            probabilities,
                            strict=True,
                        )
                    ],
                }
            )
        model_states.append(
            {
                "state_ref_sha256": state["state_ref_sha256"],
                "stop_terminal_loss": fitted_stop_by_state[
                    state["state_ref_sha256"]
                ],
                "belief_entropy": state["belief_entropy"],
                "actions": model_actions,
            }
        )
    model = build_transition_model(
        model_fit_manifest_sha256=fit_manifest,
        calibration_protocol_sha256=protocol["protocol_sha256"],
        root_state_ref_sha256=topology["root_state_ref_sha256"],
        max_depth=topology["max_depth"],
        max_budget=topology["max_budget"],
        states=model_states,
    )
    package: dict[str, Any] = {
        "artifact_version": 1,
        "role": PACKAGE_ROLE,
        "policy_id": POLICY_ID,
        "label_blind": True,
        "build_only": True,
        "topology_sha256": topology["topology_sha256"],
        "protocol_sha256": protocol["protocol_sha256"],
        "calibration_report": report,
        "calibration_report_sha256": report["report_sha256"],
        "v24255_transition_model": model,
        "v24255_transition_model_sha256": model[
            "transition_model_sha256"
        ],
        "calibration_complete": complete,
        "incomplete_calibration_forces_all_policies_to_abstain": True,
        "development_only_fit_and_calibration": True,
        "runtime_evaluator_payload_available": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "runtime_forward_authorized": RUNTIME_FORWARD_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "benchmark_evaluator_launch_authorized": (
            BENCHMARK_EVALUATOR_LAUNCH_AUTHORIZED
        ),
        "leaderboard_or_sota_claim_authorized": (
            LEADERBOARD_OR_SOTA_CLAIM_AUTHORIZED
        ),
    }
    package["package_sha256"] = object_sha256(package)
    return package


def _validate_sample_collections(
    *,
    transition_samples: object,
    stop_samples: object,
) -> None:
    if (
        not isinstance(transition_samples, Sequence)
        or isinstance(transition_samples, (str, bytes))
        or len(transition_samples) > MAX_SAMPLES
        or not isinstance(stop_samples, Sequence)
        or isinstance(stop_samples, (str, bytes))
        or len(stop_samples) > MAX_SAMPLES
    ):
        raise ValueError("V2.42.56 sample collection is invalid")


def _reject_duplicate_sample_or_source_receipt(
    *,
    transition_samples: Sequence[Mapping[str, Any]],
    stop_samples: Sequence[Mapping[str, Any]],
) -> None:
    seals = [
        str(sample["sample_sha256"])
        for sample in [*transition_samples, *stop_samples]
    ]
    source_receipts = [
        str(sample["state_transition_receipt_sha256"])
        for sample in transition_samples
    ] + [
        str(sample["terminal_receipt_sha256"])
        for sample in stop_samples
    ]
    if len(seals) != len(set(seals)):
        raise ValueError("V2.42.56 duplicate sample seal rejected")
    if len(source_receipts) != len(set(source_receipts)):
        raise ValueError("V2.42.56 source receipt reuse rejected")


def fit_dynamic_voc_source_package(
    *,
    topology: object,
    protocol: object,
    transition_samples: Sequence[object],
    stop_samples: Sequence[object],
) -> dict[str, Any]:
    clean_topology = validate_topology(topology)
    clean_protocol = validate_calibration_protocol(
        protocol, topology=clean_topology
    )
    _validate_sample_collections(
        transition_samples=transition_samples,
        stop_samples=stop_samples,
    )
    clean_transitions = [
        validate_transition_sample(
            sample,
            topology=clean_topology,
            protocol=clean_protocol,
        )
        for sample in transition_samples
    ]
    clean_stops = [
        validate_stop_loss_sample(
            sample,
            topology=clean_topology,
            protocol=clean_protocol,
        )
        for sample in stop_samples
    ]
    _reject_duplicate_sample_or_source_receipt(
        transition_samples=clean_transitions,
        stop_samples=clean_stops,
    )
    package = _fit_clean(
        topology=clean_topology,
        protocol=clean_protocol,
        transition_samples=clean_transitions,
        stop_samples=clean_stops,
    )
    return validate_dynamic_voc_source_package(
        package,
        topology=clean_topology,
        protocol=clean_protocol,
        transition_samples=clean_transitions,
        stop_samples=clean_stops,
    )


def validate_dynamic_voc_source_package(
    value: object,
    *,
    topology: object,
    protocol: object,
    transition_samples: Sequence[object],
    stop_samples: Sequence[object],
) -> dict[str, Any]:
    clean_topology = validate_topology(topology)
    clean_protocol = validate_calibration_protocol(
        protocol, topology=clean_topology
    )
    _validate_sample_collections(
        transition_samples=transition_samples,
        stop_samples=stop_samples,
    )
    package = _exact(value, keys=PACKAGE_KEYS, label="source package")
    clean_transitions = [
        validate_transition_sample(
            sample,
            topology=clean_topology,
            protocol=clean_protocol,
        )
        for sample in transition_samples
    ]
    clean_stops = [
        validate_stop_loss_sample(
            sample,
            topology=clean_topology,
            protocol=clean_protocol,
        )
        for sample in stop_samples
    ]
    _reject_duplicate_sample_or_source_receipt(
        transition_samples=clean_transitions,
        stop_samples=clean_stops,
    )
    expected = _fit_clean(
        topology=clean_topology,
        protocol=clean_protocol,
        transition_samples=clean_transitions,
        stop_samples=clean_stops,
    )
    if object_sha256(dict(package)) != object_sha256(expected):
        raise ValueError("V2.42.56 source package replay drifted")
    if (
        not _sealed(package, seal_key="package_sha256")
        or package["artifact_version"] != 1
        or package["role"] != PACKAGE_ROLE
        or package["policy_id"] != POLICY_ID
        or package["label_blind"] is not True
        or package["build_only"] is not True
        or package["topology_sha256"] != clean_topology["topology_sha256"]
        or package["protocol_sha256"] != clean_protocol["protocol_sha256"]
        or package["calibration_report_sha256"]
        != package["calibration_report"]["report_sha256"]
        or not _sealed(
            package["calibration_report"], seal_key="report_sha256"
        )
        or package[
            "incomplete_calibration_forces_all_policies_to_abstain"
        ]
        is not True
        or package["development_only_fit_and_calibration"] is not True
        or package["runtime_evaluator_payload_available"] is not False
        or package["production_package_authorized"] is not False
        or package["runtime_forward_authorized"] is not False
        or package["credit_training_authorized"] is not False
        or package["benchmark_evaluator_launch_authorized"] is not False
        or package["leaderboard_or_sota_claim_authorized"] is not False
    ):
        raise ValueError("V2.42.56 source package safety contract drifted")
    report = _exact(
        package["calibration_report"],
        keys=REPORT_KEYS,
        label="calibration report",
    )
    if (
        any(
            set(row) != ACTION_REPORT_KEYS
            or any(
                set(probability) != PROBABILITY_ROW_KEYS
                for probability in row["fitted_transition_probabilities"]
            )
            for row in report["action_calibration"]
        )
        or any(
            set(row) != STATE_REPORT_KEYS
            for row in report["state_stop_loss_calibration"]
        )
    ):
        raise ValueError("V2.42.56 calibration report nested schema drifted")
    model = validate_transition_model(
        package["v24255_transition_model"],
        expected_transition_model_sha256=package[
            "v24255_transition_model_sha256"
        ],
    )
    if package["calibration_complete"]:
        if model["transition_calibration_complete"] is not True:
            raise ValueError("V2.42.56 ready package emitted abstaining model")
    else:
        if model["transition_calibration_complete"] is not False:
            raise ValueError("V2.42.56 incomplete package emitted ready model")
        decision = evaluate_voc_policies(
            model=model,
            expected_transition_model_sha256=model[
                "transition_model_sha256"
            ],
            requested_depth=1,
            available_budget=0,
        )
        if any(
            row["decision_kind"] != "abstain"
            for row in decision["policies"].values()
        ):
            raise ValueError(
                "V2.42.56 incomplete calibration did not force abstention"
            )
    return copy.deepcopy(dict(package))


__all__ = [
    "BENCHMARK_EVALUATOR_LAUNCH_AUTHORIZED",
    "CALIBRATION_ROLE",
    "CREDIT_TRAINING_AUTHORIZED",
    "FIT_ROLE",
    "LEADERBOARD_OR_SOTA_CLAIM_AUTHORIZED",
    "POLICY_ID",
    "PRODUCTION_PACKAGE_AUTHORIZED",
    "RUNTIME_FORWARD_AUTHORIZED",
    "build_calibration_protocol",
    "build_stop_loss_sample",
    "build_topology",
    "build_transition_sample",
    "fit_dynamic_voc_source_package",
    "object_sha256",
    "reject_privileged_runtime_metadata",
    "validate_calibration_protocol",
    "validate_dynamic_voc_source_package",
    "validate_stop_loss_sample",
    "validate_topology",
    "validate_transition_sample",
]
