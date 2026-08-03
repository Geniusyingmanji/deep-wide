#!/usr/bin/env python3
"""Freeze V2.42.90 rescue versus V2.42.87 on consumed dev/validation64."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24291_forward_contract import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EVALUATOR_ROOT,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FETCH_HELPER_MARKER,
    FINAL_RESULT,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    FULL_PROTOCOL,
    ID_SOURCE,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    OUTPUT_ROOT,
    POSTAUDIT,
    PREAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RESCUE_POLICY,
    RUNTIME_PREDICTIONS,
    RUNNER_MARKER,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SEARCH,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    TASK_ROOT,
    TWO_WAVE_POLICY,
    payload_sha256,
    sha256,
    source_selected_ids,
)


ROLE = "v24291_low_coverage_rescue_consumed_dev64_preregistration"
NEUTRAL_DECISION = Path("results/v24290_neutral_low_coverage_decision_v1_20260803.json")
DIAGNOSIS = Path("results/v24288_v24287_exact220_diagnosis_v1_20260803.json")
CONTROL_RESULT = Path("results/v24287_exact220_result_v1_20260803.json")
CONTROL_POSTAUDIT = Path("results/v24287_exact220_postresult_audit_v1_20260803.json")
CONTROL_PROTOCOL = Path("results/v24287_exact220_preregistration_v1_20260803.json")
CONTROL_FORWARD_CONTRACT = Path("results/v24287_exact220_forward_contract_v1_20260803.json")
CONTROL_FORWARD_RESULT = Path("results/v24287_exact220_forward_result_v1_20260803.json")
CONTROL_PREDICTION_FREEZE = Path("outputs/v24287_exact220_v1_20260803/prediction_freeze.json")
CONTROL_RUNTIME = Path("outputs/v24287_exact220_v1_20260803/runtime_predictions.jsonl")
CONTROL_RUN_SUMMARY = Path("outputs/v24287_exact220_v1_20260803/run_summary.json")
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
EVALUATOR_WORKERS_PER_ARM = 4
TOTAL_EVALUATOR_WORKERS = 8

DECISION_CONTRACT = {
    "minimum_quality_composite_delta": 0.002,
    "minimum_entity_acc_delta": 0.0,
    "minimum_f1_by_row_delta": -0.005,
    "minimum_f1_by_item_delta": -0.005,
    "minimum_column_f1_delta": -0.005,
    "minimum_whole_table_success_delta": 0,
    "minimum_model_generated_table_delta": 0,
    "maximum_system_token_ratio": 1.20,
    "maximum_task_wall_sum_ratio": 1.25,
    "maximum_candidate_evaluator_invalid_or_not_run": 2,
    "maximum_candidate_fallback_tables": 0,
    "minimum_rescue_triggered_tasks": 1,
    "maximum_hosted_search_requests_added_by_rescue": 0,
    "maximum_cache_misses": 0,
    "maximum_cache_serve_network_fetches": 0,
    "maximum_hard_fetch_deadline_failures": 4,
    "maximum_fetch_helper_failures": 0,
}

FORWARD_FILES = (
    "src/deepwide_agent/__init__.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24267_total_fallback.py",
    "src/deepwide_agent/v24268_keyless_batched_runtime.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24272_two_wave_retrieval.py",
    "src/deepwide_agent/v24273_two_wave_task_runtime.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24289_low_coverage_rescue.py",
    "src/deepwide_agent/v24290_low_coverage_task_runtime.py",
    "src/deepwide_agent/v24291_dev64_runtime.py",
    "src/deepwide_agent/v24291_forward_contract.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/run_v24291_dev64_task.py",
    "scripts/run_v24291_dev64.py",
)
CONTROL_FILES = (
    "scripts/preregister_v24291_dev64.py",
    "scripts/audit_v24291_dev64.py",
    "scripts/activate_v24291_dev64.py",
    "scripts/finalize_v24291_dev64.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "tests/test_v24291_dev64.py",
)
FUTURE_PATHS = (
    FORWARD_CONTRACT,
    FULL_PROTOCOL,
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    FORWARD_RESULT,
    FINAL_RESULT,
    POSTAUDIT,
    OUTPUT_ROOT,
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if raw.is_absolute() or ".." in raw.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.91 expected ordinary file: {relative}")
    return path


def _read(root: Path, path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.42.91 expected object: {path}")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(root: Path, files: tuple[str, ...], *, forbid_opaque: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (forbid_opaque and OPAQUE.search(source)):
            raise RuntimeError(f"V2.42.91 unsafe frozen source: {relative}")
        output[relative] = sha256(path)
    return output


def _parents(root: Path) -> dict[str, Any]:
    neutral = _read(root, NEUTRAL_DECISION)
    diagnosis = _read(root, DIAGNOSIS)
    control = _read(root, CONTROL_RESULT)
    post = _read(root, CONTROL_POSTAUDIT)
    control_protocol = _read(root, CONTROL_PROTOCOL)
    if (
        neutral.get("status") != "neutral_mechanism_go"
        or neutral.get("passed") is not True
        or neutral.get("authorization", {}).get("consumed_dev64_design") is not True
        or neutral.get("authorization", {}).get("consumed_dev64_launch") is not False
        or neutral.get("claim_scope", {}).get("benchmark_quality_measured") is not False
        or diagnosis.get("mechanism_conclusions", {}).get("quality_regressed") is not True
        or diagnosis.get("controller", {}).get("expand_low_coverage", {}).get("selected") != 23
        or control.get("status") != "exact220_single_rollout_complete"
        or control.get("selected") != 220
        or control.get("claims", {}).get("sota") is not False
        or not _sealed(control, "result_payload_sha256")
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or not _sealed(post, "audit_payload_sha256")
        or control_protocol.get("role") != "v24287_exact220_preregistration"
        or not _sealed(control_protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.42.91 parent evidence drifted")
    evaluator = control_protocol.get("evaluator_contract")
    if (
        not isinstance(evaluator, dict)
        or evaluator.get("mapping_query_answer_or_gold_bytes_opened_or_hashed") is not False
        or evaluator.get("mapping", {}).get("path") != str(MAPPING_PATH)
    ):
        raise RuntimeError("V2.42.91 inherited evaluator contract drifted")
    return {
        "neutral": neutral,
        "diagnosis": diagnosis,
        "control": control,
        "post": post,
        "control_protocol": control_protocol,
        "evaluator": evaluator,
    }


def build_forward_contract(root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    root = root.resolve()
    parents = _parents(root)
    ids = source_selected_ids(root)
    present = [str(path) for path in (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT) if (root / path).exists() or (root / path).is_symlink()]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.91 forward future surface is not pristine: {present}")
    dependencies = _manifest(root, FORWARD_FILES, forbid_opaque=True)
    value = {
        "artifact_version": 1,
        "role": "v24291_low_coverage_rescue_dev64_forward_contract",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parent_evidence": {
            "neutral_decision": {"path": str(NEUTRAL_DECISION), "sha256": sha256(root / NEUTRAL_DECISION)},
            "postterminal_diagnosis": {"path": str(DIAGNOSIS), "sha256": sha256(root / DIAGNOSIS)},
            "control_aggregate_result": {"path": str(CONTROL_RESULT), "sha256": sha256(root / CONTROL_RESULT)},
            "control_postresult_audit": {"path": str(CONTROL_POSTAUDIT), "sha256": sha256(root / CONTROL_POSTAUDIT)},
            "control_per_task_runtime_prediction_freeze_or_summary_opened_or_hashed": False,
        },
        "task_contract": {
            "manifest_path": str(SOURCE_MANIFEST),
            "manifest_sha256": sha256(_ordinary(root, SOURCE_MANIFEST)),
            "id_source_path": str(ID_SOURCE),
            "id_source_sha256": sha256(_ordinary(root, ID_SOURCE)),
            "selection_rule": "frozen opaque-ID allowlist; split/category/question_type unavailable to runtime",
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids": ids,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_split_category_gold_score_used_for_selection": False,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model_slot_pool_id": MODEL_SLOT_POOL_ID,
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "fetch_helper_marker": FETCH_HELPER_MARKER,
            "output_root": str(OUTPUT_ROOT),
            "model_slot_directory": str(MODEL_SLOT_DIRECTORY),
            "task_root": str(TASK_ROOT),
            "runtime_predictions": str(RUNTIME_PREDICTIONS),
            "run_summary": str(RUN_SUMMARY),
            "prediction_freeze": str(PREDICTION_FREEZE),
            "safe_progress": str(SAFE_PROGRESS),
            "resume_skip_rerun_or_selective_retry": False,
        },
        "limits": dict(LIMITS),
        "two_wave_policy": dict(TWO_WAVE_POLICY),
        "rescue_policy": dict(RESCUE_POLICY),
        "model": dict(MODEL),
        "search": dict(SEARCH),
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        },
        "dependency_manifest": dependencies,
        "dependency_manifest_sha256": payload_sha256(dependencies),
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "candidate_64_predictions_frozen_before_control_or_evaluator_open": True,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_consumed_dev64_candidate_forward": True,
            "additional_rollout_resume_skip_or_rerun": False,
        },
    }
    value["forward_contract_payload_sha256"] = payload_sha256(value)
    return value


def build_protocol(
    root: Path = ROOT,
    *,
    forward: dict[str, Any] | None = None,
    now: int | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    parents = _parents(root)
    chosen = forward or build_forward_contract(root, now=now, require_pristine=require_pristine)
    present = [str(path) for path in (FINAL_RESULT, POSTAUDIT) if (root / path).exists() or (root / path).is_symlink()]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.91 result future surface is not pristine: {present}")
    controls = _manifest(root, CONTROL_FILES, forbid_opaque=False)
    evaluator = dict(parents["evaluator"])
    evaluator["mapping_query_answer_or_gold_bytes_opened_or_hashed"] = False
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_runtime_contract": {
            "path": str(FORWARD_CONTRACT),
            "payload_sha256": chosen["forward_contract_payload_sha256"],
            "dependency_manifest_sha256": chosen["dependency_manifest_sha256"],
            "contains_control_mapping_gold_evaluator_or_score_path": False,
        },
        "comparison_contract": {
            "control": "frozen V2.42.87 predictions restricted to the same consumed dev-validation64",
            "candidate": "one cold V2.42.90 low-coverage rescue rollout on all 64 opaque IDs",
            "strict_shared_random_prefix_causal_ablation": False,
            "development_gate_only": True,
            "candidate_exact64_before_control_prediction_mapping_gold_or_evaluator_open": True,
            "both_arms_fully_evaluated_with_same_current_judge": True,
            "old_evaluator_rows_reused": False,
            "selective_changed_prediction_evaluation": False,
            "fixed_denominator_per_arm": SELECTED_COUNT,
            "failure_as_zero": True,
        },
        "task_contract": dict(chosen["task_contract"]),
        "execution_contract": dict(chosen["execution"]),
        "decision_contract": dict(DECISION_CONTRACT),
        "evaluator_contract": evaluator,
        "evaluator_execution": {
            "workers_per_arm": EVALUATOR_WORKERS_PER_ARM,
            "total_parallel_workers": TOTAL_EVALUATOR_WORKERS,
            "fixed_contiguous_partition_sizes_per_arm": [16, 16, 16, 16],
            "selective_retry_or_error_revaluation": False,
        },
        "lease_contract": {
            "path": str(LEASE_PATH),
            "forward_owner": LEASE_OWNER,
            "forward_purpose": LEASE_PURPOSE,
            "evaluator_owner": "v24291_dev64_evaluator_v1",
            "evaluator_purpose": "post_candidate_freeze_fresh_both_arm_full64_evaluation",
            "forward_and_evaluator_overlap": False,
        },
        "result_paths": {
            "forward_contract": str(FORWARD_CONTRACT),
            "preactivation_audit": str(PREAUDIT),
            "activation": str(ACTIVATION),
            "execution_start": str(EXECUTION_START),
            "forward_result": str(FORWARD_RESULT),
            "candidate_prediction_freeze": str(PREDICTION_FREEZE),
            "candidate_runtime_predictions": str(RUNTIME_PREDICTIONS),
            "candidate_run_summary": str(RUN_SUMMARY),
            "evaluator_root": str(EVALUATOR_ROOT),
            "final_result": str(FINAL_RESULT),
            "postresult_audit": str(POSTAUDIT),
        },
        "control_sources_post_candidate_freeze_only": {
            "aggregate_result": str(CONTROL_RESULT),
            "postresult_audit": str(CONTROL_POSTAUDIT),
            "forward_contract": str(CONTROL_FORWARD_CONTRACT),
            "forward_result": str(CONTROL_FORWARD_RESULT),
            "prediction_freeze": str(CONTROL_PREDICTION_FREEZE),
            "runtime_predictions": str(CONTROL_RUNTIME),
            "run_summary": str(CONTROL_RUN_SUMMARY),
            "prediction_freeze_runtime_and_summary_opened_or_hashed_during_preregistration": False,
        },
        "control_manifest": controls,
        "control_manifest_sha256": payload_sha256(controls),
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "control_prediction_mapping_gold_category_question_type_split_evaluator_score_read_by_candidate_forward": False,
            "candidate_prediction_freeze_before_control_or_evaluator_side_open": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "single_candidate_dev64_forward_and_postfreeze_full_both_arm_evaluation": True,
            "additional_dev64_rollout_resume_skip_selective_retry": False,
            "exact220_launch": False,
            "avg_at_4": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path = ROOT, path: Path = FULL_PROTOCOL, *, value: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = value or _read(root, path)
    if (
        protocol.get("role") != ROLE
        or protocol.get("protocol_id") != PROTOCOL_ID
        or not _sealed(protocol, "protocol_payload_sha256")
        or protocol.get("decision_contract") != DECISION_CONTRACT
        or protocol.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or protocol.get("task_contract", {}).get("runtime_boundary") != ["opaque_id", "question"]
        or protocol.get("evaluator_execution")
        != {
            "workers_per_arm": EVALUATOR_WORKERS_PER_ARM,
            "total_parallel_workers": TOTAL_EVALUATOR_WORKERS,
            "fixed_contiguous_partition_sizes_per_arm": [16, 16, 16, 16],
            "selective_retry_or_error_revaluation": False,
        }
        or protocol.get("result_paths")
        != {
            "forward_contract": str(FORWARD_CONTRACT),
            "preactivation_audit": str(PREAUDIT),
            "activation": str(ACTIVATION),
            "execution_start": str(EXECUTION_START),
            "forward_result": str(FORWARD_RESULT),
            "candidate_prediction_freeze": str(PREDICTION_FREEZE),
            "candidate_runtime_predictions": str(RUNTIME_PREDICTIONS),
            "candidate_run_summary": str(RUN_SUMMARY),
            "evaluator_root": str(EVALUATOR_ROOT),
            "final_result": str(FINAL_RESULT),
            "postresult_audit": str(POSTAUDIT),
        }
        or protocol.get("authorization", {}).get("exact220_launch") is not False
        or protocol.get("authorization", {}).get("sota_claim") is not False
    ):
        raise RuntimeError("V2.42.91 protocol identity drifted")
    controls = protocol.get("control_manifest")
    if not isinstance(controls, dict) or protocol.get("control_manifest_sha256") != payload_sha256(controls):
        raise RuntimeError("V2.42.91 control manifest drifted")
    for relative, digest in controls.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError(f"V2.42.91 control dependency drifted: {relative}")
    forward_binding = protocol.get("forward_runtime_contract") or {}
    if (root / FORWARD_CONTRACT).is_file():
        frozen = json.loads((root / FORWARD_CONTRACT).read_text(encoding="utf-8"))
        if (
            forward_binding.get("path") != str(FORWARD_CONTRACT)
            or forward_binding.get("payload_sha256")
            != frozen.get("forward_contract_payload_sha256")
            or forward_binding.get("dependency_manifest_sha256")
            != frozen.get("dependency_manifest_sha256")
            or forward_binding.get("contains_control_mapping_gold_evaluator_or_score_path")
            is not False
        ):
            raise RuntimeError("V2.42.91 full/forward contract binding drifted")
    return protocol


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
    forward = build_forward_contract()
    protocol = build_protocol(forward=forward)
    publish_new(ROOT / FORWARD_CONTRACT, forward)
    publish_new(ROOT / FULL_PROTOCOL, protocol)
    print(json.dumps({"forward": str(FORWARD_CONTRACT), "protocol": str(FULL_PROTOCOL)}, sort_keys=True))
