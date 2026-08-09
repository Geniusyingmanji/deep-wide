#!/usr/bin/env python3
"""Seal the pre-snapshot V2.49.51 transport failure without retrying it."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24951_partial_signature_external_contract as contract  # noqa: E402
from scripts.control_v24923_target_value_external import _lease_inactive  # noqa: E402


OUTPUT = Path(
    f"results/DO_NOT_USE_invalid_v24951_snapshot_transport_failure_{contract.DATE}/invalid_run_audit.json"
)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.49.51 failure audit expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.51 failure audit expected JSON object")
    return value


def _running() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    )
    marker = str(contract.RUNNER)
    return [
        int(line.strip().split(maxsplit=1)[0])
        for line in completed.stdout.splitlines()
        if marker in line and "audit_v24951_snapshot_transport_failure.py" not in line
    ]


def build(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / contract.PROTOCOL)
    start = _read(ROOT / contract.EXECUTION_START)
    root = ROOT / contract.OUTPUT_ROOT
    expected_empty_dirs = (
        root / "model_slots",
        root / "snapshot" / "target_responses",
        root / "tasks",
    )
    files = [path for path in root.rglob("*") if path.is_file() or path.is_symlink()]
    checks = {
        "protocol_sealed": contract.sealed(protocol, "protocol_payload_sha256"),
        "execution_start_sealed": contract.sealed(
            start, "execution_start_payload_sha256"
        ),
        "single_forward_was_authorized": start.get("authorization", {}).get(
            "single_external_forward"
        )
        is True,
        "output_root_exists": root.is_dir() and not root.is_symlink(),
        "no_response_or_prediction_artifact_persisted": not files,
        "expected_create_only_directories_present": all(
            path.is_dir() and not path.is_symlink() for path in expected_empty_dirs
        ),
        "runner_absent": not _running(),
        "shared_api_lease_released": _lease_inactive(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
        "forward_result_absent": not (ROOT / contract.FORWARD_RESULT).exists(),
        "forward_audit_absent": not (ROOT / contract.FORWARD_AUDIT).exists(),
        "prediction_freeze_absent": not (ROOT / contract.PREDICTION_FREEZE).exists(),
        "predictions_absent": not (ROOT / contract.PREDICTIONS).exists(),
        "projections_absent": not (ROOT / contract.PROJECTIONS).exists(),
        "visible_tasks_absent": not (ROOT / contract.VISIBLE_TASKS).exists(),
        "evaluator_protocol_absent": not (ROOT / contract.EVALUATOR_PROTOCOL).exists(),
        "evaluator_result_absent": not (ROOT / contract.RESULT).exists(),
        "postresult_audit_absent": not (ROOT / contract.POSTAUDIT).exists(),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24951_snapshot_transport_failure_invalid_run_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "invalid_for_quality_snapshot_transport_timeout_before_freeze",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "failure": {
            "stage": "concurrent_official_snapshot_fetch_before_any_response_publish",
            "class": "TimeoutError",
            "socket_wall_seconds": contract.FETCH_TIMEOUT_SECONDS,
            "fixed_request_count": 1 + len(contract.TARGETS),
            "which_request_timed_out_or_completed": "intentionally_not_recovered_or_inferred",
            "model_requests": 0,
            "predictions": 0,
            "evaluator_calls": 0,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "quarantine": {
            "same_target_or_entity_population_resume_retry_rerun_or_revaluation": False,
            "same_output_root_reuse": False,
            "ordinary_forward_result_or_decision_publication": False,
            "quality_or_mechanism_claim": False,
        },
        "authorization": {
            "fresh_bounded_transport_successor_design": all(checks.values()),
            "same_population_retry_resume_or_rerun": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    value = build()
    if not value["audit_valid"]:
        raise RuntimeError(f"V2.49.51 invalid-run audit failed: {value['findings']}")
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=False)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "status": value["status"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
