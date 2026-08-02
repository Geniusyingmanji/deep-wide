#!/usr/bin/env python3
"""Freeze the V2.42.63 model-limited full-pipeline capacity successor."""

from __future__ import annotations

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

from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    DEFAULT_CAP,
    POOL_ID,
)
from scripts import preregister_v24262_score_first_capacity as base  # noqa: E402
from scripts import run_v24262_score_first_capacity as base_runner  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24263_model_limited_capacity_preregistration"
PROTOCOL_ID = "v24263_model_limited_full_pipeline_capacity_v1"
OUTPUT = Path("results/v24263_model_limited_capacity_preregistration_v1_20260802.json")
PREAUDIT = Path("results/v24263_model_limited_capacity_preactivation_audit_v1_20260802.json")
ACTIVATION = Path("results/v24263_model_limited_capacity_activation_v1_20260802.json")
EXECUTION_START = Path("results/v24263_model_limited_capacity_execution_start_v1_20260802.json")
RESULT = Path("results/v24263_model_limited_capacity_result_v1_20260802.json")
OUTPUT_ROOT = Path("outputs/v24263_model_limited_capacity_v1_20260802")
PROGRESS = OUTPUT_ROOT / "safe_capacity_progress.json"
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
STATE = Path("outputs/v24263_model_limited_capacity_watcher_state_v1_20260802.json")
LEASE = base.LEASE
LEASE_OWNER = "v24263_model_limited_capacity_v1"
LEASE_PURPOSE = "label_blind_capacity_with_global_gpt_concurrency_two"
RUNNER_MARKER = "scripts/run_v24263_model_limited_capacity.py"
WATCHER_MARKER = "scripts/watch_v24263_model_limited_capacity.py"
MODEL_SLOT_CAP = DEFAULT_CAP
TASK_COUNT = base.TASK_COUNT

PARENT_PROTOCOL = base.OUTPUT
PARENT_RESULT = base.RESULT
PARENT_AUDIT = Path("results/v24262_score_first_capacity_postresult_audit_v1_20260802.json")

