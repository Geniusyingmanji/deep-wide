"""Two-batch 8+2 hidden-verifier runtime under a fixed ten-fetch budget.

V2.43.61 established that two discovery batches solve registrable-host
coverage, but a single hidden verifier host has low power: a missing or
non-mentioning page is indistinguishable from lack of independent support.
This append-only successor keeps four logical queries, two hosted-search
batches, and at most ten fetches while reserving two independent verifier
hosts at full capacity.  Eight proposal hosts alone may enter the parent
search/fetch/model path.  Both hidden pages are revealed only after the parent
candidate and exact semantic support catalog are frozen; they can retain or
revert a change but never generate a new value.

The module has no benchmark selection, evaluator, mapping, label, answer,
score, or launch capability.  Runtime inputs remain ``{opaque_id, question}``.
"""

from __future__ import annotations

import copy
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as base
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24349_structural_semantic_runtime import (
    run_v24349_task,
    validate_result as validate_parent_result,
)
from .v24354_explicit_partition_utility import (
    build_explicit_partition_utility_catalog,
    validate_explicit_partition_utility_catalog,
    validate_explicit_partition_utility_receipt,
)
from .v24355_explicit_partition_runtime import (
    _filter_candidate,
    _lead_binding,
    _plain_page,
    _sha256_text,
    _source_digest_from_lead,
    _source_from_lead,
)
from .v24358_two_batch_discovery import (
    DISCOVERY_BATCH_COUNT,
    LOGICAL_QUERY_COUNT,
    TwoBatchRegistrableHostUnionSearchClient,
    _validate_state as _validate_discovery_state,
)


