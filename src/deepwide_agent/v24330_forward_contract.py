"""Frozen visible-only contract for one shared-prefix paired exact-220 run.

The forward surface deliberately has no mapping, split-label, answer, gold,
evaluator, score, or reward capability.  One visible task is executed once and
produces both a core-only baseline and an entropy-gated reserve candidate.
Evaluator-side joins are authorized only by a separate post-freeze program.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .v24257_score_first_runtime import validate_visible_task
from .v24315_forward_contract import (
    ID_SOURCES,
    SOURCE_MANIFEST,
    source_selected_ids,
    source_selected_shards,
)
from .v24320_forward_contract import protected_watcher_snapshot


DATE = "20260803"
ROLE = "v24330_shared_prefix_paired_exact220_forward_contract"
PROTOCOL_ID = "v24330_shared_prefix_entropy_paired_exact220_v1"
FORWARD_CONTRACT = Path(f"results/v24330_shared_prefix_exact220_forward_contract_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24330_shared_prefix_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24330_shared_prefix_exact220_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24330_shared_prefix_exact220_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24330_shared_prefix_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24330_shared_prefix_exact220_forward_result_v1_{DATE}.json")
EVALUATOR_GATE = Path(f"results/v24330_shared_prefix_exact220_evaluator_gate_v1_{DATE}.json")
EVALUATOR_START = Path(f"results/v24330_shared_prefix_exact220_evaluator_start_v1_{DATE}.json")
FINAL_RESULT = Path(f"results/v24330_shared_prefix_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24330_shared_prefix_exact220_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v24330_shared_prefix_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
PAIR_SUMMARY = OUTPUT_ROOT / "pair_run_summary.json"
RUNTIME_PREDICTIONS = {
    "baseline": OUTPUT_ROOT / "baseline_runtime_predictions.jsonl",
    "candidate": OUTPUT_ROOT / "candidate_runtime_predictions.jsonl",
}
RUN_SUMMARY = {
    "baseline": OUTPUT_ROOT / "baseline_run_summary.json",
    "candidate": OUTPUT_ROOT / "candidate_run_summary.json",
}
PREDICTION_FREEZE = {
    "baseline": OUTPUT_ROOT / "baseline_prediction_freeze.json",
    "candidate": OUTPUT_ROOT / "candidate_prediction_freeze.json",
}
EVALUATOR_ROOT = OUTPUT_ROOT / "postfreeze_evaluator"

LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24330_shared_prefix_paired_exact220_forward_v1"
LEASE_PURPOSE = "label_blind_shared_prefix_paired_exact220_forward"
EVALUATOR_LEASE_OWNER = "v24330_shared_prefix_paired_exact220_evaluator_v1"
EVALUATOR_LEASE_PURPOSE = "postfreeze_both_arm_exact220_official_evaluator"
RUNNER_MARKER = "scripts/run_v24330_shared_prefix_exact220.py"
CHILD_MARKER = "scripts/run_v24330_shared_prefix_exact220_task.py"
FETCH_HELPER_MARKER = "scripts/run_v24287_fetch_helper.py"
CHILD_TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_EXIT_NAME = "parent_exit_receipt.json"

ARMS = ("baseline", "candidate")
SELECTED_COUNT = 220
EXECUTOR_CONCURRENCY = 8
MODEL_SLOT_CAP = 2
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
TASK_WALL_SECONDS = 180
PARENT_TIMEOUT_SECONDS = 200
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_ATTEMPT_SECONDS = 0.05
LIMITS = {
    "wall_seconds": TASK_WALL_SECONDS,
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
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": TASK_WALL_SECONDS,
    "max_retries": 2,
}
SEARCH = {
    "provider": "azure-native-keyless-deadline-shared-prefix-entropy-revision",
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": TASK_WALL_SECONDS,
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
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.43.30 forward path is noncanonical")
    path = root / raw
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.30 expected ordinary forward file: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.43.30 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.30 expected JSON object: {path}")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def selected_ids(contract: Mapping[str, Any]) -> list[str]:
    task = contract.get("task_contract")
    values = task.get("selected_opaque_ids") if isinstance(task, Mapping) else None
    if (
        not isinstance(values, list)
        or len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(
            not isinstance(value, str) or OPAQUE.fullmatch(value) is None
            for value in values
        )
        or payload_sha256(values)
        != task.get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.43.30 frozen opaque-ID vector drifted")
    return list(values)


def _visible_manifest(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in _ordinary(root, SOURCE_MANIFEST).read_text(
        encoding="utf-8"
    ).splitlines():
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
        ):
            raise RuntimeError("V2.43.30 visible manifest schema drifted")
        rows.append(validate_visible_task(raw))
    if len({row["opaque_id"] for row in rows}) != len(rows):
        raise RuntimeError("V2.43.30 visible manifest has duplicate opaque IDs")
    return rows


def selected_tasks(root: Path, contract: Mapping[str, Any]) -> list[dict[str, str]]:
    root = root.resolve()
    ids = selected_ids(contract)
    task_contract = contract["task_contract"]
    if (
        sha256(_ordinary(root, SOURCE_MANIFEST))
        != task_contract.get("manifest_sha256")
        or source_selected_ids(root) != ids
    ):
        raise RuntimeError("V2.43.30 visible selection identity drifted")
    by_id = {row["opaque_id"]: row for row in _visible_manifest(root)}
    if any(value not in by_id for value in ids):
        raise RuntimeError("V2.43.30 selected visible task is absent")
    tasks = [by_id[value] for value in ids]
    if any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.43.30 runtime boundary drifted")
    return tasks


def validate_forward_contract(
    root: Path, path: Path = FORWARD_CONTRACT
) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, path))
    execution = value.get("execution")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    gate = value.get("forward_terminal_contract")
    manifest = value.get("dependency_manifest")
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or value.get("task_contract", {}).get("runtime_boundary")
        != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("selected_count")
        != SELECTED_COUNT
        or value.get("task_contract", {}).get(
            "mapping_split_category_gold_score_used_for_selection"
        )
        is not False
        or not isinstance(execution, Mapping)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("one_shared_prefix_forward_per_visible_task")
        is not True
        or execution.get("two_predictions_from_each_single_task_forward")
        is not True
        or execution.get("resume_skip_rerun_or_selective_retry") is not False
        or execution.get("runner_marker") != RUNNER_MARKER
        or execution.get("child_marker") != CHILD_MARKER
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("protected_watchers")
        != protected_watcher_snapshot()
        or value.get("limits") != LIMITS
        or value.get("model") != MODEL
        or value.get("search") != SEARCH
        or value.get("lease")
        != {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        }
        or not isinstance(source, Mapping)
        or source
        != {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "both_arm_220_prediction_freezes_before_evaluator_resources_open": True,
            "credential_value_persisted_hashed_or_emitted": False,
        }
        or authorization
        != {
            "single_fresh_shared_prefix_paired_exact220_forward": True,
            "additional_rollout_resume_or_rerun": False,
        }
        or gate
        != {
            "required_terminal_pair_tasks": SELECTED_COUNT,
            "required_prediction_rows_per_arm": SELECTED_COUNT,
            "required_valid_parent_exit_receipts": SELECTED_COUNT,
            "forward_failure_policy": "both_arms_failure_as_zero_no_task_rerun",
            "maximum_model_effects_per_pair": 3,
            "maximum_logical_queries_per_pair": 4,
            "maximum_fetch_targets_per_pair": 10,
            "required_repeated_upstream_effects": 0,
            "mapping_or_evaluator_open_before_both_freezes": False,
        }
        or not isinstance(manifest, Mapping)
        or value.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or not _sealed(value, "forward_contract_payload_sha256")
    ):
        raise RuntimeError("V2.43.30 forward contract identity drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError(
                f"V2.43.30 frozen forward dependency drifted: {relative}"
            )
    ids = selected_ids(value)
    if ids != source_selected_ids(root):
        raise RuntimeError("V2.43.30 exact-220 opaque-ID order drifted")
    shards = source_selected_shards(root)
    expected_partitions = [
        {
            "tag": tag,
            "path": str(relative),
            "sha256": sha256(_ordinary(root, relative)),
            "count": expected,
        }
        for tag, relative, expected in ID_SOURCES
    ]
    if value["task_contract"].get("partitions") != expected_partitions:
        raise RuntimeError("V2.43.30 exact-220 partition drifted")
    if value["task_contract"].get("partition_vector_sha256") != payload_sha256(
        [{"tag": tag, "ids": values} for tag, values in shards]
    ):
        raise RuntimeError("V2.43.30 partition vector drifted")
    if len(selected_tasks(root, value)) != SELECTED_COUNT:
        raise RuntimeError("V2.43.30 exact-220 visible task count drifted")
    return value


__all__ = [
    "ACTIVATION",
    "ARMS",
    "CHILD_MARKER",
    "CHILD_TERMINAL_NAME",
    "CLEANUP_RESERVE_SECONDS",
    "DATE",
    "EVALUATOR_LEASE_OWNER",
    "EVALUATOR_LEASE_PURPOSE",
    "EVALUATOR_GATE",
    "EVALUATOR_ROOT",
    "EVALUATOR_START",
    "EXECUTION_START",
    "EXECUTOR_CONCURRENCY",
    "FETCH_HELPER_MARKER",
    "FINAL_RESULT",
    "FORWARD_CONTRACT",
    "FORWARD_RESULT",
    "LEASE_OWNER",
    "LEASE_PATH",
    "LEASE_PURPOSE",
    "LIMITS",
    "MINIMUM_ATTEMPT_SECONDS",
    "MODEL",
    "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY",
    "MODEL_SLOT_POOL_ID",
    "OUTPUT_ROOT",
    "PAIR_SUMMARY",
    "PARENT_EXIT_NAME",
    "PARENT_TIMEOUT_SECONDS",
    "POSTAUDIT",
    "PREAUDIT",
    "PREDICTION_FREEZE",
    "PROTOCOL",
    "PROTOCOL_ID",
    "ROLE",
    "RUNNER_MARKER",
    "RUNTIME_PREDICTIONS",
    "RUN_SUMMARY",
    "SAFE_PROGRESS",
    "SEARCH",
    "SELECTED_COUNT",
    "SOURCE_MANIFEST",
    "TASK_ROOT",
    "TASK_WALL_SECONDS",
    "payload_sha256",
    "protected_watcher_snapshot",
    "read_object",
    "selected_ids",
    "selected_tasks",
    "sha256",
    "validate_forward_contract",
]
