"""Targeted-stage exact-URL candidate preservation before source selection.

V2.45.77 proved that V2.45.72 could not observe two leads from one
registrable source in the real pipeline: the frozen V2.43.71 helper selected
the first source representative before the validator-aligned selector ran.
This execution-scoped successor changes only that intermediate projection for
the V2.44.90 targeted stage.  It retains every valid exact-URL-distinct visible
lead until V2.45.72 selects one representative per registrable source.

The downstream source cap and fetch budget are unchanged.  Preserved URLs are
retrieval candidates only and receive no evidence, source, entropy,
epistemic, or decision credit.  This module performs no task, page, file,
environment, network, model, search, fetch, process, benchmark, evaluator, or
credential access.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any

from . import v24371_batch_stratified_verifier_runtime as source_projection
from . import v24490_entropy_targeted_support_search as targeted
from .v24355_explicit_partition_runtime import _source_from_lead


POLICY_ID = "v24578_targeted_prededup_candidate_preservation_v1"
EXPECTED_BINDING_COUNT = 1
TARGETED_BATCH_ORDINAL = 4
ORIGINAL_UNIQUE_HOST_LEADS = targeted._unique_host_leads
_BINDING_GUARD = threading.Lock()

COUNT_FIELDS = (
    "projection_calls",
    "raw_batch_count",
    "raw_mapping_result_count",
    "valid_projected_lead_count",
    "exact_url_distinct_lead_count",
    "exact_url_duplicate_drop_count",
    "registrable_source_count",
    "same_source_additional_candidate_count",
    "predecessor_unique_source_lead_count",
    "preserved_candidate_count",
)
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "predecessor_policy_id",
        "binding_count",
        *COUNT_FIELDS,
        "targeted_batch_ordinal",
        "only_targeted_stage_binding_changed",
        "only_valid_exact_url_distinct_visible_leads_preserved",
        "predecessor_projection_preserved_for_unique_source_vectors",
        "downstream_validator_aligned_source_selection_required",
        "logical_queries_search_batches_fetch_cap_and_page_cap_unchanged",
        "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit",
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
        raise ValueError(f"V2.45.78 {label} is invalid")
    return value


def _project_exact_url_distinct(
    batches: Sequence[Mapping[str, Any]], *, batch_ordinal: int
) -> tuple[list[dict[str, str]], dict[str, int]]:
    if batch_ordinal != TARGETED_BATCH_ORDINAL:
        raise ValueError("V2.45.78 is restricted to targeted batch ordinal 4")
    output: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    valid = 0
    raw_batches = 0
    raw_results = 0
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        raw_batches += 1
        values = batch.get("results") or []
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            continue
        for raw in values:
            if not isinstance(raw, Mapping):
                continue
            raw_results += 1
            lead = source_projection._lead(raw, batch_ordinal=batch_ordinal)
            if lead is None:
                continue
            valid += 1
            if lead["url"] in seen_urls:
                continue
            seen_urls.add(lead["url"])
            output.append(copy.deepcopy(lead))
    sources = {_source_from_lead(item) for item in output}
    predecessor = ORIGINAL_UNIQUE_HOST_LEADS(
        batches, batch_ordinal=batch_ordinal
    )
    if len(predecessor) != len(sources):
        raise RuntimeError("V2.45.78 predecessor source projection drifted")
    diagnostic = {
        "raw_batch_count": raw_batches,
        "raw_mapping_result_count": raw_results,
        "valid_projected_lead_count": valid,
        "exact_url_distinct_lead_count": len(output),
        "exact_url_duplicate_drop_count": valid - len(output),
        "registrable_source_count": len(sources),
        "same_source_additional_candidate_count": len(output) - len(sources),
        "predecessor_unique_source_lead_count": len(predecessor),
        "preserved_candidate_count": len(output) - len(predecessor),
    }
    return output, diagnostic


def preserve_exact_url_distinct_leads(
    batches: Sequence[Mapping[str, Any]], *, batch_ordinal: int
) -> list[dict[str, str]]:
    leads, _diagnostic = _project_exact_url_distinct(
        batches, batch_ordinal=batch_ordinal
    )
    return leads


class PrededupCandidatePreservation(
    AbstractContextManager["PrededupCandidatePreservation"]
):
    """Install the targeted-only projection for one worker execution."""

    def __init__(self) -> None:
        self._active = False
        self._acquired = False
        self._installed: Any = None
        self._lock = threading.RLock()
        self._stats = {name: 0 for name in COUNT_FIELDS}

    def _project(
        self,
        batches: Sequence[Mapping[str, Any]],
        *,
        batch_ordinal: int,
    ) -> list[dict[str, str]]:
        leads, diagnostic = _project_exact_url_distinct(
            batches, batch_ordinal=batch_ordinal
        )
        with self._lock:
            self._stats["projection_calls"] += 1
            for name, value in diagnostic.items():
                self._stats[name] += value
        return leads

    def __enter__(self) -> "PrededupCandidatePreservation":
        if self._active or not _BINDING_GUARD.acquire(blocking=False):
            raise RuntimeError("V2.45.78 preservation context is already active")
        self._acquired = True
        if targeted._unique_host_leads is not ORIGINAL_UNIQUE_HOST_LEADS:
            _BINDING_GUARD.release()
            self._acquired = False
            raise RuntimeError("V2.45.78 frozen projection binding drifted")
        self._installed = self._project
        targeted._unique_host_leads = self._installed
        self._active = True
        return self

    def __exit__(self, *_: object) -> None:
        drifted = False
        try:
            if self._active:
                drifted = targeted._unique_host_leads is not self._installed
                targeted._unique_host_leads = ORIGINAL_UNIQUE_HOST_LEADS
                self._active = False
                self._installed = None
        finally:
            if self._acquired:
                self._acquired = False
                _BINDING_GUARD.release()
        if drifted:
            raise RuntimeError("V2.45.78 installed projection binding drifted")

    def content_free_receipt(self) -> dict[str, Any]:
        return {
            "policy_id": POLICY_ID,
            "predecessor_policy_id": source_projection.POLICY_ID,
            "binding_count": EXPECTED_BINDING_COUNT,
            **dict(self._stats),
            "targeted_batch_ordinal": TARGETED_BATCH_ORDINAL,
            "only_targeted_stage_binding_changed": True,
            "only_valid_exact_url_distinct_visible_leads_preserved": True,
            "predecessor_projection_preserved_for_unique_source_vectors": True,
            "downstream_validator_aligned_source_selection_required": True,
            "logical_queries_search_batches_fetch_cap_and_page_cap_unchanged": True,
            "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
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
        "only_targeted_stage_binding_changed",
        "only_valid_exact_url_distinct_visible_leads_preserved",
        "predecessor_projection_preserved_for_unique_source_vectors",
        "downstream_validator_aligned_source_selection_required",
        "logical_queries_search_batches_fetch_cap_and_page_cap_unchanged",
        "bindings_restored",
    )
    false_fields = (
        "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit",
        "cache_or_cross_task_state_used",
        "task_question_opaque_id_query_url_page_content_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("predecessor_policy_id") != source_projection.POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or copied.get("targeted_batch_ordinal") != TARGETED_BATCH_ORDINAL
        or any(_count(copied.get(name), name) < 0 for name in COUNT_FIELDS)
        or copied["valid_projected_lead_count"]
        != copied["exact_url_distinct_lead_count"]
        + copied["exact_url_duplicate_drop_count"]
        or copied["exact_url_distinct_lead_count"]
        != copied["registrable_source_count"]
        + copied["same_source_additional_candidate_count"]
        or copied["predecessor_unique_source_lead_count"]
        != copied["registrable_source_count"]
        or copied["preserved_candidate_count"]
        != copied["same_source_additional_candidate_count"]
        or copied["projection_calls"] == 0
        and any(copied[name] != 0 for name in COUNT_FIELDS[1:])
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.78 pre-dedup preservation receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS",
    "POLICY_ID",
    "PrededupCandidatePreservation",
    "preserve_exact_url_distinct_leads",
    "validate_receipt",
]
