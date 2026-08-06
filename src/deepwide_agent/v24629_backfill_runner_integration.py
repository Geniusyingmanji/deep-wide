"""V2.43.19 runtime integration for bounded citation-title backfill search.

This layer changes no model prompt, task budget, retrieval policy, or fallback
rule.  It requires the V2.46.28 search type, executes the frozen V2.43.19
deadline-conserving runtime, and binds the legacy single-shot receipt and the
new content-free backfill receipt into one sealed task envelope.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24263_global_model_limiter import payload_sha256
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24280_task_union_single_shot import validate_receipt as validate_single_shot
from .v24294_staged_reserve import StagedReservePolicy
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24319_runner_integration import (
    IntegratedTaskOutcome,
    run_v24319_task,
    validate_cross_artifacts as validate_parent_cross_artifacts,
)
from .v24318_deadline_conservation_runtime import validate_v24318_result
from .v24627_same_response_citation_title_backfill import (
    SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient,
    validate_receipt as validate_backfill_receipt,
)


POLICY_ID = "v24629_deadline_conserving_citation_title_backfill_runner_v1"
ENVELOPE_ROLE = "v24629_citation_title_backfill_task_envelope"


@dataclass(frozen=True)
class IntegratedBackfillTaskOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    citation_title_backfill_receipt: dict[str, Any]


def validate_cross_artifacts(
    result: Mapping[str, Any],
    *,
    arm: str,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    citation_title_backfill_receipt: Mapping[str, Any],
    expected_cap: int,
) -> None:
    validate_parent_cross_artifacts(
        result,
        arm=arm,
        model_slot_receipt=model_slot_receipt,
        transport_health=transport_health,
        expected_cap=expected_cap,
    )
    single = dict(search_single_shot_receipt)
    backfill = validate_backfill_receipt(citation_title_backfill_receipt)
    validate_single_shot(single)
    if (
        backfill["multi_query_payload_count"] != single["multi_query_chunks"]
        or backfill["additional_search_fetch_model_process_evaluator_or_credit_effect"]
        is not False
        or backfill["mapping_gold_category_question_type_split_evaluator_score_or_reward_read"]
        is not False
        or backfill["benchmark_launch_or_evaluator_authorized"] is not False
    ):
        raise ValueError("V2.46.29 search/backfill receipt conservation drifted")


def run_v24629_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Any,
    progress: Any = None,
) -> IntegratedBackfillTaskOutcome:
    visible = validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.46.29 requires the deadline-aware global model limiter")
    if not isinstance(
        search,
        SameResponseCitationTitleBackfillNominalHardTotalWallNativeSearchClient,
    ):
        raise ValueError("V2.46.29 requires the bounded backfill search type")
    parent: IntegratedTaskOutcome = run_v24319_task(
        visible,
        arm=arm,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
        reserve_policy=reserve_policy,
        monotonic=monotonic,
        progress=progress,
    )
    single = search.single_shot_receipt()
    backfill = search.citation_title_backfill_receipt()
    validate_cross_artifacts(
        parent.result,
        arm=arm,
        model_slot_receipt=parent.model_slot_receipt,
        transport_health=parent.transport_health,
        search_single_shot_receipt=single,
        citation_title_backfill_receipt=backfill,
        expected_cap=int(parent.model_slot_receipt["slot_cap"]),
    )
    return IntegratedBackfillTaskOutcome(
        copy.deepcopy(parent.result),
        copy.deepcopy(parent.model_slot_receipt),
        copy.deepcopy(parent.transport_health),
        copy.deepcopy(single),
        copy.deepcopy(backfill),
    )


def build_envelope(
    outcome: IntegratedBackfillTaskOutcome, *, arm: str
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
        "citation_title_backfill_receipt": copy.deepcopy(
            outcome.citation_title_backfill_receipt
        ),
        "private_task_content_present": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_evaluator_called_by_envelope_builder": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    return validate_envelope(value)


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "result",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "citation_title_backfill_receipt",
        "private_task_content_present",
        "private_task_content_emitted_to_public_aggregate",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_evaluator_called_by_envelope_builder",
        "envelope_payload_sha256",
    }
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("envelope_payload_sha256", None)
    arm = str(copied.get("arm", ""))
    model = copied.get("model_slot_receipt")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ENVELOPE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or arm not in {"baseline", "candidate"}
        or not isinstance(copied.get("result"), Mapping)
        or not isinstance(model, Mapping)
        or not isinstance(copied.get("transport_health"), Mapping)
        or not isinstance(copied.get("search_single_shot_receipt"), Mapping)
        or not isinstance(copied.get("citation_title_backfill_receipt"), Mapping)
        or copied.get("private_task_content_present") is not True
        or copied.get("private_task_content_emitted_to_public_aggregate") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_evaluator_called_by_envelope_builder") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.29 task envelope drifted")
    validate_v24318_result(copied["result"], arm)
    validate_cross_artifacts(
        copied["result"],
        arm=arm,
        model_slot_receipt=model,
        transport_health=copied["transport_health"],
        search_single_shot_receipt=copied["search_single_shot_receipt"],
        citation_title_backfill_receipt=copied["citation_title_backfill_receipt"],
        expected_cap=int(model.get("slot_cap", -1)),
    )
    return copied


__all__ = [
    "ENVELOPE_ROLE",
    "IntegratedBackfillTaskOutcome",
    "POLICY_ID",
    "build_envelope",
    "run_v24629_task",
    "validate_cross_artifacts",
    "validate_envelope",
]
