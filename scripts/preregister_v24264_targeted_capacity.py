#!/usr/bin/env python3
"""Freeze the targeted 4/8/12 V2.42.64 model-limited capacity test."""

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

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from scripts import preregister_v24262_score_first_capacity as base62  # noqa: E402
from scripts import preregister_v24263_model_limited_capacity as parent  # noqa: E402
from scripts import run_v24263_model_limited_capacity as parent_runner  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24264_targeted_capacity_preregistration"
PROTOCOL_ID = "v24264_targeted_four_eight_twelve_capacity_v1"
OUTPUT = Path("results/v24264_targeted_capacity_preregistration_v1_20260802.json")
PREAUDIT = Path("results/v24264_targeted_capacity_preactivation_audit_v1_20260802.json")
ACTIVATION = Path("results/v24264_targeted_capacity_activation_v1_20260802.json")
EXECUTION_START = Path("results/v24264_targeted_capacity_execution_start_v1_20260802.json")
RESULT = Path("results/v24264_targeted_capacity_result_v1_20260802.json")
POSTAUDIT = Path(
    "results/v24264_targeted_capacity_postresult_audit_v1_20260802.json"
)
OUTPUT_ROOT = Path("outputs/v24264_targeted_capacity_v1_20260802")
PROGRESS = OUTPUT_ROOT / "safe_capacity_progress.json"
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
STATE = Path("outputs/v24264_targeted_capacity_watcher_state_v1_20260802.json")
LEASE = parent.LEASE
LEASE_OWNER = "v24264_targeted_capacity_v1"
LEASE_PURPOSE = "targeted_four_eight_twelve_with_global_gpt_cap_two"
RUNNER_MARKER = "scripts/run_v24264_targeted_capacity.py"
WATCHER_MARKER = "scripts/watch_v24264_targeted_capacity.py"
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
TASK_COUNT = parent.TASK_COUNT
LEVELS = (4, 8, 12)
WAVES_PER_LEVEL = 3

PARENT_PROTOCOL = parent.OUTPUT
PARENT_RESULT = parent.RESULT
PARENT_AUDIT = Path("results/v24263_model_limited_capacity_postresult_audit_v1_20260802.json")

