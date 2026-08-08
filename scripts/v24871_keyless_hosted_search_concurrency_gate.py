#!/usr/bin/env python3
"""Aggregate-only current-capacity gate for keyless GPT-5.6 hosted search.

Twenty independent clients each submit one four-query batch of neutral public
software-documentation queries to the local Azure Responses proxy.  This
matches the intended full-run task concurrency and logical-query shape without
using benchmark tasks, predictions, mappings, labels, gold, or evaluators.
Only aggregate counters and latency are persisted; queries, URLs, titles,
snippets, pages, answers, provider payloads, and per-worker rows are discarded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24278_search_context_pair import (  # noqa: E402
    NEUTRAL_QUERY_PAIRS,
)


DATE = "20260808"
PROTOCOL_ID = "v24871_keyless_gpt56_hosted_search_concurrency_gate_v1"
PROTOCOL = Path(
    f"results/v24871_keyless_search_concurrency_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24871_keyless_search_concurrency_result_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24871_keyless_search_concurrency_v1_{DATE}")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
ENDPOINT = "http://127.0.0.1:9878/responses"
MODEL = "gpt-5.6-sol"
EXECUTOR_CONCURRENCY = 20
TASK_COUNT = 20
LOGICAL_QUERIES_PER_TASK = 4
TOTAL_LOGICAL_QUERIES = TASK_COUNT * LOGICAL_QUERIES_PER_TASK
RESULTS_PER_QUERY = 3
TASK_DEADLINE_SECONDS = 90.0
P95_WALL_GATE_SECONDS = 60.0
MAX_BATCH_WALL_SECONDS = 120.0
BASE_QUERIES = tuple(query for pair in NEUTRAL_QUERY_PAIRS for query in pair)
SOURCES = (
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24287_hard_deadline_fetch.py"),
    Path("scripts/v24871_keyless_hosted_search_concurrency_gate.py"),
    Path("tests/test_v24871_keyless_hosted_search_concurrency_gate.py"),
    Path("scripts/deepwide_api_lease.py"),
    Path("scripts/preregister_v24278_search_context_pair.py"),
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.71 gate requires clean pushed HEAD")


def _ordinary(relative: Path, *, tracked: bool) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or tracked
        and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        != 0
    ):
        raise RuntimeError(f"V2.48.71 source is not ordinary/tracked: {relative}")
    return path


def _manifest(*, tracked: bool) -> dict[str, str]:
    value: dict[str, str] = {}
    for relative in SOURCES:
        path = _ordinary(relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.48.71 credential literal in {relative}")
        value[str(relative)] = sha256(path)
    return value


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.48.71 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.71 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def task_queries(index: int) -> tuple[str, ...]:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < TASK_COUNT:
        raise ValueError("V2.48.71 neutral task index is invalid")
    offset = (index * LOGICAL_QUERIES_PER_TASK) % len(BASE_QUERIES)
    return tuple(
        BASE_QUERIES[(offset + delta) % len(BASE_QUERIES)]
        for delta in range(LOGICAL_QUERIES_PER_TASK)
    )


def query_vector() -> tuple[tuple[str, ...], ...]:
    return tuple(task_queries(index) for index in range(TASK_COUNT))


def build_protocol(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean:
        _clean_pushed()
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PROTOCOL, RESULT, OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.48.71 future surface is not pristine")
    manifest = _manifest(tracked=require_clean)
    value = {
        "artifact_version": 1,
        "role": "v24871_keyless_search_concurrency_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "provider": {
            "endpoint": ENDPOINT,
            "model": MODEL,
            "keyless": True,
            "reasoning_effort": "low",
            "service_tier": "priority",
            "search_context_size": "medium",
            "max_retries": 2,
        },
        "schedule": {
            "task_count": TASK_COUNT,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "logical_queries_per_task": LOGICAL_QUERIES_PER_TASK,
            "total_logical_queries": TOTAL_LOGICAL_QUERIES,
            "results_per_query": RESULTS_PER_QUERY,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "query_vector_sha256": payload_sha256(query_vector()),
            "one_batched_hosted_search_invocation_per_task_intended": True,
        },
        "gates": {
            "terminal_task_count": TASK_COUNT,
            "successful_task_count": TASK_COUNT,
            "failed_task_count": 0,
            "logical_query_rows": TOTAL_LOGICAL_QUERIES,
            "successful_query_rows": TOTAL_LOGICAL_QUERIES,
            "failed_query_rows": 0,
            "minimum_provider_response_calls": TASK_COUNT,
            "maximum_provider_response_calls": TASK_COUNT,
            "minimum_tool_calls": TASK_COUNT,
            "maximum_transport_failures": 0,
            "maximum_hosted_search_deadline_failures": 0,
            "maximum_task_p95_wall_seconds": P95_WALL_GATE_SECONDS,
            "maximum_batch_wall_seconds": MAX_BATCH_WALL_SECONDS,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "neutral_public_software_documentation_queries_only": True,
            "query_url_title_snippet_page_answer_provider_payload_or_per_task_row_persisted": False,
            "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
            "credential_value_environment_or_keyring_read": False,
            "public_page_fetch_model_synthesis_or_evaluator_effect": False,
        },
        "authorization": {
            "one_current_keyless_concurrency_gate": True,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value, require_tracked=require_clean)


def validate_protocol(
    value: Mapping[str, Any], *, require_tracked: bool = True
) -> dict[str, Any]:
    copied = dict(value)
    manifest = (
        _manifest(tracked=True)
        if require_tracked
        else copied.get("source_manifest")
    )
    if (
        copied.get("role")
        != "v24871_keyless_search_concurrency_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("provider", {}).get("endpoint") != ENDPOINT
        or copied.get("provider", {}).get("model") != MODEL
        or copied.get("schedule", {}).get("task_count") != TASK_COUNT
        or copied.get("schedule", {}).get("executor_concurrency")
        != EXECUTOR_CONCURRENCY
        or copied.get("schedule", {}).get("total_logical_queries")
        != TOTAL_LOGICAL_QUERIES
        or copied.get("schedule", {}).get("query_vector_sha256")
        != payload_sha256(query_vector())
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("authorization")
        != {
            "one_current_keyless_concurrency_gate": True,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.71 protocol drifted")
    return copied


def _client(deadline: float) -> DeadlineAwareNativeSearchClient:
    return DeadlineAwareNativeSearchClient(
        ENDPOINT,
        MODEL,
        reasoning_effort="low",
        service_tier="priority",
        timeout=80,
        max_retries=2,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.05,
        max_workers=1,
        batch_size=8,
        search_context_size="medium",
        max_output_tokens=7000,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=5000,
        hard_fetch_deadline_seconds=25,
    )


def _probe(index: int) -> dict[str, int | float | bool]:
    client = _client(time.monotonic() + TASK_DEADLINE_SECONDS)
    started = time.monotonic()
    try:
        batches = client.search_many(
            task_queries(index),
            max_results=RESULTS_PER_QUERY,
            search_depth="advanced",
            include_raw_content=False,
        )
    except BaseException:
        batches = []
    wall = max(0.0, time.monotonic() - started)
    health = validate_transport_health(client.transport_health())
    successful_rows = sum(
        isinstance(batch, Mapping)
        and bool(batch.get("results"))
        and not batch.get("error")
        for batch in batches
    )
    query_rows = len(batches)
    return {
        "terminal": True,
        "successful_task": query_rows == LOGICAL_QUERIES_PER_TASK
        and successful_rows == LOGICAL_QUERIES_PER_TASK,
        "logical_query_rows": query_rows,
        "successful_query_rows": successful_rows,
        "failed_query_rows": max(0, query_rows - successful_rows),
        "provider_response_calls": int(client.calls),
        "tool_calls": int(client.tool_calls),
        "transport_failures": int(client.transport_failures),
        "hosted_search_attempts": int(health["hosted_search_attempts"]),
        "hosted_search_deadline_failures": int(
            health["hosted_search_deadline_failures"]
        ),
        "input_tokens": int(client.input_tokens),
        "output_tokens": int(client.output_tokens),
        "total_tokens": int(client.total_tokens),
        "wall_seconds": round(wall, 6),
    }


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int(probability * len(ordered) + 0.999999) - 1))
    return round(ordered[index], 6)


def _aggregate(rows: list[dict[str, int | float | bool]], batch_wall: float) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    walls: list[float] = []
    successes = 0
    for row in rows:
        successes += int(row["successful_task"] is True)
        walls.append(float(row["wall_seconds"]))
        for name, value in row.items():
            if name not in {"terminal", "successful_task", "wall_seconds"}:
                counts[name] += int(value)
    return {
        "terminal_task_count": sum(row["terminal"] is True for row in rows),
        "successful_task_count": successes,
        "failed_task_count": len(rows) - successes,
        **{name: int(counts[name]) for name in sorted(counts)},
        "task_wall_p50_seconds": _percentile(walls, 0.50),
        "task_wall_p95_seconds": _percentile(walls, 0.95),
        "task_wall_max_seconds": round(max(walls, default=0.0), 6),
        "batch_wall_seconds": round(max(0.0, batch_wall), 6),
        "contains_query_url_title_snippet_page_answer_provider_payload_or_per_task_row": False,
    }


def _passed(aggregate: Mapping[str, Any], gates: Mapping[str, Any]) -> bool:
    return (
        aggregate.get("terminal_task_count") == gates["terminal_task_count"]
        and aggregate.get("successful_task_count") == gates["successful_task_count"]
        and aggregate.get("failed_task_count") == gates["failed_task_count"]
        and aggregate.get("logical_query_rows") == gates["logical_query_rows"]
        and aggregate.get("successful_query_rows") == gates["successful_query_rows"]
        and aggregate.get("failed_query_rows") == gates["failed_query_rows"]
        and gates["minimum_provider_response_calls"]
        <= aggregate.get("provider_response_calls", -1)
        <= gates["maximum_provider_response_calls"]
        and aggregate.get("tool_calls", 0) >= gates["minimum_tool_calls"]
        and aggregate.get("transport_failures", 1)
        <= gates["maximum_transport_failures"]
        and aggregate.get("hosted_search_deadline_failures", 1)
        <= gates["maximum_hosted_search_deadline_failures"]
        and float(aggregate.get("task_wall_p95_seconds", 1e9))
        <= gates["maximum_task_p95_wall_seconds"]
        and float(aggregate.get("batch_wall_seconds", 1e9))
        <= gates["maximum_batch_wall_seconds"]
    )


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    aggregate = copied.get("aggregate") or {}
    passed = _passed(aggregate, protocol["gates"])
    if (
        copied.get("role") != "v24871_keyless_search_concurrency_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("passed") is not passed
        or copied.get("source_policy") != protocol["source_policy"]
        or copied.get("authorization")
        != {
            "benchmark_external_transport_design": passed,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.48.71 result drifted")
    return copied


def run() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (RESULT, OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.48.71 result surface is not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v24871_keyless_hosted_search_concurrency_gate",
        purpose="current_neutral_20x4_hosted_search_capacity_only",
        path=ROOT / LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(_probe, range(TASK_COUNT)))
    aggregate = _aggregate(rows, time.monotonic() - started)
    passed = _passed(aggregate, protocol["gates"])
    value = {
        "artifact_version": 1,
        "role": "v24871_keyless_search_concurrency_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "aggregate": aggregate,
        "passed": passed,
        "source_policy": protocol["source_policy"],
        "authorization": {
            "benchmark_external_transport_design": passed,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    publish_new(ROOT / OUTPUT_ROOT / "aggregate.json", value)
    publish_new(ROOT / RESULT, value)
    return validate_result(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "run"))
    args = parser.parse_args()
    if args.command == "protocol":
        value = build_protocol()
        publish_new(ROOT / PROTOCOL, value)
        print(json.dumps({"path": str(PROTOCOL), "role": value["role"]}))
    else:
        value = run()
        print(json.dumps({"path": str(RESULT), "passed": value["passed"]}))


if __name__ == "__main__":
    main()
