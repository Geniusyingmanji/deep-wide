"""Candidate-conditioned active verifier search after proposal freeze.

The parent receives four visible discovery queries as two non-recursive
batches and at most eight proposal pages.  After its candidate and bound
support declarations are frozen, proposal entropy ranks at most two changed
cells.  One additional non-recursive hosted-search batch is generated from
only those frozen row/column/value targets.  At most two source-disjoint pages
may then retain or revert the frozen candidate.

Verifier pages never enter a model prompt and cannot generate a new value.
Runtime input remains exactly ``{opaque_id, question}``; no benchmark label,
mapping, gold, evaluator, reward, or score is read.
"""

from __future__ import annotations

import copy
import math
import re
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
from .v24335_programmatic_support_runtime import _declaration_map
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
    _unique_host_leads,
)
from .v24378_adaptive_heldout_verifier_runtime import (
    _lead_projection,
    _replay_source_selection,
    _source_vectors,
    _target_score,
    _validate_selection_state,
)


POLICY_ID = "v24383_entropy_ranked_active_verifier_query_runtime_v1"
ROLE = "v24383_active_verifier_query_task_result"
RECEIPT_ROLE = "v24383_active_verifier_query_receipt"
PROPOSAL_LOGICAL_QUERIES = 4
PROPOSAL_SEARCH_BATCHES = 2
MAXIMUM_PROPOSAL_SOURCES = 8
MAXIMUM_ACTIVE_TARGETS = 2
MAXIMUM_ACTIVE_QUERIES = 2
MAXIMUM_ACTIVE_SOURCES = 2
MAXIMUM_TOTAL_FETCHES = 10
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "baseline_prediction",
        "candidate_prediction",
        "active_verifier_receipt",
        "private_replay_state",
        "result_sha256",
    }
)
PRIVATE_KEYS = frozenset(
    {
        "proposal_selection_state",
        "active_target_state",
        "active_union_leads",
        "selected_active_leads",
        "active_fetch_batches",
        "active_pages",
        "active_union_receipt_after_active",
        "page_character_cap",
        "active_provider_search_calls",
        "target_segment_utility_catalog",
        "cell_utility_resolutions",
    }
)
TARGET_STATE_KEYS = frozenset(
    {
        "candidate_change_count",
        "entropy_ranked_targets",
        "active_queries",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "target_segment_utility_policy_id",
        "partition_seed_sha256",
        "proposal_logical_query_count",
        "proposal_search_batch_count",
        "active_verifier_logical_query_count",
        "active_verifier_search_batch_count",
        "total_logical_query_count",
        "total_search_batch_count",
        "proposal_batch_host_counts",
        "proposal_source_count",
        "active_discovered_source_count",
        "active_selected_source_count",
        "candidate_change_count",
        "entropy_ranked_target_count",
        "parent_proposal_page_count",
        "active_verifier_page_count",
        "parent_fetch_calls",
        "active_verifier_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "parent_provider_search_calls",
        "active_provider_search_calls",
        "total_provider_search_calls",
        "candidate_changed_cells_before_active_verifier",
        "candidate_changed_cells_after_active_verifier",
        "selection_resolution_count",
        "candidate_changes_without_declaration",
        "selected_exactly_bound_candidate_changes",
        "active_verifier_admitted_cells",
        "active_verifier_reverted_cells",
        "verification_record_count",
        "verification_status_counts",
        "selected_verification_status_counts",
        "selected_disposition_counts",
        "verifier_semantic_projection_count",
        "proposal_support_entropy_total_nats",
        "selected_proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
        "four_proposal_queries_split_two_plus_two_before_candidate",
        "candidate_and_support_freeze_precedes_active_query_generation",
        "proposal_entropy_ranks_active_query_targets",
        "active_queries_use_only_frozen_row_column_value",
        "active_queries_execute_as_one_nonrecursive_batch",
        "active_verifier_sources_disjoint_from_proposal_sources",
        "active_verifier_pages_used_for_candidate_generation_or_model_prompt",
        "new_candidate_value_generated_by_active_verifier",
        "parent_support_set_ids_reused_without_rebuild",
        "target_segment_entity_boundary_enforced",
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _normalized(value: object) -> str:
    return " ".join(str(value).split()).strip()


def _target_identity(change: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        table._support_normalize(change["row_key"]),
        table._normalize_column(change["column"]),
        table._support_normalize(change["new_value"]),
    )


def _entropy_ranked_targets(parent: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_parent_result(parent)
    semantic = parent["semantic_result"]
    core = semantic["core_result"]
    changes = _changed_cells(
        str(core["baseline_prediction"]), str(core["candidate_prediction"])
    )
    columns, _ = table._table_matrix(str(core["baseline_prediction"]))
    declarations = _declaration_map(
        semantic["semantic_active_private_state"]["cell_support"], columns
    )
    catalog = semantic["semantic_active_private_state"]["semantic_active_catalog"]
    supports = {
        str(item["support_set_id"]): item
        for item in catalog["active_catalog"]["base_catalog"]["support_sets"]
    }
    ranked: list[dict[str, Any]] = []
    for raw in changes:
        change = dict(raw)
        declaration = declarations.get(
            (
                table._support_normalize(change["row_key"]),
                int(change["column_index"]),
            )
        )
        if declaration is None:
            continue
        support = supports.get(str(declaration["support_set_id"]))
        if (
            support is None
            or table._support_normalize(support["candidate_value"])
            != table._support_normalize(change["new_value"])
        ):
            continue
        entropy = float(
            support["admission_receipt"]["conditional_entropy_reduction_nats"]
        )
        if not math.isfinite(entropy) or entropy < 0:
            raise ValueError("V2.43.83 proposal entropy drifted")
        ranked.append(
            {
                **change,
                "proposal_support_set_id": str(declaration["support_set_id"]),
                "proposal_entropy_nats": entropy,
            }
        )
    ranked.sort(
        key=lambda item: (
            -float(item["proposal_entropy_nats"]),
            _target_identity(item),
        )
    )
    return ranked[:MAXIMUM_ACTIVE_TARGETS]


def _active_query(target: Mapping[str, Any]) -> str:
    row = _normalized(target["row_key"])
    column = _normalized(target["column"])
    value = _normalized(target["new_value"])
    if not row or not column or not value:
        raise ValueError("V2.43.83 active query target is incomplete")
    visible_target = row + column + value
    suffix = (
        "权威 独立 来源"
        if any("\u4e00" <= character <= "\u9fff" for character in visible_target)
        else "official independent source"
    )
    return f'"{row}" "{column}" "{value}" {suffix}'[:1_200]


def _active_target_state(parent: Mapping[str, Any]) -> dict[str, Any]:
    core = parent["semantic_result"]["core_result"]
    changes = _changed_cells(
        str(core["baseline_prediction"]), str(core["candidate_prediction"])
    )
    targets = _entropy_ranked_targets(parent)
    queries = [_active_query(target) for target in targets]
    if len(set(query.casefold() for query in queries)) != len(queries):
        raise ValueError("V2.43.83 active query vector is not unique")
    value = {
        "candidate_change_count": len(changes),
        "entropy_ranked_targets": targets,
        "active_queries": queries,
    }
    _validate_target_state(parent, value)
    return value


def _validate_target_state(
    parent: Mapping[str, Any], value: Mapping[str, Any]
) -> dict[str, Any]:
    if (
        set(value) != TARGET_STATE_KEYS
        or isinstance(value.get("candidate_change_count"), bool)
        or not isinstance(value.get("candidate_change_count"), int)
        or value["candidate_change_count"] < 0
        or not isinstance(value.get("entropy_ranked_targets"), list)
        or not isinstance(value.get("active_queries"), list)
        or len(value["entropy_ranked_targets"]) > MAXIMUM_ACTIVE_TARGETS
        or len(value["active_queries"]) != len(value["entropy_ranked_targets"])
        or any(not isinstance(item, Mapping) for item in value["entropy_ranked_targets"])
        or any(not isinstance(item, str) or not item for item in value["active_queries"])
    ):
        raise ValueError("V2.43.83 active target state drifted")
    core = parent["semantic_result"]["core_result"]
    changes = _changed_cells(
        str(core["baseline_prediction"]), str(core["candidate_prediction"])
    )
    expected_targets = _entropy_ranked_targets(parent)
    expected_queries = [_active_query(target) for target in expected_targets]
    if (
        value["candidate_change_count"] != len(changes)
        or value["entropy_ranked_targets"] != expected_targets
        or value["active_queries"] != expected_queries
    ):
        raise ValueError("V2.43.83 entropy-ranked query replay drifted")
    return copy.deepcopy(dict(value))


def _select_active_leads(
    leads: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    queries: Sequence[str],
    *,
    proposal_sources: set[str],
) -> list[dict[str, str]]:
    available: dict[str, dict[str, str]] = {}
    for raw in leads:
        lead = _lead_projection(raw)
        source = _source_from_lead(lead)
        if source in proposal_sources or source in available:
            continue
        available[source] = lead
    selected: list[dict[str, str]] = []
    used: set[str] = set()
    for target in targets:
        ranked = sorted(
            (
                lead
                for source, lead in available.items()
                if source not in used
            ),
            key=lambda lead: (
                tuple(-number for number in _target_score(lead, [target])),
                tuple(-number for number in _coverage(lead, queries)[1]),
                _source_from_lead(lead),
            ),
        )
        if not ranked:
            break
        chosen = ranked[0]
        used.add(_source_from_lead(chosen))
        selected.append(copy.deepcopy(chosen))
    return selected[:MAXIMUM_ACTIVE_SOURCES]


class ActiveVerifierQuerySearchClient:
    """Expose proposal pages, then issue one frozen-target verifier batch."""

    def __init__(self, inner: Any) -> None:
        self._union = TaskUnionDiscoverySearchClient(inner)
        self.query_batches: list[list[str]] = []
        self.raw_batch_leads: list[list[dict[str, str]]] = []
        self.proposal_batch_leads: list[list[dict[str, str]]] = []
        self.heldout_batch_leads: list[list[dict[str, str]]] = []
        self.proposal_parent_union_receipt: dict[str, Any] | None = None
        self.search_completed = False
        self.active_completed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._union, name)

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        if self.search_completed:
            raise RuntimeError("V2.43.83 proposal discovery repeated")
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
                "query": "active-verifier proposal discovery",
                "answer": "",
                "results": copy.deepcopy(flattened),
                "error": None,
                "provider": "v24383-proposal-only-before-active-query",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        if not self.search_completed:
            raise RuntimeError("V2.43.83 proposal fetch preceded discovery")
        allowed = {
            table.canonicalize_url(str(lead["url"]))
            for batch in self.proposal_batch_leads
            for lead in batch
        }
        values = list(requests_)
        if any(
            table.canonicalize_url(
                str(item.get("fetch_url") or item.get("url") or "")
            )
            not in allowed
            for item in values
        ):
            raise RuntimeError("V2.43.83 parent attempted nonproposal fetch")
        return self._union.fetch_urls(values)

    def proposal_selection_state(self) -> dict[str, Any]:
        if self.proposal_parent_union_receipt is None:
            raise RuntimeError("V2.43.83 proposal state is absent")
        return _validate_selection_state(
            {
                "query_batches": copy.deepcopy(self.query_batches),
                "raw_batch_leads": copy.deepcopy(self.raw_batch_leads),
                "proposal_batch_leads": copy.deepcopy(self.proposal_batch_leads),
                "heldout_batch_leads": copy.deepcopy(self.heldout_batch_leads),
                "union_receipt_after_proposal_parent": copy.deepcopy(
                    self.proposal_parent_union_receipt
                ),
            }
        )

    def active_search_and_fetch(
        self,
        parent: Mapping[str, Any],
        *,
        page_character_cap: int,
    ) -> dict[str, Any]:
        if not self.search_completed:
            raise RuntimeError("V2.43.83 active query preceded proposal discovery")
        if self.active_completed:
            raise RuntimeError("V2.43.83 active query repeated")
        self.proposal_parent_union_receipt = self._union.receipt()
        proposal_state = self.proposal_selection_state()
        target_state = _active_target_state(parent)
        queries = target_state["active_queries"]
        before_calls = int(self._union.calls)
        raw = (
            self._union.search_many(
                queries,
                max_results=3,
                search_depth="advanced",
                include_raw_content=False,
            )
            if queries
            else []
        )
        active_provider_search_calls = int(self._union.calls) - before_calls
        leads = (
            _unique_host_leads(raw, batch_ordinal=3) if queries else []
        )
        proposal_sources = {
            _source_from_lead(lead)
            for batch in proposal_state["proposal_batch_leads"]
            for lead in batch
        }
        selected = _select_active_leads(
            leads,
            target_state["entropy_ranked_targets"],
            queries,
            proposal_sources=proposal_sources,
        )
        fetched = self._union.fetch_urls(selected) if selected else []
        pages = table._page_vector(
            fetched, prefix="A", page_chars=page_character_cap
        )
        self.active_completed = True
        return {
            "proposal_selection_state": proposal_state,
            "active_target_state": target_state,
            "active_union_leads": [_lead_projection(lead) for lead in leads],
            "selected_active_leads": copy.deepcopy(selected),
            "active_fetch_batches": [
                dict(item)
                for item in fetched
                if isinstance(item, Mapping)
            ],
            "active_pages": pages,
            "active_union_receipt_after_active": self._union.receipt(),
            "page_character_cap": page_character_cap,
            "active_provider_search_calls": active_provider_search_calls,
        }


def _receipt(
    parent: Mapping[str, Any],
    private: Mapping[str, Any],
    utility: Mapping[str, Any],
    resolutions: Sequence[Mapping[str, Any]],
    *,
    before: int,
    after: int,
    proposal_credit: float,
    aligned_credit: float,
    missing_declarations: int,
    partition_seed_sha256: str,
) -> dict[str, Any]:
    core = parent["semantic_result"]["core_result"]
    target_state = private["active_target_state"]
    proposal_state = private["proposal_selection_state"]
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
    proposal_count = sum(
        len(batch) for batch in proposal_state["proposal_batch_leads"]
    )
    active_queries = target_state["active_queries"]
    active_selected = private["selected_active_leads"]
    parent_fetches = int(core["cost"]["search"]["fetch_calls"])
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": PARENT_POLICY_ID,
        "target_segment_utility_policy_id": UTILITY_POLICY_ID,
        "partition_seed_sha256": partition_seed_sha256,
        "proposal_logical_query_count": PROPOSAL_LOGICAL_QUERIES,
        "proposal_search_batch_count": PROPOSAL_SEARCH_BATCHES,
        "active_verifier_logical_query_count": len(active_queries),
        "active_verifier_search_batch_count": int(bool(active_queries)),
        "total_logical_query_count": PROPOSAL_LOGICAL_QUERIES + len(active_queries),
        "total_search_batch_count": PROPOSAL_SEARCH_BATCHES + int(bool(active_queries)),
        "proposal_batch_host_counts": [
            len(batch) for batch in proposal_state["proposal_batch_leads"]
        ],
        "proposal_source_count": proposal_count,
        "active_discovered_source_count": len(private["active_union_leads"]),
        "active_selected_source_count": len(active_selected),
        "candidate_change_count": target_state["candidate_change_count"],
        "entropy_ranked_target_count": len(target_state["entropy_ranked_targets"]),
        "parent_proposal_page_count": int(
            core["shared_prefix_revision_receipt"]["core_usable_pages"]
            + core["shared_prefix_revision_receipt"]["reserve_usable_pages"]
        ),
        "active_verifier_page_count": len(private["active_pages"]),
        "parent_fetch_calls": parent_fetches,
        "active_verifier_fetch_calls": len(active_selected),
        "total_fetch_calls": parent_fetches + len(active_selected),
        "parent_model_requests": int(core["cost"]["model"]["requests"]),
        "parent_provider_search_calls": int(core["cost"]["search"]["calls"]),
        "active_provider_search_calls": int(private["active_provider_search_calls"]),
        "total_provider_search_calls": int(core["cost"]["search"]["calls"])
        + int(private["active_provider_search_calls"]),
        "candidate_changed_cells_before_active_verifier": before,
        "candidate_changed_cells_after_active_verifier": after,
        "selection_resolution_count": len(resolutions),
        "candidate_changes_without_declaration": missing_declarations,
        "selected_exactly_bound_candidate_changes": exact_bindings,
        "active_verifier_admitted_cells": sum(
            item["admitted"] is True for item in resolutions
        ),
        "active_verifier_reverted_cells": before - after,
        "verification_record_count": int(utility["verification_record_count"]),
        "verification_status_counts": dict(utility["verification_status_counts"]),
        "selected_verification_status_counts": dict(sorted(selected_statuses.items())),
        "selected_disposition_counts": dict(sorted(selected_dispositions.items())),
        "verifier_semantic_projection_count": int(
            utility["verifier_semantic_projection_count"]
        ),
        "proposal_support_entropy_total_nats": float(
            utility["proposal_support_entropy_total_nats"]
        ),
        "selected_proposal_conditional_entropy_reduction_nats": round(
            proposal_credit, 12
        ),
        "utility_aligned_entropy_credit_nats": round(aligned_credit, 12),
        "four_proposal_queries_split_two_plus_two_before_candidate": True,
        "candidate_and_support_freeze_precedes_active_query_generation": True,
        "proposal_entropy_ranks_active_query_targets": True,
        "active_queries_use_only_frozen_row_column_value": True,
        "active_queries_execute_as_one_nonrecursive_batch": True,
        "active_verifier_sources_disjoint_from_proposal_sources": not set(
            _source_vectors(proposal_state["proposal_batch_leads"])
        )
        & set(_source_digest_from_lead(lead) for lead in active_selected),
        "active_verifier_pages_used_for_candidate_generation_or_model_prompt": False,
        "new_candidate_value_generated_by_active_verifier": False,
        "parent_support_set_ids_reused_without_rebuild": True,
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
    vector_fields = ("proposal_batch_host_counts",)
    count_fields = tuple(
        RECEIPT_KEYS
        - {
            "role",
            "policy_id",
            "parent_policy_id",
            "target_segment_utility_policy_id",
            "partition_seed_sha256",
            "proposal_batch_host_counts",
            "verification_status_counts",
            "selected_verification_status_counts",
            "selected_disposition_counts",
            "proposal_support_entropy_total_nats",
            "selected_proposal_conditional_entropy_reduction_nats",
            "utility_aligned_entropy_credit_nats",
            "receipt_sha256",
            *{
                name
                for name in RECEIPT_KEYS
                if name.startswith((
                    "four_",
                    "candidate_and_",
                    "proposal_entropy_",
                    "active_queries_",
                    "active_verifier_sources_",
                    "active_verifier_pages_",
                    "new_candidate_",
                    "parent_support_",
                    "target_segment_",
                    "question_prompt_",
                    "mapping_gold_",
                    "benchmark_launch_",
                ))
            },
        }
    )
    numeric_fields = (
        "proposal_support_entropy_total_nats",
        "selected_proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
    )
    true_fields = (
        "four_proposal_queries_split_two_plus_two_before_candidate",
        "candidate_and_support_freeze_precedes_active_query_generation",
        "proposal_entropy_ranks_active_query_targets",
        "active_queries_use_only_frozen_row_column_value",
        "active_queries_execute_as_one_nonrecursive_batch",
        "active_verifier_sources_disjoint_from_proposal_sources",
        "parent_support_set_ids_reused_without_rebuild",
        "target_segment_entity_boundary_enforced",
    )
    false_fields = (
        "active_verifier_pages_used_for_candidate_generation_or_model_prompt",
        "new_candidate_value_generated_by_active_verifier",
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
        or value.get("target_segment_utility_policy_id") != UTILITY_POLICY_ID
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("partition_seed_sha256"))) is None
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(
            not isinstance(value.get(name), list)
            or len(value[name]) != PROPOSAL_SEARCH_BATCHES
            or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value[name])
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
            name not in VERIFICATION_STATUSES
            or isinstance(number, bool)
            or not isinstance(number, int)
            or number < 0
            for mapping in (statuses, selected_statuses)
            for name, number in mapping.items()
        )
        or any(
            name not in UTILITY_DISPOSITIONS
            or isinstance(number, bool)
            or not isinstance(number, int)
            or number < 0
            for name, number in dispositions.items()
        )
        or any(value.get(name) is not True for name in true_fields)
        or any(value.get(name) is not False for name in false_fields)
        or value["proposal_logical_query_count"] != PROPOSAL_LOGICAL_QUERIES
        or value["proposal_search_batch_count"] != PROPOSAL_SEARCH_BATCHES
        or value["active_verifier_logical_query_count"] > MAXIMUM_ACTIVE_QUERIES
        or value["active_verifier_search_batch_count"]
        != int(value["active_verifier_logical_query_count"] > 0)
        or value["total_logical_query_count"]
        != PROPOSAL_LOGICAL_QUERIES + value["active_verifier_logical_query_count"]
        or value["total_search_batch_count"]
        != PROPOSAL_SEARCH_BATCHES + value["active_verifier_search_batch_count"]
        or value["parent_provider_search_calls"] < value["proposal_search_batch_count"]
        or value["active_provider_search_calls"]
        < value["active_verifier_search_batch_count"]
        or value["total_provider_search_calls"]
        != value["parent_provider_search_calls"]
        + value["active_provider_search_calls"]
        or value["proposal_source_count"] != sum(value["proposal_batch_host_counts"])
        or value["proposal_source_count"] > MAXIMUM_PROPOSAL_SOURCES
        or value["active_selected_source_count"] > MAXIMUM_ACTIVE_SOURCES
        or value["active_selected_source_count"] > value["active_discovered_source_count"]
        or value["entropy_ranked_target_count"] > MAXIMUM_ACTIVE_TARGETS
        or value["active_verifier_fetch_calls"] != value["active_selected_source_count"]
        or value["active_verifier_page_count"] > value["active_verifier_fetch_calls"]
        or value["total_fetch_calls"]
        != value["parent_fetch_calls"] + value["active_verifier_fetch_calls"]
        or value["total_fetch_calls"] > MAXIMUM_TOTAL_FETCHES
        or value["candidate_changed_cells_after_active_verifier"]
        > value["candidate_changed_cells_before_active_verifier"]
        or value["active_verifier_reverted_cells"]
        != value["candidate_changed_cells_before_active_verifier"]
        - value["candidate_changed_cells_after_active_verifier"]
        or value["active_verifier_admitted_cells"]
        != value["candidate_changed_cells_after_active_verifier"]
        or value["selection_resolution_count"]
        + value["candidate_changes_without_declaration"]
        != value["candidate_changed_cells_before_active_verifier"]
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
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.83 active verifier receipt drifted")
    return copy.deepcopy(dict(value))