POLICY_ID = "v24362_two_batch_two_verifier_partition_runtime_v1"
ROLE = "v24362_two_verifier_partition_task_result"
RECEIPT_ROLE = "v24362_two_verifier_runtime_receipt"
PARTITION_ROLE = "v24362_preproposal_two_verifier_partition_receipt"
DISCOVERY_ROLE = "v24362_two_batch_two_verifier_discovery_receipt"
MAXIMUM_FETCH_SOURCES = 10
VERIFIER_SOURCE_CAP = 2
MINIMUM_PROPOSAL_SOURCES = 2
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "baseline_prediction",
        "candidate_prediction",
        "two_batch_discovery_receipt",
        "hidden_verifier_receipt",
        "private_replay_state",
        "result_sha256",
    }
)
PRIVATE_KEYS = frozenset(
    {
        "two_batch_discovery_state",
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
        "verifier_source_cap",
        "minimum_proposal_sources",
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
DISCOVERY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "logical_query_count",
        "discovery_batch_count",
        "batch_logical_query_counts",
        "query_batch_sha256s",
        "batch_provider_search_call_counts",
        "provider_search_call_count",
        "pre_host_dedup_url_lead_count",
        "registrable_host_union_count",
        "registrable_host_duplicate_url_count",
        "selected_host_count",
        "proposal_host_count",
        "verifier_host_count",
        "partition_receipt_sha256",
        "query_split_precedes_search",
        "registrable_host_union_precedes_partition_fetch_and_candidate",
        "first_seen_host_deduplication",
        "fetch_effects_before_partition",
        "provider_narrative_snippet_or_page_content_forwarded",
        "candidate_value_entropy_page_content_or_evaluator_used_for_union",
        "question_query_url_host_page_candidate_value_or_credential_emitted",
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
        "observed_pages_respect_frozen_partition",
        "parent_semantic_catalog_present",
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
        "parent_support_set_ids_reused_without_rebuild",
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _partition_leads(
    leads: Sequence[Mapping[str, Any]],
    *,
    partition_seed_sha256: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    if re.fullmatch(r"[0-9a-f]{64}", partition_seed_sha256) is None:
        raise ValueError("V2.43.62 partition seed drifted")
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
    verifier_count = min(
        VERIFIER_SOURCE_CAP,
        max(0, len(selected_sources) - MINIMUM_PROPOSAL_SOURCES),
    )
    ranked = sorted(
        selected_sources,
        key=lambda source: (
            _sha256_text(partition_seed_sha256 + "|" + source),
            source,
        ),
    )
    verifier_sources = set(ranked[:verifier_count])
    proposal = [
        by_source[source]
        for source in selected_sources
        if source not in verifier_sources
    ]
    verifier = [
        by_source[source]
        for source in selected_sources
        if source in verifier_sources
    ]
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
        "verifier_source_cap": VERIFIER_SOURCE_CAP,
        "minimum_proposal_sources": MINIMUM_PROPOSAL_SOURCES,
        "proposal_source_key_sha256s": proposal_hashes,
        "verifier_source_key_sha256s": verifier_hashes,
        "proposal_lead_binding_sha256s": sorted(
            _lead_binding(lead) for lead in proposal
        ),
        "verifier_lead_binding_sha256s": sorted(
            _lead_binding(lead) for lead in verifier
        ),
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
    counts = (
        "discovered_unique_source_count",
        "selected_source_count",
        "proposal_source_count",
        "verifier_source_count",
        "verifier_source_cap",
        "minimum_proposal_sources",
    )
    vectors = (
        "proposal_source_key_sha256s",
        "verifier_source_key_sha256s",
        "proposal_lead_binding_sha256s",
        "verifier_lead_binding_sha256s",
    )
    selected = value.get("selected_source_count", -1)
    expected_verifier = min(
        VERIFIER_SOURCE_CAP,
        max(0, int(selected) - MINIMUM_PROPOSAL_SOURCES),
    ) if isinstance(selected, int) and not isinstance(selected, bool) else -1
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
            for name in counts
        )
        or value.get("verifier_source_cap") != VERIFIER_SOURCE_CAP
        or value.get("minimum_proposal_sources") != MINIMUM_PROPOSAL_SOURCES
        or selected > MAXIMUM_FETCH_SOURCES
        or selected
        != value.get("proposal_source_count") + value.get("verifier_source_count")
        or value.get("verifier_source_count") != expected_verifier
        or value.get("proposal_source_count", 0)
        < min(selected, MINIMUM_PROPOSAL_SOURCES)
        or selected > value.get("discovered_unique_source_count", -1)
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
        raise ValueError("V2.43.62 partition receipt drifted")
    return copy.deepcopy(dict(value))


class TwoVerifierPartitionSearchClient:
    """Expose proposal hosts to the parent and retain two verifier hosts."""

    def __init__(self, inner: Any, *, partition_seed_sha256: str) -> None:
        self._union = TaskUnionDiscoverySearchClient(inner)
        self.partition_seed_sha256 = partition_seed_sha256
        self.proposal_leads: list[dict[str, str]] = []
        self.verifier_leads: list[dict[str, str]] = []
        self.partition_receipt: dict[str, Any] | None = None
        self.search_completed = False
        self.verifier_fetch_completed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._union, name)

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        if self.search_completed:
            raise RuntimeError("V2.43.62 hosted search repeated")
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
                "query": "two-verifier preproposal source partition",
                "answer": "",
                "results": copy.deepcopy(proposal),
                "error": None,
                "provider": "v24362-proposal-only-source-partition",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        allowed = {
            base.canonicalize_url(str(lead["url"])) for lead in self.proposal_leads
        }
        requested = list(requests_)
        if any(
            base.canonicalize_url(
                str(item.get("url") or item.get("fetch_url") or "")
            )
            not in allowed
            for item in requested
        ):
            raise RuntimeError("V2.43.62 parent attempted hidden-verifier fetch")
        return self._union.fetch_urls(requested)

    def fetch_hidden_verifier(self) -> list[dict[str, Any]]:
        if not self.search_completed or self.partition_receipt is None:
            raise RuntimeError("V2.43.62 verifier fetch preceded source partition")
        if self.verifier_fetch_completed:
            raise RuntimeError("V2.43.62 verifier fetch repeated")
        raw = (
            self._union.fetch_urls(self.verifier_leads)
            if self.verifier_leads
            else []
        )
        self.verifier_fetch_completed = True
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            return []
        return [dict(item) for item in raw if isinstance(item, Mapping)]


def _build_discovery_receipt(
    state: Mapping[str, Any], partition: Mapping[str, Any]
) -> dict[str, Any]:
    replay = _validate_discovery_state(state)
    frozen = validate_partition_receipt(partition)
    host_union = replay["registrable_host_union_leads"]
    _, _, expected_partition = _partition_leads(
        host_union[:MAXIMUM_FETCH_SOURCES],
        partition_seed_sha256=frozen["partition_seed_sha256"],
    )
    if expected_partition != frozen:
        raise ValueError("V2.43.62 host union does not replay frozen partition")
    batch_leads = replay["batch_leads"]
    lead_count = sum(len(batch) for batch in batch_leads)
    value = {
        "artifact_version": 1,
        "role": DISCOVERY_ROLE,
        "policy_id": POLICY_ID,
        "logical_query_count": sum(
            len(batch) for batch in replay["query_batches"]
        ),
        "discovery_batch_count": len(replay["query_batches"]),
        "batch_logical_query_counts": [
            len(batch) for batch in replay["query_batches"]
        ],
        "query_batch_sha256s": [
            payload_sha256(batch) for batch in replay["query_batches"]
        ],
        "batch_provider_search_call_counts": list(
            replay["batch_provider_search_call_counts"]
        ),
        "provider_search_call_count": sum(
            replay["batch_provider_search_call_counts"]
        ),
        "pre_host_dedup_url_lead_count": lead_count,
        "registrable_host_union_count": len(host_union),
        "registrable_host_duplicate_url_count": max(0, lead_count - len(host_union)),
        "selected_host_count": frozen["selected_source_count"],
        "proposal_host_count": frozen["proposal_source_count"],
        "verifier_host_count": frozen["verifier_source_count"],
        "partition_receipt_sha256": frozen["receipt_sha256"],
        "query_split_precedes_search": True,
        "registrable_host_union_precedes_partition_fetch_and_candidate": True,
        "first_seen_host_deduplication": True,
        "fetch_effects_before_partition": 0,
        "provider_narrative_snippet_or_page_content_forwarded": False,
        "candidate_value_entropy_page_content_or_evaluator_used_for_union": False,
        "question_query_url_host_page_candidate_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_discovery_receipt(value)
    return value


def validate_discovery_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    integer_names = (
        "logical_query_count",
        "discovery_batch_count",
        "provider_search_call_count",
        "pre_host_dedup_url_lead_count",
        "registrable_host_union_count",
        "registrable_host_duplicate_url_count",
        "selected_host_count",
        "proposal_host_count",
        "verifier_host_count",
        "fetch_effects_before_partition",
    )
    batch_counts = value.get("batch_logical_query_counts")
    query_hashes = value.get("query_batch_sha256s")
    call_counts = value.get("batch_provider_search_call_counts")
    if (
        set(value) != DISCOVERY_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != DISCOVERY_ROLE
        or value.get("policy_id") != POLICY_ID
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in integer_names
        )
        or value.get("logical_query_count") != LOGICAL_QUERY_COUNT
        or value.get("discovery_batch_count") != DISCOVERY_BATCH_COUNT
        or batch_counts != [2, 2]
        or not isinstance(query_hashes, list)
        or len(query_hashes) != DISCOVERY_BATCH_COUNT
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(item)) is None
            for item in query_hashes
        )
        or not isinstance(call_counts, list)
        or len(call_counts) != DISCOVERY_BATCH_COUNT
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in call_counts
        )
        or value.get("provider_search_call_count") != sum(call_counts)
        or value.get("registrable_host_duplicate_url_count")
        != value.get("pre_host_dedup_url_lead_count")
        - value.get("registrable_host_union_count")
        or value.get("selected_host_count")
        != min(value.get("registrable_host_union_count", -1), MAXIMUM_FETCH_SOURCES)
        or value.get("selected_host_count")
        != value.get("proposal_host_count") + value.get("verifier_host_count")
        or value.get("verifier_host_count", -1) > VERIFIER_SOURCE_CAP
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("partition_receipt_sha256")))
        is None
        or value.get("query_split_precedes_search") is not True
        or value.get("registrable_host_union_precedes_partition_fetch_and_candidate")
        is not True
        or value.get("first_seen_host_deduplication") is not True
        or value.get("fetch_effects_before_partition") != 0
        or value.get("provider_narrative_snippet_or_page_content_forwarded") is not False
        or value.get("candidate_value_entropy_page_content_or_evaluator_used_for_union")
        is not False
        or value.get("question_query_url_host_page_candidate_value_or_credential_emitted")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.62 discovery receipt drifted")
    return copy.deepcopy(dict(value))


