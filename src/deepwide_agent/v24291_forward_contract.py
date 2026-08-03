"""Visible-only contract constants for the V2.42.91 consumed-dev64 gate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLE = "v24291_low_coverage_rescue_dev64_forward_contract"
PROTOCOL_ID = "v24291_v24290_low_coverage_rescue_consumed_dev64_v1"
FORWARD_CONTRACT = Path("results/v24291_dev64_forward_contract_v1_20260803.json")
FULL_PROTOCOL = Path("results/v24291_dev64_preregistration_v1_20260803.json")
PREAUDIT = Path("results/v24291_dev64_preactivation_audit_v1_20260803.json")
ACTIVATION = Path("results/v24291_dev64_activation_v1_20260803.json")
EXECUTION_START = Path("results/v24291_dev64_execution_start_v1_20260803.json")
FORWARD_RESULT = Path("results/v24291_dev64_forward_result_v1_20260803.json")
FINAL_RESULT = Path("results/v24291_dev64_result_v1_20260803.json")
POSTAUDIT = Path("results/v24291_dev64_postresult_audit_v1_20260803.json")
OUTPUT_ROOT = Path("outputs/v24291_low_coverage_dev64_v1_20260803")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "candidate_runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "candidate_run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "candidate_prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
EVALUATOR_ROOT = OUTPUT_ROOT / "evaluator"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24291_low_coverage_dev64_forward_v1"
LEASE_PURPOSE = "label_blind_v24290_low_coverage_rescue_consumed_dev64"
RUNNER_MARKER = "scripts/run_v24291_dev64.py"
CHILD_MARKER = "scripts/run_v24291_dev64_task.py"
FETCH_HELPER_MARKER = "scripts/run_v24287_fetch_helper.py"
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCE = Path("configs/full220_v2403_r1_devval_s04.ids")

EXECUTOR_CONCURRENCY = 8
MODEL_SLOT_CAP = 8
SELECTED_COUNT = 64
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
LIMITS = {
    "wall_seconds": 180,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
TWO_WAVE_POLICY = {
    "wave1_queries": 2,
    "wave1_fetches": 6,
    "wave2_queries": 2,
    "wave2_fetches": 4,
    "minimum_usable_pages": 3,
    "minimum_novel_pages": 3,
    "minimum_unique_hosts": 2,
    "content_chars_per_column": 1_200,
    "maximum_wave1_seconds": 30.0,
    "latency_loss_per_second": 0.005,
    "information_gain_weight": 0.25,
    "minimum_net_value": 0.0,
    "beta_prior_alpha": 1.0,
    "beta_prior_beta": 1.0,
}
RESCUE_POLICY = {
    "maximum_rescue_fetches": 4,
    "minimum_total_usable_pages": 4,
    "minimum_total_unique_hosts": 2,
    "content_chars_per_column": 1_200,
    "maximum_pre_rescue_retrieval_seconds": 60.0,
}
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 180,
    "max_retries": 2,
}
SEARCH = {
    "provider": "azure-native-keyless-same-response-tail-rescue",
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "batch_size": 8,
    "workers": 1,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 180,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "server_auto_fetch_enabled": False,
}
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if raw.is_absolute() or ".." in raw.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.91 expected ordinary forward file: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.42.91 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.42.91 expected JSON object: {path}")
    return value


def _sealed(value: MappingLike, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


MappingLike = dict[str, Any]


def source_selected_ids(root: Path) -> list[str]:
    values = [
        line.strip()
        for line in _ordinary(root, ID_SOURCE).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(values) != SELECTED_COUNT or len(set(values)) != SELECTED_COUNT or any(OPAQUE.fullmatch(value) is None for value in values):
        raise RuntimeError("V2.42.91 devval opaque-ID source drifted")
    return values


def selected_ids(contract: dict[str, Any]) -> list[str]:
    task = contract.get("task_contract") or {}
    values = task.get("selected_opaque_ids")
    if (
        not isinstance(values, list)
        or len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(not isinstance(value, str) or OPAQUE.fullmatch(value) is None for value in values)
        or payload_sha256(values) != task.get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.42.91 frozen opaque-ID vector drifted")
    return list(values)


def _visible_manifest(root: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in _ordinary(root, SOURCE_MANIFEST).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if (
            not isinstance(raw, dict)
            or set(raw) != {"opaque_id", "question"}
            or not isinstance(raw.get("opaque_id"), str)
            or OPAQUE.fullmatch(raw["opaque_id"]) is None
            or not isinstance(raw.get("question"), str)
            or not raw["question"].strip()
            or raw["opaque_id"] in rows
        ):
            raise RuntimeError("V2.42.91 visible manifest schema drifted")
        rows[raw["opaque_id"]] = {"opaque_id": raw["opaque_id"], "question": raw["question"]}
    return rows


def selected_tasks(root: Path, contract: dict[str, Any]) -> list[dict[str, str]]:
    ids = selected_ids(contract)
    task = contract["task_contract"]
    if (
        ids != source_selected_ids(root)
        or sha256(_ordinary(root, SOURCE_MANIFEST)) != task["manifest_sha256"]
        or sha256(_ordinary(root, ID_SOURCE)) != task["id_source_sha256"]
    ):
        raise RuntimeError("V2.42.91 visible selection identity drifted")
    manifest = _visible_manifest(root)
    if any(value not in manifest for value in ids):
        raise RuntimeError("V2.42.91 selected visible task is absent")
    output = [manifest[value] for value in ids]
    if any(set(row) != {"opaque_id", "question"} for row in output):
        raise RuntimeError("V2.42.91 runtime boundary drifted")
    return output


def validate_forward_contract(root: Path, path: Path = FORWARD_CONTRACT) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, path))
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or not _sealed(value, "forward_contract_payload_sha256")
        or value.get("task_contract", {}).get("runtime_boundary") != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("task_contract", {}).get("mapping_split_category_gold_score_used_for_selection") is not False
        or value.get("execution", {}).get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("execution", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("execution", {}).get("runner_marker") != RUNNER_MARKER
        or value.get("execution", {}).get("child_marker") != CHILD_MARKER
        or value.get("execution", {}).get("output_root") != str(OUTPUT_ROOT)
        or value.get("limits") != LIMITS
        or value.get("two_wave_policy") != TWO_WAVE_POLICY
        or value.get("rescue_policy") != RESCUE_POLICY
        or value.get("model") != MODEL
        or value.get("search") != SEARCH
        or value.get("lease")
        != {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        }
        or value.get("authorization")
        != {"single_consumed_dev64_candidate_forward": True, "additional_rollout_resume_skip_or_rerun": False}
        or value.get("source_policy")
        != {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "candidate_64_predictions_frozen_before_control_or_evaluator_open": True,
            "credential_value_persisted_hashed_or_emitted": False,
        }
    ):
        raise RuntimeError("V2.42.91 forward contract identity drifted")
    manifest = value.get("dependency_manifest")
    if not isinstance(manifest, dict) or value.get("dependency_manifest_sha256") != payload_sha256(manifest):
        raise RuntimeError("V2.42.91 dependency manifest seal drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError(f"V2.42.91 frozen forward dependency drifted: {relative}")
    if selected_ids(value) != source_selected_ids(root) or len(selected_tasks(root, value)) != SELECTED_COUNT:
        raise RuntimeError("V2.42.91 selected task vector drifted")
    return value


__all__ = [name for name in globals() if name.isupper()] + [
    "payload_sha256",
    "read_object",
    "selected_ids",
    "selected_tasks",
    "sha256",
    "source_selected_ids",
    "validate_forward_contract",
]
