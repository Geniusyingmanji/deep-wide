"""Effect-bounded integration for narrative title uncertainty recovery.

V2.44.34 left four children for the parent to kill after 230 seconds even
though model-slot contention was small.  Its model and hosted-search static
timeouts both equalled the full task budget.  This append-only runner requires
each provider effect to have a much shorter static cap before any runtime call.

The complete V2.44.30 parent remains the sole owner of model, search, fetch,
structured recovery, and strict title recovery.  After it returns, V2.44.37
replays narrative title evidence over the same private pages without external
effects.  Model, transport, and search-shape receipts are frozen before and
after narrative recovery and bound by V2.44.13 effect equivalence.
"""

from __future__ import annotations

import copy
import math
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
from .v24356_explicit_partition_runner import _aligned_deadlines
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
from .v24430_title_anchor_effect_runner import (
    POLICY_ID as PARENT_POLICY_ID,
    IntegratedTitleAnchorOutcome,
    build_envelope as build_parent_envelope,
    run_v24430_task,
    validate_envelope as validate_parent_envelope,
    validate_observed_bundle as validate_parent_observed_bundle,
)
from .v24437_narrative_title_uncertainty_recovery import (
    POLICY_ID as RECOVERY_POLICY_ID,
    recover_narrative_title_uncertainty,
    validate_result as validate_recovery_result,
)


POLICY_ID = "v24438_effect_bounded_narrative_title_runner_v1"
ENVELOPE_ROLE = "v24438_effect_bounded_narrative_title_envelope"
EFFECT_TIMEOUT_ROLE = "v24438_effect_timeout_contract"
MAXIMUM_PROVIDER_EFFECT_SECONDS = 70.0
PRIVATE_SCOPE = [
    "opaque_id",
    "prediction",
    "visible_proposal_query_batch",
    "proposal_source_url_title_and_page",
    "frozen_baseline_cell",
    "uncertainty_posterior",
    "active_row_column_query",
    "active_source_url_title_and_page",
    "structured_and_title_observation",
    "narrative_title_relation_observation",
    "epistemic_credit",
    "decision_credit",
    "deterministic_gate_result",
]
TIMEOUT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "maximum_provider_effect_seconds",
        "model_provider_timeout_seconds",
        "hosted_search_timeout_seconds",
        "model_and_search_timeout_equal",
        "model_and_search_share_absolute_deadline",
        "provider_effect_timeout_strictly_below_remaining_task_budget_at_start",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "contract_sha256",
    }
)
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "recovery_policy_id",
        "effect_equivalence_policy_id",
        "effect_timeout_contract",
        "parent_envelope",
        "narrative_title_result",
        "model_slot_receipt_before_narrative_recovery",
        "transport_health_before_narrative_recovery",
        "search_single_shot_receipt_before_narrative_recovery",
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
class IntegratedBoundedNarrativeOutcome:
    parent: IntegratedTitleAnchorOutcome
    narrative_title_result: dict[str, Any]
    effect_timeout_contract: dict[str, Any]
    model_slot_receipt_before_narrative_recovery: dict[str, Any]
    transport_health_before_narrative_recovery: dict[str, Any]
    search_single_shot_receipt_before_narrative_recovery: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    effect_equivalence_receipt: dict[str, Any]


