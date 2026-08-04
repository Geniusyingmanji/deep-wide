"""Effect-equivalent integration for V2.44.29 title-anchor recovery.

V2.44.23 remains the sole owner of all model, search, fetch, structured
recovery, and projection-observability behavior.  After that complete parent
returns, this runner applies the pure V2.44.29 title-anchor recovery to the
same private active pages.  Model, transport, and search-shape receipts are
frozen before and after the new recovery and bound by V2.44.13 effect
equivalence.  Only observation-time deadline state may advance.

The terminal independent receipt files contain the post-title-recovery
snapshots.  Failure paths preserve the content-free V2.43.97 partial-effect
contract and emit no task, query, title, URL, page, value, prediction, or
source.
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
from .v24413_effect_equivalence import (
    POLICY_ID as EQUIVALENCE_POLICY_ID,
    compare_effect_snapshots,
    validate_effect_equivalence_receipt,
)
from .v24423_projection_observable_runner import (
    POLICY_ID as PARENT_POLICY_ID,
    ProjectionObservableOutcome,
    build_envelope as build_parent_envelope,
    run_v24423_task,
    validate_envelope as validate_parent_envelope,
    validate_observed_bundle as validate_parent_observed_bundle,
)
from .v24429_title_anchor_uncertainty_recovery import (
    POLICY_ID as RECOVERY_POLICY_ID,
    recover_title_anchor_uncertainty,
    validate_result as validate_recovery_result,
)


POLICY_ID = "v24430_effect_equivalent_title_anchor_runner_v1"
ENVELOPE_ROLE = "v24430_effect_equivalent_title_anchor_envelope"
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
    "unique_page_title_anchor",
    "title_anchored_label_value_observation",
    "epistemic_credit",
    "decision_credit",
    "deterministic_gate_result",
]
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "recovery_policy_id",
        "effect_equivalence_policy_id",
        "parent_envelope",
        "title_anchor_result",
        "model_slot_receipt_before_title_recovery",
        "transport_health_before_title_recovery",
        "search_single_shot_receipt_before_title_recovery",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_equivalence_receipt",
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
class IntegratedTitleAnchorOutcome:
    parent: ProjectionObservableOutcome
    title_anchor_result: dict[str, Any]
    model_slot_receipt_before_title_recovery: dict[str, Any]
    transport_health_before_title_recovery: dict[str, Any]
    search_single_shot_receipt_before_title_recovery: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    effect_equivalence_receipt: dict[str, Any]


def validate_cross_artifacts(
    parent_envelope: Mapping[str, Any],
    title_anchor_result: Mapping[str, Any],
    *,
    model_slot_receipt_before_title_recovery: Mapping[str, Any],
    transport_health_before_title_recovery: Mapping[str, Any],
    search_single_shot_receipt_before_title_recovery: Mapping[str, Any],
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    effect_equivalence_receipt: Mapping[str, Any],
    expected_cap: int,
) -> None:
    parent = validate_parent_envelope(parent_envelope)
    recovered = validate_recovery_result(title_anchor_result)
    before_model = validate_model_receipt(
        dict(model_slot_receipt_before_title_recovery), expected_cap=expected_cap
    )
    before_transport = validate_transport_health(
        transport_health_before_title_recovery
    )
    before_search = dict(search_single_shot_receipt_before_title_recovery)
    validate_search_receipt(before_search)
    after_model = validate_model_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    after_transport = validate_transport_health(transport_health)
    after_search = dict(search_single_shot_receipt)
    validate_search_receipt(after_search)
    validate_parent_observed_bundle(
        parent,
        model_slot_receipt=before_model,
        transport_health=before_transport,
        search_single_shot_receipt=before_search,
        expected_cap=expected_cap,
    )
    if recovered["parent_result"] != parent["parent_envelope"]["result"]:
        raise ValueError("V2.44.30 title recovery parent drifted")
    expected_equivalence = compare_effect_snapshots(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        expected_model_cap=expected_cap,
    )
    validated_equivalence = validate_effect_equivalence_receipt(
        effect_equivalence_receipt
    )
    if expected_equivalence != validated_equivalence:
        raise ValueError("V2.44.30 effect-equivalence replay drifted")
    receipt = recovered["title_anchor_recovery_receipt"]
    if any(
        receipt[name] != 0
        for name in (
            "additional_model_requests",
            "additional_logical_queries",
            "additional_search_batches",
            "additional_fetch_calls",
        )
    ):
        raise ValueError("V2.44.30 title recovery added an external effect")


def run_v24430_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: UncertaintyDeadlineAwareNativeSearchClient,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
) -> IntegratedTitleAnchorOutcome:
    visible = validate_visible_task(task)
    parent = run_v24423_task(
        visible,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    before_model = copy.deepcopy(parent.model_slot_receipt)
    before_transport = copy.deepcopy(parent.transport_health)
    before_search = copy.deepcopy(parent.search_single_shot_receipt)
    result = recover_title_anchor_uncertainty(parent.parent.result)
    after_model = model.receipt()
    after_transport = search.transport_health()
    after_search = search.single_shot_receipt()
    equivalence = compare_effect_snapshots(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        expected_model_cap=int(before_model["slot_cap"]),
    )
    outcome = IntegratedTitleAnchorOutcome(
        parent=parent,
        title_anchor_result=result,
        model_slot_receipt_before_title_recovery=before_model,
        transport_health_before_title_recovery=before_transport,
        search_single_shot_receipt_before_title_recovery=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_equivalence_receipt=equivalence,
    )
    validate_cross_artifacts(
        build_parent_envelope(parent),
        result,
        model_slot_receipt_before_title_recovery=before_model,
        transport_health_before_title_recovery=before_transport,
        search_single_shot_receipt_before_title_recovery=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_equivalence_receipt=equivalence,
        expected_cap=int(after_model["slot_cap"]),
    )
    return outcome


def build_envelope(outcome: IntegratedTitleAnchorOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": PARENT_POLICY_ID,
        "recovery_policy_id": RECOVERY_POLICY_ID,
        "effect_equivalence_policy_id": EQUIVALENCE_POLICY_ID,
        "parent_envelope": build_parent_envelope(outcome.parent),
        "title_anchor_result": copy.deepcopy(outcome.title_anchor_result),
        "model_slot_receipt_before_title_recovery": copy.deepcopy(
            outcome.model_slot_receipt_before_title_recovery
        ),
        "transport_health_before_title_recovery": copy.deepcopy(
            outcome.transport_health_before_title_recovery
        ),
        "search_single_shot_receipt_before_title_recovery": copy.deepcopy(
            outcome.search_single_shot_receipt_before_title_recovery
        ),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
        "effect_equivalence_receipt": copy.deepcopy(
            outcome.effect_equivalence_receipt
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
    mapping_fields = (
        "parent_envelope",
        "title_anchor_result",
        "model_slot_receipt_before_title_recovery",
        "transport_health_before_title_recovery",
        "search_single_shot_receipt_before_title_recovery",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_equivalence_receipt",
    )
    if (
        set(value) != ENVELOPE_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ENVELOPE_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("parent_policy_id") != PARENT_POLICY_ID
        or value.get("recovery_policy_id") != RECOVERY_POLICY_ID
        or value.get("effect_equivalence_policy_id") != EQUIVALENCE_POLICY_ID
        or any(not isinstance(value.get(name), Mapping) for name in mapping_fields)
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
        raise ValueError("V2.44.30 title-anchor envelope identity drifted")
    after_model = value["model_slot_receipt"]
    validate_cross_artifacts(
        value["parent_envelope"],
        value["title_anchor_result"],
        model_slot_receipt_before_title_recovery=value[
            "model_slot_receipt_before_title_recovery"
        ],
        transport_health_before_title_recovery=value[
            "transport_health_before_title_recovery"
        ],
        search_single_shot_receipt_before_title_recovery=value[
            "search_single_shot_receipt_before_title_recovery"
        ],
        model_slot_receipt=after_model,
        transport_health=value["transport_health"],
        search_single_shot_receipt=value["search_single_shot_receipt"],
        effect_equivalence_receipt=value["effect_equivalence_receipt"],
        expected_cap=int(after_model.get("slot_cap", -1)),
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
    model = validate_model_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    transport = validate_transport_health(transport_health)
    search = dict(search_single_shot_receipt)
    validate_search_receipt(search)
    if (
        envelope["model_slot_receipt"] != model
        or envelope["transport_health"] != transport
        or envelope["search_single_shot_receipt"] != search
    ):
        raise ValueError("V2.44.30 terminal receipt drifted from envelope")
    return envelope


def run_and_persist_title_anchor_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> IntegratedTitleAnchorOutcome:
    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        outcome = run_v24430_task(
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
    "IntegratedTitleAnchorOutcome",
    "MODEL_NAME",
    "POLICY_ID",
    "RESULT_NAME",
    "SEARCH_NAME",
    "TRANSPORT_NAME",
    "build_envelope",
    "run_and_persist_title_anchor_task",
    "run_v24430_task",
    "validate_cross_artifacts",
    "validate_envelope",
    "validate_observed_bundle",
]
