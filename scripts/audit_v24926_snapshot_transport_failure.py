#!/usr/bin/env python3
"""Quarantine the one-shot V2.49.26 partial snapshot transport failure."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "20260808"
PROTOCOL_ID = "v24926_fresh_worldbank_snapshot_transport_v1"
PROTOCOL = Path(f"results/v24926_snapshot_transport_preregistration_v1_{DATE}.json")
START = Path(f"results/v24926_snapshot_transport_execution_start_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24926_snapshot_transport_v1_{DATE}")
RESPONSE = OUTPUT_ROOT / "responses" / "response_01.bin"
OUTPUT = Path(
    f"results/DO_NOT_USE_invalid_v24926_snapshot_transport_http400_{DATE}"
    "/invalid_run_audit.json"
)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.26 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.26 expected JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    marker = "scripts/control_v24926_snapshot_transport_gate.py execute"
    return [
        int(line.strip().split(maxsplit=1)[0])
        for line in completed.stdout.splitlines()
        if marker in line and "audit_v24926_snapshot_transport_failure.py" not in line
    ]


def _publish(path: Path, value: dict[str, Any]) -> None:
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


def build() -> dict[str, Any]:
    protocol = _read(ROOT / PROTOCOL)
    start = _read(ROOT / START)
    response = ROOT / RESPONSE
    files = sorted(
        str(path.relative_to(ROOT / OUTPUT_ROOT))
        for path in (ROOT / OUTPUT_ROOT).rglob("*")
        if path.is_file() or path.is_symlink()
    )
    protected = protocol.get("protected_watchers") or []
    current = []
    for item in protected:
        pid = int(item["pid"])
        stat = Path(f"/proc/{pid}/stat")
        if not stat.is_file():
            continue
        fields = stat.read_text(encoding="utf-8").split()
        current.append(
            {
                "marker": item["marker"],
                "pid": pid,
                "start_ticks": int(fields[21]),
            }
        )
    checks = {
        "protocol_has_no_findings": protocol.get("findings") == [],
        "single_execution_was_authorized": start.get("authorization", {}).get(
            "single_snapshot_transport_execution"
        )
        is True,
        "exactly_first_response_was_published": files == ["responses/response_01.bin"],
        "first_response_is_nonempty_ordinary_file": response.is_file()
        and not response.is_symlink()
        and response.stat().st_size > 0,
        "result_manifest_and_postaudit_absent": not any(
            (ROOT / path).exists()
            for path in (
                Path(f"results/v24926_snapshot_transport_result_v1_{DATE}.json"),
                Path(f"results/v24926_snapshot_transport_postresult_audit_v1_{DATE}.json"),
                OUTPUT_ROOT / "snapshot_manifest.json",
            )
        ),
        "execution_process_absent": not _running(),
        "protected_watchers_unchanged": current == protected,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24926_snapshot_transport_failure_invalid_run_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "invalid_for_quality_partial_snapshot_transport_http400",
        "protocol_sha256": _sha256(ROOT / PROTOCOL),
        "execution_start_sha256": _sha256(ROOT / START),
        "failure": {
            "stage": "serial_official_snapshot_fetch_after_first_response_freeze",
            "class": "HTTPError",
            "http_status": 400,
            "completed_request_count": 1,
            "failed_request_position": 2,
            "attempts_per_url": 1,
            "retry_resume_or_selective_rerun_performed": False,
            "model_search_or_evaluator_called": False,
            "prediction_created": False,
        },
        "partial_artifact": {
            "path": str(RESPONSE),
            "bytes": response.stat().st_size,
            "sha256": _sha256(response),
            "permitted_for_future_quality_or_transport_claim": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "quarantine": {
            "same_targets_retry_resume_rerun_or_revaluation": False,
            "same_output_root_reuse": False,
            "partial_response_reuse": False,
            "transport_or_quality_success_claim": False,
        },
        "authorization": {
            "independent_exact220_protocol_design": all(checks.values()),
            "same_population_retry_resume_or_rerun": False,
            "evaluator": False,
            "sota_claim": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    unsigned = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    value["audit_payload_sha256"] = hashlib.sha256(unsigned).hexdigest()
    return value


def main() -> None:
    value = build()
    if not value["audit_valid"]:
        raise RuntimeError(f"V2.49.26 quarantine failed: {value['findings']}")
    _publish(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "status": value["status"], "findings": []}))


if __name__ == "__main__":
    main()
