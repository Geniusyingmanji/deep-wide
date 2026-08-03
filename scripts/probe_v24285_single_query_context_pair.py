#!/usr/bin/env python3
"""Run the frozen neutral V2.42.85 single-query context paired probe."""

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


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import preregister_v24285_single_query_context_pair as prereg  # noqa: E402
from scripts import probe_v24284_query_width_pair as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ARM_KEYS = frozenset(parent.ARM_KEYS - {"arm"} | {"context"})


def _run_arm(protocol: Mapping[str, Any], pair: int, context: str) -> dict[str, Any]:
    provider = dict(protocol["provider"])
    provider["search_context_size"] = context
    adapted = {**dict(protocol), "provider": provider}
    raw = parent._run_arm(adapted, pair, "one_top6")
    value = {key: item for key, item in raw.items() if key != "arm"}
    value["context"] = context
    validate_arm(value)
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.85 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.85 {label} is invalid")
    return number


def validate_arm(value: Mapping[str, Any]) -> None:
    if set(value) != ARM_KEYS or value.get("context") not in prereg.CONTEXTS:
        raise RuntimeError("V2.42.85 arm schema drifted")
    parent_value = {key: item for key, item in value.items() if key != "context"}
    parent_value["arm"] = "one_top6"
    parent.validate_arm(parent_value)


