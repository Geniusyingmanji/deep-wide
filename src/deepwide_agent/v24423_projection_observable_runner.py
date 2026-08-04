"""Projection-observable wrapper around the frozen V2.44.15 runner.

V2.44.15 remains the sole owner of model, search, fetch, recovery, prediction,
entropy, credit, and effect-equivalence behavior.  After that parent returns,
this wrapper passes only its already-private V2.44.05 projection catalog to
V2.44.21 and binds the resulting counts-only rejection receipt beside the
complete parent envelope.  The receipt is replay-validated from the private
catalog whenever the wrapper envelope is opened.

The new step receives no model or search client and cannot alter the parent
result.  Independent terminal receipts continue to be the V2.44.15
post-recovery receipts.  Failure and serialization paths preserve the same
content-free partial-effect observability guarantees.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
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
from .v24415_effect_equivalent_structured_runner import (
    POLICY_ID as PARENT_POLICY_ID,
    PRIVATE_SCOPE,
    IntegratedEffectEquivalentStructuredOutcome,
    build_envelope as build_parent_envelope,
    run_v24415_task,
    validate_envelope as validate_parent_envelope,
    validate_observed_bundle as validate_parent_observed_bundle,
)
from .v24421_structured_projection_observability import (
    POLICY_ID as OBSERVABILITY_POLICY_ID,
    build_projection_observability,
    validate_projection_observability,
)


POLICY_ID = "v24423_projection_observable_effect_equivalent_runner_v1"
ENVELOPE_ROLE = "v24423_projection_observable_effect_equivalent_envelope"
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "projection_observability_policy_id",
        "parent_envelope",
        "projection_observability_receipt",
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
class ProjectionObservableOutcome:
    parent: IntegratedEffectEquivalentStructuredOutcome
    projection_observability_receipt: dict[str, Any]

    @property
    def result(self) -> dict[str, Any]:
        return self.parent.result

    @property
    def model_slot_receipt(self) -> dict[str, Any]:
        return self.parent.model_slot_receipt

    @property
    def transport_health(self) -> dict[str, Any]:
        return self.parent.transport_health

    @property
    def search_single_shot_receipt(self) -> dict[str, Any]:
        return self.parent.search_single_shot_receipt


def _cross_validate(
    parent_envelope: Mapping[str, Any], observability: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    parent = validate_parent_envelope(parent_envelope)
    catalog = parent["result"]["structured_active_projection"]
    receipt = validate_projection_observability(observability, catalog=catalog)
    recovery = parent["result"]["structured_recovery_receipt"]
    expected = {
        "page_count": recovery["active_page_count"],
        "selected_target_count": recovery["selected_target_count"],
        "structured_projection_count": recovery["structured_projection_count"],
        "novel_structured_observation_count": recovery[
            "novel_structured_observation_count"
        ],
        "legacy_observation_count": recovery["legacy_active_observation_count"],
        "combined_observation_count": recovery[
            "combined_active_observation_count"
        ],
    }
    if any(receipt[name] != value for name, value in expected.items()):
        raise ValueError("V2.44.23 observability/recovery count drifted")
    return parent, receipt


def run_v24423_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: UncertaintyDeadlineAwareNativeSearchClient,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
) -> ProjectionObservableOutcome:
    parent = run_v24415_task(
        task,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    receipt = build_projection_observability(
        parent.result["structured_active_projection"]
    )
    outcome = ProjectionObservableOutcome(
        parent=parent,
        projection_observability_receipt=receipt,
    )
    _cross_validate(build_parent_envelope(parent), receipt)
    return outcome


def build_envelope(outcome: ProjectionObservableOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": PARENT_POLICY_ID,
        "projection_observability_policy_id": OBSERVABILITY_POLICY_ID,
        "parent_envelope": build_parent_envelope(outcome.parent),
        "projection_observability_receipt": copy.deepcopy(
            outcome.projection_observability_receipt
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
        or value.get("parent_policy_id") != PARENT_POLICY_ID
        or value.get("projection_observability_policy_id")
        != OBSERVABILITY_POLICY_ID
        or not isinstance(value.get("parent_envelope"), Mapping)
        or not isinstance(value.get("projection_observability_receipt"), Mapping)
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
        raise ValueError("V2.44.23 envelope identity drifted")
    _cross_validate(
        value["parent_envelope"], value["projection_observability_receipt"]
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
    validate_parent_observed_bundle(
        envelope["parent_envelope"],
        model_slot_receipt=model_slot_receipt,
        transport_health=transport_health,
        search_single_shot_receipt=search_single_shot_receipt,
        expected_cap=expected_cap,
    )
    return envelope


def run_and_persist_projection_observable_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> ProjectionObservableOutcome:
    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        outcome = run_v24423_task(
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
    "MODEL_NAME",
    "POLICY_ID",
    "ProjectionObservableOutcome",
    "RESULT_NAME",
    "SEARCH_NAME",
    "TRANSPORT_NAME",
    "build_envelope",
    "run_and_persist_projection_observable_task",
    "run_v24423_task",
    "validate_envelope",
    "validate_observed_bundle",
]
