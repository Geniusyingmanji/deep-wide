"""Post-candidate adaptive selection from a pre-frozen held-out source pool.

V2.43.77 established that two hidden pages can be structurally independent
yet provide no target-bound semantic projection.  V2.43.71 had to choose the
two verifier anchors before the candidate existed, using only generic query
overlap.  This append-only successor preserves the same four-query, ten-fetch,
three-model cap while changing the ordering:

* four visible queries are searched in two batches;
* four sources per batch (eight total) are exposed to the frozen V2.43.49
  proposal parent and fetched there;
* all other discovered sources remain unfetched and hidden from the parent;
* after the candidate and exact support-set bindings are frozen, one held-out
  source per batch is selected from title/URL target overlap and fetched;
* the frozen V2.43.65--67 target-segment verifier retains or reverts changes.

Candidate-conditioned *source selection* is permitted, but verifier page text
is never observed before selection and never enters candidate generation.
Runtime inputs remain exactly ``{opaque_id, question}``; no benchmark label,
mapping, gold, evaluator, reward, or score is read.
"""

from __future__ import annotations

import copy
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as table
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24269_task_union_discovery import (
    TaskUnionDiscoverySearchClient,
    validate_receipt as validate_union_receipt,
)
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import _normalize as catalog_normalize
from .v24349_structural_semantic_runtime import (
    POLICY_ID as PARENT_POLICY_ID,
    run_v24349_task,
    validate_result as validate_parent_result,
)
from .v24355_explicit_partition_runtime import (
    _changed_cells,
    _plain_page,
    _source_digest_from_lead,
    _source_from_lead,
)
from .v24358_two_batch_discovery import _query_batches
from .v24365_entity_segment_projection import POLICY_ID as PROJECTOR_POLICY_ID
from .v24366_target_segment_utility import (
    DISPOSITIONS as UTILITY_DISPOSITIONS,
    POLICY_ID as UTILITY_POLICY_ID,
    VERIFICATION_STATUSES,
    build_target_segment_utility_catalog,
    validate_target_segment_utility_catalog,
    validate_target_segment_utility_receipt,
)
from .v24367_target_segment_verifier_runtime import _filter_candidate
from .v24371_batch_stratified_verifier_runtime import (
    _coverage,
    _query_vector,
    _terms,
    _unique_host_leads,
)


