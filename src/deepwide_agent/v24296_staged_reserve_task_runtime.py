"""Total label-blind task runtime for V2.42.94 staged reserve retrieval.

The runtime boundary is exactly ``{opaque_id, question}``.  It composes the
audited visible-schema wrapper, the 6+2+2 retrieval schedule, cache-only
evidence delivery, additive timing, and a total fallback boundary.  Persisted
receipts contain counts and decisions only; no question, query, URL, host,
page, prediction, benchmark label, evaluator field, or credential is emitted.

This module is build-only and authorizes no benchmark or evaluator call.
"""

from __future__ import annotations

import copy
import hashlib
import math
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from .v24257_score_first_runtime import (
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import validate_v24259_result
from .v24267_total_fallback import build_total_fallback_result
from .v24268_keyless_batched_runtime import (
    POLICY_ID as PARENT_POLICY_ID,
    RESULT_ROLE as PARENT_RESULT_ROLE,
    run_v24268_task,
    validate_v24268_result,
)
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24273_two_wave_task_runtime import DEFAULT_VISIBLE_COLUMN_PROXY
from .v24286_visible_schema_runtime import (
    TIMING_ROLE,
    VisibleSchemaModel,
    _schema_receipt,
    _schema_safe_question,
    extract_robust_visible_columns,
    validate_schema_receipt,
    validate_timing_receipt,
)
from .v24290_low_coverage_task_runtime import _cache_leads, _page_results
from .v24294_staged_reserve import (
    StagedReservePolicy,
    run_staged_reserve,
    validate_receipt as validate_staged_receipt,
)


POLICY_ID = "v24296_label_blind_visible_schema_staged_reserve_total_v1"
RESULT_ROLE = "v24296_staged_reserve_task_result"
TOTAL_POLICY_ID = "v24296_total_staged_reserve_task_boundary_v1"
MODEL_COUNTERS = ("requests", "attempts", "input_tokens", "output_tokens", "total_tokens")
SEARCH_COUNTERS = (
    "calls", "failures", "tool_calls", "fetch_calls", "fetch_failures",
    "input_tokens", "output_tokens", "total_tokens",
)
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


class StagedReserveCachingSearchClient:
    """Run V2.42.94 once, then expose only its fetched pages from memory."""

    def __init__(
        self,
        inner: Any,
        *,
        required_column_count: int,
        explicit_row_target: int = 0,
        two_wave_policy: TwoWavePolicy | None = None,
        reserve_policy: StagedReservePolicy | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        if (
            isinstance(required_column_count, bool)
            or not isinstance(required_column_count, int)
            or required_column_count <= 0
            or isinstance(explicit_row_target, bool)
            or not isinstance(explicit_row_target, int)
            or explicit_row_target < 0
        ):
            raise ValueError("V2.42.96 visible complexity proxy is invalid")
        self.inner = inner
        self.required_column_count = required_column_count
        self.explicit_row_target = explicit_row_target
        self.two_wave_policy = two_wave_policy or TwoWavePolicy()
        self.reserve_policy = reserve_policy or StagedReservePolicy()
        self.two_wave_policy.validate()
        self.reserve_policy.validate()
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
            raise RuntimeError("V2.42.96 retrieval search may execute only once")
        max_results = kwargs.get("max_results")
        if isinstance(max_results, bool) or not isinstance(max_results, int):
            raise ValueError("V2.42.96 per-query result cap is absent")
        call: dict[str, Any] = {
            "search": self.inner,
            "required_column_count": self.required_column_count,
            "explicit_row_target": self.explicit_row_target,
            "search_results_per_query": max_results,
            "two_wave_policy": self.two_wave_policy,
            "reserve_policy": self.reserve_policy,
        }
        if self.monotonic is not None:
            call["monotonic"] = self.monotonic
        self.search_invocations += 1
        try:
            value = run_staged_reserve(list(queries), **call)
        except BaseException as exc:
            self.failure_type = type(exc).__name__
            observed = max(
                0,
                int(getattr(self.inner, "fetch_calls", 0) or 0)
                - self.initial_inner_fetch_calls,
            )
            self.network_fetches_before_cache_serve = observed
            self.network_fetches_after_cache_serve = observed
            raise
        self._receipt = copy.deepcopy(value["receipt"])
        leads = _cache_leads(value["page_batches"])
        self._search_batches = (
            [
                {
                    "query": "staged-reserve fetched-page cache",
                    "answer": "",
                    "results": leads,
                    "error": None,
                    "provider": "v24296-staged-reserve-fetched-leads",
                }
            ]
            if leads
            else []
        )
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
            raise RuntimeError("V2.42.96 cache serve preceded retrieval")
        if self.cache_serve_invocations:
            raise RuntimeError("V2.42.96 cache may be served only once")
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
                        "provider": "v24296-staged-reserve-page-cache",
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
                    "provider": "v24296-staged-reserve-page-cache",
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
                raise RuntimeError("V2.42.96 retrieval receipt is unavailable")
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
        raise ValueError("V2.42.96 retrieval integration identity drifted")
    for name in (
        "cache_requested_source_count",
        "cache_returned_page_count",
        "cache_miss_count",
        "observed_inner_fetch_calls",
        "network_fetches_during_cache_serve",
    ):
        number = value.get(name)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError("V2.42.96 retrieval integration count is invalid")
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
            raise ValueError("V2.42.96 failed retrieval receipt drifted")
        return
    receipt = value.get("receipt")
    if value.get("failure_type") is not None or not isinstance(receipt, Mapping):
        raise ValueError("V2.42.96 completed retrieval receipt is absent")
    validate_staged_receipt(receipt)
    total = receipt["total"]
    if (
        value["cache_requested_source_count"] != total["usable_pages"]
        or value["cache_returned_page_count"] != total["usable_pages"]
        or value["cache_miss_count"] != 0
        or value["observed_inner_fetch_calls"] != total["fetches_attempted"]
        or value["network_fetches_during_cache_serve"] != 0
    ):
        raise ValueError("V2.42.96 retrieval cache/effect accounting drifted")


def _timing_receipt(parent: Mapping[str, Any]) -> dict[str, Any]:
    telemetry = parent["telemetry"]
    model_events = telemetry["model_events"]
    search_events = telemetry["search_events"]
    model_by_stage = {
        stage: round(
            sum(
                float(event["elapsed_seconds"])
                for event in model_events
                if event["stage"] == stage
            ),
            6,
        )
        for stage in ("plan", "synthesis", "repair")
    }
    retrieval_envelope = round(
        sum(
            float(event["elapsed_seconds"])
            for event in search_events
            if event["stage"] == "search"
        ),
        6,
    )
    cache_serve = round(
        sum(
            float(event["elapsed_seconds"])
            for event in search_events
            if event["stage"] == "fetch"
        ),
        6,
    )
    retrieval = parent["staged_reserve_retrieval"]
    if retrieval["status"] == "completed":
        total = retrieval["receipt"]["total"]
        provider_search = round(float(total["search_seconds"]), 6)
        network_fetch = round(float(total["fetch_seconds"]), 6)
        status = "complete"
    else:
        provider_search = 0.0
        network_fetch = 0.0
        status = "retrieval_failed_coarse_only"
    adapter = round(
        max(0.0, retrieval_envelope - provider_search - network_fetch), 6
    )
    instrumented = round(float(telemetry["instrumented_seconds"]), 6)
    task_wall = round(float(parent["budget"]["elapsed_seconds"]), 6)
    value = {
        "artifact_version": 1,
        "role": TIMING_ROLE,
        "status": status,
        "model_seconds": model_by_stage,
        "provider_search_seconds": provider_search,
        "network_fetch_seconds": network_fetch,
        "controller_and_adapter_seconds": adapter,
        "cache_serve_seconds": cache_serve,
        "retrieval_envelope_seconds": retrieval_envelope,
        "instrumented_seconds": instrumented,
        "task_wall_seconds": task_wall,
        "unattributed_runtime_seconds": round(max(0.0, task_wall - instrumented), 6),
        "timings_are_additive_not_parallel_work_sum": True,
        "question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    validate_timing_receipt(value)
    return value


def run_v24296_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    two_wave_policy: TwoWavePolicy | None = None,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Callable[[], float] | None = None,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
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
        raise ValueError("V2.42.96 retrieval envelope exceeded")
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
        schema_model = VisibleSchemaModel(
            model, columns=columns, question=visible["question"]
        )
        forward_model = schema_model
    proxy = StagedReserveCachingSearchClient(
        search,
        required_column_count=len(columns) or DEFAULT_VISIBLE_COLUMN_PROXY,
        two_wave_policy=two_wave_policy,
        reserve_policy=reserve_policy,
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
    result["staged_reserve_retrieval"] = proxy.receipt()
    result["visible_schema"] = _schema_receipt(
        columns=columns,
        applied=applied,
        events=schema_model.events if schema_model is not None else [],
    )
    result["attributed_timing"] = _timing_receipt(result)
    result["prediction_sha256"] = hashlib.sha256(
        str(result["prediction"]).encode("utf-8")
    ).hexdigest()
    validate_v24296_result(result)
    return result


def validate_v24296_result(value: Mapping[str, Any]) -> None:
    if value.get("role") != RESULT_ROLE or value.get("policy_id") != POLICY_ID:
        raise ValueError("V2.42.96 result identity drifted")
    retrieval = value.get("staged_reserve_retrieval")
    schema = value.get("visible_schema")
    timing = value.get("attributed_timing")
    if not isinstance(retrieval, Mapping) or not isinstance(schema, Mapping) or not isinstance(timing, Mapping):
        raise ValueError("V2.42.96 result receipts are absent")
    validate_runtime_retrieval(retrieval)
    validate_schema_receipt(schema)
    validate_timing_receipt(timing)
    parent = copy.deepcopy(dict(value))
    parent.pop("staged_reserve_retrieval", None)
    parent.pop("visible_schema", None)
    parent.pop("attributed_timing", None)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    validate_v24268_result(parent)
    limits = ScoreFirstLimits(**dict(parent["budget"]["limits"]))
    if limits.search_queries > 4 or limits.fetch_targets > 10:
        raise ValueError("V2.42.96 parent budget exceeded")
    if schema["status"] == "applied" and schema["column_count"] != len(parent["columns"]):
        raise ValueError("V2.42.96 visible schema did not reach the result")
    if not math.isclose(
        float(timing["task_wall_seconds"]),
        float(parent["budget"]["elapsed_seconds"]),
        abs_tol=1e-6,
    ):
        raise ValueError("V2.42.96 timing is not bound to the task")
    if retrieval["status"] == "failed":
        if parent["budget"]["admitted_fetch_targets"] != 0 or parent["evidence"]["fetch_target_count"] != 0:
            raise ValueError("V2.42.96 failed retrieval retained evidence")
        return
    total = retrieval["receipt"]["total"]
    if (
        total["queries_executed"] > parent["budget"]["admitted_search_queries"]
        or total["usable_pages"] != parent["budget"]["admitted_fetch_targets"]
        or total["usable_pages"] != parent["evidence"]["fetch_target_count"]
        or total["fetches_attempted"] != parent["cost"]["search"]["fetch_calls"]
    ):
        raise ValueError("V2.42.96 parent/retrieval effect accounting drifted")


def _snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


def validate_v24296_total_result(value: Mapping[str, Any]) -> str:
    try:
        validate_v24296_result(value)
        return "candidate"
    except (KeyError, TypeError, ValueError):
        try:
            validate_v24259_result(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("V2.42.96 result is neither candidate nor fallback") from exc
        if value.get("completion_kind") not in {
            "worker_failure_fallback",
            "hard_deadline_fallback",
        }:
            raise ValueError("V2.42.96 non-candidate result is not a total fallback")
        return "fallback"


def run_v24296_total_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    two_wave_policy: TwoWavePolicy | None = None,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    chosen = limits or ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )
    chosen.validate()
    try:
        started = float(monotonic())
    except BaseException:
        started = 0.0
    model_start = _snapshot(model, MODEL_COUNTERS)
    search_start = _snapshot(search, SEARCH_COUNTERS)
    last_progress: dict[str, Any] = {}

    def capture(value: Mapping[str, Any]) -> None:
        nonlocal last_progress
        last_progress = dict(value)
        if progress is not None:
            progress(value)

    try:
        result = run_v24296_task(
            visible,
            model=model,
            search=search,
            limits=chosen,
            two_wave_policy=two_wave_policy,
            reserve_policy=reserve_policy,
            monotonic=monotonic,
            progress=capture,
        )
        validate_v24296_result(result)
        return result
    except BaseException as exc:
        current = dict(last_progress)
        current["model_cost"] = _counter_delta(
            _snapshot(model, MODEL_COUNTERS), model_start
        )
        current["search_cost"] = _counter_delta(
            _snapshot(search, SEARCH_COUNTERS), search_start
        )
        try:
            elapsed = max(0.0, float(monotonic()) - started)
        except BaseException:
            elapsed = 0.0
        result = build_total_fallback_result(
            visible,
            limits=chosen,
            completion_kind="worker_failure_fallback",
            failure_stage="v24296_runtime_totality",
            failure_type=type(exc).__name__,
            elapsed_seconds=elapsed,
            last_progress=current,
        )
        validate_v24296_total_result(result)
        return result


__all__ = [
    "POLICY_ID",
    "RESULT_ROLE",
    "StagedReserveCachingSearchClient",
    "run_v24296_task",
    "run_v24296_total_task",
    "validate_runtime_retrieval",
    "validate_v24296_result",
    "validate_v24296_total_result",
]
