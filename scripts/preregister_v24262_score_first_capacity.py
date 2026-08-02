#!/usr/bin/env python3
"""Freeze a full-pipeline, label-blind concurrency ladder for V2.42.61."""

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

from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    ALL_KINDS,
    NORMALIZED_KINDS,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)
from scripts.project_v24262_serial_capacity_baseline import (  # noqa: E402
    OUTPUT as BASELINE_PROJECTION,
    validate_projection,
)


ROLE = "v24262_score_first_capacity_preregistration"
PROTOCOL_ID = "v24262_score_first_full_pipeline_capacity_v1"
OUTPUT = Path("results/v24262_score_first_capacity_preregistration_v1_20260802.json")
PREAUDIT = Path("results/v24262_score_first_capacity_preactivation_audit_v1_20260802.json")
ACTIVATION = Path("results/v24262_score_first_capacity_activation_v1_20260802.json")
EXECUTION_START = Path("results/v24262_score_first_capacity_execution_start_v1_20260802.json")
RESULT = Path("results/v24262_score_first_capacity_result_v1_20260802.json")
OUTPUT_ROOT = Path("outputs/v24262_score_first_capacity_v1_20260802")
PROGRESS = OUTPUT_ROOT / "safe_capacity_progress.json"
STATE = Path("outputs/v24262_score_first_capacity_watcher_state_v1_20260802.json")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24262_score_first_capacity_v1"
LEASE_PURPOSE = "label_blind_full_pipeline_capacity_for_score_first"
RUNNER_MARKER = "scripts/run_v24262_score_first_capacity.py"
WATCHER_MARKER = "scripts/watch_v24262_score_first_capacity.py"

PARENT_PROTOCOL = Path("results/v24261_direct_executor_smoke_preregistration_v1_20260802.json")
PARENT_RESULT = Path("results/v24261_direct_executor_smoke_result_v1_20260802.json")
PARENT_AUDIT = Path("results/v24261_direct_executor_smoke_postresult_audit_v1_20260802.json")

LEVELS = (1, 2, 4, 8, 12)
WAVES_PER_LEVEL = 3
TASK_COUNT = 12
MODEL_GENERATED = frozenset({"primary", "repaired", *NORMALIZED_KINDS})

