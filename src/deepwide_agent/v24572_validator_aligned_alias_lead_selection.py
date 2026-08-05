"""Validator-aligned, source-stable alias lead selection.

V2.45.71 exposed a ranking/validation mismatch.  The acquisition layer counted
and prioritized title-or-URL alias hits, while the conservative evidence layer
requires either its unchanged exact-title route or a unique title alias anchor.
Before ranking, V2.45.47 also kept the first lead observed for each source.  A
URL-only hit could therefore hide a later title-validatable lead from the same
source, even though the latter was strictly more useful to the frozen evidence
validator.

This append-only execution-scoped policy changes only source representative
selection.  It deterministically chooses the most validator-aligned visible
lead inside each source, then applies the frozen V2.45.47 global ranking and
fetch cap.  URL matches remain retrieval hints only.  They receive no evidence,
source, entropy, epistemic, or decision credit.  Query count, search batches,
fetch cap, evidence projection, source independence, posterior, margin,
leave-one-out, safe-change, and decision-credit rules are unchanged.

The policy has no access to task labels, mapping, gold answers, evaluator data,
rewards, scores, credentials, files, environment, network, model, search,
fetch, process state, or page content.
"""

from __future__ import annotations

import copy
import threading
from collections import defaultdict
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any

from . import v24547_alias_surface_observability as surface
from .v24355_explicit_partition_runtime import _source_from_lead
from .v24371_batch_stratified_verifier_runtime import _coverage
from .v24378_adaptive_heldout_verifier_runtime import _lead_projection, _target_score


POLICY_ID = "v24572_validator_aligned_source_representative_selection_v1"
EXPECTED_BINDING_COUNT = 1
ORIGINAL_SELECT_SURFACE_SEEDED_LEADS = surface._select_surface_seeded_leads
_BINDING_GUARD = threading.Lock()

COUNT_FIELDS = (
    "selection_calls",
    "visible_input_lead_count",
    "visible_eligible_lead_count",
    "excluded_lead_count",
    "excluded_title_alias_surface_hit_lead_count",
    "excluded_url_only_alias_surface_hit_lead_count",
    "unique_eligible_source_count",
    "duplicate_source_lead_count",
    "source_representative_replacement_count",
    "validator_aligned_title_replacement_count",
    "url_only_first_representative_avoided_count",
    "selected_lead_count",
    "selected_title_alias_surface_hit_lead_count",
    "selected_url_only_alias_surface_hit_lead_count",
)
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "predecessor_policy_id",
        "binding_count",
        *COUNT_FIELDS,
        "source_representative_selected_before_global_budget_cut",
        "within_source_selection_prefers_title_surface_validator_alignment",
        "within_source_selection_is_input_order_invariant",
        "frozen_global_surface_target_coverage_and_source_ranking_preserved",
        "logical_queries_search_batches_and_fetch_cap_unchanged",
        "url_alias_hint_receives_evidence_source_entropy_or_decision_credit",
        "exact_and_alias_title_evidence_validators_unchanged",
        "source_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged",
        "cache_or_cross_task_state_used",
        "bindings_restored",
        "task_question_opaque_id_query_url_page_content_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.45.72 {label} is invalid")
    return value


def _target(plan: Mapping[str, Any]) -> dict[str, str]:
    return {
        "row_key": str(plan["row_key"]),
        "column": str(plan["column"]),
        "new_value": str(plan["leading_alternative"]),
    }


def _global_rank(
    lead: Mapping[str, Any], plan: Mapping[str, Any]
) -> tuple[Any, ...]:
    """Replay the exact V2.45.47 cross-source ordering."""

    row = str(plan["row_key"])
    match = surface.classify_alias_surface(lead, row)
    return (
        not match["surface_hit"],
        not bool(match["title_modes"]),
        tuple(-number for number in _target_score(lead, [_target(plan)])),
        tuple(-number for number in _coverage(lead, plan["query_vector"])[1]),
        _source_from_lead(lead),
    )


