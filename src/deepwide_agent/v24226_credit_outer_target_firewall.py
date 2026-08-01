"""Independent outer-target firewall for outcome-anchored step credit.

V2.42.23/24 can construct a useful offline advantage candidate from a sealed
same-state terminal intervention.  The same terminal contribution, however,
cannot also serve as the evaluation target: sign accuracy would then be true
by construction.  This build-only module creates an executable separation
contract.

The contract has two levels.  Credit policy selection is frozen on disjoint
fit/calibration task clusters.  On an audit cluster, an inner continuation
graph may construct the credit prediction, but that prediction is frozen
before a second, semantically matched outer campaign is supplied.  Both
campaigns reuse the same frozen job manifest and bundle contract, while their
evaluated-arm, prediction-freeze, provenance, contribution-record, and
aggregate identities must be disjoint.

The module validates hashes and construction boundaries only.  It cannot prove
wall-clock order, semantic/distributional OOD, or that an external scheduler
actually respected the declared cluster split.  Its pairs are diagnostics;
they do not by themselves authorize Gate 2B, training, benchmark execution, or
leaderboard claims.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Mapping, Sequence

from .v24123_release import is_sha256, validate_job_manifest
from .v24223_sign_preserving_credit import (
    MODULATION_POLICY_SHA256,
    object_sha256,
    validate_amplitude_features,
    validate_modulation_receipt,
)
from .v24224_credit_source_adapter import (
    validate_adapter_result,
    validate_source_receipt,
)


POLICY_ID = "v24226_independent_outer_target_credit_firewall_v1"
PROTOCOL_ROLE = "v24226_credit_outer_target_protocol"
PREDICTION_FREEZE_ROLE = "v24226_credit_prediction_freeze"
OUTER_PAIR_ROLE = "v24226_independent_outer_target_pair"
AGGREGATE_ROLE = "v24226_outer_target_diagnostic_aggregate"
PRODUCTION_PACKAGE_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False
GATE2B_PASS_AUTHORIZED = False

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "benchmark_category",
        "benchmark_subset",
        "category",
        "evaluator_score",
        "gold",
        "ground_truth",
        "mapping",
        "question_type",
        "results.csv",
        "score",
        "split",
        "task_category",
    }
)

PROTOCOL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_forward",
        "selection_protocol_sha256",
        "credit_policy_sha256",
        "fit_task_cluster_ref_sha256s",
        "calibration_task_cluster_ref_sha256s",
        "audit_task_cluster_ref_sha256s",
        "fit_task_cluster_count",
        "calibration_task_cluster_count",
        "audit_task_cluster_count",
        "task_cluster_sets_pairwise_disjoint",
        "selection_uses_fit_and_calibration_only",
        "audit_clusters_unavailable_to_policy_selection",
        "prediction_target_pairing",
        "same_source_contribution_may_not_be_evaluation_target",
        "prediction_must_freeze_before_outer_target_join",
        "task_cluster_is_statistical_unit",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "protocol_sha256",
    }
)
PREDICTION_FREEZE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_forward",
        "protocol_sha256",
        "credit_policy_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "partition_role",
        "context",
        "action",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "visible_question_sha256",
        "target_binding_sha256",
        "pre_action_features_sha256",
        "continuation_policy_sha256",
        "inner_job_manifest_sha256",
        "inner_bundle_sha256",
        "inner_adapter_result_sha256",
        "inner_source_receipt_sha256",
        "inner_verified_contribution_sha256",
        "inner_modulation_receipt_sha256",
        "inner_prediction_freeze_sha256",
        "inner_evaluator_provenance_receipt_sha256",
        "inner_evaluated_terminal_receipt_sha256s",
        "inner_contribution_record_sha256s",
        "inner_replicate_aggregate_sha256",
        "inner_replicate_count",
        "inner_source_contribution",
        "predicted_credit",
        "prediction_source_kind",
        "outer_job_manifest_source_receipt_target_or_contribution_read",
        "outer_target_unavailable_to_prediction_builder",
        "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "freeze_sha256",
    }
)
OUTER_PAIR_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_forward",
        "protocol_sha256",
        "prediction_freeze_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "partition_role",
        "context",
        "action",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "continuation_policy_sha256",
        "inner_job_manifest_sha256",
        "outer_job_manifest_sha256",
        "semantic_bundle_sha256",
        "outer_adapter_result_sha256",
        "outer_source_receipt_sha256",
        "outer_verified_contribution_sha256",
        "outer_prediction_freeze_sha256",
        "outer_evaluator_provenance_receipt_sha256",
        "outer_evaluated_terminal_receipt_sha256s",
        "outer_contribution_record_sha256s",
        "outer_replicate_aggregate_sha256",
        "outer_replicate_count",
        "predicted_credit",
        "inner_source_contribution_diagnostic",
        "outer_target_contribution",
        "inner_outer_job_manifest_contract_equal",
        "inner_outer_semantic_step_identity_exact",
        "inner_outer_arm_graph_hash_intersection_count",
        "inner_outer_arm_graph_hashes_disjoint",
        "terminal_state_hash_overlap_allowed",
        "numeric_contribution_equality_does_not_imply_artifact_reuse",
        "same_source_contribution_used_as_outer_target",
        "construction_api_excluded_outer_target_from_prediction_freeze",
        "wall_clock_creation_order_independently_proven",
        "semantic_or_distributional_ood_independently_assessed",
        "outer_target_pair_contract_valid",
        "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "pair_sha256",
    }
)
AGGREGATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_forward",
        "protocol_sha256",
        "pair_sha256s",
        "pair_count",
        "unique_audit_task_cluster_count",
        "predicted_credit_vs_independent_outer_target_spearman",
        "predicted_credit_vs_independent_outer_target_signed_accuracy",
        "inner_source_vs_outer_target_signed_stability",
        "same_source_target_self_evaluation_pair_count",
        "mechanical_self_confirmation_prevented",
        "task_cluster_is_statistical_unit",
        "cluster_bootstrap_performed",
        "stress_family_minima_verified",
        "real_intervention_data_observed",
        "diagnostic_status",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "aggregate_sha256",
    }
)


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.26 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    unsigned = copy.deepcopy(dict(value))
    seal = unsigned.pop(seal_key, None)
    return is_sha256(seal) and seal == object_sha256(unsigned)


def _bounded(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.26 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or not -1.0 <= number <= 1.0:
        raise ValueError(f"V2.42.26 {label} is outside [-1,1]")
    return number


def _nonnegative_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.26 {label} is not a nonnegative integer")
    return value


def _hash_list(value: object, *, label: str, minimum: int = 1) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) < minimum
        or any(not is_sha256(item) for item in value)
        or value != sorted(value)
        or len(value) != len(set(value))
    ):
        raise ValueError(f"V2.42.26 {label} is not a sorted unique hash list")
    return list(value)


def _cluster_list(value: Sequence[str], *, label: str) -> list[str]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"V2.42.26 {label} is not a cluster sequence")
    rows = sorted(str(item) for item in value)
    if not rows or len(rows) != len(set(rows)) or any(not is_sha256(row) for row in rows):
        raise ValueError(f"V2.42.26 {label} is not a unique SHA-256 set")
    return rows


def _reject_privileged_metadata(value: object) -> None:
    if isinstance(value, Mapping):
        hits = {
            str(key).casefold() for key in value
        }.intersection(FORBIDDEN_METADATA_KEYS)
        if hits:
            raise ValueError(
                "V2.42.26 privileged metadata rejected: "
                + ",".join(sorted(hits))
            )
        for child in value.values():
            _reject_privileged_metadata(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            _reject_privileged_metadata(child)


def build_outer_target_protocol(
    *,
    selection_protocol_sha256: str,
    fit_task_cluster_ref_sha256s: Sequence[str],
    calibration_task_cluster_ref_sha256s: Sequence[str],
    audit_task_cluster_ref_sha256s: Sequence[str],
) -> dict[str, Any]:
    """Freeze disjoint selection and audit clusters before pair construction."""

    if not is_sha256(selection_protocol_sha256):
        raise ValueError("V2.42.26 selection protocol is not a SHA-256")
    fit = _cluster_list(fit_task_cluster_ref_sha256s, label="fit clusters")
    calibration = _cluster_list(
        calibration_task_cluster_ref_sha256s, label="calibration clusters"
    )
    audit = _cluster_list(audit_task_cluster_ref_sha256s, label="audit clusters")
    if set(fit) & set(calibration) or set(fit) & set(audit) or set(calibration) & set(audit):
        raise ValueError("V2.42.26 task-cluster splits overlap")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PROTOCOL_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_forward": True,
        "selection_protocol_sha256": selection_protocol_sha256,
        "credit_policy_sha256": MODULATION_POLICY_SHA256,
        "fit_task_cluster_ref_sha256s": fit,
        "calibration_task_cluster_ref_sha256s": calibration,
        "audit_task_cluster_ref_sha256s": audit,
        "fit_task_cluster_count": len(fit),
        "calibration_task_cluster_count": len(calibration),
        "audit_task_cluster_count": len(audit),
        "task_cluster_sets_pairwise_disjoint": True,
        "selection_uses_fit_and_calibration_only": True,
        "audit_clusters_unavailable_to_policy_selection": True,
        "prediction_target_pairing": (
            "same_frozen_manifest_and_audit_step_independent_inner_outer_arm_graphs"
        ),
        "same_source_contribution_may_not_be_evaluation_target": True,
        "prediction_must_freeze_before_outer_target_join": True,
        "task_cluster_is_statistical_unit": True,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
    }
    value["protocol_sha256"] = object_sha256(value)
    validate_outer_target_protocol(value)
    return value


def validate_outer_target_protocol(value: object) -> None:
    protocol = _exact_mapping(value, keys=PROTOCOL_KEYS, label="protocol")
    fit = _hash_list(protocol.get("fit_task_cluster_ref_sha256s"), label="fit clusters")
    calibration = _hash_list(
        protocol.get("calibration_task_cluster_ref_sha256s"),
        label="calibration clusters",
    )
    audit = _hash_list(
        protocol.get("audit_task_cluster_ref_sha256s"), label="audit clusters"
    )
    if (
        protocol.get("artifact_version") != 1
        or protocol.get("role") != PROTOCOL_ROLE
        or protocol.get("policy_id") != POLICY_ID
        or protocol.get("label_blind_forward") is not True
        or not is_sha256(protocol.get("selection_protocol_sha256"))
        or protocol.get("credit_policy_sha256") != MODULATION_POLICY_SHA256
        or protocol.get("fit_task_cluster_count") != len(fit)
        or protocol.get("calibration_task_cluster_count") != len(calibration)
        or protocol.get("audit_task_cluster_count") != len(audit)
        or set(fit) & set(calibration)
        or set(fit) & set(audit)
        or set(calibration) & set(audit)
        or protocol.get("task_cluster_sets_pairwise_disjoint") is not True
        or protocol.get("selection_uses_fit_and_calibration_only") is not True
        or protocol.get("audit_clusters_unavailable_to_policy_selection") is not True
        or protocol.get("prediction_target_pairing")
        != "same_frozen_manifest_and_audit_step_independent_inner_outer_arm_graphs"
        or protocol.get("same_source_contribution_may_not_be_evaluation_target")
        is not True
        or protocol.get("prediction_must_freeze_before_outer_target_join") is not True
        or protocol.get("task_cluster_is_statistical_unit") is not True
        or protocol.get("production_package_authorized") is not False
        or protocol.get("credit_training_authorized") is not False
        or protocol.get("gate2b_pass_authorized") is not False
        or not _sealed(protocol, seal_key="protocol_sha256")
    ):
        raise ValueError("V2.42.26 protocol contract drifted")


def _source_context(
    *, job_manifest: Mapping[str, Any], adapter_result: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(job_manifest, Mapping) or not isinstance(adapter_result, Mapping):
        raise ValueError("V2.42.26 source graph input is not a mapping")
    manifest = copy.deepcopy(dict(job_manifest))
    result = copy.deepcopy(dict(adapter_result))
    _reject_privileged_metadata(manifest)
    validate_job_manifest(manifest)
    validate_adapter_result(result)
    source = result["source_receipt"]
    validate_source_receipt(source)
    if source["job_manifest_sha256"] != manifest["manifest_sha256"]:
        raise ValueError("V2.42.26 source receipt and job manifest differ")
    matches = [
        row
        for row in manifest["bundles"]
        if row.get("bundle_sha256") == source["bundle_sha256"]
    ]
    if len(matches) != 1:
        raise ValueError("V2.42.26 source bundle is absent or duplicated")
    bundle = copy.deepcopy(matches[0])
    bindings = {
        "task_cluster_ref_sha256": "task_cluster_ref_sha256",
        "partition_role": "partition_role",
        "context": "context",
        "action": "action",
        "source_checkpoint_sha256": "source_checkpoint_sha256",
        "shadow_projection_sha256": "shadow_projection_sha256",
        "continuation_policy_sha256": "continuation_policy_sha256",
    }
    if any(source[left] != bundle[right] for left, right in bindings.items()):
        raise ValueError("V2.42.26 source receipt and semantic bundle differ")
    return manifest, bundle, result


def build_credit_prediction_freeze(
    *,
    protocol: Mapping[str, Any],
    inner_job_manifest: Mapping[str, Any],
    inner_adapter_result: Mapping[str, Any],
    amplitude_features: Mapping[str, Any],
    modulation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one audit-cluster prediction without accepting an outer target."""

    validate_outer_target_protocol(protocol)
    manifest, bundle, result = _source_context(
        job_manifest=inner_job_manifest, adapter_result=inner_adapter_result
    )
    source = result["source_receipt"]
    verified = result["verified_contribution"]
    validate_amplitude_features(amplitude_features)
    validate_modulation_receipt(
        modulation_receipt,
        verified_contribution=verified,
        amplitude_features=amplitude_features,
    )
    if (
        source["partition_role"] != "development_audit"
        or source["task_cluster_ref_sha256"]
        not in protocol["audit_task_cluster_ref_sha256s"]
        or modulation_receipt["modulation_policy_sha256"]
        != protocol["credit_policy_sha256"]
    ):
        raise ValueError("V2.42.26 prediction is outside the frozen audit policy")
    evaluated = sorted(source["evaluated_terminal_receipt_sha256s"])
    contributions = sorted(source["contribution_record_sha256s"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PREDICTION_FREEZE_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_forward": True,
        "protocol_sha256": protocol["protocol_sha256"],
        "credit_policy_sha256": protocol["credit_policy_sha256"],
        "task_cluster_ref_sha256": source["task_cluster_ref_sha256"],
        "trajectory_ref_sha256": bundle["trajectory_ref_sha256"],
        "partition_role": source["partition_role"],
        "context": source["context"],
        "action": source["action"],
        "source_checkpoint_sha256": source["source_checkpoint_sha256"],
        "shadow_projection_sha256": source["shadow_projection_sha256"],
        "visible_question_sha256": bundle["visible_question_sha256"],
        "target_binding_sha256": bundle["target_binding_sha256"],
        "pre_action_features_sha256": bundle["pre_action_features_sha256"],
        "continuation_policy_sha256": source["continuation_policy_sha256"],
        "inner_job_manifest_sha256": manifest["manifest_sha256"],
        "inner_bundle_sha256": source["bundle_sha256"],
        "inner_adapter_result_sha256": result["adapter_result_sha256"],
        "inner_source_receipt_sha256": source["receipt_sha256"],
        "inner_verified_contribution_sha256": verified["record_sha256"],
        "inner_modulation_receipt_sha256": modulation_receipt["receipt_sha256"],
        "inner_prediction_freeze_sha256": source["prediction_freeze_sha256"],
        "inner_evaluator_provenance_receipt_sha256": source[
            "evaluator_provenance_receipt_sha256"
        ],
        "inner_evaluated_terminal_receipt_sha256s": evaluated,
        "inner_contribution_record_sha256s": contributions,
        "inner_replicate_aggregate_sha256": source["replicate_aggregate_sha256"],
        "inner_replicate_count": verified["replicate_count"],
        "inner_source_contribution": verified[
            "mean_signed_terminal_contribution"
        ],
        "predicted_credit": modulation_receipt["modulated_advantage_candidate"],
        "prediction_source_kind": (
            "inner_same_state_contribution_sign_plus_prejoin_amplitude"
        ),
        "outer_job_manifest_source_receipt_target_or_contribution_read": False,
        "outer_target_unavailable_to_prediction_builder": True,
        "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
    }
    value["freeze_sha256"] = object_sha256(value)
    validate_credit_prediction_freeze(value, protocol=protocol)
    return value


def validate_credit_prediction_freeze(
    value: object, *, protocol: Mapping[str, Any] | None = None
) -> None:
    freeze = _exact_mapping(
        value, keys=PREDICTION_FREEZE_KEYS, label="prediction freeze"
    )
    hash_fields = (
        "protocol_sha256",
        "credit_policy_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "visible_question_sha256",
        "target_binding_sha256",
        "pre_action_features_sha256",
        "continuation_policy_sha256",
        "inner_job_manifest_sha256",
        "inner_bundle_sha256",
        "inner_adapter_result_sha256",
        "inner_source_receipt_sha256",
        "inner_verified_contribution_sha256",
        "inner_modulation_receipt_sha256",
        "inner_prediction_freeze_sha256",
        "inner_evaluator_provenance_receipt_sha256",
        "inner_replicate_aggregate_sha256",
    )
    evaluated = _hash_list(
        freeze.get("inner_evaluated_terminal_receipt_sha256s"),
        label="inner evaluated receipts",
        minimum=6,
    )
    contributions = _hash_list(
        freeze.get("inner_contribution_record_sha256s"),
        label="inner contribution records",
        minimum=3,
    )
    count = _nonnegative_integer(
        freeze.get("inner_replicate_count"), label="inner replicate count"
    )
    _bounded(freeze.get("inner_source_contribution"), label="inner contribution")
    _bounded(freeze.get("predicted_credit"), label="predicted credit")
    if (
        freeze.get("artifact_version") != 1
        or freeze.get("role") != PREDICTION_FREEZE_ROLE
        or freeze.get("policy_id") != POLICY_ID
        or freeze.get("label_blind_forward") is not True
        or any(not is_sha256(freeze.get(key)) for key in hash_fields)
        or len(evaluated) != 6
        or len(contributions) != 3
        or count != 3
        or freeze.get("partition_role") != "development_audit"
        or not isinstance(freeze.get("context"), str)
        or not isinstance(freeze.get("action"), str)
        or freeze.get("prediction_source_kind")
        != "inner_same_state_contribution_sign_plus_prejoin_amplitude"
        or freeze.get("outer_job_manifest_source_receipt_target_or_contribution_read")
        is not False
        or freeze.get("outer_target_unavailable_to_prediction_builder") is not True
        or freeze.get(
            "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward"
        )
        is not False
        or freeze.get("production_package_authorized") is not False
        or freeze.get("credit_training_authorized") is not False
        or freeze.get("gate2b_pass_authorized") is not False
        or not _sealed(freeze, seal_key="freeze_sha256")
    ):
        raise ValueError("V2.42.26 prediction freeze contract drifted")
    if protocol is not None:
        validate_outer_target_protocol(protocol)
        if (
            freeze["protocol_sha256"] != protocol["protocol_sha256"]
            or freeze["credit_policy_sha256"] != protocol["credit_policy_sha256"]
            or freeze["task_cluster_ref_sha256"]
            not in protocol["audit_task_cluster_ref_sha256s"]
        ):
            raise ValueError("V2.42.26 prediction freeze protocol binding drifted")


def _semantic_identity(bundle: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(bundle[key])
        for key in (
            "bundle_sha256",
            "task_cluster_ref_sha256",
            "trajectory_ref_sha256",
            "partition_role",
            "context",
            "action",
            "source_checkpoint_sha256",
            "shadow_projection_sha256",
            "visible_question_sha256",
            "target_manifest_sha256",
            "continuation_policy_sha256",
            "target_binding_sha256",
            "pre_action_features_sha256",
        )
    }


def _arm_graph_hashes(source: Mapping[str, Any]) -> set[str]:
    return {
        source["prediction_freeze_sha256"],
        source["evaluator_provenance_receipt_sha256"],
        source["replicate_aggregate_sha256"],
        *source["evaluated_terminal_receipt_sha256s"],
        *source["contribution_record_sha256s"],
    }


def join_independent_outer_target(
    *,
    protocol: Mapping[str, Any],
    prediction_freeze: Mapping[str, Any],
    inner_job_manifest: Mapping[str, Any],
    inner_adapter_result: Mapping[str, Any],
    amplitude_features: Mapping[str, Any],
    modulation_receipt: Mapping[str, Any],
    outer_job_manifest: Mapping[str, Any],
    outer_adapter_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Join a semantically matched but mechanically independent outer target."""

    expected_freeze = build_credit_prediction_freeze(
        protocol=protocol,
        inner_job_manifest=inner_job_manifest,
        inner_adapter_result=inner_adapter_result,
        amplitude_features=amplitude_features,
        modulation_receipt=modulation_receipt,
    )
    if dict(prediction_freeze) != expected_freeze:
        raise ValueError("V2.42.26 supplied prediction freeze differs from source replay")
    inner_manifest, inner_bundle, inner_result = _source_context(
        job_manifest=inner_job_manifest, adapter_result=inner_adapter_result
    )
    outer_manifest, outer_bundle, outer_result = _source_context(
        job_manifest=outer_job_manifest, adapter_result=outer_adapter_result
    )
    inner_source = inner_result["source_receipt"]
    outer_source = outer_result["source_receipt"]
    outer_verified = outer_result["verified_contribution"]
    if (
        inner_manifest["manifest_sha256"] != outer_manifest["manifest_sha256"]
        or _semantic_identity(inner_bundle) != _semantic_identity(outer_bundle)
        or outer_source["partition_role"] != "development_audit"
    ):
        raise ValueError("V2.42.26 inner and outer campaigns are reused or unmatched")
    inner_hashes = _arm_graph_hashes(inner_source)
    outer_hashes = _arm_graph_hashes(outer_source)
    overlap = sorted(inner_hashes & outer_hashes)
    if overlap:
        raise ValueError("V2.42.26 inner and outer arm graphs overlap")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": OUTER_PAIR_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_forward": True,
        "protocol_sha256": protocol["protocol_sha256"],
        "prediction_freeze_sha256": prediction_freeze["freeze_sha256"],
        "task_cluster_ref_sha256": outer_source["task_cluster_ref_sha256"],
        "trajectory_ref_sha256": outer_bundle["trajectory_ref_sha256"],
        "partition_role": outer_source["partition_role"],
        "context": outer_source["context"],
        "action": outer_source["action"],
        "source_checkpoint_sha256": outer_source["source_checkpoint_sha256"],
        "shadow_projection_sha256": outer_source["shadow_projection_sha256"],
        "continuation_policy_sha256": outer_source["continuation_policy_sha256"],
        "inner_job_manifest_sha256": inner_manifest["manifest_sha256"],
        "outer_job_manifest_sha256": outer_manifest["manifest_sha256"],
        "semantic_bundle_sha256": outer_source["bundle_sha256"],
        "outer_adapter_result_sha256": outer_result["adapter_result_sha256"],
        "outer_source_receipt_sha256": outer_source["receipt_sha256"],
        "outer_verified_contribution_sha256": outer_verified["record_sha256"],
        "outer_prediction_freeze_sha256": outer_source["prediction_freeze_sha256"],
        "outer_evaluator_provenance_receipt_sha256": outer_source[
            "evaluator_provenance_receipt_sha256"
        ],
        "outer_evaluated_terminal_receipt_sha256s": sorted(
            outer_source["evaluated_terminal_receipt_sha256s"]
        ),
        "outer_contribution_record_sha256s": sorted(
            outer_source["contribution_record_sha256s"]
        ),
        "outer_replicate_aggregate_sha256": outer_source[
            "replicate_aggregate_sha256"
        ],
        "outer_replicate_count": outer_verified["replicate_count"],
        "predicted_credit": prediction_freeze["predicted_credit"],
        "inner_source_contribution_diagnostic": prediction_freeze[
            "inner_source_contribution"
        ],
        "outer_target_contribution": outer_verified[
            "mean_signed_terminal_contribution"
        ],
        "inner_outer_job_manifest_contract_equal": True,
        "inner_outer_semantic_step_identity_exact": True,
        "inner_outer_arm_graph_hash_intersection_count": 0,
        "inner_outer_arm_graph_hashes_disjoint": True,
        "terminal_state_hash_overlap_allowed": True,
        "numeric_contribution_equality_does_not_imply_artifact_reuse": True,
        "same_source_contribution_used_as_outer_target": False,
        "construction_api_excluded_outer_target_from_prediction_freeze": True,
        "wall_clock_creation_order_independently_proven": False,
        "semantic_or_distributional_ood_independently_assessed": False,
        "outer_target_pair_contract_valid": True,
        "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
    }
    value["pair_sha256"] = object_sha256(value)
    validate_independent_outer_target_pair(value, protocol=protocol)
    return value


def validate_independent_outer_target_pair(
    value: object, *, protocol: Mapping[str, Any] | None = None
) -> None:
    pair = _exact_mapping(value, keys=OUTER_PAIR_KEYS, label="outer-target pair")
    hash_fields = (
        "protocol_sha256",
        "prediction_freeze_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "continuation_policy_sha256",
        "inner_job_manifest_sha256",
        "outer_job_manifest_sha256",
        "semantic_bundle_sha256",
        "outer_adapter_result_sha256",
        "outer_source_receipt_sha256",
        "outer_verified_contribution_sha256",
        "outer_prediction_freeze_sha256",
        "outer_evaluator_provenance_receipt_sha256",
        "outer_replicate_aggregate_sha256",
    )
    evaluated = _hash_list(
        pair.get("outer_evaluated_terminal_receipt_sha256s"),
        label="outer evaluated receipts",
        minimum=6,
    )
    contributions = _hash_list(
        pair.get("outer_contribution_record_sha256s"),
        label="outer contribution records",
        minimum=3,
    )
    count = _nonnegative_integer(
        pair.get("outer_replicate_count"), label="outer replicate count"
    )
    _bounded(pair.get("predicted_credit"), label="predicted credit")
    _bounded(
        pair.get("inner_source_contribution_diagnostic"),
        label="inner contribution",
    )
    _bounded(pair.get("outer_target_contribution"), label="outer target")
    true_fields = (
        "inner_outer_job_manifest_contract_equal",
        "inner_outer_semantic_step_identity_exact",
        "inner_outer_arm_graph_hashes_disjoint",
        "terminal_state_hash_overlap_allowed",
        "numeric_contribution_equality_does_not_imply_artifact_reuse",
        "construction_api_excluded_outer_target_from_prediction_freeze",
        "outer_target_pair_contract_valid",
    )
    false_fields = (
        "same_source_contribution_used_as_outer_target",
        "wall_clock_creation_order_independently_proven",
        "semantic_or_distributional_ood_independently_assessed",
        "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
    )
    if (
        pair.get("artifact_version") != 1
        or pair.get("role") != OUTER_PAIR_ROLE
        or pair.get("policy_id") != POLICY_ID
        or pair.get("label_blind_forward") is not True
        or any(not is_sha256(pair.get(key)) for key in hash_fields)
        or pair["inner_job_manifest_sha256"] != pair["outer_job_manifest_sha256"]
        or pair.get("partition_role") != "development_audit"
        or len(evaluated) != 6
        or len(contributions) != 3
        or count != 3
        or pair.get("inner_outer_arm_graph_hash_intersection_count") != 0
        or any(pair.get(key) is not True for key in true_fields)
        or any(pair.get(key) is not False for key in false_fields)
        or not _sealed(pair, seal_key="pair_sha256")
    ):
        raise ValueError("V2.42.26 outer-target pair contract drifted")
    if protocol is not None:
        validate_outer_target_protocol(protocol)
        if (
            pair["protocol_sha256"] != protocol["protocol_sha256"]
            or pair["task_cluster_ref_sha256"]
            not in protocol["audit_task_cluster_ref_sha256s"]
        ):
            raise ValueError("V2.42.26 outer-target pair protocol binding drifted")


def _sign(value: float) -> int:
    return 1 if value > 1e-12 else -1 if value < -1e-12 else 0


def _ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda row: row[1])
    output = [0.0] * len(values)
    start = 0
    while start < len(indexed):
        end = start + 1
        while end < len(indexed) and indexed[end][1] == indexed[start][1]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for index, _ in indexed[start:end]:
            output[index] = rank
        start = end
    return output


def _pearson(first: list[float], second: list[float]) -> float | None:
    if len(first) != len(second) or len(first) < 2:
        return None
    left_mean = sum(first) / len(first)
    right_mean = sum(second) / len(second)
    left = [value - left_mean for value in first]
    right = [value - right_mean for value in second]
    denominator = math.sqrt(
        sum(value * value for value in left)
        * sum(value * value for value in right)
    )
    if denominator <= 0.0:
        return None
    return sum(a * b for a, b in zip(left, right)) / denominator


def build_outer_target_diagnostic_aggregate(
    *, protocol: Mapping[str, Any], pairs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Summarize independent pairs without opening a Gate-2B pass path."""

    validate_outer_target_protocol(protocol)
    if isinstance(pairs, (str, bytes)) or not pairs:
        raise ValueError("V2.42.26 diagnostic aggregate requires pairs")
    rows = sorted(
        (copy.deepcopy(dict(pair)) for pair in pairs),
        key=lambda pair: pair["pair_sha256"],
    )
    for pair in rows:
        validate_independent_outer_target_pair(pair, protocol=protocol)
    pair_hashes = [str(pair["pair_sha256"]) for pair in rows]
    if len(pair_hashes) != len(set(pair_hashes)) or len(
        {pair["prediction_freeze_sha256"] for pair in rows}
    ) != len(rows):
        raise ValueError("V2.42.26 diagnostic pairs are duplicated")
    predicted = [float(pair["predicted_credit"]) for pair in rows]
    outer = [float(pair["outer_target_contribution"]) for pair in rows]
    inner = [float(pair["inner_source_contribution_diagnostic"]) for pair in rows]
    spearman = _pearson(_ranks(predicted), _ranks(outer))
    signed_accuracy = sum(
        _sign(left) == _sign(right) for left, right in zip(predicted, outer)
    ) / len(rows)
    stability = sum(
        _sign(left) == _sign(right) for left, right in zip(inner, outer)
    ) / len(rows)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": AGGREGATE_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_forward": True,
        "protocol_sha256": protocol["protocol_sha256"],
        "pair_sha256s": pair_hashes,
        "pair_count": len(rows),
        "unique_audit_task_cluster_count": len(
            {pair["task_cluster_ref_sha256"] for pair in rows}
        ),
        "predicted_credit_vs_independent_outer_target_spearman": (
            None if spearman is None else round(spearman, 12)
        ),
        "predicted_credit_vs_independent_outer_target_signed_accuracy": round(
            signed_accuracy, 12
        ),
        "inner_source_vs_outer_target_signed_stability": round(stability, 12),
        "same_source_target_self_evaluation_pair_count": 0,
        "mechanical_self_confirmation_prevented": True,
        "task_cluster_is_statistical_unit": True,
        "cluster_bootstrap_performed": False,
        "stress_family_minima_verified": False,
        "real_intervention_data_observed": False,
        "diagnostic_status": "contract_only_not_evaluable_or_fail",
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
    }
    value["aggregate_sha256"] = object_sha256(value)
    validate_outer_target_diagnostic_aggregate(value, protocol=protocol)
    return value


def validate_outer_target_diagnostic_aggregate(
    value: object, *, protocol: Mapping[str, Any] | None = None
) -> None:
    aggregate = _exact_mapping(value, keys=AGGREGATE_KEYS, label="aggregate")
    pairs = _hash_list(aggregate.get("pair_sha256s"), label="pair hashes")
    count = _nonnegative_integer(aggregate.get("pair_count"), label="pair count")
    clusters = _nonnegative_integer(
        aggregate.get("unique_audit_task_cluster_count"),
        label="audit cluster count",
    )
    for key in (
        "predicted_credit_vs_independent_outer_target_signed_accuracy",
        "inner_source_vs_outer_target_signed_stability",
    ):
        value_number = aggregate.get(key)
        if (
            isinstance(value_number, bool)
            or not isinstance(value_number, (int, float))
            or not math.isfinite(float(value_number))
            or not 0.0 <= float(value_number) <= 1.0
        ):
            raise ValueError(f"V2.42.26 {key} is invalid")
    correlation = aggregate.get(
        "predicted_credit_vs_independent_outer_target_spearman"
    )
    if correlation is not None and (
        isinstance(correlation, bool)
        or not isinstance(correlation, (int, float))
        or not math.isfinite(float(correlation))
        or not -1.0 <= float(correlation) <= 1.0
    ):
        raise ValueError("V2.42.26 aggregate correlation is invalid")
    if (
        aggregate.get("artifact_version") != 1
        or aggregate.get("role") != AGGREGATE_ROLE
        or aggregate.get("policy_id") != POLICY_ID
        or aggregate.get("label_blind_forward") is not True
        or not is_sha256(aggregate.get("protocol_sha256"))
        or count != len(pairs)
        or not 1 <= clusters <= count
        or aggregate.get("same_source_target_self_evaluation_pair_count") != 0
        or aggregate.get("mechanical_self_confirmation_prevented") is not True
        or aggregate.get("task_cluster_is_statistical_unit") is not True
        or aggregate.get("cluster_bootstrap_performed") is not False
        or aggregate.get("stress_family_minima_verified") is not False
        or aggregate.get("real_intervention_data_observed") is not False
        or aggregate.get("diagnostic_status")
        != "contract_only_not_evaluable_or_fail"
        or aggregate.get("production_package_authorized") is not False
        or aggregate.get("credit_training_authorized") is not False
        or aggregate.get("gate2b_pass_authorized") is not False
        or not _sealed(aggregate, seal_key="aggregate_sha256")
    ):
        raise ValueError("V2.42.26 aggregate contract drifted")
    if protocol is not None:
        validate_outer_target_protocol(protocol)
        if aggregate["protocol_sha256"] != protocol["protocol_sha256"]:
            raise ValueError("V2.42.26 aggregate protocol binding drifted")
