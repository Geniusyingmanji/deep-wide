#!/usr/bin/env python3
"""Preregister and run one aggregate-only Tavily credential health gate.

Each of twelve ephemeral credentials executes one fixed, neutral public
software-documentation query through an isolated one-slot client.  The result
contains only pool-level counters.  Credential values and hashes, query text,
URLs, titles, snippets, pages, answers, and per-key rows are never persisted.
No benchmark, evaluator, model, fetch, prediction, or score capability exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    validate_receipt,
)
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    RateAwareDeadlineTavilyThinCompatibilityClient,
    prepare_rate_aware_key_slots,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260808r2"
PROTOCOL_ID = "v24870_tavily_per_credential_neutral_health_gate_v1"
PREDECESSOR_PROTOCOL = Path(
    "results/v24870_tavily_credential_health_preregistration_v1_20260808.json"
)
PROTOCOL = Path(
    f"results/v24870_tavily_credential_health_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24870_tavily_credential_health_result_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24870_tavily_credential_health_v1_{DATE}")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
EXPECTED_KEY_COUNT = 12
EXECUTOR_CONCURRENCY = 12
ATTEMPTS_PER_KEY = 1
RESULTS_PER_QUERY = 1
DEADLINE_SECONDS = 45.0
NEUTRAL_QUERY = "Python 3.13 official documentation what's new"
SOURCES = (
    Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
    Path("src/deepwide_agent/v24852_rate_aware_tavily_search.py"),
    Path("scripts/v24870_tavily_credential_health_gate.py"),
    Path("tests/test_v24870_tavily_credential_health_gate.py"),
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
        raise RuntimeError("V2.48.70 gate requires clean pushed HEAD")


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
        raise RuntimeError(f"V2.48.70 source is not tracked: {relative}")
    return path


def _manifest(*, require_tracked: bool = True) -> dict[str, str]:
    value: dict[str, str] = {}
    for relative in SOURCES:
        path = (
            _ordinary_tracked(relative)
            if require_tracked
            else (ROOT / relative)
        )
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(ROOT.resolve())
        ):
            raise RuntimeError(f"V2.48.70 source is not ordinary: {relative}")
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.48.70 credential literal in {relative}")
        value[str(relative)] = sha256(path)
    return value


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.48.70 expected ordinary result object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.70 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def predecessor_invalidation() -> dict[str, Any]:
    value = _read(ROOT / PREDECESSOR_PROTOCOL)
    if (
        value.get("role")
        != "v24870_tavily_credential_health_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "protocol_payload_sha256")
        or subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(PREDECESSOR_PROTOCOL)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        != 0
    ):
        raise RuntimeError("V2.48.70 predecessor protocol is invalid")
    return {
        "path": str(PREDECESSOR_PROTOCOL),
        "sha256": sha256(ROOT / PREDECESSOR_PROTOCOL),
        "invalidation_reason": "client_constructor_identity_failure_before_search_many",
        "exception_type": "ValueError",
        "network_provider_search_fetch_model_or_evaluator_effect": False,
        "credential_health_conclusion_drawn": False,
        "result_or_output_artifact_created": False,
        "authorization_reused_by_r2": True,
    }


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
        or any(
            not 8 <= len(value) <= 1024
            or not value.isascii()
            or any(
                not (character.isalnum() or character in "-_.")
                for character in value
            )
            for value in values
        )
    ):
        raise RuntimeError(
            "V2.48.70 requires exactly twelve distinct ephemeral credentials"
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
        raise RuntimeError("V2.48.70 future surface is not pristine")
    manifest = _manifest(require_tracked=require_clean)
    value = {
        "artifact_version": 1,
        "role": "v24870_tavily_credential_health_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "supersedes_pre_effect_invalid_protocol": predecessor_invalidation(),
        "schedule": {
            "ephemeral_key_count": EXPECTED_KEY_COUNT,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "attempts_per_key": ATTEMPTS_PER_KEY,
            "results_per_query": RESULTS_PER_QUERY,
            "per_key_deadline_seconds": DEADLINE_SECONDS,
            "neutral_query_sha256": payload_sha256(NEUTRAL_QUERY),
            "every_key_isolated_in_own_one_slot_client": True,
        },
        "gates": {
            "healthy_key_count": EXPECTED_KEY_COUNT,
            "unhealthy_key_count": 0,
            "status_2xx": EXPECTED_KEY_COUNT,
            "status_401": 0,
            "status_403": 0,
            "status_432": 0,
            "slot_timeouts": 0,
            "credential_echo_rejections": 0,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "neutral_public_software_documentation_query_only": True,
            "credential_values_or_hashes_persisted_emitted_or_logged": False,
            "per_key_rows_persisted": False,
            "query_url_title_snippet_page_answer_or_provider_payload_persisted": False,
            "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
            "model_fetch_evaluator_or_benchmark_effect": False,
        },
        "authorization": {
            "one_neutral_per_credential_live_gate": True,
            "external_or_exact220_launch": False,
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
        _manifest(require_tracked=True)
        if require_tracked
        else copied.get("source_manifest")
    )
    if (
        copied.get("role")
        != "v24870_tavily_credential_health_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("schedule", {}).get("ephemeral_key_count")
        != EXPECTED_KEY_COUNT
        or copied.get("schedule", {}).get("executor_concurrency")
        != EXECUTOR_CONCURRENCY
        or copied.get("schedule", {}).get("attempts_per_key")
        != ATTEMPTS_PER_KEY
        or copied.get("schedule", {}).get("neutral_query_sha256")
        != payload_sha256(NEUTRAL_QUERY)
        or copied.get("supersedes_pre_effect_invalid_protocol")
        != predecessor_invalidation()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("authorization")
        != {
            "one_neutral_per_credential_live_gate": True,
            "external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.70 protocol drifted")
    return copied


def _probe(ordinal: int, credential: str, root: Path) -> dict[str, int | bool]:
    directory = root / f"key_{ordinal:02d}"
    prepare_rate_aware_key_slots(directory, 1)
    client = RateAwareDeadlineTavilyThinCompatibilityClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        timeout=30,
        max_retries=1,
        absolute_deadline=time.monotonic() + DEADLINE_SECONDS,
        cleanup_reserve_seconds=3,
        minimum_attempt_seconds=0.05,
        max_workers=1,
        batch_size=1,
        search_context_size="low",
        max_output_tokens=1000,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=10,
        max_page_chars=1000,
        # Inherited constructor identity is frozen at 25 seconds.  This gate
        # never calls fetch_urls, so the helper remains effect-free.
        hard_fetch_deadline_seconds=25,
        credentials=(credential,),
        key_slot_directory=directory,
        output_root=root,
        direct_timeout_seconds=30,
        direct_workers=1,
        direct_post=None,
        provider_attempt_cap=ATTEMPTS_PER_KEY,
    )
    try:
        batches = client.search_many(
            [NEUTRAL_QUERY],
            max_results=RESULTS_PER_QUERY,
            search_depth="basic",
            include_raw_content=False,
        )
    except BaseException:
        batches = []
    receipt = validate_receipt(client.direct_search_receipt())
    successful = int(
        len(batches) == 1
        and bool(batches[0].get("results"))
        and not batches[0].get("error")
    )
    return {
        "healthy": successful == 1 and receipt["status_2xx"] == 1,
        "status_2xx": int(receipt["status_2xx"]),
        "status_401": int(receipt["status_401"]),
        "status_403": int(receipt["status_403"]),
        "status_432": int(receipt["status_432"]),
        "status_429": int(receipt["status_429"]),
        "status_other": int(receipt["status_other"]),
        "transport_failures": int(receipt["transport_failures"]),
        "slot_timeouts": int(receipt["slot_timeouts"]),
        "credential_echo_rejections": int(
            receipt["credential_echo_rejections"]
        ),
    }


def _aggregate(rows: list[dict[str, int | bool]]) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    healthy = 0
    for row in rows:
        healthy += int(row["healthy"] is True)
        for name, value in row.items():
            if name != "healthy":
                counters[name] += int(value)
    return {
        "tested_key_count": len(rows),
        "healthy_key_count": healthy,
        "unhealthy_key_count": len(rows) - healthy,
        **{name: int(counters[name]) for name in sorted(counters)},
        "contains_credential_value_or_hash": False,
        "contains_per_key_rows": False,
        "contains_query_url_title_snippet_page_answer_or_provider_payload": False,
    }


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    aggregate = copied.get("aggregate") or {}
    gates = protocol["gates"]
    passed = (
        aggregate.get("tested_key_count") == EXPECTED_KEY_COUNT
        and all(aggregate.get(name) == expected for name, expected in gates.items())
    )
    if (
        copied.get("role") != "v24870_tavily_credential_health_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("passed") is not passed
        or copied.get("source_policy") != protocol["source_policy"]
        or copied.get("authorization")
        != {
            "benchmark_external_transport_design": passed,
            "external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.48.70 result drifted")
    return copied


def run(stream: Any = sys.stdin) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (RESULT, OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.48.70 result surface is not pristine")
    credentials = ephemeral_credentials(stream)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(
        prefix="v24870_", dir=ROOT / "outputs"
    ) as temporary:
        ephemeral_root = Path(temporary)
        with acquire_deepwide_api_lease(
            ROOT,
            owner="v24870_tavily_credential_health_gate",
            purpose="neutral_per_credential_transport_health_only",
            path=ROOT / LEASE_PATH,
        ):
            with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
                rows = list(
                    pool.map(
                        lambda item: _probe(item[0], item[1], ephemeral_root),
                        enumerate(credentials, start=1),
                    )
                )
    aggregate = _aggregate(rows)
    passed = all(
        aggregate.get(name) == expected
        for name, expected in protocol["gates"].items()
    )
    value = {
        "artifact_version": 1,
        "role": "v24870_tavily_credential_health_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "aggregate": aggregate,
        "passed": passed,
        "source_policy": protocol["source_policy"],
        "authorization": {
            "benchmark_external_transport_design": passed,
            "external_or_exact220_launch": False,
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