def _derive(
    parent: Mapping[str, Any],
    private: Mapping[str, Any],
    *,
    partition_seed_sha256: str,
) -> dict[str, Any]:
    validate_parent_result(parent)
    if set(private) != PRIVATE_KEYS:
        raise ValueError("V2.43.83 private replay identity drifted")
    proposal_state = _validate_selection_state(private["proposal_selection_state"])
    target_state = _validate_target_state(parent, private["active_target_state"])
    final_union = private["active_union_receipt_after_active"]
    validate_union_receipt(final_union)
    raw_leads = [_lead_projection(lead) for lead in private["active_union_leads"]]
    proposal_sources = {
        _source_from_lead(lead)
        for batch in proposal_state["proposal_batch_leads"]
        for lead in batch
    }
    expected_selected = _select_active_leads(
        raw_leads,
        target_state["entropy_ranked_targets"],
        target_state["active_queries"],
        proposal_sources=proposal_sources,
    )
    if private["selected_active_leads"] != expected_selected:
        raise ValueError("V2.43.83 active source selection replay drifted")
    rebuilt_pages = table._page_vector(
        private["active_fetch_batches"],
        prefix="A",
        page_chars=int(private["page_character_cap"]),
    )
    if rebuilt_pages != private["active_pages"]:
        raise ValueError("V2.43.83 active page replay drifted")
    proposal_count = sum(
        len(batch) for batch in proposal_state["proposal_batch_leads"]
    )
    if (
        final_union["search_invocations"]
        != PROPOSAL_SEARCH_BATCHES + int(bool(target_state["active_queries"]))
        or final_union["logical_query_count"]
        != PROPOSAL_LOGICAL_QUERIES + len(target_state["active_queries"])
        or final_union["fetch_requested_source_count"]
        != proposal_count + len(expected_selected)
    ):
        raise ValueError("V2.43.83 final union effect replay drifted")
    semantic = parent["semantic_result"]
    proposal_catalog = semantic["semantic_active_private_state"][
        "semantic_active_catalog"
    ]
    utility = build_target_segment_utility_catalog(
        proposal_catalog,
        [_plain_page(page) for page in rebuilt_pages],
        partition_seed_sha256=partition_seed_sha256,
        expected_proposal_source_key_sha256s=_source_vectors(
            proposal_state["proposal_batch_leads"]
        ),
        expected_verifier_source_key_sha256s=sorted(
            _source_digest_from_lead(lead) for lead in expected_selected
        ),
    )
    validate_target_segment_utility_catalog(utility)
    (
        candidate,
        resolutions,
        before,
        after,
        proposal_credit,
        aligned_credit,
        missing_declarations,
    ) = _filter_candidate(parent, utility)
    full_private = {
        **{key: copy.deepcopy(private[key]) for key in PRIVATE_KEYS if key not in {"target_segment_utility_catalog", "cell_utility_resolutions"}},
        "target_segment_utility_catalog": utility,
        "cell_utility_resolutions": resolutions,
    }
    receipt = _receipt(
        parent,
        full_private,
        utility,
        resolutions,
        before=before,
        after=after,
        proposal_credit=proposal_credit,
        aligned_credit=aligned_credit,
        missing_declarations=missing_declarations,
        partition_seed_sha256=partition_seed_sha256,
    )
    return {
        "baseline_prediction": str(parent["semantic_result"]["core_result"]["baseline_prediction"]),
        "candidate_prediction": candidate,
        "private": full_private,
        "receipt": receipt,
    }


