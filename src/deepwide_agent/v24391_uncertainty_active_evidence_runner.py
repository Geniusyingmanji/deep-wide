"""Deadline and transport integration for V2.43.90."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24263_global_model_limiter import payload_sha256
from .v24269_task_union_discovery import validate_receipt as validate_union_receipt
from .v24280_task_union_single_shot import (
    TaskUnionSingleShotMixin,
    validate_receipt as validate_single_shot_receipt,
)
from .v24312_deadline_reliability import (
    DeadlineAwareGlobalModelSlotLimiter,
    validate_receipt as validate_slot_receipt,
)
from .v24316_deadline_search import (
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from .v24356_explicit_partition_runner import _aligned_deadlines
from .v24390_uncertainty_active_evidence_runtime import (
    MAXIMUM_TOTAL_FETCHES,
    PROPOSAL_SEARCH_BATCHES,
    run_v24390_task,
    validate_result,
)


POLICY_ID = "v24391_deadline_uncertainty_active_evidence_runner_v1"
ENVELOPE_ROLE = "v24391_uncertainty_active_evidence_task_envelope"
PRIVATE_SCOPE = [
    "opaque_id",
    "prediction",
    "visible_proposal_query_batch",
    "proposal_source_url_title_and_page",
    "frozen_baseline_cell",
    "uncertainty_posterior",
    "active_row_column_query",
    "active_source_url_title_and_page",
    "programmatic_target_segment_observation",
    "epistemic_credit",
    "decision_credit",
    "deterministic_gate_result",
]


class UncertaintyDeadlineAwareNativeSearchClient(
    TaskUnionSingleShotMixin, DeadlineAwareNativeSearchClient
):
    """Deadline-aware task-union transport for proposal and active search."""


@dataclass(frozen=True)
class IntegratedUncertaintyActiveEvidenceOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]


def validate_cross_artifacts(
    result: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    expected_cap: int,
) -> None:
    validated = validate_result(result)
    slot = validate_slot_receipt(dict(model_slot_receipt), expected_cap=expected_cap)
    health = validate_transport_health(transport_health)
    single_shot = dict(search_single_shot_receipt)
    validate_single_shot_receipt(single_shot)
    parent = validated["parent_result"]
    core = parent["semantic_result"]["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    runtime = validated["uncertainty_active_receipt"]
    final_union = validated["private_replay_state"][
        "active_union_receipt_after_active"
    ]
    validate_union_receipt(final_union)

    if core_receipt["effect_accounting_complete"]:
        if (
            core_receipt["provider_model_requests"] != slot["acquisitions"]
            or core_receipt["pre_provider_model_rejections"] != slot["slot_timeouts"]
            or core_receipt["logical_model_admissions"]
            != slot["acquisitions"] + slot["slot_timeouts"]
            or core_receipt["provider_model_attempts"]
            != int(core["cost"]["model"]["attempts"])
        ):
            raise ValueError("V2.43.91 complete model conservation drifted")
    elif (
        core_receipt["unattributed_model_effects_lower_bound"]
        < slot["acquisitions"]
        or core_receipt["unattributed_model_attempts_lower_bound"]
        != int(core["cost"]["model"]["attempts"])
    ):
        raise ValueError("V2.43.91 incomplete model lower bound drifted")

    active_queries = int(runtime["active_logical_query_count"])
    active_batches = int(runtime["active_search_batch_count"])
    expected_multi_query_chunks = PROPOSAL_SEARCH_BATCHES + int(
        active_queries > 1
    )
    observed_fetch_effects = int(health["hard_fetch_helper_calls"]) + int(
        health["fetch_deadline_rejections"]
    )
    if (
        runtime["active_provider_search_calls"] < active_batches
        or runtime["total_provider_search_calls"]
        != runtime["parent_provider_search_calls"]
        + runtime["active_provider_search_calls"]
        or runtime["total_search_batch_count"]
        != int(final_union["search_invocations"])
        or runtime["total_logical_query_count"]
        != int(final_union["logical_query_count"])
        or runtime["total_provider_search_calls"]
        < runtime["total_search_batch_count"]
        or runtime["total_provider_search_calls"]
        > int(health["hosted_search_attempts"])
        or int(health["hosted_search_attempts"])
        > 2 * int(runtime["total_search_batch_count"])
        or int(core["cost"]["search"]["calls"])
        != runtime["parent_provider_search_calls"]
        or single_shot["multi_query_chunks"] != expected_multi_query_chunks
        or single_shot["recursive_split_requests"] != 0
        or runtime["parent_model_requests"]
        != int(core["cost"]["model"]["requests"])
        or runtime["parent_model_requests"] != slot["acquisitions"]
        or runtime["parent_fetch_calls"]
        != int(core["cost"]["search"]["fetch_calls"])
        or runtime["active_fetch_calls"]
        != runtime["active_selected_source_count"]
        or runtime["total_fetch_calls"]
        != runtime["parent_fetch_calls"] + runtime["active_fetch_calls"]
        or runtime["total_fetch_calls"] != observed_fetch_effects
        or runtime["total_fetch_calls"]
        != final_union["fetch_requested_source_count"]
        or runtime["total_fetch_calls"] > MAXIMUM_TOTAL_FETCHES
    ):
        raise ValueError("V2.43.91 search/fetch/active conservation drifted")


def run_v24391_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: UncertaintyDeadlineAwareNativeSearchClient,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Any,
) -> IntegratedUncertaintyActiveEvidenceOutcome:
    visible = validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.43.91 requires the deadline-aware model limiter")
    if not isinstance(search, UncertaintyDeadlineAwareNativeSearchClient):
        raise ValueError("V2.43.91 requires deadline-aware single-shot search")
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.43.91 model/search deadline identity drifted")
    result = run_v24390_task(
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
    return IntegratedUncertaintyActiveEvidenceOutcome(
        result, slot, health, single_shot
    )


def build_envelope(
    outcome: IntegratedUncertaintyActiveEvidenceOutcome,
) -> dict[str, Any]:
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
        raise ValueError("V2.43.91 envelope identity drifted")
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
        raise ValueError("V2.43.91 independent receipt drifted from envelope")
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
    "IntegratedUncertaintyActiveEvidenceOutcome",
    "POLICY_ID",
    "UncertaintyDeadlineAwareNativeSearchClient",
    "build_envelope",
    "run_v24391_task",
    "validate_cross_artifacts",
    "validate_envelope",
    "validate_observed_bundle",
]