FORWARD_FILES = tuple(
    dict.fromkeys(
        [
            *parent.FORWARD_FILES,
            "scripts/run_v24264_targeted_capacity.py",
        ]
    )
)
CONTROL_FILES = (
    "scripts/run_v24264_targeted_capacity.py",
    "scripts/preregister_v24264_targeted_capacity.py",
    "scripts/activate_v24264_targeted_capacity.py",
    "scripts/audit_v24264_targeted_capacity.py",
    "scripts/watch_v24264_targeted_capacity.py",
    "tests/test_v24264_targeted_capacity.py",
)
FUTURE_PATHS = (
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    RESULT,
    POSTAUDIT,
    OUTPUT_ROOT,
    STATE,
)
SECRET = re.compile(r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.64 path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.64 expected ordinary file: {relative}")
    return path


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def targeted_schedule() -> list[dict[str, Any]]:
    value = [
        dict(level)
        for level in base62.schedule_manifest()
        if int(level["concurrency"]) in LEVELS
    ]
    _validate_schedule(value)
    return value


def _validate_schedule(value: list[dict[str, Any]]) -> None:
    if [row.get("concurrency") for row in value] != list(LEVELS):
        raise RuntimeError("V2.42.64 target level schedule drifted")
    for level in value:
        concurrency = int(level["concurrency"])
        waves = level.get("waves")
        if (
            not isinstance(waves, list)
            or [wave.get("wave") for wave in waves]
            != list(range(1, WAVES_PER_LEVEL + 1))
            or any(
                not isinstance(wave.get("task_positions"), list)
                or len(wave["task_positions"]) != concurrency
                or any(
                    isinstance(position, bool)
                    or not isinstance(position, int)
                    or not 1 <= position <= TASK_COUNT
                    for position in wave["task_positions"]
                )
                for wave in waves
            )
        ):
            raise RuntimeError("V2.42.64 target wave schedule drifted")
        positions = [
            int(position)
            for wave in waves
            for position in wave["task_positions"]
        ]
        expected_repetitions = concurrency * WAVES_PER_LEVEL // TASK_COUNT
        if (
            concurrency * WAVES_PER_LEVEL % TASK_COUNT
            or any(
                positions.count(position) != expected_repetitions
                for position in range(1, TASK_COUNT + 1)
            )
        ):
            raise RuntimeError("V2.42.64 task exposure schedule drifted")


def targeted_gates(previous: dict[str, Any]) -> dict[str, Any]:
    gates = dict(previous["capacity_contract"]["gates"])
    gates.update(
        {
            "minimum_selected_concurrency_for_capacity_go": 4,
            "minimum_model_generated_fraction": 0.90,
            "maximum_infrastructure_fallbacks_per_level": 0,
            "maximum_stage_failures_per_level": 0,
            "maximum_additional_model_fallbacks_vs_matched_serial": 1,
            "maximum_additional_model_attempts_vs_matched_serial": 2,
            "maximum_additional_logical_search_failures_vs_matched_serial": 0,
            "maximum_additional_fetch_failures_vs_matched_serial": 24,
            "maximum_median_matched_wall_ratio": 1000.0,
            "maximum_p95_matched_wall_ratio": 1000.0,
            "maximum_absolute_p95_wall_seconds": 600.0,
            "minimum_median_effective_speedup_fraction": 0.0,
            "minimum_effective_speedup": 1.5,
            "maximum_mean_matched_token_ratio": 1.5,
            "maximum_mean_matched_fetch_ratio": 1.5,
            "maximum_model_request_errors_per_level": 0,
            "maximum_model_slot_receipt_invalid_count": 0,
            "matched_task_wall_ratios_are_diagnostic_only": True,
        }
    )
    return gates


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = parent.validate_protocol(root, PARENT_PROTOCOL)
    result = read_object(_ordinary(root, PARENT_RESULT))
    parent_runner.validate_result(protocol, result)
    audit = read_object(_ordinary(root, PARENT_AUDIT))
    levels = result.get("levels") or []
    level1 = next((row for row in levels if row.get("concurrency") == 1), None)
    level2 = next((row for row in levels if row.get("concurrency") == 2), None)
    if (
        result.get("capacity_gate") != "no_go"
        or result.get("total_executions") != 9
        or level1 is None
        or level1.get("passed") is not True
        or level2 is None
        or level2.get("model_generated") != 6
        or level2.get("stage_failures") != 0
        or level2.get("infrastructure_fallbacks") != 0
        or level2.get("model_slot_receipt_invalid_count") != 0
        or level2.get("model_slot_acquisitions") != 12
        or level2.get("findings") != ["p95_matched_wall_ratio_above_gate"]
        or audit.get("role") != "v24263_model_limited_capacity_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("mechanism_evidence", {}).get("model_request_errors") != 0
        or audit.get("mechanism_evidence", {}).get("valid_model_slot_receipts") != 9
        or audit.get("mechanism_evidence", {}).get("concurrency_four_failure_hypothesis_tested") is not False
        or audit.get("diagnosis", {}).get("blocking_stage") != "page_projection"
        or audit.get("result", {}).get("target_concurrency_four_executed") is not False
        or audit.get("claims", {}).get("limiter_mechanism_valid") is not True
        or audit.get("claims", {}).get("concurrency_four_improved") is not False
        or audit.get("claims", {}).get("benchmark_quality_improvement_observed") is not False
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.64 parent evidence drifted")
    return protocol, result, audit


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (not relative.startswith("tests/") and OPAQUE.search(source)):
            raise RuntimeError(f"V2.42.64 unsafe source: {relative}")
        values[relative] = sha256(path)
    return values


def build_protocol(
    root: Path = ROOT,
    *,
    now: int | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    previous, _, _ = _parent(root)
    present = [
        str(path)
        for path in FUTURE_PATHS
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.64 future surface is not pristine: {present}")
    controls = _manifest(root, CONTROL_FILES)
    forward = _manifest(root, FORWARD_FILES)
    schedule = targeted_schedule()
    selected = base62._selected_ids(root, previous)
    baseline = base62._baseline_rows(root, selected)
    gates = targeted_gates(previous)
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
            "limiter_mechanism_valid": True,
            "concurrency_four_hypothesis_tested": False,
            "quality_or_sota_claim": False,
        },
        "single_change": {
            "mechanism": "start_at_target_concurrency_four_and_make_matched_task_wall_ratio_diagnostic_only",
            "target_levels": list(LEVELS),
            "waves_per_level": WAVES_PER_LEVEL,
            "absolute_task_deadline_unchanged": True,
            "provider_completion_stage_failure_receipt_token_fetch_and_throughput_gates_retained": True,
            "model_limiter_prompt_provider_retry_search_fetch_task_selection_and_limits_unchanged": True,
        },
        "task_contract": dict(previous["task_contract"]),
        "baseline_contract": {
            "source": previous["baseline_contract"]["source"],
            "rows": baseline,
            "rows_sha256": payload_sha256(baseline),
            "prediction_question_query_url_page_or_answer_persisted": False,
            "parent_prediction_files_opened_by_protocol_audit_or_capacity_runner": False,
        },
        "capacity_contract": {
            "levels": list(LEVELS),
            "waves_per_level": WAVES_PER_LEVEL,
            "maximum_executions": sum(LEVELS) * WAVES_PER_LEVEL,
            "schedule": schedule,
            "schedule_sha256": payload_sha256(schedule),
            "stop_after_first_failed_level": True,
            "same_four_eight_twelve_waves_as_v24262_and_v24263": True,
            "gates": gates,
        },
        "limits": dict(previous["limits"]),
        "provider_contract": dict(previous["provider_contract"]),
        "model_slot_contract": {
            **dict(previous["model_slot_contract"]),
            "directory": str(MODEL_SLOT_DIRECTORY),
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
            "postresult_audit_path": str(POSTAUDIT),
            "watcher_state_path": str(STATE),
            "maximum_executor_concurrency": max(LEVELS),
            "parent_deadline_grace_seconds": int(previous["execution"]["parent_deadline_grace_seconds"]),
            "resume_rerun_skip_or_selective_retry_allowed": False,
        },
        "source_policy": dict(previous["source_policy"]),
        "authorization": {
            "single_targeted_capacity_ladder_after_activation_and_inactive_lease": True,
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
        or value.get("capacity_contract", {}).get("levels") != list(LEVELS)
        or value.get("source_policy", {}).get("runtime_boundary") != ["opaque_id", "question"]
        or value.get("source_policy", {}).get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
    ):
        raise RuntimeError("V2.42.64 protocol identity drifted")
    previous, _, _ = _parent(root)
    for parent_ref in value["parents"].values():
        if isinstance(parent_ref, dict) and "path" in parent_ref and sha256(_ordinary(root, parent_ref["path"])) != parent_ref["sha256"]:
            raise RuntimeError("V2.42.64 parent bytes drifted")
    for surface in ("forward_surface", "control_surface"):
        manifest = value[surface]["manifest"]
        if payload_sha256(manifest) != value[surface]["manifest_sha256"]:
            raise RuntimeError(f"V2.42.64 {surface} seal drifted")
        for relative, digest in manifest.items():
            if sha256(_ordinary(root, relative)) != digest:
                raise RuntimeError(f"V2.42.64 frozen source drifted: {relative}")
    selected = base62._selected_ids(root, value)
    if payload_sha256(selected) != value["task_contract"]["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.64 task identity drifted")
    baseline = base62._baseline_rows(root, selected)
    if baseline != value["baseline_contract"]["rows"] or payload_sha256(baseline) != value["baseline_contract"]["rows_sha256"]:
        raise RuntimeError("V2.42.64 baseline drifted")
    schedule = targeted_schedule()
    if schedule != value["capacity_contract"]["schedule"] or payload_sha256(schedule) != value["capacity_contract"]["schedule_sha256"]:
        raise RuntimeError("V2.42.64 schedule drifted")
    capacity = value["capacity_contract"]
    if (
        capacity.get("waves_per_level") != WAVES_PER_LEVEL
        or capacity.get("maximum_executions") != sum(LEVELS) * WAVES_PER_LEVEL
        or capacity.get("stop_after_first_failed_level") is not True
        or capacity.get("gates") != targeted_gates(previous)
    ):
        raise RuntimeError("V2.42.64 capacity gate drifted")
    slots = value.get("model_slot_contract") or {}
    if (
        slots.get("pool_id") != POOL_ID
        or slots.get("slot_cap") != MODEL_SLOT_CAP
        or slots.get("directory") != str(MODEL_SLOT_DIRECTORY)
        or slots.get("receipt_required_per_child") is not True
        or slots.get("receipt_acquisitions_must_equal_model_requests") is not True
    ):
        raise RuntimeError("V2.42.64 model slot contract drifted")
    execution = value.get("execution") or {}
    if (
        execution.get("runner_marker") != RUNNER_MARKER
        or execution.get("watcher_marker") != WATCHER_MARKER
        or execution.get("result_path") != str(RESULT)
        or execution.get("postresult_audit_path") != str(POSTAUDIT)
        or execution.get("resume_rerun_skip_or_selective_retry_allowed") is not False
    ):
        raise RuntimeError("V2.42.64 execution contract drifted")
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
