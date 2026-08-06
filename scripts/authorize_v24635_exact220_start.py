#!/usr/bin/env python3
"""Freeze the V2.46.35 execution-start authorization before first effect."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    ACTIVATION, EXECUTION_START, EXECUTOR_CONCURRENCY, FORWARD_CONTRACT,
    FORWARD_RESULT, MODEL_SLOT_CAP, OUTPUT_ROOT, PREAUDIT, SELECTED_COUNT,
    payload_sha256, protected_watcher_snapshot, read_object, sha256,
    validate_forward_contract,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24635_exact220 import publish_new  # noqa: E402
from scripts.run_v24635_exact220 import validate_activation, validate_preaudit  # noqa: E402


def build_start(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    contract = validate_forward_contract(root)
    validate_preaudit(root, contract)
    validate_activation(root, contract)
    lease = lease_observation(root, Path("/proc"))
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "target/main"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()
    tracked = all(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)], cwd=root,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        ).returncode == 0
        for path in (FORWARD_CONTRACT, PREAUDIT, ACTIVATION)
    )
    if (
        lease.get("active") is not False
        or head != remote
        or status
        or not tracked
        or any((root / path).exists() or (root / path).is_symlink() for path in (EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT))
    ):
        raise RuntimeError("V2.46.35 execution-start surface is not pristine")
    value = {
        "artifact_version": 1,
        "role": "v24635_exact220_execution_start_authorization",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized_not_started",
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "runtime_input_contract": ["opaque_id", "question"],
        "protected_watchers": protected_watcher_snapshot(),
        "api_called_before_execution_start": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "evaluator_imported_or_called": False,
        "resume_retry_skip_or_rerun": False,
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": not status,
            "contract_preaudit_and_activation_tracked": tracked,
        },
        "authorization": {
            "single_fresh_exact220_forward": True,
            "evaluator_call": False,
            "resume_retry_skip_or_rerun": False,
        },
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    value = build_start()
    publish_new(ROOT / EXECUTION_START, value)
    print(json.dumps({"path": str(EXECUTION_START), "status": value["status"]}, sort_keys=True))
