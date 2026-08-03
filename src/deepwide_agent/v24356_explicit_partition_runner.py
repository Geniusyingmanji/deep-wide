"""Deadline/transport integration for the V2.43.55 explicit partition runtime."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import (
    DeadlineAwareGlobalModelSlotLimiter,
    validate_receipt as validate_slot_receipt,
)
from .v24316_deadline_search import (
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from .v24355_explicit_partition_runtime import (
    MAXIMUM_FETCH_SOURCES,
    run_v24355_task,
    validate_result,
)


POLICY_ID = "v24356_deadline_explicit_partition_runner_v1"
ENVELOPE_ROLE = "v24356_explicit_partition_task_envelope"
PRIVATE_SCOPE = [
    "opaque_id",
    "prediction",
    "proposal_page",
    "hidden_verifier_page",
    "semantic_projection",
    "candidate_value",
    "evidence_id",
    "model_proposal",
    "deterministic_gate_result",
]


@dataclass(frozen=True)
class IntegratedExplicitPartitionOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]


def _aligned_deadlines(model: Any, search: Any) -> bool:
    try:
        return (
            abs(float(model.absolute_deadline) - float(search.absolute_deadline))
            <= 1e-6
            and abs(
                float(model.cleanup_reserve_seconds)
                - float(search.cleanup_reserve_seconds)
            )
            <= 1e-6
            and abs(
                float(model.minimum_attempt_seconds)
                - float(search.minimum_attempt_seconds)
            )
            <= 1e-9
        )
    except (AttributeError, TypeError, ValueError):
        return False


def validate_cross_artifacts(
    result: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    expected_cap: int,
) -> None:
    validate_result(result)
    slot = validate_slot_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    health = validate_transport_health(transport_health)
    parent = result["parent_result"]
    core = parent["semantic_result"]["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    verifier = result["hidden_verifier_receipt"]
    if core_receipt["effect_accounting_complete"]:
        if (
            core_receipt["provider_model_requests"] != slot["acquisitions"]
            or core_receipt["pre_provider_model_rejections"]
            != slot["slot_timeouts"]
            or core_receipt["logical_model_admissions"]
            != slot["acquisitions"] + slot["slot_timeouts"]
            or core_receipt["provider_model_attempts"]
            != int(core["cost"]["model"]["attempts"])
        ):
            raise ValueError("V2.43.56 complete model conservation drifted")
    elif (
        core_receipt["unattributed_model_effects_lower_bound"]
        < slot["acquisitions"]
        or core_receipt["unattributed_model_attempts_lower_bound"]
        != int(core["cost"]["model"]["attempts"])
    ):
        raise ValueError("V2.43.56 incomplete model lower bound drifted")

    observed_fetch_effects = int(health["hard_fetch_helper_calls"]) + int(
        health["fetch_deadline_rejections"]
    )
    if (
        verifier["parent_model_requests"] != int(core["cost"]["model"]["requests"])
        or verifier["parent_fetch_calls"]
        != int(core["cost"]["search"]["fetch_calls"])
        or verifier["hidden_verifier_fetch_calls"]
        != verifier["partition_receipt"]["verifier_source_count"]
        or verifier["total_fetch_calls"]
        != verifier["parent_fetch_calls"]
        + verifier["hidden_verifier_fetch_calls"]
        or verifier["total_fetch_calls"] != observed_fetch_effects
        or verifier["total_fetch_calls"] > MAXIMUM_FETCH_SOURCES
    ):
        raise ValueError("V2.43.56 combined fetch conservation drifted")


def run_v24356_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: DeadlineAwareNativeSearchClient,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Any,
) -> IntegratedExplicitPartitionOutcome:
    visible = validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.43.56 requires the deadline-aware model limiter")
    if not isinstance(search, DeadlineAwareNativeSearchClient):
        raise ValueError("V2.43.56 requires the deadline-aware search transport")
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.43.56 model/search deadline identity drifted")
    result = run_v24355_task(
        visible,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    slot = model.receipt()
    health = search.transport_health()
    validate_cross_artifacts(
        result,
        model_slot_receipt=slot,
        transport_health=health,
        expected_cap=int(slot["slot_cap"]),
    )
    return IntegratedExplicitPartitionOutcome(result, slot, health)


def build_envelope(outcome: IntegratedExplicitPartitionOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "private_task_content_present": True,
        "private_task_content_scope": list(PRIVATE_SCOPE),
        "private_task_content_emitted_to_public_aggregate": False,
        "credential_or_privileged_evaluator_content_present": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    validate_envelope(value)
    return value


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "result",
        "model_slot_receipt",
        "transport_health",
        "private_task_content_present",
        "private_task_content_scope",
        "private_task_content_emitted_to_public_aggregate",
        "credential_or_privileged_evaluator_content_present",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "envelope_payload_sha256",
    }
    unsigned = dict(value)
    seal = unsigned.pop("envelope_payload_sha256", None)
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != ENVELOPE_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(value.get("result"), Mapping)
        or not isinstance(value.get("model_slot_receipt"), Mapping)
        or not isinstance(value.get("transport_health"), Mapping)
        or value.get("private_task_content_present") is not True
        or value.get("private_task_content_scope") != PRIVATE_SCOPE
        or value.get("private_task_content_emitted_to_public_aggregate") is not False
        or value.get("credential_or_privileged_evaluator_content_present") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.56 envelope identity drifted")
    slot = value["model_slot_receipt"]
    validate_cross_artifacts(
        value["result"],
        model_slot_receipt=slot,
        transport_health=value["transport_health"],
        expected_cap=int(slot.get("slot_cap", -1)),
    )
    return dict(value)


def validate_observed_bundle(
    value: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    expected_cap: int,
) -> dict[str, Any]:
    envelope = validate_envelope(value)
    slot = validate_slot_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    health = validate_transport_health(transport_health)
    if envelope["model_slot_receipt"] != slot or envelope["transport_health"] != health:
        raise ValueError("V2.43.56 independent receipt drifted from envelope")
    validate_cross_artifacts(
        envelope["result"],
        model_slot_receipt=slot,
        transport_health=health,
        expected_cap=expected_cap,
    )
    return envelope


__all__ = [
    "ENVELOPE_ROLE",
    "IntegratedExplicitPartitionOutcome",
    "POLICY_ID",
    "build_envelope",
    "run_v24356_task",
    "validate_cross_artifacts",
    "validate_envelope",
    "validate_observed_bundle",
]
