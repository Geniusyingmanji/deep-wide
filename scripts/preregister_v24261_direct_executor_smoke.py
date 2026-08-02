#!/usr/bin/env python3
"""Freeze V2.42.61 direct executor after V2.42.60 pre-Popen recursion."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24257_score_first_smoke import ID_SOURCE, MANIFEST, _ordinary, _read_object, _selected_ids  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching, _sealed  # noqa: E402
from scripts.preregister_v24260_import_bootstrap_smoke import OUTPUT as PARENT_PROTOCOL, validate_protocol as validate_parent_protocol  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24261_direct_executor_smoke_preregistration"
PROTOCOL_ID = "v24261_direct_executor_smoke16_v1"
OUTPUT = Path("results/v24261_direct_executor_smoke_preregistration_v1_20260802.json")
ACTIVATION = Path("results/v24261_direct_executor_smoke_activation_v1_20260802.json")
EXECUTION_START = Path("results/v24261_direct_executor_smoke_execution_start_v1_20260802.json")
OUTPUT_ROOT = Path("outputs/v24261_direct_executor_smoke16_v1_20260802")
RESULT = Path("results/v24261_direct_executor_smoke_result_v1_20260802.json")
STATE = Path("outputs/v24261_direct_executor_smoke_watcher_state_v1_20260802.json")
PARENT_START = Path("results/v24260_import_bootstrap_smoke_execution_start_v1_20260802.json")
PARENT_LOG = Path("outputs/v24260_import_bootstrap_smoke_runner_v1_20260802.log")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24261_direct_executor_smoke16_v1"
LEASE_PURPOSE = "direct_non_monkeypatch_v24259_normalizer_smoke16"
RUNNER_MARKER = "scripts/run_v24261_score_first_smoke.py"
WATCHER_MARKER = "scripts/watch_v24261_direct_executor_smoke.py"
CONTROL_FILES = (
    Path("scripts/run_v24261_score_first_smoke.py"),
    Path("scripts/preregister_v24261_direct_executor_smoke.py"),
    Path("scripts/activate_v24261_direct_executor_smoke.py"),
    Path("scripts/audit_v24261_direct_executor_smoke.py"),
    Path("scripts/watch_v24261_direct_executor_smoke.py"),
    Path("tests/test_v24261_direct_executor_smoke.py"),
)
FUTURE_PATHS = (ACTIVATION, EXECUTION_START, OUTPUT_ROOT, RESULT, STATE)
SECRET = re.compile(r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _parent(root: Path):
    protocol = validate_parent_protocol(root, PARENT_PROTOCOL)
    start = _read_object(_ordinary(root, PARENT_START))
    log = _ordinary(root, PARENT_LOG).read_text(encoding="utf-8")
    parent_root = root / protocol["execution"]["output_root"]
    task_count = len(list((parent_root / "tasks").glob("*/visible_task.json"))) if (parent_root / "tasks").is_dir() else 0
    progress_count = len(list((parent_root / "tasks").glob("*/safe_progress.json"))) if (parent_root / "tasks").is_dir() else 0
    result_count = len(list((parent_root / "tasks").glob("*/result.json"))) if (parent_root / "tasks").is_dir() else 0
    if (
        start.get("role") != "v24260_import_bootstrap_smoke_execution_start"
        or start.get("api_called_before_execution_start") is not False
        or not _sealed(start, "execution_start_payload_sha256")
        or "RecursionError: maximum recursion depth exceeded" not in log
        or log.count("command = parent._task_command(") < 3
        or "scripts/run_v24259_score_first_smoke.py" not in log
        or task_count != 1
        or progress_count != 0
        or result_count != 0
        or (root / protocol["execution"]["result_path"]).exists()
    ):
        raise RuntimeError("V2.42.61 parent pre-Popen recursion evidence drifted")
    return protocol, {"visible_task_files": task_count, "progress_files": progress_count, "result_files": result_count}


def build_protocol(root: Path = ROOT, *, now=None, require_pristine=True):
    root = root.resolve()
    parent, counts = _parent(root)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    present = [str(p) for p in FUTURE_PATHS if (root / p).exists() or (root / p).is_symlink()]
    if require_pristine and present:
        raise RuntimeError("V2.42.61 future surface is not pristine")
    if lease.get("active") is not False or lease.get("ordinary") is not True or _matching(rows, RUNNER_MARKER) or _matching(rows, WATCHER_MARKER):
        raise RuntimeError("V2.42.61 process or lease boundary is not clean")
    selected = _selected_ids(root)
    if payload_sha256(selected) != parent["task_contract"]["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.61 task identity drifted")
    manifest = {}
    for relative in CONTROL_FILES:
        source = _ordinary(root, relative).read_text(encoding="utf-8")
        if SECRET.search(source) or (not str(relative).startswith("tests/") and OPAQUE.search(source)):
            raise RuntimeError(f"V2.42.61 unsafe control source: {relative}")
        manifest[str(relative)] = sha256(root / relative)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "protocol": {"path": str(PARENT_PROTOCOL), "sha256": sha256(root / PARENT_PROTOCOL)},
            "execution_start": {"path": str(PARENT_START), "sha256": sha256(root / PARENT_START)},
            "runner_log": {"path": str(PARENT_LOG), "sha256": sha256(root / PARENT_LOG), "contents_emitted": False},
            "pre_popen_residue_counts": counts,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "single_change": {
            "mechanism": "direct_task_command_and_popen_without_runtime_monkeypatch",
            "parent_executor": "scripts/run_v24260_score_first_smoke.py",
            "runtime_monkeypatch_used": False,
            "run_one_task_failure_injection_popen_count": 1,
            "child_runtime_normalizer_model_prompt_search_provider_budget_selection_and_gate_unchanged": True,
        },
        "task_contract": {
            **parent["task_contract"],
            "manifest": {"path": str(MANIFEST), "sha256": sha256(_ordinary(root, MANIFEST)), "row_schema": ["opaque_id", "question"]},
            "id_source": {"path": str(ID_SOURCE), "sha256": sha256(_ordinary(root, ID_SOURCE))},
            "selection_rule": "same_frozen_first_16_devval_ids_full_fresh_cold_start",
            "selected_opaque_ids_sha256": payload_sha256(selected),
            "selective_parent_failure_rerun": False,
        },
        "limits": dict(parent["limits"]),
        "provider_contract": dict(parent["provider_contract"]),
        "gate_contract": dict(parent["gate_contract"]),
        "lease_contract": {"path": str(LEASE), "owner": LEASE_OWNER, "purpose": LEASE_PURPOSE, "single_owner_across_all_16_tasks": True},
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "task_runner_marker": "scripts/v24260_successor/run_v24259_score_first_task.py",
            "watcher_marker": WATCHER_MARKER,
            "activation_path": str(ACTIVATION),
            "execution_start_path": str(EXECUTION_START),
            "output_root": str(OUTPUT_ROOT),
            "result_path": str(RESULT),
            "watcher_state_path": str(STATE),
            "executor_concurrency": 1,
            "parent_deadline_grace_seconds": 5,
            "forward_resume_or_selective_rerun_allowed": False,
        },
        "source_policy": {"runtime_boundary": ["opaque_id", "question"], "mapping_gold_category_question_type_evaluator_score_read": False, "same_run_evaluator_feedback_used_for_forward_or_tuning": False, "credential_value_persisted_hashed_or_emitted": False},
        "authorization": {"single_fresh_smoke16_after_activation_and_lease": True, "process_signal_restart_resume_skip_or_selective_retry": False, "official_evaluator_call": False, "paired_dev64_or_full220_launch": False, "leaderboard_submission_or_sota_claim": False},
        "control_surface": {"file_count": len(manifest), "manifest": manifest, "manifest_sha256": payload_sha256(manifest)},
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path, path: Path = OUTPUT):
    root = root.resolve()
    value = _read_object(_ordinary(root, path))
    if value.get("role") != ROLE or value.get("protocol_id") != PROTOCOL_ID or value.get("label_blind") is not True or not _sealed(value, "decision_contract_sha256"):
        raise RuntimeError("V2.42.61 protocol drifted")
    manifest = value.get("control_surface", {}).get("manifest") or {}
    if value["control_surface"].get("manifest_sha256") != payload_sha256(manifest):
        raise RuntimeError("V2.42.61 manifest drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, Path(relative))) != digest:
            raise RuntimeError(f"V2.42.61 source drifted: {relative}")
    _parent(root)
    return value


def publish(path: Path, value):
    if path.exists() or path.is_symlink():
        raise FileExistsError("V2.42.61 output exists")
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
