#!/usr/bin/env python3
"""Create the effect-free V2.46.37 launch activation."""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24637_external_contract import (  # noqa: E402
    ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT, PREAUDIT, PROTOCOL,
    PROTOCOL_ID, payload_sha256, protected_watcher_snapshot, sha256,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.37 activation expected an object")
    return value


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def build() -> dict:
    protocol = read(ROOT / PROTOCOL)
    audit = read(ROOT / PREAUDIT)
    findings = []
    if protocol.get("protocol_id") != PROTOCOL_ID or audit.get("audit_valid") is not True or audit.get("launch_authorized") is not True:
        findings.append("protocol_or_preaudit_invalid")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)):
        findings.append("future_surface_not_pristine")
    if lease_observation(ROOT, Path("/proc")).get("active") is not False:
        findings.append("shared_api_lease_active")
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=1): pass
    except OSError:
        findings.append("gpt56_endpoint_unreachable")
    watchers = protected_watcher_snapshot()
    if watchers != audit.get("protected_watchers"):
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1, "role": "v24638_objective_alignment_activation",
        "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()),
        "status": "active" if not findings else "rejected", "findings": findings,
        "launch_authorized": not findings, "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preaudit_sha256": sha256(ROOT / PREAUDIT), "protected_watchers": watchers,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {"one_external_forward_launch": not findings, "evaluator": False, "dev64": False, "exact220": False},
    }
    value["activation_sha256"] = payload_sha256(value)
    if findings: raise RuntimeError("V2.46.37 activation rejected: " + ",".join(findings))
    return value


if __name__ == "__main__":
    value = build(); publish(ROOT / ACTIVATION, value)
    print(json.dumps({"status": value["status"], "launch_authorized": value["launch_authorized"]}, sort_keys=True))