def _runtime_receipt(
    *,
    partition: Mapping[str, Any],
    observed_pages_respect_partition: bool,
    parent_semantic_catalog_present: bool,
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
    admitted = sum(item["admitted"] is True for item in resolutions)
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "partition_receipt": copy.deepcopy(dict(partition)),
        "observed_pages_respect_frozen_partition": observed_pages_respect_partition,
        "parent_semantic_catalog_present": parent_semantic_catalog_present,
        "parent_proposal_page_count": len(proposal_pages),
        "hidden_verifier_page_count": len(verifier_pages),
        "parent_fetch_calls": int(core["cost"]["search"]["fetch_calls"]),
        "hidden_verifier_fetch_calls": int(partition["verifier_source_count"]),
        "total_fetch_calls": int(core["cost"]["search"]["fetch_calls"])
        + int(partition["verifier_source_count"]),
        "parent_model_requests": int(core["cost"]["model"]["requests"]),
        "candidate_changed_cells_before_hidden_verifier": before,
        "candidate_changed_cells_after_hidden_verifier": after,
        "hidden_verifier_admitted_cells": admitted,
        "hidden_verifier_reverted_cells": before - after,
        "proposal_conditional_entropy_reduction_nats": proposal_credit,
        "utility_aligned_entropy_credit_nats": aligned_credit,
        "hidden_verifier_pages_used_for_candidate_generation_or_model_prompt": False,
        "new_candidate_value_generated_by_hidden_verifier": False,
        "parent_support_set_ids_reused_without_rebuild": True,
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
    counts = (
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
        or not isinstance(value.get("observed_pages_respect_frozen_partition"), bool)
        or not isinstance(value.get("parent_semantic_catalog_present"), bool)
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in counts
        )
        or value.get("hidden_verifier_fetch_calls")
        != partition.get("verifier_source_count")
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
            (
                value.get("observed_pages_respect_frozen_partition") is not True
                or value.get("parent_semantic_catalog_present") is not True
            )
            and value.get("candidate_changed_cells_after_hidden_verifier") != 0
        )
        or value.get("hidden_verifier_pages_used_for_candidate_generation_or_model_prompt") is not False
        or value.get("new_candidate_value_generated_by_hidden_verifier") is not False
        or value.get("parent_support_set_ids_reused_without_rebuild") is not True
        or value.get("question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.62 runtime receipt drifted")
    validate_partition_receipt(partition)
    return copy.deepcopy(dict(value))


