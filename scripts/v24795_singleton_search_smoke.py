#!/usr/bin/env python3
"""Terminal-total neutral smoke for singleton serialized hosted search."""

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
PROTOCOL_ID = "v24795_neutral_singleton_serialized_hosted_search_smoke_v1"
PROTOCOL = Path(f"results/v24795_singleton_search_smoke_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24795_singleton_search_smoke_result_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24795_singleton_search_smoke_v1_{DATE}")
SLOT_ROOT = OUTPUT_ROOT / "slots"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
DIAGNOSIS = Path(f"results/v24794_hosted_search_failure_diagnosis_v1_{DATE}.json")
FAILED_SMOKE = Path(f"results/v24793_serialized_search_smoke_result_v1_{DATE}.json")
CONCURRENCY = 4
QUERY_COUNT = 8
SOURCES = (
    Path("src/deepwide_agent/v24792_serialized_hosted_search.py"),
    Path("scripts/v24795_singleton_search_smoke.py"),
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
        raise RuntimeError("V2.47.95 neutral smoke requires clean pushed HEAD")


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
        raise RuntimeError(f"V2.47.95 source is not tracked: {path}")
    return value


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.47.95 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.95 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _parents() -> None:
    diagnosis = _read(ROOT / DIAGNOSIS)
    failed = _read(ROOT / FAILED_SMOKE)
    if (
        diagnosis.get("role") != "v24794_hosted_search_failure_diagnosis"
        or diagnosis.get("authorization", {}).get("singleton_neutral_smoke_protocol_design") is not True
        or failed.get("role") != "v24793_serialized_search_smoke_result"
        or failed.get("passed") is not False
        or failed.get("authorization", {}).get("exact220_protocol_design") is not False
    ):
        raise RuntimeError("V2.47.95 parent diagnosis drifted")


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed(); _parents()
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PROTOCOL, RESULT, OUTPUT_ROOT)):
        raise RuntimeError("V2.47.95 future surface is not pristine")
    manifest = {str(path): sha256(_ordinary_tracked(path)) for path in SOURCES}
    queries = [query for pair in NEUTRAL_QUERY_PAIRS[:4] for query in pair]
    value = {
        "artifact_version": 1, "role": "v24795_singleton_search_smoke_preregistration",
        "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parents": {"diagnosis_sha256": sha256(ROOT / DIAGNOSIS), "failed_multi_query_smoke_sha256": sha256(ROOT / FAILED_SMOKE)},
        "single_change": {
            "one_already_admitted_logical_query_per_provider_request": True,
            "global_hosted_search_slot_cap": 1,
            "logical_query_count_unchanged": True,
            "search_result_cap_per_query_unchanged": True,
            "page_fetch_model_synthesis_or_evaluator_changed": False,
        },
        "schedule": {"outer_concurrency": 4, "shared_hosted_search_slot_cap": 1, "provider_batch_size": 1, "logical_query_count": 8, "query_vector_sha256": payload_sha256(queries), "timeout_seconds": 180, "max_retries": 2},
        "gates": {"terminal_queries": 8, "usable_query_rows": 8, "result_urls": 24, "raw_query_failures": 0, "slot_timeouts": 0, "maximum_active_hosted_search_effects": 1},
        "source_manifest": manifest, "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {"neutral_public_software_documentation_queries_only": True, "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False, "query_url_page_or_answer_persisted": False, "credential_value_read_persisted_hashed_or_emitted": False},
        "authorization": {"one_singleton_neutral_live_smoke": True, "benchmark_dev64_or_exact220": False, "evaluator": False, "leaderboard_or_sota": False},
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value)


def validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    manifest = {str(path): sha256(_ordinary_tracked(path)) for path in SOURCES}
    queries = [query for pair in NEUTRAL_QUERY_PAIRS[:4] for query in pair]
    if (
        value.get("role") != "v24795_singleton_search_smoke_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("parents") != {"diagnosis_sha256": sha256(ROOT / DIAGNOSIS), "failed_multi_query_smoke_sha256": sha256(ROOT / FAILED_SMOKE)}
        or value.get("schedule") != {"outer_concurrency": 4, "shared_hosted_search_slot_cap": 1, "provider_batch_size": 1, "logical_query_count": 8, "query_vector_sha256": payload_sha256(queries), "timeout_seconds": 180, "max_retries": 2}
        or value.get("source_manifest") != manifest or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("authorization") != {"one_singleton_neutral_live_smoke": True, "benchmark_dev64_or_exact220": False, "evaluator": False, "leaderboard_or_sota": False}
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.95 protocol drifted")
    return value


def _run_query(index: int, query: str, active: dict[str, int], lock: threading.Lock) -> dict[str, Any]:
    def stage(event: str) -> None:
        with lock:
            if event == "hosted_search_effect_started":
                active["current"] += 1; active["maximum"] = max(active["maximum"], active["current"])
            elif event == "hosted_search_effect_finished": active["current"] -= 1
    client = SerializedThinHostedSearchClient(
        "http://127.0.0.1:9878/responses", "gpt-5.6-sol", reasoning_effort="low",
        service_tier="priority", timeout=65, max_retries=2,
        absolute_deadline=time.monotonic() + 180, cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.05, max_workers=1, batch_size=1,
        search_context_size="medium", max_output_tokens=7000, fetch_pages=False,
        fetch_workers=1, fetch_timeout=20, max_page_chars=5000,
        hard_fetch_deadline_seconds=25, search_slot_directory=ROOT / SLOT_ROOT,
        output_root=ROOT / "outputs", search_slot_cap=1, stage_callback=stage,
    )
    started = time.monotonic()
    batches = client.search_many([query], max_results=3, search_depth="advanced", include_raw_content=False)
    return {
        "ordinal": index + 1, "terminal": True, "logical_query_rows": len(batches),
        "usable_query_rows": sum(bool(row.get("results")) for row in batches),
        "result_urls": sum(len(row.get("results") or []) for row in batches),
        "raw_query_failures": sum(bool(row.get("error")) for row in batches),
        "provider_calls": int(client.calls), "provider_tool_calls": int(client.tool_calls),
        "transport_failures": int(client.transport_failures),
        "wall_seconds": round(time.monotonic() - started, 6),
        "search_slot_receipt": client.search_slot_receipt(),
        "query_url_page_or_answer_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def validate_result(value: dict[str, Any]) -> dict[str, Any]:
    protocol = validate_protocol(_read(ROOT / PROTOCOL)); rows = value.get("queries") or []
    for row in rows: validate_receipt(row.get("search_slot_receipt") or {})
    aggregate = value.get("aggregate") or {}
    expected_pass = all(aggregate.get(name) == expected for name, expected in protocol["gates"].items())
    if (
        value.get("role") != "v24795_singleton_search_smoke_result"
        or value.get("protocol_id") != PROTOCOL_ID or value.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or not isinstance(rows, list) or len(rows) != QUERY_COUNT or [row.get("ordinal") for row in rows] != list(range(1, QUERY_COUNT + 1))
        or value.get("passed") is not expected_pass
        or value.get("authorization") != {"exact220_protocol_design": expected_pass, "exact220_launch": False, "evaluator": False, "leaderboard_or_sota": False}
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.95 result drifted")
    return value


def run() -> dict[str, Any]:
    _clean_pushed(); protocol = validate_protocol(_read(ROOT / PROTOCOL))
    if (ROOT / RESULT).exists() or (ROOT / RESULT).is_symlink() or (ROOT / OUTPUT_ROOT).exists() or (ROOT / OUTPUT_ROOT).is_symlink(): raise RuntimeError("V2.47.95 output is not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0): pass
    (ROOT / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False); prepare_slot_directory(ROOT / SLOT_ROOT)
    queries = [query for pair in NEUTRAL_QUERY_PAIRS[:4] for query in pair]
    active = {"current": 0, "maximum": 0}; lock = threading.Lock(); started = time.monotonic()
    with acquire_deepwide_api_lease(ROOT, owner="v24795_neutral_singleton_search_smoke", purpose="label_blind_neutral_singleton_hosted_search_smoke", path=ROOT / LEASE_PATH):
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY, thread_name_prefix="v24795-neutral-singleton") as pool:
            rows = list(pool.map(lambda item: _run_query(item[0], item[1], active, lock), enumerate(queries)))
    aggregate = {
        "terminal_queries": sum(row["terminal"] is True for row in rows),
        "usable_query_rows": sum(row["usable_query_rows"] for row in rows),
        "result_urls": sum(row["result_urls"] for row in rows),
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
    value = {"artifact_version": 1, "role": "v24795_singleton_search_smoke_result", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()), "protocol_sha256": sha256(ROOT / PROTOCOL), "queries": rows, "aggregate": aggregate, "passed": passed, "source_policy": protocol["source_policy"], "authorization": {"exact220_protocol_design": passed, "exact220_launch": False, "evaluator": False, "leaderboard_or_sota": False}}
    value["result_payload_sha256"] = payload_sha256(value); validate_result(value); publish_new(ROOT / RESULT, value); return value


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("protocol", "run")); args = parser.parse_args()
    if args.command == "protocol":
        value = build_protocol(); publish_new(ROOT / PROTOCOL, value); output = {"path": str(PROTOCOL), "authorization": value["authorization"]}
    else:
        value = run(); output = {"path": str(RESULT), "passed": value["passed"], "aggregate": value["aggregate"]}
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__": main()
