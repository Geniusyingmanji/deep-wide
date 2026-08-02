"""Keyless batched-search successor with content-free stage telemetry.

V2.42.68 keeps the V2.42.59 planning, query cap, fetch cap, synthesis,
normalization, and repair behavior.  The caller may replace the search
transport, while this module records only aggregate timing and yield counts.
Question text, queries, URLs, hosts, page text, candidates, predictions, and
benchmark metadata are never copied into the telemetry surface.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from .clients import canonicalize_url
from .v24257_score_first_runtime import (
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import (
    POLICY_ID as PARENT_POLICY_ID,
    RESULT_ROLE as PARENT_RESULT_ROLE,
    _split_pipe_row,
    validate_v24259_result,
)
from .v24267_total_fallback import run_total_task


POLICY_ID = "v24268_keyless_batched_search_telemetry_v1"
RESULT_ROLE = "v24268_keyless_batched_task_result"
MODEL_COUNTERS = (
    "requests",
    "attempts",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
SEARCH_COUNTERS = (
    "calls",
    "failures",
    "tool_calls",
    "fetch_calls",
    "fetch_failures",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
MODEL_EVENT_KEYS = frozenset(
    {
        "stage",
        "success",
        "elapsed_seconds",
        "requests_delta",
        "attempts_delta",
        "input_tokens_delta",
        "output_tokens_delta",
        "total_tokens_delta",
    }
)
SEARCH_EVENT_KEYS = frozenset(
    {
        "stage",
        "success",
        "elapsed_seconds",
        "logical_request_count",
        "returned_batch_count",
        "usable_result_count",
        "unique_url_count",
        "unique_host_count",
        "content_char_count",
        "calls_delta",
        "failures_delta",
        "tool_calls_delta",
        "fetch_calls_delta",
        "fetch_failures_delta",
        "input_tokens_delta",
        "output_tokens_delta",
        "total_tokens_delta",
    }
)
TABLE_KEYS = frozenset(
    {
        "row_count",
        "column_count",
        "cell_count",
        "unknown_cell_count",
        "unknown_cell_ratio",
    }
)
TRANSPORT_KEYS = frozenset(
    {
        "provider",
        "batch_size",
        "search_workers",
        "fetch_workers",
        "fetch_timeout_seconds",
        "server_auto_fetch_enabled",
    }
)
TELEMETRY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "model_events",
        "search_events",
        "table",
        "transport",
        "instrumented_seconds",
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
)


def _elapsed(started: float, now: Callable[[], float]) -> float:
    return round(max(0.0, float(now()) - float(started)), 6)


def _safe_counter_delta(
    client: Any, names: Sequence[str], before: Mapping[str, int]
) -> dict[str, int]:
    return _counter_delta(_counter_snapshot(client, names), before)


class TimedModelClient:
    """Transparent model proxy that retains only content-free call metrics."""

    def __init__(self, inner: Any, *, monotonic: Callable[[], float]) -> None:
        self.inner = inner
        self.monotonic = monotonic
        self.events: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def _stage(self, json_mode: bool) -> str:
        if json_mode and not any(event["stage"] == "plan" for event in self.events):
            return "plan"
        if not any(event["stage"] == "synthesis" for event in self.events):
            return "synthesis"
        return "repair"

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        stage = self._stage(json_mode)
        before = _counter_snapshot(self.inner, MODEL_COUNTERS)
        started = float(self.monotonic())
        success = False
        try:
            value = self.inner.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
            success = True
            return value
        finally:
            delta = _safe_counter_delta(self.inner, MODEL_COUNTERS, before)
            self.events.append(
                {
                    "stage": stage,
                    "success": success,
                    "elapsed_seconds": _elapsed(started, self.monotonic),
                    **{f"{name}_delta": delta[name] for name in MODEL_COUNTERS},
                }
            )


def _batch_stats(batches: object) -> dict[str, int]:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return {
            "returned_batch_count": 0,
            "usable_result_count": 0,
            "unique_url_count": 0,
            "unique_host_count": 0,
            "content_char_count": 0,
        }
    urls: set[str] = set()
    hosts: set[str] = set()
    usable = 0
    characters = 0
    returned = 0
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        returned += 1
        for result in batch.get("results") or []:
            if not isinstance(result, Mapping):
                continue
            usable += 1
            canonical = canonicalize_url(str(result.get("url", "")))
            if canonical:
                urls.add(canonical)
                hostname = (urlsplit(canonical).hostname or "").casefold()
                if hostname:
                    hosts.add(hostname)
            characters += len(
                str(result.get("raw_content") or result.get("content") or "")
            )
    return {
        "returned_batch_count": returned,
        "usable_result_count": usable,
        "unique_url_count": len(urls),
        "unique_host_count": len(hosts),
        "content_char_count": characters,
    }


class TimedSearchClient:
    """Transparent search proxy with aggregate yield and latency accounting."""

    def __init__(self, inner: Any, *, monotonic: Callable[[], float]) -> None:
        self.inner = inner
        self.monotonic = monotonic
        self.events: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def _call(
        self,
        stage: str,
        logical_count: int,
        function: Callable[[], Any],
    ) -> Any:
        before = _counter_snapshot(self.inner, SEARCH_COUNTERS)
        started = float(self.monotonic())
        success = False
        batches: Any = []
        try:
            batches = function()
            success = True
            return batches
        finally:
            delta = _safe_counter_delta(self.inner, SEARCH_COUNTERS, before)
            stats = _batch_stats(batches)
            self.events.append(
                {
                    "stage": stage,
                    "success": success,
                    "elapsed_seconds": _elapsed(started, self.monotonic),
                    "logical_request_count": max(0, int(logical_count)),
                    **stats,
                    **{f"{name}_delta": delta[name] for name in SEARCH_COUNTERS},
                }
            )

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> Any:
        values = list(queries)
        return self._call(
            "search",
            len(values),
            lambda: self.inner.search_many(values, **kwargs),
        )

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        values = list(requests_)
        return self._call(
            "fetch",
            len(values),
            lambda: self.inner.fetch_urls(values),
        )


def _table_stats(prediction: str, column_count: int) -> dict[str, Any]:
    pipe_rows = [
        _split_pipe_row(line)
        for line in str(prediction or "").replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    rows = [row for row in pipe_rows[2:] if len(row) == column_count]
    cells = [cell.strip() for row in rows for cell in row]
    unknown_markers = {
        "unknown",
        "未知",
        "n/a",
        "na",
        "not available",
        "not found",
        "—",
        "-",
    }
    unknown = sum(cell.casefold() in unknown_markers for cell in cells)
    return {
        "row_count": len(rows),
        "column_count": max(0, int(column_count)),
        "cell_count": len(cells),
        "unknown_cell_count": unknown,
        "unknown_cell_ratio": round(unknown / len(cells), 12) if cells else 1.0,
    }


def _transport(search: Any) -> dict[str, Any]:
    inner = getattr(search, "inner", search)
    return {
        "provider": "azure-native-keyless-batched",
        "batch_size": max(0, int(getattr(inner, "batch_size", 0) or 0)),
        "search_workers": max(0, int(getattr(inner, "max_workers", 0) or 0)),
        "fetch_workers": max(0, int(getattr(inner, "fetch_workers", 0) or 0)),
        "fetch_timeout_seconds": max(
            0, int(getattr(inner, "fetch_timeout", 0) or 0)
        ),
        "server_auto_fetch_enabled": bool(getattr(inner, "fetch_pages", False)),
    }


def build_telemetry(
    *,
    model: TimedModelClient,
    search: TimedSearchClient,
    prediction: str,
    column_count: int,
) -> dict[str, Any]:
    model_events = [dict(event) for event in model.events]
    search_events = [dict(event) for event in search.events]
    value = {
        "artifact_version": 1,
        "role": "v24268_content_free_stage_telemetry",
        "model_events": model_events,
        "search_events": search_events,
        "table": _table_stats(prediction, column_count),
        "transport": _transport(search),
        "instrumented_seconds": round(
            sum(float(event["elapsed_seconds"]) for event in model_events + search_events),
            6,
        ),
        "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    validate_telemetry(value)
    return value


def _nonnegative_number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.42.68 {label} is not a nonnegative number")
    return float(value)


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.68 {label} is not a nonnegative integer")
    return value


def validate_telemetry(value: Mapping[str, Any]) -> None:
    if (
        set(value) != TELEMETRY_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24268_content_free_stage_telemetry"
        or value.get(
            "contains_question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise ValueError("V2.42.68 telemetry schema drifted")
    model_events = value.get("model_events")
    search_events = value.get("search_events")
    if not isinstance(model_events, list) or not isinstance(search_events, list):
        raise ValueError("V2.42.68 telemetry events are invalid")
    for event in model_events:
        if (
            not isinstance(event, Mapping)
            or set(event) != MODEL_EVENT_KEYS
            or event.get("stage") not in {"plan", "synthesis", "repair"}
            or not isinstance(event.get("success"), bool)
        ):
            raise ValueError("V2.42.68 model telemetry event drifted")
        _nonnegative_number(event.get("elapsed_seconds"), "model elapsed")
        for key in MODEL_EVENT_KEYS - {"stage", "success", "elapsed_seconds"}:
            _nonnegative_integer(event.get(key), f"model event {key}")
    for event in search_events:
        if (
            not isinstance(event, Mapping)
            or set(event) != SEARCH_EVENT_KEYS
            or event.get("stage") not in {"search", "fetch"}
            or not isinstance(event.get("success"), bool)
        ):
            raise ValueError("V2.42.68 search telemetry event drifted")
        _nonnegative_number(event.get("elapsed_seconds"), "search elapsed")
        for key in SEARCH_EVENT_KEYS - {"stage", "success", "elapsed_seconds"}:
            _nonnegative_integer(event.get(key), f"search event {key}")
    table = value.get("table")
    transport = value.get("transport")
    if not isinstance(table, Mapping) or set(table) != TABLE_KEYS:
        raise ValueError("V2.42.68 table telemetry drifted")
    if not isinstance(transport, Mapping) or set(transport) != TRANSPORT_KEYS:
        raise ValueError("V2.42.68 transport telemetry drifted")
    for key in TABLE_KEYS - {"unknown_cell_ratio"}:
        _nonnegative_integer(table.get(key), f"table {key}")
    ratio = _nonnegative_number(table.get("unknown_cell_ratio"), "unknown ratio")
    if ratio > 1:
        raise ValueError("V2.42.68 unknown ratio exceeds one")
    if table["unknown_cell_count"] > table["cell_count"]:
        raise ValueError("V2.42.68 unknown cell accounting drifted")
    if transport.get("provider") != "azure-native-keyless-batched":
        raise ValueError("V2.42.68 provider identity drifted")
    for key in TRANSPORT_KEYS - {"provider", "server_auto_fetch_enabled"}:
        _nonnegative_integer(transport.get(key), f"transport {key}")
    if transport.get("server_auto_fetch_enabled") is not False:
        raise ValueError("V2.42.68 server auto-fetch must remain disabled")
    instrumented = _nonnegative_number(
        value.get("instrumented_seconds"), "instrumented seconds"
    )
    event_sum = sum(
        float(event["elapsed_seconds"]) for event in model_events + search_events
    )
    if not math.isclose(instrumented, event_sum, abs_tol=2e-6):
        raise ValueError("V2.42.68 stage timing sum drifted")


def run_v24268_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    policy = limits or ScoreFirstLimits()
    policy.validate()
    timed_model = TimedModelClient(model, monotonic=monotonic)
    timed_search = TimedSearchClient(search, monotonic=monotonic)
    parent = run_total_task(
        visible,
        model=timed_model,
        search=timed_search,
        limits=policy,
        monotonic=monotonic,
        progress=progress,
    )
    result = dict(parent)
    result["role"] = RESULT_ROLE
    result["policy_id"] = POLICY_ID
    result["telemetry"] = build_telemetry(
        model=timed_model,
        search=timed_search,
        prediction=str(result["prediction"]),
        column_count=len(result["columns"]),
    )
    result["prediction_sha256"] = hashlib.sha256(
        str(result["prediction"]).encode("utf-8")
    ).hexdigest()
    validate_v24268_result(result)
    return result


def validate_v24268_result(value: Mapping[str, Any]) -> None:
    if value.get("role") != RESULT_ROLE or value.get("policy_id") != POLICY_ID:
        raise ValueError("V2.42.68 result identity drifted")
    telemetry = value.get("telemetry")
    if not isinstance(telemetry, Mapping):
        raise ValueError("V2.42.68 telemetry is absent")
    validate_telemetry(telemetry)
    parent = dict(value)
    parent.pop("telemetry", None)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    validate_v24259_result(parent)


__all__ = [
    "POLICY_ID",
    "RESULT_ROLE",
    "TimedModelClient",
    "TimedSearchClient",
    "build_telemetry",
    "run_v24268_task",
    "validate_telemetry",
    "validate_v24268_result",
]
