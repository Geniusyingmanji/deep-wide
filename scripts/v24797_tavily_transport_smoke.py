#!/usr/bin/env python3
"""Preregister and run one terminal-total neutral Tavily transport smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    DeadlineTavilyThinCompatibilityClient,
    prepare_key_slots,
    validate_receipt,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24278_search_context_pair import NEUTRAL_QUERY_PAIRS  # noqa: E402


DATE = "20260807"
PROTOCOL_ID = "v24797_neutral_tavily_url_lead_fetch_smoke_v1"
PROTOCOL = Path(f"results/v24797_tavily_transport_smoke_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24797_tavily_transport_smoke_result_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24797_tavily_transport_smoke_v1_{DATE}")
SLOT_ROOT = OUTPUT_ROOT / "key_slots"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
EXPECTED_KEY_COUNT = 12
QUERY_COUNT = 12
RESULTS_PER_QUERY = 3
FETCH_CAP = 24
SOURCES = (
    Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
    Path("src/deepwide_agent/v24282_direct_search_page_projection.py"),
    Path("src/deepwide_agent/v24283_tavily_header_client.py"),
    Path("scripts/v24797_tavily_transport_smoke.py"),
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
        raise RuntimeError("V2.47.97 smoke requires clean pushed HEAD")


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
        raise RuntimeError(f"V2.47.97 source is not tracked: {path}")
    return value


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.47.97 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.97 expected object")
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


def neutral_queries() -> list[str]:
    return [query for pair in NEUTRAL_QUERY_PAIRS[:6] for query in pair]


def ephemeral_credentials() -> tuple[str, ...]:
    raw = os.environ.pop("TAVILY_API_KEYS", "")
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if (
        len(values) != EXPECTED_KEY_COUNT
        or len(set(values)) != EXPECTED_KEY_COUNT
        or any(not 8 <= len(value) <= 1024 for value in values)
    ):
        raise RuntimeError(
            f"V2.47.97 requires exactly {EXPECTED_KEY_COUNT} distinct ephemeral Tavily credentials"
        )
    return values


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PROTOCOL, RESULT, OUTPUT_ROOT)):
        raise RuntimeError("V2.47.97 future surface is not pristine")
    manifest = {str(path): sha256(_ordinary_tracked(path)) for path in SOURCES}
    value = {
        "artifact_version": 1,
        "role": "v24797_tavily_transport_smoke_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "schedule": {
            "neutral_query_count": QUERY_COUNT,
            "query_vector_sha256": payload_sha256(neutral_queries()),
            "expected_ephemeral_key_count": EXPECTED_KEY_COUNT,
            "direct_search_workers": EXPECTED_KEY_COUNT,
            "results_per_query": RESULTS_PER_QUERY,
            "deterministic_fetch_cap": FETCH_CAP,
            "fetch_workers": 8,
            "shared_deadline_seconds": 300,
        },
        "gates": {
            "terminal": True,
            "credential_count": EXPECTED_KEY_COUNT,
            "search_query_rows": QUERY_COUNT,
            "successful_query_rows": QUERY_COUNT,
            "failed_query_rows": 0,
            "minimum_projected_url_leads": 30,
            "fetch_requested": FETCH_CAP,
            "minimum_usable_fetched_pages": 12,
            "slot_timeouts": 0,
            "credential_echo_rejections": 0,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "neutral_public_software_documentation_queries_only": True,
            "tavily_answer_snippet_raw_content_and_score_are_discarded": True,
            "deterministically_fetched_public_pages_are_only_active_evidence": True,
            "credential_values_are_environment_only_and_not_persisted_hashed_or_emitted": True,
            "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
            "query_url_page_or_answer_persisted": False,
        },
        "authorization": {
            "one_neutral_tavily_live_smoke": True,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value)


def validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    manifest = {str(path): sha256(_ordinary_tracked(path)) for path in SOURCES}
    if (
        value.get("role") != "v24797_tavily_transport_smoke_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("schedule") != {
            "neutral_query_count": 12,
            "query_vector_sha256": payload_sha256(neutral_queries()),
            "expected_ephemeral_key_count": 12,
            "direct_search_workers": 12,
            "results_per_query": 3,
            "deterministic_fetch_cap": 24,
            "fetch_workers": 8,
            "shared_deadline_seconds": 300,
        }
        or value.get("source_manifest") != manifest
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("authorization") != {
            "one_neutral_tavily_live_smoke": True,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.97 protocol drifted")
    return value


def _usable_pages(batches: list[dict[str, Any]]) -> int:
    return sum(
        bool(str(result.get("raw_content") or result.get("content") or "").strip())
        for batch in batches
        for result in (batch.get("results") or [])
        if isinstance(result, dict)
    )


def validate_result(value: dict[str, Any]) -> dict[str, Any]:
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    receipt = validate_receipt(value.get("direct_search_receipt") or {})
    observed = value.get("observed") or {}
    gates = protocol["gates"]
    expected_pass = (
        observed.get("terminal") is gates["terminal"]
        and observed.get("credential_count") == gates["credential_count"]
        and observed.get("search_query_rows") == gates["search_query_rows"]
        and observed.get("successful_query_rows") == gates["successful_query_rows"]
        and observed.get("failed_query_rows") == gates["failed_query_rows"]
        and observed.get("projected_url_leads", 0) >= gates["minimum_projected_url_leads"]
        and observed.get("fetch_requested") == gates["fetch_requested"]
        and observed.get("usable_fetched_pages", 0) >= gates["minimum_usable_fetched_pages"]
        and receipt["slot_timeouts"] == gates["slot_timeouts"]
        and receipt["credential_echo_rejections"] == gates["credential_echo_rejections"]
    )
    if (
        value.get("role") != "v24797_tavily_transport_smoke_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or value.get("passed") is not expected_pass
        or value.get("source_policy") != protocol["source_policy"]
        or value.get("authorization") != {
            "exact220_protocol_design": expected_pass,
            "exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.97 result drifted")
    return value


def run() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    if (ROOT / RESULT).exists() or (ROOT / RESULT).is_symlink() or (ROOT / OUTPUT_ROOT).exists() or (ROOT / OUTPUT_ROOT).is_symlink():
        raise RuntimeError("V2.47.97 output is not pristine")
    credentials = ephemeral_credentials()
    (ROOT / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    prepare_key_slots(ROOT / SLOT_ROOT, len(credentials))
    started = time.monotonic()
    deadline = started + 300
    client = DeadlineTavilyThinCompatibilityClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        timeout=65,
        max_retries=2,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.05,
        max_workers=1,
        batch_size=1,
        search_context_size="medium",
        max_output_tokens=7000,
        fetch_pages=False,
        fetch_workers=8,
        fetch_timeout=20,
        max_page_chars=5000,
        hard_fetch_deadline_seconds=25,
        credentials=credentials,
        key_slot_directory=ROOT / SLOT_ROOT,
        output_root=ROOT / "outputs",
        direct_timeout_seconds=45,
        direct_workers=12,
    )
    batches: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    terminal = True
    try:
        with acquire_deepwide_api_lease(
            ROOT, owner="v24797_neutral_tavily_transport_smoke",
            purpose="label_blind_neutral_tavily_url_lead_fetch_smoke",
            path=ROOT / LEASE_PATH,
        ):
            batches = client.search_many(
                neutral_queries(),
                max_results=RESULTS_PER_QUERY,
                search_depth="advanced",
                include_raw_content=False,
            )
            leads: list[dict[str, str]] = []
            seen: set[str] = set()
            for batch in batches:
                for result in batch.get("results") or []:
                    url = str(result.get("fetch_url") or result.get("url") or "")
                    if url and url not in seen and len(leads) < FETCH_CAP:
                        leads.append({"url": url, "query": "neutral public documentation fetch"})
                        seen.add(url)
            pages = client.fetch_urls(leads)
    except BaseException:
        terminal = True
    receipt = client.direct_search_receipt()
    projected = sum(len(batch.get("results") or []) for batch in batches)
    observed = {
        "terminal": terminal,
        "credential_count": len(credentials),
        "search_query_rows": len(batches),
        "successful_query_rows": sum(bool(batch.get("results")) and not batch.get("error") for batch in batches),
        "failed_query_rows": sum(bool(batch.get("error")) or not batch.get("results") for batch in batches),
        "projected_url_leads": projected,
        "fetch_requested": min(FETCH_CAP, projected),
        "fetch_returned_batches": len(pages),
        "usable_fetched_pages": _usable_pages(pages),
        "provider_calls": receipt["provider_attempts"],
        "key_local_disables": receipt["key_local_disables"],
        "retryable_responses": receipt["retryable_responses"],
        "transport_failures": receipt["transport_failures"],
        "wall_seconds": round(time.monotonic() - started, 6),
    }
    gates = protocol["gates"]
    passed = (
        observed["terminal"] is True
        and observed["credential_count"] == gates["credential_count"]
        and observed["search_query_rows"] == gates["search_query_rows"]
        and observed["successful_query_rows"] == gates["successful_query_rows"]
        and observed["failed_query_rows"] == 0
        and observed["projected_url_leads"] >= gates["minimum_projected_url_leads"]
        and observed["fetch_requested"] == gates["fetch_requested"]
        and observed["usable_fetched_pages"] >= gates["minimum_usable_fetched_pages"]
        and receipt["slot_timeouts"] == 0
        and receipt["credential_echo_rejections"] == 0
    )
    value = {
        "artifact_version": 1,
        "role": "v24797_tavily_transport_smoke_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "observed": observed,
        "direct_search_receipt": receipt,
        "passed": passed,
        "source_policy": protocol["source_policy"],
        "authorization": {
            "exact220_protocol_design": passed,
            "exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_result(value)
    publish_new(ROOT / RESULT, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("protocol", "run", "readiness")); args = parser.parse_args()
    if args.command == "protocol":
        value = build_protocol(); publish_new(ROOT / PROTOCOL, value); output = {"path": str(PROTOCOL), "authorization": value["authorization"]}
    elif args.command == "readiness":
        raw = os.environ.get("TAVILY_API_KEYS", "")
        values = [part.strip() for part in raw.split(",") if part.strip()]
        output = {"credential_environment_present": bool(raw), "credential_count": len(values), "expected_count": EXPECTED_KEY_COUNT, "ready": len(values) == EXPECTED_KEY_COUNT and len(set(values)) == EXPECTED_KEY_COUNT}
    else:
        value = run(); output = {"path": str(RESULT), "passed": value["passed"], "observed": value["observed"]}
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__": main()
