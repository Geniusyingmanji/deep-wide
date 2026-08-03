#!/usr/bin/env python3
"""Finalize the frozen V2.42.86 neutral probe without further effects."""

from __future__ import annotations

import argparse
import json
import os
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

from scripts import preregister_v24286_neutral_full_task as prereg  # noqa: E402
from scripts import probe_v24286_neutral_full_task as probe  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


OUTPUT = Path("results/v24286_neutral_full_task_decision_v1_20260803.json")


def _ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.86 neutral finalizer path is noncanonical")
    path = root / relative
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.86 neutral finalizer expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.86 neutral finalizer expected object")
    return value


def _checks(protocol: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, bool]:
    gates = protocol["gates"]
    timing = result["attributed_timing"]
    schema = result["visible_schema"]
    retrieval = result["two_wave_retrieval_health"]
    return {
        "maximum_wall_seconds": float(result["wall_seconds"])
        <= float(gates["maximum_wall_seconds"]),
        "required_completion_kind": result["completion_kind"]
        in gates["required_completion_kind"],
        "required_visible_schema_status": schema["status"]
        == gates["required_visible_schema_status"],
        "required_visible_schema_columns": schema["column_count"]
        == gates["required_visible_schema_columns"],
        "required_retrieval_status": retrieval["status"]
        == gates["required_retrieval_status"],
        "maximum_cache_misses": retrieval["cache_miss_count"]
        <= gates["maximum_cache_misses"],
        "maximum_network_fetches_during_cache_serve": retrieval[
            "network_fetches_during_cache_serve"
        ]
        <= gates["maximum_network_fetches_during_cache_serve"],
        "maximum_task_wall_seconds": float(timing["task_wall_seconds"])
        <= float(gates["maximum_task_wall_seconds"]),
        "timing_additivity_required": timing[
            "timings_are_additive_not_parallel_work_sum"
        ]
        is gates["timing_additivity_required"],
        "maximum_model_requests": result["model_counters"]["requests"]
        <= gates["maximum_model_requests"],
        "maximum_search_queries": result["budget"]["admitted_search_queries"]
        <= gates["maximum_search_queries"],
        "maximum_fetch_attempts": retrieval["fetches_attempted"]
        <= gates["maximum_fetch_attempts"],
        "no_forward_failure": result["failure_types"] == [],
    }


def validate_decision(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("decision_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "protocol_sha256",
        "probe_result_sha256",
        "status",
        "passed",
        "checks",
        "observed",
        "claim_scope",
        "source_policy",
        "authorization",
        "decision_payload_sha256",
    }
    checks = value.get("checks")
    observed = value.get("observed")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24286_neutral_full_task_decision"
        or value.get("protocol_id") != prereg.PROTOCOL_ID
        or value.get("status") != "engineering_go_benchmark_quality_unproven"
        or value.get("passed") is not True
        or not isinstance(checks, Mapping)
        or not checks
        or not all(checks.values())
        or not isinstance(observed, Mapping)
        or set(observed)
        != {
            "wall_seconds",
            "task_wall_seconds",
            "provider_search_seconds",
            "network_fetch_seconds",
            "controller_and_adapter_seconds",
            "cache_serve_seconds",
            "plan_seconds",
            "synthesis_seconds",
            "repair_seconds",
            "model_requests",
            "search_queries",
            "fetch_attempts",
            "usable_pages",
            "column_count",
            "row_count",
        }
        or value.get("claim_scope")
        != "neutral_engineering_latency_and_schema_only_not_deepwide_quality_or_sota"
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.86 neutral decision drifted")


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = prereg.validate_protocol(root)
    result = _read(root, probe.OUTPUT)
    probe.validate_projection(result)
    checks = _checks(protocol, result)
    if not all(checks.values()):
        raise RuntimeError("V2.42.86 neutral probe failed its frozen gate")
    timing = result["attributed_timing"]
    retrieval = result["two_wave_retrieval_health"]
    table = result["table_shape"]
    value = {
        "artifact_version": 1,
        "role": "v24286_neutral_full_task_decision",
        "protocol_id": prereg.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / prereg.OUTPUT),
        "probe_result_sha256": sha256(root / probe.OUTPUT),
        "status": "engineering_go_benchmark_quality_unproven",
        "passed": True,
        "checks": checks,
        "observed": {
            "wall_seconds": result["wall_seconds"],
            "task_wall_seconds": timing["task_wall_seconds"],
            "provider_search_seconds": timing["provider_search_seconds"],
            "network_fetch_seconds": timing["network_fetch_seconds"],
            "controller_and_adapter_seconds": timing["controller_and_adapter_seconds"],
            "cache_serve_seconds": timing["cache_serve_seconds"],
            "plan_seconds": timing["model_seconds"]["plan"],
            "synthesis_seconds": timing["model_seconds"]["synthesis"],
            "repair_seconds": timing["model_seconds"]["repair"],
            "model_requests": result["model_counters"]["requests"],
            "search_queries": result["budget"]["admitted_search_queries"],
            "fetch_attempts": retrieval["fetches_attempted"],
            "usable_pages": retrieval["usable_pages"],
            "column_count": table["column_count"],
            "row_count": table["row_count"],
        },
        "claim_scope": "neutral_engineering_latency_and_schema_only_not_deepwide_quality_or_sota",
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_field_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
            "training_credit_assignment": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)
    if output.is_absolute() or ".." in output.parts:
        raise ValueError("V2.42.86 neutral decision output must be repository-relative")
    decision = build_decision(root)
    _publish_new(root / output, decision)
    print(json.dumps({"path": str(output), "status": decision["status"]}, sort_keys=True))
