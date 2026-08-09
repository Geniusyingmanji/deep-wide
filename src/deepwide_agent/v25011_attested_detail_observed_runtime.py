"""Production-shaped attested-child runtime with detail-stage observation.

This module reuses the frozen V2.50.02 paired runner's audited code object in a
private globals mapping.  Only its pure selector and second-wave selector
binding are replaced; the parent module globals are never mutated.  Context-
local receipt pairs keep concurrent tasks isolated.

Planning, search, URL-union fetch, page partitioning, evidence rendering,
synthesis, normalization, budgets, deadlines, costs, failures, and the full
parent result validator remain V2.50.02-identical.  Search clients must be the
append-only V2.50.09 observed detail clients.  The outer envelope binds the
V2.50.10 attested-child receipt and both V2.50.09 stage receipts to the exact
validated parent result.  Entropy/IG remain shadow-only and assign no credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from types import FunctionType
from typing import Any

from . import v25001_page_visible_link_selection as compatibility
from . import v25002_page_visible_link_paired_runtime as parent
from .clients import canonicalize_url
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v25009_detail_stage_observer_fetch import (
    DetailStageObservedSearchClient,
    validate_observer_receipt,
)
from .v25010_attested_child_detail_selection import (
    select_attested_child_detail_prefixes,
    validate_receipt as validate_attested_receipt,
)


POLICY_ID = "v25011_attested_child_detail_observed_runtime_v1"
ROLE = "v25011_attested_child_detail_observed_runtime_result"
ARMS = parent.ARMS
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM
FIRST_PHASE = parent.FIRST_PHASE
SECOND_PHASE = parent.SECOND_PHASE
PHASES = parent.PHASES
_ORIGINAL_PARENT_SELECTOR = parent.select_page_visible_link_prefixes
_ORIGINAL_PARENT_SECOND_WAVE = parent._run_second_wave
_ORIGINAL_PARENT_RUNNER = parent.run_paired_task
_SELECTION_PAIRS: ContextVar[
    tuple[tuple[dict[str, Any], dict[str, Any]], ...]
] = ContextVar("v25011_selection_pairs", default=())


def _compatibility_receipt(attested: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_attested_receipt(attested)
    return compatibility._receipt(
        {
            "prefix_cap": value["prefix_cap"],
            "original_response_selected_url_count": value[
                "original_response_selected_url_count"
            ],
            "original_response_query_local_url_count": value[
                "original_response_query_local_url_count"
            ],
            "raw_first_wave_page_count": value["raw_first_wave_page_count"],
            "raw_page_visible_link_count": value["raw_page_visible_link_count"],
            "resolved_public_http_link_count": value[
                "resolved_public_http_link_count"
            ],
            "rejected_invalid_or_non_http_link_count": value[
                "rejected_invalid_or_non_http_link_count"
            ],
            "rejected_private_or_credential_link_count": value[
                "rejected_private_or_credential_link_count"
            ],
            "unique_visible_link_count_before_exclusion": value[
                "unique_visible_link_count_before_exclusion"
            ],
            "excluded_original_or_selected_link_count": value[
                "excluded_original_or_selected_link_count"
            ],
            "available_visible_link_count": value["available_visible_link_count"],
            "visible_link_prefix_cap": value["visible_link_prefix_cap"],
            "identity_authority_bound_visible_link_count": value[
                "available_attested_child_detail_link_count"
            ],
            "control_selected_visible_link_count": value[
                "control_selected_visible_link_count"
            ],
            "candidate_selected_visible_link_count": value[
                "candidate_selected_visible_link_count"
            ],
            "control_bound_visible_link_count": value[
                "control_attested_child_detail_link_count"
            ],
            "candidate_bound_visible_link_count": value[
                "candidate_attested_child_detail_link_count"
            ],
            "bound_visible_link_gain": value["attested_child_detail_link_gain"],
            "control_total_selected_url_count": value[
                "control_total_selected_url_count"
            ],
            "candidate_total_selected_url_count": value[
                "candidate_total_selected_url_count"
            ],
            "selection_changed": value["selection_changed"],
            "strategy_eligible": value["strategy_eligible"],
            "mechanism_engaged": value["mechanism_engaged"],
        }
    )


def _select_compatible(
    first_wave_page_batches: object,
    second_wave_raw: object,
    *,
    question: str,
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    attested = select_attested_child_detail_prefixes(
        first_wave_page_batches,
        second_wave_raw,
        question=question,
        cap=cap,
        exclude_urls=exclude_urls,
    )
    attested_receipt = copy.deepcopy(attested["content_free_receipt"])
    compatible = _compatibility_receipt(attested_receipt)
    _SELECTION_PAIRS.set(
        (*_SELECTION_PAIRS.get(), (attested_receipt, copy.deepcopy(compatible)))
    )
    result: dict[str, Any] = {
        "artifact_version": 1,
        "policy_id": compatibility.POLICY_ID,
        "shared_search_prefix": copy.deepcopy(attested["shared_search_prefix"]),
        "control_visible_links": copy.deepcopy(attested["control_visible_links"]),
        "candidate_visible_links": copy.deepcopy(attested["candidate_visible_links"]),
        "control": copy.deepcopy(attested["control"]),
        "candidate": copy.deepcopy(attested["candidate"]),
        "content_free_receipt": compatible,
    }
    result["artifact_payload_sha256"] = hashlib.sha256(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return result


def _clone(function: Any, replacements: Mapping[str, Any], *, name: str) -> Any:
    namespace = dict(function.__globals__)
    namespace.update(dict(replacements))
    cloned = FunctionType(
        function.__code__,
        namespace,
        name=name,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    cloned.__kwdefaults__ = copy.deepcopy(function.__kwdefaults__)
    cloned.__annotations__ = copy.deepcopy(function.__annotations__)
    return cloned


_RUN_SECOND_WAVE = _clone(
    _ORIGINAL_PARENT_SECOND_WAVE,
    {"select_page_visible_link_prefixes": _select_compatible},
    name="_v25011_run_second_wave",
)
_RUN_PARENT_TASK = _clone(
    _ORIGINAL_PARENT_RUNNER,
    {
        "select_page_visible_link_prefixes": _select_compatible,
        "_run_second_wave": _RUN_SECOND_WAVE,
    },
    name="_v25011_run_parent_task",
)


def _matching_attested_receipt(
    parent_selection: Mapping[str, Any],
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> dict[str, Any]:
    matches = [
        copy.deepcopy(dict(attested))
        for attested, compatible in pairs
        if dict(compatible) == dict(parent_selection)
    ]
    if not matches:
        raise RuntimeError("V2.50.11 parent selection has no attested binding")
    return validate_attested_receipt(matches[-1])


def _validate_observer_bindings(
    parent_result: Mapping[str, Any],
    observers: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    if set(observers) != set(PHASES):
        raise ValueError("V2.50.11 observer phase set drifted")
    output = {
        phase: validate_observer_receipt(observers[phase]) for phase in PHASES
    }
    phases = parent_result["physical_wave_receipts"]
    effects = parent_result["physical_effects"]
    for phase in PHASES:
        observed = output[phase]
        if observed["parent_fetch_calls_snapshot"] != effects[phase]["fetch_requests"]:
            raise ValueError("V2.50.11 observer/fetch effect binding drifted")
        phase_receipt = phases[phase]
        if phase_receipt is not None:
            parent_fetch = phase_receipt["fetch_receipt"]
            if (
                observed["parent_helper_result_count"]
                != parent_fetch["helper_result_count"]
                or observed["observed_detail_receipt_count"]
                != parent_fetch["projected_page_count"]
                or observed["input_content_characters"]
                != parent_fetch["input_content_characters"]
                or observed["discovered_record_count"]
                != parent_fetch["discovered_record_count"]
                or observed["retained_record_count"]
                != parent_fetch["retained_record_count"]
                or observed["compact_prefix_characters"]
                != parent_fetch["compact_prefix_characters"]
                or observed["projection_failure_count"]
                != parent_fetch["projection_failure_count"]
                or observed["positive_signed_credit_count"] != 0
                or observed["invalid_observer_envelope_count"] != 0
            ):
                raise ValueError("V2.50.11 observer/parent receipt binding drifted")
    return output


def _validate_attested_binding(
    parent_result: Mapping[str, Any], attested: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_attested_receipt(attested)
    compatible = _compatibility_receipt(checked)
    parent_selection = parent_result["selection_receipt"]
    main = parent_result["content_free_receipt"]
    if (
        compatible != parent_selection
        or main["visible_link_strategy_eligible"] != checked["strategy_eligible"]
        or main["selection_changed"] is not bool(checked["selection_changed"])
        or main["bound_visible_link_gain"]
        != checked["attested_child_detail_link_gain"]
        or checked["available_attested_child_detail_link_count"]
        > checked["available_visible_link_count"]
    ):
        raise ValueError("V2.50.11 attested/parent selection binding drifted")
    return checked


def _envelope(
    parent_result: Mapping[str, Any],
    *,
    attested_receipt: Mapping[str, Any],
    observer_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    validated_parent = parent.validate_result(parent_result)
    attested = _validate_attested_binding(validated_parent, attested_receipt)
    observers = _validate_observer_bindings(validated_parent, observer_receipts)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(validated_parent),
        "attested_selection_receipt": copy.deepcopy(attested),
        "detail_stage_observer_receipts": copy.deepcopy(observers),
        "parent_runner_code_object_reused_without_parent_global_mutation": True,
        "selection_receipts_context_local_for_concurrent_tasks": True,
        "same_planning_search_fetch_evidence_synthesis_normalizer_budget_deadline_and_failure_path_as_parent": True,
        "parent_result_and_parent_projection_receipts_unmodified": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "additional_search_fetch_model_token_context_byte_process_retry_wall_or_network_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, DetailStageObservedSearchClient],
    limits: ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], DetailStageObservedSearchClient)
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.50.11 requires two distinct observed detail clients")
    token = _SELECTION_PAIRS.set(())
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "searches": searches,
            "limits": limits,
            "arm_order": arm_order,
        }
        if monotonic is not None:
            kwargs["monotonic"] = monotonic
        parent_result = _RUN_PARENT_TASK(task, **kwargs)
        pairs = _SELECTION_PAIRS.get()
        attested = _matching_attested_receipt(
            parent_result["selection_receipt"], pairs
        )
        observers = {
            phase: searches[phase].detail_stage_observer_receipt()
            for phase in PHASES
        }
        return _envelope(
            parent_result,
            attested_receipt=attested,
            observer_receipts=observers,
        )
    finally:
        _SELECTION_PAIRS.reset(token)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    parent_result = copied.get("parent_result")
    attested = copied.get("attested_selection_receipt")
    observers = copied.get("detail_stage_observer_receipts")
    true_flags = (
        "parent_runner_code_object_reused_without_parent_global_mutation",
        "selection_receipts_context_local_for_concurrent_tasks",
        "same_planning_search_fetch_evidence_synthesis_normalizer_budget_deadline_and_failure_path_as_parent",
        "parent_result_and_parent_projection_receipts_unmodified",
        "entropy_information_gain_shadow_only",
    )
    false_flags = (
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_token_context_byte_process_retry_wall_or_network_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "attested_selection_receipt",
        "detail_stage_observer_receipts",
        *true_flags,
        *false_flags,
        "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(parent_result, Mapping)
        or not isinstance(attested, Mapping)
        or not isinstance(observers, Mapping)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.11 observed runtime envelope drifted")
    validated_parent = parent.validate_result(parent_result)
    copied["parent_result"] = validated_parent
    copied["attested_selection_receipt"] = _validate_attested_binding(
        validated_parent, attested
    )
    copied["detail_stage_observer_receipts"] = _validate_observer_bindings(
        validated_parent, observers
    )
    return copied


def validate_binding() -> None:
    if (
        parent.select_page_visible_link_prefixes is not _ORIGINAL_PARENT_SELECTOR
        or parent._run_second_wave is not _ORIGINAL_PARENT_SECOND_WAVE
        or parent.run_paired_task is not _ORIGINAL_PARENT_RUNNER
        or _RUN_PARENT_TASK.__code__ is not _ORIGINAL_PARENT_RUNNER.__code__
        or _RUN_SECOND_WAVE.__code__ is not _ORIGINAL_PARENT_SECOND_WAVE.__code__
        or _RUN_PARENT_TASK.__globals__["select_page_visible_link_prefixes"]
        is not _select_compatible
        or _RUN_PARENT_TASK.__globals__["_run_second_wave"] is not _RUN_SECOND_WAVE
        or _RUN_SECOND_WAVE.__globals__["select_page_visible_link_prefixes"]
        is not _select_compatible
        or not issubclass(
            DetailStageObservedSearchClient, parent.RobustLatePageBoundSearchClient
        )
    ):
        raise RuntimeError("V2.50.11 private parent binding drifted")


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "PHASES",
    "POLICY_ID",
    "ROLE",
    "SECOND_PHASE",
    "run_paired_task",
    "validate_binding",
    "validate_result",
]