def _aggregate(rows: Sequence[Mapping[str, Any]], context: str) -> dict[str, Any]:
    values = [row for row in rows if row["context"] == context]
    if len(values) != prereg.PAIR_COUNT:
        raise RuntimeError("V2.42.85 context count drifted")
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
        "effective_search_failures": sum(row["effective_search_failures"] for row in values),
        "unrecoverable_search_failures": sum(
            row["raw_unrecoverable_search_failures"] for row in values
        ),
        "recursive_split_requests": sum(row["recursive_split_requests"] for row in values),
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
        (pair, context)
        for pair in range(1, prereg.PAIR_COUNT + 1)
        for context in prereg.CONTEXTS
    )
    if sorted((row["pair"], row["context"]) for row in values) != expected:
        raise RuntimeError("V2.42.85 paired coverage drifted")
    medium = _aggregate(values, "medium")
    low = _aggregate(values, "low")
    ratios = {
        "search_calls": _ratio(low["search_calls"], medium["search_calls"]),
        "search_input_tokens": _ratio(low["search_input_tokens"], medium["search_input_tokens"]),
        "search_total_tokens": _ratio(low["search_total_tokens"], medium["search_total_tokens"]),
        "search_seconds_sum": _ratio(low["search_seconds_sum"], medium["search_seconds_sum"]),
        "wall_seconds_sum": _ratio(low["wall_seconds_sum"], medium["wall_seconds_sum"]),
        "admitted_sources": _ratio(low["admitted_sources"], medium["admitted_sources"]),
        "usable_pages": _ratio(low["usable_pages"], medium["usable_pages"]),
        "usable_chars": _ratio(low["usable_chars"], medium["usable_chars"]),
        "unique_hosts_sum": _ratio(low["unique_hosts_sum"], medium["unique_hosts_sum"]),
    }
    input_better = sum(
        next(
            row["provider_counters"]["input_tokens"]
            for row in values
            if row["pair"] == pair and row["context"] == "low"
        )
        < next(
            row["provider_counters"]["input_tokens"]
            for row in values
            if row["pair"] == pair and row["context"] == "medium"
        )
        for pair in range(1, prereg.PAIR_COUNT + 1)
    )
    gates = protocol["gates"]
    checks = {
        "exact_paired_terminal": all(row["terminal"] for row in values),
        "no_arm_exception": all(row["failure_type"] is None for row in values),
        "no_recursive_split": medium["recursive_split_requests"] == 0
        and low["recursive_split_requests"] == 0,
        "no_effective_search_failures": medium["effective_search_failures"]
        <= gates["maximum_effective_search_failures_per_arm"]
        and low["effective_search_failures"]
        <= gates["maximum_effective_search_failures_per_arm"],
        "no_unrecoverable_search_failures": medium["unrecoverable_search_failures"]
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
        "search_call_ratio": ratios["search_calls"]
        <= gates["maximum_low_over_medium_search_calls"],
        "input_token_ratio": ratios["search_input_tokens"]
        <= gates["maximum_low_over_medium_input_tokens"],
        "total_token_ratio": ratios["search_total_tokens"]
        <= gates["maximum_low_over_medium_total_tokens"],
        "search_wall_ratio": ratios["search_seconds_sum"]
        <= gates["maximum_low_over_medium_search_seconds"],
        "task_wall_ratio": ratios["wall_seconds_sum"]
        <= gates["maximum_low_over_medium_wall_seconds"],
        "admitted_source_yield": ratios["admitted_sources"]
        >= gates["minimum_low_over_medium_admitted_sources"],
        "usable_page_yield": ratios["usable_pages"]
        >= gates["minimum_low_over_medium_usable_pages"],
        "usable_character_yield": ratios["usable_chars"]
        >= gates["minimum_low_over_medium_usable_chars"],
        "unique_host_yield": ratios["unique_hosts_sum"]
        >= gates["minimum_low_over_medium_unique_hosts"],
        "paired_input_direction": input_better
        >= gates["minimum_pairs_with_lower_low_input_tokens"],
        "absolute_medium_yield": medium["admitted_sources"]
        >= gates["minimum_admitted_sources_per_arm"]
        and medium["usable_pages"] >= gates["minimum_usable_pages_per_arm"]
        and medium["usable_chars"] >= gates["minimum_usable_chars_per_arm"],
        "absolute_low_yield": low["admitted_sources"]
        >= gates["minimum_admitted_sources_per_arm"]
        and low["usable_pages"] >= gates["minimum_usable_pages_per_arm"]
        and low["usable_chars"] >= gates["minimum_usable_chars_per_arm"],
        "absolute_batch_wall": float(batch_wall) <= gates["maximum_batch_wall_seconds"],
    }
    pair_directions: dict[str, dict[str, int]] = {}
    for name, extractor, lower_better in (
        ("search_input_tokens", lambda row: row["provider_counters"]["input_tokens"], True),
        ("search_total_tokens", lambda row: row["provider_counters"]["total_tokens"], True),
        ("wall_seconds", lambda row: row["wall_seconds"], True),
        ("usable_pages", lambda row: row["usable_pages"], False),
    ):
        better = tie = worse = 0
        for pair in range(1, prereg.PAIR_COUNT + 1):
            by_context = {row["context"]: row for row in values if row["pair"] == pair}
            delta = float(extractor(by_context["low"])) - float(
                extractor(by_context["medium"])
            )
            if abs(delta) <= 1e-12:
                tie += 1
            elif (delta < 0) is lower_better:
                better += 1
            else:
                worse += 1
        pair_directions[name] = {
            "low_better": better,
            "tie": tie,
            "low_worse": worse,
        }
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
        value.get("role") != "v24285_neutral_single_query_context_pair_result"
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
        raise RuntimeError("V2.42.85 result drifted")


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
                max_workers=prereg.ARM_CONCURRENCY,
                thread_name_prefix="v24285-single-query-context-pair",
            ) as pool:
                futures = [
                    pool.submit(_run_arm, protocol, row["pair"], row["context"])
                    for row in wave
                ]
                rows.extend(future.result() for future in futures)
    batch_wall = max(0.0, time.monotonic() - started)
    summary = summarize(protocol, rows, batch_wall)
    value = {
        "artifact_version": 1,
        "role": "v24285_neutral_single_query_context_pair_result",
        "created_at_unix": int(time.time()),
        "protocol_id": prereg.PROTOCOL_ID,
        "protocol_sha256": sha256(root / prereg.OUTPUT),
        "arms": sorted(rows, key=lambda row: (row["pair"], row["context"])),
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
                "low_over_medium": result["summary"]["low_over_medium"],
            },
            sort_keys=True,
        )
    )