FORWARD_FILES = (
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/anthropic_search.py",
    "scripts/run_v24257_score_first_smoke.py",
    "scripts/run_v24259_score_first_smoke.py",
    "scripts/run_v24259_score_first_task.py",
    "scripts/v24260_successor/run_v24259_score_first_task.py",
    "scripts/run_v24261_score_first_smoke.py",
    "scripts/deepwide_api_lease.py",
)
CONTROL_FILES = (
    "scripts/project_v24262_serial_capacity_baseline.py",
    "scripts/preregister_v24262_score_first_capacity.py",
    "scripts/activate_v24262_score_first_capacity.py",
    "scripts/audit_v24262_score_first_capacity.py",
    "scripts/run_v24262_score_first_capacity.py",
    "scripts/watch_v24262_score_first_capacity.py",
    "tests/test_v24262_score_first_capacity.py",
)
FUTURE_PATHS = (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, OUTPUT_ROOT, STATE)
SECRET = re.compile(r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.62 path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.62 expected an ordinary file: {relative}")
    return path


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def task_positions(concurrency: int, wave: int, task_count: int = TASK_COUNT) -> list[int]:
    if concurrency not in LEVELS or not 1 <= wave <= WAVES_PER_LEVEL:
        raise ValueError("V2.42.62 schedule coordinates are invalid")
    start = (wave - 1) * concurrency
    return [((start + slot) % task_count) + 1 for slot in range(concurrency)]


def schedule_manifest() -> list[dict[str, Any]]:
    return [
        {
            "concurrency": concurrency,
            "waves": [
                {"wave": wave, "task_positions": task_positions(concurrency, wave)}
                for wave in range(1, WAVES_PER_LEVEL + 1)
            ],
        }
        for concurrency in LEVELS
    ]


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = read_object(_ordinary(root, PARENT_PROTOCOL))
    result = read_object(_ordinary(root, PARENT_RESULT))
    audit = read_object(_ordinary(root, PARENT_AUDIT))
    if (
        protocol.get("role") != "v24261_direct_executor_smoke_preregistration"
        or protocol.get("protocol_id") != "v24261_direct_executor_smoke16_v1"
        or not _sealed(protocol, "decision_contract_sha256")
        or result.get("role") != "v24261_direct_executor_smoke_result"
        or result.get("engineering_gate") != "go"
        or result.get("terminal") != 16
        or result.get("model_generated_tables") != 15
        or result.get("fallback_tables") != 1
        or result.get("official_evaluator_called") is not False
        or not _sealed(result, "result_payload_sha256")
        or audit.get("role") != "v24261_direct_executor_smoke_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("claims", {}).get("benchmark_quality_improvement_observed") is not False
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.62 parent evidence drifted")
    return protocol, result


def _selected_ids(root: Path, parent: dict[str, Any]) -> list[str]:
    contract = parent["task_contract"]
    ids_path = _ordinary(root, contract["id_source"]["path"])
    if sha256(ids_path) != contract["id_source"]["sha256"]:
        raise RuntimeError("V2.42.62 ID source drifted")
    values = [line for line in ids_path.read_text(encoding="utf-8").splitlines() if line]
    selected = values[:TASK_COUNT]
    if len(selected) != TASK_COUNT or len(set(selected)) != TASK_COUNT or any(OPAQUE.fullmatch(value) is None for value in selected):
        raise RuntimeError("V2.42.62 selected task prefix is invalid")
    return selected


def _baseline_rows(root: Path, selected: list[str]) -> list[dict[str, Any]]:
    projection = validate_projection(root, BASELINE_PROJECTION)
    if projection["selected_opaque_ids_sha256"] != payload_sha256(selected):
        raise RuntimeError("V2.42.62 serial projection task identity drifted")
    rows = [dict(row) for row in projection["rows"]]
    if any(str(row["completion_kind"]) not in ALL_KINDS for row in rows):
        raise RuntimeError("V2.42.62 serial projection completion kind drifted")
    return rows


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (not relative.startswith("tests/") and OPAQUE.search(source)):
            raise RuntimeError(f"V2.42.62 unsafe source: {relative}")
        values[relative] = sha256(path)
    return values


def build_protocol(root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    root = root.resolve()
    parent, _ = _parent(root)
    selected = _selected_ids(root, parent)
    baseline = _baseline_rows(root, selected)
    present = [str(path) for path in FUTURE_PATHS if (root / path).exists() or (root / path).is_symlink()]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.62 future surface is not pristine: {present}")
    controls = _manifest(root, CONTROL_FILES)
    forward = _manifest(root, FORWARD_FILES)
    schedule = schedule_manifest()
    task_contract = dict(parent["task_contract"])
    task_contract.update(
        {
            "selection_rule": "same_frozen_first_12_devval_visible_tasks_reused_for_capacity_only",
            "selected_count": TASK_COUNT,
            "selected_opaque_ids_sha256": payload_sha256(selected),
            "selected_opaque_ids_persisted_or_emitted": False,
            "already_consumed_engineering_tasks_not_independent_quality_evaluation": True,
            "category_question_type_split_mapping_gold_evaluator_score_used_for_selection": False,
        }
    )
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
            "serial_baseline_projection": {"path": str(BASELINE_PROJECTION), "sha256": sha256(root / BASELINE_PROJECTION)},
            "engineering_gate": "go",
            "quality_or_sota_claim": False,
        },
        "task_contract": task_contract,
        "baseline_contract": {
            "source": "v24261_same_task_serial_smoke",
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
            "same_model_prompt_search_provider_and_per_task_limits_as_parent": True,
            "gates": {
                "minimum_selected_concurrency_for_capacity_go": 4,
                "maximum_infrastructure_fallbacks_per_level": 0,
                "maximum_stage_failures_per_level": 0,
                "minimum_model_generated_fraction": 0.85,
                "maximum_additional_model_fallbacks_vs_matched_serial": 1,
                "maximum_additional_model_attempts_vs_matched_serial": 2,
                "maximum_additional_logical_search_failures_vs_matched_serial": 0,
                "maximum_additional_fetch_failures_vs_matched_serial": 12,
                "maximum_median_matched_wall_ratio": 2.5,
                "maximum_p95_matched_wall_ratio": 3.5,
                "maximum_absolute_p95_wall_seconds": 600.0,
                "minimum_median_effective_speedup_fraction": 0.5,
                "maximum_mean_matched_token_ratio": 1.5,
                "maximum_mean_matched_fetch_ratio": 1.5,
            },
        },
        "limits": dict(parent["limits"]),
        "provider_contract": dict(parent["provider_contract"]),
        "lease_contract": {
            "path": str(LEASE),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "one_owner_across_all_levels": True,
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "task_runner_marker": "scripts/v24260_successor/run_v24259_score_first_task.py",
            "watcher_marker": WATCHER_MARKER,
            "preactivation_audit_path": str(PREAUDIT),
            "activation_path": str(ACTIVATION),
            "execution_start_path": str(EXECUTION_START),
            "output_root": str(OUTPUT_ROOT),
            "progress_path": str(PROGRESS),
            "result_path": str(RESULT),
            "watcher_state_path": str(STATE),
            "maximum_executor_concurrency": max(LEVELS),
            "parent_deadline_grace_seconds": int(parent["execution"]["parent_deadline_grace_seconds"]),
            "resume_rerun_skip_or_selective_retry_allowed": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_selection": False,
            "capacity_result_contains_prediction_question_query_url_page_or_answer": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_capacity_ladder_after_activation_and_inactive_lease": True,
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
    if value.get("role") != ROLE or value.get("protocol_id") != PROTOCOL_ID or value.get("label_blind") is not True or not _sealed(value, "decision_contract_sha256"):
        raise RuntimeError("V2.42.62 protocol identity drifted")
    if value.get("source_policy", {}).get("runtime_boundary") != ["opaque_id", "question"] or value.get("source_policy", {}).get("mapping_gold_category_question_type_split_evaluator_score_read") is not False:
        raise RuntimeError("V2.42.62 label-blind boundary drifted")
    _parent(root)
    for parent in value["parents"].values():
        if isinstance(parent, dict) and "path" in parent and sha256(_ordinary(root, parent["path"])) != parent["sha256"]:
            raise RuntimeError("V2.42.62 parent bytes drifted")
    for surface in ("forward_surface", "control_surface"):
        manifest = value[surface]["manifest"]
        if payload_sha256(manifest) != value[surface]["manifest_sha256"]:
            raise RuntimeError(f"V2.42.62 {surface} seal drifted")
        for relative, digest in manifest.items():
            if sha256(_ordinary(root, relative)) != digest:
                raise RuntimeError(f"V2.42.62 frozen source drifted: {relative}")
    selected = _selected_ids(root, value)
    if payload_sha256(selected) != value["task_contract"]["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.62 selected task identity drifted")
    baseline = _baseline_rows(root, selected)
    if baseline != value["baseline_contract"]["rows"] or payload_sha256(baseline) != value["baseline_contract"]["rows_sha256"]:
        raise RuntimeError("V2.42.62 serial baseline drifted")
    schedule = schedule_manifest()
    if schedule != value["capacity_contract"]["schedule"] or payload_sha256(schedule) != value["capacity_contract"]["schedule_sha256"]:
        raise RuntimeError("V2.42.62 schedule drifted")
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
