"""Single-shot hosted-search transport for task-local source union.

The generic native-search client recursively splits a successful multi-query
response when one or more requested section markers are absent.  That is the
right conservative behaviour for callers that require query-local provenance,
but it is redundant behind :class:`TaskUnionDiscoverySearchClient`: that
adapter deliberately consumes the action-level source union and discards the
provider narrative.

This append-only transport never changes the generic client.  It performs one
request per native chunk, preserves any query-local citations that were
actually mapped, and exposes the response's action sources exactly once for
the downstream task-union adapter.  Missing markers remain mapping failures;
only the existing task-union layer may recover them when a non-empty source
union exists.  Transport failures are never reclassified or retried by this
layer beyond the parent's fixed request retry policy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .clients import SearchRequestError
from .native_search import (
    NATIVE_SEARCH_PROVIDER,
    AzureNativeSearchClient,
    _web_search_actions,
)
from .v24275_hard_deadline_fetch import HardDeadlineNativeSearchClient


POLICY_ID = "v24280_task_union_single_shot_native_search_v1"
MAPPING_FAILURE = "hosted search returned no query-local URL citation"
OMITTED_MARKER = "hosted search omitted the required query marker"
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "multi_query_chunks",
        "incomplete_mapping_chunks",
        "mapping_failure_rows_normalized",
        "action_trace_attachments",
        "recursive_split_requests",
        "one_action_trace_per_chunk",
        "task_union_only",
        "benchmark_metadata_or_evaluator_read",
    }
)


def _action_trace(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    actions = _web_search_actions(dict(payload))
    if not actions:
        return None
    return {
        "response_id": str(payload.get("id", "")),
        "search_call_ids": [
            str(action.get("id", ""))
            for action in actions
            if str(action.get("id", ""))
        ],
        "actions": actions,
    }


def parse_task_union_single_shot(
    client: AzureNativeSearchClient,
    queries: Sequence[str],
    payload: Mapping[str, Any],
    *,
    max_results: int,
) -> tuple[list[dict[str, Any]], bool, int, int]:
    """Parse one response without recursive requests for a task-union caller.

    Returns ``(batches, complete_mapping, normalized_rows, trace_attachments)``.
    The action trace is attached to at most one batch, so action sources are
    not represented once per logical query before task-level deduplication.
    """

    logical_queries = list(queries)
    batches, complete = client._parse_batch(
        logical_queries, dict(payload), max_results=max_results
    )
    if len(logical_queries) <= 1:
        return batches, complete, 0, 0

    for batch in batches:
        batch.pop("hosted_search_trace", None)
    trace = _action_trace(payload)
    attachments = 0
    if trace is not None and batches:
        batches[0]["hosted_search_trace"] = trace
        attachments = 1

    normalized = 0
    if not complete:
        for batch in batches:
            if not batch.get("results") and batch.get("error") == OMITTED_MARKER:
                batch["error"] = MAPPING_FAILURE
                normalized += 1
    return batches, complete, normalized, attachments


class TaskUnionSingleShotMixin:
    """Override only native chunk fallback; page fetching follows the parent."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.multi_query_chunks = 0
        self.incomplete_mapping_chunks = 0
        self.mapping_failure_rows_normalized = 0
        self.action_trace_attachments = 0
        self.recursive_split_requests = 0

    def _run_chunk(
        self, queries: list[str], max_results: int
    ) -> list[dict[str, Any]]:
        try:
            payload = self._request(queries)
            batches, complete, normalized, attachments = (
                parse_task_union_single_shot(
                    self, queries, payload, max_results=max_results
                )
            )
        except SearchRequestError as exc:
            self._increment("failures", len(queries))
            return [
                {
                    "query": query,
                    "answer": "",
                    "results": [],
                    "error": str(exc),
                    "provider": NATIVE_SEARCH_PROVIDER,
                }
                for query in queries
            ]

        if len(queries) > 1:
            self._increment("multi_query_chunks")
            if not complete:
                self._increment("incomplete_mapping_chunks")
            self._increment("mapping_failure_rows_normalized", normalized)
            self._increment("action_trace_attachments", attachments)
        for batch in batches:
            if batch.get("error"):
                self._increment("failures")
        self._enrich_pages(batches)
        return batches

    def single_shot_receipt(self) -> dict[str, Any]:
        value = {
            "artifact_version": 1,
            "role": "v24280_task_union_single_shot_receipt",
            "policy_id": POLICY_ID,
            "multi_query_chunks": int(self.multi_query_chunks),
            "incomplete_mapping_chunks": int(self.incomplete_mapping_chunks),
            "mapping_failure_rows_normalized": int(
                self.mapping_failure_rows_normalized
            ),
            "action_trace_attachments": int(self.action_trace_attachments),
            "recursive_split_requests": int(self.recursive_split_requests),
            "one_action_trace_per_chunk": True,
            "task_union_only": True,
            "benchmark_metadata_or_evaluator_read": False,
        }
        validate_receipt(value)
        return value


class TaskUnionSingleShotNativeSearchClient(
    TaskUnionSingleShotMixin, AzureNativeSearchClient
):
    """Native-search variant intended only behind task-local source union."""


class TaskUnionSingleShotHardDeadlineNativeSearchClient(
    TaskUnionSingleShotMixin, HardDeadlineNativeSearchClient
):
    """Single-shot task-union search plus V2.42.75 hard-deadline fetching."""


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.80 {label} is not a nonnegative integer")
    return value


def validate_receipt(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24280_task_union_single_shot_receipt"
        or value.get("policy_id") != POLICY_ID
        or value.get("one_action_trace_per_chunk") is not True
        or value.get("task_union_only") is not True
        or value.get("benchmark_metadata_or_evaluator_read") is not False
    ):
        raise ValueError("V2.42.80 receipt drifted")
    for name in (
        "multi_query_chunks",
        "incomplete_mapping_chunks",
        "mapping_failure_rows_normalized",
        "action_trace_attachments",
        "recursive_split_requests",
    ):
        _nonnegative_integer(value.get(name), name)
    if (
        value["incomplete_mapping_chunks"] > value["multi_query_chunks"]
        or value["action_trace_attachments"] > value["multi_query_chunks"]
        or value["recursive_split_requests"] != 0
    ):
        raise ValueError("V2.42.80 receipt accounting drifted")


__all__ = [
    "MAPPING_FAILURE",
    "POLICY_ID",
    "TaskUnionSingleShotHardDeadlineNativeSearchClient",
    "TaskUnionSingleShotNativeSearchClient",
    "parse_task_union_single_shot",
    "validate_receipt",
]
