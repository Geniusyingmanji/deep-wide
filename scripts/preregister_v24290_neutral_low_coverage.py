#!/usr/bin/env python3
"""Freeze one fault-injected neutral V2.42.90 rescue probe."""

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

from scripts import probe_v24290_neutral_low_coverage as probe  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


OUTPUT = Path("results/v24290_neutral_low_coverage_preregistration_v1_20260803.json")
RESULT = probe.OUTPUT
DECISION = Path("results/v24290_neutral_low_coverage_decision_v1_20260803.json")
PROTOCOL_ID = "v24290_neutral_fault_injected_low_coverage_rescue_v1"
BUILD_AUDIT = Path("results/v24290_low_coverage_task_build_audit_v1_20260803.json")
FILES = (
    "src/deepwide_agent/v24289_low_coverage_rescue.py",
    "src/deepwide_agent/v24290_low_coverage_task_runtime.py",
    "scripts/probe_v24290_neutral_low_coverage.py",
    "tests/test_v24289_low_coverage_rescue.py",
    "tests/test_v24290_low_coverage_task_runtime.py",
    "tests/test_probe_v24290_neutral_low_coverage.py",
)
GATES = {
    "maximum_wall_seconds": 45.0,
    "required_completion_kinds": ["primary", "normalized_primary"],
    "required_controller_decision": "expand",
    "required_rescue_triggered": True,
    "minimum_rescue_fetches": 1,
    "minimum_rescue_usable_pages": 1,
    "usable_pages_after_must_exceed_before": True,
    "content_chars_after_must_exceed_before": True,
    "maximum_total_fetches": 10,
    "maximum_total_queries": 4,
    "maximum_hosted_search_requests_added_by_rescue": 0,
    "required_provider_search_calls_unchanged_during_rescue": True,
    "maximum_cache_misses": 0,
    "maximum_cache_serve_network_fetches": 0,
    "minimum_output_rows": 1,
    "required_output_columns": 5,
    "timing_additivity_required": True,
}
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if raw.is_absolute() or ".." in raw.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.90 neutral expected ordinary file: {relative}")
    return path


def _manifest(root: Path) -> dict[str, str]:
    value: dict[str, str] = {}
    for relative in FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.42.90 neutral credential literal in {relative}")
        value[relative] = sha256(path)
    return value


def build_protocol(root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    root = root.resolve()
    if require_pristine:
        present = [str(path) for path in (RESULT, DECISION) if (root / path).exists() or (root / path).is_symlink()]
        if present:
            raise RuntimeError(f"V2.42.90 neutral future surface is not pristine: {present}")
    audit_path = _ordinary(root, BUILD_AUDIT)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        audit.get("role") != "v24290_low_coverage_task_build_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or any(audit.get("authorization", {}).values())
    ):
        raise RuntimeError("V2.42.90 neutral build audit parent drifted")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24290_neutral_low_coverage_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "one_fault_injected_neutral_public_documentation_rescue_probe",
        "fault_injection": {
            "kind": "first_wave_visible_source_miss_after_real_provider_call",
            "real_first_wave_provider_call_counted": True,
            "only_first_wave_returned_source_batches_masked_in_memory": True,
            "second_wave_and_tail_provider_sources_unmodified": True,
            "claim_scope": "mechanism_robustness_not_natural_frequency_or_benchmark_quality",
        },
        "task_contract": {
            "synthetic_visible_task_only": True,
            "task_count": 1,
            "expected_column_count": 5,
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
        "retrieval_contract": {
            "maximum_queries": 4,
            "maximum_fetches": 10,
            "maximum_rescue_fetches": 4,
            "minimum_total_usable_pages": 4,
            "minimum_total_unique_hosts": 2,
            "content_chars_per_column": 1_200,
            "maximum_pre_rescue_retrieval_seconds": 60,
            "same_response_tail_only": True,
            "additional_hosted_search_request_for_rescue": False,
        },
        "gates": dict(GATES),
        "lease": {
            "path": "outputs/deepwide_benchmark_api.lease.lock",
            "owner": "v24290_neutral_low_coverage_probe_v1",
            "purpose": "neutral_public_documentation_low_coverage_tail_rescue",
            "nonblocking_single_owner": True,
        },
        "parents": {str(BUILD_AUDIT): sha256(audit_path)},
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_field_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_fault_injected_neutral_probe": True,
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


def validate_protocol(root: Path = ROOT, path: Path = OUTPUT, *, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else json.loads(_ordinary(root, path).read_text(encoding="utf-8"))
    unsigned = dict(protocol)
    seal = unsigned.pop("protocol_payload_sha256", None)
    task = protocol.get("task_contract")
    injection = protocol.get("fault_injection")
    source = protocol.get("source_policy")
    auth = protocol.get("authorization")
    manifest = protocol.get("surface_manifest")
    if (
        protocol.get("role") != "v24290_neutral_low_coverage_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope") != "one_fault_injected_neutral_public_documentation_rescue_probe"
        or protocol.get("gates") != GATES
        or not isinstance(task, Mapping)
        or task.get("task_count") != 1
        or task.get("expected_column_count") != 5
        or task.get("benchmark_manifest_or_task_opened") is not False
        or task.get("question_value_or_hash_persisted_in_result") is not False
        or not isinstance(injection, Mapping)
        or injection.get("claim_scope") != "mechanism_robustness_not_natural_frequency_or_benchmark_quality"
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(auth, Mapping)
        or auth.get("one_fault_injected_neutral_probe") is not True
        or any(value_ for key, value_ in auth.items() if key != "one_fault_injected_neutral_probe")
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(FILES)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(_ordinary(root, relative)) != digest for relative, digest in manifest.items())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.90 neutral protocol drifted")
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
