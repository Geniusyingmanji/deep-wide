#!/usr/bin/env python3
"""Freeze and audit four fresh World Bank snapshots, without model/evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24925_sparse_target_value_external_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts.control_v24925_sparse_target_value_external import _lease_inactive  # noqa: E402


DATE = "20260808"
PROTOCOL_ID = "v24926_fresh_worldbank_snapshot_transport_v1"
HISTORICAL_BOUNDARY_COMMIT = "890fe86638f842f926193f6c55344060fe6d2a6a"
TARGETS = (
    {"indicator": "SP.POP.TOTL.FE.IN", "year": "2023"},
    {"indicator": "SP.POP.TOTL.MA.IN", "year": "2023"},
    {"indicator": "SP.POP.TOTL.FE.ZS", "year": "2023"},
    {"indicator": "SP.POP.TOTL.MA.ZS", "year": "2023"},
)
TARGET_KEYS = tuple(f"{target['indicator']}@{target['year']}" for target in TARGETS)
URLS = tuple(
    "https://api.worldbank.org/v2/country/all/indicator/"
    + target["indicator"]
    + "?date="
    + target["year"]
    + "&format=json&per_page=400"
    for target in TARGETS
)
CATALOG = Path(
    "outputs/v24923_target_value_external_v1_20260808/snapshot/country_catalog.bin"
)
PROTOCOL = Path(f"results/v24926_snapshot_transport_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24926_snapshot_transport_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24926_snapshot_transport_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24926_snapshot_transport_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24926_snapshot_transport_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24926_snapshot_transport_v1_{DATE}")
RESPONSE_ROOT = OUTPUT_ROOT / "responses"
SNAPSHOT_MANIFEST = OUTPUT_ROOT / "snapshot_manifest.json"
SOURCE = Path("scripts/control_v24926_snapshot_transport_gate.py")
SOCKET_WALL_SECONDS = 90
MAX_BYTES = 2 * 1024 * 1024


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


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.26 requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.49.26 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.26 expected JSON object")
    return value


def _publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _new_bytes(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _historical_hits(key: str) -> list[str]:
    completed = subprocess.run(
        ["git", "grep", "-l", "-F", key, HISTORICAL_BOUNDARY_COMMIT, "--"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RuntimeError("V2.49.26 historical scan failed")
    return [line for line in completed.stdout.splitlines() if line]


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _git("cat-file", "-e", f"{HISTORICAL_BOUNDARY_COMMIT}^{{commit}}")
    hits = {key: _historical_hits(key) for key in TARGET_KEYS}
    checks = {
        "fresh_target_literals_absent_at_historical_boundary": not any(
            bool(paths) for paths in hits.values()
        ),
        "catalog_is_existing_frozen_ordinary_file": (ROOT / CATALOG).is_file()
        and not (ROOT / CATALOG).is_symlink(),
        "future_surface_pristine": _future_pristine(
            (PROTOCOL, PREAUDIT, EXECUTION_START, RESULT, POSTAUDIT, OUTPUT_ROOT)
        ),
        "protected_watchers_present": bool(protected_watcher_snapshot()),
        "shared_api_lease_inactive": _lease_inactive(),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24926_snapshot_transport_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "historical_boundary_commit": HISTORICAL_BOUNDARY_COMMIT,
        "target_keys_fixed_unread": list(TARGET_KEYS),
        "historical_target_literal_hits": hits,
        "frozen_catalog_sha256": sha256(ROOT / CATALOG),
        "transport": {
            "request_count": len(URLS),
            "execution_order": "serial_target_order",
            "attempts_per_url": 1,
            "socket_wall_seconds": SOCKET_WALL_SECONDS,
            "maximum_response_bytes": MAX_BYTES,
            "required_http_status": 200,
            "required_json_schema": "worldbank_two_element_response_with_list_records",
            "minimum_non_null_iso3_records_per_target": 170,
            "create_exclusive_raw_response_freeze": True,
            "no_cache_resume_retry_or_selective_rerun": True,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "source_policy": {
            "benchmark_question_mapping_gold_category_evaluator_score_reward_read": False,
            "model_search_fetch_helper_or_evaluator_called": False,
            "raw_url_page_value_or_record_persisted_outside_frozen_response_files": False,
        },
        "authorization": {
            "preactivation_audit_generation": all(checks.values()),
            "single_snapshot_transport_execution": False,
            "model_or_quality_forward": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / PROTOCOL)
    checks = {
        "protocol_sealed": (
            lambda unsigned: unsigned.pop("protocol_payload_sha256", None)
            == payload_sha256(unsigned)
        )(dict(protocol)),
        "protocol_findings_empty": protocol.get("findings") == [],
        "source_tracked_and_unchanged": subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(SOURCE)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0,
        "catalog_hash_unchanged": protocol.get("frozen_catalog_sha256")
        == sha256(ROOT / CATALOG),
        "shared_api_lease_inactive": _lease_inactive(),
        "protected_watchers_unchanged": protected_watcher_snapshot()
        == protocol["protected_watchers"],
        "future_surface_pristine": _future_pristine(
            (PREAUDIT, EXECUTION_START, RESULT, POSTAUDIT, OUTPUT_ROOT)
        ),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24926_snapshot_transport_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "network_effect_started": False,
        "authorization": {
            "execution_start_generation": all(checks.values()),
            "single_snapshot_transport_execution": False,
            "model_or_quality_forward": False,
            "evaluator": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def build_start(*, now: int | None = None) -> dict[str, Any]:
    protocol, audit = _read(ROOT / PROTOCOL), _read(ROOT / PREAUDIT)
    checks = {
        "protocol_sealed": (
            lambda unsigned: unsigned.pop("protocol_payload_sha256", None)
            == payload_sha256(unsigned)
        )(dict(protocol)),
        "preactivation_audit_valid": audit.get("audit_valid") is True
        and audit.get("findings") == [],
        "lease_inactive": _lease_inactive(),
        "protected_watchers_unchanged": protected_watcher_snapshot()
        == protocol["protected_watchers"],
        "future_surface_pristine": _future_pristine(
            (EXECUTION_START, RESULT, POSTAUDIT, OUTPUT_ROOT)
        ),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24926_snapshot_transport_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized_not_started" if all(checks.values()) else "rejected",
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preactivation_audit_sha256": sha256(ROOT / PREAUDIT),
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "first_network_effect_started": False,
        "authorization": {
            "single_snapshot_transport_execution": all(checks.values()),
            "resume_retry_or_selective_rerun": False,
            "model_or_quality_forward": False,
            "evaluator": False,
        },
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


def _fetch(url: str) -> tuple[bytes, float]:
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "deepwide-v24926/1.0"})
    with urllib.request.urlopen(request, timeout=SOCKET_WALL_SECONDS) as response:
        if response.status != 200:
            raise RuntimeError("V2.49.26 official snapshot status drifted")
        data = response.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise RuntimeError("V2.49.26 official snapshot size drifted")
    return data, time.monotonic() - started


def _validate(blob: bytes) -> tuple[int, int]:
    value = json.loads(blob)
    records = value[1] if isinstance(value, list) and len(value) == 2 else None
    if not isinstance(records, list):
        raise RuntimeError("V2.49.26 official snapshot schema drifted")
    iso3 = {
        str(record.get("countryiso3code", "")).strip().upper()
        for record in records
        if isinstance(record, dict)
        and record.get("value") is not None
        and len(str(record.get("countryiso3code", "")).strip()) == 3
    }
    if len(iso3) < 170:
        raise RuntimeError("V2.49.26 official snapshot completeness drifted")
    return len(records), len(iso3)


def execute(*, now: int | None = None) -> dict[str, Any]:
    protocol, start = _read(ROOT / PROTOCOL), _read(ROOT / EXECUTION_START)
    if (
        start.get("status") != "authorized_not_started"
        or start.get("authorization", {}).get("single_snapshot_transport_execution")
        is not True
    ):
        raise RuntimeError("V2.49.26 execution authorization drifted")
    if (ROOT / OUTPUT_ROOT).exists():
        raise RuntimeError("V2.49.26 output root not pristine")
    (ROOT / RESPONSE_ROOT).mkdir(parents=True, mode=0o700)
    rows = []
    for index, (key, url) in enumerate(zip(TARGET_KEYS, URLS, strict=True), 1):
        blob, elapsed = _fetch(url)
        record_count, non_null_iso3 = _validate(blob)
        path = ROOT / RESPONSE_ROOT / f"response_{index:02d}.bin"
        _new_bytes(path, blob)
        rows.append(
            {
                "target_key": key,
                "response_sha256": hashlib.sha256(blob).hexdigest(),
                "response_bytes": len(blob),
                "record_count": record_count,
                "non_null_unique_iso3_count": non_null_iso3,
                "elapsed_seconds": round(elapsed, 6),
                "attempt_count": 1,
                "http_status": 200,
            }
        )
    manifest: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24926_frozen_snapshot_manifest",
        "protocol_id": PROTOCOL_ID,
        "targets": rows,
        "all_four_snapshots_frozen": len(rows) == 4,
        "serial_single_attempt_no_retry": True,
        "model_or_evaluator_called": False,
    }
    manifest["manifest_payload_sha256"] = payload_sha256(manifest)
    _publish(ROOT / SNAPSHOT_MANIFEST, manifest)
    checks = {
        "all_four_snapshots_frozen": len(rows) == len(TARGETS),
        "all_http_200": all(row["http_status"] == 200 for row in rows),
        "all_single_attempt": all(row["attempt_count"] == 1 for row in rows),
        "all_schema_and_completeness_valid": all(
            row["non_null_unique_iso3_count"] >= 170 for row in rows
        ),
        "manifest_sealed": True,
        "catalog_unchanged": protocol.get("frozen_catalog_sha256")
        == sha256(ROOT / CATALOG),
        "protected_watchers_unchanged": protected_watcher_snapshot()
        == protocol["protected_watchers"],
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24926_snapshot_transport_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "snapshot_transport_go" if all(checks.values()) else "snapshot_transport_no_go",
        "passed": all(checks.values()),
        "snapshot_manifest_sha256": sha256(ROOT / SNAPSHOT_MANIFEST),
        "targets": rows,
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "model_search_fetch_helper_or_evaluator_called": False,
        "authorization": {
            "fresh_snapshot_bound_quality_gate_design": all(checks.values()),
            "quality_forward_launch": False,
            "public_dev64_or_exact220": False,
            "sota_claim": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def postaudit(*, now: int | None = None) -> dict[str, Any]:
    result = _read(ROOT / RESULT)
    manifest = _read(ROOT / SNAPSHOT_MANIFEST)
    findings = []
    unsigned = dict(result)
    if unsigned.pop("result_payload_sha256", None) != payload_sha256(unsigned):
        findings.append("result_seal_invalid")
    unsigned = dict(manifest)
    if unsigned.pop("manifest_payload_sha256", None) != payload_sha256(unsigned):
        findings.append("manifest_seal_invalid")
    for index, row in enumerate(result.get("targets", []), 1):
        path = ROOT / RESPONSE_ROOT / f"response_{index:02d}.bin"
        if not path.is_file() or sha256(path) != row.get("response_sha256"):
            findings.append(f"response_{index:02d}_hash_drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24926_snapshot_transport_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": sha256(ROOT / RESULT),
        "findings": findings,
        "audit_valid": not findings,
        "protected_watchers": protected_watcher_snapshot(),
        "network_model_or_evaluator_called_by_audit": False,
        "authorization": {
            "fresh_snapshot_bound_quality_gate_design": not findings
            and result.get("passed") is True,
            "quality_forward_launch": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("protocol", "preaudit", "start", "execute", "postaudit")
    )
    args = parser.parse_args()
    _clean_pushed()
    if args.command == "protocol":
        value, path = build_protocol(), PROTOCOL
        value["protected_watchers"] = protected_watcher_snapshot()
        unsigned = dict(value)
        unsigned.pop("protocol_payload_sha256", None)
        value["protocol_payload_sha256"] = payload_sha256(unsigned)
    elif args.command == "preaudit":
        value, path = build_preaudit(), PREAUDIT
    elif args.command == "start":
        value, path = build_start(), EXECUTION_START
    elif args.command == "execute":
        value, path = execute(), RESULT
    else:
        value, path = postaudit(), POSTAUDIT
    if value.get("findings"):
        raise RuntimeError(f"V2.49.26 {args.command} failed: {value['findings']}")
    _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "status": value.get("status"),
                "passed": value.get("passed"),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
