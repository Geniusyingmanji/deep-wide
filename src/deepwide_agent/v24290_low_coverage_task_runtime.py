"""Label-blind task runtime for bounded low-coverage tail rescue.

This append-only candidate integrates the V2.42.89 retrieval kernel with the
V2.42.86 visible-schema and additive-timing protections.  The visible runtime
boundary remains exactly ``{opaque_id, question}``.  The rescue may fetch a
deterministic tail already returned by the same hosted-search response, but it
cannot issue an additional hosted-search request and remains inside the frozen
four-query / ten-fetch envelope.

The module is build-only.  It does not authorize a benchmark, evaluator,
leaderboard submission, training update, or SOTA claim.
"""

from __future__ import annotations

import copy
import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24268_keyless_batched_runtime import (
    POLICY_ID as PARENT_POLICY_ID,
    RESULT_ROLE as PARENT_RESULT_ROLE,
    run_v24268_task,
    validate_v24268_result,
)
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24273_two_wave_task_runtime import DEFAULT_VISIBLE_COLUMN_PROXY
from .v24286_visible_schema_runtime import (
    VisibleSchemaModel,
    _schema_receipt,
    _schema_safe_question,
    _timing_receipt,
    extract_robust_visible_columns,
    validate_schema_receipt,
    validate_timing_receipt,
)
from .v24289_low_coverage_rescue import (
    RescuePolicy,
    run_low_coverage_rescue,
    validate_receipt as validate_rescue_receipt,
)


