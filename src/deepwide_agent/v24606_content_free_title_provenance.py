"""Content-free title provenance observer for the concrete search transport.

V2.46.04 observed only the title carried by a lead at selection time.  This
execution-scoped observer measures four earlier/later boundaries without
changing them: provider action sources, query-local URL citations, effective
``fetch_urls`` inputs, and fetched-page results.  It retains only counts and
same-response/call co-occurrence booleans; raw titles, URLs, queries, pages,
tasks, and predictions never enter its receipt.

The observer performs no network, model, search, fetch, process, file, or
evaluator effect itself.  It calls the exact frozen methods once and returns
their exact objects.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any

from . import native_search as native
from . import v24468_total_wall_transport as transport


POLICY_ID = "v24606_content_free_title_provenance_observer_v1"
EXPECTED_BINDING_COUNT = 2
ORIGINAL_REQUEST = transport.HardTotalWallNativeSearchClient._request
ORIGINAL_FETCH_URLS = native.AzureNativeSearchClient.fetch_urls
ORIGINAL_ACTIONS = native._web_search_actions
ORIGINAL_TEXT_AND_ANNOTATIONS = native._response_text_and_annotations
_BINDING_GUARD = threading.Lock()

COUNT_FIELDS = (
    "provider_response_count",
    "action_source_count",
    "action_source_empty_title_count",
    "action_source_nonempty_title_count",
    "query_local_citation_count",
    "query_local_citation_empty_title_count",
    "query_local_citation_nonempty_title_count",
    "same_url_action_and_citation_count",
    "same_url_action_empty_citation_nonempty_count",
    "same_url_action_nonempty_citation_empty_count",
    "same_url_both_nonempty_equal_title_count",
    "same_url_both_nonempty_conflicting_title_count",
    "fetch_urls_call_count",
    "effective_fetch_request_count",
    "fetch_request_empty_title_count",
    "fetch_request_nonempty_title_count",
    "fetched_result_count",
    "fetched_result_empty_title_count",
    "fetched_result_nonempty_title_count",
    "fetched_usable_page_count",
    "empty_fetch_request_to_nonempty_result_title_count",
    "nonempty_fetch_request_to_nonempty_result_title_count",
)
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "binding_count",
        *COUNT_FIELDS,
        "provider_payload_and_fetch_batches_returned_exactly",
        "successful_provider_payload_observed_once_after_frozen_request",
        "fetch_input_observed_before_and_output_after_frozen_fetch_urls",
        "same_url_alignment_uses_canonical_url_in_memory_only",
        "raw_task_question_query_url_title_page_prediction_or_credential_emitted",
        "query_search_fetch_model_process_or_evaluator_effect_added",
        "ranking_validator_evidence_posterior_entropy_or_credit_changed",
        "cache_or_cross_task_state_used",
        "bindings_restored",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _title(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _valid_url(value: object) -> str:
    return native.canonicalize_url(str(value or "").strip())


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.46.06 {label} is invalid")
    return value


class ContentFreeTitleProvenanceObserver(
    AbstractContextManager["ContentFreeTitleProvenanceObserver"]
):
    """Observe exact concrete transport boundaries for one worker execution."""

    def __init__(self) -> None:
        self._active = False
        self._acquired = False
        self._request_replacement: Any = None
        self._fetch_replacement: Any = None
        self._lock = threading.RLock()
        self._stats = {name: 0 for name in COUNT_FIELDS}

    def _observe_payload(self, payload: Mapping[str, Any]) -> None:
        actions = ORIGINAL_ACTIONS(dict(payload))
        _text, annotations = ORIGINAL_TEXT_AND_ANNOTATIONS(dict(payload))
        action_by_url: dict[str, set[str]] = {}
        citation_by_url: dict[str, set[str]] = {}
        action_count = action_empty = action_nonempty = 0
        for action in actions:
            for source in action.get("sources", []) or []:
                if not isinstance(source, Mapping):
                    continue
                url = _valid_url(source.get("url"))
                if not url:
                    continue
                title = _title(source.get("title"))
                action_count += 1
                action_empty += int(not title)
                action_nonempty += int(bool(title))
                action_by_url.setdefault(url, set()).add(title)
        citation_count = citation_empty = citation_nonempty = 0
        for annotation in annotations:
            if (
                not isinstance(annotation, Mapping)
                or annotation.get("type") != "url_citation"
            ):
                continue
            url = _valid_url(annotation.get("url"))
            if not url:
                continue
            title = _title(annotation.get("title"))
            citation_count += 1
            citation_empty += int(not title)
            citation_nonempty += int(bool(title))
            citation_by_url.setdefault(url, set()).add(title)
        shared = set(action_by_url) & set(citation_by_url)
        action_empty_citation_nonempty = 0
        action_nonempty_citation_empty = 0
        both_nonempty_equal = 0
        both_nonempty_conflicting = 0
        for url in shared:
            action_titles = action_by_url[url]
            citation_titles = citation_by_url[url]
            action_values = {item for item in action_titles if item}
            citation_values = {item for item in citation_titles if item}
            action_empty_citation_nonempty += int(
                not action_values and bool(citation_values)
            )
            action_nonempty_citation_empty += int(
                bool(action_values) and not citation_values
            )
            if action_values and citation_values:
                if action_values & citation_values:
                    both_nonempty_equal += 1
                else:
                    both_nonempty_conflicting += 1
        with self._lock:
            self._stats["provider_response_count"] += 1
            self._stats["action_source_count"] += action_count
            self._stats["action_source_empty_title_count"] += action_empty
            self._stats["action_source_nonempty_title_count"] += action_nonempty
            self._stats["query_local_citation_count"] += citation_count
            self._stats["query_local_citation_empty_title_count"] += citation_empty
            self._stats["query_local_citation_nonempty_title_count"] += citation_nonempty
            self._stats["same_url_action_and_citation_count"] += len(shared)
            self._stats[
                "same_url_action_empty_citation_nonempty_count"
            ] += action_empty_citation_nonempty
            self._stats[
                "same_url_action_nonempty_citation_empty_count"
            ] += action_nonempty_citation_empty
            self._stats[
                "same_url_both_nonempty_equal_title_count"
            ] += both_nonempty_equal
            self._stats[
                "same_url_both_nonempty_conflicting_title_count"
            ] += both_nonempty_conflicting

    @staticmethod
    def _effective_fetch_inputs(
        requests: Sequence[object],
    ) -> dict[str, bool]:
        inputs: dict[str, bool] = {}
        for item in requests:
            if not isinstance(item, dict):
                continue
            url = _valid_url(item.get("url"))
            if not url or url in inputs:
                continue
            inputs[url] = bool(_title(item.get("title")))
        return inputs

    def _observe_fetch(
        self,
        requests: Sequence[object],
        batches: object,
    ) -> None:
        inputs = self._effective_fetch_inputs(requests)
        result_count = result_empty = result_nonempty = usable = 0
        empty_to_nonempty = nonempty_to_nonempty = 0
        values = (
            batches
            if isinstance(batches, Sequence) and not isinstance(batches, (str, bytes))
            else []
        )
        for batch in values:
            if not isinstance(batch, Mapping):
                continue
            for result in batch.get("results", []) or []:
                if not isinstance(result, Mapping):
                    continue
                result_count += 1
                title = _title(result.get("title"))
                result_empty += int(not title)
                result_nonempty += int(bool(title))
                usable += int(
                    bool(_title(result.get("raw_content") or result.get("content")))
                )
                requested = _valid_url(
                    result.get("requested_url")
                    or result.get("fetch_url")
                    or result.get("url")
                )
                if title and requested in inputs:
                    if inputs[requested]:
                        nonempty_to_nonempty += 1
                    else:
                        empty_to_nonempty += 1
        request_nonempty = sum(inputs.values())
        with self._lock:
            self._stats["fetch_urls_call_count"] += 1
            self._stats["effective_fetch_request_count"] += len(inputs)
            self._stats["fetch_request_empty_title_count"] += (
                len(inputs) - request_nonempty
            )
            self._stats["fetch_request_nonempty_title_count"] += request_nonempty
            self._stats["fetched_result_count"] += result_count
            self._stats["fetched_result_empty_title_count"] += result_empty
            self._stats["fetched_result_nonempty_title_count"] += result_nonempty
            self._stats["fetched_usable_page_count"] += usable
            self._stats[
                "empty_fetch_request_to_nonempty_result_title_count"
            ] += empty_to_nonempty
            self._stats[
                "nonempty_fetch_request_to_nonempty_result_title_count"
            ] += nonempty_to_nonempty

    def __enter__(self) -> "ContentFreeTitleProvenanceObserver":
        if self._active or not _BINDING_GUARD.acquire(blocking=False):
            raise RuntimeError("V2.46.06 title provenance observer is already active")
        self._acquired = True
        if (
            transport.HardTotalWallNativeSearchClient._request is not ORIGINAL_REQUEST
            or native.AzureNativeSearchClient.fetch_urls is not ORIGINAL_FETCH_URLS
        ):
            _BINDING_GUARD.release()
            self._acquired = False
            raise RuntimeError("V2.46.06 frozen transport binding drifted")

        observer = self

        def request(instance: Any, queries: list[str]) -> dict[str, Any]:
            payload = ORIGINAL_REQUEST(instance, queries)
            observer._observe_payload(payload)
            return payload

        def fetch_urls(instance: Any, requests: Any) -> Any:
            values = list(requests)
            batches = ORIGINAL_FETCH_URLS(instance, values)
            observer._observe_fetch(values, batches)
            return batches

        self._request_replacement = request
        self._fetch_replacement = fetch_urls
        transport.HardTotalWallNativeSearchClient._request = request
        native.AzureNativeSearchClient.fetch_urls = fetch_urls
        self._active = True
        return self

    def __exit__(self, *_: object) -> None:
        drifted = False
        try:
            if self._active:
                drifted = (
                    transport.HardTotalWallNativeSearchClient._request
                    is not self._request_replacement
                    or native.AzureNativeSearchClient.fetch_urls
                    is not self._fetch_replacement
                )
                transport.HardTotalWallNativeSearchClient._request = ORIGINAL_REQUEST
                native.AzureNativeSearchClient.fetch_urls = ORIGINAL_FETCH_URLS
                self._request_replacement = None
                self._fetch_replacement = None
                self._active = False
        finally:
            if self._acquired:
                self._acquired = False
                _BINDING_GUARD.release()
        if drifted:
            raise RuntimeError("V2.46.06 installed transport binding drifted")

    def content_free_receipt(self) -> dict[str, Any]:
        value = {
            "policy_id": POLICY_ID,
            "binding_count": EXPECTED_BINDING_COUNT,
            **copy.deepcopy(self._stats),
            "provider_payload_and_fetch_batches_returned_exactly": True,
            "successful_provider_payload_observed_once_after_frozen_request": True,
            "fetch_input_observed_before_and_output_after_frozen_fetch_urls": True,
            "same_url_alignment_uses_canonical_url_in_memory_only": True,
            "raw_task_question_query_url_title_page_prediction_or_credential_emitted": False,
            "query_search_fetch_model_process_or_evaluator_effect_added": False,
            "ranking_validator_evidence_posterior_entropy_or_credit_changed": False,
            "cache_or_cross_task_state_used": False,
            "bindings_restored": not self._active and not self._acquired,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    for name in COUNT_FIELDS:
        _count(copied.get(name), name)
    true_fields = (
        "provider_payload_and_fetch_batches_returned_exactly",
        "successful_provider_payload_observed_once_after_frozen_request",
        "fetch_input_observed_before_and_output_after_frozen_fetch_urls",
        "same_url_alignment_uses_canonical_url_in_memory_only",
        "bindings_restored",
    )
    false_fields = (
        "raw_task_question_query_url_title_page_prediction_or_credential_emitted",
        "query_search_fetch_model_process_or_evaluator_effect_added",
        "ranking_validator_evidence_posterior_entropy_or_credit_changed",
        "cache_or_cross_task_state_used",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or copied["action_source_empty_title_count"]
        + copied["action_source_nonempty_title_count"]
        != copied["action_source_count"]
        or copied["query_local_citation_empty_title_count"]
        + copied["query_local_citation_nonempty_title_count"]
        != copied["query_local_citation_count"]
        or copied["fetch_request_empty_title_count"]
        + copied["fetch_request_nonempty_title_count"]
        != copied["effective_fetch_request_count"]
        or copied["fetched_result_empty_title_count"]
        + copied["fetched_result_nonempty_title_count"]
        != copied["fetched_result_count"]
        or copied["fetched_usable_page_count"] > copied["fetched_result_count"]
        or copied["same_url_action_and_citation_count"]
        > min(copied["action_source_count"], copied["query_local_citation_count"])
        or any(
            copied[name] > copied["same_url_action_and_citation_count"]
            for name in (
                "same_url_action_empty_citation_nonempty_count",
                "same_url_action_nonempty_citation_empty_count",
                "same_url_both_nonempty_equal_title_count",
                "same_url_both_nonempty_conflicting_title_count",
            )
        )
        or copied["empty_fetch_request_to_nonempty_result_title_count"]
        + copied["nonempty_fetch_request_to_nonempty_result_title_count"]
        > copied["fetched_result_nonempty_title_count"]
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.46.06 title provenance receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS",
    "ContentFreeTitleProvenanceObserver",
    "POLICY_ID",
    "validate_receipt",
]
