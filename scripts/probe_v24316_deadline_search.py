#!/usr/bin/env python3
"""Benchmark-external real-process probe for V2.43.16 search deadlines."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24315_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
)


FIXTURE = ROOT / "tests/fixtures/v24316_slow_fetch_child.py"
SOURCE = Path("src/deepwide_agent/v24316_deadline_search.py")
RESULT = Path("results/v24316_deadline_search_probe_v2_20260803.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _real_popen(*args: Any, **kwargs: Any) -> subprocess.Popen[str]:
    del args
    return subprocess.Popen(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(FIXTURE)],
        **kwargs,
    )


def build_report(*, now: int | None = None) -> dict[str, Any]:
    started = time.monotonic()
    absolute_deadline = started + 0.35
    client = DeadlineAwareNativeSearchClient(
        "http://unused/responses",
        "model",
        timeout=180,
        max_retries=2,
        fetch_pages=False,
        max_workers=1,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=absolute_deadline,
        cleanup_reserve_seconds=0.10,
        minimum_attempt_seconds=0.01,
        popen=_real_popen,
    )
    result = client._fetch_url("https://example.com/benchmark-external-visible")
    elapsed = max(0.0, time.monotonic() - started)
    health = client.transport_health()
    findings: list[str] = []
    if result.get("status") != "hard_deadline_exceeded":
        findings.append("real_fetch_timeout_status_mismatch")
    if not 0.15 <= elapsed <= 1.5:
        findings.append("real_fetch_timeout_wall_out_of_bounds")
    if health["hard_fetch_helper_calls"] != 1:
        findings.append("real_fetch_helper_call_count_mismatch")
    if health["hard_fetch_deadline_failures"] != 1:
        findings.append("real_fetch_deadline_count_mismatch")
    value = {
        "artifact_version": 1,
        "role": "v24316_deadline_search_benchmark_external_probe_v2",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source": {"path": str(SOURCE), "sha256": sha256(ROOT / SOURCE)},
        "real_subprocess_fetch": {
            "status": result.get("status"),
            "elapsed_seconds": round(elapsed, 6),
            "parent_deadline_seconds": 0.35,
            "cleanup_reserve_seconds": 0.10,
            "transport_health": health,
        },
        "external_effect_ledger": {
            "remote_network": 0,
            "model": 0,
            "hosted_search": 0,
            "evaluator": 0,
            "local_subprocess": 1,
        },
        "benchmark_manifest_task_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "current_v24315_run_signaled_restarted_resumed_rerun_or_modified": False,
        "findings": findings,
        "passed": not findings,
        "authorization": {
            "future_integration_design": not findings,
            "benchmark_launch": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["report_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / RESULT, report)
    print(json.dumps({"path": str(RESULT), "passed": report["passed"]}, sort_keys=True))