FORWARD_FILES = tuple(
    dict.fromkeys(
        [
            *base.FORWARD_FILES,
            "src/deepwide_agent/v24263_global_model_limiter.py",
            "scripts/run_v24263_score_first_task.py",
            "scripts/run_v24263_model_limited_capacity.py",
        ]
    )
)
CONTROL_FILES = (
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "scripts/run_v24263_score_first_task.py",
    "scripts/run_v24263_model_limited_capacity.py",
    "scripts/preregister_v24263_model_limited_capacity.py",
    "scripts/activate_v24263_model_limited_capacity.py",
    "scripts/audit_v24263_model_limited_capacity.py",
    "scripts/watch_v24263_model_limited_capacity.py",
    "tests/test_v24263_global_model_limiter.py",
    "tests/test_v24263_model_limited_capacity.py",
)
FUTURE_PATHS = (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, OUTPUT_ROOT, STATE)
SECRET = re.compile(r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.63 path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.63 expected ordinary file: {relative}")
    return path


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = base.validate_protocol(root, PARENT_PROTOCOL)
    result = read_object(_ordinary(root, PARENT_RESULT))
    base_runner.validate_result(protocol, result)
    audit = read_object(_ordinary(root, PARENT_AUDIT))
    levels = result.get("levels") or []
    level4 = next(
        (level for level in levels if level.get("concurrency") == 4), None
    )
    failure_types = (
        [
            failure
            for wave in (level4 or {}).get("waves", [])
            for row in wave.get("tasks", [])
            for failure in row.get("failure_types", [])
        ]
        if level4
        else []
    )
    if (
        result.get("capacity_gate") != "no_go"
        or result.get("selected_executor_concurrency") != 2
        or level4 is None
        or level4.get("passed") is not False
        or level4.get("stage_failures") != 6
        or level4.get("infrastructure_fallbacks") != 0
        or level4.get("additional_logical_search_failures_vs_matched_serial") != 0
        or sorted(failure_types) != ["ModelRequestError"] * 6
        or audit.get("role") != "v24262_score_first_capacity_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("failure_diagnosis", {}).get("synthesis_model_request_errors") != 4
        or audit.get("failure_diagnosis", {}).get("plan_model_request_errors") != 2
        or audit.get("failure_diagnosis", {}).get("search_failures_at_concurrency_4") != 0
        or audit.get("claims", {}).get("capacity_two_stable") is not True
        or audit.get("claims", {}).get("capacity_four_stable") is not False
        or audit.get("claims", {}).get("benchmark_quality_improvement_observed") is not False
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.63 parent failure diagnosis drifted")
    return protocol, result, audit


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (not relative.startswith("tests/") and OPAQUE.search(source)):
            raise RuntimeError(f"V2.42.63 unsafe source: {relative}")
        values[relative] = sha256(path)
    return values


def build_protocol(
    root: Path = ROOT,
    *,
    now: int | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    parent, _, _ = _parent(root)
    present = [
        str(path)
        for path in FUTURE_PATHS
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.63 future surface is not pristine: {present}")
    controls = _manifest(root, CONTROL_FILES)
    forward = _manifest(root, FORWARD_FILES)
    schedule = base.schedule_manifest()
    selected = base._selected_ids(root, parent)
    baseline = base._baseline_rows(root, selected)
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
            "capacity_two_stable": True,
            "capacity_four_stable": False,
            "concurrency_four_model_request_errors": 6,
            "concurrency_four_search_failures": 0,
            "quality_or_sota_claim": False,
        },
        "single_change": {
            "mechanism": "cross_process_advisory_file_lock_model_request_slots",
            "model_slot_pool_id": POOL_ID,
            "global_model_request_concurrency_cap": MODEL_SLOT_CAP,
            "lock_scope": "one_logical_model_complete_call_including_internal_retries",
            "search_and_fetch_outside_model_lock": True,
            "slot_wait_counts_against_original_task_wall_deadline": True,
            "model_prompt_provider_retry_search_fetch_task_selection_and_limits_unchanged": True,
        },
        "task_contract": dict(parent["task_contract"]),
        "baseline_contract": {
            "source": parent["baseline_contract"]["source"],
            "rows": baseline,
            "rows_sha256": payload_sha256(baseline),
            "prediction_question_query_url_page_or_answer_persisted": False,
            "parent_prediction_files_opened_by_protocol_audit_or_capacity_runner": False,
        },
        "capacity_contract": {
            **dict(parent["capacity_contract"]),
            "schedule": schedule,
            "schedule_sha256": payload_sha256(schedule),
            "same_schedule_as_v24262": True,
            "stop_after_first_failed_level": True,
        },
        "limits": dict(parent["limits"]),
        "provider_contract": dict(parent["provider_contract"]),
        "model_slot_contract": {
            "pool_id": POOL_ID,
            "slot_cap": MODEL_SLOT_CAP,
            "directory": str(MODEL_SLOT_DIRECTORY),
            "receipt_name": "model_slot_receipt.json",
            "receipt_required_per_child": True,
            "receipt_acquisitions_must_equal_model_requests": True,
            "kernel_releases_lock_on_process_exit": True,
            "receipt_contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        },
        "lease_contract": {
            "path": str(LEASE),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "one_owner_across_all_levels": True,
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "task_runner_marker": "scripts/run_v24263_score_first_task.py",
            "watcher_marker": WATCHER_MARKER,
            "preactivation_audit_path": str(PREAUDIT),
            "activation_path": str(ACTIVATION),
            "execution_start_path": str(EXECUTION_START),
            "output_root": str(OUTPUT_ROOT),
            "progress_path": str(PROGRESS),
            "result_path": str(RESULT),
            "watcher_state_path": str(STATE),
            "maximum_executor_concurrency": max(base.LEVELS),
            "parent_deadline_grace_seconds": int(parent["execution"]["parent_deadline_grace_seconds"]),
            "resume_rerun_skip_or_selective_retry_allowed": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_selection": False,
            "capacity_result_contains_prediction_question_query_url_page_answer_or_opaque_id": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_model_limited_capacity_ladder_after_activation_and_inactive_lease": True,
            "official_evaluator_call": False,
            "paired_dev64_launch": False,
            "full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "forward_surface": {"manifest": forward, "manifest_sha256": payload_sha256(forward)},
        "control_surface": {"manifest": controls, "manifest_sha256": payload_sha256(controls)},
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path = ROOT, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, path))
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or not _sealed(value, "decision_contract_sha256")
        or value.get("single_change", {}).get("global_model_request_concurrency_cap") != MODEL_SLOT_CAP
        or value.get("source_policy", {}).get("runtime_boundary") != ["opaque_id", "question"]
        or value.get("source_policy", {}).get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
    ):
        raise RuntimeError("V2.42.63 protocol identity drifted")
    _parent(root)
    for parent in value["parents"].values():
        if isinstance(parent, dict) and "path" in parent and sha256(_ordinary(root, parent["path"])) != parent["sha256"]:
            raise RuntimeError("V2.42.63 parent bytes drifted")
    for surface in ("forward_surface", "control_surface"):
        manifest = value[surface]["manifest"]
        if payload_sha256(manifest) != value[surface]["manifest_sha256"]:
            raise RuntimeError(f"V2.42.63 {surface} seal drifted")
        for relative, digest in manifest.items():
            if sha256(_ordinary(root, relative)) != digest:
                raise RuntimeError(f"V2.42.63 frozen source drifted: {relative}")
    selected = base._selected_ids(root, value)
    if payload_sha256(selected) != value["task_contract"]["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.63 task identity drifted")
    baseline = base._baseline_rows(root, selected)
    if baseline != value["baseline_contract"]["rows"] or payload_sha256(baseline) != value["baseline_contract"]["rows_sha256"]:
        raise RuntimeError("V2.42.63 baseline drifted")
    schedule = base.schedule_manifest()
    if schedule != value["capacity_contract"]["schedule"] or payload_sha256(schedule) != value["capacity_contract"]["schedule_sha256"]:
        raise RuntimeError("V2.42.63 schedule drifted")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    publish_new(ROOT / OUTPUT, build_protocol())
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}))
