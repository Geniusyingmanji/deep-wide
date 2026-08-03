#!/usr/bin/env python3
"""Freeze the single neutral V2.42.86 schema/timing probe."""

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

from scripts import probe_v24286_neutral_full_task as probe  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


OUTPUT = Path("results/v24286_neutral_full_task_preregistration_v1_20260803.json")
RESULT = probe.OUTPUT
PROTOCOL_ID = "v24286_neutral_visible_schema_attributed_timing_v1"
FILES = (
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "scripts/preregister_v24286_neutral_full_task.py",
    "scripts/probe_v24286_neutral_full_task.py",
    "tests/test_v24286_visible_schema_runtime.py",
    "tests/test_probe_v24286_neutral_full_task.py",
)
PARENTS = (
    "results/v24286_visible_schema_timing_build_audit_v1_20260803.json",
    "results/v24275_two_wave_dev64_result_v2_20260802.json",
)
GATES = {
    "maximum_wall_seconds": 35.0,
    "required_completion_kind": ["primary", "normalized_primary"],
    "required_visible_schema_status": "applied",
    "required_visible_schema_columns": 3,
    "required_retrieval_status": "completed",
    "maximum_cache_misses": 0,
    "maximum_network_fetches_during_cache_serve": 0,
    "maximum_task_wall_seconds": 35.0,
    "timing_additivity_required": True,
    "maximum_model_requests": 3,
    "maximum_search_queries": 4,
    "maximum_fetch_attempts": 10,
}
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.86 neutral preregistration path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.86 neutral preregistration expected ordinary file: {relative}")
    return path


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    value: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.42.86 credential literal in {relative}")
        value[relative] = sha256(path)
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    if require_pristine and ((root / RESULT).exists() or (root / RESULT).is_symlink()):
        raise RuntimeError("V2.42.86 neutral result surface is not pristine")
    parents = {relative: sha256(_ordinary(root, relative)) for relative in PARENTS}
    audit = json.loads(_ordinary(root, PARENTS[0]).read_text(encoding="utf-8"))
    dev64 = json.loads(_ordinary(root, PARENTS[1]).read_text(encoding="utf-8"))
    if (
        audit.get("audit_valid") is not True
        or dev64.get("status") != "development_gate_no_go"
        or dev64.get("decision", {}).get("passed") is not False
    ):
        raise RuntimeError("V2.42.86 neutral parent status drifted")
    manifest = _manifest(root, FILES)
    value = {
        "artifact_version": 1,
        "role": "v24286_neutral_full_task_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "one_neutral_public_documentation_schema_and_attributed_latency_probe",
        "task_contract": {
            "synthetic_visible_task_only": True,
            "task_count": 1,
            "expected_column_count": 3,
            "question_value_or_hash_persisted_in_result": False,
            "benchmark_manifest_or_task_opened": False,
        },
        "provider": {
            "proxy_url": "http://127.0.0.1:9878/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "timeout_seconds": 180,
            "max_retries": 2,
            "search_context_size": "medium",
            "search_batch_size": 8,
            "fetch_workers": 8,
            "fetch_timeout_seconds": 20,
        },
        "gates": dict(GATES),
        "lease": {
            "path": "outputs/deepwide_benchmark_api.lease.lock",
            "owner": "v24286_neutral_full_task_probe_v1",
            "purpose": "neutral_public_documentation_schema_and_attributed_latency_probe",
            "nonblocking_single_owner": True,
        },
        "parents": parents,
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_field_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_neutral_provider_probe": True,
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
    protocol = (
        dict(value)
        if value is not None
        else json.loads(_ordinary(root, path).read_text(encoding="utf-8"))
    )
    unsigned = dict(protocol)
    seal = unsigned.pop("protocol_payload_sha256", None)
    task = protocol.get("task_contract")
    source = protocol.get("source_policy")
    authorization = protocol.get("authorization")
    manifest = protocol.get("surface_manifest")
    if (
        protocol.get("role") != "v24286_neutral_full_task_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "one_neutral_public_documentation_schema_and_attributed_latency_probe"
        or not isinstance(task, Mapping)
        or task.get("task_count") != 1
        or task.get("expected_column_count") != 3
        or task.get("question_value_or_hash_persisted_in_result") is not False
        or task.get("benchmark_manifest_or_task_opened") is not False
        or protocol.get("gates") != GATES
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or authorization.get("one_neutral_provider_probe") is not True
        or any(value_ for key, value_ in authorization.items() if key != "one_neutral_provider_probe")
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(FILES)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(_ordinary(root, relative)) != digest for relative, digest in manifest.items())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.86 neutral preregistration drifted")
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
