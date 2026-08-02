#!/usr/bin/env python3
"""Freeze the shared-prefix V2.42.65 paired dev64 experiment."""

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
from scripts import preregister_v24264_targeted_capacity as parent  # noqa: E402
from scripts import run_v24264_targeted_capacity as parent_runner  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    load_manifest,
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24265_shared_prefix_paired_dev64_preregistration"
PROTOCOL_ID = "v24265_v24257_vs_v24259_shared_prefix_paired_dev64_v1"
OUTPUT = Path("results/v24265_paired_dev64_preregistration_v1_20260802.json")
PREAUDIT = Path("results/v24265_paired_dev64_preactivation_audit_v1_20260802.json")
ACTIVATION = Path("results/v24265_paired_dev64_activation_v1_20260802.json")
EXECUTION_START = Path("results/v24265_paired_dev64_execution_start_v1_20260802.json")
FORWARD_RESULT = Path("results/v24265_paired_dev64_forward_result_v1_20260802.json")
FINAL_RESULT = Path("results/v24265_paired_dev64_result_v1_20260802.json")
POSTAUDIT = Path("results/v24265_paired_dev64_postresult_audit_v1_20260802.json")
OUTPUT_ROOT = Path("outputs/v24265_paired_dev64_v1_20260802")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
CONTROL_RUNTIME = OUTPUT_ROOT / "control_runtime_predictions.jsonl"
CANDIDATE_RUNTIME = OUTPUT_ROOT / "candidate_runtime_predictions.jsonl"
CONTROL_SUMMARY = OUTPUT_ROOT / "control_run_summary.json"
CANDIDATE_SUMMARY = OUTPUT_ROOT / "candidate_run_summary.json"
CONTROL_FREEZE = OUTPUT_ROOT / "control_prediction_freeze.json"
CANDIDATE_FREEZE = OUTPUT_ROOT / "candidate_prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
EVALUATOR_ROOT = OUTPUT_ROOT / "evaluator"
LEASE = parent.LEASE
LEASE_OWNER_FORWARD = "v24265_paired_dev64_forward_v1"
LEASE_OWNER_EVALUATOR = "v24265_paired_dev64_evaluator_v1"
LEASE_PURPOSE_FORWARD = "shared_prefix_label_blind_paired_dev64_forward"
LEASE_PURPOSE_EVALUATOR = "post_terminal_paired_dev64_official_evaluator"
RUNNER_MARKER = "scripts/run_v24265_paired_dev64.py"
FINALIZER_MARKER = "scripts/finalize_v24265_paired_dev64.py"
CHILD_MARKER = "scripts/run_v24265_paired_task.py"
MODEL_SLOT_CAP = 2
EXECUTOR_CONCURRENCY = 4
SELECTED_COUNT = 64

PARENT_PROTOCOL = parent.OUTPUT
PARENT_RESULT = parent.RESULT
PARENT_AUDIT = parent.POSTAUDIT
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCE = Path("configs/full220_v2403_r1_devval_s04.ids")
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
RELEASE_SEAL = Path("results/full220_v2403_r1_20260725_finalize_seal.json")
RELEASE_EVALUATOR_CONTRACT = Path(
    "outputs/full220_v2403_r1_eval_20260725/run_config.json"
)
EVALUATOR_QUERY_PATH = Path(
    "external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/"
    "data/overall_20250916.jsonl"
)
EVALUATOR_ANSWER_ROOT = Path(
    "external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/"
    "data/overall_20250916_tables"
)
EXPECTED_JUDGE = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "max_output_tokens": 8192,
    "timeout_seconds": 600,
    "max_retries": 12,
}
EXPECTED_RECOVERY = {
    "explicit_resume_required": True,
    "committed_success_or_error_is_terminal": True,
    "committed_rows_must_be_exact_prediction_prefix": True,
    "canonical_result_file_atomic_replace_per_task": True,
    "selective_error_retry_allowed": False,
}

