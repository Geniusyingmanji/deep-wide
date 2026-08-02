#!/usr/bin/env python3
"""Freeze V2.42.60: V2.42.59 plus isolated child import bootstrap only."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24257_score_first_smoke import (  # noqa: E402
    ID_SOURCE,
    MANIFEST,
    _ordinary,
    _read_object,
    _selected_ids,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    OUTPUT as PARENT_PROTOCOL,
    _matching,
    _sealed,
    validate_protocol as validate_parent_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24260_import_bootstrap_smoke_preregistration"
PROTOCOL_ID = "v24260_import_bootstrap_smoke16_v1"
OUTPUT = Path("results/v24260_import_bootstrap_smoke_preregistration_v1_20260802.json")
ACTIVATION = Path("results/v24260_import_bootstrap_smoke_activation_v1_20260802.json")
EXECUTION_START = Path("results/v24260_import_bootstrap_smoke_execution_start_v1_20260802.json")
OUTPUT_ROOT = Path("outputs/v24260_import_bootstrap_smoke16_v1_20260802")
RESULT = Path("results/v24260_import_bootstrap_smoke_result_v1_20260802.json")
STATE = Path("outputs/v24260_import_bootstrap_smoke_watcher_state_v1_20260802.json")
PARENT_RESULT = Path("results/v24259_deterministic_normalizer_smoke_result_v1_20260802.json")
PARENT_AUDIT = Path("results/v24259_deterministic_normalizer_smoke_postresult_audit_v1_20260802.json")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24260_import_bootstrap_smoke16_v1"
LEASE_PURPOSE = "v24259_normalizer_with_isolated_child_import_bootstrap"
RUNNER_MARKER = "scripts/run_v24260_score_first_smoke.py"
WATCHER_MARKER = "scripts/watch_v24260_import_bootstrap_smoke.py"
CHILD = Path("scripts/v24260_successor/run_v24259_score_first_task.py")
CONTROL_FILES = (
    CHILD,
    Path("scripts/run_v24260_score_first_smoke.py"),
    Path("scripts/preregister_v24260_import_bootstrap_smoke.py"),
    Path("scripts/activate_v24260_import_bootstrap_smoke.py"),
    Path("scripts/audit_v24260_import_bootstrap_smoke.py"),
    Path("scripts/watch_v24260_import_bootstrap_smoke.py"),
    Path("tests/test_v24260_import_bootstrap_smoke.py"),
)
FUTURE_PATHS = (ACTIVATION, EXECUTION_START, OUTPUT_ROOT, RESULT, STATE)
SECRET_LITERAL = re.compile(r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE_LITERAL = re.compile(r"task_[0-9a-f]{24}")


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = validate_parent_protocol(root, PARENT_PROTOCOL)
    result = _read_object(_ordinary(root, PARENT_RESULT))
    audit = _read_object(_ordinary(root, PARENT_AUDIT))
    if (
        result.get("role") != "v24259_deterministic_normalizer_smoke_result"
        or result.get("selected") != 16
        or result.get("terminal") != 16
        or result.get("completion_kinds") != {"worker_failure_fallback": 16}
        or result.get("mean_system_tokens") != 0
        or result.get("mean_fetch_calls") != 0
        or result.get("engineering_gate") != "no_go"
        or result.get("official_evaluator_called") is not False
        or not _sealed(result, "result_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("claims", {}).get("benchmark_quality_improvement_observed") is not False
    ):
        raise RuntimeError("V2.42.60 parent zero-call failure evidence drifted")
    return protocol, result


def build_protocol(
    root: Path = ROOT,
    *,
    now: int | None = None,
    proc_root: Path = Path("/proc"),
    processes: list[dict[str, Any]] | None = None,
    observed_lease: dict[str, Any] | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    parent_protocol, parent_result = _parent(root)
    rows = process_snapshot(proc_root) if processes is None else processes
    lease = lease_observation(root, proc_root) if observed_lease is None else dict(observed_lease)
    present = [str(path) for path in FUTURE_PATHS if (root / path).exists() or (root / path).is_symlink()]
    if require_pristine and present:
        raise RuntimeError("V2.42.60 future execution surface is not pristine")
    if lease.get("active") is not False or lease.get("ordinary") is not True or _matching(rows, RUNNER_MARKER) or _matching(rows, WATCHER_MARKER):
        raise RuntimeError("V2.42.60 process or lease boundary is not clean")
    selected = _selected_ids(root)
    if payload_sha256(selected) != parent_protocol["task_contract"]["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.60 task identity drifted")
    failed_probe = subprocess.run(
        [str(root / ".venv-eval/bin/python"), "-I", "-B", str(root / "scripts/run_v24259_score_first_task.py"), "--help"],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    success_probe = subprocess.run(
        [str(root / ".venv-eval/bin/python"), "-I", "-B", str(root / CHILD), "--help"],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
    if (
        failed_probe.returncode == 0
        or b"ModuleNotFoundError: No module named 'scripts'" not in failed_probe.stderr
        or success_probe.returncode != 0
        or success_probe.stderr
    ):
        raise RuntimeError("V2.42.60 isolated import probe did not reproduce and repair exactly")
    manifest: dict[str, str] = {}
    for relative in CONTROL_FILES:
        source = _ordinary(root, relative).read_text(encoding="utf-8")
        if SECRET_LITERAL.search(source):
            raise RuntimeError(f"V2.42.60 control contains credential: {relative}")
        if not str(relative).startswith("tests/") and OPAQUE_LITERAL.search(source):
            raise RuntimeError(f"V2.42.60 control contains opaque ID: {relative}")
        manifest[str(relative)] = sha256(root / relative)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "protocol": {"path": str(PARENT_PROTOCOL), "sha256": sha256(root / PARENT_PROTOCOL)},
            "result": {"path": str(PARENT_RESULT), "sha256": sha256(root / PARENT_RESULT)},
            "postresult_audit": {"path": str(PARENT_AUDIT), "sha256": sha256(root / PARENT_AUDIT)},
            "zero_call_failure": {
                "completion_kinds": parent_result["completion_kinds"],
                "total_system_tokens": parent_result["total_system_tokens"],
                "total_fetch_calls": parent_result["total_fetch_calls"],
            },
        },
        "single_change": {
            "mechanism": "insert_repository_root_before_importing_frozen_v24259_child_runner",
            "wrapper_path": str(CHILD),
            "parent_child_path": "scripts/run_v24259_score_first_task.py",
            "failed_parent_help_probe": "ModuleNotFoundError:scripts",
            "successor_help_probe_exit_zero": True,
            "runtime_normalizer_model_prompt_search_provider_budget_selection_and_gate_unchanged": True,
        },
        "task_contract": {
            **parent_protocol["task_contract"],
            "manifest": {"path": str(MANIFEST), "sha256": sha256(_ordinary(root, MANIFEST)), "row_schema": ["opaque_id", "question"]},
            "id_source": {"path": str(ID_SOURCE), "sha256": sha256(_ordinary(root, ID_SOURCE))},
            "selection_rule": "same_frozen_first_16_devval_ids_full_fresh_cold_start",
            "selected_opaque_ids_sha256": payload_sha256(selected),
            "selective_parent_failure_rerun": False,
        },
        "limits": dict(parent_protocol["limits"]),
        "provider_contract": dict(parent_protocol["provider_contract"]),
        "gate_contract": dict(parent_protocol["gate_contract"]),
        "lease_contract": {
            "path": str(LEASE),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_posix_flock_required": True,
            "single_owner_across_all_16_tasks": True,
            "legacy_expected_finding": "v24195:unknown_lease_owner",
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "task_runner_marker": str(CHILD),
            "watcher_marker": WATCHER_MARKER,
            "activation_path": str(ACTIVATION),
            "execution_start_path": str(EXECUTION_START),
            "output_root": str(OUTPUT_ROOT),
            "result_path": str(RESULT),
            "watcher_state_path": str(STATE),
            "executor_concurrency": 1,
            "parent_deadline_grace_seconds": 5,
            "forward_resume_or_selective_rerun_allowed": False,
            "result_overwrite_allowed": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_tuning": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_fresh_smoke16_after_activation_and_lease": True,
            "process_signal_restart_resume_skip_or_selective_retry": False,
            "official_evaluator_call": False,
            "paired_dev64_or_full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "safe_freeze_boundary": {
            "future_paths_present": present,
            "shared_api_lease_active": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "control_surface": {"file_count": len(manifest), "manifest": manifest, "manifest_sha256": payload_sha256(manifest)},
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    value = _read_object(_ordinary(root, path))
    if value.get("role") != ROLE or value.get("protocol_id") != PROTOCOL_ID or value.get("label_blind") is not True or not _sealed(value, "decision_contract_sha256"):
        raise RuntimeError("V2.42.60 protocol drifted")
    manifest = value.get("control_surface", {}).get("manifest") or {}
    if value["control_surface"].get("manifest_sha256") != payload_sha256(manifest):
        raise RuntimeError("V2.42.60 manifest drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, Path(relative))) != digest:
            raise RuntimeError(f"V2.42.60 source drifted: {relative}")
    _parent(root)
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError("V2.42.60 output exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    publish(ROOT / OUTPUT, build_protocol())
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}))
