#!/usr/bin/env python3
"""Content-free, read-only watcher for V2.42.64."""

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

from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24264_targeted_capacity import (  # noqa: E402
    ACTIVATION,
    LEASE_OWNER,
    OUTPUT,
    PROGRESS,
    RESULT,
    STATE,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
)
from scripts.run_v24264_targeted_capacity import (  # noqa: E402
    validate_progress,
    validate_result,
)


def build_state(root: Path = ROOT) -> dict:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    activation = read_object(root / ACTIVATION)
    unsigned = dict(activation)
    seal = unsigned.pop("activation_payload_sha256", None)
    if (
        activation.get("role") != "v24264_targeted_capacity_activation"
        or activation.get("status") != "active"
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.64 watcher activation drifted")
    lease = lease_observation(root, Path("/proc"))
    result_present = (root / RESULT).is_file() and not (root / RESULT).is_symlink()
    if result_present:
        validate_result(protocol, read_object(root / RESULT))
    progress_summary = None
    if (root / PROGRESS).is_file() and not (root / PROGRESS).is_symlink():
        progress = read_object(root / PROGRESS)
        validate_progress(progress)
        progress_summary = {
            key: progress.get(key)
            for key in (
                "status",
                "active_level",
                "active_wave",
                "completed_levels",
                "completed_executions",
                "level_summaries",
            )
        }
    status = (
        "complete_capacity_result_available"
        if result_present
        else "running_capacity_under_registered_lease"
        if lease.get("active") is True and lease.get("owner") == LEASE_OWNER
        else "waiting_for_capacity_launch"
        if lease.get("active") is False
        else "critical_lease_identity"
    )
    value = {
        "artifact_version": 1,
        "role": "v24264_targeted_capacity_watcher_state",
        "created_at_unix": int(time.time()),
        "label_blind": True,
        "status": status,
        "terminal": result_present,
        "result_present": result_present,
        "progress_summary": progress_summary,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "network_model_search_fetch_evaluator_or_api_called_by_watcher": False,
        "process_signal_restart_resume_skip_or_selective_retry": False,
        "paired_dev64_full220_leaderboard_or_sota_authorized": False,
    }
    value["state_payload_sha256"] = payload_sha256(value)
    return value


def publish_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--poll-seconds", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.poll_seconds <= 300:
        raise ValueError("V2.42.64 watcher poll interval is invalid")
    while True:
        state = build_state()
        publish_atomic(ROOT / STATE, state)
        if state["terminal"]:
            break
        time.sleep(args.poll_seconds)
