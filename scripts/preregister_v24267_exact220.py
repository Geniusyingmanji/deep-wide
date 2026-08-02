#!/usr/bin/env python3
"""Freeze a fresh exact-220 successor after the invalid V2.42.66 start."""

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
from scripts import preregister_v24264_targeted_capacity as capacity_parent  # noqa: E402
from scripts import preregister_v24265_paired_dev64 as paired_parent  # noqa: E402
from scripts.finalize_v24265_paired_dev64 import validate_final_result  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    load_manifest,
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24267_exact220_preregistration"
PROTOCOL_ID = "v24267_v24259_total_fallback_single_cold_exact220_v1"
OUTPUT = Path("results/v24267_exact220_preregistration_v1_20260802.json")
PREAUDIT = Path("results/v24267_exact220_preactivation_audit_v1_20260802.json")
ACTIVATION = Path("results/v24267_exact220_activation_v1_20260802.json")
EXECUTION_START = Path("results/v24267_exact220_execution_start_v1_20260802.json")
FORWARD_RESULT = Path("results/v24267_exact220_forward_result_v1_20260802.json")
FINAL_RESULT = Path("results/v24267_exact220_result_v1_20260802.json")
POSTAUDIT = Path("results/v24267_exact220_postresult_audit_v1_20260802.json")
OUTPUT_ROOT = Path("outputs/v24267_exact220_v1_20260802")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
EVALUATOR_ROOT = OUTPUT_ROOT / "evaluator"

LEASE = capacity_parent.LEASE
LEASE_OWNER_FORWARD = "v24267_exact220_forward_v1"
LEASE_OWNER_EVALUATOR = "v24267_exact220_evaluator_v1"
LEASE_PURPOSE_FORWARD = "label_blind_v24259_total_fallback_single_cold_exact220_forward"
LEASE_PURPOSE_EVALUATOR = "post_freeze_exact220_official_evaluator"
RUNNER_MARKER = "scripts/run_v24267_exact220.py"
FINALIZER_MARKER = "scripts/finalize_v24267_exact220.py"
CHILD_MARKER = "scripts/run_v24267_score_first_task.py"
MODEL_SLOT_CAP = 2
EXECUTOR_CONCURRENCY = 4
SELECTED_COUNT = 220

PARENT_PROTOCOL = paired_parent.OUTPUT
PARENT_RESULT = paired_parent.FINAL_RESULT
PARENT_AUDIT = paired_parent.POSTAUDIT
INVALID_PREDECESSOR_AUDIT = Path(
    "results/DO_NOT_USE_invalid_v24266_exact220_fallback_header_20260802/invalid_run_audit.json"
)
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCES = (
    ("test_s01", Path("configs/full220_v2403_r1_test_s01.ids"), 52),
    ("test_s02", Path("configs/full220_v2403_r1_test_s02.ids"), 52),
    ("test_s03", Path("configs/full220_v2403_r1_test_s03.ids"), 52),
    ("devval", Path("configs/full220_v2403_r1_devval_s04.ids"), 64),
)

