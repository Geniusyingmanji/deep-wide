"""Task-local discovery union for keyless multi-query hosted search.

Some valid hosted-search responses expose action-level source URLs without
section-local citation spans.  Broadcasting those URLs to every logical query
would invent provenance.  This successor instead collapses all URLs from one
``search_many`` call into one task-local, deduplicated discovery set.  Provider
narrative and snippets are discarded.  Only pages fetched later by the
deterministic public-page fetcher may enter synthesis as active evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24268_keyless_batched_runtime import (
    POLICY_ID as PARENT_POLICY_ID,
    RESULT_ROLE as PARENT_RESULT_ROLE,
    run_v24268_task,
    validate_v24268_result,
)


POLICY_ID = "v24269_task_local_source_union_v1"
RESULT_ROLE = "v24269_task_union_task_result"
COUNTERS = (
    "calls",
    "failures",
    "tool_calls",
    "fetch_calls",
    "fetch_failures",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "search_invocations",
        "logical_query_count",
        "raw_batch_count",
        "raw_query_local_result_count",
        "raw_action_source_count",
        "raw_query_local_mapping_failure_count",
        "raw_unrecoverable_failure_count",
        "union_source_count",
        "duplicate_source_count",
        "union_recovery_invocation_count",
        "returned_union_batch_count",
        "fetch_invocations",
        "fetch_requested_source_count",
        "fetch_returned_batch_count",
        "fetch_usable_page_count",
        "provider_narrative_or_snippet_forwarded",
        "source_broadcast_to_logical_queries",
        "fetched_page_text_is_only_active_evidence",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
)


def _counter_snapshot(client: Any) -> dict[str, int]:
    return {name: max(0, int(getattr(client, name, 0) or 0)) for name in COUNTERS}


def _counter_delta(after: Mapping[str, int], before: Mapping[str, int]) -> dict[str, int]:
    return {name: max(0, int(after[name]) - int(before[name])) for name in COUNTERS}


def _source_lead(value: Mapping[str, Any]) -> dict[str, str] | None:
    fetch_url = str(value.get("fetch_url") or value.get("url") or "").strip()
    url = canonicalize_url(fetch_url)
    if not url:
        return None
    return {
        "title": str(value.get("title", ""))[:500],
        "url": url,
        "fetch_url": fetch_url,
        "content": "",
        "raw_content": "",
        "score": None,
        "source_type": "task_local_discovery_lead",
    }


def _action_sources(batch: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    trace = batch.get("hosted_search_trace")
    if not isinstance(trace, Mapping):
        return []
    values: list[Mapping[str, Any]] = []
    for action in trace.get("actions") or []:
        if not isinstance(action, Mapping):
            continue
        for source in action.get("sources") or []:
            if isinstance(source, Mapping):
                values.append(source)
    return values


def _usable_pages(batches: object) -> int:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return 0
    count = 0
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        for result in batch.get("results") or []:
            if isinstance(result, Mapping) and str(
                result.get("raw_content") or result.get("content") or ""
            ).strip():
                count += 1
    return count


class TaskUnionDiscoverySearchClient:
    """Convert query-local results and action sources into one discovery set."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        for name in COUNTERS:
            setattr(self, name, 0)
        self.search_invocations = 0
        self.logical_query_count = 0
        self.raw_batch_count = 0
        self.raw_query_local_result_count = 0
        self.raw_action_source_count = 0
        self.raw_query_local_mapping_failure_count = 0
        self.raw_unrecoverable_failure_count = 0
        self.union_source_count = 0
        self.duplicate_source_count = 0
        self.union_recovery_invocation_count = 0
        self.returned_union_batch_count = 0
        self.fetch_invocations = 0
        self.fetch_requested_source_count = 0
        self.fetch_returned_batch_count = 0
        self.fetch_usable_page_count = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def _add_delta(
        self,
        delta: Mapping[str, int],
        *,
        recovered_mapping_failures: int = 0,
    ) -> None:
        for name in COUNTERS:
            amount = int(delta[name])
            if name == "failures":
                amount = max(0, amount - max(0, int(recovered_mapping_failures)))
            setattr(self, name, int(getattr(self, name)) + amount)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        logical_queries = list(queries)
        before = _counter_snapshot(self.inner)
        raw: Any = []
        try:
            raw = self.inner.search_many(logical_queries, **kwargs)
        finally:
            after = _counter_snapshot(self.inner)
        raw_batches = [batch for batch in raw if isinstance(batch, Mapping)] if isinstance(raw, Sequence) else []
        mapping_failures = sum(
            str(batch.get("error", ""))
            == "hosted search returned no query-local URL citation"
            and not bool(batch.get("results"))
            for batch in raw_batches
        )
        unrecoverable_failures = sum(
            bool(batch.get("error"))
            and str(batch.get("error", ""))
            != "hosted search returned no query-local URL citation"
            for batch in raw_batches
        )
        query_local_values: list[Mapping[str, Any]] = []
        action_values: list[Mapping[str, Any]] = []
        for batch in raw_batches:
            query_local_values.extend(
                result
                for result in (batch.get("results") or [])
                if isinstance(result, Mapping)
            )
            action_values.extend(_action_sources(batch))

        leads: list[dict[str, str]] = []
        seen: set[str] = set()
        raw_source_count = len(query_local_values) + len(action_values)
        for source in [*query_local_values, *action_values]:
            lead = _source_lead(source)
            if lead is None or lead["url"] in seen:
                continue
            seen.add(lead["url"])
            leads.append(lead)
        recovered_mapping_failures = mapping_failures if leads else 0
        self._add_delta(
            _counter_delta(after, before),
            recovered_mapping_failures=recovered_mapping_failures,
        )
        self.search_invocations += 1
        self.logical_query_count += len(logical_queries)
        self.raw_batch_count += len(raw_batches)
        self.raw_query_local_result_count += len(query_local_values)
        self.raw_action_source_count += len(action_values)
        self.raw_query_local_mapping_failure_count += int(mapping_failures)
        self.raw_unrecoverable_failure_count += int(unrecoverable_failures)
        self.union_source_count += len(leads)
        self.duplicate_source_count += max(0, raw_source_count - len(leads))
        self.union_recovery_invocation_count += int(
            bool(leads) and bool(mapping_failures)
        )
        self.returned_union_batch_count += int(bool(leads))
        if not leads:
            return []
        return [
            {
                "query": "task-local discovery union",
                "answer": "",
                "results": leads,
                "error": None,
                "provider": "azure-responses-task-local-source-union",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        values = list(requests_)
        before = _counter_snapshot(self.inner)
        batches: Any = []
        try:
            batches = self.inner.fetch_urls(values)
            return batches
        finally:
            after = _counter_snapshot(self.inner)
            self._add_delta(_counter_delta(after, before))
            self.fetch_invocations += 1
            self.fetch_requested_source_count += len(values)
            if isinstance(batches, Sequence) and not isinstance(batches, (str, bytes)):
                self.fetch_returned_batch_count += sum(
                    isinstance(batch, Mapping) for batch in batches
                )
            self.fetch_usable_page_count += _usable_pages(batches)

    def receipt(self) -> dict[str, Any]:
        value = {
            "artifact_version": 1,
            "role": "v24269_task_union_discovery_receipt",
            "search_invocations": self.search_invocations,
            "logical_query_count": self.logical_query_count,
            "raw_batch_count": self.raw_batch_count,
            "raw_query_local_result_count": self.raw_query_local_result_count,
            "raw_action_source_count": self.raw_action_source_count,
            "raw_query_local_mapping_failure_count": self.raw_query_local_mapping_failure_count,
            "raw_unrecoverable_failure_count": self.raw_unrecoverable_failure_count,
            "union_source_count": self.union_source_count,
            "duplicate_source_count": self.duplicate_source_count,
            "union_recovery_invocation_count": self.union_recovery_invocation_count,
            "returned_union_batch_count": self.returned_union_batch_count,
            "fetch_invocations": self.fetch_invocations,
            "fetch_requested_source_count": self.fetch_requested_source_count,
            "fetch_returned_batch_count": self.fetch_returned_batch_count,
            "fetch_usable_page_count": self.fetch_usable_page_count,
            "provider_narrative_or_snippet_forwarded": False,
            "source_broadcast_to_logical_queries": False,
            "fetched_page_text_is_only_active_evidence": True,
            "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        validate_receipt(value)
        return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.69 {label} is not a nonnegative integer")
    return value


def validate_receipt(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24269_task_union_discovery_receipt"
        or value.get("provider_narrative_or_snippet_forwarded") is not False
        or value.get("source_broadcast_to_logical_queries") is not False
        or value.get("fetched_page_text_is_only_active_evidence") is not True
        or value.get(
            "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise ValueError("V2.42.69 discovery receipt drifted")
    for key in RECEIPT_KEYS - {
        "role",
        "provider_narrative_or_snippet_forwarded",
        "source_broadcast_to_logical_queries",
        "fetched_page_text_is_only_active_evidence",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }:
        _nonnegative_integer(value.get(key), key)
    if value["union_recovery_invocation_count"] > value["search_invocations"]:
        raise ValueError("V2.42.69 recovery accounting drifted")
    if value["returned_union_batch_count"] > value["search_invocations"]:
        raise ValueError("V2.42.69 union batch accounting drifted")
    if value["fetch_usable_page_count"] > value["fetch_returned_batch_count"]:
        raise ValueError("V2.42.69 fetched-page accounting drifted")


def run_v24269_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    monotonic: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    union = TaskUnionDiscoverySearchClient(search)
    kwargs: dict[str, Any] = {
        "model": model,
        "search": union,
        "limits": limits,
        "progress": progress,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent = run_v24268_task(task, **kwargs)
    result = dict(parent)
    result["role"] = RESULT_ROLE
    result["policy_id"] = POLICY_ID
    result["discovery_union"] = union.receipt()
    validate_v24269_result(result)
    return result


def validate_v24269_result(value: Mapping[str, Any]) -> None:
    if value.get("role") != RESULT_ROLE or value.get("policy_id") != POLICY_ID:
        raise ValueError("V2.42.69 result identity drifted")
    receipt = value.get("discovery_union")
    if not isinstance(receipt, Mapping):
        raise ValueError("V2.42.69 discovery receipt is absent")
    validate_receipt(receipt)
    parent = dict(value)
    parent.pop("discovery_union", None)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    validate_v24268_result(parent)


__all__ = [
    "POLICY_ID",
    "RESULT_ROLE",
    "TaskUnionDiscoverySearchClient",
    "run_v24269_task",
    "validate_receipt",
    "validate_v24269_result",
]
