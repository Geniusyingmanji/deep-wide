#!/usr/bin/env python3
"""Seal the zero-effect V2.42.57 start failure and its one-shot successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24257_score_first_smoke import (  # noqa: E402
    ACTIVATION as PARENT_ACTIVATION,
    EXECUTION_START,
    LEASE,
    LEASE_OWNER,
    LEASE_PURPOSE,
    OUTPUT as PARENT_PROTOCOL,
    OUTPUT_ROOT,
    RESULT,
    RUNNER_MARKER as COMPATIBLE_RUNNER_SUFFIX,
    WATCHER_MARKER,
    validate_protocol as validate_parent_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24258_score_first_smoke_successor_preregistration"
PROTOCOL_ID = "v24258_zero_effect_start_successor_v1"
FAILURE_ROLE = "v24257_score_first_smoke_zero_effect_start_failure"
FAILURE = Path("results/v24257_score_first_smoke_start_failure_v1_20260802.json")
OUTPUT = Path(
    "results/v24258_score_first_smoke_successor_preregistration_v1_20260802.json"
)
ACTIVATION = Path(
    "results/v24258_score_first_smoke_successor_activation_v1_20260802.json"
)
RUNNER_LOG = Path("outputs/v24257_score_first_smoke_runner_v1_20260802.log")
WRAPPER = Path(
    "scripts/v24258_successor/scripts/run_v24257_score_first_smoke.py"
)
CONTROL_FILES = (
    Path("scripts/preregister_v24258_score_first_smoke_successor.py"),
    Path("scripts/activate_v24258_score_first_smoke_successor.py"),
    WRAPPER,
    Path("tests/test_v24258_score_first_smoke_successor.py"),
)
SECRET_LITERAL = re.compile(
    rb"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.58 path is noncanonical")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.42.58 expected ordinary file: {relative}")
    return path


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.42.58 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.58 expected a JSON object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _publish(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    if target.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _start_ticks(proc_root: Path, pid: int) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.42.58 process stat is truncated")
    return int(suffix[19])


def _matches(rows: list[dict[str, Any]], marker: str) -> list[int]:
    values: list[int] = []
    for row in rows:
        script = actual_python_script([str(item) for item in row.get("argv") or []])
        if script and (script == marker or script.endswith("/" + marker)):
            values.append(int(row["pid"]))
    return sorted(values)


def _parent_activation(root: Path, parent: dict[str, Any]) -> dict[str, Any]:
    value = _read(_ordinary(root, PARENT_ACTIVATION))
    if (
        value.get("role") != "v24257_score_first_smoke_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / PARENT_PROTOCOL)
        or value.get("control_manifest_sha256")
        != parent["control_surface"]["manifest_sha256"]
        or value.get("benchmark_question_prediction_mapping_gold_score_read")
        is not False
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.58 parent activation drifted")
    return value


def build_failure_receipt(
    root: Path = ROOT,
    *,
    now: int | None = None,
    proc_root: Path = Path("/proc"),
    processes: list[dict[str, Any]] | None = None,
    observed_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    parent = validate_parent_protocol(root, PARENT_PROTOCOL)
    activation = _parent_activation(root, parent)
    rows = process_snapshot(proc_root) if processes is None else processes
    lease = (
        lease_observation(root, proc_root)
        if observed_lease is None
        else dict(observed_lease)
    )
    log = _ordinary(root, RUNNER_LOG).read_bytes()
    if SECRET_LITERAL.search(log):
        raise RuntimeError("V2.42.58 failure log contains a credential literal")
    expected_fragments = (
        b"NameError: name 'RUNNER_MARKER' is not defined",
        b'"marker": RUNNER_MARKER',
    )
    residue = [
        str(path)
        for path in (EXECUTION_START, OUTPUT_ROOT, RESULT)
        if (root / path).exists() or (root / path).is_symlink()
    ]
    runners = _matches(rows, COMPATIBLE_RUNNER_SUFFIX)
    if (
        any(fragment not in log for fragment in expected_fragments)
        or residue
        or runners
        or lease.get("active") is not False
        or lease.get("ordinary") is not True
    ):
        raise RuntimeError("V2.42.58 zero-effect failure boundary is not clean")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": FAILURE_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_protocol": {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
        },
        "parent_activation": {
            "path": str(PARENT_ACTIVATION),
            "sha256": sha256(root / PARENT_ACTIVATION),
            "activation_payload_sha256": activation["activation_payload_sha256"],
        },
        "failure": {
            "class": "NameError",
            "undefined_symbol": "RUNNER_MARKER",
            "stage": "before_execution_start_publication",
            "log": {"path": str(RUNNER_LOG), "sha256": hashlib.sha256(log).hexdigest()},
            "raw_log_contents_emitted": False,
        },
        "execution_start_present": False,
        "output_root_present": False,
        "result_present": False,
        "shared_api_lease_active": False,
        "matching_runner_processes": 0,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "prediction_or_forward_artifact_created": False,
        "existing_benchmark_or_watcher_signaled_restarted_modified_or_terminated": False,
        "retry_under_parent_protocol_authorized": False,
    }
    value["failure_payload_sha256"] = payload_sha256(value)
    return value


def validate_failure(root: Path, path: Path = FAILURE) -> dict[str, Any]:
    value = _read(_ordinary(root.resolve(), path))
    if (
        value.get("role") != FAILURE_ROLE
        or value.get("execution_start_present") is not False
        or value.get("shared_api_lease_active") is not False
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("retry_under_parent_protocol_authorized") is not False
        or not _sealed(value, "failure_payload_sha256")
    ):
        raise RuntimeError("V2.42.58 failure receipt drifted")
    return value


def build_protocol(
    root: Path = ROOT,
    *,
    now: int | None = None,
    proc_root: Path = Path("/proc"),
    processes: list[dict[str, Any]] | None = None,
    observed_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    parent = validate_parent_protocol(root, PARENT_PROTOCOL)
    _parent_activation(root, parent)
    failure = validate_failure(root)
    rows = process_snapshot(proc_root) if processes is None else processes
    lease = (
        lease_observation(root, proc_root)
        if observed_lease is None
        else dict(observed_lease)
    )
    watcher_pids = _matches(rows, WATCHER_MARKER)
    if (
        len(watcher_pids) != 1
        or lease.get("active") is not False
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (EXECUTION_START, OUTPUT_ROOT, RESULT, ACTIVATION)
        )
    ):
        raise RuntimeError("V2.42.58 successor boundary is not pristine")
    watcher_pid = watcher_pids[0]
    manifest = {
        str(path): sha256(_ordinary(root, path)) for path in CONTROL_FILES
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "v24257_protocol": {
                "path": str(PARENT_PROTOCOL),
                "sha256": sha256(root / PARENT_PROTOCOL),
                "decision_contract_sha256": parent["decision_contract_sha256"],
            },
            "v24257_activation": {
                "path": str(PARENT_ACTIVATION),
                "sha256": sha256(root / PARENT_ACTIVATION),
            },
            "zero_effect_failure": {
                "path": str(FAILURE),
                "sha256": sha256(root / FAILURE),
                "failure_payload_sha256": failure["failure_payload_sha256"],
            },
        },
        "correction": {
            "single_change": "define_frozen_runner_marker_before_delegating_to_byte_frozen_v24257_runner",
            "wrapper": str(WRAPPER),
            "delegated_parent_runner": str(COMPATIBLE_RUNNER_SUFFIX),
            "model_prompt_search_budget_task_selection_and_gate_unchanged": True,
            "parent_protocol_retry_or_resume": False,
            "append_only_successor_launch": True,
        },
        "execution": {
            "activation_path": str(ACTIVATION),
            "wrapper_path": str(WRAPPER),
            "compatible_process_script_suffix": str(COMPATIBLE_RUNNER_SUFFIX),
            "parent_protocol_argument": str(PARENT_PROTOCOL),
            "execution_start_path": str(EXECUTION_START),
            "output_root": str(OUTPUT_ROOT),
            "result_path": str(RESULT),
            "shared_lease_path": str(LEASE),
            "shared_lease_owner": LEASE_OWNER,
            "shared_lease_purpose": LEASE_PURPOSE,
            "existing_watcher": {
                "marker": WATCHER_MARKER,
                "pid": watcher_pid,
                "start_ticks": _start_ticks(proc_root, watcher_pid),
            },
            "new_or_restarted_watcher_allowed": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "same_forward_evaluator_feedback": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "one_corrected_smoke16_successor_launch": True,
            "parent_retry_resume_or_selective_rerun": False,
            "process_signal_or_existing_watcher_restart": False,
            "official_evaluator_dev64_full220_or_leaderboard": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
        },
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(_ordinary(root, path))
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or value.get("authorization", {}).get(
            "official_evaluator_dev64_full220_or_leaderboard"
        )
        is not False
        or not _sealed(value, "decision_contract_sha256")
    ):
        raise RuntimeError("V2.42.58 successor protocol drifted")
    manifest = value.get("control_surface", {}).get("manifest") or {}
    if (
        not isinstance(manifest, dict)
        or value["control_surface"].get("file_count") != len(manifest)
        or value["control_surface"].get("manifest_sha256")
        != payload_sha256(manifest)
    ):
        raise RuntimeError("V2.42.58 control manifest drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, Path(relative))) != digest:
            raise RuntimeError(f"V2.42.58 control source drifted: {relative}")
    validate_failure(root)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    if (ROOT / FAILURE).exists():
        validate_failure(ROOT)
    else:
        _publish(ROOT / FAILURE, build_failure_receipt())
    _publish(ROOT / OUTPUT, build_protocol())
    print(json.dumps({"failure": str(FAILURE), "protocol": str(OUTPUT)}))


if __name__ == "__main__":
    main()