FORWARD_FILES = tuple(
    dict.fromkeys(
        [
            *capacity_parent.FORWARD_FILES,
            "src/deepwide_agent/v24267_total_fallback.py",
            "scripts/run_v24267_score_first_task.py",
            "scripts/run_v24267_exact220.py",
        ]
    )
)
CONTROL_FILES = (
    "scripts/preregister_v24267_exact220.py",
    "scripts/run_v24267_exact220.py",
    "scripts/finalize_v24267_exact220.py",
    "scripts/activate_v24267_exact220.py",
    "scripts/audit_v24267_exact220.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/run_official_eval_local.py",
    "scripts/audit_v24187_phase_liveness.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/preregister_v24259_deterministic_normalizer_smoke.py",
    "tests/test_v24267_total_fallback.py",
    "tests/test_v24267_exact220.py",
)
FUTURE_PATHS = (
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    FORWARD_RESULT,
    FINAL_RESULT,
    POSTAUDIT,
    OUTPUT_ROOT,
)
SECRET = re.compile(r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.67 path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.67 expected ordinary file: {relative}")
    return path


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = paired_parent.validate_protocol(root, PARENT_PROTOCOL)
    result = read_object(_ordinary(root, PARENT_RESULT))
    validate_final_result(protocol, result, root=root)
    audit = read_object(_ordinary(root, PARENT_AUDIT))
    if (
        result.get("status") != "go"
        or result.get("decision", {}).get("passed") is not True
        or result.get("authorization", {}).get("successor_exact220_design") is not True
        or result.get("authorization", {}).get("exact220_launch") is not False
        or result.get("claims", {}).get("sota") is not False
        or audit.get("role") != "v24265_paired_dev64_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("authorization", {}).get("successor_exact220_design") is not True
        or audit.get("authorization", {}).get("exact220_launch") is not False
        or audit.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward"
        )
        is not False
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.67 paired parent drifted")
    return protocol, result, audit


def _invalid_predecessor(root: Path) -> dict[str, Any]:
    value = read_object(_ordinary(root, INVALID_PREDECESSOR_AUDIT))
    quarantine = value.get("quarantine") or {}
    authorization = value.get("authorization") or {}
    if (
        value.get("role") != "v24266_exact220_invalid_run_audit"
        or value.get("audit_valid") is not True
        or value.get("exception_type") != "ValueError"
        or value.get("exception_message")
        != "score-first prediction is not canonical Markdown"
        or quarantine.get("partial_outputs_may_feed_successor") is not False
        or authorization.get("append_only_fresh_exact220_successor_design") is not True
        or authorization.get("resume_rerun_skip_or_selective_retry_v24266") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.67 invalid predecessor audit drifted")
    return value


def selected_shards(root: Path = ROOT) -> list[tuple[str, list[str]]]:
    values: list[tuple[str, list[str]]] = []
    combined: list[str] = []
    for tag, relative, expected in ID_SOURCES:
        path = _ordinary(root, relative)
        ids = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if (
            len(ids) != expected
            or len(set(ids)) != expected
            or any(OPAQUE.fullmatch(value) is None for value in ids)
        ):
            raise RuntimeError(f"V2.42.67 {tag} ID source drifted")
        values.append((tag, ids))
        combined.extend(ids)
    if len(combined) != SELECTED_COUNT or len(set(combined)) != SELECTED_COUNT:
        raise RuntimeError("V2.42.67 exact-220 partition is not disjoint and exhaustive")
    return values


def selected_ids(root: Path = ROOT) -> list[str]:
    return [value for _, ids in selected_shards(root) for value in ids]


def selected_tasks(root: Path, protocol: dict[str, Any]) -> list[dict[str, str]]:
    ids = selected_ids(root)
    contract = protocol["task_contract"]
    if payload_sha256(ids) != contract["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.67 exact-220 ID order drifted")
    manifest_path = _ordinary(root, SOURCE_MANIFEST)
    if sha256(manifest_path) != contract["manifest"]["sha256"]:
        raise RuntimeError("V2.42.67 visible manifest drifted")
    rows = load_manifest(manifest_path)
    if any(set(row) != {"opaque_id", "question"} for row in rows):
        raise RuntimeError("V2.42.67 visible manifest schema drifted")
    by_id = {row["opaque_id"]: row for row in rows}
    if len(by_id) != len(rows) or any(value not in by_id for value in ids):
        raise RuntimeError("V2.42.67 selected task is absent or duplicated")
    return [by_id[value] for value in ids]


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (not relative.startswith("tests/") and OPAQUE.search(source)):
            raise RuntimeError(f"V2.42.67 unsafe source: {relative}")
        output[relative] = sha256(path)
    return output


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    parent_protocol, parent_result, _ = _parent(root)
    _invalid_predecessor(root)
    shards = selected_shards(root)
    ids = [value for _, values in shards for value in values]
    manifest_path = _ordinary(root, SOURCE_MANIFEST)
    if sha256(manifest_path) != parent_protocol["task_contract"]["manifest"]["sha256"]:
        raise RuntimeError("V2.42.67 parent visible manifest drifted")
    present = [
        str(path)
        for path in FUTURE_PATHS
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.67 future surface is not pristine: {present}")
    forward = _manifest(root, FORWARD_FILES)
    controls = _manifest(root, CONTROL_FILES)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "paired_protocol": {"path": str(PARENT_PROTOCOL), "sha256": sha256(root / PARENT_PROTOCOL)},
            "paired_result": {"path": str(PARENT_RESULT), "sha256": sha256(root / PARENT_RESULT)},
            "paired_postresult_audit": {"path": str(PARENT_AUDIT), "sha256": sha256(root / PARENT_AUDIT)},
            "paired_status": parent_result["status"],
            "paired_quality_composite_delta": parent_result["decision"]["candidate_minus_control"]["quality_composite"],
            "invalid_v24266_audit": {
                "path": str(INVALID_PREDECESSOR_AUDIT),
                "sha256": sha256(root / INVALID_PREDECESSOR_AUDIT),
            },
            "invalid_v24266_partial_outputs_reused": False,
            "quality_or_sota_claim": False,
        },
        "candidate": {
            "policy_id": "v24259_deterministic_table_normalizer_v1",
            "child_entrypoint": "scripts/run_v24267_score_first_task.py",
            "single_change_from_paired_candidate": "exception-only canonical total fallback boundary",
            "normal_planning_search_fetch_synthesis_normalization_and_repair_unchanged": True,
            "fallback_columns_and_cells": ["Result", "Unknown"],
            "shared_prefix_paired_gate_passed": True,
        },
        "task_contract": {
            "manifest": {"path": str(SOURCE_MANIFEST), "sha256": sha256(manifest_path), "row_schema": ["opaque_id", "question"]},
            "id_sources": [
                {"tag": tag, "path": str(relative), "sha256": sha256(root / relative), "count": expected}
                for tag, relative, expected in ID_SOURCES
            ],
            "selection_rule": "exact frozen test_s01 then test_s02 then test_s03 then devval opaque-ID order",
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "partition_tags_sha256": payload_sha256([{"tag": tag, "ids": values} for tag, values in shards]),
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_instance_split_category_gold_evaluator_or_score_used_for_selection": False,
            "public_resource_previously_consumed_not_unseen_or_held_out": True,
        },
        "forward_contract": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "global_model_slot_cap": MODEL_SLOT_CAP,
            "exact_terminal_predictions_required": SELECTED_COUNT,
            "cold_new_output_root": True,
            "one_forward_per_visible_task": True,
            "resume_rerun_skip_or_selective_retry_allowed": False,
            "worker_failure_returns_schema_valid_fallback": True,
            "parent_child_and_validator_exception_paths_are_total": True,
            "invalid_predecessor_output_reuse_allowed": False,
            "mapping_query_answer_gold_or_evaluator_open_before_prediction_freeze": False,
        },
        "limits": dict(parent_protocol["limits"]),
        "provider_contract": dict(parent_protocol["provider_contract"]),
        "model_slot_contract": {
            "pool_id": POOL_ID,
            "slot_cap": MODEL_SLOT_CAP,
            "directory": str(MODEL_SLOT_DIRECTORY),
            "receipt_required_per_child": True,
            "receipt_acquisitions_must_equal_actual_model_requests": True,
        },
        "freeze_contract": {
            "runtime_predictions_path": str(RUNTIME_PREDICTIONS),
            "run_summary_path": str(RUN_SUMMARY),
            "prediction_freeze_path": str(PREDICTION_FREEZE),
            "exact_220_before_evaluator_side_open": True,
        },
        "evaluator_contract": dict(parent_protocol["evaluator_contract"]),
        "evaluation_contract": {
            "official_evaluator_on_all_220_predictions": True,
            "conservative_denominator": SELECTED_COUNT,
            "forward_or_evaluator_failure_as_zero": True,
            "evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "selective_error_retry_allowed": False,
        },
        "lease_contract": {
            "path": str(LEASE),
            "forward_owner": LEASE_OWNER_FORWARD,
            "forward_purpose": LEASE_PURPOSE_FORWARD,
            "evaluator_owner": LEASE_OWNER_EVALUATOR,
            "evaluator_purpose": LEASE_PURPOSE_EVALUATOR,
            "forward_and_evaluator_may_not_overlap": True,
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "finalizer_marker": FINALIZER_MARKER,
            "preactivation_audit_path": str(PREAUDIT),
            "activation_path": str(ACTIVATION),
            "execution_start_path": str(EXECUTION_START),
            "forward_result_path": str(FORWARD_RESULT),
            "final_result_path": str(FINAL_RESULT),
            "postresult_audit_path": str(POSTAUDIT),
            "output_root": str(OUTPUT_ROOT),
            "safe_progress_path": str(SAFE_PROGRESS),
            "parent_deadline_grace_seconds": 15,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_open_only_after_exact220_prediction_freeze": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_exact220_forward_after_activation_and_inactive_lease": True,
            "post_freeze_official_evaluator": True,
            "additional_rollout_or_avg4": False,
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
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("task_contract", {}).get("runtime_boundary") != ["opaque_id", "question"]
        or value.get("forward_contract", {}).get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("model_slot_contract", {}).get("slot_cap") != MODEL_SLOT_CAP
        or value.get("authorization", {}).get("additional_rollout_or_avg4") is not False
        or value.get("authorization", {}).get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.42.67 protocol identity drifted")
    parent_protocol, _, _ = _parent(root)
    _invalid_predecessor(root)
    if value.get("evaluator_contract") != parent_protocol["evaluator_contract"]:
        raise RuntimeError("V2.42.67 evaluator identity drifted")
    predecessor = value.get("parents", {}).get("invalid_v24266_audit", {})
    if (
        predecessor.get("path") != str(INVALID_PREDECESSOR_AUDIT)
        or predecessor.get("sha256") != sha256(root / INVALID_PREDECESSOR_AUDIT)
        or value.get("parents", {}).get("invalid_v24266_partial_outputs_reused") is not False
        or value.get("candidate", {}).get("child_entrypoint") != CHILD_MARKER
        or value.get("forward_contract", {}).get("parent_child_and_validator_exception_paths_are_total") is not True
        or value.get("forward_contract", {}).get("invalid_predecessor_output_reuse_allowed") is not False
    ):
        raise RuntimeError("V2.42.67 successor binding drifted")
    for name in ("forward_surface", "control_surface"):
        manifest = value[name]["manifest"]
        if payload_sha256(manifest) != value[name]["manifest_sha256"]:
            raise RuntimeError(f"V2.42.67 {name} seal drifted")
        for relative, digest in manifest.items():
            if sha256(_ordinary(root, relative)) != digest:
                raise RuntimeError(f"V2.42.67 frozen source drifted: {relative}")
    ids = selected_ids(root)
    if payload_sha256(ids) != value["task_contract"]["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.67 exact-220 partition drifted")
    tasks = selected_tasks(root, value)
    if len(tasks) != SELECTED_COUNT or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.42.67 visible exact-220 task set drifted")
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
