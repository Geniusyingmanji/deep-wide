"""Candidate-independent active evidence after a frozen baseline.

The structural semantic parent still receives four visible proposal queries in
two non-recursive batches and at most eight proposal pages.  Once its baseline
is frozen, every visible cell enters the V2.43.88 uncertainty catalog.  At most
two high-uncertainty cells generate one additional search batch using only the
frozen row and column.  At most two source-disjoint active pages are fetched.

Proposal and active pages are converted to observations by the deterministic
target-segment projector.  Active pages never enter a model prompt.  The final
table and epistemic/decision credit are computed by replaying the sealed
multi-hypothesis posterior.  Runtime input remains exactly
``{opaque_id, question}``; benchmark labels and evaluator-side data are never
read.
"""

from __future__ import annotations

import copy
import math
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as table
from . import v24365_entity_segment_projection as segment
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24269_task_union_discovery import validate_receipt as validate_union_receipt
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget, _normalize, _source_key
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
from .v24371_batch_stratified_verifier_runtime import _unique_host_leads
from .v24371_batch_stratified_verifier_runtime import _coverage
from .v24378_adaptive_heldout_verifier_runtime import (
    _lead_projection,
    _source_vectors,
    _target_score,
    _validate_selection_state,
)
from .v24383_active_verifier_query_runtime import (
    ActiveVerifierQuerySearchClient,
)
from .v24388_uncertainty_credit import (
    POLICY_ID as ENTROPY_POLICY_ID,
    apply_active_evidence,
    build_uncertainty_catalog,
    validate_active_evidence_result,
    validate_uncertainty_catalog,
)


