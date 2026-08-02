#!/usr/bin/env python3
"""Minimal read-only watcher for V2.42.61."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24261_direct_executor_smoke import ACTIVATION, LEASE_OWNER, OUTPUT, RESULT, STATE, validate_protocol  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, read_object, sha256  # noqa: E402


def build_state(root: Path = ROOT):
    root = root.resolve()
    validate_protocol(root, OUTPUT)
    activation = read_object(root / ACTIVATION)
    unsigned = dict(activation)
    seal = unsigned.pop("activation_payload_sha256", None)
    if activation.get("role") != "v24261_direct_executor_smoke_activation" or seal != payload_sha256(unsigned):
        raise RuntimeError("V2.42.61 watcher activation drifted")
    lease = lease_observation(root, Path("/proc"))
    result = (root / RESULT).is_file()
    value = {"artifact_version": 1, "role": "v24261_direct_executor_smoke_watcher_state", "created_at_unix": int(time.time()), "label_blind": True, "status": "complete_smoke_result_available" if result else "running_smoke_under_registered_lease" if lease.get("active") is True and lease.get("owner") == LEASE_OWNER else "waiting_for_smoke_launch" if lease.get("active") is False else "critical_lease_identity", "terminal": result, "result_present": result, "mapping_gold_category_question_type_evaluator_score_read": False, "credential_value_read_persisted_hashed_or_emitted": False, "network_model_search_fetch_evaluator_or_api_called_by_watcher": False, "process_signal_restart_resume_skip_or_selective_retry": False, "dev64_full220_leaderboard_or_sota_authorized": False}
    value["state_payload_sha256"] = payload_sha256(value)
    return value


def publish_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, sort_keys=True) + "\n")
    os.replace(temp, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--poll-seconds", type=int, default=10)
    args = parser.parse_args()
    while True:
        value = build_state()
        publish_atomic(ROOT / STATE, value)
        if value["terminal"]:
            break
        time.sleep(args.poll_seconds)
