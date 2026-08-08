#!/usr/bin/env python3
"""Freeze and run one aggregate-only neutral rate-aware Tavily smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
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

from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    DeadlineTavilyThinCompatibilityClient,
    prepare_key_slots,
    validate_receipt as validate_direct_receipt,
)
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    DEFAULT_MAXIMUM_COOLDOWN_SECONDS,
    DEFAULT_MINIMUM_START_INTERVAL_SECONDS,
    DEFAULT_PROVIDER_ATTEMPT_CAP,
    DEFAULT_PROVIDER_COOLDOWN_SECONDS,
    RateAwareDeadlineTavilyThinCompatibilityClient,
    prepare_rate_aware_key_slots,
    validate_receipt as validate_rate_receipt,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24278_search_context_pair import (  # noqa: E402
    NEUTRAL_QUERY_PAIRS,
)


DATE = "20260808"
PROTOCOL_ID = "v24853_neutral_old_vs_rate_aware_tavily_transport_v1"
PROTOCOL = Path(
    f"results/v24853_rate_aware_transport_smoke_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24853_rate_aware_transport_smoke_result_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24853_rate_aware_transport_smoke_v1_{DATE}")
OLD_SLOTS = OUTPUT_ROOT / "old_key_slots"
NEW_SLOTS = OUTPUT_ROOT / "rate_aware_key_slots"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
EXPECTED_KEY_COUNT = 12
QUERY_COUNT = 4
RESULTS_PER_QUERY = 3
FETCH_CAP = 8
SOURCES = (
    Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
    Path("src/deepwide_agent/v24852_rate_aware_tavily_search.py"),
    Path("scripts/v24853_rate_aware_transport_smoke.py"),
    Path("tests/test_v24853_rate_aware_transport_smoke.py"),
    Path("scripts/deepwide_api_lease.py"),
    Path("scripts/preregister_v24278_search_context_pair.py"),
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
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
        raise RuntimeError("V2.48.53 smoke requires clean pushed HEAD")


def _ordinary_tracked(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or subprocess.run(
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
        raise RuntimeError(f"V2.48.53 source is not tracked: {relative}")
    return path


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.53 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.53 expected JSON object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


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
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def neutral_queries() -> list[str]:
    return [query for pair in NEUTRAL_QUERY_PAIRS[:2] for query in pair]


def ephemeral_credentials(stream: Any = sys.stdin) -> tuple[str, ...]:
    serialized = stream.read()
    try:
        values = tuple(
            line.strip() for line in serialized.splitlines() if line.strip()
        )
    finally:
        serialized = ""
    if (
        len(values) != EXPECTED_KEY_COUNT
        or len(set(values)) != EXPECTED_KEY_COUNT
        or any(not 8 <= len(value) <= 1024 for value in values)
    ):
        raise RuntimeError(
            "V2.48.53 requires exactly 12 distinct ephemeral credentials"
        )
    return values


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
        raise RuntimeError("V2.48.53 smoke surface is not pristine")
    manifest = {
        str(path): sha256(_ordinary_tracked(path)) for path in SOURCES
    }
    value = {
        "artifact_version": 1,
        "role": "v24853_rate_aware_transport_smoke_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "schedule": {
            "neutral_query_count": QUERY_COUNT,
            "query_vector_sha256": payload_sha256(neutral_queries()),
            "expected_ephemeral_key_count": EXPECTED_KEY_COUNT,
            "results_per_query": RESULTS_PER_QUERY,
            "fetch_cap": FETCH_CAP,
            "old_then_rate_aware_same_neutral_query_vector": True,
            "phase_deadline_seconds": 180,
        },
        "rate_policy": {
            "provider_non_key_local_attempt_cap_per_logical_query": (
                DEFAULT_PROVIDER_ATTEMPT_CAP
            ),
            "minimum_start_interval_seconds": (
                DEFAULT_MINIMUM_START_INTERVAL_SECONDS
            ),
            "default_provider_cooldown_seconds": (
                DEFAULT_PROVIDER_COOLDOWN_SECONDS
            ),
            "maximum_provider_cooldown_seconds": (
                DEFAULT_MAXIMUM_COOLDOWN_SECONDS
            ),
            "provider_wide_429_rotates_all_keys_immediately": False,
        },
        "gates": {
            "new_terminal": True,
            "new_search_query_rows": QUERY_COUNT,
            "new_successful_query_rows": QUERY_COUNT,
            "new_failed_query_rows": 0,
            "new_minimum_projected_url_leads": QUERY_COUNT,
            "new_slot_timeouts": 0,
            "new_credential_echo_rejections": 0,
            "old_arm_is_descriptive_not_a_launch_gate": True,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "neutral_public_software_documentation_queries_only": True,
            "tavily_answer_snippet_raw_content_and_score_are_discarded": True,
            "deterministically_fetched_public_pages_are_only_active_evidence": True,
            "credential_values_stdin_memory_only_not_persisted_hashed_or_emitted": True,
            "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
            "query_url_page_answer_or_opaque_id_persisted": False,
        },
        "authorization": {
            "one_neutral_old_vs_rate_aware_live_smoke": True,
            "exact220_protocol_design": False,
            "exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value)


def validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        str(path): sha256(_ordinary_tracked(path)) for path in SOURCES
    }
    if (
        value.get("role")
        != "v24853_rate_aware_transport_smoke_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("schedule", {}).get("neutral_query_count") != QUERY_COUNT
        or value.get("schedule", {}).get("query_vector_sha256")
        != payload_sha256(neutral_queries())
        or value.get("source_manifest") != manifest
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("authorization")
        != {
            "one_neutral_old_vs_rate_aware_live_smoke": True,
            "exact220_protocol_design": False,
            "exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.53 smoke protocol drifted")
    return value


def _client(
    cls: type[DeadlineTavilyThinCompatibilityClient],
    *,
    credentials: tuple[str, ...],
    slots: Path,
    deadline: float,
) -> DeadlineTavilyThinCompatibilityClient:
    return cls(
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
        key_slot_directory=ROOT / slots,
        output_root=ROOT / OUTPUT_ROOT,
        direct_timeout_seconds=45,
        direct_workers=QUERY_COUNT,
    )


def _aggregate(
    batches: list[dict[str, Any]], receipt: dict[str, Any], wall: float
) -> dict[str, Any]:
    return {
        "terminal": True,
        "search_query_rows": len(batches),
        "successful_query_rows": sum(
            bool(batch.get("results")) and not batch.get("error")
            for batch in batches
        ),
        "failed_query_rows": sum(
            bool(batch.get("error")) or not batch.get("results")
            for batch in batches
        ),
        "projected_url_leads": sum(
            len(batch.get("results") or []) for batch in batches
        ),
        "provider_attempts": receipt["provider_attempts"],
        "status_429": receipt["status_429"],
        "slot_timeouts": receipt["slot_timeouts"],
        "credential_echo_rejections": receipt[
            "credential_echo_rejections"
        ],
        "wall_seconds": round(max(0.0, wall), 6),
        "contains_query_url_page_answer_or_credential": False,
    }


def validate_result(value: dict[str, Any]) -> dict[str, Any]:
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    old = value.get("old_transport_aggregate") or {}
    new = value.get("rate_aware_transport_aggregate") or {}
    direct = validate_direct_receipt(
        value.get("rate_aware_direct_search_receipt") or {}
    )
    rate = validate_rate_receipt(value.get("rate_aware_receipt") or {})
    gates = protocol["gates"]
    passed = (
        new.get("terminal") is gates["new_terminal"]
        and new.get("search_query_rows") == gates["new_search_query_rows"]
        and new.get("successful_query_rows")
        == gates["new_successful_query_rows"]
        and new.get("failed_query_rows") == gates["new_failed_query_rows"]
        and new.get("projected_url_leads", 0)
        >= gates["new_minimum_projected_url_leads"]
        and direct["slot_timeouts"] == gates["new_slot_timeouts"]
        and direct["credential_echo_rejections"]
        == gates["new_credential_echo_rejections"]
        and rate[
            "provider_wide_429_rotates_all_keys_immediately"
        ]
        is False
    )
    if (
        value.get("role") != "v24853_rate_aware_transport_smoke_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or not isinstance(old, dict)
        or value.get("passed") is not passed
        or value.get("source_policy") != protocol["source_policy"]
        or value.get("authorization")
        != {
            "exact220_protocol_design": passed,
            "exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.48.53 smoke result drifted")
    return value


def run(stream: Any = sys.stdin) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    if (
        (ROOT / RESULT).exists()
        or (ROOT / RESULT).is_symlink()
        or (ROOT / OUTPUT_ROOT).exists()
        or (ROOT / OUTPUT_ROOT).is_symlink()
    ):
        raise RuntimeError("V2.48.53 smoke output is not pristine")
    credentials = ephemeral_credentials(stream)
    (ROOT / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    prepare_key_slots(ROOT / OLD_SLOTS, len(credentials))
    prepare_rate_aware_key_slots(ROOT / NEW_SLOTS, len(credentials))
    queries = neutral_queries()
    old_batches: list[dict[str, Any]] = []
    new_batches: list[dict[str, Any]] = []
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v24853_neutral_rate_aware_transport_smoke",
        purpose="aggregate_only_neutral_old_vs_rate_aware_tavily_smoke",
        path=ROOT / LEASE_PATH,
    ):
        old_client = _client(
            DeadlineTavilyThinCompatibilityClient,
            credentials=credentials,
            slots=OLD_SLOTS,
            deadline=time.monotonic() + 180,
        )
        old_started = time.monotonic()
        try:
            old_batches = old_client.search_many(
                queries,
                max_results=RESULTS_PER_QUERY,
                search_depth="advanced",
                include_raw_content=False,
            )
        except BaseException:
            old_batches = []
        old_wall = time.monotonic() - old_started
        new_client = _client(
            RateAwareDeadlineTavilyThinCompatibilityClient,
            credentials=credentials,
            slots=NEW_SLOTS,
            deadline=time.monotonic() + 180,
        )
        new_started = time.monotonic()
        try:
            new_batches = new_client.search_many(
                queries,
                max_results=RESULTS_PER_QUERY,
                search_depth="advanced",
                include_raw_content=False,
            )
        except BaseException:
            new_batches = []
        new_wall = time.monotonic() - new_started
    old_receipt = validate_direct_receipt(old_client.direct_search_receipt())
    new_direct = validate_direct_receipt(new_client.direct_search_receipt())
    rate_receipt = validate_rate_receipt(
        new_client.rate_aware_search_receipt()
    )
    old_aggregate = _aggregate(old_batches, old_receipt, old_wall)
    new_aggregate = _aggregate(new_batches, new_direct, new_wall)
    gates = protocol["gates"]
    passed = (
        new_aggregate["terminal"] is True
        and new_aggregate["search_query_rows"] == QUERY_COUNT
        and new_aggregate["successful_query_rows"] == QUERY_COUNT
        and new_aggregate["failed_query_rows"] == 0
        and new_aggregate["projected_url_leads"]
        >= gates["new_minimum_projected_url_leads"]
        and new_direct["slot_timeouts"] == 0
        and new_direct["credential_echo_rejections"] == 0
        and rate_receipt[
            "provider_wide_429_rotates_all_keys_immediately"
        ]
        is False
    )
    value = {
        "artifact_version": 1,
        "role": "v24853_rate_aware_transport_smoke_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "old_transport_aggregate": old_aggregate,
        "rate_aware_transport_aggregate": new_aggregate,
        "rate_aware_direct_search_receipt": new_direct,
        "rate_aware_receipt": rate_receipt,
        "comparison": {
            "same_neutral_query_vector": True,
            "old_arm_used_only_as_transport_diagnostic": True,
            "new_provider_wide_429_full_key_rotation_disabled": True,
            "benchmark_quality_or_sota_inferred": False,
        },
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
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "run"))
    args = parser.parse_args()
    if args.command == "protocol":
        value = build_protocol()
        publish_new(ROOT / PROTOCOL, value)
        output = {"path": str(PROTOCOL), "role": value["role"]}
    else:
        value = run()
        output = {
            "path": str(RESULT),
            "passed": value["passed"],
            "old": value["old_transport_aggregate"],
            "rate_aware": value["rate_aware_transport_aggregate"],
        }
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
