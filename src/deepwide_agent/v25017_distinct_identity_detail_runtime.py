"""Production-shaped multi-row detail runtime with distinct-identity credit.

This append-only wrapper reuses the frozen V2.50.02 paired runner code object
in a private globals mapping.  Its only algorithm replacement is the pure
V2.50.15 selector.  The parent compatibility receipt's historical "bound
link" counters are deliberately populated with V2.50.15 *new distinct visible
identity* counters, never raw link counts; the outer receipt binds this mapping
back to the full V2.50.15 content-free receipt.

Both phases require V2.50.16 search clients, so fetched detail pages use the
V2.50.14 per-page multi-identity projector under the unchanged V2.49.81 hard
deadline boundary.  Planning, search responses, first-wave bytes, URL-union
fetch, evidence rendering, synthesis, normalization, budgets, deadlines,
costs, and failure paths remain V2.50.02-identical.  Context-local receipt
pairs keep concurrent tasks isolated and parent module globals are untouched.

Runtime task input remains exactly ``opaque_id`` and ``question``.  No label,
mapping, gold, evaluator, score, reward, historical result, or credential is
accepted.  Entropy/information gain remain shadow-only and assign no credit.
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
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v25015_distinct_identity_child_selection import (
    select_distinct_identity_child_prefixes,
    validate_receipt as validate_distinct_receipt,
)
from .v25016_multi_identity_detail_fetch import MultiIdentityDetailSearchClient


POLICY_ID = "v25017_distinct_identity_multi_detail_runtime_v1"
ROLE = "v25017_distinct_identity_multi_detail_runtime_result"
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
] = ContextVar("v25017_selection_pairs", default=())


def _compatibility_receipt(distinct: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_distinct_receipt(distinct)
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
            # These four fields are a compatibility wire format only.  The
            # outer receipt proves that they are distinct-identity counts.
            "identity_authority_bound_visible_link_count": value[
                "available_uncovered_attested_distinct_identity_count"
            ],
            "control_selected_visible_link_count": value[
                "control_selected_visible_link_count"
            ],
            "candidate_selected_visible_link_count": value[
                "candidate_selected_visible_link_count"
            ],
            "control_bound_visible_link_count": value[
                "control_new_distinct_identity_count"
            ],
            "candidate_bound_visible_link_count": value[
                "candidate_new_distinct_identity_count"
            ],
            "bound_visible_link_gain": value["new_distinct_identity_gain"],
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
    selected = select_distinct_identity_child_prefixes(
        first_wave_page_batches,
        second_wave_raw,
        question=question,
        cap=cap,
        exclude_urls=exclude_urls,
    )
    distinct_receipt = copy.deepcopy(selected["content_free_receipt"])
    compatible = _compatibility_receipt(distinct_receipt)
    _SELECTION_PAIRS.set(
        (*_SELECTION_PAIRS.get(), (distinct_receipt, copy.deepcopy(compatible)))
    )
    result: dict[str, Any] = {
        "artifact_version": 1,
        "policy_id": compatibility.POLICY_ID,
        "shared_search_prefix": copy.deepcopy(selected["shared_search_prefix"]),
        "control_visible_links": copy.deepcopy(selected["control_visible_links"]),
        "candidate_visible_links": copy.deepcopy(selected["candidate_visible_links"]),
        "control": copy.deepcopy(selected["control"]),
        "candidate": copy.deepcopy(selected["candidate"]),
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
    name="_v25017_run_second_wave",
)
_RUN_PARENT_TASK = _clone(
    _ORIGINAL_PARENT_RUNNER,
    {
        "select_page_visible_link_prefixes": _select_compatible,
        "_run_second_wave": _RUN_SECOND_WAVE,
    },
    name="_v25017_run_parent_task",
)


def _matching_distinct_receipt(
    parent_selection: Mapping[str, Any],
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> dict[str, Any]:
    matches = [
        copy.deepcopy(dict(distinct))
        for distinct, compatible in pairs
        if dict(compatible) == dict(parent_selection)
    ]
    if not matches:
        raise RuntimeError("V2.50.17 parent selection has no distinct binding")
    return validate_distinct_receipt(matches[-1])


def _validate_distinct_binding(
    parent_result: Mapping[str, Any], distinct: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_distinct_receipt(distinct)
    compatible = _compatibility_receipt(checked)
    parent_selection = parent_result["selection_receipt"]
    main = parent_result["content_free_receipt"]
    control = main["arm_metrics"][CONTROL_ARM]
    candidate = main["arm_metrics"][CANDIDATE_ARM]
    if (
        compatible != parent_selection
        or main["visible_link_strategy_eligible"] != checked["strategy_eligible"]
        or main["selection_changed"] is not bool(checked["selection_changed"])
        or main["bound_visible_link_gain"] != checked["new_distinct_identity_gain"]
        or control["second_wave_bound_visible_links"]
        != checked["control_new_distinct_identity_count"]
        or candidate["second_wave_bound_visible_links"]
        != checked["candidate_new_distinct_identity_count"]
        or checked["available_uncovered_attested_distinct_identity_count"]
        > checked["visible_identity_count"]
    ):
        raise ValueError("V2.50.17 distinct/parent selection binding drifted")
    return checked


def _envelope(
    parent_result: Mapping[str, Any],
    *,
    distinct_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    validated_parent = parent.validate_result(parent_result)
    distinct = _validate_distinct_binding(validated_parent, distinct_receipt)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(validated_parent),
        "distinct_identity_selection_receipt": copy.deepcopy(distinct),
        "parent_compatibility_bound_counts_are_new_distinct_identity_counts": True,
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
    searches: Mapping[str, MultiIdentityDetailSearchClient],
    limits: ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], MultiIdentityDetailSearchClient)
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.50.17 requires two distinct multi-identity clients")
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
        distinct = _matching_distinct_receipt(
            parent_result["selection_receipt"], _SELECTION_PAIRS.get()
        )
        return _envelope(parent_result, distinct_receipt=distinct)
    finally:
        _SELECTION_PAIRS.reset(token)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    parent_result = copied.get("parent_result")
    distinct = copied.get("distinct_identity_selection_receipt")
    true_flags = (
        "parent_compatibility_bound_counts_are_new_distinct_identity_counts",
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
        "distinct_identity_selection_receipt",
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
        or not isinstance(distinct, Mapping)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.17 runtime envelope drifted")
    validated_parent = parent.validate_result(parent_result)
    copied["parent_result"] = validated_parent
    copied["distinct_identity_selection_receipt"] = _validate_distinct_binding(
        validated_parent, distinct
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
            MultiIdentityDetailSearchClient, parent.RobustLatePageBoundSearchClient
        )
    ):
        raise RuntimeError("V2.50.17 private parent binding drifted")


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
