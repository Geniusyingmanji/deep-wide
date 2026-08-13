"""Deadline-aligned successor for the World Bank monotone-fill gate.

V2.53.09 failed before any provider/search/fetch effect because the native
runner requires the model limiter and search transport to share the exact
absolute deadline, cleanup reserve, and minimum-attempt window.  The frozen
snapshot search inherited ``0.01`` seconds while the model limiter used
``0.05`` seconds.

This append-only successor changes only the in-memory snapshot transport's
minimum-attempt attribute immediately after its no-effect constructor.  It
then checks the inherited runner's exact deadline-identity predicate before
delegating to the frozen pipe-schema/monotone-fill runtime.  It has no live
network, filesystem, benchmark label, evaluator, or historical-result
capability.  Entropy/information gain remains shadow-only and signed credit 0.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from . import v25309_pipe_visible_schema_worldbank_gate as parent
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24319_runner_integration import _aligned_deadlines
from .v24859_full_evidence_coverage_revision import EvidencePage


POLICY_ID = "v25313_deadline_aligned_worldbank_monotone_fill_v1"
RECEIPT_ROLE = "v25313_content_free_deadline_identity_receipt"
MINIMUM_ATTEMPT_SECONDS = 0.05
CLEANUP_RESERVE_SECONDS = 5.0


class DeadlineAlignedFrozenWorldBankSnapshotSearchClient(
    parent.FrozenWorldBankSnapshotSearchClient
):
    """The frozen eight-page facade with runner-identical deadline settings."""

    def __init__(
        self,
        pages: Sequence[Mapping[str, Any]],
        *,
        absolute_deadline: float,
        monotonic: Callable[[], float],
    ) -> None:
        super().__init__(
            pages, absolute_deadline=absolute_deadline, monotonic=monotonic
        )
        if (
            float(self.cleanup_reserve_seconds) != CLEANUP_RESERVE_SECONDS
            or float(self.minimum_attempt_seconds) != 0.01
            or int(self._snapshot_search_invocations) != 0
            or int(self._snapshot_fetch_hits) != 0
        ):
            raise ValueError("V2.53.13 frozen snapshot parent drifted")
        # Construction performs no search/fetch/provider effect.  Align the
        # inherited deadline parameter before the object can enter a runtime.
        self.minimum_attempt_seconds = MINIMUM_ATTEMPT_SECONDS


def deadline_identity_receipt(
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: DeadlineAlignedFrozenWorldBankSnapshotSearchClient,
) -> dict[str, Any]:
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.53.13 requires the native global model limiter")
    if not isinstance(search, DeadlineAlignedFrozenWorldBankSnapshotSearchClient):
        raise ValueError("V2.53.13 requires the aligned frozen snapshot search")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "absolute_deadline_equal": abs(
            float(model.absolute_deadline) - float(search.absolute_deadline)
        )
        <= 1e-6,
        "cleanup_reserve_seconds_model_micros": round(
            float(model.cleanup_reserve_seconds) * 1_000_000
        ),
        "cleanup_reserve_seconds_search_micros": round(
            float(search.cleanup_reserve_seconds) * 1_000_000
        ),
        "minimum_attempt_seconds_model_micros": round(
            float(model.minimum_attempt_seconds) * 1_000_000
        ),
        "minimum_attempt_seconds_search_micros": round(
            float(search.minimum_attempt_seconds) * 1_000_000
        ),
        "aligned_deadlines": bool(_aligned_deadlines(model, search)),
        "checked_before_model_search_or_fetch_effect": (
            int(model.receipt()["acquisitions"]) == 0
            and int(search.snapshot_transport_receipt()["search_invocations"]) == 0
            and int(search.snapshot_transport_receipt()["fetch_hits"]) == 0
        ),
        "contains_question_query_url_page_value_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = parent.payload_sha256(value)
    return validate_deadline_identity_receipt(value)


def validate_deadline_identity_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("receipt_payload_sha256", None)
    integer_fields = (
        "cleanup_reserve_seconds_model_micros",
        "cleanup_reserve_seconds_search_micros",
        "minimum_attempt_seconds_model_micros",
        "minimum_attempt_seconds_search_micros",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "absolute_deadline_equal",
            *integer_fields,
            "aligned_deadlines",
            "checked_before_model_search_or_fetch_effect",
            "contains_question_query_url_page_value_prediction_answer_opaque_id_or_credential",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] <= 0
            for name in integer_fields
        )
        or copied.get("absolute_deadline_equal") is not True
        or copied.get("cleanup_reserve_seconds_model_micros")
        != copied.get("cleanup_reserve_seconds_search_micros")
        or copied.get("cleanup_reserve_seconds_model_micros") != 5_000_000
        or copied.get("minimum_attempt_seconds_model_micros")
        != copied.get("minimum_attempt_seconds_search_micros")
        or copied.get("minimum_attempt_seconds_model_micros") != 50_000
        or copied.get("aligned_deadlines") is not True
        or copied.get("checked_before_model_search_or_fetch_effect") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "contains_question_query_url_page_value_prediction_answer_opaque_id_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or signature != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.13 deadline identity receipt drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: DeadlineAlignedFrozenWorldBankSnapshotSearchClient,
    limits: Any,
    two_wave_policy: Any,
    monotonic: Callable[[], float],
    progress: Any = None,
) -> dict[str, Any]:
    # Validate the exact parity before parent.run_paired_task can admit a model,
    # logical search, or snapshot fetch effect.
    deadline_identity_receipt(model, search)
    return parent.run_paired_task(
        task,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
        monotonic=monotonic,
        progress=progress,
    )


candidate = parent.candidate
PAGE_COUNT = parent.PAGE_COUNT
ENTITY_ROW_COUNT = parent.ENTITY_ROW_COUNT
TARGET_COUNT = parent.TARGET_COUNT
MAXIMUM_PAGE_CHARS = parent.MAXIMUM_PAGE_CHARS
MAXIMUM_EVIDENCE_CHARS = parent.MAXIMUM_EVIDENCE_CHARS
PARENT_LIMITS = copy.deepcopy(parent.PARENT_LIMITS)
PARENT_TWO_WAVE_POLICY = copy.deepcopy(parent.PARENT_TWO_WAVE_POLICY)
PARENT_TAVILY_KEY_SLOT_CAP = parent.PARENT_TAVILY_KEY_SLOT_CAP
payload_sha256 = parent.payload_sha256
validate_paired_receipt = parent.validate_paired_receipt
validate_result = parent.validate_result
validate_snapshot_receipt = parent.validate_snapshot_receipt


__all__ = [
    "CLEANUP_RESERVE_SECONDS",
    "DeadlineAlignedFrozenWorldBankSnapshotSearchClient",
    "ENTITY_ROW_COUNT",
    "MAXIMUM_EVIDENCE_CHARS",
    "MAXIMUM_PAGE_CHARS",
    "MINIMUM_ATTEMPT_SECONDS",
    "PAGE_COUNT",
    "PARENT_LIMITS",
    "PARENT_TAVILY_KEY_SLOT_CAP",
    "PARENT_TWO_WAVE_POLICY",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "TARGET_COUNT",
    "candidate",
    "deadline_identity_receipt",
    "payload_sha256",
    "run_paired_task",
    "validate_deadline_identity_receipt",
    "validate_paired_receipt",
    "validate_result",
    "validate_snapshot_receipt",
]
