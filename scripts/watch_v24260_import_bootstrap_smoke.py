#!/usr/bin/env python3
"""Minimal read-only watcher for V2.42.60."""

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
from scripts.preregister_v24260_import_bootstrap_smoke import (  # noqa: E402
    ACTIVATION,
    LEASE_OWNER,
    OUTPUT,
    RESULT,
    STATE,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, read_object, sha256  # noqa: E402


ROLE = "v24260_import_bootstrap_smoke_watcher_state"


def build_state(root: Path = ROOT) -> dict:
    root = root.resolve()
    validate_protocol(root, OUTPUT)
    activation = read_object(root / ACTIVATION)
    unsigned = dict(activation)
    seal = unsigned.pop("activation_payload_sha256", None)
    if activation.get("role") != "v24260_import_bootstrap_smoke_activation" or activation.get("status") != "active" or activation.get("protocol_sha256") != sha256(root / OUTPUT) or seal != payload_sha256(unsigned):
        raise RuntimeError("V2.42.60 watcher activation drifted")
    lease = lease_observation(root, Path("/proc"))
    result = (root / RESULT).is_file() and not (root / RESULT).is_symlink()
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()),
        "label_blind": True,
        "status": "complete_smoke_result_available" if result else "running_smoke_under_registered_lease" if lease.get("active") is True and lease.get("owner") == LEASE_OWNER else "waiting_for_smoke_launch" if lease.get("active") is False else "critical_lease_identity",
        "terminal": result,
        "result_present": result,
        "lease_active": lease.get("active") is True,
        "lease_expected_owner": lease.get("owner") == LEASE_OWNER if lease.get("active") is True else False,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "network_model_search_fetch_evaluator_or_api_called_by_watcher": False,
        "process_signal_restart_resume_skip_or_selective_retry": False,
        "dev64_full220_leaderboard_or_sota_authorized": False,
    }
    value["state_payload_sha256"] = payload_sha256(value)
    return value


def publish_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


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
