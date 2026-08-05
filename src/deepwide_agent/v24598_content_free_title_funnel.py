"""Content-free title transport funnel at the pre-selection lead boundary.

V2.45.96 observed 885 visible leads and 120 URL-surface hits, but no strict
title-surface hit.  Its public aggregate cannot tell whether titles were
empty, lacked a visible-row surface, placed that surface after the frozen
start limit, or failed the unchanged organization-type compatibility check.

This execution-scoped observer wraps V2.45.72's single source-selection
boundary.  It forwards the exact original selection result and records only
fixed-vocabulary integer counts.  It emits no row, title, query, URL, source,
page, value, prediction, or credential and changes no query, search, fetch,
ranking, validator, evidence, posterior, entropy, or decision-credit rule.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any

from . import v24523_conservative_alias_title_projection as validator
from . import v24547_alias_surface_observability as surface
from . import v24572_validator_aligned_alias_lead_selection as selection


POLICY_ID = "v24598_content_free_title_transport_funnel_v1"
EXPECTED_BINDING_COUNT = 1
ORIGINAL_SELECTION = selection._selection
_BINDING_GUARD = threading.Lock()

COUNT_FIELDS = (
    "selection_calls",
    "visible_input_lead_count",
    "distinct_visible_lead_count",
    "empty_title_lead_count",
    "nonempty_title_lead_count",
    "nonempty_title_without_canonical_row_token_lead_count",
    "canonical_row_token_anywhere_title_lead_count",
    "alias_surface_anywhere_title_lead_count",
    "full_or_core_surface_anywhere_title_lead_count",
    "strict_validator_aligned_title_lead_count",
    "surface_rejected_only_by_maximum_start_lead_count",
    "surface_rejected_only_by_type_compatibility_lead_count",
)
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "predecessor_policy_id",
        "binding_count",
        *COUNT_FIELDS,
        "observed_once_before_source_dedup_ranking_and_budget_cut",
        "selection_output_preserved_exactly",
        "classification_uses_visible_row_and_search_result_title_only",
        "empty_absent_late_type_incompatible_and_strict_stages_separated",
        "raw_row_title_query_url_source_page_value_prediction_or_credential_emitted",
        "query_search_fetch_ranking_validator_evidence_posterior_entropy_and_credit_changed",
        "cache_or_cross_task_state_used",
        "bindings_restored",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.45.98 {label} is invalid")
    return value


def classify_title_funnel(lead: Mapping[str, Any], row: str) -> dict[str, bool]:
    """Classify one visible lead without returning any content."""

    row_tokens = validator._canonical_tokens(row)
    title_tokens = validator._canonical_tokens(str(lead.get("title", "")))
    candidates = validator._candidate_aliases(row_tokens)
    matches: list[tuple[str, tuple[str, ...], int]] = []
    for mode, alias_tokens in candidates:
        start = validator.title._subsequence_start(title_tokens, alias_tokens)
        if start is not None:
            matches.append((mode, tuple(alias_tokens), start))
    strict = surface._matching_modes(
        title_tokens,
        row,
        maximum_start=validator.MAXIMUM_ALIAS_MATCH_START,
    )
    strict_hit = bool(strict)
    rejected_start = not strict_hit and any(
        start > validator.MAXIMUM_ALIAS_MATCH_START
        and validator._type_compatible(
            row_tokens,
            title_tokens,
            mode=mode,
            alias_tokens=alias_tokens,
            start=start,
        )
        for mode, alias_tokens, start in matches
    )
    rejected_type = not strict_hit and any(
        start <= validator.MAXIMUM_ALIAS_MATCH_START
        and not validator._type_compatible(
            row_tokens,
            title_tokens,
            mode=mode,
            alias_tokens=alias_tokens,
            start=start,
        )
        for mode, alias_tokens, start in matches
    )
    nonempty = bool(title_tokens)
    row_token = nonempty and any(token in title_tokens for token in row_tokens)
    full_or_core = any(
        mode in validator.ALIAS_MODES[:2] for mode, _alias, _start in matches
    )
    return {
        "empty_title": not nonempty,
        "nonempty_title": nonempty,
        "nonempty_title_without_canonical_row_token": nonempty and not row_token,
        "canonical_row_token_anywhere_title": row_token,
        "alias_surface_anywhere_title": bool(matches),
        "full_or_core_surface_anywhere_title": full_or_core,
        "strict_validator_aligned_title": strict_hit,
        "surface_rejected_only_by_maximum_start": rejected_start,
        "surface_rejected_only_by_type_compatibility": rejected_type,
    }


class ContentFreeTitleFunnel(
    AbstractContextManager["ContentFreeTitleFunnel"]
):
    """Observe each complete visible lead vector once without changing it."""

    def __init__(self) -> None:
        self._active = False
        self._acquired = False
        self._installed: Any = None
        self._lock = threading.RLock()
        self._stats = {name: 0 for name in COUNT_FIELDS}

    def _select(
        self,
        leads: Sequence[Mapping[str, Any]],
        plan: Mapping[str, Any],
        *,
        excluded_sources: set[str],
    ) -> tuple[list[dict[str, str]], dict[str, int]]:
        output = ORIGINAL_SELECTION(
            leads, plan, excluded_sources=excluded_sources
        )
        projected = [selection._lead_projection(item) for item in leads]
        row = str(plan["row_key"])
        classified = [classify_title_funnel(item, row) for item in projected]
        distinct = {
            (item["url"], item["title"], item["query"])
            for item in projected
        }
        additions = {
            "selection_calls": 1,
            "visible_input_lead_count": len(projected),
            "distinct_visible_lead_count": len(distinct),
            **{
                f"{name}_lead_count": sum(item[name] for item in classified)
                for name in (
                    "empty_title",
                    "nonempty_title",
                    "nonempty_title_without_canonical_row_token",
                    "canonical_row_token_anywhere_title",
                    "alias_surface_anywhere_title",
                    "full_or_core_surface_anywhere_title",
                    "strict_validator_aligned_title",
                    "surface_rejected_only_by_maximum_start",
                    "surface_rejected_only_by_type_compatibility",
                )
            },
        }
        with self._lock:
            for name, value in additions.items():
                self._stats[name] += value
        return output

    def __enter__(self) -> "ContentFreeTitleFunnel":
        if self._active or not _BINDING_GUARD.acquire(blocking=False):
            raise RuntimeError("V2.45.98 title-funnel context is already active")
        self._acquired = True
        if selection._selection is not ORIGINAL_SELECTION:
            _BINDING_GUARD.release()
            self._acquired = False
            raise RuntimeError("V2.45.98 frozen selection binding drifted")
        self._installed = self._select
        selection._selection = self._installed
        self._active = True
        return self

    def __exit__(self, *_: object) -> None:
        drifted = False
        try:
            if self._active:
                drifted = selection._selection is not self._installed
                selection._selection = ORIGINAL_SELECTION
                self._active = False
                self._installed = None
        finally:
            if self._acquired:
                self._acquired = False
                _BINDING_GUARD.release()
        if drifted:
            raise RuntimeError("V2.45.98 installed selection binding drifted")

    def content_free_receipt(self) -> dict[str, Any]:
        return {
            "policy_id": POLICY_ID,
            "predecessor_policy_id": selection.POLICY_ID,
            "binding_count": EXPECTED_BINDING_COUNT,
            **dict(self._stats),
            "observed_once_before_source_dedup_ranking_and_budget_cut": True,
            "selection_output_preserved_exactly": True,
            "classification_uses_visible_row_and_search_result_title_only": True,
            "empty_absent_late_type_incompatible_and_strict_stages_separated": True,
            "raw_row_title_query_url_source_page_value_prediction_or_credential_emitted": False,
            "query_search_fetch_ranking_validator_evidence_posterior_entropy_and_credit_changed": False,
            "cache_or_cross_task_state_used": False,
            "bindings_restored": not self._active and not self._acquired,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    true_fields = (
        "observed_once_before_source_dedup_ranking_and_budget_cut",
        "selection_output_preserved_exactly",
        "classification_uses_visible_row_and_search_result_title_only",
        "empty_absent_late_type_incompatible_and_strict_stages_separated",
        "bindings_restored",
    )
    false_fields = (
        "raw_row_title_query_url_source_page_value_prediction_or_credential_emitted",
        "query_search_fetch_ranking_validator_evidence_posterior_entropy_and_credit_changed",
        "cache_or_cross_task_state_used",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    )
    visible = copied.get("visible_input_lead_count", -1)
    nonempty = copied.get("nonempty_title_lead_count", -1)
    row_token = copied.get("canonical_row_token_anywhere_title_lead_count", -1)
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("predecessor_policy_id") != selection.POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or any(_count(copied.get(name), name) < 0 for name in COUNT_FIELDS)
        or copied["distinct_visible_lead_count"] > visible
        or copied["empty_title_lead_count"] + nonempty != visible
        or copied["nonempty_title_without_canonical_row_token_lead_count"]
        + row_token
        != nonempty
        or copied["alias_surface_anywhere_title_lead_count"] > nonempty
        or copied["full_or_core_surface_anywhere_title_lead_count"]
        > copied["alias_surface_anywhere_title_lead_count"]
        or copied["strict_validator_aligned_title_lead_count"]
        > copied["alias_surface_anywhere_title_lead_count"]
        or copied["surface_rejected_only_by_maximum_start_lead_count"]
        > copied["alias_surface_anywhere_title_lead_count"]
        or copied["surface_rejected_only_by_type_compatibility_lead_count"]
        > copied["alias_surface_anywhere_title_lead_count"]
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.98 title-funnel receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS",
    "POLICY_ID",
    "ContentFreeTitleFunnel",
    "classify_title_funnel",
    "validate_receipt",
]
