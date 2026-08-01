"""Challenge-bound compatibility graph for independent outer credit targets.

V2.42.27 creates an unpredictable launch challenge after the credit prediction
is committed, but the frozen V2.41.23 execution/evaluation artifacts and the
V2.42.26 pair do not contain that challenge.  This build-only module adds an
exact-schema envelope at every graph layer:

``request -> prediction freeze -> executor declaration -> evaluator provenance
          -> evaluated terminals -> contributions -> aggregate -> outer pair``.

Every envelope binds the same launch challenge, namespace, request and parent
hashes.  The final validator also replays the complete V2.41.23 source graph
through V2.42.24 before accepting its V2.42.26 pair.

This is deliberately a *compatibility* graph.  Historical payloads can still
have been computed before the challenge and wrapped afterwards.  The executor
declaration is unsigned and is not an independent trust-domain attestation.
Consequently this module hard-codes external-precomputation exclusion,
independent attestation, formal Gate-2B, training, benchmark and production
authority to false.  A future version must use a real executor that consumes
the challenge plus a keyed/asymmetric append-only attestation service; an
unkeyed SHA-256 is never represented as a signature here.

The module has no file, environment, process, client, model, search, fetch or
network surface and is not imported by the active benchmark forward path.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .v24123_release import (
    CONTRIBUTION_ROLE as LEGACY_CONTRIBUTION_ROLE,
    EVALUATED_TERMINAL_ROLE,
    REPLICATE_AGGREGATE_ROLE,
    REPLICATE_IDS,
    is_sha256,
    validate_evaluated_terminal_receipt,
    validate_job_manifest,
)
from .v24223_sign_preserving_credit import object_sha256
from .v24224_credit_source_adapter import (
    EVALUATOR_PROVENANCE_KEYS,
    PREDICTION_FREEZE_KEYS,
    adapt_v24123_source_graph,
    validate_adapter_result,
)
from .v24226_credit_outer_target_firewall import (
    validate_independent_outer_target_pair,
)
from .v24227_credit_commit_reveal import (
    validate_commit_reveal_protocol,
    validate_launch_receipt,
    validate_outer_reservation_receipt,
    validate_prediction_commitment,
)


POLICY_ID = "v24228_challenge_bound_outer_credit_graph_v1"
PROTOCOL_ROLE = "v24228_challenge_graph_protocol"
REQUEST_ROLE = "v24228_challenge_execution_request"
FREEZE_ROLE = "v24228_challenge_prediction_freeze"
ATTESTATION_ROLE = "v24228_unsigned_executor_challenge_declaration"
EVALUATOR_ROLE = "v24228_challenge_evaluator_provenance"
TERMINAL_ROLE = "v24228_challenge_evaluated_terminal"
CONTRIBUTION_ROLE = "v24228_challenge_contribution_record"
AGGREGATE_ROLE = "v24228_challenge_replicate_aggregate"
PAIR_ROLE = "v24228_challenge_bound_outer_pair"

ATTESTATION_MODE = "unsigned_compatibility_envelope"
SIGNATURE_SCHEME = "none"

PRODUCTION_PACKAGE_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False
GATE2B_PASS_AUTHORIZED = False
OUTER_CAMPAIGN_EXECUTION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
FORMAL_GATE2B_EVALUATION_AUTHORIZED = False
EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED = False
STORE_API_EXECUTION_INDEPENDENTLY_ATTESTED = False

SAFETY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_control",
        "graph_protocol_sha256",
        "graph_namespace_sha256",
        "launch_challenge_sha256",
        "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control",
        "active_benchmark_forward_imported",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
    }
)

PROTOCOL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_control",
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "sequence_namespace_sha256",
        "graph_namespace_sha256",
        "outer_execution_contract_sha256",
        "expected_attestor_trust_domain_sha256",
        "attestation_policy_sha256",
        "attestation_mode",
        "signature_scheme",
        "required_layer_roles",
        "launch_challenge_required_in_every_layer",
        "exact_parent_hash_dag_required",
        "legacy_payload_schemas_unchanged",
        "legacy_payloads_are_challenge_native",
        "historical_payload_after_wrapping_excluded",
        "keyed_or_asymmetric_signature_required_for_independent_attestation",
        "keyed_or_asymmetric_signature_present",
        "append_only_trust_domain_present",
        "external_target_precomputation_excluded",
        "store_api_execution_independently_attested",
        "formal_gate2b_evaluation_authorized",
        "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control",
        "active_benchmark_forward_imported",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "protocol_sha256",
    }
)

REQUEST_KEYS = SAFETY_KEYS | frozenset(
    {
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "prediction_commitment_sha256",
        "outer_launch_receipt_sha256",
        "outer_reservation_receipt_sha256",
        "legacy_job_manifest_sha256",
        "legacy_bundle_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "partition_role",
        "context",
        "action",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "continuation_policy_sha256",
        "outer_output_namespace_sha256",
        "outer_seed_schedule_sha256",
        "outer_execution_contract_sha256",
        "outer_evaluator_protocol_sha256",
        "executor_instance_sha256",
        "request_nonce_sha256",
        "challenge_present_before_request_construction",
        "legacy_job_manifest_schema_modified",
        "legacy_job_manifest_is_challenge_native",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "request_sha256",
    }
)

FREEZE_KEYS = SAFETY_KEYS | frozenset(
    {
        "execution_request_sha256",
        "legacy_job_manifest_sha256",
        "legacy_bundle_sha256",
        "legacy_prediction_freeze_sha256",
        "legacy_terminal_receipt_sha256s",
        "executor_instance_sha256",
        "predictions_frozen_before_evaluator_material_read_in_legacy_graph",
        "challenge_bound_wrapper_created_after_launch_in_api_dag",
        "legacy_prediction_freeze_schema_modified",
        "legacy_prediction_freeze_is_challenge_native",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "freeze_sha256",
    }
)

ATTESTATION_KEYS = SAFETY_KEYS | frozenset(
    {
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "legacy_prediction_freeze_sha256",
        "legacy_terminal_receipt_sha256s",
        "executor_instance_sha256",
        "execution_trace_sha256",
        "execution_result_nonce_sha256",
        "attestor_trust_domain_sha256",
        "attestation_mode",
        "signature_scheme",
        "detached_signature",
        "executor_declares_challenge_consumed_before_execution",
        "executor_challenge_consumption_independently_verified",
        "append_only_publication_independently_verified",
        "store_api_execution_independently_attested",
        "offline_self_consistent_graph_fabrication_cryptographically_excluded",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "attestation_sha256",
    }
)

EVALUATOR_KEYS = SAFETY_KEYS | frozenset(
    {
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "executor_attestation_sha256",
        "legacy_prediction_freeze_sha256",
        "legacy_evaluator_provenance_receipt_sha256",
        "legacy_bundle_sha256",
        "outer_evaluator_protocol_sha256",
        "legacy_all_six_predictions_frozen_before_evaluator_material_read",
        "challenge_parent_dag_places_evaluator_after_executor_declaration",
        "trusted_physical_or_append_only_order_independently_proven",
        "legacy_evaluator_provenance_schema_modified",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "provenance_sha256",
    }
)

TERMINAL_KEYS = SAFETY_KEYS | frozenset(
    {
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "executor_attestation_sha256",
        "challenge_evaluator_provenance_sha256",
        "legacy_job_manifest_sha256",
        "legacy_bundle_sha256",
        "legacy_prediction_freeze_sha256",
        "legacy_evaluator_provenance_receipt_sha256",
        "legacy_evaluated_terminal_receipt_sha256",
        "legacy_parent_terminal_receipt_sha256",
        "terminal_state_sha256",
        "replicate_id",
        "branch_role",
        "terminal_status",
        "evaluator_valid",
        "terminal_task_loss",
        "post_terminal_evaluator_signal_embedded",
        "evaluator_signal_available_to_forward",
        "legacy_evaluated_terminal_schema_modified",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "terminal_sha256",
    }
)

CONTRIBUTION_KEYS = SAFETY_KEYS | frozenset(
    {
        "execution_request_sha256",
        "executor_attestation_sha256",
        "challenge_evaluator_provenance_sha256",
        "no_op_challenge_terminal_sha256",
        "action_challenge_terminal_sha256",
        "legacy_no_op_evaluated_terminal_receipt_sha256",
        "legacy_action_evaluated_terminal_receipt_sha256",
        "legacy_contribution_record_sha256",
        "replicate_id",
        "signed_terminal_contribution",
        "same_state_matched_continuation",
        "post_terminal_evaluator_signal_embedded",
        "evaluator_signal_available_to_forward",
        "legacy_contribution_schema_modified",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "contribution_sha256",
    }
)

AGGREGATE_KEYS = SAFETY_KEYS | frozenset(
    {
        "execution_request_sha256",
        "executor_attestation_sha256",
        "challenge_evaluator_provenance_sha256",
        "challenge_contribution_sha256s",
        "legacy_contribution_record_sha256s",
        "legacy_replicate_aggregate_sha256",
        "replicate_ids",
        "replicate_signed_terminal_contributions",
        "mean_signed_terminal_contribution",
        "task_cluster_is_statistical_unit",
        "replicates_are_repeated_measurements_not_independent_tasks",
        "post_terminal_evaluator_signal_embedded",
        "evaluator_signal_available_to_forward",
        "legacy_aggregate_schema_modified",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "aggregate_sha256",
    }
)

PAIR_KEYS = SAFETY_KEYS | frozenset(
    {
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "prediction_commitment_sha256",
        "outer_launch_receipt_sha256",
        "outer_reservation_receipt_sha256",
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "executor_attestation_sha256",
        "challenge_evaluator_provenance_sha256",
        "challenge_terminal_sha256s",
        "challenge_contribution_sha256s",
        "challenge_replicate_aggregate_sha256",
        "legacy_outer_pair_sha256",
        "legacy_outer_job_manifest_sha256",
        "legacy_outer_bundle_sha256",
        "legacy_outer_adapter_result_sha256",
        "legacy_outer_source_receipt_sha256",
        "legacy_outer_verified_contribution_sha256",
        "legacy_outer_prediction_freeze_sha256",
        "legacy_outer_evaluator_provenance_receipt_sha256",
        "legacy_outer_evaluated_terminal_receipt_sha256s",
        "legacy_outer_contribution_record_sha256s",
        "legacy_outer_replicate_aggregate_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "context",
        "action",
        "continuation_policy_sha256",
        "predicted_credit",
        "outer_target_contribution",
        "all_required_layers_present",
        "launch_challenge_bound_in_every_envelope_layer",
        "challenge_only_at_top_level",
        "exact_parent_hash_dag_validated",
        "legacy_source_graph_replayed_through_v24224",
        "legacy_v24226_pair_revalidated",
        "legacy_payload_schemas_modified",
        "legacy_payloads_are_challenge_native",
        "native_executor_consumed_challenge_independently_proven",
        "independent_append_only_or_transparency_service_used",
        "store_api_execution_independently_attested",
        "offline_self_consistent_graph_fabrication_cryptographically_excluded",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "semantic_or_distributional_ood_independently_assessed",
        "formal_gate2b_evaluation_authorized",
        "pair_sha256",
    }
)


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.28 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    unsigned = copy.deepcopy(dict(value))
    seal = unsigned.pop(seal_key, None)
    return is_sha256(seal) and seal == object_sha256(unsigned)


def _sha256(value: object, *, label: str) -> str:
    if not is_sha256(value):
        raise ValueError(f"V2.42.28 {label} is not a SHA-256")
    return str(value)


def _bounded(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.28 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or not -1.0 <= number <= 1.0:
        raise ValueError(f"V2.42.28 {label} is outside [-1,1]")
    return number


def _hash_list(value: object, *, label: str, length: int) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) != length
        or len(set(value)) != length
        or any(not is_sha256(item) for item in value)
    ):
        raise ValueError(f"V2.42.28 {label} is invalid")
    return list(value)


def _legacy_file_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    ).hexdigest()


def _base(
    *, role: str, protocol: Mapping[str, Any], launch_challenge_sha256: str
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": role,
        "policy_id": POLICY_ID,
        "label_blind_control": True,
        "graph_protocol_sha256": protocol["protocol_sha256"],
        "graph_namespace_sha256": protocol["graph_namespace_sha256"],
        "launch_challenge_sha256": launch_challenge_sha256,
        "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control": False,
        "active_benchmark_forward_imported": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
        "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }


def _validate_base(
    value: object,
    *,
    keys: frozenset[str],
    role: str,
    seal_key: str,
    label: str,
    protocol: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    artifact = _exact_mapping(value, keys=keys, label=label)
    if (
        artifact.get("artifact_version") != 1
        or artifact.get("role") != role
        or artifact.get("policy_id") != POLICY_ID
        or artifact.get("label_blind_control") is not True
        or not is_sha256(artifact.get("graph_protocol_sha256"))
        or not is_sha256(artifact.get("graph_namespace_sha256"))
        or not is_sha256(artifact.get("launch_challenge_sha256"))
        or artifact.get(
            "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control"
        )
        is not False
        or artifact.get("active_benchmark_forward_imported") is not False
        or artifact.get("production_package_authorized") is not False
        or artifact.get("credit_training_authorized") is not False
        or artifact.get("gate2b_pass_authorized") is not False
        or artifact.get("outer_campaign_execution_authorized") is not False
        or artifact.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(artifact, seal_key=seal_key)
    ):
        raise ValueError(f"V2.42.28 {label} safety boundary drifted")
    if protocol is not None:
        validate_challenge_graph_protocol(protocol)
        if (
            artifact["graph_protocol_sha256"] != protocol["protocol_sha256"]
            or artifact["graph_namespace_sha256"]
            != protocol["graph_namespace_sha256"]
        ):
            raise ValueError(f"V2.42.28 {label} protocol binding drifted")
    return artifact


def build_challenge_graph_protocol(
    *,
    sequence_protocol: Mapping[str, Any],
    graph_namespace_sha256: str,
    outer_execution_contract_sha256: str,
    expected_attestor_trust_domain_sha256: str,
    attestation_policy_sha256: str,
) -> dict[str, Any]:
    """Freeze the challenge-layer compatibility contract."""

    validate_commit_reveal_protocol(sequence_protocol)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PROTOCOL_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_control": True,
        "sequence_protocol_sha256": sequence_protocol["protocol_sha256"],
        "outer_target_protocol_sha256": sequence_protocol[
            "outer_target_protocol_sha256"
        ],
        "sequence_namespace_sha256": sequence_protocol[
            "sequence_namespace_sha256"
        ],
        "graph_namespace_sha256": _sha256(
            graph_namespace_sha256, label="graph namespace"
        ),
        "outer_execution_contract_sha256": _sha256(
            outer_execution_contract_sha256, label="outer execution contract"
        ),
        "expected_attestor_trust_domain_sha256": _sha256(
            expected_attestor_trust_domain_sha256,
            label="expected attestor trust domain",
        ),
        "attestation_policy_sha256": _sha256(
            attestation_policy_sha256, label="attestation policy"
        ),
        "attestation_mode": ATTESTATION_MODE,
        "signature_scheme": SIGNATURE_SCHEME,
        "required_layer_roles": [
            REQUEST_ROLE,
            FREEZE_ROLE,
            ATTESTATION_ROLE,
            EVALUATOR_ROLE,
            TERMINAL_ROLE,
            CONTRIBUTION_ROLE,
            AGGREGATE_ROLE,
            PAIR_ROLE,
        ],
        "launch_challenge_required_in_every_layer": True,
        "exact_parent_hash_dag_required": True,
        "legacy_payload_schemas_unchanged": True,
        "legacy_payloads_are_challenge_native": False,
        "historical_payload_after_wrapping_excluded": False,
        "keyed_or_asymmetric_signature_required_for_independent_attestation": True,
        "keyed_or_asymmetric_signature_present": False,
        "append_only_trust_domain_present": False,
        "external_target_precomputation_excluded": EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
        "store_api_execution_independently_attested": STORE_API_EXECUTION_INDEPENDENTLY_ATTESTED,
        "formal_gate2b_evaluation_authorized": FORMAL_GATE2B_EVALUATION_AUTHORIZED,
        "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control": False,
        "active_benchmark_forward_imported": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
        "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }
    value["protocol_sha256"] = object_sha256(value)
    validate_challenge_graph_protocol(value, sequence_protocol=sequence_protocol)
    return value


def validate_challenge_graph_protocol(
    value: object, *, sequence_protocol: Mapping[str, Any] | None = None
) -> None:
    protocol = _exact_mapping(value, keys=PROTOCOL_KEYS, label="protocol")
    hashes = (
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "sequence_namespace_sha256",
        "graph_namespace_sha256",
        "outer_execution_contract_sha256",
        "expected_attestor_trust_domain_sha256",
        "attestation_policy_sha256",
    )
    if (
        protocol.get("artifact_version") != 1
        or protocol.get("role") != PROTOCOL_ROLE
        or protocol.get("policy_id") != POLICY_ID
        or protocol.get("label_blind_control") is not True
        or any(not is_sha256(protocol.get(key)) for key in hashes)
        or protocol.get("attestation_mode") != ATTESTATION_MODE
        or protocol.get("signature_scheme") != SIGNATURE_SCHEME
        or protocol.get("required_layer_roles")
        != [
            REQUEST_ROLE,
            FREEZE_ROLE,
            ATTESTATION_ROLE,
            EVALUATOR_ROLE,
            TERMINAL_ROLE,
            CONTRIBUTION_ROLE,
            AGGREGATE_ROLE,
            PAIR_ROLE,
        ]
        or protocol.get("launch_challenge_required_in_every_layer") is not True
        or protocol.get("exact_parent_hash_dag_required") is not True
        or protocol.get("legacy_payload_schemas_unchanged") is not True
        or protocol.get("legacy_payloads_are_challenge_native") is not False
        or protocol.get("historical_payload_after_wrapping_excluded") is not False
        or protocol.get(
            "keyed_or_asymmetric_signature_required_for_independent_attestation"
        )
        is not True
        or protocol.get("keyed_or_asymmetric_signature_present") is not False
        or protocol.get("append_only_trust_domain_present") is not False
        or protocol.get("external_target_precomputation_excluded") is not False
        or protocol.get("store_api_execution_independently_attested") is not False
        or protocol.get("formal_gate2b_evaluation_authorized") is not False
        or protocol.get(
            "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control"
        )
        is not False
        or protocol.get("active_benchmark_forward_imported") is not False
        or protocol.get("production_package_authorized") is not False
        or protocol.get("credit_training_authorized") is not False
        or protocol.get("gate2b_pass_authorized") is not False
        or protocol.get("outer_campaign_execution_authorized") is not False
        or protocol.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(protocol, seal_key="protocol_sha256")
    ):
        raise ValueError("V2.42.28 protocol contract drifted")
    if sequence_protocol is not None:
        validate_commit_reveal_protocol(sequence_protocol)
        bindings = {
            "sequence_protocol_sha256": "protocol_sha256",
            "outer_target_protocol_sha256": "outer_target_protocol_sha256",
            "sequence_namespace_sha256": "sequence_namespace_sha256",
        }
        if any(
            protocol[left] != sequence_protocol[right]
            for left, right in bindings.items()
        ):
            raise ValueError("V2.42.28 sequence protocol binding drifted")


def _manifest_bundle(
    job_manifest: Mapping[str, Any], *, bundle_sha256: str
) -> dict[str, Any]:
    manifest = copy.deepcopy(dict(job_manifest))
    validate_job_manifest(manifest)
    matches = [
        row
        for row in manifest["bundles"]
        if row.get("bundle_sha256") == bundle_sha256
    ]
    if len(matches) != 1 or matches[0].get("eligible") is not True:
        raise ValueError("V2.42.28 legacy bundle is absent or duplicated")
    return copy.deepcopy(matches[0])


def build_challenge_execution_request(
    *,
    protocol: Mapping[str, Any],
    commitment: Mapping[str, Any],
    launch: Mapping[str, Any],
    reservation: Mapping[str, Any],
    outer_job_manifest: Mapping[str, Any],
    outer_bundle_sha256: str,
    executor_instance_sha256: str,
    request_nonce_sha256: str,
) -> dict[str, Any]:
    validate_challenge_graph_protocol(protocol)
    validate_prediction_commitment(commitment)
    validate_launch_receipt(launch, commitment=commitment)
    validate_outer_reservation_receipt(reservation, launch=launch)
    bundle = _manifest_bundle(
        outer_job_manifest, bundle_sha256=outer_bundle_sha256
    )
    manifest_sha = outer_job_manifest["manifest_sha256"]
    if (
        commitment["expected_outer_job_manifest_sha256"] != manifest_sha
        or commitment["expected_semantic_bundle_sha256"] != outer_bundle_sha256
        or commitment["outer_execution_contract_sha256"]
        != protocol["outer_execution_contract_sha256"]
        or launch["protocol_sha256"] != protocol["sequence_protocol_sha256"]
        or launch["sequence_namespace_sha256"]
        != protocol["sequence_namespace_sha256"]
        or reservation["outer_launch_receipt_sha256"]
        != launch["launch_receipt_sha256"]
    ):
        raise ValueError("V2.42.28 execution request campaign binding drifted")
    value = _base(
        role=REQUEST_ROLE,
        protocol=protocol,
        launch_challenge_sha256=launch["launch_challenge_sha256"],
    )
    value.update(
        {
            "sequence_protocol_sha256": protocol["sequence_protocol_sha256"],
            "outer_target_protocol_sha256": protocol[
                "outer_target_protocol_sha256"
            ],
            "prediction_commitment_sha256": commitment["commitment_sha256"],
            "outer_launch_receipt_sha256": launch["launch_receipt_sha256"],
            "outer_reservation_receipt_sha256": reservation[
                "reservation_sha256"
            ],
            "legacy_job_manifest_sha256": manifest_sha,
            "legacy_bundle_sha256": outer_bundle_sha256,
            "task_cluster_ref_sha256": bundle["task_cluster_ref_sha256"],
            "trajectory_ref_sha256": bundle["trajectory_ref_sha256"],
            "partition_role": bundle["partition_role"],
            "context": bundle["context"],
            "action": bundle["action"],
            "source_checkpoint_sha256": bundle["source_checkpoint_sha256"],
            "shadow_projection_sha256": bundle["shadow_projection_sha256"],
            "continuation_policy_sha256": bundle[
                "continuation_policy_sha256"
            ],
            "outer_output_namespace_sha256": commitment[
                "outer_output_namespace_sha256"
            ],
            "outer_seed_schedule_sha256": commitment[
                "outer_seed_schedule_sha256"
            ],
            "outer_execution_contract_sha256": commitment[
                "outer_execution_contract_sha256"
            ],
            "outer_evaluator_protocol_sha256": commitment[
                "outer_evaluator_protocol_sha256"
            ],
            "executor_instance_sha256": _sha256(
                executor_instance_sha256, label="executor instance"
            ),
            "request_nonce_sha256": _sha256(
                request_nonce_sha256, label="request nonce"
            ),
            "challenge_present_before_request_construction": True,
            "legacy_job_manifest_schema_modified": False,
            "legacy_job_manifest_is_challenge_native": False,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": False,
        }
    )
    value["request_sha256"] = object_sha256(value)
    validate_challenge_execution_request(
        value,
        protocol=protocol,
        commitment=commitment,
        launch=launch,
        reservation=reservation,
    )
    return value


def validate_challenge_execution_request(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    commitment: Mapping[str, Any] | None = None,
    launch: Mapping[str, Any] | None = None,
    reservation: Mapping[str, Any] | None = None,
) -> None:
    request = _validate_base(
        value,
        keys=REQUEST_KEYS,
        role=REQUEST_ROLE,
        seal_key="request_sha256",
        label="execution request",
        protocol=protocol,
    )
    hash_fields = (
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "prediction_commitment_sha256",
        "outer_launch_receipt_sha256",
        "outer_reservation_receipt_sha256",
        "legacy_job_manifest_sha256",
        "legacy_bundle_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "continuation_policy_sha256",
        "outer_output_namespace_sha256",
        "outer_seed_schedule_sha256",
        "outer_execution_contract_sha256",
        "outer_evaluator_protocol_sha256",
        "executor_instance_sha256",
        "request_nonce_sha256",
    )
    if (
        any(not is_sha256(request.get(key)) for key in hash_fields)
        or request.get("partition_role") != "development_audit"
        or not isinstance(request.get("context"), str)
        or not isinstance(request.get("action"), str)
        or request.get("challenge_present_before_request_construction") is not True
        or request.get("legacy_job_manifest_schema_modified") is not False
        or request.get("legacy_job_manifest_is_challenge_native") is not False
        or request.get("historical_payload_after_wrapping_possible") is not True
        or request.get("external_target_precomputation_excluded") is not False
    ):
        raise ValueError("V2.42.28 execution request contract drifted")
    if commitment is not None:
        validate_prediction_commitment(commitment)
        bindings = {
            "prediction_commitment_sha256": "commitment_sha256",
            "legacy_job_manifest_sha256": "expected_outer_job_manifest_sha256",
            "legacy_bundle_sha256": "expected_semantic_bundle_sha256",
            "outer_output_namespace_sha256": "outer_output_namespace_sha256",
            "outer_seed_schedule_sha256": "outer_seed_schedule_sha256",
            "outer_execution_contract_sha256": "outer_execution_contract_sha256",
            "outer_evaluator_protocol_sha256": "outer_evaluator_protocol_sha256",
        }
        if any(request[left] != commitment[right] for left, right in bindings.items()):
            raise ValueError("V2.42.28 request commitment binding drifted")
    if launch is not None:
        validate_launch_receipt(launch, commitment=commitment)
        if (
            request["outer_launch_receipt_sha256"]
            != launch["launch_receipt_sha256"]
            or request["launch_challenge_sha256"]
            != launch["launch_challenge_sha256"]
        ):
            raise ValueError("V2.42.28 request launch binding drifted")
    if reservation is not None:
        validate_outer_reservation_receipt(reservation, launch=launch)
        if (
            request["outer_reservation_receipt_sha256"]
            != reservation["reservation_sha256"]
            or request["launch_challenge_sha256"]
            != reservation["launch_challenge_sha256"]
        ):
            raise ValueError("V2.42.28 request reservation binding drifted")


def build_challenge_prediction_freeze(
    *,
    protocol: Mapping[str, Any],
    request: Mapping[str, Any],
    legacy_prediction_freeze: Mapping[str, Any],
) -> dict[str, Any]:
    validate_challenge_graph_protocol(protocol)
    validate_challenge_execution_request(request, protocol=protocol)
    freeze = _exact_mapping(
        legacy_prediction_freeze,
        keys=PREDICTION_FREEZE_KEYS,
        label="legacy prediction freeze",
    )
    if (
        freeze.get("role") != "v24123_bundle_prediction_freeze"
        or freeze.get("job_manifest_sha256")
        != request["legacy_job_manifest_sha256"]
        or freeze.get("bundle_sha256") != request["legacy_bundle_sha256"]
        or freeze.get("prediction_values_emitted") is not False
        or freeze.get("evaluator_read") is not False
        or not _sealed(freeze, seal_key="seal_sha256")
    ):
        raise ValueError("V2.42.28 legacy prediction freeze drifted")
    terminal_hashes = _hash_list(
        freeze.get("terminal_receipt_sha256s"),
        label="legacy terminal receipts",
        length=6,
    )
    value = _base(
        role=FREEZE_ROLE,
        protocol=protocol,
        launch_challenge_sha256=request["launch_challenge_sha256"],
    )
    value.update(
        {
            "execution_request_sha256": request["request_sha256"],
            "legacy_job_manifest_sha256": request[
                "legacy_job_manifest_sha256"
            ],
            "legacy_bundle_sha256": request["legacy_bundle_sha256"],
            "legacy_prediction_freeze_sha256": _legacy_file_sha256(freeze),
            "legacy_terminal_receipt_sha256s": terminal_hashes,
            "executor_instance_sha256": request["executor_instance_sha256"],
            "predictions_frozen_before_evaluator_material_read_in_legacy_graph": True,
            "challenge_bound_wrapper_created_after_launch_in_api_dag": True,
            "legacy_prediction_freeze_schema_modified": False,
            "legacy_prediction_freeze_is_challenge_native": False,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": False,
        }
    )
    value["freeze_sha256"] = object_sha256(value)
    validate_challenge_prediction_freeze(
        value, protocol=protocol, request=request
    )
    return value


def validate_challenge_prediction_freeze(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    request: Mapping[str, Any] | None = None,
) -> None:
    freeze = _validate_base(
        value,
        keys=FREEZE_KEYS,
        role=FREEZE_ROLE,
        seal_key="freeze_sha256",
        label="challenge prediction freeze",
        protocol=protocol,
    )
    hashes = (
        "execution_request_sha256",
        "legacy_job_manifest_sha256",
        "legacy_bundle_sha256",
        "legacy_prediction_freeze_sha256",
        "executor_instance_sha256",
    )
    _hash_list(
        freeze.get("legacy_terminal_receipt_sha256s"),
        label="legacy terminal receipts",
        length=6,
    )
    if (
        any(not is_sha256(freeze.get(key)) for key in hashes)
        or freeze.get(
            "predictions_frozen_before_evaluator_material_read_in_legacy_graph"
        )
        is not True
        or freeze.get("challenge_bound_wrapper_created_after_launch_in_api_dag")
        is not True
        or freeze.get("legacy_prediction_freeze_schema_modified") is not False
        or freeze.get("legacy_prediction_freeze_is_challenge_native") is not False
        or freeze.get("historical_payload_after_wrapping_possible") is not True
        or freeze.get("external_target_precomputation_excluded") is not False
    ):
        raise ValueError("V2.42.28 challenge prediction freeze drifted")
    if request is not None:
        validate_challenge_execution_request(request, protocol=protocol)
        bindings = (
            ("execution_request_sha256", "request_sha256"),
            ("legacy_job_manifest_sha256", "legacy_job_manifest_sha256"),
            ("legacy_bundle_sha256", "legacy_bundle_sha256"),
            ("executor_instance_sha256", "executor_instance_sha256"),
            ("launch_challenge_sha256", "launch_challenge_sha256"),
        )
        if any(freeze[left] != request[right] for left, right in bindings):
            raise ValueError("V2.42.28 prediction freeze request binding drifted")


def build_unsigned_executor_declaration(
    *,
    protocol: Mapping[str, Any],
    request: Mapping[str, Any],
    challenge_prediction_freeze: Mapping[str, Any],
    execution_trace_sha256: str,
    execution_result_nonce_sha256: str,
    attestor_trust_domain_sha256: str,
) -> dict[str, Any]:
    """Build an explicitly unsigned declaration; it grants no trust claim."""

    validate_challenge_graph_protocol(protocol)
    validate_challenge_execution_request(request, protocol=protocol)
    validate_challenge_prediction_freeze(
        challenge_prediction_freeze, protocol=protocol, request=request
    )
    trust_domain = _sha256(
        attestor_trust_domain_sha256, label="attestor trust domain"
    )
    if trust_domain != protocol["expected_attestor_trust_domain_sha256"]:
        raise ValueError("V2.42.28 attestor trust domain drifted")
    value = _base(
        role=ATTESTATION_ROLE,
        protocol=protocol,
        launch_challenge_sha256=request["launch_challenge_sha256"],
    )
    value.update(
        {
            "execution_request_sha256": request["request_sha256"],
            "challenge_prediction_freeze_sha256": challenge_prediction_freeze[
                "freeze_sha256"
            ],
            "legacy_prediction_freeze_sha256": challenge_prediction_freeze[
                "legacy_prediction_freeze_sha256"
            ],
            "legacy_terminal_receipt_sha256s": challenge_prediction_freeze[
                "legacy_terminal_receipt_sha256s"
            ],
            "executor_instance_sha256": request["executor_instance_sha256"],
            "execution_trace_sha256": _sha256(
                execution_trace_sha256, label="execution trace"
            ),
            "execution_result_nonce_sha256": _sha256(
                execution_result_nonce_sha256, label="execution result nonce"
            ),
            "attestor_trust_domain_sha256": trust_domain,
            "attestation_mode": ATTESTATION_MODE,
            "signature_scheme": SIGNATURE_SCHEME,
            "detached_signature": None,
            "executor_declares_challenge_consumed_before_execution": True,
            "executor_challenge_consumption_independently_verified": False,
            "append_only_publication_independently_verified": False,
            "store_api_execution_independently_attested": False,
            "offline_self_consistent_graph_fabrication_cryptographically_excluded": False,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": False,
        }
    )
    value["attestation_sha256"] = object_sha256(value)
    validate_unsigned_executor_declaration(
        value,
        protocol=protocol,
        request=request,
        challenge_prediction_freeze=challenge_prediction_freeze,
    )
    return value


def validate_unsigned_executor_declaration(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    request: Mapping[str, Any] | None = None,
    challenge_prediction_freeze: Mapping[str, Any] | None = None,
) -> None:
    attestation = _validate_base(
        value,
        keys=ATTESTATION_KEYS,
        role=ATTESTATION_ROLE,
        seal_key="attestation_sha256",
        label="executor declaration",
        protocol=protocol,
    )
    hashes = (
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "legacy_prediction_freeze_sha256",
        "executor_instance_sha256",
        "execution_trace_sha256",
        "execution_result_nonce_sha256",
        "attestor_trust_domain_sha256",
    )
    _hash_list(
        attestation.get("legacy_terminal_receipt_sha256s"),
        label="legacy terminal receipts",
        length=6,
    )
    if (
        any(not is_sha256(attestation.get(key)) for key in hashes)
        or attestation.get("attestation_mode") != ATTESTATION_MODE
        or attestation.get("signature_scheme") != SIGNATURE_SCHEME
        or attestation.get("detached_signature") is not None
        or attestation.get("executor_declares_challenge_consumed_before_execution")
        is not True
        or attestation.get(
            "executor_challenge_consumption_independently_verified"
        )
        is not False
        or attestation.get("append_only_publication_independently_verified")
        is not False
        or attestation.get("store_api_execution_independently_attested") is not False
        or attestation.get(
            "offline_self_consistent_graph_fabrication_cryptographically_excluded"
        )
        is not False
        or attestation.get("historical_payload_after_wrapping_possible") is not True
        or attestation.get("external_target_precomputation_excluded") is not False
    ):
        raise ValueError("V2.42.28 unsigned executor declaration drifted")
    if protocol is not None and (
        attestation["attestor_trust_domain_sha256"]
        != protocol["expected_attestor_trust_domain_sha256"]
    ):
        raise ValueError("V2.42.28 executor trust domain binding drifted")
    if request is not None:
        validate_challenge_execution_request(request, protocol=protocol)
        bindings = (
            ("execution_request_sha256", "request_sha256"),
            ("executor_instance_sha256", "executor_instance_sha256"),
            ("launch_challenge_sha256", "launch_challenge_sha256"),
        )
        if any(attestation[left] != request[right] for left, right in bindings):
            raise ValueError("V2.42.28 executor request binding drifted")
    if challenge_prediction_freeze is not None:
        validate_challenge_prediction_freeze(
            challenge_prediction_freeze, protocol=protocol, request=request
        )
        if (
            attestation["challenge_prediction_freeze_sha256"]
            != challenge_prediction_freeze["freeze_sha256"]
            or attestation["legacy_prediction_freeze_sha256"]
            != challenge_prediction_freeze["legacy_prediction_freeze_sha256"]
            or attestation["legacy_terminal_receipt_sha256s"]
            != challenge_prediction_freeze["legacy_terminal_receipt_sha256s"]
        ):
            raise ValueError("V2.42.28 executor freeze binding drifted")


def build_challenge_evaluator_provenance(
    *,
    protocol: Mapping[str, Any],
    request: Mapping[str, Any],
    challenge_prediction_freeze: Mapping[str, Any],
    executor_attestation: Mapping[str, Any],
    legacy_evaluator_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    validate_unsigned_executor_declaration(
        executor_attestation,
        protocol=protocol,
        request=request,
        challenge_prediction_freeze=challenge_prediction_freeze,
    )
    provenance = _exact_mapping(
        legacy_evaluator_provenance,
        keys=EVALUATOR_PROVENANCE_KEYS,
        label="legacy evaluator provenance",
    )
    if (
        provenance.get("role")
        != "v24123_post_prediction_freeze_evaluator_provenance"
        or provenance.get("bundle_sha256") != request["legacy_bundle_sha256"]
        or provenance.get("prediction_freeze_sha256")
        != challenge_prediction_freeze["legacy_prediction_freeze_sha256"]
        or provenance.get(
            "all_six_predictions_frozen_before_evaluator_material_read"
        )
        is not True
        or not _sealed(provenance, seal_key="receipt_sha256")
    ):
        raise ValueError("V2.42.28 legacy evaluator provenance drifted")
    value = _base(
        role=EVALUATOR_ROLE,
        protocol=protocol,
        launch_challenge_sha256=request["launch_challenge_sha256"],
    )
    value.update(
        {
            "execution_request_sha256": request["request_sha256"],
            "challenge_prediction_freeze_sha256": challenge_prediction_freeze[
                "freeze_sha256"
            ],
            "executor_attestation_sha256": executor_attestation[
                "attestation_sha256"
            ],
            "legacy_prediction_freeze_sha256": challenge_prediction_freeze[
                "legacy_prediction_freeze_sha256"
            ],
            "legacy_evaluator_provenance_receipt_sha256": provenance[
                "receipt_sha256"
            ],
            "legacy_bundle_sha256": request["legacy_bundle_sha256"],
            "outer_evaluator_protocol_sha256": request[
                "outer_evaluator_protocol_sha256"
            ],
            "legacy_all_six_predictions_frozen_before_evaluator_material_read": True,
            "challenge_parent_dag_places_evaluator_after_executor_declaration": True,
            "trusted_physical_or_append_only_order_independently_proven": False,
            "legacy_evaluator_provenance_schema_modified": False,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": False,
        }
    )
    value["provenance_sha256"] = object_sha256(value)
    validate_challenge_evaluator_provenance(
        value,
        protocol=protocol,
        request=request,
        challenge_prediction_freeze=challenge_prediction_freeze,
        executor_attestation=executor_attestation,
    )
    return value


def validate_challenge_evaluator_provenance(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    request: Mapping[str, Any] | None = None,
    challenge_prediction_freeze: Mapping[str, Any] | None = None,
    executor_attestation: Mapping[str, Any] | None = None,
) -> None:
    provenance = _validate_base(
        value,
        keys=EVALUATOR_KEYS,
        role=EVALUATOR_ROLE,
        seal_key="provenance_sha256",
        label="challenge evaluator provenance",
        protocol=protocol,
    )
    hashes = (
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "executor_attestation_sha256",
        "legacy_prediction_freeze_sha256",
        "legacy_evaluator_provenance_receipt_sha256",
        "legacy_bundle_sha256",
        "outer_evaluator_protocol_sha256",
    )
    if (
        any(not is_sha256(provenance.get(key)) for key in hashes)
        or provenance.get(
            "legacy_all_six_predictions_frozen_before_evaluator_material_read"
        )
        is not True
        or provenance.get(
            "challenge_parent_dag_places_evaluator_after_executor_declaration"
        )
        is not True
        or provenance.get(
            "trusted_physical_or_append_only_order_independently_proven"
        )
        is not False
        or provenance.get("legacy_evaluator_provenance_schema_modified") is not False
        or provenance.get("historical_payload_after_wrapping_possible") is not True
        or provenance.get("external_target_precomputation_excluded") is not False
    ):
        raise ValueError("V2.42.28 challenge evaluator provenance drifted")
    if request is not None:
        validate_challenge_execution_request(request, protocol=protocol)
        bindings = (
            ("execution_request_sha256", "request_sha256"),
            ("legacy_bundle_sha256", "legacy_bundle_sha256"),
            ("outer_evaluator_protocol_sha256", "outer_evaluator_protocol_sha256"),
            ("launch_challenge_sha256", "launch_challenge_sha256"),
        )
        if any(provenance[left] != request[right] for left, right in bindings):
            raise ValueError("V2.42.28 evaluator request binding drifted")
    if challenge_prediction_freeze is not None:
        validate_challenge_prediction_freeze(
            challenge_prediction_freeze, protocol=protocol, request=request
        )
        if (
            provenance["challenge_prediction_freeze_sha256"]
            != challenge_prediction_freeze["freeze_sha256"]
            or provenance["legacy_prediction_freeze_sha256"]
            != challenge_prediction_freeze["legacy_prediction_freeze_sha256"]
        ):
            raise ValueError("V2.42.28 evaluator freeze binding drifted")
    if executor_attestation is not None:
        validate_unsigned_executor_declaration(
            executor_attestation,
            protocol=protocol,
            request=request,
            challenge_prediction_freeze=challenge_prediction_freeze,
        )
        if (
            provenance["executor_attestation_sha256"]
            != executor_attestation["attestation_sha256"]
        ):
            raise ValueError("V2.42.28 evaluator executor binding drifted")


def build_challenge_evaluated_terminal(
    *,
    protocol: Mapping[str, Any],
    request: Mapping[str, Any],
    challenge_prediction_freeze: Mapping[str, Any],
    executor_attestation: Mapping[str, Any],
    challenge_evaluator_provenance: Mapping[str, Any],
    legacy_evaluated_terminal_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    validate_challenge_evaluator_provenance(
        challenge_evaluator_provenance,
        protocol=protocol,
        request=request,
        challenge_prediction_freeze=challenge_prediction_freeze,
        executor_attestation=executor_attestation,
    )
    receipt = copy.deepcopy(dict(legacy_evaluated_terminal_receipt))
    validate_evaluated_terminal_receipt(receipt)
    parent_hash = receipt["parent_v24122_terminal_receipt_sha256"]
    if (
        receipt["role"] != EVALUATED_TERMINAL_ROLE
        or receipt["job_manifest_sha256"] != request["legacy_job_manifest_sha256"]
        or receipt["prediction_freeze_sha256"]
        != challenge_prediction_freeze["legacy_prediction_freeze_sha256"]
        or receipt["evaluator_provenance_receipt_sha256"]
        != challenge_evaluator_provenance[
            "legacy_evaluator_provenance_receipt_sha256"
        ]
        or receipt["evaluator_protocol_sha256"]
        != request["outer_evaluator_protocol_sha256"]
        or parent_hash
        not in challenge_prediction_freeze["legacy_terminal_receipt_sha256s"]
    ):
        raise ValueError("V2.42.28 legacy evaluated terminal binding drifted")
    value = _base(
        role=TERMINAL_ROLE,
        protocol=protocol,
        launch_challenge_sha256=request["launch_challenge_sha256"],
    )
    value.update(
        {
            "execution_request_sha256": request["request_sha256"],
            "challenge_prediction_freeze_sha256": challenge_prediction_freeze[
                "freeze_sha256"
            ],
            "executor_attestation_sha256": executor_attestation[
                "attestation_sha256"
            ],
            "challenge_evaluator_provenance_sha256": challenge_evaluator_provenance[
                "provenance_sha256"
            ],
            "legacy_job_manifest_sha256": request[
                "legacy_job_manifest_sha256"
            ],
            "legacy_bundle_sha256": request["legacy_bundle_sha256"],
            "legacy_prediction_freeze_sha256": challenge_prediction_freeze[
                "legacy_prediction_freeze_sha256"
            ],
            "legacy_evaluator_provenance_receipt_sha256": challenge_evaluator_provenance[
                "legacy_evaluator_provenance_receipt_sha256"
            ],
            "legacy_evaluated_terminal_receipt_sha256": receipt[
                "receipt_payload_sha256"
            ],
            "legacy_parent_terminal_receipt_sha256": parent_hash,
            "terminal_state_sha256": receipt["terminal_state_sha256"],
            "replicate_id": receipt["replicate_id"],
            "branch_role": receipt["branch_role"],
            "terminal_status": receipt["terminal_status"],
            "evaluator_valid": receipt["evaluator_valid"],
            "terminal_task_loss": receipt["terminal_task_loss"],
            "post_terminal_evaluator_signal_embedded": True,
            "evaluator_signal_available_to_forward": False,
            "legacy_evaluated_terminal_schema_modified": False,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": False,
        }
    )
    value["terminal_sha256"] = object_sha256(value)
    validate_challenge_evaluated_terminal(
        value,
        protocol=protocol,
        request=request,
        challenge_prediction_freeze=challenge_prediction_freeze,
        executor_attestation=executor_attestation,
        challenge_evaluator_provenance=challenge_evaluator_provenance,
    )
    return value


def validate_challenge_evaluated_terminal(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    request: Mapping[str, Any] | None = None,
    challenge_prediction_freeze: Mapping[str, Any] | None = None,
    executor_attestation: Mapping[str, Any] | None = None,
    challenge_evaluator_provenance: Mapping[str, Any] | None = None,
) -> None:
    terminal = _validate_base(
        value,
        keys=TERMINAL_KEYS,
        role=TERMINAL_ROLE,
        seal_key="terminal_sha256",
        label="challenge evaluated terminal",
        protocol=protocol,
    )
    hashes = (
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "executor_attestation_sha256",
        "challenge_evaluator_provenance_sha256",
        "legacy_job_manifest_sha256",
        "legacy_bundle_sha256",
        "legacy_prediction_freeze_sha256",
        "legacy_evaluator_provenance_receipt_sha256",
        "legacy_evaluated_terminal_receipt_sha256",
        "legacy_parent_terminal_receipt_sha256",
        "terminal_state_sha256",
    )
    _bounded(terminal.get("terminal_task_loss"), label="terminal task loss")
    if (
        any(not is_sha256(terminal.get(key)) for key in hashes)
        or terminal.get("replicate_id") not in REPLICATE_IDS
        or isinstance(terminal.get("replicate_id"), bool)
        or terminal.get("branch_role") not in {"no_op", "action"}
        or terminal.get("terminal_status") not in {"completed", "failed"}
        or not isinstance(terminal.get("evaluator_valid"), bool)
        or terminal.get("post_terminal_evaluator_signal_embedded") is not True
        or terminal.get("evaluator_signal_available_to_forward") is not False
        or terminal.get("legacy_evaluated_terminal_schema_modified") is not False
        or terminal.get("historical_payload_after_wrapping_possible") is not True
        or terminal.get("external_target_precomputation_excluded") is not False
    ):
        raise ValueError("V2.42.28 challenge evaluated terminal drifted")
    parents: list[tuple[Mapping[str, Any] | None, str, str]] = [
        (request, "execution_request_sha256", "request_sha256"),
        (
            challenge_prediction_freeze,
            "challenge_prediction_freeze_sha256",
            "freeze_sha256",
        ),
        (executor_attestation, "executor_attestation_sha256", "attestation_sha256"),
        (
            challenge_evaluator_provenance,
            "challenge_evaluator_provenance_sha256",
            "provenance_sha256",
        ),
    ]
    for parent, left, right in parents:
        if parent is not None and terminal[left] != parent[right]:
            raise ValueError("V2.42.28 terminal parent binding drifted")
    for parent in (
        request,
        challenge_prediction_freeze,
        executor_attestation,
        challenge_evaluator_provenance,
    ):
        if parent is not None and terminal["launch_challenge_sha256"] != parent[
            "launch_challenge_sha256"
        ]:
            raise ValueError("V2.42.28 terminal challenge binding drifted")


def build_challenge_contribution_record(
    *,
    protocol: Mapping[str, Any],
    request: Mapping[str, Any],
    executor_attestation: Mapping[str, Any],
    challenge_evaluator_provenance: Mapping[str, Any],
    no_op_terminal: Mapping[str, Any],
    action_terminal: Mapping[str, Any],
    legacy_contribution_record: Mapping[str, Any],
) -> dict[str, Any]:
    for terminal in (no_op_terminal, action_terminal):
        validate_challenge_evaluated_terminal(terminal, protocol=protocol)
    record = copy.deepcopy(dict(legacy_contribution_record))
    if (
        record.get("role") != LEGACY_CONTRIBUTION_ROLE
        or not _sealed(record, seal_key="record_sha256")
        or no_op_terminal["branch_role"] != "no_op"
        or action_terminal["branch_role"] != "action"
        or no_op_terminal["replicate_id"] != action_terminal["replicate_id"]
        or record.get("replicate_id") != no_op_terminal["replicate_id"]
        or record.get("no_op_terminal_receipt_sha256")
        != no_op_terminal["legacy_evaluated_terminal_receipt_sha256"]
        or record.get("action_terminal_receipt_sha256")
        != action_terminal["legacy_evaluated_terminal_receipt_sha256"]
        or record.get("same_state_matched_continuation") is not True
    ):
        raise ValueError("V2.42.28 legacy contribution binding drifted")
    parent_values = (
        request["request_sha256"],
        executor_attestation["attestation_sha256"],
        challenge_evaluator_provenance["provenance_sha256"],
        request["launch_challenge_sha256"],
    )
    for terminal in (no_op_terminal, action_terminal):
        if (
            terminal["execution_request_sha256"],
            terminal["executor_attestation_sha256"],
            terminal["challenge_evaluator_provenance_sha256"],
            terminal["launch_challenge_sha256"],
        ) != parent_values:
            raise ValueError("V2.42.28 contribution terminal parents differ")
    value = _base(
        role=CONTRIBUTION_ROLE,
        protocol=protocol,
        launch_challenge_sha256=request["launch_challenge_sha256"],
    )
    value.update(
        {
            "execution_request_sha256": request["request_sha256"],
            "executor_attestation_sha256": executor_attestation[
                "attestation_sha256"
            ],
            "challenge_evaluator_provenance_sha256": challenge_evaluator_provenance[
                "provenance_sha256"
            ],
            "no_op_challenge_terminal_sha256": no_op_terminal[
                "terminal_sha256"
            ],
            "action_challenge_terminal_sha256": action_terminal[
                "terminal_sha256"
            ],
            "legacy_no_op_evaluated_terminal_receipt_sha256": no_op_terminal[
                "legacy_evaluated_terminal_receipt_sha256"
            ],
            "legacy_action_evaluated_terminal_receipt_sha256": action_terminal[
                "legacy_evaluated_terminal_receipt_sha256"
            ],
            "legacy_contribution_record_sha256": record["record_sha256"],
            "replicate_id": record["replicate_id"],
            "signed_terminal_contribution": record[
                "signed_task_contribution"
            ],
            "same_state_matched_continuation": True,
            "post_terminal_evaluator_signal_embedded": True,
            "evaluator_signal_available_to_forward": False,
            "legacy_contribution_schema_modified": False,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": False,
        }
    )
    value["contribution_sha256"] = object_sha256(value)
    validate_challenge_contribution_record(
        value,
        protocol=protocol,
        request=request,
        executor_attestation=executor_attestation,
        challenge_evaluator_provenance=challenge_evaluator_provenance,
        no_op_terminal=no_op_terminal,
        action_terminal=action_terminal,
    )
    return value


def validate_challenge_contribution_record(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    request: Mapping[str, Any] | None = None,
    executor_attestation: Mapping[str, Any] | None = None,
    challenge_evaluator_provenance: Mapping[str, Any] | None = None,
    no_op_terminal: Mapping[str, Any] | None = None,
    action_terminal: Mapping[str, Any] | None = None,
) -> None:
    record = _validate_base(
        value,
        keys=CONTRIBUTION_KEYS,
        role=CONTRIBUTION_ROLE,
        seal_key="contribution_sha256",
        label="challenge contribution",
        protocol=protocol,
    )
    hashes = (
        "execution_request_sha256",
        "executor_attestation_sha256",
        "challenge_evaluator_provenance_sha256",
        "no_op_challenge_terminal_sha256",
        "action_challenge_terminal_sha256",
        "legacy_no_op_evaluated_terminal_receipt_sha256",
        "legacy_action_evaluated_terminal_receipt_sha256",
        "legacy_contribution_record_sha256",
    )
    _bounded(
        record.get("signed_terminal_contribution"),
        label="signed terminal contribution",
    )
    if (
        any(not is_sha256(record.get(key)) for key in hashes)
        or record.get("replicate_id") not in REPLICATE_IDS
        or isinstance(record.get("replicate_id"), bool)
        or record.get("same_state_matched_continuation") is not True
        or record.get("post_terminal_evaluator_signal_embedded") is not True
        or record.get("evaluator_signal_available_to_forward") is not False
        or record.get("legacy_contribution_schema_modified") is not False
        or record.get("historical_payload_after_wrapping_possible") is not True
        or record.get("external_target_precomputation_excluded") is not False
    ):
        raise ValueError("V2.42.28 challenge contribution drifted")
    parents = (
        (request, "execution_request_sha256", "request_sha256"),
        (executor_attestation, "executor_attestation_sha256", "attestation_sha256"),
        (
            challenge_evaluator_provenance,
            "challenge_evaluator_provenance_sha256",
            "provenance_sha256",
        ),
        (no_op_terminal, "no_op_challenge_terminal_sha256", "terminal_sha256"),
        (action_terminal, "action_challenge_terminal_sha256", "terminal_sha256"),
    )
    for parent, left, right in parents:
        if parent is not None and record[left] != parent[right]:
            raise ValueError("V2.42.28 contribution parent binding drifted")
    if no_op_terminal is not None and (
        no_op_terminal["branch_role"] != "no_op"
        or no_op_terminal["replicate_id"] != record["replicate_id"]
    ):
        raise ValueError("V2.42.28 no-op terminal identity drifted")
    if action_terminal is not None and (
        action_terminal["branch_role"] != "action"
        or action_terminal["replicate_id"] != record["replicate_id"]
    ):
        raise ValueError("V2.42.28 action terminal identity drifted")


def build_challenge_replicate_aggregate(
    *,
    protocol: Mapping[str, Any],
    request: Mapping[str, Any],
    executor_attestation: Mapping[str, Any],
    challenge_evaluator_provenance: Mapping[str, Any],
    challenge_contributions: Sequence[Mapping[str, Any]],
    legacy_replicate_aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    contributions = sorted(
        (copy.deepcopy(dict(row)) for row in challenge_contributions),
        key=lambda row: int(row.get("replicate_id", -1)),
    )
    if len(contributions) != 3:
        raise ValueError("V2.42.28 requires exactly three challenge contributions")
    for row in contributions:
        validate_challenge_contribution_record(row, protocol=protocol)
    aggregate = copy.deepcopy(dict(legacy_replicate_aggregate))
    if (
        aggregate.get("role") != REPLICATE_AGGREGATE_ROLE
        or not _sealed(aggregate, seal_key="aggregate_sha256")
        or [row["replicate_id"] for row in contributions] != list(REPLICATE_IDS)
        or aggregate.get("replicate_ids") != list(REPLICATE_IDS)
        or aggregate.get("replicate_record_sha256")
        != [row["legacy_contribution_record_sha256"] for row in contributions]
        or aggregate.get("replicate_signed_task_contribution")
        != [row["signed_terminal_contribution"] for row in contributions]
    ):
        raise ValueError("V2.42.28 legacy aggregate binding drifted")
    parent_values = (
        request["request_sha256"],
        executor_attestation["attestation_sha256"],
        challenge_evaluator_provenance["provenance_sha256"],
        request["launch_challenge_sha256"],
    )
    if any(
        (
            row["execution_request_sha256"],
            row["executor_attestation_sha256"],
            row["challenge_evaluator_provenance_sha256"],
            row["launch_challenge_sha256"],
        )
        != parent_values
        for row in contributions
    ):
        raise ValueError("V2.42.28 aggregate contribution parents differ")
    value = _base(
        role=AGGREGATE_ROLE,
        protocol=protocol,
        launch_challenge_sha256=request["launch_challenge_sha256"],
    )
    value.update(
        {
            "execution_request_sha256": request["request_sha256"],
            "executor_attestation_sha256": executor_attestation[
                "attestation_sha256"
            ],
            "challenge_evaluator_provenance_sha256": challenge_evaluator_provenance[
                "provenance_sha256"
            ],
            "challenge_contribution_sha256s": [
                row["contribution_sha256"] for row in contributions
            ],
            "legacy_contribution_record_sha256s": [
                row["legacy_contribution_record_sha256"]
                for row in contributions
            ],
            "legacy_replicate_aggregate_sha256": aggregate[
                "aggregate_sha256"
            ],
            "replicate_ids": list(REPLICATE_IDS),
            "replicate_signed_terminal_contributions": aggregate[
                "replicate_signed_task_contribution"
            ],
            "mean_signed_terminal_contribution": aggregate[
                "mean_signed_task_contribution"
            ],
            "task_cluster_is_statistical_unit": True,
            "replicates_are_repeated_measurements_not_independent_tasks": True,
            "post_terminal_evaluator_signal_embedded": True,
            "evaluator_signal_available_to_forward": False,
            "legacy_aggregate_schema_modified": False,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": False,
        }
    )
    value["aggregate_sha256"] = object_sha256(value)
    validate_challenge_replicate_aggregate(
        value,
        protocol=protocol,
        request=request,
        executor_attestation=executor_attestation,
        challenge_evaluator_provenance=challenge_evaluator_provenance,
        challenge_contributions=contributions,
    )
    return value


def validate_challenge_replicate_aggregate(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    request: Mapping[str, Any] | None = None,
    executor_attestation: Mapping[str, Any] | None = None,
    challenge_evaluator_provenance: Mapping[str, Any] | None = None,
    challenge_contributions: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    aggregate = _validate_base(
        value,
        keys=AGGREGATE_KEYS,
        role=AGGREGATE_ROLE,
        seal_key="aggregate_sha256",
        label="challenge aggregate",
        protocol=protocol,
    )
    hashes = (
        "execution_request_sha256",
        "executor_attestation_sha256",
        "challenge_evaluator_provenance_sha256",
        "legacy_replicate_aggregate_sha256",
    )
    challenge_hashes = _hash_list(
        aggregate.get("challenge_contribution_sha256s"),
        label="challenge contributions",
        length=3,
    )
    legacy_hashes = _hash_list(
        aggregate.get("legacy_contribution_record_sha256s"),
        label="legacy contributions",
        length=3,
    )
    contributions = aggregate.get("replicate_signed_terminal_contributions")
    if not isinstance(contributions, list) or len(contributions) != 3:
        raise ValueError("V2.42.28 aggregate contribution vector is invalid")
    numbers = [_bounded(item, label="replicate contribution") for item in contributions]
    mean = _bounded(
        aggregate.get("mean_signed_terminal_contribution"),
        label="mean terminal contribution",
    )
    if (
        any(not is_sha256(aggregate.get(key)) for key in hashes)
        or aggregate.get("replicate_ids") != list(REPLICATE_IDS)
        or mean != round(sum(numbers) / 3, 12)
        or aggregate.get("task_cluster_is_statistical_unit") is not True
        or aggregate.get(
            "replicates_are_repeated_measurements_not_independent_tasks"
        )
        is not True
        or aggregate.get("post_terminal_evaluator_signal_embedded") is not True
        or aggregate.get("evaluator_signal_available_to_forward") is not False
        or aggregate.get("legacy_aggregate_schema_modified") is not False
        or aggregate.get("historical_payload_after_wrapping_possible") is not True
        or aggregate.get("external_target_precomputation_excluded") is not False
    ):
        raise ValueError("V2.42.28 challenge aggregate drifted")
    parents = (
        (request, "execution_request_sha256", "request_sha256"),
        (executor_attestation, "executor_attestation_sha256", "attestation_sha256"),
        (
            challenge_evaluator_provenance,
            "challenge_evaluator_provenance_sha256",
            "provenance_sha256",
        ),
    )
    for parent, left, right in parents:
        if parent is not None and aggregate[left] != parent[right]:
            raise ValueError("V2.42.28 aggregate parent binding drifted")
    if challenge_contributions is not None:
        rows = sorted(challenge_contributions, key=lambda row: row["replicate_id"])
        if (
            challenge_hashes != [row["contribution_sha256"] for row in rows]
            or legacy_hashes
            != [row["legacy_contribution_record_sha256"] for row in rows]
            or numbers != [row["signed_terminal_contribution"] for row in rows]
        ):
            raise ValueError("V2.42.28 aggregate contribution binding drifted")


def build_challenge_bound_outer_pair(
    *,
    protocol: Mapping[str, Any],
    sequence_protocol: Mapping[str, Any],
    commitment: Mapping[str, Any],
    launch: Mapping[str, Any],
    reservation: Mapping[str, Any],
    request: Mapping[str, Any],
    challenge_prediction_freeze: Mapping[str, Any],
    executor_attestation: Mapping[str, Any],
    challenge_evaluator_provenance: Mapping[str, Any],
    challenge_terminals: Sequence[Mapping[str, Any]],
    challenge_contributions: Sequence[Mapping[str, Any]],
    challenge_aggregate: Mapping[str, Any],
    legacy_outer_pair: Mapping[str, Any],
    outer_job_manifest: Mapping[str, Any],
    outer_bundle_sha256: str,
    outer_evaluated_terminal_receipts: Sequence[Mapping[str, Any]],
    outer_prediction_freeze: Mapping[str, Any],
    outer_evaluator_provenance_receipt: Mapping[str, Any],
    outer_terminal_state_records: Sequence[Mapping[str, Any]],
    outer_contribution_records: Sequence[Mapping[str, Any]],
    outer_replicate_aggregate: Mapping[str, Any],
    outer_adapter_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay every legacy layer and join its challenge-bound envelope DAG."""

    validate_challenge_graph_protocol(protocol, sequence_protocol=sequence_protocol)
    validate_challenge_execution_request(
        request,
        protocol=protocol,
        commitment=commitment,
        launch=launch,
        reservation=reservation,
    )
    validate_challenge_prediction_freeze(
        challenge_prediction_freeze, protocol=protocol, request=request
    )
    validate_unsigned_executor_declaration(
        executor_attestation,
        protocol=protocol,
        request=request,
        challenge_prediction_freeze=challenge_prediction_freeze,
    )
    validate_challenge_evaluator_provenance(
        challenge_evaluator_provenance,
        protocol=protocol,
        request=request,
        challenge_prediction_freeze=challenge_prediction_freeze,
        executor_attestation=executor_attestation,
    )
    terminals = sorted(
        (copy.deepcopy(dict(row)) for row in challenge_terminals),
        key=lambda row: (row.get("replicate_id", -1), row.get("branch_role", "")),
    )
    if len(terminals) != 6:
        raise ValueError("V2.42.28 requires exactly six challenge terminals")
    for row in terminals:
        validate_challenge_evaluated_terminal(
            row,
            protocol=protocol,
            request=request,
            challenge_prediction_freeze=challenge_prediction_freeze,
            executor_attestation=executor_attestation,
            challenge_evaluator_provenance=challenge_evaluator_provenance,
        )
    terminal_index = {
        (row["replicate_id"], row["branch_role"]): row for row in terminals
    }
    if set(terminal_index) != {
        (replicate, role)
        for replicate in REPLICATE_IDS
        for role in ("no_op", "action")
    }:
        raise ValueError("V2.42.28 terminal matrix is incomplete")
    legacy_terminal_index = {
        (row["replicate_id"], row["branch_role"]): row
        for row in outer_evaluated_terminal_receipts
    }
    if set(legacy_terminal_index) != set(terminal_index):
        raise ValueError("V2.42.28 legacy terminal matrix is incomplete")
    for identity, wrapper in terminal_index.items():
        legacy = legacy_terminal_index[identity]
        if (
            wrapper["legacy_evaluated_terminal_receipt_sha256"]
            != legacy.get("receipt_payload_sha256")
            or wrapper["legacy_parent_terminal_receipt_sha256"]
            != legacy.get("parent_v24122_terminal_receipt_sha256")
            or wrapper["terminal_state_sha256"]
            != legacy.get("terminal_state_sha256")
            or wrapper["terminal_status"] != legacy.get("terminal_status")
            or wrapper["evaluator_valid"] != legacy.get("evaluator_valid")
            or wrapper["terminal_task_loss"]
            != legacy.get("terminal_task_loss")
        ):
            raise ValueError("V2.42.28 terminal wrapper differs from legacy receipt")
    contributions = sorted(
        (copy.deepcopy(dict(row)) for row in challenge_contributions),
        key=lambda row: row.get("replicate_id", -1),
    )
    if len(contributions) != 3:
        raise ValueError("V2.42.28 requires exactly three challenge contributions")
    legacy_contribution_index = {
        row["replicate_id"]: row for row in outer_contribution_records
    }
    if set(legacy_contribution_index) != set(REPLICATE_IDS):
        raise ValueError("V2.42.28 legacy contribution matrix is incomplete")
    for row in contributions:
        replicate = row["replicate_id"]
        validate_challenge_contribution_record(
            row,
            protocol=protocol,
            request=request,
            executor_attestation=executor_attestation,
            challenge_evaluator_provenance=challenge_evaluator_provenance,
            no_op_terminal=terminal_index[(replicate, "no_op")],
            action_terminal=terminal_index[(replicate, "action")],
        )
        legacy = legacy_contribution_index[replicate]
        if (
            row["legacy_contribution_record_sha256"]
            != legacy.get("record_sha256")
            or row["legacy_no_op_evaluated_terminal_receipt_sha256"]
            != legacy.get("no_op_terminal_receipt_sha256")
            or row["legacy_action_evaluated_terminal_receipt_sha256"]
            != legacy.get("action_terminal_receipt_sha256")
            or row["signed_terminal_contribution"]
            != legacy.get("signed_task_contribution")
        ):
            raise ValueError(
                "V2.42.28 contribution wrapper differs from legacy record"
            )
    validate_challenge_replicate_aggregate(
        challenge_aggregate,
        protocol=protocol,
        request=request,
        executor_attestation=executor_attestation,
        challenge_evaluator_provenance=challenge_evaluator_provenance,
        challenge_contributions=contributions,
    )
    if (
        challenge_aggregate["legacy_replicate_aggregate_sha256"]
        != outer_replicate_aggregate.get("aggregate_sha256")
        or challenge_aggregate["replicate_signed_terminal_contributions"]
        != outer_replicate_aggregate.get("replicate_signed_task_contribution")
        or challenge_aggregate["mean_signed_terminal_contribution"]
        != outer_replicate_aggregate.get("mean_signed_task_contribution")
    ):
        raise ValueError("V2.42.28 aggregate wrapper differs from legacy aggregate")
    replayed = adapt_v24123_source_graph(
        job_manifest=outer_job_manifest,
        bundle_sha256=outer_bundle_sha256,
        evaluated_terminal_receipts=outer_evaluated_terminal_receipts,
        prediction_freeze=outer_prediction_freeze,
        evaluator_provenance_receipt=outer_evaluator_provenance_receipt,
        terminal_state_records=outer_terminal_state_records,
        contribution_records=outer_contribution_records,
        replicate_aggregate=outer_replicate_aggregate,
    )
    validate_adapter_result(replayed)
    if dict(outer_adapter_result) != replayed:
        raise ValueError("V2.42.28 outer adapter result differs from source replay")
    validate_independent_outer_target_pair(legacy_outer_pair)
    source = replayed["source_receipt"]
    verified = replayed["verified_contribution"]
    pair_bindings = {
        "outer_job_manifest_sha256": outer_job_manifest["manifest_sha256"],
        "semantic_bundle_sha256": outer_bundle_sha256,
        "outer_adapter_result_sha256": replayed["adapter_result_sha256"],
        "outer_source_receipt_sha256": source["receipt_sha256"],
        "outer_verified_contribution_sha256": verified["record_sha256"],
        "outer_prediction_freeze_sha256": source["prediction_freeze_sha256"],
        "outer_evaluator_provenance_receipt_sha256": source[
            "evaluator_provenance_receipt_sha256"
        ],
        "outer_replicate_aggregate_sha256": source[
            "replicate_aggregate_sha256"
        ],
    }
    if (
        any(legacy_outer_pair[key] != expected for key, expected in pair_bindings.items())
        or sorted(legacy_outer_pair["outer_evaluated_terminal_receipt_sha256s"])
        != sorted(source["evaluated_terminal_receipt_sha256s"])
        or sorted(legacy_outer_pair["outer_contribution_record_sha256s"])
        != sorted(source["contribution_record_sha256s"])
        or legacy_outer_pair["prediction_freeze_sha256"]
        != commitment["prediction_freeze_sha256"]
        or legacy_outer_pair["task_cluster_ref_sha256"]
        != request["task_cluster_ref_sha256"]
        or legacy_outer_pair["trajectory_ref_sha256"]
        != request["trajectory_ref_sha256"]
        or legacy_outer_pair["context"] != request["context"]
        or legacy_outer_pair["action"] != request["action"]
        or legacy_outer_pair["continuation_policy_sha256"]
        != request["continuation_policy_sha256"]
    ):
        raise ValueError("V2.42.28 legacy outer pair source binding drifted")
    if (
        {
            row["legacy_evaluated_terminal_receipt_sha256"]
            for row in terminals
        }
        != set(source["evaluated_terminal_receipt_sha256s"])
        or {
            row["legacy_contribution_record_sha256"]
            for row in contributions
        }
        != set(source["contribution_record_sha256s"])
        or challenge_aggregate["legacy_replicate_aggregate_sha256"]
        != source["replicate_aggregate_sha256"]
    ):
        raise ValueError("V2.42.28 envelope-to-source graph binding drifted")
    value = _base(
        role=PAIR_ROLE,
        protocol=protocol,
        launch_challenge_sha256=request["launch_challenge_sha256"],
    )
    value.update(
        {
            "sequence_protocol_sha256": protocol["sequence_protocol_sha256"],
            "outer_target_protocol_sha256": protocol[
                "outer_target_protocol_sha256"
            ],
            "prediction_commitment_sha256": commitment["commitment_sha256"],
            "outer_launch_receipt_sha256": launch["launch_receipt_sha256"],
            "outer_reservation_receipt_sha256": reservation[
                "reservation_sha256"
            ],
            "execution_request_sha256": request["request_sha256"],
            "challenge_prediction_freeze_sha256": challenge_prediction_freeze[
                "freeze_sha256"
            ],
            "executor_attestation_sha256": executor_attestation[
                "attestation_sha256"
            ],
            "challenge_evaluator_provenance_sha256": challenge_evaluator_provenance[
                "provenance_sha256"
            ],
            "challenge_terminal_sha256s": [
                row["terminal_sha256"] for row in terminals
            ],
            "challenge_contribution_sha256s": [
                row["contribution_sha256"] for row in contributions
            ],
            "challenge_replicate_aggregate_sha256": challenge_aggregate[
                "aggregate_sha256"
            ],
            "legacy_outer_pair_sha256": legacy_outer_pair["pair_sha256"],
            "legacy_outer_job_manifest_sha256": outer_job_manifest[
                "manifest_sha256"
            ],
            "legacy_outer_bundle_sha256": outer_bundle_sha256,
            "legacy_outer_adapter_result_sha256": replayed[
                "adapter_result_sha256"
            ],
            "legacy_outer_source_receipt_sha256": source["receipt_sha256"],
            "legacy_outer_verified_contribution_sha256": verified[
                "record_sha256"
            ],
            "legacy_outer_prediction_freeze_sha256": source[
                "prediction_freeze_sha256"
            ],
            "legacy_outer_evaluator_provenance_receipt_sha256": source[
                "evaluator_provenance_receipt_sha256"
            ],
            "legacy_outer_evaluated_terminal_receipt_sha256s": sorted(
                source["evaluated_terminal_receipt_sha256s"]
            ),
            "legacy_outer_contribution_record_sha256s": sorted(
                source["contribution_record_sha256s"]
            ),
            "legacy_outer_replicate_aggregate_sha256": source[
                "replicate_aggregate_sha256"
            ],
            "task_cluster_ref_sha256": request["task_cluster_ref_sha256"],
            "trajectory_ref_sha256": request["trajectory_ref_sha256"],
            "context": request["context"],
            "action": request["action"],
            "continuation_policy_sha256": request[
                "continuation_policy_sha256"
            ],
            "predicted_credit": legacy_outer_pair["predicted_credit"],
            "outer_target_contribution": legacy_outer_pair[
                "outer_target_contribution"
            ],
            "all_required_layers_present": True,
            "launch_challenge_bound_in_every_envelope_layer": True,
            "challenge_only_at_top_level": False,
            "exact_parent_hash_dag_validated": True,
            "legacy_source_graph_replayed_through_v24224": True,
            "legacy_v24226_pair_revalidated": True,
            "legacy_payload_schemas_modified": False,
            "legacy_payloads_are_challenge_native": False,
            "native_executor_consumed_challenge_independently_proven": False,
            "independent_append_only_or_transparency_service_used": False,
            "store_api_execution_independently_attested": False,
            "offline_self_consistent_graph_fabrication_cryptographically_excluded": False,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": False,
            "semantic_or_distributional_ood_independently_assessed": False,
            "formal_gate2b_evaluation_authorized": False,
        }
    )
    value["pair_sha256"] = object_sha256(value)
    validate_challenge_bound_outer_pair(
        value,
        protocol=protocol,
        sequence_protocol=sequence_protocol,
        commitment=commitment,
        launch=launch,
        reservation=reservation,
        request=request,
        challenge_prediction_freeze=challenge_prediction_freeze,
        executor_attestation=executor_attestation,
        challenge_evaluator_provenance=challenge_evaluator_provenance,
        challenge_terminals=terminals,
        challenge_contributions=contributions,
        challenge_aggregate=challenge_aggregate,
    )
    return value