POLICY_ID = "v24378_adaptive_heldout_target_verifier_runtime_v1"
ROLE = "v24378_adaptive_heldout_target_verifier_task_result"
RECEIPT_ROLE = "v24378_adaptive_heldout_target_verifier_receipt"
DISCOVERY_BATCH_COUNT = 2
LOGICAL_QUERY_COUNT = 4
PROPOSAL_SOURCES_PER_BATCH = 4
VERIFIER_SOURCES_PER_BATCH = 1
MAXIMUM_PROPOSAL_SOURCES = 8
MAXIMUM_VERIFIER_SOURCES = 2
MAXIMUM_FETCH_SOURCES = 10
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "baseline_prediction",
        "candidate_prediction",
        "adaptive_verifier_receipt",
        "private_replay_state",
        "result_sha256",
    }
)
PRIVATE_KEYS = frozenset(
    {
        "selection_state",
        "selected_verifier_leads",
        "verifier_fetch_batches",
        "verifier_pages",
        "page_character_cap",
        "target_segment_utility_catalog",
        "cell_utility_resolutions",
    }
)
SELECTION_KEYS = frozenset(
    {
        "query_batches",
        "raw_batch_leads",
        "proposal_batch_leads",
        "heldout_batch_leads",
        "union_receipt_after_proposal_parent",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "target_segment_projection_policy_id",
        "target_segment_utility_policy_id",
        "partition_seed_sha256",
        "logical_query_count",
        "discovery_batch_count",
        "raw_batch_unique_host_counts",
        "proposal_batch_host_counts",
        "heldout_batch_host_counts",
        "selected_verifier_batch_host_counts",
        "proposal_source_count",
        "heldout_source_count",
        "selected_verifier_source_count",
        "candidate_target_count",
        "selected_verifier_exact_row_phrase_match_count",
        "selected_verifier_row_token_match_count",
        "selected_verifier_candidate_value_match_count",
        "parent_proposal_page_count",
        "hidden_verifier_page_count",
        "parent_fetch_calls",
        "hidden_verifier_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "page_character_cap",
        "candidate_changed_cells_before_hidden_verifier",
        "candidate_changed_cells_after_hidden_verifier",
        "selection_resolution_count",
        "candidate_changes_without_declaration",
        "selected_exactly_bound_candidate_changes",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
        "verification_record_count",
        "verification_status_counts",
        "selected_verification_status_counts",
        "selected_disposition_counts",
        "verifier_semantic_projection_count",
        "proposal_support_entropy_total_nats",
        "selected_proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
        "four_queries_split_two_plus_two_before_candidate",
        "eight_proposal_sources_exposed_before_candidate_at_full_capacity",
        "heldout_source_titles_urls_and_provenance_only_before_candidate",
        "verifier_source_selection_after_candidate_and_support_freeze",
        "verifier_page_content_observed_before_selection",
        "verifier_pages_used_for_candidate_generation_or_model_prompt",
        "new_candidate_value_generated_by_verifier",
        "parent_support_set_ids_reused_without_rebuild",
        "proposal_and_verifier_sources_disjoint",
        "target_segment_entity_boundary_enforced",
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = re.sub(r"[^\w\u3400-\u9fff]+", " ", text)
    return " ".join(text.split())


def _lead_projection(raw: Mapping[str, Any]) -> dict[str, str]:
    value = {
        "url": table.canonicalize_url(
            str(raw.get("fetch_url") or raw.get("url") or "")
        ),
        "query": " ".join(str(raw.get("query") or "").split())[:1_200],
        "title": " ".join(str(raw.get("title") or "").split())[:500],
        "member_label": "",
    }
    if not value["url"]:
        raise ValueError("V2.43.78 source URL is absent")
    _source_from_lead(value)
    return value


def _proposal_order(
    leads: Sequence[dict[str, str]], queries: Sequence[str]
) -> list[dict[str, str]]:
    return sorted(
        (copy.deepcopy(lead) for lead in leads),
        key=lambda lead: (
            tuple(-number for number in _coverage(lead, queries)[1]),
            tuple(not item for item in _coverage(lead, queries)[0]),
            _source_from_lead(lead),
        ),
    )


def _replay_source_selection(
    raw_batches: Sequence[Sequence[Mapping[str, Any]]],
    query_batches: Sequence[Sequence[str]],
) -> tuple[list[list[dict[str, str]]], list[list[dict[str, str]]]]:
    if (
        len(raw_batches) != DISCOVERY_BATCH_COUNT
        or len(query_batches) != DISCOVERY_BATCH_COUNT
    ):
        raise ValueError("V2.43.78 requires two discovery batches")
    proposal_batches: list[list[dict[str, str]]] = []
    heldout_batches: list[list[dict[str, str]]] = []
    used_sources: set[str] = set()
    for raw_batch, raw_queries in zip(raw_batches, query_batches, strict=True):
        queries = _query_vector(raw_queries)
        current: list[dict[str, str]] = []
        for raw in raw_batch:
            lead = _lead_projection(raw)
            source = _source_from_lead(lead)
            if source in used_sources:
                continue
            used_sources.add(source)
            current.append(lead)
        ordered = _proposal_order(current, queries)
        proposal_batches.append(ordered[:PROPOSAL_SOURCES_PER_BATCH])
        heldout_batches.append(ordered[PROPOSAL_SOURCES_PER_BATCH:])
    return proposal_batches, heldout_batches


def _target_score(
    lead: Mapping[str, Any], changes: Sequence[Mapping[str, Any]]
) -> tuple[int, int, int, int, int]:
    haystack = _normalize(
        str(lead.get("title") or "") + " " + str(lead.get("url") or "")
    )
    exact_rows = 0
    row_terms: set[str] = set()
    value_matches = 0
    column_terms: set[str] = set()
    for change in changes:
        row = _normalize(change.get("row_key"))
        value = _normalize(change.get("new_value"))
        if row and row in haystack:
            exact_rows += 1
        row_terms.update(
            term for term in _terms(str(change.get("row_key") or "")) if _normalize(term) in haystack
        )
        if value and value in haystack:
            value_matches += 1
        column_terms.update(
            term for term in _terms(str(change.get("column") or "")) if _normalize(term) in haystack
        )
    return (
        exact_rows,
        len(row_terms),
        sum(len(term) for term in row_terms),
        value_matches,
        len(column_terms),
    )


def _select_verifier_leads(
    heldout_batches: Sequence[Sequence[Mapping[str, Any]]],
    query_batches: Sequence[Sequence[str]],
    changes: Sequence[Mapping[str, Any]],
) -> list[list[dict[str, str]]]:
    if (
        len(heldout_batches) != DISCOVERY_BATCH_COUNT
        or len(query_batches) != DISCOVERY_BATCH_COUNT
    ):
        raise ValueError("V2.43.78 heldout selection batch drifted")
    if not changes:
        return [[] for _ in range(DISCOVERY_BATCH_COUNT)]
    output: list[list[dict[str, str]]] = []
    for raw_batch, raw_queries in zip(
        heldout_batches, query_batches, strict=True
    ):
        queries = _query_vector(raw_queries)
        ranked = sorted(
            (_lead_projection(lead) for lead in raw_batch),
            key=lambda lead: (
                tuple(-number for number in _target_score(lead, changes)),
                tuple(-number for number in _coverage(lead, queries)[1]),
                _source_from_lead(lead),
            ),
        )
        output.append(ranked[:VERIFIER_SOURCES_PER_BATCH])
    return output


def _source_vectors(
    batches: Sequence[Sequence[Mapping[str, Any]]],
) -> list[str]:
    return sorted(
        _source_digest_from_lead(lead) for batch in batches for lead in batch
    )


def _validate_selection_state(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != SELECTION_KEYS:
        raise ValueError("V2.43.78 selection-state identity drifted")
    query_batches = value.get("query_batches")
    raw_batches = value.get("raw_batch_leads")
    proposals = value.get("proposal_batch_leads")
    heldout = value.get("heldout_batch_leads")
    union_receipt = value.get("union_receipt_after_proposal_parent")
    if (
        not isinstance(query_batches, list)
        or len(query_batches) != DISCOVERY_BATCH_COUNT
        or [_query_vector(batch) for batch in query_batches] != query_batches
        or sum(len(batch) for batch in query_batches) != LOGICAL_QUERY_COUNT
        or not isinstance(raw_batches, list)
        or not isinstance(proposals, list)
        or not isinstance(heldout, list)
        or any(
            len(batches) != DISCOVERY_BATCH_COUNT
            or any(not isinstance(batch, list) for batch in batches)
            for batches in (raw_batches, proposals, heldout)
        )
        or any(
            not isinstance(lead, Mapping)
            for batches in (raw_batches, proposals, heldout)
            for batch in batches
            for lead in batch
        )
        or not isinstance(union_receipt, Mapping)
    ):
        raise ValueError("V2.43.78 selection-state schema drifted")
    validate_union_receipt(union_receipt)
    expected_proposals, expected_heldout = _replay_source_selection(
        raw_batches, query_batches
    )
    all_sources = [
        _source_from_lead(lead)
        for batches in (proposals, heldout)
        for batch in batches
        for lead in batch
    ]
    if (
        proposals != expected_proposals
        or heldout != expected_heldout
        or len(all_sources) != len(set(all_sources))
        or sum(len(batch) for batch in proposals) > MAXIMUM_PROPOSAL_SOURCES
        or union_receipt.get("search_invocations") != DISCOVERY_BATCH_COUNT
        or union_receipt.get("logical_query_count") != LOGICAL_QUERY_COUNT
        or union_receipt.get("fetch_requested_source_count")
        != sum(len(batch) for batch in proposals)
    ):
        raise ValueError("V2.43.78 source selection replay drifted")
    return copy.deepcopy(dict(value))


class AdaptiveHeldoutVerifierSearchClient:
    """Expose eight proposal sources and retain the unfetched discovery pool."""

    def __init__(self, inner: Any) -> None:
        self._union = TaskUnionDiscoverySearchClient(inner)
        self.query_batches: list[list[str]] = []
        self.raw_batch_leads: list[list[dict[str, str]]] = []
        self.proposal_batch_leads: list[list[dict[str, str]]] = []
        self.heldout_batch_leads: list[list[dict[str, str]]] = []
        self.selected_verifier_leads: list[list[dict[str, str]]] = []
        self.verifier_fetch_batches: list[dict[str, Any]] = []
        self.proposal_parent_union_receipt: dict[str, Any] | None = None
        self.search_completed = False
        self.verifier_selection_completed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._union, name)

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        if self.search_completed:
            raise RuntimeError("V2.43.78 proposal discovery repeated")
        batches = _query_batches(queries)
        raw_batches: list[list[dict[str, str]]] = []
        seen: set[str] = set()
        for ordinal, query_batch in enumerate(batches, start=1):
            raw = self._union.search_many(query_batch, **kwargs)
            current: list[dict[str, str]] = []
            for lead in _unique_host_leads(raw, batch_ordinal=ordinal):
                source = _source_from_lead(lead)
                if source in seen:
                    continue
                seen.add(source)
                current.append(lead)
            raw_batches.append(current)
        proposals, heldout = _replay_source_selection(raw_batches, batches)
        self.query_batches = copy.deepcopy(batches)
        self.raw_batch_leads = copy.deepcopy(raw_batches)
        self.proposal_batch_leads = proposals
        self.heldout_batch_leads = heldout
        self.search_completed = True
        flattened = [lead for batch in proposals for lead in batch]
        if not flattened:
            return []
        return [
            {
                "query": "adaptive-heldout proposal discovery",
                "answer": "",
                "results": copy.deepcopy(flattened),
                "error": None,
                "provider": "v24378-proposal-only-heldout-pool",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        if not self.search_completed:
            raise RuntimeError("V2.43.78 proposal fetch preceded discovery")
        allowed = {
            table.canonicalize_url(str(lead["url"]))
            for batch in self.proposal_batch_leads
            for lead in batch
        }
        requested = list(requests_)
        if any(
            table.canonicalize_url(
                str(item.get("fetch_url") or item.get("url") or "")
            )
            not in allowed
            for item in requested
        ):
            raise RuntimeError("V2.43.78 parent attempted heldout-source fetch")
        return self._union.fetch_urls(requested)

    def select_and_fetch_verifiers(
        self, changes: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        if not self.search_completed:
            raise RuntimeError("V2.43.78 verifier selection preceded discovery")
        if self.verifier_selection_completed:
            raise RuntimeError("V2.43.78 verifier selection repeated")
        self.proposal_parent_union_receipt = self._union.receipt()
        selected = _select_verifier_leads(
            self.heldout_batch_leads, self.query_batches, changes
        )
        flattened = [lead for batch in selected for lead in batch]
        raw = self._union.fetch_urls(flattened) if flattened else []
        self.selected_verifier_leads = copy.deepcopy(selected)
        self.verifier_fetch_batches = (
            [dict(item) for item in raw if isinstance(item, Mapping)]
            if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes))
            else []
        )
        self.verifier_selection_completed = True
        return copy.deepcopy(self.verifier_fetch_batches)

    def selection_state(self) -> dict[str, Any]:
        if not self.search_completed or self.proposal_parent_union_receipt is None:
            raise RuntimeError("V2.43.78 selection state is absent")
        value = {
            "query_batches": copy.deepcopy(self.query_batches),
            "raw_batch_leads": copy.deepcopy(self.raw_batch_leads),
            "proposal_batch_leads": copy.deepcopy(self.proposal_batch_leads),
            "heldout_batch_leads": copy.deepcopy(self.heldout_batch_leads),
            "union_receipt_after_proposal_parent": copy.deepcopy(
                self.proposal_parent_union_receipt
            ),
        }
        return _validate_selection_state(value)


def _receipt(
    parent: Mapping[str, Any],
    selection: Mapping[str, Any],
    selected_verifier_leads: Sequence[Sequence[Mapping[str, Any]]],
    verifier_pages: Sequence[Mapping[str, Any]],
    utility_catalog: Mapping[str, Any],
    resolutions: Sequence[Mapping[str, Any]],
    changes: Sequence[Mapping[str, Any]],
    *,
    after: int,
    selected_proposal_credit: float,
    aligned_credit: float,
    missing_declarations: int,
    partition_seed_sha256: str,
    page_character_cap: int,
) -> dict[str, Any]:
    core = parent["semantic_result"]["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    selected_statuses = Counter(
        str(item["verification_status"])
        for item in resolutions
        if item["verification_status"] is not None
    )
    selected_dispositions = Counter(str(item["disposition"]) for item in resolutions)
    exact_bindings = sum(
        all(
            item[name] is True
            for name in (
                "target_binding_matches",
                "value_binding_matches",
                "proposal_support_set_binding_matches",
                "proposal_evidence_binding_matches",
                "proposal_and_verifier_sources_disjoint",
            )
        )
        for item in resolutions
    )
    selected_flat = [lead for batch in selected_verifier_leads for lead in batch]
    scores = [_target_score(lead, changes) for lead in selected_flat]
    proposal_count = sum(len(batch) for batch in selection["proposal_batch_leads"])
    heldout_count = sum(len(batch) for batch in selection["heldout_batch_leads"])
    verifier_count = len(selected_flat)
    parent_fetches = int(core["cost"]["search"]["fetch_calls"])
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": PARENT_POLICY_ID,
        "target_segment_projection_policy_id": PROJECTOR_POLICY_ID,
        "target_segment_utility_policy_id": UTILITY_POLICY_ID,
        "partition_seed_sha256": partition_seed_sha256,
        "logical_query_count": sum(len(batch) for batch in selection["query_batches"]),
        "discovery_batch_count": len(selection["query_batches"]),
        "raw_batch_unique_host_counts": [
            len(batch) for batch in selection["raw_batch_leads"]
        ],
        "proposal_batch_host_counts": [
            len(batch) for batch in selection["proposal_batch_leads"]
        ],
        "heldout_batch_host_counts": [
            len(batch) for batch in selection["heldout_batch_leads"]
        ],
        "selected_verifier_batch_host_counts": [
            len(batch) for batch in selected_verifier_leads
        ],
        "proposal_source_count": proposal_count,
        "heldout_source_count": heldout_count,
        "selected_verifier_source_count": verifier_count,
        "candidate_target_count": len(changes),
        "selected_verifier_exact_row_phrase_match_count": sum(score[0] for score in scores),
        "selected_verifier_row_token_match_count": sum(score[1] for score in scores),
        "selected_verifier_candidate_value_match_count": sum(score[3] for score in scores),
        "parent_proposal_page_count": int(
            core_receipt["core_usable_pages"] + core_receipt["reserve_usable_pages"]
        ),
        "hidden_verifier_page_count": len(verifier_pages),
        "parent_fetch_calls": parent_fetches,
        "hidden_verifier_fetch_calls": verifier_count,
        "total_fetch_calls": parent_fetches + verifier_count,
        "parent_model_requests": int(core["cost"]["model"]["requests"]),
        "page_character_cap": int(page_character_cap),
        "candidate_changed_cells_before_hidden_verifier": len(changes),
        "candidate_changed_cells_after_hidden_verifier": after,
        "selection_resolution_count": len(resolutions),
        "candidate_changes_without_declaration": missing_declarations,
        "selected_exactly_bound_candidate_changes": exact_bindings,
        "hidden_verifier_admitted_cells": sum(
            item["admitted"] is True for item in resolutions
        ),
        "hidden_verifier_reverted_cells": len(changes) - after,
        "verification_record_count": int(utility_catalog["verification_record_count"]),
        "verification_status_counts": dict(utility_catalog["verification_status_counts"]),
        "selected_verification_status_counts": dict(sorted(selected_statuses.items())),
        "selected_disposition_counts": dict(sorted(selected_dispositions.items())),
        "verifier_semantic_projection_count": int(
            utility_catalog["verifier_semantic_projection_count"]
        ),
        "proposal_support_entropy_total_nats": float(
            utility_catalog["proposal_support_entropy_total_nats"]
        ),
        "selected_proposal_conditional_entropy_reduction_nats": round(
            selected_proposal_credit, 12
        ),
        "utility_aligned_entropy_credit_nats": round(aligned_credit, 12),
        "four_queries_split_two_plus_two_before_candidate": True,
        "eight_proposal_sources_exposed_before_candidate_at_full_capacity": (
            proposal_count == MAXIMUM_PROPOSAL_SOURCES
        ),
        "heldout_source_titles_urls_and_provenance_only_before_candidate": True,
        "verifier_source_selection_after_candidate_and_support_freeze": True,
        "verifier_page_content_observed_before_selection": False,
        "verifier_pages_used_for_candidate_generation_or_model_prompt": False,
        "new_candidate_value_generated_by_verifier": False,
        "parent_support_set_ids_reused_without_rebuild": True,
        "proposal_and_verifier_sources_disjoint": not set(
            _source_vectors(selection["proposal_batch_leads"])
        )
        & set(_source_vectors(selected_verifier_leads)),
        "target_segment_entity_boundary_enforced": True,
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_receipt(value)
    return value


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    statuses = value.get("verification_status_counts")
    selected_statuses = value.get("selected_verification_status_counts")
    dispositions = value.get("selected_disposition_counts")
    vector_fields = (
        "raw_batch_unique_host_counts",
        "proposal_batch_host_counts",
        "heldout_batch_host_counts",
        "selected_verifier_batch_host_counts",
    )
    count_fields = (
        "logical_query_count",
        "discovery_batch_count",
        "proposal_source_count",
        "heldout_source_count",
        "selected_verifier_source_count",
        "candidate_target_count",
        "selected_verifier_exact_row_phrase_match_count",
        "selected_verifier_row_token_match_count",
        "selected_verifier_candidate_value_match_count",
        "parent_proposal_page_count",
        "hidden_verifier_page_count",
        "parent_fetch_calls",
        "hidden_verifier_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "page_character_cap",
        "candidate_changed_cells_before_hidden_verifier",
        "candidate_changed_cells_after_hidden_verifier",
        "selection_resolution_count",
        "candidate_changes_without_declaration",
        "selected_exactly_bound_candidate_changes",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
        "verification_record_count",
        "verifier_semantic_projection_count",
    )
    numeric_fields = (
        "proposal_support_entropy_total_nats",
        "selected_proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
    )
    true_fields = (
        "four_queries_split_two_plus_two_before_candidate",
        "heldout_source_titles_urls_and_provenance_only_before_candidate",
        "verifier_source_selection_after_candidate_and_support_freeze",
        "parent_support_set_ids_reused_without_rebuild",
        "proposal_and_verifier_sources_disjoint",
        "target_segment_entity_boundary_enforced",
    )
    false_fields = (
        "verifier_page_content_observed_before_selection",
        "verifier_pages_used_for_candidate_generation_or_model_prompt",
        "new_candidate_value_generated_by_verifier",
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("parent_policy_id") != PARENT_POLICY_ID
        or value.get("target_segment_projection_policy_id") != PROJECTOR_POLICY_ID
        or value.get("target_segment_utility_policy_id") != UTILITY_POLICY_ID
        or re.fullmatch(
            r"[0-9a-f]{64}", str(value.get("partition_seed_sha256"))
        )
        is None
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(
            not isinstance(value.get(name), list)
            or len(value[name]) != DISCOVERY_BATCH_COUNT
            or any(
                isinstance(item, bool) or not isinstance(item, int) or item < 0
                for item in value[name]
            )
            for name in vector_fields
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in numeric_fields
        )
        or not isinstance(statuses, Mapping)
        or not isinstance(selected_statuses, Mapping)
        or not isinstance(dispositions, Mapping)
        or any(
            name not in (
                VERIFICATION_STATUSES if mapping is not dispositions else UTILITY_DISPOSITIONS
            )
            or isinstance(number, bool)
            or not isinstance(number, int)
            or number < 0
            for mapping in (statuses, selected_statuses, dispositions)
            for name, number in mapping.items()
        )
        or any(value.get(name) is not True for name in true_fields)
        or any(value.get(name) is not False for name in false_fields)
        or not isinstance(
            value.get("eight_proposal_sources_exposed_before_candidate_at_full_capacity"),
            bool,
        )
        or value["logical_query_count"] != LOGICAL_QUERY_COUNT
        or value["discovery_batch_count"] != DISCOVERY_BATCH_COUNT
        or value["proposal_source_count"]
        != sum(value["proposal_batch_host_counts"])
        or value["heldout_source_count"] != sum(value["heldout_batch_host_counts"])
        or value["selected_verifier_source_count"]
        != sum(value["selected_verifier_batch_host_counts"])
        or value["proposal_source_count"] > MAXIMUM_PROPOSAL_SOURCES
        or value["selected_verifier_source_count"] > MAXIMUM_VERIFIER_SOURCES
        or value["hidden_verifier_fetch_calls"]
        != value["selected_verifier_source_count"]
        or value["hidden_verifier_page_count"]
        > value["hidden_verifier_fetch_calls"]
        or value["total_fetch_calls"]
        != value["parent_fetch_calls"] + value["hidden_verifier_fetch_calls"]
        or value["total_fetch_calls"] > MAXIMUM_FETCH_SOURCES
        or value["candidate_changed_cells_after_hidden_verifier"]
        > value["candidate_changed_cells_before_hidden_verifier"]
        or value["hidden_verifier_reverted_cells"]
        != value["candidate_changed_cells_before_hidden_verifier"]
        - value["candidate_changed_cells_after_hidden_verifier"]
        or value["hidden_verifier_admitted_cells"]
        != value["candidate_changed_cells_after_hidden_verifier"]
        or value["selection_resolution_count"]
        + value["candidate_changes_without_declaration"]
        != value["candidate_changed_cells_before_hidden_verifier"]
        or value["selected_exactly_bound_candidate_changes"]
        > value["selection_resolution_count"]
        or sum(statuses.values()) != value["verification_record_count"]
        or sum(selected_statuses.values())
        != value["selected_exactly_bound_candidate_changes"]
        or sum(dispositions.values()) != value["selection_resolution_count"]
        or value["selected_proposal_conditional_entropy_reduction_nats"]
        > value["proposal_support_entropy_total_nats"] + 1e-12
        or value["utility_aligned_entropy_credit_nats"]
        > value["selected_proposal_conditional_entropy_reduction_nats"] + 1e-12
        or value[
            "eight_proposal_sources_exposed_before_candidate_at_full_capacity"
        ]
        is not (value["proposal_source_count"] == MAXIMUM_PROPOSAL_SOURCES)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.78 adaptive verifier receipt drifted")
    return copy.deepcopy(dict(value))


def _derive(
    parent: Mapping[str, Any],
    selection: Mapping[str, Any],
    selected_verifier_leads: Sequence[Sequence[Mapping[str, Any]]],
    verifier_pages: Sequence[Mapping[str, Any]],
    *,
    partition_seed_sha256: str,
    page_character_cap: int,
) -> dict[str, Any]:
    validate_parent_result(parent)
    frozen_selection = _validate_selection_state(selection)
    core = parent["semantic_result"]["core_result"]
    proposal_catalog = parent["semantic_result"]["semantic_active_private_state"][
        "semantic_active_catalog"
    ]
    if not isinstance(proposal_catalog, Mapping):
        raise ValueError("V2.43.78 proposal semantic catalog is absent")
    baseline = str(core["baseline_prediction"])
    candidate_before = str(core["candidate_prediction"])
    changes = _changed_cells(baseline, candidate_before)
    expected_verifiers = _select_verifier_leads(
        frozen_selection["heldout_batch_leads"],
        frozen_selection["query_batches"],
        changes,
    )
    projected_verifiers = [
        [_lead_projection(lead) for lead in batch]
        for batch in selected_verifier_leads
    ]
    if projected_verifiers != expected_verifiers:
        raise ValueError("V2.43.78 adaptive verifier source selection drifted")
    selected_urls = {
        table.canonicalize_url(str(lead["url"]))
        for batch in expected_verifiers
        for lead in batch
    }
    observed_urls = [
        table.canonicalize_url(str(page.get("url") or ""))
        for page in verifier_pages
    ]
    if (
        any(not url for url in observed_urls)
        or len(observed_urls) != len(set(observed_urls))
        or not set(observed_urls).issubset(selected_urls)
    ):
        raise ValueError("V2.43.78 verifier page escaped its selected URL vector")
    utility = build_target_segment_utility_catalog(
        proposal_catalog,
        [_plain_page(page) for page in verifier_pages],
        partition_seed_sha256=partition_seed_sha256,
        expected_proposal_source_key_sha256s=_source_vectors(
            frozen_selection["proposal_batch_leads"]
        ),
        expected_verifier_source_key_sha256s=_source_vectors(expected_verifiers),
    )
    validate_target_segment_utility_catalog(utility)
    (
        candidate_after,
        resolutions,
        before,
        after,
        proposal_credit,
        aligned_credit,
        missing_declarations,
    ) = _filter_candidate(parent, utility)
    if before != len(changes):
        raise ValueError("V2.43.78 candidate change count drifted")
    receipt = _receipt(
        parent,
        frozen_selection,
        expected_verifiers,
        verifier_pages,
        utility,
        resolutions,
        changes,
        after=after,
        selected_proposal_credit=proposal_credit,
        aligned_credit=aligned_credit,
        missing_declarations=missing_declarations,
        partition_seed_sha256=partition_seed_sha256,
        page_character_cap=page_character_cap,
    )
    return {
        "baseline_prediction": baseline,
        "candidate_prediction": candidate_after,
        "utility": utility,
        "resolutions": resolutions,
        "receipt": receipt,
    }


def run_v24378_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    chosen = limits or ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )
    chosen.validate()
    if (
        chosen.model_calls != 3
        or chosen.search_queries != LOGICAL_QUERY_COUNT
        or chosen.fetch_targets != MAXIMUM_FETCH_SOURCES
    ):
        raise ValueError("V2.43.78 fixed effect cap drifted")
    staged = AdaptiveHeldoutVerifierSearchClient(search)
    parent = run_v24349_task(
        visible,
        model=model,
        search=staged,
        limits=chosen,
        monotonic=monotonic,
    )
    validate_parent_result(parent)
    core = parent["semantic_result"]["core_result"]
    changes = _changed_cells(
        str(core["baseline_prediction"]), str(core["candidate_prediction"])
    )
    verifier_batches = staged.select_and_fetch_verifiers(changes)
    verifier_pages = table._page_vector(
        verifier_batches, prefix="V", page_chars=chosen.page_chars
    )
    selection = staged.selection_state()
    derived = _derive(
        parent,
        selection,
        staged.selected_verifier_leads,
        verifier_pages,
        partition_seed_sha256=partition_seed_sha256,
        page_character_cap=chosen.page_chars,
    )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(parent),
        "baseline_prediction": derived["baseline_prediction"],
        "candidate_prediction": derived["candidate_prediction"],
        "adaptive_verifier_receipt": derived["receipt"],
        "private_replay_state": {
            "selection_state": selection,
            "selected_verifier_leads": copy.deepcopy(
                staged.selected_verifier_leads
            ),
            "verifier_fetch_batches": copy.deepcopy(verifier_batches),
            "verifier_pages": copy.deepcopy(verifier_pages),
            "page_character_cap": chosen.page_chars,
            "target_segment_utility_catalog": derived["utility"],
            "cell_utility_resolutions": copy.deepcopy(derived["resolutions"]),
        },
    }
    value["result_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    parent = value.get("parent_result")
    receipt = value.get("adaptive_verifier_receipt")
    private = value.get("private_replay_state")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(parent, Mapping)
        or not isinstance(receipt, Mapping)
        or not isinstance(private, Mapping)
        or set(private) != PRIVATE_KEYS
        or not isinstance(value.get("baseline_prediction"), str)
        or not isinstance(value.get("candidate_prediction"), str)
        or not isinstance(private.get("selection_state"), Mapping)
        or not isinstance(private.get("selected_verifier_leads"), list)
        or not isinstance(private.get("verifier_fetch_batches"), list)
        or not isinstance(private.get("verifier_pages"), list)
        or isinstance(private.get("page_character_cap"), bool)
        or not isinstance(private.get("page_character_cap"), int)
        or private["page_character_cap"] <= 0
        or not isinstance(private.get("target_segment_utility_catalog"), Mapping)
        or not isinstance(private.get("cell_utility_resolutions"), list)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.78 result identity drifted")
    validate_parent_result(parent)
    validate_receipt(receipt)
    selection = _validate_selection_state(private["selection_state"])
    rebuilt_pages = table._page_vector(
        private["verifier_fetch_batches"],
        prefix="V",
        page_chars=int(private["page_character_cap"]),
    )
    if rebuilt_pages != private["verifier_pages"]:
        raise ValueError("V2.43.78 verifier page replay drifted")
    expected = _derive(
        parent,
        selection,
        private["selected_verifier_leads"],
        private["verifier_pages"],
        partition_seed_sha256=str(receipt["partition_seed_sha256"]),
        page_character_cap=int(private["page_character_cap"]),
    )
    validate_target_segment_utility_catalog(
        private["target_segment_utility_catalog"]
    )
    for item in private["cell_utility_resolutions"]:
        validate_target_segment_utility_receipt(item)
    if (
        value["baseline_prediction"] != expected["baseline_prediction"]
        or value["candidate_prediction"] != expected["candidate_prediction"]
        or dict(receipt) != expected["receipt"]
        or dict(private["target_segment_utility_catalog"]) != expected["utility"]
        or private["cell_utility_resolutions"] != expected["resolutions"]
    ):
        raise ValueError("V2.43.78 deterministic replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "AdaptiveHeldoutVerifierSearchClient",
    "POLICY_ID",
    "ROLE",
    "run_v24378_task",
    "validate_receipt",
    "validate_result",
]
