#!/usr/bin/env python3
"""Run the frozen neutral V2.42.81 request-count paired probe."""

from __future__ import annotations

import concurrent.futures
import copy
import json
import math
import os
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import canonicalize_url  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import _lead_requests  # noqa: E402
from deepwide_agent.v24270_budget_equivalent_union import (  # noqa: E402
    BudgetEquivalentTaskUnionSearchClient,
)
from deepwide_agent.v24275_hard_deadline_fetch import (  # noqa: E402
    HardDeadlineNativeSearchClient,
)
from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    TaskUnionSingleShotHardDeadlineNativeSearchClient,
    parse_task_union_single_shot,
)
from scripts import preregister_v24281_single_shot_pair as prereg  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    sha256,
)


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
ARM_KEYS = frozenset(
    {
        "pair",
        "arm",
        "terminal",
        "failure_type",
        "root_complete_mapping",
        "wall_seconds",
        "search_seconds",
        "fetch_seconds",
        "provider_counters",
        "recursive_suffix_chunk_requests",
        "single_shot_action_trace_attachments",
        "effective_search_failures",
        "raw_mapping_failures",
        "raw_unrecoverable_search_failures",
        "admitted_sources",
        "fetch_attempts",
        "usable_pages",
        "usable_chars",
        "unique_hosts",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_helper_failures",
        "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
)


def _counters(client: Any) -> dict[str, int]:
    return {name: max(0, int(getattr(client, name, 0) or 0)) for name in COUNTERS}


def _counter_sum(*values: Mapping[str, int]) -> dict[str, int]:
    return {name: sum(int(value[name]) for value in values) for name in COUNTERS}


def _pages(batches: object) -> tuple[int, int, int]:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return 0, 0, 0
    usable = 0
    characters = 0
    hosts: set[str] = set()
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        for result in batch.get("results") or []:
            if not isinstance(result, Mapping):
                continue
            text = str(result.get("raw_content") or result.get("content") or "").strip()
            if not text:
                continue
            usable += 1
            characters += len(text)
            url = canonicalize_url(str(result.get("url", "")))
            host = (urlsplit(url).hostname or "").casefold() if url else ""
            if host:
                hosts.add(host)
    return usable, characters, len(hosts)


def _new_client(
    protocol: Mapping[str, Any], *, single_shot: bool
) -> HardDeadlineNativeSearchClient:
    provider = protocol["provider"]
    cls = (
        TaskUnionSingleShotHardDeadlineNativeSearchClient
        if single_shot
        else HardDeadlineNativeSearchClient
    )
    return cls(
        provider["endpoint"],
        provider["model"],
        reasoning_effort=provider["reasoning_effort"],
        service_tier=provider["service_tier"],
        timeout=provider["timeout_seconds"],
        max_retries=provider["max_retries"],
        max_workers=provider["workers"],
        batch_size=provider["batch_size"],
        search_context_size=provider["search_context_size"],
        max_output_tokens=provider["max_output_tokens"],
        fetch_pages=False,
        fetch_workers=provider["fetch_workers"],
        fetch_timeout=provider["fetch_timeout_seconds"],
        max_page_chars=provider["max_page_chars"],
        hard_fetch_deadline_seconds=provider["hard_fetch_deadline_seconds"],
    )


class _ReplayInner:
    """Expose a frozen parse to the existing union/cap layers without I/O."""

    batch_size = 8
    max_workers = 1
    fetch_workers = 1
    fetch_timeout = 1
    fetch_pages = False

    def __init__(self, batches: Sequence[Mapping[str, Any]]) -> None:
        self.batches = copy.deepcopy(list(batches))
        for name in COUNTERS:
            setattr(self, name, 0)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        del queries, kwargs
        self.failures += sum(bool(batch.get("error")) for batch in self.batches)
        return copy.deepcopy(self.batches)

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
        del requests_
        raise RuntimeError("V2.42.81 replay fetch is forbidden")


def _union(
    batches: Sequence[Mapping[str, Any]], queries: Sequence[str]
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    capped = BudgetEquivalentTaskUnionSearchClient(
        _ReplayInner(batches),
        search_results_per_query=prereg.RESULTS_PER_QUERY,
        global_fetch_cap=prereg.FETCH_CAP,
    )
    union = capped.search_many(
        list(queries),
        max_results=prereg.RESULTS_PER_QUERY,
        search_depth="advanced",
        include_raw_content=False,
    )
    leads = _lead_requests(union, prereg.FETCH_CAP)
    discovery = capped.parent.receipt()
    budget = capped.receipt()
    return leads, {
        "effective_search_failures": int(capped.failures),
        "raw_mapping_failures": int(
            discovery["raw_query_local_mapping_failure_count"]
        ),
        "raw_unrecoverable_search_failures": int(
            discovery["raw_unrecoverable_failure_count"]
        ),
        "admitted_sources": int(budget["post_cap_source_count"]),
    }


def _fetch(
    client: HardDeadlineNativeSearchClient,
    leads: Sequence[dict[str, str]],
) -> dict[str, Any]:
    before = _counters(client)
    helper_before = int(client.hard_fetch_helper_calls)
    deadline_before = int(client.hard_fetch_deadline_failures)
    failure_before = int(client.fetch_helper_failures)
    started = time.monotonic()
    pages = client.fetch_urls(list(leads)) if leads else []
    elapsed = max(0.0, time.monotonic() - started)
    after = _counters(client)
    usable, characters, hosts = _pages(pages)
    return {
        "seconds": elapsed,
        "counter_delta": {
            name: max(0, after[name] - before[name]) for name in COUNTERS
        },
        "usable_pages": usable,
        "usable_chars": characters,
        "unique_hosts": hosts,
        "hard_fetch_helper_calls": int(client.hard_fetch_helper_calls)
        - helper_before,
        "hard_fetch_deadline_failures": int(client.hard_fetch_deadline_failures)
        - deadline_before,
        "fetch_helper_failures": int(client.fetch_helper_failures) - failure_before,
    }


def _arm(
    *,
    pair: int,
    arm: str,
    failure_type: str | None,
    root_complete_mapping: bool,
    search_seconds: float,
    fetch: Mapping[str, Any],
    counters: Mapping[str, int],
    suffix_requests: int,
    trace_attachments: int,
    union: Mapping[str, Any],
    fetch_attempts: int,
) -> dict[str, Any]:
    value = {
        "pair": pair,
        "arm": arm,
        "terminal": True,
        "failure_type": failure_type,
        "root_complete_mapping": bool(root_complete_mapping),
        "wall_seconds": round(
            max(0.0, float(search_seconds) + float(fetch["seconds"])), 6
        ),
        "search_seconds": round(max(0.0, float(search_seconds)), 6),
        "fetch_seconds": round(max(0.0, float(fetch["seconds"])), 6),
        "provider_counters": dict(counters),
        "recursive_suffix_chunk_requests": int(suffix_requests),
        "single_shot_action_trace_attachments": int(trace_attachments),
        "effective_search_failures": int(union["effective_search_failures"]),
        "raw_mapping_failures": int(union["raw_mapping_failures"]),
        "raw_unrecoverable_search_failures": int(
            union["raw_unrecoverable_search_failures"]
        ),
        "admitted_sources": int(union["admitted_sources"]),
        "fetch_attempts": int(fetch_attempts),
        "usable_pages": int(fetch["usable_pages"]),
        "usable_chars": int(fetch["usable_chars"]),
        "unique_hosts": int(fetch["unique_hosts"]),
        "hard_fetch_helper_calls": int(fetch["hard_fetch_helper_calls"]),
        "hard_fetch_deadline_failures": int(
            fetch["hard_fetch_deadline_failures"]
        ),
        "fetch_helper_failures": int(fetch["fetch_helper_failures"]),
        "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    validate_arm(value)
    return value


def _zero_fetch() -> dict[str, Any]:
    return {
        "seconds": 0.0,
        "counter_delta": {name: 0 for name in COUNTERS},
        "usable_pages": 0,
        "usable_chars": 0,
        "unique_hosts": 0,
        "hard_fetch_helper_calls": 0,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
    }


def _run_pair(protocol: Mapping[str, Any], pair: int) -> list[dict[str, Any]]:
    queries = list(prereg.NEUTRAL_QUERY_PAIRS[pair - 1])
    root = _new_client(protocol, single_shot=True)
    suffix = _new_client(protocol, single_shot=False)
    root_started = time.monotonic()
    try:
        payload = root._request(queries)
    except Exception as exc:  # noqa: BLE001 - persist class only
        root_seconds = max(0.0, time.monotonic() - root_started)
        root_counters = _counters(root)
        failure = type(exc).__name__
        union = {
            "effective_search_failures": len(queries),
            "raw_mapping_failures": 0,
            "raw_unrecoverable_search_failures": len(queries),
            "admitted_sources": 0,
        }
        return [
            _arm(
                pair=pair,
                arm=arm,
                failure_type=failure,
                root_complete_mapping=False,
                search_seconds=root_seconds,
                fetch=_zero_fetch(),
                counters=root_counters,
                suffix_requests=0,
                trace_attachments=0,
                union=union,
                fetch_attempts=0,
            )
            for arm in prereg.ARMS
        ]
    root_seconds = max(0.0, time.monotonic() - root_started)
    root_counters = _counters(root)

    candidate_batches, complete, _, attachments = parse_task_union_single_shot(
        root, queries, payload, max_results=prereg.RESULTS_PER_QUERY
    )
    control_root_batches, control_complete = root._parse_batch(
        queries, payload, max_results=prereg.RESULTS_PER_QUERY
    )
    if bool(complete) != bool(control_complete):
        raise RuntimeError("V2.42.81 root mapping view diverged")
    candidate_parse_failures = sum(
        bool(batch.get("error")) for batch in candidate_batches
    )
    control_parse_failures = sum(
        bool(batch.get("error")) for batch in control_root_batches
    )

    suffix_requests = 0
    suffix_seconds = 0.0
    if control_complete:
        control_batches = control_root_batches
    else:
        midpoint = max(1, len(queries) // 2)
        control_batches: list[dict[str, Any]] = []
        for chunk in (queries[:midpoint], queries[midpoint:]):
            if not chunk:
                continue
            suffix_requests += 1
            started = time.monotonic()
            control_batches.extend(
                suffix._run_chunk(chunk, prereg.RESULTS_PER_QUERY)
            )
            suffix_seconds += max(0.0, time.monotonic() - started)

    candidate_leads, candidate_union = _union(candidate_batches, queries)
    control_leads, control_union = _union(control_batches, queries)
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=2, thread_name_prefix="v24281-paired-fetch"
    ) as pool:
        candidate_future = pool.submit(_fetch, root, candidate_leads)
        control_future = pool.submit(_fetch, suffix, control_leads)
        candidate_fetch = candidate_future.result()
        control_fetch = control_future.result()

    candidate_counters = _counter_sum(
        root_counters, candidate_fetch["counter_delta"]
    )
    candidate_counters["failures"] += candidate_parse_failures
    control_root_counters = dict(root_counters)
    if control_complete:
        # The generic parent counts per-batch parse failures only when it does
        # not recurse.  An incomplete root response is discarded before those
        # counters are incremented, so mirror that exact accounting here.
        control_root_counters["failures"] += control_parse_failures
    control_counters = _counter_sum(control_root_counters, _counters(suffix))
    return [
        _arm(
            pair=pair,
            arm="recursive",
            failure_type=None,
            root_complete_mapping=bool(control_complete),
            search_seconds=root_seconds + suffix_seconds,
            fetch=control_fetch,
            counters=control_counters,
            suffix_requests=suffix_requests,
            trace_attachments=0,
            union=control_union,
            fetch_attempts=len(control_leads),
        ),
        _arm(
            pair=pair,
            arm="single_shot",
            failure_type=None,
            root_complete_mapping=bool(complete),
            search_seconds=root_seconds,
            fetch=candidate_fetch,
            counters=candidate_counters,
            suffix_requests=0,
            trace_attachments=attachments,
            union=candidate_union,
            fetch_attempts=len(candidate_leads),
        ),
    ]


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.81 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.81 {label} is invalid")
    return number


def validate_arm(value: Mapping[str, Any]) -> None:
    counters = value.get("provider_counters")
    if (
        set(value) != ARM_KEYS
        or value.get("arm") not in prereg.ARMS
        or isinstance(value.get("pair"), bool)
        or not isinstance(value.get("pair"), int)
        or not 1 <= value["pair"] <= prereg.PAIR_COUNT
        or value.get("terminal") is not True
        or value.get("failure_type") is not None
        and not isinstance(value.get("failure_type"), str)
        or not isinstance(value.get("root_complete_mapping"), bool)
        or not isinstance(counters, Mapping)
        or set(counters) != set(COUNTERS)
        or value.get(
            "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise RuntimeError("V2.42.81 arm schema drifted")
    for name in ("wall_seconds", "search_seconds", "fetch_seconds"):
        _finite(value.get(name), name)
    for number in [
        *counters.values(),
        *(
            value[name]
            for name in (
                "recursive_suffix_chunk_requests",
                "single_shot_action_trace_attachments",
                "effective_search_failures",
                "raw_mapping_failures",
                "raw_unrecoverable_search_failures",
                "admitted_sources",
                "fetch_attempts",
                "usable_pages",
                "usable_chars",
                "unique_hosts",
                "hard_fetch_helper_calls",
                "hard_fetch_deadline_failures",
                "fetch_helper_failures",
            )
        ),
    ]:
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise RuntimeError("V2.42.81 arm counter drifted")
    if (
        value["usable_pages"] > value["fetch_attempts"]
        or value["fetch_attempts"] != value["admitted_sources"]
        or value["hard_fetch_helper_calls"] != counters["fetch_calls"]
        or value["hard_fetch_deadline_failures"] + value["fetch_helper_failures"]
        > value["hard_fetch_helper_calls"]
        or value["arm"] == "single_shot"
        and value["recursive_suffix_chunk_requests"] != 0
        or value["arm"] == "recursive"
        and value["single_shot_action_trace_attachments"] != 0
        or value["root_complete_mapping"]
        and value["recursive_suffix_chunk_requests"] != 0
    ):
        raise RuntimeError("V2.42.81 arm accounting drifted")


def _aggregate(rows: Sequence[Mapping[str, Any]], arm: str) -> dict[str, Any]:
    values = [row for row in rows if row["arm"] == arm]
    if len(values) != prereg.PAIR_COUNT:
        raise RuntimeError("V2.42.81 arm count drifted")
    return {
        "selected": len(values),
        "terminal": sum(row["terminal"] is True for row in values),
        "failures": sum(row["failure_type"] is not None for row in values),
        "root_incomplete_mappings": sum(
            row["root_complete_mapping"] is False for row in values
        ),
        "wall_seconds_sum": round(
            sum(float(row["wall_seconds"]) for row in values), 6
        ),
        "search_seconds_sum": round(
            sum(float(row["search_seconds"]) for row in values), 6
        ),
        "fetch_seconds_sum": round(
            sum(float(row["fetch_seconds"]) for row in values), 6
        ),
        "http_search_calls": sum(row["provider_counters"]["calls"] for row in values),
        "raw_native_failures": sum(
            row["provider_counters"]["failures"] for row in values
        ),
        "search_tool_calls": sum(
            row["provider_counters"]["tool_calls"] for row in values
        ),
        "search_input_tokens": sum(
            row["provider_counters"]["input_tokens"] for row in values
        ),
        "search_output_tokens": sum(
            row["provider_counters"]["output_tokens"] for row in values
        ),
        "search_total_tokens": sum(
            row["provider_counters"]["total_tokens"] for row in values
        ),
        "recursive_suffix_chunk_requests": sum(
            row["recursive_suffix_chunk_requests"] for row in values
        ),
        "single_shot_action_trace_attachments": sum(
            row["single_shot_action_trace_attachments"] for row in values
        ),
        "effective_search_failures": sum(
            row["effective_search_failures"] for row in values
        ),
        "raw_mapping_failures": sum(row["raw_mapping_failures"] for row in values),
        "unrecoverable_search_failures": sum(
            row["raw_unrecoverable_search_failures"] for row in values
        ),
        "admitted_sources": sum(row["admitted_sources"] for row in values),
        "fetch_attempts": sum(row["fetch_attempts"] for row in values),
        "usable_pages": sum(row["usable_pages"] for row in values),
        "usable_chars": sum(row["usable_chars"] for row in values),
        "unique_hosts_sum": sum(row["unique_hosts"] for row in values),
        "hard_fetch_deadline_failures": sum(
            row["hard_fetch_deadline_failures"] for row in values
        ),
        "fetch_helper_failures": sum(row["fetch_helper_failures"] for row in values),
    }


def _ratio(candidate: int | float, control: int | float) -> float:
    return float(candidate) / float(control) if float(control) > 0 else math.inf


def summarize(
    protocol: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], batch_wall: float
) -> dict[str, Any]:
    values = [dict(row) for row in rows]
    for row in values:
        validate_arm(row)
    expected = sorted(
        (pair, arm)
        for pair in range(1, prereg.PAIR_COUNT + 1)
        for arm in prereg.ARMS
    )
    if sorted((row["pair"], row["arm"]) for row in values) != expected:
        raise RuntimeError("V2.42.81 paired coverage drifted")
    recursive = _aggregate(values, "recursive")
    single = _aggregate(values, "single_shot")
    ratios = {
        "http_search_calls": _ratio(
            single["http_search_calls"], recursive["http_search_calls"]
        ),
        "search_input_tokens": _ratio(
            single["search_input_tokens"], recursive["search_input_tokens"]
        ),
        "search_total_tokens": _ratio(
            single["search_total_tokens"], recursive["search_total_tokens"]
        ),
        "search_seconds_sum": _ratio(
            single["search_seconds_sum"], recursive["search_seconds_sum"]
        ),
        "wall_seconds_sum": _ratio(
            single["wall_seconds_sum"], recursive["wall_seconds_sum"]
        ),
        "admitted_sources": _ratio(
            single["admitted_sources"], recursive["admitted_sources"]
        ),
        "usable_pages": _ratio(single["usable_pages"], recursive["usable_pages"]),
        "usable_chars": _ratio(single["usable_chars"], recursive["usable_chars"]),
        "unique_hosts_sum": _ratio(
            single["unique_hosts_sum"], recursive["unique_hosts_sum"]
        ),
    }
    gates = protocol["gates"]
    checks = {
        "exact_paired_terminal": all(row["terminal"] for row in values),
        "no_arm_exception": all(row["failure_type"] is None for row in values),
        "shared_root_mapping_state": all(
            next(
                row["root_complete_mapping"]
                for row in values
                if row["pair"] == pair and row["arm"] == "recursive"
            )
            == next(
                row["root_complete_mapping"]
                for row in values
                if row["pair"] == pair and row["arm"] == "single_shot"
            )
            for pair in range(1, prereg.PAIR_COUNT + 1)
        ),
        "control_exercised_recursive_split": recursive[
            "recursive_suffix_chunk_requests"
        ]
        >= gates["minimum_control_recursive_split_chunk_requests"],
        "candidate_never_recursed": single["recursive_suffix_chunk_requests"] == 0,
        "no_effective_search_failures": recursive["effective_search_failures"]
        <= gates["maximum_effective_search_failures_per_arm"]
        and single["effective_search_failures"]
        <= gates["maximum_effective_search_failures_per_arm"],
        "no_unrecoverable_search_failures": recursive[
            "unrecoverable_search_failures"
        ]
        <= gates["maximum_unrecoverable_search_failures_per_arm"]
        and single["unrecoverable_search_failures"]
        <= gates["maximum_unrecoverable_search_failures_per_arm"],
        "no_hard_fetch_deadlines": recursive["hard_fetch_deadline_failures"]
        <= gates["maximum_hard_fetch_deadlines_per_arm"]
        and single["hard_fetch_deadline_failures"]
        <= gates["maximum_hard_fetch_deadlines_per_arm"],
        "no_fetch_helper_failures": recursive["fetch_helper_failures"]
        <= gates["maximum_fetch_helper_failures_per_arm"]
        and single["fetch_helper_failures"]
        <= gates["maximum_fetch_helper_failures_per_arm"],
        "http_call_ratio": ratios["http_search_calls"]
        <= gates["maximum_single_shot_over_recursive_http_calls"],
        "input_token_ratio": ratios["search_input_tokens"]
        <= gates["maximum_single_shot_over_recursive_input_tokens"],
        "total_token_ratio": ratios["search_total_tokens"]
        <= gates["maximum_single_shot_over_recursive_total_tokens"],
        "search_wall_ratio": ratios["search_seconds_sum"]
        <= gates["maximum_single_shot_over_recursive_search_seconds"],
        "task_wall_ratio": ratios["wall_seconds_sum"]
        <= gates["maximum_single_shot_over_recursive_wall_seconds"],
        "admitted_source_yield": ratios["admitted_sources"]
        >= gates["minimum_single_shot_over_recursive_admitted_sources"],
        "usable_page_yield": ratios["usable_pages"]
        >= gates["minimum_single_shot_over_recursive_usable_pages"],
        "usable_character_yield": ratios["usable_chars"]
        >= gates["minimum_single_shot_over_recursive_usable_chars"],
        "unique_host_yield": ratios["unique_hosts_sum"]
        >= gates["minimum_single_shot_over_recursive_unique_hosts"],
        "absolute_recursive_yield": recursive["admitted_sources"]
        >= gates["minimum_admitted_sources_per_arm"]
        and recursive["usable_pages"] >= gates["minimum_usable_pages_per_arm"]
        and recursive["usable_chars"] >= gates["minimum_usable_chars_per_arm"],
        "absolute_single_shot_yield": single["admitted_sources"]
        >= gates["minimum_admitted_sources_per_arm"]
        and single["usable_pages"] >= gates["minimum_usable_pages_per_arm"]
        and single["usable_chars"] >= gates["minimum_usable_chars_per_arm"],
        "absolute_batch_wall": float(batch_wall)
        <= gates["maximum_batch_wall_seconds"],
    }
    pair_directions: dict[str, dict[str, int]] = {}
    for name, extractor, lower_better in (
        ("http_search_calls", lambda row: row["provider_counters"]["calls"], True),
        ("search_total_tokens", lambda row: row["provider_counters"]["total_tokens"], True),
        ("wall_seconds", lambda row: row["wall_seconds"], True),
        ("usable_pages", lambda row: row["usable_pages"], False),
    ):
        better = tie = worse = 0
        for pair in range(1, prereg.PAIR_COUNT + 1):
            by_arm = {
                row["arm"]: row for row in values if row["pair"] == pair
            }
            delta = float(extractor(by_arm["single_shot"])) - float(
                extractor(by_arm["recursive"])
            )
            if abs(delta) <= 1e-12:
                tie += 1
            elif (delta < 0) is lower_better:
                better += 1
            else:
                worse += 1
        pair_directions[name] = {
            "single_shot_better": better,
            "tie": tie,
            "single_shot_worse": worse,
        }
    return {
        "recursive": recursive,
        "single_shot": single,
        "single_shot_over_recursive": ratios,
        "pair_directions": pair_directions,
        "batch_wall_seconds": round(max(0.0, float(batch_wall)), 6),
        "checks": checks,
        "passed": all(checks.values()),
    }


def validate_result(value: Mapping[str, Any], root: Path = ROOT) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    protocol = prereg.validate_protocol(root)
    rows = value.get("arms")
    summary = value.get("summary")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24281_neutral_single_shot_pair_result"
        or value.get("protocol_id") != prereg.PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(root / prereg.OUTPUT)
        or not isinstance(rows, list)
        or len(rows) != prereg.PAIR_COUNT * len(prereg.ARMS)
        or not isinstance(summary, Mapping)
        or summary != summarize(protocol, rows, float(summary["batch_wall_seconds"]))
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.81 result drifted")


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def run(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = prereg.validate_protocol(root)
    if (root / prereg.RESULT).exists() or (root / prereg.RESULT).is_symlink():
        raise FileExistsError(root / prereg.RESULT)
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    lease = protocol["lease"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / lease["path"],
    ):
        for wave in protocol["pair_contract"]["schedule"]:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=prereg.PAIR_CONCURRENCY,
                thread_name_prefix="v24281-single-shot-pair",
            ) as pool:
                futures = [pool.submit(_run_pair, protocol, pair) for pair in wave]
                for future in futures:
                    rows.extend(future.result())
    batch_wall = max(0.0, time.monotonic() - started)
    summary = summarize(protocol, rows, batch_wall)
    value = {
        "artifact_version": 1,
        "role": "v24281_neutral_single_shot_pair_result",
        "created_at_unix": int(time.time()),
        "protocol_id": prereg.PROTOCOL_ID,
        "protocol_sha256": sha256(root / prereg.OUTPUT),
        "arms": sorted(rows, key=lambda row: (row["pair"], row["arm"])),
        "summary": summary,
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "standalone_generation_or_official_evaluator_called": False,
        },
        "authorization": {
            "benchmark_launch": False,
            "dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_result(value, root)
    publish_new(root / prereg.RESULT, value)
    return value


if __name__ == "__main__":
    result = run()
    print(
        json.dumps(
            {
                "path": str(prereg.RESULT),
                "sha256": sha256(ROOT / prereg.RESULT),
                "passed": result["summary"]["passed"],
                "single_shot_over_recursive": result["summary"][
                    "single_shot_over_recursive"
                ],
            },
            sort_keys=True,
        )
    )
