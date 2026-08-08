"""Exact-task envelope for the bounded V2.48.60 coverage revision.

The envelope preserves both the independently valid parent task artifacts and
the final post-revision model-slot receipt.  It adds no effects and has no
benchmark evaluator capability.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .v24263_global_model_limiter import payload_sha256
from .v24280_task_union_single_shot import validate_receipt as validate_single
from .v24312_deadline_reliability import validate_receipt as validate_slot
from .v24316_deadline_search import validate_transport_health
from .v24630_exact220_task_integration import (
    validate_cross_artifacts as validate_parent_cross_artifacts,
)
from .v24630_thin_backfill_search import validate_receipt as validate_backfill
from .v24860_coverage_revision_integration import (
    CoverageRevisionOutcome,
    validate_integration_receipt,
    validate_result,
)


POLICY_ID = "v24861_coverage_revision_exact_task_envelope_v1"
ENVELOPE_ROLE = "v24861_coverage_revision_exact_task_envelope"
PARENT_ARM = "baseline"


@dataclass(frozen=True)
class IntegratedCoverageRevisionTaskOutcome:
    result: dict[str, Any]
    parent_model_slot_receipt: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    citation_title_backfill_receipt: dict[str, Any]
    coverage_revision_receipt: dict[str, Any]


def integrate_parent_outcome(
    parent: Any,
    revision: CoverageRevisionOutcome,
) -> IntegratedCoverageRevisionTaskOutcome:
    required = (
        "result",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "citation_title_backfill_receipt",
    )
    if any(not hasattr(parent, name) for name in required):
        raise TypeError("V2.48.61 parent outcome schema drifted")
    value = IntegratedCoverageRevisionTaskOutcome(
        copy.deepcopy(revision.result),
        copy.deepcopy(parent.model_slot_receipt),
        copy.deepcopy(revision.final_model_slot_receipt),
        copy.deepcopy(parent.transport_health),
        copy.deepcopy(parent.search_single_shot_receipt),
        copy.deepcopy(parent.citation_title_backfill_receipt),
        copy.deepcopy(revision.integration_receipt),
    )
    validate_cross_artifacts(value)
    return value


def validate_cross_artifacts(
    outcome: IntegratedCoverageRevisionTaskOutcome,
) -> None:
    if not isinstance(outcome, IntegratedCoverageRevisionTaskOutcome):
        raise TypeError("V2.48.61 task outcome identity drifted")
    parent_slot = validate_slot(
        outcome.parent_model_slot_receipt,
        expected_cap=int(outcome.parent_model_slot_receipt.get("slot_cap", -1)),
    )
    final_slot = validate_slot(
        outcome.model_slot_receipt,
        expected_cap=int(outcome.model_slot_receipt.get("slot_cap", -1)),
    )
    if parent_slot["slot_cap"] != final_slot["slot_cap"]:
        raise ValueError("V2.48.61 model slot cap drifted")
    validate_result(
        outcome.result,
        final_model_slot_receipt=final_slot,
    )
    receipt = validate_integration_receipt(outcome.coverage_revision_receipt)
    if outcome.result["coverage_revision_receipt"] != receipt:
        raise ValueError("V2.48.61 coverage receipt copy drifted")
    validate_transport_health(outcome.transport_health)
    validate_single(outcome.search_single_shot_receipt)
    validate_backfill(outcome.citation_title_backfill_receipt)
    validate_parent_cross_artifacts(
        outcome.result["parent_result"],
        arm=PARENT_ARM,
        model_slot_receipt=parent_slot,
        transport_health=outcome.transport_health,
        search_single_shot_receipt=outcome.search_single_shot_receipt,
        citation_title_backfill_receipt=outcome.citation_title_backfill_receipt,
        expected_cap=int(parent_slot["slot_cap"]),
    )
    if (
        int(final_slot["acquisitions"])
        != int(parent_slot["acquisitions"])
        + int(receipt["model_slot_acquisition_delta"])
        or int(final_slot["slot_timeouts"])
        != int(parent_slot["slot_timeouts"])
        + int(receipt["model_slot_timeout_delta"])
        or int(final_slot["provider_deadline_failures"])
        != int(parent_slot["provider_deadline_failures"])
        + int(receipt["model_provider_deadline_failure_delta"])
    ):
        raise ValueError("V2.48.61 parent/final slot conservation drifted")


def build_envelope(
    outcome: IntegratedCoverageRevisionTaskOutcome,
    *,
    arm: str,
) -> dict[str, Any]:
    if arm != PARENT_ARM:
        raise ValueError("V2.48.61 exact task requires baseline parent arm")
    validate_cross_artifacts(outcome)
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "result": copy.deepcopy(outcome.result),
        "parent_model_slot_receipt": copy.deepcopy(
            outcome.parent_model_slot_receipt
        ),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
        "citation_title_backfill_receipt": copy.deepcopy(
            outcome.citation_title_backfill_receipt
        ),
        "coverage_revision_receipt": copy.deepcopy(
            outcome.coverage_revision_receipt
        ),
        "private_task_content_present": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_evaluator_called_by_envelope_builder": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    return validate_envelope(value)


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("envelope_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "result",
        "parent_model_slot_receipt",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "citation_title_backfill_receipt",
        "coverage_revision_receipt",
        "private_task_content_present",
        "private_task_content_emitted_to_public_aggregate",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_evaluator_called_by_envelope_builder",
        "envelope_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ENVELOPE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("arm") != PARENT_ARM
        or copied.get("private_task_content_present") is not True
        or copied.get("private_task_content_emitted_to_public_aggregate") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_evaluator_called_by_envelope_builder") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.61 envelope identity drifted")
    outcome = IntegratedCoverageRevisionTaskOutcome(
        copy.deepcopy(dict(copied["result"])),
        copy.deepcopy(dict(copied["parent_model_slot_receipt"])),
        copy.deepcopy(dict(copied["model_slot_receipt"])),
        copy.deepcopy(dict(copied["transport_health"])),
        copy.deepcopy(dict(copied["search_single_shot_receipt"])),
        copy.deepcopy(dict(copied["citation_title_backfill_receipt"])),
        copy.deepcopy(dict(copied["coverage_revision_receipt"])),
    )
    validate_cross_artifacts(outcome)
    return copied


__all__ = [
    "ENVELOPE_ROLE",
    "IntegratedCoverageRevisionTaskOutcome",
    "POLICY_ID",
    "build_envelope",
    "integrate_parent_outcome",
    "validate_cross_artifacts",
    "validate_envelope",
]
