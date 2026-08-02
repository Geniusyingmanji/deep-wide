"""Build-only task runtime integrating V2.42.72 two-wave retrieval.

The existing score-first runtime plans once, calls ``search_many`` once, then
calls ``fetch_urls`` before synthesis.  ``TwoWaveCachingSearchClient`` uses that
unchanged interface while moving the real public-page fetches into the first
call so the entropy/VOC controller can observe first-wave evidence yield.  The
second call serves only the already fetched pages from an in-memory cache and
therefore cannot repeat network fetches.

The parent V2.42.68 runtime remains responsible for deterministic table
normalization, total fallback, synthesis/repair, and content-free timing.  This
module only appends the replay-validated two-wave retrieval receipt.  It is a
build-only candidate and grants no benchmark/evaluator/leaderboard authority.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .v24257_score_first_runtime import (
    ScoreFirstLimits,
    extract_visible_columns,
    validate_visible_task,
)
from .v24268_keyless_batched_runtime import (
    POLICY_ID as PARENT_POLICY_ID,
    RESULT_ROLE as PARENT_RESULT_ROLE,
    run_v24268_task,
    validate_v24268_result,
)
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24272_two_wave_retrieval import (
    run_two_wave_retrieval,
    validate_retrieval_receipt,
)


POLICY_ID = "v24273_two_wave_task_runtime_build_only_v1"
RESULT_ROLE = "v24273_two_wave_task_result"
DEFAULT_VISIBLE_COLUMN_PROXY = 3
RETRIEVAL_KEYS = frozenset(
    {
        "status",
        "failure_type",
        "receipt",
        "cache_requested_source_count",
        "cache_returned_page_count",
        "cache_miss_count",
        "observed_inner_fetch_calls",
        "network_fetches_during_cache_serve",
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _page_results(batches: object) -> list[Mapping[str, Any]]:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return []
    values: list[Mapping[str, Any]] = []
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        values.extend(
            result
            for result in (batch.get("results") or [])
            if isinstance(result, Mapping)
        )
    return values


def _cache_leads(batches: object) -> list[dict[str, str]]:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return []
    values: list[dict[str, str]] = []
    seen: set[str] = set()
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        query = str(batch.get("query", ""))
        for result in batch.get("results") or []:
            if not isinstance(result, Mapping):
                continue
            content = str(result.get("raw_content") or result.get("content") or "")
            url = canonicalize_url(
                str(
                    result.get("requested_url")
                    or result.get("fetch_url")
                    or result.get("url")
                    or ""
                )
            )
            if not content or not url or url in seen:
                continue
            seen.add(url)
            values.append(
                {
                    "url": url,
                    "query": query,
                    "title": str(result.get("title", ""))[:500],
                    "member_label": "",
                }
            )
    return values


class TwoWaveCachingSearchClient:
    """One-shot retrieval adapter whose second API call is cache-only."""

    def __init__(
        self,
        inner: Any,
        *,
        required_column_count: int,
        explicit_row_target: int = 0,
        policy: TwoWavePolicy | None = None,
        monotonic: Any = None,
    ) -> None:
        if (
            isinstance(required_column_count, bool)
            or not isinstance(required_column_count, int)
            or required_column_count <= 0
            or isinstance(explicit_row_target, bool)
            or not isinstance(explicit_row_target, int)
            or explicit_row_target < 0
        ):
            raise ValueError("V2.42.73 visible complexity proxy is invalid")
        self.inner = inner
        self.required_column_count = required_column_count
        self.explicit_row_target = explicit_row_target
        self.policy = policy or TwoWavePolicy()
        self.policy.validate()
        self.monotonic = monotonic
        self.search_invocations = 0
        self.cache_serve_invocations = 0
        self.cache_requested_source_count = 0
        self.cache_returned_page_count = 0
        self.cache_miss_count = 0
        self.network_fetches_before_cache_serve = 0
        self.network_fetches_after_cache_serve = 0
        self.initial_inner_fetch_calls = int(
            getattr(self.inner, "fetch_calls", 0) or 0
        )
        self.failure_type: str | None = None
        self._receipt: dict[str, Any] | None = None
        self._search_batches: list[dict[str, Any]] = []
        self._page_cache: dict[str, dict[str, Any]] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        if self.search_invocations:
            raise RuntimeError("V2.42.73 retrieval search may execute only once")
        max_results = kwargs.get("max_results")
        if isinstance(max_results, bool) or not isinstance(max_results, int):
            raise ValueError("V2.42.73 per-query result cap is absent")
        retrieval_kwargs: dict[str, Any] = {
            "search": self.inner,
            "required_column_count": self.required_column_count,
            "explicit_row_target": self.explicit_row_target,
            "search_results_per_query": max_results,
            "policy": self.policy,
        }
        if self.monotonic is not None:
            retrieval_kwargs["monotonic"] = self.monotonic
        self.search_invocations += 1
        try:
            value = run_two_wave_retrieval(list(queries), **retrieval_kwargs)
        except BaseException as exc:
            # Persist only the exception class. The unchanged parent records a
            # content-free retrieval failure and can still synthesize/fallback.
            self.failure_type = type(exc).__name__
            self.network_fetches_before_cache_serve = max(
                0,
                int(getattr(self.inner, "fetch_calls", 0) or 0)
                - self.initial_inner_fetch_calls,
            )
            self.network_fetches_after_cache_serve = (
                self.network_fetches_before_cache_serve
            )
            raise
        self._receipt = copy.deepcopy(value["receipt"])
        # Expose exactly the successfully fetched pages. Returning raw
        # discovery batches could include an unfetched tail candidate, a
        # failed fetch, or a cross-wave duplicate. Real attempts stay recorded
        # in the nested receipt and provider counters; the unchanged parent
        # requests only cache hits for active evidence projection.
        self._search_batches = [
            {
                "query": "two-wave fetched-page cache",
                "answer": "",
                "results": _cache_leads(value["page_batches"]),
                "error": None,
                "provider": "v24273-two-wave-fetched-leads",
            }
        ]
        for result in _page_results(value["page_batches"]):
            content = str(result.get("raw_content") or result.get("content") or "")
            aliases = {
                canonicalize_url(str(result.get(name, "")))
                for name in ("requested_url", "fetch_url", "url")
            }
            for alias in aliases - {""}:
                if content and alias not in self._page_cache:
                    self._page_cache[alias] = copy.deepcopy(dict(result))
        self.network_fetches_before_cache_serve = max(
            0,
            int(getattr(self.inner, "fetch_calls", 0) or 0)
            - self.initial_inner_fetch_calls,
        )
        return copy.deepcopy(self._search_batches)

    def fetch_urls(
        self, requests_: Sequence[dict[str, str]]
    ) -> list[dict[str, Any]]:
        if self.search_invocations != 1 or self._receipt is None:
            raise RuntimeError("V2.42.73 cache serve preceded retrieval")
        if self.cache_serve_invocations:
            raise RuntimeError("V2.42.73 cache may be served only once")
        values = list(requests_)
        self.cache_serve_invocations += 1
        self.cache_requested_source_count = len(values)
        batches: list[dict[str, Any]] = []
        for item in values:
            url = canonicalize_url(str(item.get("url", "")))
            cached = self._page_cache.get(url)
            if cached is None:
                self.cache_miss_count += 1
                batches.append(
                    {
                        "query": str(item.get("query", "")),
                        "answer": "",
                        "results": [],
                        "error": "cache_miss",
                        "provider": "v24273-two-wave-page-cache",
                    }
                )
                continue
            self.cache_returned_page_count += 1
            batches.append(
                {
                    "query": str(item.get("query", "")),
                    "answer": "",
                    "results": [copy.deepcopy(cached)],
                    "error": None,
                    "provider": "v24273-two-wave-page-cache",
                }
            )
        self.network_fetches_after_cache_serve = max(
            0,
            int(getattr(self.inner, "fetch_calls", 0) or 0)
            - self.initial_inner_fetch_calls,
        )
        return batches

    def receipt(self) -> dict[str, Any]:
        observed_inner_fetch_calls = max(
            0,
            int(getattr(self.inner, "fetch_calls", 0) or 0)
            - self.initial_inner_fetch_calls,
        )
        if self._receipt is None:
            if self.failure_type is None:
                raise RuntimeError("V2.42.73 retrieval receipt is not available")
            value = {
                "status": "failed",
                "failure_type": self.failure_type,
                "receipt": None,
                "cache_requested_source_count": 0,
                "cache_returned_page_count": 0,
                "cache_miss_count": 0,
                "observed_inner_fetch_calls": observed_inner_fetch_calls,
                "network_fetches_during_cache_serve": 0,
                "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
                "benchmark_launch_or_evaluator_authorized": False,
            }
            validate_runtime_retrieval(value)
            return value
        value = {
            "status": "completed",
            "failure_type": None,
            "receipt": copy.deepcopy(self._receipt),
            "cache_requested_source_count": self.cache_requested_source_count,
            "cache_returned_page_count": self.cache_returned_page_count,
            "cache_miss_count": self.cache_miss_count,
            "observed_inner_fetch_calls": observed_inner_fetch_calls,
            "network_fetches_during_cache_serve": max(
                0,
                self.network_fetches_after_cache_serve
                - self.network_fetches_before_cache_serve,
            ),
            "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        validate_runtime_retrieval(value)
        return value


def validate_runtime_retrieval(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RETRIEVAL_KEYS
        or value.get("status") not in {"completed", "failed"}
        or value.get(
            "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.42.73 retrieval integration receipt drifted")
    receipt = value.get("receipt")
    numeric = RETRIEVAL_KEYS - {
        "status",
        "failure_type",
        "receipt",
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    for name in numeric:
        number = value.get(name)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError("V2.42.73 cache accounting is invalid")
    if value["status"] == "failed":
        failure_type = value.get("failure_type")
        if (
            value.get("receipt") is not None
            or not isinstance(failure_type, str)
            or not failure_type
            or len(failure_type) > 128
            or any(
                value[name]
                for name in (
                    "cache_requested_source_count",
                    "cache_returned_page_count",
                    "cache_miss_count",
                    "network_fetches_during_cache_serve",
                )
            )
        ):
            raise ValueError("V2.42.73 failed retrieval receipt drifted")
        return
    if value.get("failure_type") is not None:
        raise ValueError("V2.42.73 completed retrieval retained a failure")
    if not isinstance(receipt, Mapping):
        raise ValueError("V2.42.73 nested retrieval receipt is absent")
    validate_retrieval_receipt(receipt)
    total = receipt["total"]
    if (
        value["cache_requested_source_count"] != total["usable_pages"]
        or value["cache_returned_page_count"] != total["usable_pages"]
        or value["cache_miss_count"] != 0
        or value["observed_inner_fetch_calls"] != total["fetches_attempted"]
        or value["network_fetches_during_cache_serve"] != 0
    ):
        raise ValueError("V2.42.73 cache/effect accounting drifted")


def run_v24273_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    policy: TwoWavePolicy | None = None,
    monotonic: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    chosen_limits = limits or ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )
    chosen_limits.validate()
    if chosen_limits.search_queries > 4 or chosen_limits.fetch_targets > 10:
        raise ValueError("V2.42.73 build-only retrieval envelope exceeded")
    columns = extract_visible_columns(visible["question"])
    proxy = TwoWaveCachingSearchClient(
        search,
        required_column_count=len(columns) or DEFAULT_VISIBLE_COLUMN_PROXY,
        policy=policy,
        monotonic=monotonic,
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "search": proxy,
        "limits": chosen_limits,
        "progress": progress,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent = run_v24268_task(visible, **kwargs)
    if proxy.failure_type == "KeyboardInterrupt":
        raise KeyboardInterrupt
    if proxy.failure_type == "SystemExit":
        raise SystemExit
    if proxy.failure_type == "GeneratorExit":
        raise GeneratorExit
    result = dict(parent)
    result["role"] = RESULT_ROLE
    result["policy_id"] = POLICY_ID
    result["two_wave_retrieval"] = proxy.receipt()
    validate_v24273_result(result)
    return result


def validate_v24273_result(value: Mapping[str, Any]) -> None:
    if value.get("role") != RESULT_ROLE or value.get("policy_id") != POLICY_ID:
        raise ValueError("V2.42.73 result identity drifted")
    retrieval = value.get("two_wave_retrieval")
    if not isinstance(retrieval, Mapping):
        raise ValueError("V2.42.73 retrieval integration is absent")
    validate_runtime_retrieval(retrieval)
    parent = dict(value)
    parent.pop("two_wave_retrieval", None)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    validate_v24268_result(parent)
    limits = ScoreFirstLimits(**dict(parent["budget"]["limits"]))
    if limits.search_queries > 4 or limits.fetch_targets > 10:
        raise ValueError("V2.42.73 parent budget exceeded build-only envelope")
    if retrieval["status"] == "failed":
        if (
            parent["budget"]["admitted_fetch_targets"] != 0
            or parent["evidence"]["fetch_target_count"] != 0
            or retrieval["observed_inner_fetch_calls"]
            != parent["cost"]["search"]["fetch_calls"]
        ):
            raise ValueError("V2.42.73 failed retrieval effect accounting drifted")
        return
    total = retrieval["receipt"]["total"]
    if (
        total["queries_executed"] > parent["budget"]["admitted_search_queries"]
        or total["usable_pages"]
        != parent["budget"]["admitted_fetch_targets"]
        or parent["evidence"]["fetch_target_count"] != total["usable_pages"]
        or parent["cost"]["search"]["fetch_calls"] != total["fetches_attempted"]
    ):
        raise ValueError("V2.42.73 parent/two-wave effect accounting drifted")


__all__ = [
    "POLICY_ID",
    "RESULT_ROLE",
    "TwoWaveCachingSearchClient",
    "run_v24273_task",
    "validate_runtime_retrieval",
    "validate_v24273_result",
]
