#!/usr/bin/env python3
"""Freeze a neutral recursive-split versus task-union single-shot probe."""

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

from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24281_neutral_single_shot_pair_preregistration"
PROTOCOL_ID = "v24281_recursive_vs_single_shot_task_union_neutral_pair_v1"
OUTPUT = Path("results/v24281_single_shot_pair_preregistration_v1_20260803.json")
RESULT = Path("results/v24281_single_shot_pair_result_v1_20260803.json")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
PAIR_COUNT = 16
WAVES = 4
PAIRS_PER_WAVE = 4
PAIR_CONCURRENCY = 4
ARMS = ("recursive", "single_shot")
QUERIES_PER_PAIR = 2
RESULTS_PER_QUERY = 3
FETCH_CAP = 6
NEUTRAL_QUERY_PAIRS = (
    (
        "Python 3.13 official documentation what's new language features",
        "Python 3.13 official documentation runtime and standard library changes",
    ),
    (
        "PostgreSQL 17 official documentation new features",
        "PostgreSQL 17 official documentation release notes changes",
    ),
    (
        "Rust 1.80 official documentation language and compiler changes",
        "Rust 1.80 official release notes library features",
    ),
    (
        "Node.js 22 official documentation new features",
        "Node.js 22 official release notes runtime changes",
    ),
    (
        "Go 1.23 official documentation language changes",
        "Go 1.23 official release notes library and tool changes",
    ),
    (
        "Java 21 official documentation language features",
        "Java 21 official documentation runtime and library changes",
    ),
    (
        "Kubernetes 1.31 official documentation release features",
        "Kubernetes 1.31 official changelog stable features",
    ),
    (
        "SQLite 3.46 official documentation changes",
        "SQLite 3.46 official release notes features",
    ),
    (
        "Linux 6.10 official kernel documentation new features",
        "Linux 6.10 official kernel release changes documentation",
    ),
    (
        "CMake 3.30 official documentation release notes",
        "CMake 3.30 official documentation new commands and features",
    ),
    (
        "Django 5.1 official documentation release notes",
        "Django 5.1 official documentation new features",
    ),
    (
        "NumPy 2.1 official documentation release notes",
        "NumPy 2.1 official documentation API changes",
    ),
    (
        "Git 2.46 official release notes new features",
        "Git 2.46 official documentation behavior changes",
    ),
    (
        "OpenSSL 3.3 official documentation release notes",
        "OpenSSL 3.3 official documentation new features",
    ),
    (
        "Terraform 1.9 official documentation language features",
        "Terraform 1.9 official documentation release changes",
    ),
    (
        "LLVM 18 official documentation release notes",
        "Clang 18 official documentation language and compiler changes",
    ),
)
PROVIDER = {
    "endpoint": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 180,
    "max_retries": 2,
    "batch_size": 8,
    "workers": 1,
    "search_context_size": "medium",
    "max_output_tokens": 7000,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "max_page_chars": 5000,
}
GATES = {
    "minimum_control_recursive_split_chunk_requests": 2,
    "maximum_single_shot_over_recursive_http_calls": 0.90,
    "maximum_single_shot_over_recursive_input_tokens": 0.90,
    "maximum_single_shot_over_recursive_total_tokens": 0.92,
    "maximum_single_shot_over_recursive_search_seconds": 0.90,
    "maximum_single_shot_over_recursive_wall_seconds": 0.95,
    "minimum_single_shot_over_recursive_admitted_sources": 0.90,
    "minimum_single_shot_over_recursive_usable_pages": 0.90,
    "minimum_single_shot_over_recursive_usable_chars": 0.75,
    "minimum_single_shot_over_recursive_unique_hosts": 0.75,
    "minimum_admitted_sources_per_arm": 64,
    "minimum_usable_pages_per_arm": 56,
    "minimum_usable_chars_per_arm": 80000,
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
    "scripts/probe_v24281_single_shot_pair.py",
)
CONTROL_FILES = ("tests/test_probe_v24281_single_shot_pair.py",)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.81 path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.81 expected ordinary file: {relative}")
    return path


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    value: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.42.81 credential literal in {relative}")
        value[relative] = sha256(path)
    return value


