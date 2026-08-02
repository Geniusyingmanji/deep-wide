#!/usr/bin/env python3
"""Freeze the V2.42.70 candidate-only dev-validation64 quality gate."""

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

from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)
from deepwide_agent.v24271_forward_contract import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_PROTOCOL,
    FORWARD_RESULT,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    OUTPUT_ROOT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUNNER_MARKER,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SEARCH,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    TASK_ROOT,
    selected_tasks,
)


ROLE = "v24271_keyless_candidate_vs_frozen_control_dev64_preregistration"
OUTPUT = Path("results/v24271_keyless_dev64_preregistration_v1_20260802.json")
PREAUDIT = Path("results/v24271_keyless_dev64_preactivation_audit_v1_20260802.json")
FINAL_RESULT = Path("results/v24271_keyless_dev64_result_v1_20260802.json")
POSTAUDIT = Path("results/v24271_keyless_dev64_postresult_audit_v1_20260802.json")
EVALUATOR_ROOT = OUTPUT_ROOT / "evaluator"
FINALIZER_MARKER = "scripts/finalize_v24271_keyless_dev64.py"
CONTROL_ID_SOURCE = Path("configs/full220_v2403_r1_devval_s04.ids")
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
CONTROL_PROTOCOL = Path("results/v24267_exact220_preregistration_v1_20260802.json")
CONTROL_RESULT = Path("results/v24267_exact220_result_v1_20260802.json")
CONTROL_POSTAUDIT = Path("results/v24267_exact220_postresult_audit_v1_20260802.json")
CONTROL_OUTPUT_ROOT = Path("outputs/v24267_exact220_v1_20260802")
CONTROL_PREDICTION_FREEZE = CONTROL_OUTPUT_ROOT / "prediction_freeze.json"
CONTROL_RUNTIME = CONTROL_OUTPUT_ROOT / "runtime_predictions.jsonl"
CONTROL_RUN_SUMMARY = CONTROL_OUTPUT_ROOT / "run_summary.json"
ENGINEERING_PARENT = Path(
    "results/v24270_budget_equivalent_nonbenchmark_smoke_result_v1_20260802.json"
)
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")

