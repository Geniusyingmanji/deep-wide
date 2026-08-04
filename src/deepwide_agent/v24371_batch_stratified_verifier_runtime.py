"""Batch-stratified source selection for the target-segment verifier.

V2.43.70 discovered hundreds of registrable hosts, but V2.43.58 concatenated
the two discovery batches and V2.43.62 partitioned only the first ten hosts.
When the first batch supplied ten hosts, the second batch therefore had zero
chance of contributing either proposal or verifier evidence.

This append-only successor places a deterministic, content-free prefilter
below the frozen V2.43.58--67 stack.  It keeps five registrable hosts from
each discovery batch and, at full capacity, arranges the frozen hash
partition so that each batch contributes four proposal hosts and one hidden
verifier host.  Selection may use only the visible query batch plus URL/title
and registrable-source provenance.  It runs before fetch, candidate
generation, entropy computation, or evaluator access and adds no search,
fetch, or model effect.

Runtime inputs remain exactly ``{opaque_id, question}``.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as table
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24269_task_union_discovery import (
    TaskUnionDiscoverySearchClient,
    validate_receipt as validate_union_receipt,
)
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24355_explicit_partition_runtime import (
    _lead_binding,
    _sha256_text,
    _source_digest_from_lead,
    _source_from_lead,
)
from .v24362_two_verifier_partition_runtime import (
    MAXIMUM_FETCH_SOURCES,
    VERIFIER_SOURCE_CAP,
    _partition_leads as frozen_partition_leads,
)
from .v24367_target_segment_verifier_runtime import (
    run_v24367_task,
    validate_result as validate_parent_result,
)


POLICY_ID = "v24371_batch_stratified_target_segment_verifier_runtime_v1"
ROLE = "v24371_batch_stratified_target_segment_verifier_task_result"
RECEIPT_ROLE = "v24371_batch_stratified_source_selection_receipt"
DISCOVERY_BATCH_COUNT = 2
LOGICAL_QUERY_COUNT = 4
HOSTS_PER_BATCH = MAXIMUM_FETCH_SOURCES // DISCOVERY_BATCH_COUNT
PROPOSAL_HOSTS_PER_BATCH = HOSTS_PER_BATCH - 1
STATE_KEYS = frozenset(
    {
        "query_batches",
        "raw_batch_leads",
        "selected_batch_leads",
        "underlying_union_receipt_before_fetch",
    }
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "baseline_prediction",
        "candidate_prediction",
        "batch_stratification_receipt",
        "private_replay_state",
        "result_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "partition_seed_sha256",
        "logical_query_count",
        "discovery_batch_count",
        "query_batch_sha256s",
        "raw_batch_unique_host_counts",
        "raw_unique_host_union_count",
        "selected_batch_host_counts",
        "selected_unique_host_union_count",
        "selected_host_count",
        "proposal_host_count",
        "verifier_host_count",
        "proposal_batch_host_counts",
        "verifier_batch_host_counts",
        "selected_batch_source_key_sha256_vectors",
        "partition_receipt_sha256",
        "full_capacity_batch_stratification_satisfied",
        "one_verifier_per_batch_at_full_capacity",
        "four_proposal_hosts_per_batch_at_full_capacity",
        "selection_precedes_fetch_candidate_entropy_and_evaluator",
        "selection_uses_visible_query_title_url_and_registrable_source_only",
        "fetch_effects_before_selection",
        "page_content_candidate_value_entropy_or_evaluator_used_for_selection",
        "provider_narrative_snippet_or_page_content_forwarded",
        "question_query_url_host_title_page_candidate_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "underlying_union_receipt_before_fetch",
        "receipt_sha256",
    }
)


def _query_vector(value: Sequence[str]) -> list[str]:
    if isinstance(value, (str, bytes)):
        raise ValueError("V2.43.71 query batch is not a sequence")
    output = [" ".join(str(item).split()).strip() for item in value]
    if len(output) != 2 or any(not item for item in output):
        raise ValueError("V2.43.71 requires two visible queries per batch")
    return output


def _lead(raw: Mapping[str, Any], *, batch_ordinal: int) -> dict[str, str] | None:
    url = table.canonicalize_url(
        str(raw.get("fetch_url") or raw.get("url") or "").strip()
    )
    if not url:
        return None
    value = {
        "url": url,
        "query": f"batch-stratified discovery {batch_ordinal}",
        "title": str(raw.get("title") or "")[:500],
        "member_label": "",
    }
    try:
        _source_from_lead(value)
    except ValueError:
        return None
    return value


def _unique_host_leads(
    batches: Sequence[Mapping[str, Any]], *, batch_ordinal: int
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        for raw in batch.get("results") or []:
            if not isinstance(raw, Mapping):
                continue
            lead = _lead(raw, batch_ordinal=batch_ordinal)
            if lead is None:
                continue
            source = _source_from_lead(lead)
            if source in seen:
                continue
            seen.add(source)
            output.append(lead)
    return output


def _rank(lead: Mapping[str, Any], *, seed: str) -> str:
    return _sha256_text(seed + "|" + _source_from_lead(lead))


def _terms(value: str) -> set[str]:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    output = set(re.findall(r"[a-z0-9][a-z0-9._-]{1,}", text))
    for block in re.findall(r"[\u3400-\u9fff]{2,}", text):
        output.add(block)
        for width in (2, 3, 4):
            output.update(
                block[index : index + width]
                for index in range(max(0, len(block) - width + 1))
            )
    return {item for item in output if len(item) >= 2}


def _coverage(
    lead: Mapping[str, Any], queries: Sequence[str]
) -> tuple[tuple[bool, ...], tuple[int, int, int]]:
    title = unicodedata.normalize("NFKC", str(lead.get("title") or "")).casefold()
    url = table.canonicalize_url(str(lead.get("url") or "")).casefold()
    haystack = title + " " + url
    per_query: list[bool] = []
    matched: set[str] = set()
    for query in queries:
        current = {term for term in _terms(query) if term in haystack}
        per_query.append(bool(current))
        matched.update(current)
    title_matches = sum(term in title for term in matched)
    return (
        tuple(per_query),
        (sum(per_query), sum(len(term) for term in matched), title_matches),
    )


def _ordered_proposals(
    leads: Sequence[dict[str, str]],
    queries: Sequence[str],
    *,
    seed: str,
    rank_floor: str,
) -> list[dict[str, str]]:
    eligible = [lead for lead in leads if _rank(lead, seed=seed) > rank_floor]
    return sorted(
        eligible,
        key=lambda lead: (
            tuple(-value for value in _coverage(lead, queries)[1]),
            tuple(not value for value in _coverage(lead, queries)[0]),
            _source_from_lead(lead),
        ),
    )[:PROPOSAL_HOSTS_PER_BATCH]


def _selection_objective(
    anchor: Mapping[str, Any],
    proposals: Sequence[Mapping[str, Any]],
    queries: Sequence[str],
    *,
    seed: str,
) -> tuple[int, int, int, int, int, str]:
    selected = [anchor, *proposals]
    masks = [_coverage(lead, queries)[0] for lead in selected]
    scores = [_coverage(lead, queries)[1] for lead in selected]
    anchor_score = scores[0]
    query_coverage = sum(
        any(mask[index] for mask in masks) for index in range(len(queries))
    )
    minimum_proposal_rank = min(_rank(lead, seed=seed) for lead in proposals)
    return (
        query_coverage,
        anchor_score[0],
        anchor_score[1],
        sum(score[1] for score in scores),
        int(minimum_proposal_rank, 16),
        _source_from_lead(anchor),
    )


def _select_batch(
    raw_leads: Sequence[dict[str, str]],
    queries: Sequence[str],
    *,
    seed: str,
    excluded_sources: set[str],
    anchor_rank_ceiling: str | None,
    proposal_rank_floor: str | None,
) -> list[dict[str, str]]:
    available = [
        copy.deepcopy(lead)
        for lead in raw_leads
        if _source_from_lead(lead) not in excluded_sources
    ]
    if len(available) <= HOSTS_PER_BATCH:
        return available
    candidates: list[
        tuple[tuple[int, int, int, int, int, str], dict[str, str], list[dict[str, str]]]
    ] = []
    for anchor in available:
        anchor_rank = _rank(anchor, seed=seed)
        if anchor_rank_ceiling is not None and anchor_rank >= anchor_rank_ceiling:
            continue
        floor = max(anchor_rank, proposal_rank_floor or anchor_rank)
        proposals = _ordered_proposals(
            [lead for lead in available if lead is not anchor],
            queries,
            seed=seed,
            rank_floor=floor,
        )
        if len(proposals) != PROPOSAL_HOSTS_PER_BATCH:
            continue
        objective = _selection_objective(
            anchor, proposals, queries, seed=seed
        )
        candidates.append((objective, anchor, proposals))
    if not candidates:
        ranked = sorted(
            available,
            key=lambda lead: (_rank(lead, seed=seed), _source_from_lead(lead)),
        )
        return [ranked[0], *ranked[-PROPOSAL_HOSTS_PER_BATCH:]]
    # The final source component is a deterministic tie breaker; prefer its
    # lexical minimum while maximizing every substantive objective field.
    substantive = max(item[0][:-1] for item in candidates)
    tied = [item for item in candidates if item[0][:-1] == substantive]
    _, anchor, proposals = min(tied, key=lambda item: item[0][-1])
    return [copy.deepcopy(anchor), *copy.deepcopy(proposals)]


def _select_batches(
    raw_batches: Sequence[Sequence[dict[str, str]]],
    query_batches: Sequence[Sequence[str]],
    *,
    seed: str,
) -> list[list[dict[str, str]]]:
    if len(raw_batches) != DISCOVERY_BATCH_COUNT or len(query_batches) != DISCOVERY_BATCH_COUNT:
        raise ValueError("V2.43.71 requires exactly two discovery batches")
    first = _select_batch(
        raw_batches[0],
        query_batches[0],
        seed=seed,
        excluded_sources=set(),
        anchor_rank_ceiling=None,
        proposal_rank_floor=None,
    )
    first_sources = {_source_from_lead(lead) for lead in first}
    first_anchor_rank = _rank(first[0], seed=seed) if len(first) == HOSTS_PER_BATCH else None
    first_proposal_floor = (
        min(_rank(lead, seed=seed) for lead in first[1:])
        if len(first) == HOSTS_PER_BATCH
        else None
    )
    second = _select_batch(
        raw_batches[1],
        query_batches[1],
        seed=seed,
        excluded_sources=first_sources,
        anchor_rank_ceiling=first_proposal_floor,
        proposal_rank_floor=first_anchor_rank,
    )
    return [first, second]


def _batch_counts(
    selected_batches: Sequence[Sequence[Mapping[str, Any]]],
    values: Sequence[Mapping[str, Any]],
) -> list[int]:
    wanted = {_source_from_lead(lead) for lead in values}
    return [
        sum(_source_from_lead(lead) in wanted for lead in batch)
        for batch in selected_batches
    ]


def _selection_summary(
    state: Mapping[str, Any], *, seed: str
) -> dict[str, Any]:
    raw_batches = state["raw_batch_leads"]
    selected_batches = state["selected_batch_leads"]
    selected_union = [lead for batch in selected_batches for lead in batch]
    proposal, verifier, partition = frozen_partition_leads(
        selected_union, partition_seed_sha256=seed
    )
    proposal_counts = _batch_counts(selected_batches, proposal)
    verifier_counts = _batch_counts(selected_batches, verifier)
    selected_counts = [len(batch) for batch in selected_batches]
    full = (
        selected_counts == [HOSTS_PER_BATCH, HOSTS_PER_BATCH]
        and len(selected_union) == MAXIMUM_FETCH_SOURCES
        and len({_source_from_lead(lead) for lead in selected_union})
        == MAXIMUM_FETCH_SOURCES
    )
    stratified = (
        full
        and proposal_counts == [PROPOSAL_HOSTS_PER_BATCH] * DISCOVERY_BATCH_COUNT
        and verifier_counts == [1, 1]
    )
    raw_union = {
        _source_from_lead(lead) for batch in raw_batches for lead in batch
    }
    return {
        "proposal": proposal,
        "verifier": verifier,
        "partition": partition,
        "proposal_counts": proposal_counts,
        "verifier_counts": verifier_counts,
        "selected_counts": selected_counts,
        "full": full,
        "stratified": stratified,
        "raw_union_count": len(raw_union),
    }


def _validate_state(value: Mapping[str, Any], *, seed: str) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{64}", seed) is None or set(value) != STATE_KEYS:
        raise ValueError("V2.43.71 replay state identity drifted")
    query_batches = value.get("query_batches")
    raw_batches = value.get("raw_batch_leads")
    selected_batches = value.get("selected_batch_leads")
    union_receipt = value.get("underlying_union_receipt_before_fetch")
    if (
        not isinstance(query_batches, list)
        or len(query_batches) != DISCOVERY_BATCH_COUNT
        or [_query_vector(batch) for batch in query_batches] != query_batches
        or len({query.casefold() for batch in query_batches for query in batch})
        != LOGICAL_QUERY_COUNT
        or not isinstance(raw_batches, list)
        or len(raw_batches) != DISCOVERY_BATCH_COUNT
        or not isinstance(selected_batches, list)
        or len(selected_batches) != DISCOVERY_BATCH_COUNT
        or any(not isinstance(batch, list) for batch in [*raw_batches, *selected_batches])
        or any(
            not isinstance(lead, Mapping)
            for batch in [*raw_batches, *selected_batches]
            for lead in batch
        )
        or not isinstance(union_receipt, Mapping)
    ):
        raise ValueError("V2.43.71 replay state schema drifted")
    validate_union_receipt(union_receipt)
    if (
        union_receipt.get("search_invocations") != DISCOVERY_BATCH_COUNT
        or union_receipt.get("logical_query_count") != LOGICAL_QUERY_COUNT
        or union_receipt.get("fetch_invocations") != 0
        or union_receipt.get("fetch_requested_source_count") != 0
        or any(
            len({_source_from_lead(lead) for lead in batch}) != len(batch)
            for batch in raw_batches
        )
        or _select_batches(raw_batches, query_batches, seed=seed) != selected_batches
    ):
        raise ValueError("V2.43.71 replay state selection drifted")
    return copy.deepcopy(dict(value))


def build_receipt(
    private_state: Mapping[str, Any], *, partition_seed_sha256: str
) -> dict[str, Any]:
    state = _validate_state(private_state, seed=partition_seed_sha256)
    summary = _selection_summary(state, seed=partition_seed_sha256)
    selected_batches = state["selected_batch_leads"]
    raw_batches = state["raw_batch_leads"]
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "partition_seed_sha256": partition_seed_sha256,
        "logical_query_count": sum(len(batch) for batch in state["query_batches"]),
        "discovery_batch_count": len(state["query_batches"]),
        "query_batch_sha256s": [
            payload_sha256(batch) for batch in state["query_batches"]
        ],
        "raw_batch_unique_host_counts": [len(batch) for batch in raw_batches],
        "raw_unique_host_union_count": summary["raw_union_count"],
        "selected_batch_host_counts": summary["selected_counts"],
        "selected_unique_host_union_count": len(
            {
                _source_from_lead(lead)
                for batch in selected_batches
                for lead in batch
            }
        ),
        "selected_host_count": summary["partition"]["selected_source_count"],
        "proposal_host_count": len(summary["proposal"]),
        "verifier_host_count": len(summary["verifier"]),
        "proposal_batch_host_counts": summary["proposal_counts"],
        "verifier_batch_host_counts": summary["verifier_counts"],
        "selected_batch_source_key_sha256_vectors": [
            [_source_digest_from_lead(lead) for lead in batch]
            for batch in selected_batches
        ],
        "partition_receipt_sha256": summary["partition"]["receipt_sha256"],
        "full_capacity_batch_stratification_satisfied": summary["stratified"],
        "one_verifier_per_batch_at_full_capacity": (
            summary["verifier_counts"] == [1, 1] if summary["full"] else False
        ),
        "four_proposal_hosts_per_batch_at_full_capacity": (
            summary["proposal_counts"] == [4, 4] if summary["full"] else False
        ),
        "selection_precedes_fetch_candidate_entropy_and_evaluator": True,
        "selection_uses_visible_query_title_url_and_registrable_source_only": True,
        "fetch_effects_before_selection": 0,
        "page_content_candidate_value_entropy_or_evaluator_used_for_selection": False,
        "provider_narrative_snippet_or_page_content_forwarded": False,
        "question_query_url_host_title_page_candidate_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "underlying_union_receipt_before_fetch": copy.deepcopy(
            state["underlying_union_receipt_before_fetch"]
        ),
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_receipt(value)
    return value


def validate_receipt(
    value: Mapping[str, Any], *, private_state: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    integer_fields = (
        "logical_query_count",
        "discovery_batch_count",
        "raw_unique_host_union_count",
        "selected_unique_host_union_count",
        "selected_host_count",
        "proposal_host_count",
        "verifier_host_count",
        "fetch_effects_before_selection",
    )
    vector_fields = (
        "query_batch_sha256s",
        "raw_batch_unique_host_counts",
        "selected_batch_host_counts",
        "proposal_batch_host_counts",
        "verifier_batch_host_counts",
        "selected_batch_source_key_sha256_vectors",
    )
    union_receipt = value.get("underlying_union_receipt_before_fetch")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("partition_seed_sha256"))) is None
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(value.get(name), list) for name in vector_fields)
        or value.get("logical_query_count") != LOGICAL_QUERY_COUNT
        or value.get("discovery_batch_count") != DISCOVERY_BATCH_COUNT
        or any(len(value.get(name, [])) != DISCOVERY_BATCH_COUNT for name in vector_fields)
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for name in (
                "raw_batch_unique_host_counts",
                "selected_batch_host_counts",
                "proposal_batch_host_counts",
                "verifier_batch_host_counts",
            )
            for item in value[name]
        )
        or any(
            not isinstance(vector, list)
            or any(re.fullmatch(r"[0-9a-f]{64}", str(item)) is None for item in vector)
            for vector in value.get("selected_batch_source_key_sha256_vectors", [])
        )
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(item)) is None
            for item in value.get("query_batch_sha256s", [])
        )
        or value.get("selected_host_count")
        != value.get("proposal_host_count") + value.get("verifier_host_count")
        or value.get("selected_host_count") != sum(value.get("selected_batch_host_counts", []))
        or value.get("proposal_host_count") != sum(value.get("proposal_batch_host_counts", []))
        or value.get("verifier_host_count") != sum(value.get("verifier_batch_host_counts", []))
        or value.get("selected_unique_host_union_count") != value.get("selected_host_count")
        or value.get("selected_host_count", -1) > MAXIMUM_FETCH_SOURCES
        or value.get("verifier_host_count", -1) > VERIFIER_SOURCE_CAP
        or value.get("full_capacity_batch_stratification_satisfied")
        is not (
            value.get("selected_batch_host_counts") == [5, 5]
            and value.get("proposal_batch_host_counts") == [4, 4]
            and value.get("verifier_batch_host_counts") == [1, 1]
        )
        or value.get("one_verifier_per_batch_at_full_capacity")
        is not (
            value.get("verifier_batch_host_counts") == [1, 1]
            if value.get("selected_batch_host_counts") == [5, 5]
            else False
        )
        or value.get("four_proposal_hosts_per_batch_at_full_capacity")
        is not (
            value.get("proposal_batch_host_counts") == [4, 4]
            if value.get("selected_batch_host_counts") == [5, 5]
            else False
        )
        or value.get("selection_precedes_fetch_candidate_entropy_and_evaluator") is not True
        or value.get("selection_uses_visible_query_title_url_and_registrable_source_only") is not True
        or value.get("fetch_effects_before_selection") != 0
        or value.get("page_content_candidate_value_entropy_or_evaluator_used_for_selection") is not False
        or value.get("provider_narrative_snippet_or_page_content_forwarded") is not False
        or value.get("question_query_url_host_title_page_candidate_value_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or not isinstance(union_receipt, Mapping)
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("partition_receipt_sha256"))) is None
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.71 selection receipt drifted")
    validate_union_receipt(union_receipt)
    if private_state is not None:
        expected = build_receipt(
            private_state,
            partition_seed_sha256=str(value["partition_seed_sha256"]),
        )
        if dict(value) != expected:
            raise ValueError("V2.43.71 selection receipt replay drifted")
    return copy.deepcopy(dict(value))


class BatchStratifiedPrefilterSearchClient:
    """Select a replayable 5+5 host vector before the frozen source union."""

    def __init__(self, inner: Any, *, partition_seed_sha256: str) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", partition_seed_sha256) is None:
            raise ValueError("V2.43.71 partition seed drifted")
        self._union = TaskUnionDiscoverySearchClient(inner)
        self.partition_seed_sha256 = partition_seed_sha256
        self.query_batches: list[list[str]] = []
        self.raw_batch_leads: list[list[dict[str, str]]] = []
        self.selected_batch_leads: list[list[dict[str, str]]] = []
        self._state: dict[str, Any] | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._union, name)

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        if len(self.query_batches) >= DISCOVERY_BATCH_COUNT:
            raise RuntimeError("V2.43.71 discovery batch repeated")
        query_batch = _query_vector(queries)
        raw = self._union.search_many(query_batch, **kwargs)
        ordinal = len(self.query_batches) + 1
        leads = _unique_host_leads(raw, batch_ordinal=ordinal)
        self.query_batches.append(query_batch)
        self.raw_batch_leads.append(leads)
        if ordinal == 1:
            selected = _select_batch(
                leads,
                query_batch,
                seed=self.partition_seed_sha256,
                excluded_sources=set(),
                anchor_rank_ceiling=None,
                proposal_rank_floor=None,
            )
        else:
            selected = _select_batches(
                self.raw_batch_leads,
                self.query_batches,
                seed=self.partition_seed_sha256,
            )[-1]
        self.selected_batch_leads.append(selected)
        if len(self.query_batches) == DISCOVERY_BATCH_COUNT:
            self._state = {
                "query_batches": copy.deepcopy(self.query_batches),
                "raw_batch_leads": copy.deepcopy(self.raw_batch_leads),
                "selected_batch_leads": copy.deepcopy(self.selected_batch_leads),
                "underlying_union_receipt_before_fetch": copy.deepcopy(
                    self._union.receipt()
                ),
            }
            _validate_state(self._state, seed=self.partition_seed_sha256)
        if not selected:
            return []
        return [
            {
                "query": f"batch-stratified discovery {ordinal}",
                "answer": "",
                "results": copy.deepcopy(selected),
                "error": None,
                "provider": "v24371-batch-stratified-prefilter",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        if self._state is None:
            raise RuntimeError("V2.43.71 fetch preceded two-batch selection")
        return self._union.fetch_urls(requests_)

    def private_replay_state(self) -> dict[str, Any]:
        if self._state is None:
            raise RuntimeError("V2.43.71 replay state is absent")
        return _validate_state(self._state, seed=self.partition_seed_sha256)


def run_v24371_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits | None = None,
    monotonic: Any,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    stratified = BatchStratifiedPrefilterSearchClient(
        search, partition_seed_sha256=partition_seed_sha256
    )
    parent = run_v24367_task(
        visible,
        model=model,
        search=stratified,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    validate_parent_result(parent)
    state = stratified.private_replay_state()
    receipt = build_receipt(state, partition_seed_sha256=partition_seed_sha256)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(parent),
        "baseline_prediction": str(parent["baseline_prediction"]),
        "candidate_prediction": str(parent["candidate_prediction"]),
        "batch_stratification_receipt": receipt,
        "private_replay_state": state,
    }
    value["result_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def _projection(lead: Mapping[str, Any]) -> dict[str, str]:
    return {
        "url": table.canonicalize_url(str(lead.get("url") or "")),
        "title": str(lead.get("title") or "")[:500],
        "source_sha256": _source_digest_from_lead(lead),
        "binding_sha256": _lead_binding(lead),
    }


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    parent = value.get("parent_result")
    receipt = value.get("batch_stratification_receipt")
    state = value.get("private_replay_state")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(parent, Mapping)
        or not isinstance(receipt, Mapping)
        or not isinstance(state, Mapping)
        or not isinstance(value.get("baseline_prediction"), str)
        or not isinstance(value.get("candidate_prediction"), str)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.71 result identity drifted")
    validate_parent_result(parent)
    validate_receipt(receipt, private_state=state)
    frozen_state = _validate_state(
        state, seed=str(receipt["partition_seed_sha256"])
    )
    parent_batches = parent["parent_result"]["private_replay_state"][
        "two_batch_discovery_state"
    ]["batch_leads"]
    selected_batches = frozen_state["selected_batch_leads"]
    if len(parent_batches) != DISCOVERY_BATCH_COUNT:
        raise ValueError("V2.43.71 parent discovery batch count drifted")
    for parent_batch, selected_batch in zip(
        parent_batches, selected_batches, strict=True
    ):
        if sorted((_projection(lead) for lead in parent_batch), key=lambda item: item["binding_sha256"]) != sorted(
            (_projection(lead) for lead in selected_batch),
            key=lambda item: item["binding_sha256"],
        ):
            raise ValueError("V2.43.71 selected batch drifted from frozen parent")
    parent_partition = parent["target_segment_verifier_receipt"][
        "partition_receipt"
    ]
    summary = _selection_summary(
        frozen_state, seed=str(receipt["partition_seed_sha256"])
    )
    if (
        summary["partition"] != parent_partition
        or receipt["partition_receipt_sha256"] != parent_partition["receipt_sha256"]
        or value["baseline_prediction"] != parent["baseline_prediction"]
        or value["candidate_prediction"] != parent["candidate_prediction"]
    ):
        raise ValueError("V2.43.71 parent handoff drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "BatchStratifiedPrefilterSearchClient",
    "POLICY_ID",
    "ROLE",
    "build_receipt",
    "run_v24371_task",
    "validate_receipt",
    "validate_result",
]