def schedule() -> list[list[int]]:
    value: list[list[int]] = []
    for wave in range(WAVES):
        value.append(
            list(
                range(
                    wave * PAIRS_PER_WAVE + 1,
                    (wave + 1) * PAIRS_PER_WAVE + 1,
                )
            )
        )
    validate_schedule(value)
    return value


def validate_schedule(value: object) -> None:
    if not isinstance(value, list) or len(value) != WAVES:
        raise RuntimeError("V2.42.81 schedule wave count drifted")
    flattened: list[int] = []
    for wave in value:
        if not isinstance(wave, list) or len(wave) != PAIR_CONCURRENCY:
            raise RuntimeError("V2.42.81 schedule concurrency drifted")
        for pair in wave:
            if (
                isinstance(pair, bool)
                or not isinstance(pair, int)
                or not 1 <= pair <= PAIR_COUNT
            ):
                raise RuntimeError("V2.42.81 schedule pair drifted")
            flattened.append(pair)
    if sorted(flattened) != list(range(1, PAIR_COUNT + 1)):
        raise RuntimeError("V2.42.81 schedule pair coverage drifted")


def _validate_queries() -> None:
    if (
        len(NEUTRAL_QUERY_PAIRS) != PAIR_COUNT
        or any(len(pair) != QUERIES_PER_PAIR for pair in NEUTRAL_QUERY_PAIRS)
    ):
        raise RuntimeError("V2.42.81 neutral query set shape drifted")
    encoded = "\n".join(query for pair in NEUTRAL_QUERY_PAIRS for query in pair)
    if any(value in encoded for value in ("DeepWide", "task_", "http://", "https://")):
        raise RuntimeError("V2.42.81 neutral query set is unsafe")


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _validate_queries()
    if require_pristine and ((root / RESULT).exists() or (root / RESULT).is_symlink()):
        raise RuntimeError("V2.42.81 result surface is not pristine")
    forward = _manifest(root, FORWARD_FILES)
    control = _manifest(root, CONTROL_FILES)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "neutral_public_documentation_task_union_request_count_pair_only",
        "pair_contract": {
            "pair_count": PAIR_COUNT,
            "waves": WAVES,
            "pairs_per_wave": PAIRS_PER_WAVE,
            "pair_concurrency": PAIR_CONCURRENCY,
            "arms": list(ARMS),
            "queries_per_pair": QUERIES_PER_PAIR,
            "results_per_query": RESULTS_PER_QUERY,
            "fetch_cap": FETCH_CAP,
            "shared_root_response_within_pair": True,
            "only_recursive_control_executes_suffix_requests": True,
            "both_arms_fetch_their_own_selected_source_set": True,
            "query_set_sha256": payload_sha256(NEUTRAL_QUERY_PAIRS),
            "neutral_query_value_or_direct_query_set_hash_persisted_in_result": False,
            "schedule": schedule(),
        },
        "provider": dict(PROVIDER),
        "gates": dict(GATES),
        "lease": {
            "path": str(LEASE),
            "owner": "v24281_single_shot_pair_v1",
            "purpose": "neutral_recursive_vs_task_union_single_shot_pair",
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
        != "neutral_public_documentation_task_union_request_count_pair_only"
        or not isinstance(pair, Mapping)
        or pair.get("pair_count") != PAIR_COUNT
        or pair.get("pair_concurrency") != PAIR_CONCURRENCY
        or pair.get("arms") != list(ARMS)
        or pair.get("query_set_sha256") != payload_sha256(NEUTRAL_QUERY_PAIRS)
        or pair.get("neutral_query_value_or_direct_query_set_hash_persisted_in_result")
        is not False
        or protocol.get("provider") != PROVIDER
        or protocol.get("gates") != GATES
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.81 protocol identity drifted")
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
            or any(
                sha256(_ordinary(root, relative)) != digest
                for relative, digest in manifest.items()
            )
        ):
            raise RuntimeError(f"V2.42.81 {name} manifest drifted")
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