def _within_source_rank(
    lead: Mapping[str, Any], plan: Mapping[str, Any]
) -> tuple[Any, ...]:
    """Add stable visible-lead tie-breaks only inside one source."""

    return (
        *_global_rank(lead, plan)[:-1],
        str(lead.get("url", "")),
        str(lead.get("title", "")),
        str(lead.get("query", "")),
    )


def _selection(
    leads: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    *,
    excluded_sources: set[str],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    first_by_source: dict[str, dict[str, str]] = {}
    input_count = 0
    excluded_count = 0
    excluded_title_hits = 0
    excluded_url_only_hits = 0
    for raw in leads:
        lead = _lead_projection(raw)
        input_count += 1
        source = _source_from_lead(lead)
        if source in excluded_sources:
            excluded_count += 1
            match = surface.classify_alias_surface(lead, str(plan["row_key"]))
            excluded_title_hits += int(bool(match["title_modes"]))
            excluded_url_only_hits += int(
                bool(match["url_modes"]) and not bool(match["title_modes"])
            )
            continue
        grouped[source].append(lead)
        first_by_source.setdefault(source, lead)

    representatives = {
        source: min(items, key=lambda item: _within_source_rank(item, plan))
        for source, items in grouped.items()
    }
    row = str(plan["row_key"])
    replacements = 0
    title_replacements = 0
    url_only_avoided = 0
    for source, chosen in representatives.items():
        first = first_by_source[source]
        if chosen == first:
            continue
        replacements += 1
        chosen_match = surface.classify_alias_surface(chosen, row)
        first_match = surface.classify_alias_surface(first, row)
        if chosen_match["title_modes"] and not first_match["title_modes"]:
            title_replacements += 1
            if first_match["url_modes"]:
                url_only_avoided += 1

    ranked = sorted(representatives.values(), key=lambda lead: _global_rank(lead, plan))
    selected = [
        copy.deepcopy(item)
        for item in ranked[: int(plan["maximum_targeted_fetches"])]
    ]
    selected_matches = [surface.classify_alias_surface(item, row) for item in selected]
    visible = sum(len(items) for items in grouped.values())
    unique = len(grouped)
    diagnostic = {
        "visible_input_lead_count": input_count,
        "visible_eligible_lead_count": visible,
        "excluded_lead_count": excluded_count,
        "excluded_title_alias_surface_hit_lead_count": excluded_title_hits,
        "excluded_url_only_alias_surface_hit_lead_count": excluded_url_only_hits,
        "unique_eligible_source_count": unique,
        "duplicate_source_lead_count": visible - unique,
        "source_representative_replacement_count": replacements,
        "validator_aligned_title_replacement_count": title_replacements,
        "url_only_first_representative_avoided_count": url_only_avoided,
        "selected_lead_count": len(selected),
        "selected_title_alias_surface_hit_lead_count": sum(
            bool(item["title_modes"]) for item in selected_matches
        ),
        "selected_url_only_alias_surface_hit_lead_count": sum(
            bool(item["url_modes"]) and not bool(item["title_modes"])
            for item in selected_matches
        ),
    }
    return selected, diagnostic


def select_validator_aligned_leads(
    leads: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    *,
    excluded_sources: set[str],
) -> list[dict[str, str]]:
    selected, _diagnostic = _selection(
        leads, plan, excluded_sources=excluded_sources
    )
    return selected


class ValidatorAlignedAliasLeadSelection(
    AbstractContextManager["ValidatorAlignedAliasLeadSelection"]
):
    """Install source-stable representative selection for one worker call."""

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
    ) -> list[dict[str, str]]:
        selected, diagnostic = _selection(
            leads, plan, excluded_sources=excluded_sources
        )
        with self._lock:
            self._stats["selection_calls"] += 1
            for name, value in diagnostic.items():
                self._stats[name] += value
        return selected

    def __enter__(self) -> "ValidatorAlignedAliasLeadSelection":
        if self._active or not _BINDING_GUARD.acquire(blocking=False):
            raise RuntimeError("V2.45.72 selection context is already active")
        self._acquired = True
        if surface._select_surface_seeded_leads is not ORIGINAL_SELECT_SURFACE_SEEDED_LEADS:
            _BINDING_GUARD.release()
            self._acquired = False
            raise RuntimeError("V2.45.72 frozen selection binding drifted")
        self._installed = self._select
        surface._select_surface_seeded_leads = self._installed
        self._active = True
        return self

    def __exit__(self, *_: object) -> None:
        drifted = False
        try:
            if self._active:
                drifted = surface._select_surface_seeded_leads is not self._installed
                surface._select_surface_seeded_leads = ORIGINAL_SELECT_SURFACE_SEEDED_LEADS
                self._active = False
                self._installed = None
        finally:
            if self._acquired:
                self._acquired = False
                _BINDING_GUARD.release()
        if drifted:
            raise RuntimeError("V2.45.72 installed selection binding drifted")

    def content_free_receipt(self) -> dict[str, Any]:
        return {
            "policy_id": POLICY_ID,
            "predecessor_policy_id": surface.POLICY_ID,
            "binding_count": EXPECTED_BINDING_COUNT,
            **dict(self._stats),
            "source_representative_selected_before_global_budget_cut": True,
            "within_source_selection_prefers_title_surface_validator_alignment": True,
            "within_source_selection_is_input_order_invariant": True,
            "frozen_global_surface_target_coverage_and_source_ranking_preserved": True,
            "logical_queries_search_batches_and_fetch_cap_unchanged": True,
            "url_alias_hint_receives_evidence_source_entropy_or_decision_credit": False,
            "exact_and_alias_title_evidence_validators_unchanged": True,
            "source_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged": True,
            "cache_or_cross_task_state_used": False,
            "bindings_restored": not self._active and not self._acquired,
            "task_question_opaque_id_query_url_page_content_prediction_value_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    true_fields = (
        "source_representative_selected_before_global_budget_cut",
        "within_source_selection_prefers_title_surface_validator_alignment",
        "within_source_selection_is_input_order_invariant",
        "frozen_global_surface_target_coverage_and_source_ranking_preserved",
        "logical_queries_search_batches_and_fetch_cap_unchanged",
        "exact_and_alias_title_evidence_validators_unchanged",
        "source_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged",
        "bindings_restored",
    )
    false_fields = (
        "url_alias_hint_receives_evidence_source_entropy_or_decision_credit",
        "cache_or_cross_task_state_used",
        "task_question_opaque_id_query_url_page_content_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("predecessor_policy_id") != surface.POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or any(_count(copied.get(name), name) < 0 for name in COUNT_FIELDS)
        or copied["unique_eligible_source_count"]
        > copied["visible_eligible_lead_count"]
        or copied["visible_input_lead_count"]
        != copied["visible_eligible_lead_count"] + copied["excluded_lead_count"]
        or copied["excluded_title_alias_surface_hit_lead_count"]
        > copied["excluded_lead_count"]
        or copied["excluded_url_only_alias_surface_hit_lead_count"]
        > copied["excluded_lead_count"]
        or copied["duplicate_source_lead_count"]
        != copied["visible_eligible_lead_count"]
        - copied["unique_eligible_source_count"]
        or copied["source_representative_replacement_count"]
        > copied["duplicate_source_lead_count"]
        or copied["validator_aligned_title_replacement_count"]
        > copied["source_representative_replacement_count"]
        or copied["url_only_first_representative_avoided_count"]
        > copied["validator_aligned_title_replacement_count"]
        or copied["selected_lead_count"]
        > copied["unique_eligible_source_count"]
        or copied["selected_title_alias_surface_hit_lead_count"]
        > copied["selected_lead_count"]
        or copied["selected_url_only_alias_surface_hit_lead_count"]
        > copied["selected_lead_count"]
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.72 validator-aligned selection receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS",
    "POLICY_ID",
    "ValidatorAlignedAliasLeadSelection",
    "select_validator_aligned_leads",
    "validate_receipt",
]
