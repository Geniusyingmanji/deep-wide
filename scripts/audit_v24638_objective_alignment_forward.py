#!/usr/bin/env python3
"""Audit the frozen V2.46.38 external forward without opening gold."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from deepwide_agent.v24312_deadline_reliability import validate_receipt as validate_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24637_external_contract import (  # noqa: E402
    FORWARD_AUDIT, FORWARD_RESULT, MODEL_SLOT_CAP, OUTPUT_ROOT, PREDICTION_FREEZE,
    PREDICTIONS, PROTOCOL_ID, RUN_SUMMARY, SELECTED_COUNT, TASK_ROOT,
    payload_sha256, protected_watcher_snapshot, sha256,
)
from deepwide_agent.v24637_objective_alignment_runtime import ARMS, validate_result  # noqa: E402


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise RuntimeError("V2.46.38 forward audit expected object")
    return value


def sealed(value: dict, field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None); return seal == payload_sha256(unsigned)


def build() -> dict:
    forward = read(ROOT / FORWARD_RESULT)
    freeze = read(ROOT / PREDICTION_FREEZE)
    summary = read(ROOT / RUN_SUMMARY)
    findings = []
    if forward.get("protocol_id") != PROTOCOL_ID or not sealed(forward, "result_sha256"): findings.append("forward_invalid")
    if not sealed(freeze, "freeze_sha256") or not sealed(summary, "summary_sha256"): findings.append("freeze_or_summary_invalid")
    if forward.get("prediction_freeze_sha256") != sha256(ROOT / PREDICTION_FREEZE) or freeze.get("predictions_sha256") != sha256(ROOT / PREDICTIONS): findings.append("freeze_binding_drifted")
    rows = [json.loads(line) for line in (ROOT / PREDICTIONS).read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != SELECTED_COUNT or any(set(row.get("predictions", {})) != set(ARMS) for row in rows): findings.append("prediction_denominator_drifted")
    for row in rows:
        for arm in ARMS:
            if row.get("prediction_sha256", {}).get(arm) != hashlib.sha256(str(row["predictions"][arm]).encode()).hexdigest(): findings.append("prediction_hash_drifted")
    valid = 0
    model_requests = 0
    slot_timeouts = 0
    for position in range(1, SELECTED_COUNT + 1):
        directory = ROOT / TASK_ROOT / f"task_{position:04d}"
        try:
            validate_result(read(directory / "result.json"))
            model = validate_model(read(directory / "model_slot_receipt.json"), expected_cap=MODEL_SLOT_CAP)
            validate_transport_health(read(directory / "transport_health.json"))
            parent = read(directory / "parent_exit_receipt.json")
            terminal = read(directory / "child_terminal_receipt.json")
            if parent.get("task_result_valid") is not True or parent.get("return_code") != 0 or parent.get("timed_out") is not False or terminal.get("stage") != "result_envelope_written": raise ValueError
            valid += 1; model_requests += int(model["acquisitions"]); slot_timeouts += int(model["slot_timeouts"])
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            findings.append(f"task_{position:04d}_receipt_invalid")
    if valid != SELECTED_COUNT or model_requests != SELECTED_COUNT * 3 or slot_timeouts != 0: findings.append("effect_or_reliability_accounting_drifted")
    value = {
        "artifact_version": 1, "role": "v24638_objective_alignment_forward_audit",
        "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()),
        "checks": {"terminal_tasks": valid, "terminal_arm_predictions": len(rows) * len(ARMS), "model_slot_acquisitions": model_requests, "model_slot_timeouts": slot_timeouts, "predictions_frozen_before_gold_open": True, "gold_path_opened_or_hashed_by_audit": False, "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False, "network_model_search_fetch_or_evaluator_called_by_audit": False},
        "protected_watchers": protected_watcher_snapshot(), "findings": findings,
        "audit_valid": not findings, "forward_sha256": sha256(ROOT / FORWARD_RESULT),
        "authorization": {"postfreeze_external_evaluator_protocol_design": not findings, "dev64": False, "exact220": False},
    }
    value["audit_sha256"] = payload_sha256(value)
    if findings: raise RuntimeError("V2.46.38 forward audit failed")
    return value


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build(); publish(ROOT / FORWARD_AUDIT, value); print(json.dumps({"audit_valid": value["audit_valid"], "findings": value["findings"]}, sort_keys=True))
