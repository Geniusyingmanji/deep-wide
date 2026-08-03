#!/usr/bin/env python3
"""Run the frozen neutral V2.42.78 search-context paired probe."""

from __future__ import annotations

import concurrent.futures
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
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts import preregister_v24278_search_context_pair as prereg  # noqa: E402
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
        "context",
        "terminal",
        "failure_type",
        "wall_seconds",
        "search_seconds",
        "fetch_seconds",
        "provider_counters",
        "search_invocations",
        "logical_queries",
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


def _new_search(protocol: Mapping[str, Any], context: str) -> HardDeadlineNativeSearchClient:
    provider = protocol["provider"]
    if context not in prereg.CONTEXTS:
        raise ValueError("V2.42.78 context drifted")
    return HardDeadlineNativeSearchClient(
        provider["endpoint"],
        provider["model"],
        reasoning_effort=provider["reasoning_effort"],
        service_tier=provider["service_tier"],
        timeout=provider["timeout_seconds"],
        max_retries=provider["max_retries"],
        max_workers=provider["workers"],
        batch_size=provider["batch_size"],
        search_context_size=context,
        max_output_tokens=provider["max_output_tokens"],
        fetch_pages=False,
        fetch_workers=provider["fetch_workers"],
        fetch_timeout=provider["fetch_timeout_seconds"],
        max_page_chars=provider["max_page_chars"],
        hard_fetch_deadline_seconds=provider["hard_fetch_deadline_seconds"],
    )


