"""Deadline/failure-observable integration for V2.44.07 recovery.

The only external effects are the frozen V2.43.91 parent effects.  After that
parent has completed, V2.44.07 deterministically replays its private pages and
uncertainty catalog.  Independent model, transport, and search-shape receipts
must therefore remain byte-identical before and after structured recovery.

On any construction, forward, recovery, or serialization failure, only the
content-free V2.43.97 partial-effect snapshot is persisted.  No task, query,
URL, page, observation, prediction, candidate value, or source is emitted by
the failure path.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24312_deadline_reliability import (
    DeadlineAwareGlobalModelSlotLimiter,
    validate_receipt as validate_model_receipt,
)
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24391_uncertainty_active_evidence_runner import (
    UncertaintyDeadlineAwareNativeSearchClient,
    run_v24391_task,
    validate_cross_artifacts as validate_parent_cross_artifacts,
)
from .v24397_failure_observability import build_failure_snapshot
from .v24399_failure_observable_runner import (
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    persist_failure_artifacts,
)
from .v24407_structured_uncertainty_recovery import (
    POLICY_ID as RECOVERY_POLICY_ID,
    recover_structured_uncertainty,
    validate_result as validate_recovery_result,
)


POLICY_ID = "v24409_failure_observable_structured_uncertainty_runner_v1"
ENVELOPE_ROLE = "v24409_structured_uncertainty_task_envelope"
PRIVATE_SCOPE = [
    "opaque_id",
    "prediction",
    "visible_proposal_query_batch",
    "proposal_source_url_title_and_page",
    "frozen_baseline_cell",
    "uncertainty_posterior",
    "active_row_column_query",
    "active_source_url_title_and_page",
    "legacy_target_segment_observation",
    "structured_label_value_observation",
    "epistemic_credit",
    "decision_credit",
    "deterministic_gate_result",
]
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "recovery_policy_id",
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
)


@dataclass(frozen=True)
class IntegratedStructuredUncertaintyOutcome:
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
    recovered = validate_recovery_result(result)
    slot = validate_model_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    health = validate_transport_health(transport_health)
    search = dict(search_single_shot_receipt)
    validate_search_receipt(search)
    legacy = recovered["parent_result"]
    validate_parent_cross_artifacts(
        legacy,
        model_slot_receipt=slot,
        transport_health=health,
        search_single_shot_receipt=search,
        expected_cap=expected_cap,
    )
    runtime = legacy["uncertainty_active_receipt"]
    receipt = recovered["structured_recovery_receipt"]
    if (
        receipt["parent_model_requests"] != runtime["parent_model_requests"]
        or receipt["parent_total_logical_queries"]
        != runtime["total_logical_query_count"]
        or receipt["parent_total_search_batches"]
        != runtime["total_search_batch_count"]
        or receipt["parent_total_fetch_calls"] != runtime["total_fetch_calls"]
        or any(
            receipt[name] != 0
            for name in (
                "additional_model_requests",
                "additional_logical_queries",
                "additional_search_batches",
                "additional_fetch_calls",
            )
        )
    ):
        raise ValueError("V2.44.09 zero-effect conservation drifted")


def run_v24409_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: UncertaintyDeadlineAwareNativeSearchClient,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
) -> IntegratedStructuredUncertaintyOutcome:
    visible = validate_visible_task(task)
    parent_outcome = run_v24391_task(
        visible,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    model_before = copy.deepcopy(parent_outcome.model_slot_receipt)
    transport_before = copy.deepcopy(parent_outcome.transport_health)
    search_before = copy.deepcopy(parent_outcome.search_single_shot_receipt)
    result = recover_structured_uncertainty(parent_outcome.result)
    model_after = model.receipt()
    transport_after = search.transport_health()
    search_after = search.single_shot_receipt()
    if (
        model_after != model_before
        or transport_after != transport_before
        or search_after != search_before
    ):
        raise RuntimeError("V2.44.09 recovery caused an external effect")
    validate_cross_artifacts(
        result,
        model_slot_receipt=model_before,
        transport_health=transport_before,
        search_single_shot_receipt=search_before,
        expected_cap=int(model_before["slot_cap"]),
    )
    return IntegratedStructuredUncertaintyOutcome(
        result=result,
        model_slot_receipt=model_before,
        transport_health=transport_before,
        search_single_shot_receipt=search_before,
    )


def build_envelope(
    outcome: IntegratedStructuredUncertaintyOutcome,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "recovery_policy_id": RECOVERY_POLICY_ID,
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
    unsigned = dict(value)
    seal = unsigned.pop("envelope_payload_sha256", None)
    if (
        set(value) != ENVELOPE_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ENVELOPE_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("recovery_policy_id") != RECOVERY_POLICY_ID
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
        raise ValueError("V2.44.09 envelope identity drifted")
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
    slot = validate_model_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    health = validate_transport_health(transport_health)
    search = dict(search_single_shot_receipt)
    validate_search_receipt(search)
    if (
        envelope["model_slot_receipt"] != slot
        or envelope["transport_health"] != health
        or envelope["search_single_shot_receipt"] != search
    ):
        raise ValueError("V2.44.09 independent receipt drifted from envelope")
    validate_cross_artifacts(
        envelope["result"],
        model_slot_receipt=slot,
        transport_health=health,
        search_single_shot_receipt=search,
        expected_cap=expected_cap,
    )
    return envelope


def run_and_persist_structured_uncertainty_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> IntegratedStructuredUncertaintyOutcome:
    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        outcome = run_v24409_task(
            task,
            model=model,
            search=search,
            partition_seed_sha256=partition_seed_sha256,
            limits=limits,
            monotonic=monotonic,
        )
    except BaseException as error:
        persist_failure_artifacts(
            error,
            failure_stage=stage,
            model=model,
            search=search,
            expected_model_cap=expected_model_cap,
            writer=writer,
        )
        raise

    envelope = build_envelope(outcome)
    model_written = False
    transport_written = False
    search_written = False
    try:
        writer(MODEL_NAME, outcome.model_slot_receipt)
        model_written = True
        writer(TRANSPORT_NAME, outcome.transport_health)
        transport_written = True
        writer(SEARCH_NAME, outcome.search_single_shot_receipt)
        search_written = True
        writer(RESULT_NAME, envelope)
    except BaseException as error:
        snapshot = build_failure_snapshot(
            error,
            failure_stage="artifact_serialization",
            model_receipt=(outcome.model_slot_receipt if model_written else None),
            transport_health=(outcome.transport_health if transport_written else None),
            search_receipt=(
                outcome.search_single_shot_receipt if search_written else None
            ),
            expected_model_cap=expected_model_cap,
        )
        writer(FAILURE_NAME, snapshot)
        raise
    return outcome


__all__ = [
    "ENVELOPE_ROLE",
    "FAILURE_NAME",
    "IntegratedStructuredUncertaintyOutcome",
    "MODEL_NAME",
    "POLICY_ID",
    "RESULT_NAME",
    "SEARCH_NAME",
    "TRANSPORT_NAME",
    "build_envelope",
    "run_and_persist_structured_uncertainty_task",
    "run_v24409_task",
    "validate_cross_artifacts",
    "validate_envelope",
    "validate_observed_bundle",
]
