#!/usr/bin/env python3
"""Fresh aggregate-only health gate for twelve ephemeral Tavily credentials."""

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
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24870_tavily_credential_health_gate as probe  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260809"
PROTOCOL_ID = "v24955_fresh_tavily_credential_health_gate_v1"
PROTOCOL = Path(f"results/v24955_tavily_credential_health_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24955_tavily_credential_health_result_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24955_tavily_credential_health_v1_{DATE}")
PARENT_RESULT = Path("results/v24870_tavily_credential_health_result_v1_20260808r2.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
EXPECTED_KEY_COUNT = 12
EXECUTOR_CONCURRENCY = 12
ATTEMPTS_PER_KEY = 1
RESULTS_PER_QUERY = 1
DEADLINE_SECONDS = 45.0
NEUTRAL_QUERY = probe.NEUTRAL_QUERY
SOURCES = (
    Path("scripts/v24955_tavily_credential_health_gate.py"),
    Path("scripts/v24870_tavily_credential_health_gate.py"),
    Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
    Path("src/deepwide_agent/v24852_rate_aware_tavily_search.py"),
    Path("scripts/deepwide_api_lease.py"),
    Path("tests/test_v24955_tavily_credential_health_gate.py"),
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
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
        raise RuntimeError("V2.49.55 gate requires clean pushed HEAD")


def _manifest(*, require_tracked: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        path = ROOT / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(ROOT.resolve())
            or (
                require_tracked
                and subprocess.run(
                    ["git", "ls-files", "--error-unmatch", str(relative)],
                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=20, check=False,
                ).returncode != 0
            )
        ):
            raise RuntimeError(f"V2.49.55 source is not ordinary tracked: {relative}")
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.49.55 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError("V2.49.55 expected ordinary repository object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.55 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent() -> dict[str, Any]:
    value = _read(ROOT / PARENT_RESULT)
    if (
        value.get("role") != "v24870_tavily_credential_health_result"
        or not _sealed(value, "result_payload_sha256")
        or value.get("aggregate", {}).get("tested_key_count") != 12
        or value.get("source_policy", {}).get(
            "credential_values_or_hashes_persisted_emitted_or_logged"
        ) is not False
    ):
        raise RuntimeError("V2.49.55 parent health evidence drifted")
    return value


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


def source_policy() -> dict[str, bool]:
    return {
        "neutral_public_software_documentation_query_only": True,
        "credential_values_or_hashes_persisted_emitted_or_logged": False,
        "per_key_rows_persisted": False,
        "query_url_title_snippet_page_answer_or_provider_payload_persisted": False,
        "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
        "model_fetch_evaluator_or_benchmark_effect": False,
    }


def build_protocol(
    *, now: int | None = None, require_clean: bool = True, require_pristine: bool = True
) -> dict[str, Any]:
    if require_clean:
        _clean_pushed()
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PROTOCOL, RESULT, OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.49.55 future surface is not pristine")
    manifest = _manifest(require_tracked=require_clean)
    parent = _parent()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24955_tavily_credential_health_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "parent_observation": {
            "path": str(PARENT_RESULT),
            "sha256": sha256(ROOT / PARENT_RESULT),
            "healthy_key_count": int(parent["aggregate"]["healthy_key_count"]),
            "status_432": int(parent["aggregate"]["status_432"]),
            "historical_result_does_not_authorize_or_predict_fresh_outcome": True,
        },
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
            "healthy_key_count": 12, "unhealthy_key_count": 0,
            "status_2xx": 12, "status_401": 0, "status_403": 0,
            "status_429": 0, "status_432": 0, "status_other": 0,
            "transport_failures": 0, "slot_timeouts": 0,
            "credential_echo_rejections": 0,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_neutral_per_credential_live_gate": True,
            "production_shaped_live_exposure_gate_design": False,
            "external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value, require_tracked=require_clean)


def validate_protocol(value: Mapping[str, Any], *, require_tracked: bool = True) -> dict[str, Any]:
    copied = dict(value)
    manifest = _manifest(require_tracked=True) if require_tracked else copied.get("source_manifest")
    if (
        copied.get("role") != "v24955_tavily_credential_health_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("schedule", {}).get("ephemeral_key_count") != 12
        or copied.get("schedule", {}).get("attempts_per_key") != 1
        or copied.get("schedule", {}).get("neutral_query_sha256") != payload_sha256(NEUTRAL_QUERY)
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get("external_or_exact220_launch") is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.49.55 protocol drifted")
    return copied


def ephemeral_credentials(stream: Any = sys.stdin) -> tuple[str, ...]:
    return probe.ephemeral_credentials(stream)


def _aggregate(rows: list[dict[str, int | bool]]) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    healthy = 0
    for row in rows:
        healthy += int(row["healthy"] is True)
        for name, number in row.items():
            if name != "healthy":
                counters[name] += int(number)
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
    passed = aggregate.get("tested_key_count") == 12 and all(
        aggregate.get(name) == expected for name, expected in protocol["gates"].items()
    )
    if (
        copied.get("role") != "v24955_tavily_credential_health_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("passed") is not passed
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization") != {
            "production_shaped_live_exposure_gate_design": passed,
            "external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.55 result drifted")
    return copied


def run(stream: Any = sys.stdin) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (RESULT, OUTPUT_ROOT)):
        raise RuntimeError("V2.49.55 result surface is not pristine")
    credentials = ephemeral_credentials(stream)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="v24955_", dir=ROOT / "outputs") as temporary:
        ephemeral_root = Path(temporary)
        with acquire_deepwide_api_lease(
            ROOT, owner="v24955_tavily_credential_health_gate",
            purpose="fresh_neutral_per_credential_transport_health_only",
            path=ROOT / LEASE_PATH,
        ):
            with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
                rows = list(pool.map(
                    lambda item: probe._probe(item[0], item[1], ephemeral_root),
                    enumerate(credentials, start=1),
                ))
    aggregate = _aggregate(rows)
    passed = aggregate.get("tested_key_count") == 12 and all(
        aggregate.get(name) == expected for name, expected in protocol["gates"].items()
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24955_tavily_credential_health_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "aggregate": aggregate,
        "passed": passed,
        "source_policy": source_policy(),
        "authorization": {
            "production_shaped_live_exposure_gate_design": passed,
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
        print(json.dumps({"path": str(PROTOCOL), "role": value["role"]}, sort_keys=True))
    else:
        value = run()
        print(json.dumps({"path": str(RESULT), "passed": value["passed"]}, sort_keys=True))


if __name__ == "__main__":
    main()
