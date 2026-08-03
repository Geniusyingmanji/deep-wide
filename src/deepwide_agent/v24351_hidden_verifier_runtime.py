"""Hidden-verifier wrapper for duplicate-safe semantic entropy search.

One hosted-search response is converted into at most ten registrable-source
leads.  A seed-only source partition is frozen before any page is fetched or
candidate value exists.  The V2.43.49 parent sees and fetches proposal leads
only.  Hidden verifier leads are fetched after the parent candidate is frozen;
they can only reject or retain already-admitted changes, never generate a new
candidate or enter a model prompt.

This module has no benchmark selection, evaluator, or score access.  Runtime
inputs remain the visible ``{opaque_id, question}`` pair plus ordinary clients.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from . import v24325_shared_prefix_revision_runtime as base
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import _normalize as catalog_normalize
from .v24333_programmatic_support_catalog import _source_key
from .v24335_programmatic_support_runtime import _declaration_map
from .v24348_structural_table_normalizer import semantic_targets
from .v24349_structural_semantic_runtime import (
    run_v24349_task,
    validate_result as validate_parent_result,
)
from .v24350_independent_entropy_utility import (
    build_independent_utility_catalog,
    resolve_independent_utility_selection,
    validate_independent_utility_catalog,
    validate_independent_utility_receipt,
)


POLICY_ID = "v24351_hidden_verifier_structural_entropy_runtime_v1"
ROLE = "v24351_hidden_verifier_task_result"
RECEIPT_ROLE = "v24351_hidden_verifier_runtime_receipt"
PARTITION_ROLE = "v24351_preproposal_source_partition_receipt"
MAXIMUM_FETCH_SOURCES = 10
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "baseline_prediction",
        "candidate_prediction",
        "hidden_verifier_receipt",
        "private_replay_state",
        "result_sha256",
    }
)
PRIVATE_KEYS = frozenset(
    {
        "partition",
        "page_character_cap",
        "verifier_fetch_batches",
        "verifier_pages",
        "utility_catalog",
        "cell_utility_resolutions",
    }
)
PARTITION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "partition_seed_sha256",
        "discovered_unique_source_count",
        "selected_source_count",
        "proposal_source_count",
        "verifier_source_count",
        "proposal_source_key_sha256s",
        "verifier_source_key_sha256s",
        "proposal_lead_binding_sha256s",
        "verifier_lead_binding_sha256s",
        "source_partition_precedes_fetch_and_candidate_discovery",
        "partition_uses_seed_and_registrable_source_only",
        "candidate_value_entropy_page_content_or_evaluator_used_for_partition",
        "proposal_and_verifier_sources_disjoint",
        "verifier_leads_exposed_to_parent_search_or_model_prompt",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "partition_receipt",
        "partition_replay_matches_successful_pages",
        "parent_proposal_page_count",
        "hidden_verifier_page_count",
        "parent_fetch_calls",
        "hidden_verifier_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "candidate_changed_cells_before_hidden_verifier",
        "candidate_changed_cells_after_hidden_verifier",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
        "proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
        "hidden_verifier_pages_used_for_candidate_generation_or_model_prompt",
        "new_candidate_value_generated_by_hidden_verifier",
        "baseline_and_candidate_share_exact_proposal_pages",
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source_from_lead(lead: Mapping[str, Any]) -> str:
    raw = str(lead.get("fetch_url") or lead.get("url") or "")
    host = (urlsplit(base.canonicalize_url(raw)).hostname or "").casefold()
    return _source_key(host)


def _source_digest_from_lead(lead: Mapping[str, Any]) -> str:
    return _sha256_text(_source_from_lead(lead))


def _lead_binding(lead: Mapping[str, Any]) -> str:
    return payload_sha256(
        {
            "registrable_source_sha256": _source_digest_from_lead(lead),
            "canonical_url_sha256": _sha256_text(
                base.canonicalize_url(
                    str(lead.get("fetch_url") or lead.get("url") or "")
                )
            ),
        }
    )


def _partition_leads(
    leads: Sequence[Mapping[str, Any]],
    *,
    partition_seed_sha256: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    if re.fullmatch(r"[0-9a-f]{64}", partition_seed_sha256) is None:
        raise ValueError("V2.43.51 partition seed drifted")
    by_source: dict[str, dict[str, str]] = {}
    source_order: list[str] = []
    for raw in leads:
        if not isinstance(raw, Mapping):
            continue
        lead = {
            "url": str(raw.get("url") or raw.get("fetch_url") or ""),
            "query": str(raw.get("query") or ""),
            "title": str(raw.get("title") or "")[:500],
            "member_label": str(raw.get("member_label") or ""),
        }
        try:
            source = _source_from_lead(lead)
        except ValueError:
            continue
        if source in by_source:
            continue
        by_source[source] = lead
        source_order.append(source)
    selected_sources = source_order[:MAXIMUM_FETCH_SOURCES]
    verifier_count = max(1, len(selected_sources) // 4) if len(selected_sources) >= 3 else 0
    ranked = sorted(
        selected_sources,
        key=lambda source: (
            _sha256_text(partition_seed_sha256 + "|" + source),
            source,
        ),
    )
    verifier_sources = set(ranked[:verifier_count])
    proposal = [by_source[source] for source in selected_sources if source not in verifier_sources]
    verifier = [by_source[source] for source in selected_sources if source in verifier_sources]
    proposal_hashes = sorted(_source_digest_from_lead(lead) for lead in proposal)
    verifier_hashes = sorted(_source_digest_from_lead(lead) for lead in verifier)
    value = {
        "artifact_version": 1,
        "role": PARTITION_ROLE,
        "policy_id": POLICY_ID,
        "partition_seed_sha256": partition_seed_sha256,
        "discovered_unique_source_count": len(source_order),
        "selected_source_count": len(selected_sources),
        "proposal_source_count": len(proposal),
        "verifier_source_count": len(verifier),
        "proposal_source_key_sha256s": proposal_hashes,
        "verifier_source_key_sha256s": verifier_hashes,
        "proposal_lead_binding_sha256s": sorted(_lead_binding(lead) for lead in proposal),
        "verifier_lead_binding_sha256s": sorted(_lead_binding(lead) for lead in verifier),
        "source_partition_precedes_fetch_and_candidate_discovery": True,
        "partition_uses_seed_and_registrable_source_only": True,
        "candidate_value_entropy_page_content_or_evaluator_used_for_partition": False,
        "proposal_and_verifier_sources_disjoint": not set(proposal_hashes)
        & set(verifier_hashes),
        "verifier_leads_exposed_to_parent_search_or_model_prompt": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_partition_receipt(value)
    return proposal, verifier, value


def validate_partition_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    integer_names = (
        "discovered_unique_source_count",
        "selected_source_count",
        "proposal_source_count",
        "verifier_source_count",
    )
    vectors = (
        "proposal_source_key_sha256s",
        "verifier_source_key_sha256s",
        "proposal_lead_binding_sha256s",
        "verifier_lead_binding_sha256s",
    )
    if (
        set(value) != PARTITION_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != PARTITION_ROLE
        or value.get("policy_id") != POLICY_ID
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("partition_seed_sha256")))
        is None
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in integer_names
        )
        or value.get("selected_source_count", -1) > MAXIMUM_FETCH_SOURCES
        or value.get("selected_source_count")
        != value.get("proposal_source_count") + value.get("verifier_source_count")
        or value.get("selected_source_count", 0)
        > value.get("discovered_unique_source_count", -1)
        or any(not isinstance(value.get(name), list) for name in vectors)
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(item)) is None
            for name in vectors
            for item in value[name]
        )
        or len(value.get("proposal_source_key_sha256s", []))
        != value.get("proposal_source_count")
        or len(value.get("verifier_source_key_sha256s", []))
        != value.get("verifier_source_count")
        or len(value.get("proposal_lead_binding_sha256s", []))
        != value.get("proposal_source_count")
        or len(value.get("verifier_lead_binding_sha256s", []))
        != value.get("verifier_source_count")
        or set(value.get("proposal_source_key_sha256s", []))
        & set(value.get("verifier_source_key_sha256s", []))
        or value.get("source_partition_precedes_fetch_and_candidate_discovery") is not True
        or value.get("partition_uses_seed_and_registrable_source_only") is not True
        or value.get("candidate_value_entropy_page_content_or_evaluator_used_for_partition") is not False
        or value.get("proposal_and_verifier_sources_disjoint") is not True
        or value.get("verifier_leads_exposed_to_parent_search_or_model_prompt") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.51 partition receipt drifted")
    return dict(value)


class PreproposalPartitionSearchClient:
    """Expose proposal leads to the parent and retain hidden verifier leads."""

    def __init__(self, inner: Any, *, partition_seed_sha256: str) -> None:
        self._union = TaskUnionDiscoverySearchClient(inner)
        self.partition_seed_sha256 = partition_seed_sha256
        self.proposal_leads: list[dict[str, str]] = []
        self.verifier_leads: list[dict[str, str]] = []
        self.partition_receipt: dict[str, Any] | None = None
        self.verifier_fetch_batches: list[dict[str, Any]] | None = None
        self.search_completed = False
        self.verifier_fetch_completed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._union, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        if self.search_completed:
            raise RuntimeError("V2.43.51 hosted search repeated")
        raw = self._union.search_many(queries, **kwargs)
        leads = base._lead_requests(raw, MAXIMUM_FETCH_SOURCES)
        proposal, verifier, receipt = _partition_leads(
            leads,
            partition_seed_sha256=self.partition_seed_sha256,
        )
        self.proposal_leads = proposal
        self.verifier_leads = verifier
        self.partition_receipt = receipt
        self.search_completed = True
        if not proposal:
            return []
        return [
            {
                "query": "preproposal source-partitioned discovery",
                "answer": "",
                "results": copy.deepcopy(proposal),
                "error": None,
                "provider": "v24351-proposal-only-source-partition",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        allowed = {
            base.canonicalize_url(str(lead["url"])) for lead in self.proposal_leads
        }
        requested = list(requests_)
        if any(
            base.canonicalize_url(str(item.get("url") or item.get("fetch_url") or ""))
            not in allowed
            for item in requested
        ):
            raise RuntimeError("V2.43.51 parent attempted hidden-verifier fetch")
        return self._union.fetch_urls(requested)

    def fetch_hidden_verifier(self) -> list[dict[str, Any]]:
        if not self.search_completed or self.partition_receipt is None:
            raise RuntimeError("V2.43.51 verifier fetch preceded source partition")
        if self.verifier_fetch_completed:
            raise RuntimeError("V2.43.51 verifier fetch repeated")
        raw = self._union.fetch_urls(self.verifier_leads) if self.verifier_leads else []
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            batches: list[dict[str, Any]] = []
        else:
            batches = [dict(item) for item in raw if isinstance(item, Mapping)]
        self.verifier_fetch_batches = batches
        self.verifier_fetch_completed = True
        return batches


def _plain_page(page: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "host": str(page["host"]),
        "content": str(page["content"]),
        "fetch_integrity": True,
    }


def _changed_cells(baseline: str, candidate: str) -> list[dict[str, Any]]:
    columns, baseline_rows = base._table_matrix(baseline)
    candidate_columns, candidate_rows = base._table_matrix(candidate)
    if [base._normalize_column(value) for value in columns] != [
        base._normalize_column(value) for value in candidate_columns
    ]:
        raise ValueError("V2.43.51 candidate columns drifted")
    baseline_by_key = {
        base._support_normalize(row[0]): row for row in baseline_rows
    }
    candidate_by_key = {
        base._support_normalize(row[0]): row for row in candidate_rows
    }
    if (
        len(baseline_by_key) != len(baseline_rows)
        or len(candidate_by_key) != len(candidate_rows)
        or set(candidate_by_key) != set(baseline_by_key)
    ):
        raise ValueError("V2.43.51 paired row identity drifted")
    output: list[dict[str, Any]] = []
    for row_index, baseline_row in enumerate(baseline_rows):
        key = base._support_normalize(baseline_row[0])
        candidate_row = candidate_by_key[key]
        for column_index in range(1, len(columns)):
            if base._support_normalize(baseline_row[column_index]) == base._support_normalize(
                candidate_row[column_index]
            ):
                continue
            output.append(
                {
                    "row_index": row_index,
                    "row_key": baseline_row[0],
                    "column_index": column_index,
                    "column": columns[column_index],
                    "old_value": baseline_row[column_index],
                    "new_value": candidate_row[column_index],
                }
            )
    return output


def _filter_candidate(
    parent: Mapping[str, Any],
    utility_catalog: Mapping[str, Any] | None,
    *,
    partition_matches: bool,
) -> tuple[str, list[dict[str, Any]], int, int, float, float]:
    semantic = parent["semantic_result"]
    core = semantic["core_result"]
    baseline = str(core["baseline_prediction"])
    candidate = str(core["candidate_prediction"])
    changes = _changed_cells(baseline, candidate)
    columns, baseline_rows = base._table_matrix(baseline)
    _, candidate_rows = base._table_matrix(candidate)
    output_rows = [list(row) for row in candidate_rows]
    proposal_credit = 0.0
    aligned_credit = 0.0
    resolutions: list[dict[str, Any]] = []
    declarations = _declaration_map(
        semantic["semantic_active_private_state"]["cell_support"],
        columns,
    )
    utility_items = (
        list(utility_catalog["utility_sets"])
        if partition_matches and utility_catalog is not None
        else []
    )
    for change in changes:
        declaration = declarations.get(
            (
                base._support_normalize(change["row_key"]),
                int(change["column_index"]),
            )
        )
        item = next(
            (
                entry
                for entry in utility_items
                if declaration is not None
                and entry["proposal_support_set_id"] == declaration["support_set_id"]
                and catalog_normalize(entry["row_key"])
                == catalog_normalize(change["row_key"])
                and catalog_normalize(entry["column"])
                == catalog_normalize(change["column"])
                and catalog_normalize(entry["candidate_value"])
                == catalog_normalize(change["new_value"])
            ),
            None,
        )
        if item is None or declaration is None:
            output_rows[int(change["row_index"])][int(change["column_index"])] = str(
                change["old_value"]
            )
            continue
        receipt = resolve_independent_utility_selection(
            utility_catalog,
            row_key=str(change["row_key"]),
            column=str(change["column"]),
            new_value=str(change["new_value"]),
            utility_set_id=str(item["utility_set_id"]),
            declared_proposal_evidence_ids=declaration["evidence_ids"],
        )
        validate_independent_utility_receipt(receipt)
        resolutions.append(receipt)
        proposal_credit += float(receipt["proposal_conditional_entropy_reduction_nats"])
        if receipt["admitted"]:
            aligned_credit += float(receipt["utility_aligned_entropy_credit_nats"])
        else:
            output_rows[int(change["row_index"])][int(change["column_index"])] = str(
                change["old_value"]
            )
    filtered = base._render_table(columns, output_rows)
    canonical, errors = base.extract_valid_markdown_table(filtered, columns)
    if canonical != filtered or errors:
        raise ValueError("V2.43.51 filtered candidate is not canonical")
    retained = len(_changed_cells(baseline, filtered))
    return (
        filtered,
        resolutions,
        len(changes),
        retained,
        round(proposal_credit, 12),
        round(aligned_credit, 12),
    )


def _partition_matches_pages(
    partition: Mapping[str, Any],
    utility_catalog: Mapping[str, Any],
) -> bool:
    return (
        partition["proposal_source_key_sha256s"]
        == utility_catalog["proposal_source_key_sha256s"]
        and partition["verifier_source_key_sha256s"]
        == utility_catalog["verifier_source_key_sha256s"]
    )


def _receipt(
    *,
    partition: Mapping[str, Any],
    partition_matches: bool,
    parent: Mapping[str, Any],
    verifier_pages: Sequence[Mapping[str, Any]],
    before: int,
    after: int,
    resolutions: Sequence[Mapping[str, Any]],
    proposal_credit: float,
    aligned_credit: float,
) -> dict[str, Any]:
    semantic = parent["semantic_result"]
    core = semantic["core_result"]
    proposal_pages = [
        *semantic["semantic_active_private_state"]["raw_core_pages"],
        *semantic["semantic_active_private_state"]["raw_reserve_pages"],
    ]
    parent_fetches = int(core["cost"]["search"]["fetch_calls"])
    hidden_fetches = int(partition["verifier_source_count"])
    admitted = sum(receipt["admitted"] is True for receipt in resolutions)
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "partition_receipt": copy.deepcopy(dict(partition)),
        "partition_replay_matches_successful_pages": partition_matches,
        "parent_proposal_page_count": len(proposal_pages),
        "hidden_verifier_page_count": len(verifier_pages),
        "parent_fetch_calls": parent_fetches,
        "hidden_verifier_fetch_calls": hidden_fetches,
        "total_fetch_calls": parent_fetches + hidden_fetches,
        "parent_model_requests": int(core["cost"]["model"]["requests"]),
        "candidate_changed_cells_before_hidden_verifier": before,
        "candidate_changed_cells_after_hidden_verifier": after,
        "hidden_verifier_admitted_cells": admitted,
        "hidden_verifier_reverted_cells": before - after,
        "proposal_conditional_entropy_reduction_nats": proposal_credit,
        "utility_aligned_entropy_credit_nats": aligned_credit,
        "hidden_verifier_pages_used_for_candidate_generation_or_model_prompt": False,
        "new_candidate_value_generated_by_hidden_verifier": False,
        "baseline_and_candidate_share_exact_proposal_pages": True,
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_runtime_receipt(value)
    return value


def validate_runtime_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    partition = value.get("partition_receipt")
    integer_names = (
        "parent_proposal_page_count",
        "hidden_verifier_page_count",
        "parent_fetch_calls",
        "hidden_verifier_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "candidate_changed_cells_before_hidden_verifier",
        "candidate_changed_cells_after_hidden_verifier",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
    )
    proposal_credit = value.get("proposal_conditional_entropy_reduction_nats")
    aligned_credit = value.get("utility_aligned_entropy_credit_nats")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(partition, Mapping)
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in integer_names
        )
        or value.get("total_fetch_calls")
        != value.get("parent_fetch_calls") + value.get("hidden_verifier_fetch_calls")
        or value.get("total_fetch_calls", -1) > MAXIMUM_FETCH_SOURCES
        or value.get("candidate_changed_cells_after_hidden_verifier", -1)
        > value.get("candidate_changed_cells_before_hidden_verifier", -1)
        or value.get("hidden_verifier_reverted_cells")
        != value.get("candidate_changed_cells_before_hidden_verifier")
        - value.get("candidate_changed_cells_after_hidden_verifier")
        or value.get("hidden_verifier_admitted_cells")
        != value.get("candidate_changed_cells_after_hidden_verifier")
        or isinstance(proposal_credit, bool)
        or not isinstance(proposal_credit, (int, float))
        or not math.isfinite(float(proposal_credit))
        or float(proposal_credit) < 0
        or isinstance(aligned_credit, bool)
        or not isinstance(aligned_credit, (int, float))
        or not math.isfinite(float(aligned_credit))
        or float(aligned_credit) < 0
        or float(aligned_credit) > float(proposal_credit) + 1e-12
        or (
            value.get("partition_replay_matches_successful_pages") is not True
            and value.get("candidate_changed_cells_after_hidden_verifier") != 0
        )
        or value.get("hidden_verifier_pages_used_for_candidate_generation_or_model_prompt") is not False
        or value.get("new_candidate_value_generated_by_hidden_verifier") is not False
        or value.get("baseline_and_candidate_share_exact_proposal_pages") is not True
        or value.get("question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.51 runtime receipt drifted")
    validate_partition_receipt(partition)
    return dict(value)


def run_v24351_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float] = time.monotonic,
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
    if chosen.fetch_targets != MAXIMUM_FETCH_SOURCES:
        raise ValueError("V2.43.51 fetch budget drifted")
    split = PreproposalPartitionSearchClient(
        search,
        partition_seed_sha256=partition_seed_sha256,
    )
    parent = run_v24349_task(
        visible,
        model=model,
        search=split,
        limits=chosen,
        monotonic=monotonic,
    )
    validate_parent_result(parent)
    if split.partition_receipt is None:
        raise RuntimeError("V2.43.51 source partition is absent")
    verifier_batches = split.fetch_hidden_verifier()
    verifier_pages = base._page_vector(
        verifier_batches,
        prefix="V",
        page_chars=chosen.page_chars,
    )
    semantic = parent["semantic_result"]
    proposal_pages = [
        *semantic["semantic_active_private_state"]["raw_core_pages"],
        *semantic["semantic_active_private_state"]["raw_reserve_pages"],
    ]
    normalization = parent["structural_private_state"]["normalization_result"]
    targets = [
        {
            "row_key": target.row_key,
            "column": target.column,
            "old_value": target.old_value,
        }
        for target in semantic_targets(
            normalization,
            unknown_marker=str(normalization["unknown_marker"]),
        )
    ]
    all_pages = [_plain_page(page) for page in [*proposal_pages, *verifier_pages]]
    utility_catalog = build_independent_utility_catalog(
        targets,
        all_pages,
        partition_seed_sha256=partition_seed_sha256,
    )
    validate_independent_utility_catalog(utility_catalog)
    partition_matches = _partition_matches_pages(
        split.partition_receipt,
        utility_catalog,
    )
    candidate, resolutions, before, after, proposal_credit, aligned_credit = _filter_candidate(
        parent,
        utility_catalog,
        partition_matches=partition_matches,
    )
    baseline = str(semantic["core_result"]["baseline_prediction"])
    receipt = _receipt(
        partition=split.partition_receipt,
        partition_matches=partition_matches,
        parent=parent,
        verifier_pages=verifier_pages,
        before=before,
        after=after,
        resolutions=resolutions,
        proposal_credit=proposal_credit,
        aligned_credit=aligned_credit,
    )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(parent),
        "baseline_prediction": baseline,
        "candidate_prediction": candidate,
        "hidden_verifier_receipt": receipt,
        "private_replay_state": {
            "partition": {
                "proposal_leads": copy.deepcopy(split.proposal_leads),
                "verifier_leads": copy.deepcopy(split.verifier_leads),
            },
            "page_character_cap": chosen.page_chars,
            "verifier_fetch_batches": copy.deepcopy(verifier_batches),
            "verifier_pages": copy.deepcopy(verifier_pages),
            "utility_catalog": copy.deepcopy(utility_catalog),
            "cell_utility_resolutions": copy.deepcopy(resolutions),
        },
    }
    value["result_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    parent = value.get("parent_result")
    receipt = value.get("hidden_verifier_receipt")
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
        raise ValueError("V2.43.51 result identity drifted")
    validate_parent_result(parent)
    validate_runtime_receipt(receipt)
    partition_private = private["partition"]
    if (
        not isinstance(partition_private, Mapping)
        or set(partition_private) != {"proposal_leads", "verifier_leads"}
        or not isinstance(partition_private["proposal_leads"], list)
        or not isinstance(partition_private["verifier_leads"], list)
    ):
        raise ValueError("V2.43.51 private partition drifted")
    proposal, verifier, expected_partition = _partition_leads(
        [*partition_private["proposal_leads"], *partition_private["verifier_leads"]],
        partition_seed_sha256=receipt["partition_receipt"]["partition_seed_sha256"],
    )
    if (
        proposal != partition_private["proposal_leads"]
        or sorted(verifier, key=_lead_binding)
        != sorted(partition_private["verifier_leads"], key=_lead_binding)
        or expected_partition != receipt["partition_receipt"]
    ):
        raise ValueError("V2.43.51 private source partition replay drifted")
    utility_catalog = private["utility_catalog"]
    if not isinstance(utility_catalog, Mapping):
        raise ValueError("V2.43.51 utility catalog is absent")
    validate_independent_utility_catalog(utility_catalog)
    page_character_cap = private["page_character_cap"]
    verifier_fetch_batches = private["verifier_fetch_batches"]
    verifier_pages = private["verifier_pages"]
    if (
        isinstance(page_character_cap, bool)
        or not isinstance(page_character_cap, int)
        or page_character_cap < 1
        or not isinstance(verifier_fetch_batches, list)
        or any(not isinstance(item, Mapping) for item in verifier_fetch_batches)
        or not isinstance(verifier_pages, list)
        or any(not isinstance(item, Mapping) for item in verifier_pages)
    ):
        raise ValueError("V2.43.51 hidden verifier fetch replay state drifted")
    replayed_verifier_pages = base._page_vector(
        verifier_fetch_batches,
        prefix="V",
        page_chars=page_character_cap,
    )
    if verifier_pages != replayed_verifier_pages:
        raise ValueError("V2.43.51 hidden verifier page replay drifted")
    verifier_urls = {
        base.canonicalize_url(str(lead.get("url") or lead.get("fetch_url") or ""))
        for lead in partition_private["verifier_leads"]
    }
    if any(
        base.canonicalize_url(str(page.get("url") or "")) not in verifier_urls
        for page in verifier_pages
    ):
        raise ValueError("V2.43.51 hidden verifier page escaped its lead partition")
    resolutions = private["cell_utility_resolutions"]
    if not isinstance(resolutions, list):
        raise ValueError("V2.43.51 utility resolution vector is absent")
    for item in resolutions:
        validate_independent_utility_receipt(item)
    partition_matches = _partition_matches_pages(
        receipt["partition_receipt"],
        utility_catalog,
    )
    expected = _filter_candidate(
        parent,
        utility_catalog,
        partition_matches=partition_matches,
    )
    candidate, expected_resolutions, before, after, proposal_credit, aligned_credit = expected
    semantic = parent["semantic_result"]
    baseline = str(semantic["core_result"]["baseline_prediction"])
    parent_pages = [
        *semantic["semantic_active_private_state"]["raw_core_pages"],
        *semantic["semantic_active_private_state"]["raw_reserve_pages"],
    ]
    expected_original_pages = [
        _plain_page(page) for page in [*parent_pages, *verifier_pages]
    ]
    if (
        utility_catalog["original_pages"] != expected_original_pages
        or (
            partition_matches
            and (
                utility_catalog["proposal_pages"]
                != [_plain_page(page) for page in parent_pages]
                or utility_catalog["verifier_pages"]
                != [_plain_page(page) for page in verifier_pages]
            )
        )
        or value["baseline_prediction"] != baseline
        or value["candidate_prediction"] != candidate
        or resolutions != expected_resolutions
    ):
        raise ValueError("V2.43.51 deterministic hidden-verifier replay drifted")
    expected_receipt = _receipt(
        partition=receipt["partition_receipt"],
        partition_matches=partition_matches,
        parent=parent,
        verifier_pages=verifier_pages,
        before=before,
        after=after,
        resolutions=expected_resolutions,
        proposal_credit=proposal_credit,
        aligned_credit=aligned_credit,
    )
    if dict(receipt) != expected_receipt:
        raise ValueError("V2.43.51 hidden verifier receipt replay drifted")
    parent_sources = {_sha256_text(_source_key(str(page["host"]))) for page in parent_pages}
    verifier_sources = {_sha256_text(_source_key(str(page["host"]))) for page in verifier_pages}
    if parent_sources & verifier_sources:
        raise ValueError("V2.43.51 hidden verifier leaked into parent pages")
    return dict(value)


__all__ = [
    "MAXIMUM_FETCH_SOURCES",
    "POLICY_ID",
    "PreproposalPartitionSearchClient",
    "ROLE",
    "run_v24351_task",
    "validate_partition_receipt",
    "validate_result",
    "validate_runtime_receipt",
]
