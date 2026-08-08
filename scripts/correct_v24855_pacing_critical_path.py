#!/usr/bin/env python3
"""Correct the V2.48.55 pacing counterfactual to use critical-path max wait.

The original immutable diagnosis used the sum of waits from concurrent query
threads.  That sum is valid load telemetry but is not a wall-clock critical
path and can over-subtract first-wave elapsed time.  This append-only report
supersedes only the pacing-counterfactual counts.  It leaves the frozen parent
artifact intact and publishes no task identifier or per-task value.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24854_rate_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    validate_receipt as validate_rate_receipt,
)


DATE = "20260808"
SOURCE = Path(
    "results/v24855_v24854_rate_aware_quality_diagnosis_v1_20260808.json"
)
OUTPUT = Path(
    f"results/v24855_v24854_pacing_critical_path_correction_v1_{DATE}.json"
)
RUN_ROOT = contract.OUTPUT_ROOT
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _read(path: Path) -> dict[str, Any]:
    absolute = ROOT / path
    if (
        path.is_absolute()
        or ".." in path.parts
        or absolute.is_symlink()
        or not absolute.is_file()
        or not absolute.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.55 correction expected ordinary file: {path}")
    value = json.loads(absolute.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.55 correction expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def build(*, now: int | None = None) -> dict[str, Any]:
    source = _read(SOURCE)
    if (
        source.get("role")
        != "v24855_v24854_rate_aware_quality_aggregate_diagnosis"
        or source.get("diagnosis_valid") is not True
        or source.get("findings") != []
        or not _sealed(source, "diagnosis_payload_sha256")
        or source.get("pacing_latency_mixture", {}).get(
            "pacing_mixed_stop_count"
        )
        != 21
    ):
        raise RuntimeError("V2.48.55 source diagnosis drifted")

    stop_count = 0
    sum_wait_below = 0
    max_wait_below = 0
    residual = 0
    positive_wait = 0
    elapsed_sum = 0.0
    total_wait_sum = 0.0
    max_wait_sum = 0.0
    for position in range(1, 221):
        envelope = _read(
            RUN_ROOT / "tasks" / f"task_{position:04d}" / "result.json"
        )
        inner = envelope.get("result") or {}
        retrieval = inner.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        controller = receipt.get("controller") or {}
        wave1 = receipt.get("wave1") or {}
        opaque_id = inner.get("opaque_id")
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or retrieval.get("status") != "completed"
            or controller.get("decision") not in {"expand", "stop"}
        ):
            raise RuntimeError("V2.48.55 correction task projection drifted")
        if controller["decision"] != "stop":
            continue
        rate = validate_rate_receipt(
            _read(
                RUN_ROOT
                / "tasks"
                / f"task_{position:04d}"
                / contract.RATE_RECEIPT_NAME
            )
        )
        elapsed = float(wave1["search_seconds"]) + float(
            wave1["fetch_seconds"]
        )
        total_wait = float(rate["total_provider_gate_wait_seconds"])
        max_wait = float(rate["max_provider_gate_wait_seconds"])
        if elapsed < 30.0 or max_wait > total_wait:
            raise RuntimeError("V2.48.55 correction timing invariant drifted")
        stop_count += 1
        elapsed_sum += elapsed
        total_wait_sum += total_wait
        max_wait_sum += max_wait
        positive_wait += int(max_wait > 0)
        sum_wait_below += int(elapsed - total_wait < 30.0)
        max_wait_below += int(elapsed - max_wait < 30.0)
        residual += int(elapsed - max_wait >= 30.0)

    value = {
        "artifact_version": 1,
        "role": "v24855_pacing_critical_path_correction",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "source_sum_wait_counterfactual_superseded_by_max_wait_critical_path",
        "source": {
            "path": str(SOURCE),
            "sha256": contract.sha256(ROOT / SOURCE),
            "diagnosis_payload_sha256": source["diagnosis_payload_sha256"],
            "source_artifact_mutated": False,
            "superseded_fields": [
                "pacing_latency_mixture.pacing_mixed_stop_count",
                "pacing_latency_mixture.residual_slow_stop_count",
                "pacing_latency_mixture.pacing_mixed_counterfactual_cohort",
            ],
        },
        "correction": {
            "v24854_latency_stop_count": stop_count,
            "source_sum_wait_below_30_count": sum_wait_below,
            "corrected_max_wait_below_30_count": max_wait_below,
            "corrected_residual_slow_count": residual,
            "stops_with_positive_provider_max_wait": positive_wait,
            "mean_wave1_elapsed_seconds": elapsed_sum / stop_count,
            "mean_sum_provider_wait_seconds": total_wait_sum / stop_count,
            "mean_max_provider_wait_seconds": max_wait_sum / stop_count,
            "critical_path_rule": (
                "wave1_elapsed_minus_max_provider_gate_wait_below_30_seconds"
            ),
            "concurrent_query_waits_summed_for_load_telemetry_only": True,
            "sum_wait_must_not_be_subtracted_from_wall_clock": True,
            "max_wait_is_conservative_same_pass_content_free_proxy": True,
            "wave2_execution_or_quality_gain_observed": False,
        },
        "boundary": {
            "postfreeze_content_free_receipts_only": True,
            "question_prediction_answer_query_url_page_evaluator_text_or_credential_accessed": False,
            "task_identifier_or_per_task_value_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "historical_stop_membership_authorized_as_runtime_route": False,
            "runtime_successor_may_use_same_pass_content_free_max_wait_only": True,
        },
        "conclusions": {
            "provider_wait_and_legacy_latency_are_still_materially_mixed": (
                max_wait_below > 0
            ),
            "original_count_21_is_valid_critical_path_count": False,
            "corrected_count_19_is_critical_path_count": max_wait_below == 19,
            "pacing_mixture_proves_quality_gain": False,
            "v24855_non_pacing_quality_and_transport_conclusions_superseded": False,
        },
        "authorization": {
            "pacing_aware_admission_adapter_build": True,
            "fresh_external_protocol_design": True,
            "fresh_external_launch": False,
            "public_dev64_or_exact220": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    checks = {
        "stop_denominator_reconciles": stop_count == 27,
        "source_sum_count_replays": sum_wait_below == 21,
        "critical_path_count_corrected": max_wait_below == 19,
        "critical_path_partition_reconciles": max_wait_below + residual == stop_count,
        "all_stops_have_positive_wait": positive_wait == stop_count,
        "max_wait_does_not_exceed_sum_wait": max_wait_sum <= total_wait_sum,
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["correction_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) or SECRET.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.48.55 correction emitted prohibited content")
    value["correction_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(value: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("correction_payload_sha256", None)
    if (
        copied.get("role") != "v24855_pacing_critical_path_correction"
        or copied.get("status")
        != "source_sum_wait_counterfactual_superseded_by_max_wait_critical_path"
        or copied.get("correction_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("correction", {}).get(
            "corrected_max_wait_below_30_count"
        )
        != 19
        or copied.get("boundary", {}).get(
            "historical_stop_membership_authorized_as_runtime_route"
        )
        is not False
        or copied.get("authorization", {}).get("public_dev64_or_exact220")
        is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.55 correction drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.55 correction is not reproducible")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build()
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "source_sum_wait_count": report["correction"][
                    "source_sum_wait_below_30_count"
                ],
                "corrected_max_wait_count": report["correction"][
                    "corrected_max_wait_below_30_count"
                ],
                "residual_slow_count": report["correction"][
                    "corrected_residual_slow_count"
                ],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