FORWARD_FILES = tuple(
    dict.fromkeys(
        [
            *parent.FORWARD_FILES,
            "src/deepwide_agent/v24265_paired_normalizer_runtime.py",
            "scripts/run_v24265_paired_task.py",
            "scripts/run_v24265_paired_dev64.py",
        ]
    )
)
CONTROL_FILES = (
    "src/deepwide_agent/v24265_paired_normalizer_runtime.py",
    "scripts/run_v24265_paired_task.py",
    "scripts/run_v24265_paired_dev64.py",
    "scripts/finalize_v24265_paired_dev64.py",
    "scripts/preregister_v24265_paired_dev64.py",
    "scripts/activate_v24265_paired_dev64.py",
    "scripts/audit_v24265_paired_dev64.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/run_official_eval_local.py",
    "scripts/audit_v24187_phase_liveness.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/preregister_v24259_deterministic_normalizer_smoke.py",
    "tests/test_v24265_paired_normalizer_runtime.py",
    "tests/test_v24265_paired_dev64.py",
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
        raise RuntimeError("V2.42.65 path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.65 expected ordinary file: {relative}")
    return path


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = parent.validate_protocol(root, PARENT_PROTOCOL)
    result = read_object(_ordinary(root, PARENT_RESULT))
    parent_runner.validate_result(protocol, result)
    audit = read_object(_ordinary(root, PARENT_AUDIT))
    if (
        result.get("capacity_gate") != "go"
        or result.get("selected_executor_concurrency") != EXECUTOR_CONCURRENCY
        or result.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or result.get("official_evaluator_called") is not False
        or audit.get("role") != "v24264_targeted_capacity_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("claims", {}).get("target_concurrency_four_stable") is not True
        or audit.get("authorization", {}).get("paired_dev64_successor_design") is not True
        or audit.get("authorization", {}).get("paired_dev64_launch") is not False
        or audit.get("source_policy", {}).get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.65 capacity parent drifted")
    return protocol, result, audit


def _evaluator_identity(root: Path) -> dict[str, Any]:
    # These are previously released content-free identity receipts.  Neither
    # mapping bytes nor query/answer corpus bytes are opened before both arms
    # reach exact terminal 64.
    seal_path = _ordinary(root, RELEASE_SEAL)
    contract_path = _ordinary(root, RELEASE_EVALUATOR_CONTRACT)
    seal = read_object(seal_path)
    contract = read_object(contract_path)
    mapping_sha = seal.get("mapping_sha256")
    query = contract.get("query_data") or {}
    answers = contract.get("answers") or {}
    source = contract.get("evaluator_source") or {}
    query_path = Path(str(query.get("path", "")))
    answer_root = Path(str(answers.get("root", "")))
    if (
        not isinstance(mapping_sha, str)
        or len(mapping_sha) != 64
        or contract.get("role") != "deepwide_official_evaluator_crash_recovery_contract"
        or contract.get("artifact_version") != 2
        or not all(
            isinstance(value, str) and len(value) == 64
            for value in (
                query.get("sha256"),
                answers.get("manifest_sha256"),
                source.get("manifest_sha256"),
            )
        )
        or query_path.resolve(strict=False)
        != (root / EVALUATOR_QUERY_PATH).resolve(strict=False)
        or answer_root.resolve(strict=False)
        != (root / EVALUATOR_ANSWER_ROOT).resolve(strict=False)
        or contract.get("judge") != EXPECTED_JUDGE
        or contract.get("recovery_policy") != EXPECTED_RECOVERY
        or contract.get("credentials") != "environment-only; not persisted"
    ):
        raise RuntimeError("V2.42.65 released evaluator identity drifted")
    return {
        "release_seal": {"path": str(RELEASE_SEAL), "sha256": sha256(seal_path)},
        "released_evaluator_contract": {
            "path": str(RELEASE_EVALUATOR_CONTRACT),
            "sha256": sha256(contract_path),
        },
        "mapping": {"path": str(MAPPING_PATH), "sha256": mapping_sha},
        "query_data": {
            "path": str(EVALUATOR_QUERY_PATH),
            "sha256": query["sha256"],
        },
        "answer_corpus": {
            "root": str(EVALUATOR_ANSWER_ROOT),
            "manifest_sha256": answers["manifest_sha256"],
        },
        "evaluator_source": {
            "manifest_sha256": source["manifest_sha256"],
        },
        "judge": dict(contract["judge"]),
        "recovery_policy": dict(contract["recovery_policy"]),
        "mapping_query_answer_or_gold_bytes_opened_or_hashed": False,
    }


def selected_ids(root: Path) -> list[str]:
    path = _ordinary(root, ID_SOURCE)
    values = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    if (
        len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(OPAQUE.fullmatch(value) is None for value in values)
    ):
        raise RuntimeError("V2.42.65 dev64 ID source drifted")
    return values


def selected_tasks(root: Path, protocol: dict[str, Any]) -> list[dict[str, str]]:
    ids = selected_ids(root)
    contract = protocol["task_contract"]
    if payload_sha256(ids) != contract["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.65 selected ID order drifted")
    manifest_path = _ordinary(root, SOURCE_MANIFEST)
    if sha256(manifest_path) != contract["manifest"]["sha256"]:
        raise RuntimeError("V2.42.65 visible manifest drifted")
    rows = load_manifest(manifest_path)
    if any(set(row) != {"opaque_id", "question"} for row in rows):
        raise RuntimeError("V2.42.65 visible manifest schema drifted")
    by_id = {row["opaque_id"]: row for row in rows}
    if any(value not in by_id for value in ids):
        raise RuntimeError("V2.42.65 visible task is absent")
    return [by_id[value] for value in ids]


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (not relative.startswith("tests/") and OPAQUE.search(source)):
            raise RuntimeError(f"V2.42.65 unsafe source: {relative}")
        output[relative] = sha256(path)
    return output


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    parent_protocol, _, _ = _parent(root)
    evaluator = _evaluator_identity(root)
    ids = selected_ids(root)
    manifest_path = _ordinary(root, SOURCE_MANIFEST)
    if sha256(manifest_path) != parent_protocol["task_contract"]["manifest"]["sha256"]:
        raise RuntimeError("V2.42.65 parent manifest drifted")
    present = [
        str(path)
        for path in FUTURE_PATHS
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.65 future surface is not pristine: {present}")
    forward = _manifest(root, FORWARD_FILES)
    controls = _manifest(root, CONTROL_FILES)
    limits = dict(parent_protocol["limits"])
    providers = dict(parent_protocol["provider_contract"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "capacity_protocol": {"path": str(PARENT_PROTOCOL), "sha256": sha256(root / PARENT_PROTOCOL)},
            "capacity_result": {"path": str(PARENT_RESULT), "sha256": sha256(root / PARENT_RESULT)},
            "capacity_postresult_audit": {"path": str(PARENT_AUDIT), "sha256": sha256(root / PARENT_AUDIT)},
            "selected_executor_concurrency": EXECUTOR_CONCURRENCY,
            "global_model_slot_cap": MODEL_SLOT_CAP,
            "quality_or_sota_claim": False,
        },
        "paired_hypothesis": {
            "control": "v24257_score_first_without_deterministic_normalizer",
            "candidate": "v24259_deterministic_table_normalizer",
            "single_scientific_change": "deterministic_markdown_structure_normalization_before_optional_repair",
            "plan_search_fetch_and_synthesis_shared_per_task": True,
            "repair_response_shared_if_both_arms_require_repair": True,
            "counterfactual_arm_cost_excludes_unneeded_repair": True,
            "task_prompt_model_search_provider_limits_and_random_prefix_identical": True,
        },
        "task_contract": {
            "manifest": {
                "path": str(SOURCE_MANIFEST),
                "sha256": sha256(manifest_path),
                "row_schema": ["opaque_id", "question"],
            },
            "id_source": {"path": str(ID_SOURCE), "sha256": sha256(root / ID_SOURCE)},
            "selection_rule": "exact frozen 24 dev plus 40 validation opaque IDs in existing order",
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_instance_split_category_gold_evaluator_or_score_used_for_selection": False,
            "development_resource_already_consumed_not_fresh_or_held_out": True,
        },
        "forward_contract": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "global_model_slot_cap": MODEL_SLOT_CAP,
            "exact_terminal_pairs_required": SELECTED_COUNT,
            "one_shared_prefix_forward_per_visible_task": True,
            "resume_rerun_skip_or_selective_retry_allowed": False,
            "failure_returns_two_schema_valid_terminal_predictions": True,
            "mapping_query_answer_gold_or_evaluator_open_before_both_freezes": False,
        },
        "limits": limits,
        "provider_contract": providers,
        "model_slot_contract": {
            "pool_id": POOL_ID,
            "slot_cap": MODEL_SLOT_CAP,
            "directory": str(MODEL_SLOT_DIRECTORY),
            "receipt_required_per_child": True,
            "receipt_acquisitions_must_equal_actual_shared_model_requests": True,
        },
        "freeze_contract": {
            "control_runtime_path": str(CONTROL_RUNTIME),
            "candidate_runtime_path": str(CANDIDATE_RUNTIME),
            "control_summary_path": str(CONTROL_SUMMARY),
            "candidate_summary_path": str(CANDIDATE_SUMMARY),
            "control_freeze_path": str(CONTROL_FREEZE),
            "candidate_freeze_path": str(CANDIDATE_FREEZE),
            "both_exact_64_before_evaluator_side_open": True,
        },
        "evaluator_contract": evaluator,
        "evaluator_pairing": {
            "control_evaluated_on_all_64_predictions": True,
            "candidate_evaluated_only_where_prediction_sha_differs": True,
            "candidate_identical_prediction_reuses_exact_control_evaluator_row": True,
            "reuse_requires_same_instance_question_and_prediction_bytes": True,
            "candidate_hybrid_result_revalidated_at_exact_64": True,
            "evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "paired_gate": {
            "denominator": SELECTED_COUNT,
            "failure_as_zero": True,
            "model_generated_table_delta_minimum": 0,
            "whole_table_success_delta_minimum": 0,
            "each_quality_component_delta_minimum": -0.005,
            "system_total_tokens_ratio_maximum": 1.0,
            "directional_gain_any": {
                "model_generated_table_delta_minimum": 1,
                "whole_table_success_delta_minimum": 1,
                "quality_composite_delta_minimum": 0.001,
            },
            "quality_components": ["entity_acc", "f1_by_row", "f1_by_item", "column_f1"],
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
            "evaluator_open_only_after_both_prediction_freezes": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_paired_dev64_forward_after_activation_and_inactive_lease": True,
            "post_terminal_official_evaluator_after_both_freezes": True,
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
        or value.get("task_contract", {}).get("runtime_boundary") != ["opaque_id", "question"]
        or value.get("forward_contract", {}).get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("model_slot_contract", {}).get("slot_cap") != MODEL_SLOT_CAP
        or value.get("authorization", {}).get("full220_launch") is not False
    ):
        raise RuntimeError("V2.42.65 protocol identity drifted")
    _parent(root)
    expected_evaluator = _evaluator_identity(root)
    if value.get("evaluator_contract") != expected_evaluator:
        raise RuntimeError("V2.42.65 evaluator identity receipt drifted")
    for name in ("forward_surface", "control_surface"):
        manifest = value[name]["manifest"]
        if payload_sha256(manifest) != value[name]["manifest_sha256"]:
            raise RuntimeError(f"V2.42.65 {name} seal drifted")
        for relative, digest in manifest.items():
            if sha256(_ordinary(root, relative)) != digest:
                raise RuntimeError(f"V2.42.65 frozen source drifted: {relative}")
    tasks = selected_tasks(root, value)
    if len(tasks) != SELECTED_COUNT or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.42.65 visible task set drifted")
    gate = value.get("paired_gate") or {}
    if (
        gate.get("denominator") != SELECTED_COUNT
        or gate.get("failure_as_zero") is not True
        or gate.get("model_generated_table_delta_minimum") != 0
        or gate.get("whole_table_success_delta_minimum") != 0
        or gate.get("each_quality_component_delta_minimum") != -0.005
        or gate.get("system_total_tokens_ratio_maximum") != 1.0
    ):
        raise RuntimeError("V2.42.65 paired gate drifted")
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