def _run_arm(protocol: Mapping[str, Any], pair: int, context: str) -> dict[str, Any]:
    search = _new_search(protocol, context)
    capped = BudgetEquivalentTaskUnionSearchClient(
        search,
        search_results_per_query=prereg.RESULTS_PER_QUERY,
        global_fetch_cap=prereg.FETCH_CAP,
    )
    started = time.monotonic()
    search_seconds = 0.0
    fetch_seconds = 0.0
    failure: str | None = None
    leads: list[dict[str, str]] = []
    pages: object = []
    try:
        search_started = time.monotonic()
        batches = capped.search_many(
            prereg.NEUTRAL_QUERY_PAIRS[pair - 1],
            max_results=prereg.RESULTS_PER_QUERY,
            search_depth="advanced",
            include_raw_content=False,
        )
        search_seconds = max(0.0, time.monotonic() - search_started)
        leads = _lead_requests(batches, prereg.FETCH_CAP)
        fetch_started = time.monotonic()
        pages = capped.fetch_urls(leads) if leads else []
        fetch_seconds = max(0.0, time.monotonic() - fetch_started)
    except Exception as exc:  # noqa: BLE001 - persist class only
        failure = type(exc).__name__
    usable, characters, hosts = _pages(pages)
    discovery = capped.parent.receipt()
    budget = capped.receipt()
    value = {
        "pair": pair,
        "context": context,
        "terminal": True,
        "failure_type": failure,
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "search_seconds": round(search_seconds, 6),
        "fetch_seconds": round(fetch_seconds, 6),
        "provider_counters": _counters(search),
        "search_invocations": int(discovery["search_invocations"]),
        "logical_queries": int(discovery["logical_query_count"]),
        "raw_unrecoverable_search_failures": int(
            discovery["raw_unrecoverable_failure_count"]
        ),
        "admitted_sources": int(budget["post_cap_source_count"]),
        "fetch_attempts": len(leads),
        "usable_pages": usable,
        "usable_chars": characters,
        "unique_hosts": hosts,
        "hard_fetch_helper_calls": int(search.hard_fetch_helper_calls),
        "hard_fetch_deadline_failures": int(search.hard_fetch_deadline_failures),
        "fetch_helper_failures": int(search.fetch_helper_failures),
        "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    validate_arm(value)
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.78 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.78 {label} is invalid")
    return number


def validate_arm(value: Mapping[str, Any]) -> None:
    counters = value.get("provider_counters")
    if (
        set(value) != ARM_KEYS
        or value.get("context") not in prereg.CONTEXTS
        or isinstance(value.get("pair"), bool)
        or not isinstance(value.get("pair"), int)
        or not 1 <= value["pair"] <= prereg.PAIR_COUNT
        or value.get("terminal") is not True
        or value.get("failure_type") is not None
        and not isinstance(value.get("failure_type"), str)
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
        raise RuntimeError("V2.42.78 arm schema drifted")
    for name in ("wall_seconds", "search_seconds", "fetch_seconds"):
        _finite(value.get(name), name)
    for number in [
        *counters.values(),
        *(
            value[name]
            for name in (
                "search_invocations",
                "logical_queries",
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
            raise RuntimeError("V2.42.78 arm counter drifted")
    if (
        value["usable_pages"] > value["fetch_attempts"]
        or value["fetch_attempts"] != value["admitted_sources"]
        or value["hard_fetch_helper_calls"] != counters["fetch_calls"]
        or value["hard_fetch_deadline_failures"]
        + value["fetch_helper_failures"]
        > value["hard_fetch_helper_calls"]
    ):
        raise RuntimeError("V2.42.78 arm accounting drifted")


def _aggregate(rows: Sequence[Mapping[str, Any]], context: str) -> dict[str, Any]:
    values = [row for row in rows if row["context"] == context]
    if len(values) != prereg.PAIR_COUNT:
        raise RuntimeError("V2.42.78 context arm count drifted")
    return {
        "selected": len(values),
        "terminal": sum(row["terminal"] is True for row in values),
        "failures": sum(row["failure_type"] is not None for row in values),
        "wall_seconds_sum": round(sum(float(row["wall_seconds"]) for row in values), 6),
        "search_seconds_sum": round(sum(float(row["search_seconds"]) for row in values), 6),
        "fetch_seconds_sum": round(sum(float(row["fetch_seconds"]) for row in values), 6),
        "search_calls": sum(row["provider_counters"]["calls"] for row in values),
        "search_failures": sum(row["provider_counters"]["failures"] for row in values),
        "search_tool_calls": sum(row["provider_counters"]["tool_calls"] for row in values),
        "search_input_tokens": sum(row["provider_counters"]["input_tokens"] for row in values),
        "search_output_tokens": sum(row["provider_counters"]["output_tokens"] for row in values),
        "search_total_tokens": sum(row["provider_counters"]["total_tokens"] for row in values),
        "admitted_sources": sum(row["admitted_sources"] for row in values),
        "fetch_attempts": sum(row["fetch_attempts"] for row in values),
        "usable_pages": sum(row["usable_pages"] for row in values),
        "usable_chars": sum(row["usable_chars"] for row in values),
        "unique_hosts_sum": sum(row["unique_hosts"] for row in values),
        "unrecoverable_search_failures": sum(row["raw_unrecoverable_search_failures"] for row in values),
        "hard_fetch_deadline_failures": sum(row["hard_fetch_deadline_failures"] for row in values),
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
        (pair, context)
        for pair in range(1, prereg.PAIR_COUNT + 1)
        for context in prereg.CONTEXTS
    )
    if sorted((row["pair"], row["context"]) for row in values) != expected:
        raise RuntimeError("V2.42.78 paired coverage drifted")
    medium = _aggregate(values, "medium")
    low = _aggregate(values, "low")
    ratios = {
        "search_input_tokens": _ratio(low["search_input_tokens"], medium["search_input_tokens"]),
        "search_total_tokens": _ratio(low["search_total_tokens"], medium["search_total_tokens"]),
        "search_calls": _ratio(low["search_calls"], medium["search_calls"]),
        "wall_seconds_sum": _ratio(low["wall_seconds_sum"], medium["wall_seconds_sum"]),
        "admitted_sources": _ratio(low["admitted_sources"], medium["admitted_sources"]),
        "usable_pages": _ratio(low["usable_pages"], medium["usable_pages"]),
        "usable_chars": _ratio(low["usable_chars"], medium["usable_chars"]),
    }
    gates = protocol["gates"]
    checks = {
        "exact_paired_terminal": all(row["terminal"] for row in values),
        "no_arm_exception": all(row["failure_type"] is None for row in values),
        "no_unrecoverable_search_failures": medium[
            "unrecoverable_search_failures"
        ]
        <= gates["maximum_unrecoverable_search_failures_per_arm"]
        and low["unrecoverable_search_failures"]
        <= gates["maximum_unrecoverable_search_failures_per_arm"],
        "no_hard_fetch_deadlines": medium["hard_fetch_deadline_failures"]
        <= gates["maximum_hard_fetch_deadlines_per_arm"]
        and low["hard_fetch_deadline_failures"]
        <= gates["maximum_hard_fetch_deadlines_per_arm"],
        "no_fetch_helper_failures": medium["fetch_helper_failures"]
        <= gates["maximum_fetch_helper_failures_per_arm"]
        and low["fetch_helper_failures"]
        <= gates["maximum_fetch_helper_failures_per_arm"],
        "search_input_token_ratio": ratios["search_input_tokens"]
        <= gates["maximum_low_over_medium_search_input_tokens"],
        "search_total_token_ratio": ratios["search_total_tokens"]
        <= gates["maximum_low_over_medium_search_total_tokens"],
        "search_call_ratio": ratios["search_calls"]
        <= gates["maximum_low_over_medium_search_calls"],
        "wall_sum_ratio": ratios["wall_seconds_sum"]
        <= gates["maximum_low_over_medium_wall_sum"],
        "admitted_source_yield": ratios["admitted_sources"]
        >= gates["minimum_low_over_medium_admitted_sources"],
        "usable_page_yield": ratios["usable_pages"]
        >= gates["minimum_low_over_medium_usable_pages"],
        "usable_character_yield": ratios["usable_chars"]
        >= gates["minimum_low_over_medium_usable_chars"],
        "absolute_medium_yield": medium["admitted_sources"]
        >= gates["minimum_admitted_sources_per_arm"]
        and medium["usable_pages"] >= gates["minimum_usable_pages_per_arm"]
        and medium["usable_chars"] >= gates["minimum_usable_chars_per_arm"],
        "absolute_low_yield": low["admitted_sources"]
        >= gates["minimum_admitted_sources_per_arm"]
        and low["usable_pages"] >= gates["minimum_usable_pages_per_arm"]
        and low["usable_chars"] >= gates["minimum_usable_chars_per_arm"],
        "absolute_batch_wall": float(batch_wall)
        <= gates["maximum_batch_wall_seconds"],
    }
    pair_directions: dict[str, dict[str, int]] = {}
    for name, extractor, lower_better in (
        ("search_input_tokens", lambda row: row["provider_counters"]["input_tokens"], True),
        ("search_total_tokens", lambda row: row["provider_counters"]["total_tokens"], True),
        ("wall_seconds", lambda row: row["wall_seconds"], True),
        ("usable_pages", lambda row: row["usable_pages"], False),
    ):
        better = tie = worse = 0
        by_pair = {
            pair: {row["context"]: row for row in values if row["pair"] == pair}
            for pair in range(1, prereg.PAIR_COUNT + 1)
        }
        for pair in by_pair.values():
            delta = float(extractor(pair["low"])) - float(extractor(pair["medium"]))
            if abs(delta) <= 1e-12:
                tie += 1
            elif (delta < 0) is lower_better:
                better += 1
            else:
                worse += 1
        pair_directions[name] = {"low_better": better, "tie": tie, "low_worse": worse}
    return {
        "medium": medium,
        "low": low,
        "low_over_medium": ratios,
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
        value.get("role") != "v24278_neutral_search_context_pair_result"
        or value.get("protocol_id") != prereg.PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(root / prereg.OUTPUT)
        or not isinstance(rows, list)
        or len(rows) != prereg.PAIR_COUNT * len(prereg.CONTEXTS)
        or not isinstance(summary, Mapping)
        or summary != summarize(protocol, rows, float(summary["batch_wall_seconds"]))
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.78 result drifted")


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
    lease = protocol["lease"]
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / lease["path"],
    ):
        for wave in protocol["pair_contract"]["schedule"]:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=prereg.ARM_CONCURRENCY,
                thread_name_prefix="v24278-context-pair",
            ) as pool:
                futures = [
                    pool.submit(_run_arm, protocol, arm["pair"], arm["context"])
                    for arm in wave
                ]
                rows.extend(future.result() for future in futures)
    batch_wall = max(0.0, time.monotonic() - started)
    summary = summarize(protocol, rows, batch_wall)
    value = {
        "artifact_version": 1,
        "role": "v24278_neutral_search_context_pair_result",
        "created_at_unix": int(time.time()),
        "protocol_id": prereg.PROTOCOL_ID,
        "protocol_sha256": sha256(root / prereg.OUTPUT),
        "arms": sorted(rows, key=lambda row: (row["pair"], row["context"])),
        "summary": summary,
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "generation_model_or_official_evaluator_called": False,
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
                "low_over_medium": result["summary"]["low_over_medium"],
            },
            sort_keys=True,
        )
    )
