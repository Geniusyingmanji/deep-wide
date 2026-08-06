#!/usr/bin/env python3
"""Content-free post-forward audit for V2.46.94; never opens gold."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24312_deadline_reliability import validate_receipt as validate_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24686_worldbank_target_value_runtime import ARMS, validate_result  # noqa: E402
from deepwide_agent.v24694_worldbank_external_contract import (  # noqa: E402
    FORWARD_AUDIT,
    FORWARD_RESULT,
    MODEL_SLOT_CAP,
    PREDICTION_FREEZE,
    PREDICTIONS,
    PROTOCOL_ID,
    RUN_SUMMARY,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24696_worldbank_runner_integration import validate_envelope  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.94 expected object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.94 expected object")
    return value


def sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def build() -> dict[str, Any]:
    forward, freeze, summary = (
        read(ROOT / path) for path in (FORWARD_RESULT, PREDICTION_FREEZE, RUN_SUMMARY)
    )
    findings: list[str] = []
    if (
        forward.get("protocol_id") != PROTOCOL_ID
        or not sealed(forward, "result_sha256")
        or not sealed(freeze, "freeze_sha256")
        or not sealed(summary, "summary_sha256")
        or forward.get("prediction_freeze_sha256") != sha256(ROOT / PREDICTION_FREEZE)
        or freeze.get("predictions_sha256") != sha256(ROOT / PREDICTIONS)
    ):
        findings.append("forward_freeze_or_summary_invalid")
    rows = [
        json.loads(line)
        for line in (ROOT / PREDICTIONS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != SELECTED_COUNT:
        findings.append("denominator_drifted")
    for row in rows:
        for arm in ARMS:
            if row.get("prediction_sha256", {}).get(arm) != hashlib.sha256(
                str(row.get("predictions", {}).get(arm, "")).encode()
            ).hexdigest():
                findings.append("prediction_hash_drifted")
    totals = {
        "terminal_tasks": 0,
        "model_slot_acquisitions": 0,
        "model_slot_timeouts": 0,
        "hosted_search_attempts": 0,
        "hard_fetch_helper_calls": 0,
        "fetch_deadline_rejections": 0,
        "generic_fetch_targets": 0,
        "targeted_lookup_fetch_targets": 0,
        "valid_exact_record_count": 0,
        "missing_target_count": 0,
        "corrected_nonunknown_count": 0,
        "filled_unknown_count": 0,
        "changed_target_count": 0,
        "completion_check_passed_tasks": 0,
        "target_value_differs_from_expanded_tasks": 0,
    }
    for index in range(1, SELECTED_COUNT + 1):
        directory = ROOT / TASK_ROOT / f"task_{index:04d}"
        try:
            envelope = validate_envelope(read(directory / "result.json"))
            result = validate_result(envelope["result"])
            model = validate_model(
                read(directory / "model_slot_receipt.json"), expected_cap=MODEL_SLOT_CAP
            )
            transport = validate_transport_health(read(directory / "transport_health.json"))
            parent = read(directory / "parent_exit_receipt.json")
            terminal = read(directory / "child_terminal_receipt.json")
            if (
                parent.get("role") != "v24694_content_free_parent_exit_receipt"
                or parent.get("return_code") != 0
                or parent.get("timed_out") is not False
                or parent.get("task_result_valid") is not True
                or terminal.get("stage") != "result_envelope_written"
            ):
                raise ValueError
            receipt = result["receipt"]
            completion = receipt["completion_check"]
            if (
                receipt.get("positive_task_credit_assigned") is not False
                or receipt.get("entropy_shadow", {}).get("routes_or_changes_forward_effects") is not False
                or receipt.get("entropy_shadow", {}).get("positive_credit_assigned") is not False
                or receipt.get("target_value_candidate_uses_only_exact_official_address_records") is not True
                or result.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
            ):
                raise ValueError
            totals["terminal_tasks"] += 1
            totals["model_slot_acquisitions"] += int(model["acquisitions"])
            totals["model_slot_timeouts"] += int(model["slot_timeouts"])
            totals["hosted_search_attempts"] += int(transport["hosted_search_attempts"])
            totals["hard_fetch_helper_calls"] += int(transport["hard_fetch_helper_calls"])
            totals["fetch_deadline_rejections"] += int(transport["fetch_deadline_rejections"])
            totals["generic_fetch_targets"] += int(receipt["generic_fetch_targets"])
            totals["targeted_lookup_fetch_targets"] += int(receipt["targeted_lookup_fetch_targets"])
            totals["valid_exact_record_count"] += int(receipt["lookup"]["valid_exact_record_count"])
            totals["missing_target_count"] += int(completion["missing_target_count"])
            totals["corrected_nonunknown_count"] += int(completion["corrected_nonunknown_count"])
            totals["filled_unknown_count"] += int(completion["filled_unknown_count"])
            totals["changed_target_count"] += int(completion["changed_target_count"])
            totals["completion_check_passed_tasks"] += int(completion["passed"] is True)
            totals["target_value_differs_from_expanded_tasks"] += int(
                result["prediction_sha256"]["target_value"]
                != result["prediction_sha256"]["expanded_parser"]
            )
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            findings.append(f"task_{index:04d}_invalid")
    lease = lease_observation(ROOT, Path("/proc"))
    if (
        totals["terminal_tasks"] != SELECTED_COUNT
        or totals["model_slot_timeouts"] != 0
        or totals["valid_exact_record_count"] != SELECTED_COUNT * 8
        or totals["completion_check_passed_tasks"] != SELECTED_COUNT
    ):
        findings.append("effect_or_completion_accounting_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active_after_forward")
    mechanism_triggered = totals["target_value_differs_from_expanded_tasks"] > 0
    value = {
        "artifact_version": 1,
        "role": "v24694_worldbank_forward_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "checks": {
            **totals,
            "terminal_arm_predictions": len(rows) * len(ARMS),
            "mechanism_triggered": mechanism_triggered,
            "predictions_frozen_before_gold_or_provenance_open": True,
            "gold_or_provenance_opened_or_hashed_by_audit": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "shared_api_lease_active_after_forward": lease.get("active"),
        },
        "protected_watchers": protected_watcher_snapshot(),
        "findings": findings,
        "audit_valid": not findings,
        "forward_sha256": sha256(ROOT / FORWARD_RESULT),
        "authorization": {
            "postfreeze_external_evaluator_protocol_design": not findings and mechanism_triggered,
            "mechanism_no_go_without_evaluator": not findings and not mechanism_triggered,
            "evaluator_execution": False,
            "dev64": False,
            "exact220": False,
        },
    }
    value["audit_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.94 forward audit failed")
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    result = build()
    publish(ROOT / FORWARD_AUDIT, result)
    print(
        json.dumps(
            {
                "audit_valid": result["audit_valid"],
                "findings": result["findings"],
                "mechanism_triggered": result["checks"]["mechanism_triggered"],
                "completion_check_passed_tasks": result["checks"]["completion_check_passed_tasks"],
                "changed_target_count": result["checks"]["changed_target_count"],
            },
            sort_keys=True,
        )
    )
