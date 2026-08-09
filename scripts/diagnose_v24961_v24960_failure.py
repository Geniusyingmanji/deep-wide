#!/usr/bin/env python3
"""Content-free diagnosis of the V2.49.60 second-wave failure signature."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24959_source_fair_discovery import compare_prefixes  # noqa: E402
from deepwide_agent.v24961_cumulative_source_fair import (  # noqa: E402
    compare_cumulative_prefixes,
)


DATE = "20260809"
PARENT = Path("results/v24960_source_fair_live_result_v1_20260809.json")
OUTPUT = Path(f"results/v24961_v24960_failure_diagnosis_v1_{DATE}.json")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("V2.49.61 expected ordinary repository object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.61 expected object")
    return value


def _source(host: str, suffix: str) -> dict[str, str]:
    return {"type": "url", "title": "", "url": f"https://{host}/{suffix}", "fetch_url": f"https://{host}/{suffix}"}


def _wave(actions: list[list[dict[str, str]]]) -> list[dict]:
    return [{"query": "discarded", "answer": "discarded", "results": [], "error": None, "hosted_search_trace": {"actions": [{"sources": values} for values in actions]}}]


def synthetic_reproduction() -> dict[str, Any]:
    first_raw = _wave([
        [
            _source("alpha.example", "a1"),
            _source("alpha.example", "a2"),
            _source("alpha.example", "a3"),
        ],
        [_source("beta.example", "b1")],
        [_source("gamma.example", "g1")],
    ])
    first = compare_cumulative_prefixes(first_raw, cap=3)
    second_raw = _wave([
        [
            _source("alpha.example", "a4"),
            _source("beta.example", "b2"),
            _source("gamma.example", "g2"),
        ],
        [_source("alpha.example", "a5")],
        [_source("delta.example", "d1")],
    ])
    legacy_raised = False
    try:
        compare_prefixes(
            second_raw,
            cap=3,
            prior_control_urls={item["url"] for item in first["stable"]},
            prior_candidate_urls={item["url"] for item in first["candidate"]},
            prior_candidate_sources=first["candidate_cumulative_sources"],
        )
    except RuntimeError:
        legacy_raised = True
    repaired = compare_cumulative_prefixes(
        second_raw,
        cap=3,
        prior_control_urls={item["url"] for item in first["stable"]},
        prior_candidate_urls={item["url"] for item in first["candidate"]},
        prior_control_sources=first["control_cumulative_sources"],
        prior_candidate_sources=first["candidate_cumulative_sources"],
    )
    receipt = repaired["receipt"]
    return {
        "legacy_local_invariant_raises": legacy_raised,
        "repaired_cumulative_invariant_accepts": True,
        "candidate_current_sources": receipt["candidate_current_registrable_source_count"],
        "control_current_sources": receipt["stable_current_registrable_source_count"],
        "candidate_cumulative_sources": receipt["candidate_cumulative_registrable_source_count"],
        "control_cumulative_sources": receipt["stable_cumulative_registrable_source_count"],
        "contains_query_url_page_prediction_or_score": False,
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    parent = _read(ROOT / PARENT)
    aggregate = parent.get("aggregate") or {}
    signature = {
        "terminal_tasks": int(aggregate.get("terminal_task_count", 0)),
        "completed_tasks": int(aggregate.get("completed_task_count", 0)),
        "failed_tasks": int(aggregate.get("failed_task_count", 0)),
        "search_provider_attempts": int(aggregate.get("search_provider_attempts", 0)),
        "search_provider_response_calls": int(aggregate.get("search_provider_response_calls", 0)),
        "search_http_2xx": int(aggregate.get("search_http_2xx", 0)),
        "logical_query_rows": int(aggregate.get("logical_query_rows", 0)),
        "expected_rows_if_failures_stop_after_second_response_before_second_selection_commit": int(aggregate.get("completed_task_count", 0)) * 4 + int(aggregate.get("failed_task_count", 0)) * 2,
        "planned_shared_url_union_count": int(aggregate.get("physical_union_fetches", 0)),
        "actual_hard_fetch_helper_calls": int(aggregate.get("hard_fetch_helper_calls", 0)),
    }
    synthetic = synthetic_reproduction()
    checks = {
        "all_provider_attempts_and_responses_completed": signature["search_provider_attempts"] == 40 == signature["search_provider_response_calls"] == signature["search_http_2xx"],
        "logical_row_signature_matches_second_wave_postresponse_failure": signature["logical_query_rows"] == signature["expected_rows_if_failures_stop_after_second_response_before_second_selection_commit"],
        "unfetched_planned_union_tail_exists": signature["planned_shared_url_union_count"] > signature["actual_hard_fetch_helper_calls"],
        "legacy_local_invariant_reproduced_synthetically": synthetic["legacy_local_invariant_raises"],
        "cumulative_successor_accepts_same_synthetic_state": synthetic["repaired_cumulative_invariant_accepts"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24961_v24960_content_free_failure_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(ROOT / PARENT)},
        "aggregate_signature": signature,
        "synthetic_reproduction": synthetic,
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "conclusion": "v24960 is consistent with the legacy current-wave source invariant rejecting a valid cumulative two-wave state; v24961 repairs that invariant without claiming per-task exception recovery",
        "source_policy": {
            "parent_aggregate_only": True,
            "parent_task_query_url_page_prediction_or_evaluator_opened": False,
            "synthetic_values_only": True,
            "network_model_search_fetch_or_evaluator_effect": False,
        },
        "authorization": {
            "fresh_successor_live_gate_design": not findings,
            "same_population_retry_resume_or_rerun": False,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("diagnose",))
    parser.parse_args()
    value = build()
    publish(value)
    print(json.dumps({"path": str(OUTPUT), "diagnosis_valid": value["diagnosis_valid"]}, sort_keys=True))


if __name__ == "__main__":
    main()