def _positive_finite(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise ValueError("V2.44.38 provider effect timeout is invalid")
    return float(value)


def build_effect_timeout_contract(
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: UncertaintyDeadlineAwareNativeSearchClient,
) -> dict[str, Any]:
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.44.38 requires deadline-aware model limiter")
    if not isinstance(search, UncertaintyDeadlineAwareNativeSearchClient):
        raise ValueError("V2.44.38 requires deadline-aware search transport")
    if not _aligned_deadlines(model, search):
        raise ValueError("V2.44.38 model/search absolute deadline drifted")
    provider = getattr(model, "inner", None)
    model_timeout = _positive_finite(getattr(provider, "timeout", None))
    search_timeout = _positive_finite(
        getattr(search, "static_search_timeout_seconds", None)
    )
    remaining = min(
        _positive_finite(model.remaining_effect_seconds()),
        _positive_finite(search.remaining_effect_seconds()),
    )
    equal = abs(model_timeout - search_timeout) <= 1e-9
    within_cap = (
        model_timeout <= MAXIMUM_PROVIDER_EFFECT_SECONDS
        and search_timeout <= MAXIMUM_PROVIDER_EFFECT_SECONDS
    )
    below_remaining = max(model_timeout, search_timeout) < remaining
    if not equal or not within_cap or not below_remaining:
        raise ValueError("V2.44.38 provider effect cap drifted")
    value = {
        "artifact_version": 1,
        "role": EFFECT_TIMEOUT_ROLE,
        "maximum_provider_effect_seconds": MAXIMUM_PROVIDER_EFFECT_SECONDS,
        "model_provider_timeout_seconds": model_timeout,
        "hosted_search_timeout_seconds": search_timeout,
        "model_and_search_timeout_equal": True,
        "model_and_search_share_absolute_deadline": True,
        "provider_effect_timeout_strictly_below_remaining_task_budget_at_start": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["contract_sha256"] = payload_sha256(value)
    validate_effect_timeout_contract(value)
    return value


def validate_effect_timeout_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("contract_sha256", None)
    model_timeout = value.get("model_provider_timeout_seconds")
    search_timeout = value.get("hosted_search_timeout_seconds")
    if (
        set(value) != TIMEOUT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != EFFECT_TIMEOUT_ROLE
        or value.get("maximum_provider_effect_seconds")
        != MAXIMUM_PROVIDER_EFFECT_SECONDS
        or _positive_finite(model_timeout) > MAXIMUM_PROVIDER_EFFECT_SECONDS
        or _positive_finite(search_timeout) > MAXIMUM_PROVIDER_EFFECT_SECONDS
        or abs(float(model_timeout) - float(search_timeout)) > 1e-9
        or value.get("model_and_search_timeout_equal") is not True
        or value.get("model_and_search_share_absolute_deadline") is not True
        or value.get(
            "provider_effect_timeout_strictly_below_remaining_task_budget_at_start"
        )
        is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.38 effect timeout contract drifted")
    return copy.deepcopy(dict(value))


def validate_cross_artifacts(
    parent_envelope: Mapping[str, Any],
    narrative_title_result: Mapping[str, Any],
    *,
    effect_timeout_contract: Mapping[str, Any],
    model_slot_receipt_before_narrative_recovery: Mapping[str, Any],
    transport_health_before_narrative_recovery: Mapping[str, Any],
    search_single_shot_receipt_before_narrative_recovery: Mapping[str, Any],
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    effect_equivalence_receipt: Mapping[str, Any],
    expected_cap: int,
) -> None:
    parent_value = validate_parent_envelope(parent_envelope)
    recovered = validate_recovery_result(narrative_title_result)
    validate_effect_timeout_contract(effect_timeout_contract)
    before_model = validate_model_receipt(
        dict(model_slot_receipt_before_narrative_recovery), expected_cap=expected_cap
    )
    before_transport = validate_transport_health(
        transport_health_before_narrative_recovery
    )
    before_search = dict(search_single_shot_receipt_before_narrative_recovery)
    validate_search_receipt(before_search)
    after_model = validate_model_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    after_transport = validate_transport_health(transport_health)
    after_search = dict(search_single_shot_receipt)
    validate_search_receipt(after_search)
    validate_parent_observed_bundle(
        parent_value,
        model_slot_receipt=before_model,
        transport_health=before_transport,
        search_single_shot_receipt=before_search,
        expected_cap=expected_cap,
    )
    if recovered["parent_result"] != parent_value["title_anchor_result"]:
        raise ValueError("V2.44.38 narrative recovery parent drifted")
    expected_equivalence = compare_effect_snapshots(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        expected_model_cap=expected_cap,
    )
    if expected_equivalence != validate_effect_equivalence_receipt(
        effect_equivalence_receipt
    ):
        raise ValueError("V2.44.38 effect-equivalence replay drifted")
    receipt = recovered["narrative_recovery_receipt"]
    if any(
        receipt[name] != 0
        for name in (
            "additional_model_requests",
            "additional_logical_queries",
            "additional_search_batches",
            "additional_fetch_calls",
        )
    ):
        raise ValueError("V2.44.38 narrative recovery added an external effect")


def run_v24438_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: UncertaintyDeadlineAwareNativeSearchClient,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
) -> IntegratedBoundedNarrativeOutcome:
    visible = validate_visible_task(task)
    timeout_contract = build_effect_timeout_contract(model, search)
    parent_outcome = run_v24430_task(
        visible,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    before_model = copy.deepcopy(parent_outcome.model_slot_receipt)
    before_transport = copy.deepcopy(parent_outcome.transport_health)
    before_search = copy.deepcopy(parent_outcome.search_single_shot_receipt)
    result = recover_narrative_title_uncertainty(
        parent_outcome.title_anchor_result
    )
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
    outcome = IntegratedBoundedNarrativeOutcome(
        parent=parent_outcome,
        narrative_title_result=result,
        effect_timeout_contract=timeout_contract,
        model_slot_receipt_before_narrative_recovery=before_model,
        transport_health_before_narrative_recovery=before_transport,
        search_single_shot_receipt_before_narrative_recovery=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_equivalence_receipt=equivalence,
    )
    validate_cross_artifacts(
        build_parent_envelope(parent_outcome),
        result,
        effect_timeout_contract=timeout_contract,
        model_slot_receipt_before_narrative_recovery=before_model,
        transport_health_before_narrative_recovery=before_transport,
        search_single_shot_receipt_before_narrative_recovery=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_equivalence_receipt=equivalence,
        expected_cap=int(after_model["slot_cap"]),
    )
    return outcome


def build_envelope(outcome: IntegratedBoundedNarrativeOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": PARENT_POLICY_ID,
        "recovery_policy_id": RECOVERY_POLICY_ID,
        "effect_equivalence_policy_id": EQUIVALENCE_POLICY_ID,
        "effect_timeout_contract": copy.deepcopy(outcome.effect_timeout_contract),
        "parent_envelope": build_parent_envelope(outcome.parent),
        "narrative_title_result": copy.deepcopy(outcome.narrative_title_result),
        "model_slot_receipt_before_narrative_recovery": copy.deepcopy(
            outcome.model_slot_receipt_before_narrative_recovery
        ),
        "transport_health_before_narrative_recovery": copy.deepcopy(
            outcome.transport_health_before_narrative_recovery
        ),
        "search_single_shot_receipt_before_narrative_recovery": copy.deepcopy(
            outcome.search_single_shot_receipt_before_narrative_recovery
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
        "effect_timeout_contract",
        "parent_envelope",
        "narrative_title_result",
        "model_slot_receipt_before_narrative_recovery",
        "transport_health_before_narrative_recovery",
        "search_single_shot_receipt_before_narrative_recovery",
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
        raise ValueError("V2.44.38 narrative runner envelope identity drifted")
    after_model = value["model_slot_receipt"]
    validate_cross_artifacts(
        value["parent_envelope"],
        value["narrative_title_result"],
        effect_timeout_contract=value["effect_timeout_contract"],
        model_slot_receipt_before_narrative_recovery=value[
            "model_slot_receipt_before_narrative_recovery"
        ],
        transport_health_before_narrative_recovery=value[
            "transport_health_before_narrative_recovery"
        ],
        search_single_shot_receipt_before_narrative_recovery=value[
            "search_single_shot_receipt_before_narrative_recovery"
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
        raise ValueError("V2.44.38 terminal receipt drifted from envelope")
    return envelope


def run_and_persist_bounded_narrative_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> IntegratedBoundedNarrativeOutcome:
    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        outcome = run_v24438_task(
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
    "IntegratedBoundedNarrativeOutcome",
    "MAXIMUM_PROVIDER_EFFECT_SECONDS",
    "MODEL_NAME",
    "POLICY_ID",
    "RESULT_NAME",
    "SEARCH_NAME",
    "TRANSPORT_NAME",
    "build_effect_timeout_contract",
    "build_envelope",
    "run_and_persist_bounded_narrative_task",
    "run_v24438_task",
    "validate_cross_artifacts",
    "validate_effect_timeout_contract",
    "validate_envelope",
    "validate_observed_bundle",
]
