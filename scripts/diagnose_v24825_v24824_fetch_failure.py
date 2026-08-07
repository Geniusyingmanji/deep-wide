#!/usr/bin/env python3
"""Aggregate-only diagnosis of V2.48.24 exact-fetch failure.

The script reads frozen per-task counters and health receipts after result
publication.  It emits no question, country, URL, page, value, prediction, or
credential.  It does not call network, model, search, fetch, or evaluator.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24824_quality_first_external_contract as contract  # noqa: E402


DATE = contract.DATE
OUTPUT = Path(
    f"results/v24825_v24824_fetch_failure_diagnosis_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24824_quality_first_external_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24824_quality_first_external_postresult_audit_v1_{DATE}.json"
)
BASELINE_ROOT = Path("outputs/v24815_worldbank_successor_v1_20260807/tasks")
CURRENT_ROOT = contract.TASK_ROOT


def payload_sha256(value: object) -> str:
    return contract.payload_sha256(value)


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


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.25 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.25 expected JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def aggregate(root: Path) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for path in sorted((ROOT / root).glob("task_*/result.json")):
        envelope = _read(path)
        result = envelope.get("result")
        health = envelope.get("transport_health")
        if not isinstance(result, Mapping) or not isinstance(health, Mapping):
            raise RuntimeError("V2.48.25 envelope schema drifted")
        receipt = result.get("receipt")
        prefix = result.get("shared_prefix")
        if not isinstance(receipt, Mapping) or not isinstance(prefix, Mapping):
            raise RuntimeError("V2.48.25 result receipt drifted")
        search = receipt.get("search_cost")
        first = prefix.get("first_wave_lookup_stats")
        full = receipt.get("full_lookup")
        if not all(isinstance(value, Mapping) for value in (search, first, full)):
            raise RuntimeError("V2.48.25 aggregate counter drifted")
        totals["tasks"] += 1
        for name in ("fetch_calls", "fetch_failures"):
            totals[name] += int(search[name])
        totals["generic_targets"] += int(receipt["generic_fetch_targets"])
        totals["generic_usable"] += int(receipt["generic_usable_pages"])
        totals["exact_targets"] += int(receipt["first_wave_lookup_targets"])
        totals["exact_targets"] += int(receipt["second_wave_lookup_targets"])
        for name in (
            "returned_result_count",
            "valid_exact_record_count",
            "null_value_record_count",
            "invalid_exact_response_count",
            "unmatched_or_duplicate_result_count",
            "missing_response_count",
        ):
            totals[f"full_{name}"] += int(full[name])
        for name in (
            "valid_exact_record_count",
            "missing_response_count",
        ):
            totals[f"first_{name}"] += int(first[name])
        for name in (
            "hard_fetch_helper_calls",
            "hard_fetch_deadline_failures",
            "fetch_deadline_rejections",
            "fetch_helper_failures",
        ):
            totals[name] += int(health[name])
    totals["generic_nonusable"] = (
        totals["generic_targets"] - totals["generic_usable"]
    )
    totals["exact_nonvalid"] = (
        totals["exact_targets"] - totals["full_valid_exact_record_count"]
    )
    totals["reconstructed_fetch_failures"] = (
        totals["generic_nonusable"] + totals["exact_nonvalid"]
    )
    return {key: int(value) for key, value in sorted(totals.items())}


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    checks = copied.get("checks")
    authorization = copied.get("authorization")
    if (
        copied.get("role") != "v24825_v24824_fetch_failure_diagnosis"
        or not isinstance(checks, Mapping)
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or copied.get("diagnosis_valid") is not (copied.get("findings") == [])
        or not isinstance(authorization, Mapping)
        or authorization.get("append_only_exact_api_transport_design")
        is not copied.get("diagnosis_valid")
        or authorization.get("same_population_retry_resume_rerun_or_revaluation")
        is not False
        or authorization.get("public_exact220") is not False
        or authorization.get("sota_claim") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.25 diagnosis drifted")
    return copied


def build(*, now: int | None = None) -> dict[str, Any]:
    result = _read(ROOT / RESULT)
    postaudit = _read(ROOT / POSTAUDIT)
    if (
        result.get("status")
        != "target_cell_disjoint_quality_first_mechanism_no_go"
        or result.get("passed") is not False
        or not _sealed(result, "result_payload_sha256")
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or not _sealed(postaudit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.25 parent result drifted")
    baseline = aggregate(BASELINE_ROOT)
    current = aggregate(CURRENT_ROOT)
    checks = {
        "baseline_complete_12_tasks": baseline["tasks"] == 12
        and baseline["exact_targets"] == 96,
        "current_complete_32_tasks": current["tasks"] == 32
        and current["exact_targets"] == 256,
        "current_fetch_failure_conservation": current["fetch_failures"]
        == current["reconstructed_fetch_failures"]
        == 275,
        "current_exact_failures_are_preprojection_missing": current[
            "full_missing_response_count"
        ]
        == current["exact_nonvalid"]
        == 252
        and current["full_invalid_exact_response_count"] == 0
        and current["full_null_value_record_count"] == 0
        and current["full_unmatched_or_duplicate_result_count"] == 0,
        "current_helper_processes_and_deadlines_healthy": current[
            "hard_fetch_helper_calls"
        ]
        == 320
        and current["hard_fetch_deadline_failures"] == 0
        and current["fetch_deadline_rejections"] == 0
        and current["fetch_helper_failures"] == 0,
        "current_exact_success_rate_materially_below_baseline": current[
            "full_valid_exact_record_count"
        ]
        * baseline["exact_targets"]
        < baseline["full_valid_exact_record_count"]
        * current["exact_targets"],
        "quality_first_controller_mechanism_itself_closed": result["metrics"][
            "adaptive_prediction_equals_fixed_full_tasks"
        ]
        == 32
        and set(result["metrics"]["adaptive_minus_fixed_full"].values()) == {0},
    }
    value = {
        "artifact_version": 1,
        "role": "v24825_v24824_fetch_failure_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "exact_api_transport_observability_and_success_failure_no_go",
        "parent_result_sha256": _sha256(ROOT / RESULT),
        "parent_postresult_audit_sha256": _sha256(ROOT / POSTAUDIT),
        "baseline_v24815_counts": baseline,
        "current_v24824_counts": current,
        "rates": {
            "baseline_exact_valid_rate": baseline[
                "full_valid_exact_record_count"
            ]
            / baseline["exact_targets"],
            "current_exact_valid_rate": current[
                "full_valid_exact_record_count"
            ]
            / current["exact_targets"],
            "current_generic_usable_rate": current["generic_usable"]
            / current["generic_targets"],
        },
        "causal_boundary": {
            "controller_wrong_stop_explains_failure": False,
            "parser_invalid_null_or_target_mismatch_explains_primary_failure": False,
            "helper_process_timeout_or_nonzero_exit_explains_primary_failure": False,
            "preprojection_fetch_non_ok_explains_all_252_exact_missing": True,
            "specific_non_ok_status_not_persisted_by_historical_transport": True,
            "concurrency_alone_identified_as_cause": False,
            "indicator_endpoint_behavior_alone_identified_as_cause": False,
            "transport_only_probe_not_part_of_diagnosis_artifact": True,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "diagnosis_valid": all(checks.values()),
        "effect_boundary": {
            "question_country_url_page_value_prediction_or_credential_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_population_replayed_retried_rerun_or_revalued": False,
        },
        "authorization": {
            "append_only_exact_api_transport_design": all(checks.values()),
            "same_population_retry_resume_rerun_or_revaluation": False,
            "new_external_population_or_launch": False,
            "public_exact220": False,
            "sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    publish(ROOT / OUTPUT, artifact)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": artifact["status"],
                "rates": artifact["rates"],
                "findings": artifact["findings"],
                "authorization": artifact["authorization"],
            },
            sort_keys=True,
        )
    )
