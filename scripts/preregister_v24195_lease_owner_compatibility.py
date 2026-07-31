#!/usr/bin/env python3
"""Freeze an append-only lease-owner compatibility layer for V2.41.94."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROLE = "v24195_lease_owner_compatibility_preregistration"
PROTOCOL_ID = "v24195_v24194_lease_owner_compatibility_v1"
OUTPUT = Path(
    "results/v24195_lease_owner_compatibility_preregistration_v1_20260731.json"
)
STATE = Path(
    "outputs/v24195_lease_owner_compatibility_watcher_state_v1_20260731.json"
)
WAIT_ACTIVATION = Path(
    "results/v24195_lease_owner_compatibility_wait_activation_audit_v1_20260731.json"
)
V24196_PROTOCOL = Path(
    "results/v24196_capacity_executor_preregistration_v1_20260731.json"
)
V24196_ACTIVATION = Path(
    "results/v24196_capacity_executor_activation_v1_20260731.json"
)
WATCHER_MARKER = "scripts/watch_v24195_lease_owner_compatibility.py"
EXECUTOR_MARKER = "scripts/watch_v24196_capacity_executor.py"
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
REGISTERED_OWNER = "v24194_neutral_gpt56_capacity_ladder_v1"
REGISTERED_PURPOSE = "neutral_capacity_for_next_fresh_all220_freeze"
EXPECTED_PARENT_FINDING = "shared_api_lease_identity"

FROZEN_PARENTS = {
    "results/v24187_phase_liveness_preregistration_v1_20260730.json": (
        "873f42369f6f5ac7d1b619510257f8cc7c932140b734dd14d23c4a5c6e45d34c"
    ),
    "scripts/audit_v24187_phase_liveness.py": (
        "ff776dafe18d2455cf74dbe953d8590b7e36b43bcda658043791f3e27d4b3fd4"
    ),
    "results/v24194_capacity_ladder_preregistration_v1_20260731.json": (
        "5da63416e800a73afa49ae479351f83e30892947e987e5d390011b02face4681"
    ),
    "scripts/preregister_v24194_capacity_ladder.py": (
        "aecf6b72b292890661b282b2f6f1c0fc6507bef77da59500bcb3e09487470583"
    ),
    "scripts/deepwide_api_lease.py": (
        "8d9cffa78617b458172307d3558c76e9370f045f531c2f5aaaceb866f5a78c7d"
    ),
}
CONTROL_FILES = (
    "scripts/preregister_v24195_lease_owner_compatibility.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/watch_v24195_lease_owner_compatibility.py",
    "scripts/audit_v24195_lease_owner_compatibility_wait_activation.py",
    "tests/test_preregister_v24195_lease_owner_compatibility.py",
    "tests/test_audit_v24195_lease_owner_compatibility.py",
    "tests/test_watch_v24195_lease_owner_compatibility.py",
    "tests/test_audit_v24195_lease_owner_compatibility_wait_activation.py",
)
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
DECISION_FIELDS = (
    "protocol_id",
    "parents",
    "compatibility_contract",
    "activation_contract",
    "execution",
    "source_policy",
    "authorization",
    "control_surface",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.41.95 expected an ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.95 expected a JSON object")
    return value


def ordinary(root: Path, relative: str | Path, digest: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.95 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or root not in (path, *path.parents)
    ):
        raise RuntimeError(f"V2.41.95 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.41.95 frozen parent drifted: {relative}")
    return path


def publish_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _parents(root: Path) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for relative, digest in FROZEN_PARENTS.items():
        records[relative] = {"sha256": sha256(ordinary(root, relative, digest))}
    v87 = read_object(root / next(iter(FROZEN_PARENTS)))
    v94 = read_object(
        root / "results/v24194_capacity_ladder_preregistration_v1_20260731.json"
    )
    if (
        v87.get("protocol_id") != "v24187_phase_aware_campaign_liveness_v1"
        or v94.get("protocol_id") != "v24194_neutral_gpt56_capacity_ladder_v1"
        or v94.get("execution", {}).get("shared_lease_owner") != REGISTERED_OWNER
        or v94.get("execution", {}).get("shared_lease_purpose")
        != REGISTERED_PURPOSE
        or v94.get("authorization", {}).get("future_all220_launch") is not False
    ):
        raise RuntimeError("V2.41.95 frozen parent semantics drifted")
    return records


def _safe_boundary(root: Path) -> dict[str, Any]:
    phase = read_object(
        ordinary(root, "outputs/v24187_phase_liveness_watcher_state_v1_20260730.json")
    )
    capacity = read_object(
        ordinary(root, "outputs/v24194_capacity_ladder_watcher_state_v1_20260731.json")
    )
    current = phase.get("current_phase") or {}
    if (
        phase.get("role") != "v24187_phase_liveness_audit"
        or phase.get("overall_status")
        not in {"healthy", "degraded_forward_healthy_manual_review_only"}
        or phase.get("critical_findings") != []
        or current.get("valid") is not True
        or capacity.get("role") != "v24194_capacity_ladder_watcher_state"
        or capacity.get("status") != "waiting_for_r1_release"
        or capacity.get("shared_api_lease_acquired") is not False
        or capacity.get("neutral_capacity_model_api_called") is not False
        or capacity.get("full220_launch_allowed") is not False
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (
                OUTPUT,
                STATE,
                WAIT_ACTIVATION,
                V24196_PROTOCOL,
                V24196_ACTIVATION,
            )
        )
    ):
        raise RuntimeError("V2.41.95 safe wait-only boundary is invalid")
    return {
        "phase": current.get("phase"),
        "phase_valid": True,
        "phase_critical_findings": [],
        "v24194_status": capacity["status"],
        "v24194_shared_api_lease_acquired": False,
        "v24194_neutral_capacity_model_api_called": False,
        "successor_activation_absent": True,
        "successor_protocol_absent": True,
    }


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.95 may only freeze the canonical workspace")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.95 unattested Python bootstrap path appeared")
    parents = _parents(root)
    boundary = _safe_boundary(root) if require_pristine else {
        "phase": "r1_full220",
        "phase_valid": True,
        "phase_critical_findings": [],
        "v24194_status": "waiting_for_r1_release",
        "v24194_shared_api_lease_acquired": False,
        "v24194_neutral_capacity_model_api_called": False,
        "successor_activation_absent": True,
        "successor_protocol_absent": True,
    }
    manifest = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "parents": parents,
        "compatibility_contract": {
            "registered_owner": REGISTERED_OWNER,
            "registered_purpose": REGISTERED_PURPOSE,
            "frozen_parent_expected_finding": EXPECTED_PARENT_FINDING,
            "suppress_only_expected_finding_for_exact_registered_live_identity": True,
            "preserve_all_unrelated_parent_critical_findings": True,
            "legacy_registered_owners_remain_parent_authoritative": True,
            "unknown_owner_or_purpose_fails_closed": True,
            "lease_lock_is_authoritative_and_json_is_observational": True,
        },
        "activation_contract": {
            "successor_protocol_path": str(V24196_PROTOCOL),
            "successor_activation_path": str(V24196_ACTIVATION),
            "successor_executor_marker": EXECUTOR_MARKER,
            "successor_protocol_must_bind_this_protocol_sha256": True,
            "successor_protocol_must_bind_v24194_protocol_sha256": True,
            "activation_payload_live_recomputed": True,
            "activation_pid_and_proc_start_ticks_live_revalidated": True,
            "activation_owner_purpose_and_executor_exact_match": True,
        },
        "execution": {
            "python_flags": ["-I", "-B"],
            "poll_seconds": 10,
            "proc_root": "/proc",
            "watcher_marker": WATCHER_MARKER,
            "state_path": str(STATE),
            "wait_activation_path": str(WAIT_ACTIVATION),
            "lease_path": str(LEASE),
            "safe_wait_boundary": boundary,
        },
        "source_policy": {
            "parent_label_blind_liveness_report_recomputed_live": True,
            "shared_lease_owner_purpose_pid_and_lock_state_only": True,
            "proc_executable_identity_and_start_ticks_only": True,
            "runtime_task_question_answer_evidence_prediction_or_url_opened": False,
            "mapping_gold_category_question_type_evaluator_or_score_read": False,
            "credential_value_or_keyring_read": False,
            "network_model_search_fetch_or_evaluator_api_called": False,
        },
        "authorization": {
            "read_only_compatibility_watcher": True,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "shared_api_lease_acquire": False,
            "execution_activation_publish": False,
            "network_model_search_fetch_or_evaluator_api_call": False,
            "benchmark_forward_or_full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha(manifest),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
        },
    }
    value["decision_contract_sha256"] = payload_sha(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    expected = (root / OUTPUT).resolve(strict=False)
    if raw.resolve(strict=False) != expected or raw.is_symlink() or not raw.is_file():
        raise RuntimeError("V2.41.95 protocol path is noncanonical")
    value = read_object(raw)
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or control.get("file_count") != len(CONTROL_FILES)
        or control.get("manifest_sha256") != payload_sha(manifest)
        or set(control.get("must_remain_absent") or []) != set(MUST_REMAIN_ABSENT)
        or value.get("decision_contract_sha256")
        != payload_sha({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.41.95 protocol contract is invalid")
    _parents(root)
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.41.95 control surface drifted")
    return {"path": raw, "sha256": sha256(raw), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.41.95 output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