def run_v24362_task(
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
        search_queries=LOGICAL_QUERY_COUNT,
        fetch_targets=MAXIMUM_FETCH_SOURCES,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )
    chosen.validate()
    if (
        chosen.search_queries != LOGICAL_QUERY_COUNT
        or chosen.fetch_targets != MAXIMUM_FETCH_SOURCES
    ):
        raise ValueError("V2.43.62 discovery/fetch budget drifted")
    discovery = TwoBatchRegistrableHostUnionSearchClient(search)
    split = TwoVerifierPartitionSearchClient(
        discovery,
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
        raise RuntimeError("V2.43.62 source partition is absent")
    verifier_batches = split.fetch_hidden_verifier()
    verifier_pages = base._page_vector(
        verifier_batches,
        prefix="V",
        page_chars=chosen.page_chars,
    )
    semantic = parent["semantic_result"]
    parent_private = semantic["semantic_active_private_state"]
    proposal_catalog = parent_private["semantic_active_catalog"]
    utility_catalog: dict[str, Any] | None = None
    observed_respected = False
    if isinstance(proposal_catalog, Mapping):
        utility_catalog = build_explicit_partition_utility_catalog(
            proposal_catalog,
            [_plain_page(page) for page in verifier_pages],
            partition_seed_sha256=partition_seed_sha256,
            expected_proposal_source_key_sha256s=split.partition_receipt[
                "proposal_source_key_sha256s"
            ],
            expected_verifier_source_key_sha256s=split.partition_receipt[
                "verifier_source_key_sha256s"
            ],
        )
        validate_explicit_partition_utility_catalog(utility_catalog)
        observed_respected = bool(
            utility_catalog["observed_pages_respect_frozen_partition"]
        )
    candidate, resolutions, before, after, proposal_credit, aligned_credit = (
        _filter_candidate(parent, utility_catalog)
    )
    baseline = str(semantic["core_result"]["baseline_prediction"])
    discovery_state = discovery.private_replay_state()
    discovery_receipt = _build_discovery_receipt(
        discovery_state,
        split.partition_receipt,
    )
    runtime_receipt = _runtime_receipt(
        partition=split.partition_receipt,
        observed_pages_respect_partition=observed_respected,
        parent_semantic_catalog_present=isinstance(proposal_catalog, Mapping),
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
        "two_batch_discovery_receipt": copy.deepcopy(discovery_receipt),
        "hidden_verifier_receipt": copy.deepcopy(runtime_receipt),
        "private_replay_state": {
            "two_batch_discovery_state": copy.deepcopy(discovery_state),
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


def _lead_projection(value: Mapping[str, Any]) -> dict[str, str]:
    url = base.canonicalize_url(
        str(value.get("url") or value.get("fetch_url") or "")
    )
    return {
        "url": url,
        "title": str(value.get("title") or "")[:500],
        "source_sha256": _source_digest_from_lead(value),
    }


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    parent = value.get("parent_result")
    discovery_receipt = value.get("two_batch_discovery_receipt")
    runtime_receipt = value.get("hidden_verifier_receipt")
    private = value.get("private_replay_state")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(parent, Mapping)
        or not isinstance(discovery_receipt, Mapping)
        or not isinstance(runtime_receipt, Mapping)
        or not isinstance(private, Mapping)
        or set(private) != PRIVATE_KEYS
        or not isinstance(value.get("baseline_prediction"), str)
        or not isinstance(value.get("candidate_prediction"), str)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.62 result identity drifted")
    validate_parent_result(parent)
    validate_discovery_receipt(discovery_receipt)
    validate_runtime_receipt(runtime_receipt)
    discovery_state = _validate_discovery_state(
        private["two_batch_discovery_state"]
    )
    partition_private = private["partition"]
    if (
        not isinstance(partition_private, Mapping)
        or set(partition_private) != {"proposal_leads", "verifier_leads"}
        or not isinstance(partition_private["proposal_leads"], list)
        or not isinstance(partition_private["verifier_leads"], list)
        or any(
            not isinstance(item, Mapping)
            for name in ("proposal_leads", "verifier_leads")
            for item in partition_private[name]
        )
    ):
        raise ValueError("V2.43.62 private partition drifted")
    proposal, verifier, expected_partition = _partition_leads(
        [
            *partition_private["proposal_leads"],
            *partition_private["verifier_leads"],
        ],
        partition_seed_sha256=runtime_receipt["partition_receipt"][
            "partition_seed_sha256"
        ],
    )
    if (
        proposal != partition_private["proposal_leads"]
        or sorted(verifier, key=_lead_binding)
        != sorted(partition_private["verifier_leads"], key=_lead_binding)
        or expected_partition != runtime_receipt["partition_receipt"]
    ):
        raise ValueError("V2.43.62 private source partition replay drifted")
    expected_discovery = _build_discovery_receipt(
        discovery_state,
        runtime_receipt["partition_receipt"],
    )
    if dict(discovery_receipt) != expected_discovery:
        raise ValueError("V2.43.62 two-batch discovery replay drifted")
    selected_union = discovery_state["registrable_host_union_leads"][
        :MAXIMUM_FETCH_SOURCES
    ]
    actual_projected = sorted(
        (_lead_projection(item)
        for item in [
            *partition_private["proposal_leads"],
            *partition_private["verifier_leads"],
        ]),
        key=lambda item: (item["source_sha256"], item["url"], item["title"]),
    )
    expected_projected = sorted(
        (_lead_projection(item) for item in selected_union),
        key=lambda item: (item["source_sha256"], item["url"], item["title"]),
    )
    if actual_projected != expected_projected:
        raise ValueError("V2.43.62 partition leads drifted from host union")
    page_cap = private["page_character_cap"]
    batches = private["verifier_fetch_batches"]
    pages = private["verifier_pages"]
    if (
        isinstance(page_cap, bool)
        or not isinstance(page_cap, int)
        or page_cap < 1
        or not isinstance(batches, list)
        or any(not isinstance(item, Mapping) for item in batches)
        or not isinstance(pages, list)
        or any(not isinstance(item, Mapping) for item in pages)
    ):
        raise ValueError("V2.43.62 hidden verifier replay state drifted")
    replayed_pages = base._page_vector(batches, prefix="V", page_chars=page_cap)
    if pages != replayed_pages:
        raise ValueError("V2.43.62 hidden verifier page replay drifted")
    verifier_urls = {
        base.canonicalize_url(
            str(lead.get("url") or lead.get("fetch_url") or "")
        )
        for lead in partition_private["verifier_leads"]
    }
    if any(
        base.canonicalize_url(str(page.get("url") or "")) not in verifier_urls
        for page in pages
    ):
        raise ValueError("V2.43.62 hidden verifier page escaped lead partition")
    semantic = parent["semantic_result"]
    proposal_catalog = semantic["semantic_active_private_state"][
        "semantic_active_catalog"
    ]
    utility_catalog = private["utility_catalog"]
    if isinstance(proposal_catalog, Mapping):
        if not isinstance(utility_catalog, Mapping):
            raise ValueError("V2.43.62 utility catalog is absent")
        validate_explicit_partition_utility_catalog(utility_catalog)
        expected_catalog = build_explicit_partition_utility_catalog(
            proposal_catalog,
            [_plain_page(page) for page in pages],
            partition_seed_sha256=runtime_receipt["partition_receipt"][
                "partition_seed_sha256"
            ],
            expected_proposal_source_key_sha256s=runtime_receipt[
                "partition_receipt"
            ]["proposal_source_key_sha256s"],
            expected_verifier_source_key_sha256s=runtime_receipt[
                "partition_receipt"
            ]["verifier_source_key_sha256s"],
        )
        if dict(utility_catalog) != expected_catalog:
            raise ValueError("V2.43.62 explicit utility replay drifted")
        observed_respected = bool(
            utility_catalog["observed_pages_respect_frozen_partition"]
        )
    else:
        if utility_catalog is not None:
            raise ValueError("V2.43.62 unexpected utility catalog")
        observed_respected = False
    resolutions = private["cell_utility_resolutions"]
    if not isinstance(resolutions, list):
        raise ValueError("V2.43.62 utility resolution vector is absent")
    for item in resolutions:
        validate_explicit_partition_utility_receipt(item)
    candidate, expected_resolutions, before, after, proposal_credit, aligned_credit = (
        _filter_candidate(parent, utility_catalog)
    )
    baseline = str(semantic["core_result"]["baseline_prediction"])
    if (
        value["baseline_prediction"] != baseline
        or value["candidate_prediction"] != candidate
        or resolutions != expected_resolutions
    ):
        raise ValueError("V2.43.62 deterministic candidate replay drifted")
    expected_runtime = _runtime_receipt(
        partition=runtime_receipt["partition_receipt"],
        observed_pages_respect_partition=observed_respected,
        parent_semantic_catalog_present=isinstance(proposal_catalog, Mapping),
        parent=parent,
        verifier_pages=pages,
        before=before,
        after=after,
        resolutions=expected_resolutions,
        proposal_credit=proposal_credit,
        aligned_credit=aligned_credit,
    )
    if dict(runtime_receipt) != expected_runtime:
        raise ValueError("V2.43.62 runtime receipt replay drifted")
    parent_pages = [
        *semantic["semantic_active_private_state"]["raw_core_pages"],
        *semantic["semantic_active_private_state"]["raw_reserve_pages"],
    ]
    parent_sources = {
        _sha256_text(_source_from_lead({"url": page["url"]}))
        for page in parent_pages
    }
    verifier_sources = {
        _sha256_text(_source_from_lead({"url": page["url"]})) for page in pages
    }
    if parent_sources & verifier_sources:
        raise ValueError("V2.43.62 hidden verifier leaked into parent pages")
    core = semantic["core_result"]
    if (
        discovery_receipt["provider_search_call_count"]
        != int(core["cost"]["search"]["calls"])
        or runtime_receipt["parent_fetch_calls"]
        != int(core["cost"]["search"]["fetch_calls"])
        or runtime_receipt["total_fetch_calls"] > MAXIMUM_FETCH_SOURCES
    ):
        raise ValueError("V2.43.62 cross-layer effect accounting drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "MAXIMUM_FETCH_SOURCES",
    "MINIMUM_PROPOSAL_SOURCES",
    "POLICY_ID",
    "ROLE",
    "TwoVerifierPartitionSearchClient",
    "VERIFIER_SOURCE_CAP",
    "run_v24362_task",
    "validate_discovery_receipt",
    "validate_partition_receipt",
    "validate_result",
    "validate_runtime_receipt",
]
