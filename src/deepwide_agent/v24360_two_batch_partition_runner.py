"""Deadline/transport integration for the V2.43.59 two-batch runtime."""

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
from .v24280_task_union_single_shot import (
    TaskUnionSingleShotMixin,
    validate_receipt as validate_single_shot_receipt,
)
from .v24355_explicit_partition_runtime import MAXIMUM_FETCH_SOURCES
from .v24356_explicit_partition_runner import _aligned_deadlines
from .v24358_two_batch_discovery import DISCOVERY_BATCH_COUNT, LOGICAL_QUERY_COUNT
from .v24359_two_batch_partition_runtime import (
    run_v24359_task,
    validate_result,
)


POLICY_ID = "v24360_deadline_two_batch_explicit_partition_runner_v1"
ENVELOPE_ROLE = "v24360_two_batch_explicit_partition_task_envelope"
PRIVATE_SCOPE = [
    "opaque_id",
    "prediction",
    "visible_query_batch",
    "source_url",
    "proposal_page",
    "hidden_verifier_page",
    "semantic_projection",
    "candidate_value",
    "evidence_id",
    "model_proposal",
    "deterministic_gate_result",
]


@dataclass(frozen=True)
class IntegratedTwoBatchPartitionOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]


class TwoBatchDeadlineAwareNativeSearchClient(
    TaskUnionSingleShotMixin, DeadlineAwareNativeSearchClient
):
    """Deadline-aware search with no recursive query-local split effects."""


def validate_cross_artifacts(
    result: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    expected_cap: int,
) -> None:
    validate_result(result)
    slot = validate_slot_receipt(dict(model_slot_receipt), expected_cap=expected_cap)
    health = validate_transport_health(transport_health)
    single_shot = dict(search_single_shot_receipt)
    validate_single_shot_receipt(single_shot)
    parent = result["explicit_partition_result"]
    core = parent["parent_result"]["semantic_result"]["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    runtime = parent["hidden_verifier_receipt"]
    discovery = result["two_batch_discovery_receipt"]
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
            raise ValueError("V2.43.60 complete model conservation drifted")
    elif (
        core_receipt["unattributed_model_effects_lower_bound"]
        < slot["acquisitions"]
        or core_receipt["unattributed_model_attempts_lower_bound"]
        != int(core["cost"]["model"]["attempts"])
    ):
        raise ValueError("V2.43.60 incomplete model lower bound drifted")

    observed_fetch_effects = int(health["hard_fetch_helper_calls"]) + int(
        health["fetch_deadline_rejections"]
    )
    if (
        discovery["logical_query_count"] != LOGICAL_QUERY_COUNT
        or discovery["discovery_batch_count"] != DISCOVERY_BATCH_COUNT
        or single_shot["multi_query_chunks"] != DISCOVERY_BATCH_COUNT
        or single_shot["recursive_split_requests"] != 0
        or discovery["provider_search_call_count"]
        != int(core["cost"]["search"]["calls"])
        or discovery["provider_search_call_count"]
        > int(health["hosted_search_attempts"])
        or runtime["parent_model_requests"]
        != int(core["cost"]["model"]["requests"])
        or runtime["parent_fetch_calls"]
        != int(core["cost"]["search"]["fetch_calls"])
        or runtime["hidden_verifier_fetch_calls"]
        != runtime["partition_receipt"]["verifier_source_count"]
        or runtime["total_fetch_calls"]
        != runtime["parent_fetch_calls"] + runtime["hidden_verifier_fetch_calls"]
        or runtime["total_fetch_calls"] != observed_fetch_effects
        or runtime["total_fetch_calls"] > MAXIMUM_FETCH_SOURCES
    ):
        raise ValueError("V2.43.60 search/fetch conservation drifted")


def run_v24360_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: TwoBatchDeadlineAwareNativeSearchClient,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Any,
) -> IntegratedTwoBatchPartitionOutcome:
    visible = validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.43.60 requires the deadline-aware model limiter")
    if not isinstance(search, TwoBatchDeadlineAwareNativeSearchClient):
        raise ValueError(
            "V2.43.60 requires deadline-aware task-union single-shot search"
        )
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.43.60 model/search deadline identity drifted")
    result = run_v24359_task(
        visible,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    slot = model.receipt()
    health = search.transport_health()
    single_shot = search.single_shot_receipt()
    validate_cross_artifacts(
        result,
        model_slot_receipt=slot,
        transport_health=health,
        search_single_shot_receipt=single_shot,
        expected_cap=int(slot["slot_cap"]),
    )
    return IntegratedTwoBatchPartitionOutcome(result, slot, health, single_shot)


def build_envelope(outcome: IntegratedTwoBatchPartitionOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
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
        "search_single_shot_receipt",
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
        or not isinstance(value.get("search_single_shot_receipt"), Mapping)
        or value.get("private_task_content_present") is not True
        or value.get("private_task_content_scope") != PRIVATE_SCOPE
        or value.get("private_task_content_emitted_to_public_aggregate") is not False
        or value.get("credential_or_privileged_evaluator_content_present") is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.60 envelope identity drifted")
    slot = value["model_slot_receipt"]
    validate_cross_artifacts(
        value["result"],
        model_slot_receipt=slot,
        transport_health=value["transport_health"],
        search_single_shot_receipt=value["search_single_shot_receipt"],
        expected_cap=int(slot.get("slot_cap", -1)),
    )
    return copy.deepcopy(dict(value))


def validate_observed_bundle(
    value: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    expected_cap: int,
) -> dict[str, Any]:
    envelope = validate_envelope(value)
    slot = validate_slot_receipt(dict(model_slot_receipt), expected_cap=expected_cap)
    health = validate_transport_health(transport_health)
    single_shot = dict(search_single_shot_receipt)
    validate_single_shot_receipt(single_shot)
    if (
        envelope["model_slot_receipt"] != slot
        or envelope["transport_health"] != health
        or envelope["search_single_shot_receipt"] != single_shot
    ):
        raise ValueError("V2.43.60 independent receipt drifted from envelope")
    validate_cross_artifacts(
        envelope["result"],
        model_slot_receipt=slot,
        transport_health=health,
        search_single_shot_receipt=single_shot,
        expected_cap=expected_cap,
    )
    return envelope


__all__ = [
    "ENVELOPE_ROLE",
    "IntegratedTwoBatchPartitionOutcome",
    "POLICY_ID",
    "TwoBatchDeadlineAwareNativeSearchClient",
    "build_envelope",
    "run_v24360_task",
    "validate_cross_artifacts",
    "validate_envelope",
    "validate_observed_bundle",
]
