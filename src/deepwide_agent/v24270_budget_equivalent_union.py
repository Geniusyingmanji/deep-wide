"""Budget-equivalent cap for task-local hosted-search discovery leads."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits
from .v24268_keyless_batched_runtime import run_v24268_task
from .v24269_task_union_discovery import (
    POLICY_ID as PARENT_POLICY_ID,
    RESULT_ROLE as PARENT_RESULT_ROLE,
    TaskUnionDiscoverySearchClient,
    validate_v24269_result,
)


POLICY_ID = "v24270_budget_equivalent_task_union_v1"
RESULT_ROLE = "v24270_budget_equivalent_task_result"
SELECTION_POLICY = "stable_first_seen_without_content_or_score_ranking"
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "search_invocations",
        "logical_query_count",
        "search_results_per_query",
        "declared_query_result_capacity",
        "global_fetch_cap",
        "pre_cap_source_count",
        "post_cap_source_count",
        "truncated_source_count",
        "remaining_global_fetch_capacity",
        "selection_policy",
        "parent_discovery_receipt_sha256",
        "content_score_url_host_or_benchmark_metadata_used_for_selection",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


class BudgetEquivalentTaskUnionSearchClient:
    """Cap task-union leads by the original query-count times top-k budget."""

    def __init__(
        self,
        inner: Any,
        *,
        search_results_per_query: int,
        global_fetch_cap: int,
    ) -> None:
        if (
            isinstance(search_results_per_query, bool)
            or not isinstance(search_results_per_query, int)
            or search_results_per_query <= 0
            or isinstance(global_fetch_cap, bool)
            or not isinstance(global_fetch_cap, int)
            or global_fetch_cap <= 0
        ):
            raise ValueError("V2.42.70 cap configuration is invalid")
        self.parent = TaskUnionDiscoverySearchClient(inner)
        self.search_results_per_query = search_results_per_query
        self.global_fetch_cap = global_fetch_cap
        self.search_invocations = 0
        self.logical_query_count = 0
        self.declared_query_result_capacity = 0
        self.pre_cap_source_count = 0
        self.post_cap_source_count = 0
        self.truncated_source_count = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.parent, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        values = list(queries)
        max_results = kwargs.get("max_results")
        if max_results != self.search_results_per_query:
            raise ValueError("V2.42.70 per-query result cap drifted")
        batches = self.parent.search_many(values, **kwargs)
        candidates: list[dict[str, Any]] = []
        for batch in batches:
            if not isinstance(batch, Mapping):
                continue
            for result in batch.get("results") or []:
                if isinstance(result, Mapping):
                    candidates.append(dict(result))
        remaining = max(0, self.global_fetch_cap - self.post_cap_source_count)
        query_capacity = len(values) * self.search_results_per_query
        admitted = min(len(candidates), query_capacity, remaining)
        selected = candidates[:admitted]
        self.search_invocations += 1
        self.logical_query_count += len(values)
        self.declared_query_result_capacity += query_capacity
        self.pre_cap_source_count += len(candidates)
        self.post_cap_source_count += len(selected)
        self.truncated_source_count += len(candidates) - len(selected)
        if not selected:
            return []
        return [
            {
                "query": "budget-equivalent task-local discovery union",
                "answer": "",
                "results": selected,
                "error": None,
                "provider": "azure-responses-budget-equivalent-task-union",
            }
        ]

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        return self.parent.fetch_urls(requests_)

    def receipt(self) -> dict[str, Any]:
        parent_receipt = self.parent.receipt()
        value = {
            "artifact_version": 1,
            "role": "v24270_budget_equivalent_union_receipt",
            "search_invocations": self.search_invocations,
            "logical_query_count": self.logical_query_count,
            "search_results_per_query": self.search_results_per_query,
            "declared_query_result_capacity": self.declared_query_result_capacity,
            "global_fetch_cap": self.global_fetch_cap,
            "pre_cap_source_count": self.pre_cap_source_count,
            "post_cap_source_count": self.post_cap_source_count,
            "truncated_source_count": self.truncated_source_count,
            "remaining_global_fetch_capacity": max(
                0, self.global_fetch_cap - self.post_cap_source_count
            ),
            "selection_policy": SELECTION_POLICY,
            "parent_discovery_receipt_sha256": payload_sha256(parent_receipt),
            "content_score_url_host_or_benchmark_metadata_used_for_selection": False,
            "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        validate_receipt(value)
        return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.70 {label} is not a nonnegative integer")
    return value


def validate_receipt(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24270_budget_equivalent_union_receipt"
        or value.get("selection_policy") != SELECTION_POLICY
        or value.get(
            "content_score_url_host_or_benchmark_metadata_used_for_selection"
        )
        is not False
        or value.get(
            "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise ValueError("V2.42.70 cap receipt drifted")
    numeric = RECEIPT_KEYS - {
        "role",
        "selection_policy",
        "parent_discovery_receipt_sha256",
        "content_score_url_host_or_benchmark_metadata_used_for_selection",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
    for key in numeric:
        _nonnegative_integer(value.get(key), key)
    digest = value.get("parent_discovery_receipt_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError("V2.42.70 parent receipt hash drifted")
    if value["search_results_per_query"] <= 0 or value["global_fetch_cap"] <= 0:
        raise ValueError("V2.42.70 positive cap drifted")
    if (
        value["declared_query_result_capacity"]
        != value["logical_query_count"] * value["search_results_per_query"]
        or value["truncated_source_count"]
        != value["pre_cap_source_count"] - value["post_cap_source_count"]
        or value["post_cap_source_count"] > value["pre_cap_source_count"]
        or value["post_cap_source_count"] > value["declared_query_result_capacity"]
        or value["post_cap_source_count"] > value["global_fetch_cap"]
        or value["remaining_global_fetch_capacity"]
        != value["global_fetch_cap"] - value["post_cap_source_count"]
    ):
        raise ValueError("V2.42.70 cap accounting drifted")


def run_v24270_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    monotonic: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    policy = limits or ScoreFirstLimits()
    policy.validate()
    capped = BudgetEquivalentTaskUnionSearchClient(
        search,
        search_results_per_query=policy.search_results_per_query,
        global_fetch_cap=policy.fetch_targets,
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "search": capped,
        "limits": policy,
        "progress": progress,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    base = run_v24268_task(task, **kwargs)
    parent = dict(base)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    parent["discovery_union"] = capped.parent.receipt()
    validate_v24269_result(parent)
    result = dict(parent)
    result["role"] = RESULT_ROLE
    result["policy_id"] = POLICY_ID
    result["budget_equivalence"] = capped.receipt()
    validate_v24270_result(result)
    return result


def validate_v24270_result(value: Mapping[str, Any]) -> None:
    if value.get("role") != RESULT_ROLE or value.get("policy_id") != POLICY_ID:
        raise ValueError("V2.42.70 result identity drifted")
    cap = value.get("budget_equivalence")
    discovery = value.get("discovery_union")
    if not isinstance(cap, Mapping) or not isinstance(discovery, Mapping):
        raise ValueError("V2.42.70 receipts are absent")
    validate_receipt(cap)
    if cap["parent_discovery_receipt_sha256"] != payload_sha256(discovery):
        raise ValueError("V2.42.70 parent receipt binding drifted")
    if discovery.get("fetch_requested_source_count", 0) > cap["post_cap_source_count"]:
        raise ValueError("V2.42.70 fetch exceeded capped union")
    parent = dict(value)
    parent.pop("budget_equivalence", None)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    validate_v24269_result(parent)


__all__ = [
    "BudgetEquivalentTaskUnionSearchClient",
    "POLICY_ID",
    "RESULT_ROLE",
    "run_v24270_task",
    "validate_receipt",
    "validate_v24270_result",
]
