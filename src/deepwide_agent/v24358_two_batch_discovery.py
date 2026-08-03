"""Two-batch registrable-host discovery union.

V2.43.57 was transport-healthy but exposed too few independent proposal
sources to the semantic support catalog.  This append-only adapter spends the
same four logical queries in two deterministic batches, discards provider
narrative/snippets, and performs a stable first-seen deduplication by
registrable host *before* the frozen 9+1 source partition.  It does not fetch
pages or inspect candidate values while constructing the union.

The adapter is intended to sit below V2.43.55's existing task-union and source
partition.  Its private replay state may contain visible queries and source
URLs; only the sealed, content-free receipt may be projected publicly.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from . import v24325_shared_prefix_revision_runtime as base
from .v24269_task_union_discovery import (
    TaskUnionDiscoverySearchClient,
    validate_receipt as validate_union_receipt,
)
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import _source_key
from .v24355_explicit_partition_runtime import (
    MAXIMUM_FETCH_SOURCES,
    _partition_leads,
    validate_partition_receipt,
)


POLICY_ID = "v24358_two_batch_registrable_host_union_v1"
RECEIPT_ROLE = "v24358_two_batch_discovery_receipt"
DISCOVERY_BATCH_COUNT = 2
LOGICAL_QUERY_COUNT = 4
STATE_KEYS = frozenset(
    {
        "query_batches",
        "batch_leads",
        "registrable_host_union_leads",
        "underlying_union_receipt_before_fetch",
        "batch_provider_search_call_counts",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "logical_query_count",
        "discovery_batch_count",
        "batch_logical_query_counts",
        "query_batch_sha256s",
        "batch_url_lead_counts",
        "batch_provider_search_call_counts",
        "provider_search_call_count",
        "pre_host_dedup_url_lead_count",
        "registrable_host_union_count",
        "registrable_host_duplicate_url_count",
        "selected_host_count",
        "proposal_host_count",
        "verifier_host_count",
        "batch_source_key_sha256_vectors",
        "registrable_host_union_source_key_sha256s",
        "selected_source_key_sha256s",
        "partition_receipt_sha256",
        "underlying_union_receipt_before_fetch",
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


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _query_batches(queries: Sequence[str]) -> list[list[str]]:
    if isinstance(queries, (str, bytes)):
        raise ValueError("V2.43.58 logical query vector is not a sequence")
    values = [str(value).strip() for value in queries]
    if (
        len(values) != LOGICAL_QUERY_COUNT
        or any(not value for value in values)
        or len({value.casefold() for value in values}) != LOGICAL_QUERY_COUNT
    ):
        raise ValueError("V2.43.58 requires four unique visible queries")
    midpoint = LOGICAL_QUERY_COUNT // DISCOVERY_BATCH_COUNT
    return [values[:midpoint], values[midpoint:]]


def _lead(raw: Mapping[str, Any]) -> dict[str, str] | None:
    fetch_url = str(raw.get("fetch_url") or raw.get("url") or "").strip()
    canonical = base.canonicalize_url(fetch_url)
    host = (urlsplit(canonical).hostname or "").casefold()
    if not canonical or not host:
        return None
    try:
        _source_key(host)
    except ValueError:
        return None
    return {
        "url": canonical,
        "query": "two-batch registrable-host discovery union",
        "title": str(raw.get("title") or "")[:500],
        "member_label": "",
    }


def _source_digest(lead: Mapping[str, Any]) -> str:
    canonical = base.canonicalize_url(str(lead.get("url") or ""))
    host = (urlsplit(canonical).hostname or "").casefold()
    return _sha256_text(_source_key(host))


def _host_union(batch_leads: Sequence[Sequence[Mapping[str, Any]]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for batch in batch_leads:
        for raw in batch:
            lead = _lead(raw)
            if lead is None:
                continue
            source = _source_digest(lead)
            if source in seen:
                continue
            seen.add(source)
            output.append(lead)
    return output


def _validate_state(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != STATE_KEYS:
        raise ValueError("V2.43.58 replay state schema drifted")
    query_batches = value.get("query_batches")
    batch_leads = value.get("batch_leads")
    host_union = value.get("registrable_host_union_leads")
    union_receipt = value.get("underlying_union_receipt_before_fetch")
    call_counts = value.get("batch_provider_search_call_counts")
    if (
        not isinstance(query_batches, list)
        or len(query_batches) != DISCOVERY_BATCH_COUNT
        or any(not isinstance(batch, list) for batch in query_batches)
        or _query_batches([item for batch in query_batches for item in batch])
        != query_batches
        or not isinstance(batch_leads, list)
        or len(batch_leads) != DISCOVERY_BATCH_COUNT
        or any(not isinstance(batch, list) for batch in batch_leads)
        or any(not isinstance(item, Mapping) for batch in batch_leads for item in batch)
        or not isinstance(host_union, list)
        or any(not isinstance(item, Mapping) for item in host_union)
        or not isinstance(union_receipt, Mapping)
        or not isinstance(call_counts, list)
        or len(call_counts) != DISCOVERY_BATCH_COUNT
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in call_counts
        )
    ):
        raise ValueError("V2.43.58 replay state drifted")
    validate_union_receipt(union_receipt)
    if (
        union_receipt.get("search_invocations") != DISCOVERY_BATCH_COUNT
        or union_receipt.get("logical_query_count") != LOGICAL_QUERY_COUNT
        or union_receipt.get("fetch_invocations") != 0
        or union_receipt.get("fetch_requested_source_count") != 0
        or union_receipt.get("fetch_returned_batch_count") != 0
        or union_receipt.get("fetch_usable_page_count") != 0
        or _host_union(batch_leads) != host_union
    ):
        raise ValueError("V2.43.58 prefetch discovery replay drifted")
    return copy.deepcopy(dict(value))


def build_discovery_receipt(
    private_state: Mapping[str, Any],
    partition_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    state = _validate_state(private_state)
    partition = validate_partition_receipt(partition_receipt)
    query_batches = state["query_batches"]
    batch_leads = state["batch_leads"]
    host_union = state["registrable_host_union_leads"]
    expected_proposal, expected_verifier, expected_partition = _partition_leads(
        host_union[:MAXIMUM_FETCH_SOURCES],
        partition_seed_sha256=partition["partition_seed_sha256"],
    )
    del expected_proposal, expected_verifier
    if expected_partition != partition:
        raise ValueError("V2.43.58 host union does not replay the frozen partition")
    batch_vectors = [[_source_digest(item) for item in batch] for batch in batch_leads]
    union_vector = [_source_digest(item) for item in host_union]
    selected_vector = union_vector[:MAXIMUM_FETCH_SOURCES]
    partition_selected = sorted(
        [
            *partition["proposal_source_key_sha256s"],
            *partition["verifier_source_key_sha256s"],
        ]
    )
    if sorted(selected_vector) != partition_selected:
        raise ValueError("V2.43.58 selected host vector drifted from partition")
    lead_count = sum(len(batch) for batch in batch_leads)
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "logical_query_count": sum(len(batch) for batch in query_batches),
        "discovery_batch_count": len(query_batches),
        "batch_logical_query_counts": [len(batch) for batch in query_batches],
        "query_batch_sha256s": [payload_sha256(batch) for batch in query_batches],
        "batch_url_lead_counts": [len(batch) for batch in batch_leads],
        "batch_provider_search_call_counts": list(
            state["batch_provider_search_call_counts"]
        ),
        "provider_search_call_count": sum(
            state["batch_provider_search_call_counts"]
        ),
        "pre_host_dedup_url_lead_count": lead_count,
        "registrable_host_union_count": len(host_union),
        "registrable_host_duplicate_url_count": max(0, lead_count - len(host_union)),
        "selected_host_count": partition["selected_source_count"],
        "proposal_host_count": partition["proposal_source_count"],
        "verifier_host_count": partition["verifier_source_count"],
        "batch_source_key_sha256_vectors": batch_vectors,
        "registrable_host_union_source_key_sha256s": union_vector,
        "selected_source_key_sha256s": selected_vector,
        "partition_receipt_sha256": partition["receipt_sha256"],
        "underlying_union_receipt_before_fetch": copy.deepcopy(
            state["underlying_union_receipt_before_fetch"]
        ),
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


def validate_discovery_receipt(
    value: Mapping[str, Any],
    *,
    private_state: Mapping[str, Any] | None = None,
    partition_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
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
    vector_names = (
        "batch_logical_query_counts",
        "query_batch_sha256s",
        "batch_url_lead_counts",
        "batch_provider_search_call_counts",
        "batch_source_key_sha256_vectors",
        "registrable_host_union_source_key_sha256s",
        "selected_source_key_sha256s",
    )
    union_receipt = value.get("underlying_union_receipt_before_fetch")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in integer_names
        )
        or any(not isinstance(value.get(name), list) for name in vector_names)
        or value.get("logical_query_count") != LOGICAL_QUERY_COUNT
        or value.get("discovery_batch_count") != DISCOVERY_BATCH_COUNT
        or value.get("batch_logical_query_counts") != [2, 2]
        or len(value.get("query_batch_sha256s", [])) != DISCOVERY_BATCH_COUNT
        or len(value.get("batch_url_lead_counts", [])) != DISCOVERY_BATCH_COUNT
        or len(value.get("batch_provider_search_call_counts", []))
        != DISCOVERY_BATCH_COUNT
        or len(value.get("batch_source_key_sha256_vectors", []))
        != DISCOVERY_BATCH_COUNT
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for name in ("batch_url_lead_counts", "batch_provider_search_call_counts")
            for item in value[name]
        )
        or value.get("provider_search_call_count")
        != sum(value.get("batch_provider_search_call_counts", []))
        or value.get("pre_host_dedup_url_lead_count")
        != sum(value.get("batch_url_lead_counts", []))
        or any(
            len(vector) != count
            for vector, count in zip(
                value.get("batch_source_key_sha256_vectors", []),
                value.get("batch_url_lead_counts", []),
                strict=True,
            )
        )
        or value.get("registrable_host_duplicate_url_count")
        != value.get("pre_host_dedup_url_lead_count")
        - value.get("registrable_host_union_count")
        or value.get("selected_host_count")
        != value.get("proposal_host_count") + value.get("verifier_host_count")
        or value.get("selected_host_count", -1) > MAXIMUM_FETCH_SOURCES
        or value.get("selected_host_count")
        != min(value.get("registrable_host_union_count", -1), MAXIMUM_FETCH_SOURCES)
        or len(value.get("registrable_host_union_source_key_sha256s", []))
        != value.get("registrable_host_union_count")
        or len(set(value.get("registrable_host_union_source_key_sha256s", [])))
        != value.get("registrable_host_union_count")
        or value.get("selected_source_key_sha256s")
        != value.get("registrable_host_union_source_key_sha256s", [])[
            :MAXIMUM_FETCH_SOURCES
        ]
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(item)) is None
            for name in (
                "query_batch_sha256s",
                "registrable_host_union_source_key_sha256s",
                "selected_source_key_sha256s",
            )
            for item in value[name]
        )
        or any(
            not isinstance(batch, list)
            or any(re.fullmatch(r"[0-9a-f]{64}", str(item)) is None for item in batch)
            for batch in value.get("batch_source_key_sha256_vectors", [])
        )
        or not isinstance(union_receipt, Mapping)
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
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("partition_receipt_sha256")))
        is None
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.58 discovery receipt drifted")
    validate_union_receipt(union_receipt)
    if (
        union_receipt.get("search_invocations") != DISCOVERY_BATCH_COUNT
        or union_receipt.get("logical_query_count") != LOGICAL_QUERY_COUNT
        or union_receipt.get("fetch_invocations") != 0
    ):
        raise ValueError("V2.43.58 underlying union receipt drifted")
    if private_state is not None or partition_receipt is not None:
        if private_state is None or partition_receipt is None:
            raise ValueError("V2.43.58 replay inputs are incomplete")
        expected = build_discovery_receipt(private_state, partition_receipt)
        if dict(value) != expected:
            raise ValueError("V2.43.58 discovery receipt replay drifted")
    return copy.deepcopy(dict(value))


class TwoBatchRegistrableHostUnionSearchClient:
    """Spend four visible queries in two batches, then expose one host union."""

    def __init__(self, inner: Any) -> None:
        self._union = TaskUnionDiscoverySearchClient(inner)
        self._state: dict[str, Any] | None = None
        self.search_completed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._union, name)

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        if self.search_completed:
            raise RuntimeError("V2.43.58 two-batch discovery repeated")
        query_batches = _query_batches(queries)
        batch_leads: list[list[dict[str, str]]] = []
        call_counts: list[int] = []
        for query_batch in query_batches:
            before = int(self._union.calls)
            batches = self._union.search_many(query_batch, **kwargs)
            call_counts.append(max(0, int(self._union.calls) - before))
            leads: list[dict[str, str]] = []
            for batch in batches:
                if not isinstance(batch, Mapping):
                    continue
                for raw in batch.get("results") or []:
                    if not isinstance(raw, Mapping):
                        continue
                    lead = _lead(raw)
                    if lead is not None:
                        leads.append(lead)
            batch_leads.append(leads)
        union_leads = _host_union(batch_leads)
        frozen_union_receipt = self._union.receipt()
        self._state = {
            "query_batches": copy.deepcopy(query_batches),
            "batch_leads": copy.deepcopy(batch_leads),
            "registrable_host_union_leads": copy.deepcopy(union_leads),
            "underlying_union_receipt_before_fetch": copy.deepcopy(
                frozen_union_receipt
            ),
            "batch_provider_search_call_counts": call_counts,
        }
        _validate_state(self._state)
        self.search_completed = True
        if not union_leads:
            return []
        return [
            {
                "query": "two-batch registrable-host discovery union",
                "answer": "",
                "results": copy.deepcopy(union_leads),
                "error": None,
                "provider": "v24358-two-batch-registrable-host-union",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        if not self.search_completed or self._state is None:
            raise RuntimeError("V2.43.58 fetch preceded discovery union")
        return self._union.fetch_urls(requests_)

    def private_replay_state(self) -> dict[str, Any]:
        if not self.search_completed or self._state is None:
            raise RuntimeError("V2.43.58 discovery state is absent")
        return _validate_state(self._state)


__all__ = [
    "DISCOVERY_BATCH_COUNT",
    "LOGICAL_QUERY_COUNT",
    "POLICY_ID",
    "TwoBatchRegistrableHostUnionSearchClient",
    "build_discovery_receipt",
    "validate_discovery_receipt",
]
