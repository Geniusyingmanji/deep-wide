#!/usr/bin/env python3
"""Current 20-way gate for keyless task-union two-wave retrieval.

Each benchmark-external task sends four neutral public-documentation queries
through the local GPT-5.6 hosted-search endpoint.  The existing task-local
source-union layer may recover action sources when query-local citation spans
are incomplete; only deterministic public-page fetches become active evidence.
The gate persists aggregate counters and latency only, never query, URL, page,
answer, provider payload, task identity, prediction, label, gold, or evaluator
content.
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

from deepwide_agent.v24272_two_wave_entropy_voc import (  # noqa: E402
    TwoWavePolicy,
)
from deepwide_agent.v24272_two_wave_retrieval import (  # noqa: E402
    run_two_wave_retrieval,
    validate_retrieval_receipt,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260808"
PROTOCOL_ID = "v24872_keyless_task_union_two_wave_concurrency_gate_v1"
PROTOCOL = Path(
    f"results/v24872_keyless_union_retrieval_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24872_keyless_union_retrieval_result_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24872_keyless_union_retrieval_v1_{DATE}")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
ENDPOINT = "http://127.0.0.1:9878/responses"
MODEL = "gpt-5.6-sol"
TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
LOGICAL_QUERIES_PER_TASK = 4
TOTAL_LOGICAL_QUERIES = TASK_COUNT * LOGICAL_QUERIES_PER_TASK
FETCHES_PER_TASK = 10
TOTAL_FETCHES = TASK_COUNT * FETCHES_PER_TASK
RESULTS_PER_QUERY = 3
TASK_DEADLINE_SECONDS = 150.0
PRODUCTS = (
    ("CMake", "3.30"),
    ("Git", "2.46"),
    ("LLVM", "18"),
    ("Docker Engine", "27"),
    ("Terraform", "1.9"),
    ("Redis", "7.4"),
    ("NGINX", "1.27"),
    ("Pandas", "2.2"),
    ("NumPy", "2.0"),
    ("Django", "5.1"),
    ("Flask", "3.0"),
    ("FastAPI", "0.112"),
    ("PyTorch", "2.4"),
    ("TensorFlow", "2.17"),
    ("Apache Spark", "3.5"),
    ("Apache Kafka", "3.8"),
    ("Prometheus", "2.54"),
    ("Grafana", "11"),
    ("OpenSSL", "3.3"),
    ("curl", "8.9"),
)
QUERY_PATTERNS = (
    "{product} {version} official documentation release notes",
    "{product} {version} official documentation installation guide",
    "{product} {version} official documentation API reference",
    "{product} {version} official documentation security changes",
)
POLICY = TwoWavePolicy(
    wave1_queries=2,
    wave1_fetches=6,
    wave2_queries=2,
    wave2_fetches=4,
    minimum_usable_pages=6,
    minimum_novel_pages=6,
    minimum_unique_hosts=6,
    content_chars_per_column=1_000_000_000,
    maximum_wave1_seconds=100.0,
    latency_loss_per_second=0.0,
    information_gain_weight=0.0,
    minimum_net_value=-1.0,
    beta_prior_alpha=1.0,
    beta_prior_beta=1.0,
)
SOURCES = (
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24270_budget_equivalent_union.py"),
    Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
    Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24287_hard_deadline_fetch.py"),
    Path("scripts/v24872_keyless_union_retrieval_gate.py"),
    Path("tests/test_v24872_keyless_union_retrieval_gate.py"),
    Path("scripts/deepwide_api_lease.py"),
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
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.72 gate requires clean pushed HEAD")


def _ordinary(relative: Path, *, tracked: bool) -> Path:
    path = ROOT / relative
    tracked_ok = not tracked or subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
        or not tracked_ok
    ):
        raise RuntimeError(f"V2.48.72 source is not ordinary/tracked: {relative}")
    return path


def _manifest(*, tracked: bool) -> dict[str, str]:
    value: dict[str, str] = {}
    for relative in SOURCES:
        path = _ordinary(relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.48.72 credential literal in {relative}")
        value[str(relative)] = sha256(path)
    return value


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("V2.48.72 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.72 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def query_vector() -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(pattern.format(product=product, version=version) for pattern in QUERY_PATTERNS)
        for product, version in PRODUCTS
    )


def policy_dict() -> dict[str, Any]:
    return dict(POLICY.__dict__)


def gates() -> dict[str, Any]:
    return {
        "terminal_task_count": TASK_COUNT,
        "completed_retrieval_count": TASK_COUNT,
        "failed_retrieval_count": 0,
        "logical_queries": TOTAL_LOGICAL_QUERIES,
        "fetches_attempted": TOTAL_FETCHES,
        "minimum_task_fetches_attempted": FETCHES_PER_TASK,
        "minimum_total_usable_pages": 140,
        "minimum_task_usable_pages": 6,
        "maximum_unrecoverable_search_failures": 0,
        "minimum_provider_response_calls": 40,
        "maximum_provider_response_calls": 80,
        "maximum_transport_failures": 0,
        "maximum_hosted_search_deadline_failures": 0,
        "maximum_hard_fetch_deadline_failures": 0,
        "maximum_fetch_helper_failures": 40,
        "maximum_task_p95_wall_seconds": 120.0,
        "maximum_batch_wall_seconds": 170.0,
    }


def build_protocol(*, now: int | None = None, require_clean: bool = True, require_pristine: bool = True) -> dict[str, Any]:
    POLICY.validate()
    if require_clean:
        _clean_pushed()
    if require_pristine and any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PROTOCOL, RESULT, OUTPUT_ROOT)):
        raise RuntimeError("V2.48.72 future surface is not pristine")
    manifest = _manifest(tracked=require_clean)
    value = {
        "artifact_version": 1,
        "role": "v24872_keyless_union_retrieval_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "provider": {"endpoint": ENDPOINT, "model": MODEL, "keyless": True, "executor_concurrency": EXECUTOR_CONCURRENCY},
        "schedule": {
            "task_count": TASK_COUNT,
            "logical_queries_per_task": LOGICAL_QUERIES_PER_TASK,
            "fetch_cap_per_task": FETCHES_PER_TASK,
            "query_vector_sha256": payload_sha256(query_vector()),
            "fixed_full_budget_no_entropy_policy": policy_dict(),
            "task_local_action_source_union": True,
            "deterministic_public_page_fetch_only_active_evidence": True,
        },
        "gates": gates(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "neutral_public_software_documentation_queries_only": True,
            "query_url_title_snippet_page_answer_provider_payload_or_per_task_row_persisted": False,
            "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
            "credential_value_environment_or_keyring_read": False,
            "model_synthesis_or_evaluator_effect": False,
            "entropy_or_information_gain_used_for_admission": False,
        },
        "authorization": {
            "one_current_keyless_union_retrieval_gate": True,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value, require_tracked=require_clean)


def validate_protocol(value: Mapping[str, Any], *, require_tracked: bool = True) -> dict[str, Any]:
    copied = dict(value)
    manifest = _manifest(tracked=True) if require_tracked else copied.get("source_manifest")
    if (
        copied.get("role") != "v24872_keyless_union_retrieval_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("schedule", {}).get("query_vector_sha256") != payload_sha256(query_vector())
        or copied.get("schedule", {}).get("fixed_full_budget_no_entropy_policy") != policy_dict()
        or copied.get("gates") != gates()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("authorization") != {
            "one_current_keyless_union_retrieval_gate": True,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.72 protocol drifted")
    return copied


def _client(deadline: float) -> DeadlineAwareNativeSearchClient:
    return DeadlineAwareNativeSearchClient(
        ENDPOINT, MODEL, reasoning_effort="low", service_tier="priority",
        timeout=120, max_retries=2, absolute_deadline=deadline,
        cleanup_reserve_seconds=5, minimum_attempt_seconds=0.05,
        max_workers=1, batch_size=8, search_context_size="medium",
        max_output_tokens=7000, fetch_pages=False, fetch_workers=8,
        fetch_timeout=20, max_page_chars=5000, hard_fetch_deadline_seconds=25,
    )


def _probe(index: int) -> dict[str, int | float | bool]:
    client = _client(time.monotonic() + TASK_DEADLINE_SECONDS)
    started = time.monotonic()
    completed = False
    total: Mapping[str, Any] = {}
    try:
        value = run_two_wave_retrieval(
            query_vector()[index], search=client, required_column_count=4,
            explicit_row_target=0, search_results_per_query=RESULTS_PER_QUERY,
            policy=POLICY, monotonic=time.monotonic,
        )
        validate_retrieval_receipt(value["receipt"])
        total = value["receipt"]["total"]
        completed = True
    except BaseException:
        completed = False
    health = validate_transport_health(client.transport_health())
    return {
        "terminal": True,
        "completed": completed,
        "logical_queries": int(total.get("queries_executed", 0)),
        "fetches_attempted": int(total.get("fetches_attempted", 0)),
        "usable_pages": int(total.get("usable_pages", 0)),
        "novel_pages": int(total.get("novel_pages", 0)),
        "unique_hosts": int(total.get("unique_hosts", 0)),
        "unrecoverable_search_failures": int(total.get("unrecoverable_search_failures", 0)),
        "provider_response_calls": int(client.calls),
        "tool_calls": int(client.tool_calls),
        "transport_failures": int(client.transport_failures),
        "hosted_search_attempts": int(health["hosted_search_attempts"]),
        "hosted_search_deadline_failures": int(health["hosted_search_deadline_failures"]),
        "hard_fetch_helper_calls": int(health["hard_fetch_helper_calls"]),
        "hard_fetch_deadline_failures": int(health["hard_fetch_deadline_failures"]),
        "fetch_helper_failures": int(health["fetch_helper_failures"]),
        "fetch_deadline_rejections": int(health["fetch_deadline_rejections"]),
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
    }


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int(probability * len(ordered) + 0.999999) - 1))
    return round(ordered[index], 6)


def _aggregate(rows: list[dict[str, int | float | bool]], batch_wall: float) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    walls: list[float] = []
    fetches: list[int] = []
    usable: list[int] = []
    completed = 0
    for row in rows:
        completed += int(row["completed"] is True)
        walls.append(float(row["wall_seconds"]))
        fetches.append(int(row["fetches_attempted"]))
        usable.append(int(row["usable_pages"]))
        for name, amount in row.items():
            if name not in {"terminal", "completed", "wall_seconds"}:
                counts[name] += int(amount)
    return {
        "terminal_task_count": sum(row["terminal"] is True for row in rows),
        "completed_retrieval_count": completed,
        "failed_retrieval_count": len(rows) - completed,
        **{name: int(counts[name]) for name in sorted(counts)},
        "minimum_task_fetches_attempted": min(fetches, default=0),
        "minimum_task_usable_pages": min(usable, default=0),
        "task_wall_p95_seconds": _percentile(walls, 0.95),
        "task_wall_max_seconds": round(max(walls, default=0.0), 6),
        "batch_wall_seconds": round(max(0.0, batch_wall), 6),
        "contains_query_url_title_snippet_page_answer_provider_payload_or_per_task_row": False,
    }


def _passed(value: Mapping[str, Any]) -> bool:
    gate = gates()
    return (
        all(value.get(name) == gate[name] for name in (
            "terminal_task_count", "completed_retrieval_count", "failed_retrieval_count",
            "logical_queries", "fetches_attempted", "minimum_task_fetches_attempted",
        ))
        and value.get("usable_pages", 0) >= gate["minimum_total_usable_pages"]
        and value.get("minimum_task_usable_pages", 0) >= gate["minimum_task_usable_pages"]
        and value.get("unrecoverable_search_failures", 1) <= gate["maximum_unrecoverable_search_failures"]
        and gate["minimum_provider_response_calls"] <= value.get("provider_response_calls", -1) <= gate["maximum_provider_response_calls"]
        and value.get("transport_failures", 1) <= gate["maximum_transport_failures"]
        and value.get("hosted_search_deadline_failures", 1) <= gate["maximum_hosted_search_deadline_failures"]
        and value.get("hard_fetch_deadline_failures", 1) <= gate["maximum_hard_fetch_deadline_failures"]
        and value.get("fetch_helper_failures", 999) <= gate["maximum_fetch_helper_failures"]
        and float(value.get("task_wall_p95_seconds", 1e9)) <= gate["maximum_task_p95_wall_seconds"]
        and float(value.get("batch_wall_seconds", 1e9)) <= gate["maximum_batch_wall_seconds"]
    )


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    aggregate = copied.get("aggregate") or {}
    passed = _passed(aggregate)
    if (
        copied.get("role") != "v24872_keyless_union_retrieval_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("passed") is not passed
        or copied.get("source_policy") != protocol["source_policy"]
        or copied.get("authorization") != {
            "fresh_benchmark_external_coverage_gate_design": passed,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.48.72 result drifted")
    return copied


def run() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (RESULT, OUTPUT_ROOT)):
        raise RuntimeError("V2.48.72 result surface is not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT, owner="v24872_keyless_union_retrieval_gate",
        purpose="neutral_20x4_query_10_fetch_task_union_capacity_only",
        path=ROOT / LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(_probe, range(TASK_COUNT)))
    aggregate = _aggregate(rows, time.monotonic() - started)
    passed = _passed(aggregate)
    value = {
        "artifact_version": 1,
        "role": "v24872_keyless_union_retrieval_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "aggregate": aggregate,
        "passed": passed,
        "source_policy": protocol["source_policy"],
        "authorization": {
            "fresh_benchmark_external_coverage_gate_design": passed,
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
