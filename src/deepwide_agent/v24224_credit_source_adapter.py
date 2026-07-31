"""V2.41.23 receipt-graph adapter for V2.42.23 verified credit.

V2.42.23 deliberately accepts only content-free hashes, bounded terminal
contributions, and validity flags.  That interface is safe but, by itself,
cannot prove that a caller derived those fields from the true-continuation
campaign.  This build-only adapter closes the mechanical part of that gap.

It validates one exact V2.41.23 job-manifest bundle, all six post-terminal
evaluator receipts and their terminal-state hashes, all three recomputed
matched-branch contribution records, and the enriched replicate aggregate.
Only then does it construct the V2.42.23 verified-contribution record.  Caller
booleans cannot choose the sign or validity path.

The adapter proves contract-level identity and replay closure, not semantic or
distributional OOD validity.  Its source receipt states that limitation, and
both production and credit-training authority remain frozen false.  The module
has no file, environment, client, network, process, or benchmark-launch API and
is not imported by the active forward path.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .v24121_continuation import object_sha256
from .v24123_release import (
    EVALUATED_TERMINAL_ROLE,
    REPLICATE_AGGREGATE_ROLE,
    REPLICATE_IDS,
    aggregate_replicate_contributions,
    contribution_record,
    is_sha256,
    validate_evaluated_terminal_receipt,
    validate_job_manifest,
    validate_replicate_aggregate,
)
from .v24223_sign_preserving_credit import (
    build_verified_terminal_contribution,
    validate_verified_terminal_contribution,
)


POLICY_ID = "v24224_v24123_receipt_graph_credit_source_adapter_v1"
SOURCE_RECEIPT_ROLE = "v24224_verified_credit_source_receipt"
ADAPTER_RESULT_ROLE = "v24224_verified_credit_adapter_result"
INTERVENTION_VALIDITY_SCOPE = (
    "v24123_exact_receipt_graph_and_same_checkpoint_contract_only"
)
V24223_OOD_FLAG_SCOPE = (
    "v24123_contract_state_only_not_semantic_or_distributional_ood"
)
PRODUCTION_PACKAGE_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False
FORBIDDEN_TERMINAL_METADATA_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "benchmark_category",
        "benchmark_subset",
        "category",
        "evaluator",
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

TERMINAL_STATE_RECORD_KEYS = frozenset(
    {"replicate_id", "branch_role", "terminal_state"}
)
JOB_MANIFEST_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "label_blind",
        "capture_design_id",
        "target_manifest_sha256",
        "continuation_policy_sha256",
        "candidate_pipeline_version",
        "candidate_state_schema_version",
        "candidate_runtime_config_sha256",
        "replicate_ids",
        "provider_seed_supported",
        "provider_seed",
        "phase_order",
        "bundles",
        "excluded_targets",
        "eligible_bundle_count",
        "excluded_target_count",
        "task_cluster_is_statistical_unit",
        "subject_level_fallback_allowed",
        "mapping_gold_category_evaluator_or_score_read",
        "controller_or_training_authorized",
        "manifest_sha256",
    }
)
JOB_BUNDLE_KEYS = frozenset(
    {
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
        "bundle_sha256",
        "opaque_id",
        "checkpoint_path",
        "target_binding",
        "target_binding_sha256",
        "pre_action_features",
        "pre_action_features_sha256",
        "replicate_ids",
        "branch_order_by_replicate",
        "provider_seed_supported",
        "provider_seed",
        "eligible",
        "mapping_gold_category_evaluator_or_score_read",
    }
)
PREDICTION_FREEZE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "bundle_sha256",
        "job_manifest_sha256",
        "replicate_action_observation_sha256s",
        "replicate_branch_adapter_receipt_sha256s",
        "terminal_receipt_sha256s",
        "prediction_values_emitted",
        "evaluator_read",
        "created_at_unix",
        "seal_sha256",
    }
)
EVALUATOR_PROVENANCE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "bundle_sha256",
        "prediction_freeze_sha256",
        "all_six_predictions_frozen_before_evaluator_material_read",
        "live_provenance",
        "mapping_gold_category_evaluator_or_score_read_scope",
        "receipt_sha256",
    }
)
SOURCE_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "phase",
        "label_blind_forward",
        "job_manifest_sha256",
        "bundle_sha256",
        "task_cluster_ref_sha256",
        "partition_role",
        "context",
        "action",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "continuation_policy_sha256",
        "evaluator_protocol_sha256",
        "prediction_freeze_sha256",
        "evaluator_provenance_receipt_sha256",
        "evaluated_terminal_receipt_sha256s",
        "terminal_state_sha256s",
        "contribution_record_sha256s",
        "replicate_aggregate_sha256",
        "replicate_ids",
        "replicate_signed_terminal_contributions",
        "mean_signed_terminal_contribution",
        "all_six_evaluated_terminal_receipts_validated",
        "all_six_terminal_state_hashes_matched",
        "all_three_contribution_records_recomputed",
        "replicate_aggregate_recomputed",
        "same_state_matched_continuation_derived",
        "post_terminal_evaluator_join_derived",
        "prediction_freeze_artifact_validated",
        "post_freeze_evaluator_provenance_binding_validated",
        "failure_as_unit_loss_enforced",
        "contract_intervention_valid",
        "contract_state_overlap_valid",
        "contract_ood_detected",
        "semantic_or_distributional_ood_independently_assessed",
        "evaluator_live_provenance_independently_replayed",
        "intervention_validity_scope",
        "terminal_states_hashed_and_shadow_snapshots_examined",
        "terminal_state_content_embedded_in_receipt",
        "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "active_forward_imported",
        "production_package_authorized",
        "credit_training_authorized",
        "receipt_sha256",
    }
)
ADAPTER_RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "source_receipt",
        "verified_contribution",
        "v24223_ood_flag_scope",
        "semantic_or_distributional_ood_independently_assessed",
        "production_package_authorized",
        "credit_training_authorized",
        "adapter_result_sha256",
    }
)


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.24 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    unsigned = copy.deepcopy(dict(value))
    seal = unsigned.pop(seal_key, None)
    return is_sha256(seal) and seal == object_sha256(unsigned)


def _v24123_artifact_sha256(value: Mapping[str, Any]) -> str:
    """Hash the exact pretty-JSON bytes used by V2.41.23 ``json_bytes``."""

    return hashlib.sha256(
        (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    ).hexdigest()


def _bounded_contribution(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("V2.42.24 contribution is not numeric")
    number = float(value)
    if not math.isfinite(number) or not -1.0 <= number <= 1.0:
        raise ValueError("V2.42.24 contribution is outside [-1,1]")
    return number


def _reject_forbidden_terminal_metadata(value: object) -> None:
    if isinstance(value, Mapping):
        hits = {
            str(key).casefold() for key in value
        }.intersection(FORBIDDEN_TERMINAL_METADATA_KEYS)
        if hits:
            raise ValueError(
                "V2.42.24 terminal state contains evaluator-only metadata: "
                + ",".join(sorted(hits))
            )
        for child in value.values():
            _reject_forbidden_terminal_metadata(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            _reject_forbidden_terminal_metadata(child)


def _manifest_bundle(
    job_manifest: Mapping[str, Any], *, bundle_sha256: str
) -> dict[str, Any]:
    _exact_mapping(job_manifest, keys=JOB_MANIFEST_KEYS, label="job manifest")
    validate_job_manifest(dict(job_manifest))
    if not is_sha256(bundle_sha256):
        raise ValueError("V2.42.24 bundle reference is not a SHA-256")
    matches = [
        row
        for row in job_manifest["bundles"]
        if isinstance(row, dict) and row.get("bundle_sha256") == bundle_sha256
    ]
    if (
        len(matches) != 1
        or matches[0].get("eligible") is not True
        or set(matches[0]) != JOB_BUNDLE_KEYS
    ):
        raise ValueError("V2.42.24 bundle is absent, duplicated, or ineligible")
    return copy.deepcopy(matches[0])


def _ordered_evaluated_receipts(
    values: Sequence[Mapping[str, Any]],
    *,
    job_manifest_sha256: str,
    bundle: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or len(values) != 2 * len(REPLICATE_IDS):
        raise ValueError("V2.42.24 requires exactly six evaluated receipts")
    indexed: dict[tuple[int, str], dict[str, Any]] = {}
    for raw in values:
        if not isinstance(raw, Mapping):
            raise ValueError("V2.42.24 evaluated receipt is not a mapping")
        value = copy.deepcopy(dict(raw))
        validate_evaluated_terminal_receipt(value)
        replicate = value.get("replicate_id")
        role = value.get("branch_role")
        key = (replicate, role)
        if (
            value.get("role") != EVALUATED_TERMINAL_ROLE
            or replicate not in REPLICATE_IDS
            or isinstance(replicate, bool)
            or role not in {"no_op", "action"}
            or key in indexed
            or value.get("job_manifest_sha256") != job_manifest_sha256
            or value.get("source_checkpoint_sha256")
            != bundle["source_checkpoint_sha256"]
            or value.get("shadow_projection_sha256")
            != bundle["shadow_projection_sha256"]
            or value.get("continuation_policy_sha256")
            != bundle["continuation_policy_sha256"]
            or value.get("evaluator_joined_post_terminal_only") is not True
            or value.get("official_score_used_as_credit_label") is not False
            or value.get("model_projection_used_as_label") is not False
            or value.get("controller_or_training_authorized") is True
        ):
            raise ValueError("V2.42.24 evaluated receipt identity drifted")
        indexed[key] = value
    expected = {
        (replicate, role)
        for replicate in REPLICATE_IDS
        for role in ("no_op", "action")
    }
    if set(indexed) != expected:
        raise ValueError("V2.42.24 evaluated receipt matrix is incomplete")
    ordered = [
        indexed[(replicate, role)]
        for replicate in REPLICATE_IDS
        for role in ("no_op", "action")
    ]
    evaluator_protocols = {
        value["evaluator_protocol_sha256"] for value in ordered
    }
    if len(evaluator_protocols) != 1:
        raise ValueError("V2.42.24 evaluator protocol differs across branches")
    return ordered


def _ordered_terminal_states(
    values: Sequence[Mapping[str, Any]],
    *,
    evaluated_receipts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or len(values) != 2 * len(REPLICATE_IDS):
        raise ValueError("V2.42.24 requires exactly six terminal states")
    receipt_index = {
        (value["replicate_id"], value["branch_role"]): value
        for value in evaluated_receipts
    }
    indexed: dict[tuple[int, str], dict[str, Any]] = {}
    for raw in values:
        row = _exact_mapping(
            raw, keys=TERMINAL_STATE_RECORD_KEYS, label="terminal state record"
        )
        replicate = row.get("replicate_id")
        role = row.get("branch_role")
        state = row.get("terminal_state")
        _reject_forbidden_terminal_metadata(state)
        key = (replicate, role)
        if (
            replicate not in REPLICATE_IDS
            or isinstance(replicate, bool)
            or role not in {"no_op", "action"}
            or not isinstance(state, Mapping)
            or key in indexed
            or key not in receipt_index
            or object_sha256(state)
            != receipt_index[key]["terminal_state_sha256"]
        ):
            raise ValueError("V2.42.24 terminal state binding drifted")
        indexed[key] = copy.deepcopy(dict(state))
    expected = set(receipt_index)
    if set(indexed) != expected:
        raise ValueError("V2.42.24 terminal state matrix is incomplete")
    return [
        indexed[(replicate, role)]
        for replicate in REPLICATE_IDS
        for role in ("no_op", "action")
    ]


def _validated_freeze_and_provenance(
    *,
    prediction_freeze: Mapping[str, Any],
    evaluator_provenance_receipt: Mapping[str, Any],
    job_manifest_sha256: str,
    bundle: Mapping[str, Any],
    evaluated_receipts: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    freeze = copy.deepcopy(
        dict(
            _exact_mapping(
                prediction_freeze,
                keys=PREDICTION_FREEZE_KEYS,
                label="prediction freeze",
            )
        )
    )
    provenance = copy.deepcopy(
        dict(
            _exact_mapping(
                evaluator_provenance_receipt,
                keys=EVALUATOR_PROVENANCE_KEYS,
                label="evaluator provenance receipt",
            )
        )
    )
    ordered = sorted(
        evaluated_receipts,
        key=lambda value: (
            int(value["replicate_id"]),
            0 if value["branch_role"] == "no_op" else 1,
        ),
    )
    action_observations = [
        next(
            value["action_observation_sha256"]
            for value in ordered
            if value["replicate_id"] == replicate
        )
        for replicate in REPLICATE_IDS
    ]
    branch_adapters = [
        next(
            value["branch_adapter_receipt_sha256"]
            for value in ordered
            if value["replicate_id"] == replicate
        )
        for replicate in REPLICATE_IDS
    ]
    receipt_index = {
        (value["replicate_id"], value["branch_role"]): value
        for value in ordered
    }
    parent_terminal_receipts = [
        receipt_index[(replicate, role)][
            "parent_v24122_terminal_receipt_sha256"
        ]
        for replicate in REPLICATE_IDS
        for role in bundle["branch_order_by_replicate"][str(replicate)]
    ]
    created = freeze.get("created_at_unix")
    if (
        freeze.get("artifact_version") != 1
        or freeze.get("role") != "v24123_bundle_prediction_freeze"
        or freeze.get("bundle_sha256") != bundle["bundle_sha256"]
        or freeze.get("job_manifest_sha256") != job_manifest_sha256
        or freeze.get("replicate_action_observation_sha256s")
        != action_observations
        or freeze.get("replicate_branch_adapter_receipt_sha256s")
        != branch_adapters
        or freeze.get("terminal_receipt_sha256s")
        != parent_terminal_receipts
        or freeze.get("prediction_values_emitted") is not False
        or freeze.get("evaluator_read") is not False
        or isinstance(created, bool)
        or not isinstance(created, int)
        or created < 0
        or not _sealed(freeze, seal_key="seal_sha256")
    ):
        raise ValueError("V2.42.24 prediction freeze binding drifted")
    freeze_sha256 = _v24123_artifact_sha256(freeze)
    evaluator_provenance_sha256 = provenance.get("receipt_sha256")
    if (
        provenance.get("artifact_version") != 1
        or provenance.get("role")
        != "v24123_post_prediction_freeze_evaluator_provenance"
        or provenance.get("bundle_sha256") != bundle["bundle_sha256"]
        or provenance.get("prediction_freeze_sha256") != freeze_sha256
        or provenance.get(
            "all_six_predictions_frozen_before_evaluator_material_read"
        )
        is not True
        or provenance.get(
            "mapping_gold_category_evaluator_or_score_read_scope"
        )
        != "post_terminal_evaluator_join_only"
        or not isinstance(provenance.get("live_provenance"), Mapping)
        or not _sealed(provenance, seal_key="receipt_sha256")
        or any(
            value.get("prediction_freeze_sha256") != freeze_sha256
            or value.get("evaluator_provenance_receipt_sha256")
            != evaluator_provenance_sha256
            for value in ordered
        )
    ):
        raise ValueError("V2.42.24 evaluator provenance binding drifted")
    return freeze, provenance


def _recomputed_contributions(
    *,
    evaluated_receipts: Sequence[Mapping[str, Any]],
    terminal_states: Sequence[Mapping[str, Any]],
    supplied_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if (
        isinstance(supplied_records, (str, bytes))
        or len(supplied_records) != len(REPLICATE_IDS)
    ):
        raise ValueError("V2.42.24 requires exactly three contribution records")
    receipt_index = {
        (value["replicate_id"], value["branch_role"]): value
        for value in evaluated_receipts
    }
    state_keys = [
        (replicate, role)
        for replicate in REPLICATE_IDS
        for role in ("no_op", "action")
    ]
    if len(terminal_states) != len(state_keys):
        raise ValueError("V2.42.24 terminal state matrix is incomplete")
    state_index = dict(zip(state_keys, terminal_states))
    supplied_index: dict[int, dict[str, Any]] = {}
    for raw in supplied_records:
        if not isinstance(raw, Mapping):
            raise ValueError("V2.42.24 contribution record is not a mapping")
        value = copy.deepcopy(dict(raw))
        replicate = value.get("replicate_id")
        if (
            replicate not in REPLICATE_IDS
            or isinstance(replicate, bool)
            or replicate in supplied_index
        ):
            raise ValueError("V2.42.24 contribution replicate identity drifted")
        supplied_index[replicate] = value
    if set(supplied_index) != set(REPLICATE_IDS):
        raise ValueError("V2.42.24 contribution record matrix is incomplete")
    recomputed: list[dict[str, Any]] = []
    for replicate in REPLICATE_IDS:
        expected = contribution_record(
            receipt_index[(replicate, "no_op")],
            receipt_index[(replicate, "action")],
            no_op_terminal_state=state_index[(replicate, "no_op")],
            action_terminal_state=state_index[(replicate, "action")],
        )
        if supplied_index[replicate] != expected:
            raise ValueError(
                "V2.42.24 supplied contribution differs from receipt-graph replay"
            )
        if (
            expected.get("same_state_matched_continuation") is not True
            or expected.get("independent_replicate_not_provider_seed") is not True
            or expected.get("model_projection_used_as_label") is not False
            or expected.get("official_score_used_as_credit_label") is not False
            or expected.get("controller_or_training_authorized") is not False
        ):
            raise ValueError("V2.42.24 contribution safety boundary drifted")
        recomputed.append(expected)
    return recomputed


def _recomputed_aggregate(
    records: Sequence[Mapping[str, Any]],
    *,
    supplied_aggregate: Mapping[str, Any],
    job_manifest_sha256: str,
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    expected = aggregate_replicate_contributions(
        [copy.deepcopy(dict(value)) for value in records]
    )
    expected.pop("aggregate_sha256", None)
    ordered = sorted(records, key=lambda value: int(value["replicate_id"]))
    expected.update(
        {
            "bundle_sha256": bundle["bundle_sha256"],
            "task_cluster_ref_sha256": bundle["task_cluster_ref_sha256"],
            "partition_role": bundle["partition_role"],
            "context": bundle["context"],
            "action": bundle["action"],
            "job_manifest_sha256": job_manifest_sha256,
            "replicate_action_observation_sha256s": [
                value["action_observation_sha256"] for value in ordered
            ],
            "replicate_branch_adapter_receipt_sha256s": [
                value["branch_adapter_receipt_sha256"] for value in ordered
            ],
        }
    )
    expected["aggregate_sha256"] = object_sha256(expected)
    if dict(supplied_aggregate) != expected:
        raise ValueError(
            "V2.42.24 supplied aggregate differs from contribution replay"
        )
    if supplied_aggregate.get("role") != REPLICATE_AGGREGATE_ROLE:
        raise ValueError("V2.42.24 aggregate role drifted")
    validate_replicate_aggregate(
        expected,
        dict(bundle),
        job_manifest_sha256=job_manifest_sha256,
    )
    return expected


def _build_source_receipt(
    *,
    job_manifest_sha256: str,
    bundle: Mapping[str, Any],
    evaluated_receipts: Sequence[Mapping[str, Any]],
    prediction_freeze: Mapping[str, Any],
    evaluator_provenance_receipt: Mapping[str, Any],
    terminal_states: Sequence[Mapping[str, Any]],
    contribution_records: Sequence[Mapping[str, Any]],
    replicate_aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    contributions = [
        _bounded_contribution(value)
        for value in replicate_aggregate["replicate_signed_task_contribution"]
    ]
    mean = _bounded_contribution(
        replicate_aggregate["mean_signed_task_contribution"]
    )
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": SOURCE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "phase": "post_terminal_receipt_graph_validation_only",
        "label_blind_forward": True,
        "job_manifest_sha256": job_manifest_sha256,
        "bundle_sha256": bundle["bundle_sha256"],
        "task_cluster_ref_sha256": bundle["task_cluster_ref_sha256"],
        "partition_role": bundle["partition_role"],
        "context": bundle["context"],
        "action": bundle["action"],
        "source_checkpoint_sha256": bundle["source_checkpoint_sha256"],
        "shadow_projection_sha256": bundle["shadow_projection_sha256"],
        "continuation_policy_sha256": bundle["continuation_policy_sha256"],
        "evaluator_protocol_sha256": evaluated_receipts[0][
            "evaluator_protocol_sha256"
        ],
        "prediction_freeze_sha256": _v24123_artifact_sha256(prediction_freeze),
        "evaluator_provenance_receipt_sha256": (
            evaluator_provenance_receipt["receipt_sha256"]
        ),
        "evaluated_terminal_receipt_sha256s": [
            value["receipt_payload_sha256"] for value in evaluated_receipts
        ],
        "terminal_state_sha256s": [object_sha256(value) for value in terminal_states],
        "contribution_record_sha256s": [
            value["record_sha256"] for value in contribution_records
        ],
        "replicate_aggregate_sha256": replicate_aggregate["aggregate_sha256"],
        "replicate_ids": list(REPLICATE_IDS),
        "replicate_signed_terminal_contributions": contributions,
        "mean_signed_terminal_contribution": mean,
        "all_six_evaluated_terminal_receipts_validated": True,
        "all_six_terminal_state_hashes_matched": True,
        "all_three_contribution_records_recomputed": True,
        "replicate_aggregate_recomputed": True,
        "same_state_matched_continuation_derived": True,
        "post_terminal_evaluator_join_derived": True,
        "prediction_freeze_artifact_validated": True,
        "post_freeze_evaluator_provenance_binding_validated": True,
        "failure_as_unit_loss_enforced": True,
        "contract_intervention_valid": True,
        "contract_state_overlap_valid": True,
        "contract_ood_detected": False,
        "semantic_or_distributional_ood_independently_assessed": False,
        "evaluator_live_provenance_independently_replayed": False,
        "intervention_validity_scope": INTERVENTION_VALIDITY_SCOPE,
        "terminal_states_hashed_and_shadow_snapshots_examined": True,
        "terminal_state_content_embedded_in_receipt": False,
        "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "active_forward_imported": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "receipt_sha256": "",
    }
    receipt["receipt_sha256"] = object_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )
    validate_source_receipt(receipt)
    return receipt


def validate_source_receipt(value: object) -> None:
    receipt = _exact_mapping(
        value, keys=SOURCE_RECEIPT_KEYS, label="source receipt"
    )
    hash_fields = (
        "job_manifest_sha256",
        "bundle_sha256",
        "task_cluster_ref_sha256",
        "source_checkpoint_sha256",
        "shadow_projection_sha256",
        "continuation_policy_sha256",
        "evaluator_protocol_sha256",
        "prediction_freeze_sha256",
        "evaluator_provenance_receipt_sha256",
        "replicate_aggregate_sha256",
    )
    true_fields = (
        "label_blind_forward",
        "all_six_evaluated_terminal_receipts_validated",
        "all_six_terminal_state_hashes_matched",
        "all_three_contribution_records_recomputed",
        "replicate_aggregate_recomputed",
        "same_state_matched_continuation_derived",
        "post_terminal_evaluator_join_derived",
        "prediction_freeze_artifact_validated",
        "post_freeze_evaluator_provenance_binding_validated",
        "failure_as_unit_loss_enforced",
        "contract_intervention_valid",
        "contract_state_overlap_valid",
        "terminal_states_hashed_and_shadow_snapshots_examined",
    )
    false_fields = (
        "contract_ood_detected",
        "semantic_or_distributional_ood_independently_assessed",
        "evaluator_live_provenance_independently_replayed",
        "terminal_state_content_embedded_in_receipt",
        "mapping_gold_category_question_type_evaluator_payload_score_or_reward_available_to_forward",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "active_forward_imported",
        "production_package_authorized",
        "credit_training_authorized",
    )
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != SOURCE_RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("phase") != "post_terminal_receipt_graph_validation_only"
        or receipt.get("intervention_validity_scope")
        != INTERVENTION_VALIDITY_SCOPE
        or any(not is_sha256(receipt.get(key)) for key in hash_fields)
        or any(receipt.get(key) is not True for key in true_fields)
        or any(receipt.get(key) is not False for key in false_fields)
        or receipt.get("replicate_ids") != list(REPLICATE_IDS)
        or not _sealed(receipt, seal_key="receipt_sha256")
    ):
        raise ValueError("V2.42.24 source receipt header or seal is invalid")
    for key, length in (
        ("evaluated_terminal_receipt_sha256s", 6),
        ("terminal_state_sha256s", 6),
        ("contribution_record_sha256s", 3),
    ):
        values = receipt.get(key)
        if (
            not isinstance(values, list)
            or len(values) != length
            or any(not is_sha256(item) for item in values)
        ):
            raise ValueError(f"V2.42.24 {key} is invalid")
    contributions = receipt.get("replicate_signed_terminal_contributions")
    if not isinstance(contributions, list) or len(contributions) != 3:
        raise ValueError("V2.42.24 source contribution vector is invalid")
    numbers = [_bounded_contribution(value) for value in contributions]
    mean = _bounded_contribution(receipt.get("mean_signed_terminal_contribution"))
    if mean != round(sum(numbers) / len(numbers), 12):
        raise ValueError("V2.42.24 source contribution mean drifted")


def adapt_v24123_source_graph(
    *,
    job_manifest: Mapping[str, Any],
    bundle_sha256: str,
    evaluated_terminal_receipts: Sequence[Mapping[str, Any]],
    prediction_freeze: Mapping[str, Any],
    evaluator_provenance_receipt: Mapping[str, Any],
    terminal_state_records: Sequence[Mapping[str, Any]],
    contribution_records: Sequence[Mapping[str, Any]],
    replicate_aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the exact source graph and derive a V2.42.23 record."""

    if not isinstance(job_manifest, Mapping):
        raise ValueError("V2.42.24 job manifest is not a mapping")
    manifest = copy.deepcopy(dict(job_manifest))
    bundle = _manifest_bundle(manifest, bundle_sha256=bundle_sha256)
    manifest_sha = manifest["manifest_sha256"]
    receipts = _ordered_evaluated_receipts(
        evaluated_terminal_receipts,
        job_manifest_sha256=manifest_sha,
        bundle=bundle,
    )
    freeze, provenance = _validated_freeze_and_provenance(
        prediction_freeze=prediction_freeze,
        evaluator_provenance_receipt=evaluator_provenance_receipt,
        job_manifest_sha256=manifest_sha,
        bundle=bundle,
        evaluated_receipts=receipts,
    )
    states = _ordered_terminal_states(
        terminal_state_records, evaluated_receipts=receipts
    )
    records = _recomputed_contributions(
        evaluated_receipts=receipts,
        terminal_states=states,
        supplied_records=contribution_records,
    )
    aggregate = _recomputed_aggregate(
        records,
        supplied_aggregate=replicate_aggregate,
        job_manifest_sha256=manifest_sha,
        bundle=bundle,
    )
    source_receipt = _build_source_receipt(
        job_manifest_sha256=manifest_sha,
        bundle=bundle,
        evaluated_receipts=receipts,
        prediction_freeze=freeze,
        evaluator_provenance_receipt=provenance,
        terminal_states=states,
        contribution_records=records,
        replicate_aggregate=aggregate,
    )
    verified = build_verified_terminal_contribution(
        opaque_step_ref_sha256=source_receipt["receipt_sha256"],
        source_checkpoint_sha256=bundle["source_checkpoint_sha256"],
        continuation_policy_sha256=bundle["continuation_policy_sha256"],
        evaluator_protocol_sha256=source_receipt["evaluator_protocol_sha256"],
        intervention_protocol_sha256=manifest_sha,
        replicate_signed_terminal_contributions=source_receipt[
            "replicate_signed_terminal_contributions"
        ],
        terminal_outcome_verified=True,
        same_state_matched_continuation=True,
        intervention_valid=True,
        state_overlap_valid=True,
        ood_detected=False,
        prediction_closed_before_evaluator_join=True,
        evaluator_joined_post_terminal_only=True,
    )
    result: dict[str, Any] = {
        "artifact_version": 1,
        "role": ADAPTER_RESULT_ROLE,
        "policy_id": POLICY_ID,
        "source_receipt": source_receipt,
        "verified_contribution": verified,
        "v24223_ood_flag_scope": V24223_OOD_FLAG_SCOPE,
        "semantic_or_distributional_ood_independently_assessed": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "adapter_result_sha256": "",
    }
    result["adapter_result_sha256"] = object_sha256(
        {
            key: value
            for key, value in result.items()
            if key != "adapter_result_sha256"
        }
    )
    validate_adapter_result(result)
    return result