FORWARD_FILES = (
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24267_total_fallback.py",
    "src/deepwide_agent/v24268_keyless_batched_runtime.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24270_budget_equivalent_union.py",
    "src/deepwide_agent/__init__.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24270_budget_equivalent_task.py",
)
FORWARD_ENTRY_FILES = (
    "src/deepwide_agent/v24271_forward_contract.py",
    "scripts/run_v24271_keyless_dev64.py",
)
CONTROL_FILES = (
    "scripts/preregister_v24271_keyless_dev64.py",
    "scripts/audit_v24271_keyless_dev64.py",
    "scripts/activate_v24271_keyless_dev64.py",
    "scripts/run_v24271_keyless_dev64.py",
    "scripts/finalize_v24271_keyless_dev64.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "tests/test_v24271_keyless_dev64.py",
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
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.71 path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.71 expected ordinary file: {relative}")
    return path


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (not relative.startswith("tests/") and OPAQUE.search(source)):
            raise RuntimeError(f"V2.42.71 unsafe frozen source: {relative}")
        output[relative] = sha256(path)
    return output


def selected_ids(root: Path = ROOT) -> list[str]:
    values = [
        line.strip()
        for line in _ordinary(root, CONTROL_ID_SOURCE)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if (
        len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(OPAQUE.fullmatch(value) is None for value in values)
    ):
        raise RuntimeError("V2.42.71 frozen development opaque IDs drifted")
    return values


def _parents(root: Path) -> dict[str, Any]:
    engineering_path = _ordinary(root, ENGINEERING_PARENT)
    engineering = read_object(engineering_path)
    control_protocol_path = _ordinary(root, CONTROL_PROTOCOL)
    control_result_path = _ordinary(root, CONTROL_RESULT)
    control_audit_path = _ordinary(root, CONTROL_POSTAUDIT)
    control_freeze_path = _ordinary(root, CONTROL_PREDICTION_FREEZE)
    control_protocol = read_object(control_protocol_path)
    control_result = read_object(control_result_path)
    control_audit = read_object(control_audit_path)
    control_freeze = read_object(control_freeze_path)
    if (
        engineering.get("status") != "engineering_go"
        or engineering.get("gate", {}).get("engineering_passed") is not True
        or engineering.get("authorization", {}).get("paired_dev_design") is not True
        or engineering.get("authorization", {}).get("paired_dev_launch") is not False
        or engineering.get("claims", {}).get("benchmark_quality_measured") is not False
        or control_protocol.get("role") != "v24267_exact220_preregistration"
        or not _sealed(control_protocol, "decision_contract_sha256")
        or control_result.get("role") != "v24267_exact220_result"
        or not _sealed(control_result, "result_payload_sha256")
        or control_result.get("claims", {}).get("sota") is not False
        or control_audit.get("role") != "v24267_exact220_postresult_audit"
        or control_audit.get("audit_valid") is not True
        or not _sealed(control_audit, "audit_payload_sha256")
        or control_freeze.get("role") != "v24267_exact220_prediction_freeze"
        or not _sealed(control_freeze, "freeze_payload_sha256")
        or control_freeze.get("selected") != 220
        or control_freeze.get("terminal") != 220
        or control_freeze.get(
            "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open"
        )
        is not True
    ):
        raise RuntimeError("V2.42.71 parent identity drifted")
    evaluator = control_protocol.get("evaluator_contract")
    if not isinstance(evaluator, dict) or evaluator.get(
        "mapping_query_answer_or_gold_bytes_opened_or_hashed"
    ) is not False:
        raise RuntimeError("V2.42.71 evaluator identity drifted")
    return {
        "engineering": engineering,
        "control_protocol": control_protocol,
        "control_result": control_result,
        "control_audit": control_audit,
        "control_freeze": control_freeze,
        "evaluator": evaluator,
    }


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    parents = _parents(root)
    ids = selected_ids(root)
    manifest_path = _ordinary(root, SOURCE_MANIFEST)
    present = [
        str(path)
        for path in (*FUTURE_PATHS, FORWARD_PROTOCOL)
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.71 future surface is not pristine: {present}")
    forward_dependencies = _manifest(root, FORWARD_FILES)
    forward_entries = _manifest(root, FORWARD_ENTRY_FILES)
    forward = {**forward_dependencies, **forward_entries}
    controls = _manifest(root, CONTROL_FILES)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "engineering_gate": {
                "path": str(ENGINEERING_PARENT),
                "sha256": sha256(root / ENGINEERING_PARENT),
                "status": parents["engineering"]["status"],
            },
            "frozen_control_protocol": {
                "path": str(CONTROL_PROTOCOL),
                "sha256": sha256(root / CONTROL_PROTOCOL),
            },
            "frozen_control_result": {
                "path": str(CONTROL_RESULT),
                "sha256": sha256(root / CONTROL_RESULT),
            },
            "frozen_control_postresult_audit": {
                "path": str(CONTROL_POSTAUDIT),
                "sha256": sha256(root / CONTROL_POSTAUDIT),
            },
            "frozen_control_prediction_freeze": {
                "path": str(CONTROL_PREDICTION_FREEZE),
                "sha256": sha256(root / CONTROL_PREDICTION_FREEZE),
                "content_free_identity_only": True,
            },
            "historical_control_prediction_mapping_gold_or_evaluator_rows_opened_or_hashed": False,
        },
        "comparison_contract": {
            "control": "frozen V2.42.67 last dev-validation64 rows",
            "candidate": "one cold V2.42.70 rollout on the same 64 opaque IDs",
            "shared_random_prefix": False,
            "strict_causal_ablation": False,
            "development_gate_only": True,
            "control_prediction_bytes_open_only_after_candidate_exact64_freeze": True,
            "both_arms_fully_re_evaluated_with_the_same_current_judge": True,
            "old_evaluator_rows_reused": False,
            "selective_changed_prediction_evaluation": False,
        },
        "task_contract": {
            "manifest": {
                "path": str(SOURCE_MANIFEST),
                "sha256": sha256(manifest_path),
                "row_schema": ["opaque_id", "question"],
            },
            "selection_rule": "frozen opaque-ID allowlist; no category, question_type, or split metadata",
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids": ids,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_split_category_gold_evaluator_or_score_used_for_selection": False,
            "development_resource_already_consumed_not_fresh_or_held_out": True,
        },
        "forward_contract": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "global_model_slot_cap": MODEL_SLOT_CAP,
            "maximum_concurrent_loopback_provider_requests": EXECUTOR_CONCURRENCY,
            "exact_terminal_predictions_required": SELECTED_COUNT,
            "one_candidate_forward_per_visible_task": True,
            "resume_rerun_skip_or_selective_retry_allowed": False,
            "worker_or_validator_failure_returns_total_v24270_fallback": True,
            "mapping_control_prediction_gold_or_evaluator_open_before_candidate_freeze": False,
        },
        "limits": dict(LIMITS),
        "provider_contract": {
            "model": dict(MODEL),
            "search": dict(SEARCH),
            "credential_required_or_persisted": False,
        },
        "model_slot_contract": {
            "pool_id": MODEL_SLOT_POOL_ID,
            "slot_cap": MODEL_SLOT_CAP,
            "directory": str(MODEL_SLOT_DIRECTORY),
            "receipt_required_per_child": True,
            "receipt_acquisitions_must_equal_actual_model_requests": True,
        },
        "freeze_contract": {
            "candidate_runtime_path": str(RUNTIME_PREDICTIONS),
            "candidate_summary_path": str(RUN_SUMMARY),
            "candidate_freeze_path": str(PREDICTION_FREEZE),
            "candidate_exact64_before_control_or_evaluator_side_open": True,
        },
        "evaluator_contract": dict(parents["evaluator"]),
        "evaluation_contract": {
            "control_and_candidate_full64_current_judge_evaluation": True,
            "conservative_denominator_per_arm": SELECTED_COUNT,
            "forward_or_evaluator_failure_as_zero": True,
            "selective_error_retry_allowed": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "decision_contract": {
            "maximum_search_token_ratio": 0.35,
            "maximum_task_wall_sum_ratio": 0.5,
            "minimum_quality_composite_delta": -0.01,
            "minimum_entity_acc_delta": -0.03125,
            "minimum_f1_by_row_delta": -0.02,
            "minimum_f1_by_item_delta": -0.02,
            "minimum_column_f1_delta": -0.02,
            "minimum_whole_table_success_delta": 0,
            "minimum_model_generated_table_delta": -1,
            "candidate_unrecoverable_provider_failures_maximum": 0,
        },
        "lease_contract": {
            "path": str(LEASE),
            "forward_owner": "v24271_keyless_dev64_forward_v1",
            "forward_purpose": "label_blind_keyless_candidate_dev64_forward",
            "evaluator_owner": "v24271_keyless_dev64_evaluator_v1",
            "evaluator_purpose": "post_candidate_freeze_full64_both_arms_evaluator",
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
            "parent_deadline_grace_seconds": 15,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "historical_control_and_evaluator_open_only_after_candidate_exact64_freeze": True,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_candidate_dev64_forward_after_activation": True,
            "post_freeze_full64_both_arms_evaluator": True,
            "successor_entropy_voc_design_if_go": True,
            "new_exact220_launch": False,
            "additional_rollout_or_avg4": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "forward_surface": {
            "dependency_manifest": forward_dependencies,
            "dependency_manifest_sha256": payload_sha256(forward_dependencies),
            "entry_manifest": forward_entries,
            "entry_manifest_sha256": payload_sha256(forward_entries),
            "manifest": forward,
            "manifest_sha256": payload_sha256(forward),
        },
        "control_surface": {
            "manifest": controls,
            "manifest_sha256": payload_sha256(controls),
        },
    }
    projection = build_forward_contract(value)
    value["forward_runtime_contract"] = {
        "path": str(FORWARD_PROTOCOL),
        "payload_sha256": projection["forward_contract_payload_sha256"],
        "contains_control_mapping_gold_evaluator_or_score_path": False,
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def build_forward_contract(protocol: dict[str, Any]) -> dict[str, Any]:
    lease = protocol["lease_contract"]
    execution = protocol["execution"]
    value = {
        "artifact_version": 1,
        "role": "v24271_keyless_dev64_forward_contract",
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": protocol["created_at_unix"],
        "label_blind": True,
        "task_contract": {
            key: protocol["task_contract"][key]
            for key in (
                "manifest",
                "selection_rule",
                "selected_count",
                "selected_opaque_ids",
                "selected_opaque_ids_sha256",
                "runtime_boundary",
                "mapping_split_category_gold_evaluator_or_score_used_for_selection",
            )
        },
        "forward_contract": dict(protocol["forward_contract"]),
        "limits": dict(protocol["limits"]),
        "provider_contract": dict(protocol["provider_contract"]),
        "model_slot_contract": dict(protocol["model_slot_contract"]),
        "lease_contract": {
            key: lease[key]
            for key in ("path", "forward_owner", "forward_purpose")
        },
        "execution": {
            key: execution[key]
            for key in (
                "runner_marker",
                "child_marker",
                "preactivation_audit_path",
                "activation_path",
                "execution_start_path",
                "forward_result_path",
                "output_root",
                "parent_deadline_grace_seconds",
            )
        },
        "source_policy": dict(protocol["source_policy"]),
        "authorization": {
            key: protocol["authorization"][key]
            for key in (
                "single_candidate_dev64_forward_after_activation",
                "new_exact220_launch",
                "additional_rollout_or_avg4",
                "leaderboard_submission_or_sota_claim",
            )
        },
        "forward_surface": {
            "dependency_manifest": dict(
                protocol["forward_surface"]["dependency_manifest"]
            ),
            "dependency_manifest_sha256": protocol["forward_surface"][
                "dependency_manifest_sha256"
            ],
            "runner_entry": {
                "path": "scripts/run_v24271_keyless_dev64.py",
                "sha256": protocol["forward_surface"]["entry_manifest"][
                    "scripts/run_v24271_keyless_dev64.py"
                ],
            },
            "contract_source": {
                "path": "src/deepwide_agent/v24271_forward_contract.py",
                "sha256": protocol["forward_surface"]["entry_manifest"][
                    "src/deepwide_agent/v24271_forward_contract.py"
                ],
            },
        },
    }
    value["forward_contract_payload_sha256"] = payload_sha256(value)
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
        or value.get("forward_contract", {}).get("executor_concurrency")
        != EXECUTOR_CONCURRENCY
        or value.get("authorization", {}).get("new_exact220_launch") is not False
        or value.get("authorization", {}).get("leaderboard_submission_or_sota_claim")
        is not False
    ):
        raise RuntimeError("V2.42.71 protocol identity drifted")
    parents = _parents(root)
    if value.get("evaluator_contract") != parents["evaluator"]:
        raise RuntimeError("V2.42.71 evaluator contract drifted")
    for name in ("forward_surface", "control_surface"):
        manifest = value[name]["manifest"]
        if payload_sha256(manifest) != value[name]["manifest_sha256"]:
            raise RuntimeError(f"V2.42.71 {name} seal drifted")
        for relative, digest in manifest.items():
            if sha256(_ordinary(root, relative)) != digest:
                raise RuntimeError(f"V2.42.71 frozen source drifted: {relative}")
    forward = value["forward_surface"]
    if (
        payload_sha256(forward["dependency_manifest"])
        != forward["dependency_manifest_sha256"]
        or payload_sha256(forward["entry_manifest"])
        != forward["entry_manifest_sha256"]
        or {**forward["dependency_manifest"], **forward["entry_manifest"]}
        != forward["manifest"]
    ):
        raise RuntimeError("V2.42.71 forward source partition drifted")
    tasks = selected_tasks(root, value)
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.42.71 visible task count drifted")
    projection = read_object(_ordinary(root, FORWARD_PROTOCOL))
    expected_projection = build_forward_contract(value)
    if (
        projection != expected_projection
        or value.get("forward_runtime_contract")
        != {
            "path": str(FORWARD_PROTOCOL),
            "payload_sha256": projection.get("forward_contract_payload_sha256"),
            "contains_control_mapping_gold_evaluator_or_score_path": False,
        }
    ):
        raise RuntimeError("V2.42.71 forward runtime projection drifted")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    protocol = build_protocol()
    publish_new(ROOT / FORWARD_PROTOCOL, build_forward_contract(protocol))
    publish_new(ROOT / OUTPUT, protocol)
    print(
        json.dumps(
            {
                "forward_contract": str(FORWARD_PROTOCOL),
                "forward_contract_sha256": sha256(ROOT / FORWARD_PROTOCOL),
                "protocol": str(OUTPUT),
                "protocol_sha256": sha256(ROOT / OUTPUT),
            },
            sort_keys=True,
        )
    )