def validate_challenge_bound_outer_pair(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    sequence_protocol: Mapping[str, Any] | None = None,
    commitment: Mapping[str, Any] | None = None,
    launch: Mapping[str, Any] | None = None,
    reservation: Mapping[str, Any] | None = None,
    request: Mapping[str, Any] | None = None,
    challenge_prediction_freeze: Mapping[str, Any] | None = None,
    executor_attestation: Mapping[str, Any] | None = None,
    challenge_evaluator_provenance: Mapping[str, Any] | None = None,
    challenge_terminals: Sequence[Mapping[str, Any]] | None = None,
    challenge_contributions: Sequence[Mapping[str, Any]] | None = None,
    challenge_aggregate: Mapping[str, Any] | None = None,
) -> None:
    pair = _validate_base(
        value,
        keys=PAIR_KEYS,
        role=PAIR_ROLE,
        seal_key="pair_sha256",
        label="challenge-bound outer pair",
        protocol=protocol,
    )
    scalar_hashes = (
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "prediction_commitment_sha256",
        "outer_launch_receipt_sha256",
        "outer_reservation_receipt_sha256",
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "executor_attestation_sha256",
        "challenge_evaluator_provenance_sha256",
        "challenge_replicate_aggregate_sha256",
        "legacy_outer_pair_sha256",
        "legacy_outer_job_manifest_sha256",
        "legacy_outer_bundle_sha256",
        "legacy_outer_adapter_result_sha256",
        "legacy_outer_source_receipt_sha256",
        "legacy_outer_verified_contribution_sha256",
        "legacy_outer_prediction_freeze_sha256",
        "legacy_outer_evaluator_provenance_receipt_sha256",
        "legacy_outer_replicate_aggregate_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "continuation_policy_sha256",
    )
    _hash_list(
        pair.get("challenge_terminal_sha256s"),
        label="challenge terminals",
        length=6,
    )
    _hash_list(
        pair.get("challenge_contribution_sha256s"),
        label="challenge contributions",
        length=3,
    )
    _hash_list(
        pair.get("legacy_outer_evaluated_terminal_receipt_sha256s"),
        label="legacy evaluated terminals",
        length=6,
    )
    _hash_list(
        pair.get("legacy_outer_contribution_record_sha256s"),
        label="legacy contributions",
        length=3,
    )
    _bounded(pair.get("predicted_credit"), label="predicted credit")
    _bounded(pair.get("outer_target_contribution"), label="outer target")
    true_fields = (
        "all_required_layers_present",
        "launch_challenge_bound_in_every_envelope_layer",
        "exact_parent_hash_dag_validated",
        "legacy_source_graph_replayed_through_v24224",
        "legacy_v24226_pair_revalidated",
        "historical_payload_after_wrapping_possible",
    )
    false_fields = (
        "challenge_only_at_top_level",
        "legacy_payload_schemas_modified",
        "legacy_payloads_are_challenge_native",
        "native_executor_consumed_challenge_independently_proven",
        "independent_append_only_or_transparency_service_used",
        "store_api_execution_independently_attested",
        "offline_self_consistent_graph_fabrication_cryptographically_excluded",
        "external_target_precomputation_excluded",
        "semantic_or_distributional_ood_independently_assessed",
        "formal_gate2b_evaluation_authorized",
    )
    if (
        any(not is_sha256(pair.get(key)) for key in scalar_hashes)
        or not isinstance(pair.get("context"), str)
        or not isinstance(pair.get("action"), str)
        or any(pair.get(key) is not True for key in true_fields)
        or any(pair.get(key) is not False for key in false_fields)
    ):
        raise ValueError("V2.42.28 challenge-bound outer pair drifted")
    if sequence_protocol is not None:
        validate_commit_reveal_protocol(sequence_protocol)
        if pair["sequence_protocol_sha256"] != sequence_protocol["protocol_sha256"]:
            raise ValueError("V2.42.28 pair sequence binding drifted")
    direct_parents = (
        (commitment, "prediction_commitment_sha256", "commitment_sha256"),
        (launch, "outer_launch_receipt_sha256", "launch_receipt_sha256"),
        (reservation, "outer_reservation_receipt_sha256", "reservation_sha256"),
        (request, "execution_request_sha256", "request_sha256"),
        (
            challenge_prediction_freeze,
            "challenge_prediction_freeze_sha256",
            "freeze_sha256",
        ),
        (executor_attestation, "executor_attestation_sha256", "attestation_sha256"),
        (
            challenge_evaluator_provenance,
            "challenge_evaluator_provenance_sha256",
            "provenance_sha256",
        ),
        (
            challenge_aggregate,
            "challenge_replicate_aggregate_sha256",
            "aggregate_sha256",
        ),
    )
    for parent, left, right in direct_parents:
        if parent is not None and pair[left] != parent[right]:
            raise ValueError("V2.42.28 final pair parent binding drifted")
    if challenge_terminals is not None:
        rows = sorted(
            challenge_terminals,
            key=lambda row: (row["replicate_id"], row["branch_role"]),
        )
        if pair["challenge_terminal_sha256s"] != [
            row["terminal_sha256"] for row in rows
        ]:
            raise ValueError("V2.42.28 final pair terminal binding drifted")
    if challenge_contributions is not None:
        rows = sorted(challenge_contributions, key=lambda row: row["replicate_id"])
        if pair["challenge_contribution_sha256s"] != [
            row["contribution_sha256"] for row in rows
        ]:
            raise ValueError("V2.42.28 final pair contribution binding drifted")
    for parent in (
        request,
        challenge_prediction_freeze,
        executor_attestation,
        challenge_evaluator_provenance,
        challenge_aggregate,
    ):
        if parent is not None and pair["launch_challenge_sha256"] != parent[
            "launch_challenge_sha256"
        ]:
            raise ValueError("V2.42.28 final pair challenge binding drifted")
