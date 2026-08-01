"""Create-exclusive commit/launch/reveal sequencing for outer credit targets.

V2.42.26 separates an inner credit prediction from a mechanically independent
outer target graph, but its pure object contract cannot establish publication
order.  This build-only module adds a repository-local state machine:

``prediction committed -> outer launch opened -> pair materialized -> revealed``.

The store creates a fresh SHA-256-named directory, publishes every control file
with ``O_EXCL``, and reserves the outer directory only after the launch receipt
exists.  The final reveal binds the commitment, launch, reservation, pair, and
their exact file bytes.  The V2.42.26 pair itself does not natively bind the
launch challenge.  The store reads and writes only exact-schema,
benchmark-content-free control artifacts.

The boundary is deliberately narrow.  It proves the order enforced by this
repository store; it does not prove a trusted physical clock, prevent an
external party from precomputing a target, exclude a hostile concurrent
filesystem writer, establish semantic/OOD equivalence, authorize a real outer
campaign, or authorize Gate 2B, training, benchmark execution, or leaderboard
claims.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping

from .v2409_interventions import CONTEXT_ACTIONS
from .v24123_release import is_sha256
from .v24223_sign_preserving_credit import object_sha256
from .v24226_credit_outer_target_firewall import (
    validate_credit_prediction_freeze,
    validate_independent_outer_target_pair,
    validate_outer_target_protocol,
)


POLICY_ID = "v24227_credit_outer_commit_launch_reveal_v1"
PROTOCOL_ROLE = "v24227_credit_commit_reveal_protocol"
COMMITMENT_ROLE = "v24227_credit_prediction_commitment"
LAUNCH_ROLE = "v24227_credit_outer_launch_receipt"
RESERVATION_ROLE = "v24227_credit_outer_root_reservation"
REVEAL_ROLE = "v24227_credit_outer_reveal_receipt"

PRODUCTION_PACKAGE_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False
GATE2B_PASS_AUTHORIZED = False
OUTER_CAMPAIGN_EXECUTION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False

MAX_CONTROL_FILE_BYTES = 2_000_000

PROTOCOL_FILE = Path("sequence_protocol.json")
COMMITMENT_FILE = Path("prediction_commitment.json")
LAUNCH_FILE = Path("outer_launch_receipt.json")
OUTER_DIRECTORY = Path("outer")
OUTER_RESERVATION_FILE = OUTER_DIRECTORY / "reservation.json"
OUTER_PAIR_FILE = OUTER_DIRECTORY / "outer_pair.json"
REVEAL_FILE = Path("outer_reveal_receipt.json")

PROTOCOL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_control",
        "outer_target_protocol_sha256",
        "credit_policy_sha256",
        "sequence_namespace_sha256",
        "coordinator_contract_sha256",
        "launch_policy_sha256",
        "sequence_states",
        "prediction_commitment_must_precede_launch",
        "launch_receipt_must_precede_pair_materialization",
        "pair_materialization_must_precede_reveal",
        "create_exclusive_stage_publication_required",
        "fresh_reserved_outer_root_required",
        "repository_publication_order_is_target_claim",
        "physical_wall_clock_or_external_precomputation_claimed",
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "protocol_sha256",
    }
)

COMMITMENT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_control",
        "protocol_sha256",
        "outer_target_protocol_sha256",
        "credit_policy_sha256",
        "sequence_namespace_sha256",
        "prediction_freeze_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "partition_role",
        "context",
        "action",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "continuation_policy_sha256",
        "expected_outer_job_manifest_sha256",
        "expected_semantic_bundle_sha256",
        "predicted_credit",
        "commit_nonce_sha256",
        "outer_output_namespace_sha256",
        "outer_seed_schedule_sha256",
        "outer_execution_contract_sha256",
        "outer_evaluator_protocol_sha256",
        "sequence_state",
        "outer_pair_target_or_contribution_input_accepted",
        "outer_target_unavailable_to_commit_builder",
        "fresh_sequence_directory_created_by_store",
        "outer_root_absent_at_commit",
        "external_target_precomputation_excluded",
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "commitment_sha256",
    }
)

LAUNCH_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_control",
        "protocol_sha256",
        "outer_target_protocol_sha256",
        "sequence_namespace_sha256",
        "prediction_commitment_sha256",
        "prediction_freeze_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "context",
        "action",
        "continuation_policy_sha256",
        "expected_outer_job_manifest_sha256",
        "expected_semantic_bundle_sha256",
        "outer_output_namespace_sha256",
        "outer_seed_schedule_sha256",
        "outer_execution_contract_sha256",
        "outer_evaluator_protocol_sha256",
        "launch_request_sha256",
        "launch_challenge_sha256",
        "sequence_state",
        "predecessor_state",
        "commitment_replayed_before_launch",
        "outer_pair_target_or_contribution_input_accepted",
        "outer_target_unavailable_to_launch_builder",
        "outer_root_absent_before_launch_receipt_publication",
        "outer_root_creation_permitted_only_after_launch_receipt",
        "launch_challenge_generated_by_store",
        "pair_native_launch_challenge_binding_required_for_future_formal_gate",
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "launch_receipt_sha256",
    }
)

RESERVATION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_control",
        "protocol_sha256",
        "sequence_namespace_sha256",
        "outer_launch_receipt_sha256",
        "launch_challenge_sha256",
        "outer_output_namespace_sha256",
        "reservation_nonce_sha256",
        "sequence_state",
        "predecessor_state",
        "launch_receipt_replayed_before_reservation",
        "reserved_root_created_by_store",
        "outer_pair_target_or_contribution_input_accepted",
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "reservation_sha256",
    }
)

REVEAL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_control",
        "protocol_sha256",
        "outer_target_protocol_sha256",
        "sequence_namespace_sha256",
        "prediction_commitment_sha256",
        "outer_launch_receipt_sha256",
        "outer_reservation_receipt_sha256",
        "prediction_freeze_sha256",
        "outer_pair_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "context",
        "action",
        "continuation_policy_sha256",
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
        "launch_challenge_sha256",
        "outer_output_namespace_sha256",
        "sequence_state",
        "predecessor_state",
        "stage_sequence",
        "protocol_file_sha256",
        "commitment_file_sha256",
        "launch_file_sha256",
        "outer_reservation_file_sha256",
        "outer_pair_file_sha256",
        "create_exclusive_stage_files",
        "fresh_sequence_directory_created_at_commit",
        "fresh_outer_root_absent_until_launch",
        "outer_pair_file_inside_reserved_root",
        "prediction_commitment_precedes_launch_in_store_state_machine",
        "launch_precedes_pair_publication_in_store_state_machine",
        "pair_precedes_reveal_publication_in_store_state_machine",
        "repository_commit_launch_reveal_order_enforced",
        "outer_pair_native_launch_challenge_binding_present",
        "external_target_precomputation_excluded",
        "trusted_physical_wall_clock_used",
        "physical_wall_clock_creation_order_independently_proven",
        "hostile_concurrent_filesystem_mutation_excluded",
        "independent_append_only_or_transparency_service_used",
        "store_api_execution_independently_attested",
        "offline_self_consistent_chain_fabrication_cryptographically_excluded",
        "local_file_and_directory_fsync_used",
        "semantic_or_distributional_ood_independently_assessed",
        "formal_gate2b_evaluation_authorized",
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control",
        "post_prediction_outer_target_contribution_available_to_reveal_validator",
        "outer_target_used_for_runtime_routing_or_same_forward_pass",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "reveal_sha256",
    }
)


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.27 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    unsigned = copy.deepcopy(dict(value))
    seal = unsigned.pop(seal_key, None)
    return is_sha256(seal) and seal == object_sha256(unsigned)


def _sha256(value: object, *, label: str) -> str:
    if not is_sha256(value):
        raise ValueError(f"V2.42.27 {label} is not a SHA-256")
    return str(value)


def _bounded(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.27 {label} is not numeric")
    number = float(value)
    if not -1.0 <= number <= 1.0:
        raise ValueError(f"V2.42.27 {label} is outside [-1,1]")
    return number


def _hash_list(value: object, *, label: str, length: int) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) != length
        or value != sorted(value)
        or len(value) != len(set(value))
        or any(not is_sha256(item) for item in value)
    ):
        raise ValueError(f"V2.42.27 {label} is not the expected hash list")
    return list(value)


def _valid_context_action(context: object, action: object) -> bool:
    return (
        isinstance(context, str)
        and isinstance(action, str)
        and context in CONTEXT_ACTIONS
        and action in CONTEXT_ACTIONS[context]
    )


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("V2.42.27 stage JSON contains a duplicate key")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"V2.42.27 stage JSON contains nonstandard {value}")


def build_commit_reveal_protocol(
    *,
    outer_target_protocol: Mapping[str, Any],
    sequence_namespace_sha256: str,
    coordinator_contract_sha256: str,
    launch_policy_sha256: str,
) -> dict[str, Any]:
    """Freeze the content-free repository sequence contract."""

    validate_outer_target_protocol(outer_target_protocol)
    namespace = _sha256(sequence_namespace_sha256, label="sequence namespace")
    coordinator = _sha256(
        coordinator_contract_sha256, label="coordinator contract"
    )
    launch_policy = _sha256(launch_policy_sha256, label="launch policy")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PROTOCOL_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_control": True,
        "outer_target_protocol_sha256": outer_target_protocol["protocol_sha256"],
        "credit_policy_sha256": outer_target_protocol["credit_policy_sha256"],
        "sequence_namespace_sha256": namespace,
        "coordinator_contract_sha256": coordinator,
        "launch_policy_sha256": launch_policy,
        "sequence_states": [
            "prediction_committed",
            "outer_launch_opened",
            "outer_root_reserved",
            "outer_pair_materialized",
            "outer_target_revealed",
        ],
        "prediction_commitment_must_precede_launch": True,
        "launch_receipt_must_precede_pair_materialization": True,
        "pair_materialization_must_precede_reveal": True,
        "create_exclusive_stage_publication_required": True,
        "fresh_reserved_outer_root_required": True,
        "repository_publication_order_is_target_claim": True,
        "physical_wall_clock_or_external_precomputation_claimed": False,
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
        "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }
    value["protocol_sha256"] = object_sha256(value)
    validate_commit_reveal_protocol(value, outer_target_protocol=outer_target_protocol)
    return value


def validate_commit_reveal_protocol(
    value: object,
    *,
    outer_target_protocol: Mapping[str, Any] | None = None,
) -> None:
    protocol = _exact_mapping(value, keys=PROTOCOL_KEYS, label="protocol")
    hash_fields = (
        "outer_target_protocol_sha256",
        "credit_policy_sha256",
        "sequence_namespace_sha256",
        "coordinator_contract_sha256",
        "launch_policy_sha256",
    )
    if (
        protocol.get("artifact_version") != 1
        or protocol.get("role") != PROTOCOL_ROLE
        or protocol.get("policy_id") != POLICY_ID
        or protocol.get("label_blind_control") is not True
        or any(not is_sha256(protocol.get(key)) for key in hash_fields)
        or protocol.get("sequence_states")
        != [
            "prediction_committed",
            "outer_launch_opened",
            "outer_root_reserved",
            "outer_pair_materialized",
            "outer_target_revealed",
        ]
        or protocol.get("prediction_commitment_must_precede_launch") is not True
        or protocol.get("launch_receipt_must_precede_pair_materialization")
        is not True
        or protocol.get("pair_materialization_must_precede_reveal") is not True
        or protocol.get("create_exclusive_stage_publication_required") is not True
        or protocol.get("fresh_reserved_outer_root_required") is not True
        or protocol.get("repository_publication_order_is_target_claim") is not True
        or protocol.get("physical_wall_clock_or_external_precomputation_claimed")
        is not False
        or protocol.get(
            "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control"
        )
        is not False
        or protocol.get("production_package_authorized") is not False
        or protocol.get("credit_training_authorized") is not False
        or protocol.get("gate2b_pass_authorized") is not False
        or protocol.get("outer_campaign_execution_authorized") is not False
        or protocol.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(protocol, seal_key="protocol_sha256")
    ):
        raise ValueError("V2.42.27 protocol contract drifted")
    if outer_target_protocol is not None:
        validate_outer_target_protocol(outer_target_protocol)
        if (
            protocol["outer_target_protocol_sha256"]
            != outer_target_protocol["protocol_sha256"]
            or protocol["credit_policy_sha256"]
            != outer_target_protocol["credit_policy_sha256"]
        ):
            raise ValueError("V2.42.27 outer-target protocol binding drifted")


def _build_prediction_commitment(
    *,
    protocol: Mapping[str, Any],
    prediction_freeze: Mapping[str, Any],
    commit_nonce_sha256: str,
    outer_output_namespace_sha256: str,
    outer_seed_schedule_sha256: str,
    outer_execution_contract_sha256: str,
    outer_evaluator_protocol_sha256: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": COMMITMENT_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_control": True,
        "protocol_sha256": protocol["protocol_sha256"],
        "outer_target_protocol_sha256": protocol[
            "outer_target_protocol_sha256"
        ],
        "credit_policy_sha256": protocol["credit_policy_sha256"],
        "sequence_namespace_sha256": protocol["sequence_namespace_sha256"],
        "prediction_freeze_sha256": prediction_freeze["freeze_sha256"],
        "task_cluster_ref_sha256": prediction_freeze[
            "task_cluster_ref_sha256"
        ],
        "trajectory_ref_sha256": prediction_freeze["trajectory_ref_sha256"],
        "partition_role": prediction_freeze["partition_role"],
        "context": prediction_freeze["context"],
        "action": prediction_freeze["action"],
        "source_checkpoint_sha256": prediction_freeze[
            "source_checkpoint_sha256"
        ],
        "shadow_projection_sha256": prediction_freeze[
            "shadow_projection_sha256"
        ],
        "continuation_policy_sha256": prediction_freeze[
            "continuation_policy_sha256"
        ],
        "expected_outer_job_manifest_sha256": prediction_freeze[
            "inner_job_manifest_sha256"
        ],
        "expected_semantic_bundle_sha256": prediction_freeze[
            "inner_bundle_sha256"
        ],
        "predicted_credit": prediction_freeze["predicted_credit"],
        "commit_nonce_sha256": commit_nonce_sha256,
        "outer_output_namespace_sha256": outer_output_namespace_sha256,
        "outer_seed_schedule_sha256": outer_seed_schedule_sha256,
        "outer_execution_contract_sha256": outer_execution_contract_sha256,
        "outer_evaluator_protocol_sha256": outer_evaluator_protocol_sha256,
        "sequence_state": "prediction_committed",
        "outer_pair_target_or_contribution_input_accepted": False,
        "outer_target_unavailable_to_commit_builder": True,
        "fresh_sequence_directory_created_by_store": True,
        "outer_root_absent_at_commit": True,
        "external_target_precomputation_excluded": False,
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
        "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }
    value["commitment_sha256"] = object_sha256(value)
    return value


def validate_prediction_commitment(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    prediction_freeze: Mapping[str, Any] | None = None,
) -> None:
    commitment = _exact_mapping(
        value, keys=COMMITMENT_KEYS, label="prediction commitment"
    )
    hash_fields = (
        "protocol_sha256",
        "outer_target_protocol_sha256",
        "credit_policy_sha256",
        "sequence_namespace_sha256",
        "prediction_freeze_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "continuation_policy_sha256",
        "expected_outer_job_manifest_sha256",
        "expected_semantic_bundle_sha256",
        "commit_nonce_sha256",
        "outer_output_namespace_sha256",
        "outer_seed_schedule_sha256",
        "outer_execution_contract_sha256",
        "outer_evaluator_protocol_sha256",
    )
    _bounded(commitment.get("predicted_credit"), label="predicted credit")
    if (
        commitment.get("artifact_version") != 1
        or commitment.get("role") != COMMITMENT_ROLE
        or commitment.get("policy_id") != POLICY_ID
        or commitment.get("label_blind_control") is not True
        or any(not is_sha256(commitment.get(key)) for key in hash_fields)
        or commitment.get("partition_role") != "development_audit"
        or not _valid_context_action(
            commitment.get("context"), commitment.get("action")
        )
        or commitment.get("sequence_state") != "prediction_committed"
        or commitment.get("outer_pair_target_or_contribution_input_accepted")
        is not False
        or commitment.get("outer_target_unavailable_to_commit_builder") is not True
        or commitment.get("fresh_sequence_directory_created_by_store") is not True
        or commitment.get("outer_root_absent_at_commit") is not True
        or commitment.get("external_target_precomputation_excluded") is not False
        or commitment.get(
            "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control"
        )
        is not False
        or commitment.get("production_package_authorized") is not False
        or commitment.get("credit_training_authorized") is not False
        or commitment.get("gate2b_pass_authorized") is not False
        or commitment.get("outer_campaign_execution_authorized") is not False
        or commitment.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(commitment, seal_key="commitment_sha256")
    ):
        raise ValueError("V2.42.27 prediction commitment contract drifted")
    if protocol is not None:
        validate_commit_reveal_protocol(protocol)
        if any(
            commitment[left] != protocol[right]
            for left, right in (
                ("protocol_sha256", "protocol_sha256"),
                ("outer_target_protocol_sha256", "outer_target_protocol_sha256"),
                ("credit_policy_sha256", "credit_policy_sha256"),
                ("sequence_namespace_sha256", "sequence_namespace_sha256"),
            )
        ):
            raise ValueError("V2.42.27 commitment protocol binding drifted")
    if prediction_freeze is not None:
        validate_credit_prediction_freeze(prediction_freeze)
        expected = {
            "outer_target_protocol_sha256": "protocol_sha256",
            "prediction_freeze_sha256": "freeze_sha256",
            "task_cluster_ref_sha256": "task_cluster_ref_sha256",
            "trajectory_ref_sha256": "trajectory_ref_sha256",
            "partition_role": "partition_role",
            "context": "context",
            "action": "action",
            "source_checkpoint_sha256": "source_checkpoint_sha256",
            "shadow_projection_sha256": "shadow_projection_sha256",
            "continuation_policy_sha256": "continuation_policy_sha256",
            "expected_outer_job_manifest_sha256": "inner_job_manifest_sha256",
            "expected_semantic_bundle_sha256": "inner_bundle_sha256",
            "predicted_credit": "predicted_credit",
        }
        if any(
            commitment[left] != prediction_freeze[right]
            for left, right in expected.items()
        ):
            raise ValueError("V2.42.27 commitment prediction binding drifted")


def _build_launch_receipt(
    *,
    protocol: Mapping[str, Any],
    commitment: Mapping[str, Any],
    launch_request_sha256: str,
    launch_challenge_sha256: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": LAUNCH_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_control": True,
        "protocol_sha256": protocol["protocol_sha256"],
        "outer_target_protocol_sha256": protocol[
            "outer_target_protocol_sha256"
        ],
        "sequence_namespace_sha256": protocol["sequence_namespace_sha256"],
        "prediction_commitment_sha256": commitment["commitment_sha256"],
        "prediction_freeze_sha256": commitment["prediction_freeze_sha256"],
        "task_cluster_ref_sha256": commitment["task_cluster_ref_sha256"],
        "trajectory_ref_sha256": commitment["trajectory_ref_sha256"],
        "context": commitment["context"],
        "action": commitment["action"],
        "continuation_policy_sha256": commitment[
            "continuation_policy_sha256"
        ],
        "expected_outer_job_manifest_sha256": commitment[
            "expected_outer_job_manifest_sha256"
        ],
        "expected_semantic_bundle_sha256": commitment[
            "expected_semantic_bundle_sha256"
        ],
        "outer_output_namespace_sha256": commitment[
            "outer_output_namespace_sha256"
        ],
        "outer_seed_schedule_sha256": commitment["outer_seed_schedule_sha256"],
        "outer_execution_contract_sha256": commitment[
            "outer_execution_contract_sha256"
        ],
        "outer_evaluator_protocol_sha256": commitment[
            "outer_evaluator_protocol_sha256"
        ],
        "launch_request_sha256": launch_request_sha256,
        "launch_challenge_sha256": launch_challenge_sha256,
        "sequence_state": "outer_launch_opened",
        "predecessor_state": "prediction_committed",
        "commitment_replayed_before_launch": True,
        "outer_pair_target_or_contribution_input_accepted": False,
        "outer_target_unavailable_to_launch_builder": True,
        "outer_root_absent_before_launch_receipt_publication": True,
        "outer_root_creation_permitted_only_after_launch_receipt": True,
        "launch_challenge_generated_by_store": True,
        "pair_native_launch_challenge_binding_required_for_future_formal_gate": True,
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
        "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }
    value["launch_receipt_sha256"] = object_sha256(value)
    return value


def validate_launch_receipt(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    commitment: Mapping[str, Any] | None = None,
) -> None:
    launch = _exact_mapping(value, keys=LAUNCH_KEYS, label="launch receipt")
    hash_fields = (
        "protocol_sha256",
        "outer_target_protocol_sha256",
        "sequence_namespace_sha256",
        "prediction_commitment_sha256",
        "prediction_freeze_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "continuation_policy_sha256",
        "expected_outer_job_manifest_sha256",
        "expected_semantic_bundle_sha256",
        "outer_output_namespace_sha256",
        "outer_seed_schedule_sha256",
        "outer_execution_contract_sha256",
        "outer_evaluator_protocol_sha256",
        "launch_request_sha256",
        "launch_challenge_sha256",
    )
    if (
        launch.get("artifact_version") != 1
        or launch.get("role") != LAUNCH_ROLE
        or launch.get("policy_id") != POLICY_ID
        or launch.get("label_blind_control") is not True
        or any(not is_sha256(launch.get(key)) for key in hash_fields)
        or not _valid_context_action(launch.get("context"), launch.get("action"))
        or launch.get("sequence_state") != "outer_launch_opened"
        or launch.get("predecessor_state") != "prediction_committed"
        or launch.get("commitment_replayed_before_launch") is not True
        or launch.get("outer_pair_target_or_contribution_input_accepted") is not False
        or launch.get("outer_target_unavailable_to_launch_builder") is not True
        or launch.get("outer_root_absent_before_launch_receipt_publication")
        is not True
        or launch.get("outer_root_creation_permitted_only_after_launch_receipt")
        is not True
        or launch.get("launch_challenge_generated_by_store") is not True
        or launch.get(
            "pair_native_launch_challenge_binding_required_for_future_formal_gate"
        )
        is not True
        or launch.get(
            "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control"
        )
        is not False
        or launch.get("production_package_authorized") is not False
        or launch.get("credit_training_authorized") is not False
        or launch.get("gate2b_pass_authorized") is not False
        or launch.get("outer_campaign_execution_authorized") is not False
        or launch.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(launch, seal_key="launch_receipt_sha256")
    ):
        raise ValueError("V2.42.27 launch receipt contract drifted")
    if protocol is not None:
        validate_commit_reveal_protocol(protocol)
        if any(
            launch[left] != protocol[right]
            for left, right in (
                ("protocol_sha256", "protocol_sha256"),
                ("outer_target_protocol_sha256", "outer_target_protocol_sha256"),
                ("sequence_namespace_sha256", "sequence_namespace_sha256"),
            )
        ):
            raise ValueError("V2.42.27 launch protocol binding drifted")
    if commitment is not None:
        validate_prediction_commitment(commitment, protocol=protocol)
        expected = {
            "prediction_commitment_sha256": "commitment_sha256",
            "prediction_freeze_sha256": "prediction_freeze_sha256",
            "task_cluster_ref_sha256": "task_cluster_ref_sha256",
            "trajectory_ref_sha256": "trajectory_ref_sha256",
            "context": "context",
            "action": "action",
            "continuation_policy_sha256": "continuation_policy_sha256",
            "expected_outer_job_manifest_sha256": "expected_outer_job_manifest_sha256",
            "expected_semantic_bundle_sha256": "expected_semantic_bundle_sha256",
            "outer_output_namespace_sha256": "outer_output_namespace_sha256",
            "outer_seed_schedule_sha256": "outer_seed_schedule_sha256",
            "outer_execution_contract_sha256": "outer_execution_contract_sha256",
            "outer_evaluator_protocol_sha256": "outer_evaluator_protocol_sha256",
        }
        if any(launch[left] != commitment[right] for left, right in expected.items()):
            raise ValueError("V2.42.27 launch commitment binding drifted")


def _build_outer_reservation_receipt(
    *,
    protocol: Mapping[str, Any],
    launch: Mapping[str, Any],
    reservation_nonce_sha256: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RESERVATION_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_control": True,
        "protocol_sha256": protocol["protocol_sha256"],
        "sequence_namespace_sha256": protocol["sequence_namespace_sha256"],
        "outer_launch_receipt_sha256": launch["launch_receipt_sha256"],
        "launch_challenge_sha256": launch["launch_challenge_sha256"],
        "outer_output_namespace_sha256": launch[
            "outer_output_namespace_sha256"
        ],
        "reservation_nonce_sha256": reservation_nonce_sha256,
        "sequence_state": "outer_root_reserved",
        "predecessor_state": "outer_launch_opened",
        "launch_receipt_replayed_before_reservation": True,
        "reserved_root_created_by_store": True,
        "outer_pair_target_or_contribution_input_accepted": False,
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
        "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }
    value["reservation_sha256"] = object_sha256(value)
    return value


def validate_outer_reservation_receipt(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    launch: Mapping[str, Any] | None = None,
) -> None:
    reservation = _exact_mapping(
        value, keys=RESERVATION_KEYS, label="outer reservation receipt"
    )
    hash_fields = (
        "protocol_sha256",
        "sequence_namespace_sha256",
        "outer_launch_receipt_sha256",
        "launch_challenge_sha256",
        "outer_output_namespace_sha256",
        "reservation_nonce_sha256",
    )
    required_true = (
        "launch_receipt_replayed_before_reservation",
        "reserved_root_created_by_store",
    )
    required_false = (
        "outer_pair_target_or_contribution_input_accepted",
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
    )
    if (
        reservation.get("artifact_version") != 1
        or reservation.get("role") != RESERVATION_ROLE
        or reservation.get("policy_id") != POLICY_ID
        or reservation.get("label_blind_control") is not True
        or any(not is_sha256(reservation.get(key)) for key in hash_fields)
        or reservation.get("sequence_state") != "outer_root_reserved"
        or reservation.get("predecessor_state") != "outer_launch_opened"
        or any(reservation.get(key) is not True for key in required_true)
        or any(reservation.get(key) is not False for key in required_false)
        or not _sealed(reservation, seal_key="reservation_sha256")
    ):
        raise ValueError("V2.42.27 outer reservation contract drifted")
    if protocol is not None:
        validate_commit_reveal_protocol(protocol)
        if any(
            reservation[left] != protocol[right]
            for left, right in (
                ("protocol_sha256", "protocol_sha256"),
                ("sequence_namespace_sha256", "sequence_namespace_sha256"),
            )
        ):
            raise ValueError("V2.42.27 reservation protocol binding drifted")
    if launch is not None:
        validate_launch_receipt(launch, protocol=protocol)
        if any(
            reservation[left] != launch[right]
            for left, right in (
                ("outer_launch_receipt_sha256", "launch_receipt_sha256"),
                ("launch_challenge_sha256", "launch_challenge_sha256"),
                ("outer_output_namespace_sha256", "outer_output_namespace_sha256"),
            )
        ):
            raise ValueError("V2.42.27 reservation launch binding drifted")


def _validate_pair_binding(
    *,
    pair: Mapping[str, Any],
    protocol: Mapping[str, Any],
    commitment: Mapping[str, Any],
) -> None:
    validate_independent_outer_target_pair(pair)
    expected = {
        "protocol_sha256": "outer_target_protocol_sha256",
        "prediction_freeze_sha256": "prediction_freeze_sha256",
        "task_cluster_ref_sha256": "task_cluster_ref_sha256",
        "trajectory_ref_sha256": "trajectory_ref_sha256",
        "partition_role": "partition_role",
        "context": "context",
        "action": "action",
        "source_checkpoint_sha256": "source_checkpoint_sha256",
        "shadow_projection_sha256": "shadow_projection_sha256",
        "continuation_policy_sha256": "continuation_policy_sha256",
        "outer_job_manifest_sha256": "expected_outer_job_manifest_sha256",
        "semantic_bundle_sha256": "expected_semantic_bundle_sha256",
        "predicted_credit": "predicted_credit",
    }
    if any(pair[left] != commitment[right] for left, right in expected.items()):
        raise ValueError("V2.42.27 outer pair differs from committed campaign")
    if pair["protocol_sha256"] != protocol["outer_target_protocol_sha256"]:
        raise ValueError("V2.42.27 outer pair protocol differs from sequence")


def _build_reveal_receipt(
    *,
    protocol: Mapping[str, Any],
    commitment: Mapping[str, Any],
    launch: Mapping[str, Any],
    reservation: Mapping[str, Any],
    pair: Mapping[str, Any],
    protocol_file_sha256: str,
    commitment_file_sha256: str,
    launch_file_sha256: str,
    outer_reservation_file_sha256: str,
    outer_pair_file_sha256: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REVEAL_ROLE,
        "policy_id": POLICY_ID,
        "label_blind_control": True,
        "protocol_sha256": protocol["protocol_sha256"],
        "outer_target_protocol_sha256": protocol[
            "outer_target_protocol_sha256"
        ],
        "sequence_namespace_sha256": protocol["sequence_namespace_sha256"],
        "prediction_commitment_sha256": commitment["commitment_sha256"],
        "outer_launch_receipt_sha256": launch["launch_receipt_sha256"],
        "outer_reservation_receipt_sha256": reservation[
            "reservation_sha256"
        ],
        "prediction_freeze_sha256": commitment["prediction_freeze_sha256"],
        "outer_pair_sha256": pair["pair_sha256"],
        "task_cluster_ref_sha256": pair["task_cluster_ref_sha256"],
        "trajectory_ref_sha256": pair["trajectory_ref_sha256"],
        "context": pair["context"],
        "action": pair["action"],
        "continuation_policy_sha256": pair["continuation_policy_sha256"],
        "outer_job_manifest_sha256": pair["outer_job_manifest_sha256"],
        "semantic_bundle_sha256": pair["semantic_bundle_sha256"],
        "outer_adapter_result_sha256": pair["outer_adapter_result_sha256"],
        "outer_source_receipt_sha256": pair["outer_source_receipt_sha256"],
        "outer_verified_contribution_sha256": pair[
            "outer_verified_contribution_sha256"
        ],
        "outer_prediction_freeze_sha256": pair[
            "outer_prediction_freeze_sha256"
        ],
        "outer_evaluator_provenance_receipt_sha256": pair[
            "outer_evaluator_provenance_receipt_sha256"
        ],
        "outer_evaluated_terminal_receipt_sha256s": copy.deepcopy(
            pair["outer_evaluated_terminal_receipt_sha256s"]
        ),
        "outer_contribution_record_sha256s": copy.deepcopy(
            pair["outer_contribution_record_sha256s"]
        ),
        "outer_replicate_aggregate_sha256": pair[
            "outer_replicate_aggregate_sha256"
        ],
        "launch_challenge_sha256": launch["launch_challenge_sha256"],
        "outer_output_namespace_sha256": launch[
            "outer_output_namespace_sha256"
        ],
        "sequence_state": "outer_target_revealed",
        "predecessor_state": "outer_pair_materialized",
        "stage_sequence": [
            "prediction_committed",
            "outer_launch_opened",
            "outer_root_reserved",
            "outer_pair_materialized",
            "outer_target_revealed",
        ],
        "protocol_file_sha256": protocol_file_sha256,
        "commitment_file_sha256": commitment_file_sha256,
        "launch_file_sha256": launch_file_sha256,
        "outer_reservation_file_sha256": outer_reservation_file_sha256,
        "outer_pair_file_sha256": outer_pair_file_sha256,
        "create_exclusive_stage_files": True,
        "fresh_sequence_directory_created_at_commit": True,
        "fresh_outer_root_absent_until_launch": True,
        "outer_pair_file_inside_reserved_root": True,
        "prediction_commitment_precedes_launch_in_store_state_machine": True,
        "launch_precedes_pair_publication_in_store_state_machine": True,
        "pair_precedes_reveal_publication_in_store_state_machine": True,
        "repository_commit_launch_reveal_order_enforced": True,
        "outer_pair_native_launch_challenge_binding_present": False,
        "external_target_precomputation_excluded": False,
        "trusted_physical_wall_clock_used": False,
        "physical_wall_clock_creation_order_independently_proven": False,
        "hostile_concurrent_filesystem_mutation_excluded": False,
        "independent_append_only_or_transparency_service_used": False,
        "store_api_execution_independently_attested": False,
        "offline_self_consistent_chain_fabrication_cryptographically_excluded": False,
        "local_file_and_directory_fsync_used": True,
        "semantic_or_distributional_ood_independently_assessed": False,
        "formal_gate2b_evaluation_authorized": False,
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control": False,
        "post_prediction_outer_target_contribution_available_to_reveal_validator": True,
        "outer_target_used_for_runtime_routing_or_same_forward_pass": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
        "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }
    value["reveal_sha256"] = object_sha256(value)
    return value


def validate_reveal_receipt(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    commitment: Mapping[str, Any] | None = None,
    launch: Mapping[str, Any] | None = None,
    reservation: Mapping[str, Any] | None = None,
    pair: Mapping[str, Any] | None = None,
) -> None:
    if any(item is None for item in (protocol, commitment, launch, reservation, pair)):
        raise ValueError(
            "V2.42.27 reveal validation requires the complete predecessor chain"
        )
    reveal = _exact_mapping(value, keys=REVEAL_KEYS, label="reveal receipt")
    hash_fields = (
        "protocol_sha256",
        "outer_target_protocol_sha256",
        "sequence_namespace_sha256",
        "prediction_commitment_sha256",
        "outer_launch_receipt_sha256",
        "outer_reservation_receipt_sha256",
        "prediction_freeze_sha256",
        "outer_pair_sha256",
        "task_cluster_ref_sha256",
        "trajectory_ref_sha256",
        "continuation_policy_sha256",
        "outer_job_manifest_sha256",
        "semantic_bundle_sha256",
        "outer_adapter_result_sha256",
        "outer_source_receipt_sha256",
        "outer_verified_contribution_sha256",
        "outer_prediction_freeze_sha256",
        "outer_evaluator_provenance_receipt_sha256",
        "outer_replicate_aggregate_sha256",
        "launch_challenge_sha256",
        "outer_output_namespace_sha256",
        "protocol_file_sha256",
        "commitment_file_sha256",
        "launch_file_sha256",
        "outer_reservation_file_sha256",
        "outer_pair_file_sha256",
    )
    _hash_list(
        reveal.get("outer_evaluated_terminal_receipt_sha256s"),
        label="outer evaluated receipts",
        length=6,
    )
    _hash_list(
        reveal.get("outer_contribution_record_sha256s"),
        label="outer contribution records",
        length=3,
    )
    required_true = (
        "create_exclusive_stage_files",
        "fresh_sequence_directory_created_at_commit",
        "fresh_outer_root_absent_until_launch",
        "outer_pair_file_inside_reserved_root",
        "prediction_commitment_precedes_launch_in_store_state_machine",
        "launch_precedes_pair_publication_in_store_state_machine",
        "pair_precedes_reveal_publication_in_store_state_machine",
        "repository_commit_launch_reveal_order_enforced",
        "post_prediction_outer_target_contribution_available_to_reveal_validator",
        "local_file_and_directory_fsync_used",
    )
    required_false = (
        "outer_pair_native_launch_challenge_binding_present",
        "external_target_precomputation_excluded",
        "trusted_physical_wall_clock_used",
        "physical_wall_clock_creation_order_independently_proven",
        "hostile_concurrent_filesystem_mutation_excluded",
        "independent_append_only_or_transparency_service_used",
        "store_api_execution_independently_attested",
        "offline_self_consistent_chain_fabrication_cryptographically_excluded",
        "semantic_or_distributional_ood_independently_assessed",
        "formal_gate2b_evaluation_authorized",
        "benchmark_category_question_type_mapping_gold_or_raw_evaluator_payload_available_to_control",
        "outer_target_used_for_runtime_routing_or_same_forward_pass",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
    )
    if (
        reveal.get("artifact_version") != 1
        or reveal.get("role") != REVEAL_ROLE
        or reveal.get("policy_id") != POLICY_ID
        or reveal.get("label_blind_control") is not True
        or any(not is_sha256(reveal.get(key)) for key in hash_fields)
        or not _valid_context_action(reveal.get("context"), reveal.get("action"))
        or reveal.get("sequence_state") != "outer_target_revealed"
        or reveal.get("predecessor_state") != "outer_pair_materialized"
        or reveal.get("stage_sequence")
        != [
            "prediction_committed",
            "outer_launch_opened",
            "outer_root_reserved",
            "outer_pair_materialized",
            "outer_target_revealed",
        ]
        or any(reveal.get(key) is not True for key in required_true)
        or any(reveal.get(key) is not False for key in required_false)
        or not _sealed(reveal, seal_key="reveal_sha256")
    ):
        raise ValueError("V2.42.27 reveal receipt contract drifted")
    validate_commit_reveal_protocol(protocol)
    if any(
        reveal[left] != protocol[right]
        for left, right in (
            ("protocol_sha256", "protocol_sha256"),
            ("outer_target_protocol_sha256", "outer_target_protocol_sha256"),
            ("sequence_namespace_sha256", "sequence_namespace_sha256"),
        )
    ):
        raise ValueError("V2.42.27 reveal protocol binding drifted")
    validate_prediction_commitment(commitment, protocol=protocol)
    if any(
        reveal[left] != commitment[right]
        for left, right in (
            ("prediction_commitment_sha256", "commitment_sha256"),
            ("prediction_freeze_sha256", "prediction_freeze_sha256"),
        )
    ):
        raise ValueError("V2.42.27 reveal commitment binding drifted")
    validate_launch_receipt(launch, protocol=protocol, commitment=commitment)
    if any(
        reveal[left] != launch[right]
        for left, right in (
            ("outer_launch_receipt_sha256", "launch_receipt_sha256"),
            ("launch_challenge_sha256", "launch_challenge_sha256"),
            ("outer_output_namespace_sha256", "outer_output_namespace_sha256"),
        )
    ):
        raise ValueError("V2.42.27 reveal launch binding drifted")
    validate_outer_reservation_receipt(
        reservation, protocol=protocol, launch=launch
    )
    if (
        reveal["outer_reservation_receipt_sha256"]
        != reservation["reservation_sha256"]
    ):
        raise ValueError("V2.42.27 reveal reservation binding drifted")
    validate_independent_outer_target_pair(pair)
    expected = {
        "outer_pair_sha256": "pair_sha256",
        "task_cluster_ref_sha256": "task_cluster_ref_sha256",
        "trajectory_ref_sha256": "trajectory_ref_sha256",
        "context": "context",
        "action": "action",
        "continuation_policy_sha256": "continuation_policy_sha256",
        "outer_job_manifest_sha256": "outer_job_manifest_sha256",
        "semantic_bundle_sha256": "semantic_bundle_sha256",
        "outer_adapter_result_sha256": "outer_adapter_result_sha256",
        "outer_source_receipt_sha256": "outer_source_receipt_sha256",
        "outer_verified_contribution_sha256": "outer_verified_contribution_sha256",
        "outer_prediction_freeze_sha256": "outer_prediction_freeze_sha256",
        "outer_evaluator_provenance_receipt_sha256": "outer_evaluator_provenance_receipt_sha256",
        "outer_evaluated_terminal_receipt_sha256s": "outer_evaluated_terminal_receipt_sha256s",
        "outer_contribution_record_sha256s": "outer_contribution_record_sha256s",
        "outer_replicate_aggregate_sha256": "outer_replicate_aggregate_sha256",
    }
    if any(reveal[left] != pair[right] for left, right in expected.items()):
        raise ValueError("V2.42.27 reveal pair binding drifted")
    _validate_pair_binding(
        pair=pair, protocol=protocol, commitment=commitment
    )


class CreditOuterSequenceStore:
    """A fixed-path, create-exclusive store for one content-free sequence."""

    def __init__(self, *, root: Path, sequence_namespace_sha256: str) -> None:
        namespace = _sha256(sequence_namespace_sha256, label="sequence namespace")
        candidate = root.absolute()
        if (
            root.is_symlink()
            or not root.is_dir()
            or root.resolve(strict=True) != candidate
        ):
            raise ValueError("V2.42.27 store root is not an ordinary directory")
        self.root = candidate
        self.namespace = namespace
        self.directory = self.root / namespace
        self.protocol_path = self.directory / PROTOCOL_FILE
        self.commitment_path = self.directory / COMMITMENT_FILE
        self.launch_path = self.directory / LAUNCH_FILE
        self.outer_directory = self.directory / OUTER_DIRECTORY
        self.outer_reservation_path = self.directory / OUTER_RESERVATION_FILE
        self.outer_pair_path = self.directory / OUTER_PAIR_FILE
        self.reveal_path = self.directory / REVEAL_FILE

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            CreditOuterSequenceStore._fsync_directory(path.parent)
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise

    @staticmethod
    def _read_object(path: Path) -> dict[str, Any]:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("V2.42.27 expected an ordinary stage file")
        if metadata.st_size > MAX_CONTROL_FILE_BYTES:
            raise ValueError("V2.42.27 stage file exceeds the control size cap")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or opened.st_dev != metadata.st_dev
                or opened.st_ino != metadata.st_ino
                or opened.st_size > MAX_CONTROL_FILE_BYTES
            ):
                raise ValueError("V2.42.27 stage file changed during open")
            payload = bytearray()
            while len(payload) <= MAX_CONTROL_FILE_BYTES:
                chunk = os.read(descriptor, min(65_536, MAX_CONTROL_FILE_BYTES + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
            if len(payload) > MAX_CONTROL_FILE_BYTES or os.read(descriptor, 1):
                raise ValueError("V2.42.27 stage file exceeds the control size cap")
            final = os.fstat(descriptor)
            if (
                final.st_dev != opened.st_dev
                or final.st_ino != opened.st_ino
                or final.st_size != opened.st_size
                or final.st_mtime_ns != opened.st_mtime_ns
                or final.st_ctime_ns != opened.st_ctime_ns
            ):
                raise ValueError("V2.42.27 stage file changed during read")
        finally:
            os.close(descriptor)
        value = json.loads(
            bytes(payload).decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
        if not isinstance(value, dict):
            raise ValueError("V2.42.27 stage file is not a JSON object")
        return value

    @staticmethod
    def _file_sha256(path: Path) -> str:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("V2.42.27 expected an ordinary stage file")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        digest = hashlib.sha256()
        size = 0
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or opened.st_dev != metadata.st_dev
                or opened.st_ino != metadata.st_ino
            ):
                raise ValueError("V2.42.27 stage file changed during hash open")
            while True:
                chunk = os.read(descriptor, 65_536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_CONTROL_FILE_BYTES:
                    raise ValueError(
                        "V2.42.27 stage file exceeds the control size cap"
                    )
                digest.update(chunk)
            final = os.fstat(descriptor)
            if (
                final.st_dev != opened.st_dev
                or final.st_ino != opened.st_ino
                or final.st_size != opened.st_size
                or final.st_mtime_ns != opened.st_mtime_ns
                or final.st_ctime_ns != opened.st_ctime_ns
            ):
                raise ValueError("V2.42.27 stage file changed during hash")
        finally:
            os.close(descriptor)
        return digest.hexdigest()

    @staticmethod
    def _require_entries(directory: Path, expected: set[Path]) -> None:
        if set(directory.iterdir()) != expected:
            raise ValueError("V2.42.27 stage directory contains residue")

    def _outer_namespace_sha256(self) -> str:
        return object_sha256(
            {
                "sequence_namespace_sha256": self.namespace,
                "outer_relative_path": str(OUTER_DIRECTORY),
            }
        )

    def _require_sequence_directory(self) -> None:
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise ValueError("V2.42.27 sequence directory is absent or nonordinary")
        if self.directory.resolve(strict=True) != self.directory.absolute():
            raise ValueError("V2.42.27 sequence directory resolves outside the store")

    def _load_protocol(self) -> dict[str, Any]:
        value = self._read_object(self.protocol_path)
        validate_commit_reveal_protocol(value)
        if value["sequence_namespace_sha256"] != self.namespace:
            raise ValueError("V2.42.27 protocol namespace drifted")
        return value

    def _load_commitment(self, protocol: Mapping[str, Any]) -> dict[str, Any]:
        value = self._read_object(self.commitment_path)
        validate_prediction_commitment(value, protocol=protocol)
        return value

    def _load_launch(
        self, protocol: Mapping[str, Any], commitment: Mapping[str, Any]
    ) -> dict[str, Any]:
        value = self._read_object(self.launch_path)
        validate_launch_receipt(value, protocol=protocol, commitment=commitment)
        return value

    def _load_reservation(
        self, protocol: Mapping[str, Any], launch: Mapping[str, Any]
    ) -> dict[str, Any]:
        value = self._read_object(self.outer_reservation_path)
        validate_outer_reservation_receipt(
            value, protocol=protocol, launch=launch
        )
        return value

    def _validate_outer_directory(self) -> None:
        metadata = self.outer_directory.lstat()
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("V2.42.27 outer root is absent or nonordinary")
        if self.outer_directory.resolve(strict=True) != self.outer_directory.absolute():
            raise ValueError("V2.42.27 outer root resolves outside the sequence")

    def commit(
        self,
        *,
        protocol: Mapping[str, Any],
        prediction_freeze: Mapping[str, Any],
        outer_seed_schedule_sha256: str,
        outer_execution_contract_sha256: str,
        outer_evaluator_protocol_sha256: str,
    ) -> dict[str, Any]:
        """Create a fresh sequence and publish the prediction commitment."""

        validate_commit_reveal_protocol(protocol)
        validate_credit_prediction_freeze(prediction_freeze)
        if protocol["sequence_namespace_sha256"] != self.namespace:
            raise ValueError("V2.42.27 store and protocol namespaces differ")
        if self.directory.exists() or self.directory.is_symlink():
            raise FileExistsError("V2.42.27 sequence namespace is not pristine")
        os.mkdir(self.directory, 0o700)
        self._fsync_directory(self.root)
        commitment = _build_prediction_commitment(
            protocol=protocol,
            prediction_freeze=prediction_freeze,
            commit_nonce_sha256=hashlib.sha256(os.urandom(32)).hexdigest(),
            outer_output_namespace_sha256=self._outer_namespace_sha256(),
            outer_seed_schedule_sha256=_sha256(
                outer_seed_schedule_sha256, label="outer seed schedule"
            ),
            outer_execution_contract_sha256=_sha256(
                outer_execution_contract_sha256, label="outer execution contract"
            ),
            outer_evaluator_protocol_sha256=_sha256(
                outer_evaluator_protocol_sha256, label="outer evaluator protocol"
            ),
        )
        validate_prediction_commitment(
            commitment, protocol=protocol, prediction_freeze=prediction_freeze
        )
        self._publish_new(self.protocol_path, protocol)
        self._publish_new(self.commitment_path, commitment)
        self._require_entries(
            self.directory, {self.protocol_path, self.commitment_path}
        )
        return commitment

    def open_launch(self, *, launch_request_sha256: str) -> dict[str, Any]:
        """Publish launch intent, then reserve the previously absent outer root."""

        self._require_sequence_directory()
        protocol = self._load_protocol()
        commitment = self._load_commitment(protocol)
        self._require_entries(
            self.directory, {self.protocol_path, self.commitment_path}
        )
        if any(
            path.exists() or path.is_symlink()
            for path in (
                self.launch_path,
                self.outer_directory,
                self.outer_reservation_path,
                self.outer_pair_path,
                self.reveal_path,
            )
        ):
            raise FileExistsError("V2.42.27 launch boundary is not pristine")
        launch = _build_launch_receipt(
            protocol=protocol,
            commitment=commitment,
            launch_request_sha256=_sha256(
                launch_request_sha256, label="launch request"
            ),
            launch_challenge_sha256=hashlib.sha256(os.urandom(32)).hexdigest(),
        )
        validate_launch_receipt(
            launch, protocol=protocol, commitment=commitment
        )
        self._publish_new(self.launch_path, launch)
        os.mkdir(self.outer_directory, 0o700)
        self._fsync_directory(self.directory)
        reservation = _build_outer_reservation_receipt(
            protocol=protocol,
            launch=launch,
            reservation_nonce_sha256=hashlib.sha256(os.urandom(32)).hexdigest(),
        )
        validate_outer_reservation_receipt(
            reservation, protocol=protocol, launch=launch
        )
        self._publish_new(self.outer_reservation_path, reservation)
        return launch

    def publish_outer_pair(self, *, pair: Mapping[str, Any]) -> dict[str, Any]:
        """Materialize one V2.42.26 pair inside the launch-reserved root."""

        self._require_sequence_directory()
        protocol = self._load_protocol()
        commitment = self._load_commitment(protocol)
        launch = self._load_launch(protocol, commitment)
        self._validate_outer_directory()
        self._load_reservation(protocol, launch)
        self._require_entries(
            self.directory,
            {
                self.protocol_path,
                self.commitment_path,
                self.launch_path,
                self.outer_directory,
            },
        )
        if self.reveal_path.exists() or self.reveal_path.is_symlink():
            raise FileExistsError("V2.42.27 reveal already exists")
        if self.outer_pair_path.exists() or self.outer_pair_path.is_symlink():
            raise FileExistsError("V2.42.27 outer pair already exists")
        if set(self.outer_directory.iterdir()) != {self.outer_reservation_path}:
            raise ValueError("V2.42.27 outer root contains uncommitted residue")
        copied = copy.deepcopy(dict(pair))
        _validate_pair_binding(
            pair=copied, protocol=protocol, commitment=commitment
        )
        self._publish_new(self.outer_pair_path, copied)
        return copied

    def reveal(self) -> dict[str, Any]:
        """Validate the full predecessor chain and publish the final reveal."""

        self._require_sequence_directory()
        protocol = self._load_protocol()
        commitment = self._load_commitment(protocol)
        launch = self._load_launch(protocol, commitment)
        if self.reveal_path.exists() or self.reveal_path.is_symlink():
            raise FileExistsError("V2.42.27 reveal already exists")
        self._validate_outer_directory()
        reservation = self._load_reservation(protocol, launch)
        self._require_entries(
            self.directory,
            {
                self.protocol_path,
                self.commitment_path,
                self.launch_path,
                self.outer_directory,
            },
        )
        if set(self.outer_directory.iterdir()) != {
            self.outer_reservation_path,
            self.outer_pair_path,
        }:
            raise ValueError("V2.42.27 outer root contains uncommitted residue")
        pair = self._read_object(self.outer_pair_path)
        _validate_pair_binding(
            pair=pair, protocol=protocol, commitment=commitment
        )
        reveal = _build_reveal_receipt(
            protocol=protocol,
            commitment=commitment,
            launch=launch,
            reservation=reservation,
            pair=pair,
            protocol_file_sha256=self._file_sha256(self.protocol_path),
            commitment_file_sha256=self._file_sha256(self.commitment_path),
            launch_file_sha256=self._file_sha256(self.launch_path),
            outer_reservation_file_sha256=self._file_sha256(
                self.outer_reservation_path
            ),
            outer_pair_file_sha256=self._file_sha256(self.outer_pair_path),
        )
        validate_reveal_receipt(
            reveal,
            protocol=protocol,
            commitment=commitment,
            launch=launch,
            reservation=reservation,
            pair=pair,
        )
        self._publish_new(self.reveal_path, reveal)
        return reveal

    def validate_complete_sequence(self) -> dict[str, Any]:
        """Replay a completed store without mutating it."""

        self._require_sequence_directory()
        protocol = self._load_protocol()
        commitment = self._load_commitment(protocol)
        launch = self._load_launch(protocol, commitment)
        self._validate_outer_directory()
        reservation = self._load_reservation(protocol, launch)
        self._require_entries(
            self.directory,
            {
                self.protocol_path,
                self.commitment_path,
                self.launch_path,
                self.outer_directory,
                self.reveal_path,
            },
        )
        if set(self.outer_directory.iterdir()) != {
            self.outer_reservation_path,
            self.outer_pair_path,
        }:
            raise ValueError("V2.42.27 outer root contains uncommitted residue")
        pair = self._read_object(self.outer_pair_path)
        _validate_pair_binding(
            pair=pair, protocol=protocol, commitment=commitment
        )
        reveal = self._read_object(self.reveal_path)
        validate_reveal_receipt(
            reveal,
            protocol=protocol,
            commitment=commitment,
            launch=launch,
            reservation=reservation,
            pair=pair,
        )
        file_bindings = {
            "protocol_file_sha256": self.protocol_path,
            "commitment_file_sha256": self.commitment_path,
            "launch_file_sha256": self.launch_path,
            "outer_reservation_file_sha256": self.outer_reservation_path,
            "outer_pair_file_sha256": self.outer_pair_path,
        }
        if any(
            reveal[field] != self._file_sha256(path)
            for field, path in file_bindings.items()
        ):
            raise ValueError("V2.42.27 reveal file binding drifted")
        return reveal
