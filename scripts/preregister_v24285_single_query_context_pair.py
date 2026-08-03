#!/usr/bin/env python3
"""Freeze a neutral low-vs-medium context probe for one-query/top6 search."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import preregister_v24281_single_shot_pair as query_source  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24285_neutral_single_query_context_pair_preregistration"
PROTOCOL_ID = "v24285_single_query_top6_low_vs_medium_neutral_pair_v1"
OUTPUT = Path(
    "results/v24285_single_query_context_pair_preregistration_v1_20260803.json"
)
RESULT = Path("results/v24285_single_query_context_pair_result_v1_20260803.json")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
PAIR_COUNT = 16
WAVES = 4
PAIRS_PER_WAVE = 4
ARM_CONCURRENCY = 8
CONTEXTS = ("medium", "low")
PRIMARY_QUERIES = tuple(pair[0] for pair in query_source.NEUTRAL_QUERY_PAIRS)
RESULTS_PER_QUERY = 6
FETCH_CAP = 6
PROVIDER = {
    "endpoint": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 180,
    "max_retries": 2,
    "batch_size": 8,
    "workers": 1,
    "max_output_tokens": 7000,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "max_page_chars": 5000,
}
GATES = {
    "maximum_low_over_medium_search_calls": 1.00,
    "maximum_low_over_medium_input_tokens": 0.90,
    "maximum_low_over_medium_total_tokens": 0.92,
    "maximum_low_over_medium_search_seconds": 0.95,
    "maximum_low_over_medium_wall_seconds": 0.97,
    "minimum_low_over_medium_admitted_sources": 0.95,
    "minimum_low_over_medium_usable_pages": 0.90,
    "minimum_low_over_medium_usable_chars": 0.75,
    "minimum_low_over_medium_unique_hosts": 0.75,
    "minimum_pairs_with_lower_low_input_tokens": 10,
    "minimum_admitted_sources_per_arm": 80,
    "minimum_usable_pages_per_arm": 72,
    "minimum_usable_chars_per_arm": 100000,
    "maximum_batch_wall_seconds": 300.0,
    "maximum_effective_search_failures_per_arm": 0,
    "maximum_unrecoverable_search_failures_per_arm": 0,
    "maximum_hard_fetch_deadlines_per_arm": 0,
    "maximum_fetch_helper_failures_per_arm": 0,
}
FORWARD_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24270_budget_equivalent_union.py",
    "src/deepwide_agent/v24275_forward_contract.py",
    "src/deepwide_agent/v24275_hard_deadline_fetch.py",
    "src/deepwide_agent/v24280_task_union_single_shot.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24275_fetch_helper.py",
    "scripts/preregister_v24281_single_shot_pair.py",
    "scripts/probe_v24284_query_width_pair.py",
    "scripts/preregister_v24285_single_query_context_pair.py",
    "scripts/probe_v24285_single_query_context_pair.py",
)
CONTROL_FILES = ("tests/test_probe_v24285_single_query_context_pair.py",)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.85 path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.85 expected ordinary file: {relative}")
    return path


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    value: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.42.85 credential literal in {relative}")
        value[relative] = sha256(path)
    return value


def schedule() -> list[list[dict[str, Any]]]:
    value: list[list[dict[str, Any]]] = []
    for wave in range(WAVES):
        arms: list[dict[str, Any]] = []
        for index in range(wave * PAIRS_PER_WAVE, (wave + 1) * PAIRS_PER_WAVE):
            order = CONTEXTS if index % 2 == 0 else tuple(reversed(CONTEXTS))
            arms.extend({"pair": index + 1, "context": context} for context in order)
        value.append(arms)
    validate_schedule(value)
    return value


def validate_schedule(value: object) -> None:
    if not isinstance(value, list) or len(value) != WAVES:
        raise RuntimeError("V2.42.85 schedule wave count drifted")
    flattened: list[tuple[int, str]] = []
    for wave in value:
        if not isinstance(wave, list) or len(wave) != ARM_CONCURRENCY:
            raise RuntimeError("V2.42.85 schedule concurrency drifted")
        for row in wave:
            if (
                not isinstance(row, Mapping)
                or set(row) != {"pair", "context"}
                or row.get("context") not in CONTEXTS
                or isinstance(row.get("pair"), bool)
                or not isinstance(row.get("pair"), int)
                or not 1 <= row["pair"] <= PAIR_COUNT
            ):
                raise RuntimeError("V2.42.85 schedule arm drifted")
            flattened.append((row["pair"], row["context"]))
    expected = [
        (pair, context)
        for pair in range(1, PAIR_COUNT + 1)
        for context in CONTEXTS
    ]
    if sorted(flattened) != sorted(expected):
        raise RuntimeError("V2.42.85 schedule coverage drifted")


def _validate_queries() -> None:
    if len(PRIMARY_QUERIES) != PAIR_COUNT or any(not query for query in PRIMARY_QUERIES):
        raise RuntimeError("V2.42.85 query set shape drifted")
    encoded = "\n".join(PRIMARY_QUERIES)
    if any(value in encoded for value in ("DeepWide", "task_", "http://", "https://")):
        raise RuntimeError("V2.42.85 query set is unsafe")


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _validate_queries()
    if require_pristine and ((root / RESULT).exists() or (root / RESULT).is_symlink()):
        raise RuntimeError("V2.42.85 result surface is not pristine")
    forward = _manifest(root, FORWARD_FILES)
    control = _manifest(root, CONTROL_FILES)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "neutral_public_documentation_single_query_context_pair_only",
        "pair_contract": {
            "pair_count": PAIR_COUNT,
            "waves": WAVES,
            "pairs_per_wave": PAIRS_PER_WAVE,
            "arm_concurrency": ARM_CONCURRENCY,
            "contexts": list(CONTEXTS),
            "queries_per_arm": 1,
            "results_per_query": RESULTS_PER_QUERY,
            "fetch_cap": FETCH_CAP,
            "same_primary_query_within_pair": True,
            "same_single_shot_task_union_transport": True,
            "query_set_sha256": payload_sha256(PRIMARY_QUERIES),
            "neutral_query_value_or_direct_hash_persisted_in_result": False,
            "schedule": schedule(),
        },
        "provider": dict(PROVIDER),
        "gates": dict(GATES),
        "lease": {
            "path": str(LEASE),
            "owner": "v24285_single_query_context_pair_v1",
            "purpose": "neutral_single_query_top6_low_vs_medium_context_pair",
            "nonblocking_single_owner": True,
        },
        "forward_manifest": forward,
        "forward_manifest_sha256": payload_sha256(forward),
        "control_manifest": control,
        "control_manifest_sha256": payload_sha256(control),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "standalone_generation_or_official_evaluator_called": False,
        },
        "authorization": {
            "benchmark_launch": False,
            "dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(
    root: Path = ROOT,
    path: Path = OUTPUT,
    *,
    value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else read_object(_ordinary(root, path))
    unsigned = dict(protocol)
    seal = unsigned.pop("protocol_payload_sha256", None)
    pair = protocol.get("pair_contract")
    source = protocol.get("source_policy")
    authorization = protocol.get("authorization")
    if (
        protocol.get("role") != ROLE
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "neutral_public_documentation_single_query_context_pair_only"
        or not isinstance(pair, Mapping)
        or pair.get("pair_count") != PAIR_COUNT
        or pair.get("arm_concurrency") != ARM_CONCURRENCY
        or pair.get("contexts") != list(CONTEXTS)
        or pair.get("query_set_sha256") != payload_sha256(PRIMARY_QUERIES)
        or pair.get("neutral_query_value_or_direct_hash_persisted_in_result") is not False
        or protocol.get("provider") != PROVIDER
        or protocol.get("gates") != GATES
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.85 protocol identity drifted")
    validate_schedule(pair.get("schedule"))
    _validate_queries()
    for name, files, seal_name in (
        ("forward", FORWARD_FILES, "forward_manifest_sha256"),
        ("control", CONTROL_FILES, "control_manifest_sha256"),
    ):
        manifest = protocol.get(f"{name}_manifest")
        if (
            not isinstance(manifest, Mapping)
            or set(manifest) != set(files)
            or protocol.get(seal_name) != payload_sha256(manifest)
            or any(sha256(_ordinary(root, relative)) != digest for relative, digest in manifest.items())
        ):
            raise RuntimeError(f"V2.42.85 {name} manifest drifted")
    return protocol


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    protocol = build_protocol()
    publish_new(ROOT / OUTPUT, protocol)
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}, sort_keys=True))