def run_v24383_task(
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
        or chosen.search_queries != PROPOSAL_LOGICAL_QUERIES
        or chosen.fetch_targets != MAXIMUM_TOTAL_FETCHES
    ):
        raise ValueError("V2.43.83 fixed effect cap drifted")
    staged = ActiveVerifierQuerySearchClient(search)
    parent = run_v24349_task(
        visible,
        model=model,
        search=staged,
        limits=chosen,
        monotonic=monotonic,
    )
    validate_parent_result(parent)
    active = staged.active_search_and_fetch(
        parent,
        page_character_cap=chosen.page_chars,
    )
    active["target_segment_utility_catalog"] = {}
    active["cell_utility_resolutions"] = []
    derived = _derive(
        parent,
        active,
        partition_seed_sha256=partition_seed_sha256,
    )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(parent),
        "baseline_prediction": derived["baseline_prediction"],
        "candidate_prediction": derived["candidate_prediction"],
        "active_verifier_receipt": derived["receipt"],
        "private_replay_state": derived["private"],
    }
    value["result_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    parent = value.get("parent_result")
    receipt = value.get("active_verifier_receipt")
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
        or not isinstance(private.get("page_character_cap"), int)
        or private["page_character_cap"] <= 0
        or not isinstance(private.get("active_provider_search_calls"), int)
        or private["active_provider_search_calls"] < 0
        or not isinstance(private.get("target_segment_utility_catalog"), Mapping)
        or not isinstance(private.get("cell_utility_resolutions"), list)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.83 result identity drifted")
    validate_parent_result(parent)
    validate_receipt(receipt)
    validate_target_segment_utility_catalog(
        private["target_segment_utility_catalog"]
    )
    for item in private["cell_utility_resolutions"]:
        validate_target_segment_utility_receipt(item)
    replay_input = {
        **dict(private),
        "target_segment_utility_catalog": {},
        "cell_utility_resolutions": [],
    }
    expected = _derive(
        parent,
        replay_input,
        partition_seed_sha256=str(receipt["partition_seed_sha256"]),
    )
    if (
        value["baseline_prediction"] != expected["baseline_prediction"]
        or value["candidate_prediction"] != expected["candidate_prediction"]
        or dict(receipt) != expected["receipt"]
        or dict(private) != expected["private"]
    ):
        raise ValueError("V2.43.83 deterministic replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "ActiveVerifierQuerySearchClient",
    "POLICY_ID",
    "ROLE",
    "run_v24383_task",
    "validate_receipt",
    "validate_result",
]
