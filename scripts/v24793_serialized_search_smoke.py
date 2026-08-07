#!/usr/bin/env python3
"""Corrected terminal-total neutral smoke for serialized hosted search."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24792_serialized_hosted_search import (  # noqa: E402
    SerializedThinHostedSearchClient,
    prepare_slot_directory,
    validate_receipt,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24278_search_context_pair import NEUTRAL_QUERY_PAIRS  # noqa: E402


DATE = "20260807"
PROTOCOL_ID = "v24793_terminal_total_neutral_serialized_hosted_search_smoke_v1"
PROTOCOL = Path(f"results/v24793_serialized_search_smoke_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24793_serialized_search_smoke_result_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24793_serialized_search_smoke_v1_{DATE}")
SLOT_ROOT = OUTPUT_ROOT / "slots"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
INVALID_PARENT = Path(f"results/v24792_serialized_search_smoke_invalid_execution_v1_{DATE}.json")
CONCURRENCY = 4
PAIR_COUNT = 4
LOGICAL_QUERY_COUNT = 8
SOURCES = (
    Path("src/deepwide_agent/v24792_serialized_hosted_search.py"),
    Path("scripts/v24793_serialized_search_smoke.py"),
    Path("scripts/deepwide_api_lease.py"),
    Path("scripts/preregister_v24278_search_context_pair.py"),
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.47.93 neutral smoke requires clean pushed HEAD")


def _ordinary_tracked(path: Path) -> Path:
    value = ROOT / path
    if (
        path.is_absolute() or ".." in path.parts or value.is_symlink()
        or not value.is_file() or not value.resolve().is_relative_to(ROOT.resolve())
        or subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode != 0
    ):
        raise RuntimeError(f"V2.47.93 smoke source is not tracked: {path}")
    return value


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.47.93 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.93 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _invalid_parent() -> dict[str, Any]:
    value = _read(ROOT / INVALID_PARENT)
    if (
        value.get("role") != "v24792_serialized_search_smoke_invalid_execution"
        or value.get("execution_terminal") is not True
        or value.get("invalid_for_capacity_gate") is not True
        or value.get("same_protocol_retry_resume_or_rerun_authorized") is not False
        or value.get("authorization", {}).get("corrected_new_neutral_smoke_protocol_design") is not True
    ):
        raise RuntimeError("V2.47.93 invalid parent disposition drifted")
    return value


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    parent = _invalid_parent()
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PROTOCOL, RESULT, OUTPUT_ROOT)):
        raise RuntimeError("V2.47.93 future surface is not pristine")
    manifest = {str(path): sha256(_ordinary_tracked(path)) for path in SOURCES}
    queries = [query for pair in NEUTRAL_QUERY_PAIRS[:PAIR_COUNT] for query in pair]
    value = {
        "artifact_version": 1,
        "role": "v24793_serialized_search_smoke_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "invalid_parent": {"path": str(INVALID_PARENT), "sha256": sha256(ROOT / INVALID_PARENT), "same_protocol_rerun": False, "reason": parent["invalid_reason"]},
        "correction": {
            "terminal_result_is_published_for_pass_and_fail": True,
            "passed_is_derived_from_frozen_gates": True,
            "failed_terminal_result_authorizes_no_exact220": True,
            "transport_query_set_schedule_and_gates_unchanged": True,
        },
        "schedule": {
            "outer_concurrency": CONCURRENCY,
            "shared_hosted_search_slot_cap": 1,
            "pair_count": PAIR_COUNT,
            "logical_query_count": LOGICAL_QUERY_COUNT,
            "query_vector_sha256": payload_sha256(queries),
            "timeout_seconds": 180,
            "max_retries": 2,
        },
        "gates": {"terminal_pairs": 4, "usable_query_rows": 8, "raw_query_failures": 0, "slot_timeouts": 0, "maximum_active_hosted_search_effects": 1},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "neutral_public_software_documentation_queries_only": True,
            "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
            "query_url_page_or_answer_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
        },
        "authorization": {"one_corrected_neutral_live_smoke": True, "benchmark_dev64_or_exact220": False, "evaluator": False, "leaderboard_or_sota": False},
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value)


def validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    manifest = {str(path): sha256(_ordinary_tracked(path)) for path in SOURCES}
    queries = [query for pair in NEUTRAL_QUERY_PAIRS[:PAIR_COUNT] for query in pair]
    if (
        value.get("role") != "v24793_serialized_search_smoke_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("invalid_parent", {}).get("sha256") != sha256(ROOT / INVALID_PARENT)
        or value.get("invalid_parent", {}).get("same_protocol_rerun") is not False
        or value.get("correction") != {"terminal_result_is_published_for_pass_and_fail": True, "passed_is_derived_from_frozen_gates": True, "failed_terminal_result_authorizes_no_exact220": True, "transport_query_set_schedule_and_gates_unchanged": True}
        or value.get("schedule") != {"outer_concurrency": 4, "shared_hosted_search_slot_cap": 1, "pair_count": 4, "logical_query_count": 8, "query_vector_sha256": payload_sha256(queries), "timeout_seconds": 180, "max_retries": 2}
        or value.get("source_manifest") != manifest
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("authorization") != {"one_corrected_neutral_live_smoke": True, "benchmark_dev64_or_exact220": False, "evaluator": False, "leaderboard_or_sota": False}
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.93 protocol drifted")
    return value


def _run_pair(index: int, active: dict[str, int], lock: threading.Lock) -> dict[str, Any]:
    def stage(event: str) -> None:
        with lock:
            if event == "hosted_search_effect_started":
                active["current"] += 1; active["maximum"] = max(active["maximum"], active["current"])
            elif event == "hosted_search_effect_finished":
                active["current"] -= 1
    client = SerializedThinHostedSearchClient(
        "http://127.0.0.1:9878/responses", "gpt-5.6-sol",
        reasoning_effort="low", service_tier="priority", timeout=65, max_retries=2,
        absolute_deadline=time.monotonic() + 180, cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.05, max_workers=1, batch_size=8,
        search_context_size="medium", max_output_tokens=7000, fetch_pages=False,
        fetch_workers=1, fetch_timeout=20, max_page_chars=5000,
        hard_fetch_deadline_seconds=25, search_slot_directory=ROOT / SLOT_ROOT,
        output_root=ROOT / "outputs", search_slot_cap=1, stage_callback=stage,
    )
    started = time.monotonic()
    batches = client.search_many(list(NEUTRAL_QUERY_PAIRS[index]), max_results=3, search_depth="advanced", include_raw_content=False)
    return {
        "pair": index + 1, "terminal": True, "logical_query_rows": len(batches),
        "usable_query_rows": sum(bool(row.get("results")) for row in batches),
        "raw_query_failures": sum(bool(row.get("error")) for row in batches),
        "provider_calls": int(client.calls), "provider_tool_calls": int(client.tool_calls),
        "transport_failures": int(client.transport_failures),
        "wall_seconds": round(time.monotonic() - started, 6),
        "search_slot_receipt": client.search_slot_receipt(),
        "query_url_page_or_answer_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def validate_result(value: dict[str, Any]) -> dict[str, Any]:
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    rows = value.get("pairs") or []
    for row in rows: validate_receipt(row.get("search_slot_receipt") or {})
    aggregate = value.get("aggregate") or {}
    expected_pass = all(aggregate.get(name) == expected for name, expected in protocol["gates"].items())
    expected_auth = {"exact220_protocol_design": expected_pass, "exact220_launch": False, "evaluator": False, "leaderboard_or_sota": False}
    if (
        value.get("role") != "v24793_serialized_search_smoke_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or not isinstance(rows, list) or len(rows) != PAIR_COUNT
        or [row.get("pair") for row in rows] != list(range(1, PAIR_COUNT + 1))
        or any(row.get("terminal") is not True for row in rows)
        or value.get("passed") is not expected_pass
        or value.get("source_policy") != protocol["source_policy"]
        or value.get("authorization") != expected_auth
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.93 result drifted")
    return value


def run() -> dict[str, Any]:
    _clean_pushed(); protocol = validate_protocol(_read(ROOT / PROTOCOL))
    if (ROOT / RESULT).exists() or (ROOT / RESULT).is_symlink() or (ROOT / OUTPUT_ROOT).exists() or (ROOT / OUTPUT_ROOT).is_symlink():
        raise RuntimeError("V2.47.93 output is not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0): pass
    (ROOT / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False); prepare_slot_directory(ROOT / SLOT_ROOT)
    active = {"current": 0, "maximum": 0}; lock = threading.Lock(); started = time.monotonic()
    with acquire_deepwide_api_lease(ROOT, owner="v24793_neutral_serialized_search_smoke", purpose="label_blind_terminal_total_neutral_search_smoke", path=ROOT / LEASE_PATH):
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY, thread_name_prefix="v24793-neutral-search") as pool:
            rows = list(pool.map(lambda index: _run_pair(index, active, lock), range(PAIR_COUNT)))
    aggregate = {
        "terminal_pairs": sum(row["terminal"] is True for row in rows),
        "logical_query_rows": sum(row["logical_query_rows"] for row in rows),
        "usable_query_rows": sum(row["usable_query_rows"] for row in rows),
        "raw_query_failures": sum(row["raw_query_failures"] for row in rows),
        "provider_calls": sum(row["provider_calls"] for row in rows),
        "provider_tool_calls": sum(row["provider_tool_calls"] for row in rows),
        "transport_failures": sum(row["transport_failures"] for row in rows),
        "slot_acquisitions": sum(row["search_slot_receipt"]["acquisitions"] for row in rows),
        "slot_timeouts": sum(row["search_slot_receipt"]["slot_timeouts"] for row in rows),
        "no_action_responses": sum(row["search_slot_receipt"]["no_action_responses"] for row in rows),
        "no_action_retries": sum(row["search_slot_receipt"]["no_action_retries"] for row in rows),
        "maximum_active_hosted_search_effects": active["maximum"],
        "batch_wall_seconds": round(time.monotonic() - started, 6),
    }
    passed = all(aggregate.get(name) == expected for name, expected in protocol["gates"].items())
    value = {
        "artifact_version": 1, "role": "v24793_serialized_search_smoke_result",
        "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL), "pairs": rows,
        "aggregate": aggregate, "passed": passed, "source_policy": protocol["source_policy"],
        "authorization": {"exact220_protocol_design": passed, "exact220_launch": False, "evaluator": False, "leaderboard_or_sota": False},
    }
    value["result_payload_sha256"] = payload_sha256(value); validate_result(value); publish_new(ROOT / RESULT, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("protocol", "run")); args = parser.parse_args()
    if args.command == "protocol":
        value = build_protocol(); publish_new(ROOT / PROTOCOL, value); output = {"path": str(PROTOCOL), "authorization": value["authorization"]}
    else:
        value = run(); output = {"path": str(RESULT), "passed": value["passed"], "aggregate": value["aggregate"]}
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__": main()