POLICY_ID = "v24290_label_blind_visible_schema_low_coverage_rescue_v1"
RESULT_ROLE = "v24290_low_coverage_rescue_task_result"
RUNTIME_RETRIEVAL_KEYS = frozenset(
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
    output: list[Mapping[str, Any]] = []
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        output.extend(
            result
            for result in (batch.get("results") or [])
            if isinstance(result, Mapping)
        )
    return output


def _cache_leads(batches: object) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    seen: set[str] = set()
    for result in _page_results(batches):
        content = str(result.get("raw_content") or result.get("content") or "")
        requested = str(
            result.get("requested_url")
            or result.get("fetch_url")
            or result.get("url")
            or ""
        )
        url = canonicalize_url(requested)
        if not content or not url or url in seen:
            continue
        seen.add(url)
        values.append(
            {
                "url": requested,
                "query": "low-coverage fetched-page cache",
                "title": str(result.get("title", ""))[:500],
                "member_label": "",
            }
        )
    return values


class LowCoverageCachingSearchClient:
    """Execute V2.42.89 once, then serve its usable pages from memory."""

    def __init__(
        self,
        inner: Any,
        *,
        required_column_count: int,
        explicit_row_target: int = 0,
        two_wave_policy: TwoWavePolicy | None = None,
        rescue_policy: RescuePolicy | None = None,
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
            raise ValueError("V2.42.90 visible complexity proxy is invalid")
        self.inner = inner
        self.required_column_count = required_column_count
        self.explicit_row_target = explicit_row_target
        self.two_wave_policy = two_wave_policy or TwoWavePolicy()
        self.rescue_policy = rescue_policy or RescuePolicy()
        self.two_wave_policy.validate()
        self.rescue_policy.validate()
        self.monotonic = monotonic
        self.search_invocations = 0
        self.cache_serve_invocations = 0
        self.cache_requested_source_count = 0
        self.cache_returned_page_count = 0
        self.cache_miss_count = 0
        self.initial_inner_fetch_calls = int(getattr(inner, "fetch_calls", 0) or 0)
        self.network_fetches_before_cache_serve = 0
        self.network_fetches_after_cache_serve = 0
        self.failure_type: str | None = None
        self._receipt: dict[str, Any] | None = None
        self._search_batches: list[dict[str, Any]] = []
        self._page_cache: dict[str, dict[str, Any]] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        if self.search_invocations:
            raise RuntimeError("V2.42.90 retrieval search may execute only once")
        max_results = kwargs.get("max_results")
        if isinstance(max_results, bool) or not isinstance(max_results, int):
            raise ValueError("V2.42.90 per-query result cap is absent")
        call: dict[str, Any] = {
            "search": self.inner,
            "required_column_count": self.required_column_count,
            "explicit_row_target": self.explicit_row_target,
            "search_results_per_query": max_results,
            "two_wave_policy": self.two_wave_policy,
            "rescue_policy": self.rescue_policy,
        }
        if self.monotonic is not None:
            call["monotonic"] = self.monotonic
        self.search_invocations += 1
        try:
            value = run_low_coverage_rescue(list(queries), **call)
        except BaseException as exc:
            self.failure_type = type(exc).__name__
            self.network_fetches_before_cache_serve = max(
                0,
                int(getattr(self.inner, "fetch_calls", 0) or 0)
                - self.initial_inner_fetch_calls,
            )
            self.network_fetches_after_cache_serve = self.network_fetches_before_cache_serve
            raise
        self._receipt = copy.deepcopy(value["receipt"])
        leads = _cache_leads(value["page_batches"])
        self._search_batches = [
            {
                "query": "low-coverage fetched-page cache",
                "answer": "",
                "results": leads,
                "error": None,
                "provider": "v24290-low-coverage-fetched-leads",
            }
        ] if leads else []
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

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
        if self.search_invocations != 1 or self._receipt is None:
            raise RuntimeError("V2.42.90 cache serve preceded retrieval")
        if self.cache_serve_invocations:
            raise RuntimeError("V2.42.90 cache may be served only once")
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
                        "provider": "v24290-low-coverage-page-cache",
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
                    "provider": "v24290-low-coverage-page-cache",
                }
            )
        self.network_fetches_after_cache_serve = max(
            0,
            int(getattr(self.inner, "fetch_calls", 0) or 0)
            - self.initial_inner_fetch_calls,
        )
        return batches

    def receipt(self) -> dict[str, Any]:
        observed = max(
            0,
            int(getattr(self.inner, "fetch_calls", 0) or 0)
            - self.initial_inner_fetch_calls,
        )
        if self._receipt is None:
            if self.failure_type is None:
                raise RuntimeError("V2.42.90 retrieval receipt is unavailable")
            value = {
                "status": "failed",
                "failure_type": self.failure_type,
                "receipt": None,
                "cache_requested_source_count": 0,
                "cache_returned_page_count": 0,
                "cache_miss_count": 0,
                "observed_inner_fetch_calls": observed,
                "network_fetches_during_cache_serve": 0,
                "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
                "benchmark_launch_or_evaluator_authorized": False,
            }
        else:
            value = {
                "status": "completed",
                "failure_type": None,
                "receipt": copy.deepcopy(self._receipt),
                "cache_requested_source_count": self.cache_requested_source_count,
                "cache_returned_page_count": self.cache_returned_page_count,
                "cache_miss_count": self.cache_miss_count,
                "observed_inner_fetch_calls": observed,
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
        set(value) != RUNTIME_RETRIEVAL_KEYS
        or value.get("status") not in {"completed", "failed"}
        or value.get("question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.42.90 retrieval integration identity drifted")
    for name in (
        "cache_requested_source_count",
        "cache_returned_page_count",
        "cache_miss_count",
        "observed_inner_fetch_calls",
        "network_fetches_during_cache_serve",
    ):
        number = value.get(name)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError("V2.42.90 retrieval integration count is invalid")
    if value["status"] == "failed":
        if (
            value.get("receipt") is not None
            or not isinstance(value.get("failure_type"), str)
            or not value["failure_type"]
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
            raise ValueError("V2.42.90 failed retrieval receipt drifted")
        return
    receipt = value.get("receipt")
    if value.get("failure_type") is not None or not isinstance(receipt, Mapping):
        raise ValueError("V2.42.90 completed retrieval receipt is absent")
    validate_rescue_receipt(receipt)
    total = receipt["total"]
    if (
        value["cache_requested_source_count"] != total["usable_pages"]
        or value["cache_returned_page_count"] != total["usable_pages"]
        or value["cache_miss_count"] != 0
        or value["observed_inner_fetch_calls"] != total["fetches_attempted"]
        or value["network_fetches_during_cache_serve"] != 0
    ):
        raise ValueError("V2.42.90 retrieval cache/effect accounting drifted")


def run_v24290_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    two_wave_policy: TwoWavePolicy | None = None,
    rescue_policy: RescuePolicy | None = None,
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
        raise ValueError("V2.42.90 retrieval envelope exceeded")
    columns = extract_robust_visible_columns(visible["question"])
    applied = bool(columns)
    forward_task = visible
    forward_model = model
    schema_model: VisibleSchemaModel | None = None
    if applied:
        forward_task = {
            "opaque_id": visible["opaque_id"],
            "question": _schema_safe_question(visible["question"], columns),
        }
        schema_model = VisibleSchemaModel(model, columns=columns, question=visible["question"])
        forward_model = schema_model
    proxy = LowCoverageCachingSearchClient(
        search,
        required_column_count=len(columns) or DEFAULT_VISIBLE_COLUMN_PROXY,
        two_wave_policy=two_wave_policy,
        rescue_policy=rescue_policy,
        monotonic=monotonic,
    )
    kwargs: dict[str, Any] = {
        "model": forward_model,
        "search": proxy,
        "limits": chosen_limits,
        "progress": progress,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent = run_v24268_task(forward_task, **kwargs)
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
    result["visible_schema"] = _schema_receipt(
        columns=columns,
        applied=applied,
        events=schema_model.events if schema_model is not None else [],
    )
    result["attributed_timing"] = _timing_receipt(result)
    result["prediction_sha256"] = hashlib.sha256(str(result["prediction"]).encode("utf-8")).hexdigest()
    validate_v24290_result(result)
    return result


def validate_v24290_result(value: Mapping[str, Any]) -> None:
    if value.get("role") != RESULT_ROLE or value.get("policy_id") != POLICY_ID:
        raise ValueError("V2.42.90 result identity drifted")
    retrieval = value.get("two_wave_retrieval")
    schema = value.get("visible_schema")
    timing = value.get("attributed_timing")
    if not isinstance(retrieval, Mapping) or not isinstance(schema, Mapping) or not isinstance(timing, Mapping):
        raise ValueError("V2.42.90 result receipts are absent")
    validate_runtime_retrieval(retrieval)
    validate_schema_receipt(schema)
    validate_timing_receipt(timing)
    parent = copy.deepcopy(dict(value))
    parent.pop("two_wave_retrieval", None)
    parent.pop("visible_schema", None)
    parent.pop("attributed_timing", None)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    validate_v24268_result(parent)
    limits = ScoreFirstLimits(**dict(parent["budget"]["limits"]))
    if limits.search_queries > 4 or limits.fetch_targets > 10:
        raise ValueError("V2.42.90 parent budget exceeded")
    if schema["status"] == "applied" and schema["column_count"] != len(parent["columns"]):
        raise ValueError("V2.42.90 visible schema did not reach the result")
    if not math.isclose(float(timing["task_wall_seconds"]), float(parent["budget"]["elapsed_seconds"]), abs_tol=1e-6):
        raise ValueError("V2.42.90 timing is not bound to the task")
    if retrieval["status"] == "failed":
        if parent["budget"]["admitted_fetch_targets"] != 0 or parent["evidence"]["fetch_target_count"] != 0:
            raise ValueError("V2.42.90 failed retrieval retained evidence")
        return
    total = retrieval["receipt"]["total"]
    if (
        total["queries_executed"] > parent["budget"]["admitted_search_queries"]
        or total["usable_pages"] != parent["budget"]["admitted_fetch_targets"]
        or total["usable_pages"] != parent["evidence"]["fetch_target_count"]
        or total["fetches_attempted"] != parent["cost"]["search"]["fetch_calls"]
    ):
        raise ValueError("V2.42.90 parent/retrieval effect accounting drifted")


__all__ = [
    "LowCoverageCachingSearchClient",
    "POLICY_ID",
    "RESULT_ROLE",
    "run_v24290_task",
    "validate_runtime_retrieval",
    "validate_v24290_result",
]