POLICY_ID = "v24390_candidate_independent_uncertainty_active_evidence_v1"
ROLE = "v24390_uncertainty_active_evidence_task_result"
RECEIPT_ROLE = "v24390_uncertainty_active_evidence_receipt"
PROPOSAL_LOGICAL_QUERIES = 4
PROPOSAL_SEARCH_BATCHES = 2
MAXIMUM_PROPOSAL_SOURCES = 8
MAXIMUM_ACTIVE_TARGETS = 2
MAXIMUM_ACTIVE_QUERIES = 2
MAXIMUM_ACTIVE_SOURCES = 2
MAXIMUM_TOTAL_FETCHES = 10
RUNTIME_SELECTED_TARGET_CAP = 1
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "baseline_prediction",
        "candidate_prediction",
        "uncertainty_active_receipt",
        "private_replay_state",
        "result_sha256",
    }
)
PRIVATE_KEYS = frozenset(
    {
        "proposal_selection_state",
        "proposal_observations",
        "uncertainty_catalog",
        "active_union_leads",
        "selected_active_leads",
        "active_fetch_batches",
        "active_pages",
        "active_observations",
        "active_evidence_result",
        "active_union_receipt_after_active",
        "page_character_cap",
        "active_provider_search_calls",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "entropy_policy_id",
        "partition_seed_sha256",
        "proposal_logical_query_count",
        "proposal_search_batch_count",
        "active_logical_query_count",
        "active_search_batch_count",
        "total_logical_query_count",
        "total_search_batch_count",
        "proposal_batch_host_counts",
        "proposal_source_count",
        "parent_proposal_page_count",
        "proposal_observation_count",
        "proposal_observation_source_count",
        "proposal_ambiguous_source_count",
        "visible_cell_target_count",
        "selected_uncertainty_target_count",
        "active_discovered_source_count",
        "active_selected_source_count",
        "active_page_count",
        "active_observation_count",
        "active_independent_source_count",
        "active_ambiguous_source_count",
        "parent_fetch_calls",
        "active_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "parent_provider_search_calls",
        "active_provider_search_calls",
        "total_provider_search_calls",
        "safe_change_count",
        "baseline_confirmed_count",
        "unresolved_count",
        "parent_candidate_changed_cell_count",
        "active_reverted_parent_candidate_count",
        "active_safe_change_overlapping_parent_target_count",
        "candidate_changed_cell_count",
        "positive_epistemic_target_count",
        "source_credit_record_count",
        "pre_active_entropy_total_nats",
        "combined_entropy_total_nats",
        "positive_information_gain_total_nats",
        "bayesian_surprise_total_nats",
        "epistemic_credit_total_nats",
        "decision_credit_total_nats",
        "baseline_freeze_precedes_uncertainty_catalog",
        "every_visible_cell_enters_uncertainty_catalog",
        "active_target_selection_requires_preexisting_candidate_change",
        "active_queries_use_only_frozen_row_and_column",
        "active_queries_execute_as_one_nonrecursive_batch",
        "active_sources_disjoint_from_proposal_sources",
        "active_pages_used_for_model_prompt_or_candidate_generation",
        "observations_use_target_segment_programmatic_projection",
        "combined_proposal_and_active_evidence_replayed",
        "epistemic_credit_may_confirm_unchanged_baseline",
        "decision_credit_requires_safe_output_change",
        "fixed_reliability_is_uncalibrated_shadow_only",
        "parent_candidate_used_as_activation_prerequisite",
        "training_policy_or_runtime_routing_update_authorized",
        "question_prompt_response_query_url_host_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _baseline_cells(baseline: str) -> list[CellTarget]:
    columns, rows = table._table_matrix(baseline)
    rendered = table._render_table(columns, rows)
    canonical, errors = table.extract_valid_markdown_table(rendered, columns)
    if canonical != baseline or errors:
        raise ValueError("V2.43.90 baseline is not canonical")
    output = [
        CellTarget(row[0], columns[column_index], row[column_index])
        for row in rows
        for column_index in range(1, len(columns))
    ]
    if len({item.binding_sha256 for item in output}) != len(output):
        raise ValueError("V2.43.90 visible target identity drifted")
    return output


def _target_identity(row: object, column: object) -> tuple[str, str]:
    return table._support_normalize(row), table._normalize_column(column)


def _project_observations(
    baseline: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    selected_identities: set[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Project relation-bound values without exposing pages to a model."""

    if isinstance(pages, (str, bytes)):
        raise ValueError("V2.43.90 page vector drifted")
    cells = _baseline_cells(baseline)
    permitted = (
        {_target_identity(item.row_key, item.column) for item in cells}
        if selected_identities is None
        else set(selected_identities)
    )
    if not permitted.issubset(
        {_target_identity(item.row_key, item.column) for item in cells}
    ):
        raise ValueError("V2.43.90 selected projection target is not visible")
    output: list[dict[str, Any]] = []
    for raw_page in pages:
        page = _plain_page(raw_page)
        if page["fetch_integrity"] is not True:
            continue
        source = _source_key(str(page["host"]))
        content = unicodedata.normalize("NFKC", str(page["content"]))
        mentions = segment._mentions(content, cells)
        for target in cells:
            identity = _target_identity(target.row_key, target.column)
            if identity not in permitted:
                continue
            kind = segment._column_kind(target.column)
            if kind is None:
                continue
            seen: set[str] = set()
            for target_segment in segment._segments_for_target(
                content, target, mentions
            ):
                for relation, _, _ in segment._bound_relations(
                    target_segment, kind
                ):
                    normalized = _normalize(relation.value)
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)
                    output.append(
                        {
                            "row_key": target.row_key,
                            "column": target.column,
                            "value": relation.value,
                            "source_host": source,
                            "fetch_integrity": True,
                        }
                    )
    output.sort(
        key=lambda item: (
            _target_identity(item["row_key"], item["column"]),
            str(item["source_host"]),
            _normalize(item["value"]),
            str(item["value"]),
        )
    )
    return output


def _parent_baseline_and_pages(
    parent: Mapping[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    validate_parent_result(parent)
    semantic = parent["semantic_result"]
    core = semantic["core_result"]
    private = semantic["semantic_active_private_state"]
    raw_core = private["raw_core_pages"]
    raw_reserve = private["raw_reserve_pages"]
    if not isinstance(raw_core, list) or not isinstance(raw_reserve, list):
        raise ValueError("V2.43.90 parent proposal pages are unavailable")
    pages = [_plain_page(item) for item in [*raw_core, *raw_reserve]]
    return str(core["baseline_prediction"]), pages


def _selected_targets(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_uncertainty_catalog(catalog)
    by_id = {
        str(item["target_binding_sha256"]): item for item in catalog["targets"]
    }
    output: list[dict[str, Any]] = []
    for binding in catalog["selected_target_binding_sha256s"]:
        target = by_id.get(str(binding))
        if target is None:
            raise ValueError("V2.43.90 selected target binding is absent")
        output.append(
            {
                "target_binding_sha256": str(binding),
                "row_key": str(target["row_key"]),
                "column": str(target["column"]),
                "new_value": "",
            }
        )
    return output


def _select_uncertainty_leads(
    leads: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    queries: Sequence[str],
    *,
    proposal_sources: set[str],
) -> list[dict[str, str]]:
    """Select two independent sources for the single runtime target."""

    if len(targets) != RUNTIME_SELECTED_TARGET_CAP or len(queries) != len(targets):
        if not targets and not queries:
            return []
        raise ValueError("V2.43.90 runtime target capacity drifted")
    available: dict[str, dict[str, str]] = {}
    for raw in leads:
        lead = _lead_projection(raw)
        source = _source_from_lead(lead)
        if source in proposal_sources or source in available:
            continue
        available[source] = lead
    target = targets[0]
    ranked = sorted(
        available.values(),
        key=lambda lead: (
            tuple(-number for number in _target_score(lead, [target])),
            tuple(-number for number in _coverage(lead, queries)[1]),
            _source_from_lead(lead),
        ),
    )
    return [copy.deepcopy(item) for item in ranked[:MAXIMUM_ACTIVE_SOURCES]]


class UncertaintyActiveEvidenceSearchClient(ActiveVerifierQuerySearchClient):
    """Reuse proposal discovery, then search from baseline uncertainty."""

    def active_search_and_fetch(  # type: ignore[override]
        self,
        parent: Mapping[str, Any],
        *,
        page_character_cap: int,
    ) -> dict[str, Any]:
        if not self.search_completed:
            raise RuntimeError("V2.43.90 active query preceded proposal discovery")
        if self.active_completed:
            raise RuntimeError("V2.43.90 active query repeated")
        self.proposal_parent_union_receipt = self._union.receipt()
        proposal_state = self.proposal_selection_state()
        baseline, proposal_pages = _parent_baseline_and_pages(parent)
        proposal_observations = _project_observations(baseline, proposal_pages)
        catalog = build_uncertainty_catalog(
            baseline,
            proposal_observations,
            maximum_selected_targets=RUNTIME_SELECTED_TARGET_CAP,
        )
        targets = _selected_targets(catalog)
        queries = list(catalog["active_queries"])
        if len(targets) != len(queries) or len(queries) > MAXIMUM_ACTIVE_QUERIES:
            raise ValueError("V2.43.90 uncertainty query vector drifted")
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
        leads = _unique_host_leads(raw, batch_ordinal=3) if queries else []
        proposal_sources = {
            _source_from_lead(lead)
            for batch in proposal_state["proposal_batch_leads"]
            for lead in batch
        }
        selected = _select_uncertainty_leads(
            leads,
            targets,
            queries,
            proposal_sources=proposal_sources,
        )
        fetched = self._union.fetch_urls(selected) if selected else []
        pages = table._page_vector(
            fetched, prefix="A", page_chars=page_character_cap
        )
        selected_identities = {
            _target_identity(item["row_key"], item["column"])
            for item in targets
        }
        active_observations = _project_observations(
            baseline,
            [_plain_page(item) for item in pages],
            selected_identities=selected_identities,
        )
        active_result = apply_active_evidence(catalog, active_observations)
        self.active_completed = True
        return {
            "proposal_selection_state": proposal_state,
            "proposal_observations": proposal_observations,
            "uncertainty_catalog": catalog,
            "active_union_leads": [_lead_projection(lead) for lead in leads],
            "selected_active_leads": copy.deepcopy(selected),
            "active_fetch_batches": [
                dict(item) for item in fetched if isinstance(item, Mapping)
            ],
            "active_pages": pages,
            "active_observations": active_observations,
            "active_evidence_result": active_result,
            "active_union_receipt_after_active": self._union.receipt(),
            "page_character_cap": page_character_cap,
            "active_provider_search_calls": active_provider_search_calls,
        }


def _receipt(
    parent: Mapping[str, Any],
    private: Mapping[str, Any],
    *,
    candidate_prediction: str,
    merge_accounting: Mapping[str, int],
    partition_seed_sha256: str,
) -> dict[str, Any]:
    semantic = parent["semantic_result"]
    core = semantic["core_result"]
    proposal_state = private["proposal_selection_state"]
    proposal_observations = private["proposal_observations"]
    catalog = private["uncertainty_catalog"]
    active_result = private["active_evidence_result"]
    entropy_receipt = active_result["receipt"]
    active_selected = private["selected_active_leads"]
    proposal_count = sum(
        len(batch) for batch in proposal_state["proposal_batch_leads"]
    )
    active_queries = list(catalog["active_queries"])
    parent_fetches = int(core["cost"]["search"]["fetch_calls"])
    baseline = str(core["baseline_prediction"])
    candidate = str(candidate_prediction)
    changes = _changed_cells(baseline, candidate)
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": PARENT_POLICY_ID,
        "entropy_policy_id": ENTROPY_POLICY_ID,
        "partition_seed_sha256": partition_seed_sha256,
        "proposal_logical_query_count": PROPOSAL_LOGICAL_QUERIES,
        "proposal_search_batch_count": PROPOSAL_SEARCH_BATCHES,
        "active_logical_query_count": len(active_queries),
        "active_search_batch_count": int(bool(active_queries)),
        "total_logical_query_count": PROPOSAL_LOGICAL_QUERIES
        + len(active_queries),
        "total_search_batch_count": PROPOSAL_SEARCH_BATCHES
        + int(bool(active_queries)),
        "proposal_batch_host_counts": [
            len(batch) for batch in proposal_state["proposal_batch_leads"]
        ],
        "proposal_source_count": proposal_count,
        "parent_proposal_page_count": len(
            semantic["semantic_active_private_state"]["raw_core_pages"]
        )
        + len(semantic["semantic_active_private_state"]["raw_reserve_pages"]),
        "proposal_observation_count": len(proposal_observations),
        "proposal_observation_source_count": len(
            {str(item["source_host"]) for item in proposal_observations}
        ),
        "proposal_ambiguous_source_count": sum(
            int(item["proposal_ambiguous_source_count"])
            for item in catalog["targets"]
        ),
        "visible_cell_target_count": len(catalog["targets"]),
        "selected_uncertainty_target_count": int(
            entropy_receipt["selected_target_count"]
        ),
        "active_discovered_source_count": len(private["active_union_leads"]),
        "active_selected_source_count": len(active_selected),
        "active_page_count": len(private["active_pages"]),
        "active_observation_count": int(
            entropy_receipt["active_observation_count"]
        ),
        "active_independent_source_count": int(
            entropy_receipt["active_independent_source_count"]
        ),
        "active_ambiguous_source_count": int(
            entropy_receipt["active_ambiguous_source_count"]
        ),
        "parent_fetch_calls": parent_fetches,
        "active_fetch_calls": len(active_selected),
        "total_fetch_calls": parent_fetches + len(active_selected),
        "parent_model_requests": int(core["cost"]["model"]["requests"]),
        "parent_provider_search_calls": int(core["cost"]["search"]["calls"]),
        "active_provider_search_calls": int(private["active_provider_search_calls"]),
        "total_provider_search_calls": int(core["cost"]["search"]["calls"])
        + int(private["active_provider_search_calls"]),
        "safe_change_count": int(entropy_receipt["safe_change_count"]),
        "baseline_confirmed_count": int(
            entropy_receipt["baseline_confirmed_count"]
        ),
        "unresolved_count": int(entropy_receipt["unresolved_count"]),
        "parent_candidate_changed_cell_count": int(
            merge_accounting["parent_candidate_changed_cell_count"]
        ),
        "active_reverted_parent_candidate_count": int(
            merge_accounting["active_reverted_parent_candidate_count"]
        ),
        "active_safe_change_overlapping_parent_target_count": int(
            merge_accounting[
                "active_safe_change_overlapping_parent_target_count"
            ]
        ),
        "candidate_changed_cell_count": len(changes),
        "positive_epistemic_target_count": int(
            entropy_receipt["positive_epistemic_target_count"]
        ),
        "source_credit_record_count": int(
            entropy_receipt["source_credit_record_count"]
        ),
        "pre_active_entropy_total_nats": float(
            entropy_receipt["pre_active_entropy_total_nats"]
        ),
        "combined_entropy_total_nats": float(
            entropy_receipt["combined_entropy_total_nats"]
        ),
        "positive_information_gain_total_nats": float(
            entropy_receipt["positive_information_gain_total_nats"]
        ),
        "bayesian_surprise_total_nats": float(
            entropy_receipt["bayesian_surprise_total_nats"]
        ),
        "epistemic_credit_total_nats": float(
            entropy_receipt["epistemic_credit_total_nats"]
        ),
        "decision_credit_total_nats": float(
            entropy_receipt["decision_credit_total_nats"]
        ),
        "baseline_freeze_precedes_uncertainty_catalog": True,
        "every_visible_cell_enters_uncertainty_catalog": True,
        "active_target_selection_requires_preexisting_candidate_change": False,
        "active_queries_use_only_frozen_row_and_column": True,
        "active_queries_execute_as_one_nonrecursive_batch": True,
        "active_sources_disjoint_from_proposal_sources": not set(
            _source_vectors(proposal_state["proposal_batch_leads"])
        )
        & {
            _source_digest_from_lead(lead) for lead in active_selected
        },
        "active_pages_used_for_model_prompt_or_candidate_generation": False,
        "observations_use_target_segment_programmatic_projection": True,
        "combined_proposal_and_active_evidence_replayed": True,
        "epistemic_credit_may_confirm_unchanged_baseline": True,
        "decision_credit_requires_safe_output_change": True,
        "fixed_reliability_is_uncalibrated_shadow_only": True,
        "parent_candidate_used_as_activation_prerequisite": False,
        "training_policy_or_runtime_routing_update_authorized": False,
        "question_prompt_response_query_url_host_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_receipt(value)
    return value


def _finite(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    count_fields = (
        "proposal_logical_query_count",
        "proposal_search_batch_count",
        "active_logical_query_count",
        "active_search_batch_count",
        "total_logical_query_count",
        "total_search_batch_count",
        "proposal_source_count",
        "parent_proposal_page_count",
        "proposal_observation_count",
        "proposal_observation_source_count",
        "proposal_ambiguous_source_count",
        "visible_cell_target_count",
        "selected_uncertainty_target_count",
        "active_discovered_source_count",
        "active_selected_source_count",
        "active_page_count",
        "active_observation_count",
        "active_independent_source_count",
        "active_ambiguous_source_count",
        "parent_fetch_calls",
        "active_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "parent_provider_search_calls",
        "active_provider_search_calls",
        "total_provider_search_calls",
        "safe_change_count",
        "baseline_confirmed_count",
        "unresolved_count",
        "parent_candidate_changed_cell_count",
        "active_reverted_parent_candidate_count",
        "active_safe_change_overlapping_parent_target_count",
        "candidate_changed_cell_count",
        "positive_epistemic_target_count",
        "source_credit_record_count",
    )
    numeric_fields = (
        "pre_active_entropy_total_nats",
        "combined_entropy_total_nats",
        "positive_information_gain_total_nats",
        "bayesian_surprise_total_nats",
        "epistemic_credit_total_nats",
        "decision_credit_total_nats",
    )
    true_fields = (
        "baseline_freeze_precedes_uncertainty_catalog",
        "every_visible_cell_enters_uncertainty_catalog",
        "active_queries_use_only_frozen_row_and_column",
        "active_queries_execute_as_one_nonrecursive_batch",
        "active_sources_disjoint_from_proposal_sources",
        "observations_use_target_segment_programmatic_projection",
        "combined_proposal_and_active_evidence_replayed",
        "epistemic_credit_may_confirm_unchanged_baseline",
        "decision_credit_requires_safe_output_change",
        "fixed_reliability_is_uncalibrated_shadow_only",
    )
    false_fields = (
        "active_target_selection_requires_preexisting_candidate_change",
        "active_pages_used_for_model_prompt_or_candidate_generation",
        "parent_candidate_used_as_activation_prerequisite",
        "training_policy_or_runtime_routing_update_authorized",
        "question_prompt_response_query_url_host_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    host_counts = value.get("proposal_batch_host_counts")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("parent_policy_id") != PARENT_POLICY_ID
        or value.get("entropy_policy_id") != ENTROPY_POLICY_ID
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("partition_seed_sha256")))
        is None
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(not _finite(value.get(name)) for name in numeric_fields)
        or not isinstance(host_counts, list)
        or len(host_counts) != PROPOSAL_SEARCH_BATCHES
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in host_counts
        )
        or any(value.get(name) is not True for name in true_fields)
        or any(value.get(name) is not False for name in false_fields)
        or value["proposal_logical_query_count"] != PROPOSAL_LOGICAL_QUERIES
        or value["proposal_search_batch_count"] != PROPOSAL_SEARCH_BATCHES
        or value["active_logical_query_count"] > MAXIMUM_ACTIVE_QUERIES
        or value["active_search_batch_count"]
        != int(value["active_logical_query_count"] > 0)
        or value["total_logical_query_count"]
        != PROPOSAL_LOGICAL_QUERIES + value["active_logical_query_count"]
        or value["total_search_batch_count"]
        != PROPOSAL_SEARCH_BATCHES + value["active_search_batch_count"]
        or value["proposal_source_count"] != sum(host_counts)
        or value["proposal_source_count"] > MAXIMUM_PROPOSAL_SOURCES
        or value["parent_proposal_page_count"] > value["proposal_source_count"]
        or value["proposal_observation_source_count"]
        > value["parent_proposal_page_count"]
        or value["selected_uncertainty_target_count"]
        != value["active_logical_query_count"]
        or value["selected_uncertainty_target_count"] > MAXIMUM_ACTIVE_TARGETS
        or value["active_selected_source_count"] > MAXIMUM_ACTIVE_SOURCES
        or value["active_selected_source_count"]
        > value["active_discovered_source_count"]
        or value["active_page_count"] > value["active_selected_source_count"]
        or value["active_independent_source_count"]
        > value["active_selected_source_count"]
        or value["active_fetch_calls"] != value["active_selected_source_count"]
        or value["total_fetch_calls"]
        != value["parent_fetch_calls"] + value["active_fetch_calls"]
        or value["total_fetch_calls"] > MAXIMUM_TOTAL_FETCHES
        or value["parent_provider_search_calls"]
        < value["proposal_search_batch_count"]
        or value["active_provider_search_calls"]
        < value["active_search_batch_count"]
        or value["total_provider_search_calls"]
        != value["parent_provider_search_calls"]
        + value["active_provider_search_calls"]
        or value["safe_change_count"]
        + value["baseline_confirmed_count"]
        + value["unresolved_count"]
        != value["selected_uncertainty_target_count"]
        or value["active_reverted_parent_candidate_count"]
        > value["parent_candidate_changed_cell_count"]
        or value["active_safe_change_overlapping_parent_target_count"]
        > min(
            value["safe_change_count"],
            value["parent_candidate_changed_cell_count"],
        )
        or value["candidate_changed_cell_count"]
        != value["parent_candidate_changed_cell_count"]
        - value["active_reverted_parent_candidate_count"]
        + value["safe_change_count"]
        - value["active_safe_change_overlapping_parent_target_count"]
        or value["positive_epistemic_target_count"]
        > value["selected_uncertainty_target_count"]
        or value["decision_credit_total_nats"]
        > value["epistemic_credit_total_nats"] + 1e-12
        or (
            value["decision_credit_total_nats"] > 0
            and value["safe_change_count"] == 0
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.90 uncertainty active receipt drifted")
    return copy.deepcopy(dict(value))


def _merge_parent_candidate(
    parent: Mapping[str, Any], active_result: Mapping[str, Any]
) -> tuple[str, dict[str, int]]:
    """Preserve safe parent changes outside explicit active resolution."""

    validate_active_evidence_result(active_result)
    core = parent["semantic_result"]["core_result"]
    baseline = str(core["baseline_prediction"])
    parent_candidate = str(core["candidate_prediction"])
    parent_changes = _changed_cells(baseline, parent_candidate)
    parent_changed_identities = {
        _target_identity(item["row_key"], item["column"])
        for item in parent_changes
    }
    columns, baseline_rows = table._table_matrix(baseline)
    candidate_columns, candidate_rows = table._table_matrix(parent_candidate)
    if [table._normalize_column(item) for item in columns] != [
        table._normalize_column(item) for item in candidate_columns
    ]:
        raise ValueError("V2.43.90 parent candidate columns drifted")
    candidate_by_row = {
        table._support_normalize(row[0]): list(row) for row in candidate_rows
    }
    if len(candidate_by_row) != len(candidate_rows):
        raise ValueError("V2.43.90 parent candidate row identity drifted")
    output_rows = [
        list(candidate_by_row[table._support_normalize(row[0])])
        for row in baseline_rows
    ]
    catalog_targets = {
        str(item["target_binding_sha256"]): item
        for item in active_result["catalog"]["targets"]
    }
    reverted = 0
    safe_overlap = 0
    for resolution in active_result["resolutions"]:
        target = catalog_targets.get(str(resolution["target_binding_sha256"]))
        if target is None:
            raise ValueError("V2.43.90 active resolution target is absent")
        identity = _target_identity(target["row_key"], target["column"])
        row_index = int(target["row_index"])
        column_index = int(target["column_index"])
        parent_changed = identity in parent_changed_identities
        if resolution["final_value_changed"]:
            output_rows[row_index][column_index] = str(resolution["final_value"])
            safe_overlap += int(parent_changed)
        elif int(resolution["active_observation_count"]) > 0:
            output_rows[row_index][column_index] = baseline_rows[row_index][
                column_index
            ]
            reverted += int(parent_changed)
    candidate = table._render_table(columns, output_rows)
    canonical, errors = table.extract_valid_markdown_table(candidate, columns)
    if canonical != candidate or errors:
        raise ValueError("V2.43.90 merged candidate is not canonical")
    final_changes = _changed_cells(baseline, candidate)
    accounting = {
        "parent_candidate_changed_cell_count": len(parent_changes),
        "active_reverted_parent_candidate_count": reverted,
        "active_safe_change_overlapping_parent_target_count": safe_overlap,
        "candidate_changed_cell_count": len(final_changes),
    }
    expected = (
        len(parent_changes)
        - reverted
        + int(active_result["receipt"]["safe_change_count"])
        - safe_overlap
    )
    if len(final_changes) != expected:
        raise ValueError("V2.43.90 parent/active merge accounting drifted")
    return candidate, accounting


def _derive(
    parent: Mapping[str, Any],
    private: Mapping[str, Any],
    *,
    partition_seed_sha256: str,
) -> dict[str, Any]:
    validate_parent_result(parent)
    if set(private) != PRIVATE_KEYS:
        raise ValueError("V2.43.90 private replay identity drifted")
    proposal_state = private["proposal_selection_state"]
    # The inherited validator is reached through this replaying method.
    baseline, proposal_pages = _parent_baseline_and_pages(parent)
    proposal_observations = _project_observations(baseline, proposal_pages)
    catalog = build_uncertainty_catalog(
        baseline,
        proposal_observations,
        maximum_selected_targets=RUNTIME_SELECTED_TARGET_CAP,
    )
    validate_uncertainty_catalog(private["uncertainty_catalog"])
    if (
        private["proposal_observations"] != proposal_observations
        or private["uncertainty_catalog"] != catalog
    ):
        raise ValueError("V2.43.90 proposal uncertainty replay drifted")
    proposal_state = _validate_selection_state(proposal_state)
    final_union = private["active_union_receipt_after_active"]
    validate_union_receipt(final_union)
    raw_leads = [_lead_projection(item) for item in private["active_union_leads"]]
    targets = _selected_targets(catalog)
    queries = list(catalog["active_queries"])
    proposal_sources = {
        _source_from_lead(lead)
        for batch in proposal_state["proposal_batch_leads"]
        for lead in batch
    }
    expected_selected = _select_uncertainty_leads(
        raw_leads, targets, queries, proposal_sources=proposal_sources
    )
    if private["selected_active_leads"] != expected_selected:
        raise ValueError("V2.43.90 active source selection replay drifted")
    if (
        isinstance(private.get("page_character_cap"), bool)
        or not isinstance(private.get("page_character_cap"), int)
        or private["page_character_cap"] <= 0
        or isinstance(private.get("active_provider_search_calls"), bool)
        or not isinstance(private.get("active_provider_search_calls"), int)
        or private["active_provider_search_calls"] < 0
    ):
        raise ValueError("V2.43.90 active private scalar drifted")
    rebuilt_pages = table._page_vector(
        private["active_fetch_batches"],
        prefix="A",
        page_chars=int(private["page_character_cap"]),
    )
    if private["active_pages"] != rebuilt_pages:
        raise ValueError("V2.43.90 active page replay drifted")
    selected_identities = {
        _target_identity(item["row_key"], item["column"]) for item in targets
    }
    active_observations = _project_observations(
        baseline,
        [_plain_page(item) for item in rebuilt_pages],
        selected_identities=selected_identities,
    )
    if private["active_observations"] != active_observations:
        raise ValueError("V2.43.90 active observation replay drifted")
    active_result = apply_active_evidence(catalog, active_observations)
    validate_active_evidence_result(private["active_evidence_result"])
    if private["active_evidence_result"] != active_result:
        raise ValueError("V2.43.90 active evidence posterior replay drifted")
    proposal_count = sum(
        len(batch) for batch in proposal_state["proposal_batch_leads"]
    )
    if (
        final_union["search_invocations"]
        != PROPOSAL_SEARCH_BATCHES + int(bool(queries))
        or final_union["logical_query_count"]
        != PROPOSAL_LOGICAL_QUERIES + len(queries)
        or final_union["fetch_requested_source_count"]
        != proposal_count + len(expected_selected)
    ):
        raise ValueError("V2.43.90 final union effect replay drifted")
    canonical_private = {
        **copy.deepcopy(dict(private)),
        "proposal_selection_state": proposal_state,
        "proposal_observations": proposal_observations,
        "uncertainty_catalog": catalog,
        "active_union_leads": raw_leads,
        "selected_active_leads": expected_selected,
        "active_pages": rebuilt_pages,
        "active_observations": active_observations,
        "active_evidence_result": active_result,
    }
    candidate, merge_accounting = _merge_parent_candidate(parent, active_result)
    receipt = _receipt(
        parent,
        canonical_private,
        candidate_prediction=candidate,
        merge_accounting=merge_accounting,
        partition_seed_sha256=partition_seed_sha256,
    )
    return {
        "baseline_prediction": baseline,
        "candidate_prediction": candidate,
        "private": canonical_private,
        "receipt": receipt,
    }


def run_v24390_task(
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
        or re.fullmatch(r"[0-9a-f]{64}", partition_seed_sha256) is None
    ):
        raise ValueError("V2.43.90 fixed effect cap or seed drifted")
    staged = UncertaintyActiveEvidenceSearchClient(search)
    parent = run_v24349_task(
        visible,
        model=model,
        search=staged,
        limits=chosen,
        monotonic=monotonic,
    )
    validate_parent_result(parent)
    private = staged.active_search_and_fetch(
        parent, page_character_cap=chosen.page_chars
    )
    derived = _derive(
        parent, private, partition_seed_sha256=partition_seed_sha256
    )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(parent),
        "baseline_prediction": derived["baseline_prediction"],
        "candidate_prediction": derived["candidate_prediction"],
        "uncertainty_active_receipt": derived["receipt"],
        "private_replay_state": derived["private"],
    }
    value["result_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    parent = value.get("parent_result")
    receipt = value.get("uncertainty_active_receipt")
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
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.90 result identity drifted")
    validate_parent_result(parent)
    validate_receipt(receipt)
    expected = _derive(
        parent,
        private,
        partition_seed_sha256=str(receipt["partition_seed_sha256"]),
    )
    if (
        value["baseline_prediction"] != expected["baseline_prediction"]
        or value["candidate_prediction"] != expected["candidate_prediction"]
        or dict(receipt) != expected["receipt"]
        or dict(private) != expected["private"]
    ):
        raise ValueError("V2.43.90 deterministic replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "MAXIMUM_TOTAL_FETCHES",
    "POLICY_ID",
    "ROLE",
    "UncertaintyActiveEvidenceSearchClient",
    "run_v24390_task",
    "validate_receipt",
    "validate_result",
]
