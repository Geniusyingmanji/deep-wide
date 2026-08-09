#!/usr/bin/env python3
"""Content-free paired capability gate for the two local Responses proxies.

Eight fixed pairs of neutral public-software documentation queries are sent
once to each endpoint.  Provider payloads are inspected only in memory.  The
persistent surface contains arm-level counts and latency, never queries, URLs,
titles, snippets, answers, provider payloads, or per-task rows.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.native_search import (  # noqa: E402
    _response_text_and_annotations,
    _web_search_actions,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24278_search_context_pair import (  # noqa: E402
    NEUTRAL_QUERY_PAIRS,
)


DATE = "20260809"
PROTOCOL_ID = "v24956_neutral_dual_responses_transport_gate_v1"
PROTOCOL = Path(
    f"results/v24956_neutral_dual_transport_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v24956_neutral_dual_transport_result_v1_{DATE}.json")
AUDIT = Path(
    f"results/v24956_neutral_dual_transport_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24956_neutral_dual_transport_v1_{DATE}")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")

CONTROL_ARM = "control_9878"
CANDIDATE_ARM = "candidate_8787"
ARMS = {
    CONTROL_ARM: "http://127.0.0.1:9878/responses",
    CANDIDATE_ARM: "http://127.0.0.1:8787/responses",
}
MODEL = "gpt-5.6-sol"
TASKS_PER_ARM = 8
QUERIES_PER_TASK = 2
QUERY_ROWS_PER_ARM = TASKS_PER_ARM * QUERIES_PER_TASK
TOTAL_INVOCATIONS = TASKS_PER_ARM * len(ARMS)
EXECUTOR_CONCURRENCY = TOTAL_INVOCATIONS
RESULTS_PER_QUERY = 3
TASK_DEADLINE_SECONDS = 90.0
REQUEST_TIMEOUT_SECONDS = 80
MAX_BATCH_WALL_SECONDS = 120.0
MAX_TASK_P95_SECONDS = 75.0

PROTECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
SOURCES = (
    Path("scripts/v24956_neutral_dual_transport_gate.py"),
    Path("tests/test_v24956_neutral_dual_transport_gate.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24287_hard_deadline_fetch.py"),
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
        raise RuntimeError("V2.49.56 requires a clean pushed HEAD")


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
        raise RuntimeError(f"V2.49.56 expected ordinary tracked source: {relative}")
    return path


def _manifest(*, tracked: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        path = _ordinary(relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.49.56 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _read(relative: Path) -> dict[str, Any]:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.49.56 expected ordinary repository object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.56 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def expected_watchers() -> list[dict[str, Any]]:
    return [
        {"pid": pid, "start_ticks": ticks, "marker": marker}
        for pid, ticks, marker in PROTECTED_WATCHERS
    ]


def _watchers() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, expected_ticks, marker in PROTECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        cmdline = Path("/proc") / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.49.56 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if (
            len(suffix) <= 19
            or int(suffix[19]) != expected_ticks
            or marker not in command
        ):
            raise RuntimeError("V2.49.56 protected watcher drifted")
        output.append(
            {"pid": pid, "start_ticks": expected_ticks, "marker": marker}
        )
    return output


def _lease_inactive() -> bool:
    path = ROOT / LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def query_vector() -> tuple[tuple[str, ...], ...]:
    if len(NEUTRAL_QUERY_PAIRS) != TASKS_PER_ARM:
        raise RuntimeError("V2.49.56 neutral query population drifted")
    return tuple(tuple(str(query) for query in pair) for pair in NEUTRAL_QUERY_PAIRS)


def invocation_schedule() -> tuple[tuple[str, int], ...]:
    output: list[tuple[str, int]] = []
    arm_names = tuple(ARMS)
    for index in range(TASKS_PER_ARM):
        order = arm_names if index % 2 == 0 else tuple(reversed(arm_names))
        output.extend((arm, index) for arm in order)
    return tuple(output)


def source_policy() -> dict[str, bool]:
    return {
        "neutral_public_software_documentation_queries_only": True,
        "query_url_title_snippet_page_answer_provider_payload_or_per_task_row_persisted": False,
        "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "credential_value_environment_or_keyring_read": False,
        "public_page_fetch_task_answer_synthesis_or_evaluator_effect": False,
    }


def gates() -> dict[str, Any]:
    return {
        "control_reference": {
            "terminal_task_count": TASKS_PER_ARM,
            "minimum_successful_task_count": 6,
            "minimum_successful_query_rows": 12,
            "minimum_query_rows_with_url_citation": 12,
            "minimum_url_citations": 12,
            "minimum_web_search_actions": 6,
            "minimum_action_sources": 6,
            "provider_attempts": TASKS_PER_ARM,
            "provider_response_calls": TASKS_PER_ARM,
            "http_2xx": TASKS_PER_ARM,
            "maximum_transport_failures": 0,
            "maximum_deadline_failures": 0,
            "maximum_task_p95_seconds": MAX_TASK_P95_SECONDS,
            "positive_total_tokens": True,
        },
        "candidate_absolute": {
            "terminal_task_count": TASKS_PER_ARM,
            "successful_task_count": TASKS_PER_ARM,
            "successful_query_rows": QUERY_ROWS_PER_ARM,
            "query_rows_with_url_citation": QUERY_ROWS_PER_ARM,
            "minimum_url_citations": QUERY_ROWS_PER_ARM,
            "minimum_web_search_actions": TASKS_PER_ARM,
            "minimum_action_sources": TASKS_PER_ARM,
            "provider_attempts": TASKS_PER_ARM,
            "provider_response_calls": TASKS_PER_ARM,
            "http_2xx": TASKS_PER_ARM,
            "maximum_transport_failures": 0,
            "maximum_deadline_failures": 0,
            "maximum_task_p95_seconds": MAX_TASK_P95_SECONDS,
            "positive_total_tokens": True,
        },
        "candidate_relative": {
            "minimum_successful_query_row_ratio": 1.0,
            "minimum_url_citation_ratio": 1.0,
            "minimum_action_source_ratio": 0.75,
            "maximum_total_token_ratio": 1.50,
            "maximum_task_p95_wall_ratio": 1.50,
        },
        "maximum_batch_wall_seconds": MAX_BATCH_WALL_SECONDS,
    }


def build_protocol(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_pristine: bool = True,
    require_watchers: bool = True,
) -> dict[str, Any]:
    if require_clean:
        _clean_pushed()
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PROTOCOL, RESULT, AUDIT, OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.49.56 future surface is not pristine")
    watchers = _watchers() if require_watchers else expected_watchers()
    manifest = _manifest(tracked=require_clean)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24956_neutral_dual_transport_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "arms": {
            name: {
                "endpoint": endpoint,
                "model": MODEL,
                "reasoning_effort": "low",
                "service_tier": "priority",
                "search_context_size": "medium",
                "max_retries": 1,
            }
            for name, endpoint in ARMS.items()
        },
        "schedule": {
            "tasks_per_arm": TASKS_PER_ARM,
            "queries_per_task": QUERIES_PER_TASK,
            "query_rows_per_arm": QUERY_ROWS_PER_ARM,
            "total_invocations": TOTAL_INVOCATIONS,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "results_per_query": RESULTS_PER_QUERY,
            "one_provider_attempt_per_invocation": True,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "query_vector_sha256": payload_sha256(query_vector()),
            "invocation_schedule_sha256": payload_sha256(invocation_schedule()),
        },
        "gates": gates(),
        "protected_watchers": watchers,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_neutral_dual_transport_gate": True,
            "production_shaped_live_exposure_gate_design": False,
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
    manifest = _manifest(tracked=True) if require_tracked else copied.get("source_manifest")
    if (
        copied.get("role") != "v24956_neutral_dual_transport_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("schedule", {}).get("tasks_per_arm") != TASKS_PER_ARM
        or copied.get("schedule", {}).get("executor_concurrency")
        != EXECUTOR_CONCURRENCY
        or copied.get("schedule", {}).get("query_vector_sha256")
        != payload_sha256(query_vector())
        or copied.get("schedule", {}).get("invocation_schedule_sha256")
        != payload_sha256(invocation_schedule())
        or copied.get("gates") != gates()
        or copied.get("protected_watchers") != expected_watchers()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get(
            "benchmark_external_or_exact220_launch"
        )
        is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.49.56 protocol drifted")
    return copied


def _client(arm: str) -> DeadlineAwareNativeSearchClient:
    if arm not in ARMS:
        raise ValueError("V2.49.56 unknown arm")
    return DeadlineAwareNativeSearchClient(
        ARMS[arm],
        MODEL,
        reasoning_effort="low",
        service_tier="priority",
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=1,
        absolute_deadline=time.monotonic() + TASK_DEADLINE_SECONDS,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.05,
        max_workers=1,
        batch_size=QUERIES_PER_TASK,
        search_context_size="medium",
        max_output_tokens=2400,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=5000,
        hard_fetch_deadline_seconds=25,
    )


def _probe(item: tuple[str, int]) -> dict[str, int | float | bool | str]:
    arm, index = item
    client = _client(arm)
    payload: dict[str, Any] | None = None
    batches: list[dict[str, Any]] = []
    complete = False
    started = time.monotonic()
    try:
        payload = client._request(list(query_vector()[index]))
        batches, complete = client._parse_batch(
            list(query_vector()[index]), payload, max_results=RESULTS_PER_QUERY
        )
    except BaseException:
        payload = None
        batches = []
        complete = False
    wall = max(0.0, time.monotonic() - started)
    actions = _web_search_actions(payload) if payload is not None else []
    _, annotations = (
        _response_text_and_annotations(payload) if payload is not None else ("", [])
    )
    successful_rows = sum(
        isinstance(batch, Mapping)
        and bool(batch.get("results"))
        and not batch.get("error")
        for batch in batches
    )
    url_citations = sum(
        len(batch.get("results") or [])
        for batch in batches
        if isinstance(batch, Mapping)
    )
    annotation_citations = sum(
        isinstance(annotation, Mapping)
        and annotation.get("type") == "url_citation"
        for annotation in annotations
    )
    action_sources = sum(len(action.get("sources") or []) for action in actions)
    health = validate_transport_health(client.transport_health())
    status_counts = dict(client.status_counts)
    return {
        "arm": arm,
        "terminal": True,
        "successful_task": complete and successful_rows == QUERIES_PER_TASK,
        "mapping_complete": complete,
        "logical_query_rows": QUERIES_PER_TASK,
        "returned_query_rows": len(batches),
        "successful_query_rows": successful_rows,
        "failed_query_rows": QUERIES_PER_TASK - successful_rows,
        "query_rows_with_url_citation": successful_rows,
        "url_citations": url_citations,
        "annotation_url_citations": annotation_citations,
        "web_search_actions": len(actions),
        "action_sources": action_sources,
        "provider_attempts": int(health["hosted_search_attempts"]),
        "provider_response_calls": int(client.calls),
        "http_2xx": sum(count for status, count in status_counts.items() if 200 <= status < 300),
        "http_4xx": sum(count for status, count in status_counts.items() if 400 <= status < 500),
        "http_5xx": sum(count for status, count in status_counts.items() if 500 <= status < 600),
        "transport_failures": int(client.transport_failures),
        "hosted_search_deadline_failures": int(
            health["hosted_search_deadline_failures"]
        ),
        "input_tokens": int(client.input_tokens),
        "output_tokens": int(client.output_tokens),
        "total_tokens": int(client.total_tokens),
        "wall_seconds": round(wall, 6),
    }


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(
        0,
        min(
            len(ordered) - 1,
            int(probability * len(ordered) + 0.999999) - 1,
        ),
    )
    return round(ordered[index], 6)


def _aggregate(
    rows: Sequence[Mapping[str, int | float | bool | str]], batch_wall: float
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for arm in ARMS:
        selected = [row for row in rows if row.get("arm") == arm]
        counts: Counter[str] = Counter()
        walls: list[float] = []
        for row in selected:
            walls.append(float(row.get("wall_seconds", 0.0)))
            for name, number in row.items():
                if name in {"arm", "wall_seconds"}:
                    continue
                counts[name] += int(number)
        output[arm] = {
            "terminal_task_count": int(counts["terminal"]),
            "successful_task_count": int(counts["successful_task"]),
            "failed_task_count": len(selected) - int(counts["successful_task"]),
            "mapping_complete_task_count": int(counts["mapping_complete"]),
            **{
                name: int(counts[name])
                for name in (
                    "logical_query_rows",
                    "returned_query_rows",
                    "successful_query_rows",
                    "failed_query_rows",
                    "query_rows_with_url_citation",
                    "url_citations",
                    "annotation_url_citations",
                    "web_search_actions",
                    "action_sources",
                    "provider_attempts",
                    "provider_response_calls",
                    "http_2xx",
                    "http_4xx",
                    "http_5xx",
                    "transport_failures",
                    "hosted_search_deadline_failures",
                    "input_tokens",
                    "output_tokens",
                    "total_tokens",
                )
            },
            "task_wall_p50_seconds": _percentile(walls, 0.50),
            "task_wall_p95_seconds": _percentile(walls, 0.95),
            "task_wall_max_seconds": round(max(walls, default=0.0), 6),
            "contains_query_url_title_snippet_page_answer_provider_payload_or_per_task_row": False,
        }
    output["batch_wall_seconds"] = round(max(0.0, float(batch_wall)), 6)
    return output


def _safe_ratio(numerator: Any, denominator: Any) -> float:
    left = float(numerator)
    right = float(denominator)
    return left / right if right > 0 else float("inf")


def decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    control = aggregate.get(CONTROL_ARM) or {}
    candidate = aggregate.get(CANDIDATE_ARM) or {}
    frozen = gates()
    control_gate = frozen["control_reference"]
    candidate_gate = frozen["candidate_absolute"]
    relative_gate = frozen["candidate_relative"]
    checks = {
        "batch_wall_within_cap": float(aggregate.get("batch_wall_seconds", 1e9))
        <= frozen["maximum_batch_wall_seconds"],
        "control_terminal": control.get("terminal_task_count")
        == control_gate["terminal_task_count"],
        "control_successful_tasks": control.get("successful_task_count", 0)
        >= control_gate["minimum_successful_task_count"],
        "control_successful_rows": control.get("successful_query_rows", 0)
        >= control_gate["minimum_successful_query_rows"],
        "control_citation_rows": control.get("query_rows_with_url_citation", 0)
        >= control_gate["minimum_query_rows_with_url_citation"],
        "control_url_citations": control.get("url_citations", 0)
        >= control_gate["minimum_url_citations"],
        "control_actions": control.get("web_search_actions", 0)
        >= control_gate["minimum_web_search_actions"],
        "control_action_sources": control.get("action_sources", 0)
        >= control_gate["minimum_action_sources"],
        "control_single_attempt": control.get("provider_attempts")
        == control_gate["provider_attempts"],
        "control_all_responses": control.get("provider_response_calls")
        == control_gate["provider_response_calls"],
        "control_all_2xx": control.get("http_2xx") == control_gate["http_2xx"],
        "control_no_transport_failure": control.get("transport_failures", 1)
        <= control_gate["maximum_transport_failures"],
        "control_no_deadline_failure": control.get(
            "hosted_search_deadline_failures", 1
        )
        <= control_gate["maximum_deadline_failures"],
        "control_p95_within_cap": float(control.get("task_wall_p95_seconds", 1e9))
        <= control_gate["maximum_task_p95_seconds"],
        "control_positive_tokens": control.get("total_tokens", 0) > 0,
        "candidate_terminal": candidate.get("terminal_task_count")
        == candidate_gate["terminal_task_count"],
        "candidate_all_tasks_successful": candidate.get("successful_task_count")
        == candidate_gate["successful_task_count"],
        "candidate_all_rows_successful": candidate.get("successful_query_rows")
        == candidate_gate["successful_query_rows"],
        "candidate_all_rows_cited": candidate.get("query_rows_with_url_citation")
        == candidate_gate["query_rows_with_url_citation"],
        "candidate_url_citations": candidate.get("url_citations", 0)
        >= candidate_gate["minimum_url_citations"],
        "candidate_actions": candidate.get("web_search_actions", 0)
        >= candidate_gate["minimum_web_search_actions"],
        "candidate_action_sources": candidate.get("action_sources", 0)
        >= candidate_gate["minimum_action_sources"],
        "candidate_single_attempt": candidate.get("provider_attempts")
        == candidate_gate["provider_attempts"],
        "candidate_all_responses": candidate.get("provider_response_calls")
        == candidate_gate["provider_response_calls"],
        "candidate_all_2xx": candidate.get("http_2xx")
        == candidate_gate["http_2xx"],
        "candidate_no_transport_failure": candidate.get("transport_failures", 1)
        <= candidate_gate["maximum_transport_failures"],
        "candidate_no_deadline_failure": candidate.get(
            "hosted_search_deadline_failures", 1
        )
        <= candidate_gate["maximum_deadline_failures"],
        "candidate_p95_within_cap": float(
            candidate.get("task_wall_p95_seconds", 1e9)
        )
        <= candidate_gate["maximum_task_p95_seconds"],
        "candidate_positive_tokens": candidate.get("total_tokens", 0) > 0,
        "candidate_success_rows_noninferior": _safe_ratio(
            candidate.get("successful_query_rows", 0),
            control.get("successful_query_rows", 0),
        )
        >= relative_gate["minimum_successful_query_row_ratio"],
        "candidate_url_citations_noninferior": _safe_ratio(
            candidate.get("url_citations", 0), control.get("url_citations", 0)
        )
        >= relative_gate["minimum_url_citation_ratio"],
        "candidate_action_sources_noninferior": _safe_ratio(
            candidate.get("action_sources", 0), control.get("action_sources", 0)
        )
        >= relative_gate["minimum_action_source_ratio"],
        "candidate_token_cost_bounded": _safe_ratio(
            candidate.get("total_tokens", 0), control.get("total_tokens", 0)
        )
        <= relative_gate["maximum_total_token_ratio"],
        "candidate_latency_bounded": _safe_ratio(
            candidate.get("task_wall_p95_seconds", 0),
            control.get("task_wall_p95_seconds", 0),
        )
        <= relative_gate["maximum_task_p95_wall_ratio"],
    }
    candidate_go = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, passed in checks.items() if not passed),
        "candidate_transport_go": candidate_go,
        "candidate_eligible_for_production_shaped_external_gate_design": candidate_go,
        "public_exact220_authorized": False,
    }


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = validate_protocol(_read(PROTOCOL))
    aggregate = copied.get("aggregate") or {}
    computed = decision(aggregate)
    passed = computed["candidate_transport_go"] is True
    if (
        copied.get("role") != "v24956_neutral_dual_transport_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("protected_watchers_before") != protocol["protected_watchers"]
        or copied.get("protected_watchers_after") != protocol["protected_watchers"]
        or copied.get("decision") != computed
        or copied.get("passed") is not passed
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization")
        != {
            "production_shaped_live_exposure_gate_design": passed,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.56 result drifted")
    return copied


def run() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (RESULT, AUDIT, OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.49.56 result surface is not pristine")
    watchers_before = _watchers()
    for endpoint in ARMS.values():
        port = int(endpoint.split(":")[2].split("/")[0])
        with socket.create_connection(("127.0.0.1", port), timeout=2.0):
            pass
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v24956_neutral_dual_transport_gate",
        purpose="content_free_paired_local_responses_transport_capability",
        path=ROOT / LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(_probe, invocation_schedule()))
    aggregate = _aggregate(rows, time.monotonic() - started)
    watchers_after = _watchers()
    computed = decision(aggregate)
    passed = computed["candidate_transport_go"] is True
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24956_neutral_dual_transport_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "protected_watchers_before": watchers_before,
        "protected_watchers_after": watchers_after,
        "aggregate": aggregate,
        "decision": computed,
        "passed": passed,
        "source_policy": protocol["source_policy"],
        "authorization": {
            "production_shaped_live_exposure_gate_design": passed,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    publish_new(ROOT / OUTPUT_ROOT / "aggregate.json", value)
    publish_new(ROOT / RESULT, value)
    return validate_result(value)


def audit() -> dict[str, Any]:
    _clean_pushed()
    if (ROOT / AUDIT).exists() or (ROOT / AUDIT).is_symlink():
        raise RuntimeError("V2.49.56 audit surface is not pristine")
    protocol = validate_protocol(_read(PROTOCOL))
    result = validate_result(_read(RESULT))
    output = _read(OUTPUT_ROOT / "aggregate.json")
    current_watchers = _watchers()
    checks = {
        "protocol_and_result_validate": True,
        "output_copy_matches_result": output == result,
        "fixed_arm_task_counts": all(
            result["aggregate"][arm]["terminal_task_count"] == TASKS_PER_ARM
            for arm in ARMS
        ),
        "persistent_aggregate_is_content_free": all(
            result["aggregate"][arm][
                "contains_query_url_title_snippet_page_answer_provider_payload_or_per_task_row"
            ]
            is False
            for arm in ARMS
        ),
        "protected_watchers_unchanged": current_watchers
        == protocol["protected_watchers"]
        == result["protected_watchers_before"]
        == result["protected_watchers_after"],
        "shared_api_lease_released": _lease_inactive(),
        "decision_recomputes_exactly": result["decision"]
        == decision(result["aggregate"]),
        "no_benchmark_or_evaluator_authority": result["authorization"][
            "benchmark_external_or_exact220_launch"
        ]
        is False
        and result["authorization"]["evaluator"] is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    audit_valid = not findings
    candidate_go = result["passed"] is True and audit_valid
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24956_neutral_dual_transport_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "result_sha256": sha256(ROOT / RESULT),
        "output_sha256": sha256(ROOT / OUTPUT_ROOT / "aggregate.json"),
        "checks": checks,
        "findings": findings,
        "audit_valid": audit_valid,
        "candidate_transport_go": candidate_go,
        "source_policy": source_policy(),
        "authorization": {
            "production_shaped_live_exposure_gate_design": candidate_go,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    publish_new(ROOT / AUDIT, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "run", "audit"))
    args = parser.parse_args()
    if args.command == "protocol":
        value = build_protocol()
        publish_new(ROOT / PROTOCOL, value)
        output = {"path": str(PROTOCOL), "role": value["role"]}
    elif args.command == "run":
        value = run()
        output = {"path": str(RESULT), "passed": value["passed"]}
    else:
        value = audit()
        output = {
            "path": str(AUDIT),
            "audit_valid": value["audit_valid"],
            "candidate_transport_go": value["candidate_transport_go"],
        }
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
