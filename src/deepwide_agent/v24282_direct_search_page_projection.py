"""Direct-search lead projection with deterministic public-page evidence.

Hosted LLM search dominates the current fast pipeline's input-token cost.  A
direct search API can remove that model context, but its answer, snippets and
provider-returned raw content must not silently become page evidence.  This
append-only adapter therefore projects only canonical URL leads from a direct
search client and delegates all active evidence acquisition to the existing
hard-deadline public-page fetcher.

Credentials remain owned by the injected direct-search client.  This module
does not read environment variables, files or keyrings and its receipt contains
only counts and policy flags, never queries, URLs, hosts, page text, task IDs,
predictions, credentials, or hashes of those values.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url


POLICY_ID = "v24282_direct_search_page_projection_v1"
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
        "policy_id",
        "search_invocations",
        "logical_query_count",
        "raw_batch_count",
        "raw_result_count",
        "projected_lead_count",
        "invalid_or_duplicate_lead_count",
        "provider_error_batch_count",
        "fetch_invocations",
        "fetch_requested_source_count",
        "fetch_returned_batch_count",
        "fetch_usable_page_count",
        "provider_answer_snippet_score_or_raw_content_forwarded",
        "deterministic_fetched_page_text_is_only_active_evidence",
        "credential_environment_file_keyring_value_or_hash_read_or_emitted",
        "question_query_url_host_page_task_id_prediction_answer_or_credential_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
)


def _counter(client: Any, name: str) -> int:
    return max(0, int(getattr(client, name, 0) or 0))


def _usable_pages(batches: object) -> int:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return 0
    return sum(
        bool(
            str(result.get("raw_content") or result.get("content") or "").strip()
        )
        for batch in batches
        if isinstance(batch, Mapping)
        for result in (batch.get("results") or [])
        if isinstance(result, Mapping)
    )


class DirectSearchPageProjectionClient:
    """Strip direct-search content and fetch every admitted URL independently."""

    def __init__(self, search: Any, fetcher: Any) -> None:
        self.search_client = search
        self.fetch_client = fetcher
        self.batch_size = max(1, int(getattr(search, "batch_size", 1) or 1))
        self.max_workers = max(1, int(getattr(search, "max_workers", 1) or 1))
        self.fetch_workers = max(
            1, int(getattr(fetcher, "fetch_workers", 1) or 1)
        )
        self.fetch_timeout = max(
            1, int(getattr(fetcher, "fetch_timeout", 1) or 1)
        )
        self.fetch_pages = False
        self.search_invocations = 0
        self.logical_query_count = 0
        self.raw_batch_count = 0
        self.raw_result_count = 0
        self.projected_lead_count = 0
        self.invalid_or_duplicate_lead_count = 0
        self.provider_error_batch_count = 0
        self.fetch_invocations = 0
        self.fetch_requested_source_count = 0
        self.fetch_returned_batch_count = 0
        self.fetch_usable_page_count = 0

    @property
    def calls(self) -> int:
        return _counter(self.search_client, "calls")

    @property
    def failures(self) -> int:
        return _counter(self.search_client, "failures")

    @property
    def tool_calls(self) -> int:
        # A direct search HTTP call is already represented by ``calls``.  It
        # does not execute an LLM-hosted tool action.
        return 0

    @property
    def fetch_calls(self) -> int:
        return _counter(self.fetch_client, "fetch_calls")

    @property
    def fetch_failures(self) -> int:
        return _counter(self.fetch_client, "fetch_failures")

    @property
    def input_tokens(self) -> int:
        # Direct API token usage is not applicable, not estimated as zero LLM
        # usage by a provider meter.  This compatibility surface remains zero
        # because the active runtime expects an integer counter.
        return 0

    @property
    def output_tokens(self) -> int:
        return 0

    @property
    def total_tokens(self) -> int:
        return 0

    @property
    def hard_fetch_helper_calls(self) -> int:
        return _counter(self.fetch_client, "hard_fetch_helper_calls")

    @property
    def hard_fetch_deadline_failures(self) -> int:
        return _counter(self.fetch_client, "hard_fetch_deadline_failures")

    @property
    def fetch_helper_failures(self) -> int:
        return _counter(self.fetch_client, "fetch_helper_failures")

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        logical = list(queries)
        raw = self.search_client.search_many(logical, **kwargs)
        raw_batches = (
            [batch for batch in raw if isinstance(batch, Mapping)]
            if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes))
            else []
        )
        output: list[dict[str, Any]] = []
        self.search_invocations += 1
        self.logical_query_count += len(logical)
        self.raw_batch_count += len(raw_batches)
        for batch in raw_batches:
            error = str(batch.get("error", "")).strip() or None
            if error:
                self.provider_error_batch_count += 1
            leads: list[dict[str, Any]] = []
            seen: set[str] = set()
            raw_results = [
                result
                for result in (batch.get("results") or [])
                if isinstance(result, Mapping)
            ]
            self.raw_result_count += len(raw_results)
            for result in raw_results:
                fetch_url = str(result.get("url", "")).strip()
                canonical = canonicalize_url(fetch_url)
                if not canonical or canonical in seen:
                    self.invalid_or_duplicate_lead_count += 1
                    continue
                seen.add(canonical)
                leads.append(
                    {
                        "title": str(result.get("title", ""))[:500],
                        "url": canonical,
                        "fetch_url": fetch_url,
                        "content": "",
                        "raw_content": "",
                        "score": None,
                        "source_type": "direct_search_untrusted_lead",
                    }
                )
            self.projected_lead_count += len(leads)
            output.append(
                {
                    "query": str(batch.get("query", "")),
                    "answer": "",
                    "results": leads,
                    "error": error if not leads else None,
                    "provider": "direct-search-page-projection",
                }
            )
        return output

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        values = list(requests_)
        batches: Any = []
        try:
            batches = self.fetch_client.fetch_urls(values)
            return batches
        finally:
            self.fetch_invocations += 1
            self.fetch_requested_source_count += len(values)
            if isinstance(batches, Sequence) and not isinstance(
                batches, (str, bytes)
            ):
                self.fetch_returned_batch_count += sum(
                    isinstance(batch, Mapping) for batch in batches
                )
            self.fetch_usable_page_count += _usable_pages(batches)

    def receipt(self) -> dict[str, Any]:
        value = {
            "artifact_version": 1,
            "role": "v24282_direct_search_page_projection_receipt",
            "policy_id": POLICY_ID,
            "search_invocations": self.search_invocations,
            "logical_query_count": self.logical_query_count,
            "raw_batch_count": self.raw_batch_count,
            "raw_result_count": self.raw_result_count,
            "projected_lead_count": self.projected_lead_count,
            "invalid_or_duplicate_lead_count": self.invalid_or_duplicate_lead_count,
            "provider_error_batch_count": self.provider_error_batch_count,
            "fetch_invocations": self.fetch_invocations,
            "fetch_requested_source_count": self.fetch_requested_source_count,
            "fetch_returned_batch_count": self.fetch_returned_batch_count,
            "fetch_usable_page_count": self.fetch_usable_page_count,
            "provider_answer_snippet_score_or_raw_content_forwarded": False,
            "deterministic_fetched_page_text_is_only_active_evidence": True,
            "credential_environment_file_keyring_value_or_hash_read_or_emitted": False,
            "question_query_url_host_page_task_id_prediction_answer_or_credential_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        validate_receipt(value)
        return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.82 {label} is not a nonnegative integer")
    return value


def validate_receipt(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24282_direct_search_page_projection_receipt"
        or value.get("policy_id") != POLICY_ID
        or value.get("provider_answer_snippet_score_or_raw_content_forwarded")
        is not False
        or value.get("deterministic_fetched_page_text_is_only_active_evidence")
        is not True
        or value.get(
            "credential_environment_file_keyring_value_or_hash_read_or_emitted"
        )
        is not False
        or value.get(
            "question_query_url_host_page_task_id_prediction_answer_or_credential_persisted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise ValueError("V2.42.82 receipt drifted")
    numeric = RECEIPT_KEYS - {
        "role",
        "policy_id",
        "provider_answer_snippet_score_or_raw_content_forwarded",
        "deterministic_fetched_page_text_is_only_active_evidence",
        "credential_environment_file_keyring_value_or_hash_read_or_emitted",
        "question_query_url_host_page_task_id_prediction_answer_or_credential_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
    for name in numeric:
        _nonnegative_integer(value.get(name), name)
    if (
        value["projected_lead_count"] > value["raw_result_count"]
        or value["invalid_or_duplicate_lead_count"]
        != value["raw_result_count"] - value["projected_lead_count"]
        or value["provider_error_batch_count"] > value["raw_batch_count"]
        or value["fetch_usable_page_count"]
        > value["fetch_requested_source_count"]
        or value["fetch_returned_batch_count"]
        > value["fetch_requested_source_count"]
    ):
        raise ValueError("V2.42.82 receipt accounting drifted")


__all__ = [
    "DirectSearchPageProjectionClient",
    "POLICY_ID",
    "validate_receipt",
]