def validate_adapter_result(value: object) -> None:
    result = _exact_mapping(
        value, keys=ADAPTER_RESULT_KEYS, label="adapter result"
    )
    if (
        result.get("artifact_version") != 1
        or result.get("role") != ADAPTER_RESULT_ROLE
        or result.get("policy_id") != POLICY_ID
        or result.get("v24223_ood_flag_scope") != V24223_OOD_FLAG_SCOPE
        or result.get("semantic_or_distributional_ood_independently_assessed")
        is not False
        or result.get("production_package_authorized") is not False
        or result.get("credit_training_authorized") is not False
        or not _sealed(result, seal_key="adapter_result_sha256")
    ):
        raise ValueError("V2.42.24 adapter result header or seal is invalid")
    source = result.get("source_receipt")
    verified = result.get("verified_contribution")
    validate_source_receipt(source)
    validate_verified_terminal_contribution(verified)
    if (
        verified["opaque_step_ref_sha256"] != source["receipt_sha256"]
        or verified["source_checkpoint_sha256"]
        != source["source_checkpoint_sha256"]
        or verified["continuation_policy_sha256"]
        != source["continuation_policy_sha256"]
        or verified["evaluator_protocol_sha256"]
        != source["evaluator_protocol_sha256"]
        or verified["intervention_protocol_sha256"]
        != source["job_manifest_sha256"]
        or verified["replicate_signed_terminal_contributions"]
        != source["replicate_signed_terminal_contributions"]
        or verified["mean_signed_terminal_contribution"]
        != source["mean_signed_terminal_contribution"]
    ):
        raise ValueError("V2.42.24 V2.42.23 source binding drifted")
